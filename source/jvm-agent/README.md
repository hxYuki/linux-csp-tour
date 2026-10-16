# TourBox Wine JVMTI agent

This Windows x64 agent is loaded immediately after the original `-agentpath:LibH.dll`:

```text
-agentpath:win64libs\tourbox-wine-compat.dll
```

The original encrypted vendor JAR remains unchanged. No class dumping, authentication bypass, or device access is added.

## HKL retry fix

The target class is `o0o002C239B88/O0o002C235C7A$1`, length 6312, SHA256
`1578f764f13c509069b4d43b0100513bff6ab97b596862941af473c8d3fd0e45`.
A bounded constant-pool/method parser locates `run()V`. Whole-class guards and
critical opcodes are checked before modifying the retry branch. One layout
activation attempt is retained per observed change, followed by the original
callback, foreground-application handling, input-method handling and sleep.
Unknown class bytes are left unchanged with a refusal message.

## CSP QR capture fix

The second target is `o0o002C239B89/O0o002C231F41`, length 12816, SHA256
`e5c77d3756e0e87cb40ab41cea251b638b329e45b963ed9b9818112b4cd3ae44`.
Only the affected PrintWindow call is replaced with BitBlt from the same window
DC. The original bitmap cleanup, QR decoding and companion authentication
remain in place. `capture_patch.h` contains guarded offsets, constants and the
replacement call bytes rather than a complete vendor class.

## Build and test

Run `bash source/jvm-agent/build.sh` from the repository root. The script uses
JAVA_HOME, or derives the JDK location from javac. Windows JNI ABI shims are
in `include/`; generated outputs go to `build/`.

`test.c` and `test_capture.c` exercise the production callback against private
vendor fixtures. `VerifyPatched.java` and `VerifyCapture.java` provide optional
JVM verification. Such fixtures are intentionally not distributed. The helper
`make_capture_patch.py` accepts a private capture class filename to reproduce
the patch metadata locally; generated classes must remain outside the repository.
