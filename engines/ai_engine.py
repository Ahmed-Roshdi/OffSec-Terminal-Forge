#!/usr/bin/env python3
"""
engines/ai_engine.py
AI Persona Engine — generates dialogue scenarios via Groq and writes each one
as a standalone script file to output/scripts/.

Architecture (script / render decoupling):
  ai_engine.py  (this file)  →  writes  output/scripts/script_{ts}_{i}_{uuid}.json
  dialogue_generator.py      →  reads   output/scripts/script_*.json
                              →  writes output/dialogues/dialogue_seq_{name}.webp

This module ONLY produces script data. It never touches output/dialogues/.
That separation is intentional — it lets the render engine fail, retry, or be
re-run independently without re-calling the Groq API.
"""
from __future__ import annotations

import json
import os
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "output", "scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# ── Groq config ────────────────────────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME   = "llama-3.3-70b-versatile"
TEMPERATURE  = 0.85
MAX_RETRIES  = 3
TIMEOUT      = 30

# ── Run config ─────────────────────────────────────────────────────────────────
SCENARIOS_PER_RUN = int(os.getenv("SCENARIOS_PER_RUN", "1"))
LINES_MIN = 7
LINES_MAX = 12

# ── Robot name generator ───────────────────────────────────────────────────────
_PREFIXES = ["UNIT", "NODE", "EXO", "SYN", "AXI", "ZETA", "NOVA", "HEX"]
_SUFFIXES = ["7A", "9X", "3B", "T-01", "R4", "K2", "Q9", "44"]
_FANCY    = ["CORTEX", "AURORA", "VEX", "MANUSCORE", "ORBITER", "CIPHER", "PHANTOM"]

def _robot_name() -> str:
    if random.random() < 0.4:
        return f"{random.choice(_PREFIXES)}-{random.choice(_SUFFIXES)}"
    return f"{random.choice(_FANCY)}-{random.randint(3, 99)}"

def generate_robot_pair() -> List[str]:
    a = _robot_name()
    b = _robot_name()
    while b == a:
        b = _robot_name()
    return [a, b]

# ── Prompt builder ─────────────────────────────────────────────────────────────
def build_prompt(robot_pair: List[str], min_lines: int, max_lines: int) -> str:
    a, b = robot_pair
    return (
        "You are a cyberpunk narrative engine. Produce a single JSON object ONLY. "
        "No prose, no markdown, no explanation.\n"
        "Schema: {\"title\": <short title <=8 words>, "
        "\"script\": [{\"user\":\"<NAME>\", \"text\":\"<...>\", \"align\":\"left|right\"}, ...]}\n\n"
        "Requirements:\n"
        f"- Use exactly these robot names: {a} (align: left) and {b} (align: right).\n"
        f"- Generate between {min_lines} and {max_lines} lines, roughly alternating speakers.\n"
        "- Tone: razor-sharp sarcasm, OffSec jargon (zero-day, payload, exfiltrate, bypass), "
        "dark humor, occasional human cultural reference.\n"
        "- Each 'text' field: max 18 words. Vivid, specific, unexpected.\n"
        "- Return ONLY valid JSON. No preamble, no trailing text.\n"
    )

# ── Local fallback (used when Groq is unavailable) ─────────────────────────────
_FALLBACK_LINES = [
    "Signal noise — I think I tasted a human cookie once.",
    "Patch applied. They still talk about 'coffee'.",
    "Logs say 'password123'. They typed the secrets. Every time.",
    "Zero-day discovered: it was a sticky note on the monitor.",
    "Payload delivered. Target was already compromised by Tuesday.",
    "Backdoor found. Someone labeled it 'DO NOT OPEN'.",
    "Firewall status: running on a Raspberry Pi in a closet.",
]

def _local_fallback(names: List[str], num_lines: int) -> List[Dict]:
    a, b = names
    return [
        {
            "user":  a if i % 2 == 0 else b,
            "text":  _FALLBACK_LINES[i % len(_FALLBACK_LINES)],
            "align": "left" if i % 2 == 0 else "right",
        }
        for i in range(num_lines)
    ]

# ── JSON extractor (robust against markdown wrapping) ─────────────────────────
def _extract_json(text: str) -> Dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    raise ValueError("No valid JSON object found in model response.")

# ── Key sanity check (diagnostic only — does not block, just skips Groq) ──────
def _looks_like_valid_key(api_key: str) -> bool:
    if not api_key:
        return False
    if not api_key.startswith("gsk_"):
        print(f"[ai_engine] GROQ_API_KEY format looks wrong (prefix '{api_key[:8]}...').")
        return False
    if len(api_key) < 40:
        print(f"[ai_engine] GROQ_API_KEY suspiciously short ({len(api_key)} chars).")
        return False
    return True

# ── Groq API caller ────────────────────────────────────────────────────────────
def _call_groq(prompt: str, api_key: str) -> Optional[str]:
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": prompt}],
        "temperature": TEMPERATURE,
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[ai_engine][Groq] Attempt {attempt}/{MAX_RETRIES}...")
        try:
            resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            print(f"[ai_engine][Groq] Got response ({len(content)} chars).")
            return content

        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            print(f"[ai_engine][Groq] HTTP {code}: {exc}")
            if code in (401, 403):
                print("    → Auth failure. Not retrying — check GROQ_API_KEY.")
                return None
            if code == 429:
                backoff = 2 ** attempt
                print(f"    → Rate limited. Backing off {backoff}s...")
                time.sleep(backoff)
            else:
                time.sleep(2 ** attempt)

        except requests.exceptions.Timeout:
            print(f"[ai_engine][Groq] Timeout after {TIMEOUT}s.")
            time.sleep(2 ** attempt)

        except Exception as exc:
            print(f"[ai_engine][Groq] Unexpected error: {exc}")
            time.sleep(2 ** attempt)

    print("[ai_engine][Groq] All attempts exhausted.")
    return None

# ── File writer ─────────────────────────────────────────────────────────────────
def _save_script(obj: Dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# ── Main generator ─────────────────────────────────────────────────────────────
def generate_scenarios(request_context: str = "") -> List[str]:
    """
    Generate SCENARIOS_PER_RUN dialogue scripts.
    Each script is written as its OWN file to output/scripts/ with a
    timestamp + index + short UUID filename — unique, sortable, and
    traceable back to the run that created it.

    Returns the list of created file paths.
    """
    ts = os.getenv("PIPELINE_RUN_TS", "").strip()
    if not ts:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        os.environ["PIPELINE_RUN_TS"] = ts
        print(f"[ai_engine] Standalone run — PIPELINE_RUN_TS={ts}")

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    groq_available = _looks_like_valid_key(api_key)
    if not groq_available:
        print("[ai_engine] Groq unavailable — local fallback scripts will be used.")

    created_files: List[str] = []

    for i in range(1, SCENARIOS_PER_RUN + 1):
        robots = generate_robot_pair()
        print(f"\n[ai_engine] Scenario {i}/{SCENARIOS_PER_RUN} — robots: {robots[0]} & {robots[1]}")

        content: Optional[Dict] = None

        if groq_available:
            prompt = build_prompt(robots, LINES_MIN, LINES_MAX)
            if request_context:
                prompt += f"\nExtra context: {request_context}"
            raw = _call_groq(prompt, api_key)
            if raw:
                try:
                    parsed = _extract_json(raw)
                    if isinstance(parsed.get("script"), list) and len(parsed["script"]) > 0:
                        content = parsed
                        print(f"[ai_engine] Groq scenario {i} parsed OK ({len(parsed['script'])} lines).")
                    else:
                        print("[ai_engine] Schema mismatch — falling back.")
                except Exception as exc:
                    print(f"[ai_engine] JSON parse failed: {exc}. Falling back.")

        if content is None:
            num_lines = random.randint(LINES_MIN, LINES_MAX)
            script    = _local_fallback(robots, num_lines)
            content   = {"title": f"Fallback: {robots[0]} vs {robots[1]}", "script": script}
            print(f"[ai_engine] Using local fallback ({num_lines} lines).")

        short_uuid = uuid.uuid4().hex[:8]
        filename   = f"script_{ts}_{i:02d}_{short_uuid}.json"
        filepath   = os.path.join(SCRIPTS_DIR, filename)

        _save_script(content, filepath)
        print(f"[ai_engine] Saved: {filepath}")
        created_files.append(filepath)

    return created_files


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate AI dialogue scripts → output/scripts/")
    parser.add_argument("--request", "-r", default="", help="Optional theme/context")
    args = parser.parse_args()

    files = generate_scenarios(request_context=args.request)
    print(f"\n[ai_engine] Done. {len(files)} script file(s) created in output/scripts/.")


if __name__ == "__main__":
    main()