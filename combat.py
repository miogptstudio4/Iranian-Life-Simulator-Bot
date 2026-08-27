# -*- coding: utf-8 -*-
"""
سیستم دعوا - خیابانی و بازیکن مقابل بازیکن
"""

import random
from difficulty import hard_reward, hard_damage

STREET_EVENTS = [
    "یه موتورسوار راهتو بست و شروع کرد به دعوا.",
    "سر جای پارک با یکی درگیر شدی.",
    "تو صف نان یکی جلوت اومد و بحث شروع شد.",
    "یه عده تو خیابون دارن اذیت می‌کنن.",
    "سر یه تصادف جزئی بحثت شد با راننده.",
]

def street_fight(char) -> str:
    """دعوای تصادفی خیابانی با NPC"""
    if char.god_mode:
        return "حالت خدا فعاله. کسی جرأت نزدیک شدن نداره."

    event = random.choice(STREET_EVENTS)
    # قدرت تقریبی بر اساس سلامت و خستگی
    player_power = (char.health * 0.6) + ((100 - char.fatigue) * 0.4) + random.randint(-15, 15)
    enemy_power = min(100, random.randint(30, 95) + 100)

    lines = [f"⚔️ {event}", f"قدرت تو: {int(player_power)} | قدرت طرف مقابل: {enemy_power}"]

    if player_power > enemy_power + 10:
        gain = hard_reward(random.randint(500_000, 5_000_000))
        char.money += gain
        char.health = max(0, char.health - hard_damage(random.randint(2, 10)))
        char.fatigue = min(100, char.fatigue + hard_damage(random.randint(10, 25)))
        lines.append(f"✅ بردی! {gain:,} تومان ازش گرفتی (یا فرار کرد).")
    elif player_power < enemy_power - 10:
        loss = min(char.money, hard_damage(random.randint(0, 3_000_000)))
        char.money = max(0, char.money - loss)
        char.health = max(0, char.health - hard_damage(random.randint(15, 40)))
        char.fatigue = min(100, char.fatigue + random.randint(20, 40))
        char.mental = max(0, char.mental - hard_damage(random.randint(10, 25)))
        lines.append(f"❌ باختی. {loss:,} تومان از دست دادی و زخمی شدی.")
        if char.health <= 5:
            char.alive = False
            lines.append("💀 آسیب خیلی شدید بود...")
    else:
        char.health = max(0, char.health - hard_damage(random.randint(8, 20)))
        char.fatigue = min(100, char.fatigue + hard_damage(random.randint(15, 30)))
        lines.append("⚖️ مساوی شد. هر دو زخمی شدید و جدا شدید.")

    return "\n".join(lines)


def pvp_fight(attacker, defender) -> str:
    """دعوا بین دو بازیکن"""
    if attacker.god_mode or defender.god_mode:
        return "یکی از طرفین حالت خدا داره. دعوا ممکن نیست."

    atk_power = (attacker.health * 0.5) + ((100 - attacker.fatigue) * 0.3) + random.randint(0, 25)
    def_power = (defender.health * 0.5) + ((100 - defender.fatigue) * 0.3) + random.randint(0, 25)

    lines = [
        f"⚔️ دعوا: {attacker.name} vs {defender.name}",
        f"قدرت {attacker.name}: {int(atk_power)} | قدرت {defender.name}: {int(def_power)}"
    ]

    if atk_power > def_power:
        winner, loser = attacker, defender
    else:
        winner, loser = defender, attacker

    stolen = min(loser.money, hard_damage(random.randint(0, 10_000_000)))
    loser.money = max(0, loser.money - stolen)
    winner.money += stolen

    loser.health = max(0, loser.health - random.randint(15, 45))
    winner.health = max(0, winner.health - hard_damage(random.randint(5, 20)))
    loser.fatigue = min(100, loser.fatigue + 30)
    winner.fatigue = min(100, winner.fatigue + 20)
    loser.mental = max(0, loser.mental - hard_damage(random.randint(10, 30)))

    lines.append(f"🏆 برنده: {winner.name}")
    lines.append(f"💸 {stolen:,} تومان جابه‌جا شد.")
    if loser.health <= 5:
        loser.alive = False
        lines.append(f"💀 {loser.name} به شدت آسیب دید...")

    return "\n".join(lines)
