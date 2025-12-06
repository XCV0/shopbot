# db/db_controller.py

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "restaurant.db"


def get_connection():
    # Enforce row factory if needed later
    conn = sqlite3.connect(DB_PATH)
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        tg_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        office TEXT NOT NULL,
        ecard TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS managers (
        tg_id INTEGER PRIMARY KEY
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        menu TEXT,
        time_available TEXT,
        day_available TEXT,
        report_time TEXT,
        active INTEGER NOT NULL DEFAULT 1
    );
    """)

    conn.commit()
    conn.close()


# ========= EMPLOYEES =========

def checker(tg_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM employees WHERE tg_id = ?", (tg_id,))
    exists = cursor.fetchone()
    conn.close()
    return exists is not None


def add_employee(tg_id: int, name: str, office: str, ecard: str) -> bool:
    if checker(tg_id):
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO employees (tg_id, name, office, ecard)
        VALUES (?, ?, ?, ?)
    """, (tg_id, name, office, ecard))
    conn.commit()
    conn.close()
    return True


def get_employee(tg_id: int) -> Optional[tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE tg_id = ?", (tg_id,))
    row = cursor.fetchone()
    conn.close()
    return row


# ========= MANAGERS =========

def add_manager(tg_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO managers (tg_id) VALUES (?)", (tg_id,))
    conn.commit()
    conn.close()


def is_manager(tg_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM managers WHERE tg_id = ?", (tg_id,))
    exists = cursor.fetchone()
    conn.close()
    return exists is not None


# ========= SHOPS & MENU HELPERS =========

def _parse_menu(raw: Optional[str]) -> List[Dict]:
    if not raw:
        return []
    try:
        menu = json.loads(raw)
        if isinstance(menu, list):
            return menu
    except:
        pass
    return []


def add_shop(name: str, address: str, menu: List[Dict], time_available: str, day_available: str, report_time: str, active: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO shops (name, address, menu, time_available, day_available, report_time, active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, address, json.dumps(menu), time_available, day_available, report_time, int(active)))
    conn.commit()
    conn.close()


def get_shops(active_only: bool = True) -> List[tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM shops WHERE active = 1")
    else:
        cursor.execute("SELECT * FROM shops")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_shop_by_id(shop_id: int) -> Optional[tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def set_shop_active(shop_id: int, active: bool) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE shops SET active = ? WHERE id = ?", (int(active), shop_id))
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def add_item_to_shop(shop_id: int, title: str, price: float) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT menu FROM shops WHERE id = ?", (shop_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False
    menu = _parse_menu(row[0])
    menu.append({"title": title, "price": float(price)})
    cursor.execute("UPDATE shops SET menu = ? WHERE id = ?", (json.dumps(menu), shop_id))
    conn.commit()
    conn.close()
    return True


def remove_item_from_shop(shop_id: int, item_index: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT menu FROM shops WHERE id = ?", (shop_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False
    menu = _parse_menu(row[0])
    if item_index < 0 or item_index >= len(menu):
        conn.close()
        return False
    menu.pop(item_index)
    cursor.execute("UPDATE shops SET menu = ? WHERE id = ?", (json.dumps(menu), shop_id))
    conn.commit()
    conn.close()
    return True
