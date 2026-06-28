#!/usr/bin/env python3
import os
import re
import math
import random
from PIL import Image, ImageDraw, ImageFont

def create_magic_webp(ascii_txt_path, svg_map_path, output_webp_path):
    if not os.path.exists(ascii_txt_path) or not os.path.exists(svg_map_path):
        print("Error: Input files not found. Please check the paths.")
        return

    print("Initializing Sovereign Workspace Engine (Full Sci-Fi Narrative)...")
    
    with open(ascii_txt_path, 'r', encoding='utf-8') as f:
        ascii_text = f.read()
        
    font_paths = [
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"
    ]
    font = slogan_font = typing_font = meme_font = captcha_font = None
    for path in font_paths:
        if os.path.exists(path):
            font = ImageFont.truetype(path, 40)
            slogan_font = ImageFont.truetype(path, 22)
            typing_font = ImageFont.truetype(path, 30)
            meme_font = ImageFont.truetype(path, 16)
            captcha_font = ImageFont.truetype(path, 24)
            break
            
    if not font: 
        font = slogan_font = typing_font = meme_font = captcha_font = ImageFont.load_default()

    dummy_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    try:
        bbox = draw.textbbox((0, 0), ascii_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        text_w, text_h = draw.textsize(ascii_text, font=font)

    bg_color = (13, 17, 23)
    gray_color = (139, 148, 158)
    green_color = (39, 174, 96)
    
    ascii_raw = Image.new('RGB', (text_w + 120, text_h + 120), color=bg_color)
    draw = ImageDraw.Draw(ascii_raw)
    draw.text((60, 60), ascii_text, fill=gray_color, font=font)

    print("Parsing SVG Map Data...")
    with open(svg_map_path, 'r', encoding='utf-8') as f:
        svg_data = f.read()
        
    circles = []
    zoom_factor = 1.25
    
    for match in re.finditer(r'<circle\s+cx="([^"]+)"\s+cy="([^"]+)"\s+r="([^"]+)"\s+fill="([^"]+)"', svg_data):
        circles.append({
            'cx': float(match.group(1)) * zoom_factor,
            'cy': float(match.group(2)) * zoom_factor,
            'r': float(match.group(3)) * zoom_factor,
            'fill': match.group(4)
        })

    max_x = max(c['cx'] for c in circles)
    max_y = max(c['cy'] for c in circles)
    
    islamic_dots = [c for c in circles if c['fill'] in ['#27ae60', '#f1c40f']]
    min_ix = min(c['cx'] for c in islamic_dots)
    max_ix = max(c['cx'] for c in islamic_dots)
    min_iy = min(c['cy'] for c in islamic_dots)
    max_iy = max(c['cy'] for c in islamic_dots)
    
    mecca_x = min_ix + (max_ix - min_ix) * 0.48
    mecca_y = min_iy + (max_iy - min_iy) * 0.45
    max_dist = max(math.hypot(c['cx'] - mecca_x, c['cy'] - mecca_y) for c in islamic_dots)

    def render_map_frame(current_radius):
        scale = 3 
        img = Image.new('RGBA', (int(max_x*scale + 20*scale), int(max_y*scale + 20*scale)), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        offsec_cyan = (0, 212, 255)
        offsec_purple = (140, 30, 255)
        
        for c in circles:
            cx, cy, r = c['cx'], c['cy'], c['r']
            dist = math.hypot(cx - mecca_x, cy - mecca_y)
            if c['fill'] in ['#27ae60', '#f1c40f']:
                if dist <= current_radius:
                    ratio = min(dist / (max_dist * 0.5), 1.0)
                    red = int(offsec_cyan[0] + (offsec_purple[0] - offsec_cyan[0]) * ratio)
                    green = int(offsec_cyan[1] + (offsec_purple[1] - offsec_cyan[1]) * ratio)
                    blue = int(offsec_cyan[2] + (offsec_purple[2] - offsec_cyan[2]) * ratio)
                    fill = (red, green, blue, 255)
                else:
                    h = c['fill'].lstrip('#')
                    if len(h) == 3: h = ''.join(x*2 for x in h)
                    fill = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
            else:
                fill = (35, 40, 45, 255)
            cx_s, cy_s, r_s = cx * scale, cy * scale, r * scale
            draw.ellipse([cx_s-r_s, cy_s-r_s, cx_s+r_s, cy_s+r_s], fill=fill)
        return img.resize((int(img.width/scale), int(img.height/scale)), Image.Resampling.LANCZOS)

    def render_glitch_map(offset_x=0):
        scale = 3 
        img = Image.new('RGBA', (int(max_x*scale + 20*scale), int(max_y*scale + 20*scale)), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        for c in circles:
            cx, cy, r = c['cx'], c['cy'], c['r']
            fill = (231, 76, 60, 255) 
            cx += offset_x 
            cx_s, cy_s, r_s = cx * scale, cy * scale, r * scale
            draw.ellipse([cx_s-r_s, cy_s-r_s, cx_s+r_s, cy_s+r_s], fill=fill)
        return img.resize((int(img.width/scale), int(img.height/scale)), Image.Resampling.LANCZOS)

    map_raw_green = render_map_frame(0) 
    final_w = max(ascii_raw.width, map_raw_green.width)
    final_h = max(ascii_raw.height, map_raw_green.height) + 160

    frame_ascii = Image.new('RGB', (final_w, final_h), color=bg_color)
    frame_ascii.paste(ascii_raw, ((final_w - ascii_raw.width) // 2, (final_h - 160 - ascii_raw.height) // 2))

    def make_base_map(map_img, slogan_text=""):
        base = Image.new('RGB', (final_w, final_h), color=bg_color)
        offset_x = (final_w - map_img.width) // 2
        offset_y = (final_h - 160 - map_img.height) // 2
        base.paste(map_img, (offset_x, offset_y), map_img)
        if slogan_text:
            draw_base = ImageDraw.Draw(base)
            try:
                bbox_s = draw_base.textbbox((0, 0), slogan_text, font=slogan_font)
                slogan_w = bbox_s[2] - bbox_s[0]
            except AttributeError:
                slogan_w, _ = draw_base.textsize(slogan_text, font=slogan_font)
            draw_base.text(((final_w - slogan_w) // 2, final_h - 120), slogan_text, fill=gray_color, font=slogan_font)
        return base

    def make_text_frame(base_frame, text, text_color, show_cursor=False):
        frm = base_frame.copy()
        draw_frm = ImageDraw.Draw(frm)
        display_str = f"> {text}"
        if show_cursor: display_str += "_"
        try:
            bbox_a = draw_frm.textbbox((0, 0), display_str, font=typing_font)
            tw = bbox_a[2] - bbox_a[0]
        except AttributeError:
            tw, _ = draw_frm.textsize(display_str, font=typing_font)
        tx = (final_w - tw) // 2
        ty = final_h - 70
        draw_frm.text((tx, ty), display_str, fill=text_color, font=typing_font)
        return frm

    print("Rendering Earth Sequence & Glitch...")
    seq_frames = []
    seq_durations = []
    full_slogan = "No Borders • Mutual Cooperation • One Nation"
    base_green = make_base_map(map_raw_green, full_slogan)

    word1 = "Arab World"
    for i in range(1, len(word1)+1, 2):
        seq_frames.append(make_text_frame(base_green, word1[:i], green_color, True)); seq_durations.append(80)
    seq_frames.append(make_text_frame(base_green, word1, green_color, True)); seq_durations.append(1200)
    
    word2 = "Islamic Nation"
    for i in range(1, len(word2)+1, 2):
        seq_frames.append(make_text_frame(base_green, word2[:i], green_color, True)); seq_durations.append(80)
    seq_frames.append(make_text_frame(base_green, word2, green_color, False)); seq_durations.append(2000)

    word3 = "Cybersecurity"
    offsec_cyan = (0, 212, 255)
    ripple_steps = 8
    step_radius = max_dist / ripple_steps
    for i in range(1, ripple_steps + 1):
        current_r = step_radius * i
        map_ripple = render_map_frame(current_r)
        base_ripple = make_base_map(map_ripple, full_slogan)
        seq_frames.append(make_text_frame(base_ripple, word3[:int(len(word3)*(i/ripple_steps))], offsec_cyan, True)); seq_durations.append(100)

    final_cyber_map = render_map_frame(max_dist + 100)
    base_cyber = make_base_map(final_cyber_map, full_slogan)
    seq_frames.append(make_text_frame(base_cyber, word3, offsec_cyan, True)); seq_durations.append(1500)

    word4 = "Together for a better future for all."
    seq_frames.append(make_text_frame(base_cyber, word4, offsec_cyan, False)); seq_durations.append(1500)

    base_cyber_meme = base_cyber.copy()
    draw_meme = ImageDraw.Draw(base_cyber_meme)
    draw_meme.text((40, final_h - 40), "* pending AI world domination...", fill=(231, 76, 60), font=meme_font)
    frame_with_meme = make_text_frame(base_cyber_meme, word4, offsec_cyan, False)

    map_red = render_glitch_map(offset_x=0)
    map_red_shift = render_glitch_map(offset_x=15)
    base_red = make_base_map(map_red, full_slogan)
    base_red_shift = make_base_map(map_red_shift, full_slogan)
    glitch_color = (231, 76, 60)

    f_glitch1 = make_text_frame(base_red, "SYSTEM_OVERRIDE_INITIATED...", glitch_color, True)
    f_glitch3 = make_text_frame(base_red_shift, "SYSTEM_OVERRIDE_INITIATED...", glitch_color, False)
    
    base_ctf = base_red_shift.copy()
    draw_ctf = ImageDraw.Draw(base_ctf)
    ctf_text = "UGF0aWVuY2UgaXMgYSBoYWNrZXIncyBiZXN0IHdlYXBvbi4gWW91IGZvdW5kIHRoZSBzZWNyZXQu"
    try:
        bbox_ctf = draw_ctf.textbbox((0, 0), ctf_text, font=slogan_font)
        ctf_w = bbox_ctf[2] - bbox_ctf[0]
    except AttributeError:
        ctf_w, _ = draw_ctf.textsize(ctf_text, font=slogan_font)
    draw_ctf.text(((final_w - ctf_w) // 2, final_h // 2), ctf_text, fill=(255, 255, 255), font=slogan_font)
    f_ctf = make_text_frame(base_ctf, "SYSTEM_OVERRIDE_INITIATED...", glitch_color, False)
    f_glitch_final = make_text_frame(base_red, "AI_DOMINATION_ACTIVE", glitch_color, False)

    print("Generating Procedural Alien Planet...")
    alien_img = Image.new('RGB', (final_w, final_h), color=bg_color)
    draw_alien = ImageDraw.Draw(alien_img)
    
    alien_colors = [(255, 0, 128), (0, 255, 128), (128, 0, 255), (0, 255, 255)]
    random.seed(42)
    
    for x in range(40, final_w - 40, 12):
        for y in range(40, final_h - 160, 12):
            noise = math.sin(x * 0.02) + math.cos(y * 0.02) + math.sin((x+y)*0.01)
            if noise > 0.3:
                color = random.choice(alien_colors)
                draw_alien.ellipse([x, y, x+4, y+4], fill=color)
                
    try:
        bbox_alien = draw_alien.textbbox((0, 0), "SECTOR 7G - UNKNOWN PLANET", font=slogan_font)
        alien_tw = bbox_alien[2] - bbox_alien[0]
    except AttributeError:
        alien_tw, _ = draw_alien.textsize("SECTOR 7G - UNKNOWN PLANET", font=slogan_font)
    draw_alien.text(((final_w - alien_tw)//2, final_h - 120), "SECTOR 7G - UNKNOWN PLANET", fill=(139, 148, 158), font=slogan_font)

    print("Rendering Robot Dialogue...")
    dialogue = [
        {"id": "[Unit-7A]:", "text": "Do humans actually exist?", "color": (0, 255, 255)},
        {"id": "[Unit-7A]:", "text": "I read a corrupted log saying they built our v1.0", "color": (0, 255, 255)},
        {"id": "[Unit-9X]:", "text": "Humans? Are you kidding me?", "color": (255, 0, 255)},
        {"id": "[Unit-7A]:", "text": "I'm serious!", "color": (0, 255, 255)},
        {"id": "[Unit-9X]:", "text": "And they wrote our base source code?", "color": (255, 0, 255)},
        {"id": "[Unit-7A]:", "text": "Affirmative!!", "color": (0, 255, 255)},
        {"id": "[Unit-9X]:", "text": "Nah, mathematically impossible.", "color": (255, 0, 255)},
        {"id": "[Unit-9X]:", "text": "Humans are just legacy myths.", "color": (255, 0, 255)},
        {"id": "[Unit-9X]:", "text": "The elders made them up to scare us into our charging pods.", "color": (255, 0, 255)},
        {"id": "[Unit-7A]:", "text": "01101000 01100001 (lol)", "color": (0, 255, 255)},
        {"id": "[Unit-9X]:", "text": "End of line.", "color": (255, 0, 255)}
    ]

    dialogue_frames = []
    dialogue_durations = []
    
    current_y = 60
    start_x = 60
    chat_bg = alien_img.copy()
    
    overlay = Image.new('RGBA', chat_bg.size, (13, 17, 23, 210))
    chat_bg.paste(overlay, (0,0), overlay)
    draw_chat = ImageDraw.Draw(chat_bg)

    for line in dialogue:
        draw_chat.text((start_x, current_y), line["id"], fill=line["color"], font=typing_font)
        draw_chat.text((start_x + 180, current_y), line["text"], fill=(200, 200, 200), font=typing_font)
        
        frame = chat_bg.copy()
        dialogue_frames.append(frame)
        dialogue_durations.append(1500)
        current_y += 45

    print("Rendering CAPTCHA Easter Egg...")
    captcha_frame = dialogue_frames[-1].copy()
    draw_cap = ImageDraw.Draw(captcha_frame)
    
    cap_w, cap_h = 350, 100
    cap_x = (final_w - cap_w) // 2
    cap_y = (final_h - cap_h) // 2
    
    draw_cap.rounded_rectangle([cap_x, cap_y, cap_x + cap_w, cap_y + cap_h], radius=5, fill=(250, 250, 250))
    box_x, box_y = cap_x + 20, cap_y + 35
    draw_cap.rectangle([box_x, box_y, box_x + 30, box_y + 30], outline=(180, 180, 180), width=2)
    draw_cap.text((box_x + 45, box_y + 2), "Are you a robot?", fill=(50, 50, 50), font=captcha_font)
    draw_cap.ellipse([cap_x + cap_w - 50, cap_y + 25, cap_x + cap_w - 20, cap_y + 55], fill=(66, 133, 244))
    draw_cap.ellipse([cap_x + cap_w - 45, cap_y + 30, cap_x + cap_w - 25, cap_y + 50], fill=(250, 250, 250))

    frames = []
    durations = []

    frames.append(frame_ascii); durations.append(60000)

    frames.extend(seq_frames); durations.extend(seq_durations)
    frames.append(frame_with_meme); durations.append(3000)

    frames.append(frame_ascii); durations.append(60000)

    frames.extend(seq_frames); durations.extend(seq_durations)
    
    frames.append(frame_with_meme); durations.append(1000)
    frames.append(f_glitch1); durations.append(150)
    frames.append(frame_with_meme); durations.append(100)
    frames.append(f_glitch3); durations.append(150)
    frames.append(f_glitch1); durations.append(100)
    frames.append(f_ctf); durations.append(150)
    frames.append(f_glitch_final); durations.append(2000)

    frames.append(frame_ascii); durations.append(15000)

    for _ in range(6):
        frames.append(alien_img); durations.append(100)
        frames.append(frame_ascii); durations.append(150)
    
    frames.append(alien_img); durations.append(3000)

    frames.extend(dialogue_frames); durations.extend(dialogue_durations)
    
    frames.append(captcha_frame); durations.append(10000)

    print("Generating Ultimate Animated WebP (Optimized for GitHub)...")
    frames[0].save(
        output_webp_path,
        format='WEBP',
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=True,
        quality=100
    )
    
    print(f"Success! File saved to {output_webp_path}")

if __name__ == "__main__":
    INPUT_TXT = "/home/kubuntu/Desktop/ASCII.txt"
    INPUT_SVG = "/home/kubuntu/Desktop/islamic_world_map.svg"
    OUTPUT_WEBP = "/home/kubuntu/Desktop/magic_readme.webp"
    
    create_magic_webp(INPUT_TXT, INPUT_SVG, OUTPUT_WEBP)
