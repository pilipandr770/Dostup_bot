import asyncio
import logging
import os
import time
import sys
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

# ───────────────────[ НАСТРОЙКА РАСШИРЕННОГО ЛОГИРОВАНИЯ ]───────────────────
# Настраиваем расширенное логирование
logging.basicConfig(
    level=logging.DEBUG,  # Используем DEBUG уровень для максимальной детализации
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("c:\\Users\\ПК\\dostup_bot\\bot_debug.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("=== ЗАПУСК БОТА С РАСШИРЕННЫМ ЛОГИРОВАНИЕМ ===")

# ───────────────────[ CONFIG ]───────────────────────────
load_dotenv()
BOT_TOKEN           = os.getenv('BOT_TOKEN')
COURSE_CHANNEL_ID   = os.getenv('COURSE_CHANNEL_ID')
YOUTUBE_CHANNEL_URL = os.getenv('YOUTUBE_CHANNEL_URL')
CHANNEL_INVITE_LINK = os.getenv('CHANNEL_INVITE_LINK')
OPENAI_API_KEY      = os.getenv('OPENAI_API_KEY')
OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')
# URL страницы оплаты Stripe
STRIPE_PAYMENT_URL  = os.getenv('STRIPE_PAYMENT_URL', 'https://buy.stripe.com/9B6fZg4TTcbwc6V7gT3Nm00')
# ID администратора для команд управления
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '403758011'))

logger.info(f"Конфигурация загружена: BOT_TOKEN={'Настроен' if BOT_TOKEN else 'Не настроен'}, COURSE_CHANNEL_ID={COURSE_CHANNEL_ID}")

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

class AgreementStates(StatesGroup):
    waiting_for_agb = State()
    waiting_for_widerruf = State()
    waiting_for_datenschutz = State()

# ───────────────────[ DATA ]─────────────────────────────
# Данные курса - упрощенная версия, только один курс за 149€
COURSE_TITLE = "Успешный YouTube-бизнес с нуля"
COURSE_DESCRIPTION = "Полный доступ к курсу и закрытому сообществу"
COURSE_PRICE_EUR = 149

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

# ───────────────────[ Legal Documents Helpers ]───────────────────
# Жестко закодированные тексты документов
LEGAL_DOCS = {
    "agb": """📋 ДОКУМЕНТ 1: Allgemeine Geschäftsbedingungen (AGB)
für den Online-Verkauf digitaler Inhalte (Online-Kurse)

1. Geltungsbereich
Diese Allgemeinen Geschäftsbedingungen (AGB) gelten für alle Verträge zwischen Firma Alexander Cherkasky Schlitzer Strasse 6, 60386 Frankfurt am Main (nachfolgend „Anbieter") und dem Kunden über den Erwerb und die Nutzung digitaler Inhalte, insbesondere Online-Kurse über die Plattform YouTube oder andere digitale Plattformen.

2. Vertragsgegenstand
Vertragsgegenstand ist der Zugang zu einem Online-Kurs, der aus vorab aufgezeichneten Videolektionen besteht. Der Zugang erfolgt digital und ausschließlich zur persönlichen Nutzung des Kunden.

3. Vertragsabschluss
Der Vertrag kommt zustande, sobald der Kunde den Bestellvorgang abgeschlossen und der Anbieter die Bestellung bestätigt hat.

4. Preise und Zahlung
Alle angegebenen Preise verstehen sich als Endpreise in Euro. Die Zahlung erfolgt über die im Bestellprozess angebotenen Zahlungsmethoden. Der Zugang zum Kurs wird nach erfolgreichem Zahlungseingang freigeschaltet.

5. Widerrufsrecht
Bei digitalen Inhalten besteht kein Widerrufsrecht, sobald die Ausführung begonnen hat und der Kunde ausdrücklich zugestimmt hat.

6. Haftung
Die Haftung des Anbieters ist auf Vorsatz und grobe Fahrlässigkeit beschränkt.

7. Anwendbares Recht
Es gilt deutsches Recht.
""",

    "widerruf": """📋 ДОКУМЕНТ 2: Widerrufsverzicht

Ich stimme ausdrücklich zu, dass der Anbieter mit der Ausführung des Vertrages vor Ablauf der Widerrufsfrist beginnt.

Mir ist bekannt, dass ich bei vollständiger Vertragserfüllung durch den Anbieter mein Widerrufsrecht verliere, wenn der Vertrag auf meinen ausdrücklichen Wunsch erfüllt wurde, bevor die Widerrufsfrist abgelaufen ist.

Bei digitalen Inhalten, deren Bereitstellung nicht auf einem körperlichen Datenträger erfolgt, verliere ich mein Widerrufsrecht, sobald der Anbieter mit der Ausführung begonnen hat, nachdem ich ausdrücklich zugestimmt habe und bestätigt habe, dass ich mein Widerrufsrecht bei Beginn der Ausführung verliere.

Ich bestätige hiermit meinen ausdrücklichen Verzicht auf das Widerrufsrecht.
""",

    "datenschutz": """📋 ДОКУМЕНТ 3: Datenschutzerklärung

1. Datenerhebung und -verarbeitung
Wir erheben und verarbeiten personenbezogene Daten nur im Rahmen der gesetzlichen Bestimmungen der DSGVO.

2. Zweck der Datenverarbeitung
Ihre Daten werden ausschließlich zur Abwicklung des Kaufvertrages und zur Bereitstellung des erworbenen Online-Kurses verwendet.

3. Datenweitergabe
Eine Weitergabe Ihrer Daten an Dritte erfolgt nur, soweit dies zur Vertragsabwicklung erforderlich ist (z.B. Zahlungsabwicklung).

4. Ihre Rechte
Sie haben das Recht auf Auskunft, Berichtigung, Löschung und Einschränkung der Verarbeitung Ihrer Daten.

5. Kontakt
Für Fragen zum Datenschutz kontaktieren Sie uns unter: [Kontaktdaten]

Mit der Zustimmung erklären Sie sich mit der Verarbeitung Ihrer Daten gemäß dieser Datenschutzerklärung einverstanden.
"""
}

async def get_document(doc_name: str) -> str:
    """Возвращает текст юридического документа из предопределенных строк"""
    logger.debug(f"Запрошен документ: {doc_name}")
    start_time = time.time()
    try:
        if doc_name in LEGAL_DOCS:
            doc_text = LEGAL_DOCS[doc_name]
            logger.debug(f"Документ {doc_name} получен из LEGAL_DOCS, длина: {len(doc_text)} символов")
            return doc_text
        else:
            logger.error(f"Запрошен неизвестный документ: {doc_name}")
            return "⚠️ Документ не найден."
    finally:
        end_time = time.time()
        logger.debug(f"Время получения документа {doc_name}: {end_time - start_time:.4f} сек")

# Клавиатуры для юридических документов
def get_agreement_keyboard(doc_type: str) -> InlineKeyboardMarkup:
    """Returns keyboard for legal document agreement"""
    logger.debug(f"Создание клавиатуры соглашения для {doc_type}")
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        InlineKeyboardButton("✅ Я согласен", callback_data=f"agree_{doc_type}"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_agreement")
    )
    return keyboard

# ───────────────────[ OpenAI helper ]────────────────────
# Для работы с OpenAI Assistant API требуется openai>=1.3.0
async def ask_assistant(question: str) -> str:
    if not openai_client_ready:
        return "❌ OpenAI Assistant недоступен."
    try:
        logger.info(f"Отправка вопроса в OpenAI: {question[:50]}...")
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
async def check_stripe_payment_by_email(email: str) -> bool:
    """Проверяет наличие успешного платежа по email покупателя"""
    if not stripe_client_ready:
        return False
    
    try:
        logger.info(f"Проверка платежа по email: {email}")
        # Ищем платежи за последние 30 дней (максимум 100 записей)
        thirty_days_ago = int(time.time() - 30 * 24 * 60 * 60)
        
        # Проверяем платежи через Payment Intents
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
        
        # Дополнительно проверяем через Checkout Sessions
        try:
            checkout_sessions = stripe.checkout.Session.list(
                limit=100,
                created={"gte": thirty_days_ago}
            )
            
            for session in checkout_sessions.data:
                if session.payment_status == 'paid' and hasattr(session, 'customer_details'):
                    if session.customer_details.email and session.customer_details.email.lower() == email.lower():
                        logger.info(f"Найден успешный платеж в сессии для {email}: {session.id}")
                        return True
        except Exception as e:
            logger.error(f"Ошибка при проверке сессий: {e}")
                        
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
        logger.info(f"Проверка платежа по имени: {name}")
        # Ищем платежи за последние 30 дней
        thirty_days_ago = int(time.time() - 30 * 24 * 60 * 60)
        
        # Нормализуем имя для поиска (убираем пробелы, приводим к нижнему регистру)
        normalized_name = name.lower().replace(' ', '')
        
        # Проверяем через Checkout Sessions (они содержат больше информации о клиенте)
        try:
            checkout_sessions = stripe.checkout.Session.list(
                limit=100,
                created={"gte": thirty_days_ago}
            )
            
            for session in checkout_sessions.data:
                if session.payment_status == 'paid' and hasattr(session, 'customer_details'):
                    if session.customer_details.name:
                        customer_name = session.customer_details.name.lower().replace(' ', '')
                        if normalized_name in customer_name or customer_name in normalized_name:
                            logger.info(f"Найден успешный платеж в сессии для {name}: {session.id}")
                            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке сессий: {e}")
        
        # Проверяем платежи через Payment Intents
        payment_intents = stripe.PaymentIntent.list(
            limit=100,
            created={"gte": thirty_days_ago}
        )
        
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

# Доступ к курсу
async def send_course_access(user_id: int):
    """Выдаёт доступ пользователю к курсу"""
    try:
        logger.info(f"Попытка выдать доступ пользователю {user_id}")
        # Пробуем добавить пользователя в закрытый канал
        if COURSE_CHANNEL_ID:
            try:
                # Добавляем пользователя в группу
                await bot.approve_chat_join_request(
                    chat_id=COURSE_CHANNEL_ID,
                    user_id=user_id
                )
                logger.info(f"Пользователь {user_id} добавлен в канал {COURSE_CHANNEL_ID}")
            except Exception as e:
                logger.error(f"Ошибка при добавлении пользователя {user_id} в канал: {e}")
        
        # Отправляем пользователю приветствие и ссылку на канал
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 Поздравляем! Вы успешно оплатили доступ к курсу.\n\n"
                f"Нажмите на ссылку, чтобы присоединиться к закрытому каналу: {CHANNEL_INVITE_LINK}\n\n"
                "Если у вас возникнут вопросы, не стесняйтесь обращаться!"
            )
        )
        
        # Уведомляем администратора о новом участнике
        try:
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"🆕 Пользователь {user_id} получил доступ к курсу."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления администратору: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка при выдаче доступа пользователю {user_id}: {e}")
        # Если произошла ошибка, пробуем отправить сообщение с ссылкой
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 Поздравляем! Вы успешно оплатили доступ к курсу.\n\n"
                    f"Нажмите на ссылку, чтобы присоединиться к закрытому каналу: {CHANNEL_INVITE_LINK}\n\n"
                    "Если у вас возникнут вопросы, не стесняйтесь обращаться к администратору."
                )
            )
        except Exception:
            logger.error(f"Критическая ошибка: невозможно отправить сообщение пользователю {user_id}")

# ───────────────────[ HANDLERS ]─────────────────────────
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text.lower() == "старт")
async def cmd_start(message: types.Message, state: FSMContext):
    logger.debug(f"Команда start от {message.from_user.id}")
    text = (
        f"👋 Добро пожаловать в бот курса '{COURSE_TITLE}'!\n\n"
        "🎬 Получи бесплатный ознакомительный урок — просто нажми соответствующую кнопку.\n\n"
        f"💳 Чтобы получить доступ ко всем материалам и закрытому Telegram-сообществу, оплати участие ({COURSE_PRICE_EUR}€) — и сразу получишь ссылку для входа.\n\n"
        "❓ В любое время можешь задать вопрос по YouTube — тебе поможет AI-ассистент!\n\n"
        "Удачи и больших доходов на YouTube!"
    )
    await message.answer(text, reply_markup=main_menu)
    await state.finish()

# ─────────[ Безкоштовний урок ]──────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "🎬 получить бесплатный урок")
async def send_free_lesson(message: types.Message):
    logger.debug(f"Запрос бесплатного урока от {message.from_user.id}")
    await message.answer(
        f"🎬 Вот твой бесплатный ознакомительный урок!\n\nСмотри на YouTube: {YOUTUBE_CHANNEL_URL}",
        reply_markup=main_menu
    )

# ─────────[ Меню покупки ]───────────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "💳 оплатить 149€")
async def payment_start_agreement(message: types.Message, state: FSMContext):
    """Начинаем процесс принятия правовых документов - с подробным логированием"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил процесс оплаты")
    
    try:
        # Замер времени для отладки
        start_time = time.time()
        
        # Получаем первый документ
        logger.debug(f"Получаем документ AGB для пользователя {user_id}")
        agb_text = await get_document("agb")
        logger.debug(f"Документ AGB получен за {time.time() - start_time:.4f} сек")
        
        # Если текст слишком длинный, обрезаем его
        if len(agb_text) > 3900:
            logger.debug(f"Обрезаем документ AGB (длина: {len(agb_text)})")
            agb_text = agb_text[:3900] + "...\n(Документ обрезан из-за ограничений Telegram)"
        
        # Создаем клавиатуру
        logger.debug(f"Создаем клавиатуру для AGB")
        keyboard = get_agreement_keyboard("agb")
        
        # Отправляем сообщение
        logger.debug(f"Отправляем документ AGB пользователю {user_id}")
        message_start_time = time.time()
        await message.answer(
            "📝 Документ 1/3: ALLGEMEINE GESCHÄFTSBEDINGUNGEN (AGB)\n\n" + agb_text,
            reply_markup=keyboard
        )
        logger.debug(f"Сообщение с AGB отправлено за {time.time() - message_start_time:.4f} сек")
        
        # Устанавливаем состояние
        logger.debug(f"Устанавливаем состояние waiting_for_agb для пользователя {user_id}")
        state_start_time = time.time()
        await AgreementStates.waiting_for_agb.set()
        logger.debug(f"Состояние установлено за {time.time() - state_start_time:.4f} сек")
        
        # Общее время выполнения
        logger.info(f"Весь процесс запуска оплаты занял {time.time() - start_time:.4f} сек")
        
    except Exception as e:
        logger.error(f"Ошибка при начале процесса оплаты: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при загрузке документов.\nПопробуйте еще раз позже.",
            reply_markup=main_menu
        )

# ─────────[ Обработчики согласия с документами ]─────────────────
# Обработчик согласия с AGB (первый документ)
@dp.callback_query_handler(lambda c: c.data == "agree_agb", state=AgreementStates.waiting_for_agb)
async def process_agb_agreement(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик согласия с AGB - с подробным логированием"""
    user_id = callback_query.from_user.id
    logger.info(f"👍 Пользователь {user_id} нажал СОГЛАСЕН с AGB")
    start_time = time.time()
    
    try:
        # ВАЖНО: Сначала отвечаем на callback, чтобы убрать индикатор загрузки!
        logger.debug("Отвечаем на callback query для скрытия индикатора загрузки")
        await callback_query.answer(text="✅ Принято", show_alert=False)
        logger.debug(f"Ответ на callback выполнен за {time.time() - start_time:.4f} сек")
        
        # Получаем второй документ
        doc_start_time = time.time()
        logger.debug(f"Получаем документ Widerruf для пользователя {user_id}")
        widerruf_text = await get_document("widerruf")
        logger.debug(f"Документ Widerruf получен за {time.time() - doc_start_time:.4f} сек")
        
        # Обрезаем при необходимости
        if len(widerruf_text) > 3900:
            widerruf_text = widerruf_text[:3900] + "...\n(Документ обрезан)"
        
        # Готовим клавиатуру
        keyboard_time = time.time()
        keyboard = get_agreement_keyboard("widerruf")
        logger.debug(f"Клавиатура для Widerruf создана за {time.time() - keyboard_time:.4f} сек")
        
        # Отправляем новое сообщение вместо редактирования текущего для надёжности
        send_start_time = time.time()
        logger.debug(f"Отправляем Widerruf пользователю {user_id}")
        await callback_query.message.answer(
            "📝 Документ 2/3: VERZICHTSERKLÄRUNG AUF WIDERRUFSRECHT\n\n" + widerruf_text,
            reply_markup=keyboard
        )
        logger.debug(f"Сообщение с Widerruf отправлено за {time.time() - send_start_time:.4f} сек")
        
        # Меняем состояние
        state_time = time.time()
        await AgreementStates.waiting_for_widerruf.set()
        logger.debug(f"Состояние изменено на waiting_for_widerruf за {time.time() - state_time:.4f} сек")
        
        # Общее время выполнения
        total_time = time.time() - start_time
        logger.info(f"Обработка согласия с AGB завершена за {total_time:.4f} сек")
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА при обработке согласия с AGB: {e}", exc_info=True)
        error_time = time.time()
        
        # Пытаемся сообщить пользователю об ошибке
        try:
            await callback_query.message.answer(
                "❌ Произошла ошибка при обработке запроса.\n"
                "Пожалуйста, начните процесс заново с команды /start",
                reply_markup=main_menu
            )
        except Exception as msg_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {msg_error}")
        
        # Сбрасываем состояние
        await state.finish()
        logger.debug(f"Обработка ошибки заняла {time.time() - error_time:.4f} сек")

# Обработчик согласия с Widerruf (второй документ)
@dp.callback_query_handler(lambda c: c.data == "agree_widerruf", state=AgreementStates.waiting_for_widerruf)
async def process_widerruf_agreement(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик согласия с Widerruf - с подробным логированием"""
    user_id = callback_query.from_user.id
    logger.info(f"👍 Пользователь {user_id} нажал СОГЛАСЕН с Widerruf")
    start_time = time.time()
    
    try:
        # ВАЖНО: Сначала отвечаем на callback, чтобы убрать индикатор загрузки!
        logger.debug("Отвечаем на callback query для скрытия индикатора загрузки")
        await callback_query.answer(text="✅ Принято", show_alert=False)
        logger.debug(f"Ответ на callback выполнен за {time.time() - start_time:.4f} сек")
        
        # Получаем третий документ
        doc_start_time = time.time()
        logger.debug(f"Получаем документ Datenschutz для пользователя {user_id}")
        datenschutz_text = await get_document("datenschutz")
        logger.debug(f"Документ Datenschutz получен за {time.time() - doc_start_time:.4f} сек")
        
        # Обрезаем при необходимости
        if len(datenschutz_text) > 3900:
            datenschutz_text = datenschutz_text[:3900] + "...\n(Документ обрезан)"
        
        # Готовим клавиатуру
        keyboard_time = time.time()
        keyboard = get_agreement_keyboard("datenschutz")
        logger.debug(f"Клавиатура для Datenschutz создана за {time.time() - keyboard_time:.4f} сек")
        
        # Отправляем новое сообщение вместо редактирования текущего для надёжности
        send_start_time = time.time()
        logger.debug(f"Отправляем Datenschutz пользователю {user_id}")
        await callback_query.message.answer(
            "📝 Документ 3/3: DATENSCHUTZERKLÄRUNG\n\n" + datenschutz_text,
            reply_markup=keyboard
        )
        logger.debug(f"Сообщение с Datenschutz отправлено за {time.time() - send_start_time:.4f} сек")
        
        # Меняем состояние
        state_time = time.time()
        await AgreementStates.waiting_for_datenschutz.set()
        logger.debug(f"Состояние изменено на waiting_for_datenschutz за {time.time() - state_time:.4f} сек")
        
        # Общее время выполнения
        total_time = time.time() - start_time
        logger.info(f"Обработка согласия с Widerruf завершена за {total_time:.4f} сек")
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА при обработке согласия с Widerruf: {e}", exc_info=True)
        error_time = time.time()
        
        # Пытаемся сообщить пользователю об ошибке
        try:
            await callback_query.message.answer(
                "❌ Произошла ошибка при обработке запроса.\n"
                "Пожалуйста, начните процесс заново с команды /start",
                reply_markup=main_menu
            )
        except Exception as msg_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {msg_error}")
        
        # Сбрасываем состояние
        await state.finish()
        logger.debug(f"Обработка ошибки заняла {time.time() - error_time:.4f} сек")

# Обработчик согласия с Datenschutz (третий документ)
@dp.callback_query_handler(lambda c: c.data == "agree_datenschutz", state=AgreementStates.waiting_for_datenschutz)
async def process_datenschutz_agreement(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик согласия с Datenschutz - с подробным логированием"""
    user_id = callback_query.from_user.id
    logger.info(f"👍 Пользователь {user_id} нажал СОГЛАСЕН с Datenschutz")
    start_time = time.time()
    
    try:
        # ВАЖНО: Сначала отвечаем на callback, чтобы убрать индикатор загрузки!
        logger.debug("Отвечаем на callback query для скрытия индикатора загрузки")
        await callback_query.answer(text="✅ Принято", show_alert=False)
        logger.debug(f"Ответ на callback выполнен за {time.time() - start_time:.4f} сек")
        
        # Завершаем FSM-состояние
        state_time = time.time()
        logger.debug(f"Завершаем состояние для пользователя {user_id}")
        await state.finish()
        logger.debug(f"Состояние завершено за {time.time() - state_time:.4f} сек")
        
        # Отправляем сообщение и кнопку оплаты
        send_start_time = time.time()
        logger.debug(f"Отправляем кнопку оплаты пользователю {user_id}")
        
        # Создаем inline клавиатуру для оплаты
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("💳 Оплатить курс (149€)", url=STRIPE_PAYMENT_URL))
        
        await callback_query.message.answer(
            f"💳 Оплата курса '{COURSE_TITLE}' — {COURSE_PRICE_EUR}€\n\n"
            "✅ После оплаты используйте /check_payment для проверки", 
            reply_markup=keyboard
        )
        logger.debug(f"Кнопка оплаты отправлена за {time.time() - send_start_time:.4f} сек")
        
        # Общее время выполнения
        total_time = time.time() - start_time
        logger.info(f"Обработка согласия с Datenschutz завершена за {total_time:.4f} сек")
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА при обработке согласия с Datenschutz: {e}", exc_info=True)
        error_time = time.time()
        
        # Пытаемся сообщить пользователю об ошибке
        try:
            await callback_query.message.answer(
                "❌ Произошла ошибка при обработке запроса.\n"
                "Пожалуйста, начните процесс заново с команды /start",
                reply_markup=main_menu
            )
        except Exception as msg_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {msg_error}")
        
        # Сбрасываем состояние
        await state.finish()
        logger.debug(f"Обработка ошибки заняла {time.time() - error_time:.4f} сек")

# Обработчик отмены на любом этапе согласия
@dp.callback_query_handler(lambda c: c.data == "cancel_agreement", state=[
    AgreementStates.waiting_for_agb,
    AgreementStates.waiting_for_widerruf,
    AgreementStates.waiting_for_datenschutz
])
async def cancel_agreement(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик отмены согласия - с подробным логированием"""
    user_id = callback_query.from_user.id
    start_time = time.time()
    
    try:
        current_state = await state.get_state()
        logger.info(f"❌ Пользователь {user_id} отменил согласие на этапе {current_state}")
        
        # ВАЖНО: Сначала отвечаем на callback, чтобы убрать индикатор загрузки!
        logger.debug("Отвечаем на callback query для скрытия индикатора загрузки")
        await callback_query.answer(text="❌ Отменено", show_alert=False)
        logger.debug(f"Ответ на callback выполнен за {time.time() - start_time:.4f} сек")
        
        # Сбрасываем состояние FSM
        state_time = time.time()
        await state.finish()
        logger.debug(f"Состояние сброшено за {time.time() - state_time:.4f} сек")
        
        # Отправляем пользователя в главное меню
        send_time = time.time()
        await callback_query.message.answer(
            "❌ Вы отменили процесс оплаты.",
            reply_markup=main_menu
        )
        logger.debug(f"Сообщение об отмене отправлено за {time.time() - send_time:.4f} сек")
        
        # Общее время выполнения
        total_time = time.time() - start_time
        logger.info(f"Обработка отмены завершена за {total_time:.4f} сек")
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА при обработке отмены: {e}", exc_info=True)
        # Пытаемся завершить состояние в любом случае
        await state.finish()
        
        # Пытаемся отправить сообщение об ошибке
        try:
            await callback_query.message.answer(
                "❌ Произошла ошибка. Начните заново с команды /start",
                reply_markup=main_menu
            )
        except Exception as msg_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {msg_error}")

# ─────────[ FSM: питання ]────────────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "❓ задать вопрос")
async def ask_question(message: types.Message, state: FSMContext):
    logger.debug(f"Пользователь {message.from_user.id} запросил задать вопрос")
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
    logger.debug(f"Получен вопрос от пользователя {message.from_user.id}")
    if message.text.lower() == "🔙 отмена":
        await state.finish()
        await message.answer("❌ Отменено.", reply_markup=main_menu)
        return
    await message.answer("🤔 Думаю...")
    reply = await ask_assistant(message.text)
    await message.answer(f"💡 {reply}", reply_markup=main_menu)
    await state.finish()
    
# ─────────[ Проверка оплаты ]───────────────────────────
# Команда для проверки статуса оплаты (для администратора)
@dp.message_handler(lambda m: m.text.lower() == "проверить оплаты" and m.from_user.id == ADMIN_USER_ID)
async def check_all_payments_status(message: types.Message):
    logger.debug(f"Администратор {message.from_user.id} запросил проверку платежей")
    # Эту функцию можно использовать для проверки платежей в ручном режиме
    await message.answer("Для просмотра всех платежей перейдите в панель Stripe: https://dashboard.stripe.com/payments")

# Команда для пользователя - проверить свою оплату
@dp.message_handler(commands=["check_payment"])
@dp.message_handler(lambda m: m.text.lower() in ["проверить оплату", "проверить мою оплату", "✅ проверить оплату", "/check_payment"])
async def check_user_payment_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.debug(f"Пользователь {user_id} запросил проверку оплаты")
    
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
    user_id = message.from_user.id
    logger.debug(f"Получен email от пользователя {user_id}: {message.text}")
    
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
    user_id = message.from_user.id
    logger.debug(f"Получено имя от пользователя {user_id}: {message.text}")
    
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
    logger.info(f"Проверяем платеж для {email} и {name}")
    email_payment_found = await check_stripe_payment_by_email(email)
    
    # Проверяем оплату по имени, если по email не нашли
    name_payment_found = False
    if not email_payment_found:
        name_payment_found = await check_stripe_payment_by_name(name)
    
    # Если платеж найден - отправляем доступ
    if email_payment_found or name_payment_found:
        logger.info(f"Платеж найден для пользователя {user_id}")
        await send_course_access(message.from_user.id)
        await message.answer(
            "✅ Мы нашли ваш платеж! Доступ к курсу предоставлен.",
            reply_markup=main_menu
        )
    else:
        logger.info(f"Платеж НЕ найден для пользователя {user_id}")
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
    user_id = message.from_user.id
    logger.info(f"Получено сообщение об оплате от пользователя {user_id}: {message.text}")
    
    # Отправляем администратору уведомление о платеже
    admin_id = ADMIN_USER_ID
    
    try:
        await bot.send_message(
            chat_id=admin_id,
            text=f"💰 Пользователь сообщает об оплате!\n\n"
                 f"👤 Пользователь: {message.from_user.full_name} (@{message.from_user.username})\n"
                 f"🆔 ID: {message.from_user.id}\n\n"
                 f"📩 Сообщение: {message.text}"
        )
        
        # Уведомляем пользователя
        await message.answer(
            "✅ Спасибо за информацию! Мы проверим ваш платеж и выдадим доступ.\n\n"
            "Обычно это занимает не более 24 часов. Как только доступ будет предоставлен, "
            "вы получите уведомление в этом боте.",
            reply_markup=main_menu
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке уведомления об оплате: {e}")

# ─────────[ Админ-команды ]────────────────────────────────
# Команда для выдачи доступа пользователю (для администратора)
@dp.message_handler(commands=["grant"])
@dp.message_handler(lambda m: m.text.lower().startswith("выдать доступ") and m.from_user.id == ADMIN_USER_ID)
async def grant_access(message: types.Message):
    logger.info(f"Администратор запросил выдачу доступа: {message.text}")
    # Парсим ID пользователя из сообщения
    try:
        if message.text.lower().startswith("выдать доступ"):
            parts = message.text.split(" ")
            if len(parts) < 3:
                await message.answer("❌ Укажите ID пользователя: 'выдать доступ 123456789'")
                return
            user_id = int(parts[2])
        else:  # Команда /grant
            parts = message.text.split(" ")
            if len(parts) < 2:
                await message.answer("❌ Укажите ID пользователя: /grant 123456789")
                return
            user_id = int(parts[1])
            
        # Выдаем доступ
        logger.info(f"Администратор выдаёт доступ пользователю {user_id}")
        await send_course_access(user_id)
        await message.answer(f"✅ Доступ выдан пользователю {user_id}")
        
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя. Используйте только цифры.")
    except Exception as e:
        logger.error(f"Ошибка при выдаче доступа: {e}")
        await message.answer(f"❌ Ошибка: {e}")

async def on_startup(dp):
    logger.info("Бот запущен!")

async def on_shutdown(dp):
    logger.info("Бот остановлен!")

if __name__ == "__main__":
    from aiogram import executor
    # Явно указываем allowed_updates, чтобы получать callback_query от inline-кнопок
    executor.start_polling(
        dp, 
        on_startup=on_startup, 
        on_shutdown=on_shutdown, 
        skip_updates=True,
        allowed_updates=["message", "callback_query", "pre_checkout_query", "chat_join_request"]
    )
