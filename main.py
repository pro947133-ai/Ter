#!/usr/bin/env python3
import os
import time
import json
import re
import shutil
import tempfile
import threading
from datetime import datetime, timedelta
import requests
import telebot
from telebot.apihelper import ApiTelegramException
from telebot import types
from http.client import RemoteDisconnected
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8408985599:AAHqEZiGxuQbLrGxR6TQNVMxyZN5Oprqibw")
USERSBOX_API_TOKEN = os.getenv("USERSBOX_API_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkX2F0IjoxNzIzNzUwOTk0LCJhcHBfaWQiOjE3MjM3MjgzMzR9.MAY7QBwMbhSMeC0OFEHHsJbYERgd8sY7FG-7zGiIyHE")
API_BASE_URL = "https://api.usersbox.ru/v1"
LIMITS_FILE = "user_limits.json"
BACKUP_LIMITS_FILE = "user_limits.json.bak"
CONFIG_FILE = "bot_config.json"
LOG_FILE = "bot_log.txt"
ADMIN_ID = int(os.getenv("ADMIN_ID", "8139531624"))
bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"Authorization": f"Bearer {USERSBOX_API_TOKEN}"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=3)
SESSION.mount('http://', adapter)
SESSION.mount('https://', adapter)
user_limits = {}
limits_lock = threading.RLock()
config_lock = threading.RLock()
shutdown_event = threading.Event()
FIO_DATE_PATTERN = re.compile(r'^\s*([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$', re.IGNORECASE | re.UNICODE)
VK_PATTERN = re.compile(r'^(?:https?://)?(?:www\.)?vk\.com/(?:id)?(\d+|[a-zA-Z0-9_.-]+)$', re.IGNORECASE)
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', re.IGNORECASE)
cfg = {}

def log_message(text):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {text}\n")
        print(f"[{ts}] {text}")
    except:
        pass

def _serialize_limits_for_disk(data):
    out = {}
    for uid, ud in data.items():
        item = {
            "limit": int(ud.get("limit", 3)),
            "unlimited": bool(ud.get("unlimited", False))
        }
        reqs = []
        for r in ud.get("requests", []):
            if isinstance(r, datetime):
                reqs.append(r.isoformat())
            else:
                try:
                    parsed = datetime.fromisoformat(str(r))
                    reqs.append(parsed.isoformat())
                except:
                    try:
                        parsed_ts = float(r)
                        reqs.append(datetime.fromtimestamp(parsed_ts).isoformat())
                    except:
                        reqs.append(str(r))
        item["requests"] = reqs
        out[str(uid)] = item
    return out

def save_limits_to_file():
    with limits_lock:
        try:
            data = _serialize_limits_for_disk(user_limits)
            dir_name = os.path.dirname(os.path.abspath(LIMITS_FILE)) or "."
            fd, tmp_path = tempfile.mkstemp(prefix="tmp_limits_", dir=dir_name, text=True)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tf:
                    json.dump(data, tf, ensure_ascii=False, indent=2)
                    tf.flush()
                    os.fsync(tf.fileno())
                if os.path.exists(LIMITS_FILE):
                    try:
                        shutil.copy2(LIMITS_FILE, BACKUP_LIMITS_FILE)
                    except:
                        pass
                os.replace(tmp_path, LIMITS_FILE)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
            log_message("Limits saved successfully.")
        except Exception as e:
            log_message(f"Error saving limits: {e}")

def load_limits_from_file():
    global user_limits
    with limits_lock:
        try:
            if os.path.exists(LIMITS_FILE):
                with open(LIMITS_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                out = {}
                for uid, ud in raw.items():
                    limit = int(ud.get("limit", 3))
                    unlimited = bool(ud.get("unlimited", False))
                    reqs = []
                    for r in ud.get("requests", []):
                        try:
                            reqs.append(datetime.fromisoformat(r))
                        except:
                            try:
                                reqs.append(datetime.fromtimestamp(float(r)))
                            except:
                                pass
                    out[str(uid)] = {
                        "requests": reqs,
                        "limit": limit,
                        "unlimited": unlimited
                    }
                user_limits = out
                log_message(f"Limits loaded successfully. Total users: {len(user_limits)}")
            else:
                user_limits = {}
                save_limits_to_file()
                log_message("Limits file not found, created a new one.")
        except Exception as e:
            log_message(f"Error loading limits: {e}")
            user_limits = {}

def load_config():
    with config_lock:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    log_message("Config loaded successfully.")
                    return config
            except Exception as e:
                log_message(f"Error loading config. Using default config: {e}")
                return {}
        cfg_local = {"required_channel": None}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg_local, f, ensure_ascii=False, indent=2)
            log_message("Default config file created.")
        except:
            pass
        return cfg_local

def save_config(local_cfg):
    with config_lock:
        try:
            fd, tmp_path = tempfile.mkstemp(prefix="tmp_cfg_", dir=".", text=True)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tf:
                    json.dump(local_cfg, tf, ensure_ascii=False, indent=2)
                    tf.flush()
                    os.fsync(tf.fileno())
                os.replace(tmp_path, CONFIG_FILE)
                log_message("Config saved successfully.")
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
        except Exception as e:
            log_message(f"Error saving config: {e}")

def ensure_user_record(user_id):
    uid = str(user_id)
    if uid not in user_limits:
        user_limits[uid] = {"requests": [], "limit": 3, "unlimited": False}

def cleanup_old_requests_internal():
    now = datetime.now()
    three_hours_ago = now - timedelta(hours=3)
    changed = False
    for uid, ud in list(user_limits.items()):
        if not ud.get("unlimited", False):
            old_count = len(ud.get("requests", []))
            new_reqs = [r for r in ud.get("requests", []) if isinstance(r, datetime) and r > three_hours_ago]
            if len(new_reqs) != old_count:
                user_limits[uid]["requests"] = new_reqs
                changed = True
    return changed

def cleanup_old_requests():
    with limits_lock:
        changed = cleanup_old_requests_internal()
    if changed:
        save_limits_to_file()

def can_user_make_request(user_id):
    with limits_lock:
        changed = cleanup_old_requests_internal()
        if changed:
            try:
                save_limits_to_file()
            except:
                pass
        ensure_user_record(user_id)
        ud = user_limits[str(user_id)]
        if ud.get("unlimited", False):
            return True, "✅ Безлимитный доступ"
        used = len(ud.get("requests", []))
        limit = int(ud.get("limit", 3))
        if used < limit:
            return True, f"📊 Запросов: {used}/{limit}"
        earliest = None
        for r in ud.get("requests", []):
            if isinstance(r, datetime):
                if earliest is None or r < earliest:
                    earliest = r
        if earliest:
            available_at = earliest + timedelta(hours=3)
            wait_seconds = max(0, int((available_at - datetime.now()).total_seconds()))
            minutes = wait_seconds // 60
            if minutes <= 0:
                return True, f"📊 Запросов: {used}/{limit}"
            return False, f"⏰ Лимит исчерпан ({used}/{limit}). Свободный слот через {minutes} минут."
        return False, f"⏰ Лимит исчерпан ({used}/{limit})"

def add_user_request(user_id):
    now = datetime.now()
    uid = str(user_id)
    with limits_lock:
        ensure_user_record(user_id)
        cleanup_old_requests_internal()
        user_limits[uid]["requests"].append(now)
        save_limits_to_file()

def set_user_limit(user_id, limit):
    uid = str(user_id)
    with limits_lock:
        if uid not in user_limits:
            user_limits[uid] = {"requests": [], "limit": int(limit), "unlimited": False}
        else:
            user_limits[uid]["limit"] = int(limit)
            user_limits[uid]["unlimited"] = False
        save_limits_to_file()

def grant_unlimited_access(user_id):
    uid = str(user_id)
    with limits_lock:
        user_limits[uid] = {"requests": [], "limit": 0, "unlimited": True}
        save_limits_to_file()

def get_user_limit_info(user_id):
    uid = str(user_id)
    with limits_lock:
        return user_limits.get(uid, {"requests": [], "limit": 3, "unlimited": False})

def format_field_name(field):
    names = {
        "_id": "ID записи",
        "full_name": "Полное имя",
        "first_name": "Имя",
        "last_name": "Фамилия",
        "middle_name": "Отчество",
        "birth_date": "Дата рождения",
        "phone": "Телефон",
        "email": "Email",
        "address": "Адрес",
        "city": "Город",
        "street": "Улица",
        "house": "Дом",
        "apartment": "Квартира",
        "floor": "Этаж",
        "passport": "Паспорт",
        "inn": "ИНН",
        "snils": "СНИЛС",
        "card_number": "Номер карты",
        "ip": "IP-адрес",
        "login": "Логин",
        "password": "Пароль",
        "user_agent": "User Agent",
        "device": "Устройство",
        "amount": "Сумма",
        "currency": "Валюта",
        "comment": "Комментарий",
        "latitude": "Широта",
        "longitude": "Долгота",
        "sex": "Пол",
        "age": "Возраст",
        "company": "Компания",
        "position": "Должность",
        "salary": "Зарплата",
        "_score": "Релевантность"
    }
    return names.get(field, field.replace("_", " ").capitalize())

def format_document_for_txt(doc, indent=0):
    lines = []
    indent_str = "  " * indent
    priority = [
        'full_name', 'first_name', 'last_name', 'phone', 'email', 'birth_date',
        'address', 'passport', 'ip', 'vk_id', 'vk_username'
    ]
    other = [k for k in doc.keys() if k not in priority and k not in ['_score']]
    for key in priority:
        if key in doc and doc[key] not in (None, ""):
            value = doc[key]
            fname = format_field_name(key)
            if isinstance(value, dict):
                lines.append(f"{indent_str}📌 {fname}:")
                lines.extend(format_document_for_txt(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{indent_str}📋 {fname} ({len(value)} элементов):")
                for i, item in enumerate(value, 1):
                    if isinstance(item, dict):
                        lines.append(f"{indent_str}  {i}.")
                        lines.extend(format_document_for_txt(item, indent + 2))
                    else:
                        lines.append(f"{indent_str}  {i}. {item}")
            else:
                lines.append(f"{indent_str}📌 {fname}: {value}")
    for key in other:
        if key in doc and doc[key] not in (None, ""):
            value = doc[key]
            fname = format_field_name(key)
            if isinstance(value, dict):
                lines.append(f"{indent_str}📁 {fname}:")
                lines.extend(format_document_for_txt(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{indent_str}📋 {fname} ({len(value)} элементов):")
                for i, item in enumerate(value, 1):
                    if isinstance(item, dict):
                        lines.append(f"{indent_str}  {i}.")
                        lines.extend(format_document_for_txt(item, indent + 2))
                    else:
                        lines.append(f"{indent_str}  {i}. {item}")
            else:
                lines.append(f"{indent_str}📄 {fname}: {value}")
    return lines

def create_beautiful_txt_report(query, results, user_id, search_time, query_type):
    lines = []
    lines.append("=" * 70)
    lines.append("📱 ПОЛНЫЙ ОТЧЕТ ПО ЗАПРОСУ".center(70))
    lines.append("=" * 70)
    lines.append(f"🔍 Тип запроса: {query_type}")
    lines.append(f"🔍 Запрос: {query}")
    lines.append(f"🕐 Дата и время поиска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append(f"⏱️ Время выполнения поиска: {search_time:.2f} секунд")
    lines.append(f"👤 ID пользователя: {user_id}")
    lines.append("")
    if not results:
        lines.append("❌ НИЧЕГО НЕ НАЙДЕНО")
        lines.append("")
        lines.append("=" * 70)
        lines.append("📱 Отчет сгенерирован автоматически".center(70))
        lines.append("=" * 70)
        lines.append(f"Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        return "\n".join(lines)
    total_sources = len(results)
    total_records = sum(r.get("found_count", 0) for r in results) if isinstance(results, list) else 0
    lines.append("📊 СТАТИСТИКА ПОИСКА:")
    lines.append("-" * 40)
    lines.append(f"📂 Всего источников: {total_sources}")
    lines.append(f"📝 Всего записей: {total_records}")
    lines.append("")
    if isinstance(results, list):
        for i, source_data in enumerate(results, 1):
            source = source_data.get("source", {})
            docs = source_data.get("documents", [])
            found_count = source_data.get("found_count", 0)
            lines.append(f"🔍 ИСТОЧНИК #{i}")
            lines.append("-" * 40)
            lines.append(f"🗄️ База данных: {source.get('database', 'Неизвестно')}")
            lines.append(f"📚 Коллекция: {source.get('collection', 'Неизвестно')}")
            lines.append(f"📊 Найдено записей: {found_count}")
            lines.append("")
            for j, doc in enumerate(docs, 1):
                lines.append(f"📄 ЗАПИСЬ #{j} из источника:")
                lines.append("-" * 30)
                formatted = format_document_for_txt(doc)
                if formatted:
                    lines.extend(formatted)
                else:
                    lines.append("  Нет данных для отображения")
                lines.append("")
    lines.append("=" * 70)
    lines.append("📱 КОНЕЦ ОТЧЕТА".center(70))
    lines.append("=" * 70)
    lines.append(f"Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    return "\n".join(lines)

def safe_request(url, params=None, max_retries=3, timeout=30, verify_ssl=False):
    for attempt in range(max_retries):
        try:
            log_message(f"Requesting {url} attempt {attempt+1}/{max_retries}")
            resp = SESSION.get(url, params=params, timeout=timeout, verify=verify_ssl)
            if resp.status_code == 401:
                log_message(f"401 Unauthorized for {url}")
                try:
                    bot.send_message(ADMIN_ID, f"⚠️ 401 Unauthorized when requesting {url}")
                except:
                    pass
                return {"status": "error", "error": {"message": "401 Unauthorized"}}
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                log_message(f"JSON parse error for {url}")
                return {"status": "error", "error": {"message": "JSON parse error"}}
        except requests.exceptions.Timeout:
            log_message(f"Timeout on attempt {attempt+1} for {url}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"status": "error", "error": {"message": "Timeout"}}
        except requests.exceptions.RequestException as e:
            try:
                status = getattr(e.response, "status_code", None)
                body = getattr(e.response, "text", None)
                log_message(f"RequestException for {url}: status={status}, body={body}")
            except:
                log_message(f"RequestException for {url}: {e}")
            return {"status": "error", "error": {"message": str(e)}}
    return {"status": "error", "error": {"message": "Max retries exceeded"}}

def normalize_phone(phone):
    if not phone:
        return ""
    s = str(phone)
    s = re.sub(r"[^\d+]", "", s)
    if s.startswith("8") and len(s) == 11:
        s = "+7" + s[1:]
    return s

def normalize_channel_input(raw):
    if not raw:
        return None
    s = str(raw).strip()
    if "t.me/" in s:
        s = s.split("t.me/")[-1].split("?")[0].strip("/")
    s = s.split("?")[0].strip("/")
    if re.fullmatch(r"-?\d+", s):
        try:
            return int(s)
        except:
            pass
    if s == "":
        return None
    if not s.startswith("@"):
        return "@" + s
    return s

def get_channel_identifier_from_cfg():
    with config_lock:
        required = cfg.get("required_channel")
    if not required:
        return None, None
    if isinstance(required, dict):
        if required.get("id") is not None:
            return required.get("id"), required
        if required.get("username"):
            uname = str(required.get("username"))
            return (uname if uname.startswith("@") else "@" + uname), required
        if required.get("raw"):
            return normalize_channel_input(required.get("raw")), required
    if isinstance(required, str):
        return normalize_channel_input(required), required
    return None, None

def build_channel_link(raw):
    if not raw:
        return None
    if isinstance(raw, dict):
        if raw.get("username"):
            return f"https://t.me/{raw.get('username').lstrip('@')}"
        if raw.get("raw"):
            r = raw.get("raw")
            if isinstance(r, int) or re.fullmatch(r"-?\d+", str(r)):
                return f"https://t.me/c/{str(r).lstrip('-')}"
            else:
                return f"https://t.me/{str(r).lstrip('@')}"
        if raw.get("id") is not None:
            return f"https://t.me/c/{str(raw.get('id')).lstrip('-')}"
    if isinstance(raw, int) or re.fullmatch(r"-?\d+", str(raw)):
        return f"https://t.me/c/{str(raw).lstrip('-')}"
    return f"https://t.me/{str(raw).lstrip('@')}"

def is_user_subscribed(user_id):
    identifier, raw = get_channel_identifier_from_cfg()
    if not identifier:
        return True, None
    try:
        member = bot.get_chat_member(identifier, user_id)
        status = getattr(member, "status", "")
        if status in ("creator", "administrator", "member", "restricted"):
            return True, None
        link = build_channel_link(raw)
        return False, link
    except ApiTelegramException as e:
        try:
            result_json = getattr(e, "result_json", {}) or {}
            desc = result_json.get("description", "")
        except:
            desc = str(e)
        if isinstance(desc, str) and ("bot was kicked" in desc.lower() or "bot is not a member" in desc.lower() or "chat not found" in desc.lower()):
            log_message(f"Bot has no access to channel: {desc}")
            return True, None
        if isinstance(desc, str) and "bot was blocked" in desc.lower():
            return False, None
        link = build_channel_link(raw)
        log_message(f"is_user_subscribed ApiTelegramException: {e}")
        return False, link
    except Exception:
        log_message("is_user_subscribed unexpected error")
        return True, None

def safe_send_document(chat_id, file_obj, **kwargs):
    try:
        return bot.send_document(chat_id, file_obj, **kwargs)
    except Exception as e:
        log_message(f"send_document error to {chat_id}: {e}")
        return None

def safe_send_message(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        log_message(f"send_message error to {chat_id}: {e}")
        return None

def create_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🔍 Поиск по телефону")
    btn2 = types.KeyboardButton("🔍 Поиск по ФИО")
    btn3 = types.KeyboardButton("🔍 Поиск по IP")
    btn4 = types.KeyboardButton("🔍 Поиск по VK")
    btn5 = types.KeyboardButton("🔍 Поиск по Email")
    btn6 = types.KeyboardButton("📊 Моя статистика")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.from_user.id
    subscribed, link = is_user_subscribed(user_id)
    if not subscribed:
        msg = "🔔 Для использования бота необходимо подписаться на канал."
        if link:
            msg += f"\n\nПерейдите по ссылке и подпишитесь: {link}"
        safe_send_message(message.chat.id, msg)
        return
    ud = user_limits.get(str(user_id), {})
    if ud.get("unlimited", False):
        limit_info = "✅ У вас безлимитный доступ"
    else:
        used = len(ud.get("requests", []))
        limit = ud.get("limit", 3)
        limit_info = f"📊 Ваш лимит: {used}/{limit} запросов (3 часа)"
    text = (
        "📱 ДОБРО ПОЖАЛОВАТЬ\n\n"
        "📤 Выберите тип поиска с помощью кнопок ниже:\n"
        "   • Поиск по телефону\n"
        "   • Поиск по ФИО и дате рождения\n"
        "   • Поиск по IP-адресу\n"
        "   • Поиск по VK профилю\n"
        "   • Поиск по Email\n\n"
        + limit_info
    )
    safe_send_message(message.chat.id, text, reply_markup=create_main_menu())

@bot.message_handler(commands=["help"])
def send_help(message):
    help_text = (
        "ℹ️ <b>Помощь по боту</b>\n\n"
        "📱 <b>Как пользоваться:</b>\n"
        "1. Используйте кнопки внизу для выбора типа поиска\n"
        "2. Введите данные в нужном формате\n"
        "3. Дождитесь завершения поиска\n"
        "4. Получите отчет в виде текстового файла\n\n"
        "📊 <b>Информация:</b>\n"
        "• Лимит использования: 3 запроса в 3 часа\n"
        "• Для увеличения лимита обратитесь к администратору\n\n"
        "💡 <b>Примеры:</b>\n"
        "<code>+79177840591</code> (телефон)\n"
        "<code>КУДРЯШОВ ПАВЕЛ СЕРГЕЕВИЧ 31.07.2002</code> (ФИО)\n"
        "<code>8.8.8.8</code> (IP-адрес)\n"
        "<code>id123456789</code> или <code>https://vk.com/id123456789</code> (VK)\n"
        "<code>example@gmail.com</code> (Email)"
    )
    safe_send_message(message.chat.id, help_text, parse_mode='HTML')

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        safe_send_message(message.chat.id, "❌ Доступ запрещён")
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        help_text = (
            "🔧 <b>Команды администратора:</b>\n"
            "/admin grant unlimited [user_id] - выдать безлимитный доступ\n"
            "/admin grant limit [limit] [user_id] - установить лимит для пользователя\n"
            "/admin info [user_id] - информация о пользователе\n"
            "/admin stats - статистика бота\n"
            "/admin broadcast [message] - рассылка сообщений всем пользователям\n"
            "/admin setchannel [channel] - установить обязательный канал (@username, ID, или ссылка)"
        )
        safe_send_message(message.chat.id, help_text, parse_mode='HTML')
        return
    action = parts[1]
    if action == "grant" and len(parts) >= 4:
        grant_type = parts[2]
        if grant_type == "unlimited":
            try:
                target = int(parts[3])
                grant_unlimited_access(target)
                safe_send_message(
                    message.chat.id,
                    f"✅ Пользователю <code>{target}</code> выдан безлимитный доступ",
                    parse_mode='HTML'
                )
            except:
                safe_send_message(message.chat.id, "❌ Неверный ID пользователя")
        elif grant_type == "limit" and len(parts) >= 5:
            try:
                limit = int(parts[3])
                target = int(parts[4])
                set_user_limit(target, limit)
                safe_send_message(
                    message.chat.id,
                    f"✅ Пользователю <code>{target}</code> установлен лимит <code>{limit}</code> запросов",
                    parse_mode='HTML'
                )
            except:
                safe_send_message(message.chat.id, "❌ Неверные параметры")
        else:
            safe_send_message(message.chat.id, "❌ Неверный формат команды grant")
    elif action == "info" and len(parts) >= 3:
        try:
            target = int(parts[2])
            info = get_user_limit_info(target)
            if info.get("unlimited", False):
                safe_send_message(
                    message.chat.id,
                    f"ℹ️ Пользователь <code>{target}</code>: Безлимитный доступ",
                    parse_mode='HTML'
                )
            else:
                used = len(info.get("requests", []))
                limit = info.get("limit", 3)
                safe_send_message(
                    message.chat.id,
                    f"ℹ️ Пользователь <code>{target}</code>: Использовано <code>{used}/{limit}</code> запросов",
                    parse_mode='HTML'
                )
        except:
            safe_send_message(message.chat.id, "❌ Неверный ID пользователя")
    elif action == "stats":
        with limits_lock:
            total = len(user_limits)
            unlimited = len([u for u in user_limits.values() if u.get("unlimited", False)])
            total_requests = sum(len(u.get("requests", [])) for u in user_limits.values())
        safe_send_message(
            message.chat.id,
            f"📈 <b>Статистика бота:</b>\n"
            f"👥 Пользователей: <code>{total}</code>\n"
            f"🔓 С безлимитом: <code>{unlimited}</code>\n"
            f"📊 Всего запросов: <code>{total_requests}</code>",
            parse_mode='HTML'
        )
    elif action == "broadcast" and len(parts) >= 3:
        broadcast_message = " ".join(parts[2:])
        safe_send_message(message.chat.id, "📢 Начинаю рассылку сообщения всем пользователям...")
        with limits_lock:
            user_ids = list(user_limits.keys())
        success_count = 0
        failed_count = 0
        for user_id_str in user_ids:
            try:
                user_id = int(user_id_str)
                safe_send_message(
                    user_id,
                    f"📢 <b>Сообщение от администратора:</b>\n\n{broadcast_message}",
                    parse_mode='HTML'
                )
                success_count += 1
                time.sleep(0.05)
            except ApiTelegramException as e:
                if "bot was blocked" in str(e) or "user is deactivated" in str(e) or "chat not found" in str(e):
                    log_message(f"User {user_id_str} blocked the bot or is deactivated. Removing from user list.")
                    with limits_lock:
                        if user_id_str in user_limits:
                            del user_limits[user_id_str]
                else:
                    log_message(f"Failed to send broadcast to user {user_id_str}: {e}")
                failed_count += 1
            except Exception as e:
                log_message(f"Unexpected error sending broadcast to user {user_id_str}: {e}")
                failed_count += 1
        save_limits_to_file()
        safe_send_message(
            message.chat.id,
            f"✅ Рассылка завершена!\n\n"
            f"✅ Успешно отправлено: <code>{success_count}</code>\n"
            f"❌ Неудачно: <code>{failed_count}</code>",
            parse_mode='HTML'
        )
    elif action == "setchannel" and len(parts) >= 3:
        channel_ref = " ".join(parts[2:])
        norm = normalize_channel_input(channel_ref)
        if not norm:
            safe_send_message(message.chat.id, "❌ Неверный формат канала")
            return
        to_save = {"raw": channel_ref}
        if isinstance(norm, int):
            to_save["id"] = norm
        else:
            if isinstance(norm, str) and norm.startswith("@"):
                to_save["username"] = norm.lstrip("@")
            else:
                to_save["raw"] = channel_ref
        with config_lock:
            cfg["required_channel"] = to_save
            save_config(cfg)
        norm_display = norm if not isinstance(norm, dict) else str(norm)
        safe_send_message(
            message.chat.id,
            f"✅ Обязательный канал установлен: <code>{norm_display}</code>",
            parse_mode='HTML'
        )
    else:
        safe_send_message(message.chat.id, "❌ Неизвестная команда. Используйте /admin для получения списка команд.")

@bot.message_handler(func=lambda m: m.text == "📊 Моя статистика")
def show_stats(message):
    user_id = message.from_user.id
    ud = user_limits.get(str(user_id), {})
    if ud.get("unlimited", False):
        safe_send_message(message.chat.id, "📊 Ваша статистика:\n✅ У вас безлимитный доступ")
    else:
        used = len(ud.get("requests", []))
        limit = ud.get("limit", 3)
        safe_send_message(message.chat.id, f"📊 Ваша статистика:\n📊 Запросов: {used}/{limit} (3 часа)")

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск по телефону")
def phone_search_prompt(message):
    safe_send_message(message.chat.id, "📞 Введите номер телефона в формате +7XXXXXXXXXX")

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск по ФИО")
def fio_search_prompt(message):
    safe_send_message(message.chat.id, "👤 Введите ФИО и дату рождения в формате:\nФАМИЛИЯ ИМЯ ОТЧЕСТВО ДД.ММ.ГГГГ")

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск по IP")
def ip_search_prompt(message):
    safe_send_message(message.chat.id, "🌐 Введите IP-адрес в формате X.X.X.X")

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск по VK")
def vk_search_prompt(message):
    safe_send_message(message.chat.id, "👤 Введите ID или ссылку на VK профиль:\nПримеры: id123456789 или https://vk.com/id123456789")

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск по Email")
def email_search_prompt(message):
    safe_send_message(message.chat.id, "📧 Введите email-адрес:\nПример: example@gmail.com")

def perform_search(message, query, query_type):
    user_id = message.from_user.id
    subscribed, link = is_user_subscribed(user_id)
    if not subscribed:
        msg = "🔔 Для использования бота необходимо подписаться на канал."
        if link:
            msg += f"\n\nПерейдите по ссылке и подпишитесь: {link}"
        safe_send_message(message.chat.id, msg)
        return
    allowed, lm = can_user_make_request(user_id)
    if not allowed:
        safe_send_message(message.chat.id, lm)
        return
    try:
        safe_send_message(message.chat.id, f"🔍 Поиск по: {query}\n{lm}")
    except:
        pass
    start = time.time()
    resp = safe_request(f"{API_BASE_URL}/search", params={"q": query})
    elapsed = time.time() - start
    if not isinstance(resp, dict) or resp.get("status") == "error":
        err_msg = "Неизвестная ошибка API"
        try:
            err = resp.get("error")
            if isinstance(err, dict):
                err_msg = err.get("message", err_msg)
            elif isinstance(err, str):
                err_msg = err
        except:
            pass
        safe_send_message(message.chat.id, f"❌ Ошибка API: {err_msg}")
        return
    items = []
    if isinstance(resp.get("items"), list):
        items = resp.get("items")
    else:
        data = resp.get("data") or {}
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            items = data.get("items")
        elif isinstance(resp.get("data"), list):
            items = resp.get("data")
    if not items:
        add_user_request(user_id)
        safe_send_message(message.chat.id, f"Ничего не найдено для: {query}")
        return
    add_user_request(user_id)
    results = []
    for item in items:
        source = item.get("source", {})
        db = source.get("database")
        coll = source.get("collection")
        if db and coll:
            r = safe_request(f"{API_BASE_URL}/{db}/{coll}/search", params={"q": query, "count": 25})
            if isinstance(r, dict) and r.get("status") == "success":
                d = r.get("data") or {}
                if isinstance(d, dict) and isinstance(d.get("items"), list):
                    docs = d.get("items")
                elif isinstance(r.get("items"), list):
                    docs = r.get("items")
                else:
                    docs = []
                if docs:
                    results.append({
                        "source": {"database": db, "collection": coll},
                        "found_count": len(docs),
                        "documents": docs
                    })
    report = create_beautiful_txt_report(query, results, user_id, elapsed, query_type)
    tf_path = None
    try:
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tf_path = tf.name
        tf.close()
        with open(tf_path, "wb") as f:
            f.write(report.encode("utf-8"))
        with open(tf_path, "rb") as fh:
            caption = f"✅ Поиск завершён\n🔍 {query}\n⏱ {elapsed:.2f}s\n📊 Источников: {len(results)}"
            safe_send_document(message.chat.id, fh, caption=caption)
    except Exception as e:
        log_message(f"Send report error: {e}")
        safe_send_message(message.chat.id, "❌ Ошибка отправки отчёта")
    finally:
        if tf_path and os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except:
                pass

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if message.text and message.text.startswith("/admin"):
        admin_panel(message)
        return
    if message.text == "🔍 Поиск по телефону":
        phone_search_prompt(message)
        return
    elif message.text == "🔍 Поиск по ФИО":
        fio_search_prompt(message)
        return
    elif message.text == "🔍 Поиск по IP":
        ip_search_prompt(message)
        return
    elif message.text == "🔍 Поиск по VK":
        vk_search_prompt(message)
        return
    elif message.text == "🔍 Поиск по Email":
        email_search_prompt(message)
        return
    elif message.text == "📊 Моя статистика":
        show_stats(message)
        return
    user_id = message.from_user.id
    subscribed, link = is_user_subscribed(user_id)
    if not subscribed:
        msg = "🔔 Для использования бота необходимо подписаться на канал."
        if link:
            msg += f"\n\nПерейдите по ссылке и подпишитесь: {link}"
        safe_send_message(message.chat.id, msg)
        return
    raw = (message.text or "").strip()
    fio_match = FIO_DATE_PATTERN.match(raw)
    if fio_match:
        last_name, first_name, middle_name, day, month, year = fio_match.groups()
        formatted_date = f"{int(day):02d}.{int(month):02d}.{year}"
        full_name = f"{last_name} {first_name} {middle_name}".upper()
        query_string = f"{full_name} {formatted_date}"
        perform_search(message, query_string, "ФИО + дата рождения")
        return
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', raw):
        if all(0 <= int(x) <= 255 for x in raw.split('.')):
            perform_search(message, raw, "IP-адрес")
            return
    if VK_PATTERN.match(raw):
        match = VK_PATTERN.match(raw)
        vk_id = match.group(1)
        perform_search(message, vk_id, "VK профиль")
        return
    if EMAIL_PATTERN.match(raw):
        perform_search(message, raw, "Email")
        return
    phone = normalize_phone(raw)
    if re.match(r"^\+7\d{10}$", phone):
        perform_search(message, phone, "Телефон")
        return
    safe_send_message(
        message.chat.id,
        "❌ НЕВЕРНЫЙ ФОРМАТ!\n\n"
        "📱 Правильные форматы:\n"
        "   +7XXXXXXXXXX (телефон)\n"
        "   ИЛИ\n"
        "   ФАМИЛИЯ ИМЯ ОТЧЕСТВО ДД.ММ.ГГГГ (ФИО)\n"
        "   ИЛИ\n"
        "   X.X.X.X (IP-адрес)\n"
        "   ИЛИ\n"
        "   id123456789 или https://vk.com/id123456789 (VK)\n"
        "   ИЛИ\n"
        "   example@gmail.com (Email)\n\n"
        "💡 Примеры:\n"
        "   +79177840591\n"
        "   КУДРЯШОВ ПАВЕЛ СЕРГЕЕВИЧ 31.07.2002\n"
        "   8.8.8.8\n"
        "   id123456789\n"
        "   example@gmail.com"
    )

def periodic_cleanup():
    while not shutdown_event.is_set():
        try:
            for _ in range(3600):
                if shutdown_event.is_set():
                    log_message("Periodic cleanup thread stopping.")
                    return
                time.sleep(1)
            cleanup_old_requests()
            log_message("Periodic cleanup completed.")
        except Exception as e:
            log_message(f"Periodic cleanup error: {e}")

def _graceful(signum, frame):
    log_message(f"Received signal {signum}, shutting down gracefully...")
    shutdown_event.set()
    try:
        save_limits_to_file()
        log_message("Limits saved on shutdown.")
    except:
        pass
    try:
        save_config(cfg)
        log_message("Config saved on shutdown.")
    except:
        pass
    try:
        os._exit(0)
    except:
        os._exit(1)

import signal
signal.signal(signal.SIGINT, _graceful)
signal.signal(signal.SIGTERM, _graceful)

def start_polling_with_retries():
    while not shutdown_event.is_set():
        try:
            log_message("Starting bot polling...")
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                allowed_updates=["message", "callback_query", "chat_member"],
                skip_pending=True
            )
        except (requests.exceptions.ReadTimeout, RemoteDisconnected):
            log_message("Connection issue. Retrying in 5 seconds...")
            time.sleep(5)
        except requests.exceptions.ConnectionError as e:
            log_message(f"ConnectionError: {e}. Retrying in 10 seconds...")
            time.sleep(10)
        except ApiTelegramException as e:
            if "Conflict" in str(e) or "409" in str(e):
                log_message("Bot conflict detected. Another instance may be running.")
                try:
                    bot.send_message(ADMIN_ID, "⚠️ Конфликт: другой экземпляр бота запущен.")
                except:
                    pass
                break
            else:
                log_message(f"ApiTelegramException: {e}. Retrying in 15 seconds...")
                time.sleep(15)
        except Exception as e:
            log_message(f"Unexpected error: {e}. Retrying in 30 seconds...")
            time.sleep(30)
        finally:
            if not shutdown_event.is_set():
                log_message("Reconnecting...")

if __name__ == "__main__":
    log_message("Bot starting...")
    load_limits_from_file()
    cfg = load_config()
    try:
        try:
            bot.remove_webhook()
            log_message("Webhook removed.")
        except:
            try:
                bot.delete_webhook()
                log_message("Webhook deleted.")
            except:
                pass
    except:
        pass
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    log_message("Periodic cleanup thread started.")
    start_polling_with_retries()
