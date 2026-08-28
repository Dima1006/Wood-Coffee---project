from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def yes_no_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Yes", callback_data="yes"),
                InlineKeyboardButton(text="No", callback_data="no")
            ]
        ]
    )


def order_status_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Arrived", callback_data=f"order:{order_id}:arrived"),
                InlineKeyboardButton(text="🟨 No show", callback_data=f"order:{order_id}:no_show"),
            ]
        ]
    )
