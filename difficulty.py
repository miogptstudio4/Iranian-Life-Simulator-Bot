# -*- coding: utf-8 -*-
"""سختی سیستمی؛ بدون ضرب میلیاردی قیمت‌ها."""
import math

DIFFICULTY_MULTIPLIER = 1.0
BASE_INFLATION = 0.18

def hard_cost(amount: int, inflation: float = BASE_INFLATION, city_modifier: float = 1.0) -> int:
    # هزینه‌ها با اقتصاد، شهر و تورم رشد می‌کنند؛ نه با ضرب ثابت 999,999,999.
    factor = max(0.55, city_modifier) * (1.0 + max(-0.05, inflation))
    return max(1, int(amount * factor))

def hard_reward(amount: int, inflation: float = BASE_INFLATION, skill: float = 0.0) -> int:
    # درآمد پایه با تورم و مهارت تعدیل می‌شود، ولی تضمینی نیست.
    factor = (1.0 + max(0.0, inflation * 0.45)) * (1.0 + min(1.0, skill/100.0)*0.35)
    return max(1, int(amount * factor))

def hard_damage(amount: int, severity: float = 1.0) -> int:
    return max(1, int(amount * max(0.5, severity)))
