import asyncio
import logging
import os
import random

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

import database as db
from content import (
    FACTS,
    JOKES,
    QUOTES,
    WARM_MESSAGES,
    COMPLIMENTS,
    get_horoscope,
    random_quiz_question,
)
from content_api import (
    fetch_cat_url,
    fetch_dog_url,
    fetch_gif,
    fetch_meme,
    get_random_local_file,
    is_video,
)
from games import check_guess, new_guess_target, play_rps
from keyboards import (
    MOOD_MAP,
    content_keyboard,
    games_menu,
    guess_menu,
    main_menu,
    mood_menu,
    quiz_keyboard,
    replay_keyboard,
    rps_menu,
    schedule_menu,
    zodiac_menu,
)
from schedualer import setup_scheduler

# ----------------------------------------------------------------------------
# НАСТРОЙКИ
# ----------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8667127538:AAEo67QcgHc4YSldkIWusnnAyHuuZ5xfs34")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/webapp/")
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "5551915250").split(",") if x.strip().isdigit()
}

logging.basicConfig(level=logging.INFO)
router = Router()

# Состояние мини-игры "угадай число": chat_id -> загаданное число
guess_targets: dict[int, int] = {}

IMAGE_CATEGORIES = {"cat", "dog", "meme", "gif"}
TEXT_CATEGORIES = {"joke": JOKES, "quote": QUOTES, "fact": FACTS, "warm": WARM_MESSAGES}
ALL_CATEGORIES = ["cat", "dog", "meme", "gif", "joke", "quote", "fact", "warm"]
SHORTCUT_CATEGORIES = ALL_CATEGORIES + ["surprise", "local"]

MOOD_LABELS = {
    "happy": "😄 Хорошо",
    "sad": "😢 Грустно",
    "angry": "😡 Раздражена",
    "tired": "🥱 Устала",
    "bored": "🥳 Скучно",
}

WELCOME_TEXT = (
    "Привет! 👋 Я бот для борьбы со скучными днями.\n\n"
    "Вот что я умею:\n"
    "🐱 котики и 🐶 пёсики\n"
    "😂 мемы и 🎞 гифки-реакции\n"
    "🃏 анекдоты, 💬 цитаты, 🧠 факты\n"
    "💌 тёплые слова поддержки\n"
    "🔮 шутливый гороскоп\n"
    "🎮 мини-игры: КНБ, угадай число, викторина\n"
    "😊 подбор контента под настроение\n"
    "⏰ ежедневная рассылка в удобное время\n"
    "👤 профиль со стриком и очками\n"
    "📁 свои фото/видео из папки media/\n"
    "🌐 Mini App с веб-интерфейсом\n\n"
    "Жми кнопки в меню 👇"
)

HELP_TEXT = (
    "Команды:\n"
    "/menu — главное меню\n"
    "/cat /dog /meme /gif — медиа\n"
    "/joke /quote /fact /warm — текстовые штуки\n"
    "/surprise — что-то случайное\n"
    "/local — файл из папки media/\n"
    "/games — мини-игры\n"
    "/mood — подобрать контент по настроению\n"
    "/horoscope — шутливый гороскоп\n"
    "/schedule — ежедневная рассылка\n"
    "/profile — твой профиль (стрик, очки)\n\n"
    "Или просто жми кнопки в /menu 🙂"
)


# ----------------------------------------------------------------------------
# ДОСТАВКА КОНТЕНТА
# ----------------------------------------------------------------------------
async def deliver_content(bot: Bot, chat_id: int, category: str) -> None:
    if category == "surprise":
        category = random.choice(ALL_CATEGORIES)

    if category in IMAGE_CATEGORIES:
        async with aiohttp.ClientSession() as session:
            try:
                if category == "cat":
                    url = await fetch_cat_url(session)
                    caption = "Мяу! 🐱"
                elif category == "dog":
                    url = await fetch_dog_url(session)
                    caption = "Гав! 🐶"
                elif category == "meme":
                    url, title = await fetch_meme(session)
                    caption = title or "Вот мем 😂"
                else:  # gif
                    url, gif_category = await fetch_gif(session)
                    caption = f"🎞 {gif_category}"

                await bot.send_photo(
                    chat_id, url, caption=caption,
                    reply_markup=content_keyboard(category, url),
                )
            except Exception:
                await bot.send_message(
                    chat_id,
                    "Не получилось загрузить контент 🙈 Попробуй ещё раз",
                    reply_markup=replay_keyboard("🔁 Повторить", f"content:{category}"),
                )
        return

    if category == "local":
        file_path = get_random_local_file()
        if file_path is None:
            await bot.send_message(
                chat_id,
                "Папка media/ пока пуста 📁\n"
                "Положи туда свои фото, видео или гифки — "
                "и бот будет иногда присылать их тоже!",
                reply_markup=replay_keyboard("⬅️ В меню", "menu:main"),
            )
            return
        try:
            file = FSInputFile(file_path)
            if is_video(file_path):
                await bot.send_video(chat_id, file, reply_markup=content_keyboard("local"))
            else:
                await bot.send_photo(chat_id, file, reply_markup=content_keyboard("local"))
        except Exception:
            await bot.send_message(chat_id, "Не получилось отправить файл 🙈")
        return

    if category in TEXT_CATEGORIES:
        text = random.choice(TEXT_CATEGORIES[category])
        prefix = {"fact": "🧠 ", "quote": "💬 "}.get(category, "")
        full_text = prefix + text
        await bot.send_message(
            chat_id, full_text, reply_markup=content_keyboard(category, full_text)
        )
        return

    await bot.send_message(chat_id, "Хм, что-то пошло не так 🤔")


async def show_menu(callback: CallbackQuery, text: str, keyboard) -> None:
    """Редактирует текущее сообщение, либо отправляет новое, если редактирование невозможно."""
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)


async def send_profile(bot: Bot, chat_id: int) -> None:
    profile = await db.get_profile(chat_id)
    mood_label = MOOD_LABELS.get(profile["mood"], "не выбрано")
    daily = profile["daily_time"] or "выключена"
    text = (
        "👤 Твой профиль\n\n"
        f"🔥 Стрик: {profile['streak']} дн.\n"
        f"⭐ Очки за игры: {profile['points']}\n"
        f"😊 Настроение: {mood_label}\n"
        f"⏰ Рассылка: {daily}"
    )
    await bot.send_message(chat_id, text, reply_markup=replay_keyboard("⬅️ В меню", "menu:main"))


# ----------------------------------------------------------------------------
# КОМАНДЫ
# ----------------------------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await db.get_or_create_user(message.chat.id, message.from_user.first_name or "")
    await db.touch_activity(message.chat.id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu(WEBAPP_URL))


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Что тебе сегодня нужно?", reply_markup=main_menu(WEBAPP_URL))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("games"))
async def cmd_games(message: Message) -> None:
    await message.answer("🎮 Выбирай игру:", reply_markup=games_menu())


@router.message(Command("mood"))
async def cmd_mood(message: Message) -> None:
    await message.answer("Как ты сейчас? Подберу что-нибудь подходящее 💫", reply_markup=mood_menu())


@router.message(Command("horoscope"))
async def cmd_horoscope(message: Message) -> None:
    await message.answer("🔮 Выбери знак зодиака (это просто для развлечения!):", reply_markup=zodiac_menu())


@router.message(Command("schedule"))
async def cmd_schedule(message: Message) -> None:
    profile = await db.get_profile(message.chat.id)
    await message.answer(
        "⏰ В какое время присылать ежедневный сюрприз?",
        reply_markup=schedule_menu(profile["daily_time"]),
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    await db.touch_activity(message.chat.id)
    await send_profile(message.bot, message.chat.id)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    stats = await db.get_stats()
    lines = [
        f"👥 Пользователей: {stats['total_users']}",
        f"⏰ С включённой рассылкой: {stats['scheduled_users']}",
        f"🔥 Лучший стрик: {stats['max_streak']} дн.",
        "",
        "Оценки контента:",
    ]
    if stats["ratings"]:
        for category, likes, dislikes in stats["ratings"]:
            lines.append(f"  {category}: 👍{likes} 👎{dislikes}")
    else:
        lines.append("  пока нет оценок")
    await message.answer("\n".join(lines))


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, command: CommandObject) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    text = command.args
    if not text:
        await message.answer("Использование: /broadcast текст сообщения")
        return

    chat_ids = await db.get_all_chat_ids()
    sent = 0
    for chat_id in chat_ids:
        try:
            await message.bot.send_message(chat_id, f"📢 {text}")
            sent += 1
        except Exception:
            pass
    await message.answer(f"Отправлено: {sent}/{len(chat_ids)}")


# Шорткаты для контента: /cat /dog /meme /gif /joke /quote /fact /warm /surprise /local
@router.message(Command(*SHORTCUT_CATEGORIES))
async def cmd_content_shortcut(message: Message, command: CommandObject) -> None:
    await db.get_or_create_user(message.chat.id, message.from_user.first_name or "")
    await db.touch_activity(message.chat.id)
    await deliver_content(message.bot, message.chat.id, command.command)


# ----------------------------------------------------------------------------
# НАВИГАЦИЯ ПО МЕНЮ
# ----------------------------------------------------------------------------
@router.callback_query(F.data == "menu:main")
async def cb_menu_main(callback: CallbackQuery) -> None:
    await show_menu(callback, "Что тебе сегодня нужно?", main_menu(WEBAPP_URL))
    await callback.answer()


@router.callback_query(F.data == "menu:games")
async def cb_menu_games(callback: CallbackQuery) -> None:
    await show_menu(callback, "🎮 Выбирай игру:", games_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:mood")
async def cb_menu_mood(callback: CallbackQuery) -> None:
    await show_menu(callback, "Как ты сейчас? Подберу что-нибудь подходящее 💫", mood_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:zodiac")
async def cb_menu_zodiac(callback: CallbackQuery) -> None:
    await show_menu(callback, "🔮 Выбери знак зодиака (это просто для развлечения!):", zodiac_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def cb_menu_profile(callback: CallbackQuery) -> None:
    await db.touch_activity(callback.message.chat.id)
    await send_profile(callback.bot, callback.message.chat.id)
    await callback.answer()


@router.callback_query(F.data == "menu:schedule")
async def cb_menu_schedule(callback: CallbackQuery) -> None:
    profile = await db.get_profile(callback.message.chat.id)
    await show_menu(
        callback,
        "⏰ В какое время присылать ежедневный сюрприз?",
        schedule_menu(profile["daily_time"]),
    )
    await callback.answer()


# ----------------------------------------------------------------------------
# КОНТЕНТ ПО КНОПКАМ
# ----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("content:"))
async def cb_content(callback: CallbackQuery) -> None:
    category = callback.data.split(":", 1)[1]
    await db.touch_activity(callback.message.chat.id)
    await deliver_content(callback.bot, callback.message.chat.id, category)
    await callback.answer()


# ----------------------------------------------------------------------------
# ОЦЕНКА КОНТЕНТА
# ----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("rate:"))
async def cb_rate(callback: CallbackQuery) -> None:
    _, category, value = callback.data.split(":")
    await db.rate_content(category, value == "1")
    await callback.answer("Спасибо за оценку! 🙌")


# ----------------------------------------------------------------------------
# НАСТРОЕНИЕ
# ----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("mood:"))
async def cb_mood(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    await db.set_mood(chat_id, key)
    emoji, intro, category = MOOD_MAP[key]
    await callback.message.answer(f"{emoji} {intro}")
    await deliver_content(callback.bot, chat_id, category)
    await callback.answer()


# ----------------------------------------------------------------------------
# ГОРОСКОП
# ----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("zodiac:"))
async def cb_zodiac(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    text = get_horoscope(key)
    await show_menu(callback, text, replay_keyboard("🔮 Другой знак", "menu:zodiac"))
    await callback.answer()


# ----------------------------------------------------------------------------
# ИГРЫ: КАМЕНЬ-НОЖНИЦЫ-БУМАГА
# ----------------------------------------------------------------------------
@router.callback_query(F.data == "game:rps")
async def cb_game_rps(callback: CallbackQuery) -> None:
    await show_menu(callback, "✊✋✌️ Камень, ножницы или бумага?", rps_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("rps:"))
async def cb_rps_choice(callback: CallbackQuery) -> None:
    choice = callback.data.split(":", 1)[1]
    _, text = play_rps(choice)
    await show_menu(callback, text, rps_menu())
    await callback.answer()


# ----------------------------------------------------------------------------
# ИГРЫ: УГАДАЙ ЧИСЛО
# ----------------------------------------------------------------------------
@router.callback_query(F.data == "game:guess")
async def cb_game_guess(callback: CallbackQuery) -> None:
    chat_id = callback.message.chat.id
    guess_targets[chat_id] = new_guess_target()
    await show_menu(callback, "🔢 Я загадал число от 1 до 10. Угадай!", guess_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("guess:"))
async def cb_guess_number(callback: CallbackQuery) -> None:
    chat_id = callback.message.chat.id
    guess = int(callback.data.split(":", 1)[1])
    target = guess_targets.get(chat_id)
    if target is None:
        target = new_guess_target()
        guess_targets[chat_id] = target

    correct, text = check_guess(target, guess)
    if correct:
        points = await db.add_points(chat_id, 5)
        guess_targets.pop(chat_id, None)
        await show_menu(
            callback,
            f"{text}\n⭐ +5 очков (всего: {points})",
            replay_keyboard("🔁 Сыграть снова", "game:guess"),
        )
    else:
        await show_menu(callback, text, guess_menu())
    await callback.answer()


# ----------------------------------------------------------------------------
# ИГРЫ: ВИКТОРИНА
# ----------------------------------------------------------------------------
@router.callback_query(F.data == "game:quiz")
async def cb_game_quiz(callback: CallbackQuery) -> None:
    q = random_quiz_question()
    await show_menu(callback, f"🧠 {q['question']}", quiz_keyboard(q["options"], q["correct"]))
    await callback.answer()


@router.callback_query(F.data.startswith("quiz:"))
async def cb_quiz_answer(callback: CallbackQuery) -> None:
    _, idx_str, correct_str = callback.data.split(":")
    idx, correct = int(idx_str), int(correct_str)
    chat_id = callback.message.chat.id

    if idx == correct:
        points = await db.add_points(chat_id, 3)
        text = f"✅ Верно! ⭐ +3 очка (всего: {points})"
    else:
        text = "❌ Не угадал в этот раз"

    await show_menu(callback, text, replay_keyboard("🔁 Ещё вопрос", "game:quiz"))
    await callback.answer()


# ----------------------------------------------------------------------------
# ЕЖЕДНЕВНАЯ РАССЫЛКА
# ----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("schedule:"))
async def cb_schedule(callback: CallbackQuery) -> None:
    value = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id

    if value == "off":
        await db.set_daily_time(chat_id, None)
        text = "🔇 Ежедневная рассылка выключена"
        current = None
    else:
        await db.set_daily_time(chat_id, value)
        text = f"✅ Буду присылать сюрприз каждый день в {value}"
        current = value

    await show_menu(callback, text, schedule_menu(current))
    await callback.answer()


async def send_daily(bot: Bot, chat_id: int) -> None:
    streak = await db.touch_activity(chat_id)
    await bot.send_message(
        chat_id,
        f"⏰ Доброе утро! Вот твой ежедневный заряд бодрости.\n🔥 Стрик: {streak} дн. подряд!",
    )
    category = random.choice(ALL_CATEGORIES)
    await deliver_content(bot, chat_id, category)


# ----------------------------------------------------------------------------
# ЛЮБОЕ ДРУГОЕ СООБЩЕНИЕ
# ----------------------------------------------------------------------------
@router.message(F.text)
async def on_any_text(message: Message) -> None:
    await db.get_or_create_user(message.chat.id, message.from_user.first_name or "")
    await db.touch_activity(message.chat.id)
    if random.random() < 0.4:
        await message.answer(random.choice(COMPLIMENTS))
    else:
        await message.answer("Если скучно — жми сюда 👇", reply_markup=main_menu(WEBAPP_URL))


# ----------------------------------------------------------------------------
# ТОЧКА ВХОДА
# ----------------------------------------------------------------------------
async def main() -> None:
    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = setup_scheduler(bot, send_daily)
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
