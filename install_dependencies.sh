#!/bin/bash
# Скрипт для установки зависимостей на Render.com
# Решает проблему с установкой aiohttp на Python 3.13

# Вывод информации о текущем окружении
echo "===== Информация об окружении ====="
python --version
pip --version

# Установка необходимых системных зависимостей
echo "===== Установка системных зависимостей ====="
apt-get update && apt-get install -y python3-dev build-essential

# Обновление pip и установка инструментов сборки
echo "===== Обновление pip и инструментов сборки ====="
pip install --upgrade pip
pip install wheel setuptools

# Установка aiohttp из бинарного пакета (обход проблемы компиляции)
echo "===== Установка aiohttp из бинарного пакета ====="
pip install --only-binary :all: aiohttp==3.8.5

# Два альтернативных метода установки aiohttp, если первый не сработал
# Раскомментируйте один из них при необходимости
#pip install https://files.pythonhosted.org/packages/6f/d0/a769f6d0a0328fee7dc453913bd1ef57e13944e45b0edb726175263fcd75/aiohttp-3.8.6-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
#pip install --no-deps aiohttp==3.8.5

# Установка остальных зависимостей
echo "===== Установка остальных зависимостей ====="
pip install -r app/requirements-render.txt

# Проверка успешности установки
echo "===== Проверка установки ====="
pip list | grep aiohttp
pip list | grep aiogram

echo "===== Установка завершена ====="
