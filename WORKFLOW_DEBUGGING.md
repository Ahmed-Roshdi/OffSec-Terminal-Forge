# 🔍 GitHub Actions Workflow Debugging Guide

## Problem Statement

**The workflow runs successfully BUT produces NO output in the repository:**
- ✅ Secrets load correctly
- ✅ Python scripts execute without errors
- ✅ Output files ARE generated (`dialogue_seq_*.webp` files)
- ✅ No errors or failures reported
- ❌ BUT: No changes appear in `main` branch
- ❌ BUT: No PR is created
- ❌ BUT: Output folder is NOT committed to the repository

---

## Workflow Flow Diagram

```
Step 1: Checkout main branch
    ↓
Step 2-4: Setup Python & verify secrets
    ↓
Step 5: Generate alien map → output/maps/
    ↓
Step 6: Generate dialogue → output/dialogues/
    ↓
Step 7: Verify output/ is NOT empty ✅ PASSES
    ↓
Step 8: Create branch auto/generate-assets & commit
    ↓ (Sets HAS_CHANGES=true or false)
    ↓
Step 9: Create PR (if HAS_CHANGES==true)
    ↓ (Should set pull-request-number output)
    ↓
Step 10: Auto-merge PR into main (if PR exists)
    ↓
Step 11: Confirm main has changes
```

---

## Current Issues Identified

### Issue 1: HAS_CHANGES Variable Not Set Correctly
**Location:** Step 8 (📤 Commit & push)

**Problem:**
```yaml
if git diff --cached --quiet; then
  echo "HAS_CHANGES=false" >> "$GITHUB_ENV"
else
  echo "HAS_CHANGES=true" >> "$GITHUB_ENV"
fi
```

**Why it fails:**
- `$GITHUB_ENV` needs proper formatting with newlines
- The variable might not persist between steps
- The condition logic may be backwards

**Solution:**
```yaml
if git diff --cached --quiet; then
  echo "HAS_CHANGES=false" >> $GITHUB_ENV
else
  echo "HAS_CHANGES=true" >> $GITHUB_ENV
fi
```

---

### Issue 2: Git Branch Not Actually Pushing
**Location:** Step 8 (git push)

**Problem:**
```bash
git checkout -B auto/generate-assets origin/main
git add output/
git commit -m "🤖 chore: auto-generated AI dialogue & map [skip ci]"
git push origin auto/generate-assets --force
```

**Why it might fail:**
1. `git add output/` might not be adding files (wrong working directory?)
2. `git diff --cached --quiet` returns 0 (true) even when files ARE staged
3. Files are being added but NOT tracked by git initially
4. `.gitignore` might be excluding the `output/` directory

**Debug needed:**
```bash
# Check what's actually in output/
ls -la output/
find output/ -type f

# Check git status
git status
git ls-files -o --exclude-standard

# Check if output/ is in .gitignore
cat .gitignore | grep -i output
```

---

### Issue 3: peter-evans/create-pull-request Action Not Running
**Location:** Step 9 (📬 Create PR)

**Problem:**
```yaml
if: env.HAS_CHANGES == 'true'
uses: peter-evans/create-pull-request@v6
```

**Why it doesn't run:**
- `HAS_CHANGES` is never set to `'true'` (Issue 1)
- OR the action runs but doesn't produce a PR because no changes exist
- The `branch: auto/generate-assets` doesn't exist or is empty

**Evidence from logs:**
```
[*] No changes — output is identical to last run.
```

This message appears, meaning `git diff --cached --quiet` returned TRUE (no changes), so `HAS_CHANGES=false`.

---

### Issue 4: .gitignore Blocking output/ Directory
**Critical Check:**

The `output/` directory might be in `.gitignore`, preventing git from tracking files inside it.

**Check:**
```bash
git check-ignore -v output/
git check-ignore -v output/dialogues/
git check-ignore -v output/dialogues/dialogue_seq_*.webp
```

---

## Root Cause Analysis

### Most Likely Cause: `.gitignore` Excludes `output/`

If `.gitignore` contains:
```
output/
build/
dist/
*.webp
```

Then:
1. Files ARE generated ✅
2. `git add output/` runs WITHOUT errors ✅
3. But git IGNORES those files silently ✅
4. So `git diff --cached --quiet` finds NO staged changes ✅
5. `HAS_CHANGES=false` ✅
6. PR is NOT created ✅

This explains the "no changes" message while files ARE being generated!

---

## Step-by-Step Fix Guide

### Fix 1: Check and Update .gitignore

**Run this in the workflow to debug:**
```yaml
- name: 🔍 Check .gitignore rules
  run: |
    echo "[*] Checking .gitignore..."
    if [ -f .gitignore ]; then
      echo "[*] Contents of .gitignore:"
      cat .gitignore
      echo ""
      echo "[*] Checking if output/ is ignored:"
      git check-ignore -v output/ || echo "[+] output/ is NOT ignored"
    else
      echo "[+] No .gitignore file"
    fi
    
    echo ""
    echo "[*] Checking if output files are ignored:"
    git check-ignore -v output/dialogues/dialogue_seq_*.webp || echo "[+] output files are NOT ignored"
```

**If output/ is ignored, fix it:**

Edit `.gitignore` and ensure it does NOT contain:
```
output/
/output
output/*
```

If you need to exclude some files in output/ but not all, use:
```gitignore
# Allow output directory to be tracked
!/output/
# But exclude certain files if needed
output/**/*.tmp
```

---

### Fix 2: Force Git to Track output/ (Temporary Fix)

Add this to Step 8 BEFORE `git add output/`:
```bash
# Force remove output/ from gitignore temporarily
git add -f output/dialogues/*.webp
git add -f output/maps/*.webp
```

---

### Fix 3: Better Logging in Step 8

Replace Step 8 with this FULL debugging version:

```yaml
      - name: 📤 Commit & push to auto/generate-assets
        id: push
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[1️⃣] CURRENT STATE"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[*] Current branch: $(git branch --show-current)"
          echo "[*] Remote branches:"
          git branch -r | head -10
          
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[2️⃣] CHECK .gitignore"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          if [ -f .gitignore ]; then
            echo "[*] .gitignore exists:"
            cat .gitignore | grep -i output || echo "[+] No 'output' rules found"
          else
            echo "[+] No .gitignore file"
          fi
          
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[3️⃣] CHECK GENERATED FILES"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[*] Files in output/:"
          find output/ -type f 2>/dev/null | head -20 || echo "[!] output/ directory not found"
          echo "[*] Total files in output/:"
          find output/ -type f 2>/dev/null | wc -l
          
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[4️⃣] CHECKOUT FEATURE BRANCH"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          git fetch origin main
          git checkout -B auto/generate-assets origin/main
          echo "[+] Checked out auto/generate-assets"
          
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[5️⃣] GIT STATUS BEFORE ADD"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          git status
          
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[6️⃣] ADD FILES (with force to bypass gitignore)"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          git add -f output/
          echo "[+] Executed: git add -f output/"
          
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[7️⃣] STAGED FILES"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[*] Staged files (git diff --cached):"
          git diff --cached --name-only | head -20
          echo "[*] Total staged files:"
          git diff --cached --name-only | wc -l
          
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[8️⃣] CHECK IF CHANGES EXIST"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          if git diff --cached --quiet; then
            echo "[!] git diff --cached --quiet returned: TRUE (no changes)"
            echo "HAS_CHANGES=false" >> $GITHUB_ENV
            echo "[*] Set HAS_CHANGES=false"
          else
            echo "[+] git diff --cached --quiet returned: FALSE (changes found!)"
            echo "HAS_CHANGES=true" >> $GITHUB_ENV
            echo "[*] Set HAS_CHANGES=true"
          fi
          
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "[9️⃣] COMMIT & PUSH"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          if [ "$HAS_CHANGES" == "true" ]; then
            git commit -m "🤖 chore: auto-generated AI dialogue & map [skip ci]"
            echo "[+] Committed"
            git push origin auto/generate-assets --force
            echo "[+] Pushed to origin/auto/generate-assets"
          else
            echo "[*] Skipping commit & push (no changes)"
          fi
```

---

## What This Debugging Will Show

After running this enhanced Step 8, you'll see:

1. **If .gitignore is the problem:**
   ```
   [*] .gitignore exists:
   output/           ← THIS IS THE CULPRIT!
   ```

2. **If files were generated:**
   ```
   [*] Total files in output/:
   15
   ```

3. **If files are staged:**
   ```
   [*] Total staged files:
   15
   ```

4. **Why no changes are detected:**
   ```
   [!] git diff --cached --quiet returned: TRUE (no changes)
   ```

---

## How to Fix (Final Solution)

### Option A: Remove `output/` from .gitignore

Edit `.gitignore` and remove:
```
output/
```

### Option B: Use .gitignore Force Add in Workflow

If you NEED `output/` in `.gitignore` for local development, use:
```bash
git add -f output/dialogues/
git add -f output/maps/
```

### Option C: Add Exception in .gitignore

```gitignore
# Ignore output but NOT the files we want to commit
output/
!output/dialogues/
!output/maps/
!output/**/*.webp
```

---

## Testing Checklist

After applying fixes, verify:

- [ ] Run workflow manually
- [ ] Check Step 8 logs for "Total staged files: > 0"
- [ ] Check Step 8 logs for "HAS_CHANGES=true"
- [ ] Check Step 9 logs for PR creation
- [ ] Check Step 10 logs for auto-merge success
- [ ] Verify `main` branch has new commit with output files
- [ ] Verify `output/` folder is now in repository

---

## Emergency Commands (If Still Broken)

Add this as a new step BEFORE "Create Pull Request" for manual push:

```yaml
- name: 🚨 Emergency: Manual PR Creation
  if: failure() || env.HAS_CHANGES == 'true'
  env:
    GH_TOKEN: ${{ secrets.GH_PAT }}
  run: |
    echo "[!] Using emergency PR creation..."
    git branch -D auto/generate-assets 2>/dev/null || true
    git checkout -b auto/generate-assets
    git add -f output/
    git commit -m "🤖 Emergency: auto-generated assets"
    git push -f origin auto/generate-assets
    
    gh pr create \
      --base main \
      --head auto/generate-assets \
      --title "🚨 Emergency: Generated AI Assets" \
      --body "Manual PR creation - workflow debugging" \
      --label automated || echo "[*] PR may already exist"
```

---

## Summary

**The Problem:** Files are generated but not committed because `.gitignore` likely excludes `output/` directory.

**The Solution:**
1. Check `.gitignore` for `output/` entry
2. Either remove it OR add exceptions with `!output/`
3. Use `git add -f output/` to force-add ignored files
4. Use the enhanced debugging step to verify

**Next Steps:**
1. Apply the debugging Step 8
2. Run the workflow
3. Share the logs from Step 8
4. We'll identify the exact issue
5. Apply the appropriate fix

