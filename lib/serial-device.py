#!/usr/bin/env python3
"""Find one connected USB TourBox NEO without storing a device serial number."""
from pathlib import Path
import sys


def select_serial(requested='', directory=Path('/dev/serial/by-id')):
    if requested:
        device = Path(requested).expanduser()
        if not device.exists():
            raise RuntimeError('Configured serial device is not connected')
        return str(device)
    devices = {}
    for path in sorted(directory.glob('*')):
        name = path.name.casefold()
        if 'tourbox' in name and 'neo' in name and path.exists():
            devices.setdefault(path.resolve(), path)
    if len(devices) != 1:
        raise RuntimeError('Connect one USB TourBox NEO, or reinstall with --serial /dev/serial/by-id/DEVICE')
    return str(next(iter(devices.values())))


if __name__ == '__main__':
    from runtime_config import CONFIG
    try:
        print(select_serial(CONFIG.get('serial', '')))
    except (RuntimeError, OSError) as problem:
        sys.exit(str(problem))
