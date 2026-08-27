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
    init_database, save_player, load_player_by_numeric_id, leaderboard_rows,
    apply_loaded_data, PSYCOPG2_AVAILABLE, get_connection
)
from render import render_status_card, render_profile
from life_system import make_family, home_for_family, home_text, family_text, daily_life_event, advance_life_age
from map_system import DIRECTIONS, generate_location_name, get_random_description
from advanced_simulation import (ensure_advanced, daily_tick, advanced_status, city_economy_adv, work_day, train_skill, bank_deposit_adv, bank_withdraw_adv, take_loan_adv, meet_npc, relationship_action, commit_crime_adv, start_business_adv, run_business_adv, stock_trade_adv)
from living_world import news_text, simulate_npcs
from smart_life import smart_status, smart_advice, smart_decision, smart_goals
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


def child_stage(age: int) -> str:
    if age < 3: return "نوزاد/خردسال"
    if age < 7: return "کودکستان"
    if age < 13: return "دانش‌آموز ابتدایی"
    if age < 16: return "دانش‌آموز متوسطه"
    if age < 19: return "دانش‌آموز دبیرستان"
    return "بزرگسال"


def child_job_for_age(age: int) -> str:
    if age < 7: return "بدون شغل"
    if age < 19: return "دانش‌آموز"
    return "جوان مستقل"

# فقط شهرهای ایران برای شروع
IRAN_CITY_SET = set(load_full_iran_cities(IRAN_CITIES))



class BotPlayer:
    def __init__(self, numeric_id: str, name: str = None, city: str = None):
        self.numeric_id = str(numeric_id)
        self.player_id = generate_player_id()
        self.gender = random.choice(["پسر", "دختر"])
        # نام شخصیت باید با جنسیت شخصیت هماهنگ باشد؛ نام تلگرام دیگر جای نام شخصیت را نمی‌گیرد.
        self.name = random.choice(MALE_NAMES if self.gender == "پسر" else FEMALE_NAMES)
        self.telegram_name = name or "بازیکن"
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
            ["🚗 وسایل نقلیه", "❤️ روابط", "⚖️ قانون", "🚔 پلیس"],
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




def admin_keyboard(is_super: bool = False):
    rows = [
        [InlineKeyboardButton("📊 آمار بازی", callback_data="admin:stats"),
         InlineKeyboardButton("👥 بازیکنان", callback_data="admin:players")],
        [InlineKeyboardButton("🌍 اقتصاد جهان", callback_data="admin:economy"),
         InlineKeyboardButton("🏆 رتبه‌بندی", callback_data="admin:leaderboard")],
        [InlineKeyboardButton("📋 لیست ادمین‌ها", callback_data="admin:admins"),
         InlineKeyboardButton("🔄 تازه‌سازی", callback_data="admin:panel")],
    ]
    if is_super:
        rows.append([InlineKeyboardButton("➕ افزودن ادمین", callback_data="admin:addhelp"),
                     InlineKeyboardButton("➖ حذف ادمین", callback_data="admin:removehelp")])
    rows.append([InlineKeyboardButton("❌ بستن پنل", callback_data="admin:close")])
    return InlineKeyboardMarkup(rows)


def admin_stats_text():
    conn = get_connection() if PSYCOPG2_AVAILABLE else None
    if not conn:
        return "❌ دیتابیس در دسترس نیست."
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE alive), COUNT(*) FILTER (WHERE NOT alive), COALESCE(SUM(money),0), COALESCE(AVG(age_days),0) FROM players")
        total, alive, dead, money, avg_age = cur.fetchone()
        cur.execute("SELECT city, COUNT(*) FROM players GROUP BY city ORDER BY COUNT(*) DESC LIMIT 5")
        cities = cur.fetchall()
        cur.close(); conn.close()
        city_text = "\n".join(f"• {c}: {n} نفر" for c,n in cities) or "—"
        return (f"📊 آمار بازی\n\n👥 بازیکنان: {total}\n🟢 زنده: {alive}\n💀 فوت‌شده: {dead}\n"
                f"💰 مجموع پول: {int(money):,} تومان\n🎂 میانگین سن بازی: {avg_age/10:.1f} سال\n\n🏙 شهرهای پرتعداد:\n{city_text}")
    except Exception as e:
        try: conn.close()
        except Exception: pass
        return f"❌ خطا در آمار: {e}"


def admin_players_text():
    conn = get_connection() if PSYCOPG2_AVAILABLE else None
    if not conn:
        return "❌ دیتابیس در دسترس نیست."
    try:
        cur = conn.cursor()
        cur.execute("SELECT numeric_id,name,gender,age_days,job,city,money,alive FROM players ORDER BY updated_at DESC LIMIT 15")
        rows = cur.fetchall(); cur.close(); conn.close()
        if not rows: return "👥 هنوز بازیکنی ثبت نشده."
        out=["👥 آخرین بازیکنان:"]
        for uid,name,gender,age,job,city,money,alive in rows:
            out.append(f"• {name} | ID: {uid or '—'} | {gender or '—'} | {age/10:.1f}س | {job or 'بیکار'} | {city or '—'} | {int(money or 0):,} | {'🟢' if alive else '💀'}")
        out.append("\n🔎 برای جزئیات: /admin player ID")
        return "\n".join(out)
    except Exception as e:
        try: conn.close()
        except Exception: pass
        return f"❌ خطا: {e}"


async def admin_cmd(update, context):
    uid = str(update.effective_user.id)
    if not is_admin(uid):
        await update.message.reply_text("⛔ دسترسی به پنل ادمین نداری.")
        return
    await update.message.reply_text("🛡️ پنل مدیریت بازی\n\nاز دکمه‌ها برای مدیریت و مشاهده وضعیت سرور استفاده کن.", reply_markup=admin_keyboard(is_super_admin(uid)))


async def admin_callback(update, context):
    query = update.callback_query
    uid = str(query.from_user.id)
    if not is_admin(uid):
        await query.answer("⛔ دسترسی ادمین نداری.", show_alert=True)
        return
    await query.answer()
    action = query.data.split(":",1)[1] if ":" in query.data else "panel"
    if action == "close":
        await query.edit_message_text("🛡️ پنل ادمین بسته شد.")
        return
    if action == "panel":
        await query.edit_message_text("🛡️ پنل مدیریت بازی\n\nیک گزینه را انتخاب کن:", reply_markup=admin_keyboard(is_super_admin(uid)))
        return
    if action == "stats":
        text = admin_stats_text()
    elif action == "players":
        text = admin_players_text()
    elif action == "leaderboard":
        rows = leaderboard_rows(15)
        text = "🏆 رتبه‌بندی\n\n" + ("\n".join(f"{i}. {r.get('name','—')} — {int(r.get('money') or 0):,} تومان — {r.get('city','—')}" for i,r in enumerate(rows,1)) or "هنوز بازیکنی نیست.")
    elif action == "admins":
        text = "🛡️ ادمین‌ها\n\n" + "\n".join(f"• {x}{' ⭐' if x == SUPER_ADMIN_ID else ''}" for x in list_admins())
    elif action == "economy":
        text = "🌍 برای مشاهده اقتصاد یک بازیکن: /admin player ID\n\nاقتصاد کل جهان از سیستم شبیه‌سازی روزانه به‌روزرسانی می‌شود."
    elif action == "addhelp":
        text = "➕ افزودن ادمین\n\nفقط سوپرادمین می‌تواند انجام دهد.\nدستور: /admin add ID"
    elif action == "removehelp":
        text = "➖ حذف ادمین\n\nفقط سوپرادمین می‌تواند انجام دهد.\nدستور: /admin remove ID"
    else:
        text = "❌ گزینه نامعتبر است."
    await query.edit_message_text(text, reply_markup=admin_keyboard(is_super_admin(uid)))

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


def after_action_keyboard(owner_id: str | None = None):
    """صفحه بعد از انجام عملیات؛ پنل بزرگ فقط با انتخاب کاربر باز می‌شود."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 بله، برو به پنل", callback_data=_owner_callback("life", owner_id, "panel")),
         InlineKeyboardButton("❌ نه، همین‌جا می‌مونم", callback_data=_owner_callback("life", owner_id, "stay"))],
    ])


def inventory_keyboard(owner_id: str | None, inventory: dict):
    """دکمه‌های واقعی کوله‌پشتی؛ هر آیتم مستقیماً قابل استفاده است."""
    rows = []
    for idx, (item, qty) in enumerate(inventory.items()):
        rows.append([InlineKeyboardButton(
            f"🧃 استفاده از {item} ×{qty}",
            callback_data=_owner_callback("life", owner_id, "usei", idx),
        )])
    rows.append([InlineKeyboardButton("🎮 پنل اصلی", callback_data=_owner_callback("life", owner_id, "panel"))])
    return InlineKeyboardMarkup(rows)


def group_panel_keyboard(owner_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 وضعیت من", callback_data=_owner_callback("life", owner_id, "status")),
         InlineKeyboardButton("👤 پروفایل", callback_data=_owner_callback("life", owner_id, "profile"))],
        [InlineKeyboardButton("🧭 حرکت", callback_data=_owner_callback("move", owner_id, "panel")),
         InlineKeyboardButton("🌍 زندگی", callback_data=_owner_callback("life", owner_id, "menu"))],
        [InlineKeyboardButton("🏠 خانه", callback_data=_owner_callback("life", owner_id, "home")),
         InlineKeyboardButton("👨‍👩‍👧 خانواده", callback_data=_owner_callback("life", owner_id, "family"))],
        [InlineKeyboardButton("🧠 زندگی هوشمند", callback_data=_owner_callback("life", owner_id, "smart"))],
        [InlineKeyboardButton("⚖️ پلیس و قانون", callback_data=_owner_callback("life", owner_id, "legal"))],
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

    # Dead player: if there is an adult child, continue the family line automatically.
    if player and not player.alive:
        children = [c for c in (getattr(player, "children", []) or []) if int(c.get("age_days",0)) >= 190 and c.get("alive",True)]
        if children:
            heir=max(children, key=lambda c:int(c.get("age_days",0)))
            legacy=max(0,int(player.money))+sum(int(p.get("value",0)) for p in ensure_advanced(player).get("properties",[]))//2
            player.name=heir.get("name", player.name); player.gender=heir.get("gender", player.gender); player.age_days=max(190,int(heir.get("age_days",190))); player.money=legacy
            player.alive=True; player.job="بیکار"; player.marital_status="مجرد"; player.children=[]; player.life_data["generation"]=int(player.life_data.get("generation",1))+1
            player.life_data["legacy"]={"from":heir.get("name"),"amount":legacy}
            if PSYCOPG2_AVAILABLE:
                try: save_player(player)
                except Exception: pass
            await update.message.reply_text(f"👨‍👩‍👧 نسل بعدی آغاز شد!\n\n👤 وارث: {player.name} ({player.gender})\n🎂 سن: {player.age_days//10} سال\n💰 میراث منتقل‌شده: {legacy:,} تومان\n\nزندگی نسل جدید ادامه دارد.", reply_markup=group_panel_keyboard(uid) if update.effective_chat.type != "private" else main_keyboard())
            return
        WAITING_CITY.add(uid)
        await update.message.reply_text(f"💀 زندگی قبلی {player.display_name} تمام شده است.\n\nفرزند بالغی برای ادامه نسل وجود ندارد؛ زندگی جدیدت را انتخاب کن.\n🏙 نام یکی از شهرهای ایران را بفرست.", reply_markup=ReplyKeyboardRemove() if update.effective_chat.type == "private" else None)
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



def law_keyboard(owner_id: str | None = None):
    """پنل مستقل قانون؛ همه دکمه‌ها به اکشن‌های واقعی متصل‌اند."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚔 وضعیت پلیس", callback_data=_owner_callback("life", owner_id, "police")),
         InlineKeyboardButton("⚖️ وضعیت قانون", callback_data=_owner_callback("life", owner_id, "legal"))],
        [InlineKeyboardButton("⚠️ جرائم", callback_data=_owner_callback("life", owner_id, "crime")),
         InlineKeyboardButton("💸 پرداخت جریمه", callback_data=_owner_callback("life", owner_id, "fine"))],
        [InlineKeyboardButton("📝 ثبت شکایت", callback_data=_owner_callback("life", owner_id, "complaint")),
         InlineKeyboardButton("👨‍⚖️ دادگاه", callback_data=_owner_callback("life", owner_id, "court"))],
        [InlineKeyboardButton("👨‍💼 وکیل", callback_data=_owner_callback("life", owner_id, "lawyer")),
         InlineKeyboardButton("🔒 زندان", callback_data=_owner_callback("life", owner_id, "jail"))],
        [InlineKeyboardButton("⬅️ بازگشت به زندگی", callback_data=_owner_callback("life", owner_id, "menu"))],
    ])


def life_keyboard(owner_id: str | None = None):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏫 تحصیل", callback_data=_owner_callback("life", owner_id, "education")), InlineKeyboardButton("📚 درس خواندن", callback_data=_owner_callback("life", owner_id, "study"))],
        [InlineKeyboardButton("🏦 بانک", callback_data=_owner_callback("life", owner_id, "bank")), InlineKeyboardButton("💰 واریز ۱ میلیون", callback_data=_owner_callback("life", owner_id, "deposit1")), InlineKeyboardButton("💵 برداشت ۱ میلیون", callback_data=_owner_callback("life", owner_id, "withdraw1"))],
        [InlineKeyboardButton("💳 وام", callback_data=_owner_callback("life", owner_id, "loan"))],
        [InlineKeyboardButton("🏠 مسکن", callback_data=_owner_callback("life", owner_id, "housing")), InlineKeyboardButton("🔑 اجاره", callback_data=_owner_callback("life", owner_id, "rent")), InlineKeyboardButton("🏡 خرید خانه", callback_data=_owner_callback("life", owner_id, "buyhouse"))],
        [InlineKeyboardButton("🚗 خودرو و موتور", callback_data=_owner_callback("life", owner_id, "vehicles"))],
        [InlineKeyboardButton("❤️ روابط", callback_data=_owner_callback("life", owner_id, "relationship")), InlineKeyboardButton("💞 آشنایی/قرار", callback_data=_owner_callback("life", owner_id, "meet")), InlineKeyboardButton("💍 ازدواج", callback_data=_owner_callback("life", owner_id, "marry"))],
        [InlineKeyboardButton("👶 فرزند", callback_data=_owner_callback("life", owner_id, "child")), InlineKeyboardButton("👨‍👩‍👧 فرزندان", callback_data=_owner_callback("life", owner_id, "children"))],
        [InlineKeyboardButton("🚔 پلیس", callback_data=_owner_callback("life", owner_id, "police")), InlineKeyboardButton("⚖️ قانون", callback_data=_owner_callback("life", owner_id, "legal"))],
        [InlineKeyboardButton("⚠️ جرم", callback_data=_owner_callback("life", owner_id, "crime")), InlineKeyboardButton("💸 پرداخت جریمه", callback_data=_owner_callback("life", owner_id, "fine"))],
        [InlineKeyboardButton("📝 شکایت", callback_data=_owner_callback("life", owner_id, "complaint")), InlineKeyboardButton("👨‍⚖️ دادگاه", callback_data=_owner_callback("life", owner_id, "court"))],
        [InlineKeyboardButton("👨‍💼 وکیل", callback_data=_owner_callback("life", owner_id, "lawyer")), InlineKeyboardButton("🔒 زندان", callback_data=_owner_callback("life", owner_id, "jail"))],
        [InlineKeyboardButton("🏥 بیمارستان", callback_data=_owner_callback("life", owner_id, "hospital")), InlineKeyboardButton("🏙 اقتصاد شهر", callback_data=_owner_callback("life", owner_id, "cityeconomy"))],
        [InlineKeyboardButton("🏢 کسب‌وکار", callback_data=_owner_callback("life", owner_id, "business")), InlineKeyboardButton("🚀 راه‌اندازی", callback_data=_owner_callback("life", owner_id, "startbiz")), InlineKeyboardButton("📊 فعالیت", callback_data=_owner_callback("life", owner_id, "runbiz"))],
        [InlineKeyboardButton("📈 بورس", callback_data=_owner_callback("life", owner_id, "stocks")), InlineKeyboardButton("🧾 مالیات", callback_data=_owner_callback("life", owner_id, "tax")), InlineKeyboardButton("💳 پرداخت مالیات", callback_data=_owner_callback("life", owner_id, "paytax"))],
        [InlineKeyboardButton("🧠 زندگی هوشمند", callback_data=_owner_callback("life", owner_id, "smart")), InlineKeyboardButton("📊 وضعیت عمیق", callback_data=_owner_callback("life", owner_id, "advanced"))],
        [InlineKeyboardButton("💡 پیشنهاد هوشمند", callback_data=_owner_callback("life", owner_id, "smartadvice")), InlineKeyboardButton("🎯 اهداف", callback_data=_owner_callback("life", owner_id, "smartgoals"))],
        [InlineKeyboardButton("🤖 تصمیم امروز", callback_data=_owner_callback("life", owner_id, "smartdecision")), InlineKeyboardButton("🤝 آشنایی", callback_data=_owner_callback("life", owner_id, "advmeet"))],
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
    markup = after_action_keyboard(owner_id)
    if key == "menu": text = "🌍 سیستم‌های زندگی\n\nیکی از بخش‌ها را انتخاب کن:"
    elif key == "home": text = home_text(player)
    elif key == "family": text = family_text(player)
    elif key == "panel":
        text = f"🎮 پنل شخصی {player.display_name}\n\n{player.status_text()}"
        markup = group_panel_keyboard(uid)
    elif key == "stay":
        text = "👌 باشه؛ همین‌جا می‌مونیم. هر وقت خواستی از دکمه «پنل» استفاده کن."
        markup = None
    elif key == "status": text = render_status_card(player, gt)
    elif key == "profile": text = render_profile(player)
    elif key == "inventory":
        inv = getattr(player, "inventory", {}) or {}
        text = "🎒 کوله‌پشتی خالیه." if not inv else "🎒 کوله‌پشتی\n\n" + "\n".join(f"• {k}: {v}" for k, v in inv.items())
        markup = inventory_keyboard(owner_id, inv)
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
    elif key == "smart": text = smart_status(player) + "\n\n" + smart_advice(player)
    elif key == "smartadvice": text = smart_advice(player)
    elif key == "smartdecision": text = smart_decision(player)
    elif key == "smartgoals": text = smart_goals(player)
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
    elif key == "children":
        children = getattr(player, "children", []) or []
        if not children:
            text = "👨‍👩‍👧 هنوز فرزندی نداری."
        else:
            lines = ["👨‍👩‍👧 فرزندان تو:"]
            for i, child in enumerate(children, 1):
                age = int(child.get("age_days", child.get("age", 0)) // 10)
                stage = child_stage(age)
                job = child_job_for_age(age)
                lines.append(f"{i}. {child.get('name','بدون نام')} ({child.get('gender','نامشخص')}) | {age} سال | {stage} | {job} | ❤️ {child.get('health', 100)}%")
            text = "\n".join(lines)
    elif key == "police":
        d = ensure_advanced(player)["legal"]
        text = ("🚔 پلیس و خدمات قانونی\n\n"
                f"📁 سابقه کیفری: {d.get('record',0)}\n"
                f"💸 جریمه‌های پرداخت‌نشده: {d.get('fines',0):,} تومان\n"
                f"🔒 زندان: {d.get('jail_days',0)} روز\n"
                f"📝 شکایت‌های ثبت‌شده: {d.get('complaints',0)}\n\n"
                "از این بخش می‌توانی وضعیت قانونی خودت را بررسی کنی، شکایت ثبت کنی یا برای پرونده وکیل بگیری.")
    elif key == "legal":
        d = ensure_advanced(player)["legal"]
        text = ("⚖️ مرکز قانون و دادگستری\n\n"
                f"📁 سابقه کیفری: {int(d.get('record', 0))}\n"
                f"💸 جریمه‌های پرداخت‌نشده: {int(d.get('fines', 0)):,} تومان\n"
                f"🔒 زندان: {int(d.get('jail_days', 0))} روز\n"
                f"📝 شکایت‌ها: {int(d.get('complaints', 0))}\n"
                f"💰 وثیقه: {int(d.get('bail', 0)):,} تومان\n\n"
                "گزینه موردنظر را از دکمه‌های پایین انتخاب کن.")
        markup = law_keyboard(owner_id)
    elif key == "complaint":
        d = ensure_advanced(player)["legal"]
        d["complaints"] = int(d.get("complaints", 0)) + 1
        text = "📝 شکایت ثبت شد و برای بررسی در سیستم قضایی قرار گرفت."
    elif key == "lawyer":
        d = ensure_advanced(player)["legal"]
        fee = 750_000
        if player.money < fee:
            text = f"👨‍💼 هزینه وکیل {fee:,} تومان است و پول کافی نداری."
        else:
            player.money -= fee
            d["lawyer_hired"] = True
            text = f"👨‍💼 وکیل استخدام شد. هزینه: {fee:,} تومان."
    elif key == "court":
        d = ensure_advanced(player)["legal"]
        if d.get("fines", 0) <= 0 and d.get("complaints", 0) <= 0 and d.get("record", 0) <= 0:
            text = "👨‍⚖️ پرونده فعالی نداری."
        elif d.get("record", 0) > 0 and random.random() < (0.45 if d.get("lawyer_hired") else 0.25):
            d["record"] = max(0, int(d["record"]) - 1)
            text = "👨‍⚖️ جلسه دادگاه برگزار شد و یک سابقه از پرونده‌ات کاهش یافت."
        else:
            text = "👨‍⚖️ جلسه دادگاه برگزار شد؛ پرونده همچنان تحت بررسی است."
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

    # عملیات انجام‌شده دیگر پنل بزرگ را خودکار باز نمی‌کند.
    action_keys = {
        "rest", "use", "usei", "study", "deposit1", "withdraw1", "loan",
        "rent", "buyhouse", "buyvehicle", "meet", "marry", "child",
        "complaint", "lawyer", "court", "crime", "fine", "jail",
        "startbiz", "runbiz", "buy", "sell", "paytax", "advmeet",
        "advwork", "advtrain", "advdeposit", "advloan", "advbiz",
    }
    if key in action_keys:
        markup = after_action_keyboard(owner_id)

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
        "📰 اخبار / روزنامه / مردم / رتبه‌بندی / کالاها\n"
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
    text = (update.message.text or "").strip().replace("\u200c", "").replace("\ufeff", "")

    # فقط فرمان‌های صریح فارسی/انگلیسی پردازش شوند؛ متن عادی نادیده گرفته شود.
    # هنگام انتخاب شهر، خود نام شهر نیز ورودی معتبر است.
    explicit_commands = {
        "شروع", "استارت", "کمک", "راهنما", "پنل", "وضعیت", "پروفایل",
        "حرکت", "🧭 حرکت", "زندگی", "خانه", "خونه", "خانواده", "استراحت",
        "شغل", "کار", "کار کن", "دعوا", "زمان", "مغازه", "مغازه‌ها",
        "کوله‌پشتی", "کیف", "بانک", "مسکن", "خانه و ملک", "خودرو", "ماشین",
        "وسایل نقلیه", "روابط", "ازدواج", "قانون", "پلیس", "بیمارستان",
        "کسب و کار", "کسب‌وکار", "بورس", "سهام", "اقتصاد شهر", "مالیات",
        "شمال", "جنوب", "شرق", "غرب", "شهرها", "فرزندان", "بچه‌ها", "سفر", "ادمین", "اخبار", "روزنامه", "اخبار اقتصادی", "مردم", "NPC", "ان پی سی", "رتبه‌بندی", "رتبه بندی", "لیدربورد", "کالاها", "بازار کالا",
        "تحصیل", "🏫 تحصیل", "درس خواندن", "بانک", "🏦 بانک", "مسکن", "🏠 مسکن", "خانه و ملک",
        "خودرو", "🚗 وسایل نقلیه", "وسایل نقلیه", "ماشین", "روابط", "❤️ روابط", "ازدواج",
        "قانون", "⚖️ قانون", "پلیس", "بیمارستان", "🏥 بیمارستان", "کسب و کار", "🏢 کسب‌وکار",
        "کسب‌وکار", "بورس", "📈 بورس", "سهام", "مالیات", "🧾 مالیات", "اقتصاد", "تورم", "بیکاری",
        "🏙 اقتصاد شهر", "🧠 زندگی هوشمند", "زندگی هوشمند", "هوش", "پیشنهاد هوشمند", "پیشنهاد", "تصمیم امروز", "تصمیم هوشمند", "اهداف", "اهداف زندگی", "🎒 کوله‌پشتی",
        "status", "profile", "move", "life", "shop", "inventory", "home",
        "family", "rest", "jobs", "work", "fight", "time", "help",
        "bank", "city", "north", "south", "east", "west"
    }
    is_dynamic_command = (
        text.startswith("انتخاب شغل ") or text.startswith("ادمین ")
        or text.startswith("شهر ") or text.startswith("city ") or text.startswith("سفر ")
    )
    if uid not in WAITING_CITY and text not in explicit_commands and not is_dynamic_command:
        return

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

    # بازیکن را پیش از فرمان‌های جهان زنده لود می‌کنیم؛ قبلاً این بخش قبل از get_or_load_player اجرا می‌شد.
    player = get_or_load_player(uid)
    if not player and text not in ["شروع", "استارت", "کمک", "راهنما"]:
        await update.message.reply_text("اول «شروع» یا /start را بزن.")
        return

    # مسیرهای قطعی پنل اصلی؛ قبل از سایر شاخه‌ها تا دکمه‌های Reply Keyboard همیشه پاسخ بگیرند.
    if text in ["خانه", "خونه", "home"]:
        await update.message.reply_text(home_text(player), reply_markup=life_keyboard(uid))
        return
    if text in ["خانواده", "family"]:
        await update.message.reply_text(family_text(player), reply_markup=life_keyboard(uid))
        return
    if text in ["زندگی", "life"]:
        await update.message.reply_text("🌱 سیستم زندگی\n\n" + home_text(player) + "\n\n" + family_text(player), reply_markup=life_keyboard(uid))
        return

    # فرمان‌های فارسی معادل دستورات Slash
    if text in ["اخبار", "روزنامه", "اخبار اقتصادی"]:
        d=ensure_advanced(player)
        await update.message.reply_text(news_text(d["world_economy"], player.city))
        return
    if text in ["مردم", "NPC", "ان پی سی"]:
        d=ensure_advanced(player)
        npcs=d.get("npcs") or {}
        if not npcs:
            from advanced_simulation import update_npc_population
            npcs=update_npc_population(player)
        lines=["👥 مردم اطراف تو:"]
        for n in list(npcs.values())[:8]:
            lines.append(f"• {n['name']} ({n['gender']}) | {n['age']} سال | {n.get('job','بیکار')} | هدف: {n.get('goal','—')}")
        await update.message.reply_text("\n".join(lines))
        return
    if text in ["رتبه‌بندی", "رتبه بندی", "لیدربورد"]:
        rows=leaderboard_rows(10)
        if not rows:
            await update.message.reply_text("🏆 هنوز اطلاعات کافی برای رتبه‌بندی وجود ندارد.")
            return
        lines=["🏆 رتبه‌بندی ثروت"]
        for i,r in enumerate(rows,1): lines.append(f"{i}. {r.get('name','بازیکن')} — {int(r.get('money') or 0):,} تومان — {r.get('city','—')}")
        await update.message.reply_text("\n".join(lines))
        return
    if text in ["کالاها", "بازار کالا"]:
        d=ensure_advanced(player); w=d["world_economy"]
        lines=["🏪 بازار کالا — عرضه و تقاضا"]
        for g,x in w["goods"].items(): lines.append(f"• {g}: عرضه {x['supply']:.0f} | تقاضا {x['demand']:.0f} | ضریب قیمت ×{x['price']:.2f}")
        await update.message.reply_text("\n".join(lines))
        return
    if text in ["شروع", "استارت"]:
        await start(update, context)
        return
    if text in ["پنل"]:
        await panel_cmd(update, context)
        return
    if text in ["راهنما"]:
        await help_cmd(update, context)
        return

    # ----- فرمان «سفر <نام شهر>» -----
    if text.startswith("سفر "):
        target = find_iran_city(text[5:].strip())
        if not target:
            await update.message.reply_text("❌ شهر مقصد پیدا نشد. مثال: سفر تهران")
            return
        if target == player.city if 'player' in locals() else False:
            await update.message.reply_text(f"📍 همین الان در {target} هستی.")
            return
        # بازیکن را قبل از سفر لود می‌کنیم
        travel_player = get_or_load_player(uid)
        if not travel_player:
            await update.message.reply_text("اول «شروع» یا /start را بزن.")
            return
        cost = hard_cost(random.randint(150_000, 1_500_000))
        if travel_player.money < cost:
            await update.message.reply_text(f"💸 پول کافی برای سفر نداری. هزینه تقریبی: {cost:,} تومان")
            return
        travel_player.money -= cost
        travel_player.city = target
        city_data = CITIES.get(target, {})
        travel_player.neighborhood = random.choice(city_data.get("neighborhoods", ["مرکز شهر"]))
        travel_player.location = "ترمینال / ایستگاه ورودی شهر"
        gt = GAME_TIMES.setdefault(uid, GameTime(start_hour=random.randint(7, 20)))
        gt.advance(random.randint(180, 480))
        age_msgs = advance_life_age(travel_player, gt.day)
        smart_msgs = daily_tick(travel_player, gt.day)
        reply = f"🚌 به {target} سفر کردی.\n💸 هزینه: {cost:,} تومان\n📍 {travel_player.neighborhood}\n💰 موجودی: {travel_player.money:,} تومان"
        if age_msgs: reply += "\n\n" + "\n".join(age_msgs)
        if smart_msgs: reply += "\n\n" + "\n".join(smart_msgs[-3:])
        if PSYCOPG2_AVAILABLE:
            try: save_player(travel_player)
            except Exception: pass
        await update.message.reply_text(reply)
        return

    # ----- فرمان «شهر <نام شهر>» -----
    if text.startswith("شهر "):
        city_name = text[5:].strip()
        city = find_iran_city(city_name)
        if not city:
            await update.message.reply_text("❌ این شهر پیدا نشد. مثال: شهر تهران")
            return
        player = get_or_load_player(uid)
        if not player:
            await update.message.reply_text("اول «شروع» یا /start را بزن.")
            return
        player.city = city
        player.neighborhood = random.choice(CITIES.get(city, {}).get("neighborhoods", ["مرکز شهر"]))
        player.location = "مرکز شهر"
        if PSYCOPG2_AVAILABLE:
            try: save_player(player)
            except Exception: pass
        await update.message.reply_text(f"🏙 شهر فعلی: {city}")
        return

    # player در ابتدای پردازش فرمان‌ها لود شده است.

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

    if uid not in GAME_TIMES:
        GAME_TIMES[uid] = GameTime(start_hour=random.randint(7, 20))
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
            smart_status(player) + "\n\n" + smart_advice(player),
            reply_markup=life_keyboard(uid)
        )
        return

    if text in ["پیشنهاد هوشمند", "پیشنهاد", "smart advice"]:
        await update.message.reply_text(smart_advice(player), reply_markup=life_keyboard(uid))
        return
    if text in ["تصمیم امروز", "تصمیم هوشمند"]:
        await update.message.reply_text(smart_decision(player), reply_markup=life_keyboard(uid))
        return
    if text in ["اهداف", "اهداف زندگی"]:
        await update.message.reply_text(smart_goals(player), reply_markup=life_keyboard(uid))
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

    if text in ["⚖️ قانون", "قانون", "قوانین", "دادگستری", "⚖️ قوانین"]:
        d = ensure_advanced(player)["legal"]
        reply = ("⚖️ مرکز قانون و دادگستری\n\n"
                 f"📁 سابقه کیفری: {int(d.get('record', 0))}\n"
                 f"💸 جریمه‌های پرداخت‌نشده: {int(d.get('fines', 0)):,} تومان\n"
                 f"🔒 زندان: {int(d.get('jail_days', 0))} روز\n"
                 f"📝 شکایت‌ها: {int(d.get('complaints', 0))}\n"
                 f"💰 وثیقه: {int(d.get('bail', 0)):,} تومان\n\n"
                 "گزینه موردنظر را از دکمه‌های پایین انتخاب کن.")
        await update.message.reply_text(reply, reply_markup=law_keyboard(uid))
        return

    if text in ["🚔 پلیس", "پلیس"]:
        d = ensure_advanced(player)["legal"]
        await update.message.reply_text(
            "🚔 پلیس و خدمات قانونی\n\n"
            f"📁 سابقه کیفری: {d.get('record',0)}\n"
            f"💸 جریمه‌های پرداخت‌نشده: {d.get('fines',0):,} تومان\n"
            f"🔒 زندان: {d.get('jail_days',0)} روز\n"
            f"📝 شکایت‌های ثبت‌شده: {d.get('complaints',0)}",
            reply_markup=law_keyboard(uid)
        )
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
        reply = "🎒 کوله‌پشتی خالیه." if not inv else (
            "🎒 کوله‌پشتی\n\n" + "\n".join(f"• {item}: {qty}" for item, qty in inv.items())
        )
        await update.message.reply_text(reply, reply_markup=inventory_keyboard(uid, inv))
        return

    if text in ["فرزندان", "بچه‌ها"]:
        children = getattr(player, "children", []) or []
        if not children:
            await update.message.reply_text("👨‍👩‍👧 هنوز فرزندی نداری.")
            return
        lines=["👨‍👩‍👧 فرزندان تو:"]
        for i,c in enumerate(children,1):
            age=int(c.get("age_days", c.get("age",0))//10)
            if age < 3: stage="نوزاد/خردسال"
            elif age < 7: stage="کودکستان"
            elif age < 13: stage="دانش‌آموز ابتدایی"
            elif age < 16: stage="دانش‌آموز متوسطه"
            elif age < 19: stage="دانش‌آموز دبیرستان"
            else: stage="بزرگسال"
            lines.append(f"{i}. {c.get('name','بدون نام')} ({c.get('gender','نامشخص')}) | {age} سال | {stage} | ❤️ {c.get('health',100)}%")
        await update.message.reply_text("\n".join(lines))
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
        # استراحت یک فرمان کامل است؛ ادامه‌ی زنجیره‌ی if/elif نباید آن را پاک کند.
        if PSYCOPG2_AVAILABLE and player:
            try:
                save_player(player)
            except Exception:
                pass
        await update.message.reply_text(reply)
        return
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
        econ = ensure_advanced(player)["economy"]
        reply = (f"💼 بازار کار شهر: {econ.get('unemployment', 0.08)*100:.1f}% بیکار | ظرفیت اشتغال: {econ.get('job_market', 50)}%\n\nمشاغل موجود:\n" + list_jobs() + "\n\nبرای انتخاب:\nانتخاب شغل نام_شغل")

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

    elif text in ["اقتصاد", "تورم", "بیکاری", "اقتصاد شهر"]:
        reply = city_economy_adv(player)

    elif text in ["زمان", "time"]:
        reply = f"🕐 {gt.formatted()}"

    elif text in ["کمک", "help"]:
        await help_cmd(update, context)
        return

    elif text.startswith("ادمین ") or text.startswith("admin "):
        if not is_admin(str(user.id)):
            return
        parts = text.split()
        sub = parts[1].lower() if len(parts) > 1 else "panel"
        if sub in ["player", "بازیکن"] and len(parts) >= 3:
            target = parts[2]
            data = load_player_by_numeric_id(target) if PSYCOPG2_AVAILABLE else None
            if not data:
                await update.message.reply_text("❌ بازیکن پیدا نشد.")
                return
            alive = data.get("alive", True)
            await update.message.reply_text(
                f"👤 بازیکن\nID: {data.get('numeric_id','—')}\nنام: {data.get('name','—')} ({data.get('gender','—')})\n"
                f"سن: {(data.get('age_days') or 0)/10:.1f} سال\nشغل: {data.get('job','بیکار')}\nشهر: {data.get('city','—')}\n"
                f"پول: {int(data.get('money') or 0):,} تومان\nوضعیت: {'زنده' if alive else 'فوت‌شده'}")
            return
        if sub == "add" and len(parts) >= 3 and is_super_admin(str(user.id)):
            ok = add_admin(parts[2])
            await update.message.reply_text("✅ ادمین اضافه شد." if ok else "ℹ️ این کاربر از قبل ادمین است.")
            return
        if sub == "remove" and len(parts) >= 3 and is_super_admin(str(user.id)):
            from admin import remove_admin
            ok = remove_admin(parts[2])
            await update.message.reply_text("✅ ادمین حذف شد." if ok else "❌ حذف انجام نشد.")
            return
        await admin_cmd(update, context)
        return

    elif text in ["ادمین"]:
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
        # متن نامعتبر عمداً نادیده گرفته می‌شود؛ ربات نباید به گفت‌وگوی عادی پاسخ دهد.
        return

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
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin:"))
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
