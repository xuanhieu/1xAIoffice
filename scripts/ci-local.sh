#!/usr/bin/env bash
# Run exactly the steps of .github/workflows/quality.yml on this machine, before pushing.
# The step list is read from the workflow itself, so the two can never drift apart. Exits non-zero on the first
# failing step, naming it. Needs shellcheck (brew install shellcheck), like the CI runner has.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v shellcheck >/dev/null || { echo "Cần shellcheck: brew install shellcheck"; exit 1; }
RUNNER_TEMP="$(mktemp -d)"
export RUNNER_TEMP
trap 'rm -rf "$RUNNER_TEMP"' EXIT
steps="$(python3 - <<'PY'
import re
name = None
for line in open(".github/workflows/quality.yml", encoding="utf-8"):
    m = re.match(r"\s*- name:\s*(.+)", line)
    if m:
        name = m.group(1).strip()
        continue
    m = re.match(r"\s*run:\s*(.+)", line)
    if m and name:
        print(f"{name}\t{m.group(1).strip()}")
PY
)"
[ -n "$steps" ] || { echo "Không đọc được bước nào trong quality.yml"; exit 1; }
while IFS=$'\t' read -r name cmd; do
  printf '==> %s\n' "$name"
  if ! bash -c "$cmd" >"$RUNNER_TEMP/step.log" 2>&1; then
    tail -40 "$RUNNER_TEMP/step.log"
    echo "HỎNG: $name ($cmd)"
    exit 1
  fi
done <<< "$steps"
echo "==> Mọi bước của workflow quality đều đạt."
