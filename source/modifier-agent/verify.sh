#!/usr/bin/env bash
set -euo pipefail
src=$(dirname "$(readlink -f "$0")")
fixtures=$(readlink -f "${1:?Usage: verify.sh /path/to/private/classes-current}")
jdk="${JAVA_HOME:-$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")}"
scratch=$(mktemp -d -t tourbox-modifier-verify-XXXXXXXX)
trap 'rm -rf -- "$scratch"' EXIT
python3 "$src/regression.py" "$fixtures"
export_arg=java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED
"$jdk/bin/javac" --add-exports "$export_arg" -d "$scratch" "$src/MakePickerPatch.java"
"$jdk/bin/java" --add-exports "$export_arg" -cp "$scratch" MakePickerPatch \
  "$fixtures/o0o002C239BAC/O0o002C23488D.class" "$scratch/generated.class"
python3 "$src/make_picker_delta.py" \
  "$fixtures/o0o002C239BAC/O0o002C23488D.class" "$scratch/generated.class" "$scratch/picker_patch.h"
cmp "$src/picker_patch.h" "$scratch/picker_patch.h"
clang -std=c11 -fdeclspec -Wno-ignored-attributes \
  -I"$jdk/include" -I"$jdk/include/linux" "$src/test_picker.c" -o "$scratch/test-picker"
"$scratch/test-picker" "$fixtures/o0o002C239BAC/O0o002C23488D.class" "$scratch/production.class"
cmp "$scratch/generated.class" "$scratch/production.class"
python3 "$src/picker-regression.py" "$fixtures" "$scratch/production.class"
echo 'PASS modifier/picker callbacks, generated delta parity and bytecode regression'
