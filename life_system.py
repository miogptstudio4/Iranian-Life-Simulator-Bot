# -*- coding: utf-8 -*-
"""سیستم خانه، خانواده و چرخه زندگی"""

import random

def make_family(gender, family_type):
    father_names = ["رضا","محمد","حسین","مجید","امیر","مهدی","علی","حامد"]
    mother_names = ["مریم","زهرا","فاطمه","سارا","نسرین","الهام","سمیه","نازنین"]
    father_jobs = ["کارمند","کارگر","کاسب","راننده","معلم","تعمیرکار","برنامه‌نویس"]
    mother_jobs = ["خانه‌دار","معلم","کارمند","پرستار","فروشنده","آرایشگر"]
    members = []
    if "تک‌والد" in family_type:
        rel = "پدر" if random.random() < .5 else "مادر"
        members.append({"relation": rel, "name": random.choice(father_names if rel=="پدر" else mother_names),
                        "age": random.randint(28, 48),
                        "job": random.choice(father_jobs if rel=="پدر" else mother_jobs),
                        "closeness": random.randint(60, 90)})
    else:
        members.append({"relation":"پدر","name":random.choice(father_names),"age":random.randint(30,52),
                        "job":random.choice(father_jobs),"closeness":random.randint(55,90)})
        members.append({"relation":"مادر","name":random.choice(mother_names),"age":random.randint(27,49),
                        "job":random.choice(mother_jobs),"closeness":random.randint(55,90)})
    siblings = random.randint(0, 3)
    for i in range(siblings):
        members.append({"relation":"خواهر" if random.random()<.5 else "برادر",
                        "name": random.choice(father_names+mother_names),
                        "age": random.randint(2, 17), "job":"دانش‌آموز",
                        "closeness":random.randint(45,85)})
    return members

def home_for_family(family_type):
    if "کارگری" in family_type or "تک‌والد" in family_type:
        kind=random.choice(["آپارتمان قدیمی اجاره‌ای","سوئیت کوچک","خانه حاشیه شهر"])
    elif "مرفه" in family_type:
        kind=random.choice(["آپارتمان نوساز","خانه ویلایی","پنت‌هاوس"])
    else:
        kind=random.choice(["آپارتمان قدیمی اجاره‌ای","آپارتمان نوساز","خانه معمولی"])
    return {"type":kind,"level":1,"rooms":random.randint(2,4),"cleanliness":random.randint(55,90),
            "comfort":random.randint(45,80),"rent":random.randint(3_000_000,18_000_000),
            "electricity":True,"water":True,"gas":True,"internet":random.random()<.75}

def home_text(char):
    h=getattr(char,"home_data",{})
    return (f"🏠 {getattr(char,'home','خانه')}\n"
            f"🛏 اتاق‌ها: {h.get('rooms','-')} | ⭐ سطح: {h.get('level',1)}\n"
            f"🧹 تمیزی: {h.get('cleanliness','-')}% | 🛋 راحتی: {h.get('comfort','-')}%\n"
            f"💡 برق: {'وصل' if h.get('electricity') else 'قطع'} | 💧 آب: {'وصل' if h.get('water') else 'قطع'} | 🔥 گاز: {'وصل' if h.get('gas') else 'قطع'}\n"
            f"🌐 اینترنت: {'وصل' if h.get('internet') else 'ندارد'}")

def family_text(char):
    members=getattr(char,"family_members",[])
    if not members: return "👨‍👩‍👧 خانواده‌ای ثبت نشده."
    lines=[f"👨‍👩‍👧 خانواده: {getattr(char,'family','نامشخص')}"]
    for m in members:
        lines.append(f"• {m['relation']}: {m['name']} | {m['age']} سال | {m['job']} | رابطه {m['closeness']}%")
    return "\n".join(lines)

def daily_life_event(char):
    events=[
        ("خانواده دور هم جمع شدند و شام خوردید.", 2),
        ("یکی از اعضای خانواده از روزش برایت تعریف کرد.", 1),
        ("خانه نیاز به مرتب‌کاری داشت.", -1),
        ("یک خرج غیرمنتظره برای خانه پیش آمد.", -2),
        ("حال و هوای خانه خوب بود و روحیه‌ات بهتر شد.", 3),
    ]
    text, mental_delta=random.choice(events)
    char.mental=max(0,min(100,char.mental+mental_delta))
    return "🏠 "+text

def advance_life_age(char, current_game_day):
    """هر ۱۰ روز بازی، یک سال به سن اضافه می‌شود."""
    last=getattr(char,"last_age_game_day",current_game_day)
    if current_game_day <= last:
        return []
    elapsed=current_game_day-last
    char.last_age_game_day=current_game_day
    char.age_days=getattr(char,"age_days",100)+elapsed
    old_years=max(10,(char.age_days-elapsed)//10)
    new_years=max(10,char.age_days//10)
    messages=[]
    if new_years>old_years:
        for y in range(old_years+1,new_years+1):
            messages.append(f"🎂 تولد {y} سالگی! یک سال از زندگی‌ات گذشت.")
            char.mental=max(0,char.mental-random.randint(0,3))
            char.health=max(1,char.health-random.randint(0,2))
    return messages
