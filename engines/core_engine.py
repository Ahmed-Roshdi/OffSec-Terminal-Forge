#!/usr/bin/env python3
"""
engines/core_engine.py  —  Core Engine / The Compilor
Applies cyberpunk glitch effects to base earth map images.

Pipeline:
  INPUT  : assets/map.png          (base earth map)
  OUTPUT : output/maps/glitched_map_{ts}.webp   (timestamped)
           output/maps/latest_glitch.webp        (fixed name for README)

Effects applied in sequence (all parameters randomised per run):
  1. RGB shift     — red/blue channel displacement (5–15 px)
  2. Scanlines     — CRT monitor overlay (spacing 3–6 px, brightness 0.1–0.4)
  3. Pixel sort    — datamosh / hue-sort rows (threshold 100–200)
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import time
from typing import List

# ── sys.path guard ──────────────────────────────────────────────────────────
_ENGINES_DIR = os.path.dirname(os.path.abspath(__file__))
if _ENGINES_DIR not in sys.path:
    sys.path.insert(0, _ENGINES_DIR)

from PIL import Image, ImageDraw

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
MAPS_DIR    = os.path.join(BASE_DIR, "output", "maps")
BASE_MAP    = os.path.join(ASSETS_DIR, "map.png")
LATEST_PATH = os.path.join(MAPS_DIR, "latest_glitch.webp")


# ── Effect functions ─────────────────────────────────────────────────────────

def load_base_image(image_path: str) -> Image.Image:
    """Load and convert base map to RGBA."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(
            f"[core_engine] Base map not found: {image_path}\n"
            f"  → Place your map at assets/map.png"
        )
    img = Image.open(image_path).convert("RGBA")
    print(f"[core_engine] Loaded: {image_path}  ({img.width}×{img.height})")
    return img


def apply_rgb_shift(image: Image.Image, shift: int = 10) -> Image.Image:
    """
    Chromatic aberration — offset red channel right, blue channel left.
    Creates the classic glitch RGB split effect.
    """
    r, g, b, a = image.split()

    # Paste channels onto offset canvases
    canvas_r = Image.new("L", image.size, 0)
    canvas_b = Image.new("L", image.size, 0)

    canvas_r.paste(r, (shift, 0))    # red shifts right
    canvas_b.paste(b, (-shift, 0))   # blue shifts left

    result = Image.merge("RGBA", (canvas_r, g, canvas_b, a))
    return result


def apply_scanlines(
    image: Image.Image,
    line_spacing: int   = 4,
    line_brightness: float = 0.2,
) -> Image.Image:
    """Overlay horizontal CRT monitor scanlines."""
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    alpha   = int(line_brightness * 255)

    for y in range(0, image.height, line_spacing):
        draw.line([(0, y), (image.width, y)], fill=(0, 0, 0, alpha), width=1)

    return Image.alpha_composite(image.convert("RGBA"), overlay)


def apply_pixel_sort(
    image: Image.Image,
    mask_threshold: int = 128,
    sort_by: str        = "hue",
) -> Image.Image:
    """
    Pixel-sort rows above a brightness threshold — classic datamosh effect.
    sort_by: 'hue' | 'saturation' | 'value'
    """
    img_hsv   = image.convert("RGB")
    result    = image.copy().convert("RGBA")
    px_in     = img_hsv.load()
    px_out    = result.load()

    sort_index = {"hue": 0, "saturation": 1, "value": 2}.get(sort_by, 0)

    for y in range(image.height):
        row: List = []
        for x in range(image.width):
            r, g, b = px_in[x, y]
            brightness = (r + g + b) // 3
            if brightness > mask_threshold:
                # Convert RGB → HSV-like tuple for sorting key
                max_c = max(r, g, b) / 255.0
                min_c = min(r, g, b) / 255.0
                delta = max_c - min_c
                # Hue
                if delta == 0:
                    h = 0.0
                elif max_c == r / 255.0:
                    h = (60 * ((g - b) / 255.0 / delta)) % 360
                elif max_c == g / 255.0:
                    h = 60 * ((b - r) / 255.0 / delta + 2)
                else:
                    h = 60 * ((r - g) / 255.0 / delta + 4)
                s = 0.0 if max_c == 0 else delta / max_c
                v = max_c
                row.append(((h, s, v), x, y))

        if len(row) > 1:
            row.sort(key=lambda t: t[0][sort_index])
            positions = [t[1] for t in row]
            for new_x, (_, orig_x, _) in zip(positions, row):
                px_out[new_x, y] = image.convert("RGBA").load()[orig_x, y]

    return result


def apply_glitch_effects(image: Image.Image) -> Image.Image:
    """
    Apply all glitch effects in sequence with randomised parameters.
    Called by main() — parameters vary on every run for unique output.
    """
    shift       = random.randint(5, 15)
    spacing     = random.randint(3, 6)
    brightness  = round(random.uniform(0.1, 0.4), 2)
    threshold   = random.randint(100, 200)
    sort_method = random.choice(["hue", "saturation", "value"])

    print(f"[core_engine] RGB shift={shift}px | scanline spacing={spacing} brightness={brightness}")
    print(f"[core_engine] Pixel sort threshold={threshold} method={sort_method}")

    img = apply_rgb_shift(image, shift=shift)
    img = apply_scanlines(img, line_spacing=spacing, line_brightness=brightness)
    img = apply_pixel_sort(img, mask_threshold=threshold, sort_by=sort_method)

    return img


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    os.makedirs(MAPS_DIR, exist_ok=True)

    print("[core_engine] Starting glitch pipeline...")
    base = load_base_image(BASE_MAP)
    glitched = apply_glitch_effects(base)

    # Save timestamped copy
    ts       = int(time.time())
    out_path = os.path.join(MAPS_DIR, f"glitched_map_{ts}.webp")
    glitched.convert("RGB").save(out_path, format="WEBP", lossless=True, quality=100)
    print(f"[core_engine] Saved: {out_path}")

    # Always overwrite latest_glitch.webp (README / downstream can reference this)
    shutil.copy2(out_path, LATEST_PATH)
    print(f"[core_engine] Updated: {LATEST_PATH}")


if __name__ == "__main__":
    main()