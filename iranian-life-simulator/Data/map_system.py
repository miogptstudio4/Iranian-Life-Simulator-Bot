# -*- coding: utf-8 -*-
"""
سیستم نقشه و گشت‌وگذار در شهر
Open World Movement System
"""

import random

# جهت‌ها
DIRECTIONS = {
    "شمال": (0, 1),
    "جنوب": (0, -1),
    "شرق": (1, 0),
    "غرب": (-1, 0),
    "n": (0, 1),
    "s": (0, -1),
    "e": (1, 0),
    "w": (-1, 0),
}

# انواع مکان‌هایی که ممکن است ظاهر شوند
LOCATION_TYPES = [
    "خیابان اصلی",
    "کوچه فرعی",
    "میدان",
    "پارک کوچک",
    "نانوایی",
    "سوپرمارکت محله",
    "مسجد",
    "مدرسه",
    "درمانگاه",
    "ایستگاه اتوبوس",
    "دکه روزنامه‌فروشی",
    "تعمیرگاه موتور",
    "خانه نیمه‌کاره",
    "زمین بایر",
    "پاساژ قدیمی",
    "آبمیوه‌گیری",
    "قصابی",
    "کافه کوچک",
    "کتابفروشی",
    "پاسگاه",
    "پارکینگ",
    "زیرگذر",
    "پل عابر",
]

# توضیحات تصادفی برای مکان‌ها
LOCATION_DESCRIPTIONS = [
    "صدای بوق ماشین‌ها از دور می‌آید.",
    "بوی نان تازه به مشام می‌رسد.",
    "چند نفر گوشه‌ای ایستاده‌اند و حرف می‌زنند.",
    "زمین پر از زباله و کیسه پلاستیکیه.",
    "یه موتور با صدای بلند رد می‌شه.",
    "هوا پر از گرد و غباره.",
    "یه دستفروش داره اجناسش رو جار می‌زنه.",
    "دیوارها پر از شعار و آگهی کنده شده‌ست.",
    "یه گربه از کنار دیوار رد می‌شه.",
    "سیم‌های برق بالای سرت آویزونن.",
    "بوی فاضلاب می‌آد.",
    "چند تا بچه دارن تو کوچه بازی می‌کنن.",
    "یه وانت میوه ایستاده و مشتری داره.",
    "نور لامپ‌های کم‌سو خیابون رو روشن کرده.",
]

def generate_location_name(city: str, neighborhood: str):
    loc_type = random.choice(LOCATION_TYPES)
    return f"{loc_type} ({neighborhood})"

def get_random_description():
    return random.choice(LOCATION_DESCRIPTIONS)

# ==================== سیستم پلیرها (شبیه‌سازی) ====================
class PlayerCounter:
    def __init__(self):
        self.total_players = random.randint(1840, 3270)      # کل ثبت‌نامی‌ها
        self.online_base = random.randint(40, 120)

    def get_online(self):
        # کمی نوسان برای حس زنده بودن
        fluctuation = random.randint(-8, 15)
        online = max(12, self.online_base + fluctuation)
        return online

    def get_total(self):
        return self.total_players

    def status_line(self):
        online = self.get_online()
        total = self.get_total()
        return f"👥 آنلاین: {online}   |   کل پلیرها: {total:,}"
