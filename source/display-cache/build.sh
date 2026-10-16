#!/usr/bin/env bash
set -euo pipefail
src=$(dirname "$(readlink -f "$0")")
destination="${1:-$src/build}"
mkdir -p "$destination"
destination=$(readlink -f "$destination")
cd "$destination"
printf 'LIBRARY win32u.dll\nEXPORTS\nNtUserCallNoParam\n' >win32u.def
printf 'LIBRARY user32.dll\nEXPORTS\nSetProcessDPIAware\nMonitorFromPoint\nGetMonitorInfoA\n' >user32.def
printf 'LIBRARY kernel32.dll\nEXPORTS\nGetStdHandle\nWriteFile\nExitProcess\n' >kernel32.def
for library in win32u user32 kernel32; do
    llvm-dlltool -m i386:x86-64 -d "$library.def" -l "$library.lib"
done
clang -target x86_64-pc-windows-msvc -O2 -ffreestanding -fno-stack-protector \
    -c "$src/csp-refresh-display.c" -o display.obj
lld-link /nodefaultlib /machine:x64 /subsystem:console /entry:mainCRTStartup /timestamp:0 \
    /out:csp-refresh-display.exe display.obj win32u.lib user32.lib kernel32.lib
