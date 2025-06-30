# Telegram Bot для продажи YouTube курсов

Упрощенный бот для продажи онлайн курсов с автоматической выдачей доступа к закрытому Telegram каналу.

## Функционал

✅ **Пробный урок**: Отправка ссылки на YouTube канал с бесплатным уроком  
✅ **Оплата курса**: Обработка платежей (тестовый режим)  
✅ **Автоматический доступ**: Создание ссылки-приглашения в закрытый канал после оплаты  
✅ **Согласие с документами**: AGB, Widerrufsverzicht, Datenschutzerklärung  

## Быстрый запуск

### 1. Настройка переменных среды
Создайте файл `.env` в корне проекта:
```env
BOT_TOKEN=your_bot_token_here
PROVIDER_TOKEN=your_provider_token_here
COURSE_CHANNEL_ID=-1001234567890
YOUTUBE_CHANNEL_URL=https://youtube.com/@your-channel-name
```

### 2. Запуск с Docker Compose (рекомендуется)
```bash
# Запуск бота
docker-compose up -d

# Просмотр логов
docker-compose logs -f telegram-bot

# Остановка
docker-compose down
```

### 3. Запуск с Docker
```bash
# Сборка образа
docker build -t dostup-bot .

# Запуск контейнера
docker run -d --name dostup_bot --env-file .env dostup-bot

# Просмотр логов
docker logs -f dostup_bot

# Остановка
docker stop dostup_bot && docker rm dostup_bot
```

## Структура проекта
```
dostup_bot/
├── app/
│   ├── bot.py              # Основной файл бота
│   └── requirements.txt    # Python зависимости
├── .env                   # Переменные окружения (НЕ КОММИТИТЬ!)
├── Dockerfile             # Конфигурация Docker образа
├── docker-compose.yml     # Конфигурация Docker Compose
├── .dockerignore         # Исключения для Docker
└── README.md             # Документация
```

## Переменные окружения (.env файл)
```env
BOT_TOKEN=your_telegram_bot_token_here
PROVIDER_TOKEN=your_payment_provider_token_here  
COURSE_CHANNEL_ID=@your_channel_username_or_chat_id
YOUTUBE_CHANNEL_URL=https://youtube.com/@your-channel-name
```

## Настройка

### 1. Создание Telegram бота
1. Напишите [@BotFather](https://t.me/BotFather) в Telegram
2. Используйте команду `/newbot`
3. Скопируйте полученный токен в `BOT_TOKEN`

### 2. Создание закрытого канала
1. Создайте закрытый Telegram канал
2. Добавьте бота как администратора
3. Скопируйте ID канала в `COURSE_CHANNEL_ID`

### 3. YouTube канал
1. Загрузите пробный урок на YouTube
2. Скопируйте ссылку на канал в `YOUTUBE_CHANNEL_URL`

## Особенности

- **Безопасность**: Бот запускается от непривилегированного пользователя
- **Логи**: Все логи доступны через `docker logs`
- **Рестарт**: Автоматический перезапуск при сбоях
- **Изоляция**: Бот работает в изолированном контейнере
- **Упрощенный процесс**: Отправка ссылки вместо загрузки видео

## Разработка

Для разработки можно монтировать код:
```bash
docker run -it --rm \
  --env-file .env \
  -v "$(pwd)/app:/app" \
  dostup-bot
```

## Производственное развертывание

1. Убедитесь что `.env` файл содержит реальные токены
2. Настройте реальный `COURSE_CHANNEL_ID`
3. Укажите правильный `YOUTUBE_CHANNEL_URL`
4. Запустите: `docker-compose up -d`

## Мониторинг

```bash
# Статус контейнера
docker-compose ps

# Логи в реальном времени
docker-compose logs -f

# Использование ресурсов
docker stats dostup_bot
```
