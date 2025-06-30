# Решение проблемы "Image not found" на Google Cloud Run

Вы столкнулись с ошибкой `Неудавшийся. Подробности: Версия 'vois-00001-dvk' не готова и не может обслуживать трафик. Изображение 'gcr.io/voise-460610/dostup-bot:latest' не найдено.`

Давайте разберем причину и решение этой проблемы.

## Причина ошибки

Данная ошибка означает, что Google Cloud Run пытается найти Docker-образ по пути `gcr.io/voise-460610/dostup-bot:latest`, но не может его найти в Container Registry. Возможные причины:

1. Образ не был загружен в Container Registry
2. Путь к образу указан неверно
3. Отсутствуют необходимые разрешения

## Пошаговое решение проблемы

### Шаг 1: Проверьте активный проект

```powershell
gcloud config get-value project
```

Убедитесь, что отображается `voise-460610`. Если нет, установите правильный проект:
```powershell
gcloud config set project voise-460610
```

### Шаг 2: Проверьте настройки Docker для работы с Google Container Registry

```powershell
gcloud auth configure-docker
```

### Шаг 3: Соберите и загрузите Docker-образ

```powershell
# Перейдите в корневую директорию проекта, где находится Dockerfile
cd c:\Users\ПК\dostup_bot

# Соберите образ с правильным тегом
docker build -t gcr.io/voise-460610/dostup-bot .

# Загрузите образ в Container Registry
docker push gcr.io/voise-460610/dostup-bot
```

### Шаг 4: Проверьте наличие образа в Container Registry

```powershell
gcloud container images list --repository=gcr.io/voise-460610
```

### Шаг 5: Повторите деплой с проверенным образом

```powershell
gcloud run deploy dostup-bot \
  --image gcr.io/voise-460610/dostup-bot \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated
```

## Альтернативное решение: Artifact Registry

Если проблемы с Container Registry продолжаются, рекомендуется использовать Artifact Registry (более новый сервис):

```powershell
# Активировать API
gcloud services enable artifactregistry.googleapis.com

# Создать репозиторий
gcloud artifacts repositories create dostup-bot-repo \
  --repository-format=docker \
  --location=europe-west1 \
  --description="Docker repository for Dostup Bot"

# Настроить Docker для работы с Artifact Registry
gcloud auth configure-docker europe-west1-docker.pkg.dev

# Собрать образ с новым тегом
docker build -t europe-west1-docker.pkg.dev/voise-460610/dostup-bot-repo/dostup-bot .

# Загрузить образ в Artifact Registry
docker push europe-west1-docker.pkg.dev/voise-460610/dostup-bot-repo/dostup-bot

# Деплой с новым путем к образу
gcloud run deploy dostup-bot \
  --image europe-west1-docker.pkg.dev/voise-460610/dostup-bot-repo/dostup-bot \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated
```

## Проверка прав доступа

Если возникают проблемы с правами доступа:

```powershell
# Получите номер проекта
$PROJECT_NUMBER = gcloud projects describe voise-460610 --format="value(projectNumber)"

# Предоставьте сервисному аккаунту Cloud Run доступ к Container Registry
gcloud projects add-iam-policy-binding voise-460610 --member="serviceAccount:service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com" --role="roles/storage.objectViewer"
```

## Полезные команды для диагностики

```powershell
# Проверка статуса деплоя
gcloud run services describe dostup-bot --region europe-west1

# Просмотр логов деплоя
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=20

# Проверка доступных тегов образа
gcloud container images list-tags gcr.io/voise-460610/dostup-bot
```

## После успешного деплоя

После успешного деплоя не забудьте добавить переменные окружения:

```powershell
gcloud run services update dostup-bot \
  --set-env-vars="BOT_TOKEN=your_token,COURSE_CHANNEL_ID=your_channel_id,ADMIN_USER_ID=your_admin_id,YOUTUBE_CHANNEL_URL=your_url,CHANNEL_INVITE_LINK=your_link,OPENAI_API_KEY=your_key,OPENAI_ASSISTANT_ID=your_assistant_id,STRIPE_PAYMENT_URL=your_url,STRIPE_API_KEY=your_key" \
  --region europe-west1
```
