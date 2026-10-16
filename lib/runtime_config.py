"""Shared, non-secret configuration for the installed Plasma add-on."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'config.json').read_text())


def wine_environment():
    env = os.environ.copy()
    env.update(WINEPREFIX=CONFIG['prefix'], WINEDEBUG='-all',
               WINESERVER=str(Path(CONFIG['wine']).with_name('wineserver')),
               WINEDLLPATH=CONFIG['cspenguin'], WINEESYNC='1', WINEFSYNC='1')
    return env


def owns_pid(pid):
    try:
        proc = Path('/proc') / str(pid)
        if proc.stat().st_uid != os.getuid():
            return False
        values = dict(item.split(b'=', 1) for item in (proc / 'environ').read_bytes().split(b'\0') if b'=' in item)
        return Path(os.fsdecode(values[b'WINEPREFIX'])).resolve() == Path(CONFIG['prefix']).resolve()
    except (OSError, KeyError, ValueError):
        return False
