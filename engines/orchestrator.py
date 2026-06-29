#!/usr/bin/env python3
"""
Single pipeline entrypoint for local dev and GitHub Actions.

Execution order (decoupled layers):
  1. core_engine   — earth base map + glitch effects → output/maps/
  2. alien_generator — procedural alien worlds       → output/maps/
  3. ai_engine     — Groq JSON dialogues             → output/dialogues/
  4. dialogue_generator — WebP HUD sequences         → output/dialogues/
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone

ENGINES_DIR = os.path.dirname(os.path.abspath(__file__))
if ENGINES_DIR not in sys.path:
    sys.path.insert(0, ENGINES_DIR)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        print(f"[!] Invalid {name}={raw!r}, using {default}")
        return default


def run_pipeline() -> None:
    maps_per_run = _env_int("MAPS_PER_RUN", 1)
    scenarios = _env_int("SCENARIOS_PER_RUN", 1 if os.getenv("CI") else 3)
    os.environ.setdefault("SCENARIOS_PER_RUN", str(scenarios))
    os.environ.setdefault(
        "PIPELINE_RUN_TS",
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    )

    print("=" * 60)
    print("[orchestrator] OffSec-Terminal-Forge pipeline starting")
    print(f"[orchestrator] MAPS_PER_RUN={maps_per_run}  SCENARIOS_PER_RUN={scenarios}")
    print("=" * 60)

    # ── 1. Earth map + glitch ─────────────────────────────────────────────
    print("\n[orchestrator] Step 1/4 — core_engine (earth map + glitch)")
    import core_engine

    core_engine.generate_glitch_map()

    # ── 2. Alien procedural maps ────────────────────────────────────────────
    print(f"\n[orchestrator] Step 2/4 — alien_generator ({maps_per_run} map(s))")
    import alien_generator

    for i in range(maps_per_run):
        alien_generator.generate_alien_world()
        if i < maps_per_run - 1:
            time.sleep(0.05)

    # ── 3. AI dialogue JSON ─────────────────────────────────────────────────
    print("\n[orchestrator] Step 3/4 — ai_engine (dialogue JSON)")
    if not os.getenv("GROQ_API_KEY", "").strip():
        print("[!] GROQ_API_KEY not set — ai_engine will use local fallback scripts.")

    import ai_engine

    request = os.getenv("AI_REQUEST", "").strip()
    ai_engine.generate_scenarios(request_context=request)

    # ── 4. Render WebP sequences ────────────────────────────────────────────
    print("\n[orchestrator] Step 4/4 — dialogue_generator (WebP HUD)")
    import dialogue_generator

    dialogue_generator.main()

    print("\n" + "=" * 60)
    print("[orchestrator] Pipeline complete.")
    print("=" * 60)


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
