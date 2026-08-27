#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
شبیه‌ساز زندگی یک ایرانی
Iranian Life Simulator - Extreme Hardcore Edition
نسخه 1.1.0 - جهان‌باز + پنل ادمین + پلیر آنلاین
"""

import random
import time
import sys
import os


try:
    from locations import CITIES, CITY_LIST, FAMILY_TYPES
    from world import GUIDE, SHOPS
    from admin import (
    DEFAULT_ADMIN_PASSWORD, show_admin_help, generate_player_id, hash_password,
    SUPER_ADMIN_ID, is_admin, is_super_admin, add_admin, remove_admin, list_admins
)
    from map_system import DIRECTIONS, generate_location_name, get_random_description, PlayerCounter
    from player_panel import player_panel, show_profile
    from time_system import GameTime, time_effects, is_open
    from database import init_database, save_player, load_player, apply_loaded_data, PSYCOPG2_AVAILABLE
    from provinces import PROVINCES, PROVINCE_LIST, ALL_IRAN_CITIES
    from life_system import make_family, home_for_family, home_text, family_text, daily_life_event, advance_life_age
except ImportError as e:
    print("خطا در بارگذاری دیتا:", e)
    sys.exit(1)

MALE_NAMES = ["پارسا", "آرین", "کیان", "سپهر", "نیما", "آرش", "سامان", "بهراد", "عرفان", "میلاد", "رضا", "امیر", "حسین", "محمد", "علی", "رادین", "ایلیا", "مانی"]
FEMALE_NAMES = ["یسنا", "آوا", "هلیا", "نازنین", "سارا", "دنیا", "مهسا", "نگین", "پریا", "کیانا", "فاطمه", "زهرا", "مریم", "آیدا", "نیکا", "باران", "هستی"]

# ==================== شخصیت ====================
class Character:
    def __init__(self):
        self.gender = random.choice(["پسر", "دختر"])
        self.name = random.choice(MALE_NAMES if self.gender == "پسر" else FEMALE_NAMES)
        self.city = random.choice(CITY_LIST)
        self.family = random.choice(FAMILY_TYPES)
        self.birth_year = 1385
        self.age_days = 170  # قانون اصلی: شروع بازی از ۱۷ سالگی

        city_data = CITIES.get(self.city, {})
        neighborhoods = city_data.get("neighborhoods", ["مرکز شهر"])
        self.neighborhood = random.choice(neighborhoods)
        self.city_hardness = city_data.get("hardness_modifier", 1.3)

        if "کارگری" in self.family or "تک‌والد" in self.family:
            self.home = random.choice(["آپارتمان قدیمی اجاره‌ای", "سوئیت ۲۰ متری", "کپر و خانه حاشیه"])
        elif "مرفه" in self.family:
            self.home = random.choice(["آپارتمان نوساز", "خانه ویلایی بزرگ", "پنت‌هاوس"])
        else:
            self.home = random.choice(["آپارتمان قدیمی اجاره‌ای", "آپارتمان نوساز"])

        base = int(12 * self.city_hardness)
        self.hunger = random.randint(55 + base, 78 + base)
        self.thirst = random.randint(45 + base, 72 + base)
        self.fatigue = random.randint(25, 55)
        self.health = random.randint(55, 80)
        self.mental = random.randint(45, 75)

        self.alive = True
        self.money = 0
        self.god_mode = False
        self.location = "خانه"
        self.x, self.y = 0, 0   # مختصات روی نقشه محله
        self.player_id = generate_player_id()
        self.admin_password_hash = hash_password(DEFAULT_ADMIN_PASSWORD, self.player_id)
        self.display_name = self.name
        self.bio = "یک ایرانی در حال زنده ماندن..."
        self.marital_status = "مجرد"
        self.children = []
        self.family_members = make_family(self.gender, self.family)
        self.home_data = home_for_family(self.family)
        self.last_age_game_day = 0
        self.numeric_id = None  # آیدی عددی (مثل تلگرام) - توسط ادمین اصلی تنظیم می‌شود

    def status(self, players: PlayerCounter = None):
        print("\n" + "═" * 55)
        print(f"  نام      : {self.name} ({self.gender})")
        print(f"  شهر     : {self.city} | محله: {self.neighborhood}")
        print(f"  مکان    : {self.location}")
        print(f"  مختصات  : ({self.x}, {self.y})")
        print(f"  خانه    : {self.home}")
        print(f"  سن      : {max(10, self.age_days // 10)} سال | روزهای سپری‌شده این چرخه: {self.age_days % 10}/10")
        print(f"  پول     : {self.money:,} تومان")
        if self.god_mode:
            print("  ⚡ حالت خدا: فعال")
        print(f"  شناسه پلیر: {self.player_id}")
        if players:
            print(f"  {players.status_line()}")
        print("─" * 55)
        print(f"  گرسنگی  : {self.bar(self.hunger)} {min(100, self.hunger)}%")
        print(f"  تشنگی   : {self.bar(self.thirst)} {min(100, self.thirst)}%")
        print(f"  خستگی   : {self.bar(self.fatigue)} {min(100, self.fatigue)}%")
        print(f"  سلامت   : {self.bar(self.health)} {self.health}%")
        print(f"  روحیه   : {self.bar(self.mental)} {self.mental}%")
        print("═" * 55)

    def bar(self, value):
        value = max(0, min(100, value))
        filled = int(value / 5)
        return "█" * filled + "░" * (20 - filled)

    def decay(self):
        if self.god_mode:
            return
        hard = self.city_hardness
        self.hunger = min(120, self.hunger + int(random.randint(6, 14) * hard))
        self.thirst = min(120, self.thirst + int(random.randint(8, 16) * hard))
        self.fatigue = min(100, self.fatigue + int(random.randint(4, 10) * hard))
        if self.hunger > 85 or self.thirst > 85:
            self.health = max(0, self.health - random.randint(5, 12))
        if self.health <= 10:
            if random.random() < 0.35:
                self.alive = False


# ==================== پنل ادمین ====================
def admin_panel(char: Character):
    print("\n" + "█" * 50)
    print("█" + "          پنل ادمین".center(48) + "█")
    print("█" * 50)

    # تشخیص نوع دسترسی
    pid = str(char.numeric_id) if char.numeric_id else char.player_id
    super_user = is_super_admin(pid) or (char.numeric_id and str(char.numeric_id) == SUPER_ADMIN_ID)
    has_admin = is_admin(pid) or super_user

    print(f"شناسه داخلی: {char.player_id}")
    if char.numeric_id:
        print(f"آیدی عددی: {char.numeric_id}")
    print(f"سطح دسترسی: {'ادمین اصلی' if super_user else 'ادمین' if has_admin else 'عادی'}")
    print("⚠️  فقط شخصیت خودت قابل مدیریت است.\n")

    password = input("رمز ادمین: ").strip()
    if hash_password(password, char.player_id) != char.admin_password_hash:
        # ادمین اصلی با آیدی عددی می‌تواند بدون رمز هم وارد شود اگر آیدی‌اش ست شده
        if not (super_user and password == ""):
            print("❌ رمز اشتباه است.")
            return

    print("✅ ورود موفق.")
    show_admin_help(is_super=super_user)

    while True:
        cmd_line = input("\n[ادمین] > ").strip()
        if not cmd_line:
            continue
        parts = cmd_line.split()
        cmd = parts[0].lower()

        if cmd in ["exit", "خروج"]:
            print("خروج از پنل ادمین.")
            break
        elif cmd in ["help", "راهنما"]:
            show_admin_help(is_super=super_user)
        elif cmd in ["status", "وضعیت"]:
            char.status()
        elif cmd == "god":
            char.god_mode = not char.god_mode
            print(f"⚡ حالت خدا: {'فعال' if char.god_mode else 'غیرفعال'}")
        elif cmd == "heal":
            char.hunger = char.thirst = 5
            char.fatigue = 0
            char.health = char.mental = 100
            char.alive = True
            print("✅ بهبود کامل.")
        elif cmd == "kill":
            char.alive = False
            char.health = 0
            print("💀 شخصیت کشته شد.")
        elif cmd == "set" and len(parts) >= 3:
            try:
                setattr(char, parts[1], int(parts[2]))
                print(f"✅ {parts[1]} = {parts[2]}")
            except:
                print("❌ خطا در تنظیم")
        elif cmd == "money" and len(parts) >= 2:
            try:
                char.money = int(parts[1])
                print(f"✅ پول: {char.money:,}")
            except:
                print("❌ مقدار نامعتبر")
        elif cmd == "city" and len(parts) >= 2:
            city_name = " ".join(parts[1:])
            if city_name in CITY_LIST:
                char.city = city_name
                print(f"✅ شهر: {char.city}")
            else:
                print("❌ شهر پیدا نشد")
        elif cmd == "info":
            print(f"\nشناسه داخلی: {char.player_id}")
            print(f"آیدی عددی: {char.numeric_id or 'تنظیم نشده'}")
            print(f"ادمین اصلی: {SUPER_ADMIN_ID}")
            print(f"سطح شما: {'ادمین اصلی' if super_user else 'ادمین' if has_admin else 'عادی'}")
        elif cmd == "changepass" and len(parts) >= 2:
            char.admin_password_hash = hash_password(parts[1], char.player_id)
            print("✅ رمز تغییر کرد.")
        elif cmd == "setid" and len(parts) >= 2:
            # فقط برای تست: تنظیم آیدی عددی خودت
            char.numeric_id = parts[1]
            print(f"✅ آیدی عددی شما تنظیم شد: {char.numeric_id}")
            if str(char.numeric_id) == SUPER_ADMIN_ID:
                print("🔑 شما به عنوان ادمین اصلی شناخته شدید!")
        # ----- دستورات سوپر ادمین -----
        elif cmd == "addadmin" and len(parts) >= 2:
            if not super_user:
                print("❌ فقط ادمین اصلی می‌تواند ادمین اضافه کند.")
                continue
            target = parts[1]
            if add_admin(target):
                print(f"✅ کاربر {target} به لیست ادمین‌ها اضافه شد.")
            else:
                print(f"⚠️  {target} از قبل ادمین بوده.")
        elif cmd == "removeadmin" and len(parts) >= 2:
            if not super_user:
                print("❌ فقط ادمین اصلی می‌تواند ادمین حذف کند.")
                continue
            target = parts[1]
            if remove_admin(target):
                print(f"✅ ادمین {target} حذف شد.")
            else:
                print("❌ نمی‌توان ادمین اصلی را حذف کرد یا پیدا نشد.")
        elif cmd == "listadmins":
            if not super_user:
                print("❌ فقط ادمین اصلی.")
                continue
            admins = list_admins()
            print("\nلیست ادمین‌ها:")
            for a in admins:
                mark = " (اصلی)" if a == SUPER_ADMIN_ID else ""
                print(f"  • {a}{mark}")
        else:
            print("❌ دستور ناشناخته. help را بزن.")



# ==================== سیستم حرکت جهان‌باز ====================
def explore_city(char: Character, players: PlayerCounter, game_time: GameTime):
    print("\n" + "═" * 55)
    print("          حالت گشت‌وگذار در شهر (جهان‌باز)")
    print("═" * 55)
    print("دستورات حرکت:  شمال / جنوب / شرق / غرب")
    print("دستورات دیگر:  وضعیت | نگاه | زمان | پلیر | پروفایل | ادمین | خروج")
    print("─" * 55)

    while char.alive:
        print(f"\n📍 مکان فعلی: {char.location}")
        print(f"   مختصات: ({char.x}, {char.y})")
        print(f"   🕐 {game_time.formatted()}")
        print(f"   {players.status_line()}")
        # وضعیت باز/بسته بودن مکان فعلی
        status = game_time.shop_status(char.location)
        print(f"   وضعیت مکان: {status}")

        cmd = input("\n> ").strip().lower()

        if cmd in ["خروج", "exit", "quit"]:
            if PSYCOPG2_AVAILABLE:
                if save_player(char):
                    print("💾 اطلاعات ذخیره شد.")
            print("از حالت گشت‌وگذار خارج شدی.")
            break

        elif cmd in ["ادمین", "admin"]:
            admin_panel(char)
            if not char.alive:
                break

        elif cmd in ["خانه", "خونه", "home"]:
            print("\n" + home_text(char))
            print("\n" + daily_life_event(char))
        elif cmd in ["خانواده", "family"]:
            print("\n" + family_text(char))
        elif cmd in ["زندگی", "life"]:
            print("\n" + home_text(char))
            print("\n" + family_text(char))
        elif cmd in ["پلیر", "player"]:
            player_panel(char)

        elif cmd in ["پروفایل", "profile"]:
            show_profile(char)

        elif cmd in ["وضعیت", "status"]:
            char.status(players)

        elif cmd in ["نگاه", "look"]:
            print(f"\n{get_random_description()}")
            if random.random() < 0.3:
                print("چند نفر دیگه هم اینجا هستن (پلیرهای آنلاین).")

        elif cmd in ["زمان", "time"]:
            print(f"\n🕐 {game_time.formatted()}")
            print(f"دوره روز: {game_time.period}")
            continue

        elif cmd in DIRECTIONS:
            dx, dy = DIRECTIONS[cmd]
            char.x += dx
            char.y += dy

            # گذر زمان (۱۵ تا ۴۵ دقیقه)
            old_day = game_time.day
            game_time.advance(random.randint(15, 45))
            for age_msg in advance_life_age(char, game_time.day):
                print(age_msg)
            if game_time.day > old_day and random.random() < 0.35:
                print(daily_life_event(char))

            # تولید مکان جدید
            char.location = generate_location_name(char.city, char.neighborhood)
            print(f"\nرفتن به سمت {cmd}...")
            time.sleep(0.3)
            print(f"رسیدی به: {char.location}")
            print(get_random_description())

            # وضعیت باز/بسته
            status = game_time.shop_status(char.location)
            print(f"وضعیت: {status}")
            if "بسته" in status:
                print("این مکان الان بسته‌ست. باید وقت دیگری بیای.")

            # تأثیر زمان
            msgs = time_effects(char, game_time.hour)
            for m in msgs:
                print(f"⚠️ {m}")

            # هزینه حرکت
            char.fatigue = min(100, char.fatigue + random.randint(3, 8))
            char.thirst = min(120, char.thirst + random.randint(2, 6))
            char.decay()
            # ذخیره خودکار هر چند حرکت
            if random.random() < 0.25 and PSYCOPG2_AVAILABLE:
                save_player(char)

            if random.random() < 0.15:
                print("⚠️ یه اتفاق کوچیک افتاد...")
                if random.random() < 0.5:
                    char.mental = max(0, char.mental - random.randint(3, 8))
                    print("حالت روحی‌ت کمی بدتر شد.")
                else:
                    print("چیزی پیدا نکردی.")

            if not char.alive:
                print("\n💀 از شدت خستگی و گرسنگی از پا افتادی...")
                break

        else:
            print("دستور نامعتبر. از این‌ها استفاده کن: شمال / جنوب / شرق / غرب / وضعیت / نگاه / ادمین / خروج")


# ==================== توابع اصلی ====================
def intro():
    print("\n" + "█" * 62)
    print("█" + " " * 60 + "█")
    print("█" + "     شبیه‌ساز زندگی یک ایرانی".center(60) + "█")
    print("█" + "     Iranian Life Simulator - v1.1".center(60) + "█")
    print("█" + " " * 60 + "█")
    print("█" + "  جهان‌باز + پنل ادمین + پلیر آنلاین".center(60) + "█")
    print("█" + " " * 60 + "█")
    print("█" * 62)
    time.sleep(1)
    print("\nدر حال اتصال به سرور و تولید شخصیت...")
    time.sleep(1.2)


def main():
    intro()

    # اتصال به دیتابیس
    db_ok = False
    if PSYCOPG2_AVAILABLE:
        print("در حال اتصال به PostgreSQL...")
        db_ok = init_database()
    else:
        print("⚠️  دیتابیس در دسترس نیست (اطلاعات فقط در حافظه می‌ماند).")

    players = PlayerCounter()
    game_time = GameTime(start_hour=8)
    char = Character()

    # امکان ادامه بازی قبلی
    if db_ok:
        choice = input("\n۱. بازی جدید   ۲. ادامه بازی قبلی (با شناسه): ").strip()
        if choice in ["2", "۲"]:
            pid = input("شناسه پلیر (player_id) را وارد کن: ").strip()
            data = load_player(pid)
            if data:
                apply_loaded_data(char, data)
                print(f"✅ بازیکن {char.name} بارگذاری شد.")
            else:
                print("پیدا نشد. بازی جدید شروع می‌شود.")


    print(f"\nتو به دنیا اومدی... (۰ سالگی)")
    print(f"▸ نام: {char.name} | جنسیت: {char.gender}")
    print(f"▸ شهر: {char.city} | محله: {char.neighborhood}")
    print(f"▸ خانه: {char.home}")
    print(f"▸ خانواده: {char.family}")
    print("\n" + family_text(char))
    print("\nچند سال اول زندگی‌ات در کنار خانواده گذشت؛ کم‌کم شخصیتت شکل گرفت و محیط زندگی‌ات را شناختی.")
    print("\n🎂 حالا به ۱۰ سالگی رسیدی.")
    print("⏳ از این لحظه بازی اصلی شروع می‌شود؛ هر ۱۰ روز بازی = ۱ سال از عمر شخصیت.")
    char.age_days = 100
    char.last_age_game_day = game_time.day
    char.status(players)

    input("\nبرای شروع زندگی در ۱۰ سالگی Enter بزن...")

    print("\n" + "─" * 55)
    print("🎮 بازی اصلی شروع شد!")
    print("دستورهای مهم: خانه | خانواده | زندگی | زمان | وضعیت")
    print("─" * 55)

    while True:
        choice = input("\n> ").strip().lower()
        if choice in ["ادمین", "admin"]:
            admin_panel(char)
            continue
        if choice in ["پلیر", "player"]:
            player_panel(char)
            continue
        if choice in ["پروفایل", "profile"]:
            show_profile(char)
            continue
        if choice in ["1", "۱"]:
            char.hunger = min(120, char.hunger + 12)
            break
        elif choice in ["2", "۲"]:
            char.hunger = min(120, char.hunger + 5)
            break
        elif choice in ["3", "۳"]:
            char.hunger = min(120, char.hunger + random.randint(5, 15))
            break
        else:
            print("۱ یا ۲ یا ۳ یا ادمین")

    char.decay()
    char.status(players)

    if not char.alive:
        print("\n💀 مردی...")
        return

    print("\nحالا می‌تونی تو شهر دور بزنی.")
    print("دستورات: شمال / جنوب / شرق / غرب")
    input("Enter بزن تا وارد نقشه بشی...")

    explore_city(char, players, game_time)

    if PSYCOPG2_AVAILABLE:
        save_player(char)
        print("💾 اطلاعات نهایی ذخیره شد.")
    print("\n" + "─" * 55)
    print("نسخه ۱.۱ - ذخیره روی PostgreSQL اضافه شد")
    print("─" * 55)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nقطع ارتباط با سرور...")
