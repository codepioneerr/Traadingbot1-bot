#!/usr/bin/env bash
# Commit and push memory files so state survives the ephemeral clone.
# Usage: bash scripts/persist.sh "<commit message>" [path ...]
# Defaults to persisting memory/ when no paths are given.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

msg="${1:?usage: persist.sh \"<commit message>\" [path ...]}"
shift
files=("$@")
[[ ${#files[@]} -eq 0 ]] && files=(memory/)

git add -- "${files[@]}"

if git diff --cached --quiet; then
  echo "[persist] nothing staged to commit"
else
  git commit -m "$msg"
fi

# A scheduled run can start on a detached HEAD. Committing there and then
# pushing 'main' pushes the stale branch, reports success, and strands the
# commit — so carry HEAD onto main before pushing.
if ! git symbolic-ref -q HEAD >/dev/null; then
  detached="$(git rev-parse HEAD)"
  echo "[persist] detached HEAD — reattaching to main (carrying $detached)"
  git checkout main 2>/dev/null || git checkout -b main origin/main
  git merge --no-edit "$detached"
fi

delay=2
for attempt in 1 2 3 4; do
  if git push -u origin main; then
    echo "[persist] pushed $(git rev-parse --short HEAD) to origin/main"
    exit 0
  fi
  echo "[persist] push failed (attempt $attempt) — rebasing on origin/main" >&2
  git pull --rebase origin main || true
  sleep "$delay"
  delay=$((delay * 2))
done

echo "[persist] ERROR: push failed after 4 attempts — state NOT persisted" >&2
exit 1
