# bot/main.py
import os
import sys
import logging
import asyncio
from typing import Dict, List

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Импортируем адаптер LLM
from bot.services.llm_client import ask as llm_ask

# -------------------------
# Логирование
# -------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# -------------------------
# Переменные окружения
# -------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")  # опционально
HF_MODEL = os.getenv("HF_MODEL", "bigscience/bloomz-1b1")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", (
    "Ты — полезный, вежливый и краткий помощник, который помогает пользователю работать с Telegram-ботом. "
    "Отвечай по-русски, давай практичные рекомендации и примеры, и предлагай следующий шаг."
))

if not TELEGRAM_TOKEN:
    logger.error("Не задана переменная окружения TELEGRAM_BOT_TOKEN")
    sys.exit(1)

# -------------------------
# Telegram bot / dispatcher
# -------------------------
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# In-memory режим для ожидания запроса к LLM
awaiting_llm: Dict[int, bool] = {}

# Reply keyboard
keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="📊 Аналитика"), KeyboardButton(text="📝 Создать пост")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="💡 Подсказка")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    input_field_placeholder="Выберите действие..."
)

# Хендлер всех сообщений (маршрутизация внутри)
@dp.message()
async def all_messages_handler(message: types.Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    # Если пользователь находится в режиме LLM — отправляем текст на обработку
    if awaiting_llm.get(user_id, False):
        if text.lower() == "/menu":
            awaiting_llm.pop(user_id, None)
            await message.answer("Режим подсказок отменён. Возвращаю в главное меню.", reply_markup=keyboard)
            return

        await message.answer("Обрабатываю ваш запрос... (несколько секунд)")

        # Собираем messages в формате chat
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]

        try:
            answer = await llm_ask(messages)
            await message.answer(answer, reply_markup=keyboard)
        except Exception as e:
            logger.exception("Ошибка при запросе в LLM")
            await message.answer(f"Не удалось получить ответ от LLM: {e}", reply_markup=keyboard)
        finally:
            awaiting_llm.pop(user_id, None)
        return

    # Обработка команд / меню
    if text == "/start":
        await message.answer("Привет! Я бот-помощник. Ниже — главное меню. Выбирайте 🚀", reply_markup=keyboard)
        return

    if text == "/menu":
        await message.answer("Главное меню:", reply_markup=keyboard)
        return

    if text == "📊 Аналитика":
        await message.answer("Здесь будет аналитика сообществ.", reply_markup=keyboard)
        return

    if text == "📝 Создать пост":
        await message.answer("Здесь можно будет создать пост для соцсетей.", reply_markup=keyboard)
        return

    if text == "⚙️ Настройки":
        await message.answer("Раздел настроек.", reply_markup=keyboard)
        return

    if text == "ℹ️ Помощь":
        help_text = (
            "Справк
