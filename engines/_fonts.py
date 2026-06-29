"""Shared font resolution for GitHub runners and local dev."""
from __future__ import annotations

import os
from typing import Dict

from PIL import ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Ubuntu Mono ships with `fonts-ubuntu` on ubuntu-latest runners.
RUNNER_FONTS = [
    os.path.join(ASSETS_DIR, "fonts", "UbuntuMono-R.ttf"),
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def load_fonts(sizes: Dict[str, int]) -> Dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    for path in RUNNER_FONTS:
        if os.path.exists(path):
            try:
                return {key: ImageFont.truetype(path, size) for key, size in sizes.items()}
            except OSError:
                continue
    default = ImageFont.load_default()
    return {key: default for key in sizes}
