#!/usr/bin/env bash
# Bootstrap-capsule checker. Supports the deliberately small task schema here.
set -euo pipefail
python3 - "$@" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]) if len(sys.argv) == 2 else None
errors = []
if root is None or not root.is_dir():
    print("CRITICAL: supply an existing capsule directory")
    sys.exit(1)
if not (root / "epic.yaml").is_file():
    errors.append("CRITICAL: missing epic.yaml")
for tasks in root.glob("*-tasks.yaml"):
    text = tasks.read_text()
    match = re.search(r"^story_id: (e[0-9]+s[0-9]+)$", text, re.M)
    specs = list(root.glob(match[1] + "-*.md")) if match else []
    if len(specs) != 1:
        errors.append("HIGH: task ledger must have exactly one matching story spec")
        continue
    story = specs[0].read_text()
    if len(re.findall(r"^## [0-9]+\.", story, re.M)) != 20:
        errors.append("HIGH: story must have 20 numbered sections")
    blocks = re.split(r"^  - id: ", text, flags=re.M)[1:]
    if not blocks:
        errors.append("HIGH: empty task ledger")
    ids = [block.splitlines()[0] for block in blocks]
    if len(ids) != len(set(ids)):
        errors.append("HIGH: duplicate task ids")
    severity = {"P0": "critical", "P1": "high", "P2": "normal", "P3": "minor"}
    for block in blocks:
        risk = re.search(r"^    risk: (P[0-3])$", block, re.M)
        if not risk or "severity: " + severity[risk[1]] not in block:
            errors.append("HIGH: missing risk or mismatched Allure severity")
        if not re.search(r"^    status: (failing|passing)$", block, re.M):
            errors.append("HIGH: missing task status")
        if not re.search(r'^    verify: "[^"]+"$', block, re.M):
            errors.append("HIGH: missing runnable verify command")
    for section in re.split(r"^####? ", story, flags=re.M)[1:]:
        if section.startswith(("MODIFIED:", "REMOVED:", "RENAMED:")) and not all(key in section for key in ("**Before:**", "**After:**")):
            errors.append("HIGH: requirement delta missing before/after")
    if "status: passing" in text.split("tasks:", 1)[0] and any("status: failing" in b for b in blocks):
        errors.append("HIGH: passing story contains failing tasks")
if not list(root.glob("*-tasks.yaml")):
    errors.append("HIGH: missing task ledger")
for error in errors:
    print(error)
if not errors:
    print("PASS: bootstrap capsule consistency; CRITICAL=0 HIGH=0 MED=0")
sys.exit(bool(errors))
PY
