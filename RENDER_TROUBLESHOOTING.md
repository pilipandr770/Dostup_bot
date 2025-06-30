# Инструкция по деплою на Render.com

## Исправление ошибки сборки aiohttp

Если вы столкнулись с ошибкой сборки aiohttp при деплое на Render.com, следуйте этим инструкциям:

1. **Укажите версию Python 3.11**
   
   Я создал файл `runtime.txt` в корне проекта, который указывает Render использовать Python 3.11 вместо более нового Python 3.13, вызывающего проблемы совместимости с aiohttp.

2. **Используйте предкомпилированные пакеты**
   
   В `render.yaml` добавлена специальная команда сборки, которая устанавливает aiohttp из бинарного пакета вместо сборки из исходников:
   
   ```yaml
   buildCommand: >
     pip install wheel && 
     pip install --only-binary :all: aiohttp==3.8.5 && 
     pip install -r app/requirements.txt
   ```

3. **Создайте отдельный файл requirements-render.txt**

   Создайте файл `app/requirements-render.txt`, который исключает aiohttp из основного списка зависимостей:
   
   ```
   # Все зависимости, кроме aiohttp, который будет установлен отдельно
   # из бинарных пакетов
   # Остальные зависимости из requirements.txt
   ```

   И измените команду сборки в render.yaml:
   
   ```yaml
   buildCommand: >
     pip install wheel && 
     pip install --only-binary :all: aiohttp==3.8.5 && 
     pip install -r app/requirements-render.txt
   ```
   
4. **Альтернативный метод установки**

   Если основной способ не работает, можно использовать созданный скрипт `install_dependencies.sh`.

## Решение проблемы с Python 3.13 и aiohttp

Ошибка, которую вы видите, связана с несовместимостью aiohttp с Python 3.13. В логах видны следующие проблемы:

1. **Устаревшие API в Python 3.13**:
   - `Py_UNICODE` устарел
   - `Py_OptimizeFlag` устарел
   - `ma_version_tag` устарел

2. **Изменения в структуре `PyLongObject`**:
   - Ошибки типа `'PyLongObject' не имеет члена с именем 'ob_digit'`
   - Изменения в функции `_PyLong_AsByteArray`

### Решения проблемы:

1. **Принудительное использование Python 3.11** (рекомендуется):
   
   Проверьте, что файл `runtime.txt` в корне проекта содержит:
   ```
   python-3.11
   ```

2. **Использование предсобранного колеса aiohttp**:
   
   Создайте файл `app/requirements-render.txt` без aiohttp, и измените `render.yaml`:
   
   ```yaml
   buildCommand: >
     pip install wheel &&
     pip install --only-binary :all: aiohttp==3.8.5 &&
     pip install -r app/requirements-render.txt
   ```

3. **Установка через скрипт**:
   
   Создайте `install_dependencies.sh` с содержимым:
   
   ```bash
   #!/bin/bash
   
   # Установка инструментов сборки
   pip install wheel setuptools
   
   # Установка aiohttp из бинарного пакета
   pip install --only-binary :all: aiohttp==3.8.5
   
   # Установка остальных зависимостей
   pip install -r app/requirements-render.txt
   ```
   
   И обновите `render.yaml`:
   ```yaml
   buildCommand: bash install_dependencies.sh
   ```

## Шаги для исправления и деплоя

1. **Загрузите изменения в GitHub:**
   ```bash
   git add runtime.txt
   git add app/requirements.txt
   git add app/requirements-render.txt
   git add render.yaml
   git add start.py
   git add RENDER_DEPLOY.md
   git add install_dependencies.sh
   git commit -m "Fix aiohttp build issues on Render"
   git push
   ```

2. **Создайте новый сервис на Render:**
   - Откройте dashboard Render.com
   - Выберите "New" -> "Blueprint"
   - Подключите GitHub репозиторий
   - Следуйте инструкциям для создания сервиса

3. **Укажите все переменные окружения:**
   - Все переменные из вашего локального файла .env нужно добавить через интерфейс Render
   - Особенно важны: BOT_TOKEN, COURSE_CHANNEL_ID, YOUTUBE_CHANNEL_URL, CHANNEL_INVITE_LINK, ADMIN_USER_ID

4. **Диск для хранения данных:**
   - В конфигурации уже указан диск для хранения базы данных и логов
   - Это позволит системе напоминаний работать между перезапусками

## Мониторинг

После успешного деплоя вы можете мониторить работу бота:
- В разделе "Logs" вашего сервиса на Render
- С помощью команды `/reminders` в боте (доступна администратору)

## Если ошибка всё равно появляется

Если проблема с aiohttp сохраняется:
1. Посмотрите последние логи сборки на Render
2. Попробуйте добавить строку `--no-binary aiohttp` в опции pip в файле render.yaml:

```yaml
buildCommand: pip install --no-binary aiohttp -r app/requirements.txt
```

Это заставит pip собирать aiohttp из исходников, что может решить проблему с несовместимостью версий.
