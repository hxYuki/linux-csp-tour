# TourBox modifier agent v3

This independent Windows x64 JVMTI agent follows the existing HKL/QR agent:

```text
-agentpath:LibH.dll
-agentpath:win64libs\tourbox-wine-compat.dll
-agentpath:win64libs\tourbox-modifier-fix.dll
```

The main installer installs/upgrades it transactionally for the current user.
Its config normalization removes duplicate modifier agents and preserves other
JVM options. Reapply with CSP and Console closed. The printed rollback command
restores the previous DLL and launch config, or removes them if newly added.

## Repeated wheel modifiers and button release

When the long button releases Alt between wheel pulses, the cached mask can
still be 4. The next wheel pulse can then skip Alt-down and send a bare bracket
instead of Alt + bracket. v1 reasserts the required modifiers in that repeated
mask path. v2 also routes the button exit through the existing cache reset
inside the class monitor, preventing an earlier release from overwriting the
rearm's entry-time invalidation. v3 retains both changes.

Target: `o0o002C239BA7/O0o002C234E69`, 17801 bytes, SHA256
`49934fb99fb768815fd93d255474a1e0bcbb18adc1e651df621bebe3c03d2f24`.
Full length/FNV and instruction guards precede the edits. The wheel edit is
six bytes; the button branch and corresponding stack-map frames are adjusted
without changing class size, timers, lock boundaries or ordinary key output.

## Delayed Alt restoration after repeated R1

The v2 cache repair alone did not resolve the physical R1 symptom. Targeted
runtime tracing showed Alt-up on release, then an SWT timer issuing a new
Alt-down after all buttons had been released. The foreground window stayed
the same. The delayed callback checked whether the picker was active when
scheduled, but did not check again when it executed.

v3 replaces that callback's method handle with `wineRestorePickerAlt` in the
same class. It calls the original restore only while the CSP or Lightroom
picker is still active and nonresident. It preserves the original timer and
deadline coalescing, and suppresses restoration after closure or a switch to
resident mode.

Target: `o0o002C239BAC/O0o002C23488D`, 6778 bytes, SHA256
`e576c475651521cca58550c93cd5bc84da0a70a3adbae57eba9df045f76caa05`.
The agent checks full length/FNV before applying the sparse delta. Unknown
classes remain unchanged with a refusal message. The generator and delta
contain no complete vendor class. No persistent input recorder or keyboard
hook is installed. The DLL imports only Kernel32 GetStdHandle/WriteFile.

Payload SHA256:
`18157e03ef697272fc10b838464750b4529797593bbf18a2d119d8fb3dbf269b`.

## Build and regression

From the repository root, build without vendor files:

```bash
bash source/modifier-agent/build.sh
```

Requirements: a JDK, clang, llvm-dlltool and lld-link. JAVA_HOME is honored;
otherwise the JDK is derived from javac. Outputs go to the ignored `build/`.
The installer uses the separately checksummed payload, not build outputs.

With your own matching private class fixtures, run:

```bash
bash source/modifier-agent/verify.sh /path/to/private/classes-current
```

The script runs `regression.py`, compiles `MakePickerPatch.java` using the
JDK's internal ASM, regenerates `picker_patch.h` and checks it byte for byte,
then runs the production C picker callback and `picker-regression.py` with
`-Xverify:all`. Vendor originals and generated classes stay outside the repo.

The original wheel replay gives 56 incorrect modifier states in 57 key-downs;
the patch gives zero. Coverage includes masks, transitions, holds, timer
release, 100 deterministic cache interleavings, and repeated R1 counts with
both release orders. The original picker replay sends two ghost Alt-downs
after closure; v3 sends none. Counts 1, 2, 3, 10, 32 and 100 pass, while active
CSP/Lightroom restoration is retained. Platform/native output dependencies
are stubbed; these tests do not replace physical acceptance.

The wheel fix passed a physical USB NEO/CSP test. On 2026-10-28 the user also
confirmed repeated long-button + R1 releases no longer left CSP in eyedropper
mode; a subsequent one-shot query found Alt/left Alt/right Alt/Ctrl/Shift all
released. CSP stayed in the same process during the v3 upgrade and test, and
temporary diagnostic components were removed. This is not a CSP crash fix.
