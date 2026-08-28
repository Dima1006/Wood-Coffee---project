import tempfile
import unittest
from pathlib import Path

from db import PAYMENT_ON_ARRIVAL, PAYMENT_ONLINE, OrderStorage


class OrderStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = OrderStorage(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.storage.close()
        self.temp_dir.cleanup()

    def create_order(self, payment_method=PAYMENT_ON_ARRIVAL):
        return self.storage.create_order(
            user_id=42,
            items=[{"name": "Latte", "size": "Medium", "price": 85}],
            total=85,
            payment_method=payment_method,
            arrival_time="12:30",
        )

    def test_second_no_show_blocks_customer(self):
        self.assertEqual(self.storage.mark_no_show(self.create_order()), (1, False))
        self.assertEqual(self.storage.mark_no_show(self.create_order()), (2, True))
        self.assertTrue(self.storage.is_customer_blocked(42))

    def test_processed_order_cannot_create_another_warning(self):
        order_id = self.create_order()
        self.storage.mark_no_show(order_id)
        self.assertIsNone(self.storage.mark_no_show(order_id))

    def test_online_order_cannot_create_a_warning(self):
        self.assertIsNone(self.storage.mark_no_show(self.create_order(PAYMENT_ONLINE)))
        self.assertFalse(self.storage.is_customer_blocked(42))

    def test_arrived_order_is_not_processed_twice(self):
        order_id = self.create_order()
        self.assertTrue(self.storage.mark_arrived(order_id))
        self.assertFalse(self.storage.mark_arrived(order_id))

    def test_unblock_resets_warnings(self):
        self.storage.mark_no_show(self.create_order())
        self.storage.mark_no_show(self.create_order())
        self.storage.unblock_customer(42)
        self.assertFalse(self.storage.is_customer_blocked(42))
        self.assertEqual(self.storage.mark_no_show(self.create_order()), (1, False))


if __name__ == "__main__":
    unittest.main()
