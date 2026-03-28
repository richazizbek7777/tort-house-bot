
import asyncio
import json
import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================================================
# ⚙️ CONFIG
# =========================================================

def env_str(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or default).strip()


def env_int_set(name: str, default: str = "") -> set[int]:
    raw = env_str(name, default)
    values: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            values.add(int(part))
    return values


BOT_TOKEN = env_str("8738414496:AAGq2O2jvel8wVmX9hdYigHpJtc1pLT5FvE")
ADMIN_IDS = env_int_set("ADMIN_IDS", "1031944247,7410870199")
SUPER_ADMIN_IDS = env_int_set("SUPER_ADMIN_IDS", "1031944247")

CARD_NUMBER = env_str("CARD_NUMBER", "9860 1201 0248 9743")
CARD_OWNER = env_str("CARD_OWNER", "Asadbek T")
CARD_TEXT = f"💳 Zakolat uchun karta:\n👤 {CARD_OWNER}\n<code>{CARD_NUMBER}</code>"
PHONE_TEXT = env_str("PHONE_TEXT", "+998 99 845 56 51\n+998 94 368 00 06")
TELEGRAM_TEXT = env_str("TELEGRAM_TEXT", "@tort_house_chartak")
WORK_TIME_TEXT = env_str("WORK_TIME_TEXT", "08:00 - 00:00")
DB_NAME = env_str("DB_NAME", "bakery_torthouse_style.db")
PAYME_URL = env_str("PAYME_URL")
CLICK_URL = env_str("CLICK_URL")
UZUM_URL = env_str("UZUM_URL")
BRAND_TEXT = env_str("BRAND_TEXT", "🍰 Tort House")

STATUS_WAITING_PRICE = "waiting_price"
STATUS_PRICED = "priced"
STATUS_AWAITING_DEPOSIT_CHECK = "awaiting_deposit_check"
STATUS_DEPOSIT_SENT = "deposit_sent"
STATUS_CONFIRMED = "confirmed"
STATUS_CANCELLED = "cancelled"
STATUS_READY = "ready"
STATUS_DELIVERED = "delivered"

# =========================================================
# 📚 PRODUCT CATALOG
# =========================================================

PRODUCT_CATALOG: dict[str, dict[str, Any]] = {
    "Tort": {
        "groups": {
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
        "needs_design": True,
        "needs_color": True,
        "needs_filling": True,
        "needs_text": True,
        "quantity_hint": "Masalan: 1 dona, 10 kishilik",
    },
    "Pirojniy": {
        "groups": {
            "Oddiy pirojniylar": [
                "Fistacho",
                "Maxroviy",
                "Jiyan",
                "Ptichi moloko",
                "Monaco",
                "Mars",
            ],
            "Mevali pirojniylar": [
                "Yagodniy pirojniy",
                "Qulupnayli pirojniy",
                "Malinali pirojniy",
                "Ice Cake qulupnayli",
                "Ice Cake malinali",
                "Ice Cake anorli",
                "Ice Cake Gilosli",
            ],
            "Premium pirojniylar": [
                "Matilda pirojniy",
                "Pistali pirojniy",
                "Sansebastian Pistali",
                "Medovik pirojniy",
                "Snikers pirojniy",
            ],
            "Rulet va konteyner": [
                "Mars konteyner",
                "Makli oq rulet",
                "Tvarogli rulet",
                "Tvarogli momiq",
            ],
        },
        "needs_design": False,
        "needs_color": False,
        "needs_filling": False,
        "needs_text": False,
        "quantity_hint": "Masalan: 1 dona",
    },
    "Trayfel": {
        "groups": {
            "Trayfel turlari": [
                "Mitti trayfel",
                "Kichik trayfel",
                "Katta trayfel",
                "Mevali trayfel",
            ],
        },
        "needs_design": False,
        "needs_color": False,
        "needs_filling": False,
        "needs_text": False,
        "quantity_hint": "Masalan: 1 dona, 2 dona, 5 dona",
    },
    "Somsa": {
        "groups": {
            "Go'shtli": ["Go'shtli", "Tovuqli"],
            "Sabzavotli": ["Oshqovoqli", "Ko'katli", "Kartoshkali"],
        },
        "needs_design": False,
        "needs_color": False,
        "needs_filling": False,
        "needs_text": False,
        "quantity_hint": "Masalan: 5 dona, 10 dona, 20 dona",
    },
    "Kruassan": {
        "groups": {
            "Kruassan turlari": ["Marojnali", "Shokoladli", "Qulupnayli"],
        },
        "needs_design": False,
        "needs_color": False,
        "needs_filling": False,
        "needs_text": False,
        "quantity_hint": "Masalan: 1 dona, 3 dona, 6 dona",
    },
    "Ichimliklar": {
        "groups": {
            "Salqin ichimliklar": ["Cola", "Fanta", "Pepsi", "Sok", "Gazsiz suv"],
            "Kofelar": ["Cappucino", "Latte", "Espresso", "Americano", "Cappucino Uno"],
            "Choylar": ["Karak choy", "Malina choy", "Limon choy", "Sitrus choy", "Ko'k/Qora choy", "Bardak choy"],
        },
        "needs_design": False,
        "needs_color": False,
        "needs_filling": False,
        "needs_text": False,
        "quantity_hint": "Masalan: 1 dona, 2 litr, 3 stakan",
    },
    "Muzqaymoq": {
        "groups": {
            "Mevali": ["Malinali", "Qulupnayli", "Qovunli", "Olchali"],
            "Klassik": ["Shokoladli", "Pistali", "Karamelli", "Qaymoqli"],
        },
        "needs_design": False,
        "needs_color": False,
        "needs_filling": False,
        "needs_text": False,
        "quantity_hint": "Masalan: 300 gramm, 500 gramm, 1 kg",
    },
}

TORT_DECOR_OPTIONS = {
    "1": "O'g'il bolalar uchun topper",
    "2": "Qiz bolalar uchun topper",
    "3": "Chopakli rasmli",
    "4": "Vaflili rasmli",
    "5": "Aylana mevali",
    "6": "Odatiy",
}

# =========================================================
# 🤖 BOT SETUP
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("tort_house_bot")

bot: Bot | None = None
dp = Dispatcher(storage=MemoryStorage())

# =========================================================
# 🧠 STATES
# =========================================================
class CheckoutStates(StatesGroup):
    product_variant = State()
    full_name = State()
    phone = State()
    delivery_date = State()
    delivery_time = State()
    delivery_type = State()
    pickup_branch = State()
    address = State()
    notes = State()
    reference_choice = State()
    reference_text = State()
    reference_photo = State()


class AddToCartStates(StatesGroup):
    amount = State()
    design = State()
    decoration = State()
    decoration_photos = State()
    color = State()
    top_text = State()
    filling = State()
    note = State()
    confirm_add = State()

# =========================================================
# 🗄️ DATABASE
# =========================================================
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cur.fetchall()}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> None:
    with closing(get_conn()) as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                delivery_date TEXT,
                delivery_time TEXT,
                delivery_type TEXT,
                pickup_branch TEXT,
                address TEXT,
                notes TEXT,
                reference_type TEXT,
                custom_description TEXT,
                reference_photo_id TEXT,
                total_price TEXT,
                deposit_amount TEXT,
                remaining_amount TEXT,
                payment_type TEXT,
                payment_check_photo_id TEXT,
                status TEXT NOT NULL DEFAULT 'waiting_price',
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_title TEXT NOT NULL,
                product_category TEXT,
                product_number INTEGER,
                quantity_value TEXT NOT NULL,
                design_text TEXT,
                decoration_text TEXT,
                decoration_photo_ids TEXT,
                color TEXT,
                top_text TEXT,
                filling TEXT,
                extra_note TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
            """
        )

        existing_columns = table_columns(conn, "order_items")
        wanted = {
            "product_number": "INTEGER",
            "decoration_text": "TEXT",
            "decoration_photo_ids": "TEXT",
        }
        for col, col_type in wanted.items():
            if col not in existing_columns:
                cur.execute(f"ALTER TABLE order_items ADD COLUMN {col} {col_type}")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS product_photos (
                product_number INTEGER PRIMARY KEY,
                product_category TEXT NOT NULL,
                product_title TEXT NOT NULL,
                photo_id TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.commit()

# =========================================================
# 🛠️ HELPERS
# =========================================================
def get_text(message: Message) -> str:
    return (message.text or "").strip()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id in SUPER_ADMIN_IDS


def is_super_admin(user_id: int) -> bool:
    return user_id in SUPER_ADMIN_IDS


def normalize_optional_text(value: str | None) -> str:
    cleaned = (value or "").strip()
    if cleaned.lower() in {"-", "yoq", "yo'q", "yo‘q", "none"}:
        return ""
    return cleaned


def safe_int_from_money(value: str | int | None) -> int | None:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def format_money(value: int) -> str:
    return f"{value:,} so'm".replace(",", " ")


def auto_deposit_by_total(total_int: int) -> int:
    deposit = int(round(total_int * 0.30))
    return max(deposit, 0)


def strip_catalog_value(value: str) -> str:
    return (value or "").strip()


def flatten_variants(category: str) -> list[str]:
    groups = PRODUCT_CATALOG.get(category, {}).get("groups", {})
    result: list[str] = []
    for items in groups.values():
        result.extend([strip_catalog_value(item) for item in items if strip_catalog_value(item)])
    return result


def build_variant_text(category: str) -> str:
    groups = PRODUCT_CATALOG.get(category, {}).get("groups", {})
    lines = [f"<b>{category} bo'limidagi turlar:</b>"]
    idx = 1
    for group_name, items in groups.items():
        lines.append(f"<b>{strip_catalog_value(group_name)}</b>")
        for item in items:
            title = strip_catalog_value(item)
            if title:
                lines.append(f"{idx}. {title}")
                idx += 1
    lines.append("Keraklisini yozing yoki raqamini yuboring.")
    return "\n".join(lines)


def build_product_number_map() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    idx = 1
    for category, cfg in PRODUCT_CATALOG.items():
        for group_name, items in cfg.get("groups", {}).items():
            for item in items:
                title = strip_catalog_value(item)
                if title:
                    rows.append(
                        {
                            "number": idx,
                            "category": category,
                            "group": strip_catalog_value(group_name),
                            "title": title,
                        }
                    )
                    idx += 1
    return rows


PRODUCT_NUMBER_MAP = build_product_number_map()
PRODUCT_NUMBER_LOOKUP = {row["number"]: row for row in PRODUCT_NUMBER_MAP}
PRODUCT_KEY_LOOKUP = {(row["category"], row["title"]): row["number"] for row in PRODUCT_NUMBER_MAP}

ODDIY_TORT_SET = {
    strip_catalog_value(item)
    for group_name, items in PRODUCT_CATALOG["Tort"]["groups"].items()
    if "Oddiy tortlar" in strip_catalog_value(group_name)
    for item in items
    if strip_catalog_value(item)
}
PREMIUM_TORT_SET = {
    strip_catalog_value(item)
    for group_name, items in PRODUCT_CATALOG["Tort"]["groups"].items()
    if "Premium tortlar" in strip_catalog_value(group_name)
    for item in items
    if strip_catalog_value(item)
}


def is_tort_product(category: str) -> bool:
    return category == "Tort"


def is_oddiy_tort(product_title: str) -> bool:
    return strip_catalog_value(product_title) in ODDIY_TORT_SET


def is_premium_tort(product_title: str) -> bool:
    return strip_catalog_value(product_title) in PREMIUM_TORT_SET


def needs_design_for_selection(category: str, product_title: str) -> bool:
    return is_tort_product(category) and is_oddiy_tort(product_title)


def needs_color_for_selection(category: str, product_title: str) -> bool:
    return is_tort_product(category) and is_oddiy_tort(product_title)


def needs_decoration_for_selection(category: str, product_title: str) -> bool:
    return is_tort_product(category)


def get_product_number(category: str, product_title: str) -> int | None:
    return PRODUCT_KEY_LOOKUP.get((category, strip_catalog_value(product_title)))


def format_decoration_text(decoration_value: str) -> str:
    return TORT_DECOR_OPTIONS.get(str(decoration_value), decoration_value or "-")


def product_photo_caption(title: str) -> str:
    return f"📷 <b>{title}</b> rasmi"


def set_product_photo(product_number: int, category: str, title: str, photo_id: str) -> None:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO product_photos (product_number, product_category, product_title, photo_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(product_number) DO UPDATE SET
                product_category = excluded.product_category,
                product_title = excluded.product_title,
                photo_id = excluded.photo_id,
                updated_at = excluded.updated_at
            """,
            (product_number, category, title, photo_id, now_str()),
        )
        conn.commit()


def get_product_photo(product_number: int) -> str | None:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT photo_id FROM product_photos WHERE product_number = ?", (product_number,))
        row = cur.fetchone()
        return row["photo_id"] if row else None


def get_product_list_text() -> str:
    lines = ["<b>📦 Mahsulotlar ro'yxati</b>"]
    current_category = None
    for row in PRODUCT_NUMBER_MAP:
        if row["category"] != current_category:
            current_category = row["category"]
            lines.append(f"\n<b>{current_category}</b>")
        lines.append(f"{row['number']}. {row['title']}")
    lines.append("\nRasm biriktirish: <code>/setphoto RAQAM</code>")
    return "\n".join(lines)


async def safe_send_message(chat_id: int, text: str, **kwargs: Any) -> None:
    if bot is None:
        return
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except Exception:
        logger.exception("Failed to send message to %s", chat_id)


async def safe_send_photo(chat_id: int, photo: str, **kwargs: Any) -> None:
    if bot is None:
        return
    try:
        await bot.send_photo(chat_id, photo=photo, **kwargs)
    except Exception:
        logger.exception("Failed to send photo to %s", chat_id)


def build_simple_cart_text(cart: list[dict[str, Any]]) -> str:
    if not cart:
        return "🛒 Savat bo'sh."
    lines = ["<b>🛒 Savat:</b>"]
    for i, item in enumerate(cart, start=1):
        lines.append(f"{i}. <b>{item.get('product_title', '-')}</b>")
        lines.append(f"   📏 Miqdori: {item.get('quantity_value', '-')}")
        if item.get("design_text"):
            lines.append(f"   🧁 Dizayn: {item['design_text']}")
        if item.get("decoration_text"):
            lines.append(f"   ✨ Bezak: {item['decoration_text']}")
        if item.get("decoration_photo_ids"):
            try:
                count = len(json.loads(item["decoration_photo_ids"])) if isinstance(item["decoration_photo_ids"], str) else len(item["decoration_photo_ids"])
            except Exception:
                count = 0
            if count:
                lines.append(f"   🖼 Bezak rasmlari: {count} ta")
        if item.get("color"):
            lines.append(f"   🎨 Rang: {item['color']}")
        if item.get("top_text"):
            lines.append(f"   ✍️ Yozuv: {item['top_text']}")
        if item.get("filling"):
            lines.append(f"   🍓 Ta'm: {item['filling']}")
        if item.get("extra_note"):
            lines.append(f"   📝 Izoh: {item['extra_note']}")
    return "\n".join(lines)


def create_order_from_simple_cart(
    user_id: int,
    username: str,
    full_name: str,
    phone: str,
    delivery_date: str,
    delivery_time: str,
    delivery_type: str,
    pickup_branch: str,
    address: str,
    notes: str,
    reference_type: str,
    custom_description: str,
    reference_photo_id: str,
    cart: list[dict[str, Any]],
) -> int | None:
    if not cart:
        return None

    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (
                user_id, username, full_name, phone, delivery_date, delivery_time, delivery_type,
                pickup_branch, address, notes, reference_type, custom_description, reference_photo_id,
                status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                full_name,
                phone,
                delivery_date,
                delivery_time,
                delivery_type,
                pickup_branch,
                address,
                notes,
                reference_type,
                custom_description,
                reference_photo_id,
                STATUS_WAITING_PRICE,
                now_str(),
            ),
        )
        order_id = int(cur.lastrowid)

        for item in cart:
            cur.execute(
                """
                INSERT INTO order_items (
                    order_id, product_title, product_category, product_number, quantity_value,
                    design_text, decoration_text, decoration_photo_ids, color, top_text, filling, extra_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item.get("product_title", ""),
                    item.get("product_category", ""),
                    item.get("product_number"),
                    item.get("quantity_value", ""),
                    item.get("design_text", ""),
                    item.get("decoration_text", ""),
                    json.dumps(item.get("decoration_photo_ids", []), ensure_ascii=False),
                    item.get("color", ""),
                    item.get("top_text", ""),
                    item.get("filling", ""),
                    item.get("extra_note", ""),
                ),
            )

        conn.commit()
        return order_id


def get_order_items(order_id: int) -> list[sqlite3.Row]:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,))
        return cur.fetchall()


def get_order_basic(order_id: int) -> sqlite3.Row | None:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return cur.fetchone()


def build_order_preview(order_id: int) -> str:
    order = get_order_basic(order_id)
    items = get_order_items(order_id)
    lines = [f"<b>🆕 Yangi zakaz #{order_id}</b>"]
    for idx, item in enumerate(items, start=1):
        lines.append(f"{idx}. <b>{item['product_title']}</b>")
        lines.append(f"   📏 Miqdori: {item['quantity_value']}")
        if item["design_text"]:
            lines.append(f"   🧁 Dizayn: {item['design_text']}")
        if item["decoration_text"]:
            lines.append(f"   ✨ Bezak: {item['decoration_text']}")
        if item["decoration_photo_ids"]:
            try:
                count = len(json.loads(item["decoration_photo_ids"]))
            except Exception:
                count = 0
            if count:
                lines.append(f"   🖼 Bezak rasmlari: {count} ta")
        if item["color"]:
            lines.append(f"   🎨 Rang: {item['color']}")
        if item["top_text"]:
            lines.append(f"   ✍️ Yozuv: {item['top_text']}")
        if item["filling"]:
            lines.append(f"   🍓 Ta'm: {item['filling']}")
        if item["extra_note"]:
            lines.append(f"   📝 Izoh: {item['extra_note']}")
    if order:
        lines.append(f"👤 Ism: {order['full_name']}")
        lines.append(f"📞 Telefon: {order['phone']}")
        lines.append(f"📅 Sana: {order['delivery_date'] or '-'}")
        lines.append(f"⏰ Vaqt: {order['delivery_time'] or '-'}")
        lines.append(f"🚚 Yetkazish turi: {order['delivery_type'] or '-'}")
        if order["pickup_branch"]:
            lines.append(f"🏬 Filial: {order['pickup_branch']}")
        if order["address"]:
            lines.append(f"📍 Manzil: {order['address']}")
        if order["notes"]:
            lines.append(f"📝 Izoh: {order['notes']}")
        if order["reference_type"]:
            lines.append(f"📌 Namuna turi: {order['reference_type']}")
        if order["custom_description"]:
            lines.append(f"✍️ Qo'shimcha tarif: {order['custom_description']}")
    lines.append(f"💬 Narx va zakolat yuborish: <code>/price {order_id} 150000</code>")
    return "\n".join(lines)


def set_order_price(order_id: int, total_price: str, deposit_amount: str, remaining_amount: str) -> tuple[bool, int | None]:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()
        if not row:
            return False, None
        user_id = row[0]
        cur.execute(
            "UPDATE orders SET total_price = ?, deposit_amount = ?, remaining_amount = ?, status = ? WHERE id = ?",
            (total_price, deposit_amount, remaining_amount, STATUS_PRICED, order_id),
        )
        conn.commit()
        return True, user_id


def set_payment_type(order_id: int, payment_type: str) -> None:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE orders SET payment_type = ?, status = ? WHERE id = ?",
            (payment_type, STATUS_AWAITING_DEPOSIT_CHECK, order_id),
        )
        conn.commit()


def save_payment_check(order_id: int, photo_id: str) -> None:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE orders SET payment_check_photo_id = ?, status = ? WHERE id = ?",
            (photo_id, STATUS_DEPOSIT_SENT, order_id),
        )
        conn.commit()


def update_order_status(order_id: int, status: str) -> tuple[bool, int | None]:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()
        if not row:
            return False, None
        user_id = row[0]
        cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        conn.commit()
        return True, user_id


def get_latest_actionable_order_for_user(user_id: int) -> sqlite3.Row | None:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM orders
            WHERE user_id = ?
              AND status IN (?, ?, ?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, STATUS_PRICED, STATUS_AWAITING_DEPOSIT_CHECK, STATUS_DEPOSIT_SENT),
        )
        return cur.fetchone()


def get_orders_count() -> int:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders")
        return cur.fetchone()[0]


def get_today_orders_count() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (f"{today}%",))
        return cur.fetchone()[0]


def get_last_orders(limit: int = 10) -> list[sqlite3.Row]:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
        return cur.fetchall()


def get_period_orders(start_date: datetime, end_date: datetime) -> list[sqlite3.Row]:
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM orders WHERE created_at >= ? AND created_at < ? ORDER BY id DESC",
            (start_date.strftime("%Y-%m-%d %H:%M:%S"), end_date.strftime("%Y-%m-%d %H:%M:%S")),
        )
        return cur.fetchall()


def sum_money_from_rows(rows: list[sqlite3.Row], column: str) -> int:
    total = 0
    for row in rows:
        value = safe_int_from_money(row[column] or "")
        if value:
            total += value
    return total


def build_admin_stats_text() -> str:
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start - timedelta(days=day_start.weekday())
    month_start = day_start.replace(day=1)

    daily = get_period_orders(day_start, now + timedelta(seconds=1))
    weekly = get_period_orders(week_start, now + timedelta(seconds=1))
    monthly = get_period_orders(month_start, now + timedelta(seconds=1))

    def stats_block(title: str, rows: list[sqlite3.Row]) -> str:
        deposits = sum_money_from_rows([r for r in rows if r["status"] in {STATUS_DEPOSIT_SENT, STATUS_CONFIRMED, STATUS_READY, STATUS_DELIVERED}], "deposit_amount")
        delivered = sum_money_from_rows([r for r in rows if r["status"] == STATUS_DELIVERED], "total_price")
        total_declared = sum_money_from_rows(rows, "total_price")
        return (
            f"<b>{title}</b>\n"
            f"📦 Zakazlar: {len(rows)}\n"
            f"💳 Zakolatlar: {format_money(deposits)}\n"
            f"🚚 Yetkazilgan daromad: {format_money(delivered)}\n"
            f"💰 Umumiy narxlar yig'indisi: {format_money(total_declared)}"
        )

    return "\n\n".join(
        [
            "<b>📊 Pro statistika</b>",
            stats_block("📅 Kunlik", daily),
            stats_block("🗓 Haftalik", weekly),
            stats_block("📆 Oylik", monthly),
        ]
    )

# =========================================================
# ⌨️ KEYBOARDS
# =========================================================
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎂 Zakaz berish")],
            [KeyboardButton(text="📋 Narx va ma'lumot"), KeyboardButton(text="📞 Aloqa")],
        ],
        resize_keyboard=True,
    )


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqam yuborish", request_contact=True)], [KeyboardButton(text="🔙 Ortga")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def only_back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Ortga")]], resize_keyboard=True, one_time_keyboard=True)


def decoration_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3")],
            [KeyboardButton(text="4"), KeyboardButton(text="5"), KeyboardButton(text="6")],
            [KeyboardButton(text="🔙 Ortga")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def decoration_photo_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Davom etish")], [KeyboardButton(text="🔙 Ortga")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def delivery_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚚 Yetkazib berish")],
            [KeyboardButton(text="🏬 Olib ketaman")],
            [KeyboardButton(text="🔙 Ortga")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def pickup_branch_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏬 Chortoq tumani")],
            [KeyboardButton(text="🏬 Uychi tumani")],
            [KeyboardButton(text="🔙 Ortga")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def reference_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Namuna rasmini yuboraman")],
            [KeyboardButton(text="✍️ Batafsil yozib beraman")],
            [KeyboardButton(text="⏭️ Namunasiz davom etaman")],
            [KeyboardButton(text="🔙 Ortga")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def add_to_cart_finish_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Savatga qo'shish")], [KeyboardButton(text="🔙 Ortga")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def after_add_cart_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Yana mahsulot qo'shish")],
            [KeyboardButton(text="🛒 Savatni ko'rish")],
            [KeyboardButton(text="✅ Zakazni rasmiylashtirish")],
            [KeyboardButton(text="🏠 Menu")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def payment_method_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Qolganini kartadan to'layman")],
            [KeyboardButton(text="💵 Qolganini naqd beraman")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def category_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Tort"), KeyboardButton(text="Trayfel")],
            [KeyboardButton(text="Pirojniy"), KeyboardButton(text="Ichimliklar")],
            [KeyboardButton(text="Somsa"), KeyboardButton(text="Kruassan")],
            [KeyboardButton(text="Muzqaymoq")],
            [KeyboardButton(text="Menu")],
        ],
        resize_keyboard=True,
    )


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Bugungi zakazlar"), KeyboardButton(text="📦 Oxirgi zakazlar")],
            [KeyboardButton(text="🔢 Jami zakazlar"), KeyboardButton(text="📈 Pro statistika")],
        ],
        resize_keyboard=True,
    )


def copy_card_keyboard() -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [[InlineKeyboardButton(text=f"💳 Karta: {CARD_NUMBER}", callback_data="noop")]]
    pay_row: list[InlineKeyboardButton] = []
    if PAYME_URL:
        pay_row.append(InlineKeyboardButton(text="💜 Payme", url=PAYME_URL))
    if CLICK_URL:
        pay_row.append(InlineKeyboardButton(text="💙 Click", url=CLICK_URL))
    if UZUM_URL:
        pay_row.append(InlineKeyboardButton(text="🟣 Uzum", url=UZUM_URL))
    if pay_row:
        buttons.append(pay_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Narx/zakolat qo'yish", callback_data=f"order:price:{order_id}")
    kb.button(text="✅ Tasdiqlash", callback_data=f"order:confirm:{order_id}")
    kb.button(text="⚠️ Ogohlantirish", callback_data=f"order:warn:{order_id}")
    kb.button(text="❌ Bekor qilish", callback_data=f"order:cancel:{order_id}")
    kb.button(text="📦 Tayyor", callback_data=f"order:ready:{order_id}")
    kb.button(text="🚚 Yetkazildi", callback_data=f"order:delivered:{order_id}")
    kb.adjust(2, 2, 2)
    return kb.as_markup()

# =========================================================
# 🏠 MAIN / ADMIN ENTRY
# =========================================================
@dp.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer("Karta raqami yuqorida ko'rsatilgan.")


@dp.errors()
async def global_error_handler(event: Any) -> bool:
    logger.exception("Unhandled update error: %s", event.exception)
    return True


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Assalomu alaykum! 👋\n"
        f"<b>{BRAND_TEXT}</b> ga xush kelibsiz.\n"
        "⏰ <b>Muhim eslatma:</b>\n"
        "Zakazni kamida <b>1 kun oldin</b>, ayrim murakkab buyurtmalarni esa <b>2 kun oldin</b> bering.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "📋 Narx va ma'lumot")
async def info_handler(message: Message) -> None:
    await message.answer(
        "ℹ️ Narxlar mahsulot, bezak, murakkablik va hajmga qarab admin tomonidan belgilanadi.\n"
        "💳 Zakolat summasi umumiy narxning <b>30%</b> qismi qilib olinadi.\n"
        "⏰ Zakazni kamida 1 kun oldin, ayrim murakkab buyurtmalarni esa 2 kun oldin berish tavsiya etiladi."
    )


@dp.message(F.text == "📞 Aloqa")
async def contact_handler(message: Message) -> None:
    await message.answer(
        f"📞 Aloqa uchun:\n{PHONE_TEXT}\n"
        f"💬 Telegram: {TELEGRAM_TEXT}\n"
        f"🕘 Ish vaqti: {WORK_TIME_TEXT}"
    )


@dp.message(F.text == "🎂 Zakaz berish")
async def open_catalog(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cart = data.get("simple_cart", [])
    await state.clear()
    await state.update_data(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        simple_cart=cart,
    )
    await message.answer(
        "⏰ Muhim eslatma:\n"
        "Zakazni kamida 1 kun oldin, ayrim murakkab mahsulotlarni esa 2 kun oldin berishingiz kerak.\n"
        "Mahsulot turini tanlang:",
        reply_markup=category_keyboard(),
    )

# =========================================================
# 📚 CATALOG
# =========================================================
@dp.message(F.text == "Menu")
@dp.message(F.text == "🏠 Menu")
async def back_to_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Asosiy menuga qaytdingiz.", reply_markup=main_keyboard())


@dp.message(F.text.in_(["Tort", "Trayfel", "Pirojniy", "Ichimliklar", "Somsa", "Kruassan", "Muzqaymoq"]))
async def open_category_products(message: Message, state: FSMContext) -> None:
    category = get_text(message)
    data = await state.get_data()
    cart = data.get("simple_cart", [])
    await state.clear()
    await state.update_data(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        selected_category=category,
        product_category=category,
        simple_cart=cart,
    )
    await message.answer(build_variant_text(category), reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.product_variant)


@dp.message(CheckoutStates.product_variant)
async def get_product_variant(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        data = await state.get_data()
        cart = data.get("simple_cart", [])
        await state.clear()
        await state.update_data(user_id=message.from_user.id, username=message.from_user.username or "", simple_cart=cart)
        await message.answer("Mahsulot turini tanlang:", reply_markup=category_keyboard())
        return

    data = await state.get_data()
    category = data.get("selected_category", "")
    variants = flatten_variants(category)

    selected_variant = None
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(variants):
            selected_variant = variants[idx]
    else:
        for item in variants:
            if text.lower() == item.lower():
                selected_variant = item
                break

    if not selected_variant:
        await message.answer(f"Iltimos, {category} uchun raqam yoki nomdan birini to'g'ri yuboring.")
        return

    product_number = get_product_number(category, selected_variant)
    await state.update_data(
        selected_product=selected_variant,
        product_title=selected_variant,
        product_category=category,
        product_number=product_number,
        design_text="",
        decoration="",
        decoration_photo_ids=[],
        color="",
        top_text="",
        filling="",
        extra_note="",
    )

    if product_number:
        photo_id = get_product_photo(product_number)
        if photo_id:
            await safe_send_photo(message.chat.id, photo_id, caption=product_photo_caption(selected_variant))

    hint = PRODUCT_CATALOG.get(category, {}).get("quantity_hint", "Masalan: 1 dona")
    await message.answer(f"📏 Miqdorini kiriting:\n{hint}", reply_markup=only_back_keyboard())
    await state.set_state(AddToCartStates.amount)

# =========================================================
# 🛒 CART FLOW
# =========================================================
@dp.message(AddToCartStates.amount)
async def cart_amount(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        await state.set_state(CheckoutStates.product_variant)
        await message.answer("Kerakli mahsulot turini yozing yoki raqamini yuboring:", reply_markup=only_back_keyboard())
        return

    await state.update_data(quantity_value=text)
    data = await state.get_data()
    category = data.get("product_category", "")
    product_title = data.get("product_title", "")

    if needs_design_for_selection(category, product_title):
        await message.answer(
            "🧁 Dizayni qanday bo'lsin?\nMasalan: yumaloq, kvadrat, 2 qavatli.\nKerak bo'lmasa '-' deb yozing.",
            reply_markup=only_back_keyboard(),
        )
        await state.set_state(AddToCartStates.design)
        return

    if needs_decoration_for_selection(category, product_title):
        await message.answer(
            "✨ Bezak turini tanlang:\n"
            "1 - O'g'il bolalar uchun topper\n"
            "2 - Qiz bolalar uchun topper\n"
            "3 - Chopakli rasmli\n"
            "4 - Vaflili rasmli\n"
            "5 - Aylana mevali\n"
            "6 - Odatiy",
            reply_markup=decoration_keyboard(),
        )
        await state.set_state(AddToCartStates.decoration)
        return

    if needs_color_for_selection(category, product_title):
        await message.answer("🎨 Rangini kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
        await state.set_state(AddToCartStates.color)
        return

    if PRODUCT_CATALOG.get(category, {}).get("needs_text"):
        await message.answer("✍️ Ustiga yozuvni kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
        await state.set_state(AddToCartStates.top_text)
        return

    if PRODUCT_CATALOG.get(category, {}).get("needs_filling"):
        await message.answer(
            "🍓 Ta'm / nachinkani kiriting.\nMasalan: 1-chi qavati bananli, 2-chi qavati mag'izli\nKerak bo'lmasa 'yo'q' deb yozing.",
            reply_markup=only_back_keyboard(),
        )
        await state.set_state(AddToCartStates.filling)
        return

    await message.answer("📝 Qo'shimcha izoh yozing.\nBo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(AddToCartStates.note)


@dp.message(AddToCartStates.design)
async def cart_design(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        await state.set_state(AddToCartStates.amount)
        await message.answer("📏 Miqdorini kiriting:", reply_markup=only_back_keyboard())
        return

    await state.update_data(design_text=normalize_optional_text(text))
    data = await state.get_data()
    category = data.get("product_category", "")
    product_title = data.get("product_title", "")

    if needs_decoration_for_selection(category, product_title):
        await message.answer(
            "✨ Bezak turini tanlang:\n"
            "1 - O'g'il bolalar uchun topper\n"
            "2 - Qiz bolalar uchun topper\n"
            "3 - Chopakli rasmli\n"
            "4 - Vaflili rasmli\n"
            "5 - Aylana mevali\n"
            "6 - Odatiy",
            reply_markup=decoration_keyboard(),
        )
        await state.set_state(AddToCartStates.decoration)
        return

    if needs_color_for_selection(category, product_title):
        await message.answer("🎨 Rangini kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
        await state.set_state(AddToCartStates.color)
        return

    await message.answer("✍️ Ustiga yozuvni kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(AddToCartStates.top_text)


@dp.message(AddToCartStates.decoration)
async def cart_decoration(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        data = await state.get_data()
        if needs_design_for_selection(data.get("product_category", ""), data.get("product_title", "")):
            await state.set_state(AddToCartStates.design)
            await message.answer("🧁 Dizayni qanday bo'lsin?", reply_markup=only_back_keyboard())
        else:
            await state.set_state(AddToCartStates.amount)
            await message.answer("📏 Miqdorini kiriting:", reply_markup=only_back_keyboard())
        return

    if text not in TORT_DECOR_OPTIONS:
        await message.answer("Iltimos, 1 dan 6 gacha tanlang.", reply_markup=decoration_keyboard())
        return

    await state.update_data(decoration=text, decoration_photo_ids=[])

    if text == "3":
        await message.answer(
            "📸 Chopakli rasmli bezak tanlandi.\nKamida 4 ta rasm tashlang. Bo'lgach ✅ Davom etish ni bosing.",
            reply_markup=decoration_photo_keyboard(),
        )
        await state.set_state(AddToCartStates.decoration_photos)
        return

    if text == "4":
        await message.answer(
            "📸 Vaflili rasmli bezak tanlandi.\nKamida 1 ta rasm tashlang. Bo'lgach ✅ Davom etish ni bosing.",
            reply_markup=decoration_photo_keyboard(),
        )
        await state.set_state(AddToCartStates.decoration_photos)
        return

    data = await state.get_data()
    if needs_color_for_selection(data.get("product_category", ""), data.get("product_title", "")):
        await message.answer("🎨 Rangini kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
        await state.set_state(AddToCartStates.color)
        return

    await message.answer("✍️ Ustiga yozuvni kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(AddToCartStates.top_text)


@dp.message(AddToCartStates.decoration_photos, F.photo)
async def cart_decoration_photo_collect(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_ids = list(data.get("decoration_photo_ids", []))
    photo_ids.append(message.photo[-1].file_id)
    await state.update_data(decoration_photo_ids=photo_ids)
    decoration = data.get("decoration")
    need = 4 if decoration == "3" else 1
    await message.answer(
        f"✅ Rasm qabul qilindi. Hozir {len(photo_ids)} ta rasm bor. Keraklisi {need} ta.\nTayyor bo'lsa ✅ Davom etish ni bosing.",
        reply_markup=decoration_photo_keyboard(),
    )


@dp.message(AddToCartStates.decoration_photos)
async def cart_decoration_photo_text(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    data = await state.get_data()

    if text == "🔙 Ortga":
        await state.update_data(decoration="", decoration_photo_ids=[])
        await state.set_state(AddToCartStates.decoration)
        await message.answer("✨ Bezak turini tanlang:", reply_markup=decoration_keyboard())
        return

    if text != "✅ Davom etish":
        await message.answer("Rasm tashlang yoki ✅ Davom etish ni bosing.", reply_markup=decoration_photo_keyboard())
        return

    decoration = data.get("decoration")
    photo_ids = list(data.get("decoration_photo_ids", []))
    need = 4 if decoration == "3" else 1
    if len(photo_ids) < need:
        await message.answer(f"Kamida {need} ta rasm kerak. Hozir {len(photo_ids)} ta.", reply_markup=decoration_photo_keyboard())
        return

    if needs_color_for_selection(data.get("product_category", ""), data.get("product_title", "")):
        await message.answer("🎨 Rangini kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
        await state.set_state(AddToCartStates.color)
        return

    await message.answer("✍️ Ustiga yozuvni kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(AddToCartStates.top_text)


@dp.message(AddToCartStates.color)
async def cart_color(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        data = await state.get_data()
        if data.get("decoration"):
            await state.set_state(AddToCartStates.decoration)
            await message.answer("✨ Bezak turini tanlang:", reply_markup=decoration_keyboard())
            return
        if needs_design_for_selection(data.get("product_category", ""), data.get("product_title", "")):
            await state.set_state(AddToCartStates.design)
            await message.answer("🧁 Dizayni qanday bo'lsin?", reply_markup=only_back_keyboard())
            return
        await state.set_state(AddToCartStates.amount)
        await message.answer("📏 Miqdorini kiriting:", reply_markup=only_back_keyboard())
        return

    await state.update_data(color=normalize_optional_text(text))
    await message.answer("✍️ Ustiga yozuvni kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(AddToCartStates.top_text)


@dp.message(AddToCartStates.top_text)
async def cart_top_text(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        data = await state.get_data()
        if needs_color_for_selection(data.get("product_category", ""), data.get("product_title", "")):
            await state.set_state(AddToCartStates.color)
            await message.answer("🎨 Rangini kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
            return
        if data.get("decoration"):
            await state.set_state(AddToCartStates.decoration)
            await message.answer("✨ Bezak turini tanlang:", reply_markup=decoration_keyboard())
            return
        if needs_design_for_selection(data.get("product_category", ""), data.get("product_title", "")):
            await state.set_state(AddToCartStates.design)
            await message.answer("🧁 Dizayni qanday bo'lsin?", reply_markup=only_back_keyboard())
            return
        await state.set_state(AddToCartStates.amount)
        await message.answer("📏 Miqdorini kiriting:", reply_markup=only_back_keyboard())
        return

    await state.update_data(top_text=normalize_optional_text(text))
    category = (await state.get_data()).get("product_category", "")
    if PRODUCT_CATALOG.get(category, {}).get("needs_filling"):
        await message.answer(
            "🍓 Ta'm / nachinkani kiriting.\nMasalan: 1-chi qavati bananli, 2-chi qavati mag'izli\nKerak bo'lmasa 'yo'q' deb yozing.",
            reply_markup=only_back_keyboard(),
        )
        await state.set_state(AddToCartStates.filling)
        return
    await message.answer("📝 Qo'shimcha izoh yozing.\nBo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(AddToCartStates.note)


@dp.message(AddToCartStates.filling)
async def cart_filling(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        await state.set_state(AddToCartStates.top_text)
        await message.answer("✍️ Ustiga yozuvni kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
        return

    await state.update_data(filling=normalize_optional_text(text))
    await message.answer("📝 Qo'shimcha izoh yozing.\nBo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(AddToCartStates.note)


@dp.message(AddToCartStates.note)
async def cart_note(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        category = (await state.get_data()).get("product_category", "")
        if PRODUCT_CATALOG.get(category, {}).get("needs_filling"):
            await state.set_state(AddToCartStates.filling)
            await message.answer(
                "🍓 Ta'm / nachinkani kiriting.\nMasalan: 1-chi qavati bananli, 2-chi qavati mag'izli\nKerak bo'lmasa 'yo'q' deb yozing.",
                reply_markup=only_back_keyboard(),
            )
            return
        await state.set_state(AddToCartStates.top_text)
        await message.answer("✍️ Ustiga yozuvni kiriting.\nKerak bo'lmasa 'yo'q' deb yozing.", reply_markup=only_back_keyboard())
        return

    await state.update_data(extra_note=normalize_optional_text(text))
    data = await state.get_data()
    lines = [
        "<b>Mahsulot tayyor:</b>",
        f"🍰 Nomi: {data.get('product_title', '')}",
        f"📏 Miqdori: {data.get('quantity_value', '')}",
        f"🧁 Dizayn: {data.get('design_text', '') or '-'}",
    ]
    if data.get("decoration"):
        lines.append(f"✨ Bezak: {format_decoration_text(data['decoration'])}")
    if data.get("decoration_photo_ids"):
        lines.append(f"🖼 Bezak rasmlari: {len(data.get('decoration_photo_ids', []))} ta")
    lines.extend([
        f"🎨 Rang: {data.get('color', '') or '-'}",
        f"✍️ Yozuv: {data.get('top_text', '') or '-'}",
        f"🍓 Ta'm: {data.get('filling', '') or '-'}",
        f"📝 Izoh: {data.get('extra_note', '') or '-'}",
    ])
    await message.answer("\n".join(lines) + "\n\nKeyingi bosqichni tanlang:", reply_markup=add_to_cart_finish_keyboard())
    await state.set_state(AddToCartStates.confirm_add)


@dp.message(AddToCartStates.confirm_add, F.text == "✅ Savatga qo'shish")
async def confirm_add_to_cart(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cart_item = {
        "product_title": data.get("product_title", ""),
        "product_category": data.get("product_category", ""),
        "product_number": data.get("product_number"),
        "quantity_value": data.get("quantity_value", ""),
        "design_text": data.get("design_text", ""),
        "decoration_text": format_decoration_text(data.get("decoration", "")) if data.get("decoration") else "",
        "decoration_photo_ids": list(data.get("decoration_photo_ids", [])),
        "color": data.get("color", ""),
        "top_text": data.get("top_text", ""),
        "filling": data.get("filling", ""),
        "extra_note": data.get("extra_note", ""),
    }
    cart = data.get("simple_cart", [])
    cart.append(cart_item)
    await state.clear()
    await state.update_data(user_id=message.from_user.id, username=message.from_user.username or "", simple_cart=cart)
    await message.answer(
        f"✅ <b>{cart_item['product_title']}</b> savatga qo'shildi.\nSavatda hozir <b>{len(cart)}</b> ta mahsulot bor.",
        reply_markup=after_add_cart_keyboard(),
    )


@dp.message(AddToCartStates.confirm_add, F.text == "🔙 Ortga")
async def back_from_confirm_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddToCartStates.note)
    await message.answer("📝 Qo'shimcha izoh yozing.\nBo'lmasa '-' deb yozing.", reply_markup=only_back_keyboard())


@dp.message(F.text == "➕ Yana mahsulot qo'shish")
async def add_more_products(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cart = data.get("simple_cart", [])
    await state.clear()
    await state.update_data(user_id=message.from_user.id, username=message.from_user.username or "", simple_cart=cart)
    await message.answer("Mahsulot turini tanlang:", reply_markup=category_keyboard())


@dp.message(F.text == "🛒 Savatni ko'rish")
async def show_simple_cart(message: Message, state: FSMContext) -> None:
    cart = (await state.get_data()).get("simple_cart", [])
    await message.answer(build_simple_cart_text(cart), reply_markup=after_add_cart_keyboard())


@dp.message(F.text == "✅ Zakazni rasmiylashtirish")
async def start_checkout_from_cart(message: Message, state: FSMContext) -> None:
    cart = (await state.get_data()).get("simple_cart", [])
    if not cart:
        await message.answer("🛒 Savat bo'sh.")
        return
    await message.answer("👤 Ismingizni kiriting:", reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.full_name)

# =========================================================
# ✅ CHECKOUT FLOW
# =========================================================
@dp.message(CheckoutStates.full_name)
async def checkout_name(message: Message, state: FSMContext) -> None:
    if get_text(message) == "🔙 Ortga":
        data = await state.get_data()
        await state.clear()
        await state.update_data(user_id=message.from_user.id, username=message.from_user.username or "", simple_cart=data.get("simple_cart", []))
        await message.answer(build_simple_cart_text(data.get("simple_cart", [])), reply_markup=after_add_cart_keyboard())
        return
    await state.update_data(full_name=get_text(message))
    await message.answer("📞 Telefon raqamingizni yuboring/yozing:", reply_markup=phone_keyboard())
    await state.set_state(CheckoutStates.phone)


@dp.message(CheckoutStates.phone, F.contact)
async def checkout_phone_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("📅 Qaysi sanaga kerak?\nMasalan: 15.03.2026", reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.delivery_date)


@dp.message(CheckoutStates.phone)
async def checkout_phone_text(message: Message, state: FSMContext) -> None:
    if get_text(message) == "🔙 Ortga":
        await state.set_state(CheckoutStates.full_name)
        await message.answer("👤 Ismingizni kiriting:", reply_markup=only_back_keyboard())
        return
    await state.update_data(phone=get_text(message))
    await message.answer("📅 Qaysi sanaga kerak?\nMasalan: 15.03.2026", reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.delivery_date)


@dp.message(CheckoutStates.delivery_date)
async def checkout_date(message: Message, state: FSMContext) -> None:
    if get_text(message) == "🔙 Ortga":
        await state.set_state(CheckoutStates.phone)
        await message.answer("📞 Telefon raqamingizni yuboring/yozing:", reply_markup=phone_keyboard())
        return
    await state.update_data(delivery_date=get_text(message))
    await message.answer("⏰ Qaysi vaqtga kerak?\nMasalan: 18:00", reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.delivery_time)


@dp.message(CheckoutStates.delivery_time)
async def checkout_time(message: Message, state: FSMContext) -> None:
    if get_text(message) == "🔙 Ortga":
        await state.set_state(CheckoutStates.delivery_date)
        await message.answer("📅 Qaysi sanaga kerak?\nMasalan: 15.03.2026", reply_markup=only_back_keyboard())
        return
    await state.update_data(delivery_time=get_text(message))
    await message.answer("🚚 Yetkazib berilsinmi yoki o'zingiz olib ketasizmi?", reply_markup=delivery_keyboard())
    await state.set_state(CheckoutStates.delivery_type)


@dp.message(CheckoutStates.delivery_type)
async def checkout_delivery_type(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        await state.set_state(CheckoutStates.delivery_time)
        await message.answer("⏰ Qaysi vaqtga kerak?\nMasalan: 18:00", reply_markup=only_back_keyboard())
        return
    await state.update_data(delivery_type=text)
    if text == "🚚 Yetkazib berish":
        await message.answer("🚕 Online taxi orqali yetkaziladi. Taxi to'lovi o'zingizdan.\n\n📍 Manzilni kiriting:", reply_markup=only_back_keyboard())
        await state.set_state(CheckoutStates.address)
        return
    if text == "🏬 Olib ketaman":
        await message.answer("🏬 Qaysi filialdan olib ketasiz?", reply_markup=pickup_branch_keyboard())
        await state.set_state(CheckoutStates.pickup_branch)
        return
    await message.answer("Iltimos, tugmadan tanlang.", reply_markup=delivery_keyboard())


@dp.message(CheckoutStates.pickup_branch)
async def checkout_branch(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        await state.set_state(CheckoutStates.delivery_type)
        await message.answer("🚚 Yetkazib berilsinmi yoki o'zingiz olib ketasizmi?", reply_markup=delivery_keyboard())
        return
    await state.update_data(pickup_branch=text, address="")
    await message.answer("📝 Qo'shimcha izoh yozing.\nBo'lmasa '-' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.notes)


@dp.message(CheckoutStates.address)
async def checkout_address(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        await state.set_state(CheckoutStates.delivery_type)
        await message.answer("🚚 Yetkazib berilsinmi yoki o'zingiz olib ketasizmi?", reply_markup=delivery_keyboard())
        return
    await state.update_data(address=text, pickup_branch="")
    await message.answer("📝 Qo'shimcha izoh yozing.\nBo'lmasa '-' deb yozing.", reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.notes)


@dp.message(CheckoutStates.notes)
async def checkout_notes(message: Message, state: FSMContext) -> None:
    text = get_text(message)
    if text == "🔙 Ortga":
        data = await state.get_data()
        if data.get("delivery_type") == "🚚 Yetkazib berish":
            await state.set_state(CheckoutStates.address)
            await message.answer("📍 Manzilni kiriting:", reply_markup=only_back_keyboard())
        else:
            await state.set_state(CheckoutStates.pickup_branch)
            await message.answer("🏬 Qaysi filialdan olib ketasiz?", reply_markup=pickup_branch_keyboard())
        return
    await state.update_data(notes=normalize_optional_text(text))
    await message.answer(
        "📌 Namuna yoki tarif (ixtiyoriy):\n📸 Namuna rasmini yuborishingiz mumkin.\n✍️ Batafsil yozib berishingiz mumkin.\n⏭️ Namunasiz ham davom etishingiz mumkin.",
        reply_markup=reference_keyboard(),
    )
    await state.set_state(CheckoutStates.reference_choice)


@dp.message(CheckoutStates.reference_choice, F.text == "📸 Namuna rasmini yuboraman")
async def checkout_reference_photo_choice(message: Message, state: FSMContext) -> None:
    await state.update_data(reference_type="photo")
    await message.answer("📸 Namuna rasmini yuboring:", reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.reference_photo)


@dp.message(CheckoutStates.reference_choice, F.text == "✍️ Batafsil yozib beraman")
async def checkout_reference_text_choice(message: Message, state: FSMContext) -> None:
    await state.update_data(reference_type="text")
    await message.answer("✍️ Mahsulot bo'yicha umumiy batafsil tarif yozing:", reply_markup=only_back_keyboard())
    await state.set_state(CheckoutStates.reference_text)


async def finalize_checkout(message: Message, state: FSMContext, reference_type: str, custom_description: str, reference_photo_id: str) -> None:
    data = await state.get_data()
    cart = data.get("simple_cart", [])
    order_id = create_order_from_simple_cart(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=data.get("full_name", ""),
        phone=data.get("phone", ""),
        delivery_date=data.get("delivery_date", ""),
        delivery_time=data.get("delivery_time", ""),
        delivery_type=data.get("delivery_type", ""),
        pickup_branch=data.get("pickup_branch", ""),
        address=data.get("address", ""),
        notes=data.get("notes", ""),
        reference_type=reference_type,
        custom_description=custom_description,
        reference_photo_id=reference_photo_id,
        cart=cart,
    )
    if not order_id:
        await message.answer("❌ Savat bo'sh bo'lib qoldi.", reply_markup=main_keyboard())
        await state.clear()
        return

    for admin_id in ADMIN_IDS | SUPER_ADMIN_IDS:
        if reference_photo_id:
            await safe_send_photo(admin_id, reference_photo_id, caption=build_order_preview(order_id), reply_markup=admin_order_actions_keyboard(order_id))
        else:
            await safe_send_message(admin_id, build_order_preview(order_id), reply_markup=admin_order_actions_keyboard(order_id))

    # send decoration images separately
    for item in cart:
        for photo_id in item.get("decoration_photo_ids", []):
            for admin_id in ADMIN_IDS | SUPER_ADMIN_IDS:
                await safe_send_photo(admin_id, photo_id, caption=f"🖼 Zakaz #{order_id} bezak rasmi: {item.get('product_title', '')}")

    await message.answer("✅ Zakazingiz adminga yuborildi. Narx va zakolat kelishini kuting.", reply_markup=main_keyboard())
    await state.clear()


@dp.message(CheckoutStates.reference_choice, F.text == "⏭️ Namunasiz davom etaman")
async def checkout_reference_skip(message: Message, state: FSMContext) -> None:
    await finalize_checkout(message, state, "skip", "Namuna yuborilmadi", "")


@dp.message(CheckoutStates.reference_choice, F.text == "🔙 Ortga")
async def checkout_reference_back(message: Message, state: FSMContext) -> None:
    await state.set_state(CheckoutStates.notes)
    await message.answer("📝 Qo'shimcha izoh yozing.\nBo'lmasa '-' deb yozing.", reply_markup=only_back_keyboard())


@dp.message(CheckoutStates.reference_choice)
async def checkout_reference_invalid(message: Message) -> None:
    await message.answer("Iltimos, tugmalardan birini tanlang.")


@dp.message(CheckoutStates.reference_text)
async def checkout_reference_text(message: Message, state: FSMContext) -> None:
    if get_text(message) == "🔙 Ortga":
        await state.set_state(CheckoutStates.reference_choice)
        await message.answer("📌 Variantni tanlang:", reply_markup=reference_keyboard())
        return
    await finalize_checkout(message, state, "text", get_text(message), "")


@dp.message(CheckoutStates.reference_photo, F.photo)
async def checkout_reference_photo(message: Message, state: FSMContext) -> None:
    await finalize_checkout(message, state, "photo", "", message.photo[-1].file_id)


@dp.message(CheckoutStates.reference_photo)
async def checkout_reference_photo_invalid(message: Message, state: FSMContext) -> None:
    if get_text(message) == "🔙 Ortga":
        await state.set_state(CheckoutStates.reference_choice)
        await message.answer("📌 Variantni tanlang:", reply_markup=reference_keyboard())
        return
    await message.answer("📸 Iltimos, rasm yuboring yoki 🔙 Ortga ni bosing.")

# =========================================================
# 💳 PAYMENT FLOW
# =========================================================
@dp.message(F.text == "💳 Qolganini kartadan to'layman")
async def choose_card_payment(message: Message) -> None:
    order = get_latest_actionable_order_for_user(message.from_user.id)
    if not order:
        await message.answer("⏳ Hozir sizda to'lov kutilayotgan faol zakaz topilmadi.")
        return
    if not order["total_price"] or not order["deposit_amount"]:
        await message.answer("⏳ Admin hali narx yoki zakolat summasini yubormagan.")
        return
    set_payment_type(order["id"], "card")
    await message.answer(
        f"{CARD_TEXT}\n"
        f"💵 Umumiy narx: <b>{order['total_price']}</b>\n"
        f"💳 Tashlanadigan zakolat: <b>{order['deposit_amount']}</b>\n"
        f"💰 Qolgan to'lov: <b>{order['remaining_amount']}</b>\n"
        "📸 Endi zakolat chekini yuboring.\n"
        "💳 Zakolat summasi umumiy narxning 30% qismi hisoblanadi.",
        reply_markup=copy_card_keyboard(),
    )


@dp.message(F.text == "💵 Qolganini naqd beraman")
async def choose_cash_payment(message: Message) -> None:
    order = get_latest_actionable_order_for_user(message.from_user.id)
    if not order:
        await message.answer("⏳ Hozir sizda to'lov kutilayotgan faol zakaz topilmadi.")
        return
    if not order["total_price"] or not order["deposit_amount"]:
        await message.answer("⏳ Admin hali narx yoki zakolat summasini yubormagan.")
        return
    set_payment_type(order["id"], "cash")
    await message.answer(
        f"💵 Qolganini naqd berish tanlandi.\n"
        f"💳 Baribir zakolat uchun <b>{order['deposit_amount']}</b> kartaga tashlashingiz kerak.\n"
        f"💰 Qolgan to'lov: <b>{order['remaining_amount']}</b> ni mahsulotni olayotganda berasiz.\n"
        f"{CARD_TEXT}\n"
        "📸 Endi zakolat chekini yuboring.\n"
        "💳 Zakolat summasi umumiy narxning 30% qismi hisoblanadi.",
        reply_markup=copy_card_keyboard(),
    )


@dp.message(F.photo)
async def get_payment_check(message: Message) -> None:
    order = get_latest_actionable_order_for_user(message.from_user.id)
    if not order or order["status"] not in {STATUS_AWAITING_DEPOSIT_CHECK, STATUS_PRICED}:
        return
    deposit_int = safe_int_from_money(order["deposit_amount"] or "")
    if deposit_int is None:
        await message.answer("⏳ Zakolat summasi hali to'g'ri belgilanmagan.\nAdmin bilan bog'laning.")
        return
    save_payment_check(order["id"], message.photo[-1].file_id)
    for admin_id in ADMIN_IDS | SUPER_ADMIN_IDS:
        await safe_send_photo(
            admin_id,
            message.photo[-1].file_id,
            caption=(
                f"🧾 Zakaz #{order['id']} uchun zakolat cheki\n"
                f"💵 Umumiy narx: {order['total_price']}\n"
                f"💳 Zakolat: {order['deposit_amount']}\n"
                f"💰 Qolgan to'lov: {order['remaining_amount']}\n"
                f"💼 Qolgan to'lov usuli: {order['payment_type'] or '-'}"
            ),
            reply_markup=admin_order_actions_keyboard(order["id"]),
        )
    await message.answer("✅ Zakolat cheki qabul qilindi.\n⏳ Admin tekshiradi va tasdiqlaydi.")

# =========================================================
# 👨‍💼 ADMIN
# =========================================================
@dp.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin emassiz.")
        return
    await message.answer("👨‍💼 Admin panel", reply_markup=admin_keyboard())


@dp.message(Command("admins"))
async def admins_handler(message: Message) -> None:
    if not is_super_admin(message.from_user.id):
        return
    await message.answer(
        "<b>👮 Adminlar</b>\n"
        f"Admin IDs: {', '.join(str(x) for x in sorted(ADMIN_IDS)) or '-'}\n"
        f"Super admin IDs: {', '.join(str(x) for x in sorted(SUPER_ADMIN_IDS)) or '-'}"
    )


@dp.message(Command("products"))
async def products_handler(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(get_product_list_text())


@dp.message(Command("setphoto"))
async def setphoto_handler(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin emassiz.")
        return

    parts = get_text(message).split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("❗ To'g'ri format: <code>/setphoto MAHSULOT_RAQAMI</code>\nRasmni command bilan birga yuboring yoki rasmga reply qiling.")
        return

    product_number = int(parts[1])
    row = PRODUCT_NUMBER_LOOKUP.get(product_number)
    if not row:
        await message.answer("❌ Bunday mahsulot raqami topilmadi. /products bilan ro'yxatni ko'ring.")
        return

    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.reply_to_message and message.reply_to_message.photo:
        photo_id = message.reply_to_message.photo[-1].file_id

    if not photo_id:
        await message.answer("❗ Rasm yuboring va captionga <code>/setphoto RAQAM</code> yozing yoki rasmga reply qilib shu commandni yuboring.")
        return

    set_product_photo(product_number, row["category"], row["title"], photo_id)
    await message.answer(f"✅ {product_number}. {row['title']} uchun rasm saqlandi.")


@dp.message(Command("adminstats"))
@dp.message(F.text.contains("Pro statistika"))
async def adminstats_handler(message: Message) -> None:
    if is_admin(message.from_user.id):
        await message.answer(build_admin_stats_text())


@dp.message(F.text.contains("Jami zakazlar"))
async def total_orders_handler(message: Message) -> None:
    if is_admin(message.from_user.id):
        await message.answer(f"📦 Jami zakazlar soni:\n<b>{get_orders_count()}</b>")


@dp.message(F.text.contains("Bugungi zakazlar"))
async def today_orders_handler(message: Message) -> None:
    if is_admin(message.from_user.id):
        await message.answer(f"📅 Bugungi zakazlar soni:\n<b>{get_today_orders_count()}</b>")


@dp.message(F.text.contains("Oxirgi zakazlar"))
async def last_orders_handler(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    rows = get_last_orders(10)
    if not rows:
        await message.answer("📭 Hali zakazlar yo'q.")
        return
    lines = ["<b>📦 Oxirgi 10 ta zakaz:</b>"]
    for row in rows:
        lines.append(
            f"#{row['id']} | {row['full_name']} | {row['phone']} | {row['delivery_date'] or '-'} {row['delivery_time'] or '-'} | {row['total_price'] or '-'} | {row['deposit_amount'] or '-'} | {row['status']}"
        )
    lines.append("💬 Narx va zakolat yuborish: <code>/price ORDER_ID 150000</code>")
    await message.answer("\n".join(lines))


@dp.message(Command("price"))
async def price_command_handler(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = get_text(message).split()
    if len(parts) < 3:
        await message.answer("❗ To'g'ri format: <code>/price ORDER_ID UMUMIY_NARX [ZAKOLAT]</code>")
        return

    try:
        order_id = int(parts[1])
    except ValueError:
        await message.answer("❗ ORDER_ID raqam bo'lishi kerak.")
        return

    total_int = safe_int_from_money(parts[2])
    if total_int is None:
        await message.answer("❗ Narx raqam bo'lishi kerak.")
        return

    if len(parts) >= 4:
        deposit_int = safe_int_from_money(parts[3])
        if deposit_int is None:
            await message.answer("❗ Zakolat raqam bo'lishi kerak.")
            return
    else:
        deposit_int = auto_deposit_by_total(total_int)

    if deposit_int > total_int:
        await message.answer("❗ Zakolat umumiy narxdan katta bo'lishi mumkin emas.")
        return

    remaining_amount = format_money(total_int - deposit_int)
    ok, user_id = set_order_price(order_id, format_money(total_int), format_money(deposit_int), remaining_amount)
    if not ok or user_id is None:
        await message.answer("❌ Bunday zakaz topilmadi.")
        return

    await safe_send_message(
        user_id,
        f"<b>💰 Sizning zakagingiz narxi tayyor.</b>\n"
        f"🆔 Zakaz raqami: #{order_id}\n"
        f"💵 Umumiy narx: <b>{format_money(total_int)}</b>\n"
        f"💳 Zakolat: <b>{format_money(deposit_int)}</b>\n"
        f"💰 Qolgan to'lov: <b>{remaining_amount}</b>\n"
        "💳 Zakolat summasi umumiy narxning 30% qismi hisoblanadi.\n"
        "Quyidagilardan birini tanlang:\n"
        "💳 Qolganini kartadan to'layman\n"
        "💵 Qolganini naqd beraman",
        reply_markup=payment_method_keyboard(),
    )
    await message.answer(
        f"✅ Zakaz #{order_id} uchun narx yuborildi.\n"
        f"💵 Umumiy narx: {format_money(total_int)}\n"
        f"💳 Zakolat: {format_money(deposit_int)}\n"
        f"💰 Qolgan to'lov: {remaining_amount}"
    )


@dp.callback_query(F.data.startswith("order:"))
async def admin_order_action_handler(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    _, action, order_id_str = callback.data.split(":", 2)
    try:
        order_id = int(order_id_str)
    except ValueError:
        await callback.answer("Noto'g'ri zakaz ID.", show_alert=True)
        return

    order = get_order_basic(order_id)
    if not order:
        await callback.answer("Zakaz topilmadi.", show_alert=True)
        return

    if action == "price":
        total_hint = order["total_price"] or "150000"
        deposit_hint = order["deposit_amount"] or format_money(auto_deposit_by_total(safe_int_from_money(total_hint) or 150000))
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                f"💰 Zakaz #{order_id} uchun narx va zakolat yuborish:\n"
                f"<code>/price {order_id} {safe_int_from_money(total_hint) or 150000} {safe_int_from_money(deposit_hint) or auto_deposit_by_total(150000)}</code>"
            )
        return

    if action == "warn":
        if order["payment_check_photo_id"]:
            await safe_send_message(
                order["user_id"],
                f"⚠️ Zakaz #{order_id} bo'yicha ogohlantirish:\n"
                "Yuborgan chekingiz qayta tekshiruvga tushdi.\nIltimos, aniq va toza chek yuboring yoki admin bilan bog'laning."
            )
            await callback.answer("Ogohlantirish yuborildi")
            return
        await callback.answer("Chek hali yuborilmagan", show_alert=True)
        return

    status_map = {
        "confirm": (STATUS_CONFIRMED, "✅ Zakaz tasdiqlandi", "✅ Zakolatingiz tekshirildi va zakagingiz qabul qilindi."),
        "cancel": (STATUS_CANCELLED, "❌ Bekor qilindi", "❌ Afsuski, zakagingiz admin tomonidan bekor qilindi."),
        "ready": (STATUS_READY, "📦 Tayyor", "📦 Sizning zakagingiz tayyor bo'ldi."),
        "delivered": (STATUS_DELIVERED, "🚚 Yetkazildi", "🚚 Sizning zakagingiz topshirildi / yetkazildi."),
    }
    if action not in status_map:
        await callback.answer("Noma'lum amal.", show_alert=True)
        return

    new_status, label, user_text = status_map[action]
    ok, user_id = update_order_status(order_id, new_status)
    if not ok or user_id is None:
        await callback.answer("Zakaz topilmadi.", show_alert=True)
        return

    await safe_send_message(
        user_id,
        f"{user_text}\n"
        f"🆔 Zakaz raqami: #{order_id}\n"
        f"💵 Umumiy narx: {order['total_price'] or '-'}\n"
        f"💳 Zakolat: {order['deposit_amount'] or '-'}\n"
        f"💰 Qolgan to'lov: {order['remaining_amount'] or '-'}"
    )
    await callback.answer(label)
    if callback.message:
        await callback.message.answer(
            f"{label}\n"
            f"🆔 Zakaz: #{order_id}\n"
            f"👤 Mijoz: {order['full_name']}\n"
            f"📌 Holati: {new_status}\n"
            f"💵 Umumiy narx: {order['total_price'] or '-'}\n"
            f"💳 Zakolat: {order['deposit_amount'] or '-'}\n"
            f"💰 Qolgan to'lov: {order['remaining_amount'] or '-'}"
        )

# =========================================================
# 🚀 MAIN
# =========================================================
async def main() -> None:
    if BOT_TOKEN == "PASTE_NEW_BOT_TOKEN_HERE":
        raise ValueError("Yangi bot tokenni kiriting.")
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
