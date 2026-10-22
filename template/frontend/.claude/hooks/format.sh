#!/usr/bin/env bash
# PostToolUse hook: format the edited file. Never fails the session.
input="$(cat 2>/dev/null)"
root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}"
[ -n "$root" ] && [ -d "$root" ] || exit 0
root="$(cd "$root" 2>/dev/null && pwd -P)" || exit 0

if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
else
  file="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)"
fi
[ -n "$file" ] && [ -f "$file" ] || exit 0

# Resolve symlinks and ".." so the prefix check cannot be spoofed.
dir="$(cd "$(dirname "$file")" 2>/dev/null && pwd -P)" || exit 0
file="$dir/$(basename "$file")"
case "$file" in "$root"/*) ;; *) exit 0 ;; esac
rel="${file#"$root"/}"

case "$rel" in
  src/client/*|src/routeTree.gen.ts|node_modules/*|*/node_modules/*|openapi.json) exit 0 ;;
esac
case "$file" in
  *.ts|*.tsx|*.js|*.jsx|*.json|*.css|*.md|*.html) ;;
  *) exit 0 ;;
esac

cd "$root" 2>/dev/null || exit 0
# Prefer the local bin (what `pnpm exec` resolves to) so a broken pnpm version switch cannot skip formatting.
run() { if [ -x "node_modules/.bin/$1" ]; then "node_modules/.bin/$1" "${@:2}"; else pnpm exec "$@"; fi; }
run prettier --write "$file" >/dev/null 2>&1
case "$file" in
  *.ts|*.tsx|*.js|*.jsx) run eslint --fix "$file" >/dev/null 2>&1 ;;
esac
exit 0
