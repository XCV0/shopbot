from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()

# ====== ВРЕМЕННЫЕ ДАННЫЕ ======
available_employees = [5201148794, 837411435]

cafes = {
    "cafe1": {
        "name": "Кафе №1",
        "menu": [
            {"id": "1", "title": "Борщ", "price": 150},
            {"id": "2", "title": "Котлета с пюре", "price": 250},
            {"id": "3", "title": "Салат Цезарь", "price": 230}
        ]
    },
    "cafe2": {
        "name": "Итальянское меню",
        "menu": [
            {"id": "4", "title": "Пицца Маргарита", "price": 450},
            {"id": "5", "title": "Паста Болоньезе", "price": 390}
        ]
    }
}

# Локальное хранилище заказов (вместо базы)
orders = {}

# ====== FSM ======
class OrderFSM(StatesGroup):
    choose_cafe = State()
    choose_items = State()
    confirm = State()


# ========= START ==========
@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id not in available_employees:
        await message.answer(
            "Вы не добавлены в список пользователей!\n"
            f"Ваш ID: {message.from_user.id}"
        )
        return

    kb = [[InlineKeyboardButton(text="Заказать еду", callback_data="create_order")],
          [InlineKeyboardButton(text="Мои заказы", callback_data="orders_history")]]

    await message.answer(
        "Привет! Я помогу тебе заказать обед.\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


# ========= CALLBACK ROOT ==========
@router.callback_query(F.data == "create_order")
async def create_order(callback: CallbackQuery, state: FSMContext):

    kb = [
        [InlineKeyboardButton(
            text=cafes[cafe_id]["name"],
            callback_data=f"cafe_{cafe_id}")
        ]
        for cafe_id in cafes
    ]

    await callback.message.edit_text(
        "Выбери кафе:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(OrderFSM.choose_cafe)


# ========= ВЫБОР КАФЕ ==========
@router.callback_query(OrderFSM.choose_cafe, F.data.startswith("cafe_"))
async def choose_cafe(callback: CallbackQuery, state: FSMContext):
    cafe_id = callback.data.replace("cafe_", "")

    await state.update_data(cafe=cafe_id, items=[])

    # Показываем меню
    menu = cafes[cafe_id]["menu"]

    kb = [
        [InlineKeyboardButton(
            text=f"{item['title']} — {item['price']}₽",
            callback_data=f"add_{item['id']}")
        ]
        for item in menu
    ]

    kb.append([InlineKeyboardButton(text="Готово", callback_data="finish_select")])

    await callback.message.edit_text(
        f"Меню ({cafes[cafe_id]['name']}):\nВыбери блюда:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(OrderFSM.choose_items)


# ========= ДОБАВЛЕНИЕ БЛЮД ==========
@router.callback_query(OrderFSM.choose_items, F.data.startswith("add_"))
async def add_item(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.replace("add_", "")

    data = await state.get_data()
    items = data.get("items", [])
    items.append(item_id)

    await state.update_data(items=items)

    await callback.answer("Добавлено!", show_alert=True)


# ========= ЗАВЕРШЕНИЕ ВЫБОРА ==========
@router.callback_query(OrderFSM.choose_items, F.data == "finish_select")
async def finish_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cafe_id = data["cafe"]
    items = data["items"]

    if not items:
        await callback.answer("Вы не выбрали блюда!", show_alert=True)
        return

    menu = cafes[cafe_id]["menu"]
    items_info = [next(i for i in menu if i["id"] == item_id) for item_id in items]

    text = "Ваш заказ:\n"
    total = 0
    for item in items_info:
        text += f"• {item['title']} — {item['price']}₽\n"
        total += item["price"]
    text += f"\nИтого: {total}₽"

    kb = [
        [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_order")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_order")]
    ]

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(OrderFSM.confirm)


# ========= ПОДТВЕРЖДЕНИЕ ==========
@router.callback_query(OrderFSM.confirm, F.data == "confirm_order")
async def confirm(callback: CallbackQuery, state: FSMContext):

    user_id = callback.from_user.id
    data = await state.get_data()

    # Сохраняем в локальный список заказов
    orders.setdefault(user_id, []).append(data)

    await state.clear()

    await callback.message.edit_text("Заказ оформлен! Спасибо 😊")


# ========= ОТМЕНА ==========
@router.callback_query(OrderFSM.confirm, F.data == "cancel_order")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Заказ отменён.")


# ========= ИСТОРИЯ ЗАКАЗОВ ==========
@router.callback_query(F.data == "orders_history")
async def order_history(callback: CallbackQuery):

    user_id = callback.from_user.id
    user_orders = orders.get(user_id, [])

    if not user_orders:
        await callback.message.edit_text("У вас пока нет заказов.")
        return

    text = "История заказов:\n\n"
    for idx, order in enumerate(user_orders, start=1):
        cafe_name = cafes[order["cafe"]]["name"]
        menu = cafes[order["cafe"]]["menu"]

        items_info = [
            next(i for i in menu if i["id"] == item_id)
            for item_id in order["items"]
        ]

        text += f"#{idx} — {cafe_name}\n"
        for item in items_info:
            text += f"  • {item['title']} ({item['price']}₽)\n"
        text += "\n"

    await callback.message.edit_text(text)
