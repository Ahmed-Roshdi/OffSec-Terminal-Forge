#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont

def create_magic_gif(ascii_txt_path, map_img_path, output_gif_path):
    if not os.path.exists(ascii_txt_path) or not os.path.exists(map_img_path):
        print("Error: Input files not found.")
        return

    print("Processing raw files...")
    
    map_img = Image.open(map_img_path).convert("RGB")
    
    with open(ascii_txt_path, 'r', encoding='utf-8') as f:
        ascii_text = f.read()
        
    font_paths = [
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf"
    ]
    font = None
    for path in font_paths:
        if os.path.exists(path):
            font = ImageFont.truetype(path, 24)
            break
    if not font:
        font = ImageFont.load_default()

    dummy_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    try:
        bbox = draw.textbbox((0, 0), ascii_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        text_w, text_h = draw.textsize(ascii_text, font=font)

    bg_color = (13, 17, 23)
    ascii_frame = Image.new('RGB', (text_w + 100, text_h + 100), color=bg_color)
    draw = ImageDraw.Draw(ascii_frame)
    draw.text((50, 50), ascii_text, fill=(39, 174, 96), font=font)

    map_w, map_h = map_img.size
    ratio = min((ascii_frame.width - 50) / map_w, (ascii_frame.height - 50) / map_h)
    new_map_w = int(map_w * ratio)
    new_map_h = int(map_h * ratio)
    map_resized = map_img.resize((new_map_w, new_map_h), Image.Resampling.LANCZOS)

    map_frame = Image.new('RGB', ascii_frame.size, color=bg_color)
    offset_x = (ascii_frame.width - new_map_w) // 2
    offset_y = (ascii_frame.height - new_map_h) // 2
    map_frame.paste(map_resized, (offset_x, offset_y))

    durations = [60000, 15000, 300000, 5000]
    frames = [ascii_frame, map_frame, ascii_frame, map_frame]

    print("Generating Animated GIF...")
    frames[0].save(
        output_gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0
    )
    print(f"Success! File saved to {output_gif_path}")

if __name__ == "__main__":
    INPUT_TXT = "/home/kubuntu/Desktop/aqsa.txt"
    INPUT_MAP = "/home/kubuntu/Desktop/Muslim_world_map-ar-colored.png"
    OUTPUT_GIF = "/home/kubuntu/Desktop/magic_readme.gif"
    
    create_magic_gif(INPUT_TXT, INPUT_MAP, OUTPUT_GIF)
