from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor

from config import BOT_TOKEN, STAFF_IDS
from menu import COFFEE, TEA, MILK_DRINK, DESSERTS
from states import OrderState
from keyboards import yes_no_kb
from cart import add_to_cart, clear_cart, get_cart, cart_total

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# ---------- Main menu ----------
def get_main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🥤 Drink", "🍰 Dessert")
    kb.add("🛒 Cart")
    return kb


# ---------- Start ----------
@dp.message_handler(commands=["start"], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    clear_cart(message.from_user.id)
    await message.answer(
        "☕ Welcome to Wood Coffee!\nChoose a category 👇",
        reply_markup=get_main_menu()
    )
    await OrderState.choosing_category.set()


# ---------- Categories ----------
@dp.message_handler(state=OrderState.choosing_category)
async def categories(message: types.Message, state: FSMContext):
    if message.text == "🥤 Drink":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("Coffee", "Tea", "Milk Drink", "⬅️ Back")
        await message.answer("Choose a drink:", reply_markup=kb)
        await OrderState.choosing_item.set()

    elif message.text == "🍰 Dessert":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for d, p in DESSERTS.items():
            kb.add(f"{d} — {p}₴")
        kb.add("⬅️ Back")
        await message.answer("Choose a dessert:", reply_markup=kb)
        await OrderState.choosing_item.set()

    elif message.text == "🛒 Cart":
        await show_cart(message)


# ---------- Item selection ----------
@dp.message_handler(state=OrderState.choosing_item)
async def pick_item(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Back":
        await message.answer("Main menu", reply_markup=get_main_menu())
        await OrderState.choosing_category.set()
        return

    menus = {
        "Coffee": COFFEE,
        "Tea": TEA,
        "Milk Drink": MILK_DRINK,
    }

    if message.text in menus:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for name in menus[message.text]:
            kb.add(name)
        kb.add("⬅️ Back")
        await message.answer("Choose an item:", reply_markup=kb)
        return

    all_drinks = {**COFFEE, **TEA, **MILK_DRINK}

    if message.text in all_drinks:
        await state.update_data(temp_name=message.text)
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for size in all_drinks[message.text]:
            kb.add(size)
        kb.add("⬅️ Back")
        await message.answer("Choose a size:", reply_markup=kb)
        await OrderState.choosing_size.set()
        return

    if " — " in message.text:
        name = message.text.split(" — ")[0]
        if name in DESSERTS:
            await state.update_data(
                temp_name=name,
                temp_size="—",
                temp_price=DESSERTS[name]
            )
            await message.answer(
                f"Add {name}?",
                reply_markup=yes_no_kb()
            )
            await OrderState.confirm_add.set()


# ---------- Size ----------
@dp.message_handler(state=OrderState.choosing_size)
async def pick_size(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["temp_name"]
    all_drinks = {**COFFEE, **TEA, **MILK_DRINK}

    if message.text not in all_drinks[name]:
        await message.answer("Choose a button 👇")
        return

    price = all_drinks[name][message.text]
    await state.update_data(temp_size=message.text, temp_price=price)

    await message.answer(
        f"{name} ({message.text}) — {price}₴\nAdd it?",
        reply_markup=yes_no_kb()
    )
    await OrderState.confirm_add.set()


# ---------- Confirmation ----------
@dp.callback_query_handler(state=OrderState.confirm_add)
async def confirm(call: types.CallbackQuery, state: FSMContext):
    if call.data == "yes":
        data = await state.get_data()
        add_to_cart(call.from_user.id, {
            "name": data["temp_name"],
            "size": data["temp_size"],
            "price": data["temp_price"]
        })
        await call.message.answer("✅ Added", reply_markup=get_main_menu())
    else:
        await call.message.answer("❌ Cancelled", reply_markup=get_main_menu())

    await call.answer()
    await OrderState.choosing_category.set()


# ---------- Cart ----------
async def show_cart(message: types.Message):
    cart = get_cart(message.from_user.id)

    if not cart:
        await message.answer("Your cart is empty 🕸")
        return

    text = "🛒 Your cart:\n\n"
    for i in cart:
        text += f"• {i['name']} ({i['size']}) — {i['price']}₴\n"
    text += f"\n💰 Total: {cart_total(message.from_user.id)}₴"

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💳 Pay", "⬅️ Back")

    await message.answer(text, reply_markup=kb)


# ---------- Payment ----------
@dp.message_handler(text="💳 Pay", state="*")
async def pay(message: types.Message, state: FSMContext):
    await message.answer("✅ Payment successful (test)")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 min", "10 min", "15 min")
    await OrderState.choosing_time.set()
    await message.answer("How many minutes until you arrive?", reply_markup=kb)


# ---------- Arrival time ----------
@dp.message_handler(state=OrderState.choosing_time)
async def time_handler(message: types.Message, state: FSMContext):
    try:
        minutes = int(message.text.split()[0])
    except:
        await message.answer("Choose a button")
        return

    arrival = (datetime.now() + timedelta(minutes=minutes)).strftime("%H:%M")
    cart = get_cart(message.from_user.id)

    order = "\n".join([f"- {i['name']} ({i['size']})" for i in cart])
    msg = f"🔔 NEW ORDER\n⏰ {arrival}\n\n{order}"

    for staff in STAFF_IDS:
        await bot.send_message(staff, msg)

    clear_cart(message.from_user.id)
    await state.finish()
    await message.answer(f"✅ We will be waiting for you at {arrival}", reply_markup=get_main_menu())


# ---------- Back ----------
@dp.message_handler(text="⬅️ Back", state="*")
async def back(message: types.Message, state: FSMContext):
    await OrderState.choosing_category.set()
    await message.answer("Main menu", reply_markup=get_main_menu())


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
