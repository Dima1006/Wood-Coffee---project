import sqlite3
import pytz
from datetime import datetime, timedelta

# Часовий пояс для всіх дат
KYIV_TZ = pytz.timezone('Europe/Kyiv')


def init_db():
    conn = sqlite3.connect('coffee_shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_number INTEGER,
            details TEXT,
            total_sum INTEGER,
            status TEXT,
            date TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def add_user(user_id, full_name, username):
    conn = sqlite3.connect('coffee_shop.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, full_name, username) VALUES (?, ?, ?)',
                   (user_id, full_name, username))
    conn.commit()
    conn.close()


def get_user_name(user_id):
    conn = sqlite3.connect('coffee_shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT full_name FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None


def get_user_history(user_id):
    conn = sqlite3.connect('coffee_shop.db')
    cursor = conn.cursor()

    now_kyiv = datetime.now(KYIV_TZ)
    start_of_week = (now_kyiv - timedelta(days=now_kyiv.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date_str = start_of_week.strftime('%Y-%m-%d %H:%M:%S')

    # Порядок стовпців: id(0), number(1), details(2), total(3), date(4)
    cursor.execute('''
        SELECT id, order_number, details, total_sum, date
        FROM orders 
        WHERE user_id = ? AND date >= ?
        ORDER BY date DESC
    ''', (user_id, start_date_str))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_order_by_id(order_id):
    conn = sqlite3.connect('coffee_shop.db')
    cursor = conn.cursor()
    # Повертаємо і текст, і підсумок замовлення
    cursor.execute('SELECT details, total_sum FROM orders WHERE id = ?', (order_id,))
    res = cursor.fetchone()
    conn.close()
    return res if res else (None, 0)


def save_order(user_id, order_num, details, total):
    # Фіксуємо час Києва перед збереженням
    kyiv_now = datetime.now(KYIV_TZ).strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect('coffee_shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (user_id, order_number, details, total_sum, status, date) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, order_num, details, total, 'pending', kyiv_now))
    conn.commit()
    conn.close()