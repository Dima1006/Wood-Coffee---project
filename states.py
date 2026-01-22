from aiogram.fsm.state import StatesGroup, State

class OrderState(StatesGroup):
    registering = State()          # Для первого ввода ФИО
    choosing_category = State()
    choosing_sub_category = State()
    choosing_item = State()
    choosing_size = State()
    choosing_quantity = State()
    choosing_payment = State()
    choosing_time = State()

class BaristaStates(StatesGroup):
    waiting_for_rejection_reason = State()  # Ожидание причины отмены