#!/usr/bin/env bash
# Shared helpers for the task scripts. Source, don't execute.
set -euo pipefail

repo_root() { git rev-parse --show-toplevel; }

# Operator: who is running this. From env, else git config, else fail loudly.
operator() {
  if [[ -n "${WAYFINDER_OPERATOR:-}" ]]; then echo "$WAYFINDER_OPERATOR"; return; fi
  local h; h="$(git config wayfinder.operator || true)"
  if [[ -z "$h" ]]; then
    echo "error: set your handle once with:  git config wayfinder.operator <handle>" >&2
    exit 1
  fi
  echo "$h"
}

# Agent: which tool/model is driving. Agents set WAYFINDER_AGENT in their environment.
agent() { echo "${WAYFINDER_AGENT:-human}"; }

# Session: stable for the life of one agent session; falls back to a per-day id for humans.
session() {
  if [[ -n "${WAYFINDER_SESSION:-}" ]]; then echo "$WAYFINDER_SESSION"; return; fi
  echo "$(date -u +%Y-%m-%dT%H:%MZ)/$(git rev-parse --short HEAD 2>/dev/null || echo init)"
}

now_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Module → owner, read from the YAML block in docs/team/OWNERSHIP.md
module_owner() {
  local module="$1"
  python3 - "$module" <<'PY'
import re, sys, pathlib
mod = sys.argv[1]
text = pathlib.Path("docs/team/OWNERSHIP.md").read_text()
block = re.search(r"```yaml\n(.*?)```", text, re.S).group(1)
m = re.search(rf"^\s*{re.escape(mod)}:\s*\{{owner:\s*([^,]+),", block, re.M)
if not m:
    print("unknown"); sys.exit(0)
print(m.group(1).strip())
PY
}

log_path() { echo "docs/agent-log/$1.md"; }

die() { echo "error: $*" >&2; exit 1; }
