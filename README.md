# OffSec-Terminal-Forge

[![Workflow-Output](https://github.com/Ahmed-Roshdi/OffSec-Terminal-Forge/actions/workflows/Workflow-Output.yml/badge.svg?event=workflow_dispatch)](https://github.com/Ahmed-Roshdi/OffSec-Terminal-Forge/actions/workflows/Workflow-Output.yml)

Autonomous Python generation engine for Cyberpunk / Offensive Security-themed visual and narrative assets: AI-driven dialogues and animated WebP terminal HUD sequences.

## Architecture (active pipeline)

| Layer | Module | Output |
|---|---|---|
| Narrative (Groq) | `engines/ai_engine.py` | `output/dialogues/ai_dialogue_raw_*.json` |
| Presentation | `engines/dialogue_generator.py` | `output/dialogues/dialogue_seq_*.webp` |

Data generation (Groq API) is decoupled from rendering (Pillow). GitHub Actions runs **ai_engine → dialogue_generator** only.

Other engines (`alien_generator`, `core_engine`) exist separately and are not part of the CI workflow.

## Run locally

```bash
pip install -r requirements.txt
export GROQ_API_KEY="your-key"   # optional — local fallback scripts used if unset
python engines/orchestrator.py     # or run ai_engine + dialogue_generator individually
```

Environment variables:

| Variable | Default (local) | CI default |
|---|---|---|
| `SCENARIOS_PER_RUN` | `3` | `1` |
| `GROQ_API_KEY` | — | GitHub secret |
| `AI_REQUEST` | — | set in workflow |

Individual steps:

```bash
python engines/ai_engine.py
python engines/dialogue_generator.py
```

## GitHub Actions

Workflow: `.github/workflows/Workflow-Output.yml`

1. Installs Python 3.11, Ubuntu Mono fonts, and dependencies
2. Runs `ai_engine.py` then `dialogue_generator.py`
3. Force-stages `output/` and opens PR from `auto/generate-assets` → `main`

Required secrets (environment `Dialogue_Generator-AI`):

- `GROQ_API_KEY` — Groq API (llama-3.3-70b-versatile)
- `GH_PAT` — PAT with repo + PR permissions for push/merge

Trigger manually: **Actions → Workflow-Output (AI Generator) → Run workflow**
