# Rebuild compatibility payloads

From the repository root:

```bash
bash source/jvm-agent/build.sh
bash source/modifier-agent/build.sh
bash source/ble-stub/build.sh
bash source/display-cache/build.sh
```

Requirements: clang, lld-link and llvm-dlltool. The agent also needs a JDK;
JAVA_HOME is used when set, otherwise it is derived from javac. Generated
outputs are kept in each source directory's ignored `build/` folder.

The installer uses the separately checksummed binaries in `payload/`. New
builds are not substituted automatically. Validate replacements before updating
the payload and SHA256 manifest. The display-cache executable uses a private
Wine 11.4 interface and must be rechecked for other Wine versions.

The vendor's installer, JAR and class fixtures are not needed to build these
sources and must not be committed. Agent callback tests requiring private
fixtures are described in `jvm-agent/README.md` and `modifier-agent/README.md`.
