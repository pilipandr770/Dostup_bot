# Команды для деплоя в Google Cloud Run через PowerShell

## Успешно выполненные шаги

```powershell
# 1. Перейдите в корневую директорию проекта
cd c:\Users\ПК\dostup_bot

# 2. Убедитесь, что Docker запущен на вашем компьютере

# 3. Соберите Docker образ
docker build -t dostup-bot .

# 4. Авторизуйте Docker в Google Container Registry
gcloud auth configure-docker

# 5. Получите ID вашего проекта
$PROJECT_ID = gcloud config get-value project

# 6. Пометьте образ для загрузки в Google Container Registry
docker tag dostup-bot gcr.io/$PROJECT_ID/dostup-bot:latest

# 7. Загрузите образ в Google Container Registry
docker push gcr.io/$PROJECT_ID/dostup-bot:latest
```

## Правильные команды для PowerShell (исправленные)

```powershell
# 8. Разверните сервис на Cloud Run (для PowerShell все на одной строке с `)
gcloud run deploy dostup-bot `
  --image gcr.io/$PROJECT_ID/dostup-bot:latest `
  --platform managed `
  --region europe-west1 `
  --allow-unauthenticated `
  --memory 512Mi `
  --cpu 1 `
  --max-instances 1

# Или одной командой без переносов:
gcloud run deploy dostup-bot --image gcr.io/$PROJECT_ID/dostup-bot:latest --platform managed --region europe-west1 --allow-unauthenticated --memory 512Mi --cpu 1 --max-instances 1

# 9. Настройте переменные окружения (для PowerShell все на одной строке с `)
gcloud run services update dostup-bot `
  --set-env-vars="BOT_TOKEN=your_token,COURSE_CHANNEL_ID=your_channel_id,ADMIN_USER_ID=your_admin_id,YOUTUBE_CHANNEL_URL=your_url,CHANNEL_INVITE_LINK=your_link,OPENAI_API_KEY=your_key,OPENAI_ASSISTANT_ID=your_assistant_id,STRIPE_PAYMENT_URL=your_url,STRIPE_API_KEY=your_key" `
  --region europe-west1

# Или одной командой без переносов:
gcloud run services update dostup-bot --set-env-vars="BOT_TOKEN=your_token,COURSE_CHANNEL_ID=your_channel_id,ADMIN_USER_ID=your_admin_id" --region europe-west1
```

## Важно: не забудьте заменить значения переменных окружения на реальные!

```powershell
# Пример с реальными значениями (замените на свои)
gcloud run services update dostup-bot `
  --set-env-vars="BOT_TOKEN=5555555555:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,COURSE_CHANNEL_ID=-1002689282996,ADMIN_USER_ID=403758011,YOUTUBE_CHANNEL_URL=https://youtube.com/channel/example,CHANNEL_INVITE_LINK=https://t.me/+example,OPENAI_API_KEY=sk-example,OPENAI_ASSISTANT_ID=asst_example,STRIPE_PAYMENT_URL=https://buy.stripe.com/example,STRIPE_API_KEY=sk_test_example" `
  --region europe-west1
```

## Проверка статуса деплоя

```powershell
# Проверьте статус сервиса
gcloud run services describe dostup-bot --region europe-west1

# Просмотр логов
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=20
```

## Если нужно использовать Artifact Registry вместо Container Registry

```powershell
# 1. Активировать API
gcloud services enable artifactregistry.googleapis.com

# 2. Создать репозиторий
gcloud artifacts repositories create dostup-bot-repo `
  --repository-format=docker `
  --location=europe-west1 `
  --description="Docker repository for Dostup Bot"

# 3. Настроить Docker
gcloud auth configure-docker europe-west1-docker.pkg.dev

# 4. Собрать и отправить образ
docker tag dostup-bot europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot:latest
docker push europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot:latest

# 5. Деплой с новым путем к образу
gcloud run deploy dostup-bot `
  --image europe-west1-docker.pkg.dev/$PROJECT_ID/dostup-bot-repo/dostup-bot:latest `
  --platform managed `
  --region europe-west1 `
  --allow-unauthenticated
```
