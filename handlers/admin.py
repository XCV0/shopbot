from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.db_controller import (
    add_shop, get_shops, get_shop_by_id,
    add_employee, add_manager, is_manager,
    add_item_to_shop, remove_item_from_shop, set_shop_active,
    get_orders_by_shop, get_employee, delete_shop
)

import json

router = Router()


class AdminFSM(StatesGroup):
    add_shop_name = State()
    add_shop_address = State()
    add_shop_menu_manual = State()
    add_shop_time = State()
    add_shop_day = State()
    add_shop_report_time = State()

    add_item_shop = State()
    add_item_title = State()
    add_item_price = State()


async def render_shop_management(message_obj, shop_id: int):
    shop = get_shop_by_id(shop_id)
    if not shop:
        try:
            await message_obj.edit_text("Кафе не найдено.")
        except Exception:
            await message_obj.answer("Кафе не найдено.")
        return

    active = shop[7] == 1
    kb = [
        [InlineKeyboardButton(text="📋 Посмотреть меню", callback_data=f"adm_shop_viewmenu_{shop_id}")],
        [InlineKeyboardButton(text="📦 Текущие заказы", callback_data=f"adm_shop_orders_{shop_id}")],
        [InlineKeyboardButton(text="📊 Агрегированный отчёт", callback_data=f"adm_shop_agg_{shop_id}")],
        [InlineKeyboardButton(text="➕ Добавить позицию", callback_data=f"adm_shop_additem_{shop_id}")],
        [InlineKeyboardButton(text="🗑 Удалить позицию", callback_data=f"adm_shop_delchoose_{shop_id}")],
        [InlineKeyboardButton(
            text=("🚫 Сделать неактивным" if active else "✅ Сделать активным"),
            callback_data=f"adm_shop_toggleactive_{shop_id}"
        )],
        [InlineKeyboardButton(text="🔥 Полностью удалить кафе", callback_data=f"adm_shop_delete_{shop_id}")],
        [InlineKeyboardButton(text="⬅ Назад (список)", callback_data="adm_list_shops")]
    ]
    text = (
        f"Управление кафе: {shop[1]}\n"
        f"Адрес: {shop[2]}\n\n"
        f"Состояние: {'активно' if active else 'неактивно'}\n"
        f"Время отчёта (МСК): {shop[6] or 'не задано'}"
    )
    try:
        await message_obj.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except Exception:
        await message_obj.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.message(Command("admin"))
async def admin_start(message: Message):
    if not is_manager(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return

    kb = [
        [InlineKeyboardButton(text="➕ Добавить кафе", callback_data="adm_add_shop")],
        [InlineKeyboardButton(text="📋 Все кафе", callback_data="adm_list_shops")],
        [InlineKeyboardButton(text="👤 Добавить сотрудника", callback_data="adm_add_employee")],
        [InlineKeyboardButton(text="⭐ Добавить менеджера", callback_data="adm_add_manager")]
    ]
    await message.answer("Панель администратора:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data == "adm_add_shop")
async def adm_add_shop(callback: CallbackQuery, state: FSMContext):
    if not is_manager(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.answer("Введите название кафе:")
    await state.set_state(AdminFSM.add_shop_name)


@router.message(AdminFSM.add_shop_name)
async def adm_shop_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите адрес кафе:")
    await state.set_state(AdminFSM.add_shop_address)


@router.message(AdminFSM.add_shop_address)
async def adm_shop_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer(
        "Можно добавить меню сейчас JSON'ом (опционально) или отправьте /skipmenu, "
        "чтобы добавить меню позже через кнопки.\n\n"
        "Пример JSON:\n"
        '[{"title": "Борщ", "price": 150}, {"title": "Пюре", "price": 100}]'
    )
    await state.set_state(AdminFSM.add_shop_menu_manual)


@router.message(AdminFSM.add_shop_menu_manual)
async def adm_shop_menu_manual(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "/skipmenu":
        await state.update_data(menu=[])
    else:
        try:
            menu = json.loads(text)
            if not isinstance(menu, list):
                raise ValueError
            norm = []
            for it in menu:
                if not isinstance(it, dict):
                    continue
                t = it.get("title")
                p = it.get("price")
                if t is None or p is None:
                    continue
                norm.append({"title": str(t), "price": float(p)})
            await state.update_data(menu=norm)
        except Exception:
            await message.answer("Ошибка в JSON. Введите корректный JSON или /skipmenu")
            return
    await message.answer("Введите время доступности (например: 10:00-12:00):")
    await state.set_state(AdminFSM.add_shop_time)


@router.message(AdminFSM.add_shop_time)
async def adm_shop_time(message: Message, state: FSMContext):
    await state.update_data(time_available=message.text)
    await message.answer("Введите дни доступности (например: пн-пт):")
    await state.set_state(AdminFSM.add_shop_day)


@router.message(AdminFSM.add_shop_day)
async def adm_shop_day(message: Message, state: FSMContext):
    await state.update_data(day_available=message.text)
    await message.answer("Введите время формирования отчёта (например: 11:00):")
    await state.set_state(AdminFSM.add_shop_report_time)


@router.message(AdminFSM.add_shop_report_time)
async def adm_shop_report_time(message: Message, state: FSMContext):
    data = await state.get_data()
    menu = data.get("menu", [])
    add_shop(
        name=data["name"],
        address=data["address"],
        menu=menu,
        time_available=data.get("time_available", ""),
        day_available=data.get("day_available", ""),
        report_time=message.text.strip()
    )
    await state.clear()
    await message.answer(
        "✅ Кафе добавлено. Меню можно редактировать в списке кафе.\n"
        "Отчёты будут отправляться автоматически по МСК."
    )


@router.callback_query(F.data == "adm_list_shops")
async def adm_list_shops(callback: CallbackQuery):
    if not is_manager(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    shops = get_shops(active_only=False)
    if not shops:
        await callback.message.edit_text("Пока нет кафе.")
        return

    kb = []
    for s in shops:
        active = "🟢" if s[7] == 1 else "🔴"
        kb.append([InlineKeyboardButton(
            text=f"{active} {s[1]} — {s[2]}",
            callback_data=f"adm_shop_{s[0]}"
        )])
    await callback.message.edit_text(
        "Список кафе (нажмите, чтобы редактировать):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


@router.callback_query(F.data.regexp(r"^adm_shop_\d+$"))
async def adm_shop_root(callback: CallbackQuery):
    shop_id = int(callback.data.replace("adm_shop_", ""))
    await render_shop_management(callback.message, shop_id)


@router.callback_query(F.data.regexp(r"^adm_shop_viewmenu_\d+$"))
async def adm_shop_viewmenu(callback: CallbackQuery):
    shop_id = int(callback.data.replace("adm_shop_viewmenu_", ""))
    shop = get_shop_by_id(shop_id)
    try:
        menu = json.loads(shop[3]) if shop and shop[3] else []
    except Exception:
        menu = []
    if not menu:
        await callback.message.edit_text("Меню пустое.")
        return
    text = f"Меню — {shop[1]}:\n\n"
    for i, item in enumerate(menu):
        text += f"{i}. {item.get('title')} — {item.get('price')}₽\n"
    kb = [[InlineKeyboardButton(text="⬅ Назад", callback_data=f"adm_shop_{shop_id}")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.regexp(r"^adm_shop_orders_\d+$"))
async def adm_shop_orders(callback: CallbackQuery):
    if not is_manager(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return

    shop_id = int(callback.data.replace("adm_shop_orders_", ""))
    shop = get_shop_by_id(shop_id)
    if not shop:
        await callback.message.edit_text("Кафе не найдено.")
        return

    orders = get_orders_by_shop(shop_id)
    if not orders:
        await callback.message.edit_text(
            f"По кафе {shop[1]} пока нет заказов.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ Назад", callback_data=f"adm_shop_{shop_id}")]
                ]
            )
        )
        return

    text = f"📦 Заказы по кафе {shop[1]}:\n\n"

    for o in orders:
        order_id, user_id, shop_id_row, items_raw, created_at, delivery_type, comment = o
        emp = get_employee(user_id)
        if emp:
            user_name = emp[1]
            office = emp[2]
            user_label = f"{user_name} (офис {office}, id {user_id})"
        else:
            user_label = f"id {user_id}"

        try:
            items = json.loads(items_raw)
        except Exception:
            items = []

        text += f"👤 {user_label} — заказ #{order_id} ({created_at}):\n"

        if delivery_type:
            if delivery_type == "office":
                delivery_txt = "доставка в офис"
            elif delivery_type == "restaurant":
                delivery_txt = "на подносе в ресторане"
            else:
                delivery_txt = delivery_type
            text += f"  Подача: {delivery_txt}\n"

        if comment:
            text += f"  Комментарий: {comment}\n"

        order_sum = 0
        for it in items:
            title = it.get("title")
            price = it.get("price", 0)
            order_sum += price
            text += f"  • {title} — {price}₽\n"

        text += f"  Итого: {order_sum}₽\n\n"

    kb = [[InlineKeyboardButton(text="⬅ Назад", callback_data=f"adm_shop_{shop_id}")]]
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


@router.callback_query(F.data.regexp(r"^adm_shop_agg_\d+$"))
async def adm_shop_agg(callback: CallbackQuery):
    if not is_manager(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return

    shop_id = int(callback.data.replace("adm_shop_agg_", ""))
    shop = get_shop_by_id(shop_id)
    if not shop:
        await callback.message.edit_text("Кафе не найдено.")
        return

    orders = get_orders_by_shop(shop_id)
    if not orders:
        await callback.message.edit_text(
            f"По кафе {shop[1]} пока нет заказов.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ Назад", callback_data=f"adm_shop_{shop_id}")]
                ]
            )
        )
        return

    item_stats = {}
    user_stats = {}
    total_sum = 0.0
    order_ids = set()

    for o in orders:
        order_id, user_id, shop_id_row, items_raw, created_at, delivery_type, comment = o
        order_ids.add(order_id)

        try:
            items = json.loads(items_raw)
        except Exception:
            items = []

        # учёт по пользователю
        if user_id not in user_stats:
            user_stats[user_id] = {"cnt": 0, "sum": 0.0}
        user_stats[user_id]["cnt"] += 1

        for it in items:
            title = it.get("title") or "Блюдо"
            try:
                price = float(it.get("price") or 0)
            except Exception:
                price = 0.0

            key = (title, price)
            if key not in item_stats:
                item_stats[key] = {"qty": 0, "sum": 0.0}
            item_stats[key]["qty"] += 1
            item_stats[key]["sum"] += price

            total_sum += price
            user_stats[user_id]["sum"] += price

    text = f"📊 Агрегированный отчёт по кафе {shop[1]}:\n\n"
    text += f"Всего заказов: {len(order_ids)}\n"
    text += f"Общая сумма: {int(total_sum)} ₽\n\n"

    if item_stats:
        text += "По блюдам:\n"
        for (title, price), st in item_stats.items():
            text += (
                f"• {title} — {st['qty']} шт, {int(st['sum'])} ₽ "
                f"(цена {int(price)} ₽)\n"
            )
        text += "\n"

    if user_stats:
        text += "По сотрудникам:\n"
        for user_id, st in user_stats.items():
            emp = get_employee(user_id)
            if emp:
                name = emp[1]
                office = emp[2]
                user_label = f"{name} (офис {office}, id {user_id})"
            else:
                user_label = f"id {user_id}"
            text += (
                f"• {user_label} — {st['cnt']} заказ(ов), {int(st['sum'])} ₽\n"
            )

    kb = [[InlineKeyboardButton(text="⬅ Назад", callback_data=f"adm_shop_{shop_id}")]]
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


@router.callback_query(F.data.regexp(r"^adm_shop_additem_\d+$"))
async def adm_shop_additem_start(callback: CallbackQuery, state: FSMContext):
    shop_id = int(callback.data.replace("adm_shop_additem_", ""))
    await state.update_data(add_item_shop=shop_id)
    await callback.message.answer("Введите название блюда:")
    await state.set_state(AdminFSM.add_item_title)


@router.message(AdminFSM.add_item_title)
async def adm_shop_additem_title(message: Message, state: FSMContext):
    await state.update_data(add_item_title=message.text)
    await message.answer("Введите цену (числом, рубли):")
    await state.set_state(AdminFSM.add_item_price)


@router.message(AdminFSM.add_item_price)
async def adm_shop_additem_price(message: Message, state: FSMContext):
    data = await state.get_data()
    shop_id = data.get("add_item_shop")
    title = data.get("add_item_title")
    if shop_id is None or title is None:
        await message.answer("Ошибка состояния. Попробуйте заново.")
        await state.clear()
        return
    try:
        price = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("Некорректная цена. Введите число, например: 150")
        return

    ok = add_item_to_shop(shop_id, title, price)
    await state.clear()
    if ok:
        await message.answer(f"✅ Позиция '{title}' добавлена.")
    else:
        await message.answer("❌ Ошибка при добавлении позиции.")
    await render_shop_management(message, shop_id)


@router.callback_query(F.data.regexp(r"^adm_shop_delchoose_\d+$"))
async def adm_shop_delchoose(callback: CallbackQuery):
    shop_id = int(callback.data.replace("adm_shop_delchoose_", ""))
    shop = get_shop_by_id(shop_id)
    try:
        menu = json.loads(shop[3]) if shop and shop[3] else []
    except Exception:
        menu = []

    if not menu:
        await callback.message.edit_text("Меню пустое.")
        return

    kb = []
    for i, item in enumerate(menu):
        kb.append([InlineKeyboardButton(
            text=f"Удалить: {item.get('title')} — {item.get('price')}₽",
            callback_data=f"adm_shop_del_{shop_id}_{i}"
        )])
    kb.append([InlineKeyboardButton(text="Отмена", callback_data=f"adm_shop_{shop_id}")])
    await callback.message.edit_text(
        "Выберите позицию для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


@router.callback_query(F.data.regexp(r"^adm_shop_del_\d+_\d+$"))
async def adm_shop_del(callback: CallbackQuery):
    parts = callback.data.split("_")
    shop_id = int(parts[3])
    idx = int(parts[4])
    ok = remove_item_from_shop(shop_id, idx)
    if ok:
        await callback.message.answer("✅ Позиция удалена.")
    else:
        await callback.message.answer("❌ Не удалось удалить (возможно неверный индекс).")
    await render_shop_management(callback.message, shop_id)


@router.callback_query(F.data.regexp(r"^adm_shop_toggleactive_\d+$"))
async def adm_shop_toggleactive(callback: CallbackQuery):
    shop_id = int(callback.data.replace("adm_shop_toggleactive_", ""))
    shop = get_shop_by_id(shop_id)
    if not shop:
        await callback.answer("Кафе не найдено", show_alert=True)
        return
    new_state = not (shop[7] == 1)
    ok = set_shop_active(shop_id, new_state)
    if ok:
        await callback.message.answer(
            f"Состояние кафе обновлено: {'активно' if new_state else 'неактивно'}."
        )
    else:
        await callback.message.answer("Не удалось изменить состояние кафе.")
    await adm_list_shops(callback)


@router.callback_query(F.data.regexp(r"^adm_shop_delete_\d+$"))
async def adm_shop_delete(callback: CallbackQuery):
    if not is_manager(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return

    shop_id = int(callback.data.replace("adm_shop_delete_", ""))
    shop = get_shop_by_id(shop_id)
    if not shop:
        await callback.answer("Кафе не найдено", show_alert=True)
        return

    text = (
        f"Вы действительно хотите *полностью удалить* кафе '{shop[1]}'?\n\n"
        f"Будут удалены:\n"
        f"• само кафе\n"
        f"• все заказы по этому кафе\n\n"
        f"Это действие необратимо."
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"adm_shop_delete_confirm_{shop_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Отмена",
                    callback_data=f"adm_shop_{shop_id}"
                )
            ]
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.regexp(r"^adm_shop_delete_confirm_\d+$"))
async def adm_shop_delete_confirm(callback: CallbackQuery):
    if not is_manager(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return

    shop_id = int(callback.data.replace("adm_shop_delete_confirm_", ""))
    shop = get_shop_by_id(shop_id)
    name = shop[1] if shop else f"id {shop_id}"

    ok = delete_shop(shop_id)
    if ok:
        await callback.message.edit_text(f"🔥 Кафе '{name}' и все его заказы были удалены.")
    else:
        await callback.message.edit_text("❌ Не удалось удалить кафе (возможно, оно уже удалено).")

    await adm_list_shops(callback)


@router.callback_query(F.data == "adm_add_employee")
async def adm_add_employee_start(callback: CallbackQuery):
    await callback.message.answer("Формат: <tg_id>;<Имя>;<Офис>;<ecard>")


@router.message(F.text.contains(";"))
async def adm_add_employee_finish(message: Message):
    try:
        tg_id, name, office, ecard = message.text.split(";")
        tg_id = int(tg_id)
        if add_employee(tg_id, name, office, ecard):
            await message.answer("✅ Сотрудник добавлен!")
        else:
            await message.answer("❌ Такой сотрудник уже существует.")
    except Exception:
        return


@router.callback_query(F.data == "adm_add_manager")
async def adm_add_manager_start(callback: CallbackQuery):
    await callback.message.answer("Введите Telegram ID менеджера:")


@router.message(F.text.regexp(r"^\d+$"))
async def adm_add_manager_finish(message: Message):
    add_manager(int(message.text))
    await message.answer("⭐ Менеджер добавлен!")
