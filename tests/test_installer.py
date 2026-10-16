import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('addon', ROOT / 'install.py')
addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(addon)


class InstallerTests(unittest.TestCase):
    def test_xml_preserves_pairing_and_presets_and_is_idempotent(self):
        original = b'<map><entry><string>RemoteController</string><string>local-secret</string></entry><entry><string>preset</string><string>14</string></entry><entry><string>bleSupport</string><string>true</string></entry></map>'
        patched = addon.patch_xml(original)
        entries = {e[0].text: e[1].text for e in ET.fromstring(patched)}
        self.assertEqual(entries['RemoteController'], 'local-secret')
        self.assertEqual(entries['preset'], '14')
        self.assertEqual(entries['bleSupport'], 'false')
        self.assertEqual(entries['ignoreWinMonitor'], 'true')
        self.assertEqual(entries['autoBoot'], 'false')
        self.assertEqual(patched, addon.patch_xml(patched))

    def test_vm_agent_order_and_diagnostic_rejection(self):
        original = {'vmArgs': ['-agentpath:LibH.dll', '-Xmx1g', '-agentpath:old\\tourbox-wine-compat.dll'], 'classPath': ['LibTW.dec']}
        patched = addon.patch_json(json.dumps(original).encode())
        args = json.loads(patched)['vmArgs']
        self.assertEqual(args[:2], ['-agentpath:LibH.dll', r'-agentpath:win64libs\tourbox-wine-compat.dll'])
        self.assertEqual(args.count('-Xmx1g'), 1)
        self.assertEqual(patched, addon.patch_json(patched))
        original['vmArgs'].append('-agentpath:console-stack.dll')
        with self.assertRaises(RuntimeError):
            addon.patch_json(json.dumps(original).encode())

    def test_asar_guard_idempotence_and_unrelated_data(self):
        source = b'prefix\nelectron["app"]["whenReady"]()\nsuffix'
        other = b'untouched packed file'
        node = {'offset': '0', 'size': len(source), 'integrity': {'blockSize': 16, 'hash': hashlib.sha256(source).hexdigest()}}
        head = {'files': {'out': {'files': {'main': {'files': {'index.js': node}}}},
                          'other': {'offset': str(len(source)), 'size': len(other)}}}
        packed = json.dumps(head).encode(); pad = (-len(packed)) % 4
        raw = struct.pack('<4I', 4, 8 + len(packed) + pad, 4 + len(packed) + pad, len(packed)) + packed + b'\0' * pad + source + other
        with self.assertRaises(RuntimeError):
            addon.patch_asar(raw)
        with mock.patch.object(addon, 'INDEX_HASH', hashlib.sha256(source).hexdigest()):
            patched = addon.patch_asar(raw)
            self.assertEqual(patched, addon.patch_asar(patched))
            offset = 8 + struct.unpack_from('<I', patched, 4)[0]
            self.assertEqual(patched[offset:offset + len(source) + len(other)], source + other)

    def test_transaction_idempotence_and_rollback_preserves_later_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); original = base / 'original'; new = base / 'new'; changed = base / 'changed'
            original.write_bytes(b'old'); original.chmod(0o640)
            transaction = addon.Transaction(base / 'backup')
            transaction.write(original, b'new')
            transaction.write(new, b'created')
            transaction.write(changed, b'installed')
            transaction.write(new, b'created')
            self.assertEqual(len(transaction.record['files']), 3)
            changed.write_bytes(b'user edited after install')
            receipt, conflicts = addon.restore_files(base / 'backup')
            self.assertEqual(original.read_bytes(), b'old')
            self.assertEqual(original.stat().st_mode & 0o777, 0o640)
            self.assertFalse(new.exists())
            self.assertEqual(conflicts, [str(changed)])
            self.assertEqual(changed.read_bytes(), b'user edited after install')

    def test_shortcuts_preserve_user_rows_and_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'default.khc'
            patched = addon.patch_shortcuts(path)
            path.write_bytes(patched)
            self.assertEqual(patched, addon.patch_shortcuts(path))
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM shortcutmenu').fetchone()[0], 2)
                db.execute('DELETE FROM shortcutmenu')
                db.execute("INSERT INTO shortcutmenu (menucommandtype,menucommand,shortcut,modifier) VALUES ('custom','user-action','F17',0)")
                db.commit()
            before = path.read_bytes()
            with self.assertRaises(RuntimeError):
                addon.patch_shortcuts(path)
            self.assertEqual(before, path.read_bytes())

    def test_existing_unassigned_picker_binding_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'default.khc'
            path.write_bytes(addon.patch_shortcuts(path))
            with closing(sqlite3.connect(path)) as db:
                db.execute("UPDATE shortcutmenu SET shortcut='NULL' WHERE menucommand='applicationscreeneyecolorpicker'")
                db.commit()
            before = path.read_bytes()
            self.assertEqual(before, addon.patch_shortcuts(path))

    def test_profile_aliases_are_deduplicated_but_distinct_profiles_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            users = Path(tmp)
            (users / 'artist/AppData/Roaming/TourBox Console').mkdir(parents=True)
            (users / 'alias').symlink_to('artist', target_is_directory=True)
            self.assertEqual(addon.find_wine_user(users), 'artist')
            self.assertEqual(addon.find_wine_user(users, 'alias'), 'alias')
            (users / 'another/AppData/Roaming/TourBox Console').mkdir(parents=True)
            with self.assertRaises(RuntimeError):
                addon.find_wine_user(users)

    def test_fresh_profile_without_application_settings_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            users = Path(tmp)
            (users / 'Public').mkdir()
            (users / 'newuser').mkdir()
            self.assertEqual(addon.find_wine_user(users), 'newuser')

    def test_reuses_upstream_exports_without_legacy_display_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'launch.sh'
            path.write_text('#!/bin/bash\nexport PATH="runner:$PATH"\nexport WINEPREFIX="old"\nexport WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--no-sandbox --proxy-server=http://proxy.example:8080 --disable-sync"\n\n# Legacy\nsystemctl --user start legacy-display.service\nexport DISPLAY=:99\nwine app.exe\n')
            result = addon.extract_exports(path).decode()
            self.assertIn('--no-sandbox', result)
            self.assertIn('--disable-sync', result)
            self.assertIn('proxy.example', result)
            self.assertNotIn('DISPLAY', result)
            self.assertNotIn('systemctl', result)

    def test_protocol_defaults_preserve_other_associations(self):
        original = b'# user comment\n[Default Applications]\ntext/plain=my-editor.desktop;\nx-scheme-handler/clipstudio=old.desktop;\n[Added Associations]\nimage/png=paint.desktop;\n'
        patched = addon.patch_protocol_defaults(original)
        self.assertIn(b'text/plain=my-editor.desktop;', patched)
        self.assertIn(b'[Added Associations]\nimage/png=paint.desktop;', patched)
        self.assertNotIn(b'old.desktop', patched)
        self.assertEqual(patched, addon.patch_protocol_defaults(patched))
        self.assertIn(b'text/plain=editor.desktop;\nx-scheme-handler/',
                      addon.patch_protocol_defaults(b'[Default Applications]\ntext/plain=editor.desktop;'))

    def test_launcher_paths_are_read_without_executing_shell_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp); launcher = home / 'launcher.sh'
            launcher.write_text('export PATH="runner:$PATH"\nexport WINEPREFIX="$HOME/art prefix"\nexport WINESERVER="${HOME}/runner/bin/wineserver"\nexit 9\n')
            self.assertEqual(addon.launcher_value(launcher, 'WINEPREFIX', home), str(home / 'art prefix'))
            self.assertEqual(addon.launcher_value(launcher, 'WINESERVER', home), str(home / 'runner/bin/wineserver'))
            launcher.write_text('export PATH="runner:$PATH"\nexport WINEPREFIX="$(touch unwanted)"\n')
            with self.assertRaises(RuntimeError):
                addon.launcher_value(launcher, 'WINEPREFIX', home)

    def test_permissions_only_changes_can_be_rolled_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); path = base / 'file'; path.write_bytes(b'same'); path.chmod(0o640)
            transaction = addon.Transaction(base / 'backup')
            transaction.write(path, b'same', 0o644)
            _, conflicts = addon.restore_files(transaction.directory)
            self.assertFalse(conflicts)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_large_payloads_are_streamed_from_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); source = base / 'source'; source.write_bytes(b'data' * 1000)
            target = base / 'target'; transaction = addon.Transaction(base / 'backup')
            transaction.write(target, source)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertFalse(addon.restore_files(transaction.directory)[1])

    def test_serial_discovery_deduplicates_links_and_refuses_ambiguity(self):
        serial_spec = importlib.util.spec_from_file_location('serial_device', ROOT / 'lib/serial-device.py')
        serial = importlib.util.module_from_spec(serial_spec); serial_spec.loader.exec_module(serial)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); device = base / 'tty'; device.touch(); by_id = base / 'by-id'; by_id.mkdir()
            (by_id / 'usb-TourBox-NEO-example').symlink_to(device)
            (by_id / 'usb-TourBox-NEO-other-link').symlink_to(device)
            self.assertTrue(serial.select_serial(directory=by_id).endswith('usb-TourBox-NEO-example'))
            (base / 'tty2').touch(); (by_id / 'usb-TourBox-NEO-second').symlink_to(base / 'tty2')
            with self.assertRaises(RuntimeError):serial.select_serial(directory=by_id)
            self.assertEqual(serial.select_serial(str(device), by_id), str(device))


if __name__ == '__main__':
    unittest.main()
