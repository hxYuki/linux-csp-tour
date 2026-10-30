"""Exercise a supplied official installer in an isolated HOME; never start real apps.

Usage: python3 tests/verify_installer.py /path/to/TourBoxConsoleSetup_5.12.0.exe
"""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(addon)
installer = Path(sys.argv[1]).resolve()

with tempfile.TemporaryDirectory(prefix='csp-tour-test-') as temporary:
    base = Path(temporary)
    home = base / 'artist home'; home.mkdir()
    prefix = home / 'custom CSP prefix'
    (prefix / 'drive_c/users/artist/AppData/Roaming').mkdir(parents=True)
    paint = prefix / 'drive_c/Program Files/CELSYS/CLIP STUDIO 1.5/CLIP STUDIO PAINT/CLIPStudioPaint.exe'
    paint.parent.mkdir(parents=True); paint.touch()
    share = home / '.local/share/cspenguin'; share.mkdir(parents=True)
    wine = share / 'wine-11.4/bin/wine'; wine.parent.mkdir(parents=True)
    wine.write_text('#!/bin/sh\nprintf "wine-11.4\\n"\n'); wine.chmod(0o755)
    (share / 'csp-launch.sh').write_text(
        f'export PATH="{wine.parent}:$PATH"\nexport WINESERVER="{wine.with_name("wineserver")}"\n'
        f'export WINEPREFIX="{prefix}"\nexport UPSTREAM_FLAG=preserved\nwine ignored.exe\n')
    env = {**os.environ, 'HOME': str(home), 'USER': 'artist', 'LANG': 'C.UTF-8'}
    for key in ('XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'LC_ALL'):
        env.pop(key, None)
    config_args = argparse.Namespace(prefix=None, cspenguin=None, wine=None, wine_user=None,
                                     serial=None, locale=None, proxy=None)
    with mock.patch.object(Path, 'home', return_value=home), mock.patch.dict(os.environ, env, clear=True):
        config = addon.resolve_configuration(config_args)
        assert config['prefix'] == str(prefix) and config['wine_user'] == 'artist'
        assert config['serial'] == '' and config['locale'] == 'C.UTF-8'
        extract_dir = base / 'extracted'; extract_dir.mkdir()
        source, fresh = addon.tourbox_source(argparse.Namespace(tourbox_installer=str(installer)), config, str(extract_dir))
        assert fresh
        print('PASS official NSIS extraction and supported-build checks', flush=True)
        states = set()
        commands = []
        def fake_run(argv, **kwargs):
            if argv[0] == str(wine):
                return subprocess.run(argv, text=True, capture_output=True, **kwargs)
            commands.append(argv)
            code = 0; stdout = ''
            if 'is-enabled' in argv:
                code = 1; stdout = 'disabled\n'
            elif 'is-active' in argv:
                code = 0 if argv[-1] in states else 3
                stdout = 'active\n' if code == 0 else 'inactive\n'
            elif 'restart' in argv:
                states.update(argv[argv.index('restart') + 1:])
            return subprocess.CompletedProcess(argv, code, stdout, '')
        def staged_source(*_):
            installed = prefix / 'drive_c/Program Files/TourBox Console'
            return (installed, False) if installed.exists() else (source, True)
        arguments = [str(ROOT / 'install.py'), str(installer)]
        with mock.patch.object(addon, 'preflight'), mock.patch.object(addon, 'run', side_effect=fake_run), \
                mock.patch.object(addon, 'tourbox_source', side_effect=staged_source), \
                mock.patch.object(sys, 'argv', arguments), redirect_stdout(io.StringIO()):
            addon.main()
            with mock.patch.object(sys, 'argv', [str(ROOT / 'install.py'), '--tourbox-installer', str(installer)]):
                addon.main()
        backups = sorted((home / '.local/state/linux-csp-tour/backups').iterdir())
        assert len(backups) == 2
        first = json.loads((backups[0] / 'receipt.json').read_text())
        second = json.loads((backups[1] / 'receipt.json').read_text())
        assert first['state'] == second['state'] == 'complete'
        assert len(first['files']) > 50 and not second['files']
        assert all('start' not in command for command in commands), 'Installer started a real application service'
        assert addon.digest(prefix / 'drive_c/Program Files/TourBox Console/LibTW.dec') == addon.JAR_HASH
        app = prefix / 'drive_c/Program Files/TourBox Console'
        assert addon.digest(app / 'win64libs/tourbox-modifier-fix.dll') == addon.digest(ROOT / 'payload/tourbox-modifier-fix.dll')
        args = json.loads((app / 'TourBox Console.json').read_bytes())['vmArgs']
        compat = args.index(r'-agentpath:win64libs\tourbox-wine-compat.dll')
        assert args[compat + 1] == r'-agentpath:win64libs\tourbox-modifier-fix.dll'
        assert args.count(r'-agentpath:win64libs\tourbox-modifier-fix.dll') == 1
        assert not addon.restore_files(backups[0])[1]
        assert not (prefix / 'drive_c/Program Files/TourBox Console/TourBox Console.exe').exists()
        assert not (app / 'win64libs/tourbox-modifier-fix.dll').exists()
        assert paint.exists()
        print('PASS fresh install, custom CSPenguin prefix discovery, unchanged reapply and rollback;',
              len(first['files']), 'files installed in temporary HOME', flush=True)
