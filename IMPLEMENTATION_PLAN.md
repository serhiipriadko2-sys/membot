# План реализации: Прототип → Продакшн

## Статус выполнения

| Задача | ID | Статус | Файл | Тесты |
|--------|----|--------|------|-------|
| Solana WebSocket Ingester | INGEST-01 | ✅ DONE | `src/ingest/solana_ingester.py` | ✅ PASS |
| Adaptive Schema Validator | SCHEMA-02 | ✅ DONE | `src/ingest/schema_validator.py` | ✅ PASS |
| Parquet Data Store | STORE-03 | ✅ DONE | `src/storage/parquet_store.py` | ✅ PASS |
| Bayesian Engine | HYP-04 | ✅ DONE | `src/analytics/bayesian_engine.py` | ✅ PASS |
| Observer Gate v2.0 | OBS-05 | ✅ DONE | `src/analytics/observer_gate.py` | ✅ PASS |
| Docker Orchestration | OPS-06 | ✅ DONE | `docker-compose.yml`, `Dockerfile` | ⏳ PENDING |
| Health Monitor API | MON-07a | ✅ DONE | `src/api/main.py` | ⏳ PENDING |
| Streamlit Dashboard | MON-07b | ✅ DONE | `src/api/dashboard.py` | ⏳ PENDING |

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                      Membot Production                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │   INGEST     │────▶│   STORAGE    │────▶│  ANALYTICS   │   │
│  │  (WebSocket) │     │   (Parquet)  │     │  (Bayesian)  │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│         │                   │                    │             │
│         │                   │                    ▼             │
│         │                   │            ┌──────────────┐     │
│         │                   │            │   OBSERVER   │     │
│         │                   │            │    GATE      │     │
│         │                   │            └──────────────┘     │
│         │                   │                    │             │
│         ▼                   ▼                    ▼             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │     DLQ      │     │   Parquet    │     │    Alerts    │   │
│  │   (JSONL)    │     │   Files      │     │  (Real-time) │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│                                                                 │
│                    ┌──────────────┐                            │
│                    │     API      │◀─── FastAPI (:8000)        │
│                    │   (Health)   │                            │
│                    └──────────────┘                            │
│                           │                                     │
│                           ▼                                     │
│                    ┌──────────────┐                            │
│                    │  Dashboard   │◀─── Streamlit (:8501)      │
│                    │  (Streamlit) │                            │
│                    └──────────────┘                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Быстрый старт

### Локальный запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Тестирование модулей
python src/ingest/schema_validator.py
python src/storage/parquet_store.py
python src/analytics/bayesian_engine.py
python src/analytics/observer_gate.py

# Запуск API
uvicorn src.api.main:app --reload --port 8000

# Запуск Dashboard
streamlit run src/api/dashboard.py
```

### Docker запуск

```bash
# Сборка и запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

---

## API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/` | Root endpoint |
| GET | `/health` | Общее состояние системы |
| GET | `/health/storage` | Статус хранилища |
| GET | `/health/dlq` | Статус DLQ |
| GET | `/metrics` | Метрики системы |
| GET | `/ready` | Kubernetes readiness |
| GET | `/live` | Kubernetes liveness |

Swagger UI: http://localhost:8000/docs

---

## Конфигурация

### Переменные окружения

```bash
# Solana RPC
SOLANA_RPC_WS_URL=wss://api.devnet.solana.com

# Пороги Observer Gate
CONFIRMATION_THRESHOLD=0.95
REJECTION_THRESHOLD=0.05

# Логирование
LOG_LEVEL=INFO
```

### Docker Compose сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| ingester | - | WebSocket ingester |
| storage-worker | - | Обработка и хранение |
| analytics | - | Байесовский движок |
| api | 8000 | Health Monitor API |
| dashboard | 8501 | Streamlit Dashboard |

---

## Структура данных

### Parquet партиционирование

```
data/processed/
├── date=2024-01-01/
│   └── program_id=Tokenkeg/
│       └── data_20240101_120000.parquet
├── date=2024-01-02/
│   └── program_id=Tokenkeg/
│       └── data_20240102_090000.parquet
```

### Dead Letter Queue

```
data/dlq/
├── dlq_20240101_120000.jsonl
├── dlq_20240101_130000.jsonl
```

Формат записи DLQ:
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "source": "ingester",
  "original_data": {...},
  "validation_result": {...},
  "error_count": 2
}
```

---

## Метрики и мониторинг

### Ключевые метрики

- **Throughput**: сообщений/сек от WebSocket
- **Latency**: задержка от получения до алерта (< 2 сек SLA)
- **Error Rate**: процент записей в DLQ
- **Storage**: размер и количество файлов Parquet
- **Hypotheses**: количество активных/подтвержденных/отклоненных

### Дашборд

- Overview: общие метрики системы
- Hypotheses: таблица и графики вероятностей
- Alerts: монитор алертов с фильтрами
- Storage: статистика хранилища и DLQ
- Settings: настройка порогов

---

## Следующие шаги

### Неделя 1-2: Стабилизация
- [ ] Интеграция с production RPC
- [ ] Настройка алертинга (Slack/Telegram)
- [ ] Load testing WebSocket подключения

### Неделя 3-4: Масштабирование
- [ ] Горизонтальное масштабирование инжесторов
- [ ] Оптимизация Parquet компактификации
- [ ] Кэширование частых запросов

### Месяц 2: Расширение
- [ ] Поддержка дополнительных блокчейнов
- [ ] ML модели для предсказания
- [ ] GraphQL API для сложных запросов

---

## Контакты и поддержка

- Документация: `/docs`
- API Swagger: http://localhost:8000/docs
- Dashboard: http://localhost:8501

---

*Документ создан: 2026-05-27*
*Версия плана: 1.0*
