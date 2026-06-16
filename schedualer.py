"""
Планировщик ежедневной рассылки. Каждую минуту проверяет, у кого
из пользователей наступило выбранное время, и отправляет им контент.
"""

import datetime
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db

logger = logging.getLogger(__name__)


def setup_scheduler(bot: Bot, send_daily) -> AsyncIOScheduler:
    """
    send_daily — асинхронная функция send_daily(bot, chat_id),
    которая отправляет пользователю ежедневный контент.
    """
    scheduler = AsyncIOScheduler()

    async def check_and_send() -> None:
        now = datetime.datetime.now().strftime("%H:%M")
        try:
            chat_ids = await db.get_users_for_time(now)
        except Exception:
            logger.exception("Не удалось получить список пользователей для рассылки")
            return

        for chat_id in chat_ids:
            try:
                await send_daily(bot, chat_id)
            except Exception:
                logger.exception("Не удалось отправить ежедневное сообщение %s", chat_id)

    scheduler.add_job(check_and_send, "cron", minute="*", second=0)
    return scheduler
