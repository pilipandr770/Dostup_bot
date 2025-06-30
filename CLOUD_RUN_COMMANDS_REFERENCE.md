# Шпаргалка по командам Google Cloud Run

Этот документ содержит наиболее часто используемые команды для управления Telegram ботом на Google Cloud Run.

## Основные команды

### Информация о сервисе

```powershell
# Получение полной информации о сервисе
gcloud run services describe dostup-bot --region=europe-west1

# Получение URL сервиса
gcloud run services describe dostup-bot --format="value(status.url)" --region=europe-west1

# Проверка статуса сервиса
gcloud run services describe dostup-bot --region=europe-west1 --format="value(status.conditions[0].status,status.conditions[0].type)"
```

### Просмотр логов

```powershell
# Просмотр последних логов (20 записей)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=20

# Просмотр логов в режиме реального времени
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --tail

# Просмотр логов ошибок
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND severity>=ERROR" --limit=20

# Просмотр логов для конкретной ревизии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00005-5lk" --limit=20
```

### Управление переменными окружения

```powershell
# Просмотр текущих переменных окружения
gcloud run services describe dostup-bot --region=europe-west1 | Select-String "Env vars"

# Обновление одной переменной (например, BOT_TOKEN)
gcloud run services update dostup-bot `
  --set-env-vars="BOT_TOKEN=новый_токен_бота" `
  --region=europe-west1

# Обновление нескольких переменных
gcloud run services update dostup-bot `
  --set-env-vars="BOT_TOKEN=новый_токен,ADMIN_USER_ID=123456789" `
  --region=europe-west1

# Удаление переменной окружения
gcloud run services update dostup-bot `
  --remove-env-vars=ПЕРЕМЕННАЯ_ДЛЯ_УДАЛЕНИЯ `
  --region=europe-west1
```

### Масштабирование сервиса

```powershell
# Установка минимального и максимального количества экземпляров
gcloud run services update dostup-bot `
  --min-instances=0 `
  --max-instances=2 `
  --region=europe-west1

# Изменение выделенных ресурсов
gcloud run services update dostup-bot `
  --memory=256Mi `
  --cpu=1 `
  --region=europe-west1
```

## Обновление образа

```powershell
# Получение ID проекта
$PROJECT_ID = gcloud config get-value project

# Сборка нового образа
docker build -t gcr.io/$PROJECT_ID/dostup-bot:latest .

# Отправка образа в Container Registry
docker push gcr.io/$PROJECT_ID/dostup-bot:latest

# Обновление сервиса для использования нового образа
gcloud run services update dostup-bot `
  --image=gcr.io/$PROJECT_ID/dostup-bot:latest `
  --region=europe-west1
```

## Управление доменом

```powershell
# Добавление собственного домена к сервису
gcloud beta run domain-mappings create `
  --service=dostup-bot `
  --domain=your-domain.com `
  --region=europe-west1

# Список привязанных доменов
gcloud beta run domain-mappings list --region=europe-west1

# Удаление привязки домена
gcloud beta run domain-mappings delete `
  --domain=your-domain.com `
  --region=europe-west1
```

## Безопасность и аутентификация

```powershell
# Получение сервисного аккаунта сервиса
gcloud run services describe dostup-bot --region=europe-west1 --format="value(spec.template.spec.serviceAccountName)"

# Изменение сервисного аккаунта
gcloud run services update dostup-bot `
  --service-account=YOUR-SERVICE-ACCOUNT@YOUR-PROJECT.iam.gserviceaccount.com `
  --region=europe-west1

# Настройка доступа к сервису (требовать авторизацию)
gcloud run services update dostup-bot `
  --no-allow-unauthenticated `
  --region=europe-west1

# Настройка доступа к сервису (публичный доступ)
gcloud run services update dostup-bot `
  --allow-unauthenticated `
  --region=europe-west1
```

## Управление секретами

```powershell
# Создание секрета
gcloud secrets create telegram-bot-token --replication-policy="automatic"

# Добавление версии секрета
echo -n "значение_секрета" | gcloud secrets versions add telegram-bot-token --data-file=-

# Предоставление доступа сервисному аккаунту Cloud Run
$SERVICE_ACCOUNT = gcloud run services describe dostup-bot --region=europe-west1 --format="value(spec.template.spec.serviceAccountName)"

gcloud secrets add-iam-policy-binding telegram-bot-token `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/secretmanager.secretAccessor"

# Использование секрета в Cloud Run
gcloud run services update dostup-bot `
  --update-secrets="BOT_TOKEN=telegram-bot-token:latest" `
  --region=europe-west1
```

## Полезные команды для Docker

```powershell
# Проверка локально собранных образов
docker images

# Запуск контейнера локально для тестирования
docker run -p 8080:8080 -e BOT_TOKEN=your_token -e ADMIN_USER_ID=123456 gcr.io/$PROJECT_ID/dostup-bot

# Просмотр логов контейнера
docker logs CONTAINER_ID

# Удаление неиспользуемых образов
docker system prune -a
```

## Управление несколькими сервисами

```powershell
# Список всех сервисов
gcloud run services list --region=europe-west1

# Удаление сервиса
gcloud run services delete dostup-bot --region=europe-west1

# Клонирование сервиса под новым именем
gcloud run services describe dostup-bot --region=europe-west1 --format=json | `
  jq '.spec' | `
  gcloud run services create dostup-bot-new `
  --region=europe-west1 `
  --spec-from-file=-
```
