#!/usr/bin/env python3
"""
engines/alien_generator.py
Fractal noise terrain engine — generates dot-matrix alien world maps.

Output:
  output/maps/alien_sector_{ID}.webp   ← timestamped unique map
  output/maps/latest_map.webp          ← always overwritten (README uses this)
"""
import os
import random
import shutil
import time

from PIL import Image, ImageDraw, ImageEnhance

from _fonts import load_fonts

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MAPS_DIR   = os.path.join(OUTPUT_DIR, "maps")
LATEST_MAP = os.path.join(MAPS_DIR, "latest_map.webp")


def generate_fractal_noise_map(width: int, height: int, seed: int) -> Image.Image:
    """Bicubic-upscaled multi-octave noise — simulates Fractal Brownian Motion."""
    random.seed(seed)

    def _octave(divisor: int) -> Image.Image:
        img = Image.new("L", (width // divisor, height // divisor))
        img.putdata([random.randint(0, 255) for _ in range(img.width * img.height)])
        return img.resize((width, height), Image.Resampling.BICUBIC)

    o1 = _octave(64)   # continents
    o2 = _octave(32)   # regions
    o3 = _octave(16)   # coastline detail

    blended = Image.blend(o1, o2, 0.4)
    blended = Image.blend(blended, o3, 0.2)
    return ImageEnhance.Contrast(blended).enhance(1.8)


def generate_alien_world(
    width:        int  = 1200,
    height:       int  = 800,
    save_to_disk: bool = True,
):
    """Generate a single procedural alien world. Returns (Image, output_path | None)."""
    print("[*] Initializing Organic Alien World Generator (Fractal Engine)...")
    os.makedirs(MAPS_DIR, exist_ok=True)

    seed = time.time_ns()
    print(f"[*] Generating organic terrain with seed: {seed}")

    img  = Image.new("RGB", (width, height), color=(13, 17, 23))
    draw = ImageDraw.Draw(img)

    noise_map = generate_fractal_noise_map(width, height, seed)
    pixels    = noise_map.load()

    random.seed(seed)
    sea_level      = random.randint(110, 140)
    coast_level    = sea_level      + 15
    highland_level = coast_level    + 30
    peak_level     = highland_level + 25

    for x in range(40, width - 40, 12):
        for y in range(40, height - 160, 12):
            elev = pixels[x, y]
            if elev > sea_level:
                if   elev < coast_level:    color = (0,   255, 255)
                elif elev < highland_level: color = (0,   255, 128)
                elif elev < peak_level:     color = (128, 0,   255)
                else:                       color = (255, 0,   128)
                draw.ellipse([x, y, x + 4, y + 4], fill=color)

    sector_id   = f"{random.randint(4096, 65535):04X}"
    planet_name = f"SECTOR {sector_id} - UNKNOWN PLANET"
    fonts       = load_fonts({"label": 22})
    font        = fonts["label"]

    try:
        bbox   = draw.textbbox((0, 0), planet_name, font=font)
        text_w = bbox[2] - bbox[0]
    except AttributeError:
        text_w, _ = draw.textsize(planet_name, font=font)

    draw.text(((width - text_w) // 2, height - 120),
              planet_name, fill=(139, 148, 158), font=font)

    output_path = None
    if save_to_disk:
        filename    = f"alien_sector_{sector_id}.webp"
        output_path = os.path.join(MAPS_DIR, filename)
        img.save(output_path, format="WEBP", lossless=True, quality=100)
        print(f"[+] Generated Map: {output_path}")

    return img, output_path


def generate_multiple_worlds(count: int = 1) -> list:
    print(f"[*] Starting batch generation of {count} alien world(s)...")
    generated = []

    for _ in range(count):
        _, path = generate_alien_world(save_to_disk=True)
        generated.append(path)
        time.sleep(0.05)

    # Keep latest_map.webp pointing to the most recent generation (README uses this)
    if generated:
        shutil.copy2(generated[-1], LATEST_MAP)
        print(f"[+] Updated: {LATEST_MAP}")

    print(f"[*] Batch complete. {len(generated)} world(s) in '{MAPS_DIR}'.")
    return generated


if __name__ == "__main__":
    count = int(os.getenv("MAPS_PER_RUN", "1"))
    generate_multiple_worlds(count=count)