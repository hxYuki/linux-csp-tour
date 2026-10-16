# linux-csp-tour

Install the official **TourBox Console** into the current user's [CSPenguin](https://github.com/parka6060/CSPenguin-Installer) environment, with Wine compatibility fixes for USB TourBox NEO and Clip Studio Paint.

[中文说明](README.zh-CN.md)

## Install

Use your normal desktop account in **one Plasma Wayland session**. Install CSP with CSPenguin first, and obtain the official TourBox Console **5.12.0** Windows installer.

Save your work and close CSP and Console, then run:

```bash
git clone https://github.com/hxYuki/linux-csp-tour.git
cd linux-csp-tour
./install.sh "$HOME/Downloads/TourBoxConsoleSetup_5.12.0.exe"
```

The script reads the current user's `~/.local/share/cspenguin/csp-launch.sh` to locate its existing Wine prefix and runner. It extracts the supplied installer, applies the compatibility patches, and adds application menu entries and user services. Open **Clip Studio Paint** from the menu afterward; it starts Console alongside CSP.

The supported combination is **CSPenguin Wine 11.4 + the supported TourBox 5.12.0 build + USB NEO + Plasma Wayland**. Exact application hashes are checked before modifying anything. Bluetooth and other Console builds are not covered.

The script uses the current user's environment throughout. It does not create accounts, switch users, manage virtual terminals, start another compositor, or install device-specific tablet rules. Existing CSPenguin Wine, WebView2, DXVK, media patches, fonts and thumbnails are reused.

### Dependencies

Python 3.11+, Python Xlib and PyGObject, 7zip, systemd user services, XRandR, `stty`, `flock`, and `fuser`. On Arch-based systems the relevant packages include:

```text
python python-xlib python-gobject 7zip xorg-xrandr util-linux psmisc
```

Dependencies are checked, not installed. Run without sudo. The USB NEO must be readable and writable by your desktop user when Console starts. Its stable serial device is detected automatically; stop any other driver using it before launching Console.

### Options

```bash
# Read-only checks and patch planning; applications can remain open.
./install.sh --check /path/to/TourBoxConsoleSetup_5.12.0.exe

# Reapply to an already installed, supported Console.
./install.sh

# Optional overrides for a custom current-user installation.
./install.sh /path/to/installer.exe --prefix /path/to/prefix \
  --cspenguin /path/to/cspenguin --serial /dev/serial/by-id/DEVICE
```

The Console locale defaults to the current language. If a device's regional check requires a different locale, use `--locale` with an installed locale, such as `zh_CN.UTF-8`. `--proxy` optionally overrides WebView2's proxy; otherwise existing CSPenguin browser arguments are preserved. Standard `~/.local` and `~/.config` paths are used, matching upstream CSPenguin.

## Included fixes

| Area | Change |
|---|---|
| USB NEO | Raw 115200/8N1 serial setup, COM33 mapping, Wine USB enumeration values |
| BLE initialization | USB-only compatibility shim and Console configuration |
| Keyboard layout | Guarded JVMTI patch bounds the HKL activation retry loop |
| CSP companion QR | Guarded replacement of the affected PrintWindow call with BitBlt |
| Picker rendering | Software rendering enabled before Electron readiness; other ASAR files preserved |
| SQLite | Official SQLite x64 DLL provided inside Console |
| CSP integration | Add missing official F17/F18 commands without replacing existing bindings |
| Maximize behavior | Refresh Wine 11.4's work-area cache when the desktop work area or CSP windows change |
| Navigator | Maintain its transient relationship directly with the same CSP process's main window |
| Launch/exit | Current display, monitor readiness, a single-instance lock without inherited Wine lock descriptors, scoped Console exit |

The window helpers watch the current X11/Xwayland connection. They do not enumerate other users' sessions or depend on account switching. Companion login and pairing continue through the official UI; existing pairing data is preserved.

## Backup and rollback

Each apply records original file contents and modes under:

```text
~/.local/state/linux-csp-tour/backups/TIMESTAMP/
```

The installer prints its exact rollback command. Close CSP and Console before running it:

```bash
./install.sh --rollback "$HOME/.local/state/linux-csp-tour/backups/TIMESTAMP"
```

Later file edits are preserved as conflicts. Rollback covers managed files and user-service enablement. Runtime COM33 registry values, serial settings, and later application state are not rewound. The generated files and backups stay local; they are not uploaded.

Logs:

```bash
journalctl --user -u csp-display-cache.service -u csp-navigator-parent.service
tail -f "$HOME/.local/state/linux-csp-tour/console.log"
```

## Verification and source

```bash
bash verify.sh
```

Optional integration tests use a private Xvfb server or your own official installer:

```bash
/usr/bin/python3 tests/verify_x11.py
/usr/bin/python3 tests/verify_installer.py /path/to/TourBoxConsoleSetup_5.12.0.exe
```

The fresh-install test extracts the actual NSIS package, installs into a temporary HOME, reapplies without changes, and rolls back. Wine applications and user-service actions are stubbed. Xvfb tests run the actual window helpers and verify ownership, work-area updates, and refresh deduplication. The compatibility payloads have been exercised with CSP and a USB NEO; a successful isolated test does not replace physical control, pen-pressure, or companion-pairing checks on a new setup.

See [patch details](docs/patches.md), [third-party components](THIRD_PARTY.md), and [rebuild instructions](source/README.md). The official TourBox installer, vendor JAR/classes, user settings, credentials, device serial numbers, and machine audit reports are not included in this repository.
