# filepath: c:\Users\ПК\dostup_bot\app\bot_v2.py
import asyncio
import logging
import os
import time
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from dotenv import load_dotenv
import openai
# Для проверки платежей через API нам нужен модуль stripe
import stripe
# from aiohttp import web  # для вебхуков не нужно

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
# Для простой интеграции нам нужен только URL платежной страницы
STRIPE_PAYMENT_URL  = os.getenv('STRIPE_PAYMENT_URL', 'https://buy.stripe.com/9B6fZg4TTcbwc6V7gT3Nm00')
# ID администратора для команд управления
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '403758011'))

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

# ───────────────────[ Stripe ]───────────────────────────
# Инициализация API Stripe для проверки платежей
stripe_client_ready = False
# Получаем ключ из переменных окружения
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
if STRIPE_API_KEY and STRIPE_API_KEY != 'your_stripe_api_key_here':
    stripe.api_key = STRIPE_API_KEY
    stripe_client_ready = True
    logger.info("Stripe API успешно инициализирован")
else:
    logger.warning("STRIPE_API_KEY не задан — проверка платежей будет недоступна")

# ───────────────────[ Aiogram ]──────────────────────────
bot     = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(bot, storage=storage)

# ───────────────────[ FSM ]──────────────────────────────
class QuestionStates(StatesGroup):
    waiting_for_question = State()
    
class PaymentCheckStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_name = State()

# ───────────────────[ DATA ]─────────────────────────────
COURSE_PRICES = {
    "basic":   {
        "price": 299_000, "title": "Базовый курс", "description": "Основы YouTube-бизнеса",
        "price_eur": 149, "stripe_price_id": "создайте ID цены в панели Stripe и вставьте его сюда"
    },
    "premium": {
        "price": 599_000, "title": "Премиум курс", "description": "Полная программа с поддержкой",
        "price_eur": 299, "stripe_price_id": "создайте ID цены в панели Stripe и вставьте его сюда"
    },
    "vip":     {
        "price": 999_000, "title": "VIP курс", "description": "Индивидуальное сопровождение",
        "price_eur": 499, "stripe_price_id": "создайте ID цены в панели Stripe и вставьте его сюда"
    }
}

# ───────────────────[ KEYBOARDS ]────────────────────────
main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🎬 Получить бесплатный урок")],
        [KeyboardButton("💳 Оплатить 149€")],
        [KeyboardButton("✅ Проверить оплату")],
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

# ───────────────────[ Stripe helper ]────────────────────
async def create_stripe_checkout(tariff: str, user_id: int) -> str:
    """Создаёт платёжную сессию в Stripe и возвращает URL для оплаты"""
    if not stripe_client_ready:
        return None
    
    try:
        price_cfg = COURSE_PRICES[tariff]
        # Получаем URL для перенаправления из переменных окружения или используем дефолтные
        success_url = os.getenv('STRIPE_SUCCESS_URL', 'https://t.me/your_bot_username')
        cancel_url = os.getenv('STRIPE_CANCEL_URL', 'https://t.me/your_bot_username')
        
        # Создаём чекаут сессию
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_cfg["stripe_price_id"],  # ID продукта/цены в Stripe
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{success_url}?session_id={{CHECKOUT_SESSION_ID}}&user_id={user_id}&tariff={tariff}',
            cancel_url=cancel_url,
            client_reference_id=str(user_id),  # Для связи с пользователем Telegram
            metadata={
                'user_id': str(user_id),
                'tariff': tariff,
            },
        )
        logger.info(f"Создана Stripe сессия: {checkout_session.id}")
        return checkout_session.url
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        return None

async def check_stripe_payment_by_email(email: str) -> bool:
    """Проверяет наличие успешного платежа по email покупателя"""
    if not stripe_client_ready:
        return False
    
    try:
        # Ищем платежи за последние 30 дней (максимум 100 записей)
        thirty_days_ago = int(time.time() - 30 * 24 * 60 * 60)
        payment_intents = stripe.PaymentIntent.list(
            limit=100,
            created={"gte": thirty_days_ago}
        )
        
        # Проверяем платежи
        for payment in payment_intents.data:
            if payment.status == 'succeeded':
                # Получаем данные о клиенте
                if hasattr(payment, 'customer') and payment.customer:
                    try:
                        customer = stripe.Customer.retrieve(payment.customer)
                        if customer.email and customer.email.lower() == email.lower():
                            logger.info(f"Найден успешный платеж для {email}: {payment.id}")
                            return True
                    except Exception as e:
                        logger.error(f"Ошибка при получении данных о клиенте: {e}")
                
                # Проверяем данные в метаданных платежа
                if hasattr(payment, 'metadata') and payment.metadata:
                    payment_email = payment.metadata.get('email')
                    if payment_email and payment_email.lower() == email.lower():
                        logger.info(f"Найден успешный платеж для {email} в метаданных: {payment.id}")
                        return True
                        
        logger.info(f"Платежи для {email} не найдены")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {e}")
        return False

async def check_stripe_payment_by_name(name: str) -> bool:
    """Проверяет наличие успешного платежа по имени покупателя (неточный поиск)"""
    if not stripe_client_ready:
        return False
    
    try:
        # Ищем платежи за последние 30 дней
        thirty_days_ago = int(time.time() - 30 * 24 * 60 * 60)
        payment_intents = stripe.PaymentIntent.list(
            limit=100,
            created={"gte": thirty_days_ago}
        )
        
        # Нормализуем имя для поиска (убираем пробелы, приводим к нижнему регистру)
        normalized_name = name.lower().replace(' ', '')
        
        # Проверяем платежи
        for payment in payment_intents.data:
            if payment.status == 'succeeded':
                # Проверяем данные клиента
                if hasattr(payment, 'customer') and payment.customer:
                    try:
                        customer = stripe.Customer.retrieve(payment.customer)
                        if customer.name:
                            customer_name = customer.name.lower().replace(' ', '')
                            if normalized_name in customer_name or customer_name in normalized_name:
                                logger.info(f"Найден успешный платеж для {name}: {payment.id}")
                                return True
                    except Exception as e:
                        logger.error(f"Ошибка при получении данных о клиенте: {e}")
                
                # Проверяем метаданные платежа
                if hasattr(payment, 'metadata') and payment.metadata:
                    customer_name = payment.metadata.get('name')
                    if customer_name:
                        customer_name = customer_name.lower().replace(' ', '')
                        if normalized_name in customer_name or customer_name in normalized_name:
                            logger.info(f"Найден успешный платеж для {name} в метаданных: {payment.id}")
                            return True
                
        logger.info(f"Платежи для {name} не найдены")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {e}")
        return False

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
async def payment_menu(message: types.Message):
    # Создаем inline клавиатуру с кнопкой для оплаты Stripe
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("💳 Оплатить картой", url=STRIPE_PAYMENT_URL))
    
    # Если настроен Telegram платеж, добавляем и эту опцию
    if PROVIDER_TOKEN:
        keyboard.add(InlineKeyboardButton("💰 Оплатить через Telegram", callback_data="telegram_pay_basic"))
    
    await message.answer(
        "Выберите способ оплаты:\n\n"
        "1️⃣ Оплата картой - быстро и безопасно\n"
        "2️⃣ После оплаты используйте команду /check_payment\n"
        "3️⃣ Мы автоматически проверим вашу оплату и выдадим доступ\n\n"
        "❓ Если возникли проблемы, напишите нам 'Я оплатил курс'", 
        reply_markup=keyboard
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
    
# ─────────[ Проверка оплаты ]───────────────────────────
# Команда для проверки статуса оплаты (для администратора)
@dp.message_handler(lambda m: m.text.lower() == "проверить оплаты" and m.from_user.id == ADMIN_USER_ID)
async def check_all_payments_status(message: types.Message):
    # Эту функцию можно использовать для проверки платежей в ручном режиме
    await message.answer("Для просмотра всех платежей перейдите в панель Stripe: https://dashboard.stripe.com/payments")

# Команда для пользователя - проверить свою оплату
@dp.message_handler(commands=["check_payment"])
@dp.message_handler(lambda m: m.text.lower() in ["проверить оплату", "проверить мою оплату", "/check_payment"])
async def check_user_payment_start(message: types.Message, state: FSMContext):
    if not stripe_client_ready:
        await message.answer(
            "❌ К сожалению, проверка платежей временно недоступна.\n"
            "Если вы уже оплатили, напишите 'Я оплатил курс' и мы проверим вручную.",
            reply_markup=main_menu
        )
        return
        
    await message.answer(
        "Для проверки вашего платежа нам нужен email, который вы указали при оплате.\n\n"
        "Пожалуйста, введите этот email:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Отмена")]], resize_keyboard=True)
    )
    await PaymentCheckStates.waiting_for_email.set()

# Обработчик ввода email для проверки
@dp.message_handler(state=PaymentCheckStates.waiting_for_email)
async def check_payment_by_email(message: types.Message, state: FSMContext):
    if message.text.lower() == "🔙 отмена":
        await state.finish()
        await message.answer("❌ Проверка отменена.", reply_markup=main_menu)
        return
        
    email = message.text.strip()
    
    # Валидация email
    if "@" not in email or "." not in email:
        await message.answer(
            "❌ Пожалуйста, введите корректный email адрес.\n"
            "Например: name@example.com"
        )
        return
    
    # Сохраняем email и просим ввести имя
    await state.update_data(email=email)
    await message.answer(
        "Спасибо! Теперь введите имя, которое вы указали при оплате:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Отмена")]], resize_keyboard=True)
    )
    
    await PaymentCheckStates.waiting_for_name.set()

# Обработчик ввода имени для проверки
@dp.message_handler(state=PaymentCheckStates.waiting_for_name)
async def check_payment_by_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "🔙 отмена":
        await state.finish()
        await message.answer("❌ Проверка отменена.", reply_markup=main_menu)
        return
        
    user_data = await state.get_data()
    email = user_data.get("email")
    name = message.text.strip()
    
    # Сообщаем о начале проверки
    await message.answer("🔄 Проверяем оплату... Это может занять несколько секунд.")
    
    # Проверяем оплату по email
    email_payment_found = await check_stripe_payment_by_email(email)
    
    # Проверяем оплату по имени, если по email не нашли
    name_payment_found = False
    if not email_payment_found:
        name_payment_found = await check_stripe_payment_by_name(name)
    
    # Если платеж найден - отправляем доступ
    if email_payment_found or name_payment_found:
        await send_course_access(message.from_user.id)
        await message.answer(
            "✅ Мы нашли ваш платеж! Доступ к курсу предоставлен.",
            reply_markup=main_menu
        )
    else:
        # Если платеж не найден
        await message.answer(
            "❌ К сожалению, мы не смогли найти ваш платеж.\n\n"
            "Возможные причины:\n"
            "1️⃣ Платеж еще обрабатывается (это может занять до 15 минут)\n"
            "2️⃣ Вы указали другой email или имя при оплате\n"
            "3️⃣ Оплата не была завершена\n\n"
            "Пожалуйста, подождите немного и попробуйте снова, или напишите нам: 'Я оплатил курс'",
            reply_markup=main_menu
        )
    
    await state.finish()

# ─────────[ Обработчики для получения оплаты ]─────────────────
# Хендлер для обработки сообщений от пользователя об оплате
@dp.message_handler(lambda m: "оплатил" in m.text.lower() or "оплатила" in m.text.lower())
async def handle_payment_notification(message: types.Message):
    # Отправляем администратору уведомление о платеже
    admin_id = ADMIN_USER_ID
    
    try:
        await bot.send_message(
            chat_id=admin_id,
            text=f"💰 Пользователь сообщает об оплате!\n\n"
                 f"👤 Пользователь: {message.from_user.full_name} (@{message.from_user.username})\n"
                 f"🆔 ID: {message.from_user.id}\n\n"
                 f"✉️ Сообщение: {message.text}"
        )
        
        # Отвечаем пользователю
        await message.answer(
            "✅ Спасибо за информацию об оплате!\n\n"
            "Мы проверим её в ближайшее время и предоставим вам доступ к материалам курса. "
            "Обычно это занимает не более 15 минут.",
            reply_markup=main_menu
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке уведомления об оплате: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, напишите нам на почту support@example.com")
        
# Команда администратора для выдачи доступа вручную
@dp.message_handler(lambda m: m.text.startswith("/grant_access") and m.from_user.id == ADMIN_USER_ID)
async def grant_access(message: types.Message):
    try:
        # Формат команды: /grant_access USER_ID
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /grant_access USER_ID")
            return
            
        user_id = int(parts[1])
        
        # Используем созданную нами функцию для отправки доступа
        success = await send_course_access(user_id)
        
        # Сообщаем администратору об успешной выдаче доступа
        await message.answer(f"✅ Доступ успешно выдан пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при выдаче доступа: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith("telegram_pay_"))
async def process_telegram_payment(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    tariff = callback_query.data.replace("telegram_pay_", "")
    
    if not PROVIDER_TOKEN:
        await callback_query.message.answer(
            "❌ Оплата через Telegram временно недоступна.", 
            reply_markup=main_menu
        )
        return
    
    price_cfg = COURSE_PRICES[tariff]
    prices = [types.LabeledPrice(label=price_cfg["title"], amount=price_cfg["price"])]
    
    try:
        await bot.send_invoice(
            chat_id=callback_query.message.chat.id,
            title=price_cfg["title"],
            description=price_cfg["description"],
            payload=f"course_{tariff}",
            provider_token=PROVIDER_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="yt-course"
        )
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        await callback_query.message.answer(
            "❌ Не удалось создать счет.", 
            reply_markup=main_menu
        )

# ─────────[ FALLBACK: чат ]──────────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "✅ проверить оплату")
async def check_payment_button(message: types.Message, state: FSMContext):
    # Перенаправляем на обработчик проверки оплаты
    await check_user_payment_start(message, state)

@dp.message_handler(content_types=types.ContentType.TEXT)
async def ai_fallback(message: types.Message, state: FSMContext):
    if await state.get_state() is not None:
        return
    menu_cmds = {"🎬 получить бесплатный урок", "💳 оплатить 149€", "ℹ️ о курсе", "❓ задать вопрос", "✅ проверить оплату", "/start", "старт"}
    if message.text.lower() in menu_cmds:
        return
    if not openai_client_ready:
        await message.answer("👋 Выберите действие из меню:", reply_markup=main_menu)
        return
    await message.answer("🤔 Думаю...")
    rsp = await ask_assistant(message.text)
    await message.answer(f"💡 {rsp}", reply_markup=main_menu)

# ───────────────────[ Функции для выдачи доступа ]─────────────────────
# Полезная функция для отправки ссылки пользователю при ручном подтверждении
async def send_course_access(user_id: int, tariff: str = "basic"):
    """Отправляет доступ к курсу пользователю"""
    try:
        # Используем ссылку из .env
        invite_link = CHANNEL_INVITE_LINK if CHANNEL_INVITE_LINK else "https://t.me/+xazMLl_YLUllMzUy"
        
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Ваш платеж подтвержден!\n\n"
                f"Ваша ссылка для доступа в закрытый канал: {invite_link}\n\n"
                f"Добро пожаловать в наше сообщество! 🎉"
            ),
            reply_markup=main_menu
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки доступа: {e} для пользователя {user_id}")
        return False

# ───────────────────[ Упрощенная интеграция - без webhook-сервера ]─────────────
# Webhook-функционал отключен, так как используем упрощенную интеграцию
# В будущем при необходимости можно раскомментировать и настроить
    
    # Запуск в фоновом режиме
    # Примечание: в продакшене следует использовать лучший вариант асинхронного запуска
    runner = web.AppRunner(app)
    return runner

# ───────────────────[ MAIN ]─────────────────────────────
async def main():
    logger.info("Bot starting…")
    
    # В упрощённой версии интеграции со Stripe не используем webhook-сервер
    webhook_runner = None
    # Закомментировано, так как используем простую интеграцию без API
    # if 'STRIPE_API_KEY' in os.environ and 'STRIPE_WEBHOOK_SECRET' in os.environ:
    #     webhook_runner = setup_webhook_server(dp)
    #     await webhook_runner.setup()
    #     site = web.TCPSite(webhook_runner, 'localhost', 8080)
    #     await site.start()
    #     logger.info("Webhook server started on http://localhost:8080")
    
    try:
        # Запуск бота
        await dp.start_polling()
    finally:
        # Закрытие соединений
        if webhook_runner:
            await webhook_runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
