import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import openai
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем токены из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

openai.api_key = OPENAI_KEY

# Клавиатура
keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton("📊 Аналитика"), KeyboardButton("📝 Создать пост")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("💡 Подсказка")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
)

# Хэндлер /start
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer("Привет! Выберите пункт меню:", reply_markup=keyboard)

# Хэндлер кнопок
@dp.message_handler(lambda message: message.text in ["📊 Аналитика", "📝 Создать пост",
                                                   "⚙️ Настройки", "💡 Подсказка", "ℹ️ Помощь"])
async def menu_handler(message: types.Message):
    text = message.text
    if text == "📊 Аналитика":
        await message.answer("Здесь будет аналитика сообществ.")
    elif text == "📝 Создать пост":
        await message.answer("Здесь можно будет создать пост для соцсетей.")
    elif text == "⚙️ Настройки":
        await message.answer("Раздел настроек.")
    elif text == "ℹ️ Помощь":
        await message.answer("Справка по работе с ботом.")
    elif text == "💡 Подсказка":
        await message.answer("Напишите ваш вопрос, я передам его GPT.")

        # Ставим бота в режим ожидания следующего сообщения как запроса к GPT
        @dp.message_handler()
        async def gpt_handler(msg: types.Message):
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": msg.text}]
            )
            answer = response['choices'][0]['message']['content']
            await msg.answer(answer)

# Запуск бота
if __name__ == "__main__":
    print("Bot is starting...")
    executor.start_polling(dp, skip_updates=True)

