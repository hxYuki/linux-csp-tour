#!/usr/bin/env python3
"""Transactional, version-guarded add-on for an existing CSPenguin installation."""
import argparse
from contextlib import closing
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import stat
import struct
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
JAR_HASH = '5ff44ed8ee8553311c4562fa7b4c96f0c105d1ea36038db60d01af87aa4024ed'
EXE_HASH = '86aa460f5a159392ffc9b6a2bef8cfdef180d681b056b35b4e20296c041d3b90'
INDEX_HASH = '3777ed70b40266d23e7db61f76f662fd23795956884151dd42d0b2c11fb81435'
PAYLOAD = ('// Local Wine rendering compatibility, before Electron readiness.\n'
           'electron.app.disableHardwareAcceleration();\n'
           'logger.info("[tourbox-wine-compat] Electron software rendering enabled");\n')
SERVICES = ('tourbox-console.service', 'csp-display-cache.service', 'csp-navigator-parent.service')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(argv, **kwargs):
    return subprocess.run(argv, text=True, capture_output=True, timeout=20, **kwargs)


def content_digest(data):
    return digest(data) if isinstance(data, Path) else hashlib.sha256(data).hexdigest()


def atomic(path, data, mode):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            if isinstance(data, Path):
                with data.open('rb') as source:
                    shutil.copyfileobj(source, stream, length=1024 * 1024)
            else:
                stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class Transaction:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, mode=0o700)
        self.record = {'version': 1, 'uid': os.getuid(), 'state': 'applying', 'files': [], 'services': {}}
        self.save()

    def save(self):
        atomic(self.directory / 'receipt.json', (json.dumps(self.record, indent=2) + '\n').encode(), 0o600)

    def write(self, path, data, mode=0o644):
        path = Path(path).absolute()
        require(not path.is_symlink(), f'Refusing to overwrite symlink: {path}')
        if path.exists() and digest(path) == content_digest(data) and stat.S_IMODE(path.stat().st_mode) == mode:
            return
        before = None
        if path.exists():
            require(path.is_file(), f'Not a regular file: {path}')
            backup = str(len(self.record['files'])) + '.before'
            shutil.copy2(path, self.directory / backup)
            before = {'backup': backup, 'sha256': digest(path), 'mode': stat.S_IMODE(path.stat().st_mode)}
        entry = {'path': str(path), 'before': before, 'sha256': content_digest(data), 'mode': mode}
        self.record['files'].append(entry)
        self.save()  # journal before replacing, so interruption is recoverable
        atomic(path, data, mode)


def restore_files(directory):
    directory = Path(directory).resolve()
    receipt = json.loads((directory / 'receipt.json').read_text())
    require(receipt['uid'] == os.getuid(), 'Run rollback as the original installing user')
    conflicts = []
    for entry in reversed(receipt['files']):
        path = Path(entry['path'])
        old = entry['before']
        if path.is_symlink() or (path.exists() and not path.is_file()):
            conflicts.append(str(path)); continue
        current = digest(path) if path.exists() else None
        current_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
        if old and current == old['sha256'] and current_mode == old['mode']:
            continue  # already restored, or the journal write preceded an interrupted replacement
        if current is None and old is None:
            continue
        if current != entry['sha256'] or current_mode != entry['mode']:
            conflicts.append(str(path)); continue
        if old:
            backup = directory / old['backup']
            require(digest(backup) == old['sha256'], f'Backup checksum mismatch: {backup}')
            atomic(path, backup.read_bytes(), old['mode'])
        else:
            path.unlink()
    receipt['state'] = 'rollback-conflicts' if conflicts else 'rolled-back'
    atomic(directory / 'receipt.json', (json.dumps(receipt, indent=2) + '\n').encode(), 0o600)
    return receipt, conflicts


def patch_asar(raw):
    require(len(raw) >= 16, 'Invalid ASAR')
    header_size, json_size = struct.unpack_from('<I', raw, 4)[0], struct.unpack_from('<I', raw, 12)[0]
    require(16 + json_size <= 8 + header_size <= len(raw), 'Invalid ASAR header bounds')
    head = json.loads(raw[16:16 + json_size])
    data = raw[8 + header_size:]
    node = head['files']['out']['files']['main']['files']['index.js']
    start = int(node['offset'])
    require(0 <= start <= start + node['size'] <= len(data), 'ASAR script outside archive')
    original = data[start:start + node['size']]
    anchor = b'electron["app"]["whenReady"]()'
    expected = hashlib.sha256(original).hexdigest()
    patched_hash = hashlib.sha256(original.replace(PAYLOAD.encode(), b'', 1)).hexdigest()
    if original.count(PAYLOAD.encode()) == 1 and patched_hash == INDEX_HASH:
        return raw
    require(expected == INDEX_HASH and original.count(anchor) == 1,
            'Unsupported TourBox Electron build; archive left unchanged')
    new = original.replace(anchor, PAYLOAD.encode() + anchor)
    node['offset'], node['size'] = str(len(data)), len(new)
    block_size = node['integrity']['blockSize']
    require(block_size > 0, 'Invalid ASAR integrity block size')
    node['integrity']['hash'] = hashlib.sha256(new).hexdigest()
    node['integrity']['blocks'] = [hashlib.sha256(new[i:i + block_size]).hexdigest()
                                    for i in range(0, len(new), block_size)]
    packed = json.dumps(head, ensure_ascii=False, separators=(',', ':')).encode()
    pad = (-len(packed)) % 4
    return (struct.pack('<4I', 4, 8 + len(packed) + pad, 4 + len(packed) + pad, len(packed))
            + packed + b'\0' * pad + data + new)


def patch_json(raw):
    value = json.loads(raw)
    args = value['vmArgs']
    require(isinstance(args, list), 'Invalid TourBox vmArgs')
    require(not any('classdump' in x or 'console-stack' in x or 'purejavacomm.loglevel' in x for x in args),
            'Temporary diagnostic arguments found; remove them before applying')
    args = [x for x in args if not (x.startswith('-agentpath:') and 'tourbox-wine-compat' in x)]
    indices = [i for i, x in enumerate(args) if x.lower() == '-agentpath:libh.dll']
    require(len(indices) == 1, 'Expected the original LibH agent exactly once')
    args.insert(indices[0] + 1, r'-agentpath:win64libs\tourbox-wine-compat.dll')
    value['vmArgs'] = args
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def patch_xml(raw):
    root = ET.fromstring(raw) if raw else ET.Element('map')
    require(root.tag == 'map', 'Unknown TourBox customConfig format')
    for key, value in {'bleSupport': 'false', 'ignoreWinMonitor': 'true', 'autoBoot': 'false'}.items():
        found = []
        for entry in root.findall('entry'):
            strings = entry.findall('string')
            if strings and strings[0].text == key:
                require(len(strings) == 2, f'Unknown customConfig entry: {key}')
                strings[1].text = value
                found.append(entry)
        require(len(found) <= 1, f'Duplicate customConfig entry: {key}')
        if not found:
            entry = ET.SubElement(root, 'entry')
            ET.SubElement(entry, 'string').text = key
            ET.SubElement(entry, 'string').text = value
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def patch_shortcuts(path):
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / 'shortcuts.sqlite'
        with closing(sqlite3.connect(target)) as db:
            if path.exists():
                with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as original:
                    original.backup(db)
            require(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Shortcut database is corrupt')
            before = db.total_changes
            db.execute('CREATE TABLE IF NOT EXISTS shortcutmenu (_PW_ID INTEGER PRIMARY KEY AUTOINCREMENT, '
                       'menucommandtype TEXT, menucommand TEXT, shortcut TEXT, modifier INTEGER)')
            for command, key in [('applicationscreeneyecolorpicker', 'F17'),
                                 ('applicationremotecontrollerconnection', 'F18')]:
                if db.execute('SELECT 1 FROM shortcutmenu WHERE menucommand=?', (command,)).fetchone():
                    continue  # preserve any existing user binding for this action
                require(not db.execute('SELECT 1 FROM shortcutmenu WHERE shortcut=? AND modifier=0', (key,)).fetchone(),
                        f'{key} is already assigned; resolve that shortcut conflict first')
                db.execute('INSERT INTO shortcutmenu (menucommandtype,menucommand,shortcut,modifier) VALUES (?,?,?,0)',
                           ('advancedcommand', command, key))
            if path.exists() and db.total_changes == before:
                return path.read_bytes()
            db.commit()
        return target.read_bytes()


def extract_exports(path):
    """Reuse upstream's export block; discard old launch actions and private displays."""
    result = []
    started = False
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith('export '):
            result.append(line)
            started = True
        elif started and stripped and not stripped.startswith('#'):
            break
    require(any(line.startswith('export WINEPREFIX=') for line in result)
            and any(line.startswith('export PATH=') for line in result),
            f'Cannot identify CSPenguin export block in {path}')
    # Keep installed upstream flags, including any intentional local proxy setting.
    require(not any(re.match(r'export\s+(DISPLAY|WAYLAND_DISPLAY)=', line) for line in result),
            'Unexpected hard-coded display in upstream exports')
    return ('\n'.join(result) + '\n').encode()


def patch_protocol_defaults(raw):
    lines = raw.decode('utf-8').splitlines(keepends=True)
    wanted = {'x-scheme-handler/clipstudio', 'x-scheme-handler/clipstudiopaint'}
    start = next((i for i, line in enumerate(lines) if line.strip() == '[Default Applications]'), None)
    if start is None:
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines.extend(['\n', '[Default Applications]\n'])
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith('[')), len(lines))
    seen = set()
    for i in range(start + 1, end):
        key = lines[i].split('=', 1)[0].strip()
        if key in wanted:
            require(key not in seen, f'Duplicate protocol default: {key}')
            lines[i] = key + '=clipstudio-url-handler.desktop;\n'
            seen.add(key)
    if end > 0 and not lines[end - 1].endswith('\n'):
        lines[end - 1] += '\n'
    lines[end:end] = [key + '=clipstudio-url-handler.desktop;\n' for key in sorted(wanted - seen)]
    return ''.join(lines).encode()


def running_apps(prefix):
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            values = dict(x.split(b'=', 1) for x in (proc / 'environ').read_bytes().split(b'\0') if b'=' in x)
            command = (proc / 'cmdline').read_bytes().split(b'\0')[0].decode(errors='replace')
            if (Path(os.fsdecode(values.get(b'WINEPREFIX', b'/nonexistent'))).resolve() == prefix.resolve()
                    and any(x in command.casefold() for x in ('clipstudio', 'tourbox'))):
                found.append((proc.name, command))
        except (OSError, ValueError):
            pass
    return found


def find_wine_user(users, explicit=None):
    if explicit:
        require(Path(explicit).name == explicit and explicit not in ('.', '..'), 'Invalid Windows profile name')
        require((users / explicit).is_dir(), 'Windows profile is missing')
        return explicit
    available = [path for path in users.iterdir() if path.is_dir()
                 and path.name.lower() not in ('public', 'default', 'default user')]
    candidates = [path for path in available if (path / 'AppData/Roaming/CELSYSUserData').exists()
                  or (path / 'AppData/Roaming/TourBox Console').exists()] or available
    groups = {}
    for path in candidates:
        groups.setdefault(path.resolve(), []).append(path)
    require(len(groups) == 1, 'Cannot uniquely identify the Windows profile; pass --wine-user NAME')
    aliases = next(iter(groups.values()))
    # Multiple names can refer to the same profile; count its actual directory once.
    return min(aliases, key=lambda path: (path.is_symlink(), path.name)).name


def launcher_value(launcher, key, home):
    """Read simple installer-generated export values without executing the launcher."""
    exports = extract_exports(launcher).decode()
    for line in exports.splitlines():
        fields = shlex.split(line)
        for item in fields[1:]:
            if item.startswith(key + '='):
                value = item.split('=', 1)[1]
                require('$(' not in value and '`' not in value, f'Unsupported command expansion in {key}')
                value = value.replace('${HOME}', str(home)).replace('$HOME', str(home))
                require('$' not in value, f'Cannot resolve {key} from the CSPenguin launcher; specify the path explicitly')
                return value
    return None


def resolve_configuration(args):
    home = Path.home()
    share = Path(args.cspenguin).expanduser() if args.cspenguin else home / '.local/share/cspenguin'
    launcher = share / 'csp-launch.sh'
    require(launcher.is_file(), f'Current user CSPenguin launcher missing: {launcher}')
    prefix = Path(args.prefix or launcher_value(launcher, 'WINEPREFIX', home) or home / '.wine-csp').expanduser().absolute()
    require(prefix.is_dir(), f'CSPenguin prefix is missing or inaccessible: {prefix}')
    require(prefix.stat().st_uid == os.getuid(), 'The CSPenguin prefix must belong to the current user')
    server = launcher_value(launcher, 'WINESERVER', home) if not args.wine else None
    wine = Path(args.wine).expanduser() if args.wine else Path(server).with_name('wine') if server else share / 'wine-11.4/bin/wine'
    require(os.access(wine, os.X_OK), f'Wine runtime missing: {wine}')
    version = run([str(wine), '--version'], check=True).stdout.strip()
    require(re.match(r'^wine-11\.4(?:\s|$)', version),
            f'The display-cache helper is bound to Wine 11.4; found {version}')
    users = prefix / 'drive_c/users'
    wine_user = find_wine_user(users, args.wine_user)
    return {'prefix': str(prefix), 'cspenguin': str(share.absolute()), 'wine': str(wine.absolute()),
            'wine_user': wine_user, 'serial': args.serial or '',
            'locale': args.locale or os.environ.get('LC_ALL') or os.environ.get('LANG') or 'C.UTF-8',
            'proxy': args.proxy or ''}


def preflight(config, readonly=False):
    prefix, share = Path(config['prefix']), Path(config['cspenguin'])
    if not readonly:
        require(not running_apps(prefix), 'CSP or TourBox is running. Save your work and close both normally, then retry.')
    for name in ('bin/csp-tour', 'bin/tourbox-compat-run', 'lib/environment.sh'):
        result = run(['bash', '-n', str(ROOT / name)])
        require(result.returncode == 0, result.stderr)
    for name, expected in json.loads((ROOT / 'payload/SHA256.json').read_text()).items():
        require(digest(ROOT / 'payload' / name) == expected, f'Payload checksum mismatch: {name}')
    require((prefix / 'drive_c/Program Files/CELSYS/CLIP STUDIO 1.5/CLIP STUDIO PAINT/CLIPStudioPaint.exe').is_file(),
            'Install CSP with CSPenguin before applying this add-on')
    extract_exports(share / 'csp-launch.sh')
    require(os.environ.get('XDG_SESSION_TYPE') == 'wayland' and 'KDE' in os.environ.get('XDG_CURRENT_DESKTOP', '')
            and os.environ.get('DISPLAY'), 'Apply from a terminal inside the target user’s Plasma Wayland session')
    for command in ('systemctl', 'xrandr', 'stty', 'flock', 'fuser'):
        require(shutil.which(command), f'Missing dependency: {command}')
    require(run(['/usr/bin/python3', '-c', 'import Xlib; from gi.repository import GLib']).returncode == 0,
            'Missing Python packages: Xlib, PyGObject (Arch: python-xlib python-gobject)')
    locales = run(['locale', '-a'], check=True).stdout.lower().replace('-', '')
    require(config['locale'].lower().replace('-', '') in locales, f'Locale is not generated: {config["locale"]}')
    require(run(['systemctl', '--user', 'show-environment']).returncode == 0, 'User systemd manager unavailable')
    if not readonly:
        require(run(['systemctl', '--user', 'is-active', '--quiet', 'tourbox-console.service']).returncode != 0,
                'The Console service is still active. Exit Console normally and stop its service before applying.')


def tourbox_source(args, config, temporary):
    app = Path(config['prefix']) / 'drive_c/Program Files/TourBox Console'
    if app.is_dir() and not args.tourbox_installer:
        return app, False
    require(args.tourbox_installer, 'TourBox is absent; pass --tourbox-installer /path/to/5.12.0.exe')
    sevenzip = shutil.which('7z') or shutil.which('7zz')
    require(sevenzip, 'Install 7zip to extract the official TourBox installer')
    installer = Path(args.tourbox_installer).expanduser().resolve()
    require(installer.is_file(), f'Installer not found: {installer}')
    # Extract to staging first; no Wine installation or privileged driver installer runs.
    subprocess.run([sevenzip, 'x', '-tNSIS', '-y', f'-o{temporary}', str(installer)], check=True,
                   stdout=subprocess.DEVNULL, timeout=180)
    candidates = list(Path(temporary).rglob('TourBox Console.exe'))
    require(len(candidates) == 1, 'Cannot identify official TourBox application directory')
    extracted = candidates[0].parent
    require(digest(extracted / 'LibTW.dec') == JAR_HASH and digest(extracted / 'TourBox Console.exe') == EXE_HASH,
            'Unsupported TourBox installer build; nothing installed')
    return (app, False) if app.is_dir() else (extracted, True)


def plan_files(config, source, fresh):
    prefix, share, home = Path(config['prefix']), Path(config['cspenguin']), Path.home()
    target = home / '.local/share/linux-csp-tour'
    require(digest(source / 'LibTW.dec') == JAR_HASH and digest(source / 'TourBox Console.exe') == EXE_HASH,
            'Only the observed TourBox Console 5.12.0 build is supported; no files changed')
    plan = []
    add = lambda p, b, m=0o644: plan.append((p, b, m))
    app = prefix / 'drive_c/Program Files/TourBox Console'
    if fresh:
        for item in sorted(source.rglob('*')):
            relative = item.relative_to(source)
            if any(part.startswith('$') for part in relative.parts) or not item.is_file():
                continue
            require(not item.is_symlink(), 'Unexpected symlink in TourBox installer')
            if str(relative) in ('TourBox Console.json', 'app/resources/app.asar', 'win64libs/libBLEWrapper.dll'):
                continue
            add(app / relative, item)
    add(app / 'TourBox Console.json', patch_json((source / 'TourBox Console.json').read_bytes()))
    add(app / 'app/resources/app.asar', patch_asar((source / 'app/resources/app.asar').read_bytes()))
    for name in ('tourbox-wine-compat.dll', 'libBLEWrapper.dll', 'winsqlite3.dll'):
        add(app / 'win64libs' / name, (ROOT / 'payload' / name).read_bytes())
    roaming = prefix / 'drive_c/users' / config['wine_user'] / 'AppData/Roaming'
    custom = roaming / 'TourBox Console/customConfig'
    add(custom, patch_xml(custom.read_bytes() if custom.exists() else None))
    shortcuts = roaming / 'CELSYSUserData/CELSYS/CLIPStudioPaintVer1_5_0/Shortcut/default.khc'
    add(shortcuts, patch_shortcuts(shortcuts))
    add(target / 'config.json', (json.dumps(config, indent=2) + '\n').encode(), 0o600)
    shell = '\n'.join('compat_' + k + '=' + shlex.quote(config[k]) for k in ('prefix', 'cspenguin', 'wine', 'serial', 'locale', 'proxy'))
    add(target / 'config.sh', (shell + '\n').encode(), 0o600)
    add(target / 'upstream-exports.sh', extract_exports(share / 'csp-launch.sh'), 0o600)
    for name in ('environment.sh', 'runtime_config.py', 'tourbox-stop.py', 'serial-device.py',
                 'csp-display-cache.py', 'csp-navigator-parent.py'):
        add(target / name, (ROOT / 'lib' / name).read_bytes(), 0o755)
    add(target / 'csp-refresh-display.exe', (ROOT / 'payload/csp-refresh-display.exe').read_bytes(), 0o755)
    add(home / '.local/bin/csp-tour', (ROOT / 'bin/csp-tour').read_bytes(), 0o755)
    add(target / 'tourbox-run.sh', (ROOT / 'bin/tourbox-compat-run').read_bytes(), 0o755)
    for name in SERVICES:
        if name == 'tourbox-console.service':
            body = (f'Type=exec\nExecStart="{target}/tourbox-run.sh"\n'
                    f'ExecStop="{target}/tourbox-stop.py"\n'
                    'KillMode=process\nTimeoutStopSec=25\nSuccessExitStatus=143\nRestart=no\n')
        else:
            helper = name.removesuffix('.service') + '.py'
            body = f'Type=simple\nExecStart=/usr/bin/python3 "{target}/{helper}"\nRestart=on-failure\nRestartSec=3\n'
        unit = ('[Unit]\nDescription=CSP TourBox Plasma compatibility: ' + name + '\n'
                'After=graphical-session.target\nPartOf=graphical-session.target\n\n[Service]\n'
                + body + '\n[Install]\nWantedBy=graphical-session.target\n')
        # systemd specifiers must not interpret percent signs in filesystem paths.
        add(home / '.config/systemd/user' / name, unit.replace(str(target), str(target).replace('%', '%%')).encode())
    for filename, title, command, extra in (
        ('clipstudiopaint.desktop', 'Clip Studio Paint', 'paint %F', 'MimeType=application/x-clip;\n'),
        ('clipstudio.desktop', 'Clip Studio', 'studio', ''),
        ('clipstudio-url-handler.desktop', 'Clip Studio URL Handler', 'url %u',
         'NoDisplay=true\nMimeType=x-scheme-handler/clipstudio;x-scheme-handler/clipstudiopaint;\n'),
    ):
        executable = str(home / '.local/bin/csp-tour').replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
        text = ('[Desktop Entry]\nType=Application\nName=' + title + f'\nExec="{executable}" {command}\n'
                'Icon=applications-graphics\nTerminal=false\nCategories=Graphics;\n' + extra)
        add(home / '.local/share/applications' / filename, text.encode())
    desktop = ('[Desktop Entry]\nType=Application\nName=TourBox Console\n'
               'Exec=systemctl --user start tourbox-console.service\nIcon=input-gaming\nTerminal=false\nCategories=Graphics;\n')
    add(home / '.local/share/applications/tourbox-console.desktop', desktop.encode())
    mime = home / '.config/kde-mimeapps.list'
    add(mime, patch_protocol_defaults(mime.read_bytes() if mime.exists() else b''))
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installer', nargs='?', help='Official TourBox Console installer file')
    parser.add_argument('--check', action='store_true', help='Read-only preflight and full patch planning')
    parser.add_argument('--rollback', metavar='BACKUP', help='Restore a receipt, preserving later file changes')
    parser.add_argument('--prefix')
    parser.add_argument('--cspenguin')
    parser.add_argument('--wine')
    parser.add_argument('--wine-user')
    parser.add_argument('--tourbox-installer')
    parser.add_argument('--serial', help='Optional NEO serial device path; otherwise discover it at launch')
    parser.add_argument('--locale', help='Optional Console locale override; otherwise inherit the current language')
    parser.add_argument('--proxy', help='Override the existing WebView2 proxy; otherwise preserve upstream flags')
    args = parser.parse_args()
    require(not (args.installer and args.tourbox_installer), 'Supply the installer once, as a filename or --tourbox-installer')
    args.tourbox_installer = args.tourbox_installer or args.installer
    require(os.getuid() != 0, 'Run as the current desktop user, without sudo')
    require(not any(os.environ.get(k) for k in ('XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME')),
            'This release uses standard ~/.local and ~/.config paths; custom XDG roots are unsupported')
    if args.rollback:
        directory = Path(args.rollback).resolve()
        receipt = json.loads((directory / 'receipt.json').read_text())
        require(not running_apps(Path(receipt['config']['prefix'])), 'Close CSP and Console normally before rollback')
        for name in SERVICES[1:]:
            run(['systemctl', '--user', 'stop', name])
        receipt, conflicts = restore_files(directory)
        run(['systemctl', '--user', 'daemon-reload'])
        if shutil.which('update-desktop-database'):
            run(['update-desktop-database', str(Path.home() / '.local/share/applications')])
        require(not conflicts, 'Later changes preserved; manually resolve these paths:\n' + '\n'.join(conflicts))
        for name, previous in receipt.get('services', {}).items():
            run(['systemctl', '--user', 'enable' if previous['enabled'] else 'disable', name])
            if previous['active']:
                run(['systemctl', '--user', 'start', name])
        print('File rollback complete. See README.md for runtime COM and device-state notes.')
        return
    config = resolve_configuration(args)
    preflight(config, readonly=args.check)
    with tempfile.TemporaryDirectory(prefix='csp-tourbox-') as temporary:
        source, fresh = tourbox_source(args, config, temporary)
        plan = plan_files(config, source, fresh)
        print(json.dumps({'tourbox_fresh_install': fresh, 'planned_files': len(plan)}, indent=2))
        if args.check:
            print('PASS: read-only preflight. Nothing installed, no services or devices changed.')
            return
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        directory = Path.home() / '.local/state/linux-csp-tour/backups' / stamp
        transaction = Transaction(directory)
        transaction.record['config'] = config
        for name in SERVICES:
            transaction.record['services'][name] = {
                'enabled': run(['systemctl', '--user', 'is-enabled', name]).stdout.strip() == 'enabled',
                'active': run(['systemctl', '--user', 'is-active', name]).stdout.strip() == 'active'}
        transaction.save()
        print('Backup and recovery receipt:', directory, flush=True)
        try:
            for path, data, mode in plan:
                transaction.write(path, data, mode)
            run(['systemctl', '--user', 'daemon-reload'], check=True)
            run(['systemctl', '--user', 'enable', *SERVICES], check=True)
            variables = [k for k in ('DISPLAY', 'XAUTHORITY', 'WAYLAND_DISPLAY', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_TYPE') if k in os.environ]
            run(['systemctl', '--user', 'import-environment', *variables], check=True)
            run(['systemctl', '--user', 'restart', *SERVICES[1:]], check=True)
            time.sleep(.5)
            for name in SERVICES[1:]:
                run(['systemctl', '--user', 'is-active', '--quiet', name], check=True)
            transaction.record['state'] = 'complete'
            transaction.save()
        except Exception:
            for name in SERVICES[1:]:
                run(['systemctl', '--user', 'stop', name])
            _, conflicts = restore_files(directory)
            run(['systemctl', '--user', 'daemon-reload'])
            require(not conflicts, 'Automatic file rollback preserved later edits; inspect ' + str(directory))
            for name, previous in transaction.record['services'].items():
                run(['systemctl', '--user', 'enable' if previous['enabled'] else 'disable', name])
                if previous['active']:
                    run(['systemctl', '--user', 'start', name])
            raise
        print('Applied. CSPenguin runtime was reused; no Wine server or application was restarted.')
        if shutil.which('update-desktop-database'):
            run(['update-desktop-database', str(Path.home() / '.local/share/applications')])
        print('Open Clip Studio Paint from the application menu. Reconnect the companion in CSP if needed.')
        print('Rollback:', shlex.join([str(ROOT / 'install.sh'), '--rollback', str(directory)]))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, struct.error, sqlite3.Error,
            ET.ParseError, subprocess.SubprocessError) as problem:
        print('ERROR:', problem, file=sys.stderr)
        sys.exit(1)
