from aiogram import Bot, Dispatcher
import asyncio
from handlers import users, admin

async def main():
    bot = Bot(token="8404133001:AAHEW9DXaKErO4gD_8rXHSa-XQ13X1Xbu8c")
    dp = Dispatcher()

    dp.include_router(users.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())