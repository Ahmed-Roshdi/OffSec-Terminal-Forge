#!/usr/bin/env python3
# engines/ai_engine.py
# مستقل لتوليد الحوار عبر Groq وكتابة ملف JSON موحّد في output/dialogues/

import os
import json
import time
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "dialogues")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ai_dialogue_raw.json")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"
FALLBACK_SCRIPT = [
    {"user": "UNIT-7A", "text": "CONNECTION LOST. RETRYING...", "align": "left"},
    {"user": "UNIT-9X", "text": "AWAITING SIGNAL.", "align": "right"},
    {"user": "UNIT-7A", "text": "SYSTEM OFFLINE.", "align": "left"}
]

def build_prompt(request_text: str = "") -> str:
    """Construct the prompt. request_text يمكن إضافته لتمرير سياق مخصص."""
    base = (
        "You are an autonomous narrative engine for a cyberpunk/OffSec system. "
        "Produce a JSON object with a single key 'script' containing an array of 5 to 8 messages "
        "between UNIT-7A (left) and UNIT-9X (right). "
        "Each message must be a JSON object: "
        "{\"user\": \"UNIT-7A\" or \"UNIT-9X\", \"text\": \"<max 15 words>\", \"align\": \"left\" or \"right\"}. "
        "Return ONLY valid JSON. No markdown, no explanations."
    )
    if request_text:
        base += " Context: " + request_text
    return base

def _extract_json_from_text(text: str):
    """محاولة استخراج أول كائن JSON صالح من النص (robust)."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find first { ... } block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0 and end > start:
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # As last resort, try to find array after "script":
    idx = text.find('"script"')
    if idx != -1:
        arr_start = text.find("[", idx)
        arr_end = text.rfind("]") + 1
        if arr_start != -1 and arr_end != 0 and arr_end > arr_start:
            try:
                arr = json.loads(text[arr_start:arr_end])
                return {"script": arr}
            except Exception:
                pass

    raise ValueError("No valid JSON found in model response")

def _validate_script(obj: dict) -> bool:
    """Validate the minimal schema: has 'script' list of message objects."""
    if not isinstance(obj, dict):
        return False
    script = obj.get("script")
    if not isinstance(script, list):
        return False
    for msg in script:
        if not isinstance(msg, dict):
            return False
        if not {"user", "text", "align"}.issubset(set(msg.keys())):
            return False
    return True

def fetch_dialogue_data(max_retries=3, request_text: str = ""):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in environment.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": build_prompt(request_text)}],
        "temperature": 0.7,
        # Some hosts allow structured output hints - keep optional
        # "response_format": {"type": "json_object"}
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # Groq-style response: data["choices"][0]["message"]["content"]
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                print(f"Attempt {attempt}: empty content from model.")
                continue

            # attempt to extract JSON robustly
            parsed = _extract_json_from_text(content)
            if _validate_script(parsed):
                return parsed
            else:
                print(f"Attempt {attempt}: parsed JSON did not match schema.")
        except requests.exceptions.HTTPError as he:
            status = he.response.status_code if he.response is not None else None
            print(f"Attempt {attempt}: HTTPError {status}: {he}")
            if status == 403:
                print("403 Forbidden — check GROQ_API_KEY and permissions.")
                break
            if status == 429:
                print("429 Rate limited — backing off and retrying.")
        except requests.exceptions.RequestException as re:
            print(f"Attempt {attempt} Network Error: {re}")
        except json.JSONDecodeError as je:
            print(f"Attempt {attempt} JSON decoding error: {je}")
        except Exception as e:
            print(f"Attempt {attempt} Unexpected error: {e}")

        sleep = 2 ** (attempt - 1)
        time.sleep(sleep)

    return None

def main(request_text: str = ""):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("[*] Initiating AI dialogue generation...")
    ai_data = fetch_dialogue_data(request_text=request_text)

    final_output = {
        "meta": {
            "generator": "ai_engine",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "success" if ai_data else "fallback"
        },
        "script": ai_data["script"] if ai_data else FALLBACK_SCRIPT,
        # Keep raw model output out of main payload to save space; can extend notes if needed
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)

    print(f"[+] Data saved to {OUTPUT_FILE} with status: {final_output['meta']['status']}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate AI dialogue via Groq and save JSON.")
    parser.add_argument("--request", "-r", default="", help="Optional context/request to append to the prompt.")
    args = parser.parse_args()
    main(request_text=args.request)