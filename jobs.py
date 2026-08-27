# -*- coding: utf-8 -*-
"""
سیستم شغل
"""

import random
from difficulty import hard_reward, hard_damage
from advanced_simulation import ensure_advanced

JOBS = {
    "بیکار": {
        "salary_min": 0, "salary_max": 0,
        "energy_cost": 0, "required_age_days": 0,
        "description": "هیچ درآمدی نداری"
    },
    "پیک موتوری": {
        "salary_min": 8_000_000, "salary_max": 18_000_000,
        "energy_cost": 25, "required_age_days": 180,
        "description": "با موتور بسته جابه‌جا می‌کنی. خطر تصادف بالاست"
    },
    "کارگر ساختمانی": {
        "salary_min": 10_000_000, "salary_max": 22_000_000,
        "energy_cost": 35, "required_age_days": 180,
        "description": "کار سخت فیزیکی. کمر درد تضمینیه"
    },
    "فروشنده مغازه": {
        "salary_min": 9_000_000, "salary_max": 16_000_000,
        "energy_cost": 15, "required_age_days": 170,
        "description": "پشت پیشخوان ایستادی و مشتری‌داری"
    },
    "راننده اسنپ": {
        "salary_min": 12_000_000, "salary_max": 28_000_000,
        "energy_cost": 20, "required_age_days": 180,
        "description": "با ماشین مسافرکشی. بنزین گرونه"
    },
    "کارمند اداره": {
        "salary_min": 15_000_000, "salary_max": 25_000_000,
        "energy_cost": 10, "required_age_days": 180,
        "description": "کار دولتی. امنیت شغلی نسبی"
    },
    "معلم": {
        "salary_min": 14_000_000, "salary_max": 24_000_000,
        "energy_cost": 18, "required_age_days": 220,
        "description": "تدریس در مدرسه. صبر زیادی می‌خواد"
    },
    "برنامه‌نویس": {
        "salary_min": 30_000_000, "salary_max": 80_000_000,
        "energy_cost": 15, "required_age_days": 220,
        "description": "دورکاری یا شرکتی. درآمد خوب اما رقابت شدید"
    },
    "پزشک": {
        "salary_min": 50_000_000, "salary_max": 150_000_000,
        "energy_cost": 30, "required_age_days": 240,
        "description": "درآمد بالا اما مسئولیت و استرس خیلی زیاد"
    },
    "کاسب": {
        "salary_min": 5_000_000, "salary_max": 100_000_000,
        "energy_cost": 20, "required_age_days": 180,
        "description": "مغازه خودت. سود و زیان دست خودته"
    },
}

def list_jobs():
    lines = []
    for name, info in JOBS.items():
        sal = f"{info['salary_min']//1_000_000}-{info['salary_max']//1_000_000} میلیون"
        lines.append(f"• {name}: {sal} | انرژی: {info['energy_cost']} | {info['description']}")
    return "\n".join(lines)

def can_take_job(char, job_name: str) -> tuple:
    job = JOBS.get(job_name)
    if not job:
        return False, "این شغل وجود نداره"
    if char.age_days < job["required_age_days"]:
        years_needed = job["required_age_days"] // 10
        return False, f"حداقل سن تقریبی برای این شغل حدود {years_needed} سالگیه"
    if char.health < 30:
        return False, "سلامتت برای کار کردن خیلی پایینه"
    return True, "OK"

def work(char, job_name: str) -> str:
    ok, msg = can_take_job(char, job_name)
    if not ok:
        return msg
    job = JOBS[job_name]
    d = ensure_advanced(char)
    econ = d.get("economy", {})
    earned = hard_reward(random.randint(job["salary_min"], job["salary_max"]), inflation=econ.get("inflation",0.18), unemployment=econ.get("unemployment",0.08))
    char.money += earned
    char.fatigue = min(100, char.fatigue + hard_damage(job["energy_cost"]))
    char.hunger = min(120, char.hunger + hard_damage(random.randint(5, 12)))
    char.thirst = min(120, char.thirst + hard_damage(random.randint(5, 10)))
    if char.fatigue > 90:
        char.health = max(0, char.health - hard_damage(random.randint(5, 15)))
    return f"✅ کار کردی و {earned:,} تومان درآوردی.\nخستگی و گرسنگی‌ت بیشتر شد."
