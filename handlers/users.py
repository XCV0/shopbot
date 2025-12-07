import os
import json
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from pytz import timezone

from db.db_controller import (
    get_employee,
    get_shops,
    get_shop_by_id,
    add_order,
    get_orders_by_user,
    delete_order,
    add_employee
)
# РЕЖИМ ПРЕЗЕНТАЦИИ, ОТВЕЧАЕТ ВСЕМ ПОЛЬЗОВАТЕЛЯМ
PRESENTATION_MODE = False
# URL tg app
WEBAPP_URL = "https://ixipa.ru/"

router = Router()



MSK_TZ = timezone("Europe/Moscow")


class OrderFSM(StatesGroup):
    choose_cafe = State()
    choose_items = State()
    confirm = State()


def is_shop_open_for_order(shop_row: tuple) -> bool:
    if shop_row[7] != 1:
        return False

    report_time = (shop_row[6] or "").strip()
    if not report_time:
        
        return True

    now_msk = datetime.now(MSK_TZ).strftime("%H:%M")
    
    return now_msk < report_time


# ГЛАВНОЕ МЕНЮ
@router.message(Command("start"))
async def cmd_start(message: Message):
    user = get_employee(message.from_user.id)
    if not user and PRESENTATION_MODE == False:
        await message.answer(
            "Вы не зарегистрированы в системе.\n"
            "Ваш ID: {}".format(message.from_user.id)
        )
        return
    
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🍱 Открыть мини-приложение",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ],
        resize_keyboard=True,
    )

    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍽 Заказать через бота", callback_data="create_order")],
            [InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders_history")],
        ]
    )

    if not user and PRESENTATION_MODE:
        add_employee(message.from_user.id, message.from_user.first_name, "test", "test")
        await message.answer(
            f"Привет, {message.from_user.first_name}! 👋\n"
            f"Ты можешь сделать заказ в мини-приложении.".format(message.from_user.first_name)
        )
        await message.answer("Выбери действие:", reply_markup=inline_kb)
        return


    await message.answer(
        f"Привет, {user[1]}! 👋\n"
        f"Ты можешь сделать заказ в мини-приложении или через бота.\nЗаказ доступен для редактирования по кнопке \"Мои заказы\".",
        reply_markup=reply_kb,
    )
    await message.answer("Выбери действие:", reply_markup=inline_kb)


# back button
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    user = get_employee(callback.from_user.id)
    if not user and PRESENTATION_MODE == False:
        # Если человек не зарегистрирован
        await callback.message.edit_text(
            "Вы не зарегистрированы в системе.\n"
            f"Ваш ID: {callback.from_user.id}"
        )
        return

    reply_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🍱 Открыть мини-приложение",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ],
        resize_keyboard=True,
    )

    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍽 Заказать через бота", callback_data="create_order")],
            [InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders_history")],
        ]
    )

    await callback.message.answer(
        f"Привет, {user[1]}! 👋\n"
        f"Ты можешь открыть мини-приложение или заказать прямо через бота.",
        reply_markup=reply_kb,
    )
    await callback.message.answer("Выбери действие:", reply_markup=inline_kb)


# Заказ через бота | Блок
@router.callback_query(F.data == "create_order")
async def create_order(callback: CallbackQuery, state: FSMContext):
    shops = get_shops(active_only=True)
    open_shops = [s for s in shops if is_shop_open_for_order(s)]

    if not open_shops:
        await callback.message.edit_text(
            "Сейчас все кафе закрыты для заказов (дедлайн по времени отчёта)."
        )
        return

    kb = [[InlineKeyboardButton(
        text=f"{s[1]} ({s[2]})",
        callback_data=f"cafe_{s[0]}"
    )] for s in open_shops]
    await callback.message.edit_text(
        "Выберите кафе:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(OrderFSM.choose_cafe)


@router.callback_query(OrderFSM.choose_cafe, F.data.startswith("cafe_"))
async def choose_cafe(callback: CallbackQuery, state: FSMContext):
    cafe_id = int(callback.data.replace("cafe_", ""))
    shop = get_shop_by_id(cafe_id)
    if not shop or shop[7] != 1:
        await callback.answer("Это кафе сейчас недоступно.", show_alert=True)
        return

    if not is_shop_open_for_order(shop):
        await callback.answer(
            f"Заказы в этом кафе на сегодня уже закрыты (дедлайн {shop[6] or 'не задан'}).",
            show_alert=True
        )
        return

    try:
        menu = json.loads(shop[3]) if shop[3] else []
    except Exception:
        menu = []

    if not menu:
        await callback.message.edit_text("В этом кафе пока нет меню.")
        return

    await state.update_data(cafe_id=cafe_id, items=[])
    kb = [[InlineKeyboardButton(
        text=f"{item['title']} — {item['price']}₽",
        callback_data=f"add_{idx}"
    )] for idx, item in enumerate(menu)]
    kb.append([InlineKeyboardButton(text="Готово", callback_data="finish_select")])
    await callback.message.edit_text(
        f"Меню — {shop[1]}:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
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
    except Exception:
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

    shop = get_shop_by_id(cafe_id)
    if not shop or not is_shop_open_for_order(shop):
        await state.clear()
        if shop:
            await callback.message.edit_text(
                f"❌ Дедлайн для заказов в кафе {shop[1]} уже прошёл (время отчёта {shop[6]})."
            )
        else:
            await callback.message.edit_text("❌ Кафе недоступно, заказ не сохранён.")
        return

    add_order(user_id=user_id, shop_id=cafe_id, items=items_snapshot)
    await state.clear()
    await callback.message.edit_text("🎉 Заказ сохранён! Спасибо.")

    # После сохранения заказа показываем главное меню
    user = get_employee(user_id)
    if user:
        reply_kb = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="🍱 Открыть мини-приложение",
                        web_app=WebAppInfo(url=WEBAPP_URL),
                    )
                ]
            ],
            resize_keyboard=True,
        )

        inline_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🍽 Заказать через бота", callback_data="create_order")],
                [InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders_history")],
            ]
        )

        await callback.message.answer(
            f"Привет, {user[1]}! 👋\n"
            f"Ты можешь открыть мини-приложение или заказать прямо через бота.",
            reply_markup=reply_kb,
        )
        await callback.message.answer("Выбери действие:", reply_markup=inline_kb)


@router.callback_query(OrderFSM.confirm, F.data == "cancel_order")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменён.\nПропишите /start, чтобы оформить новый заказ.")
    


# Мои заказы
@router.callback_query(F.data == "orders_history")
async def order_history(callback: CallbackQuery):
    user_id = callback.from_user.id
    orders = get_orders_by_user(user_id)
    if not orders:
        await callback.message.edit_text(
            "У вас нет заказов.\n\n"
            "Можете оформить заказ через бота или мини-приложение.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
                ]
            )
        )
        return

    text = "📦 Ваши заказы:\n\n"
    kb = []
    for ord_row in orders:
        order_id, user_id_row, shop_id, items_raw, created_at, delivery_type, comment = ord_row
        shop = get_shop_by_id(shop_id)
        shop_name = shop[1] if shop else "Кафе удалено"
        try:
            items = json.loads(items_raw)
        except Exception:
            items = []

        text += f"#{order_id} — {shop_name} ({created_at}):\n"

        if delivery_type:
            if delivery_type == "office":
                delivery_txt = "доставка в офис"
            elif delivery_type == "restaurant":
                delivery_txt = "на подносе в ресторане"
            else:
                delivery_txt = delivery_type
            text += f"Подача: {delivery_txt}\n"

        if comment:
            text += f"Комментарий: {comment}\n"

        for it in items:
            text += f"• {it.get('title')} — {it.get('price')}₽\n"

        text += "\n"
        kb.append([
            InlineKeyboardButton(
                text=f"Отменить #{order_id}",
                callback_data=f"cancel_order_{order_id}"
            )
        ])

    kb.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")])
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


@router.callback_query(F.data.regexp(r"^cancel_order_\d+$"))
async def cancel_order(callback: CallbackQuery):
    user_id = callback.from_user.id
    order_id = int(callback.data.replace("cancel_order_", ""))
    ok = delete_order(order_id, user_id)
    if ok:
        await callback.message.edit_text(f"✅ Заказ #{order_id} отменён.")
    else:
        await callback.message.edit_text(
            "❌ Не удалось отменить заказ (возможно он уже был удалён или не ваш)."
        )


@router.message(F.web_app_data)
async def handle_webapp_order(message: Message):
    try:
        raw = message.web_app_data.data
        data = json.loads(raw)
    except Exception:
        await message.answer("⚠️ Не удалось прочитать данные из мини-приложения.")
        return

    if not isinstance(data, dict) or data.get("type") != "lunch-order":
        await message.answer("⚠️ Пришли непонятные данные из мини-приложения.")
        return

    cafe_id_raw = data.get("cafeId")
    cafe_name = data.get("cafeName") or "Кафе"
    items_payload = data.get("items") or []

    if cafe_id_raw is None:
        await message.answer("⚠️ Нет ID кафе в заказе.")
        return

    shop = None
    cafe_id: int | None = None

    try:
        cafe_id = int(cafe_id_raw)
        shop = get_shop_by_id(cafe_id)
    except Exception:
        shop = None

    if not shop and cafe_name:
        shops = get_shops(active_only=False)
        for s in shops:
            if s[1] == cafe_name:
                shop = s
                cafe_id = s[0]
                break

    if not shop or cafe_id is None:
        await message.answer(
            "⚠️ Не удалось сопоставить кафе из мини-приложения с кафе в системе.\n"
            "Проверьте, что названия кафе совпадают."
        )
        return

    # Проверяем дедлайн
    if not is_shop_open_for_order(shop):
        await message.answer(
            f"❌ Заказы в кафе {shop[1]} на сегодня уже закрыты "
            f"(дедлайн {shop[6] or 'не задан'})."
        )
        return

    if not items_payload:
        await message.answer("⚠️ Мини-приложение прислало пустой заказ.")
        return

    db_items = []
    total_calc = 0

    for it in items_payload:
        name = it.get("name") or "Блюдо"
        try:
            price = float(it.get("price") or 0)
        except Exception:
            price = 0.0
        qty = int(it.get("qty") or 0)
        if qty <= 0:
            continue

        for _ in range(qty):
            db_items.append({"title": name, "price": price})
        total_calc += price * qty

    if not db_items:
        await message.answer("⚠️ Мини-приложение прислало пустой заказ.")
        return

    delivery_type = data.get("deliveryType", "office")
    delivery_text = "доставка в офис" if delivery_type == "office" else "на подносе в ресторане"
    comment = data.get("comment") or ""
    comment = comment.strip() if isinstance(comment, str) else ""

    order_id = add_order(
        user_id=message.from_user.id,
        shop_id=cafe_id,
        items=db_items,
        delivery_type=delivery_type,
        comment=comment,
    )

    text = f"🎉 Заказ из мини-приложения сохранён!\n\n"
    text += f"Кафе: {cafe_name}\n"
    text += f"Подача: {delivery_text}\n\n"
    text += "Состав заказа:\n"

    for it in items_payload:
        name = it.get("name") or "Блюдо"
        qty = int(it.get("qty") or 0)
        try:
            price = float(it.get("price") or 0)
        except Exception:
            price = 0.0
        if qty <= 0:
            continue
        line_total = price * qty
        text += f"• {name} ×{qty} — {line_total} ₽\n"

    text += f"\nИтого: {total_calc} ₽"
    text += f"\nID заказа в системе: #{order_id}"

    if comment:
        text += f"\nКомментарий: {comment}"

    await message.answer(text)

    user = get_employee(message.from_user.id)
    if user:
        reply_kb = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="🍱 Открыть мини-приложение",
                        web_app=WebAppInfo(url=WEBAPP_URL),
                    )
                ]
            ],
            resize_keyboard=True,
        )

        inline_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🍽 Заказать через бота", callback_data="create_order")],
                [InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders_history")],
            ]
        )

        await message.answer(
            f"Привет, {user[1]}! 👋\n"
            f"Ты можешь открыть мини-приложение или заказать прямо через бота.",
            reply_markup=reply_kb,
        )
        await message.answer("Выбери действие:", reply_markup=inline_kb)
