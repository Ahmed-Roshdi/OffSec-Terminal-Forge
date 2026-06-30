import os
from PIL import ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

def load_fonts(sizes: dict) -> dict:
    """
    Load fonts of specified sizes.
    sizes: dict of {name: size}, e.g., {"label": 22, "title": 30}
    Returns: dict of {name: ImageFont instance}
    """
    fonts = {}
    font_path = None
    
    # Auto-detect any .ttf font in the assets/fonts directory
    if os.path.exists(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if f.endswith(".ttf"):
                font_path = os.path.join(FONTS_DIR, f)
                break

    for name, size in sizes.items():
        if font_path:
            try:
                fonts[name] = ImageFont.truetype(font_path, size)
                continue
            except Exception as e:
                print(f"[!] Failed to load font {font_path}: {e}")
        
        # Fallback to default PIL font if custom font fails or is missing
        fonts[name] = ImageFont.load_default()
        
    return fonts
