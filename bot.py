import pytz
import asyncio
import logging
import re
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# Імпорти ваших модулів
from config import BOT_TOKEN, STAFF_IDS
from menu import COFFEE, TEA, MILK_DRINK, DESSERTS
from states import OrderState, BaristaStates
from keyboards import yes_no_kb, get_main_menu, get_vertical_kb, get_cart_kb, get_place_kb
from database import init_db, add_user, get_user_name, save_order, get_user_history, get_order_by_id

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

init_db()
KYIV_TZ = pytz.timezone('Europe/Kyiv')


# --- ДОПОМІЖНІ ФУНКЦІЇ ---

def get_repeat_choice_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="➕ Додати ще щось"))
    builder.row(types.KeyboardButton(text="💳 Оформити замовлення"))
    builder.row(types.KeyboardButton(text="🏠 На головну"))
    return builder.as_markup(resize_keyboard=True)


def is_cafe_open():
    now = datetime.now(KYIV_TZ)
    current_hour = now.hour
    weekday = now.weekday()
    if weekday == 6: return 9 <= current_hour < 20
    return 8 <= current_hour < 20


def parse_order_details_to_cart(details: str):
    """Парсить текст замовлення та шукає актуальні ціни в меню"""
    new_cart = []
    lines = details.strip().split('\n')

    for line in lines:
        match = re.search(r"-\s+(.+?)\s+\((.+?)\)\s+x(\d+)", line.strip())
        if not match:
            match = re.search(r"-\s+(.+?)\s+x(\d+)", line.strip())
            if not match: continue
            name = match.group(1).strip()
            size = "—"
            qty = int(match.group(2))
        else:
            name = match.group(1).strip()
            size = match.group(2).strip()
            qty = int(match.group(3))

        price_per_one = 0
        if name in DESSERTS:
            price_per_one = DESSERTS[name]
        elif name in COFFEE:
            price_per_one = COFFEE[name].get(size, 0)
        elif name in TEA:
            price_per_one = TEA[name].get(size, 0)
        elif name in MILK_DRINK:
            price_per_one = MILK_DRINK[name].get(size, 0)

        new_cart.append({
            "name": name,
            "size": size,
            "qty": qty,
            "price": price_per_one * qty
        })
    return new_cart


COUNTER_FILE = "order_number.txt"


def get_next_order_number():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f: f.write("1")
        return 1
    with open(COUNTER_FILE, "r") as f:
        try:
            current = int(f.read().strip())
        except:
            current = 1
    next_num = 1 if current >= 50 else current + 1
    with open(COUNTER_FILE, "w") as f:
        f.write(str(next_num))
    return current


# --- РЕЄСТРАЦІЯ ТА ГОЛОВНЕ МЕНЮ ---

BAD_WORDS = ["хуй", "пизда", "админ", "eblan", "dura"]


def is_bad_name(text: str) -> bool:
    text = text.lower()
    return any(word in text for word in BAD_WORDS)


@dp.message(Command("start"), StateFilter("*"))
@dp.message(F.text == "🏠 На головну", StateFilter("*"))
async def start(message: types.Message, state: FSMContext):
    if not is_cafe_open():
        await message.answer("🌙 Вибачте, кав'ярня зараз зачинена.")
        return
    user_name = get_user_name(message.from_user.id)
    if not user_name:
        await message.answer("👋 Вітаємо! Введіть ваше Прізвище та Ім'я:")
        await state.set_state(OrderState.registering)
    else:
        data = await state.get_data()
        cart = data.get("cart", [])
        await state.clear()
        await state.update_data(cart=cart)
        await message.answer(f"☕ Вітаємо, {user_name}!", reply_markup=get_main_menu())
        await state.set_state(OrderState.choosing_category)


@dp.message(OrderState.registering)
async def register(message: types.Message, state: FSMContext):
    if len(message.text.split()) < 2:
        await message.answer("❌ Введіть, будь ласка, і Прізвище, і Ім'я.")
        return
    if is_bad_name(message.text):
        await message.answer("❌ Будь ласка, вкажіть коректне ім'я.")
        return
    add_user(message.from_user.id, message.text, message.from_user.username)
    await message.answer(f"Приємно познайомитись, {message.text}!", reply_markup=get_main_menu())
    await state.set_state(OrderState.choosing_category)


# --- УНІВЕРСАЛЬНИЙ ОБРОБНИК "ДОДАТИ ЩЕ" ---

@dp.message(F.text.in_(["Додати ще ➕", "➕ Додати ще щось"]), StateFilter("*"))
async def universal_add_more(message: types.Message, state: FSMContext):
    await state.set_state(OrderState.choosing_category)
    await message.answer("🛒 Кошик збережено. Оберіть категорію:", reply_markup=get_main_menu())


# --- ЛОГІКА НАЗАД (ВИПРАВЛЕНО) ---

@dp.message(F.text == "⬅️ Назад", StateFilter("*"))
async def back_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()

    if current_state == OrderState.choosing_sub_category:
        await state.set_state(OrderState.choosing_category)
        await message.answer("Оберіть категорію:", reply_markup=get_main_menu())

    elif current_state == OrderState.choosing_item:
        await drink_cats(message, state)

    elif current_state in [OrderState.choosing_size, OrderState.choosing_quantity]:
        cat = data.get("current_cat")
        menu_items = {"COFFEE": COFFEE, "TEA": TEA, "MILK_DRINK": MILK_DRINK, "DESSERTS": DESSERTS}
        if cat in menu_items:
            await message.answer("Оберіть товар:", reply_markup=get_vertical_kb(list(menu_items[cat].keys())))
            await state.set_state(OrderState.choosing_item)
        else:
            await state.set_state(OrderState.choosing_category)
            await message.answer("Оберіть категорію:", reply_markup=get_main_menu())

    elif current_state == OrderState.choosing_time:
        await show_cart(message, state)

    elif current_state == OrderState.choosing_place:
        await pay_start(message, state)

    else:
        await state.set_state(OrderState.choosing_category)
        await message.answer("Повертаємось до вибору страв. Кошик збережено.", reply_markup=get_main_menu())


# --- ІСТОРІЯ ТА ПОВТОР ---

@dp.message(F.text == "📜 Мої замовлення", StateFilter("*"))
async def show_history(message: types.Message):
    history = get_user_history(message.from_user.id)
    if not history:
        await message.answer("💨 У вас ще немає замовлень.")
        return

    last = history[0]
    try:
        order_db_id = last[0]
        order_num = last[1]
        details = last[2]
        total_db = last[3]
        date_raw = last[4]

        if not total_db or total_db == 0:
            temp_cart = parse_order_details_to_cart(details)
            total = sum(item['price'] for item in temp_cart)
        else:
            total = total_db

        date_str = date_raw.split('.')[0] if isinstance(date_raw, str) else date_raw.strftime("%Y-%m-%d %H:%M")
        builder = InlineKeyboardBuilder()
        builder.button(text=f"🔄 Повторити №{order_num}", callback_data=f"repeat_{order_db_id}")

        msg = (
            f"📜 **Ваше останнє замовлення №{order_num}:**\n"
            f"🗓 Дата: {date_str}\n"
            f"------------------------\n"
            f"{details}\n"
            f"------------------------\n"
            f"💰 **Загальна сума: {total}₴**"
        )
        await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_history: {e}")
        await message.answer("❌ Помилка завантаження даних історії.")


@dp.callback_query(F.data.startswith("repeat_"))
async def repeat_order(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    result = get_order_by_id(order_id)
    if result and result[0]:
        details = result[0]
        temp_cart = parse_order_details_to_cart(details)
        if not temp_cart:
            await callback.message.answer("❌ Не вдалося знайти ціни на ці товари.")
            return
        total_sum = sum(item['price'] for item in temp_cart)
        await state.update_data(temp_repeat_cart=temp_cart)
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Так", callback_data="confirm_repeat_yes")
        builder.button(text="❌ Ні", callback_data="confirm_repeat_no")
        await callback.message.answer(
            f"🛒 **Бажаєте повторити це замовлення?**\n\n{details}\n\n💰 Поточна сума: **{total_sum}₴**",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer("❌ Замовлення не знайдено.")
    await callback.answer()


@dp.callback_query(F.data == "confirm_repeat_yes")
async def confirm_repeat_yes(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    temp_cart = data.get("temp_repeat_cart", [])
    if not temp_cart:
        await callback.message.answer("❌ Помилка кошика.")
        return
    current_cart = data.get("cart", [])
    current_cart.extend(temp_cart)
    await state.update_data(cart=current_cart)
    await callback.message.delete()
    await callback.message.answer("🛒 Товари додані в кошик!", reply_markup=get_repeat_choice_kb())
    await state.set_state(OrderState.choosing_category)
    await callback.answer()


@dp.callback_query(F.data == "confirm_repeat_no")
async def confirm_repeat_no(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer("Скасовано")


# --- КАТЕГОРІЇ ТА ВИБІР ТОВАРУ ---

@dp.message(OrderState.choosing_category, F.text == "🥤 Напій")
async def drink_cats(message: types.Message, state: FSMContext):
    await message.answer("Який напій?", reply_markup=get_vertical_kb(["Кава", "Чай", "Молочні напої"]))
    await state.set_state(OrderState.choosing_sub_category)


@dp.message(OrderState.choosing_category, F.text == "🍰 Десерт")
async def dessert_list(message: types.Message, state: FSMContext):
    await state.update_data(current_cat="DESSERTS")
    await message.answer("Оберіть десерт:", reply_markup=get_vertical_kb(list(DESSERTS.keys())))
    await state.set_state(OrderState.choosing_item)


@dp.message(OrderState.choosing_sub_category)
async def sub_cats(message: types.Message, state: FSMContext):
    menu_map = {"Кава": (COFFEE, "COFFEE"), "Чай": (TEA, "TEA"), "Молочні напої": (MILK_DRINK, "MILK_DRINK")}
    if message.text in menu_map:
        menu, cat_id = menu_map[message.text]
        await state.update_data(current_cat=cat_id)
        await message.answer("Меню:", reply_markup=get_vertical_kb(list(menu.keys())))
        await state.set_state(OrderState.choosing_item)


@dp.message(OrderState.choosing_item)
async def pick_item(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat = data.get('current_cat')
    menus = {"COFFEE": COFFEE, "TEA": TEA, "MILK_DRINK": MILK_DRINK, "DESSERTS": DESSERTS}
    if not cat or message.text not in menus[cat]: return
    await state.update_data(selected_item=message.text)
    if cat == "DESSERTS":
        await state.update_data(selected_size="—", selected_price=menus[cat][message.text])
        await message.answer("Кількість?", reply_markup=get_vertical_kb(["1", "2", "3", "4", "5"]))
        await state.set_state(OrderState.choosing_quantity)
    else:
        sizes = list(menus[cat][message.text].keys())
        await message.answer("Розмір:", reply_markup=get_vertical_kb(sizes))
        await state.set_state(OrderState.choosing_size)


@dp.message(OrderState.choosing_size)
async def pick_size(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat, item = data['current_cat'], data['selected_item']
    price = {"COFFEE": COFFEE, "TEA": TEA, "MILK_DRINK": MILK_DRINK}[cat][item][message.text]
    await state.update_data(selected_size=message.text, selected_price=price)
    await message.answer("Кількість?", reply_markup=get_vertical_kb(["1", "2", "3", "4", "5"]))
    await state.set_state(OrderState.choosing_quantity)


@dp.message(OrderState.choosing_quantity)
async def pick_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    qty = int(message.text)
    data = await state.get_data()
    total = data['selected_price'] * qty
    await state.update_data(selected_qty=qty, total_item_price=total)
    await message.answer(f"Додати {data['selected_item']} x{qty} за {total}₴?", reply_markup=yes_no_kb())


@dp.callback_query(F.data.startswith("confirm_"))
async def cart_confirm(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm_yes":
        data = await state.get_data()
        cart = data.get("cart", [])
        cart.append({"name": data['selected_item'], "size": data['selected_size'], "qty": data['selected_qty'],
                     "price": data['total_item_price']})
        await state.update_data(cart=cart)
        await callback.message.edit_text("✅ Додано!")
    await callback.message.answer("Оберіть категорію:", reply_markup=get_main_menu())
    await state.set_state(OrderState.choosing_category)
    await callback.answer()


# --- КОШИК ---

@dp.message(F.text == "🛒 Кошик", StateFilter("*"))
async def show_cart(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await message.answer("🛒 Кошик порожній", reply_markup=get_main_menu())
        return
    res = "🛒 **Кошик:**\n"
    total_sum = 0
    builder = InlineKeyboardBuilder()
    for idx, i in enumerate(cart):
        res += f"{idx + 1}. {i['name']} ({i['size']}) x{i['qty']} = {i['price']}₴\n"
        total_sum += i['price']
        builder.button(text=f"❌ {i['name']}", callback_data=f"del_{idx}")
    res += f"\n💰 Разом: {total_sum}₴"
    await message.answer(res, reply_markup=get_cart_kb(), parse_mode="Markdown")
    await message.answer("Видалити позицію?", reply_markup=builder.adjust(1).as_markup())


@dp.callback_query(F.data.startswith("del_"))
async def delete_item(callback: types.CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    data = await state.get_data()
    cart = data.get("cart", [])
    if idx < len(cart): cart.pop(idx); await state.update_data(cart=cart)
    await callback.answer("Видалено")
    await show_cart(callback.message, state)


# --- ОФОРМЛЕННЯ (ЧАС ТА МІСЦЕ) ---

@dp.message(F.text.in_(["💳 Оплатити", "💳 Оформити замовлення"]), StateFilter("*"))
async def pay_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("cart"): await message.answer("Кошик порожній!"); return
    await message.answer("⏰ Через скільки хвилин будете? (Напишіть число або оберіть)",
                         reply_markup=get_vertical_kb(["5", "10", "15", "20"]))
    await state.set_state(OrderState.choosing_time)


@dp.message(OrderState.choosing_time)
async def pick_time(message: types.Message, state: FSMContext):
    match = re.search(r'\d+', message.text)
    if not match:
        await message.answer("🔢 Введіть число хвилин!")
        return
    mins = int(match.group())
    await state.update_data(arrival_mins=mins)

    # ПЕРЕХІД ДО ВИБОРУ МІСЦЯ
    await message.answer("Де бажаєте випити каву?", reply_markup=get_place_kb())
    await state.set_state(OrderState.choosing_place)


@dp.message(OrderState.choosing_place)
async def finish_order(message: types.Message, state: FSMContext):
    if message.text not in ["🥡 Із собою", "☕ У закладі"]:
        await message.answer("Будь ласка, оберіть варіант на кнопках!")
        return

    data = await state.get_data()
    mins = data.get("arrival_mins", 10)
    arrival_time = (datetime.now(KYIV_TZ) + timedelta(minutes=mins)).strftime("%H:%M")
    cart = data.get("cart", [])
    order_id = get_next_order_number()

    items_text = "\n".join([f"- {i['name']} ({i['size']}) x{i['qty']}" for i in cart])
    total_sum = sum(i['price'] for i in cart)

    # Зберігаємо замовлення в базу
    save_order(message.from_user.id, order_id, items_text, total_sum)

    # Формуємо повідомлення для бариста (додаємо МІСЦЕ)
    admin_msg = (
        f"🔔 **ЗАМОВЛЕННЯ №{order_id}**\n"
        f"👤 {get_user_name(message.from_user.id)}\n"
        f"📍 **МІСЦЕ: {message.text}**\n"
        f"⏰ Орієнтовно о {arrival_time}\n\n"
        f"{items_text}\n"
        f"💰 {total_sum}₴"
    )

    admin_kb = InlineKeyboardBuilder()
    admin_kb.button(text="✅ Прийняти", callback_data=f"adm_accept_{message.from_user.id}_{order_id}_{mins}")
    admin_kb.button(text="❌ Відхилити", callback_data=f"adm_decline_{message.from_user.id}_{order_id}")

    for adm in STAFF_IDS:
        try:
            await bot.send_message(adm, admin_msg, reply_markup=admin_kb.as_markup())
        except:
            continue

    await message.answer(f"⏳ Замовлення №{order_id} надіслано! Буде готово о ~{arrival_time}",
                         reply_markup=get_main_menu())
    await state.clear()


# --- АДМІН-ДІЇ ТА ЗАГЛУШКА ---

@dp.callback_query(F.data.startswith("adm_"))
async def admin_action(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    action, client_id, order_num = parts[1], int(parts[2]), parts[3]
    if action == "accept":
        wait = parts[4]
        await bot.send_message(client_id, f"✅ №{order_num} підтверджено! Буде через {wait} хв.")
        await callback.message.edit_text(callback.message.text + "\n\n🟢 ПРИЙНЯТО")
    elif action == "decline":
        await state.update_data(rej_client_id=client_id, rej_order_num=order_num)
        await state.set_state(BaristaStates.waiting_for_rejection_reason)
        await callback.message.answer(f"Причина відмови для №{order_num}?")
    await callback.answer()


@dp.message(BaristaStates.waiting_for_rejection_reason)
async def rejection_reason(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await bot.send_message(data['rej_client_id'], f"❌ Замовлення №{data['rej_order_num']} відхилено: {message.text}")
    await message.answer("Клієнта повідомлено.")
    await state.clear()


@dp.message()
async def unknown_message(message: types.Message):
    await message.answer("🤔 Будь ласка, використовуйте кнопки меню.", reply_markup=get_main_menu())


async def main(): await dp.start_polling(bot)


if __name__ == "__main__": asyncio.run(main())