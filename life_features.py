# -*- coding: utf-8 -*-
"""سیستم‌های پیشرفته شبیه‌ساز زندگی: تحصیل، بانک، مسکن، خودرو، روابط، قانون، درمان، کسب‌وکار، بورس و مالیات."""
import random
from difficulty import hard_cost, hard_reward, hard_damage


def default_life_data(city=""):
    return {
        "education": {"level": "دبیرستان", "status": "سال آخر دبیرستان", "field": None, "progress": 70, "skill": 10},
        "bank": {"balance": 0, "loan": 0, "loan_due": 0},
        "housing": {"owned": False, "property": None, "value": 0, "rent": 12_000_000},
        "vehicles": [],
        "relationship": {"partner": None, "affection": 0, "meetings": 0},
        "legal": {"record": 0, "wanted": 0, "jail_days": 0, "fine": 0},
        "business": {"active": False, "name": None, "type": None, "capital": 0, "revenue": 0, "employees": 0, "level": 1},
        "stocks": {"holdings": {}, "last_prices": {}},
        "tax": {"owed": 0, "last_settlement_day": 0},
        "healthcare": {"last_visit_day": -1},
        "city_economy": {"city": city, "index": round(random.uniform(0.9, 1.25), 2)},
    }


def ensure_data(char):
    data = getattr(char, "life_data", None)
    base = default_life_data(getattr(char, "city", ""))
    if not isinstance(data, dict):
        data = base
    for k, v in base.items():
        if k not in data or not isinstance(data[k], dict):
            data[k] = v
        else:
            for sk, sv in v.items():
                data[k].setdefault(sk, sv)
    data["city_economy"]["city"] = getattr(char, "city", data["city_economy"].get("city", ""))
    char.life_data = data
    return data


def age_years(char):
    return max(17, int(getattr(char, "age_days", 170) // 10))


def economy_factor(char):
    from locations import CITIES
    city = CITIES.get(getattr(char, "city", ""), {})
    opp = city.get("opportunities", "متوسط")
    cost = city.get("cost_of_living", "متوسط")
    opp_factor = {"خیلی بالا": 1.25, "بالا": 1.15, "متوسط رو به بالا": 1.08, "متوسط": 1.0, "متوسط رو به پایین": .92}.get(opp, 1.0)
    cost_factor = {"خیلی بالا": 1.35, "بالا": 1.18, "متوسط رو به بالا": 1.08, "متوسط": 1.0}.get(cost, 1.0)
    return opp_factor, cost_factor


def education_text(char):
    d = ensure_data(char)["education"]
    return (f"🏫 تحصیل\n🎓 مدرک: {d['level']}\n📚 وضعیت: {d['status']}\n"
            f"📖 رشته: {d.get('field') or 'انتخاب نشده'}\n🧠 مهارت: {d['skill']}\n📈 پیشرفت: {d['progress']}%")


def study(char, gt):
    d = ensure_data(char)["education"]
    age = age_years(char)
    if age < 17:
        return "🏫 هنوز در سن مدرسه هستی؛ بازی اصلی از ۱۷ سالگی شروع می‌شود."
    if d["level"] == "لیسانس":
        return "🎓 مدرک لیسانس رو گرفتی. برای کار تخصصی آماده‌ای."
    if age_years(char) < 18:
        d["progress"] = min(100, d["progress"] + random.randint(5, 12))
        d["skill"] = min(100, d["skill"] + random.randint(1, 3))
        char.fatigue = min(100, char.fatigue + 5); gt.advance(90)
        if d["progress"] >= 100:
            d.update(level="دیپلم", status="فارغ‌التحصیل دبیرستان", progress=0)
            return "🎓 دبیرستان رو تموم کردی و دیپلم گرفتی. از ۱۸ سالگی می‌تونی دانشگاه رو شروع کنی."
        return f"🏫 برای امتحان‌های مدرسه درس خوندی. پیشرفت سال آخر: {d['progress']}%"
    if d["status"] in ("سال آخر دبیرستان", "فارغ‌التحصیل دبیرستان") and d["level"] != "دیپلم":
        d.update(level="دیپلم", status="آماده دانشگاه", progress=0)
    if d["status"] == "آماده دانشگاه":
        tuition = hard_cost(8_000_000)
        if char.money < tuition:
            return f"💸 شهریه شروع دانشگاه {tuition:,} تومنه و پول کافی نداری."
        char.money -= tuition
        d.update(status="دانشجو", field=random.choice(["مهندسی کامپیوتر", "مدیریت", "حسابداری", "حقوق", "علوم تجربی"]), progress=0)
        return f"🎓 وارد دانشگاه شدی؛ رشته‌ات: {d['field']}\n💸 شهریه: {tuition:,} تومان"
    d["progress"] = min(100, d["progress"] + random.randint(8, 16))
    d["skill"] = min(100, d["skill"] + random.randint(2, 5))
    char.fatigue = min(100, char.fatigue + 8); gt.advance(90)
    if d["progress"] >= 100:
        d.update(level="لیسانس", status="فارغ‌التحصیل")
        return "🎓 تبریک! دانشگاه رو تموم کردی و مدرک لیسانس گرفتی."
    return f"📚 درس خوندی. پیشرفت دانشگاه: {d['progress']}%"


def bank_text(char):
    b = ensure_data(char)["bank"]
    return f"🏦 بانک\n💵 پول نقد: {char.money:,} تومان\n🏧 موجودی حساب: {b['balance']:,} تومان\n💳 وام: {b['loan']:,} تومان\n📅 سررسید وام: {b['loan_due']} روز"


def bank_deposit(char, amount):
    b = ensure_data(char)["bank"]
    if char.money < amount:
        return "💸 پول نقد کافی نداری."
    char.money -= amount; b["balance"] += amount
    return f"🏦 {amount:,} تومان به حساب واریز شد."


def bank_withdraw(char, amount):
    b = ensure_data(char)["bank"]
    if b["balance"] < amount:
        return "💸 موجودی حسابت کافی نیست."
    b["balance"] -= amount; char.money += amount
    return f"🏧 {amount:,} تومان برداشت کردی."


def bank_loan(char):
    b = ensure_data(char)["bank"]
    if b["loan"] > 0:
        return "❌ هنوز وام قبلیت تسویه نشده."
    amount = max(10_000_000, min(50_000_000, char.money * 2 + 10_000_000))
    b["loan"] = amount; b["loan_due"] = 10
    char.money += amount
    return f"💳 وام {amount:,} تومانی گرفتی. سررسید: ۱۰ روز بازی."


def housing_text(char):
    h = ensure_data(char)["housing"]
    if h["owned"]:
        return f"🏠 مسکن\n🏡 ملک: {h['property']}\n💰 ارزش تقریبی: {h['value']:,} تومان\n🔑 مالک: خودت"
    return f"🏠 مسکن\n🏢 وضعیت: اجاره‌ای\n💸 اجاره سالانه بازی: {h['rent']:,} تومان\nبرای خرید خانه آماده باش سرمایه جمع کنی."


def rent_house(char):
    h = ensure_data(char)["housing"]
    cost = hard_cost(h["rent"])
    if char.money < cost:
        return f"💸 برای تمدید اجاره {cost:,} تومان لازم داری."
    char.money -= cost
    return f"🏠 اجاره خانه پرداخت شد: {cost:,} تومان"


def buy_house(char):
    h = ensure_data(char)["housing"]
    if h["owned"]:
        return "🏡 از قبل صاحب خانه‌ای."
    factor = economy_factor(char)[1]
    price = hard_cost(int(2_500_000_000 * factor))
    if char.money < price:
        return f"💸 قیمت خانه مناسب این شهر حدود {price:,} تومنه. پولت کافیه نیست."
    char.money -= price
    h.update(owned=True, property="آپارتمان شخصی", value=price)
    char.home = "آپارتمان شخصی"
    return f"🎉 خانه خریدی!\n🏡 قیمت: {price:,} تومان"


def vehicle_text(char):
    vs = ensure_data(char)["vehicles"]
    if not vs:
        return "🚗 وسایل نقلیه\nهنوز وسیله نقلیه‌ای نداری."
    return "🚗 وسایل نقلیه\n" + "\n".join(f"• {v['name']} | ارزش {v['value']:,} | سوخت {v.get('fuel', 100)}%" for v in vs)


def buy_vehicle(char, kind):
    options = {"موتورسیکلت": (hard_cost(180_000_000), 180), "خودرو اقتصادی": (hard_cost(1_200_000_000), 60), "خودرو خانوادگی": (hard_cost(2_500_000_000), 70)}
    price, fuel = options[kind]
    if char.money < price:
        return f"💸 قیمت {kind}: {price:,} تومان"
    char.money -= price
    ensure_data(char)["vehicles"].append({"name": kind, "value": price, "fuel": fuel})
    return f"🚘 {kind} خریدی.\n💸 هزینه: {price:,} تومان"


def relationship_text(char):
    r = ensure_data(char)["relationship"]
    if not r["partner"]:
        return "❤️ روابط\nوضعیت: مجرد\nمی‌تونی از ۱۸ سالگی وارد رابطه جدی بشی."
    return f"❤️ شریک عاطفی: {r['partner']}\n💞 صمیمیت: {r['affection']}%\n💍 برای ازدواج باید صمیمیتت به ۷۰٪ برسه."


def meet_partner(char):
    if age_years(char) < 18:
        return "❌ برای رابطه جدی حداقل ۱۸ سال لازمه."
    r = ensure_data(char)["relationship"]
    if not r["partner"]:
        r["partner"] = random.choice(["سارا", "مریم", "نگار", "آرین", "کیان", "پارسا"])
        r["affection"] = random.randint(15, 30)
        return f"💞 با {r['partner']} آشنا شدی. صمیمیت اولیه: {r['affection']}%"
    r["affection"] = min(100, r["affection"] + random.randint(5, 12)); r["meetings"] += 1
    return f"❤️ با {r['partner']} وقت گذروندی. صمیمیت: {r['affection']}%"


def marry(char):
    if age_years(char) < 18: return "❌ ازدواج از ۱۸ سالگی در دسترسه."
    r = ensure_data(char)["relationship"]
    if not r["partner"]: return "اول یک رابطه ایجاد کن."
    if r["affection"] < 70: return "💞 رابطه هنوز برای ازدواج آماده نیست؛ صمیمیت باید حداقل ۷۰٪ باشه."
    if char.marital_status == "متأهل": return "💍 تو متأهلی."
    char.marital_status = "متأهل"
    return f"💍 با {r['partner']} ازدواج کردی!"


def have_child(char):
    if char.marital_status != "متأهل": return "❌ برای فرزندآوری باید متأهل باشی."
    if age_years(char) < 20: return "❌ برای داشتن فرزند کمی زوده؛ حداقل ۲۰ سال."
    if len(getattr(char, "children", [])) >= 5: return "👶 فعلاً تعداد فرزندانت به سقف سیستم رسیده."
    male = ["آراد", "نیما", "رادین", "کیان", "پارسا", "سام", "یونس"]
    female = ["آوا", "هانا", "یسنا", "نیکا", "باران", "هلیا", "رها"]
    gender = random.choice(["پسر", "دختر"])
    name = random.choice(male if gender == "پسر" else female)
    child = {"name": name, "gender": gender, "health": random.randint(75, 100), "age_days": 0, "age": 0, "alive": True}
    char.children.append(child)
    return f"👶 فرزند جدیدت به دنیا اومد: {child['name']} ({child['gender']})\n🍼 سن: ۰ سال | وضعیت: نوزاد"

# Compatibility wrappers for the advanced bot panel. Kept lazy to avoid circular imports.
def legal_text(char):
    from advanced_simulation import ensure_advanced
    d=ensure_advanced(char)["legal"]
    return f"⚖️ قانون\n📁 سابقه: {d['record']}\n💸 جریمه: {d['fines']:,}\n🚔 زندان: {d['jail_days']} روز"
def commit_crime(char):
    from advanced_simulation import commit_crime_adv
    return commit_crime_adv(char)
def pay_fine(char):
    from advanced_simulation import ensure_advanced
    d=ensure_advanced(char); amount=int(d['legal'].get('fines',0))
    if amount<=0: return "✅ جریمه‌ای نداری."
    if char.money<amount: return f"💸 برای پرداخت جریمه {amount:,} تومان لازم داری."
    char.money-=amount; d['legal']['fines']=0; return f"✅ جریمه {amount:,} تومان پرداخت شد."
def hospital(char):
    from advanced_simulation import ensure_advanced, living_cost
    d=ensure_advanced(char); cost=living_cost(char,500_000)
    if char.money<cost: return f"🏥 هزینه درمان {cost:,} تومان است."
    char.money-=cost; char.health=min(100,char.health+random.randint(8,20)); d['needs']['stress']=max(0,d['needs']['stress']-8); return f"🏥 درمان انجام شد. هزینه: {cost:,} تومان. سلامت: {char.health}%"
def business_text(char):
    from advanced_simulation import ensure_advanced
    bs=ensure_advanced(char).get('businesses',[]); return "🏢 کسب‌وکار\n"+("هنوز کسب‌وکاری نداری." if not bs else "\n".join(f"• {b.get('name','کسب‌وکار')} | سرمایه {b.get('capital',0):,} | فعال: {b.get('active',True)}" for b in bs))
def start_business(char):
    from advanced_simulation import start_business_adv
    return start_business_adv(char,"کسب‌وکار محلی")
def run_business(char):
    from advanced_simulation import run_business_adv
    d=ensure_advanced(char); return run_business_adv(char) if d.get('businesses') else "❌ ابتدا کسب‌وکار راه‌اندازی کن."
def stock_text(char):
    from advanced_simulation import ensure_advanced
    p=ensure_advanced(char).get('portfolio',{}); return "📈 بورس\n"+("سبد سهامت خالی است." if not p else "\n".join(f"• {k}: {v.get('qty',0)} سهم | میانگین {v.get('avg',0):,.0f}" for k,v in p.items()))
def stock_trade(char,symbol,buy):
    from advanced_simulation import stock_trade_adv
    return stock_trade_adv(char,symbol,buy,1)
def tax_text(char):
    from advanced_simulation import ensure_advanced
    tax=ensure_advanced(char).setdefault('tax',{'owed':0}); return f"🧾 مالیات\n💸 بدهی مالیاتی: {tax.get('owed',0):,} تومان"
def pay_tax(char):
    from advanced_simulation import ensure_advanced
    d=ensure_advanced(char); tax=d.setdefault('tax',{'owed':0}); amount=int(tax.get('owed',0))
    if amount<=0: return "✅ مالیاتی برای پرداخت نداری."
    if char.money<amount: return f"💸 برای پرداخت {amount:,} تومان مالیات پول کافی نداری."
    char.money-=amount; tax['owed']=0; return f"✅ {amount:,} تومان مالیات پرداخت شد."
def economic_tick(char,game_day):
    from advanced_simulation import advance_economy
    advance_economy(char); return None
def city_economy_text(char):
    from advanced_simulation import city_economy_adv
    return city_economy_adv(char)
def serve_jail(char):
    from advanced_simulation import ensure_advanced
    d=ensure_advanced(char); days=d['legal'].get('jail_days',0)
    if days<=0: return "🚔 زندانی نیستی."
    d['legal']['jail_days']=max(0,days-1); return f"🚔 یک روز زندان گذشت. روزهای باقی‌مانده: {d['legal']['jail_days']}"
