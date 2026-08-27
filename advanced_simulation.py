# -*- coding: utf-8 -*-
"""
Advanced life-simulation engine.
All long-term systems live in player.life_data so older saves remain compatible.
"""
from __future__ import annotations
import random
from datetime import datetime

CITY_PROFILES = {
    "تهران": {"cost":1.45,"salary":1.35,"jobs":1.30,"crime":1.25,"home":1.55,"transport":1.15},
    "کرج": {"cost":1.15,"salary":1.10,"jobs":1.10,"crime":1.10,"home":1.20,"transport":1.05},
    "مشهد": {"cost":1.00,"salary":0.95,"jobs":1.00,"crime":1.05,"home":0.95,"transport":1.00},
    "اصفهان": {"cost":1.08,"salary":1.00,"jobs":1.05,"crime":0.95,"home":1.05,"transport":1.00},
    "شیراز": {"cost":1.05,"salary":0.98,"jobs":1.00,"crime":0.92,"home":1.00,"transport":0.95},
    "تبریز": {"cost":1.02,"salary":1.00,"jobs":1.02,"crime":0.90,"home":0.98,"transport":0.95},
    "رشت": {"cost":1.03,"salary":0.95,"jobs":0.95,"crime":0.90,"home":1.00,"transport":0.95},
    "اهواز": {"cost":0.98,"salary":1.00,"jobs":1.00,"crime":1.12,"home":0.90,"transport":1.00},
}
DEFAULT_CITY = {"cost":1.0,"salary":0.95,"jobs":0.95,"crime":1.0,"home":0.9,"transport":1.0}

JOB_CATALOG = {
    "کارگر": (10_000_000, 18_000_000, 20, 0),
    "فروشنده": (11_000_000, 20_000_000, 14, 0),
    "پیک": (12_000_000, 24_000_000, 22, 0),
    "راننده": (15_000_000, 30_000_000, 18, 0),
    "مکانیک": (18_000_000, 38_000_000, 16, 1),
    "آشپز": (17_000_000, 35_000_000, 18, 1),
    "معلم": (20_000_000, 42_000_000, 12, 2),
    "حسابدار": (24_000_000, 50_000_000, 11, 2),
    "برنامه‌نویس": (30_000_000, 80_000_000, 12, 3),
    "مهندس": (35_000_000, 85_000_000, 13, 3),
    "پزشک": (55_000_000, 160_000_000, 20, 5),
    "وکیل": (45_000_000, 140_000_000, 14, 4),
    "مدیر": (50_000_000, 180_000_000, 12, 4),
}
SKILLS = ["ارتباطات","فنی","برنامه‌نویسی","مدیریت","حسابداری","زبان","رانندگی","پزشکی","حقوق","هنر"]
HABITS = ["ورزش","مطالعه","خواب منظم","پس‌انداز","سیگار","ولخرجی","شب‌بیداری"]  # فقط به‌عنوان ویژگی بازی

def _default():
    return {
        "version": 2,
        "personality": {"شجاعت":50,"هوش":50,"کاریزما":50,"نظم":50,"خوش‌شانسی":50,"اراده":50},
        "needs": {"sleep":30,"energy":75,"hygiene":70,"stress":20},
        "health_state": {"conditions":[],"injuries":[],"temporary_effects":[]},
        "habits": [],
        "reputation": 0,
        "life_history": [],
        "skills": {k: 0 for k in SKILLS},
        "education": {"level":"دیپلم","field":None,"gpa":0.0,"credits":0,"scholarship":False,"studying":False},
        "career": {"job":"بیکار","level":1,"experience":0,"contract_days":0,"overtime":0,"part_time":[]},
        "economy": {"inflation":0.18,"growth":0.01,"unemployment":0.08,"currency_value":1.0,"shock":None},
        "bank": {"checking":0,"savings":0,"debt":0,"loan_rate":0.24,"credit":500,"missed":0},
        "properties": [],
        "vehicles": [],
        "relationships": [],
        "npcs": {},
        "businesses": [],
        "portfolio": {},
        "legal": {"record":0,"fines":0,"jail_days":0,"lawsuits":0,"bail":0},
        "achievements": [],
        "records": {"highest_money":0,"highest_reputation":0,"longest_job_days":0,"business_profit":0},
        "last_tick_day": 0,
        "event_cooldown": 0,
        "city_stats": {},
    }

def ensure_advanced(char):
    d = getattr(char, "life_data", None)
    if not isinstance(d, dict): d = {}
    defaults = _default()
    for k,v in defaults.items():
        if k not in d: d[k] = v
    for k,v in defaults["personality"].items(): d["personality"].setdefault(k,v)
    for k,v in defaults["needs"].items(): d["needs"].setdefault(k,v)
    for k in SKILLS: d["skills"].setdefault(k,0)
    d["career"].setdefault("job", getattr(char,"job","بیکار"))
    d["economy"].setdefault("inflation",0.18)
    d["bank"].setdefault("credit",500)
    d["legal"].setdefault("record",0)
    char.life_data = d
    return d

def city_profile(city):
    return CITY_PROFILES.get(city, DEFAULT_CITY).copy()

def price_factor(char):
    d=ensure_advanced(char)
    c=city_profile(getattr(char,"city",""))
    return c["cost"] * (1 + max(-0.05, d["economy"]["inflation"]))

def living_cost(char, base):
    return max(1, int(base * price_factor(char)))

def job_salary(char, job_name=None):
    d=ensure_advanced(char); job_name=job_name or d["career"]["job"]
    if job_name not in JOB_CATALOG: return 0
    lo,hi,_,required_skill=JOB_CATALOG[job_name]
    c=city_profile(getattr(char,"city",""))
    skill_bonus=min(1.8, 1 + (sum(d["skills"].values())/len(SKILLS))/100)
    exp_bonus=1 + min(.6,d["career"]["experience"]/3650)
    return random.randint(lo,hi) * c["salary"] * skill_bonus * exp_bonus * (1+d["economy"]["inflation"])

def work_day(char, overtime=False, part_time=False):
    d=ensure_advanced(char)
    job=d["career"]["job"]
    if job not in JOB_CATALOG: return "💼 شغلی برای انجام دادن نداری."
    lo,hi,energy,req=JOB_CATALOG[job]
    skill = d["skills"].get("مدیریت",0) if req>=4 else max(d["skills"].values())
    if skill < req*10:
        return f"⚠️ مهارت کافی برای عملکرد خوب در «{job}» نداری."
    income=int(job_salary(char,job))
    if part_time: income//=2
    if overtime: income=int(income*1.25); d["career"]["overtime"] += 1
    char.money += income
    d["career"]["experience"] += 1
    d["needs"]["energy"]=max(0,d["needs"]["energy"]-energy)
    d["needs"]["sleep"]=min(100,d["needs"]["sleep"]+random.randint(3,8))
    d["needs"]["stress"]=min(100,d["needs"]["stress"]+random.randint(1,5))
    d["records"]["highest_money"]=max(d["records"]["highest_money"],char.money)
    return f"💼 یک روز در «{job}» کار کردی و {income:,} تومان گرفتی."

def train_skill(char, skill, hours=2):
    d=ensure_advanced(char)
    if skill not in d["skills"]: return "❌ مهارت ناشناخته است."
    cost= living_cost(char, 150_000*hours)
    if char.money < cost: return f"💸 هزینه آموزش {cost:,} تومان است."
    char.money -= cost
    gain=random.randint(2,5)*hours//2 + d["personality"]["هوش"]//40
    d["skills"][skill]=min(100,d["skills"][skill]+gain)
    d["needs"]["energy"]=max(0,d["needs"]["energy"]-hours*4)
    return f"🎓 مهارت «{skill}» +{gain}. سطح: {d['skills'][skill]}/100"

def bank_deposit_adv(char, amount, savings=False):
    d=ensure_advanced(char); amount=int(amount)
    if amount<=0 or char.money<amount: return "💸 مبلغ نامعتبر یا موجودی ناکافی."
    char.money-=amount
    key="savings" if savings else "checking"
    d["bank"][key]+=amount
    return f"🏦 {amount:,} تومان به {'پس‌انداز' if savings else 'حساب جاری'} منتقل شد."

def bank_withdraw_adv(char, amount, savings=False):
    d=ensure_advanced(char); amount=int(amount); key="savings" if savings else "checking"
    if amount<=0 or d["bank"][key]<amount: return "💸 موجودی حساب کافی نیست."
    d["bank"][key]-=amount; char.money+=amount
    return f"🏦 {amount:,} تومان برداشت شد."

def take_loan_adv(char, amount):
    d=ensure_advanced(char); amount=int(amount)
    if amount<=0 or d["bank"]["debt"]>0: return "❌ تا بدهی قبلی تسویه نشده وام جدید نمی‌گیری."
    credit=d["bank"]["credit"]
    limit=max(1_000_000, credit*150_000)
    if amount>limit: return f"❌ سقف وام فعلی: {limit:,} تومان."
    d["bank"]["debt"]+=amount
    d["bank"]["credit"]=max(0,credit-40)
    char.money+=amount
    return f"💳 وام {amount:,} تومان ثبت شد. سود سالانه حدود {int(d['bank']['loan_rate']*100)}٪."

def city_economy_adv(char):
    d=ensure_advanced(char); c=city_profile(char.city)
    return (f"🏙 اقتصاد {char.city}\n"
            f"💸 هزینه زندگی: ×{c['cost']:.2f}\n💼 حقوق: ×{c['salary']:.2f}\n"
            f"📈 تورم جهانی بازی: {d['economy']['inflation']*100:.1f}%\n"
            f"📉 بیکاری: {d['economy']['unemployment']*100:.1f}%\n"
            f"💱 ارزش پول: {d['economy']['currency_value']:.3f}\n"
            f"🚨 ریسک جرم: ×{c['crime']:.2f}")

def buy_property_adv(char, name, base_price, rent=0):
    d=ensure_advanced(char); price=living_cost(char,base_price)
    if char.money<price: return f"🏠 قیمت {price:,} تومان است و پول کافی نداری."
    char.money-=price
    prop={"name":name,"value":price,"rent":rent,"level":1,"occupied":True,"maintenance":max(50_000,price//400)}
    d["properties"].append(prop)
    return f"🏠 «{name}» خریداری شد."

def buy_vehicle_adv(char, name, price, fuel=0.0):
    d=ensure_advanced(char); price=living_cost(char,price)
    if char.money<price: return f"🚗 قیمت {price:,} تومان است."
    char.money-=price
    d["vehicles"].append({"name":name,"value":price,"condition":100,"fuel":100.0,"insurance":True})
    return f"🚗 {name} خریداری شد."

def meet_npc(char):
    d=ensure_advanced(char)
    pool=[("سینا",24,"فروشنده",62),("نگار",22,"دانشجو",58),("رضا",31,"مهندس",55),
          ("مهسا",27,"معلم",66),("کیان",35,"کاسب",52),("سارا",29,"پزشک",60)]
    name,age,job,base=random.choice(pool)
    if name in d["npcs"]:
        npc=d["npcs"][name]
        npc["memory"].append("دیدار دوباره")
    else:
        npc={"name":name,"age":age,"job":job,"opinion":base,
             "memory":["آشنایی اولیه"],"goal":random.choice(["پیشرفت شغلی","خرید خانه","سفر","کمک به خانواده"])}
        d["npcs"][name]=npc
    d["relationships"].append({"npc":name,"type":"آشنا","score":base,"last_event":"آشنایی"})
    return f"🤝 با «{name}» آشنا شدی؛ {age} ساله، {job}. نظر اولیه درباره تو: {base}/100."

def relationship_action(char, npc_name, action):
    d=ensure_advanced(char); npc=d["npcs"].get(npc_name)
    if not npc: return "❌ این NPC را نمی‌شناسی."
    delta={"گفتگو":3,"کمک":7,"دعوا":-20,"آشتی":12}.get(action,1)
    npc["opinion"]=max(-100,min(100,npc["opinion"]+delta))
    npc["memory"].append(action)
    return f"❤️ رابطه با {npc_name}: {npc['opinion']}/100."

def commit_crime_adv(char, crime="دزدی"):
    d=ensure_advanced(char); c=city_profile(char.city)
    risk=min(.95,.18*c["crime"] + d["legal"]["record"]*.03)
    if random.random()<risk:
        d["legal"]["record"]+=1
        d["legal"]["fines"]+=living_cost(char,random.randint(2_000_000,12_000_000))
        d["reputation"]-=random.randint(3,12)
        d["legal"]["jail_days"]+=random.randint(1,7)
        return f"⚖️ جرم «{crime}» لو رفت. سابقه کیفری و مجازات گرفتی."
    gain=living_cost(char,random.randint(1_000_000,8_000_000))
    char.money+=gain
    d["reputation"]-=random.randint(1,5)
    return f"⚠️ جرم «{crime}» انجام شد و {gain:,} تومان به دست آوردی؛ اما ریسک همچنان باقی است."

def start_business_adv(char, kind="فروشگاه"):
    d=ensure_advanced(char)
    if any(b["active"] for b in d["businesses"]): return "🏢 در حال حاضر یک کسب‌وکار فعال داری."
    capital=living_cost(char,30_000_000)
    if char.money<capital: return f"🏢 سرمایه شروع حداقل {capital:,} تومان است."
    char.money-=capital
    b={"name":kind,"active":True,"capital":capital,"employees":0,"revenue":0,"expenses":0,
       "reputation":50,"branches":1,"days":0}
    d["businesses"].append(b)
    return f"🏢 کسب‌وکار «{kind}» با سرمایه {capital:,} تومان راه افتاد."

def run_business_adv(char):
    d=ensure_advanced(char)
    if not d["businesses"]: return "🏢 هنوز کسب‌وکاری نداری."
    b=d["businesses"][-1]
    if not b["active"]: return "📉 کسب‌وکار ورشکسته است."
    rev=int(random.randint(2_000_000,12_000_000)*city_profile(char.city)["jobs"]*(1+d["economy"]["growth"]))
    exp=int(rev*random.uniform(.45,.9))
    profit=rev-exp
    b["revenue"]+=rev; b["expenses"]+=exp; b["capital"]+=profit; b["days"]+=1
    d["records"]["business_profit"]+=profit
    if b["capital"]<=0:
        b["active"]=False
        return "💥 کسب‌وکارت ورشکست شد."
    return f"🏢 درآمد امروز: {rev:,} | هزینه: {exp:,} | سود: {profit:,} تومان."

def stock_trade_adv(char, symbol, buy=True, amount=1):
    d=ensure_advanced(char)
    prices={"فولاد":2_500_000,"بانک":1_800_000,"فناوری":4_500_000,"خودرو":2_200_000,"دارویی":3_200_000}
    if symbol not in prices: return "❌ سهم وجود ندارد."
    old=d["portfolio"].get(symbol,{"qty":0,"avg":0})
    if buy:
        cost=living_cost(char,prices[symbol])*amount
        if char.money<cost: return "📈 سرمایه کافی نیست."
        total=old["avg"]*old["qty"]+cost; qty=old["qty"]+amount
        old={"qty":qty,"avg":total/qty}
        d["portfolio"][symbol]=old; char.money-=cost
        return f"📈 {amount} سهم «{symbol}» خریدی."
    if old["qty"]<amount: return "📉 تعداد سهم کافی نیست."
    value=living_cost(char,prices[symbol])*amount*random.uniform(.85,1.20)
    old["qty"]-=amount; d["portfolio"][symbol]=old; char.money+=int(value)
    return f"📉 {amount} سهم «{symbol}» فروختی و {int(value):,} تومان گرفتی."

def advance_economy(char):
    d=ensure_advanced(char)
    econ=d["economy"]
    shock=random.random()
    if shock<.03:
        econ["inflation"]=min(.80,econ["inflation"]+random.uniform(.03,.12)); econ["shock"]="شوک تورمی"
    elif shock<.05:
        econ["growth"]-=random.uniform(.03,.08); econ["unemployment"]=min(.35,econ["unemployment"]+.04); econ["shock"]="رکود"
    elif shock<.08:
        econ["growth"]+=random.uniform(.02,.06); econ["unemployment"]=max(.02,econ["unemployment"]-.02); econ["shock"]="رونق"
    else:
        econ["inflation"]=max(.02,econ["inflation"]+random.uniform(-.005,.008))
        econ["growth"]=max(-.10,min(.12,econ["growth"]+random.uniform(-.01,.01)))
        econ["unemployment"]=max(.02,min(.35,econ["unemployment"]+random.uniform(-.008,.008)))
        econ["shock"]=None
    econ["currency_value"]=max(.1,econ["currency_value"]/(1+max(0,econ["inflation"]-0.15)*.08))

def random_event(char):
    d=ensure_advanced(char)
    events=[
        ("💰 در خیابان مقداری پول پیدا کردی.", lambda: setattr(char,"money",char.money+living_cost(char,random.randint(100_000,1_500_000)))),
        ("📱 یک پیشنهاد شغلی غیرمنتظره دریافت کردی.", lambda: d["career"].update({"job":"فروشنده","level":max(1,d["career"]["level"])})),
        ("🤒 یک بیماری موقت گرفتی و چند روز انرژی‌ات پایین می‌آید.", lambda: d["health_state"]["conditions"].append({"name":"بیماری موقت","days":random.randint(2,5)})),
        ("🚗 حادثه کوچکی رخ داد و خودرو آسیب دید.", lambda: [v.update({"condition":max(0,v["condition"]-random.randint(5,20))}) for v in d["vehicles"][:1]]),
        ("🤝 یک آشنایی اتفاقی در شهر شکل گرفت.", lambda: None),
        ("🎁 یک جایزه کوچک بردی.", lambda: setattr(char,"money",char.money+living_cost(char,random.randint(200_000,2_000_000)))),
    ]
    msg,fn=random.choice(events); fn()
    if "آشنایی" in msg: msg += "\n"+meet_npc(char)
    d["life_history"].append({"day":d["last_tick_day"],"event":msg})
    return msg

def daily_tick(char, game_day):
    d=ensure_advanced(char)
    last=d.get("last_tick_day",0)
    if game_day<=last: return []
    msgs=[]
    for day in range(last+1,game_day+1):
        d["last_tick_day"]=day
        n=d["needs"]
        n["sleep"]=min(100,n["sleep"]+random.randint(3,7))
        n["energy"]=max(0,n["energy"]-random.randint(2,6))
        n["hygiene"]=max(0,n["hygiene"]-random.randint(1,4))
        n["stress"]=max(0,min(100,n["stress"]+random.randint(-2,4)))
        char.hunger=min(120,char.hunger+random.randint(3,9))
        char.thirst=min(120,char.thirst+random.randint(3,9))
        char.fatigue=min(100,char.fatigue+random.randint(1,5))
        if n["sleep"]>80 or n["energy"]<15:
            char.health=max(0,char.health-random.randint(0,2))
        if char.hunger>100 or char.thirst>100:
            char.health=max(0,char.health-random.randint(1,4))
        if n["hygiene"]<20:
            char.health=max(0,char.health-random.randint(0,2))
        # debts/interest
        if d["bank"]["debt"]>0:
            d["bank"]["debt"] += int(d["bank"]["debt"]*d["bank"]["loan_rate"]/365)
            d["bank"]["credit"]=max(0,d["bank"]["credit"]-1)
        # property maintenance/rent
        for prop in d["properties"]:
            fee=max(0,prop.get("maintenance",0))
            if char.money>=fee: char.money-=fee
            else: prop["level"]=max(1,prop.get("level",1)-1)
        # vehicle deterioration
        for v in d["vehicles"]:
            v["condition"]=max(0,v["condition"]-random.choice([0,0,1]))
        advance_economy(char)
        if d["event_cooldown"]<=0 and random.random()<.18:
            msgs.append(random_event(char)); d["event_cooldown"]=2
        else: d["event_cooldown"]=max(0,d["event_cooldown"]-1)
        # temporary conditions
        for c in d["health_state"]["conditions"][:]:
            c["days"]-=1
            if c["days"]<=0: d["health_state"]["conditions"].remove(c)
        # achievements
        if char.money>=1_000_000_000 and "میلیاردر" not in d["achievements"]:
            d["achievements"].append("میلیاردر"); msgs.append("🏆 دستاورد: میلیاردر")
        if d["reputation"]>=80 and "چهره محبوب" not in d["achievements"]:
            d["achievements"].append("چهره محبوب"); msgs.append("🏆 دستاورد: چهره محبوب")
    d["records"]["highest_money"]=max(d["records"]["highest_money"],char.money)
    d["records"]["highest_reputation"]=max(d["records"]["highest_reputation"],d["reputation"])
    if char.health<=0:
        char.alive=False
        msgs.append("💀 سلامتت به صفر رسید؛ شخصیتت از دنیا رفت.")
    return msgs

def advanced_status(char):
    d=ensure_advanced(char); p=d["personality"]; n=d["needs"]; e=d["education"]; b=d["bank"]; l=d["legal"]
    return (
        "🧠 **زندگی پیشرفته**\n\n"
        f"🎭 شخصیت: شجاعت {p['شجاعت']} | هوش {p['هوش']} | کاریزما {p['کاریزما']}\n"
        f"📋 نظم {p['نظم']} | شانس {p['خوش‌شانسی']} | اراده {p['اراده']}\n"
        f"😴 خواب {n['sleep']}% | ⚡ انرژی {n['energy']}% | 🧼 بهداشت {n['hygiene']}% | 😰 استرس {n['stress']}%\n"
        f"⭐ شهرت: {d['reputation']}/100\n"
        f"🎓 تحصیل: {e['level']} | معدل: {e['gpa']:.2f}\n"
        f"🏦 بانک: جاری {b['checking']:,} | پس‌انداز {b['savings']:,} | بدهی {b['debt']:,}\n"
        f"⚖️ سابقه کیفری: {l['record']} | جریمه: {l['fines']:,}\n"
        f"🏠 املاک: {len(d['properties'])} | 🚗 وسایل نقلیه: {len(d['vehicles'])}\n"
        f"🏢 کسب‌وکار: {len(d['businesses'])} | 📈 سبد سهام: {sum(x['qty'] for x in d['portfolio'].values())}"
    )
