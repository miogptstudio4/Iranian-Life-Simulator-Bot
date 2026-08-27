# -*- coding: utf-8 -*-
"""بارگذاری فهرست کامل شهرهای ایران.
منبع داده: مخزن عمومی sajaddp/list-of-cities-in-Iran، نسخه تقسیمات کشوری ۱۴۰۲.
در صورت نبود اینترنت، فهرست داخلی پروژه به عنوان fallback استفاده می‌شود.
"""
import json
import os
import urllib.request

CITIES_URL = "https://raw.githubusercontent.com/sajaddp/list-of-cities-in-Iran/main/dist/json/cities.json"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "iran_cities_cache.json")


def load_full_iran_cities(fallback):
    names = []
    try:
        with urllib.request.urlopen(CITIES_URL, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        names = [str(x.get("name", "")).strip() for x in data if x.get("name")]
        names = sorted(set(n for n in names if n))
        if names:
            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(names, f, ensure_ascii=False)
            except Exception:
                pass
            return names
    except Exception:
        pass

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if cached:
            return sorted(set(cached))
    except Exception:
        pass
    return sorted(set(fallback))
