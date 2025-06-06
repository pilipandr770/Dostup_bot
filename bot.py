import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token and other variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
PROVIDER_TOKEN = os.getenv('PROVIDER_TOKEN')
COURSE_CHANNEL_ID = os.getenv('COURSE_CHANNEL_ID')
YOUTUBE_CHANNEL_URL = os.getenv('YOUTUBE_CHANNEL_URL', 'https://youtube.com/@your-channel-name')

# Check if BOT_TOKEN is provided
if not BOT_TOKEN or BOT_TOKEN == 'YOUR_REAL_BOT_TOKEN_HERE':
    logger.error("BOT_TOKEN is not set or using placeholder. Please get a real token from @BotFather")
    exit(1)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# FSM States
class ConsentStates(StatesGroup):
    agb = State()
    widerruf = State()
    datenschutz = State()
    payment_form = State()
    ready = State()

# Main menu keyboard
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎬 Получить бесплатный урок")],
        [KeyboardButton(text="🎓 Пройти курс")]
    ],
    resize_keyboard=True
)

# Payment keyboard
payment_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 99€", callback_data="pay_course")]
    ]
)

# Consent keyboard
consent_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Согласен")],
        [KeyboardButton(text="❌ Не согласен")]
    ],
    resize_keyboard=True
)

# Test payment form keyboard
test_payment_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Имя: Иван Иванов")],
        [KeyboardButton(text="Email: test@example.com")],
        [KeyboardButton(text="Телефон: +49123456789")],
        [KeyboardButton(text="✅ Подтвердить тестовую оплату")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
@dp.message(F.text.lower() == "старт")
async def send_welcome(message: types.Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} started bot (/start)")
    welcome_text = """👋 Добро пожаловать в бот курса «Успешный YouTube-бизнес с нуля»!

Ты здесь не случайно — значит, хочешь создать YouTube-канал, который будет приносить доход. Мы поможем тебе это сделать.

📚 Что тебя ждёт:
✅ Пошаговая система от запуска до монетизации
✅ Реальные примеры и инструменты, которые работают
✅ Без воды — только практика

⸻

🎁 Начни прямо сейчас — получи бесплатный ознакомительный урок!
👀 Узнаешь, какие каналы сегодня реально зарабатывают, с чего начать и как избежать частых ошибок.

👉 Нажми «Посмотреть тестовый урок»"""
    
    await message.answer(welcome_text, reply_markup=main_menu)
    await state.clear()

@dp.message(F.text.lower() == "🎬 получить бесплатный урок")
async def send_test_lesson(message: types.Message):
    logger.info(f"User {message.from_user.id} requested test lesson")
    try:        # Отправляем ссылку на YouTube канал вместо видео
        youtube_message = f"""🎬 Вот твой бесплатный ознакомительный урок!

📌 В этом уроке ты узнаешь:
• Какие каналы реально зарабатывают
• С чего начать новичку
• Как избежать частых ошибок

🎥 Смотри пробный урок на нашем YouTube канале:
👉 {YOUTUBE_CHANNEL_URL}

🔥 Переходи по ссылке и получай первые знания прямо сейчас!"""
        
        await message.answer(youtube_message)
        
        # Сообщение после отправки ссылки
        after_link_text = """💬 Понравился пробный урок? Это только начало 😉

📦 Полная программа включает:
📌 Анализ ниш и выбор тематики
📌 Создание контента без дорогой техники
📌 Алгоритмы YouTube и продвижение
📌 Способы заработка и монетизации
📌 Реальные кейсы + поддержка в чате

⸻

🔥 Хочешь пройти весь путь вместе с нами и запустить свой канал?
Тогда присоединяйся к полному курсу прямо сейчас 👇

👉 Нажми «🎓 Пройти курс»"""
        
        await message.answer(after_link_text, reply_markup=main_menu)
    except Exception as e:
        logger.error(f"Error sending test lesson: {e}")
        await message.answer("❌ Ошибка при отправке ссылки. Свяжитесь с поддержкой.")

@dp.message(F.text.lower() == "🎓 пройти курс")
async def start_consent(message: types.Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} started consent process")
    course_info_text = """🎓 Курс «Успешный YouTube-бизнес с нуля»

💰 Стоимость: 99€
🕒 Доступ навсегда + закрытое сообщество
📚 Полная программа + поддержка экспертов

⸻

Перед оплатой необходимо ознакомиться и подтвердить согласие с документами:

📋 ДОКУМЕНТ 1: Allgemeine Geschäftsbedingungen (AGB)
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
Es gilt deutsches Recht."""
    await message.answer(course_info_text, reply_markup=consent_keyboard)
    await state.set_state(ConsentStates.agb)

@dp.message(ConsentStates.agb)
async def handle_agb_consent(message: types.Message, state: FSMContext):
    if message.text == "✅ Согласен":
        logger.info(f"User {message.from_user.id} agreed to AGB")
        doc_text = """📋 ДОКУМЕНТ 2: Widerrufsverzicht

Ich stimme ausdrücklich zu, dass der Anbieter mit der Ausführung des Vertrages vor Ablauf der Widerrufsfrist beginnt.

Mir ist bekannt, dass ich bei vollständiger Vertragserfüllung durch den Anbieter mein Widerrufsrecht verliere, wenn der Vertrag auf meinen ausdrücklichen Wunsch erfüllt wurde, bevor die Widerrufsfrist abgelaufen ist.

Bei digitalen Inhalten, deren Bereitstellung nicht auf einem körperlichen Datenträger erfolgt, verliere ich mein Widerrufsrecht, sobald der Anbieter mit der Ausführung begonnen hat, nachdem ich ausdrücklich zugestimmt habe und bestätigt habe, dass ich mein Widerrufsrecht bei Beginn der Ausführung verliere.

Ich bestätige hiermit meinen ausdrücklichen Verzicht auf das Widerrufsrecht."""
        await message.answer(doc_text, reply_markup=consent_keyboard)
        await state.set_state(ConsentStates.widerruf)
    else:
        await message.answer("Для продолжения необходимо согласие с условиями.", reply_markup=main_menu)
        await state.clear()

@dp.message(ConsentStates.widerruf)
async def handle_widerruf_consent(message: types.Message, state: FSMContext):
    if message.text == "✅ Согласен":
        logger.info(f"User {message.from_user.id} agreed to Widerrufsverzicht")
        doc_text = """📋 ДОКУМЕНТ 3: Datenschutzerklärung

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

Mit der Zustimmung erklären Sie sich mit der Verarbeitung Ihrer Daten gemäß dieser Datenschutzerklärung einverstanden."""
        await message.answer(doc_text, reply_markup=consent_keyboard)
        await state.set_state(ConsentStates.datenschutz)
    else:
        await message.answer("Для продолжения необходимо согласие с условиями.", reply_markup=main_menu)
        await state.clear()

@dp.message(ConsentStates.datenschutz)
async def handle_datenschutz_consent(message: types.Message, state: FSMContext):
    if message.text == "✅ Согласен":
        logger.info(f"User {message.from_user.id} completed all consents")
        await message.answer(
            "🎉 Отлично! Все согласия получены.\n\n"
            "💳 ТЕСТОВАЯ ОПЛАТА\n"
            "💰 Курс «YouTube-бизнес с нуля»: 99€\n\n"
            "📝 Заполните тестовые данные для оплаты:",
            reply_markup=test_payment_keyboard
        )
        await state.set_state(ConsentStates.payment_form)
    else:
        await message.answer("Для продолжения необходимо согласие с условиями.", reply_markup=main_menu)
        await state.clear()

@dp.message(ConsentStates.payment_form)
async def handle_test_payment(message: types.Message, state: FSMContext):
    if message.text == "✅ Подтвердить тестовую оплату":
        logger.info(f"User {message.from_user.id} completed test payment")
          # Create invite link for the channel
        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=COURSE_CHANNEL_ID,
                expire_date=None,
                member_limit=1
            )
            
            await message.answer(
                f"🎉 ТЕСТОВАЯ ОПЛАТА ПРОШЛА УСПЕШНО!\n\n"
                f"💰 Сумма: 99.00 EUR\n"
                f"🎓 Курс: «YouTube-бизнес с нуля»\n"
                f"🔗 Ваша ссылка для доступа к курсу: {invite_link.invite_link}\n\n"
                f"✅ Добро пожаловать в закрытое сообщество!\n"
                f"📚 Начинайте обучение и создавайте свой успешный канал!\n\n"
                f"⚠️ Это тестовая оплата - в реальной версии здесь будет настоящий платеж.",
                reply_markup=main_menu
            )
            await state.clear()
        except Exception as e:
            logger.error(f"Error creating invite link: {e}")
            await message.answer(
                f"🎉 ТЕСТОВАЯ ОПЛАТА ПРОШЛА УСПЕШНО!\n\n"
                f"💰 Сумма: 99.00 EUR\n"
                f"❗ Произошла ошибка при создании ссылки. Свяжитесь с поддержкой.\n"
                f"📚 Это тестовая оплата - в реальной версии здесь будет настоящий платеж.",
                reply_markup=main_menu
            )
            await state.clear()
    else:
        # User is filling in payment form data
        await message.answer("Заполните все поля и нажмите 'Подтвердить тестовую оплату'", reply_markup=test_payment_keyboard)

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    logger.info(f"Pre-checkout query from user {pre_checkout_query.from_user.id}")
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.content_type == types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    logger.info(f"Successful payment from user {message.from_user.id}")
    payment_info = message.successful_payment
    
    # Create invite link for the channel
    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=COURSE_CHANNEL_ID,
            expire_date=None,
            member_limit=1
        )
        
        await message.answer(
            f"🎉 Оплата прошла успешно!\n\n"
            f"💰 Сумма: {payment_info.total_amount // 100} {payment_info.currency}\n"
            f"🔗 Ваша ссылка для доступа к курсу: {invite_link.invite_link}\n\n"
            f"Добро пожаловать в закрытый курс!",
            reply_markup=main_menu
        )
    except Exception as e:
        logger.error(f"Error creating invite link: {e}")
        await message.answer(
            f"🎉 Оплата прошла успешно!\n\n"
            f"💰 Сумма: {payment_info.total_amount // 100} {payment_info.currency}\n"
            f"❗ Произошла ошибка при создании ссылки. Свяжитесь с поддержкой.",
            reply_markup=main_menu
        )

# Fallback handler for unknown messages
@dp.message()
async def handle_unknown(message: types.Message):
    logger.info(f"Unknown message from user {message.from_user.id}: {message.text}")
    await message.answer("Используйте кнопки меню:", reply_markup=main_menu)

async def main():
    logger.info("Bot is starting...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
