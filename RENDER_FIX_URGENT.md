# Срочное исправление проблемы с aiohttp на Render.com

## Проблема

Сборка `aiohttp` на Render.com продолжает использовать Python 3.13, несмотря на указание в файле `runtime.txt` использовать Python 3.11. Это приводит к ошибкам при компиляции C-расширений из-за несовместимости с внутренними API Python 3.13.

## Окончательное решение

1. **Обновление render.yaml с прямой ссылкой на wheel-файл:**

```yaml
services:
  # Фоновый сервис для Telegram бота
  - type: worker
    name: dostup-bot
    runtime: python
    # Принудительно используем Python 3.11 и устанавливаем предкомпилированный aiohttp
    buildCommand: >
      echo "Python version:" && python --version &&
      pip install wheel setuptools &&
      # Устанавливаем конкретную версию aiohttp напрямую из готового wheel-файла
      pip install https://files.pythonhosted.org/packages/6f/d0/a769f6d0a0328fee7dc453913bd1ef57e13944e45b0edb726175263fcd75/aiohttp-3.8.6-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl &&
      pip install -r app/requirements-render.txt
    startCommand: python start.py
```

2. **Проверка файла runtime.txt:**
```
python-3.11.8
```

3. **Переключение на Docker deployment:**

Если прямая установка wheel-файла не поможет, переключите сервис на Docker deployment используя существующий Dockerfile:

```yaml
services:
  - type: web
    name: dostup-bot
    runtime: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: BOT_TOKEN
        sync: false
      # ... другие переменные окружения
```

## Причины проблемы

Render.com, вероятно, игнорирует файл `runtime.txt` для воркеров, либо не применяет его до запуска `buildCommand`. По этой причине мы вынуждены использовать прямую ссылку на уже собранный wheel-файл для Python 3.11.

## Шаги для применения исправления

1. Обновите `render.yaml` с новой конфигурацией
2. Убедитесь, что `app/requirements-render.txt` не содержит упоминания `aiohttp`
3. Загрузите изменения на GitHub
4. Запустите ручной деплой на Render.com

## Если ничего не помогает

Используйте Docker deployment, который полностью изолирует ваше окружение от настроек Render.com.
