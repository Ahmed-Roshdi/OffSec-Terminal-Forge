#!/usr/bin/env python3
"""
CI/local entrypoint for the AI dialogue pipeline only.

Execution order:
  1. ai_engine          — Groq JSON dialogues  → output/dialogues/
  2. dialogue_generator — WebP HUD sequences   → output/dialogues/
"""
from __future__ import annotations

import os
import sys
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
    scenarios = _env_int("SCENARIOS_PER_RUN", 1 if os.getenv("CI") else 3)
    os.environ.setdefault("SCENARIOS_PER_RUN", str(scenarios))
    os.environ.setdefault(
        "PIPELINE_RUN_TS",
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    )

    print("=" * 60)
    print("[orchestrator] AI dialogue pipeline starting")
    print(f"[orchestrator] SCENARIOS_PER_RUN={scenarios}")
    print("=" * 60)

    print("\n[orchestrator] Step 1/2 — ai_engine (dialogue JSON)")
    if not os.getenv("GROQ_API_KEY", "").strip():
        print("[!] GROQ_API_KEY not set — ai_engine will use local fallback scripts.")

    import ai_engine

    request = os.getenv("AI_REQUEST", "").strip()
    ai_engine.generate_scenarios(request_context=request)

    print("\n[orchestrator] Step 2/2 — dialogue_generator (WebP HUD)")
    import dialogue_generator

    dialogue_generator.main()

    print("\n" + "=" * 60)
    print("[orchestrator] Pipeline complete.")
    print("=" * 60)


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
