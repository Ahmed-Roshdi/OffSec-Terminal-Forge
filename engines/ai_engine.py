#!/usr/bin/env python3
"""
engines/ai_engine.py
Generate N dialogue scenarios per run (JSON + plain .txt) for dialogue_generator.py
Writes files to output/dialogues/:
 - ai_dialogue_raw_{timestamp}_{i}.json
 - ai_dialogue_{timestamp}_{i}.txt

Behavior:
 - Builds a richer prompt (longer, sarcastic+realistic tone)
 - Generates variable robot names locally and passes them in the prompt (so model uses them)
 - Retries Groq, robustly extracts JSON; falls back to local generator if needed
"""
from __future__ import annotations
import os
import json
import time
import random
import requests
from datetime import datetime
from typing import List, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "dialogues")
os.makedirs(OUTPUT_DIR, exist_ok=True)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"

# Configurable generation params
SCENARIOS_PER_RUN = 3
LINES_MIN = 7
LINES_MAX = 12
TEMPERATURE = 0.85
MAX_RETRIES = 3
TIMEOUT = 30

# Local fallback generator (if API fails)
def local_fallback_script(names: List[str], num_lines: int) -> List[Dict]:
    a, b = names
    lines = []
    for i in range(num_lines):
        speaker = a if i % 2 == 0 else b
        text = {
            0: f"{speaker}: Signal noise—I think I tasted a human cookie once.",
            1: f"{speaker}: Patch applied. They still talk about 'coffee'.",
            2: f"{speaker}: Logs say 'password'—they typed the secrets.",
        }[i % 3]
        align = "left" if speaker == a else "right"
        lines.append({"user": speaker, "text": text, "align": align})
    return lines

# Robot name generator (local, to pass into the prompt)
PREFIXES = ["UNIT", "NODE", "EXO", "SYN", "AXI", "ZETA", "NOVA", "HEX"]
SUFFIXES = ["7A", "9X", "3B", "T-01", "R4", "K2", "Q9", "44"]

def generate_robot_pair() -> List[str]:
    # create two distinct robot names, random style (short or fanciful)
    def name():
        if random.random() < 0.4:
            return f"{random.choice(PREFIXES)}-{random.choice(SUFFIXES)}"
        else:
            return random.choice(["CORTEX", "AURORA", "VEX", "MANUSCORE", "ORBITER"]) + f"-{random.randint(3,99)}"
    a = name()
    b = name()
    while b == a:
        b = name()
    return [a, b]

def build_prompt(robot_pair: List[str], min_lines: int, max_lines: int) -> str:
    a, b = robot_pair
    return (
        "You are a cyberpunk narrative engine. Produce a single JSON object ONLY. No prose, no markdown.\n"
        "Schema: { \"title\": <short title>, \"script\": [ {\"user\":\"<NAME>\", \"text\":\"<...>\", \"align\":\"left|right\"}, ... ] }\n"
        "Requirements:\n"
        f"- Use exactly the robot names: {a} (left) and {b} (right). Do NOT invent other names.\n"
        f"- Generate between {min_lines} and {max_lines} lines, alternating speakers roughly, starting with either.\n"
        "- Tone: razor-sharp sarcasm, realistic technical details (OffSec jargon), occasionally surprising human cultural reference.\n"
        "- Keep each 'text' max ~18 words. Prefer vivid metaphors, dark humor, and realistic bug/ops references.\n"
        "- Return only valid JSON. No explanation. Include a short 'title' field (<=8 words).\n"
        "Example element: {\"user\":\"UNIT-7A\",\"text\":\"I found their password file in a tea cup.\",\"align\":\"left\"}\n"
    )

def _extract_json_from_text(text: str):
    # robust extraction: try full parse, then find first {..}
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except Exception:
            pass
    raise ValueError("No JSON object found")

def call_groq(prompt: str, api_key: str) -> Optional[str]:
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": prompt}],
        "temperature": TEMPERATURE,
    }
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(GROQ_API_URL, json=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content
        except requests.exceptions.HTTPError as he:
            code = he.response.status_code if he.response is not None else "?"
            print(f"[Groq] HTTPError {code}: {he}")
            if code == 403:
                break
            if code == 429:
                backoff = 2 ** attempt
                print(f"[Groq] Rate limited. Backing off {backoff}s")
                time.sleep(backoff)
        except Exception as e:
            print(f"[Groq] Attempt {attempt} failed: {e}")
            last_exc = e
            time.sleep(2 ** attempt)
    if last_exc:
        print("[Groq] All attempts failed.")
    return None

def save_scenario_json(obj: Dict, filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def save_scenario_txt(script: List[Dict], filename: str) -> None:
    # plain text file: one message per line "NAME|align|text"
    with open(filename, "w", encoding="utf-8") as f:
        for msg in script:
            f.write(f"{msg['user']}|{msg.get('align','left')}|{msg['text']}\n")

def generate_scenarios(request_context: str = "") -> List[str]:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    created_files = []

    for i in range(1, SCENARIOS_PER_RUN + 1):
        robot_pair = generate_robot_pair()
        min_lines = LINES_MIN
        max_lines = LINES_MAX
        prompt = build_prompt(robot_pair, min_lines, max_lines)
        if request_context:
            prompt += "\nContext: " + request_context

        print(f"[*] Generating scenario {i} with robots: {robot_pair[0]} , {robot_pair[1]}")

        content = None
        if api_key:
            raw = call_groq(prompt, api_key)
            if raw:
                try:
                    parsed = _extract_json_from_text(raw)
                    # validate parsed shape quickly
                    if isinstance(parsed, dict) and isinstance(parsed.get("script"), list):
                        content = parsed
                    else:
                        print("[!] Groq returned JSON but schema mismatch — falling back.")
                except Exception as e:
                    print(f"[!] Failed to parse Groq JSON: {e}")
        else:
            print("[!] No GROQ_API_KEY provided — using local fallback.")

        if not content:
            # build fallback content programmatically to avoid blocking pipeline
            num_lines = random.randint(min_lines, max_lines)
            script = local_fallback_script(robot_pair, num_lines)
            title = f"Fallback: {robot_pair[0]} vs {robot_pair[1]}"
            content = {"title": title, "script": script}

        base = f"ai_dialogue_raw_{ts}_{i}"
        json_path = os.path.join(OUTPUT_DIR, base + ".json")
        txt_path  = os.path.join(OUTPUT_DIR, base + ".txt")

        save_scenario_json(content, json_path)
        save_scenario_txt(content["script"], txt_path)
        print(f"[+] Saved scenario {i}: {json_path}  and {txt_path}")
        created_files.append(json_path)

    return created_files

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate multiple AI dialogue scenarios (JSON + TXT)")
    parser.add_argument("--request", "-r", default="", help="Optional context or theme for the scenarios")
    args = parser.parse_args()
    files = generate_scenarios(request_context=args.request)
    print(f"[+] Generated {len(files)} scenario JSON files.")

if __name__ == "__main__":
    main()