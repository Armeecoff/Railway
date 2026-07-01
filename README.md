# ⚡ Telegram Multi-Tool v2.0 — Bot Interface

Управление 74+ функциями автоматизации Telegram-аккаунтов через Telegram-бота.

## 🚀 Деплой на Railway

### 1. Форкни/загрузи репозиторий на GitHub

```bash
git clone <твой-репо>
cd <репо>
```

### 2. Создай проект на Railway

1. Зайди на [railway.com](https://railway.com)
2. **New Project → Deploy from GitHub repo**
3. Выбери свой репозиторий

### 3. Добавь переменные окружения в Railway

В разделе **Variables** добавь:

| Переменная | Значение | Где взять |
|---|---|---|
| `BOT_TOKEN` | `123456:ABC...` | [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | `123456789` | [@userinfobot](https://t.me/userinfobot) |
| `GEMINI_API_KEY` | `AIzaSy...` | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `API_ID` | `2040` | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `API_HASH` | `b18441...` | [my.telegram.org/apps](https://my.telegram.org/apps) |

> `ADMIN_IDS` — несколько ID через запятую: `123,456,789`

### 4. Railway автоматически запустит бота

Railway найдёт `railway.toml` и выполнит `python bot.py`.

---

## 💻 Локальный запуск

```bash
# Установи зависимости
pip install -r requirements.txt

# Настрой config.json
cp .env.example .env  # для справки

# Запусти бота
python bot.py

# Или консольный интерфейс
python main.py
```

Заполни `config.json`:
```json
{
  "api_id": 12345,
  "api_hash": "твой_хеш",
  "bot_token": "токен_от_BotFather",
  "admin_ids": [123456789],
  "gemini_api_key": "AIzaSy..."
}
```

---

## 📁 Структура проекта

```
├── bot.py           — Telegram-бот (aiogram)
├── main.py          — Консольный интерфейс + все функции (Telethon)
├── config.json      — Настройки (api_id, bot_token, и т.д.)
├── requirements.txt — Зависимости Python
├── Procfile         — Для Railway/Heroku
├── railway.toml     — Конфигурация Railway
├── sessions/        — .session файлы аккаунтов
├── proxies.txt      — Список прокси (по одному на строку)
└── scenarios/       — Сохранённые сценарии
```

---

## 🤖 Команды бота

| Команда | Описание |
|---|---|
| `/start` | Запуск и главное меню |
| `/menu` | Открыть меню (74+ пункта) |
| `/sessions` | Список загруженных сессий |
| `/status` | Статус бота и сессий |
| `/cancel` | Прервать текущее действие |
| `/setup` | Информация о настройках |
| `/help` | Справка |

📎 **Загрузка сессий**: просто отправь боту `.session` файл — он сохранится автоматически.

---

## 🔑 Получение Gemini API ключа (бесплатно)

1. Зайди на [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Нажми **Create API key**
3. Скопируй ключ (начинается с `AIza...`)
4. Добавь в `config.json` или переменную окружения `GEMINI_API_KEY`

Используется модель **`gemini-2.5-flash`** — лучшая бесплатная модель на июль 2026.

---

## 📋 Прокси

Добавь прокси в `proxies.txt` (по одному на строку):
```
socks5://user:pass@ip:port
socks5://ip:port
http://ip:port
```

---

## ⚠️ Важно

- Файлы `.session` содержат доступ к аккаунтам — не делись ими
- `config.json` добавлен в `.gitignore` — не коммить его с токенами
- На Railway сессии хранятся в папке `sessions/` (не персистентны между деплоями — загружай через бота)
