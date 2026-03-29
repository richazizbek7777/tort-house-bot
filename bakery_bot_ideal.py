import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

BOT_TOKEN = "8738414496:AAGP29DR-pdHMUX5ZnMaFNIdH_NM-ZxHCu4"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎂 Zakaz berish")],
            [KeyboardButton(text="📋 Narx va ma'lumot"), KeyboardButton(text="📞 Aloqa")],
        ],
        resize_keyboard=True,
    )

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Assalomu alaykum! 👋\n"
        "<b>Tort House</b> ga xush kelibsiz.",
        reply_markup=main_keyboard(),
    )

@dp.message(F.text == "📋 Narx va ma'lumot")
async def info_handler(message: Message):
    await message.answer("Narxlar admin tomonidan belgilanadi.")

@dp.message(F.text == "📞 Aloqa")
async def contact_handler(message: Message):
    await message.answer("Aloqa: +998 99 845 56 51")

@dp.message(F.text == "🎂 Zakaz berish")
async def order_handler(message: Message):
    await message.answer("Zakaz bo'limi ishladi ✅")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())