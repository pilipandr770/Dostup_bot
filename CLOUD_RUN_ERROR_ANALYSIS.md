# Анализ ошибок Google Cloud Run для dostup-bot

В этом документе проанализированы конкретные ошибки, обнаруженные в аудит-логах Google Cloud Run для сервиса `dostup-bot`.

## Обнаруженные ошибки

В аудит-логах были обнаружены следующие ошибки:

1. `Error detected in dostup-bot version dostup-bot-00001-fqb` (10:32:59)
2. `Error detected in dostup-bot version dostup-bot-00004-qkq` (10:58:58)
3. `Error detected in dostup-bot version dostup-bot-00005-5lk` (11:01:51)

## Анализ ошибок по версиям

### Версия dostup-bot-00001-fqb

#### Возможные причины:
- Первоначальная настройка сервиса
- Проблемы с импортом модулей
- Неправильно настроенные переменные окружения

#### Рекомендуемый анализ:
```powershell
# Получить детальные логи для этой версии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb" --limit=50

# Поиск конкретных ошибок импорта
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND textPayload:ModuleNotFoundError" --limit=20

# Проблемы с переменными окружения
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND textPayload:environ" --limit=20
```

### Версия dostup-bot-00004-qkq

#### Возможные причины:
- Проблемы с авторизацией Telegram (неверный токен)
- Проблемы с форматом переменных окружения
- Проблемы с HTTP-сервером для health check

#### Рекомендуемый анализ:
```powershell
# Получить детальные логи для этой версии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00004-qkq" --limit=50

# Поиск ошибок авторизации
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00004-qkq AND textPayload:Unauthorized" --limit=20

# Проблемы с переменными окружения
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00004-qkq AND textPayload:ValueError" --limit=20

# Проверка запуска HTTP-сервера
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00004-qkq AND textPayload:cloud_run_adapter" --limit=20
```

### Версия dostup-bot-00005-5lk

#### Возможные причины:
- Повторяющиеся проблемы после исправлений в предыдущих версиях
- Новые ошибки после обновления переменных окружения
- Проблемы с взаимодействием с API Telegram

#### Рекомендуемый анализ:
```powershell
# Получить детальные логи для этой версии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00005-5lk" --limit=50

# Поиск общих ошибок
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00005-5lk AND severity>=ERROR" --limit=20
```

## Общий план диагностики и исправления

1. **Изучение логов по каждой ревизии**
   - Определение точных причин ошибок
   - Выявление паттернов повторяющихся проблем

2. **Проверка переменных окружения**
   ```powershell
   # Проверка текущих переменных среды
   gcloud run services describe dostup-bot --region=europe-west1 --format="yaml(spec.template.spec.containers[0].env)"
   ```

3. **Исправление переменных окружения**
   ```powershell
   # Обновление переменных с правильными значениями
   gcloud run services update dostup-bot `
     --region=europe-west1 `
     --set-env-vars=ADMIN_USER_ID=123456789,BOT_TOKEN=5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk
   ```

4. **Проверка доступности API Telegram**
   - Создание простого скрипта для проверки токена
   ```python
   import requests
   
   BOT_TOKEN = "ваш_токен_здесь"
   response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
   print(response.json())
   ```

5. **Обновление образа Docker с дополнительным логированием**
   - Добавление более подробного логирования в код
   - Перестроение и повторная отправка образа

## Проверка текущего статуса

```powershell
# Проверка статуса последней версии
gcloud run services describe dostup-bot --region=europe-west1

# Проверка метрик работоспособности
gcloud run services describe dostup-bot --region=europe-west1 --format="yaml(status)"

# Получение списка всех версий и их статуса
gcloud run revisions list --service=dostup-bot --region=europe-west1
```

## План исправления конкретных ошибок

### 1. ModuleNotFoundError: No module named 'reminder_system'

```powershell
# Проверка в Dockerfile
# Убедитесь, что файл reminder_system.py копируется в правильную директорию
# Обновите Dockerfile:

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всех нужных файлов
COPY app/ /app/
COPY cloud_run_adapter.py start.py ./

# Гарантированное копирование reminder_system.py в путь Python
RUN mkdir -p /usr/local/lib/python3.11/site-packages/app/
COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/app/
COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/

# Открываем порт для HTTP-сервера
EXPOSE 8080

CMD ["python", "start.py"]
```

### 2. ValueError: invalid literal for int() with base 10: 'your_admin_id'

```powershell
# Проверка и обновление переменных окружения без кавычек
gcloud run services update dostup-bot `
  --region=europe-west1 `
  --set-env-vars=ADMIN_USER_ID=123456789
```

### 3. aiogram.utils.exceptions.Unauthorized: Unauthorized

```powershell
# Проверка и обновление токена бота
gcloud run services update dostup-bot `
  --region=europe-west1 `
  --set-env-vars=BOT_TOKEN=5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk
```

## Мониторинг после исправлений

```powershell
# Проверка логов новой версии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND timestamp>=\"$(Get-Date).AddMinutes(-30).ToString('o')\"" --limit=50

# Наблюдение за ошибками в реальном времени
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND severity>=ERROR" --limit=20 --format="table(timestamp, severity, textPayload)" --freshness=1h
```

## Проверка успешной работы бота

После внесения исправлений необходимо проверить:

1. **Работает ли HTTP-сервер на порту 8080**
   - Проверка через Cloud Run URL

2. **Отвечает ли бот на сообщения в Telegram**
   - Отправка тестового сообщения боту
   - Проверка логов на наличие обработки входящих сообщений
   ```powershell
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:\"Received message\"" --limit=20
   ```

3. **Работает ли система напоминаний**
   - Создание тестового напоминания
   - Проверка его сохранения и отправки
   ```powershell
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:reminder" --limit=20
   ```
