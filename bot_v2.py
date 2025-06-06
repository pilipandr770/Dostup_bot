# filepath: c:\Users\ПК\dostup_bot\app\bot_v2.py
import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from dotenv import load_dotenv
import openai

# ───────────────────[ ENV & LOGGING ]───────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ───────────────────[ CONFIG ]───────────────────────────
BOT_TOKEN           = os.getenv('BOT_TOKEN')
PROVIDER_TOKEN      = os.getenv('PROVIDER_TOKEN')
COURSE_CHANNEL_ID   = os.getenv('COURSE_CHANNEL_ID')
OPENAI_API_KEY      = os.getenv('OPENAI_API_KEY')
OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

# Шлях до безкоштовного відео-уроку (локальний файл)
LESSON_VIDEO_PATH = Path(r"C:\Users\ПК\dostup_bot\lessons\ЮТУБ урок 0.mp4")

# Перевірка ключів
if not BOT_TOKEN or BOT_TOKEN == 'YOUR_REAL_BOT_TOKEN_HERE':
    logger.error("BOT_TOKEN не налаштовано!")
    raise SystemExit(1)

# ───────────────────[ OpenAI ]───────────────────────────
openai_client_ready = False
if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_api_key_here':
    openai.api_key = OPENAI_API_KEY
    openai_client_ready = True
    logger.info("OpenAI API ініціалізовано")
else:
    logger.warning("OpenAI API-ключ не задано — функції Assistant вимкнені")

# ───────────────────[ Aiogram ]──────────────────────────
bot     = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(bot, storage=storage)

# ───────────────────[ FSM ]──────────────────────────────
class QuestionStates(StatesGroup):
    waiting_for_question = State()

# ───────────────────[ DATA ]─────────────────────────────
COURSE_PRICES = {
    "basic":   {"price": 299_000, "title": "Базовый курс",   "description": "Основы YouTube-бизнеса"},
    "premium": {"price": 599_000, "title": "Премиум курс",  "description": "Полная программа с поддержкой"},
    "vip":     {"price": 999_000, "title": "VIP курс",      "description": "Индивидуальное сопровождение"}
}

# ───────────────────[ KEYBOARDS ]────────────────────────
main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🎬 Отримати безкоштовний урок")],
        [KeyboardButton("💰 Купити курс"), KeyboardButton("ℹ️ Про курс")],
        [KeyboardButton("❓ Поставити запитання")]
    ],
    resize_keyboard=True
)

buy_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💎 Базовый - 2990₽")],
        [KeyboardButton("🚀 Премиум - 5990₽")],
        [KeyboardButton("👑 VIP - 9990₽")],
        [KeyboardButton("🔙 Головне меню")]
    ],
    resize_keyboard=True
)

# ───────────────────[ OpenAI helper ]────────────────────
async def ask_assistant(question: str) -> str:
    if not openai_client_ready:
        return "❌ OpenAI Assistant недоступний."
    try:
        rsp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "Ти експерт з YouTube-бізнесу. "
                            "Допомагай користувачам запускати та монетизувати канали."},
                {"role": "user", "content": question}
            ],
            max_tokens=800,
            temperature=0.7,
        )
        return rsp.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "❌ Помилка OpenAI, спробуйте пізніше."

# ───────────────────[ HANDLERS ]─────────────────────────
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text.lower() == "старт")
async def cmd_start(message: types.Message, state: FSMContext):
    text = (
        "👋 Вітаю у боті курсу «Успішний YouTube-бізнес з нуля»!\n\n"
        "🎁 Щоб почати, отримай безкоштовний ознайомчий урок.\n"
        "Натисни «🎬 Отримати безкоштовний урок»👇"
    )
    await message.answer(text, reply_markup=main_menu)
    await state.finish()

# ─────────[ Безкоштовний урок ]──────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "🎬 отримати безкоштовний урок")
async def send_free_lesson(message: types.Message):
    logger.info(f"Free lesson requested by {message.from_user.id}")

    if LESSON_VIDEO_PATH.exists():
        await bot.send_video(
            chat_id=message.chat.id,
            video=types.InputFile(LESSON_VIDEO_PATH),
            caption="🎬 Безкоштовний урок: дивись і роби перші кроки!"
        )
    else:
        await message.answer(
            "❌ Відео наразі недоступне. Спробуйте пізніше.",
            reply_markup=main_menu
        )
        logger.error(f"Video not found at {LESSON_VIDEO_PATH}")

# ─────────[ Інформація про курс ]────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "ℹ️ про курс")
async def course_info(message: types.Message):
    text = (
        "📚 **Курс «Успішний YouTube-бізнес з нуля»**\n\n"
        "✔️ Поетапний запуск каналу\n"
        "✔️ Стратегії монетизації\n"
        "✔️ Підтримка експертів\n\n"
        "💰 Щоб придбати, обери тариф у меню «Купити курс»."
    )
    await message.answer(text, reply_markup=main_menu, parse_mode="Markdown")

# ─────────[ Меню покупки ]───────────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "💰 купити курс")
async def buy_menu_handler(message: types.Message):
    await message.answer(
        "💰 Обери тариф і слідуй інструкціям:",
        reply_markup=buy_menu
    )

# ─────────[ Створення інвойсу ]──────────────────────────
@dp.message_handler(lambda m: m.text in ["💎 Базовый - 2990₽", "🚀 Премиум - 5990₽", "👑 VIP - 9990₽"])
async def create_invoice(message: types.Message):
    tariff_key = ("basic"   if "Базовый" in message.text else
                  "premium" if "Премиум" in message.text else
                  "vip")
    price_cfg = COURSE_PRICES[tariff_key]

    prices = [types.LabeledPrice(label=price_cfg["title"], amount=price_cfg["price"])]
    try:
        await bot.send_invoice(
            chat_id=message.chat.id,
            title=price_cfg["title"],
            description=price_cfg["description"],
            payload=f"course_{tariff_key}",
            provider_token=PROVIDER_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="yt-course"
        )
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        await message.answer("❌ Не вдалося створити рахунок.", reply_markup=main_menu)

# ─────────[ FSM: питання ]────────────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "❓ поставити запитання")
async def ask_question(message: types.Message, state: FSMContext):
    if not openai_client_ready:
        await message.answer("❌ Питання тимчасово недоступні.", reply_markup=main_menu)
        return
    await QuestionStates.waiting_for_question.set()
    await message.answer(
        "Введіть своє питання щодо YouTube-каналів.\n\n"
        "Для відміни натисніть «🔙 Скасувати».",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
    )

@dp.message_handler(state=QuestionStates.waiting_for_question)
async def handle_question(message: types.Message, state: FSMContext):
    if message.text.lower() == "🔙 скасувати":
        await state.finish()
        await message.answer("❌ Скасовано.", reply_markup=main_menu)
        return
    await message.answer("🤔 Думаю...")
    reply = await ask_assistant(message.text)
    await message.answer(f"💡 {reply}", reply_markup=main_menu)
    await state.finish()

# ─────────[ Оплата ]─────────────────────────────────────
@dp.pre_checkout_query_handler()
async def pre_checkout(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    tariff = message.successful_payment.invoice_payload.replace("course_", "")
    await message.answer(
        f"✅ Дякуємо за оплату тарифу **{COURSE_PRICES[tariff]['title']}**!\n"
        "Доступи буде надіслано протягом 24 годин.",
        parse_mode="Markdown",
        reply_markup=main_menu
    )

# ─────────[ FALLBACK: чат ]──────────────────────────────
@dp.message_handler(content_types=types.ContentType.TEXT)
async def ai_fallback(message: types.Message, state: FSMContext):
    if await state.get_state() is not None:
        return
    menu_cmds = {"🎬 отримати безкоштовний урок", "💰 купити курс", "ℹ️ про курс",
                 "❓ поставити запитання", "🔙 головне меню", "/start", "старт",
                 "💎 базовый - 2990₽", "🚀 премиум - 5990₽", "👑 vip - 9990₽"}
    if message.text.lower() in menu_cmds:
        return
    if not openai_client_ready:
        await message.answer("👋 Оберіть дію з меню:", reply_markup=main_menu)
        return
    await message.answer("🤔 Думаю...")
    rsp = await ask_assistant(message.text)
    await message.answer(f"💡 {rsp}", reply_markup=main_menu)

# ───────────────────[ MAIN ]─────────────────────────────
async def main():
    logger.info("Bot starting…")
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
