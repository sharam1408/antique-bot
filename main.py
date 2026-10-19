import asyncio
import logging
import os
import re
import urllib.parse
from aiohttp import web

from aiogram import Bot, Dispatcher, F, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

BOT_TOKEN = "8872342248:AAF2XA6ptR0IUTkkbjlAHuqYXapq0lMgZLU"

PRICE_TIERS = {
    "xviii": {"max_year": 1800, "min_price": 50000, "max_price": 300000, "label": "🏛 Памятник книгопечатания XVIII в."},
    "pushkin": {"max_year": 1850, "min_price": 30000, "max_price": 180000, "label": "📜 Золотой век / Эпоха Пушкина"},
    "late_xix": {"max_year": 1900, "min_price": 10000, "max_price": 70000, "label": "📖 Вторая половина XIX века"},
    "silver": {"max_year": 1917, "min_price": 5000, "max_price": 40000, "label": "⚜️ Серебряный век (до 1917 г.)"}
}

def parse_book_request(raw_text: str):
    clean_query = re.sub(r"\s+", " ", raw_text).strip()
    year_match = re.search(r"\b(1[6-9]\d{2}|20\d{2})\b", clean_query)
    if year_match:
        return clean_query, int(year_match.group(1)), True
    return clean_query, 1895, False

def get_pricing_info(year: int):
    if year < PRICE_TIERS["xviii"]["max_year"]:
        t = PRICE_TIERS["xviii"]
    elif year <= PRICE_TIERS["pushkin"]["max_year"]:
        t = PRICE_TIERS["pushkin"]
    elif year <= PRICE_TIERS["late_xix"]["max_year"]:
        t = PRICE_TIERS["late_xix"]
    else:
        t = PRICE_TIERS["silver"]
    return t["min_price"], t["max_price"], t["label"]

def make_search_keyboard(query: str) -> InlineKeyboardMarkup:
    not_books = "-монета -марка -значок -открытка -бона -плакат -фотография -медаль"
    query_strict = f"{query} {not_books}"
    enc_q = urllib.parse.quote(query_strict)
    enc_q_clean = urllib.parse.quote(query)

    avito_title_url = f"https://www.avito.ru/rossiya/knigi_i_zhurnaly?q={enc_q}&pmin=1000&searchInTitle=1"
    avito_full_url = f"https://www.avito.ru/rossiya/knigi_i_zhurnaly?q={enc_q}&pmin=1000"
    meshok_antique_url = f"https://meshok.net/listing?good=115&search={enc_q}&price_from=1000"
    meshok_books_url = f"https://meshok.net/listing?good=179&search={enc_q}&price_from=1000"
    alib_query = urllib.parse.quote(f"site:alib.ru {query}")
    alib_url = f"https://yandex.ru/search/?text={alib_query}"
    libex_url = f"https://www.libex.ru/search/?tfind={enc_q_clean}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏛 Meshok: Антикварные книги (от 1 000 ₽)", url=meshok_antique_url)],
        [InlineKeyboardButton(text="📖 Meshok: Раздел всех книг (от 1 000 ₽)", url=meshok_books_url)],
        [InlineKeyboardButton(text="🎯 Авито: По заголовкам (от 1 000 ₽)", url=avito_title_url)],
        [InlineKeyboardButton(text="📦 Авито: По описанию (от 1 000 ₽)", url=avito_full_url)],
        [
            InlineKeyboardButton(text="📜 Alib.ru", url=alib_url),
            InlineKeyboardButton(text="📚 Libex.ru", url=libex_url)
        ]
    ])

@dp.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(
        "Приветствую! 🏛\n"
        "Я бот для <b>точного поиска и оценки антикварных книг (до 1917 г., от 1 000 ₽)</b>.\n\n"
        "Отправьте автора, название, издательство или год издания:\n"
        "• <code>Пушкин 1887</code>\n"
        "• <code>Пушкин Суворин</code>\n"
        "• <code>Карамзин История 1842</code>"
    )

@dp.message(F.text)
async def handle_book(msg: Message):
    raw_query = msg.text.strip()
    if raw_query.startswith("/"):
        return

    clean_query, year, has_exact_year = parse_book_request(raw_query)

    if has_exact_year and year > 1917:
        await msg.answer(
            f"⚠️ <b>Внимание:</b> Указан <b>{year} год</b>.\n"
            f"Бот предназначен для поиска изданий <b>до 1917 года включительно</b>."
        )
        return

    p_min, p_max, rarity = get_pricing_info(year)
    p_min_fmt = f"{p_min:,}".replace(",", " ")
    p_max_fmt = f"{p_max:,}".replace(",", " ")
    year_label = f"{year} г." if has_exact_year else f"до 1917 г. (ориентир {year} г.)"

    text = (
        f"🏛 <b>АНТИКВАРНАЯ КНИГА (ДО 1917 ГОДА)</b>\n\n"
        f"📖 <b>Поисковый запрос:</b> <code>{html.quote(clean_query)}</code>\n"
        f"📅 <b>Эпоха:</b> {year_label}\n"
        f"🎖 <b>Категория:</b> {rarity}\n"
        f"💵 <b>Фильтр цены:</b> <code>от 1 000 ₽</code>\n\n"
        f"📊 <b>ОРИЕНТИРЫ РЫНКА (СПРАВОЧНО):</b>\n"
        f"• Отдельные тома / дефекты: <code>от 1 000 – 4 000 ₽</code>\n"
        f"• Комплектные в сохранности: <code>{p_min_fmt} – {p_max_fmt} ₽</code>\n\n"
        f"🔎 <b>Ссылки на книжные каталоги:</b>"
    )

    kb = make_search_keyboard(clean_query)
    await msg.answer(text, reply_markup=kb)

async def handle_ping(request):
    return web.Response(text="Bot is running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    me = await bot.get_me()
    print(f"\n>>> БОТ ЗАПУЩЕН: @{me.username} <<<\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
