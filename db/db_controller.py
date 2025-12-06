import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "restaurant.db"


def get_connection():
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        shop_id INTEGER NOT NULL,
        items TEXT NOT NULL,
        created_at TEXT NOT NULL,
        delivery_type TEXT,
        comment TEXT
    );
    """)

    conn.commit()
    conn.close()


# Сотрудники
def checker(tg_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM employees WHERE tg_id = ?", (tg_id,))
    exists = cur.fetchone()
    conn.close()
    return exists is not None


def add_employee(tg_id: int, name: str, office: str, ecard: str) -> bool:
    if checker(tg_id):
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO employees (tg_id, name, office, ecard) VALUES (?, ?, ?, ?)",
        (tg_id, name, office, ecard)
    )
    conn.commit()
    conn.close()
    return True


def get_employee(tg_id: int) -> Optional[tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    return row


# Менеджеры
def add_manager(tg_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO managers (tg_id) VALUES (?)", (tg_id,))
    conn.commit()
    conn.close()


def is_manager(tg_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM managers WHERE tg_id = ?", (tg_id,))
    exists = cur.fetchone()
    conn.close()
    return exists is not None


def get_managers() -> List[int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT tg_id FROM managers")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


# Магазины и меню
def _parse_menu(raw: Optional[str]) -> List[Dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except:
        pass
    return []


def add_shop(
    name: str,
    address: str,
    menu: List[Dict],
    time_available: str,
    day_available: str,
    report_time: str,
    active: bool = True
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO shops (name, address, menu, time_available, day_available, report_time, active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            name,
            address,
            json.dumps(menu, ensure_ascii=False),
            time_available,
            day_available,
            report_time,
            int(active)
        )
    )
    shop_id = cur.lastrowid
    conn.commit()
    conn.close()
    return shop_id


def get_shops(active_only: bool = True) -> List[tuple]:
    conn = get_connection()
    cur = conn.cursor()
    if active_only:
        cur.execute("SELECT * FROM shops WHERE active = 1")
    else:
        cur.execute("SELECT * FROM shops")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_shop_by_id(shop_id: int) -> Optional[tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
    row = cur.fetchone()
    conn.close()
    return row


def set_shop_active(shop_id: int, active: bool) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE shops SET active = ? WHERE id = ?", (int(active), shop_id))
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def delete_shop(shop_id: int) -> bool:
    """
    Полное удаление кафе:
      - удаляем все заказы по этому кафе
      - удаляем сам кафе из таблицы shops
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM orders WHERE shop_id = ?", (shop_id,))
    cur.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def add_item_to_shop(shop_id: int, title: str, price: float) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT menu FROM shops WHERE id = ?", (shop_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return False
    menu = _parse_menu(row[0])
    menu.append({"title": str(title), "price": float(price)})
    cur.execute(
        "UPDATE shops SET menu = ? WHERE id = ?",
        (json.dumps(menu, ensure_ascii=False), shop_id)
    )
    conn.commit()
    conn.close()
    return True


def remove_item_from_shop(shop_id: int, item_index: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT menu FROM shops WHERE id = ?", (shop_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return False
    menu = _parse_menu(row[0])
    if item_index < 0 or item_index >= len(menu):
        conn.close()
        return False
    menu.pop(item_index)
    cur.execute(
        "UPDATE shops SET menu = ? WHERE id = ?",
        (json.dumps(menu, ensure_ascii=False), shop_id)
    )
    conn.commit()
    conn.close()
    return True


# Заказы
def add_order(
    user_id: int,
    shop_id: int,
    items: List[Dict],
    delivery_type: Optional[str] = None,
    comment: Optional[str] = None
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (user_id, shop_id, items, created_at, delivery_type, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            shop_id,
            json.dumps(items, ensure_ascii=False),
            datetime.now().isoformat(),
            delivery_type,
            comment,
        )
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_orders_by_shop(shop_id: int) -> List[tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, shop_id, items, created_at, delivery_type, comment "
        "FROM orders WHERE shop_id = ?",
        (shop_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_orders_by_user(user_id: int) -> List[tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, shop_id, items, created_at, delivery_type, comment "
        "FROM orders WHERE user_id = ?",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_order(order_id: int, user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def clear_orders_for_shop(shop_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM orders WHERE shop_id = ?", (shop_id,))
    conn.commit()
    conn.close()
