# Quick Start Guide 🚀

Быстрый старт HOLDER Price Bot за 5 минут

## 1️⃣ Создать бота

```bash
# Открой @BotFather в Telegram и получи токен
/newbot
```

## 2️⃣ Склонировать и настроить

```bash
# Клонировать репозиторий
git clone https://github.com/Memetrix/holder-price-bot.git
cd holder-price-bot

# Скопировать .env файл
cp .env.example .env

# Отредактировать .env и вставить BOT_TOKEN
nano .env
```

## 3️⃣ Запустить с Docker (Рекомендуется)

```bash
docker-compose up -d
```

**Готово!** Бот работает. Открой его в Telegram.

## 4️⃣ Или запустить локально

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить бота
python bot/main.py
```

## 5️⃣ (Опционально) Запустить Mini App

```bash
# Терминал 1: Backend
python -m uvicorn miniapp.backend.app.main:app --host 0.0.0.0 --port 8000

# Терминал 2: Frontend
cd miniapp/frontend
npm install
npm run dev
```

Mini App доступен на `http://localhost:3000`

## 📝 Что дальше?

- Попробуй команды: `/start`, `/price`, `/stats`
- Настрой уведомления: `/alerts on`
- Добавь в портфель: `/portfolio add 1000 0.05`
- Проверь арбитраж: `/arbitrage`

## 🆘 Проблемы?

- Проверь BOT_TOKEN в .env
- Посмотри логи: `docker-compose logs -f`
- Прочитай FAQ в README.md

## 📚 Полная документация

См. [README.md](README.md)
