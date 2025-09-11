import sqlite3
import os

DB_NAME = "weather_bot.db"


def get_conn():
    """Создаёт подключение к базе SQLite."""
    return sqlite3.connect(DB_NAME)


def init_db():
    """Создаёт таблицы из db_init.sql."""
    script_path = os.path.join(os.path.dirname(__file__), "db_init.sql")
    with open(script_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_conn()
    try:
        conn.executescript(sql)
        conn.commit()
        print("✅ База и таблицы инициализированы")
    finally:
        conn.close()

def add_user(tg_id: int, chat_id: int):
    """Добавить пользователя, если его ещё нет в базе."""
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO users (tg_id, chat_id)
            VALUES (?, ?)
        """, (tg_id, chat_id))
        conn.commit()
    finally:
        conn.close()


def get_user(tg_id: int):
    """Получить данные пользователя по tg_id."""
    conn = get_conn()
    try:
        cur = conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        return cur.fetchone()
    finally:
        conn.close()


def update_city(tg_id: int, city: str, lat: float, lon: float, timezone: str = None, tz_offset: int = None):
    """Обновить город пользователя."""
    conn = get_conn()
    try:
        conn.execute("""
            UPDATE users
            SET city = ?, lat = ?, lon = ?, timezone = ?, tz_offset = ?
            WHERE tg_id = ?
        """, (city, lat, lon, timezone, tz_offset, tg_id))
        conn.commit()
    finally:
        conn.close()

def get_all_users():
    """Возвращает список всех пользователей в виде словарей."""
    conn = get_conn()
    try:
        cur = conn.execute("SELECT * FROM users")
        columns = [column[0] for column in cur.description]
        rows = cur.fetchall()
        # Преобразуем в список словарей
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()

def update_last_notify_date(tg_id, date_str):
    """Обновляет last_notify_date пользователя."""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE users SET last_notify_date = ? WHERE tg_id = ?",
            (date_str, tg_id)
        )
        conn.commit()
    finally:
        conn.close()


def save_weather_sample(tg_id, date, temp, temp_max, temp_min, condition, precipitation_type, pop, raw_json):
    """Сохраняет погодный прогноз в weather_samples."""
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO weather_samples
            (tg_id, date, temp, temp_max, temp_min, condition, precipitation_type, pop, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tg_id, date, temp, temp_max, temp_min, condition, precipitation_type, pop, raw_json))
        conn.commit()
    finally:
        conn.close()

def get_user_by_tg_id(tg_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # чтобы возвращать словарь
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()

    conn.close()

    if row:
        return dict(row)
    return None

if __name__ == "__main__":
    init_db()
