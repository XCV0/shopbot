# bot.py
import os
import asyncio
import logging
import json
from datetime import datetime

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from db.db_controller import (
    init_db,
    get_shops,
    get_orders_by_shop,
    clear_orders_for_shop,
    get_managers,
    get_employee,
    get_shop_by_id,
)
from handlers import users, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Часовой пояс МСК
SCHED_TZ = timezone("Europe/Moscow")
scheduler = AsyncIOScheduler(timezone=SCHED_TZ)

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_TOKEN_HERE")  # замени на свой токен


async def send_report_for_shop(bot: Bot, shop_id: int):
    orders = get_orders_by_shop(shop_id)
    if not orders:
        logger.info("No orders for shop_id=%s, skipping report", shop_id)
        return

    shop = get_shop_by_id(shop_id)
    shop_name = shop[1] if shop else f"#{shop_id}"

    text = f"📦 Отчёт по кафе *{shop_name}*:\n\n"
    total_sum_all = 0
    for o in orders:
        order_id, user_id, shop_id_row, items_raw, created_at = o
        try:
            items = json.loads(items_raw)
        except:
            items = []
        user = get_employee(user_id)
        user_name = user[1] if user else str(user_id)
        text += f"👤 {user_name} (id {user_id}) — заказ #{order_id} ({created_at}):\n"
        order_sum = 0
        for it in items:
            title = it.get("title")
            price = it.get("price", 0)
            order_sum += price
            text += f"  • {title} — {price}₽\n"
        text += f"  Итого: {order_sum}₽\n\n"
        total_sum_all += order_sum

    text += f"Всего по кафе: {total_sum_all}₽"

    managers = get_managers()
    if not managers:
        logger.info("No managers to send report to for shop %s", shop_id)
    for m in managers:
        try:
            await bot.send_message(m, text, parse_mode="Markdown")
        except Exception as e:
            logger.exception("Failed to send report to manager %s: %s", m, e)

    clear_orders_for_shop(shop_id)
    logger.info("Cleared orders for shop_id=%s after sending report", shop_id)


async def check_and_send_reports(bot: Bot):
    now = datetime.now(SCHED_TZ)
    current_hhmm = now.strftime("%H:%M")
    logger.debug("Checking reports for time %s (MSK)", current_hhmm)

    shops = get_shops(active_only=False)
    for s in shops:
        shop_id = s[0]
        report_time = (s[6] or "").strip()
        if not report_time:
            continue
        if report_time == current_hhmm:
            logger.info("Time matched for shop %s at %s, sending report", shop_id, current_hhmm)
            await send_report_for_shop(bot, shop_id)


def start_scheduler(bot: Bot):
    scheduler.add_job(
        check_and_send_reports,
        CronTrigger(minute="*", timezone=SCHED_TZ),
        args=[bot],
        id="check_reports_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started with 1-minute check job (MSK).")


async def main():
    init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(users.router)
    dp.include_router(admin.router)

    start_scheduler(bot)

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Bot started, polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down")
        scheduler.shutdown()