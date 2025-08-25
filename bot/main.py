# bot/main.py
import os
import sys
import logging
import asyncio
from typing import Dict

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import openai

# -------------------------
# Настройка логирования
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------------
# Проверка переменных окружения
# -------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not TELEGRAM_TOKEN:
    logger.error("Не задана переменная окружения TELEGRAM_BOT_TOKEN")
    sys.exit(1)

if not OPENAI_KEY:
    logger.warning("OPENAI_API_KEY не задан. Запросы к GPT будут возвращать ошибку.")

# Настройка OpenAI (sync client used via to_thread)
openai.api_key = OPENAI_KEY

# -------------------------
# Создание бота и диспетчера
# -------------------------
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# -------------------------
# Простая in-memory логика режима GPT
# (Для продакшна лучше использовать FSM/БД)
# -------------------------
# awaiting_gpt[user_id] = True означает, что следующий текст от пользователя
# будет отправлен в GPT (и флаг снимется).
awaiting_gpt: Dict[int, bool] = {}

# -------------------------
# Клавиатура (ReplyKeyboardMarkup)
# В aiogram v3 используем именованные параметры для моделей pydantic
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
# Хэндлер: всё входящие сообщения (маршрутизируем внутри)
# -------------------------
@dp.message()
async def all_messages_handler(message: types.Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    # Норма: если юзер в режиме ожидания GPT, то этот текст отправляем в модель
    if awaiting_gpt.get(user_id, False):
        # Если пользователь ввёл /menu — отменяем режим
        if text.lower() == "/menu":
            awaiting_gpt.pop(user_id, None)
            await message.answer("Режим подсказок отменён. Возвращаю в главное меню.", reply_markup=keyboard)
            return

        await message.answer("Отправляю запрос в GPT... (это может занять пару секунд)")
        try:
            # Используем asyncio.to_thread чтобы не блокировать event loop при sync вызове openai
            def call_openai_sync():
                # Синхронный клиент (openai.ChatCompletion.create) — вызывать в отдельном потоке
                resp = openai.ChatCompletion.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": text}],
                    temperature=0.7,
                )
                return resp

            resp = await asyncio.to_thread(call_openai_sync)

            # Безопасно извлекаем текст
            answer = ""
            try:
                answer = resp["choices"][0]["message"]["content"]
            except Exception:
                answer = str(resp)

            # Отправляем результат пользователю
            await message.answer(answer, reply_markup=keyboard)
        except Exception as e:
            logger.exception("Ошибка при запросе к OpenAI")
            await message.answer(f"Не удалось получить ответ от GPT: {e}", reply_markup=keyboard)
        finally:
            # Снимаем режим ожидания
            awaiting_gpt.pop(user_id, None)

        return  # обработка завершена

    # Если не в режиме GPT — обычная маршрутизация по меню/командам
    if text == "/start":
        await message.answer(
            "Привет! Я бот-помощник. Ниже — главное меню. Выбирайте 🚀",
            reply_markup=keyboard
        )
        return

    if text == "/menu":
        await message.answer("Главное меню:", reply_markup=keyboard)
        return

    # Меню через кнопки
    if text == "📊 Аналитика":
        # TODO: тут можно подключать аналитику соцсетей
        await message.answer("Здесь будет аналитика сообществ.", reply_markup=keyboard)
        return

    if text == "📝 Создать пост":
        # TODO: мастер создания постов, шаблоны и планирование
        await message.answer("Здесь можно будет создать пост для соцсетей.", reply_markup=keyboard)
        return

    if text == "⚙️ Настройки":
        # TODO: раздел настроек (язык, уведомления, интеграции)
        await message.answer("Раздел настроек.", reply_markup=keyboard)
        return

    if text == "ℹ️ Помощь":
        help_text = (
            "Справка по работе с ботом:\n"
            "• Кнопка «💡 Подсказка» — начать диалог с GPT.\n"
            "• В режиме GPT просто отправь вопрос, бот пришлёт ответ модели.\n"
            "• Команда /menu — вернуть главное меню.\n"
            "• Команда /start — приветственное сообщение.\n"
        )
        await message.answer(help_text, reply_markup=keyboard)
        return

    if text == "💡 Подсказка":
        # Включаем режим ожидания следующего сообщения как запроса для GPT
        awaiting_gpt[user_id] = True
        await message.answer(
            "Режим подсказок GPT активирован. Напишите ваш вопрос.\n"
            "Чтобы выйти, отправьте /menu.",
            reply_markup=keyboard
        )
        return

    # Если сообщение не распознано — подсказка по командам
    await message.answer(
        "Я не понял сообщение. Используйте меню или /help для справки.",
        reply_markup=keyboard
    )

# -------------------------
# Запуск бота
# -------------------------
async def main():
    logger.info("Запуск бота...")
    # Указываем bot в polling, чтобы Telegram-сообщения доставлялись
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
