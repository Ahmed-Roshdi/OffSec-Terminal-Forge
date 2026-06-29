# OffSec-Terminal-Forge

[![Workflow-Output](https://github.com/Ahmed-Roshdi/OffSec-Terminal-Forge/actions/workflows/Workflow-Output.yml/badge.svg?event=workflow_dispatch)](https://github.com/Ahmed-Roshdi/OffSec-Terminal-Forge/actions/workflows/Workflow-Output.yml)

Autonomous Python generation engine for Cyberpunk / Offensive Security-themed visual and narrative assets: procedural maps, AI-driven dialogues, and animated WebP terminal HUD sequences.

## Architecture

| Layer | Module | Output |
|---|---|---|
| Earth + glitch | `engines/core_engine.py` | `output/maps/earth_glitch_*.webp` |
| Procedural worlds | `engines/alien_generator.py` | `output/maps/alien_sector_*.webp` |
| Narrative (Groq) | `engines/ai_engine.py` | `output/dialogues/ai_dialogue_raw_*.json` |
| Presentation | `engines/dialogue_generator.py` | `output/dialogues/dialogue_seq_*.webp` |

Data generation (AI / math) is decoupled from rendering (Pillow). GitHub Actions runs the full pipeline via a single entrypoint.

## Run locally

```bash
pip install -r requirements.txt
export GROQ_API_KEY="your-key"   # optional — local fallback scripts used if unset
python engines/orchestrator.py
```

Environment variables:

| Variable | Default (local) | CI default |
|---|---|---|
| `MAPS_PER_RUN` | `1` | `1` |
| `SCENARIOS_PER_RUN` | `3` | `1` |
| `GROQ_API_KEY` | — | GitHub secret |
| `AI_REQUEST` | — | set in workflow |
| `BASE_MAP` | `assets/map.png` | `assets/map.png` |

Individual engines can still be run standalone:

```bash
python engines/core_engine.py
python engines/alien_generator.py
python engines/ai_engine.py
python engines/dialogue_generator.py
```

## GitHub Actions

Workflow: `.github/workflows/Workflow-Output.yml`

1. Installs Python 3.11, Ubuntu Mono fonts, and dependencies
2. Runs `python engines/orchestrator.py`
3. Force-stages `output/` (bypasses local `.gitignore`)
4. Opens PR from `auto/generate-assets` → `main` and auto-merges

Required secrets (environment `Dialogue_Generator-AI`):

- `GROQ_API_KEY` — Groq API (llama-3.3-70b-versatile)
- `GH_PAT` — PAT with repo + PR permissions for push/merge

Trigger manually: **Actions → Workflow-Output (AI Generator) → Run workflow**
