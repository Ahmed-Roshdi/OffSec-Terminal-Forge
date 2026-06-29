#!/usr/bin/env python3
"""
engines/ai_engine.py
Generates N dialogue scenarios per run (JSON + plain .txt) for dialogue_generator.py.

Output files written to output/dialogues/:
  ai_dialogue_raw_{timestamp}_{i}.json
  ai_dialogue_raw_{timestamp}_{i}.txt

Pipeline integration:
  - orchestrator.py sets PIPELINE_RUN_TS before calling this module.
  - Both this module and dialogue_generator.py share PIPELINE_RUN_TS to
    ensure dialogue_generator only renders the JSONs created in THIS run.
"""
from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "dialogues")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Groq config ────────────────────────────────────────────────────────────────
GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME    = "llama-3.3-70b-versatile"
TEMPERATURE   = 0.85
MAX_RETRIES   = 3
TIMEOUT       = 30

# ── Run config ─────────────────────────────────────────────────────────────────
SCENARIOS_PER_RUN = int(os.getenv("SCENARIOS_PER_RUN", "3"))
LINES_MIN         = 7
LINES_MAX         = 12

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
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first complete JSON object
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    raise ValueError("No valid JSON object found in model response.")

# ── API key validation ─────────────────────────────────────────────────────────
def _validate_key(api_key: str) -> bool:
    """Basic sanity checks before hitting the API."""
    if not api_key:
        print("[!] GROQ_API_KEY is empty.")
        return False
    if not api_key.startswith("gsk_"):
        print(f"[!] GROQ_API_KEY wrong format — got prefix '{api_key[:8]}...', expected 'gsk_'.")
        print("    → Regenerate at https://console.groq.com/keys")
        return False
    if len(api_key) < 40:
        print(f"[!] GROQ_API_KEY suspiciously short ({len(api_key)} chars). Likely truncated.")
        return False
    return True

# ── Groq API caller ────────────────────────────────────────────────────────────
def _call_groq(prompt: str, api_key: str) -> Optional[str]:
    payload = {
        "model":    MODEL_NAME,
        "messages": [{"role": "system", "content": prompt}],
        "temperature": TEMPERATURE,
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[Groq] Attempt {attempt}/{MAX_RETRIES}...")
        try:
            resp = requests.post(
                GROQ_API_URL, json=payload, headers=headers, timeout=TIMEOUT
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            print(f"[Groq] Got response ({len(content)} chars).")
            return content

        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            print(f"[Groq] HTTP {code}: {exc}")
            if code == 401:
                print("    → Key is INVALID. Regenerate at https://console.groq.com/keys")
                return None   # no point retrying auth failure
            if code == 403:
                print("    → Key REVOKED or quota EXCEEDED.")
                print("    → Check status: https://console.groq.com/keys")
                print("    → Free tier: 500K tokens/day, 14.4K tokens/min")
                return None   # no point retrying a 403
            if code == 429:
                backoff = 2 ** attempt
                print(f"    → Rate limited. Backing off {backoff}s...")
                time.sleep(backoff)
            else:
                time.sleep(2 ** attempt)

        except requests.exceptions.Timeout:
            print(f"[Groq] Timeout after {TIMEOUT}s.")
            time.sleep(2 ** attempt)

        except Exception as exc:
            print(f"[Groq] Unexpected error: {exc}")
            time.sleep(2 ** attempt)

    print("[Groq] All attempts exhausted.")
    return None

# ── File writers ───────────────────────────────────────────────────────────────
def _save_json(obj: Dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _save_txt(script: List[Dict], path: str) -> None:
    """Plain text: one line per message in 'NAME|align|text' format."""
    with open(path, "w", encoding="utf-8") as f:
        for msg in script:
            f.write(f"{msg['user']}|{msg.get('align', 'left')}|{msg['text']}\n")

# ── Main generator ─────────────────────────────────────────────────────────────
def generate_scenarios(request_context: str = "") -> List[str]:
    """
    Generate SCENARIOS_PER_RUN dialogue scenarios.
    Returns list of created JSON file paths.
    """
    # PIPELINE_RUN_TS is set by orchestrator.py before this function is called.
    # If running standalone, set it here so dialogue_generator can match files.
    ts = os.getenv("PIPELINE_RUN_TS", "").strip()
    if not ts:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        os.environ["PIPELINE_RUN_TS"] = ts
        print(f"[ai_engine] Standalone run — PIPELINE_RUN_TS={ts}")

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    groq_available = _validate_key(api_key)
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

        base      = f"ai_dialogue_raw_{ts}_{i}"
        json_path = os.path.join(OUTPUT_DIR, base + ".json")
        txt_path  = os.path.join(OUTPUT_DIR, base + ".txt")

        _save_json(content, json_path)
        _save_txt(content["script"], txt_path)
        print(f"[ai_engine] Saved: {json_path}")
        created_files.append(json_path)

    return created_files


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate AI dialogue scenarios (JSON + TXT)")
    parser.add_argument("--request", "-r", default="", help="Optional theme/context")
    args = parser.parse_args()

    files = generate_scenarios(request_context=args.request)
    print(f"\n[ai_engine] Done. {len(files)} scenario file(s) created.")


if __name__ == "__main__":
    main()