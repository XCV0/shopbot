import sqlite3
import json
from pathlib import Path

DB_PATH = "restaurant.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица employees
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        tg_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        office TEXT NOT NULL,
        ecard TEXT
    );
    """)

    # Таблица managers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS managers (
        tg_id INTEGER PRIMARY KEY
    );
    """)

    # Таблица shops
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        menu TEXT,               -- JSON
        time_available TEXT,
        day_available TEXT,
        report_time TEXT,
        active INTEGER NOT NULL DEFAULT 1  -- boolean (0/1)
    );
    """)

    conn.commit()
    conn.close()


# ======== EMPLOYEES ========

def add_employee(tg_id, name, office, ecard):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO employees (tg_id, name, office, ecard)
        VALUES (?, ?, ?, ?)
    """, (tg_id, name, office, ecard))

    conn.commit()
    conn.close()


def get_employee(tg_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM employees WHERE tg_id = ?", (tg_id,))
    row = cursor.fetchone()

    conn.close()
    return row


# ======== MANAGERS ========

def add_manager(tg_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT OR REPLACE INTO managers (tg_id) VALUES (?)", (tg_id,))
    conn.commit()
    conn.close()


def is_manager(tg_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM managers WHERE tg_id = ?", (tg_id,))
    exists = cursor.fetchone()

    conn.close()
    return exists is not None


# ======== SHOPS ========

def add_shop(name, address, menu: list, time_available, day_available, report_time, active=True):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO shops (name, address, menu, time_available, day_available, report_time, active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, address, json.dumps(menu), time_available, day_available, report_time, int(active)))

    conn.commit()
    conn.close()


def get_shops(active_only=True):
    conn = get_connection()
    cursor = conn.cursor()

    if active_only:
        cursor.execute("SELECT * FROM shops WHERE active = 1")
    else:
        cursor.execute("SELECT * FROM shops")

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_shop_by_id(shop_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
    row = cursor.fetchone()

    conn.close()
    return row