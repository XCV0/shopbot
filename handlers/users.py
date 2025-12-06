# handlers/users.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.db_controller import get_employee, get_shops, get_shop_by_id, add_order, get_orders_by_user, delete_order
import json

router = Router()


class OrderFSM(StatesGroup):
    choose_cafe = State()
    choose_items = State()
    confirm = State()


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = get_employee(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы в системе.\nВаш ID: {}".format(message.from_user.id))
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

    kb = [[InlineKeyboardButton(text=f"{s[1]} ({s[2]})", callback_data=f"cafe_{s[0]}")] for s in shops]
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
    kb = [[InlineKeyboardButton(text=f"{item['title']} — {item['price']}₽", callback_data=f"add_{idx}")] for idx, item in enumerate(menu)]
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
    cafe_id = data.get("cafe_id")
    idxs = data.get("items", [])

    shop = get_shop_by_id(cafe_id)
    try:
        menu = json.loads(shop[3]) if shop[3] else []
    except:
        menu = []

    if not idxs:
        await callback.answer("Вы не выбрали блюда!", show_alert=True)
        return

    items_snapshot = []
    total = 0
    text = f"Ваш заказ из {shop[1]}:\n\n"
    for idx in idxs:
        if idx < 0 or idx >= len(menu):
            continue
        it = menu[idx]
        items_snapshot.append({"title": it.get("title"), "price": it.get("price")})
        text += f"• {it.get('title')} — {it.get('price')}₽\n"
        total += it.get("price", 0)
    text += f"\nИтого: {total}₽"

    await state.update_data(items_snapshot=items_snapshot)
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
    cafe_id = data.get("cafe_id")
    items_snapshot = data.get("items_snapshot", [])
    if not cafe_id or not items_snapshot:
        await callback.message.edit_text("Ошибка — данные заказа потеряны. Попробуйте ещё раз.")
        await state.clear()
        return

    add_order(user_id=user_id, shop_id=cafe_id, items=items_snapshot)
    await state.clear()
    await callback.message.edit_text("🎉 Заказ сохранён! Спасибо.")


@router.callback_query(OrderFSM.confirm, F.data == "cancel_order")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменён.")


@router.callback_query(F.data == "orders_history")
async def order_history(callback: CallbackQuery):
    user_id = callback.from_user.id
    orders = get_orders_by_user(user_id)
    if not orders:
        await callback.message.edit_text("У вас нет заказов.")
        return

    text = "📦 Ваши заказы:\n\n"
    kb = []
    for ord_row in orders:
        order_id, user_id, shop_id, items_raw, created_at = ord_row
        shop = get_shop_by_id(shop_id)
        shop_name = shop[1] if shop else "Кафе удалено"
        try:
            items = json.loads(items_raw)
        except:
            items = []
        text += f"#{order_id} — {shop_name} ({created_at}):\n"
        for it in items:
            text += f"• {it.get('title')} — {it.get('price')}₽\n"
        text += "\n"
        kb.append([InlineKeyboardButton(text=f"Отменить #{order_id}", callback_data=f"cancel_order_{order_id}")])

    kb.append([InlineKeyboardButton(text="Назад", callback_data="back_to_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.regexp(r"^cancel_order_\d+$"))
async def cancel_order(callback: CallbackQuery):
    user_id = callback.from_user.id
    order_id = int(callback.data.replace("cancel_order_", ""))
    ok = delete_order(order_id, user_id)
    if ok:
        await callback.message.edit_text(f"✅ Заказ #{order_id} отменён.")
    else:
        await callback.message.edit_text("❌ Не удалось отменить заказ (возможно он уже был удалён или не ваш).")
