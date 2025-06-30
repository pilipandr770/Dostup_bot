# Деплой Telegram бота на Google Cloud Run

Google Cloud Run - это бессерверная вычислительная платформа, которая позволяет запускать контейнеры без необходимости управлять серверами. Это отличный выбор для размещения Telegram ботов благодаря:

- Оплате только за реально используемое время
- Высокой производительности и масштабируемости
- Щедрому бесплатному тиру (2 миллиона запросов в месяц)
- Отсутствию "засыпания" контейнеров (в отличие от бесплатного плана Render)

## Подготовка к деплою

### 1. Создание аккаунта и проекта

1. **Создайте аккаунт Google Cloud**:
   - Перейдите на [console.cloud.google.com](https://console.cloud.google.com/)
   - Зарегистрируйтесь или войдите в существующий аккаунт
   - Новые пользователи получают $300 кредитов на 90 дней

2. **Создайте новый проект**:
   - В консоли нажмите на селектор проектов вверху страницы
   - Выберите "New Project"
   - Укажите имя проекта (например, "dostup-bot")
   - Нажмите "Create"

### 2. Установка Google Cloud SDK

Установите Google Cloud SDK для управления сервисами из командной строки:

#### Windows:
1. Скачайте установщик с [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
2. Запустите скачанный файл (GoogleCloudSDKInstaller.exe)
3. Следуйте инструкциям установщика:
   - Выберите "Установить для всех пользователей" или "Установить только для текущего пользователя"
   - Оставьте галочки для всех компонентов (gcloud CLI, kubectl, etc.)
   - Включите опцию "Добавить в PATH" для удобного доступа из командной строки
4. После завершения установки **откройте новое окно** PowerShell или командной строки
5. Инициализируйте SDK:
   ```powershell
   gcloud init
   ```
6. Следуйте инструкциям, чтобы войти в аккаунт Google и выбрать проект

#### macOS/Linux:
```bash
# Установите gcloud через пакетный менеджер Homebrew
brew install --cask google-cloud-sdk

# Инициализируйте SDK
gcloud init
```

### 3. Активация необходимых API

```powershell
# Активация Cloud Run
gcloud services enable run.googleapis.com

# Активация Container Registry (для хранения Docker образов)
gcloud services enable containerregistry.googleapis.com

# Активация Cloud Build (для сборки Docker образов в облаке)
gcloud services enable cloudbuild.googleapis.com
```

## Настройка Docker образа

### 1. Проверка Dockerfile

Убедитесь, что ваш Dockerfile корректно настроен для работы с Google Cloud Run:
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
COPY cloud_run_adapter.py ../cloud_run_adapter.py

# Create directory for modules in Python path
RUN mkdir -p /usr/local/lib/python3.11/site-packages/app
COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/app/
COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port 8080 for Cloud Run health checks
EXPOSE 8080

# Command to run the application using start.py
CMD ["python", "../start.py"]
```

### 2. Подготовка .dockerignore

Создайте файл `.dockerignore`, чтобы исключить ненужные файлы из контекста сборки:

```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg
.env
.git
.gitignore
*.md
```

## Деплой на Google Cloud Run

### Вариант 1: Деплой через Google Cloud Console (веб-интерфейс)

1. **Загрузите Docker образ в Container Registry**:
   ```powershell
   # Настройте Docker для работы с Google Container Registry
   gcloud auth configure-docker

   # Соберите образ с тегом для GCR
   docker build -t gcr.io/YOUR_PROJECT_ID/dostup-bot .

   # Отправьте образ в Container Registry
   docker push gcr.io/YOUR_PROJECT_ID/dostup-bot
   ```

2. **Создайте сервис Cloud Run через консоль**:
   - Перейдите в [console.cloud.google.com](https://console.cloud.google.com/)
   - Выберите "Cloud Run" в меню слева
   - Нажмите "Create Service"
   - В поле "Container image URL" укажите `gcr.io/YOUR_PROJECT_ID/dostup-bot`
   - Укажите имя сервиса (например, "dostup-bot")
   - Настройте CPU, память и масштабирование (для бота обычно достаточно минимальных значений)
   - Добавьте все переменные окружения в разделе "Variables & Secrets"
   - Нажмите "Create"

### Вариант 2: Деплой через командную строку (рекомендуется)

#### Для PowerShell (Windows):

```powershell
# Получите ID проекта
$PROJECT_ID = gcloud config get-value project

# Соберите и отправьте образ в Container Registry
gcloud auth configure-docker
docker build -t gcr.io/$PROJECT_ID/dostup-bot .
docker push gcr.io/$PROJECT_ID/dostup-bot

# Разверните сервис на Cloud Run (используйте обратный апостроф ` для переноса строк в PowerShell)
gcloud run deploy dostup-bot `
  --image gcr.io/$PROJECT_ID/dostup-bot `
  --platform managed `
  --region europe-west1 `
  --allow-unauthenticated `
  --memory 512Mi `
  --cpu 1 `
  --max-instances 1 `
  --port 8080

# Настройте переменные окружения - ВАЖНО! Используйте реальные значения, а не заполнители
gcloud run services update dostup-bot `
  --set-env-vars="BOT_TOKEN=your_real_bot_token,COURSE_CHANNEL_ID=your_real_channel_id,ADMIN_USER_ID=your_real_admin_id" `
  --region europe-west1
```

#### Для Bash (Linux/Mac):

```bash
# Получите ID проекта
PROJECT_ID=$(gcloud config get-value project)

# Соберите и отправьте образ в Container Registry
gcloud auth configure-docker
docker build -t gcr.io/$PROJECT_ID/dostup-bot .
docker push gcr.io/$PROJECT_ID/dostup-bot

# Разверните сервис на Cloud Run
gcloud run deploy dostup-bot \
  --image gcr.io/$PROJECT_ID/dostup-bot \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 1 \
  --port 8080

# Настройте переменные окружения - ВАЖНО! Используйте реальные значения, а не заполнители
gcloud run services update dostup-bot \
  --set-env-vars="BOT_TOKEN=your_real_bot_token,COURSE_CHANNEL_ID=your_real_channel_id,ADMIN_USER_ID=your_real_admin_id" \
  --region europe-west1
```

## Важные особенности деплоя на Google Cloud Run

### 1. HTTP сервер на порту 8080

Google Cloud Run требует, чтобы контейнер запускал HTTP-сервер на порту 8080 и отвечал на проверки работоспособности. Для этого мы используем специальный адаптер `cloud_run_adapter.py`, который запускает простой HTTP-сервер параллельно с ботом.

### 2. Правильные переменные окружения

При деплое бота необходимо указать действительные значения переменных окружения:
- `BOT_TOKEN` - токен вашего Telegram бота
- `COURSE_CHANNEL_ID` - ID канала с курсом (с минусом для публичных каналов)
- `ADMIN_USER_ID` - числовой ID администратора бота

**ВНИМАНИЕ**: Переменная `ADMIN_USER_ID` должна содержать числовое значение, а не текстовую заглушку.

## Решение проблемы "Image not found"

Если вы видите ошибку `Изображение 'gcr.io/YOUR_PROJECT_ID/dostup-bot:latest' не найдено`:

### 1. Проверьте ID вашего проекта

```powershell
# Посмотрите текущий проект
gcloud config get-value project

# Если нужно, установите правильный проект
gcloud config set project YOUR_PROJECT_ID
```

### 2. Проверьте, что образ был загружен в Container Registry

```powershell
# Просмотр списка образов
gcloud container images list --repository=gcr.io/YOUR_PROJECT_ID

# Проверка тегов конкретного образа
gcloud container images list-tags gcr.io/YOUR_PROJECT_ID/dostup-bot
```

### 3. Проверьте права доступа

#### Для PowerShell (Windows):

```powershell
# Получите номер вашего проекта
$PROJECT_NUMBER = $(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Предоставьте сервисному аккаунту Cloud Run доступ к Container Registry
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:service-$PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com" `
  --role="roles/storage.objectViewer"
```

#### Для Bash (Linux/Mac):

```bash
# Получите номер вашего проекта
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Предоставьте сервисному аккаунту Cloud Run доступ к Container Registry
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:service-$PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com \
  --role=roles/storage.objectViewer
```

## Решение проблемы с импортом модулей

Если возникает ошибка `ModuleNotFoundError: No module named 'reminder_system'`, это может быть связано с неправильным путем импорта Python-модулей. В Dockerfile добавлена копия модуля в sys.path:

```dockerfile
# Create directory for modules in Python path
RUN mkdir -p /usr/local/lib/python3.11/site-packages/app
COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/app/
COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/
```

### 4. Используйте Artifact Registry вместо Container Registry

Google рекомендует использовать Artifact Registry вместо устаревающего Container Registry:

#### Для PowerShell (Windows):

```powershell
# Получите ID проекта
$PROJECT_ID = gcloud config get-value project

# Активировать API
gcloud services enable artifactregistry.googleapis.com

# Создать репозиторий
gcloud artifacts repositories create dostup-bot-repo `
  --repository-format=docker `
  --location=europe-west1 `
  --description="Docker repository for Dostup Bot"

# Настроить Docker
gcloud auth configure-docker europe-west1-docker.pkg.dev

# Собрать и отправить образ
docker build -t europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot .
docker push europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot

# Деплой с новым путем к образу
gcloud run deploy dostup-bot `
  --image europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot `
  --platform managed `
  --region europe-west1 `
  --allow-unauthenticated
```

#### Для Bash (Linux/Mac):

```bash
# Получите ID проекта
PROJECT_ID=$(gcloud config get-value project)

# Активировать API
gcloud services enable artifactregistry.googleapis.com

# Создать репозиторий
gcloud artifacts repositories create dostup-bot-repo \
  --repository-format=docker \
  --location=europe-west1 \
  --description="Docker repository for Dostup Bot"

# Настроить Docker
gcloud auth configure-docker europe-west1-docker.pkg.dev

# Собрать и отправить образ
docker build -t europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot .
docker push europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot

# Деплой с новым путем к образу
gcloud run deploy dostup-bot \
  --image europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated
```

## Управление постоянными данными

Cloud Run не поддерживает постоянные тома напрямую, но есть несколько вариантов для хранения данных:

### 1. Google Cloud Storage для файлов

```powershell
# Создание бакета
gcloud storage buckets create gs://YOUR_PROJECT_ID-bot-data --location=europe-west1

# Установка прав доступа
gcloud storage buckets add-iam-policy-binding gs://YOUR_PROJECT_ID-bot-data \
  --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/storage.objectAdmin
```

В коде Python:
```python
from google.cloud import storage

def save_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """Загрузить файл в Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Скачать файл из Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
```

### 2. Cloud Firestore для NoSQL данных

```powershell
# Активация Firestore
gcloud services enable firestore.googleapis.com

# Создание коллекции и документа через Python
```

В коде Python:
```python
from google.cloud import firestore

# Инициализация клиента
db = firestore.Client()

# Добавление данных
doc_ref = db.collection('users').document('user_id')
doc_ref.set({
    'name': 'John',
    'email': 'john@example.com'
})

# Чтение данных
user_ref = db.collection('users').document('user_id')
user = user_ref.get()
if user.exists:
    print(user.to_dict())
```

### 3. Cloud SQL для реляционных баз данных

```powershell
# Активация Cloud SQL
gcloud services enable sqladmin.googleapis.com

# Создание экземпляра PostgreSQL
gcloud sql instances create dostup-bot-db \
  --database-version=POSTGRES_13 \
  --tier=db-f1-micro \
  --region=europe-west1

# Создание базы данных
gcloud sql databases create bot_data --instance=dostup-bot-db

# Создание пользователя
gcloud sql users create botuser \
  --instance=dostup-bot-db \
  --password=YOUR_SECURE_PASSWORD
```

В коде Python (с SQLAlchemy):
```python
import os
import sqlalchemy

# Подключение к базе данных
db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
db_host = os.environ.get("DB_HOST")

db = sqlalchemy.create_engine(
    sqlalchemy.engine.url.URL(
        drivername="postgresql",
        username=db_user,
        password=db_pass,
        database=db_name,
        host=db_host,
    ),
)
```

## Решение проблем с Telegram API

### Ошибка "Unauthorized" в логах

Если ваш бот успешно запускается, но в логах вы видите ошибку `aiogram.utils.exceptions.Unauthorized: Unauthorized`, это означает, что бот не может авторизоваться в API Telegram. Возможные причины:

1. **Недействительный токен бота**:
   - Токен мог быть аннулирован или изменен
   - В переменной окружения указан неверный токен
   - Токен содержит лишние пробелы или символы

2. **Обновление токена бота**:
   ```powershell
   # Проверьте текущее значение токена
   gcloud run services describe dostup-bot --region=europe-west1 | Select-String "BOT_TOKEN"
   
   # Обновите токен бота
   gcloud run services update dostup-bot `
     --set-env-vars="BOT_TOKEN=ваш_новый_токен" `
     --region=europe-west1
   ```

3. **Проверка токена бота**:
   - Откройте в браузере `https://api.telegram.org/bot<ваш_токен>/getMe`
   - Если токен верный, вы увидите JSON-ответ с информацией о боте
   - Если токен неверный, вы увидите сообщение об ошибке

4. **Получение нового токена**:
   - Если ваш токен перестал работать, создайте нового бота через @BotFather
   - Получите новый токен и обновите его в Cloud Run

Важно: после обновления переменных окружения Google Cloud Run автоматически перезапустит сервис с новыми значениями.

### Мониторинг работы бота

Для проверки работы бота даже при наличии некритичных ошибок в логах:

1. **Проверка статуса сервиса**:
   ```powershell
   # Проверка общего статуса сервиса
   gcloud run services describe dostup-bot --region=europe-west1 --format="value(status.conditions[0].status,status.conditions[0].type)"
   
   # Если результат "TrueReady", сервис запущен и готов к работе
   ```

2. **Отправка тестового сообщения боту** через Telegram, чтобы убедиться, что он отвечает

3. **Просмотр логов в реальном времени**:
   ```powershell
   # Просмотр логов в режиме реального времени
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --tail
   ```

## Мониторинг и логи

### 1. Просмотр логов

```powershell
# Просмотр последних логов
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=20

# Потоковый вывод логов
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --tail

# Более удобный способ (если доступен beta компонент)
gcloud beta run services logs read dostup-bot --region=europe-west1
```

### 2. Настройка алертов

Для получения уведомлений о проблемах:
1. Перейдите в "Monitoring" > "Alerting"
2. Создайте политику оповещений на основе логов ошибок или метрик использования

### 3. Мониторинг использования ресурсов

- Перейдите в "Cloud Run" > Выберите ваш сервис > "Metrics"
- Отслеживайте CPU, память, количество запросов и т.д.

## Оптимизация стоимости

1. **Настройте параметры масштабирования**:
   ```powershell
   gcloud run services update dostup-bot \
     --min-instances=0 \
     --max-instances=1 \
     --region=europe-west1
   ```

2. **Уменьшите выделенные ресурсы**:
   ```powershell
   gcloud run services update dostup-bot \
     --memory=256Mi \
     --cpu=1 \
     --region=europe-west1
   ```

3. **Используйте Cloud Run за пределами бесплатного тира**:
   - 2 миллиона запросов в месяц бесплатно
   - $0.40 за миллион запросов сверх лимита
   - $0.00002400 за ГБ-секунду памяти
   - $0.00001000 за CPU-секунду

## Полезные команды для управления сервисом

```powershell
# Посмотреть информацию о сервисе
gcloud run services describe dostup-bot --region=europe-west1

# Обновить сервис
gcloud run services update dostup-bot --image=gcr.io/YOUR_PROJECT_ID/dostup-bot:latest --region=europe-west1

# Удалить сервис
gcloud run services delete dostup-bot --region=europe-west1

# Получить URL сервиса
gcloud run services describe dostup-bot --format="value(status.url)" --region=europe-west1
```

## Настройка домена (опционально)

Если вы хотите использовать собственный домен:

1. **Добавьте домен в Cloud Run**:
   ```powershell
   gcloud beta run domain-mappings create --service=dostup-bot --domain=your-domain.com --region=europe-west1
   ```

2. **Настройте DNS-записи** согласно инструкциям, которые предоставит команда

## Итоги успешного деплоя

После выполнения всех указанных шагов ваш Telegram бот должен успешно работать на Google Cloud Run. Вот что мы сделали:

1. **Настроили Docker-образ** с правильной структурой файлов и путями импорта Python-модулей
2. **Добавили Cloud Run адаптер** для обеспечения HTTP-проверок работоспособности на порту 8080
3. **Загрузили образ** в Google Container Registry
4. **Развернули сервис** в Cloud Run с нужными параметрами и переменными окружения
5. **Настроили масштабирование и ресурсы** для оптимальной работы

### Текущий URL сервиса
Ваш сервис доступен по URL, который можно получить с помощью команды:
```powershell
gcloud run services describe dostup-bot --format="value(status.url)" --region=europe-west1
```

### Следующие шаги

1. **Настройка постоянного хранилища** для данных бота:
   - Cloud Storage для файлов
   - Firestore для NoSQL данных
   - Cloud SQL для реляционной базы данных

2. **Настройка мониторинга и оповещений** для отслеживания работы бота:
   - Создание алертов при возникновении ошибок
   - Настройка панели мониторинга для отслеживания производительности

3. **Оптимизация расходов**:
   - Установка лимитов на масштабирование
   - Уменьшение выделенных ресурсов до необходимого минимума

4. **Безопасность**:
   - Использование Secret Manager для хранения конфиденциальных данных
   - Регулярное обновление образа и зависимостей

### Преимущества Google Cloud Run

- **Нет "засыпания" контейнера** в отличие от бесплатного плана Render
- **Платите только за фактическое использование** ресурсов
- **Масштабирование до нуля** — не платите, когда бот не используется
- **Автоматическое масштабирование** при необходимости
- **Интеграция с другими сервисами** Google Cloud

С этой настройкой ваш бот будет работать надежно и эффективно, а вы сможете сосредоточиться на разработке его функциональности, не беспокоясь об инфраструктуре.

## Устранение неполадок и анализ логов

При развертывании сервисов на Google Cloud Run могут возникать различные ошибки. Правильное чтение и интерпретация логов поможет быстро выявить и устранить проблемы.

### 1. Анализ ошибок в аудит-логах

Аудит-логи Google Cloud Run содержат информацию о всех операциях с вашим сервисом. Особое внимание стоит обратить на записи с пометкой "Error detected":

```
NOTICE 2025-06-29T10:32:59.229153274Z Error detected in dostup-bot version dostup-bot-00001-fqb
```

Такие записи указывают на проблемы с конкретной версией вашего сервиса. Для получения более подробной информации об ошибке:

#### Для PowerShell (Windows):

```powershell
# Получить подробные логи для указанной версии сервиса
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb" --limit=50

# Получить только сообщения об ошибках
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND severity>=ERROR" --limit=20
```

#### Для Bash (Linux/Mac):

```bash
# Получить подробные логи для указанной версии сервиса
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb" --limit=50

# Получить только сообщения об ошибках
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND severity>=ERROR" --limit=20
```

### 2. Проверка статуса развертывания сервиса

Чтобы узнать текущий статус сервиса и его версий:

```powershell
# Получить общую информацию о сервисе
gcloud run services describe dostup-bot --region=europe-west1

# Получить список всех версий (ревизий) сервиса
gcloud run revisions list --service=dostup-bot --region=europe-west1
```

### 3. Общие причины ошибок и их решения

#### Ошибка запуска контейнера

Если контейнер не может запуститься, проверьте:

1. **Правильность переменных окружения**:
   ```powershell
   # Проверьте текущие переменные окружения
   gcloud run services describe dostup-bot --region=europe-west1 --format="yaml(spec.template.spec.containers[0].env)"
   
   # Обновите переменные с правильными значениями (без кавычек для числовых значений)
   gcloud run services update dostup-bot --region=europe-west1 --set-env-vars=ADMIN_USER_ID=123456789,BOT_TOKEN=5555:your-actual-token
   ```

2. **Проблемы с импортом модулей**:
   - Проверьте структуру файлов в контейнере
   - Убедитесь, что все зависимости установлены в Dockerfile

#### Ошибки проверки работоспособности (Health Check)

Cloud Run ожидает, что сервис будет отвечать на запросы на порту 8080. Если проверка не проходит:

1. **Убедитесь, что HTTP-сервер запускается**:
   - Проверьте, что `cloud_run_adapter.py` правильно запускается в `start.py`
   - Проверьте, что порт 8080 открыт и доступен

2. **Проверьте логи для ошибок запуска сервера**:
   ```powershell
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:cloud_run_adapter" --limit=20
   ```

#### Ошибки API Telegram

Если бот не может подключиться к API Telegram:

1. **Проверьте правильность токена**:
   - Убедитесь, что токен имеет правильный формат (например: `5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk`)
   - Токен не должен содержать лишние пробелы или символы

2. **Проверьте доступ к API Telegram**:
   - Cloud Run должен иметь доступ к внешним сетям
   - Можно проверить доступность API вручную:
   ```python
   import requests
   response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
   print(response.json())
   ```

### 4. Расширенный поиск в логах

Для более глубокого анализа используйте комбинированные фильтры:

```powershell
# Поиск всех ошибок для конкретного сервиса
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND severity>=ERROR" --limit=50

# Поиск определенных ключевых слов в логах (например, "ModuleNotFoundError")
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:ModuleNotFoundError" --limit=20

# Поиск проблем с переменными окружения
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:environ" --limit=20
```

### 5. Диагностика с использованием интерактивной отладки

Для сложных случаев можно использовать интерактивную отладку:

1. **Создать тестовую версию с возможностью доступа по SSH**:
   ```powershell
   # Примечание: этот подход требует дополнительной настройки и доступен только для некоторых типов проектов
   gcloud run deploy dostup-bot-debug `
     --image=gcr.io/YOUR_PROJECT_ID/dostup-bot:latest `
     --command=/bin/bash `
     --args="-c","sleep 3600" `
     --region=europe-west1
   ```

2. **Подключиться к контейнеру для проверки**:
   ```powershell
   gcloud beta run services proxy dostup-bot-debug --region=europe-west1
   ```

### 6. Создание нового образа с улучшенной диагностикой

Если проблема остается неясной, создайте специальную версию образа с дополнительной диагностикой:

```dockerfile
# Добавить в Dockerfile
ENV DEBUG=True
ENV PYTHONVERBOSE=1
```

```python
# Добавить в код
import os
import sys

# Вывод информации о среде
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")
print(f"Working directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")
print(f"Environment variables: {os.environ}")
```

### 7. Исправление распространенных ошибок

#### ValueError с переменными окружения

Ошибка: `ValueError: invalid literal for int() with base 10: 'your_admin_id'`

Решение:
```powershell
# Укажите числовое значение без кавычек
gcloud run services update dostup-bot `
  --set-env-vars=ADMIN_USER_ID=123456789 `
  --region=europe-west1
```

#### ModuleNotFoundError

Ошибка: `ModuleNotFoundError: No module named 'reminder_system'`

Решение:
1. Проверьте структуру Dockerfile
2. Добавьте отладочную информацию в start.py:
```python
import sys
print(f"Python path: {sys.path}")
try:
    import reminder_system
    print("reminder_system imported successfully")
except ImportError as e:
    print(f"Failed to import reminder_system: {e}")
    # Пытаемся добавить путь вручную
    sys.path.append('/app')
    sys.path.append('/usr/local/lib/python3.11/site-packages')
    print(f"Updated Python path: {sys.path}")
    try:
        import reminder_system
        print("reminder_system imported successfully after path update")
    except ImportError as e:
        print(f"Still failed to import reminder_system: {e}")
```

#### Ошибки API Telegram

Ошибка: `aiogram.utils.exceptions.Unauthorized: Unauthorized`

Решение:
1. Проверьте формат токена
2. Убедитесь, что токен активен (проверьте в @BotFather)
3. Обновите токен в переменных окружения:
```powershell
gcloud run services update dostup-bot `
  --set-env-vars=BOT_TOKEN=5555555555:AAHBbbbCccDDDeeeFFFgggHHHiiiJJJkkk `
  --region=europe-west1
```
