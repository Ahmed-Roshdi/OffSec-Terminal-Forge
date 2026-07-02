#!/usr/bin/env python3
"""
engines/core_engine.py  —  Core Engine / The Compilor
Applies cyberpunk glitch effects to a base earth map image.

Pipeline:
  INPUT  : assets/map.png
  OUTPUT : output/maps/glitched_map_{ts}.webp   (timestamped)
           output/maps/latest_glitch.webp        (fixed name for README)

Effects (applied in sequence, parameters randomised per run):
  1. RGB shift   — chromatic aberration, red/blue channel offset  (5–15 px)
  2. Scanlines   — CRT monitor overlay                            (3–6 px spacing)
  3. Pixel sort  — hue/luma sort per row above brightness threshold
                   (uses numpy — fast vectorised ops, <1s on 1200×800)
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import time

# ── sys.path guard ──────────────────────────────────────────────────────────
_ENGINES_DIR = os.path.dirname(os.path.abspath(__file__))
if _ENGINES_DIR not in sys.path:
    sys.path.insert(0, _ENGINES_DIR)

import numpy as np
from PIL import Image, ImageDraw

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
MAPS_DIR    = os.path.join(BASE_DIR, "output", "maps")
BASE_MAP    = os.path.join(ASSETS_DIR, "map.png")
LATEST_PATH = os.path.join(MAPS_DIR, "latest_glitch.webp")

# ── Max working resolution — resize before processing to cap run time ───────
MAX_W, MAX_H = 1200, 800


# ── Effect functions ─────────────────────────────────────────────────────────

def load_base_image(image_path: str) -> Image.Image:
    """Load, resize to processing cap, and convert to RGBA."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(
            f"[core_engine] Base map not found: {image_path}\n"
            f"  → Add your earth map at assets/map.png to activate this engine."
        )
    img = Image.open(image_path).convert("RGBA")
    if img.width > MAX_W or img.height > MAX_H:
        img.thumbnail((MAX_W, MAX_H), Image.Resampling.LANCZOS)
    print(f"[core_engine] Loaded: {image_path}  ({img.width}×{img.height})")
    return img


def apply_rgb_shift(image: Image.Image, shift: int = 10) -> Image.Image:
    """
    Chromatic aberration — red channel shifts right, blue shifts left.
    Operates on numpy arrays: fast even for large images.
    """
    arr = np.array(image)          # H × W × 4  (RGBA)
    h, w = arr.shape[:2]
    result = arr.copy()

    # Red channel: shift right by `shift` pixels
    if shift < w:
        result[:, shift:,  0] = arr[:, :w - shift, 0]
        result[:, :shift,  0] = 0

    # Blue channel: shift left by `shift` pixels
    if shift < w:
        result[:, :w - shift, 2] = arr[:, shift:, 2]
        result[:, w - shift:, 2] = 0

    return Image.fromarray(result.astype(np.uint8), "RGBA")


def apply_scanlines(
    image: Image.Image,
    line_spacing:    int   = 4,
    line_brightness: float = 0.2,
) -> Image.Image:
    """Overlay dark horizontal CRT scanlines using PIL draw (fast)."""
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    alpha   = int(line_brightness * 255)

    for y in range(0, image.height, line_spacing):
        draw.line([(0, y), (image.width, y)], fill=(0, 0, 0, alpha), width=1)

    return Image.alpha_composite(image.convert("RGBA"), overlay)


def apply_pixel_sort(
    image:          Image.Image,
    mask_threshold: int = 128,
    sort_by:        str = "luma",
) -> Image.Image:
    """
    Sort pixels within each row that exceed a brightness threshold.
    Produces the classic glitch-art datamosh streak effect.

    Uses numpy for full vectorised row operations — runs in <1s on 1200×800.
    sort_by: 'luma' | 'hue' | 'saturation' | 'value'
    """
    arr = np.array(image.convert("RGBA"), dtype=np.uint8)  # H × W × 4
    h, w = arr.shape[:2]

    rgb = arr[:, :, :3].astype(np.float32)   # H × W × 3

    # ── Compute per-pixel sort key ─────────────────────────────────────────
    if sort_by in ("luma", "value"):
        # BT.601 luma — fast, single weighted sum
        key = (rgb[:, :, 0] * 0.299 +
               rgb[:, :, 1] * 0.587 +
               rgb[:, :, 2] * 0.114)           # H × W

    elif sort_by == "saturation":
        max_c = rgb.max(axis=2)
        min_c = rgb.min(axis=2)
        delta = max_c - min_c
        key   = np.where(max_c > 0, delta / (max_c + 1e-7), 0.0)

    elif sort_by == "hue":
        # Approximate hue using red channel dominance vs green (good enough for sorting)
        key = rgb[:, :, 0] - rgb[:, :, 1]      # H × W
    else:
        key = rgb.mean(axis=2)

    # ── Per-row sort (only pixels above threshold) ─────────────────────────
    luma_mask = key > mask_threshold            # H × W  boolean

    for y in range(h):
        row_mask = luma_mask[y]                 # W boolean
        if row_mask.sum() < 2:
            continue

        indices = np.where(row_mask)[0]         # positions to sort
        sort_order = np.argsort(key[y, indices])
        sorted_indices = indices[sort_order]

        # Write sorted pixels back (bright pixels exchange positions)
        original_pixels = arr[y, indices].copy()
        arr[y, sorted_indices] = original_pixels

    return Image.fromarray(arr, "RGBA")


def apply_glitch_effects(image: Image.Image) -> Image.Image:
    """
    Apply all three effects in sequence with randomised parameters.
    Each call produces a unique glitched variant.
    """
    shift      = random.randint(5, 15)
    spacing    = random.randint(3, 6)
    brightness = round(random.uniform(0.1, 0.4), 2)
    threshold  = random.randint(100, 200)
    sort_method= random.choice(["luma", "hue", "saturation", "value"])

    print(f"[core_engine] RGB shift={shift}px")
    print(f"[core_engine] Scanlines spacing={spacing} brightness={brightness}")
    print(f"[core_engine] Pixel sort threshold={threshold} method={sort_method}")

    t0  = time.time()
    img = apply_rgb_shift(image,    shift=shift)
    t1  = time.time()
    img = apply_scanlines(img,      line_spacing=spacing, line_brightness=brightness)
    t2  = time.time()
    img = apply_pixel_sort(img,     mask_threshold=threshold, sort_by=sort_method)
    t3  = time.time()

    print(f"[core_engine] Timings — rgb_shift: {t1-t0:.2f}s | "
          f"scanlines: {t2-t1:.2f}s | pixel_sort: {t3-t2:.2f}s | "
          f"total: {t3-t0:.2f}s")
    return img


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    os.makedirs(MAPS_DIR, exist_ok=True)
    print("[core_engine] Starting glitch pipeline...")

    base     = load_base_image(BASE_MAP)
    glitched = apply_glitch_effects(base)

    ts       = int(time.time())
    out_path = os.path.join(MAPS_DIR, f"glitched_map_{ts}.webp")
    glitched.convert("RGB").save(out_path, format="WEBP", lossless=True, quality=100)
    print(f"[core_engine] Saved: {out_path}")

    shutil.copy2(out_path, LATEST_PATH)
    print(f"[core_engine] Updated: {LATEST_PATH}")


if __name__ == "__main__":
    main()