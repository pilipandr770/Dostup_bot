#!/bin/bash
# Script to set up Redis for the bot

# Проверяем наличие Redis
command -v redis-cli >/dev/null 2>&1 || { echo "Redis не установлен. Установите Redis для использования распределенной блокировки."; exit 1; }

# Проверяем, запущен ли Redis
redis-cli ping >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Redis не запущен. Запускаем локальный Redis сервер..."
    redis-server --daemonize yes
    sleep 2
    
    # Проверяем, запустился ли Redis
    redis-cli ping >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Не удалось запустить Redis. Проверьте установку Redis."
        exit 1
    fi
    echo "Redis успешно запущен."
else
    echo "Redis сервер уже запущен."
fi

# Создаем тестовую блокировку
echo "Тестирование Redis блокировки..."
python -c "from redis_lock import RedisLock; lock = RedisLock(redis_url='redis://localhost:6379/0'); print(f'Redis подключение: {lock.connect()}'); print(f'Тестовая блокировка: {lock.acquire() and lock.release()}')"

echo
echo "Добавьте следующую строку в .env файл для использования Redis блокировки:"
echo "REDIS_URL=redis://localhost:6379/0"
echo
echo "Для облачных сервисов используйте предоставленный URL, например:"
echo "REDIS_URL=redis://default:password@redis-12345.c12345.region.cloud.redislabs.com:12345"
