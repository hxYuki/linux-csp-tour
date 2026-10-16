#!/usr/bin/python
"""Refresh the dedicated Wine display cache after Plasma work-area changes."""
import logging
import subprocess
import re
from runtime_config import CONFIG, ROOT, owns_pid, wine_environment

from gi.repository import GLib
from Xlib import X, Xatom, display, error

logging.basicConfig(level=logging.INFO, format='%(message)s')
connection = display.Display()
root = connection.screen().root
work_atom = connection.intern_atom('_NET_WORKAREA')
list_atom = connection.intern_atom('_NET_CLIENT_LIST')
pid_atom = connection.intern_atom('_NET_WM_PID')
pending = None
last_signature = None
force_pending = False


def refresh():
    global pending, last_signature, force_pending
    pending = None
    force = force_pending
    force_pending = False
    try:
        work = root.get_full_property(work_atom, Xatom.CARDINAL)
        clients = root.get_full_property(list_atom, Xatom.WINDOW)
        if work is None or clients is None or len(work.value) < 4:
            return False
        pids = set()
        for window_id in clients.value:
            try:
                window = connection.create_resource_object('window', int(window_id))
                if 'clipstudiopaint.exe' not in tuple(s.lower() for s in (window.get_wm_class() or ())):
                    continue
                pid = window.get_full_property(pid_atom, Xatom.CARDINAL)
                if pid is not None:
                    if owns_pid(int(pid.value[0])):
                        pids.add(int(pid.value[0]))
            except error.BadWindow:
                continue
        if not pids:
            last_signature = None
            return False
        signature = (tuple(int(value) for value in work.value), tuple(sorted(pids)))
        if not force and signature == last_signature:
            return False
        monitors = subprocess.run(['/usr/bin/xrandr', '--listmonitors'], capture_output=True,
                                  text=True, timeout=3, check=True)
        if int(monitors.stdout.splitlines()[0].split()[1]) < 1:
            return False
        version = subprocess.run([CONFIG['wine'], '--version'], capture_output=True, text=True, timeout=3, check=True)
        if not re.match(r'^wine-11\.4(?:\s|$)', version.stdout.strip()):
            logging.warning('Display refresh requires Wine 11.4; skipping changed runtime')
            return False
        result = subprocess.run([
            CONFIG['wine'], str(ROOT / 'csp-refresh-display.exe'),
        ], env=wine_environment(), capture_output=True, text=True, timeout=12, check=True)
        logging.info('%s', result.stdout.strip())
        last_signature = signature
    except (subprocess.SubprocessError, ValueError, IndexError) as problem:
        logging.warning('Display cache refresh skipped or failed: %s', problem)
    return False


def schedule(force=False):
    global pending, force_pending
    force_pending = force_pending or force
    if pending is not None:
        GLib.source_remove(pending)
    pending = GLib.timeout_add(1000, refresh)


def x_events(source, condition):
    if condition & (GLib.IO_HUP | GLib.IO_ERR):
        raise SystemExit('Xwayland connection closed')
    relevant = False
    while connection.pending_events():
        event = connection.next_event()
        if event.type == X.PropertyNotify and event.atom in (work_atom, list_atom):
            relevant = True
    if relevant:
        schedule()
    return True


root.change_attributes(event_mask=X.PropertyChangeMask)
connection.flush()
GLib.io_add_watch(connection.fileno(), GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, x_events)
schedule(force=True)
logging.info('Watching current desktop work-area and CSP window changes')
GLib.MainLoop().run()
