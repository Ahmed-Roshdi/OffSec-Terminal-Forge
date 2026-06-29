#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/sync_repo.sh [branch]
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
echo "[*] Syncing branch: $BRANCH"

# Save local uncommitted changes (auto-commit) to avoid losing them
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[*] Uncommitted changes detected — committing as autosave."
  git add -A
  git commit -m "autosave: local changes before sync ($(date -u +%Y-%m-%dT%H:%M:%SZ))" || true
fi

# Fetch remote updates
git fetch origin

# Rebase local commits on top of remote
echo "[*] Rebasing onto origin/$BRANCH"
if git rev-parse --verify origin/"$BRANCH" >/dev/null 2>&1; then
  git rebase origin/"$BRANCH"
else
  echo "[*] Remote branch origin/$BRANCH not found — skipping rebase."
fi

# Push local commits (if any) to remote
echo "[*] Pushing to origin/$BRANCH"
git push origin "$BRANCH"

echo "[+] Sync complete."
