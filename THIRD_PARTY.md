# Third-party components

| Component | Source and terms |
|---|---|
| CSPenguin | [CSPenguin-Installer](https://github.com/parka6060/CSPenguin-Installer), installed separately. Its Wine/runtime components are reused locally. |
| TourBox Console | Supplied separately by the user from [TourBox](https://www.tourboxtech.com/en/downloads/). No installer, vendor executable, JAR, class fixture or complete patched ASAR is distributed here. |
| SQLite | `payload/winsqlite3.dll` is the official Windows x64 SQLite 3.54.0 DLL renamed for Console's loader. SQLite is [public domain](https://www.sqlite.org/copyright.html). Source package URL and verified SHA3-256 are in `docs/sqlite-source.txt`. |
| Wine | Installed by CSPenguin. The cache helper targets the [Wine 11.4 interface](https://gitlab.winehq.org/wine/wine/-/tree/wine-11.4) and does not bundle Wine. |
| JNI/JVMTI | Build-time interfaces supplied by the user's JDK; local ABI declarations are in `source/jvm-agent/include/`. |

The installer, launchers, window helpers and compatibility shim sources are covered by the repository's MIT license. `payload/SHA256.json` records the exact shipped compatibility binaries.

The SQLite DLL is kept byte-for-byte identical to the upstream release, including its public CodeView build metadata. Distribution checks allow that exact checksummed vendor artifact while continuing to scan the project's own code and binaries for private workstation paths and credential patterns.
