#!/usr/bin/env python3
"""
Updated dialogue_generator.py

- Detects all ai_dialogue_raw_*.json files in output/dialogues/
- For each JSON, builds a WebP sequence: dialogue_seq_{basename}.webp
- Improved visuals: avatar circles with initials, per-robot color hashing, slightly wider bubbles, longer wrap
- If no JSONs found, falls back to built-in fallback dialogues and renders one sequence
"""
from __future__ import annotations
import json
import os
import random
import textwrap
import time
import glob
from typing import List, Dict, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

import alien_generator

# ── Directory layout ────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR    = os.path.join(BASE_DIR, "output")
DIALOGUES_DIR = os.path.join(OUTPUT_DIR, "dialogues")
ASSETS_DIR    = os.path.join(BASE_DIR, "assets")
FONT_PATH     = os.path.join(ASSETS_DIR, "fonts", "UbuntuMono-R.ttf")
FALLBACK_FONT = "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf"

# ── Visual constants ────────────────────────────────────────────────────────
CANVAS_W      = 1400   # slightly wider for longer text
CANVAS_H      = 900
BG_COLOR      = (9, 10, 15)
SCANLINE_ALPHA = 36
BUBBLE_WRAP   = 48      # increased wrap
BUBBLE_PAD    = 18
FRAME_DURATION_CHAT   = 2000
FRAME_DURATION_BG     = 3200
FRAME_DURATION_FINAL  = 10000

# ── Fallback dialogues (kept) ───────────────────────────────────────────────
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

# ── Font loader ────────────────────────────────────────────────────────────
def _load_fonts() -> dict:
    """Load UbuntuMono at three sizes; fall back to PIL default on failure."""
    sizes = {"chat": 24, "name": 18, "decal": 12}
    candidates = [FONT_PATH, FALLBACK_FONT]
    for path in candidates:
        if os.path.exists(path):
            try:
                return {key: ImageFont.truetype(path, size) for key, size in sizes.items()}
            except Exception:
                continue
    default = ImageFont.load_default()
    return {key: default for key in sizes}

# ── Visual helpers ────────────────────────────────────────────────────────
def _apply_scanlines(image: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, image.height, 3):
        draw.line([(0,y),(image.width,y)], fill=(0,0,0,SCANLINE_ALPHA), width=1)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int,int]:
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        return bbox[2]-bbox[0], bbox[3]-bbox[1]
    except AttributeError:
        return draw.textsize(text, font=font)

def _bubble_height(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    lines = textwrap.wrap(text, width=BUBBLE_WRAP)
    total = sum(_text_size(draw, line, font)[1] + 6 for line in lines)
    return total + 70

def _color_for_name(name: str) -> Tuple[int,int,int]:
    # deterministic color from name
    h = abs(hash(name)) % (256**3)
    r = (h >> 16) & 0xFF
    g = (h >> 8) & 0xFF
    b = h & 0xFF
    # boost contrast
    return (max(30, r), max(40, g), max(50, b))

def _initials(name: str) -> str:
    parts = name.replace('-', ' ').split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()

def _draw_avatar(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, name: str, font) -> None:
    col = _color_for_name(name)
    bbox = [x, y, x+size, y+size]
    draw.ellipse(bbox, fill=col)
    init = _initials(name)
    w,h = _text_size(draw, init, font)
    draw.text((x + (size-w)/2, y + (size-h)/2), init, fill=(255,255,255), font=font)

def _draw_bubble(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, align: str, fonts: dict, user_name: str, decal: str) -> None:
    lines = textwrap.wrap(text, width=BUBBLE_WRAP)
    line_dims = [_text_size(draw, line, fonts["chat"]) for line in lines]
    max_w = max((w for w,_ in line_dims), default=0)
    prefix = ">_ " if align == "left" else ">> "
    name_w, _ = _text_size(draw, f"{prefix}{user_name}", fonts["name"])
    decal_w, _ = _text_size(draw, decal, fonts["decal"])
    box_w = max(max_w + 60, name_w + decal_w + 60)
    box_h = sum(h + 6 for _,h in line_dims) + 60
    cut = 18

    # avatar position
    avatar_size = 56
    if align == "left":
        bg_color = (18,24,28)
        border = (0,220,220)
        text_color = (220,255,255)
        box_x = x + avatar_size + 20
        avatar_x = x
    else:
        bg_color = (28,18,24)
        border = (255,40,200)
        text_color = (255,210,240)
        box_x = x - box_w - avatar_size - 20
        avatar_x = x - avatar_size

    # draw rounded-ish polygon (approx with polygon)
    pts = [
        (box_x + cut, y), (box_x + box_w, y),
        (box_x + box_w, y + box_h - cut), (box_x + box_w - cut, y + box_h),
        (box_x, y + box_h), (box_x, y + cut),
        (box_x + cut, y)
    ]
    draw.polygon(pts, fill=bg_color)
    draw.line(pts, fill=border, width=2)
    draw.line([(box_x, y + 28), (box_x + box_w, y + 28)], fill=border, width=1)

    # draw avatar
    try:
        _draw_avatar(draw, avatar_x, y, avatar_size, user_name, fonts["name"])
    except Exception:
        pass

    draw.text((box_x + 12, y + 6), f"{prefix}{user_name}", fill=border, font=fonts["name"])
    draw.text((box_x + box_w - decal_w - 16, y + 10), decal, fill=(140,140,140), font=fonts["decal"])
    text_y = y + 36
    for (_, h), line in zip(line_dims, lines):
        draw.text((box_x + 16, text_y), line, fill=text_color, font=fonts["chat"])
        text_y += h + 6

# ── Frame builders ─────────────────────────────────────────────────────────
def _build_chat_frame(visible: List[Dict], fonts: dict, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    cur_y = 40
    for msg in visible:
        x_pos = 80 if msg["align"] == "left" else width - 80
        _draw_bubble(draw, msg["text"], x_pos, cur_y, msg["align"], fonts, msg["user"], msg.get("decal",""))
        cur_y += msg["height"] + BUBBLE_PAD
    return _apply_scanlines(canvas)

def _build_captcha_frame(fonts: dict, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGB", (width, height), color=BG_COLOR)
    captcha_path = os.path.join(ASSETS_DIR, "captcha.png")
    if os.path.exists(captcha_path):
        cap = Image.open(captcha_path).convert("RGBA")
        max_w = 520
        if cap.width > max_w:
            ratio = max_w / cap.width
            cap = cap.resize((max_w, int(cap.height * ratio)), Image.Resampling.LANCZOS)
        cx = (width - cap.width)//2
        cy = (height - cap.height)//2
        canvas.paste(cap, (cx, cy), cap)
    else:
        draw = ImageDraw.Draw(canvas)
        draw.text((width//2-200, height//2), "[MISSING: assets/captcha.png]", fill=(255,0,0), font=fonts["chat"])
    return _apply_scanlines(canvas)

# ── JSON loader ───────────────────────────────────────────────────────────
def load_script_from_json_file(filepath: str) -> Optional[List[Dict]]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        script = data.get("script")
        if isinstance(script, list) and len(script) > 0:
            return script
    except Exception as e:
        print(f"[!] Failed to load {filepath}: {e}")
    return None

# ── Sequence builder per script ───────────────────────────────────────────
def generate_dialogue_from_script(script: List[Dict], basename: str, bg_image: Optional[Image.Image] = None) -> str:
    fonts = _load_fonts()
    frames: List[Image.Image] = []
    durations: List[int] = []

    if bg_image is not None:
        frames.append(bg_image.copy().convert("RGB"))
        durations.append(FRAME_DURATION_BG)

    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1,1)))
    for msg in script:
        msg.setdefault("decal",
            f"[SYS] // {random.randint(0x1000,0xFFFF):04X}" if msg["align"] == "left" else f"[NET] // {random.randint(10,99)}"
        )
        # compute height with chat font
        msg["height"] = _bubble_height(dummy_draw, msg["text"], fonts["chat"])

    visible: List[Dict] = []
    for msg in script:
        visible.append(msg)
        # Trim from the top if we overflow the canvas
        while sum(m["height"] + BUBBLE_PAD for m in visible) > (CANVAS_H - 180):
            visible.pop(0)
        frames.append(_build_chat_frame(visible, fonts, CANVAS_W, CANVAS_H))
        durations.append(FRAME_DURATION_CHAT)

    # Closing captcha frame
    frames.append(_build_captcha_frame(fonts, CANVAS_W, CANVAS_H))
    durations.append(FRAME_DURATION_FINAL)

    output_path = os.path.join(DIALOGUES_DIR, f"dialogue_seq_{basename}.webp")
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
    return output_path

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    os.makedirs(DIALOGUES_DIR, exist_ok=True)

    # generate a single background map and reuse for all sequences
    print("[*] Generating background map (one for all sequences)...")
    bg_img, _ = alien_generator.generate_alien_world(save_to_disk=False)

    # find all JSON scenario files
    pattern = os.path.join(DIALOGUES_DIR, "ai_dialogue_raw_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        print("[!] No ai_dialogue_raw_*.json files found in output/dialogues. Using fallback single script.")
        scripts = [random.choice(FALLBACK_DIALOGUES)]
        names = ["fallback"]
    else:
        scripts = []
        names = []
        for p in files:
            script = load_script_from_json_file(p)
            if script:
                scripts.append(script)
                names.append(os.path.splitext(os.path.basename(p))[0])
            else:
                print(f"[!] Skipping invalid JSON file: {p}")

    for script, name in zip(scripts, names):
        print(f"[*] Rendering sequence for {name} (lines: {len(script)})...")
        out = generate_dialogue_from_script(script, basename=name, bg_image=bg_img)
        if os.path.exists(out):
            size_kb = os.path.getsize(out) / 1024
            print(f"[+] Saved: {out} ({size_kb:.1f} KB)")
        else:
            print(f"[!] Failed to save: {out}")

if __name__ == "__main__":
    main()