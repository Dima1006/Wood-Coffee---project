from aiogram.dispatcher.filters.state import State, StatesGroup

class OrderState(StatesGroup):
    choosing_category = State()
    choosing_item = State()
    choosing_size = State()
    confirm_add = State()
    choosing_time = State()
