#!/usr/bin/env python3
"""Stop only the sole Console belonging to this prefix and launch token."""
import os
from pathlib import Path
import subprocess
import sys
import time
from runtime_config import CONFIG, wine_environment

tokenfile = Path(os.environ['XDG_RUNTIME_DIR']) / 'tourbox-console.token'
expected = r'C:\Program Files\TourBox Console\TourBox Console.exe'.casefold()


def consoles():
    result = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            env = dict(x.split(b'=', 1) for x in (proc / 'environ').read_bytes().split(b'\0') if b'=' in x)
            command = (proc / 'cmdline').read_bytes().split(b'\0')[0].decode(errors='replace').casefold()
            if (Path(os.fsdecode(env.get(b'WINEPREFIX', b'/nonexistent'))).resolve() == Path(CONFIG['prefix']).resolve()
                    and command == expected):
                result.append((int(proc.name), env.get(b'TOURBOX_SESSION_TOKEN')))
        except (OSError, ValueError):
            pass
    return result


if '--check' in sys.argv:
    if consoles():
        sys.exit('Console is already running; refusing a duplicate')
    sys.exit(0)
if not tokenfile.exists():
    sys.exit(0)
token = tokenfile.read_bytes().strip()
owned = consoles()
if owned:
    if len(owned) != 1 or owned[0][1] != token:
        sys.exit('Refusing to stop a Console not owned by this launcher')
    # Win32 termination was verified with this Console; Unix SIGTERM destabilized Wine.
    subprocess.run([CONFIG['wine'], 'taskkill', '/im', 'TourBox Console.exe', '/f'],
                   env=wine_environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=10, check=True)
deadline = time.monotonic() + 8
while time.monotonic() < deadline:
    if not any(owner == token for _, owner in consoles()):
        tokenfile.unlink(missing_ok=True)
        sys.exit(0)
    time.sleep(.1)
sys.exit('Owned Console has not exited; shared wineserver was left running')
