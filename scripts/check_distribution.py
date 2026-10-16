#!/usr/bin/env python3
"""Check the tracked distribution for private artifacts and credential patterns."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
result = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True)
if result.returncode == 0:
    paths = [ROOT / item.decode() for item in result.stdout.split(b'\0') if item]
else:
    paths = [path for path in ROOT.rglob('*') if path.is_file()
             and not {'.git', '__pycache__', 'build'} & set(path.relative_to(ROOT).parts)]
patterns = {
    'absolute personal home path': re.compile(r'(?:/home/[A-Za-z0-9_.-]+/|[A-Z]:\\(?:home|Users)\\[A-Za-z0-9_.-]+\\)'),
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'GitHub credential': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})'),
    'AWS access key': re.compile(r'AKIA[0-9A-Z]{16}'),
}
allowed_binaries = json.loads((ROOT / 'payload/SHA256.json').read_text())
failures = []
for path in paths:
    relative = path.relative_to(ROOT)
    name = relative.as_posix()
    if path.suffix in ('.pyc', '.pyo'):
        continue
    if (path.name in ('app.asar', 'LibTW.dec', 'config.json', 'config.sh', 'upstream-exports.sh')
            or path.suffix in ('.class', '.reg', '.khc', '.sqlite', '.db', '.log', '.before')
            or any(part.startswith(('diagnostics-', 'live-audit', 'live-plan')) for part in relative.parts)):
        failures.append((name, 'private/vendor runtime artifact'))
    raw = path.read_bytes()
    if path.suffix.lower() in ('.dll', '.exe'):
        if relative.parent != Path('payload') or path.name not in allowed_binaries:
            failures.append((name, 'unapproved binary'))
        elif hashlib.sha256(raw).hexdigest() != allowed_binaries[path.name]:
            failures.append((name, 'binary checksum mismatch'))
    texts = [raw.decode('utf-8', errors='ignore')]
    if b'\0' in raw:
        texts.extend(raw[offset:].decode('utf-16-le', errors='ignore') for offset in (0, 1))
    for description, pattern in patterns.items():
        # The official SQLite release carries its upstream CodeView build path.
        # Preserve that public vendor artifact verbatim; its exact release hash
        # gates this exception. Credential patterns are still checked below.
        if (description == 'absolute personal home path' and name == 'payload/winsqlite3.dll'
                and hashlib.sha256(raw).hexdigest() == allowed_binaries.get(path.name)):
            continue
        if any(pattern.search(text) for text in texts):
            failures.append((name, description))
if failures:
    for name, reason in failures:
        print(f'FAIL {name}: {reason}', file=sys.stderr)
    sys.exit(1)
print(f'PASS distribution check: {len(paths)} files; no private home paths, runtime data, unapproved binaries or credential patterns')
