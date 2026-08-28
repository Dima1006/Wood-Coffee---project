import sqlite3

conn = sqlite3.connect("coffee.db")
cursor = conn.cursor()

# Create the shopping cart table.
cursor.execute("""
CREATE TABLE IF NOT EXISTS cart (
    user_id INTEGER,
    item_name TEXT,
    size TEXT,
    price INTEGER
)
""")
conn.commit()

def add_to_cart(user_id, item_name, size, price):
    cursor.execute("INSERT INTO cart VALUES (?, ?, ?, ?)", (user_id, item_name, size, price))
    conn.commit()

def get_cart(user_id):
    cursor.execute("SELECT item_name, size, price FROM cart WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def clear_cart(user_id):
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
