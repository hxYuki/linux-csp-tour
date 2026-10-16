#!/usr/bin/env bash
set -euo pipefail
src=$(dirname "$(readlink -f "$0")")
destination="${1:-$src/build}"
mkdir -p "$destination"
clang -target x86_64-pc-windows-msvc -O2 -ffreestanding -fno-stack-protector \
    -c "$src/ble-usb-only.c" -o "$destination/ble.obj"
lld-link /dll /noentry /nodefaultlib /machine:x64 /timestamp:0 \
    "/out:$destination/libBLEWrapper.dll" "$destination/ble.obj"
