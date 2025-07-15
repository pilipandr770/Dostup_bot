#!/usr/bin/env python3
# debug_cloud_run.py - Скрипт диагностики для развертывания dostup-bot в Google Cloud Run

import os
import sys
import logging
import traceback
import platform
import json
import asyncio
from aiohttp import web

# Настройка расширенного логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dostup_bot_diagnostic")

def print_separator(title=""):
    width = 80
    if title:
        side_width = (width - len(title) - 2) // 2
        logger.info("=" * side_width + f" {title} " + "=" * side_width)
    else:
        logger.info("=" * width)

def diagnose_system():
    """Диагностика системного окружения"""
    print_separator("СИСТЕМНАЯ ИНФОРМАЦИЯ")
    
    logger.info(f"Python версия: {sys.version}")
    logger.info(f"Платформа: {platform.platform()}")
    logger.info(f"Интерпретатор: {sys.executable}")
    logger.info(f"Текущая директория: {os.getcwd()}")
    logger.info(f"Содержимое директории:")
    
    try:
        for item in os.listdir('.'):
            if os.path.isdir(item):
                logger.info(f" - 📁 {item}/")
            else:
                logger.info(f" - 📄 {item}")
    except Exception as e:
        logger.error(f"Ошибка при чтении содержимого директории: {e}")
    
    logger.info(f"Путь Python (sys.path):")
    for idx, path in enumerate(sys.path, 1):
        logger.info(f" {idx}. {path}")

def diagnose_env_variables():
    """Диагностика переменных окружения"""
    print_separator("ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ")
    
    # Список критичных переменных
    critical_vars = ['BOT_TOKEN', 'ADMIN_USER_ID', 'COURSE_CHANNEL_ID']
    
    for var in critical_vars:
        value = os.environ.get(var)
        if value:
            # Маскируем токен, но показываем его длину и начало/конец
            if var == 'BOT_TOKEN':
                length = len(value)
                if length > 8:
                    masked = f"{value[:4]}{'*' * (length - 8)}{value[-4:]}"
                else:
                    masked = "********"
                logger.info(f"{var}: {masked} (длина: {length})")
                
                # Проверка формата токена
                if ':' in value and length > 30:
                    logger.info(f"✅ Формат BOT_TOKEN выглядит правильным")
                else:
                    logger.warning(f"⚠️ Формат BOT_TOKEN может быть некорректным. Ожидается формат числа:строки")
            else:
                logger.info(f"{var}: {value}")
                
                # Проверка числовых значений
                if var == 'ADMIN_USER_ID':
                    try:
                        admin_id = int(value)
                        logger.info(f"✅ ADMIN_USER_ID успешно преобразован в число: {admin_id}")
                    except ValueError:
                        logger.error(f"❌ ADMIN_USER_ID не является числом! Это вызовет ошибку!")
        else:
            logger.error(f"❌ Переменная {var} не определена!")

    # Вывод всех остальных переменных окружения
    logger.info("Другие переменные окружения:")
    for key, value in sorted(os.environ.items()):
        if key not in critical_vars:
            logger.debug(f" - {key}: {value}")

def check_imports():
    """Проверка импорта критических модулей"""
    print_separator("ПРОВЕРКА ИМПОРТА МОДУЛЕЙ")
    
    modules_to_check = [
        ('cloud_run_adapter', 'HTTP-адаптер для Cloud Run'),
        ('reminder_system', 'Система напоминаний'),
        ('app.reminder_system', 'Система напоминаний (через app)'),
        ('app.bot', 'Основной модуль бота'),
        ('aiogram', 'Библиотека Telegram Bot API'),
        ('sqlite3', 'Поддержка SQLite'),
        ('aiohttp', 'HTTP-клиент/сервер'),
    ]
    
    for module_name, description in modules_to_check:
        try:
            module = __import__(module_name)
            if hasattr(module, '__version__'):
                version = module.__version__
                logger.info(f"✅ Импорт {module_name} успешен (версия {version}) - {description}")
            else:
                logger.info(f"✅ Импорт {module_name} успешен - {description}")
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта {module_name} - {description}: {e}")
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при импорте {module_name}: {e}")
            logger.error(traceback.format_exc())

def verify_telegram_token():
    """Проверка валидности токена Telegram Bot API"""
    print_separator("ПРОВЕРКА ТОКЕНА TELEGRAM")
    
    bot_token = os.environ.get('BOT_TOKEN')
    
    if not bot_token:
        logger.error("❌ Переменная BOT_TOKEN не определена!")
        return
    
    try:
        import requests
        
        logger.info("Отправка запроса к API Telegram...")
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        
        response = requests.get(url, timeout=10)
        logger.info(f"Код ответа: {response.status_code}")
        
        data = response.json()
        logger.info(f"Ответ API: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200 and data.get('ok'):
            bot_info = data.get('result', {})
            logger.info(f"✅ Токен действителен! Информация о боте:")
            logger.info(f" - ID: {bot_info.get('id')}")
            logger.info(f" - Имя: {bot_info.get('first_name')}")
            logger.info(f" - Username: @{bot_info.get('username')}")
        else:
            logger.error(f"❌ Недействительный токен! Ошибка: {data.get('description', 'Неизвестная ошибка')}")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке токена: {e}")
        logger.error(traceback.format_exc())

def check_http_server():
    """Проверка настройки HTTP-сервера для Cloud Run"""
    print_separator("ПРОВЕРКА HTTP-СЕРВЕРА")
    
    try:
        # Попытка найти модуль cloud_run_adapter
        import cloud_run_adapter
        
        logger.info("✅ Модуль cloud_run_adapter успешно импортирован")
        
        # Проверка наличия функции для запуска HTTP-сервера
        if hasattr(cloud_run_adapter, 'start_http_server'):
            logger.info("✅ Функция start_http_server найдена в модуле")
            
            # Проверка порта
            if hasattr(cloud_run_adapter, 'PORT'):
                port = getattr(cloud_run_adapter, 'PORT')
                if port == 8080:
                    logger.info("✅ Порт HTTP-сервера правильно настроен на 8080")
                else:
                    logger.warning(f"⚠️ Порт HTTP-сервера настроен на {port}, но Cloud Run ожидает 8080")
        else:
            logger.error("❌ Функция start_http_server не найдена в модуле cloud_run_adapter")
            
        # Проверка файла start.py
        if os.path.exists('start.py'):
            logger.info("✅ Файл start.py найден")
            try:
                with open('start.py', 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'cloud_run_adapter' in content and 'start_http_server' in content:
                        logger.info("✅ Файл start.py содержит вызов cloud_run_adapter.start_http_server")
                    else:
                        logger.warning("⚠️ Файл start.py может не запускать HTTP-сервер для Cloud Run")
            except Exception as e:
                logger.error(f"❌ Ошибка при чтении файла start.py: {e}")
        else:
            logger.error("❌ Файл start.py не найден")
    except ImportError:
        logger.error("❌ Модуль cloud_run_adapter не найден")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при проверке HTTP-сервера: {e}")
        logger.error(traceback.format_exc())

def check_file_permissions():
    """Проверка прав доступа к файлам"""
    print_separator("ПРОВЕРКА ПРАВ ДОСТУПА")
    
    critical_paths = [
        '.',
        './app',
        './app/bot.py',
        './start.py',
        './cloud_run_adapter.py'
    ]
    
    for path in critical_paths:
        if os.path.exists(path):
            try:
                # Для файлов проверяем возможность чтения
                if os.path.isfile(path):
                    with open(path, 'r') as f:
                        first_line = f.readline().strip()
                    logger.info(f"✅ Файл {path} доступен для чтения: {first_line[:30]}...")
                # Для директорий проверяем возможность листинга
                else:
                    items = os.listdir(path)
                    logger.info(f"✅ Директория {path} доступна для чтения ({len(items)} элементов)")
            except PermissionError:
                logger.error(f"❌ Отказано в доступе к {path}")
            except Exception as e:
                logger.error(f"❌ Ошибка при проверке {path}: {e}")
        else:
            logger.warning(f"⚠️ Путь {path} не существует")

def check_dockerfile():
    """Проверка настроек Dockerfile"""
    print_separator("ПРОВЕРКА DOCKERFILE")
    
    if os.path.exists('Dockerfile'):
        try:
            with open('Dockerfile', 'r') as f:
                content = f.read()
                
            logger.info("Анализ содержимого Dockerfile...")
            
            # Проверка базового образа
            if 'FROM python:3.11' in content:
                logger.info("✅ Использует Python 3.11")
            else:
                logger.warning("⚠️ Может не использовать Python 3.11")
                
            # Проверка копирования reminder_system.py
            if '/usr/local/lib/python3.11/site-packages/app/' in content and 'reminder_system.py' in content:
                logger.info("✅ Копирует reminder_system.py в путь Python")
            else:
                logger.warning("⚠️ Может не копировать reminder_system.py в путь Python")
                
            # Проверка порта
            if 'EXPOSE 8080' in content:
                logger.info("✅ Экспортирует порт 8080")
            else:
                logger.warning("⚠️ Может не экспортировать порт 8080")
                
            # Проверка команды запуска
            if 'CMD ["python"' in content and 'start.py' in content:
                logger.info("✅ Команда запуска использует start.py")
            else:
                logger.warning("⚠️ Может не запускать start.py")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при чтении Dockerfile: {e}")
    else:
        logger.error("❌ Dockerfile не найден")

def diagnose_database():
    """Диагностика базы данных"""
    print_separator("ПРОВЕРКА БАЗЫ ДАННЫХ")
    
    db_paths = [
        './app/bot_database.db',
        './bot_database.db',
        './database.db'
    ]
    
    db_found = False
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            db_found = True
            logger.info(f"✅ База данных найдена: {db_path}")
            
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Получаем список таблиц
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                if tables:
                    logger.info(f"✅ База данных содержит {len(tables)} таблиц:")
                    for table in tables:
                        table_name = table[0]
                        logger.info(f" - {table_name}")
                        
                        # Проверяем структуру таблицы
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        logger.info(f"   Колонки ({len(columns)}):")
                        for col in columns:
                            logger.info(f"   - {col[1]} ({col[2]})")
                        
                        # Проверяем количество записей
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        logger.info(f"   Записей: {count}")
                else:
                    logger.warning("⚠️ База данных не содержит таблиц")
                
                conn.close()
            except Exception as e:
                logger.error(f"❌ Ошибка при проверке базы данных {db_path}: {e}")
                logger.error(traceback.format_exc())
    
    if not db_found:
        logger.warning("⚠️ База данных не найдена в ожидаемых местах")

async def run_http_server():
    """Запуск HTTP-сервера для проверки работоспособности Cloud Run"""
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Запуск HTTP-сервера на порту {port} для проверки работоспособности Cloud Run")
    
    async def health_handler(request):
        return web.Response(text="Debug server is running")
    
    async def debug_handler(request):
        # Сбор всей диагностической информации
        try:
            # Используем все диагностические функции для сбора данных
            diagnose_system()
            diagnose_env_variables()
            check_imports()
            check_file_permissions()
            
            # Сбор информации о системе для JSON-ответа
            system_info = {
                "python_version": sys.version,
                "platform": platform.platform(),
                "current_directory": os.getcwd(),
                "directory_contents": os.listdir('.') if os.path.exists('.') else [],
                "parent_directory_contents": os.listdir('..') if os.path.exists('..') else [],
                "python_path": sys.path,
                "environment_variables": {k: ("[HIDDEN]" if k in ["BOT_TOKEN", "ADMIN_USER_ID"] else v) for k, v in os.environ.items()},
            }
            
            # Проверка критически важных файлов
            file_paths = [
                "/app/reminder_system.py",
                "/usr/local/lib/python3.11/site-packages/reminder_system.py",
                "/usr/local/lib/python3.11/site-packages/app/reminder_system.py",
                "../start.py",
                "../cloud_run_adapter.py",
                "bot.py"
            ]
            system_info["file_checks"] = {path: os.path.exists(path) for path in file_paths}
            
            # Проверка возможностей импорта
            import_tests = {}
            try:
                import reminder_system
                import_tests["reminder_system"] = {
                    "success": True, 
                    "file": getattr(reminder_system, "__file__", "Unknown")
                }
            except ImportError as e:
                import_tests["reminder_system"] = {"success": False, "error": str(e)}
                
            try:
                from app.reminder_system import ReminderSystem
                import_tests["app.reminder_system"] = {"success": True}
            except ImportError as e:
                import_tests["app.reminder_system"] = {"success": False, "error": str(e)}
            
            system_info["import_tests"] = import_tests
            
            return web.json_response(system_info)
        except Exception as e:
            logger.error(f"Ошибка в обработчике отладки: {e}")
            logger.error(traceback.format_exc())
            return web.Response(text=f"Ошибка при сборе информации для отладки: {e}", status=500)
    
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/debug", debug_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logger.info(f"HTTP-сервер запущен на http://0.0.0.0:{port}")
    logger.info("Доступ к /debug для получения подробной диагностической информации")
    
    # Поддержание работы сервера
    while True:
        await asyncio.sleep(3600)

def main():
    """Основная функция диагностики"""
    print_separator("НАЧАЛО ДИАГНОСТИКИ DOSTUP-BOT")
    logger.info("Запуск диагностики для достижения успешного развертывания в Cloud Run")
    
    try:
        # Запуск всех диагностических функций
        diagnose_system()
        diagnose_env_variables()
        check_imports()
        verify_telegram_token()
        check_http_server()
        check_file_permissions()
        check_dockerfile()
        diagnose_database()
        
        print_separator("ЗАВЕРШЕНИЕ ДИАГНОСТИКИ")
        logger.info("Диагностика завершена. Исправьте выявленные проблемы для успешного развертывания.")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в процессе диагностики: {e}")
        logger.error(traceback.format_exc())

# Добавлено для запуска HTTP-сервера в Cloud Run
if __name__ == "__main__":
    # Если мы в Cloud Run (установлена переменная окружения PORT), запускаем HTTP-сервер
    if "PORT" in os.environ:
        logger.info("Работа в режиме Cloud Run с HTTP-сервером")
        try:
            asyncio.run(run_http_server())
        except Exception as e:
            logger.error(f"Ошибка HTTP-сервера: {e}")
            logger.error(traceback.format_exc())
    else:
        # Запуск обычной диагностики, если не в Cloud Run
        logger.info("Работа в режиме локальной диагностики")
        print_separator("НАЧАЛО ДИАГНОСТИКИ")
        diagnose_system()
        diagnose_env_variables()
        check_imports()
        check_file_permissions()
        print_separator("КОНЕЦ ДИАГНОСТИКИ")
