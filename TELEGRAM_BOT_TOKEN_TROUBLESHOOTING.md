# Устранение проблем с токеном Telegram бота

## Проблема "Unauthorized" в логах Cloud Run

Если в логах вашего развернутого бота в Google Cloud Run появляются ошибки вида `aiogram.utils.exceptions.Unauthorized: Unauthorized`, это означает, что бот не может пройти авторизацию в API Telegram. Несмотря на эту ошибку, сам контейнер Cloud Run может работать нормально (статус "Ready"), поскольку HTTP-сервер для проверки работоспособности запущен успешно.

## Шаги по диагностике

### 1. Проверьте текущий токен бота

```powershell
# Для Windows PowerShell
gcloud run services describe dostup-bot --region=europe-west1 | Select-String "BOT_TOKEN"

# Для Linux/Mac
gcloud run services describe dostup-bot --region=europe-west1 | grep BOT_TOKEN
```

### 2. Проверьте валидность токена

Откройте в браузере:
```
https://api.telegram.org/bot<ваш_токен>/getMe
```

Если токен действительный, вы увидите ответ примерно такого вида:
```json
{
  "ok": true,
  "result": {
    "id": 1234567890,
    "is_bot": true,
    "first_name": "ИмяВашегоБота",
    "username": "YourBotUsername",
    "can_join_groups": true,
    "can_read_all_group_messages": false,
    "supports_inline_queries": false
  }
}
```

Если токен недействительный, вы увидите:
```json
{
  "ok": false,
  "error_code": 401,
  "description": "Unauthorized"
}
```

### 3. Возможные причины проблемы

1. **Токен был аннулирован**
   - BotFather мог отозвать токен
   - Кто-то мог сбросить токен бота

2. **Неправильный формат токена**
   - Лишние пробелы или символы в токене
   - Отсутствие части токена

3. **Ограничения со стороны Telegram**
   - Временные проблемы с API Telegram
   - Блокировка токена из-за подозрительной активности
   - Региональные ограничения доступа к API Telegram

### 4. Решение проблемы

#### Получение нового токена

1. Откройте чат с [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/mybots`
3. Выберите вашего бота из списка
4. Нажмите на "API Token"
5. Выберите "Revoke current token"
6. Подтвердите действие
7. BotFather выдаст новый токен

#### Обновление токена в Cloud Run

```powershell
# Для Windows PowerShell
gcloud run services update dostup-bot `
  --set-env-vars="BOT_TOKEN=ваш_новый_токен" `
  --region=europe-west1

# Для Linux/Mac
gcloud run services update dostup-bot \
  --set-env-vars="BOT_TOKEN=ваш_новый_токен" \
  --region=europe-west1
```

#### Проверка логов после обновления

```powershell
# Просмотр логов после обновления токена
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=20

# Просмотр логов в реальном времени
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --tail
```

## Дополнительные рекомендации

### Хранение токена в Secret Manager

Вместо того чтобы хранить токен непосредственно в переменных окружения, рассмотрите возможность использования Google Secret Manager:

1. **Создание секрета**:
   ```powershell
   # Создаем секрет для токена бота
   gcloud secrets create telegram-bot-token --replication-policy="automatic"
   
   # Добавляем значение токена
   echo -n "ваш_токен_бота" | gcloud secrets versions add telegram-bot-token --data-file=-
   ```

2. **Предоставление доступа сервисному аккаунту**:
   ```powershell
   # Получаем ID проекта и номер
   $PROJECT_ID = gcloud config get-value project
   $PROJECT_NUMBER = $(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
   
   # Предоставляем доступ к секрету
   gcloud secrets add-iam-policy-binding telegram-bot-token `
     --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
     --role="roles/secretmanager.secretAccessor"
   ```

3. **Обновление сервиса для использования секрета**:
   ```powershell
   gcloud run services update dostup-bot `
     --update-secrets="BOT_TOKEN=telegram-bot-token:latest" `
     --region=europe-west1
   ```

### Проверка доступности API Telegram

Если проблема не в токене, убедитесь, что API Telegram доступен из вашего региона Cloud Run:

```powershell
# Выполняем команду curl к API Telegram из контейнера
gcloud run services update dostup-bot `
  --command="/bin/sh" `
  --args="-c,curl -s https://api.telegram.org/bot${BOT_TOKEN}/getMe" `
  --region=europe-west1
```

После проверки не забудьте вернуть исходную команду:

```powershell
gcloud run services update dostup-bot `
  --command="python" `
  --args="../start.py" `
  --region=europe-west1
```
