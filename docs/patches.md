# Patch scope and verification

## Upstream boundary

CSPenguin remains responsible for CSP installation, Wine, WebView2, DirectComposition, DXVK/VKD3D, fonts, media export and file thumbnails. This add-on reads its existing launcher's export block; it does not run the full launcher during discovery or duplicate those installation steps. Prefix and runner paths are taken from the current user's installation, including a custom prefix written by CSPenguin.

The launcher adapter preserves upstream export flags. Reapply the add-on after changing the upstream launcher if you want to refresh its local environment snapshot.

## Console-specific compatibility

- Serial input is set to raw 115200/8N1 with software/hardware flow control disabled before Console opens the USB NEO. COM33 and the Wine USB discovery registry values are refreshed at launch. Another active serial reader causes a refusal; other driver services are not stopped or managed.
- The USB-only BLE shim avoids unsupported native BLE initialization. Console's `bleSupport`, `ignoreWinMonitor` and `autoBoot` compatibility options are changed without replacing other preferences.
- The JVMTI agent is placed after the original LibH agent. Exact class identity, size/hash and byte guards bound the HKL retry loop and adapt the affected QR window capture. See `source/jvm-agent/README.md`.
- Electron software rendering is enabled before readiness, guarded by the original main-script hash. The rest of the ASAR is retained. Existing F17/F18 bindings are preserved, including an explicitly unassigned action.
- The original serial DLL is retained. SQLite is added within Console rather than replacing a global Wine component.

## Single desktop

The current user's existing Plasma Wayland display is used for CSP and Console. Monitor readiness is checked before Wine display initialization. Window helpers subscribe to this Xwayland connection: the display-cache helper follows work-area/client changes, and the Navigator helper maintains the direct relationship with the same process's visible main window.

There is no login-manager configuration, session enumeration, other-account fallback, VT switching, private compositor or tablet hardware policy in this project. The prefix is checked for current-user ownership. One desktop session is the operating assumption.

## Validation

- Unit tests cover exact-build refusal, idempotent patching, settings/binding preservation, profile discovery, current-user launcher parsing, serial discovery, streamed installation files, and transactional rollback including permissions.
- The supplied official 5.12.0 NSIS installer has been extracted and used in a fresh temporary HOME. The complete file plan was installed, reapplied with zero changes, and rolled back; external service/app actions were stubbed.
- Every packed ASAR entry was checked against its integrity metadata. Only the intended main script changed.
- Private-Xvfb tests run the actual current-desktop helpers, checking Navigator parenting, exclusion of another prefix, work-area refresh and redundant-refresh suppression without logind/session services.
- Launcher simulation checks raw serial flags, COM mapping, filenames containing spaces, prefix/environment forwarding and absence of the lock descriptor in Wine children.

Compatibility payloads also have prior physical USB NEO/CSP exercise. A fresh machine still needs normal device-control, drawing/pressure and companion-pairing checks. Runtime settings/backups and machine audit records are never part of the public distribution.
