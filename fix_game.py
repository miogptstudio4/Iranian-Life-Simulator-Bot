from pathlib import Path
p=Path('/mnt/data/work/bot.py')
s=p.read_text()
old='''        self.gender = random.choice(["پسر", "دختر"])
        self.name = name or random.choice(MALE_NAMES if self.gender == "پسر" else FEMALE_NAMES)
        if name and not any(name == n for n in MALE_NAMES + FEMALE_NAMES):
            self.name = name  # اسم تلگرام
        self.display_name = self.name
'''
new='''        self.gender = random.choice(["پسر", "دختر"])
        # نام شخصیت باید با جنسیت شخصیت هماهنگ باشد؛ نام تلگرام دیگر جای نام شخصیت را نمی‌گیرد.
        self.name = random.choice(MALE_NAMES if self.gender == "پسر" else FEMALE_NAMES)
        self.telegram_name = name or "بازیکن"
        self.display_name = self.name
'''
assert old in s
s=s.replace(old,new)
# add commands to explicit set
s=s.replace('''        "شمال", "جنوب", "شرق", "غرب", "ادمین",''','''        "شمال", "جنوب", "شرق", "غرب", "شهرها", "فرزندان", "بچه‌ها", "سفر", "ادمین",''')
s=s.replace('''        text.startswith("انتخاب شغل ") or text.startswith("ادمین ")
        or text.startswith("شهر ") or text.startswith("city ")''','''        text.startswith("انتخاب شغل ") or text.startswith("ادمین ")
        or text.startswith("شهر ") or text.startswith("city ") or text.startswith("سفر ")''')
# add child button
needle='''        [InlineKeyboardButton("👶 فرزند", callback_data=_owner_callback("life", owner_id, "child"))],'''
rep='''        [InlineKeyboardButton("👶 فرزند", callback_data=_owner_callback("life", owner_id, "child")), InlineKeyboardButton("👨‍👩‍👧 فرزندان", callback_data=_owner_callback("life", owner_id, "children"))],'''
assert needle in s
s=s.replace(needle,rep)
# add callback children
needle='''    elif key == "child": text = have_child(player)
'''
rep='''    elif key == "child": text = have_child(player)
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
            text = "\\n".join(lines)
'''
assert needle in s
s=s.replace(needle,rep)
# inject helper imports/functions after names
anchor='''FEMALE_NAMES = ["یسنا", "آوا", "هلیا", "نازنین", "سارا", "دنیا", "مهسا", "آیدا", "نیکا", "باران", "هستی", "کیمیا"]
'''
helper='''FEMALE_NAMES = ["یسنا", "آوا", "هلیا", "نازنین", "سارا", "دنیا", "مهسا", "آیدا", "نیکا", "باران", "هستی", "کیمیا"]


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
'''
assert anchor in s
s=s.replace(anchor,helper)
# advance children when age advances: replace age update block
old='''    char.age_days=getattr(char,"age_days",100)+elapsed
    old_years=max(10,(char.age_days-elapsed)//10)
    new_years=max(10,char.age_days//10)
    messages=[]
'''
new='''    char.age_days=getattr(char,"age_days",100)+elapsed
    old_years=max(10,(char.age_days-elapsed)//10)
    new_years=max(10,char.age_days//10)
    # سن فرزندان با همان تقویم بازی جلو می‌رود؛ ۲ ساله هرگز دانش‌آموز نمایش داده نمی‌شود.
    for child in getattr(char, "children", []) or []:
        child["age_days"] = int(child.get("age_days", child.get("age", 0))) + elapsed
        child["age"] = child["age_days"] // 10
    messages=[]
'''
# This is in life_system, not bot. handle separately
lp=Path('/mnt/data/work/life_system.py')
ls=lp.read_text()
assert old in ls
ls=ls.replace(old,new)
# replace make_family entirely with consistent version
start=ls.index('def make_family(')
end=ls.index('\ndef home_for_family', start)
family_func='''def make_family(gender, family_type):
    father_names = ["رضا","محمد","حسین","مجید","امیر","مهدی","علی","حامد"]
    mother_names = ["مریم","زهرا","فاطمه","سارا","نسرین","الهام","سمیه","نازنین"]
    father_jobs = ["کارمند","کارگر","کاسب","راننده","معلم","تعمیرکار","برنامه‌نویس"]
    mother_jobs = ["خانه‌دار","معلم","کارمند","پرستار","فروشنده","آرایشگر"]
    members = []
    # بازیکن در شروع ۱۷ ساله است؛ والدین باید سن منطقی نسبت به او داشته باشند.
    player_age = 17
    if "تک‌والد" in family_type:
        rel = "پدر" if random.random() < .5 else "مادر"
        age = random.randint(player_age + 18, player_age + 38)
        members.append({"relation": rel, "name": random.choice(father_names if rel=="پدر" else mother_names),
                        "age": age, "job": random.choice(father_jobs if rel=="پدر" else mother_jobs),
                        "closeness": random.randint(60, 90)})
    else:
        father_age = random.randint(player_age + 18, player_age + 38)
        mother_age = random.randint(max(player_age + 18, father_age - 8), father_age + 4)
        members.append({"relation":"پدر","name":random.choice(father_names),"age":father_age,
                        "job":random.choice(father_jobs),"closeness":random.randint(55,90)})
        members.append({"relation":"مادر","name":random.choice(mother_names),"age":mother_age,
                        "job":random.choice(mother_jobs),"closeness":random.randint(55,90)})
    siblings = random.randint(0, 3)
    for i in range(siblings):
        age = random.randint(2, 16)
        if age < 3:
            job = "نوزاد"
        elif age < 7:
            job = "کودکستان"
        else:
            job = "دانش‌آموز"
        is_female = random.random() < .5
        members.append({"relation":"خواهر" if is_female else "برادر",
                        "name": random.choice(["مریم","زهرا","فاطمه","سارا","نسرین","الهام","سمیه","نازنین","آوا","هانا","یسنا","نیکا","رها"] if is_female else ["رضا","محمد","حسین","مجید","امیر","مهدی","علی","حامد","سعید","نوید","کیان","پارسا"]),
                        "age": age, "job":job, "closeness":random.randint(45,85)})
    return members
'''
ls=ls[:start]+family_func+ls[end:]
lp.write_text(ls)
# patch life_features child and education age
lf=Path('/mnt/data/work/life_features.py')
fs=lf.read_text()
old='''def study(char, gt):
    d = ensure_data(char)["education"]
    if d["level"] == "لیسانس":'''
new='''def study(char, gt):
    d = ensure_data(char)["education"]
    age = age_years(char)
    if age < 17:
        return "🏫 هنوز در سن مدرسه هستی؛ بازی اصلی از ۱۷ سالگی شروع می‌شود."
    if d["level"] == "لیسانس":'''
assert old in fs
fs=fs.replace(old,new)
# replace have_child
start=fs.index('def have_child(char):')
end=len(fs)
# preserve anything after? likely function at end. inspect tail
oldfunc=fs[start:]
newfunc='''def have_child(char):
    if char.marital_status != "متأهل": return "❌ برای فرزندآوری باید متأهل باشی."
    if age_years(char) < 20: return "❌ برای داشتن فرزند کمی زوده؛ حداقل ۲۰ سال."
    if len(getattr(char, "children", [])) >= 5: return "👶 فعلاً تعداد فرزندانت به سقف سیستم رسیده."
    male = ["آراد", "نیما", "رادین", "کیان", "پارسا", "سام", "یونس"]
    female = ["آوا", "هانا", "یسنا", "نیکا", "باران", "هلیا", "رها"]
    gender = random.choice(["پسر", "دختر"])
    name = random.choice(male if gender == "پسر" else female)
    child = {"name": name, "gender": gender, "health": random.randint(75, 100), "age_days": 0, "age": 0, "alive": True}
    char.children.append(child)
    return f"👶 فرزند جدیدت به دنیا اومد: {child['name']} ({child['gender']})\\n🍼 سن: ۰ سال | وضعیت: نوزاد"
'''
fs=fs[:start]+newfunc
lf.write_text(fs)
# Add city travel command and children to explicit handled command branch before city
p.write_text(s)
