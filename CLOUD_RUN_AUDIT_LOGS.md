# Работа с аудит-логами Google Cloud Run

Аудит-логи Google Cloud Run содержат важную информацию о операциях с вашим сервисом, включая развертывания, изменения конфигурации, ошибки и другие события. Этот документ объясняет, как эффективно использовать эти логи для диагностики проблем.

## Получение аудит-логов

### Базовая команда для просмотра логов

```powershell
# PowerShell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=50
```

```bash
# Linux/Mac
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=50
```

### Фильтрация по уровню серьезности

```powershell
# Только ошибки и предупреждения
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND severity>=WARNING" --limit=50

# Только критические ошибки
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND severity=ERROR" --limit=20
```

### Фильтрация по конкретной версии (ревизии)

```powershell
# Логи для конкретной версии сервиса
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb" --limit=50
```

### Поиск конкретных ошибок

```powershell
# Поиск ошибок импорта модулей
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:ModuleNotFoundError" --limit=20

# Поиск ошибок авторизации Telegram
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:Unauthorized" --limit=20

# Поиск проблем с переменными окружения
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:ValueError" --limit=20
```

## Интерпретация аудит-логов

### Типичные записи в аудит-логах

1. **Создание новой версии**:
   ```
   NOTICE 2025-06-29T10:30:00.123456789Z Creating new revision dostup-bot-00001-fqb
   ```

2. **Ошибка в версии**:
   ```
   NOTICE 2025-06-29T10:32:59.229153274Z Error detected in dostup-bot version dostup-bot-00001-fqb
   ```

3. **Успешное развертывание**:
   ```
   NOTICE 2025-06-29T10:35:00.123456789Z Revision dostup-bot-00002-abc became ready
   ```

4. **Обновление конфигурации**:
   ```
   NOTICE 2025-06-29T10:40:00.123456789Z Configuration for dostup-bot was updated
   ```

### Анализ ошибок в версиях

Если в логах появляется сообщение "Error detected in [service] version [revision]", это значит, что произошла ошибка при запуске или работе данной версии. Для более подробного анализа:

1. **Получите ID ревизии с ошибкой** (например, `dostup-bot-00001-fqb`)

2. **Запросите подробные логи для этой ревизии**:
   ```powershell
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND severity>=ERROR" --limit=20
   ```

3. **Проверьте события контейнера**:
   ```powershell
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND jsonPayload.container.name=dostup-bot" --limit=20
   ```

### Формат временных меток

Временные метки в аудит-логах имеют формат ISO 8601 с UTC часовым поясом:
```
YYYY-MM-DDThh:mm:ss.sssssssssZ
```

Например: `2025-06-29T10:32:59.229153274Z`

## Расширенные техники поиска в логах

### Временные интервалы

```powershell
# Логи за последний час
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND timestamp>=\"$(Get-Date).AddHours(-1).ToString('o')\"" --limit=50

# Логи за конкретный период
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND timestamp>=\"2025-06-29T10:00:00Z\" AND timestamp<=\"2025-06-29T11:00:00Z\"" --limit=100
```

### Форматирование вывода

```powershell
# Вывод в JSON формате
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=20 --format=json

# Вывод только текста сообщений
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=20 --format="value(textPayload)"

# Сохранение логов в файл
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot" --limit=50 > cloud_run_logs.txt
```

## Диагностика специфических проблем

### Проблемы с запуском контейнера

```powershell
# Поиск ошибок при запуске контейнера
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND jsonPayload.container.name=dostup-bot AND textPayload:\"starting container\"" --limit=20
```

### Проблемы с проверками работоспособности

```powershell
# Поиск проблем с health check
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:health" --limit=20
```

### Проблемы с переменными окружения

```powershell
# Поиск проблем с переменными окружения
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:environ" --limit=20
```

### Проблемы с потреблением ресурсов

```powershell
# Поиск проблем с памятью
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:memory" --limit=20

# Поиск проблем с CPU
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:cpu" --limit=20
```

## Практические примеры

### Пример 1: Диагностика ошибки импорта модуля

```powershell
# Шаг 1: Найти ревизии с ошибками
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND severity>=ERROR" --limit=10

# Шаг 2: Проверить конкретную ревизию
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb" --limit=30

# Шаг 3: Искать конкретную ошибку импорта
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:ModuleNotFoundError" --limit=20
```

### Пример 2: Диагностика проблем с авторизацией Telegram

```powershell
# Шаг 1: Поиск ошибок авторизации
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:Unauthorized" --limit=20

# Шаг 2: Проверка переменных окружения
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:BOT_TOKEN" --limit=20
```

### Пример 3: Анализ успешного запуска

```powershell
# Поиск успешно запущенных версий
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND textPayload:\"became ready\"" --limit=10

# Анализ событий после успешного запуска
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00003-xyz AND timestamp>=\"2025-06-29T10:45:00Z\"" --limit=50
```

## Интеграция с другими инструментами

### Экспорт логов для дальнейшего анализа

```powershell
# Экспорт логов в BigQuery
gcloud logging sinks create dostup-bot-logs bigquery.googleapis.com/projects/YOUR_PROJECT_ID/datasets/dostup_bot_logs "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot"

# Экспорт логов в Cloud Storage
gcloud logging sinks create dostup-bot-logs-storage storage.googleapis.com/YOUR_BUCKET_NAME "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot"
```

### Настройка оповещений

```powershell
# Создание политики оповещений для критических ошибок
gcloud alpha monitoring policies create --policy-from-file=alert-policy.json
```

Пример `alert-policy.json`:
```json
{
  "displayName": "Dostup Bot Critical Errors",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Log entries matching Error in dostup-bot",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"dostup-bot\" AND severity>=ERROR",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0,
        "duration": "0s",
        "trigger": {
          "count": 1
        },
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_COUNT"
          }
        ]
      }
    }
  ]
}
```

## Заключение

Умелое использование аудит-логов Google Cloud Run значительно упрощает диагностику проблем с сервисами. Регулярный мониторинг логов поможет выявлять и решать проблемы до того, как они повлияют на работу пользователей.

## Интерпретация расширенного формата аудит-логов

Аудит-логи Google Cloud Run могут отображаться в расширенном формате, содержащем дополнительные метаданные в квадратных скобках. Этот формат особенно полезен для глубокого анализа событий и диагностики проблем.

### Анализ структуры расширенного формата

Типичная запись в расширенном формате выглядит так:

```
NOTICE 2025-06-29T10:32:59.229153274Z [protoPayload.serviceName: run.googleapis.com] [protoPayload.methodName: google.cloud.run.v1.Services.ReplaceService] [protoPayload.resourceName: namespaces/voise-460610/services/dostup-bot] [protoPayload.authenticationInfo.principalEmail: pylypchukandrii770@gmail.com] audit_log, method: "google.cloud.run.v1.Services.ReplaceService", principal_email: "pylypchukandrii770@gmail.com"
```

Структура такой записи:
1. **Уровень серьезности** (NOTICE, INFO, WARNING, ERROR)
2. **Временная метка** в формате ISO 8601
3. **Метаданные в квадратных скобках**:
   - `protoPayload.serviceName`: Имя сервиса Google Cloud (e.g., run.googleapis.com)
   - `protoPayload.methodName`: Вызываемый метод API
   - `protoPayload.resourceName`: Путь к затрагиваемому ресурсу
   - `protoPayload.authenticationInfo.principalEmail`: Email пользователя или сервисного аккаунта
4. **Краткое описание** действия и связанных параметров

### Ключевые события в жизненном цикле сервиса

Анализируя логи для сервиса `dostup-bot`, можно выделить следующие ключевые события:

#### 1. Создание сервиса
```
NOTICE 2025-06-29T10:32:32.524890Z [protoPayload.serviceName: run.googleapis.com] [protoPayload.methodName: google.cloud.run.v1.Services.CreateService] [protoPayload.resourceName: namespaces/voise-460610/services/dostup-bot] [protoPayload.authenticationInfo.principalEmail: pylypchukandrii770@gmail.com] audit_log, method: "google.cloud.run.v1.Services.CreateService", principal_email: "pylypchukandrii770@gmail.com"
```
Это событие показывает первоначальное создание сервиса `dostup-bot`.

#### 2. Настройка прав доступа к сервису
```
NOTICE 2025-06-29T10:32:34.492797Z [protoPayload.serviceName: run.googleapis.com] [protoPayload.methodName: google.cloud.run.v1.Services.SetIamPolicy] [protoPayload.resourceName: projects/voise-460610/locations/europe-west1/services/dostup-bot] [protoPayload.authenticationInfo.principalEmail: pylypchukandrii770@gmail.com] audit_log, method: "google.cloud.run.v1.Services.SetIamPolicy", principal_email: "pylypchukandrii770@gmail.com"
```
Это запись о настройке политик доступа IAM для сервиса.

#### 3. Обновление сервиса
```
NOTICE 2025-06-29T10:32:59.179533Z [protoPayload.serviceName: run.googleapis.com] [protoPayload.methodName: google.cloud.run.v1.Services.ReplaceService] [protoPayload.resourceName: namespaces/voise-460610/services/dostup-bot] [protoPayload.authenticationInfo.principalEmail: pylypchukandrii770@gmail.com] audit_log, method: "google.cloud.run.v1.Services.ReplaceService", principal_email: "pylypchukandrii770@gmail.com"
```
Запись об обновлении конфигурации сервиса.

#### 4. Обнаружение ошибки
```
NOTICE 2025-06-29T10:32:59.229153274Z Error detected in dostup-bot version dostup-bot-00001-fqb
```
Это критически важная запись, указывающая на проблему в конкретной версии сервиса. 

### Хронология ошибок в жизненном цикле развертывания

Проанализируем хронологию выявленных ошибок:

1. **Первая ошибка** (10:32:59):
   ```
   NOTICE 2025-06-29T10:32:59.229153274Z Error detected in dostup-bot version dostup-bot-00001-fqb
   ```
   Произошла сразу после первого создания сервиса, что может указывать на проблемы с начальной конфигурацией.

2. **Вторая ошибка** (10:58:58):
   ```
   NOTICE 2025-06-29T10:58:58.866962249Z Error detected in dostup-bot version dostup-bot-00004-qkq
   ```
   Возникла после нескольких попыток обновления сервиса (видно по записям `ReplaceService`).

3. **Третья ошибка** (11:01:51):
   ```
   NOTICE 2025-06-29T11:01:51.955754160Z Error detected in dostup-bot version dostup-bot-00005-5lk
   ```
   Произошла после очередного обновления, что может указывать на сохранение проблемы.

### Методы поиска расширенной информации по конкретным ошибкам

#### Для первой ошибки (dostup-bot-00001-fqb):

```powershell
# Получить все логи для этой версии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb" --limit=50

# Получить только сообщения об ошибках
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND severity>=ERROR" --limit=20

# Анализ контейнерных логов этой ревизии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00001-fqb AND jsonPayload.container.name=user-container" --limit=20
```

#### Для второй ошибки (dostup-bot-00004-qkq):

```powershell
# Получить все логи для этой версии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00004-qkq" --limit=50

# Получить только сообщения об ошибках
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00004-qkq AND severity>=ERROR" --limit=20
```

#### Для третьей ошибки (dostup-bot-00005-5lk):

```powershell
# Получить все логи для этой версии
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00005-5lk" --limit=50

# Получить только сообщения об ошибках
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dostup-bot AND resource.labels.revision_name=dostup-bot-00005-5lk AND severity>=ERROR" --limit=20
```

### Анализ последовательности действий по аудит-логам

Анализ предоставленных логов показывает следующую последовательность действий:

1. **09:31** - Активация сервисных аккаунтов и настройка прав доступа
2. **10:24** - Активация дополнительных сервисов и подготовка контейнера (Docker-CreateOnPush)
3. **10:32** - Создание сервиса dostup-bot и первая попытка развертывания (завершилась ошибкой)
4. **10:50 - 10:58** - Несколько попыток обновить конфигурацию сервиса (также с ошибками)
5. **11:01** - Заключительная попытка с версией dostup-bot-00005-5lk (тоже завершилась ошибкой)

Для исправления проблемы следует:

1. Подробно изучить логи для каждой неудачной ревизии
2. Проверить и исправить переменные окружения
3. Проанализировать проблемы с импортом модулей
4. Убедиться в правильности настройки токена Telegram бота
