<div align="center">

# 🤖 OffSec-Terminal-Forge

**A self-updating cyberpunk terminal — AI-generated alien worlds and security dialogues,
rebuilt automatically on every workflow run.**

[![Workflow](https://github.com/Ahmed-Roshdi/OffSec-Terminal-Forge/actions/workflows/Workflow-Output.yml/badge.svg)](https://github.com/Ahmed-Roshdi/OffSec-Terminal-Forge/actions/workflows/Workflow-Output.yml)
![Last Commit](https://img.shields.io/github/last-commit/Ahmed-Roshdi/OffSec-Terminal-Forge?color=00ffff)
![Language](https://img.shields.io/badge/language-Python%203.11-blue?logo=python)
![Model](https://img.shields.io/badge/AI-Groq%20%7C%20Llama%203.3%2070B-8a2be2)

</div>

---

## 🌌 Latest Alien Sector Map

<div align="center">
<img src="output/maps/latest_map.webp" width="860" alt="Latest Alien Sector Map" />
</div>

---

## 💬 Latest AI Dialogue Sequence

<div align="center">
<img src="output/dialogues/latest_dialogue.webp" width="860" alt="Latest AI Dialogue" />
</div>

> *Each frame is a new AI-generated exchange. The sequence loops.*

---

## 🧠 How It Works

```
workflow_dispatch
      │
      ▼
alien_generator.py  ──►  output/maps/alien_sector_XXXX.webp
                                     latest_map.webp
      │
      ▼
orchestrator.py
      │
      ├──► ai_engine.py  ──────────►  Groq API (Llama 3.3 70B)
      │         │                          │
      │         ▼                          ▼
      │    ai_dialogue_raw_{ts}.json  (fallback if API down)
      │
      └──► dialogue_generator.py ──►  dialogue_seq_{ts}.webp
                                       latest_dialogue.webp
      │
      ▼
GitHub Actions PR  ──►  auto-merge into main  ──►  README updates live
```

### Pipeline Steps

| # | Engine | Does |
|---|--------|------|
| 1 | `alien_generator.py` | Fractal noise → dot-matrix alien world map |
| 2 | `ai_engine.py` | Calls Groq API → JSON dialogue script |
| 3 | `dialogue_generator.py` | JSON → animated WebP HUD with avatar circles |
| 4 | `Workflow-Output.yml` | Commits output, opens PR, auto-merges to `main` |

---

## 🏗️ Repository Structure

```
OffSec-Terminal-Forge/
├── .github/workflows/
│   └── Workflow-Output.yml       # Zero-touch CI/CD pipeline
├── engines/
│   ├── orchestrator.py           # CI entrypoint: runs ai_engine → dialogue_generator
│   ├── ai_engine.py              # Groq API → dialogue JSON scripts
│   ├── dialogue_generator.py     # JSON scripts → animated WebP HUD sequences
│   ├── alien_generator.py        # Fractal terrain → dot-matrix maps
│   ├── core_engine.py            # [PENDING] Earth map glitch processor
│   └── _fonts.py                 # Shared font resolution (runner + local)
├── output/
│   ├── maps/
│   │   ├── alien_sector_*.webp   # Generated maps (one per run)
│   │   └── latest_map.webp       # ← README reads this
│   └── dialogues/
│       ├── dialogue_seq_*.webp   # Generated sequences (one per run)
│       └── latest_dialogue.webp  # ← README reads this
└── assets/
    ├── fonts/                    # UbuntuMono (monospace terminal font)
    └── captcha.png               # Easter egg — closing frame of every sequence
```

---

## ⚙️ Tech Stack

| Component       | Technology                        |
|-----------------|-----------------------------------|
| AI Model        | Groq API — Llama 3.3 70B Versatile |
| Fallback        | Local procedural dialogue generator |
| Image Engine    | Python Pillow (PIL) 12.x          |
| Terrain         | Fractal Brownian Motion (fBm)     |
| Output Format   | Animated WebP (lossless)          |
| CI/CD           | GitHub Actions — ubuntu-latest    |
| Auto-merge      | `gh pr merge --admin`             |

---

## 🔒 Secrets Required

| Secret | Environment | Purpose |
|--------|-------------|---------|
| `GROQ_API_KEY` | `Dialogue_Generator-AI` | Llama 3.3 70B via Groq |
| `GH_PAT` | `Dialogue_Generator-AI` | Push branches + auto-merge PRs |

---

<div align="center">

*Runs on every `workflow_dispatch`. No humans required.*

</div>