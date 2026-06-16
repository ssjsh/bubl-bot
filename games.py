"""
Логика мини-игр: камень-ножницы-бумага и угадай число.
"""

import random

RPS_OPTIONS = {
    "rock": "🪨 Камень",
    "scissors": "✂️ Ножницы",
    "paper": "📄 Бумага",
}

# Что побеждает что: ключ побеждает значение
RPS_WINS = {
    "rock": "scissors",
    "scissors": "paper",
    "paper": "rock",
}


def play_rps(user_choice: str) -> tuple[str, str]:
    """Возвращает (выбор бота, текст результата)."""
    bot_choice = random.choice(list(RPS_OPTIONS.keys()))

    if user_choice == bot_choice:
        result = "Ничья! 🤝 Сыграем ещё раз?"
    elif RPS_WINS[user_choice] == bot_choice:
        result = "Ты победил! 🎉"
    else:
        result = "Бот победил в этот раз 😏 Реванш?"

    text = (
        f"Ты выбрал: {RPS_OPTIONS[user_choice]}\n"
        f"Бот выбрал: {RPS_OPTIONS[bot_choice]}\n\n"
        f"{result}"
    )
    return bot_choice, text


def new_guess_target(low: int = 1, high: int = 10) -> int:
    return random.randint(low, high)


def check_guess(target: int, guess: int) -> tuple[bool, str]:
    if guess == target:
        return True, f"🎯 Угадал! Это было число {target}!"
    elif guess < target:
        return False, "Больше! Попробуй ещё 👆"
    else:
        return False, "Меньше! Попробуй ещё 👇"
