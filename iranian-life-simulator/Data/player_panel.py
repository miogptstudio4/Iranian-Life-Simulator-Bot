# -*- coding: utf-8 -*-
"""
پنل پلیر + سیستم پروفایل
"""

PLAYER_COMMANDS = {
    "پروفایل": "نمایش پروفایل کامل خودت",
    "وضعیت": "نمایش وضعیت بقا (گرسنگی، سلامت و...)",
    "موجودی": "نمایش پول و دارایی",
    "مکان": "نمایش شهر، محله و مختصات فعلی",
    "فرزندان": "لیست فرزندان (اگر داشته باشی)",
    "تنظیمات": "تغییر نام نمایشی و بیو",
    "کمک": "راهنمای پنل پلیر",
    "خروج": "خروج از پنل پلیر"
}

def show_player_help():
    print("\n" + "═" * 50)
    print("              پنل پلیر")
    print("═" * 50)
    for cmd, desc in PLAYER_COMMANDS.items():
        print(f"  {cmd:12} → {desc}")
    print("═" * 50)
    print()


def show_profile(char):
    print("\n" + "╔" + "═" * 50 + "╗")
    print("║" + "           پروفایل پلیر".center(50) + "║")
    print("╠" + "═" * 50 + "╣")
    print(f"║  شناسه        : {char.player_id:<33} ║")
    print(f"║  نام          : {char.name:<33} ║")
    print(f"║  نام نمایشی   : {getattr(char, 'display_name', char.name):<33} ║")
    print(f"║  جنسیت        : {char.gender:<33} ║")
    print(f"║  سن           : {char.age_days} روز{' '*27} ║")
    print(f"║  شهر          : {char.city:<33} ║")
    print(f"║  محله         : {char.neighborhood:<33} ║")
    print(f"║  خانه         : {char.home:<33} ║")
    print(f"║  خانواده      : {char.family:<33} ║")
    print(f"║  وضعیت تأهل   : {getattr(char, 'marital_status', 'مجرد'):<33} ║")
    print(f"║  پول          : {char.money:,} تومان{' '*(20-len(f'{char.money:,}'))} ║")
    bio = getattr(char, 'bio', 'بیو تنظیم نشده')
    print(f"║  بیو          : {bio[:33]:<33} ║")
    print("╚" + "═" * 50 + "╝")


def player_panel(char):
    print("\n" + "─" * 50)
    print("          ورود به پنل پلیر")
    print("─" * 50)
    show_player_help()

    while True:
        cmd = input("\n[پلیر] > ").strip().lower()

        if cmd in ["خروج", "exit", "quit"]:
            print("خروج از پنل پلیر.")
            break
        elif cmd in ["کمک", "help"]:
            show_player_help()
        elif cmd in ["پروفایل", "profile"]:
            show_profile(char)
        elif cmd in ["وضعیت", "status"]:
            char.status()
        elif cmd in ["موجودی", "money", "inventory"]:
            print(f"\n💰 پول فعلی: {char.money:,} تومان")
        elif cmd in ["مکان", "location"]:
            print(f"\n📍 شهر: {char.city}")
            print(f"   محله: {char.neighborhood}")
            print(f"   مکان: {char.location}")
            print(f"   مختصات: ({char.x}, {char.y})")
        elif cmd in ["فرزندان", "children"]:
            children = getattr(char, 'children', [])
            if not children:
                print("هنوز فرزندی نداری.")
            else:
                for i, c in enumerate(children, 1):
                    print(f"  {i}. {c.get('name')} ({c.get('gender')}) - سلامت: {c.get('health')}")
        elif cmd in ["تنظیمات", "settings"]:
            print("\n۱. تغییر نام نمایشی")
            print("۲. تغییر بیو")
            sub = input("انتخاب: ").strip()
            if sub == "1":
                new_name = input("نام نمایشی جدید: ").strip()
                if new_name:
                    char.display_name = new_name
                    print("✅ نام نمایشی تغییر کرد.")
            elif sub == "2":
                new_bio = input("بیو جدید (حداکثر ۶۰ کاراکتر): ").strip()[:60]
                char.bio = new_bio
                print("✅ بیو تغییر کرد.")
        else:
            print("دستور نامعتبر. «کمک» را بزن.")
