#!/usr/bin/env python3
import cv2
import numpy as np
import os

# المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(BASE_DIR, "vecteezy_captcha-vector-icon_11170480.jpg")
output_path = os.path.join(BASE_DIR, "captcha.png")

print("[*] Loading image...")
img = cv2.imread(input_path)

if img is None:
    print(f"[!] Error: Could not load {input_path}")
    exit()

# 1. تحويل الصورة للرمادي
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 2. تطبيق فلتر ضبابي خفيف لتقليل تشويش المربعات الخلفية
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# 3. اكتشاف الحواف (Canny Edge Detection)
edges = cv2.Canny(blurred, 50, 150)

# 4. البحث عن الخطوط المتصلة (Contours)
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 5. ترتيب الخطوط حسب المساحة (أكبر مساحة ستكون صندوق الكابتشا)
contours = sorted(contours, key=cv2.contourArea, reverse=True)

if contours:
    largest_contour = contours[0]
    
    # الحصول على إحداثيات الصندوق المحيط (Bounding Box)
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # إضافة هامش بسيط جداً (Padding) لضمان عدم قطع الإطار
    padding = 2
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(img.shape[1] - x, w + 2*padding)
    h = min(img.shape[0] - y, h + 2*padding)
    
    print(f"[*] Found CAPTCHA box at X:{x} Y:{y} Width:{w} Height:{h}")
    
    # 6. قص الصورة الأصلية
    cropped = img[y:y+h, x:x+w]
    
    # 7. تحويلها إلى صيغة تدعم الشفافية (RGBA) وحفظها
    cropped_rgba = cv2.cvtColor(cropped, cv2.COLOR_BGR2BGRA)
    cv2.imwrite(output_path, cropped_rgba)
    
    print(f"[+] Success! Clean CAPTCHA saved to {output_path}")
else:
    print("[!] Could not find any contours.")
