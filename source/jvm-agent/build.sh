#!/usr/bin/env bash
set -euo pipefail
src=$(dirname "$(readlink -f "$0")")
jdk="${JAVA_HOME:-$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")}"
destination="${1:-$src/build}"
mkdir -p "$destination"
destination=$(readlink -f "$destination")
cd "$destination"
clang -target x86_64-pc-windows-msvc -std=c11 -O2 -ffreestanding \
  -fno-stack-protector -mno-stack-arg-probe -Wall -Wextra -Werror \
  -I"$src/include" -I"$jdk/include" -c "$src/compat.c" -o compat.obj
llvm-dlltool -m i386:x86-64 -d "$src/kernel32.def" -l kernel32.lib
lld-link /dll /noentry /nodefaultlib /machine:x64 /timestamp:0 /out:tourbox-wine-compat.dll \
  /implib:tourbox-wine-compat.lib /export:Agent_OnLoad compat.obj kernel32.lib
llvm-readobj --coff-imports --coff-exports tourbox-wine-compat.dll
