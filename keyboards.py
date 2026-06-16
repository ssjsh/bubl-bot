"""
Все inline-клавиатуры бота в одном месте.
"""

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from content import ZODIAC_SIGNS

# ----------------------------------------------------------------------------
# ГЛАВНОЕ МЕНЮ
# ----------------------------------------------------------------------------
def main_menu(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🐱 Котик", callback_data="content:cat"),
                InlineKeyboardButton(text="🐶 Песик", callback_data="content:dog"),
            ],
            [
                InlineKeyboardButton(text="😂 Мем", callback_data="content:meme"),
                InlineKeyboardButton(text="🎞 Гифка", callback_data="content:gif"),
            ],
            [
                InlineKeyboardButton(text="🃏 Анекдот", callback_data="content:joke"),
                InlineKeyboardButton(text="💬 Цитата", callback_data="content:quote"),
            ],
            [
                InlineKeyboardButton(text="🧠 Факт", callback_data="content:fact"),
                InlineKeyboardButton(text="💌 Тёплые слова", callback_data="content:warm"),
            ],
            [
                InlineKeyboardButton(text="🎲 Сюрприз", callback_data="content:surprise"),
                InlineKeyboardButton(text="📁 Мои файлы", callback_data="content:local"),
            ],
            [
                InlineKeyboardButton(text="🔮 Гороскоп", callback_data="menu:zodiac"),
                InlineKeyboardButton(text="🎮 Игры", callback_data="menu:games"),
            ],
            [
                InlineKeyboardButton(text="😊 Настроение", callback_data="menu:mood"),
                InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
            ],
            [
                InlineKeyboardButton(text="⏰ Ежедневная рассылка", callback_data="menu:schedule"),
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Открыть приложение",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
        ]
    )


def back_to_menu_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")


def replay_keyboard(label: str, callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=callback_data)],
            [back_to_menu_button()],
        ]
    )


# ----------------------------------------------------------------------------
# ОЦЕНКА КОНТЕНТА + ПОДЕЛИТЬСЯ
# ----------------------------------------------------------------------------
def content_keyboard(category: str, share_text: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="👍", callback_data=f"rate:{category}:1"),
            InlineKeyboardButton(text="👎", callback_data=f"rate:{category}:0"),
        ]
    ]
    if share_text:
        url = f"https://t.me/share/url?url={quote(share_text)}"
        rows.append([InlineKeyboardButton(text="↗️ Поделиться", url=url)])
    rows.append([back_to_menu_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ----------------------------------------------------------------------------
# НАСТРОЕНИЕ
# ----------------------------------------------------------------------------
MOOD_MAP = {
    "happy": ("😄", "Отлично, давай продолжать в том же духе!", "surprise"),
    "sad": ("😢", "Хочу немного тебя поддержать", "warm"),
    "angry": ("😡", "Кажется, нужно немного разрядки", "meme"),
    "tired": ("🥱", "Тут что-то спокойное и тёплое", "warm"),
    "bored": ("🥳", "Сейчас разгоним скуку!", "surprise"),
}


def mood_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="😄 Хорошо", callback_data="mood:happy"),
                InlineKeyboardButton(text="😢 Грустно", callback_data="mood:sad"),
            ],
            [
                InlineKeyboardButton(text="😡 Раздражена", callback_data="mood:angry"),
                InlineKeyboardButton(text="🥱 Устала", callback_data="mood:tired"),
            ],
            [
                InlineKeyboardButton(text="🥳 Скучно", callback_data="mood:bored"),
            ],
            [back_to_menu_button()],
        ]
    )


# ----------------------------------------------------------------------------
# ГОРОСКОП
# ----------------------------------------------------------------------------
def zodiac_menu() -> InlineKeyboardMarkup:
    keys = list(ZODIAC_SIGNS.items())
    rows = []
    for i in range(0, len(keys), 3):
        row = [
            InlineKeyboardButton(text=name, callback_data=f"zodiac:{key}")
            for key, name in keys[i : i + 3]
        ]
        rows.append(row)
    rows.append([back_to_menu_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ----------------------------------------------------------------------------
# ИГРЫ
# ----------------------------------------------------------------------------
def games_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✊✋✌️ Камень-ножницы-бумага", callback_data="game:rps")],
            [InlineKeyboardButton(text="🔢 Угадай число", callback_data="game:guess")],
            [InlineKeyboardButton(text="🧠 Викторина", callback_data="game:quiz")],
            [back_to_menu_button()],
        ]
    )


def rps_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🪨 Камень", callback_data="rps:rock"),
                InlineKeyboardButton(text="✂️ Ножницы", callback_data="rps:scissors"),
                InlineKeyboardButton(text="📄 Бумага", callback_data="rps:paper"),
            ],
            [back_to_menu_button()],
        ]
    )


def guess_menu(low: int = 1, high: int = 10) -> InlineKeyboardMarkup:
    numbers = [
        InlineKeyboardButton(text=str(n), callback_data=f"guess:{n}")
        for n in range(low, high + 1)
    ]
    rows = [numbers[i : i + 5] for i in range(0, len(numbers), 5)]
    rows.append([back_to_menu_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_keyboard(options: list[str], correct: int) -> InlineKeyboardMarkup:
    rows = []
    for idx, option in enumerate(options):
        rows.append(
            [InlineKeyboardButton(text=option, callback_data=f"quiz:{idx}:{correct}")]
        )
    rows.append([back_to_menu_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ----------------------------------------------------------------------------
# ЕЖЕДНЕВНАЯ РАССЫЛКА
# ----------------------------------------------------------------------------
SCHEDULE_TIMES = ["08:00", "12:00", "18:00", "21:00"]


def schedule_menu(current: str | None) -> InlineKeyboardMarkup:
    rows = []
    for t in SCHEDULE_TIMES:
        mark = " ✅" if t == current else ""
        rows.append([InlineKeyboardButton(text=f"{t}{mark}", callback_data=f"schedule:{t}")])
    rows.append([InlineKeyboardButton(text="🔇 Выключить", callback_data="schedule:off")])
    rows.append([back_to_menu_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)
