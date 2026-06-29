#!/usr/bin/env python3
"""
Process base earth maps into cyberpunk dot-matrix frames with glitch effects.

Reads a raster base map from assets/, remaps biomes to OffSec palette,
renders a dot grid, then applies slice-shift / RGB-channel glitch.
Output: output/maps/earth_glitch_{SECTOR}.webp
"""
from __future__ import annotations

import os
import random
import time
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance

from _fonts import load_fonts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "maps")

BASE_MAP_CANDIDATES = [
    os.path.join(ASSETS_DIR, "map.png"),
    os.path.join(ASSETS_DIR, "Muslim_world_map-ar-colored.png"),
    os.path.join(ASSETS_DIR, "Muslim_world_map-ar1.png"),
]

# OffSec terminal palette (R, G, B)
PALETTE = {
    "deep": (13, 17, 23),
    "cyan": (0, 212, 255),
    "green": (0, 255, 128),
    "purple": (128, 0, 255),
    "pink": (255, 0, 128),
    "amber": (255, 200, 0),
    "grey": (74, 74, 74),
    "muted": (139, 148, 158),
}


def _resolve_base_map() -> str:
    override = os.getenv("BASE_MAP", "").strip()
    if override and os.path.isfile(override):
        return override
    for path in BASE_MAP_CANDIDATES:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "No base earth map found. Set BASE_MAP or add assets/map.png."
    )


def _classify_pixel(r: int, g: int, b: int) -> Tuple[int, int, int]:
    """Map source pixels to cyberpunk biome colors."""
    brightness = (r + g + b) / 3
    if g > r + 30 and g > b + 20:
        return PALETTE["green"] if g > 160 else PALETTE["cyan"]
    if r > 180 and g > 150 and b < 80:
        return PALETTE["amber"]
    if brightness < 45:
        return PALETTE["deep"]
    if brightness < 110:
        return PALETTE["grey"]
    if r > b + 40:
        return PALETTE["pink"]
    return PALETTE["purple"]


def _render_dot_matrix(
    source: Image.Image,
    width: int = 1200,
    height: int = 800,
    spacing: int = 10,
    dot_size: int = 4,
) -> Image.Image:
    src = source.convert("RGB")
    src.thumbnail((width - 80, height - 160), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), color=PALETTE["deep"])
    draw = ImageDraw.Draw(canvas)

    ox = (width - src.width) // 2
    oy = (height - src.height) // 2 - 40

    for y in range(0, src.height, max(1, spacing // 2)):
        for x in range(0, src.width, max(1, spacing // 2)):
            r, g, b = src.getpixel((x, y))
            color = _classify_pixel(r, g, b)
            if color == PALETTE["deep"]:
                continue
            px = ox + x
            py = oy + y
            draw.ellipse([px, py, px + dot_size, py + dot_size], fill=color)

    return canvas


def _apply_glitch(img: Image.Image, seed: int, intensity: float = 0.35) -> Image.Image:
    """Horizontal slice shifts + RGB channel offset."""
    random.seed(seed)
    out = img.copy()
    w, h = out.size

    # RGB channel separation bands
    sep = Image.new("RGB", (w, h))
    src = img.load()
    shift = max(2, int(w * 0.008))
    for y in range(h):
        for x in range(w):
            r = src[min(w - 1, x + shift), y][0]
            g = src[x, y][1]
            b = src[max(0, x - shift), y][2]
            sep.putpixel((x, y), (r, g, b))
    out = Image.blend(img, sep, alpha=intensity * 0.5)

    # Horizontal slice displacement
    glitched = out.copy()
    bands = random.randint(4, 10)
    for _ in range(bands):
        y0 = random.randint(0, max(0, h - 20))
        band_h = random.randint(8, max(9, h // 12))
        y1 = min(h, y0 + band_h)
        dx = random.randint(-int(w * 0.04), int(w * 0.04))
        region = out.crop((0, y0, w, y1))
        glitched.paste(region, (dx, y0))

    # Scanline noise strips
    draw = ImageDraw.Draw(glitched)
    for _ in range(random.randint(6, 14)):
        y = random.randint(0, h - 1)
        alpha = random.randint(20, 60)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0), width=1)

    enhancer = ImageEnhance.Contrast(glitched)
    return enhancer.enhance(1.15)


def _draw_sector_label(img: Image.Image, sector_id: str) -> Image.Image:
    draw = ImageDraw.Draw(img)
    label = f"EARTH SECTOR {sector_id} // GLITCH RECON"
    fonts = load_fonts({"label": 22})
    font = fonts["label"]
    w, h = img.size
    try:
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(label, font=font)
    draw.text(((w - tw) // 2, h - 100), label, fill=PALETTE["muted"], font=font)
    return img


def generate_glitch_map(
    save_to_disk: bool = True,
    width: int = 1200,
    height: int = 800,
) -> Tuple[Image.Image, Optional[str]]:
    print("[*] core_engine: loading base earth map...")
    base_path = _resolve_base_map()
    print(f"[*] core_engine: source = {base_path}")

    source = Image.open(base_path)
    seed = time.time_ns()
    random.seed(seed)

    dotted = _render_dot_matrix(source, width=width, height=height)
    glitched = _apply_glitch(dotted, seed=seed)

    sector_id = f"{random.randint(4096, 65535):04X}"
    glitched = _draw_sector_label(glitched, sector_id)

    output_path = None
    if save_to_disk:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"earth_glitch_{sector_id}.webp")
        glitched.save(output_path, format="WEBP", lossless=True, quality=100)
        print(f"[+] core_engine: saved {output_path}")

    return glitched, output_path


def main() -> None:
    generate_glitch_map()


if __name__ == "__main__":
    main()
