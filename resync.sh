#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/resync.sh [branch]
REQUESTED_BRANCH="${1:-}"

# Determine current branch name; handle detached HEAD
current_branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"

if [ -n "$REQUESTED_BRANCH" ]; then
  BRANCH="$REQUESTED_BRANCH"
elif [ -n "$current_branch" ] && [ "$current_branch" != "HEAD" ]; then
  BRANCH="$current_branch"
else
  # Detached HEAD: create a safe autosave branch name
  SHORT=$(git rev-parse --short HEAD)
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  BRANCH="autosave-${SHORT}-${TS}"
  echo "[*] Detached HEAD detected — will create branch: $BRANCH"
  # create the branch locally pointing at HEAD
  git checkout -b "$BRANCH"
fi

echo "[*] Syncing branch: $BRANCH"

# Commit uncommitted changes as autosave if any
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[*] Uncommitted changes detected — committing as autosave."
  git add -A
  git commit -m "autosave: local changes before sync ($(date -u +%Y-%m-%dT%H:%M:%SZ))" || true
fi

# Fetch remote updates
git fetch origin

# If remote branch exists, rebase local branch onto it; otherwise try origin/main
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  echo "[*] Rebasing onto origin/$BRANCH"
  git rebase "origin/$BRANCH"
else
  # fallback: try to rebase onto origin/main if it exists
  if git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
    echo "[*] origin/$BRANCH not found — rebasing onto origin/main"
    git rebase origin/main
  else
    echo "[*] No suitable remote branch to rebase against; skipping rebase."
  fi
fi

# Push local branch to origin (create/overwrite remote branch)
echo "[*] Pushing to origin/$BRANCH"
git push --set-upstream origin "$BRANCH"

echo "[+] Sync complete."
