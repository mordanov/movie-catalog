from aiogram.fsm.state import State, StatesGroup


class AddMedia(StatesGroup):
    waiting_title = State()
    showing_candidates = State()
    confirming_category = State()
    confirming_add = State()


class EditMedia(StatesGroup):
    choosing_field = State()
    entering_value = State()


class DeleteConfirm(StatesGroup):
    confirming = State()
