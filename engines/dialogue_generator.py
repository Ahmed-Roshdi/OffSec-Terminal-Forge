#!/usr/bin/env python3
"""
dialogue_generator.py
Cyberpunk/OffSec Dialogue Engine (updated)

This version reads a pre-generated script JSON from output/dialogues/ai_dialogue_raw.json
instead of calling the AI service itself. All original rendering helpers are preserved.
"""
from __future__ import annotations
import json
import os
import random
import textwrap
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont

import alien_generator

# ── Directory layout ────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR    = os.path.join(BASE_DIR, "output")
DIALOGUES_DIR = os.path.join(OUTPUT_DIR, "dialogues")
ASSETS_DIR    = os.path.join(BASE_DIR, "assets")
FONT_PATH     = os.path.join(ASSETS_DIR, "fonts", "UbuntuMono-R.ttf")
FALLBACK_FONT = "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf"

# ── Visual constants ────────────────────────────────────────────────────────
CANVAS_W      = 1200
CANVAS_H      = 800
BG_COLOR      = (9, 10, 15)
SCANLINE_ALPHA = 40
BUBBLE_WRAP   = 40      # chars per line in a chat bubble
BUBBLE_PAD    = 15      # vertical gap between bubbles
FRAME_DURATION_CHAT   = 1800   # ms per dialogue frame
FRAME_DURATION_BG     = 3000   # ms for the initial map frame
FRAME_DURATION_FINAL  = 10000  # ms for the closing captcha frame

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

# ── Script file loader (new)────────────────────────────────────────────────
def load_script_from_file(filepath: Optional[str] = None) -> Optional[List[Dict]]:
    """
    Read the generated ai_dialogue_raw.json and return the script list or None.
    Expected structure:
    {
      "meta": { ... },
      "script": [ {"user":"UNIT-7A","text":"...","align":"left"}, ... ]
    }
    """
    if filepath is None:
        filepath = os.path.join(DIALOGUES_DIR, "ai_dialogue_raw.json")
    if not os.path.exists(filepath):
        print(f"WARNING: {filepath} not found. Using fallback.")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        script = data.get("script")
        if isinstance(script, list) and len(script) > 0:
            # Basic shape check for each message
            for idx, m in enumerate(script):
                if not isinstance(m, dict) or not {"user", "text", "align"}.issubset(set(m.keys())):
                    print(f"WARNING: script item #{idx} missing required keys; ignoring file.")
                    return None
            return script
        print("WARNING: 'script' key missing or empty in file.")
        return None
    except Exception as e:
        print(f"ERROR reading {filepath}: {e}")
        return None

# ── Image helpers (kept from original)─────────────────────────────────────
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

# ── Frame builders ─────────────────────────────────────────────────────────
def _build_chat_frame(
    visible: List[Dict],
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
                     fonts, msg["user"], msg.get("decal", ""))
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

# ── Main sequence generator ─────────────────────────────────────────────────
def generate_dialogue_sequence(
    bg_image: Optional[Image.Image] = None,
    width:    int = CANVAS_W,
    height:   int = CANVAS_H,
) -> Tuple[List[Image.Image], List[int]]:
    """
    Build the full animated sequence.
    Returns (frames, durations) ready for WebP export.
    """
    print("[*] Initialising Cyberpunk/OffSec Dialogue Engine...")
    fonts   = _load_fonts()
    frames:    List[Image.Image] = []
    durations: List[int]         = []

    # Optional map background as the opening frame
    if bg_image is not None:
        frames.append(bg_image.copy().convert("RGB"))
        durations.append(FRAME_DURATION_BG)

    # NEW: load script from file (generated by ai_engine) or fall back to static
    script = load_script_from_file() or random.choice(FALLBACK_DIALOGUES)

    # Pre-compute per-message metadata
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for msg in script:
        msg.setdefault("decal",
            f"[SYS.AUTH: OK] // HEX:{random.randint(0x1000, 0xFFFF):04X}"
            if msg["align"] == "left"
            else f"[NET.UPLINK] // PKT:{random.randint(10, 99)}"
        )
        msg["height"] = _bubble_height(dummy_draw, msg["text"], fonts["chat"])

    # Build one frame per dialogue line (sliding window if content overflows)
    visible: List[Dict] = []
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

# ── Entry point ─────────────────────────────────────────────────────────────
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
    main()