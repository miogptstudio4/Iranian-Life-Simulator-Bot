# -*- coding: utf-8 -*-
"""
سیستم زمان - ساعت، روز، باز و بسته بودن مکان‌ها
"""

import random

# نام روزهای هفته (ایرانی)
WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]

# ساعات باز بودن انواع مکان‌ها
OPENING_HOURS = {
    "نانوایی": (5, 21),
    "سوپرمارکت محله": (7, 23),
    "هایپرمارکت": (9, 22),
    "قصابی": (7, 20),
    "میوه‌فروشی": (7, 21),
    "کافه": (9, 24),
    "رستوران سنتی": (11, 23),
    "فست‌فود": (11, 24),
    "داروخانه": (8, 22),
    "موبایل فروشی": (10, 21),
    "پوشاک": (10, 22),
    "آرایشگاه مردانه": (9, 21),
    "آرایشگاه زنانه": (10, 21),
    "کتابفروشی": (9, 21),
    "لوازم التحریر": (8, 20),
    "تعمیرگاه موتور": (8, 19),
    "مسجد": (4, 23),          # تقریباً همیشه
    "بیمارستان دولتی": (0, 24), # ۲۴ ساعته
    "بیمارستان خصوصی": (0, 24),
    "پارک": (6, 23),
    "مدرسه": (7, 14),          # فقط صبح تا بعدازظهر
    "اداره دولتی": (7, 14),
    "بانک": (7, 14),
    "بازار سنتی": (8, 20),
    "default": (8, 21),
}

# تأثیر ساعت روی بازی
def get_time_period(hour: int) -> str:
    if 5 <= hour < 12:
        return "صبح"
    elif 12 <= hour < 17:
        return "ظهر"
    elif 17 <= hour < 20:
        return "عصر"
    elif 20 <= hour < 24:
        return "شب"
    else:
        return "نیمه‌شب"


def is_open(place_type: str, hour: int) -> bool:
    """آیا این مکان در این ساعت باز است؟"""
    hours = OPENING_HOURS.get(place_type, OPENING_HOURS["default"])
    start, end = hours
    if start < end:
        return start <= hour < end
    else:  # مثلاً از ۲۲ تا ۲ صبح
        return hour >= start or hour < end


def time_effects(char, hour: int):
    """تأثیر ساعت روی شخصیت"""
    period = get_time_period(hour)
    messages = []

    if period == "نیمه‌شب":
        char.fatigue = min(100, char.fatigue + random.randint(8, 15))
        char.mental = max(0, char.mental - random.randint(2, 6))
        messages.append("نیمه‌شبه... خستگی‌ت داره شدید می‌شه.")
    elif period == "شب":
        char.fatigue = min(100, char.fatigue + random.randint(3, 8))
        if random.random() < 0.2:
            messages.append("شب شده و خیابون‌ها خلوت‌ترن.")
    elif period == "صبح":
        if char.fatigue > 60:
            messages.append("صبحه اما هنوز خسته‌ای.")
    return messages


class GameTime:
    def __init__(self, start_hour=8, start_day=0):
        self.hour = start_hour          # 0 تا 23
        self.minute = random.randint(0, 59)
        self.day = start_day            # روز از شروع بازی
        self.weekday_index = start_day % 7

    def advance(self, minutes=30):
        """گذراندن زمان (به دقیقه)"""
        self.minute += minutes
        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1
            self.weekday_index = (self.weekday_index + 1) % 7

    def advance_hours(self, hours=1):
        self.advance(hours * 60)

    @property
    def weekday(self):
        return WEEKDAYS[self.weekday_index]

    @property
    def period(self):
        return get_time_period(self.hour)

    def formatted(self):
        return f"{self.weekday} | {self.hour:02d}:{self.minute:02d} ({self.period}) | روز {self.day + 1}"

    def shop_status(self, place_name: str) -> str:
        """وضعیت باز/بسته بودن یک مکان"""
        # تشخیص تقریبی نوع مکان از اسم
        place_type = "default"
        for key in OPENING_HOURS:
            if key in place_name:
                place_type = key
                break
        open_now = is_open(place_type, self.hour)
        return "🟢 باز" if open_now else "🔴 بسته"
