# -*- coding: utf-8 -*-
"""جهان زنده: اقتصاد، بازار کالا، NPC، اخبار، بحران و رویدادهای زنجیره‌ای."""
from __future__ import annotations
import random
from copy import deepcopy
GOODS={"نان":80000,"برنج":900000,"سوخت":40000,"دارو":350000,"لباس":2000000,"موبایل":18000000,"لوازم خانه":7000000}
CITY_SECTORS={"تهران":["فناوری","خدمات","ساخت‌وساز"],"اصفهان":["صنعت","خدمات"],"مشهد":["گردشگری","خدمات"],"شیراز":["گردشگری","کشاورزی"],"تبریز":["صنعت","تجارت"],"رشت":["کشاورزی","گردشگری"],"اهواز":["انرژی","صنعت"],"کرج":["صنعت","خدمات"]}
NPC_NAMES=[("رضا","پسر"),("نگار","دختر"),("سینا","پسر"),("مهسا","دختر"),("کیان","پسر"),("سارا","دختر"),("محمد","پسر"),("آوا","دختر")]
def default_world():
    return {"inflation":.18,"unemployment":.08,"growth":.01,"currency_value":1.0,"day":0,"cycle":"عادی","goods":{k:{"supply":100.0,"demand":100.0,"price":1.0} for k in GOODS},"cities":{},"news":[]}
def ensure_world(w):
    base=default_world(); w=w if isinstance(w,dict) else {}
    for k,v in base.items(): w.setdefault(k,deepcopy(v))
    for g in GOODS: w["goods"].setdefault(g,deepcopy(base["goods"][g]))
    return w
def city_econ(w,city):
    w=ensure_world(w); c=w["cities"].setdefault(city,{"inflation":w["inflation"],"unemployment":w["unemployment"],"growth":w["growth"],"wealth":1.0,"jobs":1.0,"rent":1.0,"crime":1.0})
    c["unemployment"] += (w["unemployment"]-c["unemployment"])*.15; c["growth"] += (w["growth"]-c["growth"])*.15; c["inflation"] += (w["inflation"]-c["inflation"])*.15
    c["jobs"]=max(.15,1.35-c["unemployment"]*1.1+max(-.2,w["growth"])*1.5); c["rent"]=max(.5,1+c["inflation"]*1.8+c["wealth"]*.08)
    return c
def advance_world(w,day,city=None):
    w=ensure_world(w)
    if day<=int(w.get("day",0)): return w,[]
    news=[]
    for _ in range(min(60,day-int(w.get("day",0)))):
        r=random.random()
        if r<.035:
            w["growth"]-=random.uniform(.03,.08); w["unemployment"]+=random.uniform(.02,.07); w["inflation"]+=random.uniform(.02,.10); w["cycle"]="بحران اقتصادی"; news.append("🏭 موج تعطیلی کارخانه‌ها؛ فرصت‌های شغلی کاهش یافت.")
        elif r<.075:
            w["growth"]+=random.uniform(.02,.06); w["unemployment"]-=random.uniform(.01,.035); w["cycle"]="رونق"; news.append("📈 رونق اقتصادی؛ شرکت‌ها دوباره استخدام می‌کنند.")
        elif r<.11:
            good=random.choice(list(GOODS)); w["goods"][good]["supply"]*=random.uniform(.60,.85); w["goods"][good]["demand"]*=random.uniform(1.08,1.30); w["cycle"]="شوک عرضه"; news.append(f"📦 کمبود «{good}»؛ قیمت بازار بالا رفت.")
        else:
            w["growth"]+=random.uniform(-.012,.015); w["unemployment"]+=random.uniform(-.008,.012); w["inflation"]+=random.uniform(-.006,.014); w["cycle"]="عادی"
        w["inflation"]=max(.01,min(3,w["inflation"])); w["unemployment"]=max(.015,min(.90,w["unemployment"])); w["growth"]=max(-.35,min(.25,w["growth"]))
        for x in w["goods"].values():
            x["supply"]*=random.uniform(.97,1.03); x["demand"]*=1+max(0,w["inflation"])*.015; ratio=max(.35,min(4,x["demand"]/max(1,x["supply"]))); x["price"]=max(.25,min(12,x["price"]*(1+.18*(ratio-1)+w["inflation"]*.12)))
        w["currency_value"]=max(.02,w["currency_value"]/(1+max(0,w["inflation"]-.12)*.10)); w["day"]+=1
        for c in list(w["cities"]): city_econ(w,c)
    if city: city_econ(w,city)
    if news: w["news"]=(news+w.get("news",[]))[:20]
    return w,news
def job_chance(w,char,skill=0):
    p=getattr(char,"life_data",{}).get("personality",{}); e=getattr(char,"life_data",{}).get("education",{}); education=10 if e.get("level") in ("دیپلم","لیسانس") else 0
    return max(.03,min(.95,.90-w["unemployment"]*.82+skill*.004+education*.003+(p.get("کاریزما",50)-50)*.002))
def market_price(w,good,city_factor=1):
    w=ensure_world(w); return int(GOODS.get(good,100000)*w["goods"].get(good,{}).get("price",1)*(1+w["inflation"])*city_factor)
def simulate_npcs(w,city,limit=8):
    c=city_econ(w,city); out=[]
    for _ in range(limit):
        name,gender=random.choice(NPC_NAMES); age=random.randint(18,67); job="بیکار" if random.random()<c["unemployment"] else random.choice(CITY_SECTORS.get(city,["خدمات"])); money=random.randint(1_000_000,120_000_000); goal=random.choice(["خرید خانه","پیشرفت شغلی","تشکیل خانواده","مهاجرت","پس‌انداز"]); action="جست‌وجوی کار" if job=="بیکار" else random.choice(["کار","خرید ضروریات","پس‌انداز","پرداخت اجاره"]); out.append({"name":name,"gender":gender,"age":age,"job":job,"money":money,"goal":goal,"action":action,"memory":[f"روز {w['day']}: {action}"]})
    return out
def chain_event(char,w):
    d=getattr(char,"life_data",{}); ch=d.setdefault("event_chain",{})
    if ch.get("active"): return None
    if random.random()<.045: ch.update({"active":True,"type":"accident","step":1,"days_left":3}); return "🚗 حادثه زنجیره‌ای: آسیب دیدی؛ چند روز توان کار کردنت کمتر می‌شود."
    if random.random()<.10 and w["unemployment"]>.20 and getattr(char,"job","بیکار")!="بیکار": ch.update({"active":True,"type":"jobloss","step":1,"days_left":5}); char.job="بیکار"; d["career"]["job"]="بیکار"; return "📉 تعدیل نیرو: شغلت را از دست دادی و باید دوباره دنبال کار بگردی."
    return None
def advance_chain(char):
    ch=getattr(char,"life_data",{}).get("event_chain")
    if not ch or not ch.get("active"): return None
    ch["days_left"]=max(0,int(ch.get("days_left",1))-1)
    if ch["type"]=="accident" and ch["step"]==1: ch["step"]=2; return "🏥 پیامد حادثه: درمان زودتر می‌تواند از طولانی شدن آسیب جلوگیری کند."
    if ch["days_left"]==0: ch["active"]=False; return "✅ پیامد رویداد تمام شد؛ وضعیت به حالت عادی برگشت."
    return None
def news_text(w,city=None):
    w=ensure_world(w); lines=["📰 روزنامه جهان بازی",f"📈 تورم: {w['inflation']*100:.1f}%",f"📉 بیکاری: {w['unemployment']*100:.1f}%",f"📊 رشد اقتصادی: {w['growth']*100:.1f}%",f"💱 ارزش پول: {w['currency_value']:.3f}",f"🏷 وضعیت: {w['cycle']}"]
    if city:
        c=city_econ(w,city); lines.append(f"🏙 {city} | بیکاری محلی: {c['unemployment']*100:.1f}% | فرصت شغلی ×{c['jobs']:.2f} | اجاره ×{c['rent']:.2f}")
    lines += ["• "+x for x in w.get("news",[])[:4]]; return "\n".join(lines)


def neighborhood_factor(name):
    n=str(name or "")
    if any(x in n for x in ("بالا","اعیان","مرفه","شمال")): return 1.30
    if any(x in n for x in ("پایین","حاشیه","فقیر")): return .78
    return 1.0

def evolve_businesses(w,city):
    c=city_econ(w,city); events=[]
    if c["unemployment"]>.35 and random.random()<.18: events.append("🏪 چند مغازه به‌دلیل کاهش مشتریان تعطیل شدند.")
    if c["jobs"]>1.05 and random.random()<.16: events.append("🏢 یک کسب‌وکار جدید در شهر افتتاح شد.")
    if events: w["news"]=(events+w.get("news",[]))[:20]
    return events
