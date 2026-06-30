#!/bin/bash

REPO_PATH="/run/media/kubuntu/Fsat-Storage-SSD/04_Projects/01_In-Progress/OffSec-Terminal-Forge"
LOG_FILE="$REPO_PATH/.git/auto_sync.log"

cd "$REPO_PATH" || exit 1

# Fetch latest changes silently
git fetch origin main > /dev/null 2>&1

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date)] Updates detected. Synchronizing..." >> "$LOG_FILE"
    
    # Save uncommitted changes
    git stash > /dev/null 2>&1
    
    # Pull updates cleanly
    git pull --rebase origin main >> "$LOG_FILE" 2>&1
    
    # Restore uncommitted changes
    git stash pop > /dev/null 2>&1
    
    echo "[$(date)] Synchronization complete." >> "$LOG_FILE"
fi
