import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

BOT_TOKEN = "8738414496:AAGP29DR-pdHMUX5ZnMaFNIdH_NM-ZxHCu4"

PRODUCT_CATALOG = {
    "Tort": {
        "Oddiy tortlar": [
            "Bento",
            "Bento konteyner",
            "Yurakchali",
            "Mini-oq/shokoladli",
            "Mini 2 qavatli oq/shokoladli",
            "O'rta oq/shokoladli",
            "Kvadrat 2 qavatli oq/shokoladli",
            "Kvadrat 3 qavatli oq/shokoladli",
            "Katta tortburchak 2 qavatli oq/shokoladli",
            "Katta tortburchak 3 qavatli oq/shokoladli",
        ],
        "Premium tortlar": [
            "Snikersli",
            "Bagatiy",
            "Gumbaz",
            "Mevali",
            "Rafaello",
            "Yagodniy",
            "Izabello malinali",
            "Izabello",
            "Bakalashka qulupnay",
            "Bakalashka snikers",
        ],
    },
    "Trayfel": {
        "Trayfel turlari": [
            "Mitti trayfel",
            "Kichik trayfel",
            "Katta trayfel",
            "Mevali trayfel",
        ],
    },
    "Pirojniy": {
        "Pirojniy turlari": [
            "Fistacho",
            "Maxroviy",
            "Jiyan",
            "Ptichi moloko",
            "Monaco",
            "Mars",
        ],
    },
}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


class OrderStates(StatesGroup):
    category = State()
    product = State()


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎂 Zakaz berish")],
            [KeyboardButton(text="📋 Narx va ma'lumot"), KeyboardButton(text="📞 Aloqa")],
        ],
        resize_keyboard=True,
    )


def category_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Tort"), KeyboardButton(text="Trayfel")],
            [KeyboardButton(text="Pirojniy")],
            [KeyboardButton(text="🏠 Menu")],
        ],
        resize_keyboard=True,
    )


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Ortga")]],
        resize_keyboard=True,
    )


def flatten_variants(category: str) -> list[str]:
    result = []
    for items in PRODUCT_CATALOG.get(category, {}).values():
        result.extend(items)
    return result


def build_variant_text(category: str) -> str:
    groups = PRODUCT_CATALOG.get(category, {})
    lines = [f"<b>{category} bo'limidagi turlar:</b>"]
    idx = 1
    for group_name, items in groups.items():
        lines.append(group_name)
        for item in items:
            lines.append(f"{idx}. {item}")
            idx += 1
    lines.append("Keraklisini yozing yoki raqamini yuboring.")
    return "\n".join(lines)


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Assalomu alaykum! 👋\n<b>Tort House</b> ga xush kelibsiz.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "📋 Narx va ma'lumot")
async def info_handler(message: Message):
    await message.answer("Narxlar admin tomonidan belgilanadi.")


@dp.message(F.text == "📞 Aloqa")
async def contact_handler(message: Message):
    await message.answer("Aloqa: +998 99 845 56 51")


@dp.message(F.text == "🎂 Zakaz berish")
async def order_handler(message: Message, state: FSMContext):
    await state.set_state(OrderStates.category)
    await message.answer("Mahsulot turini tanlang:", reply_markup=category_keyboard())


@dp.message(F.text == "🏠 Menu")
async def menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menu.", reply_markup=main_keyboard())


@dp.message(OrderStates.category, F.text.in_(["Tort", "Trayfel", "Pirojniy"]))
async def category_select_handler(message: Message, state: FSMContext):
    category = message.text.strip()
    await state.update_data(category=category)
    await state.set_state(OrderStates.product)
    await message.answer(build_variant_text(category), reply_markup=back_keyboard())


@dp.message(OrderStates.product)
async def product_select_handler(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == "🔙 Ortga":
        await state.set_state(OrderStates.category)
        await message.answer("Mahsulot turini tanlang:", reply_markup=category_keyboard())
        return

    data = await state.get_data()
    category = data.get("category", "")
    variants = flatten_variants(category)

    selected_product = None

    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(variants):
            selected_product = variants[idx]
    else:
        for item in variants:
            if text.lower() == item.lower():
                selected_product = item
                break

    if not selected_product:
        await message.answer("Raqam yoki nomni to'g'ri yuboring.")
        return

    await message.answer(
        f"Tanlandi: <b>{selected_product}</b>\n✅ Mahsulot tanlash ishladi.",
        reply_markup=main_keyboard(),
    )
    await state.clear()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())