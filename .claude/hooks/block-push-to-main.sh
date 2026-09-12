#!/usr/bin/env bash
# PreToolUse hook for Bash: refuse any `git push` that targets main.
# Every change to this repository is a pull request (docs/development/AGENT_PROTOCOL.md "Delivery").
set -euo pipefail
input="$(cat)"
cmd="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null || true)"
case "$cmd" in
  *"git push"*) ;;
  *) exit 0 ;;
esac
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
if printf '%s' "$cmd" | grep -Eq '(^|[[:space:]:])main([[:space:]]|$)' || [ "$branch" = "main" ]; then
  echo "Blocked: pushes to main are not allowed. Open a pull request from a feature branch instead." >&2
  exit 2
fi
exit 0
