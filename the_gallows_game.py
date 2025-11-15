# pip install pyTelegramBotAPI

import os
import random
from collections import Counter
import telebot

token = os.getenv("YOUR_BOT_TOKEN")

bot = telebot.TeleBot(token)

WORD_LIST_PATH = os.path.join(os.path.dirname(__file__), "russian_nouns.txt")

with open(WORD_LIST_PATH, encoding="utf-8") as words_file:
    WORD_LIST = [
        word.upper()
        for word in (line.strip() for line in words_file)
        if 4 < len(word) < 11
    ]

HANGMAN_STAGES = [
    """
               --------
               |      |
               |      O
               |     \\|/
               |      |
               |     / \\
               -
            """,
    """
               --------
               |      |
               |      O
               |     \\|/
               |      |
               |     /
               -
            """,
    """
               --------
               |      |
               |      O
               |     \\|/
               |      |
               |
               -
            """,
    """
               --------
               |      |
               |      O
               |     \\|
               |      |
               |
               -
            """,
    """
               --------
               |      |
               |      O
               |      |
               |      |
               |
               -
            """,
    """
               --------
               |      |
               |      O
               |
               |
               |
               -
            """,
    """
               --------
               |      |
               |
               |
               |
               |
               -
            """,
]

games = {}

# Возвращает случайное слово из подготовленного списка русских существительных
def get_word():
    return random.choice(WORD_LIST)

# Подбирает ASCII-стадию виселицы, соответствующую количеству оставшихся попыток
def display_hangman(tries):
    return HANGMAN_STAGES[tries]

# Преобразует текущее состояние слова в строку с пробелами между символами
def render_state(state):
    return " ".join(state)

# Частично раскрывает слово, чтобы уменьшить сложность первых ходов
def reveal_initial_letters(word, count=2):

    if not word:
        return ["_"], set()

    letter_counter = Counter(word)
    target = min(count, len(set(word)))

    unique_letter_indices = [index for index, letter in enumerate(word) if letter_counter[letter] == 1]
    random.shuffle(unique_letter_indices)
    selected_indices = unique_letter_indices[:target]
    used_letters = {word[i] for i in selected_indices}

    if len(selected_indices) < target:
        indices = list(range(len(word)))
        random.shuffle(indices)
        for index in indices:
            letter = word[index]
            if letter in used_letters:
                continue
            selected_indices.append(index)
            used_letters.add(letter)
            if len(selected_indices) == target:
                break

    state = ["_"] * len(word)
    for index in selected_indices:
        state[index] = word[index]

    if len(used_letters) < count:
        state = [letter if letter in used_letters else "_" for letter in word]

    return state, used_letters

# Проверяет, что строка состоит исключительно из символов русского алфавита
def is_russian(text):
    return all("А" <= ch <= "Я" or ch == "Ё" for ch in text)

# Инициализирует новое игровое состояние
def start_game(chat_id):
    word = get_word()
    state, revealed_letters = reveal_initial_letters(word)
    games[chat_id] = {
        "word": word,
        "tries": 6,
        "guessed_letters": set(revealed_letters),
        "guessed_words": set(),
        "state": state,
        "status": "playing",
    }
    bot.send_message(
        chat_id,
        "\n".join(
            [
                "Игра началась! Угадай слово по буквам или целиком",
                display_hangman(6),
                render_state(games[chat_id]["state"]),
                f"Осталось попыток: {games[chat_id]['tries']}",
            ]
        ),
    )
    if "_" not in games[chat_id]["state"]:
        handle_win(chat_id)

# Обрабатывает команду /start и выводит краткое описание бота и доступных команд
@bot.message_handler(commands=["start"])
def help_handler(message):
    bot.send_message(
        message.chat.id,
        "Привет! Это бот, с которым можно сыграть в игру «Виселица» 𓍯. Правила: необходимо присылать буквы, чтобы угадать слово, также можно попытаться угадать слово целиком.\n"
        "Доступные команды:\n"
        "/help - вывести список доступных команд\n"
        "/new - начать новую игру\n"
        "/stop - завершить текущую игру\n"
    )

# Обрабатывает команду /help и повторяет перечень поддерживаемых ботом команд
@bot.message_handler(commands=["help"])
def help_handler(message):
    bot.send_message(
        message.chat.id,
        "Доступные команды:\n"
        "/help - вывести список доступных команд\n"
        "/new - начать новую игру\n"
        "/stop - завершить текущую игру\n"
    )

# Запускает новую игру по команде /new, сбрасывая состояние предыдущей партии
@bot.message_handler(commands=["new"])
def new_game(message):
    start_game(message.chat.id)

# Принудительно завершает текущую игру 
@bot.message_handler(commands=["stop"])
def stop_game(message):
    chat_id = message.chat.id
    if chat_id in games:
        del games[chat_id]
        bot.send_message(chat_id, "Игра остановлена. Чтобы начать заново, отправьте /new")
    else:
        bot.send_message(chat_id, "Сейчас игра не запущена. Используйте /new, чтобы начать")

# Переводит игру в состояние ожидания и информирует пользователя о поражении
def handle_loss(chat_id):
    game = games.get(chat_id)
    if not game:
        return
    game["status"] = "await_restart"
    word = game["word"]
    bot.send_message(
        chat_id,
        "\n".join(
            [
                f"К сожалению, вы проиграли.☠️ Загаданное слово: {word}\n",
                "Хотите сыграть еще раз? (ответьте да или нет)",
            ]
        ),
    )

# Переводит игру в состояние ожидания и поздравляет пользователя с победой
def handle_win(chat_id):
    game = games.get(chat_id)
    if not game:
        return
    game["status"] = "await_restart"
    word = game["word"]
    bot.send_message(
        chat_id,
        f"Поздравляю!🎉 Вы угадали слово: {word}\n\nХотите сыграть еще раз? (ответьте да или нет)",
    )

# Центральный обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True, content_types=["text"])
def game_handler(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text.startswith("/"):
        return

    if not text:
        bot.send_message(chat_id, "Отправьте букву или слово.")
        return

    if chat_id not in games:
        bot.send_message(chat_id, "Сначала начните игру командой /new.")
        return

    game = games[chat_id]

    if game.get("status") == "await_restart":
        answer = text.lower()
        if answer == "да":
            start_game(chat_id)
        elif answer == "нет":
            bot.send_message(chat_id, "Игра завершена. Возвращайтесь, когда захотите сыграть снова!👋")
            del games[chat_id]
        else:
            bot.send_message(chat_id, "Пожалуйста, ответьте да или нет")
        return

    if not text.isalpha():
        bot.send_message(chat_id, "Требуется ввести букву или слово (только буквы).")
        return

    if not is_russian(text.upper()):
        bot.send_message(chat_id, "Пожалуйста, используйте только русские буквы.")
        return
    text = text.upper()

    if len(text) == 1:
        if text in game["guessed_letters"]:
            bot.send_message(chat_id, "Эту букву уже называли, попробуйте другую 🤔")
            return

        game["guessed_letters"].add(text)

        if text in game["word"]:
            for index, letter in enumerate(game["word"]):
                if letter == text:
                    game["state"][index] = text

            bot.send_message(
                chat_id,
                "\n".join(
                    [
                        "Вы угадали букву!🤓",
                        render_state(game["state"]),
                        f"Осталось попыток: {game['tries']}",
                    ]
                ),
            )

            if "_" not in game["state"]:
                handle_win(chat_id)
            return

        game["tries"] -= 1
        bot.send_message(
            chat_id,
            "\n".join(
                [
                    "Вы не угадали 😟",
                    display_hangman(game["tries"]),
                    render_state(game["state"]),
                    f"Осталось попыток: {game['tries']}",
                ]
            ),
        )

        if game["tries"] == 0:
            handle_loss(chat_id)
        return

    if text in game["guessed_words"]:
        bot.send_message(chat_id, "Это слово уже называли, попробуйте другое 🤔")
        return

    game["guessed_words"].add(text)

    if text == game["word"]:
        game["state"] = list(game["word"])
        handle_win(chat_id)
        return

    game["tries"] -= 1
    bot.send_message(
        chat_id,
        "\n".join(
            [
                "Неверное слово 😟",
                display_hangman(game["tries"]),
                render_state(game["state"]),
                f"Осталось попыток: {game['tries']}",
            ]
        ),
    )

    if game["tries"] == 0:
        handle_loss(chat_id)


bot.infinity_polling()