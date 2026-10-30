# Patch scope and verification

## Upstream boundary

CSPenguin remains responsible for CSP installation, Wine, WebView2, DirectComposition, DXVK/VKD3D, fonts, media export and file thumbnails. This add-on reads its existing launcher's export block; it does not run the full launcher during discovery or duplicate those installation steps. Prefix and runner paths are taken from the current user's installation, including a custom prefix written by CSPenguin.

The launcher adapter preserves upstream export flags. Reapply the add-on after changing the upstream launcher if you want to refresh its local environment snapshot.

## Console-specific compatibility

- Serial input is set to raw 115200/8N1 with software/hardware flow control disabled before Console opens the USB NEO. COM33 and the Wine USB discovery registry values are refreshed at launch. Another active serial reader causes a refusal; other driver services are not stopped or managed.
- The USB-only BLE shim avoids unsupported native BLE initialization. Console's `bleSupport`, `ignoreWinMonitor` and `autoBoot` compatibility options are changed without replacing other preferences.
- The JVMTI agent is placed after the original LibH agent. Exact class identity, size/hash and byte guards bound the HKL retry loop and adapt the affected QR window capture. See `source/jvm-agent/README.md`.
- A separate v3 modifier agent follows the HKL/QR agent. It reasserts modifiers in the repeated-wheel path and moves button cache invalidation inside the existing monitor. A delayed picker callback rechecks active/nonresident state before restoring Alt, preventing a late Alt-down after all buttons have been released. The original timers, shortcuts and presets remain in use. Exact class guards leave other builds unchanged; see `source/modifier-agent/README.md`.
- Electron software rendering is enabled before readiness, guarded by the original main-script hash. The rest of the ASAR is retained. Existing F17/F18 bindings are preserved, including an explicitly unassigned action.
- The original serial DLL is retained. SQLite is added within Console rather than replacing a global Wine component.

## Per-installation desktop scope

The current user's existing Plasma Wayland display is used for CSP and Console. Monitor readiness is checked before Wine display initialization. Window helpers subscribe to this Xwayland connection: the display-cache helper follows work-area/client changes, and the Navigator helper maintains the direct relationship with the same process's visible main window.

Each installation belongs to its current user and Plasma session; the prefix is checked for current-user ownership. Separate users may keep a Niri work session and a native Plasma drawing session running concurrently. Account/session creation and VT switching are configured outside this installer. Apply from the drawing user's Plasma terminal, with that user's prefix and user services.

## Session switching and the separate Wine patch

The motivating workflow keeps Niri available for other work while CSP and
TourBox remain open in another user's native Plasma Wayland session. The user
switches VTs between these sessions and expects the canvas, pen input and
Console connection to survive the round trip, followed by normal CSP exit and
reopening. This is broader than switching focus between two application windows.

During VT/display transitions, physical outputs can disappear and reappear in
Xwayland's RandR view. In the observed Wine 11.4 failures, IDs from a screen
resource snapshot became invalid before later queries. Fatal `BadRROutput`
and `BadRRCrtc` errors could terminate Wine explorer and destroy shared X11
resources. CSP and Console also exited with `BadWindow / X_UnmapWindow` on
focus changes. A later incident left CSP windowless but still running, blocking
reopening; its waiting-thread stack did not establish the CRTC error as the
sole cause of the shutdown wait.

Investigation separately reproduced a wineserver serial polling use-after-free:
waking an exiting client could free the request before the callback rearmed
its timeout. This establishes a callback defect, rather than proving that VT
switching caused every serial crash or that all observed failures share one
complete causal chain.

The [Wine fork branch](https://github.com/hxYuki/wine/tree/csp-stability-wine-11.4)
is based on upstream `wine-11.4` (`cc893ef9cb17b994bfd1f1a1f7355be55e615623`):

| Source | Repair |
|---|---|
| `dlls/winex11.drv/xrandr.c` | Trap stale output, CRTC, provider and EDID query errors and use the existing failure paths, retaining RandR and monitor enumeration |
| `server/serial.c` | Rearm the polling timeout before waking the wait queue, so the callback does not access a request freed during wakeup |

The [pinned source and validation notes](https://github.com/hxYuki/wine/blob/0ebfb09bde4045aa2446b20690d88e5dbe65f962/documentation/csp-stability-fixes.md)
include ASan serial reproduction, 1,000 serial wait/cancel/termination cycles,
and isolated Xvfb fault injection for output/CRTC/provider/EDID queries. On
2026-10-28, the local patched runtime passed drawing/pressure, switching to
another VT and back, TourBox/CSP focus changes, and a separate real CSP
close/reopen test. Fresh-login and extended-use acceptance were not covered.

The local deployment used a dedicated copy of Wine 11.4, preserving the
original runtime and existing prefix. This repository references the Wine
source patch separately from its Console JVMTI agents and window helpers;
`install.sh` does not build or deploy the fork. Select a prepared matching
runner with `--wine /path/to/patched-wine/bin/wine`, or configure it in the
upstream launcher's `WINESERVER` export before applying. The runtime helpers
remain bound to Wine 11.4; the patch's modules must be rebuilt and revalidated
for a different Wine version.

## Validation

- Unit tests cover exact-build refusal, idempotent patching, settings/binding preservation, profile discovery, current-user launcher parsing, serial discovery, streamed installation files, and transactional rollback including permissions.
- The supplied official 5.12.0 NSIS installer has been extracted and used in a fresh temporary HOME. The complete file plan was installed, reapplied with zero changes, and rolled back; external service/app actions were stubbed.
- Every packed ASAR entry was checked against its integrity metadata. Only the intended main script changed.
- Private-Xvfb tests run the actual current-desktop helpers, checking Navigator parenting, exclusion of another prefix, work-area refresh and redundant-refresh suppression without logind/session services.
- Launcher simulation checks raw serial flags, COM mapping, filenames containing spaces, prefix/environment forwarding and absence of the lock descriptor in Wine children.
- Modifier callback tests and real private class-bytecode replays reproduce the original wheel/cache faults and delayed Alt-down after picker closure. v3 passes repeated masks, both button release orders, 100 cache interleavings, and closed/resident picker cases while retaining active CSP/Lightroom restoration. On 2026-10-28 the user confirmed repeated long-button + R1 releases no longer left CSP in eyedropper mode; a subsequent one-shot query showed Alt, Ctrl and Shift released. The wheel fix had also passed the user's physical CSP test. These are modifier-specific results; no CSP stability claim is made.

Compatibility payloads also have prior physical USB NEO/CSP exercise. A fresh machine still needs normal device-control, drawing/pressure and companion-pairing checks. Runtime settings/backups and machine audit records are never part of the public distribution.
