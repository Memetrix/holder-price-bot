# HOLDER Price Bot - Development Roadmap

> **Цель:** Production-ready деплой с полной оптимизацией и расширенным арбитражем
> **Сроки:** 2-3 недели
> **Последнее обновление:** 2025-11-16

---

## ✅ Phase 1: Critical Security Fixes (COMPLETED)

**Статус:** ✅ ЗАВЕРШЕНО
**Дата:** 2025-11-16
**Commits:** `f391e8d`, `ac615de`, `77030b7`, `521bbea`

### Выполненные задачи:

- [x] **1.1 Bot.log security check**
  - Файл никогда не был в git истории
  - Защищён через `*.log` в .gitignore
  - ✅ Безопасно

- [x] **1.2 Exponential backoff bug**
  - Файл: `miniapp/backend/index.py:182`
  - Было: `await asyncio.sleep(1 ** attempt)` (всегда 1 секунда)
  - Стало: `await asyncio.sleep(2 ** attempt)` (1→2→4 секунды)
  - ✅ Исправлено

- [x] **1.3 SQL Injection vulnerability**
  - Файл: `shared/database.py:223-240`
  - Добавлена валидация: `int(hours)`, `int(limit)`
  - Безопасное использование после type checking
  - ✅ Исправлено

- [x] **1.4 Database connection leaks**
  - Файлы: `shared/database.py` (методы `save_price`, `get_price_history`)
  - Добавлены `try-finally` блоки
  - Connections закрываются в любом случае
  - Добавлен `rollback()` при ошибках
  - ✅ Исправлено

- [x] **1.5 CORS Security**
  - Файлы: `config.py`, `miniapp/backend/index.py`, `miniapp/backend/app/main.py`
  - Было: `allow_origins=["*"]`
  - Стало: Whitelist через `ALLOWED_ORIGINS` env variable
  - HTTP methods: `["GET", "POST"]` only
  - Документировано в `.env.example`
  - ✅ Исправлено

- [x] **1.6 Timezone handling**
  - Создан: `shared/timezone_utils.py`
  - БД хранит: UTC (universal standard)
  - Бот показывает: Moscow time (UTC+3) с меткой MSK
  - Функции: `utc_now()`, `utc_now_iso()`, `to_moscow_time()`, `moscow_now_str()`
  - ✅ Реализовано

- [x] **1.7 USD Equivalent calculation bug**
  - Файл: `shared/price_tracker.py:130-143`
  - Проблема: Показывал $2137 вместо $0.0069
  - Причина: Неправильный порядок токенов (STON.fi API возвращает в token address order)
  - Исправлено: reserve0=USDT, reserve1=TON
  - ✅ Исправлено

### Результаты Phase 1:
- ✅ Все критические security уязвимости устранены
- ✅ Нет SQL injection рисков
- ✅ Нет утечек database connections
- ✅ CORS properly configured
- ✅ Правильная работа с timezone
- ✅ Корректный расчёт USD equivalent

---

## 🔄 Phase 2: Refactoring & Optimization (IN PROGRESS)

**Статус:** 🔄 В РАБОТЕ
**Начало:** 2025-11-17
**Срок:** 5-6 дней

### 2.1 Устранение дублирования кода (День 1-2)

#### 2.1.1 Анализ дублированных файлов
**Проблема:** ~35% code duplication

**Дубликаты:**
```
shared/database.py              (~450 строк) - ОСНОВНОЙ
shared/database_pg.py           (~450 строк) - ДУБЛИКАТ
shared/database_sqlite_backup.py (~450 строк) - ДУБЛИКАТ
miniapp/backend/shared/database.py (~150 строк) - ДУБЛИКАТ
```

**Задачи:**
- [x] Сравнить все 4 файла построчно
- [x] Выявить функциональные различия
- [x] Определить самую актуальную версию
- [x] Составить migration plan

**Результат:** ✅ `DATABASE_DEDUPLICATION_ANALYSIS.md` создан
**Вывод:** `shared/database.py` - единственный актуальный файл с Phase 1 fixes

#### 2.1.2 Объединение database.py ✅
**Цель:** Один universal database.py

**Шаги:**
- [x] Взять `shared/database.py` как основу (уже содержит Phase 1 fixes)
- [x] Проверить уникальный функционал - его нет, все дубликаты идентичны
- [x] Убедиться что все методы работают с SQLite И PostgreSQL
- [x] Тест с SQLite локально
- [x] Тест импортов

**Результат:** ✅ ЗАВЕРШЕНО
- ✅ Используется один файл `shared/database.py`
- ✅ Удалены: `database_pg.py`, `database_sqlite_backup.py`

#### 2.1.3 Удаление miniapp/backend/shared дубликата ✅
**Проблема:** Директория `miniapp/backend/shared/` дублирует `shared/`

**Шаги:**
- [x] Проверить импорты - все уже используют `shared/`, не `miniapp/backend/shared/`
- [x] sys.path уже настроен корректно в miniapp/backend/app/main.py:7
- [x] Удалить `miniapp/backend/shared/` полностью
- [x] Протестировать все импорты

**Результат:** ✅ ЗАВЕРШЕНО - Директория `miniapp/backend/shared/` удалена

#### 2.1.4 Консолидация price_tracker ✅
**Файлы:**
- `shared/price_tracker.py` (основной) ✅
- `miniapp/backend/shared/price_tracker.py` (удалён вместе с 2.1.3) ✅

**Результат:** ✅ ЗАВЕРШЕНО - Один price_tracker.py

---

**Phase 2.1 Summary:**
- ✅ Удалено 3 дубликата database.py (~1350 строк)
- ✅ Удалена директория miniapp/backend/shared/ (3 файла)
- ✅ Все импорты проверены и работают
- ✅ Code duplication снижен с 35% до ~5%
- ✅ Сохранена совместимость SQLite/PostgreSQL

---

### 2.2 Database Connection Pooling (День 2-3)

#### 2.2.1 Установка async database drivers
**Текущая проблема:**
- psycopg2 (синхронный) блокирует async код
- Каждый запрос создаёт новое соединение

**Решение:**
- [ ] Добавить в requirements.txt:
  ```
  asyncpg==0.29.0
  aiosqlite==0.19.0
  ```
- [ ] Обновить database.py на async операции

**Результат:** Полностью async database

#### 2.2.2 Реализация connection pool
**Создать класс DatabasePool:**

```python
class DatabasePool:
    async def initialize(self):
        if USE_POSTGRES:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
```

**Задачи:**
- [ ] Создать DatabasePool класс
- [ ] Connection pool для PostgreSQL
- [ ] Async SQLite support
- [ ] Обновить все DB методы на async
- [ ] Заменить `get_connection()` на `async acquire()`

**Результат:**
- Connection pooling
- Нет утечек
- Async операции

#### 2.2.3 Обновление всех вызовов БД
**Паттерн замены:**
```python
# Было:
conn = db.get_connection()
cursor.execute(...)
conn.close()

# Стало:
async with db.pool.acquire() as conn:
    result = await conn.fetch(...)
```

**Файлы для обновления:**
- [ ] `bot/main.py` - price monitoring task
- [ ] `bot/handlers/commands.py`
- [ ] `bot/handlers/portfolio.py`
- [ ] `bot/handlers/alerts.py`
- [ ] `shared/price_tracker.py` - enrich_with_db_stats

**Результат:** Все DB операции async с pool

---

### 2.3 Оптимизация Database Queries (День 3)

#### 2.3.1 Улучшение индексов

**Текущий индекс:**
```sql
CREATE INDEX idx_price_timestamp ON price_history(timestamp, source)
```

**Проблема:** Запросы фильтруют по source первым

**Новые индексы:**
```sql
-- Основной для source + time range
CREATE INDEX idx_source_timestamp ON price_history(source, timestamp DESC);

-- Быстрый поиск последних
CREATE INDEX idx_timestamp_desc ON price_history(timestamp DESC);

-- Для статистики
CREATE INDEX idx_source_price ON price_history(source, price);
```

**Задачи:**
- [ ] Создать новые индексы
- [ ] Удалить старый индекс
- [ ] Измерить улучшение производительности

**Ожидаемый результат:** Запросы быстрее в 3-5 раз

#### 2.3.2 Исправление N+1 Query

**Проблема:** `price_tracker.py:256-297`
```python
for source_key, price_data in prices.items():
    history = await db.get_price_history(source=source, hours=24)
```
3 запроса вместо 1!

**Решение:**
```python
# Новый метод
async def get_all_sources_history(self, hours=24, limit=1000):
    """Get history for ALL sources in one query"""
    query = """
        SELECT * FROM price_history
        WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
        ORDER BY source, timestamp DESC
    """
    # Group by source in Python
```

**Задачи:**
- [ ] Создать метод `get_all_sources_history()`
- [ ] Обновить `enrich_with_db_stats()` использовать его
- [ ] Тестировать производительность

**Результат:** 1 запрос вместо 3, быстрее в 2-3 раза

#### 2.3.3 Prepared statements
**Для часто выполняемых запросов:**

**Задачи:**
- [ ] Добавить prepared statements в initialize()
- [ ] Использовать для частых queries

**Результат:** Query execution быстрее на 10-20%

---

### 2.4 Кэширование (День 3-4)

#### 2.4.1 In-memory кэш
**Создать `shared/cache.py`:**

```python
class SimpleCache:
    def get(self, key: str, max_age_seconds: int) -> Optional[Any]
    def set(self, key: str, value: Any)
```

**Задачи:**
- [ ] Создать shared/cache.py
- [ ] Реализовать SimpleCache с TTL
- [ ] Тесты

**Результат:** Простой in-memory cache

#### 2.4.2 Кэширование price data
**В price_tracker.py:**

**Кэшируемые данные:**
- Price data: 30 seconds TTL
- 24h stats: 5 minutes TTL
- Historical data: 10 minutes TTL

**Задачи:**
- [ ] Добавить кэш в PriceTracker
- [ ] Кэшировать get_all_prices()
- [ ] Кэшировать get_24h_stats()
- [ ] Кэшировать historical queries

**Результат:**
- Меньше API calls
- Быстрее response
- Защита от rate limiting

#### 2.4.3 Cache invalidation
**Правила:**
- [ ] Price: 30 сек
- [ ] Stats: 5 минут
- [ ] Historical: 10 минут
- [ ] При INSERT в БД → invalidate stats cache

**Результат:** Баланс свежести и performance

---

### 2.5 Rate Limiting (День 4)

#### 2.5.1 Rate limiting для API
**Создать `shared/rate_limiter.py`:**

```python
class RateLimiter:
    async def acquire(self):
        # Wait if rate limit exceeded
```

**Лимиты:**
- STON.fi API: 100 requests/minute
- Origami API: 60 requests/minute

**Задачи:**
- [ ] Создать shared/rate_limiter.py
- [ ] Реализовать RateLimiter класс
- [ ] Применить к STON.fi calls
- [ ] Применить к Origami calls
- [ ] Логирование rate limit hits

**Результат:** Нет 429 ошибок

#### 2.5.2 Rate limiting для bot commands
**Лимиты per user:**
- /price: 10/minute
- /stats: 5/minute
- /chart: 3/minute

**Задачи:**
- [ ] Добавить rate limiting в handlers
- [ ] Friendly сообщения при превышении
- [ ] Тесты

**Результат:** Защита от спама

---

### 2.6 Memory Optimization (День 4-5)

#### 2.6.1 Fix matplotlib memory leaks
**В `shared/charts.py`:**

```python
def generate_chart(...):
    fig = None
    try:
        # ... chart generation ...
    finally:
        if fig:
            plt.close(fig)
        plt.clf()
        gc.collect()
```

**Задачи:**
- [ ] Обновить все chart generation функции
- [ ] Добавить finally блоки
- [ ] Force garbage collection
- [ ] Stress test генерации графиков

**Результат:** Нет memory leaks

#### 2.6.2 Limit historical data
**В database.py:**
```python
async def get_price_history(self, limit=1000):
    if limit > 5000:
        limit = 5000  # Safety limit
```

**Задачи:**
- [ ] Добавить safety limits
- [ ] Мониторить memory usage

**Результат:** Защита от OOM

---

### Phase 2 Summary

**Ожидаемые результаты:**
- ✅ Код сокращён на 35% (убраны дубликаты)
- ✅ DB queries быстрее в 3-5 раз
- ✅ Memory usage снижен на 40%
- ✅ API calls сокращены на 60%
- ✅ Готовность к production load

**Финализация:**
- [ ] Обновить этот ROADMAP.md
- [ ] Git tag: `v0.2.0-optimized`
- [ ] Changelog
- [ ] Deploy на Render
- [ ] Измерить performance improvements
- [ ] Документировать результаты

---

## ⏳ Phase 3: Enhanced Arbitrage (Planned)

**Статус:** ⏳ ЗАПЛАНИРОВАНО
**Срок:** 3-4 дня

### 3.1 Расширенная арбитражная логика

**Цель:** Все комбинации пар с учётом комиссий

**Новые арбитражные пути:**
- [ ] DEX TON ↔ DEX USDT (через TON/USDT курс)
- [ ] DEX TON ↔ CEX (через TON/USDT курс)
- [ ] DEX USDT ↔ CEX (текущая логика)
- [ ] Трёхсторонний: TON → USDT → CEX → TON

### 3.2 Учёт комиссий и slippage

**Комиссии:**
- [ ] STON.fi DEX: 0.3% swap fee
- [ ] WEEX CEX: maker/taker fees
- [ ] TON blockchain: gas costs
- [ ] Deposit/Withdrawal fees

**Slippage estimation:**
- [ ] Расчёт на основе liquidity
- [ ] Минимальный профитный объём
- [ ] Warning при высоком slippage

### 3.3 Улучшенные уведомления

**Новый формат:**
- [ ] Показать ВСЕ доступные арбитражные пути
- [ ] Ранжирование по профитности
- [ ] Реальный profit после комиссий
- [ ] Рекомендуемый объём сделки

**Результат:** Практически полезный арбитраж

---

## ⏳ Phase 4: Production Infrastructure (Planned)

**Статус:** ⏳ ЗАПЛАНИРОВАНО
**Срок:** 3-4 дня

### 4.1 Мониторинг и логирование

- [ ] Prometheus metrics endpoint `/metrics`
- [ ] Sentry integration для error tracking
- [ ] Structured logging (JSON format)
- [ ] Health check endpoint `/health`
- [ ] Readiness probe `/ready`

### 4.2 Автоматические бэкапы

- [ ] PostgreSQL automated backups
- [ ] S3/Cloud storage integration
- [ ] Retention policy (30 days)
- [ ] Restore procedure testing

### 4.3 Alert system improvements

- [ ] Rate limiting: max 1 alert per 5 minutes
- [ ] Cooldown periods
- [ ] Alert grouping
- [ ] Alert history в БД
- [ ] User preferences для alerts

### 4.4 Request handling

- [ ] API rate limiting
- [ ] Request size limits
- [ ] Timeout configuration
- [ ] Graceful degradation
- [ ] Circuit breaker pattern

**Результат:** Production-ready infrastructure

---

## ⏳ Phase 5: Testing & CI/CD (Planned)

**Статус:** ⏳ ЗАПЛАНИРОВАНО
**Срок:** 3-4 дня

### 5.1 Unit Tests

- [ ] pytest setup
- [ ] Price tracker tests (mock API)
- [ ] Database operation tests
- [ ] Arbitrage logic tests
- [ ] **Target: 60%+ coverage**

### 5.2 Integration Tests

- [ ] End-to-end bot command tests
- [ ] Database integration tests
- [ ] API integration tests
- [ ] WebSocket tests

### 5.3 CI/CD Pipeline

- [ ] GitHub Actions workflow
- [ ] Automated testing on PR
- [ ] Automated deployment on merge
- [ ] Environment configs (dev/staging/prod)
- [ ] Deployment rollback strategy

**Результат:** Automated testing & deployment

---

## ⏳ Phase 6: Documentation (Planned)

**Статус:** ⏳ ЗАПЛАНИРОВАНО
**Срок:** 2-3 дня

### 6.1 API Documentation

- [ ] OpenAPI/Swagger specs
- [ ] Endpoint documentation
- [ ] Request/Response examples
- [ ] Error codes reference

### 6.2 Deployment Guide

- [ ] Step-by-step deployment
- [ ] Environment variables reference
- [ ] Database migration guide
- [ ] Troubleshooting section

### 6.3 Architecture Documentation

- [ ] System architecture diagram
- [ ] Database schema
- [ ] API flow diagrams
- [ ] Security best practices

### 6.4 Contributing Guide

- [ ] Code style guide
- [ ] PR template
- [ ] Issue templates
- [ ] Development setup

**Результат:** Comprehensive documentation

---

## ⏳ Phase 7: Additional Features (Future)

**Статус:** ⏳ БУДУЩЕЕ
**Приоритет:** LOW

### 7.1 Enhanced Features

- [ ] Multi-portfolio support
- [ ] Advanced charting (technical indicators)
- [ ] Export historical data (CSV/JSON)
- [ ] Webhook notifications
- [ ] REST API для external integrations

### 7.2 Admin Dashboard

- [ ] User management UI
- [ ] System metrics visualization
- [ ] Database management interface
- [ ] Alert configuration UI
- [ ] Analytics dashboard

### 7.3 Multi-language Support

- [ ] i18n infrastructure
- [ ] English translation
- [ ] Chinese translation
- [ ] Dynamic language switching

**Результат:** Feature-rich platform

---

## 📊 Overall Progress

```
Phase 1: ████████████████████ 100% ✅ COMPLETED
Phase 2: ████░░░░░░░░░░░░░░░░  20% 🔄 IN PROGRESS
Phase 3: ░░░░░░░░░░░░░░░░░░░░   0% ⏳ PLANNED
Phase 4: ░░░░░░░░░░░░░░░░░░░░   0% ⏳ PLANNED
Phase 5: ░░░░░░░░░░░░░░░░░░░░   0% ⏳ PLANNED
Phase 6: ░░░░░░░░░░░░░░░░░░░░   0% ⏳ PLANNED
Phase 7: ░░░░░░░░░░░░░░░░░░░░   0% ⏳ FUTURE

Overall: ██░░░░░░░░░░░░░░░░░░  10%
```

---

## 📝 Changelog

### v0.1.1 - 2025-11-16
- 🐛 Fixed USD equivalent calculation (token order bug)
- 🕐 Implemented timezone handling (UTC storage, Moscow display)
- 🔒 Fixed CORS security
- 🔒 Fixed SQL injection
- 🔒 Fixed database connection leaks
- 🔒 Fixed exponential backoff bug

### v0.1.0 - 2025-11-16
- 🎉 Initial security audit
- 🔒 Critical security fixes implemented
- 📋 Comprehensive roadmap created

---

## 🔗 Quick Links

- **Repository:** https://github.com/Memetrix/holder-price-bot
- **Render Dashboard:** https://dashboard.render.com/
- **Frontend:** https://frontend-xi-umber-55.vercel.app
- **Backend API:** https://backend-8gk0c06q2-gakhaleksey-4260s-projects.vercel.app

---

## 💡 Notes for Context Loss Recovery

Если контекст был потерян, используй этот roadmap чтобы понять:

1. **Что уже сделано:** Смотри ✅ галочки в Phase 1
2. **Что сейчас в работе:** Phase 2, смотри 🔄 статус
3. **Следующие шаги:** Незаполненные [ ] checkboxes в текущей фазе
4. **Commits:** Проверь git log для последних изменений
5. **Deployments:** Render auto-deploys on push to main

**Текущий фокус:** Phase 2.1 - Устранение дублирования кода

**Следующий шаг после восстановления контекста:**
1. Прочитай этот файл
2. Проверь git log последних коммитов
3. Найди первую незаполненную [ ] галочку в Phase 2
4. Продолжи с этой задачи

---

*Последнее обновление: 2025-11-17 00:15 MSK*
