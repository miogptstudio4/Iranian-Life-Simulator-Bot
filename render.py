# -*- coding: utf-8 -*-
"""
فایل مخصوص رندر - نمایش زیبای وضعیت، پروفایل و کارت بازیکن
برای استفاده در کنسول، تلگرام و خروجی HTML
"""

from datetime import datetime

def bar(value: int, width: int = 12) -> str:
    value = max(0, min(100, int(value)))
    filled = int(value / 100 * width)
    return "█" * filled + "░" * (width - filled)


def render_status_card(char, game_time=None, players_line: str = None) -> str:
    """کارت وضعیت فشرده و خوانا"""
    lines = [
        "╔══════════════════════════════════════╗",
        f"║  {getattr(char, 'display_name', char.name):^36}  ║",
        "╠══════════════════════════════════════╣",
        f"║ 🏙 {char.city:<20} {char.neighborhood[:12]:<12} ║",
        f"║ 💼 {getattr(char, 'job', 'بیکار'):<32} ║",
        f"║ 💰 {char.money:>20,} تومان          ║",
        "╟──────────────────────────────────────╢",
        f"║ ❤️  سلامت   {bar(char.health)} {char.health:3}%  ║",
        f"║ 🧠 روحیه    {bar(char.mental)} {char.mental:3}%  ║",
        f"║ 🍖 گرسنگی   {bar(char.hunger)} {min(100,char.hunger):3}%  ║",
        f"║ 💧 تشنگی    {bar(char.thirst)} {min(100,char.thirst):3}%  ║",
        f"║ 😴 خستگی    {bar(char.fatigue)} {char.fatigue:3}%  ║",
        "╟──────────────────────────────────────╢",
        f"║ 📍 {str(getattr(char, 'location', 'نامشخص'))[:34]:<34} ║",
    ]
    if game_time:
        lines.append(f"║ 🕐 {game_time.formatted()[:34]:<34} ║")
    if players_line:
        lines.append(f"║ {players_line[:36]:<36} ║")
    if getattr(char, "god_mode", False):
        lines.append("║ ⚡ حالت خدا: فعال                      ║")
    if getattr(char, "pregnant", False):
        days = getattr(char, "pregnancy_days", 0)
        lines.append(f"║ 🤰 باردار ({days}/270 روز)                ║")
    lines.append("╚══════════════════════════════════════╝")
    return "\n".join(lines)


def render_profile(char) -> str:
    """رندر کامل پروفایل"""
    children = getattr(char, "children", []) or []
    children_str = "ندارد" if not children else ", ".join(
        f"{c.get('name', '?')}({c.get('gender', '?')})" for c in children
    )
    return f"""
╔════════════════════════════════════════════╗
║              پروفایل بازیکن                 ║
╠════════════════════════════════════════════╣
║ شناسه داخلی : {getattr(char, 'player_id', '—'):<28} ║
║ آیدی عددی   : {str(getattr(char, 'numeric_id', '—')):<28} ║
║ نام         : {char.name:<28} ║
║ نام نمایشی  : {getattr(char, 'display_name', char.name):<28} ║
║ جنسیت       : {char.gender:<28} ║
║ سن (روز)    : {char.age_days:<28} ║
║ شهر         : {char.city:<28} ║
║ محله        : {char.neighborhood:<28} ║
║ خانه        : {str(getattr(char, 'home', '—'))[:28]:<28} ║
║ خانواده     : {char.family:<28} ║
║ شغل         : {getattr(char, 'job', 'بیکار'):<28} ║
║ تأهل        : {getattr(char, 'marital_status', 'مجرد'):<28} ║
║ پول         : {char.money:>20,} تومان     ║
║ فرزندان     : {children_str[:28]:<28} ║
║ بیو         : {str(getattr(char, 'bio', ''))[:28]:<28} ║
╚════════════════════════════════════════════╝
""".strip()


def render_html_card(char, game_time=None) -> str:
    """خروجی HTML ساده برای رندر وب یا ذخیره فایل"""
    def pct_bar(v, color="#4caf50"):
        v = max(0, min(100, int(v)))
        return f'<div style="background:#333;border-radius:4px;height:14px;width:120px;display:inline-block"><div style="background:{color};height:100%;width:{v}%;border-radius:4px"></div></div> {v}%'

    time_str = game_time.formatted() if game_time else "—"
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>وضعیت {getattr(char, 'display_name', char.name)}</title>
  <style>
    body {{ font-family: Tahoma, sans-serif; background: #1a1a2e; color: #eee; padding: 24px; }}
    .card {{ background: #16213e; border-radius: 12px; padding: 20px; max-width: 420px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
    h1 {{ margin: 0 0 8px; font-size: 1.4rem; }}
    .row {{ margin: 8px 0; }}
    .label {{ color: #aaa; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{getattr(char, 'display_name', char.name)}</h1>
    <div class="row"><span class="label">شهر</span> {char.city} — {char.neighborhood}</div>
    <div class="row"><span class="label">شغل</span> {getattr(char, 'job', 'بیکار')}</div>
    <div class="row"><span class="label">پول</span> {char.money:,} تومان</div>
    <div class="row"><span class="label">سلامت</span> {pct_bar(char.health, '#e74c3c')}</div>
    <div class="row"><span class="label">روحیه</span> {pct_bar(char.mental, '#9b59b6')}</div>
    <div class="row"><span class="label">گرسنگی</span> {pct_bar(char.hunger, '#f39c12')}</div>
    <div class="row"><span class="label">تشنگی</span> {pct_bar(char.thirst, '#3498db')}</div>
    <div class="row"><span class="label">خستگی</span> {pct_bar(char.fatigue, '#95a5a6')}</div>
    <div class="row"><span class="label">زمان</span> {time_str}</div>
    <div class="row"><span class="label">مکان</span> {getattr(char, 'location', '—')}</div>
  </div>
</body>
</html>"""


def save_html_card(char, path: str = "status_card.html", game_time=None) -> str:
    """ذخیره کارت HTML در فایل"""
    html = render_html_card(char, game_time)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def render_fight_result(text: str) -> str:
    """قاب برای نتیجه دعوا"""
    return f"⚔️ ─────────── دعوا ───────────\n{text}\n────────────────────────────"


def render_job_list(jobs_text: str) -> str:
    return f"💼 ─── مشاغل موجود ───\n{jobs_text}\n────────────────────"
