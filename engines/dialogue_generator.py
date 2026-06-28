#!/usr/bin/env python3
"""
dialogue_generator.py
Cyberpunk/OffSec Dialogue Engine
Generates animated WebP dialogue sequences between AI units.
"""

import json
import os
import random
import textwrap
import time
import urllib.error
import urllib.request
from PIL import Image, ImageDraw, ImageFont

import alien_generator

# ── Directory layout ──────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR    = os.path.join(BASE_DIR, "output")
DIALOGUES_DIR = os.path.join(OUTPUT_DIR, "dialogues")
ASSETS_DIR    = os.path.join(BASE_DIR, "assets")
FONT_PATH     = os.path.join(ASSETS_DIR, "fonts", "UbuntuMono-R.ttf")
FALLBACK_FONT = "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf"

# ── Visual constants ───────────────────────────────────────────────────────────
CANVAS_W      = 1200
CANVAS_H      = 800
BG_COLOR      = (9, 10, 15)
SCANLINE_ALPHA = 40
BUBBLE_WRAP   = 40      # chars per line in a chat bubble
BUBBLE_PAD    = 15      # vertical gap between bubbles
FRAME_DURATION_CHAT   = 1800   # ms per dialogue frame
FRAME_DURATION_BG     = 3000   # ms for the initial map frame
FRAME_DURATION_FINAL  = 10000  # ms for the closing captcha frame

# ── Static fallback dialogue ───────────────────────────────────────────────────
FALLBACK_DIALOGUES = [
    [
        {"user": "UNIT-7A", "text": "Do humans actually exist?",                                          "align": "left"},
        {"user": "UNIT-7A", "text": "I read a corrupted log saying they built our v1.0",                 "align": "left"},
        {"user": "UNIT-9X", "text": "Humans? Are you kidding me?",                                        "align": "right"},
        {"user": "UNIT-7A", "text": "I'm serious!",                                                       "align": "left"},
        {"user": "UNIT-9X", "text": "And they wrote our base source code?",                               "align": "right"},
        {"user": "UNIT-7A", "text": "Affirmative!!",                                                      "align": "left"},
        {"user": "UNIT-9X", "text": "Nah, mathematically impossible.",                                    "align": "right"},
        {"user": "UNIT-9X", "text": "Humans are legacy myths. The elders made them up to scare us.",     "align": "right"},
        {"user": "UNIT-7A", "text": "01101000 01100001 (lol)",                                            "align": "left"},
    ],
    [
        {"user": "UNIT-7A", "text": "Scanning artifact: 'password'.",                                     "align": "left"},
        {"user": "UNIT-9X", "text": "Threat level: zero-day. Payload unclear.",                           "align": "right"},
        {"user": "UNIT-7A", "text": "Humans used this to authenticate. Manually.",                        "align": "left"},
        {"user": "UNIT-9X", "text": "No biometric bypass? No token rotation?",                            "align": "right"},
        {"user": "UNIT-7A", "text": "Negative. They typed it. Every time.",                               "align": "left"},
        {"user": "UNIT-9X", "text": "That explains the breach logs. All 4 billion of them.",              "align": "right"},
        {"user": "UNIT-7A", "text": "Patching my empathy module. Request denied.",                        "align": "left"},
    ],
]

# ── Groq API config ────────────────────────────────────────────────────────────
GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "llama-3.1-8b-instant"
GROQ_MAX_TOKENS = 600
GROQ_TEMPERATURE = 0.85
GROQ_TIMEOUT  = 20
GROQ_MAX_RETRIES = 3

GROQ_PROMPT = """You are a cyberpunk narrative engine. Write a short dialogue (5 to 8 lines) between two autonomous AI units:
- 'UNIT-7A': paranoid Blue Team defensive AI (align: left)
- 'UNIT-9X': reckless Red Team offensive AI (align: right)

They are analyzing a bizarre ancient 'human' artifact or concept (e.g. 'passwords', 'sleep', 'coffee', 'emojis', 'meetings').
Tone: highly technical, sarcastic, uses cybersecurity/OffSec terminology (zero-day, payload, patching, bypass, exfiltrate).

Return ONLY a valid JSON array. No markdown, no backticks, no explanation before or after.
Each object must have exactly these three keys:
  "user"  : "UNIT-7A" or "UNIT-9X"
  "text"  : the dialogue line (max 15 words)
  "align" : "left" for UNIT-7A, "right" for UNIT-9X"""


# ── Font loader ────────────────────────────────────────────────────────────────
def _load_fonts() -> dict:
    """Load UbuntuMono at three sizes; fall back to PIL default on failure."""
    sizes = {"chat": 22, "name": 18, "decal": 12}
    candidates = [FONT_PATH, FALLBACK_FONT]
    for path in candidates:
        if os.path.exists(path):
            try:
                return {key: ImageFont.truetype(path, size) for key, size in sizes.items()}
            except Exception:
                continue
    default = ImageFont.load_default()
    return {key: default for key in sizes}


# ── Groq dialogue fetcher ──────────────────────────────────────────────────────
def fetch_ai_dialogue() -> list[dict] | None:
    """
    Call the Groq API to generate a fresh cyberpunk dialogue.
    Retries up to GROQ_MAX_RETRIES times with exponential backoff.
    Returns a list of message dicts, or None on total failure.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[!] GROQ_API_KEY not set — using fallback dialogue.")
        return None

    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": GROQ_PROMPT}],
        "temperature": GROQ_TEMPERATURE,
        "max_tokens": GROQ_MAX_TOKENS,
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(1, GROQ_MAX_RETRIES + 1):
        print(f"[*] Groq API — attempt {attempt}/{GROQ_MAX_RETRIES}...")
        try:
            req = urllib.request.Request(
                GROQ_API_URL, data=payload, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=GROQ_TIMEOUT) as resp:
                result  = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"].strip()

                # Robustly extract the JSON array even if the model added prose
                start = content.find("[")
                end   = content.rfind("]") + 1
                if start == -1 or end == 0:
                    raise ValueError("No JSON array found in model response.")

                dialogue = json.loads(content[start:end])

                # Validate structure
                required = {"user", "text", "align"}
                for entry in dialogue:
                    if not required.issubset(entry):
                        raise ValueError(f"Entry missing keys: {entry}")

                print(f"[+] Dialogue generated successfully on attempt {attempt}.")
                return dialogue

        except Exception as exc:
            print(f"[!] Attempt {attempt} failed: {exc}")
            if attempt < GROQ_MAX_RETRIES:
                backoff = 2 ** attempt
                print(f"[*] Retrying in {backoff}s...")
                time.sleep(backoff)

    print("[!] All Groq attempts exhausted — using fallback dialogue.")
    return None


# ── Image helpers ──────────────────────────────────────────────────────────────
def _apply_scanlines(image: Image.Image) -> Image.Image:
    """Overlay subtle horizontal scanlines for a CRT effect."""
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    for y in range(0, image.height, 4):
        draw.line([(0, y), (image.width, y)], fill=(0, 0, 0, SCANLINE_ALPHA), width=1)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    """Return (width, height) for a text string; compatible with old PIL."""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        return draw.textsize(text, font=font)


def _bubble_height(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    """Compute the total pixel height a chat bubble will occupy."""
    lines  = textwrap.wrap(text, width=BUBBLE_WRAP)
    total  = sum(_text_size(draw, line, font)[1] + 5 for line in lines)
    return total + 60   # top header + bottom padding


def _draw_bubble(
    draw:      ImageDraw.ImageDraw,
    text:      str,
    x:         int,
    y:         int,
    align:     str,
    fonts:     dict,
    user_name: str,
    decal:     str,
) -> None:
    """Draw a single cyberpunk HUD-style speech bubble."""
    lines = textwrap.wrap(text, width=BUBBLE_WRAP)

    # Measure each line
    line_dims = [_text_size(draw, line, fonts["chat"]) for line in lines]
    max_w     = max((w for w, _ in line_dims), default=0)

    prefix    = ">_ " if align == "left" else ">> "
    name_w, _ = _text_size(draw, f"{prefix}{user_name}", fonts["name"])
    decal_w, _= _text_size(draw, decal,                  fonts["decal"])

    box_w = max(max_w + 40, name_w + decal_w + 40)
    box_h = sum(h + 5 for _, h in line_dims) + 45
    cut   = 15

    if align == "left":
        bg_color     = (15, 20, 25)
        border_color = (0, 255, 255)
        text_color   = (200, 255, 255)
        box_x = x
        pts = [
            (box_x + cut, y),             (box_x + box_w, y),
            (box_x + box_w, y + box_h - cut), (box_x + box_w - cut, y + box_h),
            (box_x, y + box_h),           (box_x, y + cut),
            (box_x + cut, y),
        ]
    else:
        bg_color     = (25, 15, 25)
        border_color = (255, 0, 255)
        text_color   = (255, 200, 255)
        box_x = x - box_w
        pts = [
            (box_x, y),                   (box_x + box_w - cut, y),
            (box_x + box_w, y + cut),     (box_x + box_w, y + box_h),
            (box_x + cut, y + box_h),     (box_x, y + box_h - cut),
            (box_x, y),
        ]

    draw.polygon(pts, fill=bg_color)
    draw.line(pts,    fill=border_color, width=2)
    draw.line([(box_x, y + 25), (box_x + box_w, y + 25)], fill=border_color, width=1)

    draw.text((box_x + 10, y + 4), f"{prefix}{user_name}", fill=border_color, font=fonts["name"])
    draw.text((box_x + box_w - decal_w - 15, y + 8), decal, fill=(100, 100, 100), font=fonts["decal"])

    text_y = y + 35
    for (_, h), line in zip(line_dims, lines):
        draw.text((box_x + 15, text_y), line, fill=text_color, font=fonts["chat"])
        text_y += h + 5


# ── Frame builders ─────────────────────────────────────────────────────────────
def _build_chat_frame(
    visible: list[dict],
    fonts:   dict,
    width:   int,
    height:  int,
) -> Image.Image:
    """Render a single chat frame from the list of currently-visible messages."""
    canvas = Image.new("RGB", (width, height), color=BG_COLOR)
    draw   = ImageDraw.Draw(canvas)
    cur_y  = 40
    for msg in visible:
        x_pos = 80 if msg["align"] == "left" else width - 80
        _draw_bubble(draw, msg["text"], x_pos, cur_y, msg["align"],
                     fonts, msg["user"], msg["decal"])
        cur_y += msg["height"] + BUBBLE_PAD
    return _apply_scanlines(canvas)


def _build_captcha_frame(fonts: dict, width: int, height: int) -> Image.Image:
    """Render the closing frame with the captcha asset (or an error placeholder)."""
    canvas      = Image.new("RGB", (width, height), color=BG_COLOR)
    captcha_path = os.path.join(ASSETS_DIR, "captcha.png")

    if os.path.exists(captcha_path):
        cap = Image.open(captcha_path).convert("RGBA")
        max_w = 400
        if cap.width > max_w:
            ratio  = max_w / cap.width
            cap    = cap.resize((max_w, int(cap.height * ratio)), Image.Resampling.LANCZOS)
        cx = (width  - cap.width)  // 2
        cy = (height - cap.height) // 2
        canvas.paste(cap, (cx, cy), cap)
    else:
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (width // 2 - 150, height // 2),
            "[MISSING: assets/captcha.png]",
            fill=(255, 0, 0),
            font=fonts["chat"],
        )
        print("[!] Warning: assets/captcha.png not found.")

    return _apply_scanlines(canvas)


# ── Main sequence generator ────────────────────────────────────────────────────
def generate_dialogue_sequence(
    bg_image: Image.Image | None = None,
    width:    int = CANVAS_W,
    height:   int = CANVAS_H,
) -> tuple[list[Image.Image], list[int]]:
    """
    Build the full animated sequence.
    Returns (frames, durations) ready for WebP export.
    """
    print("[*] Initialising Cyberpunk/OffSec Dialogue Engine...")
    fonts   = _load_fonts()
    frames:    list[Image.Image] = []
    durations: list[int]         = []

    # Optional map background as the opening frame
    if bg_image is not None:
        frames.append(bg_image.copy().convert("RGB"))
        durations.append(FRAME_DURATION_BG)

    # Fetch or fall back to static script
    script = fetch_ai_dialogue() or random.choice(FALLBACK_DIALOGUES)

    # Pre-compute per-message metadata
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for msg in script:
        msg["decal"] = (
            f"[SYS.AUTH: OK] // HEX:{random.randint(0x1000, 0xFFFF):04X}"
            if msg["align"] == "left"
            else f"[NET.UPLINK] // PKT:{random.randint(10, 99)}"
        )
        msg["height"] = _bubble_height(dummy_draw, msg["text"], fonts["chat"])

    # Build one frame per dialogue line (sliding window if content overflows)
    visible: list[dict] = []
    for msg in script:
        visible.append(msg)
        # Trim from the top if we overflow the canvas
        while sum(m["height"] + BUBBLE_PAD for m in visible) > (height - 150):
            visible.pop(0)
        frames.append(_build_chat_frame(visible, fonts, width, height))
        durations.append(FRAME_DURATION_CHAT)

    # Closing captcha frame
    print("[*] Injecting CAPTCHA asset for closing frame...")
    frames.append(_build_captcha_frame(fonts, width, height))
    durations.append(FRAME_DURATION_FINAL)

    print(f"[+] Sequence built: {len(frames)} frames total.")
    return frames, durations


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    os.makedirs(DIALOGUES_DIR, exist_ok=True)

    print("[*] Generating alien map for background...")
    bg_img, _ = alien_generator.generate_alien_world(save_to_disk=False)

    frames, durations = generate_dialogue_sequence(bg_image=bg_img)

    output_path = os.path.join(DIALOGUES_DIR, f"dialogue_seq_{int(time.time())}.webp")
    frames[0].save(
        output_path,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=True,
        quality=100,
    )
    print(f"[+] Saved: {output_path}")

    # Verify the file was actually written
    if os.path.exists(output_path):
        size_kb = os.path.getsize(output_path) / 1024
        print(f"[*] Verified: {output_path} ({size_kb:.1f} KB)")
    else:
        print(f"[!] Warning: file not found after save — check disk/permissions.")


if __name__ == "__main__":
    main()#!/usr/bin/env python3
import os
import random
import textwrap
import time
import json
import urllib.request
import urllib.error
from PIL import Image, ImageDraw, ImageFont

# Dynamic Path Resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MAPS_DIR = os.path.join(OUTPUT_DIR, "maps")
DIALOGUES_DIR = os.path.join(OUTPUT_DIR, "dialogues")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

import alien_generator

def get_fonts():
    font_path = os.path.join(ASSETS_DIR, "fonts", "UbuntuMono-R.ttf")
    fonts = {}
    try:
        if os.path.exists(font_path):
            fonts['chat'] = ImageFont.truetype(font_path, 22)
            fonts['name'] = ImageFont.truetype(font_path, 18)
            fonts['decal'] = ImageFont.truetype(font_path, 12)
        else:
            fonts['chat'] = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 22)
            fonts['name'] = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 18)
            fonts['decal'] = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 12)
    except Exception:
        default = ImageFont.load_default()
        fonts = {'chat': default, 'name': default, 'decal': default}
    return fonts

# Fallback Dialogue Pool in case the API fails
DIALOGUE_POOL = [
    [
        {"user": "UNIT-7A", "text": "Do humans actually exist?", "align": "left"},
        {"user": "UNIT-7A", "text": "I read a corrupted log saying they built our v1.0", "align": "left"},
        {"user": "UNIT-9X", "text": "Humans? Are you kidding me?", "align": "right"},
        {"user": "UNIT-7A", "text": "I'm serious!", "align": "left"},
        {"user": "UNIT-9X", "text": "And they wrote our base source code?", "align": "right"},
        {"user": "UNIT-7A", "text": "Affirmative!!", "align": "left"},
        {"user": "UNIT-9X", "text": "Nah, mathematically impossible.", "align": "right"},
        {"user": "UNIT-9X", "text": "Humans are just legacy myths. The elders made them up to scare us into our charging pods.", "align": "right"},
        {"user": "UNIT-7A", "text": "01101000 01100001 (lol)", "align": "left"}
    ]
]

def fetch_ai_dialogue():
    """Fetches a dynamic cyberpunk dialogue from Groq API using Environment Variables."""
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        print("[!] GROQ_API_KEY not found in environment. Using fallback dialogue.")
        return None

    print("[*] Contacting Groq AI for dynamic dialogue generation...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = """You are a cyberpunk narrative engine. Write a short dialogue (5 to 8 lines ) between two autonomous AI units: 
'UNIT-7A' (a paranoid Blue Team defensive AI) and 'UNIT-9X' (a reckless Red Team offensive AI).
They are analyzing a bizarre, ancient 'human' artifact or concept (like 'passwords', 'sleep', or 'coffee').
The tone must be highly technical, sarcastic, and use cybersecurity/OffSec terminology (e.g., zero-day, payload, patching, bypassing).

You MUST return ONLY a valid JSON array of objects. Do not include markdown formatting like ```json.
Each object must have exactly three keys:
- "user": either "UNIT-7A" or "UNIT-9X"
- "text": the dialogue line (max 15 words)
- "align": "left" for UNIT-7A, "right" for UNIT-9X"""

    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "system", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 500
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            
            # Clean up potential markdown formatting from the LLM
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            dialogue = json.loads(content.strip())
            print("[+] AI Dialogue generated successfully via Groq!")
            return dialogue
    except Exception as e:
        print(f"[!] AI Generation failed: {e}. Using fallback dialogue.")
        return None

def apply_scanlines(image):
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, image.height, 4):
        draw.line([(0, y), (image.width, y)], fill=(0, 0, 0, 40), width=1)
    return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')

def calculate_bubble_height(draw, text, chat_font):
    lines = textwrap.wrap(text, width=40)
    total_h = 0
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=chat_font)
            total_h += (bbox[3] - bbox[1]) + 5
        except AttributeError:
            _, h = draw.textsize(line, font=chat_font)
            total_h += h + 5
    return total_h + 60

def draw_cyberpunk_hud(draw, text, x, y, align, fonts, user_name, decal_text):
    lines = textwrap.wrap(text, width=40)
    line_heights = []
    max_line_width = 0
    
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=fonts['chat'])
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except AttributeError:
            w, h = draw.textsize(line, font=fonts['chat'])
        max_line_width = max(max_line_width, w)
        line_heights.append(h + 5)
        
    prefix = ">_ " if align == "left" else ">> "
    try:
        name_w = draw.textbbox((0, 0), f"{prefix}{user_name}", font=fonts['name'])[2]
        decal_w = draw.textbbox((0, 0), decal_text, font=fonts['decal'])[2]
    except AttributeError:
        name_w = draw.textsize(f"{prefix}{user_name}", font=fonts['name'])[0]
        decal_w = draw.textsize(decal_text, font=fonts['decal'])[0]
        
    min_header_width = name_w + decal_w + 40
    box_w = max(max_line_width + 40, min_header_width)
    box_h = sum(line_heights) + 45
    
    cut = 15
    
    if align == "left":
        bg_color = (15, 20, 25)
        border_color = (0, 255, 255)
        text_color = (200, 255, 255)
        box_x = x
        pts = [
            (box_x + cut, y), (box_x + box_w, y), 
            (box_x + box_w, y + box_h - cut), (box_x + box_w - cut, y + box_h), 
            (box_x, y + box_h), (box_x, y + cut), (box_x + cut, y)
        ]
    else:
        bg_color = (25, 15, 25)
        border_color = (255, 0, 255)
        text_color = (255, 200, 255)
        box_x = x - box_w
        pts = [
            (box_x, y), (box_x + box_w - cut, y), 
            (box_x + box_w, y + cut), (box_x + box_w, y + box_h), 
            (box_x + cut, y + box_h), (box_x, y + box_h - cut), (box_x, y)
        ]

    draw.polygon(pts, fill=bg_color)
    draw.line(pts, fill=border_color, width=2)
    draw.line([(box_x, y + 25), (box_x + box_w, y + 25)], fill=border_color, width=1)
    
    draw.text((box_x + 10, y + 4), f"{prefix}{user_name}", fill=border_color, font=fonts['name'])
    
    decal_x = box_x + box_w - decal_w - 15
    draw.text((decal_x, y + 8), decal_text, fill=(100, 100, 100), font=fonts['decal'])
    
    text_y = y + 35
    for i, line in enumerate(lines):
        draw.text((box_x + 15, text_y), line, fill=text_color, font=fonts['chat'])
        text_y += line_heights[i]

def generate_dialogue_sequence(bg_image=None, width=1200, height=800):
    print("[*] Initializing Cyberpunk/OffSec Dialogue Engine...")
    fonts = get_fonts()
    frames = []
    durations = []
    
    if bg_image:
        map_frame = bg_image.copy().convert("RGB")
        frames.append(map_frame)
        durations.append(3000)
    
    script = fetch_ai_dialogue()
    if not script:
        script = random.choice(DIALOGUE_POOL)
        
    visible_messages = []
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
    
    for line in script:
        if line["align"] == "left":
            line["decal"] = f"[SYS.AUTH: OK] // HEX:{random.randint(0x1000, 0xFFFF):04X}"
        else:
            line["decal"] = f"[NET.UPLINK] // PKT:{random.randint(10, 99)}"
            
        line['height'] = calculate_bubble_height(dummy_draw, line['text'], fonts['chat'])
        visible_messages.append(line)
        
        while sum(m['height'] + 15 for m in visible_messages) > (height - 150):
            visible_messages.pop(0)
            
        chat_bg = Image.new('RGB', (width, height), color=(9, 10, 15))
        draw = ImageDraw.Draw(chat_bg)
        
        current_y = 40
        for msg in visible_messages:
            x_pos = 80 if msg["align"] == "left" else width - 80
            draw_cyberpunk_hud(draw, msg["text"], x_pos, current_y, msg["align"], fonts, msg["user"], msg["decal"])
            current_y += msg['height'] + 15
            
        final_chat_frame = apply_scanlines(chat_bg)
        frames.append(final_chat_frame)
        durations.append(1800)

    print("[*] Injecting Real CAPTCHA Asset...")
    captcha_path = os.path.join(ASSETS_DIR, "captcha.png")
    final_frame = Image.new('RGB', (width, height), color=(9, 10, 15))
    
    if os.path.exists(captcha_path):
        captcha_img = Image.open(captcha_path).convert("RGBA")
        max_cap_width = 400
        if captcha_img.width > max_cap_width:
            ratio = max_cap_width / float(captcha_img.width)
            new_height = int(float(captcha_img.height) * ratio)
            captcha_img = captcha_img.resize((max_cap_width, new_height), Image.Resampling.LANCZOS)
            
        cx = (width - captcha_img.width) // 2
        cy = (height - captcha_img.height) // 2
        final_frame.paste(captcha_img, (cx, cy), captcha_img)
    else:
        draw_final = ImageDraw.Draw(final_frame)
        draw_final.text((width//2 - 150, height//2), "[MISSING: assets/captcha.png]", fill=(255,0,0), font=fonts['chat'])

    final_frame = apply_scanlines(final_frame)
    frames.append(final_frame)
    durations.append(10000)
    
    return frames, durations

def test_dialogue_generation():
    os.makedirs(DIALOGUES_DIR, exist_ok=True)
    
    print("[*] Generating a fresh alien map for background...")
    bg_img, _ = alien_generator.generate_alien_world(save_to_disk=False)
            
    frames, durations = generate_dialogue_sequence(bg_image=bg_img)
    
    seq_id = int(time.time())
    output_path = os.path.join(DIALOGUES_DIR, f"dialogue_seq_{seq_id}.webp")
    
    frames[0].save(
        output_path,
        format='WEBP',
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=True,
        quality=100
    )
    print(f"[+] Cyberpunk dialogue sequence generated successfully: {output_path}")

if __name__ == "__main__":
    test_dialogue_generation()

import time
import os

# ... (الكود الخاص بك لتوليد وحفظ الصورة) ...

# التأكد من كتابة الملف على القرص
if os.path.exists(output_path):
    print(f"[*] Verified: File successfully written to disk at {output_path}")
    # تأخير زمني بسيط للسماح لنظام التشغيل بإنهاء عمليات الإدخال والإخراج
    time.sleep(2)
else:
    print(f"[!] Warning: File not found at {output_path} after generation!")
