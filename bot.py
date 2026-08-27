#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات تلگرام - شبیه‌ساز زندگی یک ایرانی
به پیام‌های کاربران جواب می‌دهد.
"""

import os
import sys
import logging
import random

# تلاش برای python-telegram-bot
try:
    from telegram import Update, ReplyKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("برای ربات تلگرام نصب کنید: pip install python-telegram-bot")

from locations import CITY_LIST, CITIES, FAMILY_TYPES
from admin import SUPER_ADMIN_ID, generate_player_id, hash_password, DEFAULT_ADMIN_PASSWORD, is_super_admin, add_admin, list_admins
from jobs import JOBS, list_jobs, work, can_take_job
from combat import street_fight, pvp_fight
from time_system import GameTime
from database import init_database, save_player, load_player_by_numeric_id, apply_loaded_data, PSYCOPG2_AVAILABLE
from render import render_status_card, render_profile

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# حافظه موقت بازیکن‌ها (اگر دیتابیس نباشد)
PLAYERS = {}  # numeric_id -> Character-like dict/object
GAME_TIMES = {}

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ==================== کلاس ساده شخصیت برای ربات ====================
class BotPlayer:
    def __init__(self, numeric_id: str, name: str = None):
        self.numeric_id = str(numeric_id)
        self.player_id = generate_player_id()
        self.gender = random.choice(["پسر", "دختر"])
        self.name = name or random.choice(["پارسا", "آرین", "سارا", "نیما", "هلیا", "کیان"])
        self.display_name = self.name
        self.city = random.choice(CITY_LIST[:50])
        city_data = CITIES.get(self.city, {})
        self.neighborhood = random.choice(city_data.get("neighborhoods", ["مرکز شهر"]))
        self.family = random.choice(FAMILY_TYPES)
        self.home = "آپارتمان اجاره‌ای"
        self.birth_year = 1385
        self.age_days = random.randint(6000, 9000)  # جوان
        self.hunger = random.randint(30, 60)
        self.thirst = random.randint(20, 50)
        self.fatigue = random.randint(10, 40)
        self.health = random.randint(70, 95)
        self.mental = random.randint(50, 85)
        self.money = random.randint(5_000_000, 30_000_000)
        self.location = "خانه"
        self.x = self.y = 0
        self.god_mode = False
        self.marital_status = "مجرد"
        self.bio = ""
        self.job = "بیکار"
        self.children = []
        self.alive = True
        self.admin_password_hash = hash_password(DEFAULT_ADMIN_PASSWORD, self.player_id)

    def status_text(self):
        return (
            f"👤 {self.display_name} ({self.gender})\n"
            f"🏙 {self.city} | {self.neighborhood}\n"
            f"💼 شغل: {self.job}\n"
            f"💰 {self.money:,} تومان\n"
            f"❤️ سلامت: {self.health}% | 🧠 روحیه: {self.mental}%\n"
            f"🍖 گرسنگی: {self.hunger}% | 💧 تشنگی: {self.thirst}%\n"
            f"😴 خستگی: {self.fatigue}%\n"
            f"📍 {self.location}"
        )


def get_or_create_player(user_id: str, name: str = None) -> BotPlayer:
    uid = str(user_id)
    if uid in PLAYERS:
        return PLAYERS[uid]

    # تلاش برای لود از دیتابیس
    if PSYCOPG2_AVAILABLE:
        data = load_player_by_numeric_id(uid)
        if data:
            p = BotPlayer(uid, data.get("name"))
            # اعمال داده
            for k, v in data.items():
                if hasattr(p, k) and v is not None:
                    setattr(p, k, v)
            PLAYERS[uid] = p
            return p

    p = BotPlayer(uid, name)
    PLAYERS[uid] = p
    if PSYCOPG2_AVAILABLE:
        save_player(p)
    return p


# ==================== هندلرها ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.first_name)

    keyboard = [
        ["وضعیت", "پروفایل"],
        ["شمال", "جنوب", "شرق", "غرب"],
        ["شغل", "کار کن", "دعوا"],
        ["زمان", "کمک"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"سلام {user.first_name}!\n"
        f"به شبیه‌ساز زندگی یک ایرانی خوش اومدی.\n\n"
        f"{player.status_text()}\n\n"
        f"از دکمه‌ها یا دستورات استفاده کن.",
        reply_markup=reply_markup
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 راهنما\n\n"
        "وضعیت / پروفایل → اطلاعات تو\n"
        "شمال جنوب شرق غرب → حرکت در شهر\n"
        "شغل → لیست شغل‌ها\n"
        "کار کن → کار کردن با شغل فعلی\n"
        "دعوا → دعوای خیابانی\n"
        "زمان → ساعت فعلی\n"
        "انتخاب شغل نام_شغل → تغییر شغل\n"
        "ادمین → پنل ادمین (اگر دسترسی داری)\n"
    )
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()
    player = get_or_create_player(user.id, user.first_name)

    if not player.alive:
        await update.message.reply_text("💀 شخصیتت مرده. با /start دوباره شروع کن (یا از ادمین کمک بگیر).")
        return

    # زمان
    if user.id not in GAME_TIMES:
        GAME_TIMES[user.id] = GameTime(start_hour=random.randint(7, 20))
    gt = GAME_TIMES[user.id]

    reply = None

    if text in ["وضعیت", "status"]:
        reply = render_status_card(player, gt)

    elif text in ["پروفایل", "profile"]:
        reply = render_profile(player)

    elif text in ["شمال", "جنوب", "شرق", "غرب", "n", "s", "e", "w"]:
        gt.advance(random.randint(15, 40))
        player.fatigue = min(100, player.fatigue + random.randint(3, 8))
        player.thirst = min(120, player.thirst + random.randint(2, 6))
        places = ["خیابان اصلی", "کوچه", "میدان", "نانوایی", "سوپرمارکت", "پارک", "مسجد"]
        player.location = random.choice(places)
        reply = f"رفتی سمت {text}.\nرسیدی به: {player.location}\n🕐 {gt.formatted()}"
        if random.random() < 0.12:
            reply += "\n\n" + street_fight(player)

    elif text in ["شغل", "jobs"]:
        reply = "مشاغل موجود:\n" + list_jobs() + "\n\nبرای انتخاب بنویس:\nانتخاب شغل نام_شغل"

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
            reply = "اول یه شغل انتخاب کن (دستور: شغل)"
        else:
            reply = work(player, player.job)

    elif text in ["دعوا", "fight"]:
        reply = street_fight(player)

    elif text in ["زمان", "time"]:
        reply = f"🕐 {gt.formatted()}"

    elif text in ["کمک", "help", "/help"]:
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
                reply = f"🔑 ادمین اصلی\nدستورات: addadmin / listadmins\nآیدی تو: {user.id}"
        else:
            reply = "دسترسی ادمین نداری."

    else:
        reply = "متوجه نشدم. «کمک» رو بزن یا از دکمه‌ها استفاده کن."

    # ذخیره
    if PSYCOPG2_AVAILABLE:
        try:
            save_player(player)
        except:
            pass

    if reply:
        await update.message.reply_text(reply)


def main_bot():
    if not TELEGRAM_AVAILABLE:
        print("python-telegram-bot نصب نیست.")
        return
    if not TOKEN:
        print("توکن ربات را تنظیم کن: export TELEGRAM_BOT_TOKEN=your_token")
        print("از @BotFather در تلگرام توکن بگیر.")
        return

    if PSYCOPG2_AVAILABLE:
        init_database()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("ربات شروع شد...")
    app.run_polling()


if __name__ == "__main__":
    main_bot()
