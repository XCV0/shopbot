# bot.py
import os
import asyncio
import logging
import json
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from db.db_controller import (
    init_db, get_shops, get_orders_by_shop, clear_orders_for_shop,
    get_managers, get_employee, get_shop_by_id
)
from handlers import users, admin

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Scheduler timezone: Europe/Berlin
SCHED_TZ = "Europe/Moscow"
scheduler = AsyncIOScheduler(timezone=SCHED_TZ)


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

    # clear orders for this shop after sending
    clear_orders_for_shop(shop_id)
    logger.info("Cleared orders for shop_id=%s after sending report", shop_id)


def schedule_jobs_for_all_shops(bot: Bot):
    """
    (Re)create cron jobs for all shops that have report_time.
    Called at startup.
    """
    scheduler.remove_all_jobs()
    shops = get_shops(active_only=False)
    for s in shops:
        shop_id = s[0]
        report_time = s[6]
        if not report_time:
            continue
        try:
            hhmm = report_time.strip()
            hh, mm = map(int, hhmm.split(":"))
        except Exception:
            logger.warning("Invalid report_time for shop %s: %s", shop_id, report_time)
            continue
        # Add cron job in Europe/Berlin tz
        trigger = CronTrigger(hour=hh, minute=mm, timezone=SCHED_TZ)
        scheduler.add_job(send_report_for_shop, trigger, args=[bot, shop_id],
                          id=f"report_shop_{shop_id}", replace_existing=True)
        logger.info("Scheduled report for shop %s at %02d:%02d (%s)", shop_id, hh, mm, SCHED_TZ)


async def main():
    # Init DB
    init_db()
    # Create bot & dp
    bot = Bot(token="8404133001:AAHEW9DXaKErO4gD_8rXHSa-XQ13X1Xbu8c")
    dp = Dispatcher()

    # register routers
    dp.include_router(users.router)
    dp.include_router(admin.router)

    # start scheduler
    scheduler.start()
    schedule_jobs_for_all_shops(bot)

    # delete webhook and start polling
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Bot started, polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down")
        scheduler.shutdown()
