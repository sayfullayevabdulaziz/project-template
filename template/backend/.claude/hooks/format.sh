#!/bin/bash
# PostToolUse hook: ruff-format a .py file that was just edited inside this repo.
# Never blocks an edit: every path exits 0. No -e on purpose.
set -u

input=$(cat)
root=$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd -P) || exit 0

if command -v jq >/dev/null 2>&1; then
  file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty | strings' 2>/dev/null)
else
  file=$(printf '%s' "$input" | python3 -c '
import json, sys
p = json.load(sys.stdin)["tool_input"]["file_path"]
print(p if isinstance(p, str) else "")' 2>/dev/null)
fi
[ -n "$file" ] || exit 0
case "$file" in *.py) ;; *) exit 0 ;; esac

case "$file" in /*) ;; *) file="$root/$file" ;; esac
[ -f "$file" ] || exit 0

# Canonicalize (resolves symlinks and ..) so the inside-repo check cannot be dodged.
dir=$(cd "$(dirname "$file")" 2>/dev/null && pwd -P) || exit 0
file="$dir/${file##*/}"
case "$file" in "$root"/*) ;; *) exit 0 ;; esac

cd "$root" || exit 0
uv run ruff format "$file" >/dev/null 2>&1 && uv run ruff check --fix "$file" >/dev/null 2>&1
exit 0
