from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def yes_no_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Так ✅", callback_data="confirm_yes")
    builder.button(text="Ні ❌", callback_data="confirm_no")
    return builder.as_markup()

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🥤 Напій")
    builder.button(text="🍰 Десерт")
    builder.button(text="📜 Мої замовлення")
    builder.button(text="🛒 Кошик")
    builder.button(text="🏠 На головну")
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def get_cart_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="💳 Оплатити")
    builder.button(text="Додати ще ➕")
    builder.button(text="⬅️ Назад")
    builder.button(text="🏠 На головну")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_place_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🥡 Із собою")
    builder.button(text="☕ У закладі")
    builder.button(text="⬅️ Назад")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_vertical_kb(items):
    builder = ReplyKeyboardBuilder()
    for item in items:
        builder.button(text=str(item))

    # Додаємо кнопки лише якщо їх ще немає в списку items
    if "⬅️ Назад" not in items:
        builder.button(text="⬅️ Назад")
    if "🏠 На головну" not in items:
        builder.button(text="🏠 На головну")

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)