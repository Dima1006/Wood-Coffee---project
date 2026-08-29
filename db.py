import json
import sqlite3
from pathlib import Path
from typing import Any, Optional


PAYMENT_ONLINE = "online_test"
PAYMENT_ON_ARRIVAL = "pay_on_arrival"
PENDING = "pending"
ARRIVED = "arrived"
NO_SHOW = "no_show"


class OrderStorage:
    def __init__(self, database_path: str | Path = "coffee.db"):
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            user_id INTEGER PRIMARY KEY,
            warning_count INTEGER NOT NULL DEFAULT 0,
            is_blocked INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            items TEXT NOT NULL,
            total INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            branch TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        order_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(orders)")
        }
        if "branch" not in order_columns:
            self.connection.execute(
                "ALTER TABLE orders ADD COLUMN branch TEXT NOT NULL DEFAULT ''"
            )
        self.connection.commit()

    def create_order(
        self,
        user_id: int,
        items: list[dict[str, Any]],
        total: int,
        payment_method: str,
        arrival_time: str,
        branch: str,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO orders (user_id, items, total, payment_method, arrival_time, branch)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, json.dumps(items), total, payment_method, arrival_time, branch),
        )
        self.connection.commit()
        return cursor.lastrowid

    def is_customer_blocked(self, user_id: int) -> bool:
        row = self.connection.execute(
            "SELECT is_blocked FROM customers WHERE user_id = ?", (user_id,)
        ).fetchone()
        return bool(row and row["is_blocked"])

    def mark_arrived(self, order_id: int) -> bool:
        cursor = self.connection.execute(
            "UPDATE orders SET status = ? WHERE id = ? AND status = ?",
            (ARRIVED, order_id, PENDING),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def get_order_customer_id(self, order_id: int) -> Optional[int]:
        row = self.connection.execute(
            "SELECT user_id FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        return row["user_id"] if row else None

    def get_order_branch(self, order_id: int) -> Optional[str]:
        row = self.connection.execute(
            "SELECT branch FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        return row["branch"] if row else None

    def mark_no_show(self, order_id: int) -> Optional[tuple[int, bool]]:
        with self.connection:
            order = self.connection.execute(
                "SELECT user_id, payment_method, status FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            if not order or order["status"] != PENDING or order["payment_method"] != PAYMENT_ON_ARRIVAL:
                return None

            cursor = self.connection.execute(
                "UPDATE orders SET status = ? WHERE id = ? AND status = ?",
                (NO_SHOW, order_id, PENDING),
            )
            if cursor.rowcount != 1:
                return None
            self.connection.execute(
                "INSERT OR IGNORE INTO customers (user_id) VALUES (?)", (order["user_id"],)
            )
            self.connection.execute(
                """
                UPDATE customers
                SET warning_count = warning_count + 1,
                    is_blocked = CASE WHEN warning_count + 1 >= 2 THEN 1 ELSE is_blocked END
                WHERE user_id = ?
                """,
                (order["user_id"],),
            )
            customer = self.connection.execute(
                "SELECT warning_count, is_blocked FROM customers WHERE user_id = ?", (order["user_id"],)
            ).fetchone()
            return customer["warning_count"], bool(customer["is_blocked"])

    def unblock_customer(self, user_id: int) -> None:
        self.connection.execute(
            """
            INSERT INTO customers (user_id, warning_count, is_blocked)
            VALUES (?, 0, 0)
            ON CONFLICT(user_id) DO UPDATE SET warning_count = 0, is_blocked = 0
            """,
            (user_id,),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


storage = OrderStorage(Path(__file__).with_name("coffee.db"))
