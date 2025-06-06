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
YOUTUBE_CHANNEL_URL = os.getenv('YOUTUBE_CHANNEL_URL')
CHANNEL_INVITE_LINK = os.getenv('CHANNEL_INVITE_LINK')
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
        [KeyboardButton("🎬 Получить бесплатный урок")],
        [KeyboardButton("💳 Оплатить 149€")],
        [KeyboardButton("❓ Задать вопрос")]
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
# Для работы с OpenAI Assistant API требуется openai>=1.3.0
# В requirements.txt должно быть: openai>=1.3.0
# В .env должен быть OPENAI_ASSISTANT_ID=asst_...
# Ответ ассистента приходит через OpenAI Assistants API
async def ask_assistant(question: str) -> str:
    if not openai_client_ready:
        return "❌ OpenAI Assistant недоступен."
    try:
        # Используем OpenAI Assistants API (asst_...)
        thread = openai.beta.threads.create()
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=OPENAI_ASSISTANT_ID
        )
        # Ждем завершения run
        import time
        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            elif run_status.status in ("failed", "cancelled", "expired"):
                return "❌ Ошибка OpenAI Assistant. Попробуйте позже."
            time.sleep(1)
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        # Берем последний ответ ассистента
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                return msg.content[0].text.value
        return "❌ Нет ответа от ассистента."
    except Exception as e:
        logger.error(f"OpenAI Assistant error: {e}")
        return "❌ Ошибка OpenAI Assistant, попробуйте позже."

# ───────────────────[ HANDLERS ]─────────────────────────
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text.lower() == "старт")
async def cmd_start(message: types.Message, state: FSMContext):
    text = (
        "👋 Добро пожаловать в бот курса 'Успешный YouTube-бизнес с нуля'!\n\n"
        "🎬 Получи бесплатный ознакомительный урок — просто нажми соответствующую кнопку.\n\n"
        "💳 Чтобы получить доступ ко всем материалам и закрытому Telegram-сообществу, оплати участие (149€) — и сразу получишь ссылку для входа.\n\n"
        "❓ В любое время можешь задать вопрос по YouTube — тебе поможет AI-ассистент!\n\n"
        "Удачи и больших доходов на YouTube!"
    )
    await message.answer(text, reply_markup=main_menu)
    await state.finish()

# ─────────[ Безкоштовний урок ]──────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "🎬 получить бесплатный урок")
async def send_free_lesson(message: types.Message):
    await message.answer(
        f"🎬 Вот твой бесплатный ознакомительный урок!\n\nСмотри на YouTube: {YOUTUBE_CHANNEL_URL}",
        reply_markup=main_menu
    )

# ─────────[ Інформація про курс ]────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "ℹ️ о курсе")
async def course_info(message: types.Message):
    text = (
        "📚 Курс «Успешный YouTube-бизнес с нуля»\n\n"
        "✔️ Пошаговый запуск канала\n"
        "✔️ Стратегии монетизации\n"
        "✔️ Поддержка экспертов\n\n"
        "💰 Чтобы получить доступ, воспользуйся кнопкой оплаты."
    )
    await message.answer(text, reply_markup=main_menu, parse_mode="Markdown")

# ─────────[ Меню покупки ]───────────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "💳 оплатить 149€")
async def fake_payment(message: types.Message):
    # Используем ссылку из .env или дефолтную
    invite_link = CHANNEL_INVITE_LINK if CHANNEL_INVITE_LINK else "https://t.me/+xazMLl_YLUllMzUy"
    await message.answer(
        f"✅ Оплата прошла успешно!\n\nВаша ссылка для доступа в закрытый канал: {invite_link}",
        reply_markup=main_menu
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
@dp.message_handler(lambda m: m.text.lower() == "❓ задать вопрос")
async def ask_question(message: types.Message, state: FSMContext):
    if not openai_client_ready:
        await message.answer("❌ Вопросы временно недоступны.", reply_markup=main_menu)
        return
    await QuestionStates.waiting_for_question.set()
    await message.answer(
        "Введите ваш вопрос по YouTube-каналам.\n\nДля отмены нажмите «🔙 Отмена».",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Отмена")]], resize_keyboard=True)
    )

@dp.message_handler(state=QuestionStates.waiting_for_question)
async def handle_question(message: types.Message, state: FSMContext):
    if message.text.lower() == "🔙 отмена":
        await state.finish()
        await message.answer("❌ Отменено.", reply_markup=main_menu)
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
    menu_cmds = {"🎬 получить бесплатный урок", "💳 оплатить 149€", "ℹ️ о курсе", "❓ задать вопрос", "/start", "старт"}
    if message.text.lower() in menu_cmds:
        return
    if not openai_client_ready:
        await message.answer("👋 Выберите действие из меню:", reply_markup=main_menu)
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
