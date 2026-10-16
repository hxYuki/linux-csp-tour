"""Exercise the actual single-desktop helpers on a private Xvfb server."""
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import time

from Xlib import X, Xatom, display

ROOT = Path(__file__).resolve().parents[1]


def until(predicate, description):
    deadline = time.monotonic() + 7
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.1)
    raise AssertionError(description)


processes = []
connection = None
try:
    with tempfile.TemporaryDirectory(prefix='csp-tour-x11-') as temporary:
        base = Path(temporary)
        prefix = base / 'prefix'; prefix.mkdir()
        read_fd, write_fd = os.pipe()
        server = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x1024x24', '-nolisten', 'tcp'],
                                  pass_fds=(write_fd,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(server); os.close(write_fd)
        assert select.select([read_fd], [], [], 5)[0], 'Xvfb did not become ready'
        display_name = ':' + os.read(read_fd, 64).decode().strip(); os.close(read_fd)
        env = {**os.environ, 'DISPLAY': display_name, 'WINEPREFIX': str(prefix)}
        owner = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], env=env)
        other = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], env={**env, 'WINEPREFIX': str(base / 'other-prefix')})
        processes.extend([owner, other])
        connection = display.Display(display_name); root = connection.screen().root
        atom = connection.intern_atom
        def window(caption, pid, width=700):
            result = root.create_window(0, 0, width, 400, 0, X.CopyFromParent, X.InputOutput, X.CopyFromParent)
            result.set_wm_class('clipstudiopaint.exe', 'clipstudiopaint.exe')
            result.set_wm_name(caption)
            result.change_property(atom('_NET_WM_PID'), Xatom.CARDINAL, 32, [pid])
            result.change_property(atom('_NET_WM_WINDOW_TYPE'), Xatom.ATOM, 32, [atom('_NET_WM_WINDOW_TYPE_NORMAL')])
            result.map()
            return result
        main = window('CLIP STUDIO PAINT', owner.pid)
        navigator = window('Navigator', owner.pid, 260)
        foreign = window('Navigator', other.pid, 260)
        root.change_property(atom('_NET_CLIENT_LIST'), Xatom.WINDOW, 32, [main.id, navigator.id, foreign.id])
        root.change_property(atom('_NET_WORKAREA'), Xatom.CARDINAL, 32, [0, 0, 1280, 1000])
        connection.sync()
        for name in ['runtime_config.py', 'csp-display-cache.py', 'csp-navigator-parent.py']:
            shutil.copy2(ROOT / 'lib' / name, base / name)
        wine = base / 'wine'
        marker = base / 'refreshes'
        wine.write_text('''#!/usr/bin/python3
import os,sys
from pathlib import Path
if sys.argv[1:] == ['--version']:
 print('wine-11.4')
else:
 with Path(__file__).with_name('refreshes').open('a') as stream:stream.write(os.environ['WINEPREFIX']+'\\n')
 print('Wine display cache refreshed')
'''); wine.chmod(0o755)
        (base / 'config.json').write_text(json.dumps({'prefix': str(prefix), 'wine': str(wine), 'cspenguin': str(base)}))
        with (base / 'helpers.log').open('w') as log:
            for name in ['csp-display-cache.py', 'csp-navigator-parent.py']:
                processes.append(subprocess.Popen([sys.executable, str(base / name)], env=env, stdout=log, stderr=log))
            def parent_is_correct():
                connection.sync()
                value = navigator.get_full_property(atom('WM_TRANSIENT_FOR'), Xatom.WINDOW)
                return value is not None and list(value.value) == [main.id]
            until(parent_is_correct, 'Navigator was not attached directly to its main window')
            until(lambda: marker.exists() and len(marker.read_text().splitlines()) == 1, 'Initial work-area cache was not refreshed')
            assert foreign.get_full_property(atom('WM_TRANSIENT_FOR'), X.AnyPropertyType) is None
            root.change_property(atom('_NET_WORKAREA'), Xatom.CARDINAL, 32, [0, 0, 1280, 990]); connection.sync()
            until(lambda: len(marker.read_text().splitlines()) == 2, 'Changed work area was not refreshed')
            root.change_property(atom('_NET_WORKAREA'), Xatom.CARDINAL, 32, [0, 0, 1280, 990]); connection.sync()
            time.sleep(1.5)
            assert len(marker.read_text().splitlines()) == 2, 'Unchanged work area caused redundant Wine refresh'
            assert set(marker.read_text().splitlines()) == {str(prefix)}
            assert all(process.poll() is None for process in processes), (base / 'helpers.log').read_text()
        print('PASS private X11: Navigator ownership, foreign-prefix exclusion, work-area refresh and deduplication')
finally:
    if connection is not None:
        connection.close()
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
