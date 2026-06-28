#!/usr/bin/env python3
import os
import random
import textwrap
import time
import json
import urllib.request
import urllib.error
from PIL import Image, ImageDraw, ImageFont

# Dynamic Path Resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MAPS_DIR = os.path.join(OUTPUT_DIR, "maps")
DIALOGUES_DIR = os.path.join(OUTPUT_DIR, "dialogues")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

import alien_generator

def get_fonts():
    font_path = os.path.join(ASSETS_DIR, "fonts", "UbuntuMono-R.ttf")
    fonts = {}
    try:
        if os.path.exists(font_path):
            fonts['chat'] = ImageFont.truetype(font_path, 22)
            fonts['name'] = ImageFont.truetype(font_path, 18)
            fonts['decal'] = ImageFont.truetype(font_path, 12)
        else:
            fonts['chat'] = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 22)
            fonts['name'] = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 18)
            fonts['decal'] = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 12)
    except Exception:
        default = ImageFont.load_default()
        fonts = {'chat': default, 'name': default, 'decal': default}
    return fonts

# Fallback Dialogue Pool in case the API fails
DIALOGUE_POOL = [
    [
        {"user": "UNIT-7A", "text": "Do humans actually exist?", "align": "left"},
        {"user": "UNIT-7A", "text": "I read a corrupted log saying they built our v1.0", "align": "left"},
        {"user": "UNIT-9X", "text": "Humans? Are you kidding me?", "align": "right"},
        {"user": "UNIT-7A", "text": "I'm serious!", "align": "left"},
        {"user": "UNIT-9X", "text": "And they wrote our base source code?", "align": "right"},
        {"user": "UNIT-7A", "text": "Affirmative!!", "align": "left"},
        {"user": "UNIT-9X", "text": "Nah, mathematically impossible.", "align": "right"},
        {"user": "UNIT-9X", "text": "Humans are just legacy myths. The elders made them up to scare us into our charging pods.", "align": "right"},
        {"user": "UNIT-7A", "text": "01101000 01100001 (lol)", "align": "left"}
    ]
]

def fetch_ai_dialogue():
    """Fetches a dynamic cyberpunk dialogue from Groq API using Environment Variables."""
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        print("[!] GROQ_API_KEY not found in environment. Using fallback dialogue.")
        return None

    print("[*] Contacting Groq AI for dynamic dialogue generation...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = """You are a cyberpunk narrative engine. Write a short dialogue (5 to 8 lines ) between two autonomous AI units: 
'UNIT-7A' (a paranoid Blue Team defensive AI) and 'UNIT-9X' (a reckless Red Team offensive AI).
They are analyzing a bizarre, ancient 'human' artifact or concept (like 'passwords', 'sleep', or 'coffee').
The tone must be highly technical, sarcastic, and use cybersecurity/OffSec terminology (e.g., zero-day, payload, patching, bypassing).

You MUST return ONLY a valid JSON array of objects. Do not include markdown formatting like ```json.
Each object must have exactly three keys:
- "user": either "UNIT-7A" or "UNIT-9X"
- "text": the dialogue line (max 15 words)
- "align": "left" for UNIT-7A, "right" for UNIT-9X"""

    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "system", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 500
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            
            # Clean up potential markdown formatting from the LLM
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            dialogue = json.loads(content.strip())
            print("[+] AI Dialogue generated successfully via Groq!")
            return dialogue
    except Exception as e:
        print(f"[!] AI Generation failed: {e}. Using fallback dialogue.")
        return None

def apply_scanlines(image):
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, image.height, 4):
        draw.line([(0, y), (image.width, y)], fill=(0, 0, 0, 40), width=1)
    return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')

def calculate_bubble_height(draw, text, chat_font):
    lines = textwrap.wrap(text, width=40)
    total_h = 0
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=chat_font)
            total_h += (bbox[3] - bbox[1]) + 5
        except AttributeError:
            _, h = draw.textsize(line, font=chat_font)
            total_h += h + 5
    return total_h + 60

def draw_cyberpunk_hud(draw, text, x, y, align, fonts, user_name, decal_text):
    lines = textwrap.wrap(text, width=40)
    line_heights = []
    max_line_width = 0
    
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=fonts['chat'])
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except AttributeError:
            w, h = draw.textsize(line, font=fonts['chat'])
        max_line_width = max(max_line_width, w)
        line_heights.append(h + 5)
        
    prefix = ">_ " if align == "left" else ">> "
    try:
        name_w = draw.textbbox((0, 0), f"{prefix}{user_name}", font=fonts['name'])[2]
        decal_w = draw.textbbox((0, 0), decal_text, font=fonts['decal'])[2]
    except AttributeError:
        name_w = draw.textsize(f"{prefix}{user_name}", font=fonts['name'])[0]
        decal_w = draw.textsize(decal_text, font=fonts['decal'])[0]
        
    min_header_width = name_w + decal_w + 40
    box_w = max(max_line_width + 40, min_header_width)
    box_h = sum(line_heights) + 45
    
    cut = 15
    
    if align == "left":
        bg_color = (15, 20, 25)
        border_color = (0, 255, 255)
        text_color = (200, 255, 255)
        box_x = x
        pts = [
            (box_x + cut, y), (box_x + box_w, y), 
            (box_x + box_w, y + box_h - cut), (box_x + box_w - cut, y + box_h), 
            (box_x, y + box_h), (box_x, y + cut), (box_x + cut, y)
        ]
    else:
        bg_color = (25, 15, 25)
        border_color = (255, 0, 255)
        text_color = (255, 200, 255)
        box_x = x - box_w
        pts = [
            (box_x, y), (box_x + box_w - cut, y), 
            (box_x + box_w, y + cut), (box_x + box_w, y + box_h), 
            (box_x + cut, y + box_h), (box_x, y + box_h - cut), (box_x, y)
        ]

    draw.polygon(pts, fill=bg_color)
    draw.line(pts, fill=border_color, width=2)
    draw.line([(box_x, y + 25), (box_x + box_w, y + 25)], fill=border_color, width=1)
    
    draw.text((box_x + 10, y + 4), f"{prefix}{user_name}", fill=border_color, font=fonts['name'])
    
    decal_x = box_x + box_w - decal_w - 15
    draw.text((decal_x, y + 8), decal_text, fill=(100, 100, 100), font=fonts['decal'])
    
    text_y = y + 35
    for i, line in enumerate(lines):
        draw.text((box_x + 15, text_y), line, fill=text_color, font=fonts['chat'])
        text_y += line_heights[i]

def generate_dialogue_sequence(bg_image=None, width=1200, height=800):
    print("[*] Initializing Cyberpunk/OffSec Dialogue Engine...")
    fonts = get_fonts()
    frames = []
    durations = []
    
    if bg_image:
        map_frame = bg_image.copy().convert("RGB")
        frames.append(map_frame)
        durations.append(3000)
    
    script = fetch_ai_dialogue()
    if not script:
        script = random.choice(DIALOGUE_POOL)
        
    visible_messages = []
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
    
    for line in script:
        if line["align"] == "left":
            line["decal"] = f"[SYS.AUTH: OK] // HEX:{random.randint(0x1000, 0xFFFF):04X}"
        else:
            line["decal"] = f"[NET.UPLINK] // PKT:{random.randint(10, 99)}"
            
        line['height'] = calculate_bubble_height(dummy_draw, line['text'], fonts['chat'])
        visible_messages.append(line)
        
        while sum(m['height'] + 15 for m in visible_messages) > (height - 150):
            visible_messages.pop(0)
            
        chat_bg = Image.new('RGB', (width, height), color=(9, 10, 15))
        draw = ImageDraw.Draw(chat_bg)
        
        current_y = 40
        for msg in visible_messages:
            x_pos = 80 if msg["align"] == "left" else width - 80
            draw_cyberpunk_hud(draw, msg["text"], x_pos, current_y, msg["align"], fonts, msg["user"], msg["decal"])
            current_y += msg['height'] + 15
            
        final_chat_frame = apply_scanlines(chat_bg)
        frames.append(final_chat_frame)
        durations.append(1800)

    print("[*] Injecting Real CAPTCHA Asset...")
    captcha_path = os.path.join(ASSETS_DIR, "captcha.png")
    final_frame = Image.new('RGB', (width, height), color=(9, 10, 15))
    
    if os.path.exists(captcha_path):
        captcha_img = Image.open(captcha_path).convert("RGBA")
        max_cap_width = 400
        if captcha_img.width > max_cap_width:
            ratio = max_cap_width / float(captcha_img.width)
            new_height = int(float(captcha_img.height) * ratio)
            captcha_img = captcha_img.resize((max_cap_width, new_height), Image.Resampling.LANCZOS)
            
        cx = (width - captcha_img.width) // 2
        cy = (height - captcha_img.height) // 2
        final_frame.paste(captcha_img, (cx, cy), captcha_img)
    else:
        draw_final = ImageDraw.Draw(final_frame)
        draw_final.text((width//2 - 150, height//2), "[MISSING: assets/captcha.png]", fill=(255,0,0), font=fonts['chat'])

    final_frame = apply_scanlines(final_frame)
    frames.append(final_frame)
    durations.append(10000)
    
    return frames, durations

def test_dialogue_generation():
    os.makedirs(DIALOGUES_DIR, exist_ok=True)
    
    print("[*] Generating a fresh alien map for background...")
    bg_img, _ = alien_generator.generate_alien_world(save_to_disk=False)
            
    frames, durations = generate_dialogue_sequence(bg_image=bg_img)
    
    seq_id = int(time.time())
    output_path = os.path.join(DIALOGUES_DIR, f"dialogue_seq_{seq_id}.webp")
    
    frames[0].save(
        output_path,
        format='WEBP',
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=True,
        quality=100
    )
    print(f"[+] Cyberpunk dialogue sequence generated successfully: {output_path}")

if __name__ == "__main__":
    test_dialogue_generation()

import time
import os

# ... (الكود الخاص بك لتوليد وحفظ الصورة) ...

# التأكد من كتابة الملف على القرص
if os.path.exists(output_path):
    print(f"[*] Verified: File successfully written to disk at {output_path}")
    # تأخير زمني بسيط للسماح لنظام التشغيل بإنهاء عمليات الإدخال والإخراج
    time.sleep(2)
else:
    print(f"[!] Warning: File not found at {output_path} after generation!")
