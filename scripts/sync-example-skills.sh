#!/usr/bin/env bash
# Sync the canonical panel skill into every example's .claude/skills/panel.
# Usage:
#   scripts/sync-example-skills.sh          # copy canonical -> examples (default)
#   scripts/sync-example-skills.sh check    # exit non-zero if any example has drifted
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/skills/panel"
MODE="${1:-sync}"

if [[ ! -d "$SRC" ]]; then
  echo "canonical skill missing: $SRC" >&2
  exit 1
fi

exit_code=0
found=0
while IFS= read -r dst; do
  found=1
  case "$MODE" in
    sync)
      rsync -a --delete "$SRC/" "$dst/"
      echo "synced $dst"
      ;;
    check)
      if ! diff -r "$SRC" "$dst" >/dev/null 2>&1; then
        echo "drift: $dst" >&2
        exit_code=1
      fi
      ;;
    *)
      echo "usage: $0 [sync|check]" >&2
      exit 2
      ;;
  esac
done < <(find "$ROOT/examples" -type d -path "*/.claude/skills/panel" | sort)

if [[ "$found" -eq 0 ]]; then
  echo "no example panel skills found under $ROOT/examples" >&2
  exit 1
fi

if [[ "$MODE" == "check" && "$exit_code" -eq 0 ]]; then
  echo "all example panel skills match canonical"
fi

exit "$exit_code"
