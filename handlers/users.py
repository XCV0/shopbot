from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters.command import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton


router = Router()

# ВРЕМЕННО АЙДИ НЕ С БАЗЫ
available_employees = [5201148794, 837411435]

@router.message(Command("start")) 
async def cmd_start(message: Message):
    if message.from_user.id not in available_employees:
        await message.answer("Вы не добавлены в пользовтаелей бота!Обратитесь к менеджеру в вашем офисе.\nВаш ID: " + str(message.from_user.id))
        return
        
    kb = [[InlineKeyboardButton(
        text="Попробовать", callback_data="create_order"
    )], [InlineKeyboardButton(
        text="Мои заказы", callback_data="orders_history"
    )]]

    await message.answer(
        "Привет! Я помогу тебе заказать обед в офис.\nВыберите нужное действие из кнопок ниже", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
