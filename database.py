# -*- coding: utf-8 -*-
"""
سیستم دیتابیس PostgreSQL برای ذخیره دائمی اطلاعات بازیکن‌ها
"""

import os
import json
from datetime import datetime
from urllib.parse import urlparse

# تلاش برای وارد کردن psycopg2
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("⚠️  psycopg2 نصب نیست. برای ذخیره دائمی: pip install psycopg2-binary")

# تنظیمات اتصال (از محیط یا پیش‌فرض)
def _db_config():
    """Build a safe psycopg2 config. DATABASE_URL is preferred on Render."""
    url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if url:
        try:
            parsed = urlparse(url)
            if not parsed.hostname:
                raise ValueError("DATABASE_URL فاقد hostname است")
            cfg = {
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "dbname": (parsed.path or "").lstrip("/") or "iranian_life_sim",
                "user": parsed.username or "postgres",
                "password": parsed.password or "",
            }
            # Preserve sslmode when supplied by an external PostgreSQL URL.
            if parsed.query:
                from urllib.parse import parse_qs
                qs = parse_qs(parsed.query)
                if qs.get("sslmode"):
                    cfg["sslmode"] = qs["sslmode"][0]
            return cfg
        except Exception as e:
            print(f"⚠️ DATABASE_URL نامعتبر است: {e}")

    host = os.getenv("DB_HOST", "localhost").strip()
    # Backward compatibility: older Render deployments sometimes put the whole URL in DB_HOST.
    if host.startswith(("postgres://", "postgresql://")):
        os.environ["DATABASE_URL"] = host
        return _db_config()
    return {
        "host": host,
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "iranian_life_sim"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }


DB_CONFIG = _db_config()

def get_connection():
    if not PSYCOPG2_AVAILABLE:
        return None
    try:
        return psycopg2.connect(connect_timeout=10, **_db_config())
    except Exception as e:
        print(f"❌ خطا در اتصال به دیتابیس: {e}")
        return None


def init_database():
    """ساخت جدول‌ها در صورت نبودن"""
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id              SERIAL PRIMARY KEY,
                player_id       VARCHAR(32) UNIQUE NOT NULL,
                numeric_id      VARCHAR(32),
                name            VARCHAR(64) NOT NULL,
                job             VARCHAR(64) DEFAULT 'بیکار',
                display_name    VARCHAR(64),
                gender          VARCHAR(16),
                city            VARCHAR(64),
                neighborhood    VARCHAR(64),
                home            VARCHAR(128),
                family          VARCHAR(64),
                birth_year      INT DEFAULT 1385,
                age_days        INT DEFAULT 0,
                hunger          INT DEFAULT 50,
                thirst          INT DEFAULT 50,
                fatigue         INT DEFAULT 30,
                health          INT DEFAULT 80,
                mental          INT DEFAULT 70,
                money           BIGINT DEFAULT 0,
                location        VARCHAR(128) DEFAULT 'خانه',
                x               INT DEFAULT 0,
                y               INT DEFAULT 0,
                god_mode        BOOLEAN DEFAULT FALSE,
                marital_status  VARCHAR(32) DEFAULT 'مجرد',
                bio             TEXT DEFAULT '',
                admin_password_hash VARCHAR(64),
                children        JSONB DEFAULT '[]',
                family_members JSONB DEFAULT '[]',
                home_data      JSONB DEFAULT '{}',
                inventory      JSONB DEFAULT '{}',
                life_data      JSONB DEFAULT '{}',
                last_age_game_day INT DEFAULT 0,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_admins (
                numeric_id  VARCHAR(32) PRIMARY KEY,
                added_by    VARCHAR(32),
                added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ستون‌های جدید برای نسخه‌های قبلی دیتابیس
        for migration in [
            "ALTER TABLE players ADD COLUMN IF NOT EXISTS job VARCHAR(64) DEFAULT 'بیکار'",
            "ALTER TABLE players ADD COLUMN IF NOT EXISTS family_members JSONB DEFAULT '[]'",
            "ALTER TABLE players ADD COLUMN IF NOT EXISTS home_data JSONB DEFAULT '{}'",
            "ALTER TABLE players ADD COLUMN IF NOT EXISTS last_age_game_day INT DEFAULT 0",
            "ALTER TABLE players ADD COLUMN IF NOT EXISTS inventory JSONB DEFAULT '{}'",
            "ALTER TABLE players ADD COLUMN IF NOT EXISTS life_data JSONB DEFAULT '{}'",
        ]:
            cur.execute(migration)

        # ادمین اصلی همیشه باشد
        cur.execute("""
            INSERT INTO game_admins (numeric_id, added_by)
            VALUES ('6227792513', 'system')
            ON CONFLICT (numeric_id) DO NOTHING;
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_players_player_id ON players(player_id);
            CREATE INDEX IF NOT EXISTS idx_players_numeric_id ON players(numeric_id);
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("✅ دیتابیس و جدول‌ها آماده شدند.")
        return True
    except Exception as e:
        print(f"❌ خطا در ساخت جدول: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False


def save_player(char) -> bool:
    """ذخیره یا آپدیت بازیکن"""
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        children_json = json.dumps(getattr(char, 'children', []), ensure_ascii=False)
        family_json = json.dumps(getattr(char, 'family_members', []), ensure_ascii=False)
        home_json = json.dumps(getattr(char, 'home_data', {}), ensure_ascii=False)
        inventory_json = json.dumps(getattr(char, 'inventory', {}), ensure_ascii=False)
        life_data_json = json.dumps(getattr(char, 'life_data', {}), ensure_ascii=False)

        cur.execute("""
            INSERT INTO players (
                player_id, numeric_id, name, job, display_name, gender, city, neighborhood,
                home, family, birth_year, age_days, hunger, thirst, fatigue, health, mental,
                money, location, x, y, god_mode, marital_status, bio, admin_password_hash,
                children, family_members, home_data, inventory, life_data, last_age_game_day, updated_at, last_login
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON CONFLICT (player_id) DO UPDATE SET
                numeric_id = EXCLUDED.numeric_id,
                name = EXCLUDED.name,
                job = EXCLUDED.job,
                display_name = EXCLUDED.display_name,
                gender = EXCLUDED.gender,
                city = EXCLUDED.city,
                neighborhood = EXCLUDED.neighborhood,
                home = EXCLUDED.home,
                family = EXCLUDED.family,
                age_days = EXCLUDED.age_days,
                hunger = EXCLUDED.hunger,
                thirst = EXCLUDED.thirst,
                fatigue = EXCLUDED.fatigue,
                health = EXCLUDED.health,
                mental = EXCLUDED.mental,
                money = EXCLUDED.money,
                location = EXCLUDED.location,
                x = EXCLUDED.x,
                y = EXCLUDED.y,
                god_mode = EXCLUDED.god_mode,
                marital_status = EXCLUDED.marital_status,
                bio = EXCLUDED.bio,
                admin_password_hash = EXCLUDED.admin_password_hash,
                children = EXCLUDED.children,
                family_members = EXCLUDED.family_members,
                home_data = EXCLUDED.home_data,
                inventory = EXCLUDED.inventory,
                life_data = EXCLUDED.life_data,
                last_age_game_day = EXCLUDED.last_age_game_day,
                updated_at = CURRENT_TIMESTAMP,
                last_login = CURRENT_TIMESTAMP;
        """, (
            char.player_id,
            getattr(char, 'numeric_id', None),
            char.name,
            getattr(char, 'job', 'بیکار'),
            getattr(char, 'display_name', char.name),
            char.gender,
            char.city,
            char.neighborhood,
            char.home,
            char.family,
            char.birth_year,
            char.age_days,
            char.hunger,
            char.thirst,
            char.fatigue,
            char.health,
            char.mental,
            char.money,
            char.location,
            char.x,
            char.y,
            char.god_mode,
            getattr(char, 'marital_status', 'مجرد'),
            getattr(char, 'bio', ''),
            getattr(char, 'admin_password_hash', ''),
            children_json,
            family_json,
            home_json,
            inventory_json,
            life_data_json,
            getattr(char, 'last_age_game_day', 0),
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره بازیکن: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False


def load_player(player_id: str):
    """بارگذاری بازیکن با player_id"""
    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM players WHERE player_id = %s", (player_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ خطا در بارگذاری: {e}")
        if conn:
            conn.close()
        return None


def load_player_by_numeric_id(numeric_id: str):
    """بارگذاری با آیدی عددی (مثل تلگرام)"""
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM players WHERE numeric_id = %s", (str(numeric_id),))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ خطا: {e}")
        if conn:
            conn.close()
        return None


def apply_loaded_data(char, data: dict):
    """اعمال داده‌های لود شده روی آبجکت شخصیت"""
    if not data:
        return
    char.player_id = data.get("player_id", char.player_id)
    char.numeric_id = data.get("numeric_id")
    char.name = data.get("name", char.name)
    char.job = data.get("job", getattr(char, "job", "بیکار"))
    char.display_name = data.get("display_name", char.name)
    char.gender = data.get("gender", char.gender)
    char.city = data.get("city", char.city)
    char.neighborhood = data.get("neighborhood", char.neighborhood)
    char.home = data.get("home", char.home)
    char.family = data.get("family", char.family)
    char.birth_year = data.get("birth_year", 1385)
    char.age_days = max(170, data.get("age_days", 170))
    char.family_members = data.get("family_members") or getattr(char, 'family_members', [])
    char.home_data = data.get("home_data") or getattr(char, 'home_data', {})
    inventory = data.get("inventory", {})
    if isinstance(inventory, str):
        try: inventory = json.loads(inventory)
        except Exception: inventory = {}
    char.inventory = inventory or {}
    life_data = data.get("life_data", {})
    if isinstance(life_data, str):
        try: life_data = json.loads(life_data)
        except Exception: life_data = {}
    char.life_data = life_data or {}
    try:
        from advanced_simulation import ensure_advanced
        ensure_advanced(char)["career"]["job"] = getattr(char, "job", "بیکار")
    except Exception:
        pass
    char.last_age_game_day = data.get("last_age_game_day", 0)
    char.hunger = data.get("hunger", 50)
    char.thirst = data.get("thirst", 50)
    char.fatigue = data.get("fatigue", 30)
    char.health = data.get("health", 80)
    char.mental = data.get("mental", 70)
    char.money = data.get("money", 0)
    char.location = data.get("location", "خانه")
    char.x = data.get("x", 0)
    char.y = data.get("y", 0)
    char.god_mode = data.get("god_mode", False)
    char.marital_status = data.get("marital_status", "مجرد")
    char.bio = data.get("bio", "")
    char.admin_password_hash = data.get("admin_password_hash", "")
    children = data.get("children", [])
    if isinstance(children, str):
        children = json.loads(children)
    char.children = children or []
