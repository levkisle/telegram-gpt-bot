# bot/main.py
import os
import sys
import logging
import asyncio
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Новый OpenAI-клиент (openai>=1.0.0)
from openai import OpenAI

# -------------------------
# Логирование
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------------
# Переменные окружения
# -------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not TELEGRAM_TOKEN:
    logger.error("Не задана переменная окружения TELEGRAM_BOT_TOKEN")
    sys.exit(1)

if not OPENAI_KEY:
    logger.warning("OPENAI_API_KEY не задан. Запросы к GPT будут недоступны.")

# -------------------------
# Инициализация OpenAI client (v1+)
# -------------------------
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# -------------------------
# Telegram bot / dispatcher (aiogram v3)
# -------------------------
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Простая in-memory логика режима GPT (для производства лучше FSM/БД)
awaiting_gpt: Dict[int, bool] = {}

# -------------------------
# ReplyKeyboardMarkup (aiogram v3: pydantic models use named args)
# -------------------------
keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="📊 Аналитика"), KeyboardButton(text="📝 Создать пост")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="💡 Подсказка")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    input_field_placeholder="Выберите действие..."
)

# -------------------------
# Утилиты для извлечения ответа из OpenAI-объекта
# -------------------------
def extract_chat_completion_text(resp: Any) -> str:
    """
    Пытаемся корректно извлечь content из ответа client.chat.completions.create(...)
    Поддерживаем несколько возможных форматов.
    """
    try:
        # dict-like
        return resp["choices"][0]["message"]["content"]
    except Exception:
        pass

    try:
        # attribute-like
        choice = getattr(resp, "choices", None)
        if choice:
            first = choice[0]
            msg = getattr(first, "message", None)
            if msg:
                return getattr(msg, "content", str(resp))
    except Exception:
        pass

    # fallback — строковое представление
    return str(resp)

# -------------------------
# Общий обработчик сообщений
# -------------------------
@dp.message()
async def all_messages_handler(message: types.Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    # Если пользователь находится в режиме "подсказок" — отправляем сообщение в GPT
    if awaiting_gpt.get(user_id, False):
        if text.lower() == "/menu":
            awaiting_gpt.pop(user_id, None)
            await message.answer("Режим подсказок отменён. Возвращаю в главное меню.", reply_markup=keyboard)
            return

        await message.answer("Отправляю запрос в GPT... (может занять пару секунд)")

        if client is None:
            await message.answer("OpenAI не настроен (OPENAI_API_KEY не задан).", reply_markup=keyboard)
            awaiting_gpt.pop(user_id, None)
            return

        try:
            # Выполняем вызов OpenAI client в отдельном потоке, чтобы не блокировать event loop
            def call_openai_sync(local_text: str):
                # Используем Chat Completions интерфейс клиента v1.x
                return client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": local_text}],
                    temperature=0.7,
                )

            resp = await asyncio.to_thread(call_openai_sync, text)
            answer = extract_chat_completion_text(resp)
            await message.answer(answer, reply_markup=keyboard)
        except Exception as e:
            logger.exception("Ошибка при запросе к OpenAI")
            await message.answer(f"Не удалось получить ответ от GPT: {e}", reply_markup=keyboard)
        finally:
            awaiting_gpt.pop(user_id, None)
        return

    # Если не в режиме GPT — обычная маршрутизация
    if text == "/start":
        await message.answer("Привет! Я бот-помощник. Ниже — главное меню. Выбирайте 🚀", reply_markup=keyboard)
        return

    if text == "/menu":
        await message.answer("Главное меню:", reply_markup=keyboard)
        return

    if text == "📊 Аналитика":
        # TODO: подключить аналитику соцсетей
        await message.answer("Здесь будет аналитика сообществ.", reply_markup=keyboard)
        return

    if text == "📝 Создать пост":
        # TODO: мастер создания/планировщик постов
        await message.answer("Здесь можно будет создать пост для соцсетей.", reply_markup=keyboard)
        return

    if text == "⚙️ Настройки":
        # TODO: настройки пользователя
        await message.answer("Раздел настроек.", reply_markup=keyboard)
        return

    if text == "ℹ️ Помощь":
        help_text = (
            "Справка по работе с ботом:\n"
            "• Кнопка «💡 Подсказка» — начать диалог с GPT.\n"
            "• В режиме GPT: просто отправь вопрос, бот пришлёт ответ модели.\n"
            "• Команда /menu — вернуть главное меню.\n"
            "• Команда /start — приветственное сообщение.\n"
        )
        await message.answer(help_text, reply_markup=keyboard)
        return

    if text == "💡 Подсказка":
        awaiting_gpt[user_id] = True
        await message.answer(
            "Режим подсказок GPT активирован. Напишите ваш вопрос.\nЧтобы выйти — отправьте /menu.",
            reply_markup=keyboard
        )
        return

    # Не распознано
    await message.answer("Я не понял сообщение. Используйте главное меню или /help.", reply_markup=keyboard)

# -------------------------
# Запуск бота
# -------------------------
async def main():
    logger.info("Запуск бота...")
    # Запускаем long polling — процесс не завершится
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
