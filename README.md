<div align="center">

# 🤖 OffSec Terminal Forge

**A self-updating cyberpunk terminal — AI-generated alien worlds, Islamic world map animations,
ASCII sanctuary art, and security dialogues, rebuilt automatically on every workflow run.**

[![Master Workflow](https://github.com/Ahmed-Roshdi/OffSec-Terminal-Forge/actions/workflows/Master-Workflow.yml/badge.svg)](https://github.com/Ahmed-Roshdi/OffSec-Terminal-Forge/actions/workflows/Master-Workflow.yml)
![Last Commit](https://img.shields.io/github/last-commit/Ahmed-Roshdi/OffSec-Terminal-Forge/Output?color=00ffff&label=Output%20branch)
![Model](https://img.shields.io/badge/AI-Groq%20%7C%20Llama%203.3%2070B-8a2be2)

</div>

---

## 🌌 Latest Alien Sector Map

<div align="center">
<img src="https://raw.githubusercontent.com/Ahmed-Roshdi/OffSec-Terminal-Forge/Output/output/maps/latest_map.webp" width="860" alt="Latest Alien Sector Map" />
</div>

---

## 💬 Latest AI Dialogue Sequence

<div align="center">
<img src="https://raw.githubusercontent.com/Ahmed-Roshdi/OffSec-Terminal-Forge/Output/output/dialogues/latest_dialogue.webp" width="860" alt="Latest AI Dialogue" />
</div>

---

## 🗺️ Latest Islamic World Map (Glitch)

<div align="center">
<img src="https://raw.githubusercontent.com/Ahmed-Roshdi/OffSec-Terminal-Forge/Output/output/maps/latest_glitch.webp" width="860" alt="Islamic World Map Glitch" />
</div>

---

## 📐 Visual Benchmark — Gold Standard

The file `output/Old-Standerd-Of-Final-Output/magic_readme.webp` is the
**definitive visual reference** for this project. All rendering engines are
validated against it.

### Programmatic Analysis Results

The following parameters were extracted by running a pixel-level analysis
script on `magic_readme.webp`:

| Parameter | Value | Hex |
|-----------|-------|-----|
| Canvas size | 2428 × 1136 px | — |
| Total frames | 66 (animated WebP) | — |
| Background RGB | (13, 17, 23) | `#0d1117` |
| Gray text RGB | (139, 148, 158) | `#8b949e` |
| Green accent RGB | (39, 174, 96) | `#27ae60` |
| OffSec cyan RGB | (0, 212, 255) | `#00d4ff` |
| OffSec purple RGB | (140, 30, 255) | `#8c1eff` |
| Glitch red RGB | (231, 76, 60) | `#e74c3c` |
| Background coverage | 91.0% of pixels | — |
| Foreground coverage | 9.0% of pixels | — |

### Critical Finding — Previous Glitch Implementation Was Incorrect

> **⚠️ The glitch effect previously implemented by Claude in `core_engine.py`
> (RGB channel pixel splitting, numpy scanlines, pixel-sort by HSV) was
> architecturally wrong and does not exist in the gold standard output.**

The CORRECT glitch effect, as extracted from the original construction code, is:

```python
# CORRECT: 15 px horizontal x-offset on the red dot layer only
def render_glitch_map(circles, offset_x=15):
    for c in circles:
        c['cx'] += offset_x        # shift x coordinate only
    # render red (231, 76, 60) dots — no pixel manipulation
```

There is no per-pixel operation. No numpy. No channel splitting. No scanlines.
The effect is a simple coordinate offset applied before drawing SVG circles.

---

## 🧠 How It Works

```
Master-Workflow.yml (schedule 3×/day or workflow_dispatch)
  │
  ├── analyze-state    → count assets on Output branch → decide what runs
  │
  ├── generate-maps    → alien_generator.py   → output/maps/
  ├── generate-scripts → ai_engine.py         → output/scripts/
  ├── render-dialogues → dialogue_generator.py→ output/dialogues/
  ├── compile-core     → core_engine.py       → output/maps/ (glitch)
  └── generate-ascii   → ascii_generator.py   → output/ascii/
        │
        └── ALL outputs committed exclusively to → Output branch
```

> **GitOps rule:** `main` branch is never touched by automated commits.
> All generated assets live on the `Output` branch.

---

## 🏗️ Repository Structure

```
OffSec-Terminal-Forge/
├── .github/workflows/
│   ├── Master-Workflow.yml          # State controller — schedules child workflows
│   ├── Alien-Maps-Generator.yml     # workflow_call — fractal dot maps
│   ├── AI-Engine-Workflow.yml       # workflow_call — Groq dialogue scripts
│   ├── Orchestrator.yml             # workflow_call — WebP dialogue render
│   ├── Core_Engine_The-Compilor.yml # workflow_call — SVG Islamic map glitch
│   ├── ACSII-Art-Generator.yml      # workflow_call — ASCII sanctuary art
│   ├── Debug-Control.yml            # tmate SSH reverse shell for live debug
│   └── auto_doc_updater.yml         # AI-powered README + DEVELOP updater
├── engines/
│   ├── orchestrator.py              # Local entrypoint: ai_engine → dialogue
│   ├── ai_engine.py                 # Groq API → output/scripts/script_*.json
│   ├── dialogue_generator.py        # JSON scripts → animated WebP HUD
│   ├── alien_generator.py           # Fractal noise → dot-matrix alien maps
│   ├── core_engine.py               # SVG parse → Islamic map + glitch effect
│   ├── ascii_generator.py           # ASCII.txt → output/ascii/*.txt
│   ├── doc_updater.py               # OpenRouter → README.md + DEVELOP.md
│   └── _fonts.py                    # Shared font resolution
├── assets/
│   ├── ASCII.txt                    # Sacred garden sanctuary ASCII art
│   ├── islamic_world_map.svg        # Base SVG for core_engine
│   ├── captcha.png                  # reCAPTCHA easter egg (closing frame)
│   └── fonts/                       # UbuntuMono TTF
├── output/                          # gitignored locally — lives on Output branch
│   ├── maps/                        # alien_sector_*.webp + latest_map.webp
│   │                                  glitched_map_*.webp + latest_glitch.webp
│   ├── scripts/                     # script_{ts}_{i}_{uuid}.json
│   ├── dialogues/                   # dialogue_seq_*.webp + latest_dialogue.webp
│   └── ascii/                       # ascii_art_*.txt + latest_ascii.txt
├── output/Old-Standerd-Of-Final-Output/
│   └── magic_readme.webp            # ← GOLD STANDARD — do not modify
├── requirements.txt                 # Pillow, requests, numpy
├── PROJECT_MEMORY.md                # Architecture context for AI doc updater
├── README.md                        # This file
└── DEVELOP.md                       # Contributor technical guide
```

---

## ⚙️ Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Dialogue | Groq API — Llama 3.3 70B Versatile |
| Image Engine | Python Pillow (PIL) 12.x |
| Map Parser | Python `re` on SVG `<circle>` elements |
| Terrain Gen | Fractal Brownian Motion (fBm) |
| Output Format | Animated WebP (lossless, 100% quality) |
| CI/CD | GitHub Actions — ubuntu-latest |
| Branch Strategy | `main` (code) + `Output` (generated assets) |

---

## 🔒 Secrets Required

| Secret | Environment | Purpose |
|--------|-------------|---------|
<<<<<<< HEAD
| `` | `Dialogue_Generator-AI` | Llama 3.3 70B via Groq |
| `` | `Dialogue_Generator-AI` | Push branches + auto-merge PRs |
=======
| `GROQ_API_KEY` | `Dialogue_Generator-AI` | Llama 3.3 70B via Groq |
| `GH_PAT` | `Dialogue_Generator-AI` | Push to Output branch |
| `AI_Auto_Projrct_Information_Updater` | repo-level | OpenRouter doc generation |
>>>>>>> b01ba6b (autosave: local changes before sync (2026-06-29T01:14:03Z))

---

<div align="center">

*Runs on schedule. Commits to Output. main stays clean.*

</div>