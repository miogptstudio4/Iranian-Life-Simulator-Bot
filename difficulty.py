# -*- coding: utf-8 -*-
"""سیستم سختی اقتصادی پویا و حالت کابوس.
هزینه‌ها و ریسک‌ها به‌صورت غیرخطی بالا می‌روند؛ اما از اعداد نجومیِ غیرقابل‌بازی پرهیز می‌شود.
"""
import math

# شدت طراحی‌شده برای حالت فعلی: «کابوس اقتصادی»
NIGHTMARE_LEVEL = 9999999999999999999999999999999999

def _effective_pressure(inflation=0.18, unemployment=0.08):
    # فشار بسیار شدید، ولی با سقف عملی تا بازی هنوز قابل برگشت باشد.
    inf = max(0.0, float(inflation))
    unemp = max(0.0, min(0.95, float(unemployment)))
    pressure = 1.0 + min(18.0, inf * 12.0) + min(14.0, unemp * 20.0)
    return max(1.0, pressure)

def hard_cost(amount: int, inflation: float = 0.18, city_modifier: float = 1.0,
              unemployment: float = 0.08) -> int:
    factor = max(0.55, city_modifier)
    return max(1, int(amount * factor * _effective_pressure(inflation, unemployment)))

def hard_reward(amount: int, inflation: float = 0.18, skill: float = 0.0,
                unemployment: float = 0.08) -> int:
    # تورم اسمی دستمزد را بالا می‌برد، ولی بیکاری قدرت چانه‌زنی را کم می‌کند.
    skill_factor = 1.0 + min(1.0, max(0.0, skill) / 100.0) * 0.35
    real_pressure = max(0.35, 1.0 - min(0.65, max(0.0, unemployment) * 0.75))
    nominal = 1.0 + min(3.0, max(0.0, inflation) * 0.45)
    return max(1, int(amount * nominal * skill_factor * real_pressure))

def hard_damage(amount: int, severity: float = 1.0) -> int:
    return max(1, int(amount * max(0.5, severity)))
