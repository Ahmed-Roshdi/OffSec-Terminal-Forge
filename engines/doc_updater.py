#!/usr/bin/env python3
"""
engines/doc_updater.py
AI-powered documentation generator.

Reads PROJECT_MEMORY.md for architecture context, then calls OpenRouter
to generate/overwrite README.md and DEVELOP.md with current, accurate content.

Secret required: AI_Auto_Projrct_Information_Updater (OpenRouter API key)
"""
import os
import sys
import requests

# ── sys.path guard ──────────────────────────────────────────────────────────
_ENGINES_DIR = os.path.dirname(os.path.abspath(__file__))
if _ENGINES_DIR not in sys.path:
    sys.path.insert(0, _ENGINES_DIR)

# ── Config ───────────────────────────────────────────────────────────────────
API_KEY  = os.getenv("AI_Auto_Projrct_Information_Updater", "").strip()
API_URL  = "https://openrouter.ai/api/v1/chat/completions"
MODEL    = "meta-llama/llama-3.3-70b-instruct"
TIMEOUT  = 60

MEMORY_PATH = "PROJECT_MEMORY.md"

# ── Docs to generate ─────────────────────────────────────────────────────────
DOCS = [
    {
        "output": "README.md",
        "prompt": (
            "Write a comprehensive, professional README.md for this project. "
            "Include: project overview, live animated preview section "
            "(reference output/maps/latest_map.webp and "
            "output/dialogues/latest_dialogue.webp as inline images), "
            "architecture diagram, CI/CD pipeline description, "
            "secrets/environment setup, and usage instructions. "
            "Maintain a Cyberpunk/OffSec aesthetic in tone and style. "
            "Use GitHub-flavoured Markdown."
        ),
    },
    {
        "output": "DEVELOP.md",
        "prompt": (
            "Write a highly technical DEVELOP.md contributor guide. "
            "Cover: repo file structure, full function call chains for each engine "
            "(alien_generator, ai_engine, dialogue_generator, core_engine, "
            "ascii_generator, orchestrator, doc_updater), "
            "how to add a new engine, how the microservices YAML workflows "
            "call each other via workflow_call, "
            "the output directory conventions "
            "(output/maps/, output/scripts/, output/dialogues/, output/ascii/), "
            "and the latest_*.* fixed-name convention used by README. "
            "Be precise and technical. No marketing language."
        ),
    },
]


def _call_api(system_msg: str, user_msg: str) -> str:
    if not API_KEY:
        print("[!] AI_Auto_Projrct_Information_Updater is not set.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as exc:
        print(f"[!] API HTTP error {exc.response.status_code}: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"[!] API request failed: {exc}")
        sys.exit(1)


def main() -> None:
    if not os.path.exists(MEMORY_PATH):
        print(f"[!] {MEMORY_PATH} not found. Cannot generate docs without context.")
        sys.exit(1)

    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        context = f.read()

    system_msg = (
        "You are an elite Systems Architect and Technical Writer. "
        "Output ONLY valid GitHub-Flavoured Markdown. "
        "Do not include conversational filler, preamble, or code fences "
        "around the outer document."
    )

    for doc in DOCS:
        print(f"[*] Generating {doc['output']}...")
        user_msg = (
            f"{doc['prompt']}\n\n"
            f"### PROJECT ARCHITECTURE CONTEXT:\n{context}"
        )
        content = _call_api(system_msg, user_msg)

        with open(doc["output"], "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] {doc['output']} written ({len(content)} chars).")

    print("[+] Documentation generation complete.")


if __name__ == "__main__":
    main()