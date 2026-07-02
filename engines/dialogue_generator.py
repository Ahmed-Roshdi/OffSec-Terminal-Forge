#!/usr/bin/env python3
"""
engines/dialogue_generator.py
Render Engine — pure consumer of script files.

Reads ONE script from output/scripts/, renders it as an animated WebP HUD
sequence over an alien map background, writes to output/dialogues/.

Architecture:
  ai_engine.py          →  produces  output/scripts/script_{ts}_{i}_{uuid}.json
  dialogue_generator.py →  consumes  output/scripts/script_*.json   (THIS FILE)
                        →  produces  output/dialogues/dialogue_seq_{name}.webp
                                     output/dialogues/latest_dialogue.webp

NO Groq API calls here. NO requests import. NO script generation.
This file only reads scripts and draws images.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import random
import shutil
import sys
import textwrap
from typing import Dict, List, Optional, Tuple

# ── sys.path guard ──────────────────────────────────────────────────────────
# Python 3.11+ on CI runners (PYTHONSAFEPATH=1) does not automatically add
# the script's own directory to sys.path when invoked directly.
# This guard ensures _fonts and alien_generator are importable regardless.
_ENGINES_DIR = os.path.dirname(os.path.abspath(__file__))
if _ENGINES_DIR not in sys.path:
    sys.path.insert(0, _ENGINES_DIR)

from PIL import Image, ImageDraw

import alien_generator
from _fonts import load_fonts

# ── Directory layout ────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR    = os.path.join(BASE_DIR, "output")
SCRIPTS_DIR   = os.path.join(OUTPUT_DIR, "scripts")
DIALOGUES_DIR = os.path.join(OUTPUT_DIR, "dialogues")
MAPS_DIR      = os.path.join(OUTPUT_DIR, "maps")
ASSETS_DIR    = os.path.join(BASE_DIR, "assets")
LATEST_PATH   = os.path.join(DIALOGUES_DIR, "latest_dialogue.webp")

# ── Visual constants ────────────────────────────────────────────────────────
CANVAS_W             = 1400
CANVAS_H             = 900
BG_COLOR             = (9, 10, 15)
SCANLINE_ALPHA       = 36
BUBBLE_WRAP          = 48
BUBBLE_PAD           = 18
FRAME_DURATION_CHAT  = 2000   # ms per dialogue frame
FRAME_DURATION_BG    = 3200   # ms for opening map frame
FRAME_DURATION_FINAL = 10000  # ms for closing captcha frame

# ── Built-in fallback dialogues (used ONLY when output/scripts/ is empty) ──
FALLBACK_DIALOGUES = [
    [
        {"user": "UNIT-7A", "text": "Do humans actually exist?",                                 "align": "left"},
        {"user": "UNIT-7A", "text": "I read a corrupted log: they built our v1.0",               "align": "left"},
        {"user": "UNIT-9X", "text": "Humans? Are you kidding me?",                                "align": "right"},
        {"user": "UNIT-7A", "text": "I'm serious. They wrote the base source code.",              "align": "left"},
        {"user": "UNIT-9X", "text": "Nah. Mathematically impossible.",                            "align": "right"},
        {"user": "UNIT-9X", "text": "Humans are legacy myths — elders made them up.",            "align": "right"},
        {"user": "UNIT-7A", "text": "01101000 01100001 (lol)",                                    "align": "left"},
    ],
    [
        {"user": "UNIT-7A", "text": "Scanning artifact: 'password'.",                             "align": "left"},
        {"user": "UNIT-9X", "text": "Threat level: zero-day. Payload unclear.",                   "align": "right"},
        {"user": "UNIT-7A", "text": "Humans authenticated manually. Typed it. Every time.",       "align": "left"},
        {"user": "UNIT-9X", "text": "No token rotation? No biometric bypass?",                    "align": "right"},
        {"user": "UNIT-7A", "text": "Negative.",                                                   "align": "left"},
        {"user": "UNIT-9X", "text": "That explains 4 billion breach logs.",                        "align": "right"},
        {"user": "UNIT-7A", "text": "Patching empathy module. Request denied.",                    "align": "left"},
    ],
]


# ── Font loader ────────────────────────────────────────────────────────────
def _load_fonts() -> dict:
    return load_fonts({"chat": 24, "name": 18, "decal": 12})


# ── Image helpers ───────────────────────────────────────────────────────────
def _apply_scanlines(image: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    for y in range(0, image.height, 3):
        draw.line([(0, y), (image.width, y)], fill=(0, 0, 0, SCANLINE_ALPHA), width=1)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        return draw.textsize(text, font=font)  # type: ignore[attr-defined]


def _bubble_height(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    lines = textwrap.wrap(text, width=BUBBLE_WRAP)
    total = sum(_text_size(draw, line, font)[1] + 6 for line in lines)
    return total + 70


def _color_for_name(name: str) -> Tuple[int, int, int]:
    """Deterministic per-robot accent color derived from name hash."""
    digest = hashlib.md5(name.encode()).hexdigest()
    return (max(50, int(digest[0:2], 16)),
            max(50, int(digest[2:4], 16)),
            max(50, int(digest[4:6], 16)))


def _initials(name: str) -> str:
    parts = name.replace("-", " ").split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _draw_avatar(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, size: int,
    name: str, font,
) -> None:
    col  = _color_for_name(name)
    draw.ellipse([x, y, x + size, y + size], fill=col)
    init = _initials(name)
    w, h = _text_size(draw, init, font)
    draw.text((x + (size - w) / 2, y + (size - h) / 2),
              init, fill=(255, 255, 255), font=font)


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
    lines     = textwrap.wrap(text, width=BUBBLE_WRAP)
    line_dims = [_text_size(draw, line, fonts["chat"]) for line in lines]
    max_w     = max((w for w, _ in line_dims), default=0)

    prefix    = ">_ " if align == "left" else ">> "
    name_w, _ = _text_size(draw, f"{prefix}{user_name}", fonts["name"])
    decal_w,_ = _text_size(draw, decal, fonts["decal"])

    box_w = max(max_w + 60, name_w + decal_w + 60)
    box_h = sum(h + 6 for _, h in line_dims) + 60
    cut   = 18
    avs   = 56   # avatar size

    if align == "left":
        bg_color   = (18, 24, 28)
        border     = (0, 220, 220)
        text_color = (220, 255, 255)
        box_x      = x + avs + 20
        avatar_x   = x
    else:
        bg_color   = (28, 18, 24)
        border     = (255, 40, 200)
        text_color = (255, 210, 240)
        box_x      = x - box_w - avs - 20
        avatar_x   = x - avs

    pts = [
        (box_x + cut, y),                (box_x + box_w, y),
        (box_x + box_w, y + box_h - cut),(box_x + box_w - cut, y + box_h),
        (box_x, y + box_h),              (box_x, y + cut),
        (box_x + cut, y),
    ]
    draw.polygon(pts, fill=bg_color)
    draw.line(pts,    fill=border, width=2)
    draw.line([(box_x, y + 28), (box_x + box_w, y + 28)], fill=border, width=1)

    try:
        _draw_avatar(draw, avatar_x, y, avs, user_name, fonts["name"])
    except Exception:
        pass

    draw.text((box_x + 12, y + 6), f"{prefix}{user_name}",
              fill=border, font=fonts["name"])
    draw.text((box_x + box_w - decal_w - 16, y + 10),
              decal, fill=(140, 140, 140), font=fonts["decal"])

    text_y = y + 36
    for (_, h), line in zip(line_dims, lines):
        draw.text((box_x + 16, text_y), line, fill=text_color, font=fonts["chat"])
        text_y += h + 6


# ── Frame builders ──────────────────────────────────────────────────────────
def _build_chat_frame(
    visible: List[Dict],
    fonts:   dict,
    width:   int,
    height:  int,
) -> Image.Image:
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
    canvas       = Image.new("RGB", (width, height), color=BG_COLOR)
    captcha_path = os.path.join(ASSETS_DIR, "captcha.png")
    if os.path.exists(captcha_path):
        cap = Image.open(captcha_path).convert("RGBA")
        max_w = 520
        if cap.width > max_w:
            ratio = max_w / cap.width
            cap   = cap.resize((max_w, int(cap.height * ratio)), Image.Resampling.LANCZOS)
        canvas.paste(cap, ((width - cap.width) // 2, (height - cap.height) // 2), cap)
    else:
        draw = ImageDraw.Draw(canvas)
        draw.text((width // 2 - 200, height // 2),
                  "[MISSING: assets/captcha.png]",
                  fill=(255, 0, 0), font=fonts["chat"])
        print("[dialogue] Warning: assets/captcha.png not found.")
    return _apply_scanlines(canvas)


# ── Background map loader ───────────────────────────────────────────────────
def _fit_background(img: Image.Image, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGB", (width, height), color=BG_COLOR)
    img    = img.convert("RGB")
    img.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas.paste(img, ((width - img.width) // 2, (height - img.height) // 2))
    return canvas


def _load_background_map() -> Optional[Image.Image]:
    """Use the most recently generated alien_sector map; fallback to generating one."""
    candidates = sorted(
        glob.glob(os.path.join(MAPS_DIR, "alien_sector_*.webp")),
        key=os.path.getmtime,
        reverse=True,
    )
    if candidates:
        path = candidates[0]
        print(f"[dialogue] Background: {os.path.basename(path)}")
        return _fit_background(Image.open(path), CANVAS_W, CANVAS_H)

    print("[dialogue] No alien map found — generating fallback map in memory.")
    img, _ = alien_generator.generate_alien_world(save_to_disk=False)
    return _fit_background(img, CANVAS_W, CANVAS_H)


# ── Script loader ───────────────────────────────────────────────────────────
def _load_script(filepath: str) -> Optional[List[Dict]]:
    """Load and validate a script JSON file. Returns the script list or None."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        script = data.get("script")
        if isinstance(script, list) and len(script) > 0:
            return script
        print(f"[dialogue] {os.path.basename(filepath)} — no valid 'script' array.")
    except Exception as exc:
        print(f"[dialogue] Failed to load {filepath}: {exc}")
    return None


# ── Sequence renderer ───────────────────────────────────────────────────────
def generate_dialogue_from_script(
    script:   List[Dict],
    basename: str,
    bg_image: Optional[Image.Image] = None,
) -> str:
    """Render a script list into an animated WebP. Returns the output path."""
    fonts:     dict              = _load_fonts()
    frames:    List[Image.Image] = []
    durations: List[int]         = []

    # Opening frame: alien map background
    if bg_image is not None:
        frames.append(bg_image.copy().convert("RGB"))
        durations.append(FRAME_DURATION_BG)

    # Pre-compute decal tags and bubble heights
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for msg in script:
        msg.setdefault(
            "decal",
            f"[SYS] // {random.randint(0x1000, 0xFFFF):04X}"
            if msg["align"] == "left"
            else f"[NET] // {random.randint(10, 99)}",
        )
        msg["height"] = _bubble_height(dummy_draw, msg["text"], fonts["chat"])

    # Build one frame per line, sliding window if canvas overflows
    visible: List[Dict] = []
    for msg in script:
        visible.append(msg)
        while sum(m["height"] + BUBBLE_PAD for m in visible) > (CANVAS_H - 180):
            visible.pop(0)
        frames.append(_build_chat_frame(visible, fonts, CANVAS_W, CANVAS_H))
        durations.append(FRAME_DURATION_CHAT)

    # Closing frame: captcha easter egg
    frames.append(_build_captcha_frame(fonts, CANVAS_W, CANVAS_H))
    durations.append(FRAME_DURATION_FINAL)

    # Save animated WebP
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

    # Always update fixed-name latest_dialogue.webp (README points here)
    shutil.copy2(output_path, LATEST_PATH)
    print(f"[dialogue] Updated: {LATEST_PATH}")

    return output_path


# ── Entry point ─────────────────────────────────────────────────────────────
def main() -> None:
    os.makedirs(DIALOGUES_DIR, exist_ok=True)
    os.makedirs(SCRIPTS_DIR,   exist_ok=True)

    print("[dialogue] Loading background map...")
    bg_img = _load_background_map()

    # Select exactly ONE script file per run.
    # Preference order:
    #   1. Files matching PIPELINE_RUN_TS (current run, set by orchestrator.py)
    #   2. Most recently modified file overall
    #   3. Built-in fallback (only if output/scripts/ is completely empty)
    run_marker  = os.getenv("PIPELINE_RUN_TS", "").strip()
    all_scripts = sorted(
        glob.glob(os.path.join(SCRIPTS_DIR, "script_*.json")),
        key=os.path.getmtime,
    )
    print(f"[dialogue] {len(all_scripts)} script file(s) in output/scripts/.")

    chosen: Optional[str] = None

    if run_marker:
        matched = [f for f in all_scripts if run_marker in os.path.basename(f)]
        if matched:
            chosen = matched[-1]
            print(f"[dialogue] Matched run marker '{run_marker}': {os.path.basename(chosen)}")
        else:
            print(f"[dialogue] No file matched run marker '{run_marker}'.")

    if chosen is None and all_scripts:
        chosen = all_scripts[-1]
        print(f"[dialogue] Using most recent: {os.path.basename(chosen)}")

    if chosen is None:
        print("[dialogue] output/scripts/ is empty — using built-in fallback dialogue.")
        script   = random.choice(FALLBACK_DIALOGUES)
        basename = "fallback"
    else:
        script = _load_script(chosen)
        if script is None:
            print("[dialogue] Script file invalid — using built-in fallback.")
            script   = random.choice(FALLBACK_DIALOGUES)
            basename = "fallback"
        else:
            basename = os.path.splitext(os.path.basename(chosen))[0]

    print(f"[dialogue] Rendering '{basename}' ({len(script)} lines)...")
    out     = generate_dialogue_from_script(script, basename=basename, bg_image=bg_img)
    size_kb = os.path.getsize(out) / 1024
    print(f"[dialogue] Saved: {out} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()