from pathlib import Path
import sys
import os
import logging
import time
import openai

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from dotenv import load_dotenv
import stripe

# Импорт системы напоминаний
# Попытка импорта ReminderSystem с разных путей
ReminderSystem = None

def create_placeholder_reminder_system():
    """Creates a placeholder class for ReminderSystem when import fails"""
    class PlaceholderReminderSystem:
        def __init__(self, bot, db_path=None, reminder_intervals=None,
                    openai_client=None, openai_assistant_id=None):
            print("Using placeholder ReminderSystem - reminders will not work!")
            self.bot = bot
            self.is_running = False

        async def start(self):
            print("Placeholder ReminderSystem.start() called")
            self.is_running = True

        async def stop(self):
            print("Placeholder ReminderSystem.stop() called")
            self.is_running = False

        async def track_free_lesson_view(self, user_id):
            print(f"Placeholder track_free_lesson_view called for user {user_id}")

        async def track_lesson_view(self, user_id, username=None, first_name=None, last_name=None):
            print(f"Placeholder track_lesson_view called for user {user_id}")
            
        async def mark_user_purchased(self, user_id):
            print(f"Placeholder mark_user_purchased called for user {user_id}")
            
        def get_stats(self):
            return {"error": "ReminderSystem not available"}
    
    print("Created placeholder ReminderSystem class to prevent crashes")
    return PlaceholderReminderSystem()  # Instantiate the class when returning

# Импорт с обработкой ошибок - полностью переписан для Docker-совместимости
# Простая и надежная схема импорта без вложенных блоков
import_successful = False

# Первая попытка импорта
try:
    from app.reminder_system import ReminderSystem
    print("ReminderSystem импортирован из app")
    import_successful = True
except ImportError:
    print("Не удалось импортировать из app.reminder_system")

# Вторая попытка импорта, если первая не удалась
if not import_successful:
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from reminder_system import ReminderSystem
        print("ReminderSystem импортирован после добавления пути")
        import_successful = True
    except ImportError as e:
        print(f"Не удалось импортировать из reminder_system: {e}")
    except Exception as e:
        print(f"Ошибка при импорте из reminder_system: {e}")
        pass

# Используем заглушку, если обе попытки не удались
if not import_successful:
    print("Используем заглушку ReminderSystem")
    ReminderSystem = create_placeholder_reminder_system()
# [НАСТРОЙКА РАСШИРЕННОГО ЛОГИРОВАНИЯ]
# Определяем путь для логов, совместимый с Docker и локальным запуском
if os.path.exists("/app"):
    # Запуск в Docker
    log_path = "/app/bot_debug.log"
else:
    # Локальный запуск
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_debug.log")

# Создаем директорию для логов, если ее нет
os.makedirs(os.path.dirname(log_path), exist_ok=True)

# Настраиваем расширенное логирование
logging.basicConfig(
    level=logging.DEBUG,  # Используем DEBUG уровень для максимальной детализации
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("=== ЗАПУСК БОТА С РАСШИРЕННЫМ ЛОГИРОВАНИЕМ ===")

# [CONFIG]
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

# [OpenAI]
openai_client_ready = False
if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_api_key_here':
    openai.api_key = OPENAI_API_KEY
    openai_client_ready = True
    logger.info("OpenAI API ініціалізовано")
else:
    logger.warning("OpenAI API-ключ не задано — функції Assistant вимкнені")

# [Stripe]
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

# [Aiogram]
bot     = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(bot, storage=storage)

# [Reminder System]
# Определяем путь для базы данных напоминаний, совместимый с Docker и локальным запуском
if os.path.exists("/app"):
    # Запуск в Docker
    reminder_db_path = "/app/reminder_data.db"
else:
    # Локальный запуск
    reminder_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminder_data.db")

# Инициализируем систему напоминаний
reminder_system = None
if openai_client_ready:
    reminder_system = ReminderSystem(
        bot=bot, 
        db_path=reminder_db_path,
        openai_client=openai,
        openai_assistant_id=OPENAI_ASSISTANT_ID
    )
    logger.info(f"Система напоминаний инициализирована с поддержкой OpenAI (БД: {reminder_db_path})")
else:
    reminder_system = ReminderSystem(
        bot=bot,
        db_path=reminder_db_path
    )
    logger.info(f"Система напоминаний инициализирована без поддержки OpenAI (БД: {reminder_db_path})")

# [FSM]
class QuestionStates(StatesGroup):
    waiting_for_question = State()
    
class PaymentCheckStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_name = State()

class AgreementStates(StatesGroup):
    waiting_for_agb = State()
    waiting_for_widerruf = State()
    waiting_for_datenschutz = State()

# [ DATA ]
# Данные курса - упрощенная версия, только один курс за 149€
COURSE_TITLE = "Успешный YouTube-бизнес с нуля"
COURSE_DESCRIPTION = "Полный доступ к курсу и закрытому сообществу"
COURSE_PRICE_EUR = 149

# [ KEYBOARDS ]
main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🎬 Получить бесплатный урок")],
        [KeyboardButton("💳 Оплатить 149€")],
        [KeyboardButton("✅ Проверить оплату")],
        [KeyboardButton("❓ Задать вопрос")],
        [KeyboardButton("📋 Datenschutz"), KeyboardButton("📄 AGB"), KeyboardButton("📝 Impressum")]
    ],
    resize_keyboard=True
)

# [Legal Documents Helpers]
# Жестко закодированные тексты документов
LEGAL_DOCS = {
    "agb": """� AGB

1. Geltungsbereich
Diese Allgemeinen Geschäftsbedingungen (AGB) gelten für alle Verträge zwischen Firma Alexander Cherkasky Schlitzer Strasse 6, 60386 Frankfurt am Main (nachfolgend „Anbieter") und dem Kunden über den Erwerb und die Nutzung digitaler Inhalte, insbesondere Online-Kurse über die Plattform YouTube oder andere digitale Plattformen.

2. Vertragsgegenstand
Vertragsgegenstand ist der Zugang zu einem Online-Kurs, der aus vorab aufgezeichneten Videolektionen besteht. Der Zugang erfolgt digital und ausschließlich zur persönlichen Nutzung des Kunden.

3. Vertragsabschluss
Der Vertrag kommt zustande, sobald der Kunde den Bestellvorgang abgeschlossen und der Anbieter die Bestellung bestätigt hat.

4. Preise und Zahlung
Alle angegebenen Preise verstehen sich als Endpreise in Euro. Die Zahlung erfolgt über die im Bestellprozess angebotenen Zahlungsmethoden. Der Zugang zum Kurs wird nach erfolgreichem Zahlungseingang freigeschaltet.

5. Nutzungsrechte
Mit der Buchung erhält der Kunde ein einfaches, nicht übertragbares Nutzungsrecht zur privaten Nutzung der Inhalte. Eine Weitergabe, Vervielfältigung oder öffentliche Wiedergabe ist untersagt.

6. Haftungsausschluss
Die Inhalte wurden mit größter Sorgfalt erstellt. Für die Richtigkeit, Vollständigkeit und Aktualität wird jedoch keine Haftung übernommen. Die Nutzung der Inhalte erfolgt auf eigene Verantwortung.

7. Widerruf und Verzicht
Da es sich um digitale Inhalte handelt, die sofort nach Kauf bereitgestellt werden, besteht kein Widerrufsrecht, wenn der Kunde ausdrücklich zustimmt und bestätigt, dass er mit der Ausführung des Vertrags vor Ablauf der Widerrufsfrist beginnt.
""",

    "widerruf": """⚠️ Widerrufsverzicht

Widerrufsverzicht – Zustimmung zur vorzeitigen Vertragserfüllung
Verzicht auf Widerrufsrecht gemäß § 356 Abs. 5 BGB
Ich stimme ausdrücklich zu, dass Alexander Cherkasky Schlitzer Strasse 6, 60386 Frankfurt am Main vor Ablauf der Widerrufsfrist mit der Ausführung des Vertrages beginnt. Ich nehme zur Kenntnis, dass ich mit Beginn der Ausführung des Vertrates mein Widerrufsrecht verliere.
Ich stimme dem Verzicht auf das Widerrufsrecht ausdrücklich zu.

Отказ от права на отзыв – Согласие на досрочное выполнение договора
Отказ от права на отзыв в соответствии с § 356, абз. 5 Гражданского кодекса Германии (BGB)
Я даю явное согласие на то, что Alexander Cherkasky Schlitzer Strasse 6, 60386 Frankfurt am Main начнёт выполнение договора до истечения срока отзыва. Я принимаю к сведению, что с началом исполнения договора я теряю своё право на отзыв.
Я явно соглашаюсь на отказ от права на отзыв.
""",

    "datenschutz": """📋 Datenschutzerklärung

1. Verantwortlicher
Verantwortlich für die Datenverarbeitung ist:
Firma Alexander Cherkasky 
Schlitzer Strasse 6, 60386 Frankfurt am Main
[+4917624160386 / E-Mail-Adresse a.cherkasky@rusverlag.de]

2. Erhebung und Speicherung personenbezogener Daten
Wir erheben personenbezogene Daten (z. B. Name, E-Mail-Adresse, Zahlungsdaten), die zur Vertragsabwicklung und Kundenbetreuung erforderlich sind.

3. Zweck der Datenverarbeitung
Die Daten werden ausschließlich zur Vertragserfüllung, Kundenkommunikation, Zahlungsabwicklung und Bereitstellung der Online-Kurse verarbeitet.

4. Weitergabe an Dritte
Eine Weitergabe an Dritte erfolgt nur, soweit dies zur Vertragserfüllung notwendig ist (z. B. Zahlungsdienstleister).

5. Speicherdauer
Personenbezogene Daten werden nur so lange gespeichert, wie es für die genannten Zwecke erforderlich ist oder gesetzliche Aufbewahrungsfristen bestehen.

6. Ihre Rechte
Sie haben jederzeit das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung sowie Widerspruch und Datenübertragbarkeit. Bitte wenden Sie sich dazu an [Kontaktadresse].

7. Sicherheit
Wir setzen technische und organisatorische Sicherheitsmaßnahmen ein, um Ihre Daten vor Verlust oder unbefugtem Zugriff zu schützen.

8. Kontakt Datenschutzbeauftragter
Bei Fragen zum Datenschutz wenden Sie sich bitte an:
Firma Alexander Cherkasky a.cherkasky@rusverlag.de
""",

    "impressum": """📋 IMPRESSUM

Alexander Cherkasky Media
Schlitzer Straße 6
60386 Frankfurt
Deutschland

Steuernummer:
DE454894230

Bankverbindung:
Frankfurter Volksbank
IBAN: DE30 5019 0000 6000 4445 19

Kontakt:
Tel: +4917624160386
E-Mail: a.cherkasky@rusverlag.de

Verantwortlich für den Inhalt:
Alexander Cherkasky

Plattform der EU-Kommission zur Online-Streitbeilegung: https://ec.europa.eu/consumers/odr

Wir sind zur Teilnahme an einem Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle weder verpflichtet noch bereit.
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

# [OpenAI helper]
# Для работы с OpenAI Assistant API требуется openai>=1.3.0
async def ask_assistant(question: str) -> str:
    if not openai_client_ready:
        return "❌ OpenAI Assistant недоступен."
    try:
        logger.info(f"Отправка вопроса в OpenAI: {question[:50]}...")
        
        # Используем Chat Completions API с правильным разделением ролей
        # Правильно разделяем роли: system для инструкций, user для вопроса
        messages = [
            {"role": "system", "content": "Вы — помощник, который отвечает на вопросы о курсе 'Успешный YouTube-бизнес с нуля'. Отвечайте кратко и точно."},
            {"role": "user", "content": question}
        ]
        
        # Отправляем запрос используя новый формат API для версии >= 1.3.0
        import time
        start_time = time.time()
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # Используем модель gpt-3.5-turbo
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        # Получаем ответ (новый формат API)
        answer = response.choices[0].message.content
        logger.info(f"Получен ответ от OpenAI за {time.time() - start_time:.2f} сек.")
        return answer
        
    except Exception as e:
        logger.error(f"OpenAI Assistant error: {e}")
        return "❌ Ошибка OpenAI Assistant, попробуйте позже."
    except Exception as e:
        logger.error(f"OpenAI Assistant error: {e}")
        return "❌ Ошибка OpenAI Assistant, попробуйте позже."

# [Stripe helper]
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
        
        # Обновляем статус в системе напоминаний
        if reminder_system:
            await reminder_system.mark_user_purchased(user_id)
            logger.info(f"Пользователь {user_id} отмечен как оплативший в системе напоминаний")
        
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
                # Пробуем отправить ссылку на канал вместо прямого добавления
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Для доступа к курсу, перейдите по этой ссылке: {CHANNEL_INVITE_LINK}"
                    )
                    logger.info(f"Отправлена ссылка на канал пользователю {user_id}")
                except Exception as inner_e:
                    logger.error(f"Не удалось отправить ссылку на канал: {inner_e}")
        
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
        except Exception as e2:
            logger.error(f"Не удалось отправить ссылку пользователю {user_id}: {e2}")
            logger.error(f"Критическая ошибка: невозможно отправить сообщение пользователю {user_id}")

# [HANDLERS]
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text.lower() == "старт")
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user
    user_id = user.id
    username = user.username or "Нет username"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Имя не указано"
    
    logger.debug(f"Команда start от {user_id}")
    text = (
        f"👋 Добро пожаловать в бот курса '{COURSE_TITLE}'!\n\n"
        "🎬 Получи бесплатный ознакомительный урок — просто нажми соответствующую кнопку.\n\n"
        f"💳 Чтобы получить доступ ко всем материалам и закрытому Telegram-сообществу, оплати участие ({COURSE_PRICE_EUR}€) — и сразу получишь ссылку для входа.\n\n"
        "❓ В любое время можешь задать вопрос по YouTube — тебе поможет AI-ассистент!\n\n"
        "Удачи и больших доходов на YouTube!"
    )
    await message.answer(text, reply_markup=main_menu)
    await state.finish()
    
    # Уведомляем администратора о новом пользователе
    try:
        admin_notification = (
            f"🆕 Новый пользователь в боте!\n\n"
            f"👤 ID: {user_id}\n"
            f"👤 Username: @{username}\n"
            f"👤 Имя: {full_name}"
        )
        await bot.send_message(chat_id=ADMIN_USER_ID, text=admin_notification)
        logger.info(f"Администратор уведомлен о новом пользователе {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления администратору: {e}")

# ─────────[ Безкоштовний урок ]──────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "🎬 получить бесплатный урок")
async def send_free_lesson(message: types.Message):
    user = message.from_user
    user_id = user.id
    username = user.username or "Нет username"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Имя не указано"
    
    logger.debug(f"Запрос бесплатного урока от {user_id}")
    
    # Отправляем урок
    await message.answer(
        f"🎬 Вот твой бесплатный ознакомительный урок!\n\nСмотри на YouTube: {YOUTUBE_CHANNEL_URL}",
        reply_markup=main_menu
    )
    
    # Записываем просмотр для системы напоминаний
    if reminder_system:
        await reminder_system.track_lesson_view(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        logger.debug(f"Просмотр урока записан в систему напоминаний для пользователя {user_id}")
    
    # Уведомляем администратора о просмотре бесплатного урока
    try:
        admin_notification = (
            f"👁️ Просмотр бесплатного урока!\n\n"
            f"👤 ID: {user_id}\n"
            f"👤 Username: @{username}\n"
            f"👤 Имя: {full_name}"
        )
        await bot.send_message(chat_id=ADMIN_USER_ID, text=admin_notification)
        logger.info(f"Администратор уведомлен о просмотре бесплатного урока пользователем {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления администратору: {e}")

# ─────────[ Меню покупки ]───────────────────────────────
@dp.message_handler(lambda m: m.text.lower() == "💳 оплатить 149€")
async def payment_start_agreement(message: types.Message, state: FSMContext):
    """Показываем отказ от возврата платежа (Widerruf) перед оплатой"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил процесс оплаты")
    
    try:
        # Замер времени для отладки
        start_time = time.time()
        
        # Получаем документ отказа от возврата платежа
        logger.debug(f"Получаем документ Widerruf для пользователя {user_id}")
        widerruf_text = await get_document("widerruf")
        logger.debug(f"Документ Widerruf получен за {time.time() - start_time:.4f} сек")
        
        # Если текст слишком длинный, обрезаем его
        if len(widerruf_text) > 3900:
            logger.debug(f"Обрезаем документ Widerruf (длина: {len(widerruf_text)})")
            widerruf_text = widerruf_text[:3900] + "...\n(Документ обрезан из-за ограничений Telegram)"
        
        # Создаем клавиатуру
        logger.debug(f"Создаем клавиатуру для Widerruf")
        keyboard = get_agreement_keyboard("widerruf")
        
        # Отправляем сообщение
        logger.debug(f"Отправляем документ Widerruf пользователю {user_id}")
        message_start_time = time.time()
        await message.answer(
            "📝 ОТКАЗ ОТ ПРАВА НА ВОЗВРАТ СРЕДСТВ\n\nДля продолжения оплаты, пожалуйста, ознакомьтесь и примите этот документ:\n\n" + widerruf_text,
            reply_markup=keyboard
        )
        logger.debug(f"Сообщение с Widerruf отправлено за {time.time() - message_start_time:.4f} сек")
        
        # Устанавливаем состояние
        logger.debug(f"Устанавливаем состояние waiting_for_widerruf для пользователя {user_id}")
        state_start_time = time.time()
        await AgreementStates.waiting_for_widerruf.set()
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
    """Обработчик согласия с Widerruf - показывает кнопку оплаты сразу после согласия"""
    user_id = callback_query.from_user.id
    logger.info(f"👍 Пользователь {user_id} нажал СОГЛАСЕН с Widerruf")
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
            f"� Оплата курса '{COURSE_TITLE}' — {COURSE_PRICE_EUR}€\n\n"
            "✅ После оплаты используйте /check_payment для проверки", 
            reply_markup=keyboard
        )
        logger.debug(f"Кнопка оплаты отправлена за {time.time() - send_start_time:.4f} сек")
        
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
# Обработчик для Datenschutz удален - теперь доступен через постоянную кнопку в меню

# Обработчик отмены на этапе согласия с Widerruf
@dp.callback_query_handler(lambda c: c.data == "cancel_agreement", state=AgreementStates.waiting_for_widerruf)
async def cancel_agreement(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик отмены согласия с отказом от права возврата средств"""
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

# Команда для проверки статистики напоминаний (для администратора)
@dp.message_handler(commands=["reminders"])
@dp.message_handler(lambda m: m.text.lower().startswith("статистика напоминаний") and m.from_user.id == ADMIN_USER_ID)
async def check_reminder_stats(message: types.Message):
    logger.info(f"Администратор запросил статистику напоминаний")
    
    if not reminder_system:
        await message.answer("❌ Система напоминаний не инициализирована.")
        return
    
    try:
        # Получаем статистику из модуля напоминаний
        from reminder_system import get_reminder_stats
        stats = await get_reminder_stats(reminder_system.db_path)
        
        # Формируем сообщение
        stats_message = (
            "📊 Статистика системы напоминаний:\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"📨 Отправлено напоминаний: {stats['reminders_sent']}\n"
            f"👤 Пользователей с напоминаниями: {stats['users_with_reminders']}\n"
            f"💰 Конверсия в покупки: {stats['conversion_rate']:.2f}%"
        )
        
        await message.answer(stats_message)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики напоминаний: {e}")
        await message.answer(f"❌ Ошибка при получении статистики: {str(e)}")

@dp.message_handler(lambda m: m.text == "📋 Datenschutz")
async def show_datenschutz(message: types.Message):
    """Обработчик для показа Datenschutz (политики конфиденциальности)"""
    logger.info(f"Пользователь {message.from_user.id} запросил Datenschutz")
    
    # Получаем текст документа
    doc_text = await get_document("datenschutz")
    
    # Отправляем текст с политикой конфиденциальности
    await message.answer(doc_text, reply_markup=main_menu)

@dp.message_handler(lambda m: m.text == "📝 Impressum")
async def show_impressum(message: types.Message):
    """Обработчик для показа Impressum"""
    logger.info(f"Пользователь {message.from_user.id} запросил Impressum")
    
    # Получаем текст Impressum
    doc_text = await get_document("impressum")
    
    # Отправляем текст Impressum
    await message.answer(doc_text, reply_markup=main_menu)

@dp.message_handler(lambda m: m.text == "📄 AGB" or m.text == "AGB" or m.text.lower() == "agb")
async def show_agb(message: types.Message):
    """Обработчик для показа AGB (общие условия)"""
    logger.info(f"Пользователь {message.from_user.id} запросил AGB")
    
    # Получаем текст документа
    doc_text = await get_document("agb")
    
    # Отправляем текст с общими условиями
    await message.answer(doc_text, reply_markup=main_menu)

async def on_startup(dp):
    import os
    import socket
    
    # Дополнительное логирование для отладки
    startup_id = os.environ.get('BOT_STARTUP_ID', 'НЕИЗВЕСТНО')
    hostname = socket.gethostname()
    pid = os.getpid()
    
    logger.info(f"=== БОТ ЗАПУЩЕН [PID:{pid}] [ID:{startup_id}] [HOST:{hostname}] ===")
    
    # Записываем информацию о запуске в файл для мониторинга
    try:
        with open("/tmp/dostup_bot_running.txt", "w") as f:
            f.write(f"PID: {pid}\n")
            f.write(f"Startup ID: {startup_id}\n")
            f.write(f"Hostname: {hostname}\n")
            f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception as e:
        logger.error(f"Ошибка при записи информации о запуске: {e}")
    
    # Запускаем систему напоминаний
    if reminder_system:
        try:
            await reminder_system.start()
            logger.info("Система напоминаний запущена")
        except Exception as e:
            logger.error(f"Ошибка при запуске системы напоминаний: {e}")

async def on_shutdown(dp):
    import os
    import signal
    
    pid = os.getpid()
    logger.info(f"=== БОТ ОСТАНАВЛИВАЕТСЯ [PID:{pid}] ===")
    
    # Удаляем информационный файл
    try:
        if os.path.exists("/tmp/dostup_bot_running.txt"):
            os.remove("/tmp/dostup_bot_running.txt")
    except Exception as e:
        logger.error(f"Ошибка при удалении информационного файла: {e}")
    
    # Удаляем файлы блокировок для чистоты
    lock_files = [
        "/tmp/dostup_bot_instance.lock",
        "/tmp/dostup_bot_render_lock.lock",
        "/var/tmp/dostup_bot.lock",
        "/tmp/dostup_bot_var_lock.lock"
    ]
    
    for lock_path in lock_files:
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
                logger.info(f"Файл блокировки {lock_path} удален при остановке")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла блокировки {lock_path}: {e}")
    
    # Останавливаем систему напоминаний
    if reminder_system:
        try:
            await reminder_system.stop()
            logger.info("Система напоминаний остановлена")
        except Exception as e:
            logger.error(f"Ошибка при остановке системы напоминаний: {e}")
    
    logger.info("=== БОТ ОСТАНОВЛЕН ===")
    
    # Для гарантированной остановки, принудительно завершаем процесс после всех операций
    try:
        def force_exit():
            logger.info("Принудительное завершение процесса через 3 секунды")
            time.sleep(3)
            os.kill(pid, signal.SIGTERM)
        
        import threading
        threading.Thread(target=force_exit).start()
    except:
        pass

# Функция, которая запускается при запуске бота
async def main():
    # Запускаем систему напоминаний, если она создана
    if reminder_system and not reminder_system.is_running:
        await reminder_system.start()
        logger.info("Система напоминаний запущена")
    
    # Запускаем поллинг бота
    try:
        logger.info("Бот запущен!")
        await dp.start_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        # При завершении работы останавливаем систему напоминаний
        logger.info("Бот останавливается...")
        if reminder_system and reminder_system.is_running:
            await reminder_system.stop()
            logger.info("Система напоминаний остановлена")
        logger.info("Бот остановлен!")

# Функция для запуска бота из внешнего скрипта (для Render)
def start_polling():
    import os
    import sys
    import fcntl
    import signal
    import time
    import socket
    from aiogram import executor
    
    # Создаем множественные файлы блокировки для большей надежности
    LOCK_FILES = [
        "/tmp/dostup_bot_instance.lock",
        "/tmp/dostup_bot_render_lock.lock",
        "/var/tmp/dostup_bot.lock" if os.path.exists("/var/tmp") else "/tmp/dostup_bot_var_lock.lock"
    ]
    
    # Получаем информацию о запуске для логов
    startup_id = os.environ.get('BOT_STARTUP_ID', str(int(time.time())))
    hostname = socket.gethostname()
    pid = os.getpid()
    
    logger.info(f"=== ИНИЦИАЛИЗАЦИЯ БОТА [PID:{pid}] [ID:{startup_id}] [HOST:{hostname}] ===")
    
    # Функция для завершения всех других процессов бота
    def kill_other_bot_processes():
        logger.warning("Активное завершение других процессов бота")
        try:
            import subprocess
            # Получаем список всех процессов Python, связанных с ботом
            ps_output = subprocess.check_output(
                "ps aux | grep -E 'python.*(bot\\.py|start\\.py)' | grep -v grep", 
                shell=True
            ).decode('utf-8')
            
            # Парсим вывод и получаем PID'ы
            for line in ps_output.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) > 1:
                        other_pid = int(parts[1])
                        # Не убиваем текущий процесс
                        if other_pid != pid:
                            logger.warning(f"Завершаем другой процесс бота с PID {other_pid}")
                            try:
                                os.kill(other_pid, signal.SIGKILL)
                                logger.info(f"Процесс {other_pid} успешно завершен")
                            except Exception as e:
                                logger.error(f"Ошибка при завершении процесса {other_pid}: {e}")
        except Exception as e:
            logger.error(f"Ошибка при поиске других процессов: {e}")
    
    # Проверяем и устраняем другие экземпляры бота
    kill_other_bot_processes()
    
    # Обрабатываем файловые блокировки
    locks = []
    try:
        for lock_path in LOCK_FILES:
            try:
                # Убираем старый файл блокировки, если есть
                if os.path.exists(lock_path):
                    try:
                        with open(lock_path, 'r') as f:
                            old_pid = f.read().strip()
                            logger.warning(f"Найден старый файл блокировки {lock_path} с PID {old_pid}")
                    except:
                        pass
                    try:
                        os.remove(lock_path)
                        logger.info(f"Старый файл блокировки {lock_path} удален")
                    except Exception as e:
                        logger.error(f"Не удалось удалить старый файл блокировки {lock_path}: {e}")
                
                # Создаем новый файл блокировки
                lock_file = open(lock_path, "w")
                lock_file.write(f"{pid}\n{startup_id}\n{hostname}\n{time.time()}")
                lock_file.flush()
                
                # Получаем блокировку
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locks.append(lock_file)  # Сохраняем ссылку на файл, чтобы он не закрылся GC
                logger.info(f"Успешно получена блокировка для {lock_path}")
            except IOError:
                logger.error(f"Не удалось получить блокировку для {lock_path} - возможно другой экземпляр запущен")
            except Exception as e:
                logger.error(f"Ошибка при работе с файлом блокировки {lock_path}: {e}")
        
        # Даже если не получилось получить все блокировки, продолжаем работу
        # после завершения других процессов
        logger.info(f"Запуск бота через функцию start_polling() [PID:{pid}] [ID:{startup_id}]")
        executor.start_polling(
            dp, 
            on_startup=on_startup, 
            on_shutdown=on_shutdown, 
            skip_updates=True,
            allowed_updates=["message", "callback_query", "pre_checkout_query", "chat_join_request"]
        )
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        # Удаляем все созданные файлы блокировки
        for lock_file in locks:
            try:
                lock_path = lock_file.name
                lock_file.close()
                os.remove(lock_path)
                logger.info(f"Файл блокировки {lock_path} удален при ошибке")
            except:
                pass
        sys.exit(1)

# Запуск бота при прямом запуске файла
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


