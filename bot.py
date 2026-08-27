#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات تلگرام - شبیه‌ساز زندگی یک ایرانی
"""

import os
import sys
import logging
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from difficulty import hard_cost

try:
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("برای ربات تلگرام نصب کنید: pip install python-telegram-bot")

from locations import CITY_LIST, CITIES, FAMILY_TYPES, IRAN_CITIES
from iran_cities_full import load_full_iran_cities
from shops import SHOPS, shop_list_text, buy_item, use_item
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
from map_system import DIRECTIONS, generate_location_name, get_random_description
from advanced_simulation import (ensure_advanced, daily_tick, advanced_status, city_economy_adv, work_day, train_skill, bank_deposit_adv, bank_withdraw_adv, take_loan_adv, meet_npc, relationship_action, commit_crime_adv, start_business_adv, run_business_adv, stock_trade_adv)
from life_features import (ensure_data, education_text, study, bank_text, bank_deposit, bank_withdraw, bank_loan,
    housing_text, rent_house, buy_house, vehicle_text, buy_vehicle, relationship_text, meet_partner, marry, have_child,
    legal_text, commit_crime, pay_fine, hospital, business_text, start_business, run_business, stock_text, stock_trade,
    tax_text, pay_tax, economic_tick, city_economy_text, serve_jail)

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

# Render Web Service health server.
# Telegram bot همچنان با polling کار می‌کند، اما Render باید یک پورت HTTP
# روی 0.0.0.0 ببیند تا deploy و health check موفق شوند.
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health", "/healthz"):
            body = b"OK - Iranian Life Simulator is running"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_render_health_server():
    """Start a tiny HTTP server for Render health checks."""
    port = int(os.getenv("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, name="render-health", daemon=True)
    thread.start()
    logger.info("Render health server listening on 0.0.0.0:%s", port)
    return server

MALE_NAMES = ["پارسا", "آرین", "کیان", "سپهر", "نیما", "آرش", "رادین", "ایلیا", "مانی", "سینا", "رضا", "امیر"]
FEMALE_NAMES = ["یسنا", "آوا", "هلیا", "نازنین", "سارا", "دنیا", "مهسا", "آیدا", "نیکا", "باران", "هستی", "کیمیا"]

# فقط شهرهای ایران برای شروع
IRAN_CITY_SET = set(load_full_iran_cities(IRAN_CITIES))



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
        self.age_days = 170  # بازی اصلی از ۱۷ سالگی آغاز می‌شود
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
        self.inventory = {}
        self.life_data = {}
        ensure_data(self)
        ensure_advanced(self)
        self.alive = True
        self.pregnant = False
        self.pregnancy_days = 0
        self.conception_attempt = None
        self.admin_password_hash = hash_password(DEFAULT_ADMIN_PASSWORD, self.player_id)

    def status_text(self):
        return (
            f"👤 {self.display_name} ({self.gender}) | سن: {max(17, self.age_days // 10)} سال\n"
            f"🏙 {self.city} | {self.neighborhood}\n"
            f"💼 شغل: {self.job}\n"
            f"💰 {self.money:,} تومان\n"
            f"❤️ سلامت: {self.health}% | 🧠 روحیه: {self.mental}%\n"
            f"🍖 گرسنگی: {self.hunger}% | 💧 تشنگی: {self.thirst}%\n"
            f"😴 خستگی: {self.fatigue}%\n"
            f"📍 {self.location}"
            f"\n🎒 وسایل: {sum(self.inventory.values()) if self.inventory else 0} عدد"
        )


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["وضعیت", "پروفایل"],
            ["خانه", "خانواده", "زندگی", "استراحت"],
            ["🧭 حرکت"],
            ["شغل", "کار کن", "دعوا"],
            ["🏪 مغازه‌ها", "🎒 کوله‌پشتی"],
            ["🏫 تحصیل", "🏦 بانک", "🏠 مسکن"],
            ["🚗 وسایل نقلیه", "❤️ روابط", "⚖️ قانون"],
            ["🏥 بیمارستان", "🏢 کسب‌وکار", "📈 بورس"],
            ["🧾 مالیات", "شهرها", "سفر"],
            ["🧠 زندگی هوشمند", "زمان", "کمک"],
        ],
        resize_keyboard=True,
    )


def movement_keyboard(owner_id: str | None = None):
    """پنل دکمه‌ای حرکت؛ کاربر دیگر لازم نیست جهت را تایپ کند."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬆️ شمال", callback_data=_owner_callback("move", owner_id, "north")),
        ],
        [
            InlineKeyboardButton("⬅️ غرب", callback_data=_owner_callback("move", owner_id, "west")),
            InlineKeyboardButton("🏠 خانه", callback_data=_owner_callback("move", owner_id, "home")),
            InlineKeyboardButton("➡️ شرق", callback_data=_owner_callback("move", owner_id, "east")),
        ],
        [
            InlineKeyboardButton("⬇️ جنوب", callback_data=_owner_callback("move", owner_id, "south")),
        ],
        [
            InlineKeyboardButton("🏪 مغازه‌ها", callback_data=_owner_callback("shop", owner_id, "list")),
        ],
        [
            InlineKeyboardButton("🔄 تازه‌سازی موقعیت", callback_data=_owner_callback("move", owner_id, "panel")),
        ],
    ])


def movement_text(player, gt):
    return (
        "🧭 **پنل حرکت**\n\n"
        f"📍 مکان فعلی: {player.location}\n"
        f"🏙 شهر: {player.city} | {player.neighborhood}\n"
        f"📌 مختصات: ({player.x}, {player.y})\n\n"
        "با دکمه‌های زیر حرکت کن:"
    )


def get_player(user_id: str):
    return PLAYERS.get(str(user_id))


def get_or_load_player(user_id: str):
    """Get the in-memory player or restore it from PostgreSQL after a restart."""
    uid = str(user_id)
    player = PLAYERS.get(uid)
    if player:
        return player
    if PSYCOPG2_AVAILABLE:
        try:
            data = load_player_by_numeric_id(uid)
            if data:
                player = BotPlayer(uid, name=data.get("name"), city=data.get("city"))
                apply_loaded_data(player, data)
                PLAYERS[uid] = player
                if uid not in GAME_TIMES:
                    GAME_TIMES[uid] = GameTime(start_hour=random.randint(7, 20))
                return player
        except Exception as exc:
            logger.warning("Could not restore player %s: %s", uid, exc)
    return None


def _owner_callback(prefix: str, owner_id: str | None, *parts: str) -> str:
    """Build callback data. Group panels carry the owner's Telegram ID."""
    values = [prefix]
    if owner_id:
        values.append(str(owner_id))
    values.extend(str(x) for x in parts)
    return ":".join(values)


def _callback_owner_and_parts(data: str, prefix: str):
    parts = data.split(":")
    if not parts or parts[0] != prefix:
        return None, []
    # New group-safe form: prefix:telegram_user_id:action...
    if len(parts) >= 3 and parts[1].isdigit():
        return parts[1], parts[2:]
    # Legacy private form: prefix:action...
    return None, parts[1:]


def _is_authorized_panel(query, owner_id: str | None) -> bool:
    if owner_id is None:
        return True
    return str(query.from_user.id) == str(owner_id)


def group_panel_keyboard(owner_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 وضعیت من", callback_data=_owner_callback("life", owner_id, "status")),
         InlineKeyboardButton("👤 پروفایل", callback_data=_owner_callback("life", owner_id, "profile"))],
        [InlineKeyboardButton("🧭 حرکت", callback_data=_owner_callback("move", owner_id, "panel")),
         InlineKeyboardButton("🌍 زندگی", callback_data=_owner_callback("life", owner_id, "menu"))],
        [InlineKeyboardButton("🏪 مغازه‌ها", callback_data=_owner_callback("shop", owner_id, "list")),
         InlineKeyboardButton("🎒 کوله‌پشتی", callback_data=_owner_callback("life", owner_id, "inventory"))],
        [InlineKeyboardButton("💼 کار", callback_data=_owner_callback("life", owner_id, "advwork")),
         InlineKeyboardButton("😴 استراحت", callback_data=_owner_callback("life", owner_id, "rest"))],
        [InlineKeyboardButton("🔄 تازه‌سازی", callback_data=_owner_callback("life", owner_id, "panel"))],
    ])


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
    """Start is a one-time initialization command for a living player.

    Once a character exists and is alive, /start must NOT ask for a city or
    recreate/reset the character. A new life can only be created after death.
    """
    user = update.effective_user
    uid = str(user.id)
    player = get_or_load_player(uid)

    # Already alive: /start is finished and simply opens the existing game.
    if player and player.alive:
        WAITING_CITY.discard(uid)
        gt = GAME_TIMES.setdefault(uid, GameTime(start_hour=random.randint(7, 20)))
        await update.message.reply_text(
            f"🎮 {player.display_name}، زندگی‌ات از قبل شروع شده و هنوز زنده‌ای.\n\n"
            f"سن: {player.age} سال\n"
            f"شهر: {player.city}\n\n"
            f"از اینجا ادامه بده؛ /start زندگی فعلی را ریست نمی‌کند.",
            reply_markup=(group_panel_keyboard(uid)
                          if update.effective_chat.type != "private"
                          else main_keyboard()),
        )
        return

    # Dead player: /start explicitly begins a new life.
    if player and not player.alive:
        WAITING_CITY.add(uid)
        await update.message.reply_text(
            f"💀 زندگی قبلی {player.display_name} تمام شده است.\n\n"
            "اگر می‌خواهی یک زندگی کاملاً جدید بسازی، شهر شروع را انتخاب کن.\n"
            "🏙 نام یکی از شهرهای ایران را بفرست یا در گروه از /city تهران استفاده کن.",
            reply_markup=ReplyKeyboardRemove() if update.effective_chat.type == "private" else None,
        )
        return

    # First ever start: create only after city selection.
    WAITING_CITY.add(uid)
    await update.message.reply_text(
        f"سلام {user.first_name}!\n\n"
        "به شبیه‌ساز زندگی یک ایرانی خوش اومدی.\n\n"
        "🎮 بازی اصلی از ۱۷ سالگی شروع می‌شه.\n"
        "🏙 اول شهر شروع زندگی را انتخاب کن.\n\n"
        "مثال: تهران، اهواز، مشهد، اصفهان، شیراز، رشت، تبریز\n\n"
        "بعد از ساخت شخصیت، دیگر /start از تو شهر نمی‌خواهد و زندگی‌ات را ریست نمی‌کند.",
        reply_markup=ReplyKeyboardRemove() if update.effective_chat.type == "private" else None,
    )


async def movement_callback(update, context):
    query = update.callback_query
    owner_id, parts = _callback_owner_and_parts(query.data, "move")
    if not _is_authorized_panel(query, owner_id):
        await query.answer("⛔ این پنل برای بازیکن دیگری است.", show_alert=True)
        return
    await query.answer()
    uid = str(query.from_user.id)
    player = get_or_load_player(uid)

    if not player:
        await query.edit_message_text("اول /start را بزن و شخصیتت را بساز.")
        return
    if not player.alive:
        await query.edit_message_text("💀 شخصیتت مرده. برای شروع دوباره /start را بزن.")
        return

    if uid not in GAME_TIMES:
        GAME_TIMES[uid] = GameTime(start_hour=random.randint(7, 20))
    gt = GAME_TIMES[uid]
    action = parts[0] if parts else "panel"

    if action == "panel":
        await query.edit_message_text(movement_text(player, gt), reply_markup=movement_keyboard(owner_id))
        return

    if action == "home":
        player.location = "خانه"
        await query.edit_message_text(
            f"🏠 به خانه برگشتی.\n\n{movement_text(player, gt)}",
            reply_markup=movement_keyboard(owner_id),
        )
        if PSYCOPG2_AVAILABLE:
            try:
                save_player(player)
            except Exception:
                pass
        return

    direction_map = {
        "north": ("شمال", DIRECTIONS["شمال"]),
        "south": ("جنوب", DIRECTIONS["جنوب"]),
        "east": ("شرق", DIRECTIONS["شرق"]),
        "west": ("غرب", DIRECTIONS["غرب"]),
    }
    if action not in direction_map:
        await query.edit_message_text("❌ جهت نامعتبر است.", reply_markup=movement_keyboard(owner_id))
        return
    direction, (dx, dy) = direction_map[action]

    gt.advance(random.randint(15, 40))
    player.x += dx
    player.y += dy
    player.location = generate_location_name(player.city, player.neighborhood)
    player.fatigue = min(100, player.fatigue + random.randint(3, 8))
    player.thirst = min(120, player.thirst + random.randint(2, 6))
    player.hunger = min(120, player.hunger + random.randint(1, 5))

    age_msgs = advance_life_age(player, gt.day)
    smart_msgs = daily_tick(player, gt.day)
    text = (
        f"🚶 به سمت {direction} حرکت کردی.\n"
        f"📍 {player.location}\n"
        f"📌 مختصات جدید: ({player.x}, {player.y})\n"
        f"📝 {get_random_description()}\n"
        f"🕐 {gt.formatted()}"
    )
    if age_msgs:
        text += "\n\n" + "\n".join(age_msgs)
    if smart_msgs:
        text += "\n\n" + "\n".join(smart_msgs[-3:])

    if random.random() < 0.12:
        fight_result = street_fight(player)
        text += "\n\n" + fight_result

    if not player.alive:
        text += "\n\n💀 مردی! برای شروع مجدد /start بزن."

    if PSYCOPG2_AVAILABLE:
        try:
            save_player(player)
        except Exception:
            pass

    await query.edit_message_text(text + "\n\n" + movement_text(player, gt), reply_markup=movement_keyboard(owner_id))



def life_keyboard(owner_id: str | None = None):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏫 تحصیل", callback_data=_owner_callback("life", owner_id, "education")), InlineKeyboardButton("📚 درس خواندن", callback_data=_owner_callback("life", owner_id, "study"))],
        [InlineKeyboardButton("🏦 بانک", callback_data=_owner_callback("life", owner_id, "bank")), InlineKeyboardButton("💰 واریز ۱ میلیون", callback_data=_owner_callback("life", owner_id, "deposit1")), InlineKeyboardButton("💵 برداشت ۱ میلیون", callback_data=_owner_callback("life", owner_id, "withdraw1"))],
        [InlineKeyboardButton("💳 وام", callback_data=_owner_callback("life", owner_id, "loan"))],
        [InlineKeyboardButton("🏠 مسکن", callback_data=_owner_callback("life", owner_id, "housing")), InlineKeyboardButton("🔑 اجاره", callback_data=_owner_callback("life", owner_id, "rent")), InlineKeyboardButton("🏡 خرید خانه", callback_data=_owner_callback("life", owner_id, "buyhouse"))],
        [InlineKeyboardButton("🚗 خودرو و موتور", callback_data=_owner_callback("life", owner_id, "vehicles"))],
        [InlineKeyboardButton("❤️ روابط", callback_data=_owner_callback("life", owner_id, "relationship")), InlineKeyboardButton("💞 آشنایی/قرار", callback_data=_owner_callback("life", owner_id, "meet")), InlineKeyboardButton("💍 ازدواج", callback_data=_owner_callback("life", owner_id, "marry"))],
        [InlineKeyboardButton("👶 فرزند", callback_data=_owner_callback("life", owner_id, "child"))],
        [InlineKeyboardButton("⚖️ پلیس و قانون", callback_data=_owner_callback("life", owner_id, "legal")), InlineKeyboardButton("⚠️ جرم", callback_data=_owner_callback("life", owner_id, "crime")), InlineKeyboardButton("💸 پرداخت جریمه", callback_data=_owner_callback("life", owner_id, "fine"))],
        [InlineKeyboardButton("🔒 زندان", callback_data=_owner_callback("life", owner_id, "jail"))],
        [InlineKeyboardButton("🏥 بیمارستان", callback_data=_owner_callback("life", owner_id, "hospital")), InlineKeyboardButton("🏙 اقتصاد شهر", callback_data=_owner_callback("life", owner_id, "cityeconomy"))],
        [InlineKeyboardButton("🏢 کسب‌وکار", callback_data=_owner_callback("life", owner_id, "business")), InlineKeyboardButton("🚀 راه‌اندازی", callback_data=_owner_callback("life", owner_id, "startbiz")), InlineKeyboardButton("📊 فعالیت", callback_data=_owner_callback("life", owner_id, "runbiz"))],
        [InlineKeyboardButton("📈 بورس", callback_data=_owner_callback("life", owner_id, "stocks")), InlineKeyboardButton("🧾 مالیات", callback_data=_owner_callback("life", owner_id, "tax")), InlineKeyboardButton("💳 پرداخت مالیات", callback_data=_owner_callback("life", owner_id, "paytax"))],
        [InlineKeyboardButton("🧠 وضعیت عمیق", callback_data=_owner_callback("life", owner_id, "advanced")), InlineKeyboardButton("🤝 آشنایی", callback_data=_owner_callback("life", owner_id, "advmeet"))],
        [InlineKeyboardButton("💼 یک روز کار", callback_data=_owner_callback("life", owner_id, "advwork")), InlineKeyboardButton("📚 آموزش مهارت", callback_data=_owner_callback("life", owner_id, "advtrain"))],
        [InlineKeyboardButton("🏦 واریز ۱۰ میلیون", callback_data=_owner_callback("life", owner_id, "advdeposit")), InlineKeyboardButton("💳 وام ۱۰ میلیون", callback_data=_owner_callback("life", owner_id, "advloan"))],
        [InlineKeyboardButton("🏢 کسب‌وکار پیشرفته", callback_data=_owner_callback("life", owner_id, "advbiz"))],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data=_owner_callback("move", owner_id, "panel"))],
    ])


def life_trade_keyboard(owner_id: str | None = None):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 خرید فولاد", callback_data=_owner_callback("life", owner_id, "buy", "فولاد")), InlineKeyboardButton("📉 فروش فولاد", callback_data=_owner_callback("life", owner_id, "sell", "فولاد"))],
        [InlineKeyboardButton("📈 خرید خودرو", callback_data=_owner_callback("life", owner_id, "buy", "خودرو")), InlineKeyboardButton("📉 فروش خودرو", callback_data=_owner_callback("life", owner_id, "sell", "خودرو"))],
        [InlineKeyboardButton("📈 خرید فناوری", callback_data=_owner_callback("life", owner_id, "buy", "فناوری")), InlineKeyboardButton("📉 فروش فناوری", callback_data=_owner_callback("life", owner_id, "sell", "فناوری"))],
        [InlineKeyboardButton("📈 خرید بانک", callback_data=_owner_callback("life", owner_id, "buy", "بانک")), InlineKeyboardButton("📉 فروش بانک", callback_data=_owner_callback("life", owner_id, "sell", "بانک"))],
        [InlineKeyboardButton("⬅️ برگشت", callback_data=_owner_callback("life", owner_id, "menu"))],
    ])


async def life_callback(update, context):
    query = update.callback_query
    owner_id, action = _callback_owner_and_parts(query.data, "life")
    if not _is_authorized_panel(query, owner_id):
        await query.answer("⛔ این پنل برای بازیکن دیگری است.", show_alert=True)
        return
    await query.answer()
    uid = str(query.from_user.id)
    player = get_or_load_player(uid)
    if not player or not player.alive:
        await query.edit_message_text("اول /start را بزن و شخصیتت را بساز.")
        return
    if uid not in GAME_TIMES:
        GAME_TIMES[uid] = GameTime(start_hour=random.randint(7, 20))
    gt = GAME_TIMES[uid]
    key = action[0] if action else "menu"
    text = ""
    markup = life_keyboard(owner_id)
    if key == "menu": text = "🌍 سیستم‌های زندگی\n\nیکی از بخش‌ها را انتخاب کن:"
    elif key == "panel": text = f"🎮 پنل شخصی {player.display_name}\n\n{player.status_text()}"; markup = group_panel_keyboard(uid) if owner_id else life_keyboard(owner_id)
    elif key == "status": text = render_status_card(player, gt)
    elif key == "profile": text = render_profile(player)
    elif key == "inventory":
        inv = getattr(player, "inventory", {}) or {}
        text = "🎒 کوله‌پشتی خالیه." if not inv else "🎒 کوله‌پشتی\n\n" + "\n".join(f"• {k}: {v}" for k, v in inv.items())
    elif key == "rest":
        player.fatigue = max(0, player.fatigue - random.randint(12, 25))
        player.mental = min(100, player.mental + random.randint(1, 5))
        gt.advance(120)
        text = "😴 استراحت کردی و انرژی‌ات بهتر شد.\n" + daily_life_event(player)
    elif key == "use": text = use_item(player, action[1])[1] if len(action)>1 else "❌ آیتم مشخص نیست."
    elif key == "usei":
        inv = getattr(player, "inventory", {}) or {}
        try:
            item_name = list(inv.keys())[int(action[1])]
            text = use_item(player, item_name)[1]
        except Exception:
            text = "❌ آیتم پیدا نشد."
    elif key == "advanced": text = advanced_status(player) + "\n\n" + city_economy_adv(player)
    elif key == "advmeet": text = meet_npc(player)
    elif key == "advwork": text = work_day(player, overtime=False)
    elif key == "advtrain": text = train_skill(player, "ارتباطات", 2)
    elif key == "advdeposit": text = bank_deposit_adv(player, 10_000_000, savings=True)
    elif key == "advloan": text = take_loan_adv(player, 10_000_000)
    elif key == "advbiz": text = start_business_adv(player, "کسب‌وکار محلی") if not ensure_advanced(player)["businesses"] else run_business_adv(player)
    elif key == "education": text = education_text(player)
    elif key == "study": text = study(player, gt)
    elif key == "bank": text = bank_text(player)
    elif key == "deposit1": text = bank_deposit(player, 1_000_000)
    elif key == "withdraw1": text = bank_withdraw(player, 1_000_000)
    elif key == "loan": text = bank_loan(player)
    elif key == "housing": text = housing_text(player)
    elif key == "rent": text = rent_house(player)
    elif key == "buyhouse": text = buy_house(player)
    elif key == "vehicles": text = vehicle_text(player)
    elif key == "buyvehicle":
        vehicle_codes = {"m": "موتورسیکلت", "e": "خودروی اقتصادی", "f": "خودروی خانوادگی"}
        vehicle_name = vehicle_codes.get(action[1], action[1]) if len(action) > 1 else None
        text = buy_vehicle(player, vehicle_name) if vehicle_name else vehicle_text(player)
    elif key == "relationship": text = relationship_text(player)
    elif key == "meet": text = meet_partner(player)
    elif key == "marry": text = marry(player)
    elif key == "child": text = have_child(player)
    elif key == "legal": text = legal_text(player)
    elif key == "crime": text = commit_crime(player)
    elif key == "fine": text = pay_fine(player)
    elif key == "hospital": text = hospital(player)
    elif key == "cityeconomy": text = city_economy_text(player)
    elif key == "jail": text = serve_jail(player)
    elif key == "business": text = business_text(player)
    elif key == "startbiz": text = start_business(player)
    elif key == "runbiz": text = run_business(player)
    elif key == "stocks": text = stock_text(player); markup = life_trade_keyboard(owner_id)
    elif key == "buy": text = stock_trade(player, action[1], True); markup = life_trade_keyboard(owner_id)
    elif key == "sell": text = stock_trade(player, action[1], False); markup = life_trade_keyboard(owner_id)
    elif key == "tax": text = tax_text(player)
    elif key == "paytax": text = pay_tax(player)
    else: text = "🌍 سیستم زندگی"
    economic_tick(player, gt.day)
    daily_tick(player, gt.day)
    if PSYCOPG2_AVAILABLE:
        try: save_player(player)
        except Exception: pass
    await query.edit_message_text(text + "\n\n" + ("روز بازی: " + str(gt.day + 1)), reply_markup=markup)


def shop_keyboard(owner_id: str | None = None):
    rows = []
    for i, (name, data) in enumerate(SHOPS.items()):
        rows.append([InlineKeyboardButton(f"{data['icon']} {name}", callback_data=_owner_callback("shop", owner_id, "open", i))])
    rows.append([InlineKeyboardButton("⬅️ برگشت به حرکت", callback_data=_owner_callback("move", owner_id, "panel"))])
    return InlineKeyboardMarkup(rows)


def shop_items_keyboard(shop_name, owner_id: str | None = None):
    shop = SHOPS[shop_name]
    shop_i = list(SHOPS.keys()).index(shop_name)
    rows = []
    for item_i, (item, (price, _)) in enumerate(shop["items"].items()):
        rows.append([InlineKeyboardButton(f"{item} — {price:,} تومان", callback_data=_owner_callback("shop", owner_id, "buy", shop_i, item_i))])
    rows.append([InlineKeyboardButton("⬅️ مغازه‌ها", callback_data=_owner_callback("shop", owner_id, "list"))])
    return InlineKeyboardMarkup(rows)


def shop_text(shop_name, player):
    shop = SHOPS[shop_name]
    lines = [f"{shop['icon']} **{shop_name}**", f"💰 پول: {player.money:,} تومان", "", "کالا را انتخاب کن:"]
    for item, (price, _) in shop["items"].items():
        lines.append(f"• {item}: {price:,} تومان")
    return "\n".join(lines)


async def shop_callback(update, context):
    query = update.callback_query
    owner_id, parts = _callback_owner_and_parts(query.data, "shop")
    if not _is_authorized_panel(query, owner_id):
        await query.answer("⛔ این پنل برای بازیکن دیگری است.", show_alert=True)
        return
    await query.answer()
    uid = str(query.from_user.id)
    player = get_or_load_player(uid)
    if not player or not player.alive:
        await query.edit_message_text("اول /start را بزن و شخصیتت را بساز.")
        return
    action = parts[0] if parts else "list"
    if action == "list":
        await query.edit_message_text(shop_list_text(), reply_markup=shop_keyboard(owner_id))
        return
    if action == "open" and len(parts) >= 2:
        try:
            shop_name = list(SHOPS.keys())[int(parts[1])]
        except Exception:
            await query.edit_message_text("❌ مغازه پیدا نشد.", reply_markup=shop_keyboard(owner_id))
            return
        await query.edit_message_text(shop_text(shop_name, player), reply_markup=shop_items_keyboard(shop_name, owner_id))
        return
    if action == "buy" and len(parts) >= 3:
        try:
            shop_i, item_i = int(parts[1]), int(parts[2])
            shop_name = list(SHOPS.keys())[shop_i]
            item_name = list(SHOPS[shop_name]["items"].keys())[item_i]
        except Exception:
            await query.edit_message_text("❌ اطلاعات خرید نامعتبر است.", reply_markup=shop_keyboard(owner_id))
            return
        ok, msg = buy_item(player, shop_name, item_name)
        if PSYCOPG2_AVAILABLE:
            try: save_player(player)
            except Exception: pass
        await query.edit_message_text(msg + "\n\n" + shop_text(shop_name, player), reply_markup=shop_items_keyboard(shop_name, owner_id))


async def panel_cmd(update, context):
    """Show a personal inline panel. Safe for groups: only the owner can use its buttons."""
    uid = str(update.effective_user.id)
    player = get_or_load_player(uid)
    if not player:
        await update.message.reply_text("🎮 هنوز شخصیت نداری. /start را بزن و شهر را انتخاب کن.")
        return
    if not player.alive:
        await update.message.reply_text("💀 شخصیتت مرده. برای شروع دوباره /start را بزن.")
        return
    gt = GAME_TIMES.setdefault(uid, GameTime(start_hour=random.randint(7, 20)))
    await update.message.reply_text(
        f"🎮 پنل شخصی {player.display_name}\n\n{player.status_text()}",
        reply_markup=group_panel_keyboard(uid) if update.effective_chat.type != "private" else main_keyboard()
    )


async def city_cmd(update, context):
    """Group-safe city selection: /city Tehran"""
    uid = str(update.effective_user.id)
    args = getattr(context, "args", []) or []
    city_text = " ".join(args).strip()
    if not city_text:
        await update.message.reply_text("🏙 مثال: /city تهران")
        return
    city = find_iran_city(city_text)
    if not city:
        await update.message.reply_text("❌ شهر پیدا نشد. فقط شهرهای ایران مجاز هستند. مثال: /city تهران")
        return
    player = create_fresh_player(uid, name=update.effective_user.first_name, city=city)
    WAITING_CITY.discard(uid)
    await update.message.reply_text(
        f"🎂 زندگی جدیدت از ۱۷ سالگی شروع شد.\n\n{player.status_text()}",
        reply_markup=group_panel_keyboard(uid) if update.effective_chat.type != "private" else main_keyboard()
    )


async def status_cmd(update, context):
    uid = str(update.effective_user.id)
    player = get_or_load_player(uid)
    if not player:
        await update.message.reply_text("اول /start و سپس /city تهران را بزن.")
        return
    gt = GAME_TIMES.setdefault(uid, GameTime(start_hour=random.randint(7, 20)))
    await update.message.reply_text(render_status_card(player, gt), reply_markup=group_panel_keyboard(uid) if update.effective_chat.type != "private" else None)


async def move_cmd(update, context):
    uid = str(update.effective_user.id)
    player = get_or_load_player(uid)
    if not player:
        await update.message.reply_text("اول /start و سپس /city تهران را بزن.")
        return
    gt = GAME_TIMES.setdefault(uid, GameTime(start_hour=random.randint(7, 20)))
    await update.message.reply_text(movement_text(player, gt), reply_markup=movement_keyboard(uid))


async def life_cmd(update, context):
    uid = str(update.effective_user.id)
    player = get_or_load_player(uid)
    if not player:
        await update.message.reply_text("اول /start و سپس /city تهران را بزن.")
        return
    await update.message.reply_text("🌍 سیستم‌های زندگی\n\nیکی از بخش‌ها را انتخاب کن:", reply_markup=life_keyboard(uid))


async def shop_cmd(update, context):
    uid = str(update.effective_user.id)
    player = get_or_load_player(uid)
    if not player:
        await update.message.reply_text("اول /start و سپس /city تهران را بزن.")
        return
    await update.message.reply_text(shop_list_text(), reply_markup=shop_keyboard(uid))


async def help_cmd(update, context):
    await update.message.reply_text(
        "📖 راهنما\n\n"
        "/start → شروع جدید / زنده شدن بعد از مرگ (ریست کامل)\n"
        "وضعیت / پروفایل\n"
        "خانه / خانواده / زندگی → مدیریت و مشاهده زندگی\n"
        "استراحت → استراحت در خانه\n"
        "🧭 حرکت → باز کردن پنل دکمه‌ای حرکت\n"
        "شغل → لیست شغل‌ها\n"
        "انتخاب شغل نام_شغل\n"
        "کار کن → کار کردن\n"
        "دعوا → دعوای خیابانی\n"
        "🏪 مغازه‌ها → ورود به مغازه و خرید\n"
        "🎒 کوله‌پشتی → وسایل خریداری‌شده\n"
        "شهرها → فهرست شهرهای ایران\n"
        "سفر نام شهر → سفر به شهر دیگر\n"
        "زمان\n"
        "🏫 تحصیل / 🏦 بانک / 🏠 مسکن / 🚗 خودرو\n"
        "❤️ روابط / 👶 فرزند / ⚖️ قانون / 🏥 بیمارستان\n"
        "🏢 کسب‌وکار / 📈 بورس / 🧾 مالیات / 🏙 اقتصاد شهر\n\n"
        "⏳ هر ۱۰ روز بازی = ۱ سال زندگی.\n"
        "⚠️ وقتی زنده‌ای، /start زندگی‌ات را ریست نمی‌کند. فقط بعد از مرگ می‌توانی با /start زندگی جدید بسازی."
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

        # کیبورد پایین صفحه فقط در چت خصوصی نمایش داده شود؛
        # در گروه‌ها پیام‌ها عادی ارسال می‌شوند و Reply Keyboard ساخته نمی‌شود.
        markup = main_keyboard() if update.effective_chat and update.effective_chat.type == "private" else None
        await update.message.reply_text(
            f"👶 تو در ۰ سالگی به دنیا اومدی.\n\n"
            f"🏙 شهر: {player.city}\n"
            f"👤 نام: {player.name} ({player.gender})\n"
            f"👨‍👩‍👧 خانواده: {player.family}\n"
            f"🏠 خانه: {player.home}\n\n"
            f"{family_text(player)}\n\n"
            f"📖 چند سال اول زندگی‌ات در کنار خانواده گذشت؛ رشد کردی، محیط اطرافت را شناختی و شخصیتت شکل گرفت.\n\n"
            f"🎂 حالا داستان اصلی از ۱۷ سالگی شروع می‌شود.\n"
            f"⏳ از اینجا به بعد هر ۱۰ روز بازی = ۱ سال زندگی.\n\n"
            f"{player.status_text()}",
            reply_markup=markup,
        )
        return

    player = get_or_load_player(uid)

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

    # بازیکن زندانی فقط می‌تواند یک روز از محکومیتش را بگذراند یا وضعیت قانون را ببیند.
    jail_days = ensure_data(player)["legal"].get("jail_days", 0)
    if jail_days > 0 and text not in ["⚖️ قانون", "قانون", "پلیس", "🔒 زندان", "زندگی", "life"]:
        await update.message.reply_text(f"🔒 در زندان هستی. روزهای باقی‌مانده: {jail_days}\nبرای گذراندن یک روز، دکمه «زندان» را بزن.", reply_markup=life_keyboard(uid))
        return

    reply = None

    if text in ["🏫 تحصیل", "تحصیل", "زندگی پیشرفته", "🌍 زندگی"]:
        await update.message.reply_text("🌍 سیستم‌های زندگی\n\nیکی از بخش‌ها را انتخاب کن:", reply_markup=life_keyboard(uid))
        return

    if text in ["🧠 زندگی هوشمند", "زندگی هوشمند", "هوش"]:
        await update.message.reply_text(
            advanced_status(player) + "\n\n" + city_economy_adv(player),
            reply_markup=life_keyboard()
        )
        return

    if text in ["🏦 بانک", "بانک", "bank"]:
        await update.message.reply_text(bank_text(player), reply_markup=life_keyboard(uid))
        return

    if text in ["🏠 مسکن", "مسکن", "خانه و ملک"]:
        await update.message.reply_text(housing_text(player), reply_markup=life_keyboard(uid))
        return

    if text in ["🚗 وسایل نقلیه", "وسایل نقلیه", "خودرو", "ماشین"]:
        await update.message.reply_text(vehicle_text(player), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏍️ موتور", callback_data=_owner_callback("life", uid, "buyvehicle", "m"))],[InlineKeyboardButton("🚗 خودروی اقتصادی", callback_data=_owner_callback("life", uid, "buyvehicle", "e"))],[InlineKeyboardButton("🚙 خودروی خانوادگی", callback_data=_owner_callback("life", uid, "buyvehicle", "f"))],[InlineKeyboardButton("⬅️ برگشت", callback_data=_owner_callback("life", uid, "menu"))]]))
        return

    if text in ["❤️ روابط", "روابط", "ازدواج"]:
        await update.message.reply_text(relationship_text(player), reply_markup=life_keyboard(uid))
        return

    if text in ["⚖️ قانون", "قانون", "پلیس"]:
        await update.message.reply_text(legal_text(player), reply_markup=life_keyboard(uid))
        return

    if text in ["🏥 بیمارستان", "بیمارستان"]:
        await update.message.reply_text(hospital(player), reply_markup=life_keyboard(uid))
        return

    if text in ["🏢 کسب‌وکار", "کسب و کار", "کسب‌وکار"]:
        await update.message.reply_text(business_text(player), reply_markup=life_keyboard(uid))
        return

    if text in ["📈 بورس", "بورس", "سهام"]:
        await update.message.reply_text(stock_text(player), reply_markup=life_trade_keyboard(uid))
        return

    if text in ["🏙 اقتصاد شهر", "اقتصاد شهر"]:
        await update.message.reply_text(city_economy_text(player), reply_markup=life_keyboard(uid))
        return

    if text in ["🧾 مالیات", "مالیات"]:
        await update.message.reply_text(tax_text(player), reply_markup=life_keyboard(uid))
        return

    if text in ["🏪 مغازه‌ها", "مغازه‌ها", "مغازه", "shop"]:
        await update.message.reply_text(shop_list_text(), reply_markup=shop_keyboard(uid))
        return

    if text in ["🎒 کوله‌پشتی", "کوله‌پشتی", "کیف", "inventory"]:
        inv = getattr(player, "inventory", {}) or {}
        if not inv:
            reply = "🎒 کوله‌پشتی خالیه."
            markup = None
        else:
            reply = "🎒 کوله‌پشتی\n\n" + "\n".join(f"• {k}: {v}" for k,v in inv.items())
            rows = []
            for idx, (item, qty) in enumerate(inv.items()):
                rows.append([InlineKeyboardButton(f"استفاده: {item} ×{qty}", callback_data=_owner_callback("life", uid, "usei", idx))])
            markup = InlineKeyboardMarkup(rows)
        await update.message.reply_text(reply, reply_markup=markup)
        return

    if text in ["شهرها", "cities"]:
        cities = sorted(IRAN_CITY_SET)
        reply = f"🏙 فهرست شهرهای ایران: {len(cities)} شهر در دادهٔ فعال\n\n" + "، ".join(cities[:80]) + "\n\nبرای سفر: «سفر نام شهر»"
        await update.message.reply_text(reply)
        return

    if text.startswith("سفر "):
        target = find_iran_city(text[5:].strip())
        if not target:
            reply = "❌ شهر مقصد پیدا نشد. دستور «شهرها» را ببین یا نام شهر را دقیق‌تر بنویس."
        elif target == player.city:
            reply = f"📍 همین الان در {target} هستی."
        else:
            cost = hard_cost(random.randint(150_000, 1_500_000))
            if player.money < cost:
                reply = f"💸 پول کافی برای سفر نداری. هزینه تقریبی: {cost:,} تومان"
            else:
                player.money -= cost
                player.city = target
                city_data = CITIES.get(target, {})
                player.neighborhood = random.choice(city_data.get("neighborhoods", ["مرکز شهر"]))
                player.location = "ترمینال / ایستگاه ورودی شهر"
                gt.advance(random.randint(180, 480))
                age_msgs = advance_life_age(player, gt.day)
                smart_msgs = daily_tick(player, gt.day)
                reply = f"🚌 به {target} سفر کردی.\n💸 هزینه سفر: {cost:,} تومان\n📍 {player.neighborhood}\n💰 موجودی: {player.money:,} تومان"
                if age_msgs: reply += "\n\n" + "\n".join(age_msgs)
                if smart_msgs: reply += "\n\n" + "\n".join(smart_msgs[-3:])
            if PSYCOPG2_AVAILABLE:
                try: save_player(player)
                except Exception: pass
            await update.message.reply_text(reply)
            return

    if text in ["🧭 حرکت", "حرکت", "move"]:
        await update.message.reply_text(movement_text(player, gt), reply_markup=movement_keyboard(uid))
        return

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
        for msg in daily_tick(player, gt.day):
            reply += "\n" + msg
    if text in ["وضعیت", "status"]:
        reply = render_status_card(player, gt)

    elif text in ["پروفایل", "profile"]:
        reply = render_profile(player)

    elif text in ["شمال", "جنوب", "شرق", "غرب", "n", "s", "e", "w"]:
        old_day = gt.day
        gt.advance(random.randint(15, 40))
        age_msgs = advance_life_age(player, gt.day)
        smart_msgs = daily_tick(player, gt.day)
        player.fatigue = min(100, player.fatigue + random.randint(3, 8))
        player.thirst = min(120, player.thirst + random.randint(2, 6))
        player.hunger = min(120, player.hunger + random.randint(1, 5))
        places = ["خیابان اصلی", "کوچه", "میدان", "نانوایی", "سوپرمارکت", "پارک", "مسجد", "ایستگاه اتوبوس"]
        player.location = random.choice(places)
        reply = f"رفتی سمت {text}.\n📍 {player.location}\n🕐 {gt.formatted()}"
        if age_msgs:
            reply += "\n\n" + "\n".join(age_msgs)
        if smart_msgs:
            reply += "\n\n" + "\n".join(smart_msgs[-3:])
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
                ensure_advanced(player)["career"]["job"] = job_name
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
    # On Render this process is deployed as a Web Service so the health endpoint
    # keeps the service observable while the Telegram polling loop runs.
    health_server = None
    if os.getenv("RENDER") or os.getenv("PORT"):
        try:
            health_server = start_render_health_server()
        except OSError as e:
            logger.error("Render health server could not start: %s", e)

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
    app.add_handler(CommandHandler("panel", panel_cmd))
    app.add_handler(CommandHandler("city", city_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("move", move_cmd))
    app.add_handler(CommandHandler("life", life_cmd))
    app.add_handler(CommandHandler("shop", shop_cmd))
    app.add_handler(CallbackQueryHandler(movement_callback, pattern=r"^move:"))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern=r"^shop:"))
    app.add_handler(CallbackQueryHandler(life_callback, pattern=r"^life:"))
    # Text commands work in private chats and groups. For groups, Telegram privacy mode
    # may need to be disabled in BotFather if you want arbitrary non-command text.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("ربات شروع شد...")
    app.run_polling()


if __name__ == "__main__":
    main_bot()
