#!/bin/bash
# PostToolUse hook: forward the hook JSON to the edited file's repo formatter.
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

case "$file" in /*) ;; *) file="$root/$file" ;; esac

# Canonicalize without requiring the file (a new Write target) to exist:
# resolve the deepest existing ancestor, then re-append the rest.
rest=${file##*/}
dir=$(dirname "$file")
while [ ! -d "$dir" ] && [ "$dir" != "/" ]; do
  rest="${dir##*/}/$rest"
  dir=$(dirname "$dir")
done
dir=$(cd "$dir" 2>/dev/null && pwd -P) || exit 0
case "/$rest/" in */../*) exit 0 ;; esac
file="$dir/$rest"

for repo in backend frontend mobile; do
  case "$file" in
    "$root/$repo/"*)
      fmt="$root/$repo/.claude/hooks/format.sh"
      [ -x "$fmt" ] && (cd "$root/$repo" && printf '%s' "$input" | CLAUDE_PROJECT_DIR="$root/$repo" "$fmt") >/dev/null 2>&1
      break
      ;;
  esac
done
exit 0
