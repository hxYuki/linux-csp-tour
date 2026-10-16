"""Validate all real ASAR packed files and a complete install/reapply/rollback in temp HOME.

Usage: python3 tests/verify_local_fixture.py /path/to/extracted/TourBox-directory
Vendor files remain external fixtures and are never included in this package.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('addon', ROOT / 'install.py')
addon = importlib.util.module_from_spec(spec); spec.loader.exec_module(addon)
source = Path(sys.argv[1]).resolve()


def entries(raw):
    size = struct.unpack_from('<I', raw, 12)[0]
    head = json.loads(raw[16:16 + size])
    data = raw[8 + struct.unpack_from('<I', raw, 4)[0]:]
    result = {}
    def walk(node, prefix=''):
        for name, value in node['files'].items():
            path = prefix + name
            if 'files' in value:
                walk(value, path + '/')
            elif not value.get('unpacked') and 'offset' in value:
                start = int(value['offset']); content = data[start:start + value['size']]
                if 'integrity' in value:
                    assert hashlib.sha256(content).hexdigest() == value['integrity']['hash'], path
                    block = value['integrity']['blockSize']
                    assert value['integrity']['blocks'] == [hashlib.sha256(content[i:i + block]).hexdigest() for i in range(0, max(1, len(content)), block)], path
                result[path] = content
    walk(head)
    return result


raw = (source / 'app/resources/app.asar').read_bytes()
patched = addon.patch_asar(raw)
before, after = entries(raw), entries(patched)
assert before.keys() == after.keys()
assert [name for name in before if before[name] != after[name]] == ['out/main/index.js']
assert addon.patch_asar(patched) == patched
print('PASS real ASAR:', len(before), 'packed entries checked; only main script changed')

with tempfile.TemporaryDirectory() as tmp:
    home = Path(tmp) / 'home with spaces'; home.mkdir()
    prefix = home / '.wine-csp'; roaming = prefix / 'drive_c/users/test/AppData/Roaming'
    roaming.mkdir(parents=True)
    share = home / '.local/share/cspenguin'; share.mkdir(parents=True)
    # A stand-in for the installed export block, including a new upstream-only flag.
    (share / 'csp-launch.sh').write_text('#!/bin/bash\nexport PATH="runner:$PATH"\nexport WINEPREFIX="prefix"\nexport UPSTREAM_FLAG=preserved\nwine app.exe\n')
    config = {'prefix': str(prefix), 'cspenguin': str(share), 'wine': str(share / 'wine-11.4/bin/wine'),
              'wine_user': 'test', 'serial': '/dev/serial/by-id/test', 'locale': 'zh_CN.UTF-8', 'proxy': ''}
    with mock.patch.object(Path, 'home', return_value=home):
        fixture = Path(tmp) / 'vendor-fixture'; fixture.mkdir()
        for filename in ('LibTW.dec', 'TourBox Console.exe', 'app'):
            (fixture / filename).symlink_to(source / filename)
        (fixture / 'TourBox Console.json').write_bytes((source / ('TourBox Console.original.json' if (source / 'TourBox Console.original.json').exists() else 'TourBox Console.json')).read_bytes())
        plan = addon.plan_files(config, fixture, False)
        transaction = addon.Transaction(home / 'backups/first')
        for path, data, mode in plan:
            transaction.write(path, data, mode)
        # Re-plan against the installed patched vendor files using only the fixture copies needed for version guards.
        installed = prefix / 'drive_c/Program Files/TourBox Console'
        import shutil
        for filename in ('LibTW.dec', 'TourBox Console.exe'):
            shutil.copy2(source / filename, installed / filename)
        second = addon.Transaction(home / 'backups/second')
        for path, data, mode in addon.plan_files(config, installed, False):
            second.write(path, data, mode)
        assert second.record['files'] == [], [f['path'] for f in second.record['files']]
        runtime = Path(tmp) / 'runtime'; runtime.mkdir(mode=0o700)
        for path in home.rglob('*.service'):
            result = subprocess.run(['systemd-analyze', '--user', 'verify', str(path)], capture_output=True, text=True,
                                    env={**os.environ, 'XDG_RUNTIME_DIR': str(runtime)})
            assert result.returncode == 0, result.stderr
        for path in home.rglob('*.desktop'):
            result = subprocess.run(['desktop-file-validate', str(path)], capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
        # Exercise launch wrappers with stand-in Wine/serial/systemd programs.
        # No real device, user manager, display, registry, or app is used.
        stubs = Path(tmp) / 'commands'; stubs.mkdir()
        scripts = {
            'systemctl': '#!/bin/bash\n[[ "$*" != *is-active* ]]\n',
            'fuser': '#!/bin/sh\nexit 1\n',
            'xrandr': '#!/bin/sh\nprintf "Monitors: 1\\n"\n',
            'stty': '#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/stty-calls"\n',
            'winepath': '#!/bin/sh\nprintf "Z:%s\\n" "$2"\n',
        }
        for name, content in scripts.items():
            path = stubs / name; path.write_text(content); path.chmod(0o755)
        wine = Path(config['wine']); wine.parent.mkdir(parents=True)
        wine.write_text('''#!/usr/bin/python3
import os,json,sys
from pathlib import Path
with (Path.home()/'wine-calls').open('a') as f:
 f.write(json.dumps({'args':sys.argv[1:], 'fd9':Path('/proc/self/fd/9').exists(), 'prefix':os.getenv('WINEPREFIX'), 'upstream':os.getenv('UPSTREAM_FLAG')})+'\\n')
'''); wine.chmod(0o755)
        exports = home / '.local/share/linux-csp-tour/upstream-exports.sh'
        exports.write_text('export PATH=' + __import__('shlex').quote(str(stubs)) + ':$PATH\nexport UPSTREAM_FLAG=preserved\n')
        config['serial'] = str(Path(tmp) / 'serial-device')
        Path(config['serial']).touch(); (prefix / 'dosdevices').mkdir()
        cfgdir = home / '.local/share/linux-csp-tour'
        (cfgdir / 'config.json').write_text(json.dumps(config))
        (cfgdir / 'config.sh').write_text('\n'.join('compat_'+key+'='+__import__('shlex').quote(config[key]) for key in ('prefix','cspenguin','wine','serial','locale','proxy'))+'\n')
        env = {**os.environ, 'HOME':str(home), 'USER':'fixture', 'XDG_RUNTIME_DIR':str(runtime),
               'DISPLAY':':fixture', 'WAYLAND_DISPLAY':'wayland-fixture', 'XDG_CURRENT_DESKTOP':'KDE', 'XDG_SESSION_TYPE':'wayland'}
        for key in ('XDG_DATA_HOME','XDG_CONFIG_HOME','XDG_STATE_HOME'):
            env.pop(key, None)
        result = subprocess.run([str(cfgdir / 'tourbox-run.sh')], env=env, capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr + (home / '.local/state/linux-csp-tour/console.log').read_text()
        calls = [json.loads(line) for line in (home/'wine-calls').read_text().splitlines()]
        assert len(calls) == 4 and calls[-1]['args'] == ['TourBox Console.exe'], calls
        assert all(not call['fd9'] and call['prefix'] == str(prefix) for call in calls)
        assert 'raw 115200 cs8 -cstopb -parenb -ixon -ixoff -crtscts clocal -hupcl' in (home/'stty-calls').read_text()
        result = subprocess.run([str(home/'.local/bin/csp-tour'), 'paint', '/fixture/a drawing.clip'], env=env,
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        paint = json.loads((home/'wine-calls').read_text().splitlines()[-1])
        assert paint['upstream'] == 'preserved' and paint['args'][-1] == 'Z:/fixture/a drawing.clip', paint
        # Undo fixture-specific edits before testing the normal rollback receipt.
        for path, data, mode in plan:
            addon.atomic(path, data, mode)
        _, conflicts = addon.restore_files(transaction.directory)
        assert not conflicts, conflicts
        assert not (home / '.local/bin/csp-tour').exists()
print('PASS full temp-HOME install, unchanged second apply, services/desktops, wrappers/raw serial/FD isolation, rollback')
