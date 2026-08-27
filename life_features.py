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
    child = {"name": random.choice(["آراد", "آوا", "نیما", "هانا", "رادین", "یسنا"]), "gender": random.choice(["پسر", "دختر"]), "health": random.randint(75, 100), "age": 0}
    char.children.append(child)
    return f"👶 فرزند جدیدت به دنیا اومد: {child['name']} ({child['gender']})"


def legal_text(char):
    l = ensure_data(char)["legal"]
    return f"⚖️ قانون و پلیس\n🚨 تحت تعقیب: {l['wanted']}%\n📋 سابقه: {l['record']}\n🔒 زندان: {l['jail_days']} روز\n💸 جریمه: {l['fine']:,} تومان"


def commit_crime(char):
    l = ensure_data(char)["legal"]
    if age_years(char) < 18: return "❌ این فعالیت فقط برای شخصیت بزرگسال در دسترسه."
    chance = min(0.999999, 0.95 + l["wanted"] / 2000)
    if random.random() < chance:
        l["record"] += 1; l["wanted"] = min(100, l["wanted"] + random.randint(20, 45)); l["fine"] += hard_cost(random.randint(500_000, 5_000_000)); l["jail_days"] += random.randint(1, 3)
        return f"🚔 پلیس گیرت انداخت! سابقه +۱ و محکوم به زندان شدی: {l['jail_days']} روز"
    gain = hard_reward(random.randint(500_000, 8_000_000)); char.money += gain; l["wanted"] = min(100, l["wanted"] + random.randint(8, 20))
    return f"⚠️ جرم انجام دادی و {gain:,} تومان به دست آوردی؛ تحت تعقیب شدی."


def pay_fine(char):
    l = ensure_data(char)["legal"]
    if l["fine"] <= 0: return "✅ جریمه‌ای نداری."
    if char.money < l["fine"]: return f"💸 جریمه‌ات {l['fine']:,} تومنه."
    amount = l["fine"]; char.money -= amount; l["fine"] = 0; l["wanted"] = max(0, l["wanted"] - 25)
    return f"⚖️ جریمه پرداخت شد: {amount:,} تومان"


def hospital(char):
    if char.health >= 95: return "❤️ سلامتت خوبه و فعلاً نیازی به بیمارستان نداری."
    cost = hard_cost(max(300_000, (100 - char.health) * 120_000))
    if char.money < cost: return f"🏥 هزینه درمان حدود {cost:,} تومنه."
    char.money -= cost; char.health = min(100, char.health + random.randint(15, 35)); char.fatigue = max(0, char.fatigue - 10)
    return f"🏥 درمان شدی. هزینه: {cost:,} تومان\n❤️ سلامت: {char.health}%"


def business_text(char):
    b = ensure_data(char)["business"]
    if not b["active"]: return "🏢 کسب‌وکار\nهنوز کسب‌وکاری نداری.\nسرمایه شروع: ۱۰۰ میلیون تومان."
    return f"🏢 {b['name']}\n📦 نوع: {b['type']}\n💰 سرمایه: {b['capital']:,}\n📈 درآمد آخر: {b['revenue']:,}\n👥 کارکنان: {b['employees']}\n⭐ سطح: {b['level']}"


def start_business(char):
    if age_years(char) < 18: return "❌ راه‌اندازی کسب‌وکار از ۱۸ سالگی."
    b = ensure_data(char)["business"]
    cost = hard_cost(100_000_000)
    if b["active"]: return "🏢 از قبل کسب‌وکار داری."
    if char.money < cost: return f"💸 حداقل سرمایه شروع {cost:,} تومنه."
    char.money -= cost; b.update(active=True, name=random.choice(["کسب‌وکار پارسا", "بازرگانی نوین", "فروشگاه آینده"]), type=random.choice(["فروشگاهی", "خدماتی", "آنلاین"]), capital=cost, revenue=0, employees=0, level=1)
    return f"🏢 کسب‌وکارت راه افتاد: {b['name']}"


def run_business(char):
    b = ensure_data(char)["business"]
    if not b["active"]: return "اول کسب‌وکار راه‌اندازی کن."
    opp, cost = economy_factor(char)
    revenue = hard_reward(int(random.randint(8_000_000, 30_000_000) * opp))
    expenses = int(revenue * random.uniform(.45, .75) * cost)
    profit = max(0, revenue - expenses)
    b["revenue"] = revenue; b["capital"] += profit; char.money += profit
    return f"📊 کسب‌وکارت فعالیت کرد.\n💵 فروش: {revenue:,}\n💸 هزینه: {expenses:,}\n📈 سود: {profit:,} تومان"


def stock_text(char):
    s = ensure_data(char)["stocks"]
    if not s["holdings"]: return "📈 بورس\nسهام نداری.\nاز گزینه خرید سهام شروع کن."
    lines=["📈 سبد سهام"]
    for sym, item in s["holdings"].items():
        lines.append(f"• {sym}: {item['shares']} سهم × {item['avg']:,} تومان")
    return "\n".join(lines)


def stock_trade(char, sym, buy=True):
    market = {"فولاد": 2_000_000, "خودرو": 1_200_000, "فناوری": 3_500_000, "بانک": 1_800_000}
    s = ensure_data(char)["stocks"]; price = hard_cost(market[sym])
    if buy:
        shares = 1
        if char.money < price: return "💸 پول کافی برای خرید این سهم نداری."
        char.money -= price
        item=s["holdings"].setdefault(sym, {"shares":0,"avg":price})
        item["avg"] = int((item["avg"]*item["shares"] + price)/(item["shares"]+1)); item["shares"] += shares
        return f"📈 یک سهم {sym} خریدی: {price:,} تومان"
    item=s["holdings"].get(sym)
    if not item or item["shares"]<=0: return "❌ از این سهم نداری."
    change = random.uniform(.85, 1.2); sell = int(price*change); item["shares"] -= 1; char.money += sell
    if item["shares"] <= 0: del s["holdings"][sym]
    return f"💹 یک سهم {sym} فروختی و {sell:,} تومان گرفتی."


def city_economy_text(char):
    from locations import CITIES
    city=getattr(char, "city", "")
    c=CITIES.get(city, {})
    opp, cost=economy_factor(char)
    return (f"🏙 اقتصاد {city}\n"
            f"💼 فرصت شغلی: {c.get('opportunities','متوسط')}\n"
            f"🏷 هزینه زندگی: {c.get('cost_of_living','متوسط')}\n"
            f"📊 ضریب فرصت: {opp:.2f}x\n"
            f"💸 ضریب هزینه: {cost:.2f}x\n"
            f"🏘 محله فعلی: {getattr(char,'neighborhood','مرکز شهر')}")


def serve_jail(char):
    l=ensure_data(char)["legal"]
    if l["jail_days"]<=0: return "🔓 زندانی نیستی."
    l["jail_days"]-=1
    char.mental=max(0,char.mental-random.randint(2,6)); char.fatigue=min(100,char.fatigue+5)
    return f"🔒 یک روز از محکومیتت را گذراندی. روزهای باقی‌مانده: {l['jail_days']}"


def tax_text(char):
    t=ensure_data(char)["tax"]
    return f"🧾 مالیات\n💸 مالیات معوق: {t['owed']:,} تومان\n📅 آخرین تسویه: روز {t['last_settlement_day']}"


def pay_tax(char):
    t=ensure_data(char)["tax"]
    if t["owed"]<=0: return "✅ مالیات معوقی نداری."
    if char.money<t["owed"]: return f"💸 مالیات معوق {t['owed']:,} تومنه."
    amount=t["owed"]; char.money-=amount; t["owed"]=0
    return f"🧾 مالیات پرداخت شد: {amount:,} تومان"


def economic_tick(char, current_day):
    """تسویه سالانه (هر ۱۰ روز بازی) و رویدادهای مالی."""
    d=ensure_data(char); years=max(0, current_day//10)
    t=d["tax"]
    if years > t["last_settlement_day"]//10:
        t["last_settlement_day"] = current_day
        income = max(0, int(char.money*.002))
        t["owed"] += income
    b=d["bank"]
    if b["loan"] and current_day >= b["loan_due"]:
        installment=min(b["loan"], int(b["loan"]*.25))
        if char.money>=installment:
            char.money-=installment; b["loan"]-=installment; b["loan_due"] = current_day+3
        else:
            b["loan"] += int(b["loan"]*.05); b["loan_due"] = current_day+3
    return []
