# -*- coding: utf-8 -*-
"""Smart life assistant: rule-based decisions and world-aware recommendations."""
from __future__ import annotations
from advanced_simulation import ensure_advanced, city_profile


def _goal(d):
    goals = d.get("goals") or []
    if goals:
        return goals[0]
    candidates=[]
    if not d.get("properties"): candidates.append("خانه‌دار شدن")
    if d.get("bank",{}).get("savings",0) < 10_000_000: candidates.append("ساختن پس‌انداز")
    if d.get("career",{}).get("job") in (None,"بیکار"): candidates.append("پیدا کردن شغل")
    if not candidates: candidates=["پیشرفت شغلی","بهبود سلامت و تعادل زندگی"]
    d["goals"] = candidates[:3]
    return d["goals"][0]


def smart_status(player):
    d=ensure_advanced(player); p=d["personality"]; n=d["needs"]; e=d["economy"]
    goals=d.get("goals") or [_goal(d)]
    return (
        "🧠 زندگی هوشمند\n\n"
        f"🎯 هدف اصلی: {goals[0]}\n"
        f"💼 شغل: {d['career'].get('job','بیکار')} | تجربه: {d['career'].get('experience',0)}\n"
        f"💰 پول: {player.money:,} تومان | پس‌انداز: {d['bank'].get('savings',0):,}\n"
        f"😴 خواب/نیاز به خواب: {n.get('sleep',0)}% | ⚡ انرژی: {n.get('energy',0)}% | 🧼 بهداشت: {n.get('hygiene',0)}% | 😰 استرس: {n.get('stress',0)}%\n"
        f"📈 تورم: {e.get('inflation',0)*100:.1f}% | 📉 بیکاری: {e.get('unemployment',0)*100:.1f}%\n"
        f"🧠 هوش {p.get('هوش',50)} | نظم {p.get('نظم',50)} | اراده {p.get('اراده',50)} | کاریزما {p.get('کاریزما',50)}\n"
        f"🏙 شهر: {player.city} | ضریب هزینه: ×{city_profile(player.city)['cost']:.2f}"
    )


def smart_advice(player):
    d=ensure_advanced(player); n=d["needs"]; e=d["economy"]; c=city_profile(player.city)
    advice=[]
    if n.get("energy",100) < 30 or n.get("sleep",0) > 75:
        advice.append("😴 اول استراحت کن؛ انرژی پایین بهره‌وری کارت را کم می‌کند.")
    if n.get("hygiene",100) < 35:
        advice.append("🧼 بهداشت پایین است؛ رسیدگی به خودت را در اولویت بگذار.")
    if n.get("stress",0) > 70:
        advice.append("🧠 استرس بالاست؛ کار سنگین را پشت‌سرهم انجام نده و یک فعالیت آرام‌تر انتخاب کن.")
    job=d["career"].get("job","بیکار")
    if job in (None,"بیکار"):
        if e.get("unemployment",0) > .18:
            advice.append("💼 بازار کار ضعیف است؛ مهارت‌آموزی یا شغل‌های ورودی را قبل از مشاغل تخصصی امتحان کن.")
        else:
            advice.append("💼 پیشنهاد: چند شغل را امتحان کن و هم‌زمان یک مهارت مرتبط را بالا ببر.")
    if e.get("inflation",0) > .25:
        advice.append("📈 تورم بالاست؛ نگه‌داشتن تمام دارایی به شکل نقدی ریسک کاهش قدرت خرید دارد.")
    if d["bank"].get("debt",0) > 0:
        advice.append("🏦 بدهی فعال داری؛ قبل از وام جدید، بدهی فعلی را مدیریت کن.")
    if player.money < 2_000_000:
        advice.append("💸 نقدینگی پایین است؛ فعلاً خریدهای غیرضروری را عقب بینداز.")
    if not advice:
        advice.append(f"🎯 وضعیت متعادل است؛ روی هدف «{_goal(d)}» تمرکز کن.")
    return "🧠 پیشنهاد هوشمند\n\n" + "\n".join(f"{i+1}. {x}" for i,x in enumerate(advice[:5]))


def smart_decision(player):
    d=ensure_advanced(player); n=d["needs"]; e=d["economy"]
    job=d["career"].get("job","بیکار")
    if n.get("energy",100) < 25 or n.get("sleep",0) > 82:
        return "😴 تصمیم پیشنهادی امروز: استراحت و بازیابی انرژی."
    if n.get("hygiene",100) < 30:
        return "🧼 تصمیم پیشنهادی امروز: اول رسیدگی به بهداشت، بعد کار."
    if job in (None,"بیکار"):
        if e.get("unemployment",0) > .20:
            return "📚 تصمیم پیشنهادی امروز: آموزش یک مهارت + جست‌وجوی شغل؛ بازار کار فعلاً سخت است."
        return "💼 تصمیم پیشنهادی امروز: روی پیدا کردن شغل ورودی تمرکز کن."
    if d["bank"].get("debt",0) > 0:
        return "🏦 تصمیم پیشنهادی امروز: درآمدت را برای مدیریت بدهی حفظ کن و فعلاً وام جدید نگیر."
    if n.get("stress",0) > 65:
        return "🧠 تصمیم پیشنهادی امروز: فشار کاری را کم کن و یک فعالیت آرام‌تر انتخاب کن."
    return f"💼 تصمیم پیشنهادی امروز: روی شغل «{job}» کار کن و بخشی از درآمد را برای هدف «{_goal(d)}» کنار بگذار."


def smart_goals(player):
    d=ensure_advanced(player); goals=d.get("goals") or []
    if not goals: _goal(d); goals=d["goals"]
    return "🎯 اهداف زندگی\n\n" + "\n".join(f"{i+1}. {g}" for i,g in enumerate(goals[:5]))
