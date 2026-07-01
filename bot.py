#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot.py — Telegram Bot Interface for TG Multi-Tool v2.0
Управление всеми функциями через Telegram-бота.
Запуск: python bot.py
"""

import os
import sys
import json
import asyncio
import threading
import re
import builtins
import queue as thread_queue
from pathlib import Path
from typing import Optional, Dict, List

# ═══════════════════════════════════════════════════════════════
# ПАТЧ ВВОДА/ВЫВОДА — ДОЛЖЕН БЫТЬ ДО ИМПОРТА main.py
# ═══════════════════════════════════════════════════════════════

_thread_local = threading.local()
_original_input = builtins.input
_original_print = builtins.print

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[mKGHFJ]')


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub('', text)


def _patched_input(prompt=""):
    session = getattr(_thread_local, 'bot_session', None)
    if session is not None:
        return session._get_input(prompt)
    return _original_input(prompt)


def _patched_print(*args, sep=" ", end="\n", file=None, flush=False):
    session = getattr(_thread_local, 'bot_session', None)
    if session is not None and file is None:
        text = sep.join(str(a) for a in args)
        clean = _strip_ansi(text)
        if clean.strip():
            session._put_output(clean)
    else:
        _original_print(*args, sep=sep, end=end, file=file, flush=flush)


builtins.input = _patched_input
builtins.print = _patched_print

# ═══════════════════════════════════════════════════════════════
# ИМПОРТЫ
# ═══════════════════════════════════════════════════════════════

try:
    from aiogram import Bot, Dispatcher, Router, F
    from aiogram.types import (
        Message, CallbackQuery,
        InlineKeyboardMarkup, InlineKeyboardButton,
    )
    from aiogram.filters import Command
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
except ImportError:
    _original_print("❌ Установите: pip install aiogram")
    sys.exit(1)

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    import main as tg_main
except Exception as e:
    _original_print(f"❌ Ошибка импорта main.py: {e}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

CONFIG_FILE = BASE_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_bot_settings():
    cfg = load_config()
    bot_token = cfg.get("bot_token", os.environ.get("BOT_TOKEN", ""))
    raw_ids = cfg.get("admin_ids", os.environ.get("ADMIN_IDS", ""))
    if isinstance(raw_ids, list):
        admin_ids = [int(x) for x in raw_ids if str(x).isdigit()]
    elif isinstance(raw_ids, str) and raw_ids:
        admin_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]
    else:
        admin_ids = []
    gemini_key = cfg.get("gemini_api_key", os.environ.get("GEMINI_API_KEY", ""))
    return bot_token, admin_ids, gemini_key


# ═══════════════════════════════════════════════════════════════
# КАРТА МЕНЮ
# ═══════════════════════════════════════════════════════════════

MENU_ITEMS: Dict[int, str] = {
    1:  "👁 Просмотр поста",
    2:  "👍 Реакция",
    3:  "📢 Подписка",
    4:  "🚀 Всё сразу",
    5:  "💬 Комментарий",
    6:  "📤 Пересылка",
    7:  "📊 Голосование",
    8:  "🔘 Inline кнопки",
    9:  "💥 Массовая реакция",
    10: "🤖 Авто-старт бота",
    11: "📋 Сценарий бота из JSON",
    12: "🌐 WebApp + startapp",
    13: "📨 Рассылка в ЛС",
    14: "👥 Инвайт",
    15: "📝 Отправка с медиа",
    16: "⏰ Отложенная отправка",
    17: "✏️ Редактирование сообщения",
    18: "📌 Закреп/откреп",
    19: "🗑 Удалить свои сообщения",
    20: "➕ Создать канал/группу",
    21: "⚙️ Настройка канала",
    22: "👑 Назначить админа",
    23: "🔨 Массовый бан/кик",
    24: "🧹 Очистка канала",
    25: "📋 Копировать канал",
    26: "🚨 Репорт юзер/канал",
    27: "🚨 Репорт сообщение",
    28: "🚫 Массовая блокировка",
    29: "🔍 Парсер участников",
    30: "📊 Статистика канала",
    31: "📥 Скачивание медиа",
    32: "👀 Мониторинг",
    33: "🤖 Авто-ответчик",
    34: "📝 Авто-постинг",
    35: "📋 Задачи из JSON",
    36: "🔥 Прогрев аккаунтов",
    37: "🟢 Имитация онлайна",
    38: "✅ Чекер сессий",
    39: "📱 Активные сессии",
    40: "💀 Сброс ВСЕХ сессий",
    41: "🎯 Выборочный сброс",
    42: "🔑 Запрос кода + 2FA",
    43: "ℹ️ Инфо об аккаунте",
    44: "✏️ Имя / Био",
    45: "🖼 Фото профиля",
    46: "🔐 2FA",
    47: "🚪 Отписка от каналов",
    48: "☠️ Удалить аккаунт",
    49: "👤 Изменить Username",
    50: "📥 Парсинг личных сообщений",
    51: "💎 Премиум реакция",
    52: "📋 Список сессий",
    53: "🌐 Список прокси",
    54: "👀 Авто-просмотры будущих постов",
    55: "➕ Массовое создание каналов",
    56: "👑 Передача прав владельца",
    57: "👀 Накрутка просмотров N постов",
    58: "📧 Смена Email",
    59: "🚫 Проверка спам-блока",
    60: "🎭 Конструктор сценариев",
    61: "🗑 Удаление файла сессии",
    62: "👁 Накрутка просмотров историй",
    63: "❤️ Реакция на историю",
    64: "🔍 Поиск пользователя",
    65: "👥 Общие группы двух юзеров",
    66: "🔑 Фильтрация постов по словам",
    67: "📋 Копирование контактов",
    68: "🛡 Авто-модерация",
    69: "📤 Форвард с фильтром",
    70: "📂 Копирование истории канала",
    71: "⏰ Расписание задач",
    72: "🚫 Авто-обход спам-блока",
    73: "📂 Браузер диалогов",
    74: "🔗 Авто-подписка по кнопкам",
    75: "🤖 Gemini AI Ассистент",
}

# Карта action-функций: добавляем пункты 49-74 (в main() они обрабатываются явно)
EXTRA_ACTIONS: Dict[int, any] = {
    49: tg_main.action_update_username,
    50: tg_main.action_parse_messages,
    51: tg_main.action_premium_reaction,
    52: tg_main.action_list_sessions,
    53: tg_main.action_list_proxies,
    54: tg_main.action_monitor_future,
    55: tg_main.action_mass_create_channels,
    56: tg_main.action_transfer_ownership,
    57: tg_main.action_add_views_n_posts,
    58: tg_main.action_change_email,
    59: tg_main.action_check_spambot,
    60: tg_main.action_scenario_constructor,
    61: tg_main.action_delete_session_files,
    62: tg_main.action_story_view,
    63: tg_main.action_story_reaction,
    64: tg_main.action_search_user,
    65: tg_main.action_common_chats,
    66: tg_main.action_filter_posts,
    67: tg_main.action_copy_contacts,
    68: tg_main.action_auto_moderation,
    69: tg_main.action_forward_filtered,
    70: tg_main.action_copy_channel_history,
    71: tg_main.action_task_scheduler,
    72: tg_main.action_antispam_bypass,
    73: tg_main.action_browse_account,
    74: tg_main.action_subscribe_and_check,
}


def resolve_action(num: int):
    """Возвращает action-функцию по номеру пункта меню"""
    if num in EXTRA_ACTIONS:
        return EXTRA_ACTIONS[num]
    return tg_main.ACTION_MAP.get(num)


# ═══════════════════════════════════════════════════════════════
# СЕССИЯ ПОЛЬЗОВАТЕЛЯ (управление вводом/выводом)
# ═══════════════════════════════════════════════════════════════

class BotSession:
    """Управляет I/O одного пользователя бота."""

    def __init__(self, bot: Bot, chat_id: int, main_loop: asyncio.AbstractEventLoop):
        self.bot = bot
        self.chat_id = chat_id
        self.main_loop = main_loop
        self.input_queue: thread_queue.Queue = thread_queue.Queue()
        self.running = False
        self.thread: Optional[threading.Thread] = None

    # ─── вызывается из рабочего потока ─────────────────────────

    def _get_input(self, prompt: str = "") -> str:
        clean = _strip_ansi(str(prompt)).strip()
        if clean:
            self._send_sync(f"📥 {clean}")
        try:
            value = self.input_queue.get(timeout=600)
        except thread_queue.Empty:
            raise EOFError("Таймаут ожидания ввода (10 мин)")
        return value

    def _put_output(self, text: str):
        self._send_sync(text)

    def _send_sync(self, text: str):
        text = str(text)
        if not text.strip():
            return
        chunks = [text[i:i + 3800] for i in range(0, len(text), 3800)]
        for chunk in chunks:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._async_send(chunk), self.main_loop
                )
                future.result(timeout=30)
            except Exception as e:
                _original_print(f"[BOT SEND ERROR] {e}")

    async def _async_send(self, text: str):
        try:
            await self.bot.send_message(self.chat_id, text)
        except Exception as e:
            _original_print(f"[BOT] send_message error: {e}")

    # ─── вызывается из async-контекста бота ────────────────────

    def feed_input(self, text: str):
        self.input_queue.put(text)

    def run_action(self, action_num: int) -> bool:
        if self.running:
            return False
        fn = resolve_action(action_num)
        if fn is None:
            return False
        self.running = True

        def thread_target():
            _thread_local.bot_session = self
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = fn()
                if asyncio.iscoroutine(result):
                    loop.run_until_complete(result)
            except EOFError as e:
                self._put_output(f"⏱ Завершено по таймауту: {e}")
            except KeyboardInterrupt:
                self._put_output("⏹ Прервано")
            except Exception as e:
                import traceback
                self._put_output(f"❌ Ошибка: {e}\n{traceback.format_exc()[-500:]}")
            finally:
                loop.close()
                self.running = False
                asyncio.run_coroutine_threadsafe(
                    self._async_send("✅ Готово. /menu — вернуться в меню."),
                    self.main_loop
                )

        self.thread = threading.Thread(target=thread_target, daemon=True, name=f"action-{action_num}")
        self.thread.start()
        return True


# ═══════════════════════════════════════════════════════════════
# FSM СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════════════

class S(StatesGroup):
    waiting_input = State()
    gemini_chat = State()


# ═══════════════════════════════════════════════════════════════
# РОУТЕР И КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════════

router = Router()
user_sessions: Dict[int, BotSession] = {}

ITEMS_PER_PAGE = 18


def make_menu_kb(page: int = 0) -> InlineKeyboardMarkup:
    items = list(MENU_ITEMS.items())
    total = len(items)
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start = page * ITEMS_PER_PAGE
    chunk = items[start:start + ITEMS_PER_PAGE]

    rows = []
    pair = []
    for num, name in chunk:
        pair.append(InlineKeyboardButton(
            text=f"{num}. {name[:22]}",
            callback_data=f"run:{num}"
        ))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"pg:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"pg:{page + 1}"))
    rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def is_admin(uid: int) -> bool:
    _, admin_ids, _ = get_bot_settings()
    if not admin_ids:
        return True
    return uid in admin_ids


# ═══════════════════════════════════════════════════════════════
# КОМАНДЫ
# ═══════════════════════════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return
    await state.clear()
    sessions_n = len(tg_main.get_sessions())
    await message.answer(
        f"⚡ *Telegram Multi-Tool v2.0*\n\n"
        f"📂 Сессий загружено: *{sessions_n}*\n\n"
        f"Выбери нужный пункт из меню:",
        parse_mode="Markdown",
        reply_markup=make_menu_kb(0)
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    if uid in user_sessions and user_sessions[uid].running:
        await message.answer(
            "⚠️ Сейчас выполняется действие. Подожди или /cancel для отмены."
        )
        return
    await state.clear()
    await message.answer("📋 Главное меню:", reply_markup=make_menu_kb(0))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    uid = message.from_user.id
    sess = user_sessions.get(uid)
    if sess and sess.running:
        sess.feed_input("")
        sess.running = False
        await message.answer("⏹ Действие отменено.")
    await state.clear()
    await message.answer("Нажми /menu для возврата в меню.")


@router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    sess = user_sessions.get(uid)
    status = "🔄 Выполняется" if (sess and sess.running) else "💤 Свободен"
    sessions_n = len(tg_main.get_sessions())
    _, admin_ids, gemini_key = get_bot_settings()
    await message.answer(
        f"📊 *Статус*\n\n"
        f"• Состояние: {status}\n"
        f"• TG-сессий: *{sessions_n}*\n"
        f"• Gemini AI: {'✅ Подключён' if gemini_key else '❌ Не настроен'}\n"
        f"• Твой ID: `{uid}`\n"
        f"• Админы: `{admin_ids if admin_ids else 'все'}`",
        parse_mode="Markdown"
    )


@router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    cfg = load_config()
    await message.answer(
        f"⚙️ *Настройки (config.json)*\n\n"
        f"• `bot_token` — токен бота от @BotFather\n"
        f"• `admin_ids` — список ваших Telegram ID (через запятую)\n"
        f"• `gemini_api_key` — ключ Gemini API (пункт 75)\n"
        f"• `api_id` / `api_hash` — данные для Telethon\n\n"
        f"Текущее состояние:\n"
        f"  bot\\_token: `{'✅' if cfg.get('bot_token') else '❌'}`\n"
        f"  admin\\_ids: `{cfg.get('admin_ids', '❌ не задано')}`\n"
        f"  gemini\\_api\\_key: `{'✅' if cfg.get('gemini_api_key') else '❌'}`",
        parse_mode="Markdown"
    )


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📖 *Команды бота*\n\n"
        "/start — приветствие и меню\n"
        "/menu — открыть меню (74+ пункта)\n"
        "/sessions — список загруженных сессий\n"
        "/status — статус бота и сессий\n"
        "/cancel — отменить текущее действие\n"
        "/setup — информация о настройках\n"
        "/help — эта справка\n\n"
        "📎 *Загрузка сессий:* просто отправь боту `.session` файл — он сохранится автоматически.\n\n"
        "💡 Нажимай кнопки в меню и отвечай на вопросы бота.\n"
        "🤖 Пункт 75 — Gemini AI выполняет команды по описанию на русском языке.",
        parse_mode="Markdown"
    )


# ═══════════════════════════════════════════════════════════════
# INLINE CALLBACKS
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("pg:"))
async def cb_page(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    try:
        await call.message.edit_reply_markup(reply_markup=make_menu_kb(page))
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


@router.callback_query(F.data.startswith("run:"))
async def cb_run(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет доступа", show_alert=True)
        return

    num = int(call.data.split(":")[1])
    uid = call.from_user.id

    # ─── Пункт 75: Gemini AI ───────────────────────────────────
    if num == 75:
        _, _, gemini_key = get_bot_settings()
        if not gemini_key:
            await call.message.answer(
                "❌ Gemini API ключ не настроен.\n\n"
                "Добавь в config.json:\n"
                '`"gemini_api_key": "ВАШ_КЛЮЧ"`\n\n'
                "Ключ получи на: https://aistudio.google.com/app/apikey",
                parse_mode="Markdown"
            )
            await call.answer()
            return
        await call.message.answer(
            "🤖 *Gemini AI Ассистент*\n\n"
            "Напиши что нужно сделать с аккаунтами, например:\n"
            "• «Подпишись на @durov от всех аккаунтов»\n"
            "• «Поставь реакцию 👍 на пост https://t.me/channel/123»\n"
            "• «Проверь все сессии на бан»\n"
            "• «Покажи список прокси»\n\n"
            "/cancel — выход из режима Gemini",
            parse_mode="Markdown"
        )
        await state.set_state(S.gemini_chat)
        await call.answer()
        return

    # ─── Обычный пункт ─────────────────────────────────────────
    if uid in user_sessions and user_sessions[uid].running:
        await call.answer("⚠️ Уже выполняется другое действие!", show_alert=True)
        return

    fn = resolve_action(num)
    if fn is None:
        await call.answer(f"❌ Действие {num} не найдено", show_alert=True)
        return

    main_loop = asyncio.get_event_loop()
    sess = BotSession(bot, call.message.chat.id, main_loop)
    user_sessions[uid] = sess

    name = MENU_ITEMS.get(num, f"Пункт {num}")
    await call.message.answer(
        f"▶️ *{name}*\n\n"
        f"Отвечай на вопросы в чате.\n"
        f"/cancel — прервать выполнение.",
        parse_mode="Markdown"
    )

    ok = sess.run_action(num)
    if not ok:
        await call.message.answer("❌ Не удалось запустить действие.")
    else:
        await state.set_state(S.waiting_input)

    await call.answer()


# ═══════════════════════════════════════════════════════════════
# ОБРАБОТКА ВВОДА ПОЛЬЗОВАТЕЛЯ
# ═══════════════════════════════════════════════════════════════

@router.message(S.waiting_input)
async def handle_user_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    sess = user_sessions.get(uid)

    if not sess:
        await state.clear()
        await message.answer("❌ Нет активной сессии. /menu")
        return

    if not sess.running:
        await state.clear()
        await message.answer("✅ Действие завершено. /menu")
        return

    sess.feed_input(message.text or "")


# ═══════════════════════════════════════════════════════════════
# GEMINI AI РЕЖИМ
# ═══════════════════════════════════════════════════════════════

@router.message(S.gemini_chat)
async def handle_gemini(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    _, _, gemini_key = get_bot_settings()
    uid = message.from_user.id
    user_text = message.text or ""

    thinking_msg = await message.answer("🤔 Анализирую запрос...")

    try:
        import aiohttp

        menu_list = "\n".join(f"{k}: {v}" for k, v in MENU_ITEMS.items() if k != 75)
        sessions_list = tg_main.get_sessions()
        sess_str = ", ".join(sessions_list[:15]) + ("..." if len(sessions_list) > 15 else "") if sessions_list else "нет"

        prompt = f"""Ты — умный помощник для управления Telegram-аккаунтами через TG Multi-Tool.

Доступные команды (номер меню: описание):
{menu_list}

Доступные Telegram-сессии (аккаунты): {sess_str}
Количество аккаунтов: {len(sessions_list)}

Запрос пользователя: "{user_text}"

Проанализируй запрос и определи нужную команду.
Ответь СТРОГО в формате JSON (ничего кроме JSON):
{{
  "action_num": <номер команды или 0 если непонятно>,
  "action_name": "<название команды>",
  "explanation": "<объясни что будет сделано на русском языке>",
  "can_execute": true/false
}}

Если запрос непонятен, невозможен или не соответствует ни одной команде — верни action_num: 0 и can_execute: false."""

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={gemini_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    await thinking_msg.delete()
                    await message.answer(
                        f"❌ Ошибка Gemini API (HTTP {resp.status}):\n"
                        f"`{err[:300]}`\n\n"
                        f"Проверь правильность `gemini_api_key` в config.json.\n"
                        f"Ключ получи на: https://aistudio.google.com/app/apikey",
                        parse_mode="Markdown"
                    )
                    await state.clear()
                    return
                data_raw = await resp.json()

        raw = data_raw["candidates"][0]["content"]["parts"][0]["text"].strip()

        json_match = re.search(r'\{[\s\S]*\}', raw)
        if not json_match:
            await thinking_msg.delete()
            await message.answer(f"🤖 Gemini отвечает:\n\n{raw}")
            return

        data = json.loads(json_match.group())
        action_num = int(data.get("action_num", 0))
        explanation = data.get("explanation", "")
        can_execute = data.get("can_execute", False)
        action_name = data.get("action_name", "")

        await thinking_msg.delete()

        if not can_execute or action_num == 0:
            await message.answer(
                f"🤖 *Gemini:*\n\n{explanation}\n\n"
                f"Попробуй уточнить запрос или используй /menu.",
                parse_mode="Markdown"
            )
            return

        await message.answer(
            f"🤖 *Gemini определил команду:*\n\n"
            f"▶️ [{action_num}] {action_name}\n\n"
            f"📋 {explanation}\n\n"
            f"Запускаю...",
            parse_mode="Markdown"
        )

        if uid in user_sessions and user_sessions[uid].running:
            await message.answer("⚠️ Уже выполняется другое действие!")
            return

        fn = resolve_action(action_num)
        if fn is None:
            await message.answer(f"❌ Команда {action_num} не найдена.")
            await state.clear()
            return

        main_loop = asyncio.get_event_loop()
        sess = BotSession(bot, message.chat.id, main_loop)
        user_sessions[uid] = sess

        ok = sess.run_action(action_num)
        if ok:
            await state.set_state(S.waiting_input)
        else:
            await message.answer("❌ Не удалось запустить команду.")
            await state.clear()

    except json.JSONDecodeError:
        await thinking_msg.delete()
        await message.answer("❌ Gemini вернул неверный ответ. Попробуй ещё раз.")
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(f"❌ Ошибка Gemini: {e}")
        await state.clear()


# ═══════════════════════════════════════════════════════════════
# ЗАГРУЗКА .SESSION ФАЙЛОВ
# ═══════════════════════════════════════════════════════════════

@router.message(F.document)
async def handle_document(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    doc = message.document
    fname = doc.file_name or ""

    # Принимаем .session и .json файлы (Telethon session + metadata)
    if not (fname.endswith(".session") or fname.endswith(".session.json")):
        # Если не session-файл — передаём в активную сессию как текст
        uid = message.from_user.id
        sess = user_sessions.get(uid)
        if sess and sess.running:
            sess.feed_input(fname)
        else:
            await message.answer(
                "📎 Для загрузки Telegram-сессии отправь файл с расширением `.session`",
                parse_mode="Markdown"
            )
        return

    # Проверяем размер (session-файл не должен быть огромным)
    if doc.file_size and doc.file_size > 5 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой (макс. 5 МБ)")
        return

    sessions_dir = tg_main.SESSIONS_DIR
    dest = sessions_dir / fname

    # Не перезаписываем существующие без подтверждения
    existed = dest.exists()

    try:
        file_info = await bot.get_file(doc.file_id)
        file_bytes = await bot.download_file(file_info.file_path)
        with open(dest, "wb") as f:
            f.write(file_bytes.read())

        sessions_total = len(tg_main.get_sessions())
        status = "♻️ Перезаписан" if existed else "✅ Добавлен"
        await message.answer(
            f"{status}: `{fname}`\n\n"
            f"📂 Сессий всего: *{sessions_total}*\n\n"
            f"Используй пункт *38 (Чекер)* чтобы проверить сессию.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка сохранения: {e}")


@router.message(Command("sessions"))
async def cmd_sessions(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    sessions = tg_main.get_sessions()
    if not sessions:
        await message.answer(
            "📂 *Сессии не найдены*\n\n"
            "Отправь боту `.session` файл чтобы добавить аккаунт.",
            parse_mode="Markdown"
        )
        return
    lines = "\n".join(f"  {i+1}. `{s}`" for i, s in enumerate(sessions))
    await message.answer(
        f"📋 *Загруженные сессии ({len(sessions)}):*\n\n{lines}\n\n"
        f"💡 Отправь `.session` файл боту — он автоматически добавится.",
        parse_mode="Markdown"
    )


# ═══════════════════════════════════════════════════════════════
# СООБЩЕНИЯ БЕЗ СОСТОЯНИЯ (fallback)
# ═══════════════════════════════════════════════════════════════

@router.message()
async def handle_any(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    uid = message.from_user.id
    sess = user_sessions.get(uid)

    # Если есть активная сессия — кормим ввод
    if sess and sess.running:
        sess.feed_input(message.text or "")
        await state.set_state(S.waiting_input)
        return

    await message.answer(
        "📋 /menu — главное меню\n"
        "📂 /sessions — список сессий\n"
        "📊 /status — статус\n"
        "⚙️ /setup — настройки\n"
        "❓ /help — справка\n"
        "❌ /cancel — отмена действия\n\n"
        "💡 Отправь `.session` файл — он добавится автоматически"
    )


# ═══════════════════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════════════════

async def run_bot():
    bot_token, admin_ids, gemini_key = get_bot_settings()

    # Railway/production: токен берётся из переменных окружения — интерактивный ввод не нужен
    is_interactive = os.environ.get("RAILWAY_ENVIRONMENT") is None and os.environ.get("CI") is None

    if not bot_token and is_interactive:
        _original_print("\n" + "=" * 50)
        _original_print("⚡  TELEGRAM MULTI-TOOL BOT — ПЕРВЫЙ ЗАПУСК")
        _original_print("=" * 50)
        _original_print("Нужно настроить бота. Данные сохранятся в config.json\n")

        cfg = load_config()

        bot_token = _original_input("🔑 BOT_TOKEN (от @BotFather): ").strip()
        if not bot_token:
            _original_print("❌ BOT_TOKEN не введён. Выход.")
            return

        admin_raw = _original_input("👤 Твой Telegram ID (можно несколько через запятую): ").strip()
        gemini_raw = _original_input("🤖 GEMINI_API_KEY (Enter для пропуска): ").strip()

        cfg["bot_token"] = bot_token
        cfg["admin_ids"] = [int(x.strip()) for x in admin_raw.split(",") if x.strip().isdigit()]
        if gemini_raw:
            cfg["gemini_api_key"] = gemini_raw

        save_config(cfg)
        _original_print("\n✅ Настройки сохранены в config.json")
        bot_token, admin_ids, gemini_key = get_bot_settings()

    if not bot_token:
        _original_print("❌ BOT_TOKEN не задан.")
        _original_print("   Локально: добавь в config.json поле \"bot_token\"")
        _original_print("   Railway:   добавь переменную окружения BOT_TOKEN")
        return

    sessions_n = len(tg_main.get_sessions())
    _original_print("\n" + "=" * 50)
    _original_print("⚡  TELEGRAM MULTI-TOOL BOT")
    _original_print("=" * 50)
    _original_print(f"📂 TG-сессий загружено : {sessions_n}")
    _original_print(f"👥 Админы             : {admin_ids if admin_ids else 'все (не ограничено)'}")
    _original_print(f"🤖 Gemini AI          : {'✅ подключён' if gemini_key else '❌ не настроен'}")
    _original_print("=" * 50)

    bot = Bot(token=bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    try:
        me = await bot.get_me()
        _original_print(f"✅ Бот запущен: @{me.username}")
        _original_print("   Напиши /start в Telegram\n")
    except Exception as e:
        _original_print(f"❌ Ошибка подключения: {e}")
        return

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        _original_print("\n👋 Бот остановлен.")
    except Exception as e:
        _original_print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
