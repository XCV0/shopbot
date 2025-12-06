# handlers/users.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.db_controller import get_employee, get_shops, get_shop_by_id
import json

router = Router()

# локальное хранилище заказов (в будущем можно перенести в БД)
orders = {}


class OrderFSM(StatesGroup):
    choose_cafe = State()
    choose_items = State()
    confirm = State()


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = get_employee(message.from_user.id)
    if not user:
        await message.answer(
            "Вы не зарегистрированы в системе.\n"
            f"Ваш ID: {message.from_user.id}"
        )
        return

    kb = [
        [InlineKeyboardButton(text="🍽 Заказать еду", callback_data="create_order")],
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders_history")]
    ]

    await message.answer(f"Привет, {user[1]}! 👋\nВыбери действие:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data == "create_order")
async def create_order(callback: CallbackQuery, state: FSMContext):
    shops = get_shops(active_only=True)
    if not shops:
        await callback.message.edit_text("Сейчас нет доступных кафе.")
        return

    kb = [
        [InlineKeyboardButton(text=f"{s[1]} ({s[2]})", callback_data=f"cafe_{s[0]}")]
        for s in shops
    ]
    await callback.message.edit_text("Выберите кафе:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(OrderFSM.choose_cafe)


@router.callback_query(OrderFSM.choose_cafe, F.data.startswith("cafe_"))
async def choose_cafe(callback: CallbackQuery, state: FSMContext):
    cafe_id = int(callback.data.replace("cafe_", ""))
    shop = get_shop_by_id(cafe_id)
    if not shop or shop[7] != 1:
        await callback.answer("Это кафе сейчас недоступно.", show_alert=True)
        return

    try:
        menu = json.loads(shop[3]) if shop[3] else []
    except:
        menu = []

    if not menu:
        await callback.message.edit_text("В этом кафе пока нет меню.")
        return

    await state.update_data(cafe_id=cafe_id, items=[])
    kb = [
        [InlineKeyboardButton(text=f"{item['title']} — {item['price']}₽", callback_data=f"add_{idx}")]
        for idx, item in enumerate(menu)
    ]
    kb.append([InlineKeyboardButton(text="Готово", callback_data="finish_select")])
    await callback.message.edit_text(f"Меню — {shop[1]}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(OrderFSM.choose_items)


@router.callback_query(OrderFSM.choose_items, F.data.startswith("add_"))
async def add_item(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.replace("add_", ""))
    data = await state.get_data()
    items = data.get("items", [])
    items.append(idx)
    await state.update_data(items=items)
    await callback.answer("Добавлено!")


@router.callback_query(OrderFSM.choose_items, F.data == "finish_select")
async def finish_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    shop = get_shop_by_id(data["cafe_id"])
    try:
        menu = json.loads(shop[3]) if shop[3] else []
    except:
        menu = []

    if not data.get("items"):
        await callback.answer("Вы не выбрали блюда!", show_alert=True)
        return

    text = f"Ваш заказ из {shop[1]}:\n\n"
    total = 0
    for idx in data["items"]:
        item = menu[idx]
        text += f"• {item['title']} — {item['price']}₽\n"
        total += item["price"]
    text += f"\nИтого: {total}₽"

    kb = [
        [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_order")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_order")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(OrderFSM.confirm)


@router.callback_query(OrderFSM.confirm, F.data == "confirm_order")
async def confirm(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    orders.setdefault(user_id, []).append(data)
    await state.clear()
    await callback.message.edit_text("🎉 Заказ оформлен! Спасибо.")


@router.callback_query(OrderFSM.confirm, F.data == "cancel_order")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменён.")


@router.callback_query(F.data == "orders_history")
async def order_history(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_orders = orders.get(user_id, [])
    if not user_orders:
        await callback.message.edit_text("У вас нет заказов.")
        return

    text = "📦 История заказов:\n\n"
    for idx, order in enumerate(user_orders, start=1):
        shop = get_shop_by_id(order["cafe_id"])
        try:
            menu = json.loads(shop[3]) if shop[3] else []
        except:
            menu = []
        text += f"#{idx} — {shop[1]}\n"
        for i in order["items"]:
            it = menu[i]
            text += f"• {it['title']} ({it['price']}₽)\n"
        text += "\n"
    await callback.message.edit_text(text)
