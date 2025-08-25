import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
import openai
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Логирование
logging.basicConfig(level=logging.INFO)

# Получаем токены из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

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

# /start и меню
@dp.message()
async def menu_handler(message: types.Message):
    text = message.text

    if text == "/start":
        await message.answer("Привет! Выберите пункт меню:", reply_markup=keyboard)
    elif text == "📊 Аналитика":
        await message.answer("Здесь будет аналитика сообществ.")
    elif text == "📝 Создать пост":
        await message.answer("Здесь можно будет создать пост для соцсетей.")
    elif text == "⚙️ Настройки":
        await message.answer("Раздел настроек.")
    elif text == "ℹ️ Помощь":
        await message.answer("Справка по работе с ботом.")
    elif text == "💡 Подсказка":
        await message.answer("Напишите ваш вопрос, я передам его GPT.")

        # Следующее сообщение пользователя будет отправлено в GPT
        @dp.message()
        async def gpt_handler(msg: types.Message):
            try:
                response = openai.ChatCompletion.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": msg.text}]
                )
                answer = response['choices'][0]['message']['content']
                await msg.answer(answer)
            except Exception as e:
                await msg.answer(f"Произошла ошибка при обращении к GPT:\n{e}")

# Запуск бота
async def main():
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

