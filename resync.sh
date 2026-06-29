#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  git-sync.sh — Interactive Git Operations Menu
#  Place at repo root. Run: bash git-sync.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────
CY='\033[0;36m'   # cyan
MG='\033[0;35m'   # magenta
GR='\033[0;32m'   # green
YL='\033[1;33m'   # yellow
RD='\033[0;31m'   # red
DM='\033[2;37m'   # dim white
BD='\033[1m'      # bold
RS='\033[0m'      # reset

# ── Helpers ───────────────────────────────────────────────────
info()    { echo -e "${CY}[*]${RS} $*"; }
ok()      { echo -e "${GR}[+]${RS} $*"; }
warn()    { echo -e "${YL}[!]${RS} $*"; }
err()     { echo -e "${RD}[!]${RS} $*"; }
dim()     { echo -e "${DM}$*${RS}"; }
divider() { echo -e "${DM}──────────────────────────────────────────${RS}"; }

current_branch() {
  git symbolic-ref --quiet --short HEAD 2>/dev/null \
    || echo "(detached:$(git rev-parse --short HEAD 2>/dev/null))"
}

require_git() {
  if ! git rev-parse --git-dir >/dev/null 2>&1; then
    err "Not inside a git repository."
    exit 1
  fi
}

press_enter() {
  echo ""
  dim "  Press Enter to return to menu..."
  read -r
}

# ── Header ────────────────────────────────────────────────────
print_header() {
  clear
  echo -e "${MG}${BD}"
  echo "  ╔══════════════════════════════════════════╗"
  echo "  ║        OffSec-Terminal-Forge             ║"
  echo "  ║        Git Sync & Operations             ║"
  echo "  ╚══════════════════════════════════════════╝"
  echo -e "${RS}"
  local branch
  branch=$(current_branch)
  local status_line
  status_line=$(git status --short | wc -l | tr -d ' ')
  echo -e "  ${DM}Branch  :${RS} ${CY}${BD}${branch}${RS}"
  echo -e "  ${DM}Changes :${RS} ${YL}${status_line} uncommitted file(s)${RS}"
  echo -e "  ${DM}Remote  :${RS} ${DM}$(git remote get-url origin 2>/dev/null || echo 'none')${RS}"
  divider
}

# ── Menu ──────────────────────────────────────────────────────
print_menu() {
  echo ""
  echo -e "  ${BD}Choose an operation:${RS}"
  echo ""
  echo -e "  ${CY} 1${RS}  📥  Pull          — fetch & merge latest from remote"
  echo -e "  ${CY} 2${RS}  📤  Push          — push current branch to remote"
  echo -e "  ${CY} 3${RS}  🔄  Resync        — rebase onto remote, then push"
  echo -e "  ${CY} 4${RS}  💾  Quick Save    — add all → commit → push"
  echo -e "  ${CY} 5${RS}  🌿  Branch        — switch or create a branch"
  echo -e "  ${CY} 6${RS}  📊  Status & Log  — show diff summary + last 5 commits"
  echo -e "  ${CY} 7${RS}  🔀  Merge         — merge another branch into current"
  echo -e "  ${CY} 8${RS}  🗑️   Discard       — reset all uncommitted changes"
  echo -e "  ${CY} 9${RS}  🔁  Stash         — stash changes / pop stash"
  echo -e "  ${MG}10${RS}  ❌  Exit"
  echo ""
  divider
}

# ─────────────────────────────────────────────────────────────
#  Operations
# ─────────────────────────────────────────────────────────────

op_pull() {
  print_header
  local branch; branch=$(current_branch)
  info "Pulling latest from origin/${branch}..."
  echo ""
  if git pull origin "$branch"; then
    ok "Pull complete. Branch is up to date."
  else
    warn "Pull failed — there may be conflicts to resolve."
  fi
  press_enter
}

op_push() {
  print_header
  local branch; branch=$(current_branch)

  # Check for uncommitted changes
  if ! git diff --quiet || ! git diff --cached --quiet; then
    warn "You have uncommitted changes."
    echo -e "  ${DM}$(git status --short)${RS}"
    echo ""
    echo -e "  ${YL}Commit them first? (y/n):${RS} \c"
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
      echo -e "  ${YL}Commit message:${RS} \c"
      read -r msg
      msg="${msg:-chore: local changes}"
      git add -A
      git commit -m "$msg"
    else
      warn "Pushing with uncommitted changes — only staged files will be included."
    fi
  fi

  info "Pushing to origin/${branch}..."
  echo ""
  if git push --set-upstream origin "$branch"; then
    ok "Push complete → origin/${branch}"
  else
    err "Push failed. Try Resync (option 3) to rebase first."
  fi
  press_enter
}

op_resync() {
  print_header
  local branch; branch=$(current_branch)
  info "Full Resync: autosave → fetch → rebase → push"
  echo ""

  # Step 1: autosave uncommitted changes
  if ! git diff --quiet || ! git diff --cached --quiet; then
    info "Uncommitted changes detected — autosaving..."
    git add -A
    git commit -m "autosave: before resync ($(date -u +%Y-%m-%dT%H:%M:%SZ))" || true
    ok "Autosave committed."
  else
    dim "  Nothing to autosave."
  fi

  # Step 2: fetch
  info "Fetching from origin..."
  git fetch origin

  # Step 3: rebase
  if git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
    info "Rebasing onto origin/${branch}..."
    if git rebase "origin/${branch}"; then
      ok "Rebase complete."
    else
      err "Rebase conflict detected."
      warn "Resolve conflicts, then run: git rebase --continue"
      warn "Or abort with: git rebase --abort"
      press_enter
      return
    fi
  elif git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
    warn "origin/${branch} not found — rebasing onto origin/main instead."
    if git rebase origin/main; then
      ok "Rebase onto main complete."
    else
      err "Rebase conflict. Resolve then: git rebase --continue"
      press_enter
      return
    fi
  else
    warn "No remote branch to rebase against — skipping rebase."
  fi

  # Step 4: push
  info "Pushing to origin/${branch}..."
  if git push --set-upstream origin "$branch"; then
    ok "Resync complete → origin/${branch}"
  else
    err "Push failed. You may need to force-push: git push --force-with-lease origin ${branch}"
  fi
  press_enter
}

op_quick_save() {
  print_header

  # Check if there's anything to save
  if git diff --quiet && git diff --cached --quiet; then
    warn "Nothing to commit — working tree is clean."
    press_enter
    return
  fi

  echo -e "  ${DM}Files to be committed:${RS}"
  git status --short
  echo ""
  echo -e "  ${YL}Commit message${RS} ${DM}(Enter for default):${RS} \c"
  read -r msg

  local branch; branch=$(current_branch)
  local ts; ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  msg="${msg:-chore: quick save ${ts}}"

  git add -A
  git commit -m "$msg"
  info "Pushing to origin/${branch}..."
  if git push --set-upstream origin "$branch"; then
    ok "Saved and pushed → origin/${branch}"
  else
    err "Commit saved locally but push failed. Run option 2 or 3 to push."
  fi
  press_enter
}

op_branch() {
  print_header
  echo -e "  ${BD}Branch Operations:${RS}"
  echo ""
  echo -e "  ${CY}1${RS}  Switch to existing branch"
  echo -e "  ${CY}2${RS}  Create new branch (from current HEAD)"
  echo -e "  ${CY}3${RS}  Create new branch (from origin/main)"
  echo -e "  ${CY}4${RS}  List all branches"
  echo -e "  ${CY}5${RS}  Delete a local branch"
  echo -e "  ${CY}6${RS}  Back"
  echo ""
  divider
  echo -e "  ${YL}Choice:${RS} \c"
  read -r choice

  case "$choice" in
    1)
      echo ""
      git branch -a
      echo ""
      echo -e "  ${YL}Branch name:${RS} \c"
      read -r name
      git checkout "$name" && ok "Switched to ${name}"
      ;;
    2)
      echo -e "  ${YL}New branch name:${RS} \c"
      read -r name
      git checkout -b "$name"
      ok "Created and switched to ${name}"
      ;;
    3)
      git fetch origin
      echo -e "  ${YL}New branch name:${RS} \c"
      read -r name
      git checkout -B "$name" origin/main
      ok "Created ${name} from origin/main"
      ;;
    4)
      echo ""
      echo -e "${CY}Local branches:${RS}"
      git branch -v
      echo ""
      echo -e "${CY}Remote branches:${RS}"
      git branch -r
      ;;
    5)
      echo ""
      git branch -v
      echo ""
      echo -e "  ${YL}Branch to delete:${RS} \c"
      read -r name
      git branch -d "$name" && ok "Deleted local branch: ${name}" \
        || warn "Use -D to force delete: git branch -D ${name}"
      ;;
    *) ;;
  esac
  press_enter
}

op_status() {
  print_header
  echo -e "${CY}${BD}Git Status:${RS}"
  echo ""
  git status
  echo ""
  divider
  echo -e "${CY}${BD}Last 5 commits:${RS}"
  echo ""
  git log --oneline --graph --decorate -5 2>/dev/null || git log --oneline -5
  echo ""
  divider
  echo -e "${CY}${BD}Diff summary (staged + unstaged):${RS}"
  echo ""
  git diff --stat HEAD 2>/dev/null || dim "  Nothing staged."
  press_enter
}

op_merge() {
  print_header
  local current; current=$(current_branch)
  echo -e "  ${DM}Current branch:${RS} ${CY}${current}${RS}"
  echo ""
  echo -e "${CY}Available branches:${RS}"
  git branch -a
  echo ""
  echo -e "  ${YL}Branch to merge INTO ${current}:${RS} \c"
  read -r source

  if [ -z "$source" ]; then
    warn "No branch specified."
    press_enter
    return
  fi

  info "Merging ${source} into ${current}..."
  if git merge "$source"; then
    ok "Merge complete."
    echo -e "  Push to remote? ${YL}(y/n):${RS} \c"
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
      git push --set-upstream origin "$current"
      ok "Pushed merged result to origin/${current}"
    fi
  else
    err "Merge conflict. Resolve manually, then: git merge --continue"
  fi
  press_enter
}

op_discard() {
  print_header
  warn "This will PERMANENTLY discard all uncommitted changes."
  echo ""
  echo -e "  ${DM}$(git status --short)${RS}"
  echo ""
  echo -e "  ${RD}Type 'yes' to confirm discard:${RS} \c"
  read -r answer
  if [ "$answer" = "yes" ]; then
    git checkout -- .
    git clean -fd
    ok "All uncommitted changes discarded."
  else
    info "Cancelled — nothing changed."
  fi
  press_enter
}

op_stash() {
  print_header
  echo -e "  ${BD}Stash Operations:${RS}"
  echo ""
  echo -e "  ${CY}1${RS}  Stash current changes"
  echo -e "  ${CY}2${RS}  Pop latest stash"
  echo -e "  ${CY}3${RS}  List all stashes"
  echo -e "  ${CY}4${RS}  Drop latest stash"
  echo -e "  ${CY}5${RS}  Back"
  echo ""
  divider
  echo -e "  ${YL}Choice:${RS} \c"
  read -r choice

  case "$choice" in
    1)
      echo -e "  ${YL}Stash message (optional):${RS} \c"
      read -r msg
      if [ -n "$msg" ]; then
        git stash push -m "$msg" && ok "Changes stashed: $msg"
      else
        git stash push && ok "Changes stashed."
      fi
      ;;
    2)
      git stash pop && ok "Stash popped." || err "No stash to pop."
      ;;
    3)
      git stash list || dim "  No stashes."
      ;;
    4)
      git stash drop && ok "Latest stash dropped." || err "No stash to drop."
      ;;
    *) ;;
  esac
  press_enter
}

# ─────────────────────────────────────────────────────────────
#  Main loop
# ─────────────────────────────────────────────────────────────
require_git

while true; do
  print_header
  print_menu
  echo -e "  ${YL}Choice:${RS} \c"
  read -r choice

  case "$choice" in
    1)  op_pull       ;;
    2)  op_push       ;;
    3)  op_resync     ;;
    4)  op_quick_save ;;
    5)  op_branch     ;;
    6)  op_status     ;;
    7)  op_merge      ;;
    8)  op_discard    ;;
    9)  op_stash      ;;
    10) ok "Bye."; exit 0 ;;
    *)  warn "Invalid choice. Enter 1–10." ;;
  esac
done
