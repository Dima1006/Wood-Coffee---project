from typing import Dict, List, Optional

user_carts: Dict[int, List[dict]] = {}

def add_to_cart(user_id: int, item: dict):
    user_carts.setdefault(user_id, []).append(item)

def clear_cart(user_id: int):
    user_carts[user_id] = []

def get_cart(user_id: int):
    return user_carts.get(user_id, [])

def cart_total(user_id: int):
    return sum(item["price"] for item in get_cart(user_id))

def remove_from_cart(user_id: int, index: int) -> Optional[dict]:
    cart = get_cart(user_id)
    if not 0 <= index < len(cart):
        return None
    return cart.pop(index)
