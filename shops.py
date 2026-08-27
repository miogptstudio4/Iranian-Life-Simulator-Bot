# -*- coding: utf-8 -*-
"""مغازه‌ها و خرید در شبیه‌ساز زندگی"""
import random
from difficulty import hard_cost

SHOPS = {
    "سوپرمارکت": {
        "icon": "🛒",
        "items": {
            "آب معدنی": (25000, {"thirst": -25}),
            "نوشابه": (45000, {"thirst": -8, "hunger": -3}),
            "نان": (30000, {"hunger": -12}),
            "ساندویچ": (180000, {"hunger": -35}),
            "شیر": (60000, {"hunger": -12, "health": 2}),
        },
    },
    "لباس‌فروشی": {
        "icon": "👕",
        "items": {
            "تی‌شرت": (450000, {"style": 2}),
            "شلوار": (700000, {"style": 3}),
            "کفش": (1200000, {"style": 4}),
            "کاپشن": (1800000, {"style": 4}),
        },
    },
    "لوازم دیجیتال": {
        "icon": "📱",
        "items": {
            "هندزفری": (650000, {"mental": 2}),
            "هدفون": (1800000, {"mental": 4}),
            "گوشی اقتصادی": (6500000, {"mental": 6}),
            "گوشی پرچمدار": (35000000, {"mental": 10}),
            "لپ‌تاپ": (55000000, {"mental": 8}),
        },
    },
    "داروخانه": {
        "icon": "💊",
        "items": {
            "ویتامین": (180000, {"health": 3}),
            "داروی عمومی": (250000, {"health": 5}),
            "کمک‌های اولیه": (450000, {"health": 8}),
        },
    },
    "کتابفروشی": {
        "icon": "📚",
        "items": {
            "کتاب داستان": (220000, {"mental": 3}),
            "کتاب آموزشی": (350000, {"mental": 5}),
            "کتاب تخصصی": (750000, {"mental": 8}),
        },
    },
    "لوازم خانگی": {
        "icon": "🏠",
        "items": {
            "چراغ مطالعه": (350000, {"comfort": 2}),
            "پنکه": (1800000, {"comfort": 4}),
            "تلویزیون": (12000000, {"comfort": 7}),
            "یخچال": (30000000, {"comfort": 10}),
        },
    },
}


def shop_list_text():
    lines = ["🏪 **مغازه‌های شهر**", ""]
    for name, data in SHOPS.items():
        lines.append(f"{data['icon']} {name}")
    lines.append("\nاز دکمه‌های مغازه برای ورود و خرید استفاده کن.")
    return "\n".join(lines)


def buy_item(player, shop_name, item_name):
    shop = SHOPS.get(shop_name)
    if not shop or item_name not in shop["items"]:
        return False, "❌ این کالا پیدا نشد."
    price, effects = shop["items"][item_name]
    # خرید بر اساس اقتصاد واقعی شهر/تورم
    try:
        from advanced_simulation import living_cost
        price = living_cost(player, price)
    except Exception:
        price = hard_cost(price)
    if player.money < price:
        return False, f"💸 پول کافی نداری. قیمت: {price:,} تومان"
    player.money -= price
    inventory = getattr(player, "inventory", {}) or {}
    inventory[item_name] = inventory.get(item_name, 0) + 1
    player.inventory = inventory
    return True, f"✅ {item_name} وارد کوله‌پشتی شد.\n💰 هزینه: {price:,} تومان\n🎒 تعداد: {inventory[item_name]}\nبرای استفاده، از «کوله‌پشتی» انتخابش کن."

def use_item(player, item_name):
    inventory = getattr(player, "inventory", {}) or {}
    if inventory.get(item_name, 0) <= 0:
        return False, "❌ این وسیله را نداری."
    effects = None
    for shop in SHOPS.values():
        if item_name in shop["items"]:
            effects = shop["items"][item_name][1]
            break
    if effects is None:
        return False, "❌ اثر این آیتم تعریف نشده."
    inventory[item_name] -= 1
    if inventory[item_name] <= 0:
        inventory.pop(item_name, None)
    player.inventory = inventory
    if "hunger" in effects:
        player.hunger = max(0, player.hunger + effects["hunger"])
    if "thirst" in effects:
        player.thirst = max(0, player.thirst + effects["thirst"])
    if "health" in effects:
        player.health = min(100, player.health + effects["health"])
    if "mental" in effects:
        player.mental = min(100, player.mental + effects["mental"])
    return True, f"🎒 «{item_name}» استفاده شد و اثرش اعمال شد."
