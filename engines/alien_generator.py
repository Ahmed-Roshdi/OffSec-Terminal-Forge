#!/usr/bin/env python3
import os
import random
import time
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# 1. Dynamic Path Resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MAPS_DIR = os.path.join(OUTPUT_DIR, "maps")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def generate_fractal_noise_map(width, height, seed):
    """
    Generates an organic, procedural topographical map using PIL's Bicubic interpolation
    to simulate Fractal Brownian Motion (fBm) Perlin Noise.
    """
    random.seed(seed)
    
    # Octave 1: Base Continents (Low frequency, high amplitude)
    img1 = Image.new('L', (width // 64, height // 64))
    img1.putdata([random.randint(0, 255) for _ in range(img1.width * img1.height)])
    img1 = img1.resize((width, height), Image.Resampling.BICUBIC)

    # Octave 2: Regional Details (Medium frequency)
    img2 = Image.new('L', (width // 32, height // 32))
    img2.putdata([random.randint(0, 255) for _ in range(img2.width * img2.height)])
    img2 = img2.resize((width, height), Image.Resampling.BICUBIC)

    # Octave 3: Fine Coastline Details (High frequency)
    img3 = Image.new('L', (width // 16, height // 16))
    img3.putdata([random.randint(0, 255) for _ in range(img3.width * img3.height)])
    img3 = img3.resize((width, height), Image.Resampling.BICUBIC)

    # Blend octaves together
    blended = Image.blend(img1, img2, 0.4) # 60% Base, 40% Regional
    blended = Image.blend(blended, img3, 0.2) # 80% Previous, 20% Fine details
    
    # Enhance contrast to make landmasses more defined
    enhancer = ImageEnhance.Contrast(blended)
    final_noise = enhancer.enhance(1.8)
    
    return final_noise

def generate_alien_world(width=1200, height=800, save_to_disk=True):
    """
    Generates a single procedural alien world and returns the Image object and its saved path.
    """
    print("[*] Initializing Organic Alien World Generator (Fractal Engine)...")
    
    # Ensure the maps directory exists
    os.makedirs(MAPS_DIR, exist_ok=True)
    
    bg_color = (13, 17, 23)
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Use a highly precise seed to allow rapid batch generation without duplicates
    current_seed = time.time_ns() 
    print(f"[*] Generating organic terrain with seed: {current_seed}")
    
    # Generate the topographical noise map
    noise_map = generate_fractal_noise_map(width, height, current_seed)
    pixels = noise_map.load()
    
    # Dynamic Sea Level (creates water worlds or desert worlds randomly)
    random.seed(current_seed)
    sea_level = random.randint(110, 140)
    coast_level = sea_level + 15
    highland_level = coast_level + 30
    peak_level = highland_level + 25
    
    dot_size = 4
    spacing = 12
    
    # Render the dot-matrix map based on topography
    for x in range(40, width - 40, spacing):
        for y in range(40, height - 160, spacing):
            elevation = pixels[x, y]
            
            if elevation > sea_level:
                # Determine biome color based on elevation
                if elevation < coast_level:
                    color = (0, 255, 255)     # Cyan (Shallow Waters / Coast)
                elif elevation < highland_level:
                    color = (0, 255, 128)     # Toxic Green (Lowlands)
                elif elevation < peak_level:
                    color = (128, 0, 255)     # Deep Purple (Highlands)
                else:
                    color = (255, 0, 128)     # Neon Pink (Mountain Peaks)
                    
                draw.ellipse([x, y, x + dot_size, y + dot_size], fill=color)
                
    # Add Planet Designation Text
    sector_id = f"{random.randint(4096, 65535):04X}"
    planet_name = f"SECTOR {sector_id} - UNKNOWN PLANET"
    
    # Font handling (Fallback mechanism)
    font_path = os.path.join(ASSETS_DIR, "fonts", "UbuntuMono-R.ttf")
    try:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 22)
        else:
            font = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
        
    # Center the text
    try:
        bbox = draw.textbbox((0, 0), planet_name, font=font)
        text_w = bbox[2] - bbox[0]
    except AttributeError:
        text_w, _ = draw.textsize(planet_name, font=font)
        
    text_x = (width - text_w) // 2
    text_y = height - 120
    
    draw.text((text_x, text_y), planet_name, fill=(139, 148, 158), font=font)
    
    output_path = None
    if save_to_disk:
        # Dynamic unique filename based on Sector ID, saved in MAPS_DIR
        filename = f"alien_sector_{sector_id}.webp"
        output_path = os.path.join(MAPS_DIR, filename)
        img.save(output_path, format='WEBP', lossless=True, quality=100)
        print(f"[+] Generated Map: {output_path}")
    
    return img, output_path

def generate_multiple_worlds(count=5):
    """
    Batch generator for creating multiple unique alien worlds.
    """
    print(f"[*] Starting batch generation of {count} alien worlds...")
    generated_files = []
    
    for i in range(count):
        _, path = generate_alien_world(save_to_disk=True)
        generated_files.append(path)
        # Small sleep to ensure time_ns() seed is distinctly different
        time.sleep(0.05) 
        
    print(f"[*] Batch generation complete. {len(generated_files)} worlds created in '{MAPS_DIR}'.")
    return generated_files

if __name__ == "__main__":
    # Test batch generation by creating 3 different planets
    generate_multiple_worlds(count=3)
