#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات تلگرام - شبیه‌ساز زندگی یک ایرانی
"""

import os
import sys
import logging
import random

try:
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("برای ربات تلگرام نصب کنید: pip install python-telegram-bot")

from locations import CITY_LIST, CITIES, FAMILY_TYPES, IRAN_CITIES
from admin import (
    SUPER_ADMIN_ID, generate_player_id, hash_password, DEFAULT_ADMIN_PASSWORD,
    is_super_admin, add_admin, list_admins
)
from jobs import JOBS, list_jobs, work, can_take_job
from combat import street_fight
from time_system import GameTime
from database import (
    init_database, save_player, load_player_by_numeric_id,
    apply_loaded_data, PSYCOPG2_AVAILABLE
)
from render import render_status_card, render_profile
from life_system import make_family, home_for_family, home_text, family_text, daily_life_event, advance_life_age

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PLAYERS = {}
GAME_TIMES = {}
# کاربرهایی که منتظر انتخاب شهر هستند
WAITING_CITY = set()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

MALE_NAMES = ["پارسا", "آرین", "کیان", "سپهر", "نیما", "آرش", "رادین", "ایلیا", "مانی", "سینا", "رضا", "امیر"]
FEMALE_NAMES = ["یسنا", "آوا", "هلیا", "نازنین", "سارا", "دنیا", "مهسا", "آیدا", "نیکا", "باران", "هستی", "کیمیا"]

# فقط شهرهای ایران برای شروع
IRAN_CITY_SET = set(IRAN_CITIES) if "IRAN_CITIES" in dir() else set()
try:
    from locations import IRAN_CITIES as _IC
    IRAN_CITY_SET = set(_IC)
except Exception:
    IRAN_CITY_SET = {c for c in CITY_LIST if CITIES.get(c, {}).get("region", "").startswith("ایران") or c in [
        "تهران", "اهواز", "مشهد", "اصفهان", "شیراز", "تبریز", "کرج", "رشت", "کرمانشاه", "قم",
        "یزد", "کرمان", "ارومیه", "همدان", "ساری", "گرگان", "زاهدان", "بندرعباس", "بوشهر", "اردبیل"
    ]}


class BotPlayer:
    def __init__(self, numeric_id: str, name: str = None, city: str = None):
        self.numeric_id = str(numeric_id)
        self.player_id = generate_player_id()
        self.gender = random.choice(["پسر", "دختر"])
        self.name = name or random.choice(MALE_NAMES if self.gender == "پسر" else FEMALE_NAMES)
        if name and not any(name == n for n in MALE_NAMES + FEMALE_NAMES):
            self.name = name  # اسم تلگرام
        self.display_name = self.name
        self.city = city or random.choice(list(IRAN_CITY_SET) if IRAN_CITY_SET else CITY_LIST[:30])
        city_data = CITIES.get(self.city, {})
        self.neighborhood = random.choice(city_data.get("neighborhoods", ["مرکز شهر"]))
        self.family = random.choice(FAMILY_TYPES)
        self.home = "آپارتمان اجاره‌ای"
        self.birth_year = 1385
        self.age_days = 100  # بازی قابل‌کنترل از ۱۰ سالگی آغاز می‌شود
        self.family_members = make_family(self.gender, self.family)
        self.home_data = home_for_family(self.family)
        self.home = self.home_data["type"]
        self.last_age_game_day = 0
        self.hunger = random.randint(25, 50)
        self.thirst = random.randint(20, 45)
        self.fatigue = random.randint(10, 35)
        self.health = random.randint(75, 95)
        self.mental = random.randint(55, 85)
        self.money = random.randint(3_000_000, 20_000_000)
        self.location = "خانه"
        self.x = self.y = 0
        self.god_mode = False
        self.marital_status = "مجرد"
        self.bio = ""
        self.job = "بیکار"
        self.children = []
        self.alive = True
        self.pregnant = False
        self.pregnancy_days = 0
        self.conception_attempt = None
        self.admin_password_hash = hash_password(DEFAULT_ADMIN_PASSWORD, self.player_id)

    def status_text(self):
        return (
            f"👤 {self.display_name} ({self.gender}) | سن: {max(10, self.age_days // 10)} سال\n"
            f"🏙 {self.city} | {self.neighborhood}\n"
            f"💼 شغل: {self.job}\n"
            f"💰 {self.money:,} تومان\n"
            f"❤️ سلامت: {self.health}% | 🧠 روحیه: {self.mental}%\n"
            f"🍖 گرسنگی: {self.hunger}% | 💧 تشنگی: {self.thirst}%\n"
            f"😴 خستگی: {self.fatigue}%\n"
            f"📍 {self.location}"
        )


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["وضعیت", "پروفایل"],
            ["خانه", "خانواده", "زندگی", "استراحت"],
            ["شمال", "جنوب", "شرق", "غرب"],
            ["شغل", "کار کن", "دعوا"],
            ["زمان", "کمک"],
        ],
        resize_keyboard=True,
    )


def get_player(user_id: str):
    return PLAYERS.get(str(user_id))


def create_fresh_player(user_id: str, name: str = None, city: str = None) -> BotPlayer:
    """ساخت کامل از صفر (بعد از مرگ یا بازی جدید)"""
    p = BotPlayer(str(user_id), name=name, city=city)
    PLAYERS[str(user_id)] = p
    GAME_TIMES[user_id] = GameTime(start_hour=random.randint(7, 20))
    if PSYCOPG2_AVAILABLE:
        try:
            save_player(p)
        except Exception:
            pass
    return p


def find_iran_city(text: str) -> str | None:
    """پیدا کردن شهر ایران از متن کاربر"""
    t = text.strip()
    # تطبیق دقیق
    for c in IRAN_CITY_SET:
        if c == t:
            return c
    # بدون فاصله / جزئی
    t2 = t.replace(" ", "").replace("‌", "")
    for c in IRAN_CITY_SET:
        if c.replace(" ", "").replace("‌", "") == t2:
            return c
    # شروع با
    matches = [c for c in IRAN_CITY_SET if c.startswith(t) or t in c]
    if len(matches) == 1:
        return matches[0]
    return None


async def start(update, context):
    user = update.effective_user
    uid = str(user.id)

    # همیشه امکان شروع مجدد
    # اگر مرده یا /start زده → ریست کامل بعد از انتخاب شهر
    WAITING_CITY.add(uid)

    await update.message.reply_text(
        f"سلام {user.first_name}!\n\n"
        f"به شبیه‌ساز زندگی یک ایرانی خوش اومدی.\n\n"
        f"🎮 بازی از صفر شروع می‌شه:\n"
        f"• جنسیت، پول، شغل و همه چیز رندوم از اول ساخته می‌شه\n\n"
        f"🏙 اول بگو می‌خوای تو کدوم **شهر ایران** باشی؟\n"
        f"فقط **نام شهر** را بنویس.\n\n"
        f"مثال:\nتهران\nاهواز\nمشهد\nاصفهان\nشیراز\nرشت\nتبریز\n...",
        reply_markup=ReplyKeyboardRemove(),
    )


async def help_cmd(update, context):
    await update.message.reply_text(
        "📖 راهنما\n\n"
        "/start → شروع جدید / زنده شدن بعد از مرگ (ریست کامل)\n"
        "وضعیت / پروفایل\n"
        "خانه / خانواده / زندگی → مدیریت و مشاهده زندگی\n"
        "استراحت → استراحت در خانه\n"
        "شمال جنوب شرق غرب → حرکت\n"
        "شغل → لیست شغل‌ها\n"
        "انتخاب شغل نام_شغل\n"
        "کار کن → کار کردن\n"
        "دعوا → دعوای خیابانی\n"
        "زمان\n\n"
        "⚠️ اگر مردی، دوباره /start بزن تا از صفر شروع کنی."
    )


async def handle_message(update, context):
    user = update.effective_user
    uid = str(user.id)
    text = (update.message.text or "").strip()

    # ----- منتظر انتخاب شهر -----
    if uid in WAITING_CITY:
        city = find_iran_city(text)
        if not city:
            # پیشنهاد چند شهر
            samples = random.sample(list(IRAN_CITY_SET), min(8, len(IRAN_CITY_SET))) if IRAN_CITY_SET else ["تهران", "اهواز", "مشهد"]
            await update.message.reply_text(
                f"❌ شهر «{text}» پیدا نشد یا خارج از ایرانه.\n\n"
                f"فقط شهرهای ایران مجاز هستند.\n"
                f"مثال: {', '.join(samples)}\n\n"
                f"دوباره نام شهر را بنویس:"
            )
            return

        # ریست کامل + شهر انتخابی
        player = create_fresh_player(uid, name=user.first_name, city=city)
        WAITING_CITY.discard(uid)

        await update.message.reply_text(
            f"👶 تو در ۰ سالگی به دنیا اومدی.\n\n"
            f"🏙 شهر: {player.city}\n"
            f"👤 نام: {player.name} ({player.gender})\n"
            f"👨‍👩‍👧 خانواده: {player.family}\n"
            f"🏠 خانه: {player.home}\n\n"
            f"{family_text(player)}\n\n"
            f"📖 چند سال اول زندگی‌ات در کنار خانواده گذشت؛ رشد کردی، محیط اطرافت را شناختی و شخصیتت شکل گرفت.\n\n"
            f"🎂 حالا داستان اصلی از ۱۰ سالگی شروع می‌شود.\n"
            f"⏳ از اینجا به بعد هر ۱۰ روز بازی = ۱ سال زندگی.\n\n"
            f"{player.status_text()}",
            reply_markup=main_keyboard(),
        )
        return

    player = get_player(uid)

    # هنوز شخصیت نساخته
    if not player:
        WAITING_CITY.add(uid)
        await update.message.reply_text(
            "اول /start بزن و شهر ایران را انتخاب کن."
        )
        return

    # مرده
    if not player.alive:
        await update.message.reply_text(
            "💀 شخصیتت مرده.\n\n"
            "برای زنده شدن و شروع از صفر، دستور /start را بزن.\n"
            "همه چیز (جنسیت، پول، شغل، شهر و...) از اول ساخته می‌شود."
        )
        return

    if user.id not in GAME_TIMES:
        GAME_TIMES[user.id] = GameTime(start_hour=random.randint(7, 20))
    gt = GAME_TIMES[user.id]

    reply = None

    if text in ["خانه", "خونه", "home"]:
        reply = home_text(player)
    elif text in ["خانواده", "family"]:
        reply = family_text(player)
    elif text in ["زندگی", "life"]:
        reply = "🌱 سیستم زندگی\n\n" + home_text(player) + "\n\n" + family_text(player)
    elif text in ["استراحت", "rest"]:
        player.fatigue = max(0, player.fatigue - random.randint(12, 25))
        player.mental = min(100, player.mental + random.randint(1, 5))
        gt.advance(120)
        reply = "😴 در خانه استراحت کردی و انرژی‌ات برگشت."
        reply += "\n" + daily_life_event(player)
        for msg in advance_life_age(player, gt.day):
            reply += "\n" + msg
    if text in ["وضعیت", "status"]:
        reply = render_status_card(player, gt)

    elif text in ["پروفایل", "profile"]:
        reply = render_profile(player)

    elif text in ["شمال", "جنوب", "شرق", "غرب", "n", "s", "e", "w"]:
        old_day = gt.day
        gt.advance(random.randint(15, 40))
        age_msgs = advance_life_age(player, gt.day)
        player.fatigue = min(100, player.fatigue + random.randint(3, 8))
        player.thirst = min(120, player.thirst + random.randint(2, 6))
        player.hunger = min(120, player.hunger + random.randint(1, 5))
        places = ["خیابان اصلی", "کوچه", "میدان", "نانوایی", "سوپرمارکت", "پارک", "مسجد", "ایستگاه اتوبوس"]
        player.location = random.choice(places)
        reply = f"رفتی سمت {text}.\n📍 {player.location}\n🕐 {gt.formatted()}"
        if age_msgs:
            reply += "\n\n" + "\n".join(age_msgs)
        if random.random() < 0.12:
            reply += "\n\n" + street_fight(player)
        # چک مرگ بعد از دعوا
        if not player.alive:
            reply += "\n\n💀 مردی! برای شروع مجدد /start بزن."

    elif text in ["شغل", "jobs"]:
        reply = "مشاغل موجود:\n" + list_jobs() + "\n\nبرای انتخاب:\nانتخاب شغل نام_شغل"

    elif text.startswith("انتخاب شغل"):
        job_name = text.replace("انتخاب شغل", "").strip()
        if job_name in JOBS:
            ok, msg = can_take_job(player, job_name)
            if ok:
                player.job = job_name
                reply = f"✅ شغلت شد: {job_name}"
            else:
                reply = msg
        else:
            reply = "این شغل وجود نداره. «شغل» رو بزن."

    elif text in ["کار کن", "کار", "work"]:
        if player.job == "بیکار":
            reply = "اول شغل انتخاب کن (دستور: شغل)"
        else:
            reply = work(player, player.job)

    elif text in ["دعوا", "fight"]:
        reply = street_fight(player)
        if not player.alive:
            reply += "\n\n💀 مردی! برای شروع مجدد /start بزن."

    elif text in ["زمان", "time"]:
        reply = f"🕐 {gt.formatted()}"

    elif text in ["کمک", "help"]:
        await help_cmd(update, context)
        return

    elif text in ["ادمین"] or text.startswith("ادمین"):
        if str(user.id) == SUPER_ADMIN_ID or is_super_admin(str(user.id)):
            if "addadmin" in text:
                parts = text.split()
                if len(parts) >= 2:
                    add_admin(parts[-1])
                    reply = f"✅ {parts[-1]} ادمین شد."
                else:
                    reply = "مثال: ادمین addadmin 123456789"
            elif "listadmins" in text:
                reply = "ادمین‌ها:\n" + "\n".join(list_admins())
            else:
                reply = f"🔑 ادمین اصلی\nآیدی تو: {user.id}\nدستورات: addadmin / listadmins"
        else:
            reply = "دسترسی ادمین نداری."

    else:
        reply = "متوجه نشدم. «کمک» یا /start را بزن."

    if PSYCOPG2_AVAILABLE and player:
        try:
            save_player(player)
        except Exception:
            pass

    if reply:
        await update.message.reply_text(reply)


def main_bot():
    if not TELEGRAM_AVAILABLE:
        print("python-telegram-bot نصب نیست.")
        return
    if not TOKEN:
        print("export TELEGRAM_BOT_TOKEN=your_token")
        return

    if PSYCOPG2_AVAILABLE:
        try:
            init_database()
        except Exception as e:
            print("DB init:", e)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("ربات شروع شد...")
    app.run_polling()


if __name__ == "__main__":
    main_bot()
