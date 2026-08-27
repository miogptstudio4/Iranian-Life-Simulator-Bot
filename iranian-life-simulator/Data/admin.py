# -*- coding: utf-8 -*-
"""
پنل ادمین - با ادمین اصلی و سیستم ارتقا
"""

import hashlib
import random
import string
import json
import os

# ==================== ادمین اصلی ====================
SUPER_ADMIN_ID = "6227792513"          # آیدی عددی ادمین اصلی
DEFAULT_ADMIN_PASSWORD = "darksouls999"

# فایل ذخیره لیست ادمین‌ها (برای پایداری)
ADMINS_FILE = os.path.join(os.path.dirname(__file__), "admins.json")

def load_admins():
    """بارگذاری لیست ادمین‌ها"""
    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            pass
    return set()

def save_admins(admins_set):
    """ذخیره لیست ادمین‌ها"""
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(admins_set), f, ensure_ascii=False, indent=2)

# لیست ادمین‌ها در حافظه
ADMINS = load_admins()
ADMINS.add(SUPER_ADMIN_ID)  # ادمین اصلی همیشه هست

def is_admin(player_id: str) -> bool:
    return str(player_id) in ADMINS or str(player_id) == SUPER_ADMIN_ID

def is_super_admin(player_id: str) -> bool:
    return str(player_id) == SUPER_ADMIN_ID

def add_admin(target_id: str) -> bool:
    """اضافه کردن ادمین جدید (فقط توسط سوپر ادمین)"""
    target_id = str(target_id)
    if target_id in ADMINS:
        return False
    ADMINS.add(target_id)
    save_admins(ADMINS)
    return True

def remove_admin(target_id: str) -> bool:
    """حذف ادمین (نمی‌توان ادمین اصلی را حذف کرد)"""
    target_id = str(target_id)
    if target_id == SUPER_ADMIN_ID:
        return False
    if target_id in ADMINS:
        ADMINS.discard(target_id)
        save_admins(ADMINS)
        return True
    return False

def list_admins():
    return sorted(list(ADMINS))

# ==================== شناسه و رمز ====================
def generate_player_id():
    chars = string.ascii_uppercase + string.digits
    return "PLR-" + "".join(random.choices(chars, k=8))

def hash_password(password: str, player_id: str) -> str:
    data = (password + player_id).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]

# ==================== دستورات ====================
ADMIN_COMMANDS = {
    "help": "نمایش دستورات",
    "status": "وضعیت شخصیت خودت",
    "set": "تغییر ویژگی خودت (set health 100)",
    "god": "حالت خدا",
    "heal": "بهبود کامل",
    "kill": "کشتن شخصیت خودت",
    "money": "تغییر پول",
    "city": "تغییر شهر",
    "age": "تغییر سن",
    "event": "رویداد اجباری",
    "info": "اطلاعات و شناسه",
    "reset": "ریست شخصیت",
    "changepass": "تغییر رمز",
    "exit": "خروج",
}

# دستورات مخصوص ادمین اصلی
SUPER_ADMIN_COMMANDS = {
    "addadmin": "ادمین کردن یک نفر (addadmin 123456789)",
    "removeadmin": "حذف ادمین (removeadmin 123456789)",
    "listadmins": "لیست تمام ادمین‌ها",
    "broadcast": "ارسال پیام به همه (فعلاً شبیه‌سازی)",
}

def show_admin_help(is_super=False):
    print("\n" + "═" * 55)
    print("          پنل ادمین (فقط شخصیت خودت)")
    print("═" * 55)
    for cmd, desc in ADMIN_COMMANDS.items():
        print(f"  {cmd:14} → {desc}")
    if is_super:
        print("\n── دستورات ادمین اصلی ──")
        for cmd, desc in SUPER_ADMIN_COMMANDS.items():
            print(f"  {cmd:14} → {desc}")
    print("═" * 55)
    print()
