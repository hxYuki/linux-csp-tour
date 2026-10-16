#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py' -v
/usr/bin/python3 - <<'PY'
import ast, hashlib, json
from pathlib import Path
for path in Path('.').rglob('*.py'):
    ast.parse(path.read_text(), filename=str(path))
for name, expected in json.loads(Path('payload/SHA256.json').read_text()).items():
    assert hashlib.sha256((Path('payload') / name).read_bytes()).hexdigest() == expected, name
print('PASS Python syntax and payload checksums')
PY
while IFS= read -r -d '' script; do bash -n "$script"; done < <(find . -name '*.sh' -print0)
bash -n bin/csp-tour bin/tourbox-compat-run
/usr/bin/python3 scripts/check_distribution.py
if command -v Xvfb >/dev/null; then /usr/bin/python3 tests/verify_x11.py; fi
if [[ $# -gt 0 ]]; then /usr/bin/python3 tests/verify_local_fixture.py "$1"; fi
