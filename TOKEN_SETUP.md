🚨 **ВНИМАНИЕ: Нужен реальный токен бота!**

## Проблема
Контейнер пересобран успешно, но бот не может запуститься из-за неверного токена.

## Решение

### 1. Создайте реального Telegram бота:

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Введите имя бота (например: "YouTube Course Sales Bot")
4. Введите username бота (например: "youtube_course_sales_bot")
5. **Скопируйте полученный токен** (выглядит как `123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk`)

### 2. Обновите файл `.env`:

Замените в файле `.env`:
```env
BOT_TOKEN=YOUR_REAL_BOT_TOKEN_HERE
```

На ваш реальный токен:
```env
BOT_TOKEN=ваш_настоящий_токен_от_BotFather
```

### 3. Перезапустите контейнер:

```powershell
docker-compose up --build -d
```

### 4. Проверьте логи:

```powershell
docker-compose logs -f telegram-bot
```

---

## После получения токена:

1. **Обновите `.env`** с реальным токеном
2. **Пересоберите контейнер**: `docker-compose up --build -d`
3. **Бот будет готов к тестированию!**

🎯 **Готово!** После установки реального токена бот заработает и вы сможете протестировать весь функционал.

## Диагностика и устранение ошибок токена в Google Cloud Run

При развертывании бота в Google Cloud Run, неверно настроенный токен может привести к различным ошибкам. Вот как диагностировать и решать эти проблемы:

### Типичные ошибки, связанные с токеном

1. **`aiogram.utils.exceptions.Unauthorized: Unauthorized`**
   - **Причина**: Неверный токен бота или токен был отозван
   - **Решение**: Проверьте токен в BotFather и обновите переменные окружения

2. **`ValueError: invalid literal for int() with base 10: 'your_admin_id'`**
   - **Причина**: Переменная `ADMIN_USER_ID` содержит текстовое значение вместо числа
   - **Решение**: Убедитесь, что переменная среды содержит числовое значение без кавычек

### Проверка токена и переменных окружения в Cloud Run

#### 1. Проверьте текущие переменные окружения

```powershell
# PowerShell
gcloud run services describe dostup-bot --region=europe-west1 --format="yaml(spec.template.spec.containers[0].env)"
```

Убедитесь, что:
- `BOT_TOKEN` имеет правильный формат (5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk)
- `ADMIN_USER_ID` содержит числовое значение без кавычек

#### 2. Обновите переменные окружения с правильным токеном

```powershell
# PowerShell
gcloud run services update dostup-bot `
  --region=europe-west1 `
  --set-env-vars=BOT_TOKEN=5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk,ADMIN_USER_ID=123456789
```

#### 3. Проверьте работоспособность токена

Вы можете проверить действительность токена, выполнив запрос к API Telegram:

```python
import requests

BOT_TOKEN = "ваш_токен_здесь"
response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
print(response.json())
```

Если токен действителен, вы получите ответ с информацией о боте:
```json
{
  "ok": true,
  "result": {
    "id": 123456789,
    "is_bot": true,
    "first_name": "YourBot",
    "username": "your_bot_username",
    "can_join_groups": true,
    "can_read_all_group_messages": false,
    "supports_inline_queries": false
  }
}
```

Если токен недействителен:
```json
{
  "ok": false,
  "error_code": 401,
  "description": "Unauthorized"
}
```

### Анализ логов для выявления проблем с токеном

```powershell
# Поиск ошибок авторизации в логах
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:Unauthorized" --limit=20
```

### Общие причины проблем с токеном и их решения

1. **Пробелы или специальные символы в токене**
   - Проверьте, что токен не содержит случайных пробелов в начале или конце
   - Используйте команду `echo -n "$BOT_TOKEN" | wc -c` для подсчета символов

2. **Использование тестовых/примерных токенов**
   - Убедитесь, что вы используете реальный токен от BotFather, а не пример вида `YOUR_BOT_TOKEN`

3. **Отозванный или неактивный токен**
   - Проверьте статус бота в BotFather: `/mybots` → выберите бота → Bot Settings
   - При необходимости создайте новый токен: Bot Settings → API Token → Revoke current token → Generate new token

4. **Неправильные кавычки в переменных окружения**
   - В PowerShell избегайте одинарных кавычек для значений переменных среды
   - Используйте формат `--set-env-vars=BOT_TOKEN=токен_без_кавычек`

5. **Несколько запущенных экземпляров бота**
   - Проверьте, не запущено ли несколько экземпляров с одним токеном
   - В Telegram API одновременно может быть активен только один вебхук для бота

### Дополнительные действия для устранения проблем

1. **Создайте временного тестового бота**
   - Создайте новый тестовый бот через BotFather
   - Используйте его токен для проверки работоспособности инфраструктуры

2. **Добавьте расширенное логирование**
   - Добавьте в код дополнительные логи для отладки проблем с токеном:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   try:
       # Попытка инициализации бота
       bot = Bot(token=BOT_TOKEN)
       logging.info("Bot initialized successfully")
       # Проверка токена через API
       me = await bot.get_me()
       logging.info(f"Bot info: {me.to_python()}")
   except Exception as e:
       logging.error(f"Failed to initialize bot: {e}")
       # Вывод первых и последних 4 символа токена для проверки
       if BOT_TOKEN:
           token_len = len(BOT_TOKEN)
           safe_token = BOT_TOKEN[:4] + '*' * (token_len - 8) + BOT_TOKEN[-4:] if token_len > 8 else "***"
           logging.debug(f"Token length: {token_len}, Token preview: {safe_token}")
       else:
           logging.critical("BOT_TOKEN is empty or None")
   ```

## Чеклист проверки токена перед деплоем

✅ Токен получен от официального @BotFather
✅ Токен имеет правильный формат (числа:буквы/символы)
✅ Токен передается как переменная окружения без кавычек
✅ ADMIN_USER_ID передается как числовое значение без кавычек
✅ Токен прошел тестовую проверку через API запрос к getMe
✅ В логах нет ошибок авторизации после деплоя
