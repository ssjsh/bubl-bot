"""
Лёгкая база данных на SQLite (через aiosqlite) для:
- пользователей (имя, стрик, настроение, время ежедневной рассылки, очки)
- оценок контента (лайки/дизлайки по категориям) — для общей статистики
"""

import datetime
from typing import Optional

import aiosqlite

DB_PATH = "bot.db"


async def init_db(path: str = DB_PATH) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                name TEXT,
                streak INTEGER DEFAULT 0,
                last_active TEXT,
                mood TEXT,
                daily_time TEXT,
                points INTEGER DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS ratings (
                category TEXT PRIMARY KEY,
                likes INTEGER DEFAULT 0,
                dislikes INTEGER DEFAULT 0
            )
            """
        )
        await db.commit()


def _today() -> str:
    return datetime.date.today().isoformat()


def _yesterday() -> str:
    return (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


async def get_or_create_user(chat_id: int, name: str, path: str = DB_PATH) -> dict:
    async with aiosqlite.connect(path) as db:
        cur = await db.execute(
            "SELECT chat_id, name, streak, last_active, mood, daily_time, points "
            "FROM users WHERE chat_id = ?",
            (chat_id,),
        )
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (chat_id, name, streak, last_active, points) "
                "VALUES (?, ?, 0, NULL, 0)",
                (chat_id, name),
            )
            await db.commit()
            return {
                "chat_id": chat_id,
                "name": name,
                "streak": 0,
                "last_active": None,
                "mood": None,
                "daily_time": None,
                "points": 0,
            }
        keys = ["chat_id", "name", "streak", "last_active", "mood", "daily_time", "points"]
        return dict(zip(keys, row))


async def touch_activity(chat_id: int, path: str = DB_PATH) -> int:
    """Обновляет дату активности и стрик. Возвращает текущий стрик."""
    today = _today()
    async with aiosqlite.connect(path) as db:
        cur = await db.execute(
            "SELECT streak, last_active FROM users WHERE chat_id = ?", (chat_id,)
        )
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (chat_id, streak, last_active, points) VALUES (?, 1, ?, 0)",
                (chat_id, today),
            )
            await db.commit()
            return 1

        streak, last_active = row
        if last_active == today:
            return streak
        elif last_active == _yesterday():
            streak += 1
        else:
            streak = 1

        await db.execute(
            "UPDATE users SET streak = ?, last_active = ? WHERE chat_id = ?",
            (streak, today, chat_id),
        )
        await db.commit()
        return streak


async def set_mood(chat_id: int, mood: str, path: str = DB_PATH) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE users SET mood = ? WHERE chat_id = ?", (mood, chat_id))
        await db.commit()


async def set_daily_time(chat_id: int, time_str: Optional[str], path: str = DB_PATH) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "UPDATE users SET daily_time = ? WHERE chat_id = ?", (time_str, chat_id)
        )
        await db.commit()


async def get_users_for_time(time_str: str, path: str = DB_PATH) -> list[int]:
    async with aiosqlite.connect(path) as db:
        cur = await db.execute(
            "SELECT chat_id FROM users WHERE daily_time = ?", (time_str,)
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_all_chat_ids(path: str = DB_PATH) -> list[int]:
    async with aiosqlite.connect(path) as db:
        cur = await db.execute("SELECT chat_id FROM users")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def add_points(chat_id: int, amount: int, path: str = DB_PATH) -> int:
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "UPDATE users SET points = points + ? WHERE chat_id = ?", (amount, chat_id)
        )
        await db.commit()
        cur = await db.execute("SELECT points FROM users WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def rate_content(category: str, positive: bool, path: str = DB_PATH) -> None:
    column = "likes" if positive else "dislikes"
    async with aiosqlite.connect(path) as db:
        await db.execute(
            f"INSERT INTO ratings (category, {column}) VALUES (?, 1) "
            f"ON CONFLICT(category) DO UPDATE SET {column} = {column} + 1",
            (category,),
        )
        await db.commit()


async def get_stats(path: str = DB_PATH) -> dict:
    async with aiosqlite.connect(path) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE daily_time IS NOT NULL")
        scheduled_users = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT category, likes, dislikes FROM ratings ORDER BY (likes+dislikes) DESC"
        )
        ratings = await cur.fetchall()

        cur = await db.execute("SELECT MAX(streak) FROM users")
        max_streak = (await cur.fetchone())[0] or 0

        return {
            "total_users": total_users,
            "scheduled_users": scheduled_users,
            "ratings": ratings,
            "max_streak": max_streak,
        }


async def get_profile(chat_id: int, path: str = DB_PATH) -> dict:
    return await get_or_create_user(chat_id, "", path)
