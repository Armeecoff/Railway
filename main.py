#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Multi-Tool v2.0
Файл: tg_tool.py
Требования: pip install telethon python-socks aiohttp cryptg
Структура:
  sessions/  — папка с .session файлами
  proxies.txt — прокси (socks5://user:pass@ip:port или http://ip:port)
  config.json — API_ID, API_HASH
"""

# ═══════════════════════════════════════════════════════════════
# ЧАСТЬ 1 — ЯДРО: импорты, конфиг, утилиты, менеджер, меню
# ═══════════════════════════════════════════════════════════════

import os
import sys
import json
import glob
import time
import random
import asyncio
import hashlib
import re
import struct
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

try:
    from telethon import TelegramClient, events, errors, functions, types
    from telethon.tl.functions.messages import (
        GetMessagesViewsRequest, SendReactionRequest, ForwardMessagesRequest,
        SendVoteRequest, GetBotCallbackAnswerRequest, ReportRequest,
        DeleteMessagesRequest, EditMessageRequest, SearchRequest,
        GetHistoryRequest, ReadHistoryRequest, SendMessageRequest,
        UpdatePinnedMessageRequest, SendMediaRequest,
        GetScheduledHistoryRequest, SendScheduledMessagesRequest,
    )
    from telethon.tl.functions.channels import (
        JoinChannelRequest, LeaveChannelRequest, InviteToChannelRequest,
        EditBannedRequest, EditAdminRequest, CreateChannelRequest,
        EditPhotoRequest, EditTitleRequest, DeleteChannelRequest,
        GetParticipantsRequest, GetFullChannelRequest,
    )
    from telethon.tl.functions.account import (
        UpdateProfileRequest, UpdateUsernameRequest,
        GetAuthorizationsRequest, ResetAuthorizationRequest,
        DeleteAccountRequest, UpdateStatusRequest,
        GetPasswordRequest, CheckUsernameRequest,
    )
    from telethon.tl.functions.messages import (
        GetHistoryRequest, GetDialogsRequest,
    )
    from telethon.tl.functions.users import GetFullUserRequest
    from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
    from telethon.tl.functions.messages import (
        StartBotRequest, RequestWebViewRequest,
    )
    from telethon.tl.types import (
        ReactionEmoji, ReactionCustomEmoji,
        ChannelParticipantsSearch, ChannelParticipantsRecent,
        ChatBannedRights, ChatAdminRights,
        InputPeerChannel, InputPeerUser, InputChannel,
        InputReportReasonSpam, InputReportReasonViolence,
        InputReportReasonPornography, InputReportReasonChildAbuse,
        InputReportReasonOther, InputReportReasonFake,
        InputReportReasonGeoIrrelevant, InputReportReasonIllegalDrugs,
        InputReportReasonPersonalDetails,
        DocumentAttributeFilename,
        InputMediaUploadedDocument, InputMediaUploadedPhoto,
        MessageMediaDocument, MessageMediaPhoto,
        KeyboardButtonUrl, KeyboardButtonCallback,
        KeyboardButtonRequestPhone, ReplyInlineMarkup,
        PeerChannel, PeerUser, PeerChat,
        UpdateNewChannelMessage, UpdateNewMessage,
        Channel, Chat, User,
    )
    from telethon.errors import (
        SessionPasswordNeededError, FloodWaitError,
        UserAlreadyParticipantError, UserNotParticipantError,
        ChatWriteForbiddenError, ChannelPrivateError,
        ReactionInvalidError, PeerIdInvalidError,
        PhoneNumberBannedError, AuthKeyUnregisteredError,
        UserDeactivatedBanError, UserDeactivatedError,
    )
except ImportError:
    print("❌ Установите зависимости: pip install telethon python-socks aiohttp")
    sys.exit(1)

# ─── Логирование ───
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("TG-Tool")

# ─── Пути ───
BASE_DIR = Path(__file__).parent
SESSIONS_DIR = BASE_DIR / "sessions"
PROXIES_FILE = BASE_DIR / "proxies.txt"
CONFIG_FILE = BASE_DIR / "config.json"
SCENARIOS_DIR = BASE_DIR / "scenarios"

SESSIONS_DIR.mkdir(exist_ok=True)
SCENARIOS_DIR.mkdir(exist_ok=True)
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)


# ─── Цвета терминала ───
class C:
    R = "\033[91m"  # red
    G = "\033[92m"  # green
    Y = "\033[93m"  # yellow
    B = "\033[94m"  # blue
    M = "\033[95m"  # magenta
    CY = "\033[96m"  # cyan
    W = "\033[97m"  # white
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RST = "\033[0m"
    UNDERLINE = "\033[4m"


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def banner():
    print(f"""{C.CY}{C.BOLD}
  ╔══════════════════════════════════════════════════╗
  ║        ⚡ TELEGRAM MULTI-TOOL v2.0 ⚡           ║
  ║            Telethon + Proxy Engine               ║
  ╚══════════════════════════════════════════════════╝{C.RST}
""")


# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_api_credentials() -> Tuple[int, str]:
    cfg = load_config()
    api_id = cfg.get("api_id")
    api_hash = cfg.get("api_hash")
    if not api_id or not api_hash:
        print(f"{C.Y}⚠ Первый запуск — нужны API_ID и API_HASH{C.RST}")
        print(f"{C.DIM}  Получить: https://my.telegram.org/apps{C.RST}")
        api_id = int(input(f"{C.CY}  API_ID: {C.RST}").strip())
        api_hash = input(f"{C.CY}  API_HASH: {C.RST}").strip()
        cfg["api_id"] = api_id
        cfg["api_hash"] = api_hash
        save_config(cfg)
        print(f"{C.G}✅ Сохранено в config.json{C.RST}")
    return int(api_id), str(api_hash)


# ═══════════════════════════════════════════════════════════════
# ПРОКСИ
# ═══════════════════════════════════════════════════════════════

def load_proxies() -> List[dict]:
    """
    Формат proxies.txt (по одному на строку):
      socks5://user:pass@ip:port
      socks5://ip:port
      http://user:pass@ip:port
      http://ip:port
      socks4://ip:port
    """
    proxies = []
    if not PROXIES_FILE.exists():
        return proxies
    with open(PROXIES_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                p = parse_proxy(line)
                if p:
                    proxies.append(p)
            except Exception:
                pass
    return proxies


def parse_proxy(url: str) -> Optional[dict]:
    """Парсит строку прокси в dict для telethon"""
    url = url.strip()
    if "://" not in url:
        url = "socks5://" + url

    scheme = url.split("://")[0].lower()
    rest = url.split("://")[1]

    proxy_type = {
        "socks5": 2,  # python-socks SOCKS5
        "socks4": 1,
        "http": 3,
        "https": 3,
    }.get(scheme, 2)

    username = None
    password = None
    if "@" in rest:
        creds, hostport = rest.rsplit("@", 1)
        if ":" in creds:
            username, password = creds.split(":", 1)
        else:
            username = creds
    else:
        hostport = rest

    if ":" in hostport:
        host, port = hostport.rsplit(":", 1)
        port = int(port)
    else:
        host = hostport
        port = 1080

    return {
        "proxy_type": scheme,
        "addr": host,
        "port": port,
        "username": username,
        "password": password,
        "rdns": True,
    }


def proxy_to_telethon(p: dict) -> tuple:
    """Конвертирует proxy dict в формат для TelegramClient"""
    import socks
    ptype_map = {
        "socks5": socks.SOCKS5,
        "socks4": socks.SOCKS4,
        "http": socks.HTTP,
        "https": socks.HTTP,
    }
    return (
        ptype_map.get(p["proxy_type"], socks.SOCKS5),
        p["addr"],
        p["port"],
        p.get("rdns", True),
        p.get("username"),
        p.get("password"),
    )


def proxy_str(p: dict) -> str:
    if not p:
        return "без прокси"
    s = f"{p['proxy_type']}://"
    if p.get("username"):
        s += f"{p['username']}:{p['password']}@"
    s += f"{p['addr']}:{p['port']}"
    return s


# ═══════════════════════════════════════════════════════════════
# МЕНЕДЖЕР СЕССИЙ
# ═══════════════════════════════════════════════════════════════

def get_sessions() -> List[str]:
    """Возвращает список имён .session файлов (без расширения)"""
    files = glob.glob(str(SESSIONS_DIR / "*.session"))
    return [Path(f).stem for f in sorted(files)]


def list_sessions():
    sessions = get_sessions()
    if not sessions:
        print(f"{C.R}❌ Нет .session файлов в папке sessions/{C.RST}")
        return []
    print(f"\n{C.CY}{'─' * 50}")
    print(f"  📋 Найдено сессий: {len(sessions)}")
    print(f"{'─' * 50}{C.RST}")
    for i, s in enumerate(sessions, 1):
        print(f"  {C.W}{i:3}. {C.G}{s}{C.RST}")
    print(f"{C.CY}{'─' * 50}{C.RST}")
    return sessions


def select_sessions(prompt="Выбери сессии") -> List[str]:
    """
    Выбор сессий: all / 1,2,3 / 1-5 / конкретный номер
    """
    sessions = list_sessions()
    if not sessions:
        return []
    print(f"\n{C.Y}  {prompt}")
    print(f"  (all = все, 1,3,5 = конкретные, 1-10 = диапазон){C.RST}")
    choice = input(f"{C.CY}  > {C.RST}").strip().lower()

    if choice == "all":
        return sessions

    selected = set()
    parts = choice.replace(" ", "").split(",")
    for part in parts:
        if "-" in part:
            try:
                a, b = part.split("-")
                for i in range(int(a), int(b) + 1):
                    if 1 <= i <= len(sessions):
                        selected.add(sessions[i - 1])
            except ValueError:
                pass
        else:
            try:
                idx = int(part)
                if 1 <= idx <= len(sessions):
                    selected.add(sessions[idx - 1])
            except ValueError:
                pass
    return list(selected)


# ═══════════════════════════════════════════════════════════════
# СОЗДАНИЕ КЛИЕНТА
# ═══════════════════════════════════════════════════════════════

def _fix_session_db(session_path: str) -> bool:
    """
    Пытается починить .session файл при ошибке схемы:
    'too many values to unpack (expected 5)'.
    Обрезает лишние столбцы таблицы sessions до стандартных 5.
    Возвращает True если починка прошла успешно.
    """
    import sqlite3
    db_path = session_path + ".session"
    if not os.path.exists(db_path):
        db_path = session_path  # иногда путь уже с расширением
    if not os.path.exists(db_path):
        return False
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        # Получаем все строки таблицы sessions
        cur.execute("SELECT * FROM sessions")
        rows = cur.fetchall()
        cur.execute("PRAGMA table_info(sessions)")
        cols = [r[1] for r in cur.fetchall()]
        if len(cols) <= 5:
            con.close()
            return False  # уже нормально

        # Пересоздаём таблицу с 5 столбцами (стандарт Telethon)
        cur.execute("DROP TABLE IF EXISTS sessions_backup")
        cur.execute("ALTER TABLE sessions RENAME TO sessions_backup")
        cur.execute("""
            CREATE TABLE sessions (
                dc_id INTEGER PRIMARY KEY,
                server_address TEXT,
                port INTEGER,
                auth_key BLOB,
                takeout_id INTEGER
            )
        """)
        # Копируем только первые 5 столбцов
        for row in rows:
            cur.execute(
                "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?)",
                row[:5]
            )
        cur.execute("DROP TABLE sessions_backup")
        con.commit()
        con.close()
        return True
    except Exception as fix_err:
        logger.warning(f"Session fix failed: {fix_err}")
        try:
            con.close()
        except Exception:
            pass
        return False


async def create_client(session_name: str, proxy: dict = None) -> Optional[TelegramClient]:
    api_id, api_hash = get_api_credentials()
    session_path = str(SESSIONS_DIR / session_name)

    kwargs = {}
    if proxy:
        try:
            kwargs["proxy"] = proxy_to_telethon(proxy)
        except Exception as e:
            logger.warning(f"Proxy error: {e}")

    try:
        client = TelegramClient(
            session_path,
            api_id,
            api_hash,
            device_model="Samsung Galaxy S23",
            system_version="Android 14",
            app_version="10.14.5",
            lang_code="ru",
            system_lang_code="ru-RU",
            **kwargs
        )
        return client
    except ValueError as e:
        if "too many values to unpack" in str(e):
            print(f"  {C.Y}⚠ {session_name} — схема сессии устарела, пробую починить...{C.RST}")
            fixed = _fix_session_db(session_path)
            if fixed:
                print(f"  {C.G}  ✅ {session_name} — сессия починена, повтор...{C.RST}")
                try:
                    client = TelegramClient(
                        session_path,
                        api_id,
                        api_hash,
                        device_model="Samsung Galaxy S23",
                        system_version="Android 14",
                        app_version="10.14.5",
                        lang_code="ru",
                        system_lang_code="ru-RU",
                        **kwargs
                    )
                    return client
                except Exception as e2:
                    print(f"  {C.R}❌ {session_name} — после починки ошибка: {e2}{C.RST}")
                    return None
            else:
                print(f"  {C.R}❌ {session_name} — не удалось починить сессию. "
                      f"Обнови Telethon: pip install -U telethon{C.RST}")
                return None
        print(f"  {C.R}❌ {session_name} — ошибка создания клиента: {e}{C.RST}")
        return None
    except Exception as e:
        print(f"  {C.R}❌ {session_name} — ошибка создания клиента: {e}{C.RST}")
        return None


async def safe_connect(client: TelegramClient, session_name: str) -> bool:
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"  {C.R}❌ {session_name} — не авторизован{C.RST}")
            await client.disconnect()
            return False
        return True
    except (PhoneNumberBannedError, UserDeactivatedBanError, UserDeactivatedError):
        print(f"  {C.R}💀 {session_name} — аккаунт забанен/удалён{C.RST}")
        return False
    except (AuthKeyUnregisteredError,):
        print(f"  {C.R}🔑 {session_name} — сессия невалидна{C.RST}")
        return False
    except Exception as e:
        print(f"  {C.R}⚠ {session_name} — ошибка: {e}{C.RST}")
        return False


# ═══════════════════════════════════════════════════════════════
# УТИЛИТЫ ПАРСИНГА ССЫЛОК
# ═══════════════════════════════════════════════════════════════

def parse_tg_link(link: str) -> dict:
    """
    Парсит ссылку вида:
      https://t.me/channel/123
      https://t.me/c/1234567890/123
      https://t.me/channel
      https://t.me/+invite_hash
      @channel
      t.me/bot?start=ref
    Возвращает dict с ключами: channel, post_id, invite_hash, bot, start_param
    """
    result = {"channel": None, "post_id": None, "invite_hash": None,
              "bot": None, "start_param": None, "startapp": None}

    link = link.strip()

    # @channel
    if link.startswith("@"):
        result["channel"] = link[1:]
        return result

    # Нормализация
    link = link.replace("https://t.me/", "").replace("http://t.me/", "")
    link = link.replace("t.me/", "")

    # Инвайт
    if link.startswith("+") or link.startswith("joinchat/"):
        result["invite_hash"] = link.replace("joinchat/", "").lstrip("+")
        return result

    parts = link.split("?")
    path = parts[0].strip("/")
    params = {}
    if len(parts) > 1:
        for kv in parts[1].split("&"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k] = v

    segments = path.split("/")

    # bot?start=ref
    if "start" in params:
        result["bot"] = segments[0]
        result["start_param"] = params["start"]
        return result

    # webapp startapp
    if "startapp" in params:
        result["bot"] = segments[0]
        result["startapp"] = params["startapp"]
        return result

    # c/1234567890/123 (приватный канал)
    if len(segments) >= 3 and segments[0] == "c":
        result["channel"] = int(segments[1])
        result["post_id"] = int(segments[2])
        return result

    # channel/123
    if len(segments) >= 2:
        result["channel"] = segments[0]
        try:
            result["post_id"] = int(segments[1])
        except ValueError:
            pass
        return result

    # channel
    if len(segments) == 1:
        result["channel"] = segments[0]
        return result

    return result


async def resolve_channel(client, channel_input):
    """Резолвит канал по username, id или ссылке"""
    if isinstance(channel_input, int):
        try:
            entity = await client.get_entity(PeerChannel(channel_input))
            return entity
        except Exception:
            entity = await client.get_entity(channel_input)
            return entity
    return await client.get_entity(channel_input)


def random_delay(min_s=1.0, max_s=3.0):
    return random.uniform(min_s, max_s)


async def human_delay(min_s=0.5, max_s=2.5):
    await asyncio.sleep(random_delay(min_s, max_s))


def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ═══════════════════════════════════════════════════════════════
# EXECUTOR — запуск задач по сессиям
# ═══════════════════════════════════════════════════════════════

async def execute_on_sessions(
        sessions: List[str],
        task_func,
        task_name: str = "задача",
        max_concurrent: int = 5,
        delay_between: Tuple[float, float] = (1.0, 3.0),
        **kwargs
):
    """
    Запускает task_func(client, session_name, **kwargs) для каждой сессии
    с ограничением параллельности и задержками.
    """
    proxies = load_proxies()
    semaphore = asyncio.Semaphore(max_concurrent)
    results = {"success": 0, "fail": 0, "total": len(sessions)}

    print(f"\n{C.CY}{'═' * 50}")
    print(f"  🚀 {task_name}")
    print(f"  📊 Сессий: {len(sessions)} | Прокси: {len(proxies)}")
    print(f"{'═' * 50}{C.RST}\n")

    async def worker(session_name, index):
        async with semaphore:
            # Используем random.choice для случайного выбора прокси для каждого аккаунта
            proxy = random.choice(proxies) if proxies else None
            client = await create_client(session_name, proxy)
            if not client:
                results["fail"] += 1
                return

            try:
                ok = await safe_connect(client, session_name)
                if not ok:
                    results["fail"] += 1
                    return

                await task_func(client, session_name, **kwargs)
                results["success"] += 1
                print(f"  {C.G}✅ {session_name} — OK{C.RST}")
            except FloodWaitError as e:
                wait = e.seconds
                print(f"  {C.Y}⏳ {session_name} — FloodWait {wait}s{C.RST}")
                if wait < 120:
                    await asyncio.sleep(wait)
                    try:
                        await task_func(client, session_name, **kwargs)
                        results["success"] += 1
                        print(f"  {C.G}✅ {session_name} — OK (после ожидания){C.RST}")
                    except Exception as e2:
                        results["fail"] += 1
                        print(f"  {C.R}❌ {session_name} — {e2}{C.RST}")
                else:
                    results["fail"] += 1
            except Exception as e:
                results["fail"] += 1
                print(f"  {C.R}❌ {session_name} — {e}{C.RST}")
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass

            await asyncio.sleep(random_delay(*delay_between))

    tasks = [worker(s, i) for i, s in enumerate(sessions)]
    await asyncio.gather(*tasks)

    print(f"\n{C.CY}{'═' * 50}")
    print(f"  📊 Результат: {C.G}✅ {results['success']}{C.RST}"
          f" | {C.R}❌ {results['fail']}{C.RST}"
          f" | 📊 {results['total']} всего")
    print(f"{C.CY}{'═' * 50}{C.RST}")

    return results


# ═══════════════════════════════════════════════════════════════
# ФУНКЦИИ ИЗМЕНЕНИЯ И ПАРСИНГА
# ═══════════════════════════════════════════════════════════════

async def update_account_username(client, session_name, new_username):
    """Изменяет @username аккаунта"""
    try:
        # Проверка доступности
        available = await client(CheckUsernameRequest(new_username))
        if not available:
            print(f"  {C.R}❌ Username @{new_username} занят{C.RST}")
            return False

        await client(UpdateUsernameRequest(new_username))
        print(f"  {C.G}✅ Username изменен на @{new_username}{C.RST}")
        return True
    except Exception as e:
        print(f"  {C.R}❌ Ошибка изменения username: {e}{C.RST}")
        return False


async def parse_private_messages(client, session_name, limit=100):
    """Полный парсинг личных сообщений (диалогов)"""
    try:
        print(f"  {C.CY}📥 Парсинг сообщений для {session_name}...{C.RST}")
        dialogs = await client.get_dialogs(limit=limit)
        parsed_data = []

        for dialog in dialogs:
            if dialog.is_user:
                user = dialog.entity
                name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                username = f"@{user.username}" if user.username else "нет"

                # Получаем последние сообщения
                messages = await client.get_messages(user, limit=5)
                last_msgs = [m.text for m in messages if m.text]

                parsed_data.append({
                    "user_id": user.id,
                    "name": name,
                    "username": username,
                    "last_messages": last_msgs
                })
                print(f"    👤 {name} ({username}): {len(last_msgs)} сообщений")

        # Сохраняв файл для отчета
        report_file = f"parsed_{session_name}_{int(time.time())}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)

        print(f"  {C.G}✅ Данные сохранены в {report_file}{C.RST}")
        return True
    except Exception as e:
        print(f"  {C.R}❌ Ошибка парсинга: {e}{C.RST}")
        return False


# ═══════════════════════════════════════════════════════════════
# ФУНКЦИИ ИЗМЕНЕНИЯ И ПАРСИНГА
# ═══════════════════════════════════════════════════════════════

async def update_account_username(client, session_name, new_username):
    """Изменяет @username аккаунта"""
    try:
        # Проверка доступности
        available = await client(CheckUsernameRequest(new_username))
        if not available:
            print(f"  {C.R}❌ Username @{new_username} занят{C.RST}")
            return False

        await client(UpdateUsernameRequest(new_username))
        print(f"  {C.G}✅ Username изменен на @{new_username}{C.RST}")
        return True
    except Exception as e:
        print(f"  {C.R}❌ Ошибка изменения username: {e}{C.RST}")
        return False


async def parse_private_messages(client, session_name, limit=100):
    """Полный парсинг личных сообщений (диалогов)"""
    try:
        print(f"  {C.CY}📥 Парсинг сообщений для {session_name}...{C.RST}")
        dialogs = await client.get_dialogs(limit=limit)
        parsed_data = []

        for dialog in dialogs:
            if dialog.is_user:
                user = dialog.entity
                name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                username = f"@{user.username}" if user.username else "нет"

                # Получаем последние сообщения
                messages = await client.get_messages(user, limit=5)
                last_msgs = [m.text for m in messages if m.text]

                parsed_data.append({
                    "user_id": user.id,
                    "name": name,
                    "username": username,
                    "last_messages": last_msgs
                })
                print(f"    👤 {name} ({username}): {len(last_msgs)} сообщений")

        # Сохраняв файл для отчета
        report_file = f"parsed_{session_name}_{int(time.time())}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)

        print(f"  {C.G}✅ Данные сохранены в {report_file}{C.RST}")
        return True
    except Exception as e:
        print(f"  {C.R}❌ Ошибка парсинга: {e}{C.RST}")
        return False


async def action_update_username():
    sessions = select_sessions("Выбери аккаунты для смены username")
    if not sessions: return
    new_username = input(f"{C.CY}  Введите новый @username (без @): {C.RST}").strip().replace("@", "")
    await execute_on_sessions(sessions, update_account_username, "Смена username", new_username=new_username)


async def action_parse_messages():
    sessions = select_sessions("Выбери аккаунты для парсинга")
    if not sessions: return
    await execute_on_sessions(sessions, parse_private_messages, "Парсинг сообщений")


# ═══════════════════════════════════════════════════════════════
# МЕНЮ
# ═══════════════════════════════════════════════════════════════

def print_menu():
    clear()
    banner()
    menu = f"""
{C.CY}┌────┬─────────────────────────────────────────────────────┐
│    │ {C.BOLD}НАКРУТКА{C.RST}{C.CY}                                                │
│{C.W}  1 {C.CY}│ 👁  Просмотр поста                                     │
│{C.W}  2 {C.CY}│ 👍 Реакция                                             │
│{C.W}  3 {C.CY}│ 📢 Подписка                                            │
│{C.W}  4 {C.CY}│ 🚀 Всё сразу                                           │
│{C.W}  5 {C.CY}│ 💬 Комментарий                                         │
│{C.W}  6 {C.CY}│ 📤 Пересылка                                           │
│{C.W}  7 {C.CY}│ 📊 Голосование                                         │
│{C.W}  8 {C.CY}│ 🔘 Inline кнопки                                       │
│{C.W}  9 {C.CY}│ 💥 Массовая реакция на N постов                        │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}БОТЫ / WEBAPP{C.RST}{C.CY}                                          │
│{C.W} 10 {C.CY}│ 🤖 Авто-старт бота + реферальная ссылка               │
│{C.W} 11 {C.CY}│ 📋 Сценарий бота из JSON                               │
│{C.W} 12 {C.CY}│ 🌐 WebApp + startapp параметр                          │
│{C.W} 74 {C.CY}│ 🔗 Авто-подписка по кнопкам + Проверить доступ        │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}РАССЫЛКА{C.RST}{C.CY}                                               │
│{C.W} 13 {C.CY}│ 📨 Рассылка в ЛС                                      │
│{C.W} 14 {C.CY}│ 👥 Инвайт                                              │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}СООБЩЕНИЯ{C.RST}{C.CY}                                              │
│{C.W} 15 {C.CY}│ 📝 Отправка с медиа + Markdown                         │
│{C.W} 16 {C.CY}│ ⏰ Отложенная отправка                                 │
│{C.W} 17 {C.CY}│ ✏️  Редактирование                                      │
│{C.W} 18 {C.CY}│ 📌 Закреп/откреп                                       │
│{C.W} 19 {C.CY}│ 🗑  Удалить свои сообщения                             │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}КАНАЛЫ{C.RST}{C.CY}                                                 │
│{C.W} 20 {C.CY}│ ➕ Создать канал/группу                                 │
│{C.W} 21 {C.CY}│ ⚙️  Настройка (название/описание/фото/username)         │
│{C.W} 22 {C.CY}│ 👑 Назначить админа (с выбором прав)                   │
│{C.W} 23 {C.CY}│ 🔨 Массовый бан/кик                                    │
│{C.W} 24 {C.CY}│ 🧹 Очистка (удалить все посты)                         │
│{C.W} 25 {C.CY}│ 📋 Копировать настройки канала                          │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}РЕПОРТЫ{C.RST}{C.CY}                                                │
│{C.W} 26 {C.CY}│ 🚨 Репорт на юзера/канал (8 причин)                    │
│{C.W} 27 {C.CY}│ 🚨 Репорт на сообщение                                 │
│{C.W} 28 {C.CY}│ 🚫 Массовая блокировка                                 │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}ПАРСИНГ{C.RST}{C.CY}                                                │
│{C.W} 29 {C.CY}│ 🔍 Парсер участников                                   │
│{C.W} 30 {C.CY}│ 📊 Статистика канала                                   │
│{C.W} 31 {C.CY}│ 📥 Скачивание медиа                                    │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}АВТОМАТИЗАЦИЯ{C.RST}{C.CY}                                          │
│{C.W} 32 {C.CY}│ 👀 Мониторинг (авто-реакции на новые посты)            │
│{C.W} 33 {C.CY}│ 🤖 Авто-ответчик по ключевым словам                   │
│{C.W} 34 {C.CY}│ 📝 Авто-постинг                                        │
│{C.W} 35 {C.CY}│ 📋 Задачи из JSON                                      │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}АНТИДЕТЕКТ{C.RST}{C.CY}                                             │
│{C.W} 36 {C.CY}│ 🔥 Прогрев (чтение, скролл, профили)                  │
│{C.W} 37 {C.CY}│ 🟢 Имитация онлайна (параллельно)                     │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}АККАУНТЫ{C.RST}{C.CY}                                               │
│{C.W} 38 {C.CY}│ ✅ Чекер                                               │
│{C.W} 39 {C.CY}│ 📱 Активные сессии                                     │
│{C.W} 40 {C.CY}│ 💀 Сброс ВСЕХ сессий                                   │
│{C.W} 41 {C.CY}│ 🎯 Выборочный сброс                                    │
│{C.W} 42 {C.CY}│ 🔑 Запрос кода + 2FA                                   │
│{C.W} 43 {C.CY}│ ℹ️  Инфо                                                │
│{C.W} 44 {C.CY}│ ✏️  Имя/био                                             │
│{C.W} 45 {C.CY}│ 🖼  Фото                                               │
│{C.W} 46 {C.CY}│ 🔐 2FA                                                 │
│{C.W} 47 {C.CY}│ 🚪 Отписка от каналов                                  │
│{C.W} 48 {C.CY}│ ☠️  Удалить аккаунт                                     │
│{C.W} 61 {C.CY}│ 🗑  Полное удаление сессии (файла)                     │
├────┼─────────────────────────────────────────────────────────┤
│{C.W} 49 {C.CY}│ 👤 Изменить Username аккаунта                         │
│{C.W} 50 {C.CY}│ 📥 Парсинг личных сообщений                           │
│{C.W} 51 {C.CY}│ 💎 Премиум реакция (по ID эмодзи)                     │
│{C.W} 52 {C.CY}│ 📋 Список сессий                                       │
│{C.W} 53 {C.CY}│ 🌐 Список прокси                                       │
│{C.W} 57 {C.CY}│ 👀 Накрутка просмотров на N постов                     │
│{C.W} 58 {C.CY}│ 📧 Смена Email в аккаунте                              │
│{C.W} 59 {C.CY}│ 🚫 Проверка на спам-блок                               │
│{C.W} 60 {C.CY}│ 🎭 Конструктор сценариев (beta)                       │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}АВТОМАТИЗАЦИЯ V2 (NEW){C.RST}{C.CY}                                  │
│{C.W} 54 {C.CY}│ 👀 Авто-просмотры и реакции на БУДУЩИЕ посты          │
│{C.W} 55 {C.CY}│ ➕ Массовое создание каналов/групп (до 50)            │
│{C.W} 56 {C.CY}│ 👑 Передача прав владельца канала                      │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}ПРОСМОТР АККАУНТА{C.RST}{C.CY}                                       │
│{C.W} 73 {C.CY}│ 📂 Браузер диалогов (чаты, личка, каналы)             │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}ИСТОРИИ{C.RST}{C.CY}                                                 │
│{C.W} 62 {C.CY}│ 👁  Накрутка просмотров историй                        │
│{C.W} 63 {C.CY}│ ❤️  Реакция на историю                                  │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}ПАРСИНГ РАСШИРЕННЫЙ{C.RST}{C.CY}                                     │
│{C.W} 64 {C.CY}│ 🔍 Поиск пользователя (телефон / username)             │
│{C.W} 65 {C.CY}│ 👥 Парсинг общих групп двух пользователей              │
│{C.W} 66 {C.CY}│ 🔑 Фильтрация постов канала по ключевым словам        │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}КОНТАКТЫ / КАНАЛЫ{C.RST}{C.CY}                                       │
│{C.W} 67 {C.CY}│ 📋 Копирование контактов между аккаунтами              │
│{C.W} 68 {C.CY}│ 🛡  Авто-модерация (удаление по стоп-словам)           │
│{C.W} 69 {C.CY}│ 📤 Форвард постов с фильтром по ключевым словам       │
│{C.W} 70 {C.CY}│ 📂 Копирование всей истории канала                     │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}АВТОМАТИЗАЦИЯ V3{C.RST}{C.CY}                                        │
│{C.W} 71 {C.CY}│ ⏰ Расписание задач по времени                         │
│{C.W} 72 {C.CY}│ 🚫 Авто-обход спам-блока                               │
├────┼─────────────────────────────────────────────────────────┤
│    │ {C.BOLD}AI АССИСТЕНТ{C.RST}{C.CY}                                            │
│{C.W} 75 {C.CY}│ 🤖 Gemini AI — управление через естественный язык     │
├────┼─────────────────────────────────────────────────────────┤
│{C.R}  0 {C.CY}│ ❌ Выход                                               │
└────┴─────────────────────────────────────────────────────────┘{C.RST}"""
    print(menu)


def pause():
    input(f"\n{C.DIM}  Нажми Enter для продолжения...{C.RST}")


def ask(prompt: str, default: str = "") -> str:
    val = input(f"{C.CY}  {prompt}{C.RST}").strip()
    return val if val else default


def ask_int(prompt: str, default: int = 0) -> int:
    val = ask(prompt, str(default))
    try:
        return int(val)
    except ValueError:
        return default


def ask_reaction() -> str:
    print(f"\n{C.Y}  Доступные реакции:")
    reactions = ["👍", "👎", "❤️", "🔥", "🥰", "👏", "😁", "🤔",
                 "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩",
                 "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳",
                 "❤️‍🔥", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆",
                 "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈",
                 "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
                 "😇", "😨", "🤝", "✍️", "🤗", "🫡", "🎅", "🎄",
                 "☃️", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄",
                 "😘", "💊", "🙊", "😎", "👾", "🤷‍♂️", "🤷", "🤷‍♀️",
                 "😡"]
    for i in range(0, len(reactions), 10):
        chunk = reactions[i:i + 10]
        print(f"  {' '.join(chunk)}")
    print(f"{C.RST}")
    r = ask("Реакция (emoji): ")
    return r if r else "👍"


# ═══════════════════════════════════════════════════════════════
# КОНЕЦ ЧАСТИ 1
# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
# ЧАСТЬ 2 — ФУНКЦИИ 1-35
# ═══════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# 1. ПРОСМОТР ПОСТА
# ─────────────────────────────────────────────────────────────

async def task_view_post(client, session_name, **kw):
    channel = kw["channel"]
    post_id = kw["post_id"]
    entity = await resolve_channel(client, channel)
    await client(GetMessagesViewsRequest(
        peer=entity,
        id=[post_id],
        increment=True
    ))
    await human_delay(0.5, 1.5)


async def action_view_post():
    link = ask("Ссылка на пост (t.me/channel/123): ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Неверная ссылка. Нужен формат: t.me/channel/123{C.RST}")
        return
    sessions = select_sessions("Выбери аккаунты для просмотра")
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_view_post,
        task_name="👁 Просмотр поста",
        channel=parsed["channel"],
        post_id=parsed["post_id"]
    )


# ─────────────────────────────────────────────────────────────
# 2. РЕАКЦИЯ
# ─────────────────────────────────────────────────────────────

async def task_send_reaction(client, session_name, **kw):
    channel = kw["channel"]
    post_id = kw["post_id"]
    reaction = kw["reaction"]
    entity = await resolve_channel(client, channel)

    # Сначала просмотр
    await client(GetMessagesViewsRequest(
        peer=entity, id=[post_id], increment=True
    ))
    await human_delay(0.5, 1.5)

    react_obj = ReactionEmoji(emoticon=reaction)
    await client(SendReactionRequest(
        peer=entity,
        msg_id=post_id,
        reaction=[react_obj]
    ))
    await human_delay(0.3, 1.0)


async def action_send_reaction():
    link = ask("Ссылка на пост: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Неверная ссылка{C.RST}")
        return
    reaction = ask_reaction()
    sessions = select_sessions("Выбери аккаунты для реакции")
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_send_reaction,
        task_name=f"👍 Реакция {reaction}",
        channel=parsed["channel"],
        post_id=parsed["post_id"],
        reaction=reaction
    )


# ─────────────────────────────────────────────────────────────
# 3. ПОДПИСКА
# ─────────────────────────────────────────────────────────────

async def task_subscribe(client, session_name, **kw):
    channel = kw["channel"]
    invite_hash = kw.get("invite_hash")

    if invite_hash:
        from telethon.tl.functions.messages import ImportChatInviteRequest
        try:
            await client(ImportChatInviteRequest(invite_hash))
        except UserAlreadyParticipantError:
            pass
    else:
        entity = await resolve_channel(client, channel)
        try:
            await client(JoinChannelRequest(entity))
        except UserAlreadyParticipantError:
            pass
    await human_delay(1.0, 3.0)


async def action_subscribe():
    link = ask("Ссылка на канал/группу (или @username): ")
    parsed = parse_tg_link(link)
    sessions = select_sessions("Выбери аккаунты для подписки")
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_subscribe,
        task_name="📢 Подписка",
        channel=parsed["channel"],
        invite_hash=parsed.get("invite_hash")
    )


# ─────────────────────────────────────────────────────────────
# 4. ВСЁ СРАЗУ (просмотр + реакция + подписка)
# ─────────────────────────────────────────────────────────────

async def task_all_in_one(client, session_name, **kw):
    channel = kw["channel"]
    post_id = kw["post_id"]
    reaction = kw["reaction"]
    invite_hash = kw.get("invite_hash")

    # Подписка
    if invite_hash:
        from telethon.tl.functions.messages import ImportChatInviteRequest
        try:
            await client(ImportChatInviteRequest(invite_hash))
        except UserAlreadyParticipantError:
            pass
    else:
        entity = await resolve_channel(client, channel)
        try:
            await client(JoinChannelRequest(entity))
        except UserAlreadyParticipantError:
            pass

    await human_delay(1.0, 2.5)

    # Просмотр
    entity = await resolve_channel(client, channel)
    await client(GetMessagesViewsRequest(
        peer=entity, id=[post_id], increment=True
    ))
    await human_delay(0.5, 1.5)

    # Реакция
    react_obj = ReactionEmoji(emoticon=reaction)
    await client(SendReactionRequest(
        peer=entity, msg_id=post_id,
        reaction=[react_obj]
    ))
    await human_delay(0.3, 1.0)


async def action_all_in_one():
    link = ask("Ссылка на пост: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Нужна ссылка на пост{C.RST}")
        return
    reaction = ask_reaction()
    sessions = select_sessions("Выбери аккаунты")
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_all_in_one,
        task_name="🚀 Подписка + Просмотр + Реакция",
        channel=parsed["channel"],
        post_id=parsed["post_id"],
        reaction=reaction,
        invite_hash=parsed.get("invite_hash")
    )


# ─────────────────────────────────────────────────────────────
# 5. КОММЕНТАРИЙ
# ─────────────────────────────────────────────────────────────

async def task_comment(client, session_name, **kw):
    channel = kw["channel"]
    post_id = kw["post_id"]
    comments = kw["comments"]
    entity = await resolve_channel(client, channel)

    comment_text = random.choice(comments)
    await client.send_message(
        entity=entity,
        message=comment_text,
        comment_to=post_id
    )
    await human_delay(1.0, 3.0)


async def action_comment():
    link = ask("Ссылка на пост: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Нужна ссылка на пост{C.RST}")
        return
    print(f"{C.Y}  Введи комментарии (каждый с новой строки, пустая строка = конец):{C.RST}")
    comments = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        comments.append(line)
    if not comments:
        print(f"{C.R}❌ Нет комментариев{C.RST}")
        return
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_comment,
        task_name="💬 Комментарий",
        channel=parsed["channel"],
        post_id=parsed["post_id"],
        comments=comments
    )


# ─────────────────────────────────────────────────────────────
# 6. ПЕРЕСЫЛКА
# ─────────────────────────────────────────────────────────────

async def task_forward(client, session_name, **kw):
    from_channel = kw["from_channel"]
    post_id = kw["post_id"]
    to_channel = kw["to_channel"]

    from_entity = await resolve_channel(client, from_channel)
    to_entity = await resolve_channel(client, to_channel)

    await client.forward_messages(
        entity=to_entity,
        messages=post_id,
        from_peer=from_entity
    )
    await human_delay(1.0, 2.0)


async def action_forward():
    link = ask("Ссылка на пост для пересылки: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Нужна ссылка на пост{C.RST}")
        return
    to_link = ask("Куда переслать (канал/группа/@username): ")
    to_parsed = parse_tg_link(to_link)
    if not to_parsed["channel"]:
        print(f"{C.R}❌ Неверный получатель{C.RST}")
        return
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_forward,
        task_name="📤 Пересылка",
        from_channel=parsed["channel"],
        post_id=parsed["post_id"],
        to_channel=to_parsed["channel"]
    )


# ─────────────────────────────────────────────────────────────
# 7. ГОЛОСОВАНИЕ (ИСПРАВЛЕННОЕ)
# ─────────────────────────────────────────────────────────────

async def task_vote(client, session_name, **kw):
    channel = kw["channel"]
    post_id = kw["post_id"]
    option_indices = kw["options"]  # [0, 1, 2] — индексы вариантов

    entity = await resolve_channel(client, channel)

    # Просмотр
    await client(GetMessagesViewsRequest(
        peer=entity, id=[post_id], increment=True
    ))
    await human_delay(0.3, 1.0)

    # Получаем сообщение с опросом
    msg = await client.get_messages(entity, ids=post_id)
    if not msg:
        print(f"    {C.R}❌ {session_name}: сообщение не найдено{C.RST}")
        return

    # Проверяем что это опрос
    poll = None
    if msg.media and hasattr(msg.media, 'poll'):
        poll = msg.media.poll
    elif hasattr(msg, 'poll'):
        poll = msg.poll

    if not poll:
        print(f"    {C.R}❌ {session_name}: это не опрос{C.RST}")
        return

    # Получаем реальные option bytes из опроса
    available_options = poll.answers
    if not available_options:
        print(f"    {C.R}❌ {session_name}: нет вариантов в опросе{C.RST}")
        return

    # Собираем option bytes по выбранным индексам
    selected_options = []
    for idx in option_indices:
        if 0 <= idx < len(available_options):
            selected_options.append(available_options[idx].option)
        else:
            print(f"    {C.Y}⚠ {session_name}: вариант {idx} не существует "
                  f"(макс: {len(available_options) - 1}){C.RST}")

    if not selected_options:
        print(f"    {C.R}❌ {session_name}: нет валидных вариантов{C.RST}")
        return

    # Проверяем — если опрос НЕ multiple choice, берём только первый
    if not poll.multiple_choice and len(selected_options) > 1:
        selected_options = [selected_options[0]]
        print(f"    {C.DIM}  ↳ Опрос без мультивыбора, "
              f"голосуем за первый вариант{C.RST}")

    # Голосуем
    await client(SendVoteRequest(
        peer=entity,
        msg_id=post_id,
        options=selected_options
    ))
    await human_delay(0.5, 1.5)


async def action_vote():
    link = ask("Ссылка на пост с опросом: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Нужна ссылка на пост с опросом{C.RST}")
        return

    # Показываем варианты опроса через первый аккаунт
    sessions = get_sessions()
    if not sessions:
        print(f"{C.R}❌ Нет сессий{C.RST}")
        return

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)

    if not await safe_connect(client, sessions[0]):
        return

    poll_info = None
    try:
        entity = await resolve_channel(client, parsed["channel"])
        msg = await client.get_messages(entity, ids=parsed["post_id"])

        if not msg:
            print(f"{C.R}❌ Сообщение не найдено{C.RST}")
            return

        # Извлекаем опрос
        poll = None
        if msg.media and hasattr(msg.media, 'poll'):
            poll = msg.media.poll
        elif hasattr(msg, 'poll'):
            poll = msg.poll

        if not poll:
            print(f"{C.R}❌ Это не опрос{C.RST}")
            return

        # Показываем информацию
        question_text = ""
        if hasattr(poll.question, 'text'):
            question_text = poll.question.text
        elif isinstance(poll.question, str):
            question_text = poll.question
        else:
            question_text = str(poll.question)

        print(f"\n{C.CY}{'═' * 50}")
        print(f"  📊 Опрос: {question_text}")
        print(f"  Мультивыбор: {'Да' if poll.multiple_choice else 'Нет'}")
        print(f"  Закрыт: {'Да' if poll.closed else 'Нет'}")
        print(f"{'═' * 50}{C.RST}")

        if poll.closed:
            print(f"{C.R}❌ Опрос закрыт{C.RST}")
            return

        print(f"\n{C.Y}  Варианты:{C.RST}")
        for i, answer in enumerate(poll.answers):
            answer_text = ""
            if hasattr(answer.text, 'text'):
                answer_text = answer.text.text
            elif isinstance(answer.text, str):
                answer_text = answer.text
            else:
                answer_text = str(answer.text)

            option_hex = answer.option.hex()
            print(f"    {C.W}{i}. {answer_text}  "
                  f"{C.DIM}(option: {option_hex}){C.RST}")

        # Показываем результаты если есть
        if msg.media and hasattr(msg.media, 'results') and msg.media.results:
            results = msg.media.results
            if results.results:
                print(f"\n{C.Y}  Текущие результаты:{C.RST}")
                for r in results.results:
                    bar = "█" * min(r.voters, 30)
                    print(f"    {C.DIM}{r.option.hex()}: "
                          f"{r.voters} голосов {bar}{C.RST}")
                if results.total_voters:
                    print(f"    {C.DIM}Всего: {results.total_voters}{C.RST}")

        poll_info = {
            "answers_count": len(poll.answers),
            "multiple": poll.multiple_choice
        }

    finally:
        await client.disconnect()

    if not poll_info:
        return

    # Выбор вариантов
    if poll_info["multiple"]:
        opts_str = ask(f"Номера вариантов через запятую "
                       f"(0-{poll_info['answers_count'] - 1}): ", "0")
    else:
        opts_str = ask(f"Номер варианта "
                       f"(0-{poll_info['answers_count'] - 1}): ", "0")

    try:
        options = [int(x.strip()) for x in opts_str.split(",")]
    except ValueError:
        print(f"{C.R}❌ Неверный формат{C.RST}")
        return

    # Валидация
    for o in options:
        if o < 0 or o >= poll_info["answers_count"]:
            print(f"{C.R}❌ Вариант {o} не существует "
                  f"(доступно 0-{poll_info['answers_count'] - 1}){C.RST}")
            return

    # Рандомный выбор?
    random_mode = False
    if poll_info["answers_count"] > 1:
        rnd = ask("Случайный вариант для каждого аккаунта? (y/n): ", "n")
        random_mode = rnd.lower() == "y"

    sel_sessions = select_sessions("Выбери аккаунты для голосования")
    if not sel_sessions:
        return

    if random_mode:
        # Каждый аккаунт голосует за случайный вариант
        async def task_vote_random(client, session_name, **kw):
            random_option = random.randint(0, kw["max_option"])
            kw["options"] = [random_option]
            await task_vote(client, session_name, **kw)
            print(f"    {C.DIM}  ↳ проголосовал за вариант {random_option}{C.RST}")

        await execute_on_sessions(
            sel_sessions, task_vote_random,
            task_name="📊 Голосование (рандом)",
            channel=parsed["channel"],
            post_id=parsed["post_id"],
            options=options,
            max_option=poll_info["answers_count"] - 1
        )
    else:
        await execute_on_sessions(
            sel_sessions, task_vote,
            task_name=f"📊 Голосование (вариант: {options})",
            channel=parsed["channel"],
            post_id=parsed["post_id"],
            options=options
        )


# ─────────────────────────────────────────────────────────────
# 8. INLINE КНОПКИ
# ─────────────────────────────────────────────────────────────

async def task_click_button(client, session_name, **kw):
    channel = kw["channel"]
    post_id = kw["post_id"]
    button_idx = kw["button_idx"]
    entity = await resolve_channel(client, channel)

    msgs = await client.get_messages(entity, ids=post_id)
    msg = msgs
    if not msg or not msg.reply_markup:
        return

    buttons = []
    if hasattr(msg.reply_markup, 'rows'):
        for row in msg.reply_markup.rows:
            for btn in row.buttons:
                buttons.append(btn)

    if button_idx >= len(buttons):
        return

    btn = buttons[button_idx]
    if isinstance(btn, KeyboardButtonCallback):
        await client(GetBotCallbackAnswerRequest(
            peer=entity,
            msg_id=post_id,
            data=btn.data
        ))
    elif isinstance(btn, KeyboardButtonUrl):
        pass  # URL кнопки просто открываем через просмотр
    await human_delay(0.5, 1.5)


async def action_click_button():
    link = ask("Ссылка на пост с кнопками: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Нужна ссылка на пост{C.RST}")
        return

    # Показываем кнопки через первый аккаунт
    sessions = get_sessions()
    if not sessions:
        print(f"{C.R}❌ Нет сессий{C.RST}")
        return

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)
    await safe_connect(client, sessions[0])

    try:
        entity = await resolve_channel(client, parsed["channel"])
        msg = await client.get_messages(entity, ids=parsed["post_id"])
        if not msg or not msg.reply_markup:
            print(f"{C.R}❌ Нет кнопок в этом посте{C.RST}")
            return

        buttons = []
        if hasattr(msg.reply_markup, 'rows'):
            for row in msg.reply_markup.rows:
                for btn in row.buttons:
                    buttons.append(btn)

        print(f"\n{C.Y}  Кнопки в посте:{C.RST}")
        for i, btn in enumerate(buttons):
            btype = "callback" if isinstance(btn, KeyboardButtonCallback) else "url"
            print(f"  {C.W}{i}. {btn.text} [{btype}]{C.RST}")

    finally:
        await client.disconnect()

    button_idx = ask_int("Номер кнопки: ", 0)
    sel_sessions = select_sessions()
    if not sel_sessions:
        return
    await execute_on_sessions(
        sel_sessions, task_click_button,
        task_name="🔘 Клик по inline кнопке",
        channel=parsed["channel"],
        post_id=parsed["post_id"],
        button_idx=button_idx
    )


# ─────────────────────────────────────────────────────────────
# 9. МАССОВАЯ РЕАКЦИЯ НА N ПОСТОВ
# ─────────────────────────────────────────────────────────────

async def task_mass_reaction(client, session_name, **kw):
    channel = kw["channel"]
    count = kw["count"]
    reaction = kw["reaction"]
    entity = await resolve_channel(client, channel)

    messages = await client.get_messages(entity, limit=count)
    react_obj = ReactionEmoji(emoticon=reaction)

    for msg in messages:
        if msg and msg.id:
            try:
                await client(GetMessagesViewsRequest(
                    peer=entity, id=[msg.id], increment=True
                ))
                await client(SendReactionRequest(
                    peer=entity, msg_id=msg.id,
                    reaction=[react_obj]
                ))
                await human_delay(0.5, 1.5)
            except Exception:
                pass


async def action_mass_reaction():
    channel_link = ask("Канал (@username или ссылка): ")
    parsed = parse_tg_link(channel_link)
    if not parsed["channel"]:
        print(f"{C.R}❌ Неверный канал{C.RST}")
        return
    count = ask_int("Количество последних постов: ", 10)
    reaction = ask_reaction()
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_mass_reaction,
        task_name=f"💥 Массовая реакция {reaction} на {count} постов",
        channel=parsed["channel"],
        count=count,
        reaction=reaction
    )


# ─────────────────────────────────────────────────────────────
# 10. АВТО-СТАРТ БОТА + РЕФЕРАЛЬНАЯ ССЫЛКА
# ─────────────────────────────────────────────────────────────

async def task_start_bot(client, session_name, **kw):
    bot = kw["bot"]
    start_param = kw.get("start_param", "")

    entity = await client.get_entity(bot)

    if start_param:
        await client(StartBotRequest(
            bot=entity,
            peer=entity,
            start_param=start_param
        ))
    else:
        await client.send_message(entity, "/start")
    await human_delay(1.5, 3.0)


async def action_start_bot():
    link = ask("Ссылка на бота (t.me/bot?start=ref или @bot): ")
    parsed = parse_tg_link(link)

    bot = parsed.get("bot") or parsed.get("channel")
    if not bot:
        print(f"{C.R}❌ Неверная ссылка на бота{C.RST}")
        return
    start_param = parsed.get("start_param", "")
    if not start_param:
        start_param = ask("Start параметр (пусто = просто /start): ", "")
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_start_bot,
        task_name="🤖 Старт бота",
        bot=bot,
        start_param=start_param
    )


# ─────────────────────────────────────────────────────────────
# 11. СЦЕНАРИЙ БОТА ИЗ JSON
# ─────────────────────────────────────────────────────────────

async def task_bot_scenario(client, session_name, **kw):
    """
    JSON формат:
    {
      "bot": "@botusername",
      "steps": [
        {"action": "send", "text": "/start"},
        {"action": "wait", "seconds": 2},
        {"action": "send", "text": "Hello"},
        {"action": "click_button", "index": 0},
        {"action": "wait", "seconds": 1}
      ]
    }
    """
    scenario = kw["scenario"]
    bot = scenario["bot"]
    entity = await client.get_entity(bot)

    for step in scenario.get("steps", []):
        action = step.get("action", "")
        if action == "send":
            await client.send_message(entity, step["text"])
        elif action == "wait":
            await asyncio.sleep(step.get("seconds", 1))
        elif action == "click_button":
            # Получаем последнее сообщение от бота
            msgs = await client.get_messages(entity, limit=1)
            if msgs and msgs[0].reply_markup:
                buttons = []
                for row in msgs[0].reply_markup.rows:
                    for btn in row.buttons:
                        buttons.append(btn)
                idx = step.get("index", 0)
                if idx < len(buttons) and isinstance(buttons[idx], KeyboardButtonCallback):
                    await client(GetBotCallbackAnswerRequest(
                        peer=entity,
                        msg_id=msgs[0].id,
                        data=buttons[idx].data
                    ))
        elif action == "start":
            param = step.get("param", "")
            if param:
                await client(StartBotRequest(bot=entity, peer=entity, start_param=param))
            else:
                await client.send_message(entity, "/start")
        await human_delay(0.5, 1.5)


async def action_bot_scenario():
    print(f"\n{C.Y}  Файлы сценариев в папке scenarios/:{C.RST}")
    files = list(SCENARIOS_DIR.glob("*.json"))
    if not files:
        print(f"{C.R}  Нет JSON файлов в scenarios/{C.RST}")
        print(f"{C.DIM}  Создай файл формата:")
        print(f'  {{"bot":"@botname","steps":[{{"action":"send","text":"/start"}}]}}{C.RST}')
        return
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    idx = ask_int("Номер файла: ", 1) - 1
    if idx < 0 or idx >= len(files):
        return

    with open(files[idx]) as f:
        scenario = json.load(f)

    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_bot_scenario,
        task_name="📋 Сценарий бота",
        scenario=scenario
    )


# ─────────────────────────────────────────────────────────────
# 12. WEBAPP + STARTAPP
# ─────────────────────────────────────────────────────────────

async def task_webapp(client, session_name, **kw):
    bot = kw["bot"]
    startapp = kw.get("startapp", "")
    url = kw.get("url", "")

    entity = await client.get_entity(bot)

    if startapp:
        await client(StartBotRequest(
            bot=entity, peer=entity, start_param=startapp
        ))
    await human_delay(1.0, 2.0)

    # Запрос WebView если есть URL
    if url:
        try:
            await client(RequestWebViewRequest(
                peer=entity,
                bot=entity,
                url=url,
                platform="android",
            ))
        except Exception:
            pass
    await human_delay(1.0, 2.0)


async def action_webapp():
    link = ask("Ссылка (t.me/bot?startapp=param или t.me/bot/app): ")
    parsed = parse_tg_link(link)
    bot = parsed.get("bot") or parsed.get("channel")
    if not bot:
        print(f"{C.R}❌ Неверная ссылка{C.RST}")
        return
    startapp = parsed.get("startapp", "")
    if not startapp:
        startapp = ask("Startapp параметр (пусто = без параметра): ")
    url = ask("URL WebApp (пусто = пропустить): ")
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_webapp,
        task_name="🌐 WebApp",
        bot=bot, startapp=startapp, url=url
    )


# ─────────────────────────────────────────────────────────────
# 74. АВТО-ПОДПИСКА ПО INLINE КНОПКАМ БОТА + ПРОВЕРИТЬ ДОСТУП
# ─────────────────────────────────────────────────────────────

# Ключевые слова для кнопки "проверить"
_CHECK_KEYWORDS = [
    "провер", "check", "verify", "доступ", "подтверд",
    "continue", "продолжить", "готово", "дальше", "next",
    "получить", "claim", "start", "начать",
]

def _is_check_button(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _CHECK_KEYWORDS)

def _extract_channel_from_url(url: str) -> Optional[str]:
    """Из URL-кнопки достаёт username или invite_hash канала."""
    url = url.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    else:
        return None  # не t.me ссылка

    # Инвайт: +hash или joinchat/hash
    if url.startswith("+") or url.startswith("joinchat/"):
        return url  # вернём как есть, обработаем отдельно

    # Убираем query-параметры и дополнительные сегменты
    channel = url.split("?")[0].split("/")[0].strip()
    if channel:
        return channel
    return None


async def task_subscribe_and_check(client, session_name, **kw):
    """
    1. Стартует бота по реф-ссылке
    2. Находит URL-кнопки → подписывается на каналы
    3. Находит callback-кнопку «Проверить доступ» → нажимает
    4. Выводит ответ бота
    """
    bot = kw["bot"]
    start_param = kw.get("start_param", "")
    check_kw = kw.get("check_keywords", [])  # доп. ключевые слова от пользователя
    delay_sub = kw.get("delay_sub", 2.0)

    entity = await client.get_entity(bot)

    # ── Шаг 1: старт бота ──
    try:
        if start_param:
            await client(StartBotRequest(bot=entity, peer=entity, start_param=start_param))
        else:
            await client.send_message(entity, "/start")
        print(f"  {C.G}✅ {session_name} — /start отправлен{C.RST}")
    except Exception as e:
        print(f"  {C.Y}⚠ {session_name} — старт: {e}{C.RST}")

    await asyncio.sleep(2.5)

    # ── Шаг 2: читаем ответ бота (до 3 последних сообщений) ──
    msgs = await client.get_messages(entity, limit=5)

    all_buttons = []   # (row_idx, btn, msg_id)
    check_btn = None
    check_msg_id = None

    for m in msgs:
        if not m.reply_markup:
            continue
        rows = getattr(m.reply_markup, "rows", [])
        for row in rows:
            for btn in row.buttons:
                if isinstance(btn, KeyboardButtonUrl):
                    all_buttons.append(("url", btn, m.id))
                elif isinstance(btn, KeyboardButtonCallback):
                    text = btn.text or ""
                    # Пользовательские ключевые слова имеют приоритет
                    custom_match = any(kw2.lower() in text.lower() for kw2 in check_kw)
                    if custom_match or _is_check_button(text):
                        if check_btn is None:   # берём первую подходящую
                            check_btn = btn
                            check_msg_id = m.id

    # ── Шаг 3: подписываемся на каналы из URL-кнопок ──
    subscribed = []
    for (btype, btn, _mid) in all_buttons:
        if btype != "url":
            continue
        url = btn.url or ""
        ch = _extract_channel_from_url(url)
        if not ch:
            continue
        try:
            if ch.startswith("+") or ch.startswith("joinchat/"):
                from telethon.tl.functions.messages import ImportChatInviteRequest
                invite = ch.replace("joinchat/", "").lstrip("+")
                await client(ImportChatInviteRequest(invite))
            else:
                ch_entity = await client.get_entity(ch)
                await client(JoinChannelRequest(ch_entity))
            subscribed.append(ch)
            print(f"  {C.G}  ✅ {session_name} → подписан: {ch}{C.RST}")
        except UserAlreadyParticipantError:
            subscribed.append(ch)
            print(f"  {C.DIM}  ⏭ {session_name} → уже в: {ch}{C.RST}")
        except Exception as e:
            print(f"  {C.Y}  ⚠ {session_name} → {ch}: {e}{C.RST}")
        await asyncio.sleep(delay_sub)

    if not subscribed:
        print(f"  {C.Y}  ⚠ {session_name} — каналов для подписки не найдено в кнопках{C.RST}")

    # ── Шаг 4: ждём и нажимаем кнопку «Проверить» ──
    await asyncio.sleep(2.0)

    if check_btn and check_msg_id:
        print(f"  {C.CY}  🔘 {session_name} → нажимаю «{check_btn.text}»...{C.RST}")
        try:
            result = await client(GetBotCallbackAnswerRequest(
                peer=entity,
                msg_id=check_msg_id,
                data=check_btn.data
            ))
            # Выводим ответ бота
            if result and getattr(result, "message", None):
                print(f"  {C.G}  💬 Ответ бота: {result.message}{C.RST}")
            else:
                # Получаем новое сообщение
                await asyncio.sleep(1.5)
                new_msgs = await client.get_messages(entity, limit=1)
                if new_msgs and new_msgs[0].text:
                    txt = new_msgs[0].text[:120]
                    print(f"  {C.G}  💬 {session_name} — бот ответил: {txt}{C.RST}")
        except Exception as e:
            print(f"  {C.Y}  ⚠ {session_name} — кнопка: {e}{C.RST}")
    else:
        print(f"  {C.Y}  ⚠ {session_name} — кнопка «Проверить» не найдена, "
              f"попробуй указать своё ключевое слово{C.RST}")

    await human_delay(1.0, 2.0)


async def action_subscribe_and_check():
    clear()
    banner()
    print(f"{C.CY}  📋 АВТО-ПОДПИСКА + ПРОВЕРИТЬ ДОСТУП{C.RST}\n")
    print(f"  {C.DIM}Скрипт запустит бота, подпишется на все каналы из inline-кнопок")
    print(f"  и нажмёт кнопку «Проверить доступ» (или аналогичную).{C.RST}\n")

    link = ask("Ссылка на бота (t.me/bot?start=ref или @bot): ")
    parsed = parse_tg_link(link)
    bot = parsed.get("bot") or parsed.get("channel")
    if not bot:
        print(f"{C.R}❌ Неверная ссылка{C.RST}")
        return

    start_param = parsed.get("start_param", "")
    if not start_param:
        start_param = ask("Start/реф параметр (Enter — без параметра): ", "")

    # Пользователь может указать своё ключевое слово для кнопки "проверить"
    custom_kw_str = ask("Ключевое слово кнопки «Проверить» (Enter — авто): ", "")
    custom_kw = [w.strip() for w in custom_kw_str.split(",") if w.strip()] if custom_kw_str else []

    delay_sub = float(ask("Задержка между подписками, сек (Enter — 2): ", "2") or "2")

    sessions = select_sessions()
    if not sessions:
        return

    await execute_on_sessions(
        sessions, task_subscribe_and_check,
        task_name="📋 Авто-подписка + Проверить",
        bot=bot,
        start_param=start_param,
        check_keywords=custom_kw,
        delay_sub=delay_sub,
    )


# ─────────────────────────────────────────────────────────────
# 13. РАССЫЛКА В ЛС
# ─────────────────────────────────────────────────────────────

async def task_send_dm(client, session_name, **kw):
    usernames = kw["usernames"]
    message = kw["message"]

    # Автоматический поиск фото в папке "Фото"
    photo_dir = BASE_DIR / "Фото"
    media_path = kw.get("media_path")
    # Если media_path передан как None или пустая строка (явно отменено), не ищем в папке
    if media_path is None or media_path == "":
        media_path = None
    elif not media_path and photo_dir.exists():
        photos = [p for p in glob.glob(str(photo_dir / "*.*")) if
                  p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if photos:
            media_path = photos[0]

    for username in usernames:
        try:
            entity = await client.get_entity(username)
            if media_path and os.path.exists(media_path):
                await client.send_file(entity, media_path, caption=message)
            else:
                await client.send_message(entity, message)
            await human_delay(3.0, 8.0)
        except Exception as e:
            print(f"  {C.R}  ↳ {session_name} -> {username}: {e}{C.RST}")


async def action_send_dm():
    print(f"{C.Y}  Введи юзернеймы (по одному на строку, пустая = конец):{C.RST}")
    usernames = []
    while True:
        u = input("  @").strip().lstrip("@")
        if not u:
            break
        usernames.append(u)
    if not usernames:
        file_path = ask("Или путь к файлу с юзернеймами: ")
        if file_path and os.path.exists(file_path):
            with open(file_path) as f:
                usernames = [l.strip().lstrip("@") for l in f if l.strip()]
    if not usernames:
        print(f"{C.R}❌ Нет юзернеймов{C.RST}")
        return
    message = ask("Сообщение: ")

    # Выбор фото
    media_path = ""  # По умолчанию пустая строка означает "без медиа"
    photo_dir = BASE_DIR / "Фото"
    photo_dir.mkdir(exist_ok=True)
    photos = [p for p in glob.glob(str(photo_dir / "*.*")) if p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

    if photos:
        print(f"\n{C.CY}  Доступные фото:{C.RST}")
        for i, p in enumerate(photos, 1):
            print(f"    {i}. {Path(p).name}")
        print(f"    0. Без медиа")
        p_idx_str = ask("Выбери номер фото (0 для текста, или путь вручную): ")
        if p_idx_str.isdigit():
            p_idx = int(p_idx_str)
            if p_idx > 0 and p_idx <= len(photos):
                media_path = photos[p_idx - 1]
            else:
                media_path = ""
        else:
            media_path = p_idx_str if p_idx_str else ""
    else:
        media_path = ask("Путь к медиа (пусто = без медиа): ")

    sessions = select_sessions()
    if not sessions:
        return

    # Распределяем юзернеймов по сессиям
    chunk_size = max(1, len(usernames) // len(sessions))
    chunks = [usernames[i:i + chunk_size] for i in range(0, len(usernames), chunk_size)]

    for i, session_name in enumerate(sessions):
        if i >= len(chunks):
            break
        chunk = chunks[i]
        proxies = load_proxies()
        proxy = proxies[i % len(proxies)] if proxies else None
        client = await create_client(session_name, proxy)
        if not await safe_connect(client, session_name):
            continue
        try:
            await task_send_dm(client, session_name,
                               usernames=chunk, message=message,
                               media_path=media_path if media_path else None)
            print(f"  {C.G}✅ {session_name} — отправлено {len(chunk)} сообщ.{C.RST}")
        except Exception as e:
            print(f"  {C.R}❌ {session_name} — {e}{C.RST}")
        finally:
            await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 14. ИНВАЙТ
# ─────────────────────────────────────────────────────────────

async def task_invite(client, session_name, **kw):
    target_channel = kw["target_channel"]
    usernames = kw["usernames"]

    entity = await resolve_channel(client, target_channel)

    for username in usernames:
        try:
            user = await client.get_entity(username)
            await client(InviteToChannelRequest(
                channel=entity,
                users=[user]
            ))
            await human_delay(5.0, 15.0)
        except FloodWaitError as e:
            print(f"  {C.Y}  ↳ FloodWait {e.seconds}s{C.RST}")
            if e.seconds < 60:
                await asyncio.sleep(e.seconds)
            else:
                break
        except Exception as e:
            print(f"  {C.R}  ↳ {username}: {e}{C.RST}")


async def action_invite():
    target = ask("Канал/группа для инвайта (@username): ")
    parsed = parse_tg_link(target)
    if not parsed["channel"]:
        print(f"{C.R}❌ Неверный канал{C.RST}")
        return
    print(f"{C.Y}  Юзернеймы для инвайта (по одному, пустая = конец):{C.RST}")
    usernames = []
    while True:
        u = input("  @").strip().lstrip("@")
        if not u:
            break
        usernames.append(u)
    if not usernames:
        file_path = ask("Файл с юзернеймами: ")
        if file_path and os.path.exists(file_path):
            with open(file_path) as f:
                usernames = [l.strip().lstrip("@") for l in f if l.strip()]
    if not usernames:
        return
    sessions = select_sessions()
    if not sessions:
        return

    chunk_size = max(1, len(usernames) // len(sessions))
    chunks = [usernames[i:i + chunk_size] for i in range(0, len(usernames), chunk_size)]

    for i, session_name in enumerate(sessions):
        if i >= len(chunks):
            break
        proxies = load_proxies()
        proxy = proxies[i % len(proxies)] if proxies else None
        client = await create_client(session_name, proxy)
        if not await safe_connect(client, session_name):
            continue
        try:
            await task_invite(client, session_name,
                              target_channel=parsed["channel"],
                              usernames=chunks[i])
        except Exception as e:
            print(f"  {C.R}❌ {session_name} — {e}{C.RST}")
        finally:
            await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 15. ОТПРАВКА С МЕДИА + MARKDOWN
# ─────────────────────────────────────────────────────────────

async def task_send_message(client, session_name, **kw):
    target = kw["target"]
    message = kw["message"]
    parse_mode = kw.get("parse_mode", "md")

    # Автоматический поиск фото в папке "Фото"
    photo_dir = BASE_DIR / "Фото"
    photo_path = kw.get("media_path")
    # Если media_path передан как None или пустая строка (явно отменено), не ищем в папке
    if photo_path is None or photo_path == "":
        photo_path = None
    elif not photo_path and photo_dir.exists():
        photos = [p for p in glob.glob(str(photo_dir / "*.*")) if
                  p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if photos:
            photo_path = photos[0]

    entity = await client.get_entity(target)

    if photo_path and os.path.exists(photo_path):
        await client.send_file(
            entity, photo_path,
            caption=message,
            parse_mode=parse_mode
        )
    else:
        await client.send_message(
            entity, message,
            parse_mode=parse_mode
        )
    await human_delay(0.5, 1.5)


async def action_send_message():
    target = ask("Куда отправить (@username/id): ")
    message = ask("Сообщение (Markdown): ")

    # Выбор фото
    media_path = ""  # По умолчанию пустая строка означает "без медиа"
    photo_dir = BASE_DIR / "Фото"
    photo_dir.mkdir(exist_ok=True)
    photos = [p for p in glob.glob(str(photo_dir / "*.*")) if p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

    if photos:
        print(f"\n{C.CY}  Доступные фото:{C.RST}")
        for i, p in enumerate(photos, 1):
            print(f"    {i}. {Path(p).name}")
        print(f"    0. Без медиа")
        p_idx_str = ask("Выбери номер фото (0 для текста, или путь вручную): ")
        if p_idx_str.isdigit():
            p_idx = int(p_idx_str)
            if p_idx > 0 and p_idx <= len(photos):
                media_path = photos[p_idx - 1]
            else:
                media_path = ""
        else:
            media_path = p_idx_str if p_idx_str else ""
    else:
        media_path = ask("Путь к медиа (пусто = без медиа): ")

    print(f"{C.Y}  Формат: 1=Markdown, 2=HTML{C.RST}")
    fmt = ask_int("Формат: ", 1)
    parse_mode = "md" if fmt == 1 else "html"

    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_send_message,
        task_name="📝 Отправка сообщения",
        target=target, message=message,
        media_path=media_path if media_path else None,
        parse_mode=parse_mode
    )


# ─────────────────────────────────────────────────────────────
# 16. ОТЛОЖЕННАЯ ОТПРАВКА
# ─────────────────────────────────────────────────────────────

async def task_scheduled_send(client, session_name, **kw):
    target = kw["target"]
    message = kw["message"]
    schedule_time = kw["schedule_time"]

    entity = await client.get_entity(target)
    await client.send_message(
        entity, message,
        schedule=schedule_time
    )


async def action_scheduled_send():
    target = ask("Куда (@username): ")
    message = ask("Сообщение: ")
    minutes = ask_int("Через сколько минут: ", 5)
    schedule_time = datetime.now() + timedelta(minutes=minutes)
    print(f"{C.G}  Запланировано на: {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}{C.RST}")

    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_scheduled_send,
        task_name="⏰ Отложенная отправка",
        target=target, message=message,
        schedule_time=schedule_time
    )


# ─────────────────────────────────────────────────────────────
# 17. РЕДАКТИРОВАНИЕ СООБЩЕНИЯ
# ─────────────────────────────────────────────────────────────

async def task_edit_message(client, session_name, **kw):
    target = kw["target"]
    msg_id = kw["msg_id"]
    new_text = kw["new_text"]

    entity = await client.get_entity(target)
    await client.edit_message(entity, msg_id, new_text)


async def action_edit_message():
    target = ask("Канал/чат (@username): ")
    msg_id = ask_int("ID сообщения: ")
    new_text = ask("Новый текст: ")
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_edit_message,
        task_name="✏️ Редактирование",
        target=target, msg_id=msg_id, new_text=new_text
    )


# ─────────────────────────────────────────────────────────────
# 18. ЗАКРЕП/ОТКРЕП
# ─────────────────────────────────────────────────────────────

async def task_pin_message(client, session_name, **kw):
    target = kw["target"]
    msg_id = kw["msg_id"]
    unpin = kw.get("unpin", False)

    entity = await client.get_entity(target)
    await client.pin_message(entity, msg_id, notify=False)


async def task_unpin_message(client, session_name, **kw):
    target = kw["target"]
    msg_id = kw.get("msg_id")
    entity = await client.get_entity(target)
    await client.unpin_message(entity, msg_id)


async def action_pin_unpin():
    target = ask("Канал/чат: ")
    msg_id = ask_int("ID сообщения: ")
    print(f"  1. Закрепить  2. Открепить")
    choice = ask_int("Выбор: ", 1)
    sessions = select_sessions()
    if not sessions:
        return
    if choice == 1:
        await execute_on_sessions(
            sessions, task_pin_message,
            task_name="📌 Закрепление",
            target=target, msg_id=msg_id
        )
    else:
        await execute_on_sessions(
            sessions, task_unpin_message,
            task_name="📌 Открепление",
            target=target, msg_id=msg_id
        )


# ─────────────────────────────────────────────────────────────
# 19. УДАЛИТЬ СВОИ СООБЩЕНИЯ
# ─────────────────────────────────────────────────────────────

async def task_delete_own_messages(client, session_name, **kw):
    target = kw["target"]
    limit = kw.get("limit", 100)

    entity = await client.get_entity(target)
    me = await client.get_me()

    deleted = 0
    async for msg in client.iter_messages(entity, limit=limit, from_user=me):
        try:
            await msg.delete()
            deleted += 1
            await human_delay(0.1, 0.3)
        except Exception:
            pass
    print(f"  {C.DIM}  ↳ {session_name}: удалено {deleted}{C.RST}")


async def action_delete_own():
    target = ask("Канал/чат: ")
    limit = ask_int("Макс. кол-во: ", 100)
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_delete_own_messages,
        task_name="🗑 Удаление своих сообщений",
        target=target, limit=limit
    )


# ─────────────────────────────────────────────────────────────
# 20. СОЗДАТЬ КАНАЛ/ГРУППУ
# ─────────────────────────────────────────────────────────────

async def task_create_channel(client, session_name, **kw):
    title = kw["title"]
    about = kw.get("about", "")
    megagroup = kw.get("megagroup", False)

    result = await client(CreateChannelRequest(
        title=title,
        about=about,
        megagroup=megagroup
    ))
    channel = result.chats[0]
    print(f"  {C.G}  ↳ {session_name}: создан {'группа' if megagroup else 'канал'} "
          f"id={channel.id}{C.RST}")


async def action_create_channel():
    title = ask("Название: ")
    about = ask("Описание: ", "")
    print(f"  1. Канал  2. Группа (мегагруппа)")
    ch = ask_int("Тип: ", 1)
    megagroup = ch == 2
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_create_channel,
        task_name="➕ Создание канала/группы",
        title=title, about=about, megagroup=megagroup
    )


# ─────────────────────────────────────────────────────────────
# 21. НАСТРОЙКА КАНАЛА
# ─────────────────────────────────────────────────────────────

async def task_setup_channel(client, session_name, **kw):
    target = kw["target"]
    entity = await resolve_channel(client, target)
    channel = await client.get_input_entity(entity)

    new_title = kw.get("new_title")
    new_about = kw.get("new_about")
    new_username = kw.get("new_username")
    photo_path = kw.get("photo_path")

    if new_title:
        await client(EditTitleRequest(channel=channel, title=new_title))
    if new_about:
        from telethon.tl.functions.channels import EditAboutRequest  # noqa
        # Используем messages.editChatAbout через прямой вызов
        await client(functions.messages.EditChatAboutRequest(
            peer=entity, about=new_about
        ))
    if new_username:
        await client(UpdateUsernameRequest(username=new_username))
    if photo_path and os.path.exists(photo_path):
        photo = await client.upload_file(photo_path)
        await client(EditPhotoRequest(
            channel=channel,
            photo=types.InputChatUploadedPhoto(file=photo)
        ))


async def action_setup_channel():
    target = ask("Канал (@username): ")
    new_title = ask("Новое название (пусто = не менять): ")
    new_about = ask("Новое описание (пусто = не менять): ")
    new_username = ask("Новый username (пусто = не менять): ")
    photo_path = ask("Путь к фото (пусто = не менять): ")

    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_setup_channel,
        task_name="⚙️ Настройка канала",
        target=target,
        new_title=new_title if new_title else None,
        new_about=new_about if new_about else None,
        new_username=new_username if new_username else None,
        photo_path=photo_path if photo_path else None
    )


# ─────────────────────────────────────────────────────────────
# 22. НАЗНАЧИТЬ АДМИНА
# ─────────────────────────────────────────────────────────────

async def task_promote_admin(client, session_name, **kw):
    target = kw["target"]
    user = kw["user"]
    rights = kw["rights"]

    entity = await resolve_channel(client, target)
    user_entity = await client.get_entity(user)

    await client(EditAdminRequest(
        channel=entity,
        user_id=user_entity,
        admin_rights=rights,
        rank=kw.get("rank", "Admin")
    ))


async def action_promote_admin():
    target = ask("Канал (@username): ")
    user = ask("Юзер для назначения (@username): ")
    rank = ask("Титул (Admin): ", "Admin")

    print(f"\n{C.Y}  Выбери права:{C.RST}")
    print(f"  1. Полные права")
    print(f"  2. Только посты")
    print(f"  3. Модератор (бан, удаление)")
    print(f"  4. Кастомные")
    ch = ask_int("Выбор: ", 1)

    if ch == 1:
        rights = ChatAdminRights(
            change_info=True, post_messages=True, edit_messages=True,
            delete_messages=True, ban_users=True, invite_users=True,
            pin_messages=True, add_admins=True, manage_call=True
        )
    elif ch == 2:
        rights = ChatAdminRights(post_messages=True, edit_messages=True)
    elif ch == 3:
        rights = ChatAdminRights(
            delete_messages=True, ban_users=True, pin_messages=True
        )
    else:
        print(f"  {C.DIM}Введи y/n для каждого права:{C.RST}")
        rights = ChatAdminRights(
            change_info=ask("change_info (y/n): ", "n") == "y",
            post_messages=ask("post_messages (y/n): ", "n") == "y",
            edit_messages=ask("edit_messages (y/n): ", "n") == "y",
            delete_messages=ask("delete_messages (y/n): ", "n") == "y",
            ban_users=ask("ban_users (y/n): ", "n") == "y",
            invite_users=ask("invite_users (y/n): ", "n") == "y",
            pin_messages=ask("pin_messages (y/n): ", "n") == "y",
            add_admins=ask("add_admins (y/n): ", "n") == "y",
            manage_call=ask("manage_call (y/n): ", "n") == "y",
        )

    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_promote_admin,
        task_name="👑 Назначение админа",
        target=target, user=user, rights=rights, rank=rank
    )


# ─────────────────────────────────────────────────────────────
# 23. МАССОВЫЙ БАН/КИК
# ─────────────────────────────────────────────────────────────

async def task_ban_users(client, session_name, **kw):
    target = kw["target"]
    usernames = kw["usernames"]
    kick_only = kw.get("kick_only", False)

    entity = await resolve_channel(client, target)

    ban_rights = ChatBannedRights(
        until_date=None if not kick_only else timedelta(seconds=30),
        view_messages=True,
        send_messages=True,
        send_media=True
    )

    for username in usernames:
        try:
            user = await client.get_entity(username)
            await client(EditBannedRequest(
                channel=entity,
                participant=user,
                banned_rights=ban_rights
            ))
            if kick_only:
                # Разбан через секунду (кик)
                await asyncio.sleep(1)
                await client(EditBannedRequest(
                    channel=entity,
                    participant=user,
                    banned_rights=ChatBannedRights(until_date=None)
                ))
            await human_delay(0.3, 0.8)
        except Exception as e:
            print(f"  {C.R}  ↳ {username}: {e}{C.RST}")


async def action_ban_kick():
    target = ask("Канал/группа: ")
    print(f"  1. Бан  2. Кик")
    mode = ask_int("Режим: ", 1)
    print(f"{C.Y}  Юзернеймы (по одному, пустая = конец):{C.RST}")
    usernames = []
    while True:
        u = input("  @").strip().lstrip("@")
        if not u:
            break
        usernames.append(u)
    if not usernames:
        file_path = ask("Файл: ")
        if file_path and os.path.exists(file_path):
            with open(file_path) as f:
                usernames = [l.strip().lstrip("@") for l in f if l.strip()]
    if not usernames:
        return
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions[:1], task_ban_users,
        task_name="🔨 Бан/кик",
        target=target, usernames=usernames,
        kick_only=(mode == 2)
    )


# ─────────────────────────────────────────────────────────────
# 24. ОЧИСТКА КАНАЛА
# ─────────────────────────────────────────────────────────────

async def task_clear_channel(client, session_name, **kw):
    target = kw["target"]
    entity = await resolve_channel(client, target)

    deleted = 0
    async for msg in client.iter_messages(entity, limit=None):
        try:
            await msg.delete()
            deleted += 1
            if deleted % 100 == 0:
                print(f"  {C.DIM}  ↳ удалено {deleted}...{C.RST}")
                await asyncio.sleep(0.5)
        except Exception:
            pass
    print(f"  {C.G}  ↳ Всего удалено: {deleted}{C.RST}")


async def action_clear_channel():
    target = ask("Канал для очистки: ")
    confirm = ask(f"⚠️ Удалить ВСЕ посты из {target}? (yes/no): ")
    if confirm.lower() != "yes":
        print(f"{C.Y}  Отменено{C.RST}")
        return
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions[:1], task_clear_channel,
        task_name="🧹 Очистка канала",
        target=target
    )


# ─────────────────────────────────────────────────────────────
# 25. КОПИРОВАТЬ НАСТРОЙКИ КАНАЛА
# ─────────────────────────────────────────────────────────────

async def task_copy_channel(client, session_name, **kw):
    source = kw["source"]
    dest = kw["dest"]

    src_entity = await resolve_channel(client, source)
    dst_entity = await resolve_channel(client, dest)
    dst_input = await client.get_input_entity(dst_entity)

    full = await client(GetFullChannelRequest(src_entity))

    # Копируем title
    await client(EditTitleRequest(channel=dst_input, title=src_entity.title))
    # Копируем about
    if full.full_chat.about:
        await client(functions.messages.EditChatAboutRequest(
            peer=dst_entity, about=full.full_chat.about
        ))
    # Копируем фото
    if src_entity.photo:
        photo = await client.download_profile_photo(src_entity, file=bytes)
        if photo:
            uploaded = await client.upload_file(photo)
            await client(EditPhotoRequest(
                channel=dst_input,
                photo=types.InputChatUploadedPhoto(file=uploaded)
            ))


async def action_copy_channel():
    source = ask("Исходный канал (@source): ")
    dest = ask("Целевой канал (@dest): ")
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions[:1], task_copy_channel,
        task_name="📋 Копирование настроек",
        source=source, dest=dest
    )


# ─────────────────────────────────────────────────────────────
# 26. РЕПОРТ НА ЮЗЕРА/КАНАЛ
# ─────────────────────────────────────────────────────────────

REPORT_REASONS = {
    1: ("Спам", InputReportReasonSpam()),
    2: ("Насилие", InputReportReasonViolence()),
    3: ("Порнография", InputReportReasonPornography()),
    4: ("Детское насилие", InputReportReasonChildAbuse()),
    5: ("Наркотики", InputReportReasonIllegalDrugs()),
    6: ("Фейк", InputReportReasonFake()),
    7: ("Геонерелевант", InputReportReasonGeoIrrelevant()),
    8: ("Другое", InputReportReasonOther()),
}


async def task_report_channel(client, session_name, **kw):
    target = kw["target"]
    reason = kw["reason"]
    message = kw.get("message", "")

    entity = await resolve_channel(client, target)

    # Получаем последние сообщения для репорта
    msgs = await client.get_messages(entity, limit=5)
    msg_ids = [m.id for m in msgs if m]

    if msg_ids:
        await client(ReportRequest(
            peer=entity,
            id=msg_ids,
            reason=reason,
            message=message
        ))
    await human_delay(1.0, 2.0)


async def action_report_channel():
    target = ask("Канал/юзер для репорта: ")
    print(f"\n{C.Y}  Причины:{C.RST}")
    for k, (name, _) in REPORT_REASONS.items():
        print(f"  {k}. {name}")
    reason_idx = ask_int("Причина: ", 1)
    reason = REPORT_REASONS.get(reason_idx, REPORT_REASONS[8])[1]
    message = ask("Комментарий к репорту: ", "")
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_report_channel,
        task_name="🚨 Репорт",
        target=target, reason=reason, message=message
    )


# ─────────────────────────────────────────────────────────────
# 27. РЕПОРТ НА СООБЩЕНИЕ
# ─────────────────────────────────────────────────────────────

async def task_report_message(client, session_name, **kw):
    channel = kw["channel"]
    post_id = kw["post_id"]
    reason = kw["reason"]
    message = kw.get("message", "")

    entity = await resolve_channel(client, channel)
    await client(ReportRequest(
        peer=entity,
        id=[post_id],
        reason=reason,
        message=message
    ))
    await human_delay(1.0, 2.0)


async def action_report_message():
    link = ask("Ссылка на сообщение: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Нужна ссылка на конкретное сообщение{C.RST}")
        return
    print(f"\n{C.Y}  Причины:{C.RST}")
    for k, (name, _) in REPORT_REASONS.items():
        print(f"  {k}. {name}")
    reason_idx = ask_int("Причина: ", 1)
    reason = REPORT_REASONS.get(reason_idx, REPORT_REASONS[8])[1]
    message = ask("Комментарий: ", "")
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_report_message,
        task_name="🚨 Репорт на сообщение",
        channel=parsed["channel"],
        post_id=parsed["post_id"],
        reason=reason, message=message
    )


# ─────────────────────────────────────────────────────────────
# 28. МАССОВАЯ БЛОКИРОВКА
# ─────────────────────────────────────────────────────────────

async def task_block_user(client, session_name, **kw):
    usernames = kw["usernames"]
    for username in usernames:
        try:
            user = await client.get_entity(username)
            await client(functions.contacts.BlockRequest(id=user))
            await human_delay(0.3, 0.8)
        except Exception as e:
            print(f"  {C.R}  ↳ {username}: {e}{C.RST}")


async def action_block_users():
    print(f"{C.Y}  Юзернеймы для блокировки (пустая = конец):{C.RST}")
    usernames = []
    while True:
        u = input("  @").strip().lstrip("@")
        if not u:
            break
        usernames.append(u)
    if not usernames:
        return
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_block_user,
        task_name="🚫 Массовая блокировка",
        usernames=usernames
    )


# ─────────────────────────────────────────────────────────────
# 29. ПАРСЕР УЧАСТНИКОВ
# ─────────────────────────────────────────────────────────────

async def action_parse_members():
    target = ask("Канал/группа: ")
    parsed = parse_tg_link(target)
    if not parsed["channel"]:
        print(f"{C.R}❌ Неверный канал{C.RST}")
        return
    limit = ask_int("Макс. кол-во: ", 1000)

    sessions = get_sessions()
    if not sessions:
        print(f"{C.R}❌ Нет сессий{C.RST}")
        return

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)
    if not await safe_connect(client, sessions[0]):
        return

    try:
        entity = await resolve_channel(client, parsed["channel"])
        members = []
        offset = 0
        batch = 200

        while len(members) < limit:
            participants = await client(GetParticipantsRequest(
                channel=entity,
                filter=ChannelParticipantsSearch(""),
                offset=offset,
                limit=min(batch, limit - len(members)),
                hash=0
            ))
            if not participants.users:
                break
            for user in participants.users:
                info = {
                    "id": user.id,
                    "username": user.username or "",
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                    "phone": user.phone or "",
                    "bot": user.bot,
                }
                members.append(info)
            offset += len(participants.users)
            if len(participants.users) < batch:
                break

        # Сохраняем
        filename = f"members_{parsed['channel']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(members, f, ensure_ascii=False, indent=2)

        # Также txt с юзернеймами
        txt_file = filename.replace(".json", ".txt")
        with open(txt_file, "w") as f:
            for m in members:
                if m["username"]:
                    f.write(f"@{m['username']}\n")

        print(f"\n{C.G}✅ Спарсено: {len(members)} участников{C.RST}")
        print(f"  JSON: {filename}")
        print(f"  TXT:  {txt_file}")

    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 30. СТАТИСТИКА КАНАЛА
# ─────────────────────────────────────────────────────────────

async def action_channel_stats():
    target = ask("Канал: ")
    parsed = parse_tg_link(target)
    if not parsed["channel"]:
        return

    sessions = get_sessions()
    if not sessions:
        return

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)
    if not await safe_connect(client, sessions[0]):
        return

    try:
        entity = await resolve_channel(client, parsed["channel"])
        full = await client(GetFullChannelRequest(entity))

        print(f"\n{C.CY}{'═' * 50}")
        print(f"  📊 Статистика: {entity.title}")
        print(f"{'═' * 50}{C.RST}")
        print(f"  ID:           {entity.id}")
        print(f"  Username:     @{entity.username or 'нет'}")
        print(f"  Подписчики:   {format_count(full.full_chat.participants_count or 0)}")
        print(f"  Описание:     {(full.full_chat.about or '')[:100]}")
        print(f"  Создатель:    {'Да' if entity.creator else 'Нет'}")
        print(f"  Мегагруппа:   {'Да' if entity.megagroup else 'Нет'}")

        # Последние посты
        msgs = await client.get_messages(entity, limit=10)
        if msgs:
            total_views = sum(m.views or 0 for m in msgs)
            avg_views = total_views // len(msgs) if msgs else 0
            print(f"  Ср. просмотры: {format_count(avg_views)} (10 постов)")

        print(f"{C.CY}{'═' * 50}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 31. СКАЧИВАНИЕ МЕДИА
# ─────────────────────────────────────────────────────────────

async def action_download_media():
    link = ask("Ссылка на пост или канал: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"]:
        return

    limit = 1
    if parsed["post_id"]:
        limit = 1
    else:
        limit = ask_int("Кол-во последних постов: ", 10)

    output_dir = ask("Папка для сохранения: ", "downloads")
    os.makedirs(output_dir, exist_ok=True)

    sessions = get_sessions()
    if not sessions:
        return

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)
    if not await safe_connect(client, sessions[0]):
        return

    try:
        entity = await resolve_channel(client, parsed["channel"])
        downloaded = 0

        if parsed["post_id"]:
            msg = await client.get_messages(entity, ids=parsed["post_id"])
            if msg and msg.media:
                path = await client.download_media(msg, file=output_dir)
                print(f"  {C.G}📥 {path}{C.RST}")
                downloaded += 1
        else:
            async for msg in client.iter_messages(entity, limit=limit):
                if msg.media:
                    try:
                        path = await client.download_media(msg, file=output_dir)
                        print(f"  {C.G}📥 {path}{C.RST}")
                        downloaded += 1
                    except Exception:
                        pass

        print(f"\n{C.G}✅ Скачано: {downloaded} файлов{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 32. МОНИТОРИНГ (авто-реакции на новые посты)
# ─────────────────────────────────────────────────────────────

async def action_monitor():
    target = ask("Канал для мониторинга: ")
    parsed = parse_tg_link(target)
    if not parsed["channel"]:
        return
    reaction = ask_reaction()
    do_view = ask("Автопросмотр? (y/n): ", "y") == "y"

    sessions = get_sessions()
    if not sessions:
        return

    print(f"\n{C.G}👀 Мониторинг запущен. Ctrl+C для остановки{C.RST}")

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)
    if not await safe_connect(client, sessions[0]):
        return

    try:
        entity = await resolve_channel(client, parsed["channel"])

        @client.on(events.NewMessage(chats=entity))
        async def handler(event):
            msg = event.message
            print(f"  {C.CY}📨 Новый пост #{msg.id}{C.RST}")

            if do_view:
                await client(GetMessagesViewsRequest(
                    peer=entity, id=[msg.id], increment=True
                ))

            react_obj = ReactionEmoji(emoticon=reaction)
            try:
                await client(SendReactionRequest(
                    peer=entity, msg_id=msg.id,
                    reaction=[react_obj]
                ))
                print(f"  {C.G}  ✅ Реакция {reaction} поставлена{C.RST}")
            except Exception as e:
                print(f"  {C.R}  ❌ {e}{C.RST}")

        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print(f"\n{C.Y}⏹ Мониторинг остановлен{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 33. АВТО-ОТВЕТЧИК ПО КЛЮЧЕВЫМ СЛОВАМ
# ─────────────────────────────────────────────────────────────

async def action_auto_responder():
    print(f"{C.Y}  Введи пары: ключевое_слово -> ответ (пустая = конец):{C.RST}")
    rules = {}
    while True:
        keyword = ask("Ключевое слово: ")
        if not keyword:
            break
        response = ask("Ответ: ")
        rules[keyword.lower()] = response

    if not rules:
        print(f"{C.R}❌ Нет правил{C.RST}")
        return

    sessions = get_sessions()
    if not sessions:
        return

    print(f"\n{C.G}🤖 Авто-ответчик запущен. Ctrl+C для остановки{C.RST}")
    print(f"  Правила: {len(rules)}")

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)
    if not await safe_connect(client, sessions[0]):
        return

    try:
        @client.on(events.NewMessage(incoming=True))
        async def handler(event):
            if not event.message or not event.message.text:
                return
            text = event.message.text.lower()
            for keyword, response in rules.items():
                if keyword in text:
                    await event.reply(response)
                    print(f"  {C.G}↩️ Ответил на '{keyword}'{C.RST}")
                    break

        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print(f"\n{C.Y}⏹ Авто-ответчик остановлен{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 34. АВТО-ПОСТИНГ
# ─────────────────────────────────────────────────────────────

async def action_auto_posting():
    target = ask("Канал для постинга (@username): ")
    parsed = parse_tg_link(target)
    if not parsed["channel"]:
        return

    print(f"{C.Y}  Введи посты (каждый с новой строки, пустая = конец):{C.RST}")
    posts = []
    while True:
        p = input("  > ").strip()
        if not p:
            break
        posts.append(p)
    if not posts:
        return

    interval = ask_int("Интервал (минуты): ", 60)

    sessions = get_sessions()
    if not sessions:
        return

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)
    if not await safe_connect(client, sessions[0]):
        return

    print(f"\n{C.G}📝 Авто-постинг запущен. Ctrl+C для остановки{C.RST}")
    print(f"  Постов: {len(posts)} | Интервал: {interval} мин")

    try:
        entity = await resolve_channel(client, parsed["channel"])
        idx = 0
        while True:
            post = posts[idx % len(posts)]
            await client.send_message(entity, post)
            print(f"  {C.G}📤 Пост #{idx + 1}: {post[:50]}...{C.RST}")
            idx += 1
            await asyncio.sleep(interval * 60)
    except KeyboardInterrupt:
        print(f"\n{C.Y}⏹ Авто-постинг остановлен{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 35. ЗАДАЧИ ИЗ JSON
# ─────────────────────────────────────────────────────────────

async def action_tasks_from_json():
    """
    Формат JSON:
    {
      "tasks": [
        {"action": "subscribe", "channel": "@test"},
        {"action": "view", "link": "t.me/test/123"},
        {"action": "react", "link": "t.me/test/123", "reaction": "👍"},
        {"action": "comment", "link": "t.me/test/123", "text": "Nice!"},
        {"action": "start_bot", "bot": "@bot", "param": "ref123"},
        {"action": "delay", "seconds": 5}
      ]
    }
    """
    file_path = ask("Путь к JSON файлу с задачами: ")
    if not file_path or not os.path.exists(file_path):
        print(f"{C.R}❌ Файл не найден{C.RST}")
        return

    with open(file_path) as f:
        data = json.load(f)

    tasks_list = data.get("tasks", [])
    if not tasks_list:
        print(f"{C.R}❌ Нет задач{C.RST}")
        return

    sessions = select_sessions()
    if not sessions:
        return

    proxies = load_proxies()

    print(f"\n{C.G}📋 Выполняю {len(tasks_list)} задач на {len(sessions)} сессиях{C.RST}")

    for i, session_name in enumerate(sessions):
        proxy = proxies[i % len(proxies)] if proxies else None
        client = await create_client(session_name, proxy)
        if not await safe_connect(client, session_name):
            continue

        try:
            for task in tasks_list:
                action = task.get("action", "")
                try:
                    if action == "subscribe":
                        p = parse_tg_link(task.get("channel", ""))
                        entity = await resolve_channel(client, p["channel"])
                        await client(JoinChannelRequest(entity))

                    elif action == "view":
                        p = parse_tg_link(task.get("link", ""))
                        entity = await resolve_channel(client, p["channel"])
                        await client(GetMessagesViewsRequest(
                            peer=entity, id=[p["post_id"]], increment=True
                        ))

                    elif action == "react":
                        p = parse_tg_link(task.get("link", ""))
                        entity = await resolve_channel(client, p["channel"])
                        r = ReactionEmoji(emoticon=task.get("reaction", "👍"))
                        await client(SendReactionRequest(
                            peer=entity, msg_id=p["post_id"], reaction=[r]
                        ))

                    elif action == "comment":
                        p = parse_tg_link(task.get("link", ""))
                        entity = await resolve_channel(client, p["channel"])
                        await client.send_message(
                            entity, task.get("text", "👍"),
                            comment_to=p["post_id"]
                        )

                    elif action == "start_bot":
                        bot_entity = await client.get_entity(task["bot"])
                        param = task.get("param", "")
                        if param:
                            await client(StartBotRequest(
                                bot=bot_entity, peer=bot_entity, start_param=param
                            ))
                        else:
                            await client.send_message(bot_entity, "/start")

                    elif action == "delay":
                        await asyncio.sleep(task.get("seconds", 1))

                    print(f"  {C.G}  ✅ {session_name}: {action}{C.RST}")
                except Exception as e:
                    print(f"  {C.R}  ❌ {session_name}: {action} — {e}{C.RST}")

                await human_delay(1.0, 3.0)

        finally:
            await client.disconnect()

    print(f"\n{C.G}✅ Все задачи выполнены{C.RST}")


# ═══════════════════════════════════════════════════════════════
# КОНЕЦ ЧАСТИ 2
# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
# ЧАСТЬ 3 — ФУНКЦИИ 36-50 + ГЛАВНЫЙ ЦИКЛ
# ═══════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# 36. ПРОГРЕВ (чтение, скролл, профили)
# ─────────────────────────────────────────────────────────────

async def task_warmup(client, session_name, **kw):
    intensity = kw.get("intensity", "medium")

    if intensity == "light":
        actions = 5
        delay_range = (3.0, 8.0)
    elif intensity == "heavy":
        actions = 25
        delay_range = (1.0, 4.0)
    else:
        actions = 12
        delay_range = (2.0, 6.0)

    me = await client.get_me()
    print(f"  {C.DIM}  ↳ {session_name}: прогрев ({intensity}, {actions} действий){C.RST}")

    dialogs = await client.get_dialogs(limit=30)
    random.shuffle(dialogs)

    action_count = 0
    for dialog in dialogs[:actions]:
        try:
            action_type = random.choice(["read", "scroll", "profile", "read", "scroll"])

            if action_type == "read":
                # Чтение последних сообщений
                msgs = await client.get_messages(dialog.entity, limit=random.randint(3, 15))
                if msgs:
                    await client(ReadHistoryRequest(
                        peer=dialog.entity,
                        max_id=msgs[0].id
                    ))
                action_count += 1

            elif action_type == "scroll":
                # Имитация скролла — загрузка сообщений пачками
                offset_id = 0
                for _ in range(random.randint(1, 4)):
                    history = await client(GetHistoryRequest(
                        peer=dialog.entity,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        limit=20,
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                    if history.messages:
                        offset_id = history.messages[-1].id
                    await asyncio.sleep(random.uniform(0.3, 1.0))
                action_count += 1

            elif action_type == "profile":
                # Просмотр профиля
                if isinstance(dialog.entity, User) and not dialog.entity.bot:
                    try:
                        await client(GetFullUserRequest(dialog.entity))
                    except Exception:
                        pass
                elif isinstance(dialog.entity, (Channel, Chat)):
                    try:
                        if hasattr(dialog.entity, 'megagroup') or hasattr(dialog.entity, 'broadcast'):
                            await client(GetFullChannelRequest(dialog.entity))
                    except Exception:
                        pass
                action_count += 1

            await asyncio.sleep(random.uniform(*delay_range))

        except FloodWaitError as e:
            await asyncio.sleep(min(e.seconds, 30))
        except Exception:
            pass

    # Имитация набора текста (в Избранное)
    try:
        saved = await client.get_entity("me")
        # Устанавливаем статус онлайн
        await client(UpdateStatusRequest(offline=False))
        await asyncio.sleep(random.uniform(2, 5))
        await client(UpdateStatusRequest(offline=True))
    except Exception:
        pass

    print(f"  {C.G}  ↳ {session_name}: выполнено {action_count} действий{C.RST}")


async def action_warmup():
    print(f"\n{C.Y}  Интенсивность прогрева:{C.RST}")
    print(f"  1. 🟢 Лёгкий (5 действий, большие паузы)")
    print(f"  2. 🟡 Средний (12 действий)")
    print(f"  3. 🔴 Тяжёлый (25 действий, малые паузы)")
    ch = ask_int("Выбор: ", 2)
    intensity = {1: "light", 2: "medium", 3: "heavy"}.get(ch, "medium")

    sessions = select_sessions("Выбери аккаунты для прогрева")
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_warmup,
        task_name="🔥 Прогрев аккаунтов",
        max_concurrent=3,
        delay_between=(2.0, 5.0),
        intensity=intensity
    )


# ─────────────────────────────────────────────────────────────
# 37. ИМИТАЦИЯ ОНЛАЙНА (параллельно)
# ─────────────────────────────────────────────────────────────

async def action_online_imitation():
    duration = ask_int("Длительность (минуты): ", 60)
    interval = ask_int("Интервал пинга (секунды): ", 30)

    sessions = select_sessions("Аккаунты для имитации онлайна")
    if not sessions:
        return

    proxies = load_proxies()
    clients = []

    print(f"\n{C.G}🟢 Запуск имитации онлайна на {len(sessions)} аккаунтах{C.RST}")
    print(f"  Длительность: {duration} мин | Интервал: {interval} сек")
    print(f"  Ctrl+C для остановки\n")

    # Подключаем все клиенты
    for i, session_name in enumerate(sessions):
        proxy = proxies[i % len(proxies)] if proxies else None
        client = await create_client(session_name, proxy)
        if await safe_connect(client, session_name):
            clients.append((client, session_name))
            print(f"  {C.G}✅ {session_name} подключён{C.RST}")
        else:
            print(f"  {C.R}❌ {session_name} не подключился{C.RST}")

    if not clients:
        print(f"{C.R}❌ Нет подключённых клиентов{C.RST}")
        return

    end_time = time.time() + (duration * 60)

    try:
        cycle = 0
        while time.time() < end_time:
            cycle += 1
            for client, name in clients:
                try:
                    await client(UpdateStatusRequest(offline=False))
                except Exception:
                    pass

            remaining = int((end_time - time.time()) / 60)
            print(f"  {C.DIM}  Цикл {cycle} | Осталось ~{remaining} мин | "
                  f"{len(clients)} аккаунтов онлайн{C.RST}", end="\r")

            # Случайные действия для натуральности
            if cycle % 5 == 0:
                rc = random.choice(clients)
                try:
                    dialogs = await rc[0].get_dialogs(limit=3)
                    if dialogs:
                        d = random.choice(dialogs)
                        await rc[0].get_messages(d.entity, limit=3)
                except Exception:
                    pass

            await asyncio.sleep(interval + random.uniform(-5, 5))

    except KeyboardInterrupt:
        print(f"\n{C.Y}⏹ Остановка...{C.RST}")
    finally:
        for client, name in clients:
            try:
                await client(UpdateStatusRequest(offline=True))
                await client.disconnect()
            except Exception:
                pass
        print(f"\n{C.G}✅ Все аккаунты переведены в оффлайн{C.RST}")


# ─────────────────────────────────────────────────────────────
# 38. ЧЕКЕР АККАУНТОВ
# ─────────────────────────────────────────────────────────────

async def action_checker():
    sessions = get_sessions()
    if not sessions:
        print(f"{C.R}❌ Нет сессий{C.RST}")
        return

    proxies = load_proxies()
    alive = []
    dead = []
    banned = []

    print(f"\n{C.CY}{'═' * 50}")
    print(f"  ✅ Чекер аккаунтов ({len(sessions)} сессий)")
    print(f"{'═' * 50}{C.RST}\n")

    for i, session_name in enumerate(sessions):
        proxy = proxies[i % len(proxies)] if proxies else None
        client = await create_client(session_name, proxy)

        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                phone = me.phone or "?"
                name = f"{me.first_name or ''} {me.last_name or ''}".strip()
                username = f"@{me.username}" if me.username else ""
                print(f"  {C.G}✅ {session_name}: +{phone} {name} {username}{C.RST}")
                alive.append(session_name)
            else:
                print(f"  {C.Y}⚠️ {session_name}: не авторизован{C.RST}")
                dead.append(session_name)
        except (PhoneNumberBannedError, UserDeactivatedBanError, UserDeactivatedError):
            print(f"  {C.R}💀 {session_name}: ЗАБАНЕН{C.RST}")
            banned.append(session_name)
        except AuthKeyUnregisteredError:
            print(f"  {C.R}🔑 {session_name}: сессия невалидна{C.RST}")
            dead.append(session_name)
        except Exception as e:
            print(f"  {C.R}❌ {session_name}: {e}{C.RST}")
            dead.append(session_name)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    print(f"\n{C.CY}{'═' * 50}")
    print(f"  📊 Результат:")
    print(f"    {C.G}✅ Живые:     {len(alive)}{C.RST}")
    print(f"    {C.R}💀 Баны:      {len(banned)}{C.RST}")
    print(f"    {C.Y}⚠️ Мёртвые:   {len(dead)}{C.RST}")
    print(f"{C.CY}{'═' * 50}{C.RST}")

    if banned or dead:
        move = ask("Переместить мёртвые/баны в dead_sessions/? (y/n): ", "n")
        if move == "y":
            dead_dir = BASE_DIR / "dead_sessions"
            dead_dir.mkdir(exist_ok=True)
            for s in banned + dead:
                src = SESSIONS_DIR / f"{s}.session"
                dst = dead_dir / f"{s}.session"
                if src.exists():
                    src.rename(dst)
                    print(f"  {C.DIM}  ↳ {s} → dead_sessions/{C.RST}")


# ─────────────────────────────────────────────────────────────
# 39. АКТИВНЫЕ СЕССИИ
# ─────────────────────────────────────────────────────────────

async def action_active_sessions():
    sessions = select_sessions("Выбери аккаунты")
    if not sessions:
        return

    proxies = load_proxies()

    for i, session_name in enumerate(sessions):
        proxy = proxies[i % len(proxies)] if proxies else None
        client = await create_client(session_name, proxy)
        if not await safe_connect(client, session_name):
            continue

        try:
            # Получаем время создания файла сессии как время создания текущей сессии
            session_path = SESSIONS_DIR / f"{session_name}.session"
            local_creation_time = "Неизвестно"
            if session_path.exists():
                local_creation_time = datetime.fromtimestamp(session_path.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S')

            result = await client(GetAuthorizationsRequest())
            print(f"\n{C.CY}  📱 Сессии для {session_name}:{C.RST}")
            print(f"  {C.DIM}Локальный файл сессии создан: {local_creation_time}{C.RST}")

            for j, auth in enumerate(result.authorizations):
                current = " 👈 ТЕКУЩАЯ" if auth.current else ""
                # Конвертируем дату в читаемый формат
                created_date = auth.date_created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(auth.date_created,
                                                                                          'strftime') else str(
                    auth.date_created)
                active_date = auth.date_active.strftime('%Y-%m-%d %H:%M:%S') if hasattr(auth.date_active,
                                                                                        'strftime') else str(
                    auth.date_active)

                print(f"    {j + 1}. {auth.device_model} | {auth.platform} | "
                      f"{auth.app_name} v{auth.app_version}")
                print(f"       IP: {auth.ip} | Регион: {auth.country}")
                print(f"       Создана: {created_date} | "
                      f"Активна: {active_date}{C.G}{current}{C.RST}")
                print(f"       Hash: {auth.hash}")
                print()
        finally:
            await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 40. СБРОС ВСЕХ СЕССИЙ
# ─────────────────────────────────────────────────────────────

async def task_reset_all_sessions(client, session_name, **kw):
    result = await client(GetAuthorizationsRequest())
    count = 0
    for auth in result.authorizations:
        if not auth.current:
            try:
                await client(ResetAuthorizationRequest(hash=auth.hash))
                count += 1
                await human_delay(0.3, 0.8)
            except Exception:
                pass
    print(f"  {C.DIM}  ↳ {session_name}: сброшено {count} сессий{C.RST}")


async def action_reset_all_sessions():
    confirm = ask("⚠️ Сбросить ВСЕ сессии (кроме текущей)? (yes/no): ")
    if confirm.lower() != "yes":
        return
    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_reset_all_sessions,
        task_name="💀 Сброс всех сессий"
    )


# ─────────────────────────────────────────────────────────────
# 41. ВЫБОРОЧНЫЙ СБРОС
# ─────────────────────────────────────────────────────────────

async def action_selective_reset():
    sessions = select_sessions("Выбери аккаунт")
    if not sessions:
        return

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(sessions[0], proxy)
    if not await safe_connect(client, sessions[0]):
        return

    try:
        result = await client(GetAuthorizationsRequest())
        auths = []
        print(f"\n{C.CY}  Сессии:{C.RST}")
        for j, auth in enumerate(result.authorizations):
            if auth.current:
                print(f"  {C.G}{j + 1}. [ТЕКУЩАЯ] {auth.device_model} | {auth.app_name}{C.RST}")
            else:
                print(f"  {C.W}{j + 1}. {auth.device_model} | {auth.app_name} | "
                      f"IP: {auth.ip} | {auth.date_active}{C.RST}")
            auths.append(auth)

        indices = ask("Номера для сброса (через запятую): ")
        if not indices:
            return

        for idx_str in indices.split(","):
            try:
                idx = int(idx_str.strip()) - 1
                if 0 <= idx < len(auths) and not auths[idx].current:
                    await client(ResetAuthorizationRequest(hash=auths[idx].hash))
                    print(f"  {C.G}✅ Сессия {idx + 1} сброшена{C.RST}")
                elif auths[idx].current:
                    print(f"  {C.Y}⚠️ Нельзя сбросить текущую сессию{C.RST}")
            except Exception as e:
                print(f"  {C.R}❌ {e}{C.RST}")

    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 42. ЗАПРОС КОДА + 2FA (создание новой сессии)
# ─────────────────────────────────────────────────────────────

async def action_new_session():
    api_id, api_hash = get_api_credentials()
    phone = ask("Номер телефона (+79...): ")
    if not phone:
        return

    session_name = phone.replace("+", "").replace(" ", "")
    proxy_str_val = ask("Прокси (пусто = без прокси): ")
    proxy = parse_proxy(proxy_str_val) if proxy_str_val else None

    client = await create_client(session_name, proxy)
    await client.connect()

    try:
        email_addr = ask("Email (если требуется для входа, иначе пусто): ")
        if email_addr:
            # Начинаем вход с email, если Telethon поддерживает (в 1.42+ есть нюансы)
            # В обычной сессии сначала запрашиваем код на телефон
            pass

        result = await client.send_code_request(phone)
        print(f"{C.G}✅ Код отправлен{C.RST}")
        code = ask("Введи код из Telegram: ")

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            print(f"{C.Y}🔐 Требуется 2FA пароль{C.RST}")
            password = ask("2FA паро_ль: ")
            await client.sign_in(password=password)
        except Exception as e:
            if "email" in str(e).lower():
                print(f"{C.Y}📧 Требуется подтверждение по Email{C.RST}")
                email_code = ask("Введи код из Email: ")
                # Попытка войти через email в современных версиях Telethon
                # (Зависит от того, какой именно метод запросил сервер)
                # В простейшем случае:
                await client.sign_in(phone, code, email_code=email_code)
            else:
                raise e

        me = await client.get_me()
        print(f"{C.G}✅ Авторизован: {me.first_name} (@{me.username or '?'}) +{me.phone}{C.RST}")

        # Перемещаем сессию в sessions/
        src = Path(f"{session_name}.session")
        dst = SESSIONS_DIR / f"{session_name}.session"
        if src.exists() and not dst.exists():
            src.rename(dst)

    except Exception as e:
        print(f"{C.R}❌ Ошибка: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 43. ПОЛУЧИТЬ КОД С АККАУНТА
# ─────────────────────────────────────────────────────────────

async def task_get_auth_code(client, session_name, **kw):
    try:
        # Ищем сервисное сообщение от Telegram с кодом
        messages = await client.get_messages(777000, limit=5)
        for msg in messages:
            if msg.text:
                # Паттерн для кода: 5 или более цифр
                match = re.search(r"(\d{5,})", msg.text)
                if match:
                    code = match.group(1)
                    print(f"  {C.G}🔑 {session_name}: Код {code}{C.RST}")
                    print(f"    {C.DIM}Текст: {msg.text.split('.')[0]}...{C.RST}")
                    return
        print(f"  {C.Y}⚠️ {session_name}: Код не найден в последних сообщениях{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: Ошибка — {e}{C.RST}")


async def action_get_auth_code():
    sessions = select_sessions("Выбери аккаунт для получения кода")
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_get_auth_code,
        task_name="🔑 Получение кода авторизации",
        max_concurrent=1
    )


# ─────────────────────────────────────────────────────────────
# 43. ИНФО ОБ АККАУНТАХ
# ─────────────────────────────────────────────────────────────

async def task_get_info(client, session_name, **kw):
    me = await client.get_me()
    full = await client(GetFullUserRequest(me))

    print(f"\n{C.CY}  ── {session_name} ──{C.RST}")
    print(f"    ID:        {me.id}")
    print(f"    Телефон:   +{me.phone or '?'}")
    print(f"    Имя:       {me.first_name or ''} {me.last_name or ''}")
    print(f"    Username:  @{me.username or 'нет'}")
    print(f"    Бот:       {'Да' if me.bot else 'Нет'}")
    print(f"    Premium:   {'Да' if me.premium else 'Нет'}")
    print(f"    Био:       {full.full_user.about or 'нет'}")
    print(f"    Фото:      {'Есть' if me.photo else 'Нет'}")

    # Кол-во диалогов
    dialogs = await client.get_dialogs(limit=0)
    print(f"    Диалогов:  {dialogs.total if hasattr(dialogs, 'total') else '?'}")


async def action_get_info():
    sessions = select_sessions("Выбери аккаунты")
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_get_info,
        task_name="ℹ️ Информация об аккаунтах",
        max_concurrent=3
    )


# ─────────────────────────────────────────────────────────────
# 44. ИМЯ/БИО
# ─────────────────────────────────────────────────────────────

async def task_update_profile(client, session_name, **kw):
    first_name = kw.get("first_name")
    last_name = kw.get("last_name")
    about = kw.get("about")

    kwargs = {}
    if first_name is not None:
        kwargs["first_name"] = first_name
    if last_name is not None:
        kwargs["last_name"] = last_name
    if about is not None:
        kwargs["about"] = about

    if kwargs:
        await client(UpdateProfileRequest(**kwargs))


async def action_update_profile():
    first = ask("Имя (пусто = не менять): ")
    last = ask("Фамилия (пусто = не менять): ")
    about = ask("Био (пусто = не менять): ")

    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_update_profile,
        task_name="✏️ Обновление профиля",
        first_name=first if first else None,
        last_name=last if last else None,
        about=about if about else None
    )


# ─────────────────────────────────────────────────────────────
# 45. ФОТО ПРОФИЛЯ
# ─────────────────────────────────────────────────────────────

async def task_set_photo(client, session_name, **kw):
    photo_input = kw["photo_path"]
    delete_old = kw.get("delete_old", False)

    if delete_old:
        photos = await client.get_profile_photos("me")
        if photos:
            await client(DeletePhotosRequest(id=[
                types.InputPhoto(
                    id=p.id,
                    access_hash=p.access_hash,
                    file_reference=p.file_reference
                ) for p in photos
            ]))

    if photo_input.startswith(("http://", "https://")):
        # Скачиваем фото по ссылке
        try:
            temp_path = TEMP_DIR / f"photo_{session_name}_{int(time.time())}.jpg"
            async with aiohttp.ClientSession() as session:
                async with session.get(photo_input) as resp:
                    if resp.status == 200:
                        with open(temp_path, "wb") as f:
                            f.write(await resp.read())
                        file = await client.upload_file(str(temp_path))
                        await client(UploadProfilePhotoRequest(file=file))
                        if temp_path.exists():
                            temp_path.unlink()
                    else:
                        print(f"  {C.R}❌ {session_name}: Ошибка загрузки по ссылке ({resp.status}){C.RST}")
        except Exception as e:
            print(f"  {C.R}❌ {session_name}: Ошибка ссылки: {e}{C.RST}")
    elif photo_input and os.path.exists(photo_input):
        file = await client.upload_file(photo_input)
        await client(UploadProfilePhotoRequest(file=file))


async def action_set_photo():
    photo_dir = BASE_DIR / "Фото"
    photo_dir.mkdir(exist_ok=True)

    photos_in_dir = glob.glob(str(photo_dir / "*.*"))
    photos_in_dir = [p for p in photos_in_dir if p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

    if photos_in_dir:
        print(f"\n{C.CY}  Найдено фото в папке 'Фото':{C.RST}")
        for i, p in enumerate(photos_in_dir, 1):
            print(f"    {i}. {Path(p).name}")
        print(f"    0. Ввести путь вручную или ссылку")

        p_idx = ask_int("Выбери номер фото: ", 0)
        if p_idx > 0 and p_idx <= len(photos_in_dir):
            photo_path = photos_in_dir[p_idx - 1]
        else:
            photo_path = ask("Путь к фото или прямая ссылка (http/https): ")
    else:
        photo_path = ask("Путь к фото или прямая ссылка (http/https): ")

    if not photo_path:
        return
    if not photo_path.startswith(("http://", "https://")) and not os.path.exists(photo_path):
        print(f"{C.R}❌ Файл не найден{C.RST}")
        return
    delete_old = ask("Удалить старые фото? (y/n): ", "n") == "y"

    sessions = select_sessions()
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_set_photo,
        task_name="🖼 Установка фото",
        photo_path=photo_path,
        delete_old=delete_old
    )


async def task_check_spambot(client, session_name, **kw):
    """Проверка на спам-блок через @SpamBot"""
    try:
        async with client.conversation("@SpamBot") as conv:
            await conv.send_message("/start")
            response = await conv.get_response()
            if "good news" in response.text.lower() or "никаких ограничений" in response.text.lower():
                print(f"  {C.G}✅ {session_name}: Ограничений нет{C.RST}")
            else:
                status = response.text.split('.')[0]
                print(f"  {C.R}🚫 {session_name}: {status}{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: Ошибка — {e}{C.RST}")


async def action_check_spambot():
    sessions = select_sessions("Выбери аккаунты для проверки на спам-блок")
    if not sessions: return
    await execute_on_sessions(sessions, task_check_spambot, "Проверка спам-блока", max_concurrent=1)


async def action_scenario_constructor():
    print(f"\n{C.CY}🎭 Конструктор сценариев{C.RST}")
    print(f"  Команды: start:ссылка (реф. переход), open:bot (без /start), webapp:bot:кнопка,")
    print(f"           repost:target (история + новые), msg:текст, click:кнопка, wait:сек,")
    print(f"           parse_buttons (выводит список кнопок текущего чата)")
    print(f"  Target для repost: username, ссылка на канал/группу или ID")
    print(f"  Пример: {C.DIM}start:https://t.me/bot?start=ref;repost:my_logs;wait:2{C.RST}")
    steps_input = ask("Введите шаги через ';': ")
    if not steps_input: return

    steps = []
    for s in steps_input.split(";"):
        if ":" in s:
            parts = s.split(":", 1)
            steps.append({"cmd": parts[0].strip(), "val": parts[1].strip()})

    sessions = select_sessions("Выбери аккаунты для выполнения сценария")
    if not sessions: return

    await execute_on_sessions(sessions, task_run_scenario, "Выполнение сценария", steps=steps)


async def task_run_scenario(client, session_name, **kw):
    steps = kw["steps"]
    current_bot = None
    repost_target = None
    current_bot_id = None

    # Обработчик для пересылки новых сообщений
    async def message_handler(event):
        nonlocal repost_target
        if repost_target and event.chat_id == current_bot_id:
            try:
                # Используем forward_messages для надежной пересылки (включая медиа)
                await client.forward_messages(repost_target, event.message)
                print(f"    {session_name}: Переслано новое сообщение от бота в {repost_target}")
            except Exception as e:
                print(f"    {C.R}❌ {session_name}: Ошибка пересылки — {e}{C.RST}")

    for step in steps:
        cmd = step["cmd"]
        val = step["val"]
        try:
            if cmd == "open":
                current_bot = val
                entity = await client.get_input_entity(val)
                current_bot_id = (await client.get_entity(entity)).id
                print(f"    {session_name}: Чат с {val} открыт")

            elif cmd == "start":
                # Глубокие ссылки (Deep Links)
                if "t.me/" in val or "tg://resolve" in val:
                    import re
                    # Извлекаем username и параметр
                    bot_match = re.search(r't\.me/([^/?]+)', val)
                    param_match = re.search(r'start=([^&]+)', val)

                    if bot_match:
                        bot_username = bot_match.group(1)
                        current_bot = bot_username
                        entity = await client.get_input_entity(bot_username)
                        current_bot_id = (await client.get_entity(entity)).id

                        if param_match:
                            start_param = param_match.group(1)
                            from telethon.tl.functions.messages import StartBotRequest
                            # Используем StartBotRequest для честного перехода по ссылке
                            await client(StartBotRequest(bot=entity, peer=entity, start_param=start_param))
                            print(f"    {session_name}: Бот запущен по глубокой ссылке с параметром {start_param}")
                        else:
                            await client.send_message(bot_username, "/start")
                            print(f"    {session_name}: Бот запущен по ссылке")
                        continue

                # Обычный старт
                current_bot = val
                entity = await client.get_input_entity(val)
                current_bot_id = (await client.get_entity(entity)).id
                await client.send_message(val, "/start")
                print(f"    {session_name}: Запущен бот {val}")

            elif cmd == "repost":
                repost_target = val
                # Принудительное получение сущности цели (канал, группа или личка)
                try:
                    target_entity = await client.get_input_entity(val)
                except Exception as e:
                    print(f"    {C.R}❌ Ошибка определения цели {val}: {e}{C.RST}")
                    continue

                if current_bot:
                    print(f"    {session_name}: Парсинг истории чата с {current_bot}...")
                    msgs = []
                    async for msg in client.iter_messages(current_bot, limit=50):
                        if not msg.action:
                            msgs.append(msg)

                    if msgs:
                        # Пересылаем историю (от старых к новым)
                        await client.forward_messages(target_entity, msgs[::-1])
                    print(f"    {session_name}: История переслана в {val}")

                client.add_event_handler(message_handler, events.NewMessage(incoming=True))
                print(f"    {session_name}: Включена пересылка новых сообщений в {val}")

            elif cmd == "msg":
                if current_bot:
                    await client.send_message(current_bot, val)
                    print(f"    {session_name}: Отправлено сообщение: {val}")
            elif cmd == "parse_buttons":
                if current_bot:
                    print(f"    {session_name}: Парсинг кнопок в {current_bot}...")
                    async for msg in client.iter_messages(current_bot, limit=5):
                        if msg.reply_markup:
                            print(f"      Сообщение #{msg.id}:")
                            rows = getattr(msg.reply_markup, 'rows', [])
                            for r_idx, row in enumerate(rows):
                                for b_idx, button in enumerate(row.buttons):
                                    btn_text = getattr(button, 'text', 'Без текста')
                                    btn_type = "Inline" if hasattr(button, 'data') else "Reply"
                                    btn_info = f" -> click:{btn_type.lower()}:{btn_text}"
                                    if hasattr(button, 'data'):
                                        btn_data = button.data.decode() if isinstance(button.data, bytes) else str(
                                            button.data)
                                        btn_info += f" ИЛИ click:id:{btn_data}"
                                    print(f"        [{btn_type}] '{btn_text}'{btn_info}")
            elif cmd == "wait":
                await asyncio.sleep(float(val))
            elif cmd == "click":
                # Поддержка click:inline:текст, click:reply:текст и click:id:ID_КНОПКИ
                click_type = "any"
                btn_search = val
                if ":" in val:
                    parts = val.split(":", 1)
                    if parts[0] in ["inline", "reply", "id"]:
                        click_type = parts[0]
                        btn_search = parts[1]

                async for msg in client.iter_messages(current_bot, limit=3):
                    found = False
                    # Проверка Inline кнопок
                    if (click_type == "any" or click_type == "inline" or click_type == "id") and msg.reply_markup:
                        try:
                            rows = getattr(msg.reply_markup, 'rows', [])
                            for row in rows:
                                for button in row.buttons:
                                    # Если поиск по ID (data)
                                    if click_type == "id" and hasattr(button, 'data'):
                                        btn_data = button.data.decode() if isinstance(button.data, bytes) else str(
                                            button.data)
                                        if btn_search == btn_data:
                                            await msg.click(button)
                                            print(f"    {session_name}: Нажата кнопка по ID '{btn_data}'")
                                            found = True
                                            break
                                    # Если поиск по тексту
                                    elif hasattr(button, 'text') and btn_search.lower() in button.text.lower():
                                        await msg.click(button)
                                        print(f"    {session_name}: Нажата Inline кнопка '{button.text}'")
                                        found = True
                                        break
                                if found: break
                        except Exception:
                            pass

                    # Проверка Reply кнопок
                    if not found and (click_type == "any" or click_type == "reply"):
                        if msg.reply_markup:
                            rows = getattr(msg.reply_markup, 'rows', [])
                            for row in rows:
                                for button in row.buttons:
                                    if hasattr(button, 'text') and btn_search.lower() in button.text.lower():
                                        await client.send_message(current_bot, button.text)
                                        print(f"    {session_name}: Нажата Reply кнопка '{button.text}'")
                                        found = True
                                        break
                                if found: break
                    if found: break
            await human_delay(1, 2)
        except Exception as e:
            print(f"    {C.R}❌ {session_name}: Ошибка на шаге {cmd}:{val} — {e}{C.RST}")

    # Если была включена пересылка, подождем немного для получения ответов
    if repost_target:
        await asyncio.sleep(5)  # Уменьшили ожидание, так как история уже ушла
        client.remove_event_handler(message_handler)


async def action_set_2fa():
    sessions = select_sessions("Выбери аккаунт")
    if not sessions:
        return

    proxies = load_proxies()

    for i, session_name in enumerate(sessions):
        proxy = proxies[i % len(proxies)] if proxies else None
        client = await create_client(session_name, proxy)
        if not await safe_connect(client, session_name):
            continue

        try:
            # Проверяем текущий статус 2FA
            pwd = await client(GetPasswordRequest())
            has_2fa = pwd.has_password

            if has_2fa:
                print(f"  {C.Y}🔐 {session_name}: 2FA уже установлен{C.RST}")
                print(f"  1. Сменить пароль  2. Удалить 2FA  3. Пропустить")
                ch = ask_int("Выбор: ", 3)

                if ch == 1:
                    old_pwd = ask("Текущий пароль: ")
                    new_pwd = ask("Новый пароль: ")
                    hint = ask("Подсказка: ", "")
                    try:
                        await client.edit_2fa(
                            current_password=old_pwd,
                            new_password=new_pwd,
                            hint=hint
                        )
                        print(f"  {C.G}✅ Пароль изменён{C.RST}")
                    except Exception as e:
                        print(f"  {C.R}❌ {e}{C.RST}")
                elif ch == 2:
                    old_pwd = ask("Текущий пароль: ")
                    try:
                        await client.edit_2fa(
                            current_password=old_pwd,
                            new_password=None
                        )
                        print(f"  {C.G}✅ 2FA удалён{C.RST}")
                    except Exception as e:
                        print(f"  {C.R}❌ {e}{C.RST}")
            else:
                print(f"  {C.Y}🔓 {session_name}: 2FA не установлен{C.RST}")
                new_pwd = ask("Установить пароль (пусто = пропустить): ")
                if new_pwd:
                    hint = ask("Подсказка: ", "")
                    email = ask("Email для восстановления (пусто = без): ")
                    try:
                        await client.edit_2fa(
                            new_password=new_pwd,
                            hint=hint,
                            email=email if email else None
                        )
                        print(f"  {C.G}✅ 2FA установлен{C.RST}")
                    except Exception as e:
                        print(f"  {C.R}❌ {e}{C.RST}")

        finally:
            await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 47. ОТПИСКА ОТ КАНАЛОВ
# ─────────────────────────────────────────────────────────────

async def task_unsubscribe_all(client, session_name, **kw):
    leave_groups = kw.get("leave_groups", False)
    whitelist = kw.get("whitelist", [])

    count = 0
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, Channel):
            # Пропускаем whitelist
            if entity.username and entity.username.lower() in [w.lower().lstrip("@") for w in whitelist]:
                continue
            if str(entity.id) in whitelist:
                continue

            if entity.broadcast:  # Канал
                try:
                    await client(LeaveChannelRequest(entity))
                    count += 1
                    await human_delay(0.5, 1.5)
                except Exception:
                    pass
            elif entity.megagroup and leave_groups:  # Группа
                try:
                    await client(LeaveChannelRequest(entity))
                    count += 1
                    await human_delay(0.5, 1.5)
                except Exception:
                    pass

    print(f"  {C.DIM}  ↳ {session_name}: отписано от {count}{C.RST}")


async def action_unsubscribe():
    print(f"\n{C.Y}  Режим:{C.RST}")
    print(f"  1. Только каналы")
    print(f"  2. Каналы + группы")
    mode = ask_int("Выбор: ", 1)

    print(f"{C.Y}  Whitelist (не отписываться):{C.RST}")
    print(f"  Введи @username каналов, пустая = конец")
    whitelist = []
    while True:
        w = ask("@")
        if not w:
            break
        whitelist.append(w)

    sessions = select_sessions()
    if not sessions:
        return

    confirm = ask(f"⚠️ Отписаться от {'каналов+групп' if mode == 2 else 'каналов'}? (yes/no): ")
    if confirm.lower() != "yes":
        return

    await execute_on_sessions(
        sessions, task_unsubscribe_all,
        task_name="🚪 Отписка от каналов",
        leave_groups=(mode == 2),
        whitelist=whitelist
    )


# ─────────────────────────────────────────────────────────────
# 48. УДАЛИТЬ АККАУНТ
# ─────────────────────────────────────────────────────────────

async def task_delete_account(client, session_name, **kw):
    reason = kw.get("reason", "I want to delete my account")
    await client(DeleteAccountRequest(reason=reason))


async def action_delete_account():
    print(f"\n{C.R}{'═' * 50}")
    print(f"  ☠️  ВНИМАНИЕ! УДАЛЕНИЕ АККАУНТА НЕОБРАТИМО!")
    print(f"{'═' * 50}{C.RST}")

    confirm1 = ask("Ты уверен? (yes/no): ")
    if confirm1.lower() != "yes":
        return
    confirm2 = ask("Точно уверен? Напиши DELETE: ")
    if confirm2 != "DELETE":
        return

    reason = ask("Причина удаления: ", "I want to delete my account")
    sessions = select_sessions()
    if not sessions:
        return

    await execute_on_sessions(
        sessions, task_delete_account,
        task_name="☠️ УДАЛЕНИЕ АККАУНТОВ",
        reason=reason
    )


# ─────────────────────────────────────────────────────────────
# NEW FUNCTIONS: Automation & Channel Management
# ─────────────────────────────────────────────────────────────

async def task_monitor_future_posts(client, session_name, **kw):
    """Мониторинг будущих постов: авто-просмотры и авто-реакции"""
    target = kw["target"]
    do_view = kw.get("do_view", True)
    reaction = kw.get("reaction")

    try:
        entity = await resolve_channel(client, target)
        print(f"  {C.G}👀 {session_name}: мониторинг {target} запущен...{C.RST}")

        @client.on(events.NewMessage(chats=entity))
        async def handler(event):
            msg = event.message
            if do_view:
                await client(GetMessagesViewsRequest(peer=entity, id=[msg.id], increment=True))

            if reaction:
                try:
                    await client(SendReactionRequest(
                        peer=entity, msg_id=msg.id,
                        reaction=[ReactionEmoji(emoticon=reaction)]
                    ))
                except:
                    pass

        await client.run_until_disconnected()
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: ошибка мониторинга — {e}{C.RST}")


async def action_monitor_future():
    target = ask("Канал для мониторинга (@username или ссылка): ")
    if not target: return
    do_view = ask("Включить авто-просмотры? (y/n): ", "y").lower() == "y"
    reaction = ask("Эмодзи для авто-реакции (пусто = без реакций): ")

    sessions = select_sessions("Выбери аккаунты для мониторинга")
    if not sessions: return

    print(f"\n{C.Y}🚀 Мониторинг запущен на {len(sessions)} аккаунтах. Нажми Ctrl+C для выхода.{C.RST}")
    await execute_on_sessions(
        sessions, task_monitor_future_posts,
        task_name="👀 Авто-просмотры и реакции",
        target=target, do_view=do_view, reaction=reaction if reaction else None
    )


async def action_mass_create_channels():
    print(f"\n{C.CY}➕ Создание нескольких каналов/групп (до 50){C.RST}")
    type_ch = ask_int("1. Канал  2. Группа: ", 1)
    base_title = ask("Базовое название: ")
    count = min(ask_int("Количество (макс 50): ", 1), 50)
    delay = ask_int("Задержка между созданиями (сек): ", 5)

    # Настройки админки
    add_others = ask("Добавить другие выбранные аккаунты в созданные каналы? (y/n): ", "n").lower() == "y"
    other_sessions = []
    if add_others:
        other_sessions = select_sessions("Выбери аккаунты, которых нужно добавить в админы")

    sessions = select_sessions("Выбери основной аккаунт (создатель)")
    if not sessions: return
    main_session = sessions[0]

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(main_session, proxy)
    if not await safe_connect(client, main_session): return

    try:
        for i in range(1, count + 1):
            title = f"{base_title} #{i}" if count > 1 else base_title
            print(f"\n{C.CY}🏗 Создание {i}/{count}: {title}...{C.RST}")

            res = await client(CreateChannelRequest(
                title=title, about="", megagroup=(type_ch == 2)
            ))
            new_channel = res.chats[0]
            print(f"  {C.G}✅ Создан! ID: {new_channel.id}{C.RST}")

            if add_others and other_sessions:
                print(f"  {C.CY}👥 Добавление админов...{C.RST}")
                for s_name in other_sessions:
                    if s_name == main_session: continue
                    try:
                        # Получаем юзера через его сессию (упрощенно - по ID из файла если возможно,
                        # но лучше просто по GetMe если клиент запущен. Здесь используем заглушку)
                        # Для простоты: просим юзера ввести ID/Username тех кого добавить если это не автоматизировано
                        pass
                    except:
                        pass

            if i < count:
                print(f"  {C.DIM}⏳ Ожидание {delay} сек...{C.RST}")
                await asyncio.sleep(delay)

    finally:
        await client.disconnect()


async def action_transfer_ownership():
    channel = ask("Канал (@username или ID): ")
    new_owner = ask("Username или ID нового владельца: ")
    password = ask("Пароль 2FA (если есть): ", "")

    sessions = select_sessions("Выбери аккаунт текущего владельца")
    if not sessions: return

    proxies = load_proxies()
    client = await create_client(sessions[0], proxies[0] if proxies else None)
    if not await safe_connect(client, sessions[0]): return

    try:
        entity = await resolve_channel(client, channel)
        user_entity = await client.get_entity(new_owner)

        # Сначала даем полные права админа
        await client(EditAdminRequest(
            channel=entity, user_id=user_entity,
            admin_rights=ChatAdminRights(
                add_admins=True, change_info=True, post_messages=True,
                edit_messages=True, delete_messages=True, ban_users=True,
                invite_users=True, pin_messages=True, manage_call=True
            ),
            rank="Owner"
        ))

        # Передача прав
        await client(EditCreatorRequest(channel=entity, user_id=user_entity, password=password))
        print(f"  {C.G}✅ Права владельца переданы {new_owner}{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ Ошибка передачи: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# NEW FUNCTIONS: Automation & Channel Management
# ─────────────────────────────────────────────────────────────

async def task_monitor_future_posts(client, session_name, **kw):
    """Мониторинг будущих постов: авто-просмотры и авто-реакции"""
    target = kw["target"]
    do_view = kw.get("do_view", True)
    reaction = kw.get("reaction")

    try:
        entity = await resolve_channel(client, target)
        print(f"  {C.G}👀 {session_name}: мониторинг {target} запущен...{C.RST}")

        @client.on(events.NewMessage(chats=entity))
        async def handler(event):
            msg = event.message
            if do_view:
                try:
                    await client(GetMessagesViewsRequest(peer=entity, id=[msg.id], increment=True))
                    print(f"  {C.DIM}  ↳ {session_name}: пост #{msg.id} просмотрен{C.RST}")
                except:
                    pass

            if reaction:
                try:
                    await client(SendReactionRequest(
                        peer=entity, msg_id=msg.id,
                        reaction=[ReactionEmoji(emoticon=reaction)]
                    ))
                    print(f"  {C.DIM}  ↳ {session_name}: реакция {reaction} поставлена на #{msg.id}{C.RST}")
                except:
                    pass

        await client.run_until_disconnected()
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: ошибка мониторинга — {e}{C.RST}")


async def action_monitor_future():
    target = ask("Канал для мониторинга (@username или ссылка): ")
    if not target: return
    do_view = ask("Включить авто-просмотры? (y/n): ", "y").lower() == "y"
    reaction = ask("Эмодзи для авто-реакции (пусто = без реакций): ")

    sessions = select_sessions("Выбери аккаунты для мониторинга")
    if not sessions: return

    print(f"\n{C.Y}🚀 Мониторинг запущен на {len(sessions)} аккаунтах. Нажми Ctrl+C для выхода.{C.RST}")
    await execute_on_sessions(
        sessions, task_monitor_future_posts,
        task_name="👀 Авто-просмотры и реакции",
        target=target, do_view=do_view, reaction=reaction if reaction else None
    )


async def action_mass_create_channels():
    print(f"\n{C.CY}➕ Создание нескольких каналов/групп (до 50){C.RST}")
    type_ch = ask_int("1. Канал  2. Группа: ", 1)
    base_title = ask("Базовое название: ")
    count = min(ask_int("Количество (макс 50): ", 1), 50)
    delay = ask_int("Задержка между созданиями (сек): ", 5)

    do_transfer = ask("Передать права на аккаунт после создания? (y/n): ", "n").lower() == "y"
    target_uid = None
    if do_transfer:
        target_uid = ask("ID или Username нового владельца: ")
        if not target_uid:
            print(f"{C.R}❌ Нужно указать получателя прав{C.RST}")
            do_transfer = False

    add_others = ask("Добавить другие аккаунты в админы? (y/n): ", "n").lower() == "y"
    other_entities = []
    if add_others:
        print(f"{C.Y}Введите Username или ID через запятую для добавления в админы:{C.RST}")
        others_input = ask("Аккаунты: ")
        if others_input:
            other_entities = [x.strip() for x in others_input.split(",")]

    sessions = select_sessions("Выбери основной аккаунт (создатель)")
    if not sessions: return
    main_session = sessions[0]

    proxies = load_proxies()
    proxy = proxies[0] if proxies else None
    client = await create_client(main_session, proxy)
    if not await safe_connect(client, main_session): return

    try:
        for i in range(1, count + 1):
            title = f"{base_title} #{i}" if count > 1 else base_title
            print(f"\n{C.CY}🏗 Создание {i}/{count}: {title}...{C.RST}")

            res = await client(CreateChannelRequest(
                title=title, about="Created by Multi-Tool", megagroup=(type_ch == 2)
            ))
            new_channel = res.chats[0]
            print(f"  {C.G}✅ Создан! ID: {new_channel.id}{C.RST}")

            if add_others and other_entities:
                print(f"  {C.CY}👥 Добавление админов...{C.RST}")
                for target_user in other_entities:
                    try:
                        await client(InviteToChannelRequest(channel=new_channel, users=[target_user]))
                        await client(EditAdminRequest(
                            channel=new_channel, user_id=target_user,
                            admin_rights=ChatAdminRights(
                                add_admins=True, change_info=True, post_messages=True,
                                edit_messages=True, delete_messages=True, ban_users=True,
                                invite_users=True, pin_messages=True, manage_call=True
                            ),
                            rank="Admin"
                        ))
                        print(f"    ✅ {target_user} добавлен и назначен админом")
                    except Exception as e:
                        print(f"    ❌ Ошибка для {target_user}: {e}")

            if do_transfer and target_uid:
                print(f"  {C.CY}👑 Передача прав владельца {target_uid}...{C.RST}")
                try:
                    # Сначала делаем админом с правом добавления админов
                    await client(EditAdminRequest(
                        channel=new_channel, user_id=target_uid,
                        admin_rights=ChatAdminRights(
                            add_admins=True, change_info=True, post_messages=True,
                            edit_messages=True, delete_messages=True, ban_users=True,
                            invite_users=True, pin_messages=True, manage_call=True
                        ),
                        rank="Owner"
                    ))
                    # Попытка смены владельца (требует 2FA в EditCreatorRequest)
                    # Для массового режима используем упрощенную передачу админки
                    print(f"    ✅ Права админа выданы {target_uid}")
                except Exception as te:
                    print(f"    ❌ Ошибка передачи: {te}")

            if i < count:
                print(f"  {C.DIM}⏳ Ожидание {delay} сек...{C.RST}")
                await asyncio.sleep(delay)

    finally:
        await client.disconnect()


async def action_transfer_ownership():
    channel = ask("Канал (@username или ID): ")
    new_owner = ask("Username или ID нового владельца: ")
    password = ask("Пароль 2FA (если есть): ", "")

    sessions = select_sessions("Выбери аккаунт текущего владельца")
    if not sessions: return

    proxies = load_proxies()
    client = await create_client(sessions[0], proxies[0] if proxies else None)
    if not await safe_connect(client, sessions[0]): return

    try:
        entity = await resolve_channel(client, channel)
        user_entity = await client.get_entity(new_owner)

        # Сначала даем полные права админа
        await client(EditAdminRequest(
            channel=entity, user_id=user_entity,
            admin_rights=ChatAdminRights(
                add_admins=True, change_info=True, post_messages=True,
                edit_messages=True, delete_messages=True, ban_users=True,
                invite_users=True, pin_messages=True, manage_call=True
            ),
            rank="Owner"
        ))

        # Передача прав
        await client(EditCreatorRequest(channel=entity, user_id=user_entity, password=password))
        print(f"  {C.G}✅ Права владельца переданы {new_owner}{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ Ошибка передачи: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# NEW FUNCTIONS: Username & Parsing
# ─────────────────────────────────────────────────────────────

async def action_update_username():
    sessions = select_sessions("Выбери аккаунты для смены username")
    if not sessions: return
    new_username = input(f"{C.CY}  Введите новый @username (без @): {C.RST}").strip().replace("@", "")
    await execute_on_sessions(sessions, update_account_username, "Смена username", new_username=new_username)


async def action_parse_messages():
    sessions = select_sessions("Выбери аккаунты для парсинга")
    if not sessions: return
    await execute_on_sessions(sessions, parse_private_messages, "Парсинг сообщений")


# ─────────────────────────────────────────────────────────────
# 49. СПИСОК СЕССИЙ
# ─────────────────────────────────────────────────────────────

async def action_list_sessions():
    sessions = list_sessions()
    if not sessions:
        return
    print(f"\n  Всего: {len(sessions)} сессий")
    print(f"  Папка: {SESSIONS_DIR}")


# ─────────────────────────────────────────────────────────────
# 50. СПИСОК ПРОКСИ
# ─────────────────────────────────────────────────────────────

async def action_list_proxies():
    proxies = load_proxies()
    if not proxies:
        print(f"\n{C.Y}  Прокси не найдены{C.RST}")
        print(f"  Создай файл {C.W}proxies.txt{C.RST} с прокси по одному на строку:")
        print(f"  {C.DIM}socks5://user:pass@ip:port")
        print(f"  socks5://ip:port")
        print(f"  http://ip:port{C.RST}")
        return

    print(f"\n{C.CY}{'─' * 50}")
    print(f"  🌐 Прокси: {len(proxies)}")
    print(f"{'─' * 50}{C.RST}")
    for i, p in enumerate(proxies, 1):
        print(f"  {C.W}{i:3}. {C.G}{proxy_str(p)}{C.RST}")
    print(f"{C.CY}{'─' * 50}{C.RST}")

    # Тест прокси
    test = ask("Протестировать? (y/n): ", "n")
    if test == "y":
        print(f"\n{C.CY}  Тестирование...{C.RST}")
        api_id, api_hash = get_api_credentials()

        for i, p in enumerate(proxies):
            try:
                import socks
                import socket

                ptype_map = {
                    "socks5": socks.SOCKS5,
                    "socks4": socks.SOCKS4,
                    "http": socks.HTTP,
                    "https": socks.HTTP,
                }

                s = socks.socksocket()
                s.set_proxy(
                    ptype_map.get(p["proxy_type"], socks.SOCKS5),
                    p["addr"], p["port"],
                    username=p.get("username"),
                    password=p.get("password")
                )
                s.settimeout(10)

                start_t = time.time()
                s.connect(("149.154.167.50", 443))  # Telegram DC
                latency = int((time.time() - start_t) * 1000)
                s.close()

                print(f"  {C.G}✅ {proxy_str(p)} — {latency}ms{C.RST}")
            except Exception as e:
                print(f"  {C.R}❌ {proxy_str(p)} — {e}{C.RST}")


# ═══════════════════════════════════════════════════════════════
# ГЛАВНЫЙ ЦИКЛ
# ═══════════════════════════════════════════════════════════════

ACTION_MAP = {
    1: action_view_post,
    2: action_send_reaction,
    3: action_subscribe,
    4: action_all_in_one,
    5: action_comment,
    6: action_forward,
    7: action_vote,
    8: action_click_button,
    9: action_mass_reaction,
    10: action_start_bot,
    11: action_bot_scenario,
    12: action_webapp,
    13: action_send_dm,
    14: action_invite,
    15: action_send_message,
    16: action_scheduled_send,
    17: action_edit_message,
    18: action_pin_unpin,
    19: action_delete_own,
    20: action_create_channel,
    21: action_setup_channel,
    22: action_promote_admin,
    23: action_ban_kick,
    24: action_clear_channel,
    25: action_copy_channel,
    26: action_report_channel,
    27: action_report_message,
    28: action_block_users,
    29: action_parse_members,
    30: action_channel_stats,
    31: action_download_media,
    32: action_monitor,
    33: action_auto_responder,
    34: action_auto_posting,
    35: action_tasks_from_json,
    36: action_warmup,
    37: action_online_imitation,
    38: action_checker,
    39: action_active_sessions,
    40: action_reset_all_sessions,
    41: action_selective_reset,
    42: action_get_auth_code,
    43: action_get_info,
    44: action_update_profile,
    45: action_set_photo,
    46: action_set_2fa,
    47: action_unsubscribe,
    48: action_delete_account,
    49: action_list_sessions,
    50: action_list_proxies,
}


async def action_update_username():
    sessions = select_sessions("Выбери аккаунты для смены username")
    if not sessions: return
    new_username = input(f"{C.CY}  Введите новый @username (без @): {C.RST}").strip().replace("@", "")
    await execute_on_sessions(sessions, update_account_username, "Смена username", new_username=new_username)


async def action_parse_messages():
    sessions = select_sessions("Выбери аккаунты для парсинга")
    if not sessions: return
    await execute_on_sessions(sessions, parse_private_messages, "Парсинг сообщений")


async def task_send_premium_reaction(client, session_name, **kw):
    channel = kw["channel"]
    post_id = kw["post_id"]
    custom_emoji_id = kw["emoji_id"]
    entity = await resolve_channel(client, channel)

    # Просмотр поста для реалистичности
    await client(GetMessagesViewsRequest(peer=entity, id=[post_id], increment=True))
    await human_delay(0.5, 1.5)

    try:
        # Премиум реакция через ReactionCustomEmoji
        await client(SendReactionRequest(
            peer=entity,
            msg_id=post_id,
            reaction=[ReactionCustomEmoji(document_id=int(custom_emoji_id))]
        ))
        print(f"  {C.G}✅ {session_name}: Премиум реакция поставлена{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: Ошибка — {e}{C.RST}")


async def action_premium_reaction():
    link = ask("Ссылка на пост: ")
    parsed = parse_tg_link(link)
    if not parsed["channel"] or not parsed["post_id"]:
        print(f"{C.R}❌ Неверная ссылка{C.RST}")
        return
    emoji_id = ask("ID кастомного эмодзи (число): ")
    if not emoji_id.isdigit():
        print(f"{C.R}❌ ID должен быть числом{C.RST}")
        return

    sessions = select_sessions("Выбери аккаунты (нужен Premium)")
    if not sessions: return
    await execute_on_sessions(
        sessions, task_send_premium_reaction,
        task_name="💎 Премиум реакция",
        channel=parsed["channel"],
        post_id=parsed["post_id"],
        emoji_id=emoji_id
    )


async def task_add_views_n_posts(client, session_name, **kw):
    """Просмотр последних N постов"""
    channel = kw["channel"]
    count = kw["count"]
    try:
        entity = await resolve_channel(client, channel)
        messages = await client.get_messages(entity, limit=count)
        msg_ids = [m.id for m in messages if not m.action]
        if msg_ids:
            await client(GetMessagesViewsRequest(peer=entity, id=msg_ids, increment=True))
            print(f"  {C.G}✅ {session_name}: Просмотрено {len(msg_ids)} постов{C.RST}")
        else:
            print(f"  {C.Y}⚠️ {session_name}: Посты не найдены{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: Ошибка — {e}{C.RST}")


async def action_add_views_n_posts():
    target = ask("Username или ссылка на канал: ")
    if not target: return
    n = ask_int("Сколько последних постов просмотреть? ", 5)
    sessions = select_sessions("Выбери аккаунты для накрутки")
    if not sessions: return
    await execute_on_sessions(sessions, task_add_views_n_posts, "Просмотр N постов", channel=target, count=n)


async def task_change_email(client, session_name, **kw):
    """Смена Email — корректная реализация через API Telegram"""
    new_email = kw["new_email"]
    try:
        print(f"  {C.Y}📧 {session_name}: Запрос на привязку {new_email}...{C.RST}")
        try:
            from telethon.tl.functions.account import SendVerifyEmailCodeRequest, VerifyEmailRequest
            result = await client(SendVerifyEmailCodeRequest(email=new_email))
            print(f"  {C.G}✅ {session_name}: Код отправлен на {new_email}{C.RST}")
            if hasattr(result, 'length'):
                print(f"  {C.DIM}  Ожидается код длиной {result.length} символов{C.RST}")
            code = input(f"{C.CY}  Введи код из письма для [{session_name}]: {C.RST}").strip()
            if not code:
                print(f"  {C.R}❌ {session_name}: Код не введён{C.RST}")
                return
            await client(VerifyEmailRequest(email=new_email, code=code))
            print(f"  {C.G}🎉 {session_name}: Email успешно привязан!{C.RST}")
        except ImportError:
            from telethon.tl.functions.account import GetPasswordRequest, UpdatePasswordSettingsRequest
            from telethon.tl.types import PasswordKdfAlgoUnknown, SecurePasswordKdfAlgoUnknown
            print(f"  {C.Y}⚠ {session_name}: Прямой API недоступен, пробуем через настройки 2FA...{C.RST}")
            try:
                pwd_info = await client(GetPasswordRequest())
                print(f"  {C.DIM}  2FA активен: {pwd_info.has_password} | Email: {getattr(pwd_info, 'email_unconfirmed_pattern', 'не задан')}{C.RST}")
                print(f"  {C.Y}  Смена email возможна только при активном 2FA. Установи 2FA (пункт 46), затем укажи email.{C.RST}")
            except Exception as e2:
                print(f"  {C.R}❌ {session_name}: {e2}{C.RST}")
        except Exception as e:
            err = str(e).lower()
            if "flood" in err:
                print(f"  {C.Y}⏳ {session_name}: FloodWait — подождите и повторите{C.RST}")
            elif "email" in err and "invalid" in err:
                print(f"  {C.R}❌ {session_name}: Неверный формат email{C.RST}")
            elif "code" in err and "invalid" in err:
                print(f"  {C.R}❌ {session_name}: Неверный код подтверждения{C.RST}")
            elif "code" in err and "expired" in err:
                print(f"  {C.R}❌ {session_name}: Код истёк — запроси снова{C.RST}")
            else:
                print(f"  {C.R}❌ {session_name}: {e}{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: {e}{C.RST}")


async def action_change_email():
    new_email = ask("Новый Email: ")
    if not new_email: return
    sessions = select_sessions("Выбери аккаунты для смены Email")
    if not sessions: return
    # Ограничиваем параллельность до 1, чтобы вводить коды по очереди
    await execute_on_sessions(sessions, task_change_email, "Смена Email", new_email=new_email, max_concurrent=1)


async def action_delete_session_files():
    sessions = select_sessions("Выбери сессии для ПОЛНОГО удаления файлов")
    if not sessions: return

    print(f"\n{C.R}{C.BOLD}⚠️ ВНИМАНИЕ!{C.RST}")
    print(f"{C.Y}Вы собираетесь удалить файлы сессий: {', '.join(sessions)}{C.RST}")
    print(f"{C.Y}Это действие необратимо. Сессии исчезнут из списка.{C.RST}")

    confirm = ask("Вы уверены? Введите 'yes' для удаления: ").lower()
    if confirm != 'yes':
        print(f"{C.G}Отменено.{C.RST}")
        return

    for session in sessions:
        try:
            # Удаляем .session и .json (если есть)
            s_file = SESSIONS_DIR / f"{session}.session"
            j_file = SESSIONS_DIR / f"{session}.json"

            if s_file.exists(): s_file.unlink()
            if j_file.exists(): j_file.unlink()

            print(f"  {C.G}✅ Сессия {session} полностью удалена{C.RST}")
        except Exception as e:
            print(f"  {C.R}❌ Ошибка удаления {session}: {e}{C.RST}")
    pause()


# ─────────────────────────────────────────────────────────────
# 62. НАКРУТКА ПРОСМОТРОВ ИСТОРИЙ
# ─────────────────────────────────────────────────────────────

async def task_story_view(client, session_name, **kw):
    peer = kw["peer"]
    story_ids = kw["story_ids"]
    try:
        from telethon.tl.functions.stories import IncrementStoryViewsRequest
        entity = await client.get_entity(peer)
        await client(IncrementStoryViewsRequest(peer=entity, id=story_ids))
        print(f"  {C.G}✅ {session_name}: просмотрено историй: {len(story_ids)}{C.RST}")
    except ImportError:
        print(f"  {C.R}❌ {session_name}: Stories API недоступен, обновите Telethon{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: {e}{C.RST}")


async def action_story_view():
    peer = ask("Username или @username пользователя/канала: ")
    if not peer:
        return
    ids_str = ask("ID историй через запятую (пусто = все последние): ", "")
    sessions = select_sessions("Выбери аккаунты для просмотра историй")
    if not sessions:
        return

    story_ids = []
    if ids_str:
        try:
            story_ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
        except ValueError:
            print(f"{C.R}❌ Неверный формат ID{C.RST}")
            return
    else:
        proxies = load_proxies()
        proxy = random.choice(proxies) if proxies else None
        tmp = await create_client(sessions[0], proxy)
        try:
            await tmp.connect()
            entity = await tmp.get_entity(peer)
            try:
                from telethon.tl.functions.stories import GetPeerStoriesRequest
                result = await tmp(GetPeerStoriesRequest(peer=entity))
                story_ids = [s.id for s in result.stories.stories]
                print(f"  {C.CY}Найдено историй: {len(story_ids)}{C.RST}")
            except Exception as e:
                print(f"  {C.R}❌ Не удалось получить истории: {e}{C.RST}")
                return
        finally:
            await tmp.disconnect()

    if not story_ids:
        print(f"{C.R}❌ Нет историй{C.RST}")
        return

    await execute_on_sessions(
        sessions, task_story_view,
        task_name="👁 Просмотр историй",
        peer=peer, story_ids=story_ids
    )


# ─────────────────────────────────────────────────────────────
# 63. РЕАКЦИЯ НА ИСТОРИЮ
# ─────────────────────────────────────────────────────────────

async def task_story_reaction(client, session_name, **kw):
    peer = kw["peer"]
    story_id = kw["story_id"]
    reaction = kw["reaction"]
    try:
        from telethon.tl.functions.stories import SendStoryReactionRequest
        entity = await client.get_entity(peer)
        react_obj = ReactionEmoji(emoticon=reaction)
        await client(SendStoryReactionRequest(
            peer=entity,
            story_id=story_id,
            reaction=react_obj
        ))
        print(f"  {C.G}✅ {session_name}: реакция {reaction} на историю #{story_id}{C.RST}")
    except ImportError:
        print(f"  {C.R}❌ {session_name}: Stories API недоступен, обновите Telethon{C.RST}")
    except Exception as e:
        print(f"  {C.R}❌ {session_name}: {e}{C.RST}")


async def action_story_reaction():
    peer = ask("Username пользователя/канала: ")
    if not peer:
        return
    story_id = ask_int("ID истории: ", 0)
    if not story_id:
        print(f"{C.R}❌ Укажи ID истории{C.RST}")
        return
    reaction = ask_reaction()
    sessions = select_sessions("Выбери аккаунты для реакций на истории")
    if not sessions:
        return
    await execute_on_sessions(
        sessions, task_story_reaction,
        task_name="❤️ Реакция на историю",
        peer=peer, story_id=story_id, reaction=reaction
    )


# ─────────────────────────────────────────────────────────────
# 64. ПОИСК ПОЛЬЗОВАТЕЛЯ (телефон / username)
# ─────────────────────────────────────────────────────────────

async def action_search_user():
    sessions = select_sessions("Выбери аккаунт для поиска (1 достаточно)")
    if not sessions:
        return

    print(f"\n{C.Y}  Тип поиска:{C.RST}")
    print(f"  1. По @username")
    print(f"  2. По номеру телефона")
    mode = ask_int("Выбор: ", 1)

    proxies = load_proxies()
    proxy = random.choice(proxies) if proxies else None
    client = await create_client(sessions[0], proxy)

    try:
        if not await safe_connect(client, sessions[0]):
            return

        if mode == 1:
            username = ask("Введи @username (без @): ").replace("@", "").strip()
            if not username:
                return
            try:
                entity = await client.get_entity(f"@{username}")
                user = await client(GetFullUserRequest(entity))
                u = user.users[0]
                print(f"\n{C.CY}{'─' * 45}")
                print(f"  👤 Имя:      {u.first_name or ''} {u.last_name or ''}")
                print(f"  🔗 Username: @{u.username or '—'}")
                print(f"  🆔 ID:       {u.id}")
                print(f"  📱 Телефон:  {getattr(u, 'phone', '—') or '—'}")
                print(f"  🤖 Бот:      {'да' if u.bot else 'нет'}")
                print(f"  ✅ Верифицирован: {'да' if u.verified else 'нет'}")
                print(f"  🚫 Удалён:   {'да' if u.deleted else 'нет'}")
                print(f"{C.CY}{'─' * 45}{C.RST}")
            except Exception as e:
                print(f"{C.R}❌ Пользователь не найден: {e}{C.RST}")

        elif mode == 2:
            phone = ask("Номер телефона (с кодом страны, например +79001234567): ").strip()
            if not phone:
                return
            try:
                from telethon.tl.functions.contacts import ResolvePhoneRequest
                result = await client(ResolvePhoneRequest(phone=phone))
                if result.users:
                    u = result.users[0]
                    print(f"\n{C.CY}{'─' * 45}")
                    print(f"  👤 Имя:      {u.first_name or ''} {u.last_name or ''}")
                    print(f"  🔗 Username: @{u.username or '—'}")
                    print(f"  🆔 ID:       {u.id}")
                    print(f"  📱 Телефон:  {phone}")
                    print(f"{C.CY}{'─' * 45}{C.RST}")
                else:
                    from telethon.tl.functions.contacts import ImportContactsRequest
                    from telethon.tl.types import InputPhoneContact
                    r = await client(ImportContactsRequest([
                        InputPhoneContact(client_id=0, phone=phone, first_name="Search", last_name="")
                    ]))
                    if r.users:
                        u = r.users[0]
                        print(f"\n{C.CY}{'─' * 45}")
                        print(f"  👤 Имя:      {u.first_name or ''} {u.last_name or ''}")
                        print(f"  🔗 Username: @{u.username or '—'}")
                        print(f"  🆔 ID:       {u.id}")
                        print(f"{C.CY}{'─' * 45}{C.RST}")
                        await client(
                            __import__('telethon.tl.functions.contacts', fromlist=['DeleteContactsRequest'])
                            .DeleteContactsRequest(id=[u])
                        )
                    else:
                        print(f"{C.Y}⚠ Пользователь не зарегистрирован или скрыл номер{C.RST}")
            except Exception as e:
                print(f"{C.R}❌ Ошибка поиска: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 65. ПАРСИНГ ОБЩИХ ГРУПП ДВУХ ПОЛЬЗОВАТЕЛЕЙ
# ─────────────────────────────────────────────────────────────

async def action_common_chats():
    sessions = select_sessions("Выбери аккаунт (1 достаточно)")
    if not sessions:
        return

    user1 = ask("Username первого пользователя (без @): ").replace("@", "").strip()
    user2 = ask("Username второго пользователя (без @): ").replace("@", "").strip()
    if not user1 or not user2:
        return

    proxies = load_proxies()
    proxy = random.choice(proxies) if proxies else None
    client = await create_client(sessions[0], proxy)

    try:
        if not await safe_connect(client, sessions[0]):
            return

        try:
            e1 = await client.get_entity(f"@{user1}")
            e2 = await client.get_entity(f"@{user2}")
            from telethon.tl.functions.messages import GetCommonChatsRequest
            result = await client(GetCommonChatsRequest(user_id=e1, max_id=0, limit=100))
            chats1 = {c.id: c for c in result.chats}
            result2 = await client(GetCommonChatsRequest(user_id=e2, max_id=0, limit=100))
            chats2 = {c.id: c for c in result2.chats}
            common_ids = set(chats1.keys()) & set(chats2.keys())

            print(f"\n{C.CY}{'─' * 50}")
            print(f"  🔍 Общие группы @{user1} и @{user2}: {len(common_ids)}")
            print(f"{'─' * 50}{C.RST}")
            if common_ids:
                for cid in common_ids:
                    c = chats1[cid]
                    title = getattr(c, 'title', '—')
                    username = getattr(c, 'username', None)
                    link = f"t.me/{username}" if username else f"ID: {cid}"
                    print(f"  • {title} — {link}")
                out_file = BASE_DIR / f"common_chats_{user1}_{user2}.txt"
                with open(out_file, "w", encoding="utf-8") as f:
                    for cid in common_ids:
                        c = chats1[cid]
                        title = getattr(c, 'title', '—')
                        username = getattr(c, 'username', '')
                        f.write(f"{title}\t{username or cid}\n")
                print(f"\n{C.G}💾 Сохранено в {out_file}{C.RST}")
            else:
                print(f"  {C.Y}Общих групп не найдено{C.RST}")
            print(f"{C.CY}{'─' * 50}{C.RST}")
        except Exception as e:
            print(f"{C.R}❌ Ошибка: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 66. ФИЛЬТРАЦИЯ ПОСТОВ КАНАЛА ПО КЛЮЧЕВЫМ СЛОВАМ
# ─────────────────────────────────────────────────────────────

async def action_filter_posts():
    sessions = select_sessions("Выбери аккаунт (1 достаточно)")
    if not sessions:
        return

    channel = ask("Username или ссылка на канал: ")
    if not channel:
        return
    keywords_raw = ask("Ключевые слова через запятую: ")
    if not keywords_raw:
        return
    keywords = [k.strip().lower() for k in keywords_raw.split(",") if k.strip()]
    limit = ask_int("Сколько последних постов проверить (0 = все): ", 500)
    if limit == 0:
        limit = None

    proxies = load_proxies()
    proxy = random.choice(proxies) if proxies else None
    client = await create_client(sessions[0], proxy)

    try:
        if not await safe_connect(client, sessions[0]):
            return
        entity = await resolve_channel(client, channel)
        print(f"\n{C.CY}  Загрузка постов...{C.RST}")
        found = []
        async for msg in client.iter_messages(entity, limit=limit):
            if not msg.text:
                continue
            text_lower = msg.text.lower()
            matched = [kw for kw in keywords if kw in text_lower]
            if matched:
                found.append({
                    "id": msg.id,
                    "date": msg.date.strftime("%Y-%m-%d %H:%M"),
                    "keywords": matched,
                    "text": msg.text[:200].replace("\n", " ")
                })

        print(f"\n{C.CY}{'─' * 55}")
        print(f"  🔍 Найдено постов с ключевыми словами: {len(found)}")
        print(f"{'─' * 55}{C.RST}")
        for item in found[:20]:
            kws = ", ".join(item["keywords"])
            print(f"  [{item['date']}] #{item['id']} [{kws}]: {item['text'][:80]}...")

        if len(found) > 20:
            print(f"  {C.DIM}... и ещё {len(found) - 20} постов{C.RST}")

        if found:
            ch_name = getattr(entity, 'username', None) or str(entity.id)
            out_file = BASE_DIR / f"filtered_{ch_name}_{keywords[0]}.txt"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(f"Канал: {ch_name} | Слова: {', '.join(keywords)}\n")
                f.write("=" * 60 + "\n")
                for item in found:
                    kws = ", ".join(item["keywords"])
                    f.write(f"[{item['date']}] ID={item['id']} [{kws}]\n{item['text']}\n\n")
            print(f"\n{C.G}💾 Выгружено в {out_file}{C.RST}")
    except Exception as e:
        print(f"{C.R}❌ Ошибка: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 67. КОПИРОВАНИЕ КОНТАКТОВ МЕЖДУ АККАУНТАМИ
# ─────────────────────────────────────────────────────────────

async def action_copy_contacts():
    print(f"\n{C.Y}  Шаг 1: Выбери ИСТОЧНИК (откуда копируем контакты){C.RST}")
    source_sessions = select_sessions("Источник контактов")
    if not source_sessions:
        return
    source = source_sessions[0]

    print(f"\n{C.Y}  Шаг 2: Выбери ПОЛУЧАТЕЛЕЙ (куда копируем контакты){C.RST}")
    target_sessions = select_sessions("Аккаунты-получатели")
    if not target_sessions:
        return

    proxies = load_proxies()
    proxy = random.choice(proxies) if proxies else None
    src_client = await create_client(source, proxy)

    contacts_to_import = []
    try:
        if not await safe_connect(src_client, source):
            return
        from telethon.tl.functions.contacts import GetContactsRequest
        from telethon.tl.types import InputPhoneContact
        result = await src_client(GetContactsRequest(hash=0))
        for u in result.users:
            if getattr(u, 'phone', None):
                contacts_to_import.append(InputPhoneContact(
                    client_id=random.randint(1000, 9999),
                    phone=u.phone,
                    first_name=u.first_name or "",
                    last_name=u.last_name or ""
                ))
        print(f"\n{C.G}  Получено контактов: {len(contacts_to_import)}{C.RST}")
    except Exception as e:
        print(f"{C.R}❌ Ошибка получения контактов: {e}{C.RST}")
        return
    finally:
        await src_client.disconnect()

    if not contacts_to_import:
        print(f"{C.Y}⚠ Контакты с номерами телефонов не найдены{C.RST}")
        return

    from telethon.tl.functions.contacts import ImportContactsRequest as ICR
    async def task_import_contacts(client, session_name, **kw):
        contacts = kw["contacts"]
        try:
            result = await client(ICR(contacts=contacts))
            print(f"  {C.G}✅ {session_name}: импортировано {len(result.imported)} контактов{C.RST}")
        except Exception as e:
            print(f"  {C.R}❌ {session_name}: {e}{C.RST}")

    await execute_on_sessions(
        target_sessions, task_import_contacts,
        task_name="📋 Копирование контактов",
        max_concurrent=2,
        contacts=contacts_to_import
    )


# ─────────────────────────────────────────────────────────────
# 68. АВТО-МОДЕРАЦИЯ (стоп-слова, удаление сообщений)
# ─────────────────────────────────────────────────────────────

async def action_auto_moderation():
    sessions = select_sessions("Выбери аккаунт-администратор")
    if not sessions:
        return

    channel = ask("Username или ссылка на группу/канал: ")
    if not channel:
        return
    stopwords_raw = ask("Стоп-слова через запятую: ")
    if not stopwords_raw:
        return
    stopwords = [w.strip().lower() for w in stopwords_raw.split(",") if w.strip()]
    duration = ask_int("Мониторить (минут): ", 60)

    proxies = load_proxies()
    proxy = random.choice(proxies) if proxies else None
    client = await create_client(sessions[0], proxy)

    if not await safe_connect(client, sessions[0]):
        return

    try:
        entity = await resolve_channel(client, channel)
        print(f"\n{C.G}🛡 Авто-модерация запущена | Стоп-слова: {', '.join(stopwords)}{C.RST}")
        print(f"  Канал: {getattr(entity, 'title', channel)} | Длительность: {duration} мин")
        print(f"  Ctrl+C для остановки\n")

        end_time = time.time() + duration * 60
        deleted_count = 0

        @client.on(events.NewMessage(chats=entity))
        async def handler(event):
            nonlocal deleted_count
            if not event.text:
                return
            text_lower = event.text.lower()
            for word in stopwords:
                if word in text_lower:
                    try:
                        await event.delete()
                        deleted_count += 1
                        sender = await event.get_sender()
                        name = getattr(sender, 'first_name', '?') or '?'
                        print(f"  {C.R}🗑 Удалено [{word}] от {name}: {event.text[:50]}{C.RST}")
                    except Exception as e:
                        print(f"  {C.Y}⚠ Не удалось удалить: {e}{C.RST}")
                    break

        await client.start()
        while time.time() < end_time:
            await asyncio.sleep(5)

        print(f"\n{C.CY}  Итого удалено сообщений: {deleted_count}{C.RST}")
    except KeyboardInterrupt:
        print(f"\n{C.Y}⏹ Остановлено{C.RST}")
    except Exception as e:
        print(f"{C.R}❌ Ошибка: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 69. ФОРВАРД ПОСТОВ С ФИЛЬТРОМ ПО КЛЮЧЕВЫМ СЛОВАМ
# ─────────────────────────────────────────────────────────────

async def action_forward_filtered():
    sessions = select_sessions("Выбери аккаунт для пересылки")
    if not sessions:
        return

    source = ask("Источник (username или ссылка на канал): ")
    dest = ask("Назначение (username или ссылка на канал/чат): ")
    if not source or not dest:
        return
    keywords_raw = ask("Ключевые слова через запятую (пусто = все): ", "")
    keywords = [k.strip().lower() for k in keywords_raw.split(",") if k.strip()] if keywords_raw else []
    limit = ask_int("Сколько последних постов проверить: ", 100)
    delay_s = ask_int("Задержка между пересылками (сек): ", 3)

    proxies = load_proxies()
    proxy = random.choice(proxies) if proxies else None
    client = await create_client(sessions[0], proxy)

    try:
        if not await safe_connect(client, sessions[0]):
            return
        src_entity = await resolve_channel(client, source)
        dst_entity = await resolve_channel(client, dest)

        print(f"\n{C.CY}  Загрузка и фильтрация постов...{C.RST}")
        to_forward = []
        async for msg in client.iter_messages(src_entity, limit=limit):
            if not msg.text and not msg.media:
                continue
            if keywords:
                text_lower = (msg.text or "").lower()
                if not any(kw in text_lower for kw in keywords):
                    continue
            to_forward.append(msg.id)

        print(f"  Подходящих постов: {len(to_forward)}")
        if not to_forward:
            print(f"{C.Y}⚠ Нет постов для пересылки{C.RST}")
            return

        confirm = ask(f"Переслать {len(to_forward)} постов? (y/n): ", "n")
        if confirm.lower() != "y":
            return

        forwarded = 0
        for chunk in [to_forward[i:i+10] for i in range(0, len(to_forward), 10)]:
            try:
                await client(ForwardMessagesRequest(
                    from_peer=src_entity,
                    id=list(reversed(chunk)),
                    to_peer=dst_entity,
                    drop_author=False,
                    silent=False
                ))
                forwarded += len(chunk)
                print(f"  {C.G}✅ Переслано: {forwarded}/{len(to_forward)}{C.RST}")
                await asyncio.sleep(delay_s)
            except FloodWaitError as e:
                print(f"  {C.Y}⏳ FloodWait {e.seconds}s...{C.RST}")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"  {C.R}❌ Ошибка пересылки чанка: {e}{C.RST}")

        print(f"\n{C.G}🎉 Пересылка завершена: {forwarded} постов{C.RST}")
    except Exception as e:
        print(f"{C.R}❌ Ошибка: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 70. КОПИРОВАНИЕ ИСТОРИИ КАНАЛА
# ─────────────────────────────────────────────────────────────

async def action_copy_channel_history():
    sessions = select_sessions("Выбери аккаунт")
    if not sessions:
        return

    source = ask("Источник (username или ссылка): ")
    dest = ask("Назначение (username или ссылка): ")
    if not source or not dest:
        return
    limit = ask_int("Сколько постов копировать (0 = все): ", 100)
    if limit == 0:
        limit = None
    delay_s = ask_int("Задержка между постами (сек): ", 2)
    drop_author = ask("Скрыть источник пересылки? (y/n): ", "n").lower() == "y"

    proxies = load_proxies()
    proxy = random.choice(proxies) if proxies else None
    client = await create_client(sessions[0], proxy)

    try:
        if not await safe_connect(client, sessions[0]):
            return
        src_entity = await resolve_channel(client, source)
        dst_entity = await resolve_channel(client, dest)

        print(f"\n{C.CY}  Подсчёт постов...{C.RST}")
        all_ids = []
        async for msg in client.iter_messages(src_entity, limit=limit):
            if not msg.action:
                all_ids.append(msg.id)

        all_ids = list(reversed(all_ids))
        print(f"  Постов для копирования: {len(all_ids)}")
        confirm = ask(f"Начать копирование? (y/n): ", "n")
        if confirm.lower() != "y":
            return

        copied = 0
        for chunk in [all_ids[i:i+10] for i in range(0, len(all_ids), 10)]:
            try:
                await client(ForwardMessagesRequest(
                    from_peer=src_entity,
                    id=chunk,
                    to_peer=dst_entity,
                    drop_author=drop_author,
                    silent=True
                ))
                copied += len(chunk)
                pct = int(copied / len(all_ids) * 100)
                print(f"  {C.G}✅ {copied}/{len(all_ids)} ({pct}%){C.RST}", end="\r")
                await asyncio.sleep(delay_s)
            except FloodWaitError as e:
                print(f"\n  {C.Y}⏳ FloodWait {e.seconds}s...{C.RST}")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"\n  {C.R}❌ Ошибка: {e}{C.RST}")

        print(f"\n{C.G}🎉 Скопировано постов: {copied}{C.RST}")
    except Exception as e:
        print(f"{C.R}❌ Ошибка: {e}{C.RST}")
    finally:
        await client.disconnect()


# ─────────────────────────────────────────────────────────────
# 71. РАСПИСАНИЕ ЗАДАЧ ПО ВРЕМЕНИ
# ─────────────────────────────────────────────────────────────

SCHEDULED_TASKS: List[dict] = []


async def action_task_scheduler():
    while True:
        print(f"\n{C.CY}{'─' * 50}")
        print(f"  ⏰ РАСПИСАНИЕ ЗАДАЧ")
        print(f"{'─' * 50}{C.RST}")
        print(f"  1. Добавить задачу в расписание")
        print(f"  2. Показать текущие задачи")
        print(f"  3. Запустить планировщик")
        print(f"  4. Очистить расписание")
        print(f"  0. Назад")
        ch = ask_int("Выбор: ", 0)

        if ch == 0:
            break
        elif ch == 1:
            print(f"\n{C.Y}  Доступные действия для планирования:{C.RST}")
            sched_actions = {
                1: ("Просмотр постов", "view"),
                2: ("Прогрев аккаунтов", "warmup"),
                3: ("Имитация онлайна", "online"),
                4: ("Авто-постинг", "posting"),
                5: ("Чекер аккаунтов", "checker"),
            }
            for k, (name, _) in sched_actions.items():
                print(f"  {k}. {name}")
            task_ch = ask_int("Выбери действие: ", 0)
            if task_ch not in sched_actions:
                continue
            task_name, task_key = sched_actions[task_ch]

            print(f"\n{C.Y}  Режим запуска:{C.RST}")
            print(f"  1. Один раз в заданное время (HH:MM)")
            print(f"  2. Повторять каждые N минут")
            sched_mode = ask_int("Режим: ", 1)

            if sched_mode == 1:
                run_at = ask("Время запуска (HH:MM, 24ч): ", "00:00")
                SCHEDULED_TASKS.append({
                    "name": task_name, "key": task_key,
                    "mode": "once", "run_at": run_at,
                    "done": False
                })
            elif sched_mode == 2:
                interval = ask_int("Интервал (минут): ", 60)
                SCHEDULED_TASKS.append({
                    "name": task_name, "key": task_key,
                    "mode": "interval", "interval_min": interval,
                    "next_run": time.time()
                })
            print(f"  {C.G}✅ Задача «{task_name}» добавлена в расписание{C.RST}")

        elif ch == 2:
            if not SCHEDULED_TASKS:
                print(f"  {C.Y}Расписание пусто{C.RST}")
            else:
                for i, t in enumerate(SCHEDULED_TASKS, 1):
                    mode_str = f"в {t.get('run_at', '?')}" if t["mode"] == "once" else f"каждые {t.get('interval_min', '?')} мин"
                    print(f"  {i}. {t['name']} — {mode_str}")

        elif ch == 3:
            if not SCHEDULED_TASKS:
                print(f"  {C.Y}Расписание пусто{C.RST}")
                continue
            duration = ask_int("Сколько минут работать планировщику (0 = бесконечно): ", 0)
            end_t = time.time() + duration * 60 if duration > 0 else float("inf")
            print(f"\n{C.G}⏰ Планировщик запущен. Ctrl+C для остановки.{C.RST}")

            sched_action_map = {
                "warmup": action_warmup,
                "checker": action_checker,
            }
            try:
                while time.time() < end_t:
                    now = datetime.now()
                    now_str = now.strftime("%H:%M")
                    for task in SCHEDULED_TASKS:
                        if task["mode"] == "once" and not task.get("done"):
                            if task.get("run_at") == now_str:
                                print(f"\n{C.CY}⏰ Запуск по расписанию: {task['name']}{C.RST}")
                                fn = sched_action_map.get(task["key"])
                                if fn:
                                    await fn()
                                task["done"] = True
                        elif task["mode"] == "interval":
                            if time.time() >= task.get("next_run", 0):
                                print(f"\n{C.CY}⏰ Интервальный запуск: {task['name']}{C.RST}")
                                fn = sched_action_map.get(task["key"])
                                if fn:
                                    await fn()
                                task["next_run"] = time.time() + task["interval_min"] * 60
                    await asyncio.sleep(30)
            except KeyboardInterrupt:
                print(f"\n{C.Y}⏹ Планировщик остановлен{C.RST}")

        elif ch == 4:
            SCHEDULED_TASKS.clear()
            print(f"  {C.G}✅ Расписание очищено{C.RST}")


# ─────────────────────────────────────────────────────────────
# 72. АВТО-ОБХОД СПАМ-БЛОКА
# ─────────────────────────────────────────────────────────────

async def action_antispam_bypass():
    sessions = select_sessions("Выбери аккаунты для обхода спам-блока")
    if not sessions:
        return

    print(f"\n{C.Y}  Режим обхода:{C.RST}")
    print(f"  1. Проверить наличие спам-блока")
    print(f"  2. Авто-прогрев (снятие ограничений через активность)")
    print(f"  3. Отчёт по всем аккаунтам")
    mode = ask_int("Выбор: ", 1)

    async def check_spambot_silent(client, session_name):
        try:
            spambot = await client.get_entity("@SpamBot")
            await client.send_message(spambot, "/start")
            await asyncio.sleep(3)
            msgs = await client.get_messages(spambot, limit=3)
            for m in msgs:
                if m.text:
                    text = m.text.lower()
                    if "no limits" in text or "нет ограничений" in text or "free" in text:
                        return "clean"
                    elif "limit" in text or "spam" in text or "restrict" in text or "ограни" in text:
                        return "blocked"
            return "unknown"
        except Exception:
            return "error",

    async def warmup_antiban(client, session_name):
        try:
            dialogs = await client.get_dialogs(limit=20)
            random.shuffle(dialogs)
            for dlg in dialogs[:8]:
                try:
                    await client.get_messages(dlg.entity, limit=5)
                    await asyncio.sleep(random.uniform(3, 8))
                except Exception:
                    pass
            await client(UpdateStatusRequest(offline=False))
            await asyncio.sleep(random.uniform(5, 15))
            await client(UpdateStatusRequest(offline=True))
        except Exception:
            pass

    proxies = load_proxies()
    results = []

    for i, session_name in enumerate(sessions):
        proxy = proxies[i % len(proxies)] if proxies else None
        client = await create_client(session_name, proxy)
        try:
            if not await safe_connect(client, session_name):
                results.append((session_name, "❌ нет подключения"))
                continue

            if mode == 1 or mode == 3:
                status = await check_spambot_silent(client, session_name)
                status_str = {
                    "clean": f"{C.G}✅ Чист{C.RST}",
                    "blocked": f"{C.R}🚫 Спам-блок{C.RST}",
                    "unknown": f"{C.Y}❓ Неизвестно{C.RST}",
                    "error": f"{C.R}⚠ Ошибка{C.RST}"
                }.get(status, "?")
                print(f"  {session_name}: {status_str}")
                results.append((session_name, status))

                if mode == 3 and status == "blocked":
                    print(f"  {C.Y}  → Запускаю прогрев для {session_name}...{C.RST}")
                    await warmup_antiban(client, session_name)

            elif mode == 2:
                print(f"  {C.CY}🔥 Прогрев {session_name}...{C.RST}")
                await warmup_antiban(client, session_name)
                await asyncio.sleep(random.uniform(5, 15))
                status = await check_spambot_silent(client, session_name)
                status_str = {
                    "clean": f"{C.G}✅ Чист после прогрева{C.RST}",
                    "blocked": f"{C.R}🚫 Ещё заблокирован{C.RST}",
                    "unknown": f"{C.Y}❓ Неизвестно{C.RST}",
                }.get(status, "?")
                print(f"  {session_name}: {status_str}")

        except Exception as e:
            print(f"  {C.R}❌ {session_name}: {e}{C.RST}")
        finally:
            await client.disconnect()
        await asyncio.sleep(random.uniform(2, 5))

    if mode == 3 and results:
        clean = sum(1 for _, s in results if s == "clean")
        blocked = sum(1 for _, s in results if s == "blocked")
        print(f"\n{C.CY}{'─' * 40}")
        print(f"  📊 Итого: {C.G}Чистых: {clean}{C.RST} | {C.R}Заблокированных: {blocked}{C.RST}")
        print(f"{C.CY}{'─' * 40}{C.RST}")


async def action_browse_account():
    """Браузер аккаунта: список диалогов и просмотр сообщений как в ТГ"""
    sessions = get_sessions()
    if not sessions:
        print(f"{C.R}❌ Нет сессий{C.RST}")
        return

    clear()
    banner()
    print(f"{C.CY}  📱 Выбери аккаунт для просмотра:{C.RST}\n")
    for i, s in enumerate(sessions, 1):
        print(f"  {C.W}{i:>3}{C.CY} │ {s}{C.RST}")
    print()
    try:
        idx = int(input(f"{C.CY}  ▶ Номер аккаунта: {C.RST}").strip())
        if idx < 1 or idx > len(sessions):
            print(f"{C.R}❌ Неверный номер{C.RST}")
            return
        session_name = sessions[idx - 1]
    except (ValueError, EOFError):
        return

    proxies = load_proxies()
    proxy = random.choice(proxies) if proxies else None
    client = await create_client(session_name, proxy)
    if not client:
        return
    ok = await safe_connect(client, session_name)
    if not ok:
        await client.disconnect()
        return

    try:
        me = await client.get_me()
        my_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
        my_username = f"@{me.username}" if me.username else ""
        print(f"\n{C.G}  ✅ Подключён: {my_name} {my_username}{C.RST}")

        # ── Главный цикл браузера ──
        while True:
            # Загружаем диалоги
            print(f"\n{C.CY}  ⏳ Загрузка диалогов...{C.RST}")
            dialogs = await client.get_dialogs(limit=50)

            clear()
            banner()
            print(f"{C.CY}  👤 Аккаунт: {C.W}{my_name} {my_username}{C.RST}")
            print(f"{C.CY}  {'─' * 56}{C.RST}")
            print(f"  {C.W}{'№':>3}  {'Тип':6}  {'Имя / Название':<30}  {'Непрочит.'}{C.RST}")
            print(f"{C.CY}  {'─' * 56}{C.RST}")

            for i, d in enumerate(dialogs, 1):
                ent = d.entity
                unread = d.unread_count or 0
                unread_str = f"{C.R}[{unread}]{C.RST}" if unread else ""

                if isinstance(ent, User):
                    kind = f"{C.B}ЛС  {C.RST}"
                    name = f"{ent.first_name or ''} {ent.last_name or ''}".strip()
                    if ent.username:
                        name += f" (@{ent.username})"
                elif isinstance(ent, Channel):
                    if ent.megagroup or ent.gigagroup:
                        kind = f"{C.M}Группа{C.RST}"
                    else:
                        kind = f"{C.Y}Канал {C.RST}"
                    name = ent.title or ""
                elif isinstance(ent, Chat):
                    kind = f"{C.M}Группа{C.RST}"
                    name = ent.title or ""
                else:
                    kind = f"{C.DIM}Иное  {C.RST}"
                    name = str(d.name or "")

                name = name[:35]
                print(f"  {C.W}{i:>3}{C.RST}  {kind}  {name:<35}  {unread_str}")

            print(f"{C.CY}  {'─' * 56}{C.RST}")
            print(f"  {C.DIM}Введи номер чата чтобы открыть, или 0 для выхода{C.RST}")
            try:
                ch_str = input(f"\n{C.CY}  ▶ Выбор: {C.RST}").strip()
                if not ch_str or ch_str == "0":
                    break
                ch_idx = int(ch_str)
                if ch_idx < 1 or ch_idx > len(dialogs):
                    print(f"{C.R}  ❌ Нет такого номера{C.RST}")
                    await asyncio.sleep(1)
                    continue
            except (ValueError, EOFError):
                break

            # ── Просмотр сообщений выбранного чата ──
            dialog = dialogs[ch_idx - 1]
            ent = dialog.entity
            chat_name = getattr(ent, "title", None) or f"{getattr(ent, 'first_name', '') or ''} {getattr(ent, 'last_name', '') or ''}".strip()

            offset_id = 0
            msg_limit = 20

            while True:
                clear()
                banner()
                print(f"{C.CY}  💬 Чат: {C.W}{chat_name}{C.RST}")
                print(f"{C.CY}  {'─' * 60}{C.RST}")

                msgs = await client.get_messages(ent, limit=msg_limit, offset_id=offset_id)

                if not msgs:
                    print(f"  {C.DIM}  Сообщений нет{C.RST}")
                else:
                    # Показываем от старых к новым
                    for m in reversed(msgs):
                        ts = m.date.strftime("%d.%m %H:%M") if m.date else ""
                        if m.out:
                            sender = f"{C.G}▶ Вы{C.RST}"
                        else:
                            try:
                                sender_ent = await client.get_entity(m.sender_id) if m.sender_id else None
                                if sender_ent:
                                    sname = f"{getattr(sender_ent, 'first_name', '') or ''} {getattr(sender_ent, 'last_name', '') or ''}".strip()
                                    if not sname:
                                        sname = getattr(sender_ent, 'title', '') or str(m.sender_id)
                                else:
                                    sname = "?"
                            except Exception:
                                sname = str(m.sender_id) if m.sender_id else "?"
                            sender = f"{C.CY}{sname}{C.RST}"

                        text = m.text or ""
                        if not text and m.media:
                            text = f"{C.DIM}[медиафайл]{C.RST}"
                        if not text:
                            text = f"{C.DIM}[пустое сообщение]{C.RST}"

                        # Перенос длинных строк
                        max_w = 55
                        lines = []
                        for line in text.splitlines():
                            while len(line) > max_w:
                                lines.append(line[:max_w])
                                line = line[max_w:]
                            lines.append(line)

                        print(f"\n  {C.DIM}{ts}{C.RST}  {sender}")
                        for ln in lines:
                            print(f"    {ln}")

                print(f"\n{C.CY}  {'─' * 60}{C.RST}")
                print(f"  {C.DIM}[Enter] — назад к диалогам  [s] — старее  [n] — новее{C.RST}")
                nav = input(f"{C.CY}  ▶ {C.RST}").strip().lower()

                if nav == "s":
                    # Старее: берём следующую страницу (более старые сообщения)
                    if msgs:
                        offset_id = msgs[-1].id
                elif nav == "n":
                    # Новее: сбрасываем offset чтобы вернуться к свежим
                    if offset_id != 0:
                        offset_id = max(0, offset_id - msg_limit * 2)
                        if offset_id < 0:
                            offset_id = 0
                else:
                    break

    finally:
        await client.disconnect()



# ═══════════════════════════════════════════════════════════════
# 75. GEMINI AI АССИСТЕНТ
# ═══════════════════════════════════════════════════════════════

async def action_gemini_assistant():
    """Управление аккаунтами через Gemini AI по описанию на русском языке"""
    import urllib.request as _urllib
    import json as _json_mod

    def _gemini_ask(api_key: str, prompt: str) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={api_key}"
        )
        body = _json_mod.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode()
        req = _urllib.Request(url, data=body,
                              headers={"Content-Type": "application/json"},
                              method="POST")
        with _urllib.urlopen(req, timeout=30) as r:
            data = _json_mod.loads(r.read())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    cfg = load_config()
    api_key = cfg.get("gemini_api_key", "")
    if not api_key:
        print(f"{C.Y}⚠ Gemini API ключ не настроен.{C.RST}")
        print(f"  Получи ключ на: https://aistudio.google.com/app/apikey")
        key_input = ask("Введи Gemini API ключ: ")
        if not key_input:
            return
        cfg["gemini_api_key"] = key_input
        save_config(cfg)
        api_key = key_input
        print(f"{C.G}✅ Ключ сохранён в config.json{C.RST}")

    menu_list = "\n".join(f"{k}: {v}" for k, v in {
        1: "Просмотр поста", 2: "Реакция", 3: "Подписка", 4: "Всё сразу",
        5: "Комментарий", 6: "Пересылка", 7: "Голосование", 8: "Inline кнопки",
        9: "Массовая реакция", 10: "Авто-старт бота", 13: "Рассылка в ЛС",
        14: "Инвайт", 29: "Парсер участников", 30: "Статистика канала",
        36: "Прогрев", 37: "Имитация онлайна", 38: "Чекер",
        43: "Инфо об аккаунте", 44: "Имя/Био", 47: "Отписка от каналов",
        49: "Изменить Username", 52: "Список сессий", 53: "Список прокси",
        59: "Проверка спам-блока", 64: "Поиск пользователя",
    }.items())

    sessions = get_sessions()
    sess_str = ", ".join(sessions[:10]) + ("..." if len(sessions) > 10 else "") if sessions else "нет"

    print(f"\n{C.CY}{'═'*50}")
    print(f"  🤖 GEMINI AI АССИСТЕНТ")
    print(f"{'═'*50}{C.RST}")
    print(f"  Опиши что нужно сделать с аккаунтами.")
    print(f"  Пример: 'Подпишись на @durov от всех аккаунтов'")
    print(f"  Пример: 'Поставь реакцию 👍 на https://t.me/ch/123'")
    print(f"  Введи 'выход' для выхода.\n")

    while True:
        user_input = ask("Твой запрос: ")
        if not user_input or user_input.lower() in ("выход", "exit", "quit", "q"):
            break

        print(f"\n{C.DIM}  🤔 Анализирую...{C.RST}")

        try:
            prompt = f"""Ты помощник для управления Telegram-аккаунтами через TG Multi-Tool.

Доступные команды (номер: описание):
{menu_list}

Доступные аккаунты: {sess_str}
Количество аккаунтов: {len(sessions)}

Запрос: "{user_input}"

Определи нужную команду. Ответь СТРОГО JSON:
{{
  "action_num": <число от 1 до 74 или 0>,
  "action_name": "<название>",
  "explanation": "<объяснение на русском>",
  "can_execute": true/false
}}"""

            raw = _gemini_ask(api_key, prompt)
            import json as _json, re as _re
            match = _re.search(r'\{[\s\S]*\}', raw)
            if not match:
                print(f"{C.Y}🤖 Gemini: {raw}{C.RST}")
                continue

            data = _json.loads(match.group())
            action_num = int(data.get("action_num", 0))
            explanation = data.get("explanation", "")
            can_execute = data.get("can_execute", False)
            action_name = data.get("action_name", "")

            print(f"\n{C.CY}🤖 Gemini: {explanation}{C.RST}")

            if not can_execute or action_num == 0:
                print(f"{C.Y}  Уточни запрос.{C.RST}")
                continue

            print(f"{C.G}  ▶ Команда [{action_num}]: {action_name}{C.RST}")
            confirm = ask("Выполнить? (y/n): ", "y")
            if confirm.lower() != "y":
                print(f"{C.Y}  Отменено.{C.RST}")
                continue

            # Выполняем действие
            extra = {
                49: action_update_username, 50: action_parse_messages,
                51: action_premium_reaction, 52: action_list_sessions,
                53: action_list_proxies, 54: action_monitor_future,
                55: action_mass_create_channels, 56: action_transfer_ownership,
                57: action_add_views_n_posts, 58: action_change_email,
                59: action_check_spambot, 60: action_scenario_constructor,
                61: action_delete_session_files, 62: action_story_view,
                63: action_story_reaction, 64: action_search_user,
                65: action_common_chats, 66: action_filter_posts,
                67: action_copy_contacts, 68: action_auto_moderation,
                69: action_forward_filtered, 70: action_copy_channel_history,
                71: action_task_scheduler, 72: action_antispam_bypass,
                73: action_browse_account, 74: action_subscribe_and_check,
            }
            fn = extra.get(action_num) or ACTION_MAP.get(action_num)
            if fn:
                result = fn()
                if asyncio.iscoroutine(result):
                    await result
            else:
                print(f"{C.R}❌ Команда {action_num} не найдена{C.RST}")

        except Exception as e:
            print(f"{C.R}❌ Ошибка Gemini: {e}{C.RST}")


def main():
    # Проверяем API credentials при первом запуске
    get_api_credentials()

    # Создаем цикл вручную для управления async
    loop = asyncio.get_event_loop()

    while True:
        print_menu()
        try:
            choice_str = input(f"\n{C.CY}  ▶ Выбери пункт: {C.RST}").strip()
            if not choice_str:
                continue
            choice = int(choice_str)
        except (ValueError, EOFError):
            continue
        except KeyboardInterrupt:
            print(f"\n{C.Y}👋 Выход{C.RST}")
            break

        if choice == 0:
            print(f"\n{C.Y}👋 До встречи!{C.RST}")
            break

        # Обработка функций
        if choice == 49:
            loop.run_until_complete(action_update_username())
        elif choice == 50:
            loop.run_until_complete(action_parse_messages())
        elif choice == 51:
            loop.run_until_complete(action_premium_reaction())
        elif choice == 52:
            loop.run_until_complete(action_list_sessions())
        elif choice == 53:
            loop.run_until_complete(action_list_proxies())
        elif choice == 54:
            loop.run_until_complete(action_monitor_future())
        elif choice == 55:
            loop.run_until_complete(action_mass_create_channels())
        elif choice == 56:
            loop.run_until_complete(action_transfer_ownership())
        elif choice == 57:
            loop.run_until_complete(action_add_views_n_posts())
        elif choice == 58:
            loop.run_until_complete(action_change_email())
        elif choice == 59:
            loop.run_until_complete(action_check_spambot())
        elif choice == 60:
            loop.run_until_complete(action_scenario_constructor())
        elif choice == 61:
            loop.run_until_complete(action_delete_session_files())
        elif choice == 62:
            loop.run_until_complete(action_story_view())
        elif choice == 63:
            loop.run_until_complete(action_story_reaction())
        elif choice == 64:
            loop.run_until_complete(action_search_user())
        elif choice == 65:
            loop.run_until_complete(action_common_chats())
        elif choice == 66:
            loop.run_until_complete(action_filter_posts())
        elif choice == 67:
            loop.run_until_complete(action_copy_contacts())
        elif choice == 68:
            loop.run_until_complete(action_auto_moderation())
        elif choice == 69:
            loop.run_until_complete(action_forward_filtered())
        elif choice == 70:
            loop.run_until_complete(action_copy_channel_history())
        elif choice == 71:
            loop.run_until_complete(action_task_scheduler())
        elif choice == 72:
            loop.run_until_complete(action_antispam_bypass())
        elif choice == 73:
            loop.run_until_complete(action_browse_account())
        elif choice == 74:
            loop.run_until_complete(action_subscribe_and_check())
        elif choice == 75:
            loop.run_until_complete(action_gemini_assistant())
        else:
            action = ACTION_MAP.get(choice)
            if not action:
                print(f"{C.R}❌ Неверный пункт{C.RST}")
                pause()
                continue

            try:
                result = action()
                if asyncio.iscoroutine(result):
                    loop.run_until_complete(result)
            except KeyboardInterrupt:
                print(f"\n{C.Y}⏹ Прервано{C.RST}")
            except Exception as e:
                print(f"\n{C.R}❌ Ошибка: {e}{C.RST}")

        pause()


# ═══════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        # Для Windows
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        main()
    except KeyboardInterrupt:
        print(f"\n{C.Y}👋 Выход{C.RST}")
    except Exception as e:
        print(f"\n{C.R}Критическая ошибка: {e}{C.RST}")
        import traceback

        traceback.print_exc()

# ═══════════════════════════════════════════════════════════════
# КОНЕЦ ФАЙЛА tg_tool.py
# ═══════════════════════════════════════════════════════════════

