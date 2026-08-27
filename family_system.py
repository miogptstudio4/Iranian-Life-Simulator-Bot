# -*- coding: utf-8 -*-
"""
سیستم خانواده، ازدواج و بچه‌دار شدن
با زمان‌بندی و شانس بارداری متغیر
"""

import random

MARITAL_STATUS = ["مجرد", "نامزد", "متأهل", "مطلقه", "همسر فوت‌شده"]

# ==================== شانس بارداری ====================
# شانس پایه بارداری در هر تلاش (ارضا / نزدیکی)
BASE_PREGNANCY_CHANCE = {
    "very_high": 0.28,   # شرایط عالی
    "high": 0.18,
    "normal": 0.12,
    "low": 0.06,
    "very_low": 0.025,
}

def get_pregnancy_chance(mother_age_years: int, mother_health: int, mother_mental: int, stress: bool = False) -> float:
    """محاسبه شانس بارداری بر اساس سن، سلامت و روحیه مادر"""
    # سن ایده‌آل تقریبی ۲۰ تا ۳۲
    if 20 <= mother_age_years <= 32:
        base = BASE_PREGNANCY_CHANCE["high"]
    elif 18 <= mother_age_years < 20 or 33 <= mother_age_years <= 37:
        base = BASE_PREGNANCY_CHANCE["normal"]
    elif 38 <= mother_age_years <= 42:
        base = BASE_PREGNANCY_CHANCE["low"]
    else:
        base = BASE_PREGNANCY_CHANCE["very_low"]

    # سلامت
    if mother_health >= 80:
        base *= 1.25
    elif mother_health < 50:
        base *= 0.5
    elif mother_health < 30:
        base *= 0.25

    # روحیه
    if mother_mental < 40:
        base *= 0.7
    if stress:
        base *= 0.6

    return min(0.45, max(0.01, base))


# ==================== زمان‌بندی تلاش برای بچه‌دار شدن ====================
# از لحظه «تلاش» تا مشخص شدن نتیجه (بارداری یا نه)
CONCEPTION_TIME = {
    # حداقل و حداکثر روز تا مشخص شدن نتیجه هر تلاش
    "min_days": 10,
    "max_days": 45,          # ممکنه تا یک ماه و نیم طول بکشه
    "lucky_min": 8,          # شانس خوب → زودتر معلوم می‌شه
    "unlucky_max": 60,       # بدشانسی → بیشتر طول می‌کشه
}

def roll_conception_wait_days(lucky: bool = False) -> int:
    """چند روز طول می‌کشه تا نتیجه تلاش مشخص بشه"""
    if lucky:
        return random.randint(CONCEPTION_TIME["lucky_min"], CONCEPTION_TIME["max_days"] // 2)
    # گاهی بدشانسی
    if random.random() < 0.15:
        return random.randint(CONCEPTION_TIME["max_days"], CONCEPTION_TIME["unlucky_max"])
    return random.randint(CONCEPTION_TIME["min_days"], CONCEPTION_TIME["max_days"])


def try_conceive(mother_age_years: int, mother_health: int, mother_mental: int, stress: bool = False) -> dict:
    """
    یک تلاش برای بارداری.
    برمی‌گرداند:
    {
      "success": bool,          # آیا باردار شد؟
      "wait_days": int,         # چند روز بعد نتیجه معلوم می‌شه
      "chance_used": float,     # شانسی که استفاده شد
      "message": str
    }
    """
    chance = get_pregnancy_chance(mother_age_years, mother_health, mother_mental, stress)
    success = random.random() < chance
    wait = roll_conception_wait_days(lucky=success and random.random() < 0.3)

    if success:
        msg = (
            f"تلاش انجام شد. شانس بارداری حدود {int(chance*100)}٪ بود.\n"
            f"نتیجه تا {wait} روز دیگه مشخص می‌شه..."
        )
    else:
        msg = (
            f"تلاش انجام شد. شانس بارداری حدود {int(chance*100)}٪ بود.\n"
            f"باید {wait} روز صبر کنی تا بفهمی باردار شدی یا نه."
        )

    return {
        "success": success,
        "wait_days": wait,
        "chance_used": chance,
        "message": msg,
        "revealed": False,      # هنوز به بازیکن نگفتیم موفق بوده یا نه
    }


# ==================== بارداری (بعد از موفقیت) ====================
PREGNANCY = {
    "duration_days": 270,           # حدود ۹ ماه
    "monthly_effects": {
        "mother_health": (-3, -8),
        "mother_mental": (-2, -7),
        "mother_fatigue": (5, 12),
        "costs_per_month": (8_000_000, 35_000_000),
    },
    "complications_chance": {
        "normal": 0.18,
        "extreme_hardcore": 0.42,
    },
    "complications": [
        "تهوع شدید و کم‌آبی",
        "فشار خون بارداری",
        "دیابت بارداری",
        "زایمان زودرس",
        "خونریزی",
        "نیاز به سزارین اضطراری",
        "عفونت",
        "افسردگی بارداری",
    ],
}

CHILDBIRTH = {
    "locations": ["بیمارستان دولتی", "بیمارستان خصوصی", "زایشگاه", "خانه (زایمان خانگی - خیلی خطرناک)"],
    "costs": {
        "بیمارستان دولتی": (15_000_000, 60_000_000),
        "بیمارستان خصوصی": (80_000_000, 350_000_000),
        "زایشگاه": (40_000_000, 120_000_000),
        "خانه (زایمان خانگی - خیلی خطرناک)": (2_000_000, 15_000_000),
    },
    "risk_of_death_mother": {
        "بیمارستان دولتی": 0.04,
        "بیمارستان خصوصی": 0.015,
        "زایشگاه": 0.03,
        "خانه (زایمان خانگی - خیلی خطرناک)": 0.22,
    },
    "risk_of_death_baby": {
        "بیمارستان دولتی": 0.035,
        "بیمارستان خصوصی": 0.012,
        "زایشگاه": 0.025,
        "خانه (زایمان خانگی - خیلی خطرناک)": 0.28,
    },
}

CHILD_RAISING_COSTS = {
    "نوزاد (۰-۲ سال)": {"ماهانه": (25_000_000, 70_000_000)},
    "کودک (۳-۶ سال)": {"ماهانه": (20_000_000, 55_000_000)},
    "مدرسه (۷-۱۲ سال)": {"ماهانه": (15_000_000, 80_000_000)},
    "نوجوان (۱۳-۱۸ سال)": {"ماهانه": (25_000_000, 120_000_000)},
}

def generate_child(parent_city: str, parent_family: str):
    gender = random.choice(["پسر", "دختر"])
    male_names = ["پارسا", "آرین", "کیان", "سپهر", "نیما", "آرش", "رادین", "ایلیا", "مانی", "محمد", "علی", "حسین"]
    female_names = ["یسنا", "آوا", "هلیا", "نازنین", "سارا", "دنیا", "مهسا", "آیدا", "نیکا", "باران", "فاطمه", "زهرا"]
    name = random.choice(male_names if gender == "پسر" else female_names)
    health = random.randint(60, 90)
    child = {
        "name": name,
        "gender": gender,
        "age_days": 0,
        "health": health,
        "hunger": random.randint(40, 70),
        "alive": True,
        "birth_place": parent_city,
        "traits": [],
    }
    if random.random() < 0.09:
        problems = ["نارس", "وزن کم", "مشکل تنفسی خفیف"]
        child["traits"].append(random.choice(problems))
        child["health"] = max(20, child["health"] - random.randint(15, 35))
    return child


# ==================== وضعیت تلاش در حال انتظار ====================
# برای ذخیره روی شخصیت بازیکن:
# char.conception_attempt = {
#   "success": True/False,
#   "wait_days": 20,
#   "days_passed": 0,
#   "revealed": False,
#   "started_day": 5
# }

def advance_conception(char, days: int = 1) -> str | None:
    """
    هر بار که زمان می‌گذرد این تابع را صدا بزن.
    اگر نتیجه مشخص شد پیام برمی‌گرداند.
    """
    attempt = getattr(char, "conception_attempt", None)
    if not attempt or attempt.get("revealed"):
        return None

    attempt["days_passed"] = attempt.get("days_passed", 0) + days

    if attempt["days_passed"] >= attempt["wait_days"]:
        attempt["revealed"] = True
        if attempt["success"]:
            char.pregnant = True
            char.pregnancy_days = 0
            return (
                f"🤰 نتیجه اومد: باردار شدی!\n"
                f"حدود ۹ ماه (۲۷۰ روز) تا زایمان مونده.\n"
                f"مراقب سلامت و روحیه‌ت باش."
            )
        else:
            char.conception_attempt = None
            return (
                "نتیجه اومد: این بار باردار نشدی.\n"
                "می‌تونی دوباره تلاش کنی. شانس هر بار متفاوته."
            )
    return None


def advance_pregnancy(char, days: int = 1) -> str | None:
    """پیشبرد بارداری. اگر موقع زایمان شد خبر می‌دهد."""
    if not getattr(char, "pregnant", False):
        return None

    char.pregnancy_days = getattr(char, "pregnancy_days", 0) + days

    # اثرات ماهانه تقریبی
    if char.pregnancy_days % 30 == 0:
        char.health = max(0, char.health - random.randint(3, 8))
        char.mental = max(0, char.mental - random.randint(2, 7))
        char.fatigue = min(100, char.fatigue + random.randint(5, 12))

    if char.pregnancy_days >= PREGNANCY["duration_days"]:
        return "time_for_birth"  # سیگنال برای شروع زایمان
    return None
