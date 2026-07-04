#!/usr/bin/env python3
"""
engines/core_engine.py  —  Core Engine / The Compilor

Parses the Islamic world map SVG, renders it as a dot-matrix image on the
gold-standard dark background, and applies the CORRECT glitch effect:
a simple horizontal x-coordinate offset on the red-channel dot layer.

IMPORTANT — RENDERING FAILURE HISTORY:
  Previous AI implementations incorrectly applied RGB channel splitting,
  numpy scanlines, and pixel-sort to this engine. ALL OF THAT WAS WRONG.
  The gold standard (output/Old-Standerd-Of-Final-Output/magic_readme.webp)
  contains NO pixel-level glitch. The only "glitch" is a 15 px horizontal
  shift of the circle x-coordinates in the red overlay layer.

Gold-standard parameters extracted via programmatic analysis:
  Canvas background : RGB(13, 17, 23)      #0d1117
  Gray text color   : RGB(139, 148, 158)   #8b949e
  Green dot color   : RGB(39, 174, 96)     #27ae60 (normal map)
  Cyan accent       : RGB(0, 212, 255)     #00d4ff
  Purple accent     : RGB(140, 30, 255)    #8c1eff
  Glitch red        : RGB(231, 76, 60)     #e74c3c
  Glitch x-offset   : 15 px (horizontal shift on red overlay only)
  SVG zoom factor   : 1.25×
  Dot render scale  : 3× (then downscaled by LANCZOS for anti-alias)
  Slogan font size  : 22 px

Pipeline:
  INPUT  : assets/islamic_world_map.svg
  OUTPUT : output/maps/glitched_map_{ts}.webp
           output/maps/latest_glitch.webp
"""
from __future__ import annotations

import math
import os
import re
import shutil
import sys
import time
from typing import List, Dict

# ── sys.path guard ──────────────────────────────────────────────────────────
_ENGINES_DIR = os.path.dirname(os.path.abspath(__file__))
if _ENGINES_DIR not in sys.path:
    sys.path.insert(0, _ENGINES_DIR)

from PIL import Image, ImageDraw

from _fonts import load_fonts

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR   = os.path.join(BASE_DIR, "assets")
MAPS_DIR     = os.path.join(BASE_DIR, "output", "maps")
SVG_PATH     = os.path.join(ASSETS_DIR, "islamic_world_map.svg")
LATEST_PATH  = os.path.join(MAPS_DIR, "latest_glitch.webp")

# ── Gold-standard color palette (extracted from magic_readme.webp analysis) ──
BG_COLOR      = (13, 17, 23)       # #0d1117 — GitHub dark mode bg
GRAY_COLOR    = (139, 148, 158)    # #8b949e — muted text
GREEN_COLOR   = (39, 174, 96)      # #27ae60 — normal Islamic dots
CYAN_COLOR    = (0, 212, 255)      # #00d4ff — OffSec accent
PURPLE_COLOR  = (140, 30, 255)     # #8c1eff — OffSec accent
GLITCH_RED    = (231, 76, 60)      # #e74c3c — glitch overlay
DARK_DOT      = (35, 40, 45)       # non-Islamic country dots

# ── Render constants (from original build_magic_gif.py) ─────────────────────
SVG_ZOOM    = 1.25    # zoom factor applied to all SVG coordinates
DOT_SCALE   = 3       # render at 3× then downscale for anti-aliasing
GLITCH_OFFSET_X = 15  # horizontal pixel shift for the glitch red layer


# ── SVG parser ────────────────────────────────────────────────────────────────
def parse_svg_circles(svg_path: str) -> List[Dict]:
    """
    Extract circle elements from the SVG.
    Applies SVG_ZOOM to all coordinates so the map fills the canvas correctly.
    Returns list of {cx, cy, r, fill} dicts.
    """
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_data = f.read()

    circles = []
    pattern = re.compile(
        r'<circle\s+cx="([^"]+)"\s+cy="([^"]+)"\s+r="([^"]+)"\s+fill="([^"]+)"'
    )
    for m in pattern.finditer(svg_data):
        circles.append({
            "cx":   float(m.group(1)) * SVG_ZOOM,
            "cy":   float(m.group(2)) * SVG_ZOOM,
            "r":    float(m.group(3)) * SVG_ZOOM,
            "fill": m.group(4),
        })

    print(f"[core_engine] Parsed {len(circles)} circles from SVG.")
    return circles


# ── Dot map renderer ──────────────────────────────────────────────────────────
def _render_dot_layer(
    circles:    List[Dict],
    canvas_w:   int,
    canvas_h:   int,
    glitch:     bool   = False,
    glitch_x:   int    = GLITCH_OFFSET_X,
) -> Image.Image:
    """
    Render all SVG circles at DOT_SCALE, then downscale to (canvas_w, canvas_h).

    Normal mode : Islamic dots (#27ae60, #f1c40f) → gradient cyan→purple
                  Others → DARK_DOT
    Glitch mode : ALL dots → GLITCH_RED, x-coordinates shifted by glitch_x px
                  (this is the ONLY glitch effect — no pixel manipulation)
    """
    scale  = DOT_SCALE
    max_cx = max(c["cx"] for c in circles)
    max_cy = max(c["cy"] for c in circles)

    img  = Image.new("RGBA", (int(max_cx * scale + 20 * scale),
                               int(max_cy * scale + 20 * scale)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    islamic_fills = {"#27ae60", "#f1c40f"}

    if not glitch:
        # Identify Mecca centroid for gradient calculation
        islamic = [c for c in circles if c["fill"] in islamic_fills]
        if islamic:
            mecca_x = min(c["cx"] for c in islamic) + (
                (max(c["cx"] for c in islamic) - min(c["cx"] for c in islamic)) * 0.48
            )
            mecca_y = min(c["cy"] for c in islamic) + (
                (max(c["cy"] for c in islamic) - min(c["cy"] for c in islamic)) * 0.45
            )
            max_dist = max(
                math.hypot(c["cx"] - mecca_x, c["cy"] - mecca_y) for c in islamic
            )
        else:
            mecca_x = mecca_y = max_dist = 1.0

    for c in circles:
        cx, cy, r = c["cx"], c["cy"], c["r"]

        if glitch:
            cx += glitch_x
            fill = GLITCH_RED + (255,)
        else:
            if c["fill"] in islamic_fills:
                dist  = math.hypot(cx - mecca_x, cy - mecca_y)
                ratio = min(dist / (max_dist * 0.5 + 1e-7), 1.0)
                red   = int(CYAN_COLOR[0] + (PURPLE_COLOR[0] - CYAN_COLOR[0]) * ratio)
                grn   = int(CYAN_COLOR[1] + (PURPLE_COLOR[1] - CYAN_COLOR[1]) * ratio)
                blu   = int(CYAN_COLOR[2] + (PURPLE_COLOR[2] - CYAN_COLOR[2]) * ratio)
                fill  = (red, grn, blu, 255)
            else:
                fill = DARK_DOT + (255,)

        cx_s, cy_s, r_s = cx * scale, cy * scale, r * scale
        draw.ellipse(
            [cx_s - r_s, cy_s - r_s, cx_s + r_s, cy_s + r_s],
            fill=fill,
        )

    return img.resize((canvas_w, canvas_h - 160), Image.Resampling.LANCZOS)


# ── Entry point ───────────────────────────────────────────────────────────────
def load_base_image(image_path: str) -> Image.Image:
    """Retained for API compatibility — loads any raster base image."""
    return Image.open(image_path).convert("RGBA")


def apply_glitch_effects(circles: List[Dict], canvas_w: int, canvas_h: int) -> Image.Image:
    """
    The CORRECT glitch: renders red dot layer with x-offset=15.
    Returns a composited RGB frame on the dark background.
    """
    fonts      = load_fonts({"slogan": 22})
    slogan_font = fonts["slogan"]
    slogan_text = "No Borders • Mutual Cooperation • One Nation"

    normal_dots = _render_dot_layer(circles, canvas_w, canvas_h, glitch=False)
    glitch_dots = _render_dot_layer(circles, canvas_w, canvas_h, glitch=True,
                                    glitch_x=GLITCH_OFFSET_X)

    def _compose(dot_layer: Image.Image) -> Image.Image:
        frame = Image.new("RGB", (canvas_w, canvas_h), color=BG_COLOR)
        offset_x = (canvas_w  - dot_layer.width)  // 2
        offset_y = (canvas_h  - 160 - dot_layer.height) // 2
        frame.paste(dot_layer, (offset_x, offset_y), dot_layer)
        draw = ImageDraw.Draw(frame)
        try:
            bbox = draw.textbbox((0, 0), slogan_text, font=slogan_font)
            slogan_w = bbox[2] - bbox[0]
        except AttributeError:
            slogan_w, _ = draw.textsize(slogan_text, font=slogan_font)
        draw.text(
            ((canvas_w - slogan_w) // 2, canvas_h - 120),
            slogan_text,
            fill=GRAY_COLOR,
            font=slogan_font,
        )
        return frame

    normal_frame = _compose(normal_dots)
    glitch_frame = _compose(glitch_dots)

    # Composite: blend normal and glitched 50/50 for the saved output
    blended = Image.blend(normal_frame, glitch_frame, alpha=0.5)
    return blended


def main() -> None:
    os.makedirs(MAPS_DIR, exist_ok=True)

    if not os.path.exists(SVG_PATH):
        print(f"[core_engine] SVG not found: {SVG_PATH}")
        print(f"  → Place islamic_world_map.svg in assets/ to activate this engine.")
        return

    print("[core_engine] Parsing SVG map data...")
    circles = parse_svg_circles(SVG_PATH)

    # Infer canvas size from SVG extents + padding
    max_cx  = max(c["cx"] for c in circles)
    max_cy  = max(c["cy"] for c in circles)
    canvas_w = int(max_cx * SVG_ZOOM + 120)
    canvas_h = int(max_cy * SVG_ZOOM + 280)

    print("[core_engine] Rendering glitch composite...")
    result = apply_glitch_effects(circles, canvas_w, canvas_h)

    ts       = int(time.time())
    out_path = os.path.join(MAPS_DIR, f"glitched_map_{ts}.webp")
    result.save(out_path, format="WEBP", lossless=True, quality=100)
    print(f"[core_engine] Saved: {out_path}")

    shutil.copy2(out_path, LATEST_PATH)
    print(f"[core_engine] Updated: {LATEST_PATH}")


if __name__ == "__main__":
    main()