# Анализ и исправление ошибок развертывания dostup-bot (Июнь 2025)

Этот документ содержит пошаговое руководство по анализу и исправлению конкретных ошибок, обнаруженных при развертывании сервиса `dostup-bot` в Google Cloud Run 29 июня 2025 года.

## Выявленные ошибки

По результатам анализа аудит-логов Google Cloud Run выявлены три неудачные попытки развертывания сервиса:

1. `Error detected in dostup-bot version dostup-bot-00001-fqb` (10:32:59)
2. `Error detected in dostup-bot version dostup-bot-00004-qkq` (10:58:58)
3. `Error detected in dostup-bot version dostup-bot-00005-5lk` (11:01:51)

## Пошаговый план диагностики и исправления

### Шаг 1: Сбор детальной информации о каждой ошибке

Выполните следующие команды для получения подробной информации о каждой неудачной ревизии:

```powershell
# Для версии 00001-fqb
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND severity>=ERROR" --limit=20

# Для версии 00004-qkq
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00004-qkq AND severity>=ERROR" --limit=20

# Для версии 00005-5lk
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00005-5lk AND severity>=ERROR" --limit=20
```

### Шаг 2: Проверка переменных окружения

Неправильно настроенные переменные окружения — частая причина ошибок:

```powershell
# Проверка текущих переменных окружения
gcloud run services describe dostup-bot --region=europe-west1 --format="yaml(spec.template.spec.containers[0].env)"
```

Убедитесь, что:
- `BOT_TOKEN` содержит валидный токен Telegram бота (без кавычек)
- `ADMIN_USER_ID` содержит числовое значение (без кавычек)
- `COURSE_CHANNEL_ID` содержит корректный ID канала

### Шаг 3: Исправление переменных окружения

На основе проведенного анализа, скорее всего, следует исправить переменные окружения:

```powershell
# Обновление переменных окружения
gcloud run services update dostup-bot `
  --region=europe-west1 `
  --set-env-vars=ADMIN_USER_ID=123456789,BOT_TOKEN=5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk,COURSE_CHANNEL_ID=-1001234567890
```

Важно:
- Заменить `123456789` на реальный ID администратора
- Заменить токен и ID канала на действительные значения
- Не использовать кавычки для числовых значений

### Шаг 4: Проверка проблем импорта модулей

Частой проблемой является ошибка импорта модулей. Проверьте:

```powershell
# Поиск ошибок импорта
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:ModuleNotFoundError" --limit=20
```

Если обнаружены ошибки импорта `reminder_system`, необходимо обновить Dockerfile:

1. Проверьте текущий Dockerfile и убедитесь, что он содержит:
   ```dockerfile
   # Create directory for modules in Python path
   RUN mkdir -p /usr/local/lib/python3.11/site-packages/app
   COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/app/
   COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/
   ```

2. Соберите и загрузите обновленный образ:
   ```powershell
   # Получите ID проекта
   $PROJECT_ID = gcloud config get-value project
   
   # Соберите и отправьте образ
   docker build -t gcr.io/$PROJECT_ID/dostup-bot:latest .
   docker push gcr.io/$PROJECT_ID/dostup-bot:latest
   
   # Обновите сервис с новым образом
   gcloud run services update dostup-bot `
     --region=europe-west1 `
     --image=gcr.io/$PROJECT_ID/dostup-bot:latest
   ```

### Шаг 5: Проверка HTTP-сервера для Cloud Run

Google Cloud Run требует, чтобы контейнер запускал HTTP-сервер на порту 8080. Проверьте:

```powershell
# Поиск проблем с HTTP-сервером
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:cloud_run_adapter" --limit=20
```

Убедитесь, что файл `cloud_run_adapter.py` правильно импортируется и запускается в `start.py`.

Пример правильной реализации `start.py`:
```python
import os
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # Импорт адаптера для Cloud Run
    logger.info("Importing cloud_run_adapter")
    import cloud_run_adapter
    
    # Запуск HTTP-сервера в отдельном потоке
    logger.info("Starting HTTP server for Cloud Run health checks")
    cloud_run_adapter.start_http_server()
    
    # Импорт основного модуля бота
    logger.info("Importing bot module")
    from app.bot import main
    
    # Запуск бота
    logger.info("Starting Telegram bot")
    main()
    
except Exception as e:
    logger.error(f"Error during startup: {e}")
    # Вывод дополнительной информации для отладки
    logger.error(f"Python version: {sys.version}")
    logger.error(f"Python path: {sys.path}")
    logger.error(f"Working directory: {os.getcwd()}")
    logger.error(f"Directory contents: {os.listdir('.')}")
    
    # Повышаем ошибку, чтобы контейнер перезапустился
    raise e
```

### Шаг 6: Проверка проблем авторизации Telegram

Ошибки типа `Unauthorized` часто связаны с недействительным токеном Telegram:

```powershell
# Поиск проблем авторизации
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:Unauthorized" --limit=20
```

Если обнаружены такие ошибки:
1. Проверьте токен в BotFather
2. Убедитесь, что токен активен
3. Обновите переменную окружения `BOT_TOKEN`

### Шаг 7: Добавление расширенной диагностики

Создайте новый образ с расширенной диагностикой для более точного выявления проблем:

1. Создайте файл `debug.py` в директории вашего проекта:
   ```python
   import os
   import sys
   import logging
   import requests
   import json
   
   logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
   logger = logging.getLogger(__name__)
   
   # Вывод информации о системе
   logger.info(f"Python version: {sys.version}")
   logger.info(f"Python path: {sys.path}")
   logger.info(f"Working directory: {os.getcwd()}")
   logger.info(f"Directory contents: {os.listdir('.')}")
   logger.info(f"Environment variables: {os.environ}")
   
   # Проверка токена Telegram (если он задан)
   bot_token = os.environ.get('BOT_TOKEN')
   if bot_token:
       token_len = len(bot_token)
       masked_token = bot_token[:4] + '*' * (token_len - 8) + bot_token[-4:] if token_len > 8 else "***"
       logger.info(f"BOT_TOKEN length: {token_len}, preview: {masked_token}")
       
       # Проверка через API
       try:
           url = f"https://api.telegram.org/bot{bot_token}/getMe"
           logger.info(f"Checking token validity via API call to {url}")
           response = requests.get(url, timeout=10)
           logger.info(f"API Response status: {response.status_code}")
           logger.info(f"API Response content: {response.text}")
       except Exception as e:
           logger.error(f"Error checking token: {e}")
   else:
       logger.critical("BOT_TOKEN environment variable is not set")
   
   # Проверка других переменных окружения
   admin_id = os.environ.get('ADMIN_USER_ID')
   if admin_id:
       logger.info(f"ADMIN_USER_ID: {admin_id}, type: {type(admin_id)}")
       try:
           admin_id_int = int(admin_id)
           logger.info(f"ADMIN_USER_ID as int: {admin_id_int}")
       except ValueError as e:
           logger.error(f"Error converting ADMIN_USER_ID to int: {e}")
   else:
       logger.critical("ADMIN_USER_ID environment variable is not set")
   
   # Проверка импорта модулей
   try:
       logger.info("Trying to import reminder_system")
       import reminder_system
       logger.info("Successfully imported reminder_system")
   except ImportError as e:
       logger.error(f"Failed to import reminder_system: {e}")
       try:
           logger.info("Trying to import app.reminder_system")
           from app import reminder_system
           logger.info("Successfully imported app.reminder_system")
       except ImportError as e:
           logger.error(f"Failed to import app.reminder_system: {e}")
   
   # Проверка HTTP-сервера
   try:
       logger.info("Importing cloud_run_adapter")
       import cloud_run_adapter
       logger.info("Successfully imported cloud_run_adapter")
   except ImportError as e:
       logger.error(f"Failed to import cloud_run_adapter: {e}")
   ```

2. Обновите Dockerfile, добавив запуск диагностики:
   ```dockerfile
   # Добавить после COPY операций
   COPY debug.py ./
   
   # Изменить команду запуска для диагностики
   CMD ["sh", "-c", "python debug.py && python start.py"]
   ```

3. Соберите и отправьте обновленный образ:
   ```powershell
   docker build -t gcr.io/$PROJECT_ID/dostup-bot:debug .
   docker push gcr.io/$PROJECT_ID/dostup-bot:debug
   
   # Развертывание отладочной версии
   gcloud run deploy dostup-bot-debug `
     --image gcr.io/$PROJECT_ID/dostup-bot:debug `
     --region=europe-west1 `
     --set-env-vars=ADMIN_USER_ID=123456789,BOT_TOKEN=5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk `
     --memory=512Mi `
     --cpu=1
   ```

### Шаг 8: Проверка результатов диагностики

После развертывания отладочной версии проанализируйте логи:

```powershell
# Получение логов отладочной версии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot-debug" --limit=50
```

На основе полученной информации определите точную причину ошибок и внесите соответствующие исправления.

### Шаг 9: Финальное развертывание исправленной версии

После выявления и исправления всех проблем выполните окончательное развертывание:

```powershell
# Сборка и отправка финальной версии
docker build -t gcr.io/$PROJECT_ID/dostup-bot:fixed .
docker push gcr.io/$PROJECT_ID/dostup-bot:fixed

# Обновление основного сервиса
gcloud run services update dostup-bot `
  --region=europe-west1 `
  --image=gcr.io/$PROJECT_ID/dostup-bot:fixed `
  --set-env-vars=ADMIN_USER_ID=123456789,BOT_TOKEN=5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk
```

### Шаг 10: Проверка работоспособности

Проверьте работоспособность бота:

1. **Через логи**:
   ```powershell
   # Проверка логов на отсутствие ошибок
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND severity>=ERROR" --limit=20 --freshness=1h
   ```

2. **Через Telegram**:
   - Отправьте сообщение боту
   - Проверьте логи на наличие обработки входящих сообщений

3. **Проверка статуса сервиса**:
   ```powershell
   gcloud run services describe dostup-bot --region=europe-west1 --format="yaml(status)"
   ```

## Краткое резюме решения проблем

Наиболее вероятные причины ошибок в сервисе `dostup-bot`:

1. **Неправильно настроенные переменные окружения**:
   - `ADMIN_USER_ID` должен быть числовым значением без кавычек
   - `BOT_TOKEN` должен быть действительным токеном Telegram

2. **Проблемы с импортом модулей**:
   - Модуль `reminder_system.py` должен быть доступен в пути Python
   - Необходимо правильно настроить копирование файлов в Dockerfile

3. **Проблемы с HTTP-сервером для Cloud Run**:
   - Необходимо правильно инициализировать `cloud_run_adapter.py`
   - HTTP-сервер должен слушать порт 8080

4. **Ошибки авторизации Telegram**:
   - Токен бота может быть недействительным или отозванным
   - Необходима проверка токена через API

Следуя этому руководству, вы должны успешно выявить и исправить проблемы с развертыванием сервиса `dostup-bot` в Google Cloud Run.
