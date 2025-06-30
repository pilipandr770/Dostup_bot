# Деплой бота на Render.com через Docker

После нескольких попыток решить проблему с совместимостью aiohttp и Python 3.13, мы переключаемся на деплой через Docker, который дает полный контроль над окружением.

## Преимущества использования Docker

1. **Полная изоляция окружения** - мы точно контролируем версию Python (3.11)
2. **Отсутствие проблем с компиляцией** - все зависимости устанавливаются в контролируемой среде
3. **Одинаковое окружение локально и на сервере** - устраняет проблемы "у меня работает"
4. **Простое масштабирование** - при необходимости легко перенести на другую платформу

## Настройка Render.yaml для Docker

```yaml
services:
  - type: web
    name: dostup-bot
    runtime: docker
    dockerfilePath: ./Dockerfile
    plan: free
    autoDeploy: true
    envVars:
      - key: BOT_TOKEN
        sync: false
      # ... другие переменные окружения
    disk:
      name: bot-data
      mountPath: /app
      sizeGB: 1
```

## Что изменилось в настройке

1. **runtime: docker** вместо python - использует Docker для запуска бота
2. **dockerfilePath: ./Dockerfile** - путь к файлу Dockerfile
3. **type: web** вместо worker - Render требует тип web для Docker-сервисов

## Dockerfile

Вот обновленный Dockerfile с учетом всех исправлений:

```dockerfile
# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY app/requirements.txt .

# Install Python dependencies - важно! Сначала устанавливаем aiohttp из бинарных пакетов
RUN pip install wheel && \
    pip install --only-binary :all: aiohttp==3.8.5 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .
COPY start.py ../start.py

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Command to run the application using start.py
CMD ["python", "../start.py"]
```

## Переменные окружения

Все переменные окружения настраиваются в Render Dashboard и передаются в Docker-контейнер автоматически.

## Хранение данных

Persistent disk в Render подключается к контейнеру по указанному пути (`/app`), что позволяет сохранять данные между перезапусками.

## Как деплоить

### Подготовка файлов

1. **Проверьте настройку Dockerfile:**
   - Убедитесь, что он использует Python 3.11
   - Убедитесь, что aiohttp устанавливается из бинарных пакетов
   - Проверьте, что start.py копируется правильно

2. **Проверьте настройку render.yaml:**
   - Тип должен быть `web` (не `worker`)
   - Должен использовать `runtime: docker`
   - Должен указывать правильный путь к Dockerfile

3. **Загрузите изменения в GitHub:**
   ```bash
   git add render.yaml Dockerfile start.py RENDER_DOCKER_DEPLOY.md
   git commit -m "Switch to Docker deployment on Render to fix aiohttp issues"
   git push
   ```

### Настройка на Render.com

1. **Удалите предыдущую версию сервиса:**
   - Перейдите в Render Dashboard
   - Выберите текущий сервис
   - Нажмите "Settings" > "Delete Service"
   - Подтвердите удаление

2. **Создайте новый сервис на Render:**
   - Выберите "New" > "Web Service"
   - Подключите ваш GitHub репозиторий
   - На странице настройки:
     - Выберите "Docker" в разделе Runtime
     - Укажите корректное имя сервиса

3. **Укажите все переменные окружения:**
   - BOT_TOKEN
   - COURSE_CHANNEL_ID
   - YOUTUBE_CHANNEL_URL
   - CHANNEL_INVITE_LINK
   - OPENAI_API_KEY
   - OPENAI_ASSISTANT_ID
   - STRIPE_PAYMENT_URL
   - ADMIN_USER_ID
   - STRIPE_API_KEY

4. **Настройте постоянный диск:**
   - В разделе "Disks" создайте новый диск
   - Укажите путь монтирования `/app`
   - Размер 1GB

### Проверка деплоя

После завершения сборки и запуска:
1. Проверьте логи на наличие ошибок
2. Отправьте боту команду `/start` или `/help`
3. Убедитесь, что система напоминаний работает через `/reminders` (для админа)

## Мониторинг и логи

После деплоя вы можете мониторить работу бота в разделе "Logs" в Render Dashboard.

## Важно! Проблема с Python 3.13 на Render

Мы продолжаем видеть ошибки сборки aiohttp на Render из-за того, что:

1. **Render игнорирует runtime.txt** для воркеров и всегда использует Python 3.13
2. **Сборка aiohttp из исходников не работает** с Python 3.13 из-за изменений в C API
3. **Предустановка бинарных пакетов не решает проблему** для сервисов типа worker

### Почему Docker решает проблему:

1. Docker использует образ Python 3.11, изолированный от системы Render
2. Все зависимости устанавливаются внутри контейнера, без взаимодействия с Python 3.13
3. Собранный контейнер запускается как есть, без дополнительной сборки на Render

## Альтернативные платформы для деплоя Docker образа

Если у вас уже готов работающий Docker образ, вы можете развернуть его на следующих платформах:

### 1. DigitalOcean App Platform
- Простая интеграция с GitHub
- Поддержка Docker из коробки
- Бесплатный тир для маленьких проектов
- Масштабируемость при необходимости

### 2. Heroku
- Простой интерфейс
- Поддержка Docker через Heroku Container Registry
- Хорошо документированный процесс деплоя
- Команда: `heroku container:push web && heroku container:release web`

### 3. Railway.app
- Современный интерфейс
- Очень простой процесс деплоя Docker образов
- Интеграция с GitHub
- Хороший бесплатный тир

### 4. Google Cloud Run
- Бессерверный запуск Docker контейнеров
- Оплата только за время выполнения
- Высокая масштабируемость
- Бесплатный тир (2 миллиона запросов в месяц)

#### Пошаговая инструкция для деплоя на Google Cloud Run

1. **Установите и настройте Google Cloud SDK**:
   - Скачайте и установите [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
   - Авторизуйтесь: `gcloud auth login`
   - Создайте новый проект или выберите существующий: 
     ```powershell
     # Создание нового проекта
     gcloud projects create YOUR_PROJECT_ID --name "Dostup Bot"
     
     # Выбор существующего проекта
     gcloud config set project YOUR_PROJECT_ID
     ```

2. **Активируйте необходимые API**:
   ```powershell
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   ```

3. **Подготовьте Docker образ**:
   - Создайте файл `.dockerignore` для исключения ненужных файлов
   - Убедитесь, что Dockerfile корректно настроен

4. **Соберите и отправьте образ в Container Registry**:
   ```powershell
   # Настройте Docker для использования gcloud в качестве аутентификатора
   gcloud auth configure-docker
   
   # Соберите образ с тегом для Google Container Registry
   docker build -t gcr.io/YOUR_PROJECT_ID/dostup-bot .
   
   # Отправьте образ в Container Registry
   docker push gcr.io/YOUR_PROJECT_ID/dostup-bot
   ```

5. **Разверните сервис на Cloud Run**:
   ```powershell
   gcloud run deploy dostup-bot \
     --image gcr.io/YOUR_PROJECT_ID/dostup-bot \
     --platform managed \
     --region europe-west1 \
     --allow-unauthenticated \
     --memory 512Mi \
     --cpu 1 \
     --max-instances 1
   ```

6. **Настройте переменные окружения** (можно добавить все сразу через флаги):
   ```powershell
   gcloud run services update dostup-bot \
     --set-env-vars="BOT_TOKEN=your_token,COURSE_CHANNEL_ID=your_channel_id,ADMIN_USER_ID=your_admin_id" \
     --region europe-west1
   ```

7. **Настройте постоянное хранилище**:
   - Cloud Run не поддерживает постоянные тома напрямую
   - Рекомендуемые варианты:
     - Google Cloud Storage для файлов
     - Cloud SQL для баз данных
     - Firestore для NoSQL данных

   Пример подключения к Cloud Storage:
   ```python
   from google.cloud import storage
   
   storage_client = storage.Client()
   bucket = storage_client.bucket('your-bucket-name')
   blob = bucket.blob('path/to/your/file')
   
   # Загрузить данные
   blob.upload_from_filename('local-file.txt')
   
   # Скачать данные
   blob.download_to_filename('local-file.txt')
   ```

8. **Проверьте работоспособность**:
   - После деплоя вы получите URL вашего сервиса
   - Telegram бот не требует доступа к этому URL, но можно добавить веб-интерфейс
   - Проверьте логи: `gcloud beta run services logs read dostup-bot --region europe-west1`

#### Решение проблемы "Image not found"

Если вы видите ошибку `Изображение 'gcr.io/YOUR_PROJECT_ID/dostup-bot:latest' не найдено`:

1. **Проверьте имя проекта**:
   ```powershell
   gcloud config get-value project
   ```
   
2. **Убедитесь, что образ был правильно загружен**:
   ```powershell
   gcloud container images list --repository=gcr.io/YOUR_PROJECT_ID
   ```
   
3. **Проверьте права доступа**:
   - Убедитесь, что сервисный аккаунт Cloud Run имеет роль `Storage Object Viewer`
   ```powershell
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member=serviceAccount:service-PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com \
     --role=roles/storage.objectViewer
   ```

4. **Если проблема не решается**, используйте Artifact Registry вместо Container Registry:
   ```powershell
   # Активировать API
   gcloud services enable artifactregistry.googleapis.com
   
   # Создать репозиторий
   gcloud artifacts repositories create dostup-bot-repo \
     --repository-format=docker \
     --location=europe-west1
   
   # Настроить Docker
   gcloud auth configure-docker europe-west1-docker.pkg.dev
   
   # Соберите и отправьте образ
   docker build -t europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/dostup-bot-repo/dostup-bot .
   docker push europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/dostup-bot-repo/dostup-bot
   
   # Деплой с новым путем к образу
   gcloud run deploy dostup-bot \
     --image europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/dostup-bot-repo/dostup-bot \
     --platform managed \
     --region europe-west1
   ```

### 5. AWS ECS (Elastic Container Service)
- Полный контроль над инфраструктурой
- Интеграция с другими сервисами AWS
- Высокая надежность
- Fargate для запуска без управления серверами

### 6. VPS с Docker
- Полный контроль над средой
- Linode, DigitalOcean, Vultr предлагают недорогие VPS
- Команды: `docker build -t dostup-bot .` и `docker run -d dostup-bot`
- Возможность запуска через docker-compose

## Процесс деплоя Docker образа (общие шаги)

1. **Сборка образа локально**:
   ```bash
   docker build -t dostup-bot .
   ```

2. **Проверка работоспособности**:
   ```bash
   docker run -p 8000:8000 --env-file .env dostup-bot
   ```

3. **Публикация в Docker Hub** (опционально):
   ```bash
   docker tag dostup-bot yourusername/dostup-bot
   docker push yourusername/dostup-bot
   ```

4. **Деплой на выбранную платформу** с использованием их инструкций для Docker контейнеров

## Известные ограничения

При использовании бесплатного тарифа Render:
- Сервис будет "засыпать" после 15 минут неактивности
- Есть ограничения на время работы CPU
- Docker-контейнеры потребляют больше ресурсов и могут быстрее достигать лимитов
