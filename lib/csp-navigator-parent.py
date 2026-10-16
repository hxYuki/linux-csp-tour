#!/usr/bin/python
"""Keep CSP's Navigator transient directly for its own visible main window."""
import logging
from runtime_config import owns_pid

from gi.repository import GLib
from Xlib import X, Xatom, display, error


logging.basicConfig(level=logging.INFO, format='%(message)s')
connection = display.Display()
root = connection.screen().root
atoms = {name: connection.intern_atom(name) for name in (
    '_NET_CLIENT_LIST', '_NET_WM_NAME', '_NET_WM_PID', '_NET_WM_WINDOW_TYPE',
    '_NET_WM_WINDOW_TYPE_NORMAL', 'WM_TRANSIENT_FOR', 'WM_NAME', 'WM_CLASS',
)}
watched = set()
navigator_titles = {'导航器', '導航器', 'Navigator', 'ナビゲーター'}


def handle_x_error(problem, request):
    # Windows can disappear between reading the client list and updating a hint.
    if not isinstance(problem, error.BadWindow):
        logging.warning('X11 request failed: %s', problem)


connection.set_error_handler(handle_x_error)


def property_value(window, name):
    prop = window.get_full_property(atoms[name], X.AnyPropertyType)
    return prop.value if prop is not None else None


def title(window):
    value = property_value(window, '_NET_WM_NAME')
    if value is not None:
        return bytes(value).decode('utf-8', errors='replace')
    return window.get_wm_name() or ''


def repair():
    try:
        ids = property_value(root, '_NET_CLIENT_LIST')
        if ids is None:
            return True
        current_ids = {int(value) for value in ids}
        watched.intersection_update(current_ids)
        mains, navigators = [], []
        for window_id in current_ids:
            try:
                window = connection.create_resource_object('window', window_id)
                wmclass = window.get_wm_class() or ()
                if not any(str(value).lower() == 'clipstudiopaint.exe' for value in wmclass):
                    continue
                if window_id not in watched:
                    window.change_attributes(event_mask=X.PropertyChangeMask)
                    watched.add(window_id)
                if window.get_attributes().map_state != X.IsViewable:
                    continue
                pid_value = property_value(window, '_NET_WM_PID')
                if pid_value is None or len(pid_value) != 1:
                    continue
                pid = int(pid_value[0])
                if not owns_pid(pid):
                    continue
                caption = title(window)
                types = property_value(window, '_NET_WM_WINDOW_TYPE')
                geometry = window.get_geometry()
                if caption in navigator_titles:
                    navigators.append((window, pid))
                elif (types is not None and atoms['_NET_WM_WINDOW_TYPE_NORMAL'] in types
                      and geometry.width > 300 and geometry.height > 200):
                    mains.append((window, pid))
            except error.BadWindow:
                continue
        for navigator, pid in navigators:
            candidates = [window for window, main_pid in mains if main_pid == pid]
            if len(candidates) != 1:
                continue
            main = candidates[0]
            old = navigator.get_full_property(atoms['WM_TRANSIENT_FOR'], X.AnyPropertyType)
            correct = (old is not None and old.property_type == Xatom.WINDOW
                       and old.format == 32 and list(old.value) == [main.id])
            if not correct:
                navigator.change_property(atoms['WM_TRANSIENT_FOR'], Xatom.WINDOW, 32, [main.id])
                connection.sync()
                logging.info('Navigator 0x%x -> CSP main 0x%x (pid %s)', navigator.id, main.id, pid)
        connection.flush()
    except error.BadWindow:
        pass
    return True


def x_events(source, condition):
    if condition & (GLib.IO_HUP | GLib.IO_ERR):
        raise SystemExit('Xwayland connection closed')
    relevant = False
    while connection.pending_events():
        event = connection.next_event()
        if event.type == X.PropertyNotify and event.atom in atoms.values():
            relevant = True
    if relevant:
        repair()
    return True


root.change_attributes(event_mask=X.PropertyChangeMask)
GLib.io_add_watch(connection.fileno(), GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, x_events)
GLib.timeout_add_seconds(3, repair)
repair()
logging.info('Watching CSP Navigator ownership on the current desktop')
GLib.MainLoop().run()
