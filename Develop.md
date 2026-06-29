# 📋 DEVLOG — OffSec-Terminal-Forge

> Development log: fixed bugs, current status, and what's next.

---

## ✅ Current Status

| Module | Status | Notes |
|--------|--------|-------|
| `alien_generator.py` | ✅ Working | Generates map + `latest_map.webp` |
| `ai_engine.py` | ✅ Working | Groq `llama-3.3-70b-versatile` + local fallback |
| `dialogue_generator.py` | ✅ Working | JSON → WebP + `latest_dialogue.webp` |
| `orchestrator.py` | ✅ Working | Shares `PIPELINE_RUN_TS` across both engines |
| `Workflow-Output.yml` | ✅ Working | Auto-PR → auto-merge to `main` |
| `_fonts.py` | ✅ Working | Shared font resolution |
| `core_engine.py` | 🔲 Pending | Not yet implemented |

---

## 🐛 Fixed Issues (History)

| # | Error | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | `NameError: output_path` | Dead code block at bottom of original `dialogue_generator.py` floated outside any function | Removed the broken block; moved verification inside `main()` |
| 2 | `peter-evans` action reset branch | Action did its own `git push` after ours and force-reset `auto/generate-assets` to `main` HEAD | Replaced with `gh pr create` CLI — we control all git operations |
| 3 | `output/` never committed | `.gitignore` silently excluded `output/` | Added `git add -f output/` (force bypasses gitignore) |
| 4 | `GROQ_API_KEY` 403 on every call | Wrong key value stored in GitHub secret | Regenerated fresh key from `console.groq.com`; added `gsk_` prefix check |
| 5 | `git add` before `git checkout` | Staging area state inconsistent after branch switch | Reordered: fetch → checkout from `origin/main` → `git add -f` |
| 6 | `PIPELINE_RUN_TS` lost between steps | `os.environ` set in `ai_engine.py` process dies when the step ends; `dialogue_generator.py` runs in a new process with empty env | Use `orchestrator.py` as single entrypoint — both engines share the same process and the env var persists |
| 7 | `dialogue_generator.py` rendered all historical JSON files | `PIPELINE_RUN_TS` was empty so the run filter had no effect | Fixed by using orchestrator (issue 6 fix) + graceful fallback to most recent file if marker not found |
| 8 | README showed nothing | `latest_dialogue.webp` and `latest_map.webp` did not exist | Added `shutil.copy2()` at end of each render in both generators |

---

## 📋 TODO

### 🔴 High Priority

- [ ] **`core_engine.py`** — Earth map processor + visual glitch effects (Phase 3)
- [ ] **Scheduled trigger** — Add `schedule: cron: '0 6 * * *'` to run daily automatically
- [ ] **`AI_REQUEST` env var** — Pass theme/context from workflow to vary dialogue topics per run

### 🟡 Medium Priority

- [ ] **Multi-scenario per CI run** — Set `SCENARIOS_PER_RUN: "3"` in workflow for richer output
- [ ] **GitLab CI mirror** — Add `.gitlab-ci.yml` to mirror the pipeline on GitLab
- [ ] **README auto-refresh badge** — Add `last updated` timestamp badge that reflects actual last run time
- [ ] **earth_glitch maps** — Implement in `core_engine.py` as alternative background type

### 🟢 Low Priority

- [ ] **ASCII garden animation** — Original Phase 0: integrate the terminal-rendered garden drawing
- [ ] **Dialogue themes rotation** — Randomize the `AI_REQUEST` from a predefined theme list each run
- [ ] **Output archiving** — Keep last N runs; prune older files to avoid repo bloat
- [ ] **Artifact upload** — Upload WebP files as GitHub Actions artifacts for download without committing

---

## 🏗️ Architecture Notes

### Why `orchestrator.py` instead of separate workflow steps?

`PIPELINE_RUN_TS` is a timestamp used to match JSON files created by `ai_engine.py` with the
render pass in `dialogue_generator.py`. When called as separate workflow steps, each step runs
in its own shell process. `os.environ["PIPELINE_RUN_TS"] = ts` in `ai_engine.py` only sets the
variable in that process — it disappears when the step ends. `dialogue_generator.py` then sees
an empty `PIPELINE_RUN_TS` and falls back to rendering all historical JSON files.

`orchestrator.py` fixes this by running both engines in the **same Python process**, so the
`os.environ` mutation persists across both function calls.

### Why `git add -f output/`?

`output/` is in `.gitignore` for local development (you don't want generated files cluttering
`git status`). On the CI runner, we want to commit these files to remote. The `-f` flag forces
git to stage files that would otherwise be excluded by `.gitignore`. This is intentional and
correct — it's the standard pattern for "ignore locally, track remotely."

### Why `gh pr create` instead of `peter-evans/create-pull-request@v6`?

The action does its own internal git operations after our manual `git push`. It re-fetches the
branch, compares it against `main`, and if it decides the branch "already matches" main (which
can happen when it rebases internally), it force-resets `auto/generate-assets` back to `main`'s
HEAD — erasing our commit. Using the CLI directly means we have full control over every git
operation and nothing can silently overwrite our work.

### `latest_map.webp` and `latest_dialogue.webp`

GitHub README images are static references. Timestamped files (`alien_sector_F4A1.webp`,
`dialogue_seq_2024...webp`) change names every run, so the README can't reference them by name.
Instead, each generator overwrites a fixed-name file after every successful render. The README
always points to these fixed names, so it automatically shows the newest output without any
README edits needed.

---

## 🔑 Key File Locations

| File | Repo Path |
|------|-----------|
| Workflow | `.github/workflows/Workflow-Output.yml` |
| CI entrypoint | `engines/orchestrator.py` |
| Groq dialogue gen | `engines/ai_engine.py` |
| WebP renderer | `engines/dialogue_generator.py` |
| Map generator | `engines/alien_generator.py` |
| Shared fonts | `engines/_fonts.py` |
| Latest map | `output/maps/latest_map.webp` |
| Latest dialogue | `output/dialogues/latest_dialogue.webp` |
| Easter egg | `assets/captcha.png` |