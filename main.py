import httpx
from bs4 import BeautifulSoup
import re
from datetime import datetime
from gtts import gTTS
import time
import threading
import json
import os
import hashlib
import phonenumbers
from phonenumbers import geocoder
import requests
from langdetect import detect, LangDetectException, DetectorFactory
from colorama import init, Fore, Style

def make_httpx_client(timeout=30):
    return httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "X-Requested-With": "XMLHttpRequest"}
    )

def make_requests_session():
    return requests.Session()

# ================= FILES =================
ACCOUNTS_FILE = "accounts.json"
COOKIES_FILE = "cookie.json"
CACHE_FILE = "file/sent_cache.json"
MAX_CACHE_SIZE = 2000
LANG_CODE_MAP = {  
    "id": "#Indonesia", "en": "#English", "fr": "#French", "es": "#Spanish",  
    "pt": "#Portuguese", "ar": "#Arabic", "ru": "#Russian", "tr": "#Turkish",  
    "hi": "#Hindi", "th": "#Thai", "vi": "#Vietnamese", "ms": "#Malay",  
    "tl": "#Filipino", "ja": "#Japanese", "ko": "#Korean", "zh-cn": "#Chinese",  
    "nl": "#Dutch", "sv": "#Swedish", "pl": "#Polish", "uk": "#Ukrainian",  
    "cs": "#Czech", "ro": "#Romanian", "el": "#Greek", "he": "#Hebrew", "fa": "#Persian"  
}  
    
# ================= CONFIG =================
OWNER_ID = 1611669051  # ID OWNER 
BASE = "https://ivaskicen2.serverkicen.biz.id"
LOGIN_URL = f"{BASE}/login"
GET_RANGE_URL = f"{BASE}/portal/sms/received/getsms"
GET_NUMBER_URL = f"{BASE}/portal/sms/received/getsms/number"
GET_SMS_URL = f"{BASE}/portal/sms/received/getsms/number/sms"
RETURN_NUMBER_URL = f"{BASE}/portal/numbers/return/number"
RETURN_ALL_URL = f"{BASE}/portal/numbers/return/allnumber/bluck"
EXPORT_URL = f"{BASE}/portal/numbers/export"

BOT_TOKEN = "8972596901:AAEZueI_bs2Z4CIfaTEhk01ibTj-wrOFcFE"
GROUPS_FILE = "groups.json"
ADDNUM_API_URL = "https://ws.websocket.web.id/admin/addnumber"
ADDNUM_API_KEY = "112231"
USERS_FILE = "users.json"
PREMIUM_FILE = "premium.json"
AMBIL_FILE = "file/ambil_nomor.json"
PREMIUM_COOKIE_FILE = "premium-cookie.json"
LINK_OWNER = "t.me/maklocuki"
LINK_CHANNEL = "https://t.me/xorakuk"

SERVICE_SHORT = {
    "WHATSAPP": "#WS", "TELEGRAM": "#TG", "GOOGLE": "#G", "FACEBOOK": "#FB",
    "INSTAGRAM": "#IG", "SHOPEE": "#SP", "TOKOPEDIA": "#TP", "GRAB": "#GR",
    "GOJEK": "#GJ", "TIKTOK": "#TT"
}
sms_stats = {
    "total_sms": 0,
    "total_otp": 0,
    "total_number": set()
}
last_update_id = 0
MAX_EMAIL = 20 # Setting Max Email User/Owner
DetectorFactory.seed = 0
init(autoreset=True)
accounts_lock = threading.Lock()
LOGIN_COOLDOWN = 300  # 5 menit
SESSION_RETRY_INTERVAL = 600  # retry setiap 10 menit kalau session gagal
pending_setcookie = {}   # user_id -> {"email": str, "msg_id": int}
pending_addcookie = {}   # user_id -> {"email": str, "msg_id": int}
pending_addnum    = {}   # user_id -> {"email": str, "msg_id": int}

# ================= SESSION TRACKER =================
_session_fail_time   = {}   # email -> timestamp pertama kali gagal
_session_notified    = {}   # email -> bool sudah notif atau belum
_session_retry_time  = {}   # email -> timestamp terakhir retry
_session_recovered   = {}   # email -> bool sudah notif recover

# ================= ACCOUNT MANAGEMENT =================
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "w") as f:
            f.write('{"accounts":[]}')
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("accounts", [])
    except:
        return []

def save_accounts():
    data_to_save = []
    for acc in accounts:
        data_to_save.append({
            "email": acc.get("email"),
            "password": acc.get("password"),
            "cookies": acc.get("cookies", {})
        })
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"accounts": data_to_save}, f, indent=2)

def load_cookies():
    if not os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "w") as f:
            f.write("{}")
        return {}
    try:
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def load_premium():
    if not os.path.exists(PREMIUM_FILE):
        with open(PREMIUM_FILE, "w") as f:
            json.dump({}, f)
    try:
        with open(PREMIUM_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_premium(data):
    with open(PREMIUM_FILE, "w") as f:
        json.dump(data, f, indent=2)

premium_users = load_premium()

def is_premium(user_id):
    if user_id == OWNER_ID:
        return True
    user = premium_users.get(str(user_id))
    if not user:
        return False
    return time.time() < user["expired"]
    
def save_cookies(cookies_dict):
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies_dict, f, indent=2)
        
def load_groups():
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w") as f:
            json.dump({"groups": []}, f)
    try:
        with open(GROUPS_FILE, "r") as f:
            return json.load(f).get("groups", [])
    except:
        return []

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}
        
def load_premium_cookies():
    if not os.path.exists(PREMIUM_COOKIE_FILE):
        with open(PREMIUM_COOKIE_FILE, "w") as f:
            json.dump({}, f)
    try:
        with open(PREMIUM_COOKIE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_premium_cookies(data):
    with open(PREMIUM_COOKIE_FILE, "w") as f:
        json.dump(data, f, indent=2)

premium_cookies = load_premium_cookies()        

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)        

def save_groups():
    with open(GROUPS_FILE, "w") as f:
        json.dump({"groups": groups}, f, indent=2)

groups = load_groups()

def load_sent_cache():
    os.makedirs("file", exist_ok=True)
    if not os.path.exists(CACHE_FILE):
        return set()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except:
        return set()

def save_sent_cache():
    try:
        os.makedirs("file", exist_ok=True)
        cache_list = list(sent_cache)
        if len(cache_list) > MAX_CACHE_SIZE:
            cache_list = cache_list[-MAX_CACHE_SIZE:]
            sent_cache.clear()
            sent_cache.update(cache_list)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_list, f)
    except Exception as e:
        print(f"Error save cache: {e}")

# ================= LOAD DATA =================
accounts = load_accounts()
cookies_data = load_cookies()
sent_cache = load_sent_cache()

for acc in accounts:
    acc["session"] = make_httpx_client()
    acc["last_login"] = 0
    acc["csrf_token"] = "" 

    email = acc["email"]
    if email in cookies_data:
        acc["cookies"] = cookies_data[email]
        acc["session"].cookies.update(cookies_data[email])

# ================= ACCOUNT COMMANDS =================
def add_account(text):
    try:
        parts = text.split()
        if len(parts) < 3:
            tg_active("  Format: /addakun email password")
            return

        email, password = parts[1], parts[2]

        with accounts_lock:
            for acc in accounts:
                if acc["email"] == email:
                    tg_active(f"  Akun sudah ada: {email}")
                    return

            acc = {
                "email": email,
                "password": password,
                "cookies": {},
                "session": make_httpx_client(),
                "last_login": 0,
                "csrf_token": ""
            }

            accounts.append(acc)
            save_accounts()

        if login(acc):
            acc["last_login"] = time.time()
            tg_active(f"  Akun aktif & login: {email}")
        else:
            tg_active(f"   Akun masuk tapi login gagal: {email}")

    except Exception as e:
        tg_active(f"  Error add akun: {e}")
        
def save_number(number):
    try:
        with open(AMBIL_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {"numbers": []}

    if number not in data["numbers"]:
        data["numbers"].append(number)

    with open(AMBIL_FILE, "w") as f:
        json.dump(data, f, indent=2)

def ambilnomor_to_txt():
    try:
        with open(AMBIL_FILE, "r") as f:
            data = json.load(f)
            numbers = data.get("numbers", [])
    except:
        numbers = []

    if not numbers:
        return None

    filename = "file/nomor.txt"
    with open(filename, "w") as f:
        for n in numbers:
            f.write(f"{n}\n") 

    return filename

def export_numbers_ivas(chat_id, email, status_msg_id=None):
    def _status(text):
        if status_msg_id:
            delete_and_send(chat_id, status_msg_id, text)
        else:
            send_msg(chat_id, text)

    all_cookies = load_cookies()
    prem_cookies = load_premium_cookies()

    cookies = all_cookies.get(email) or prem_cookies.get(email)
    if not cookies:
        _status(f"📁 <b>AMBIL FILE</b>\n\n📧 Email: <code>{email}</code>\n❌ Cookie tidak ditemukan. Set cookie dulu dengan /setcookie atau /addcookie.")
        return

    session = make_requests_session()
    session.cookies.update(cookies)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": f"{BASE}/portal/numbers",
        "Origin": BASE,
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        r_home = session.get(f"{BASE}/portal/numbers", headers=headers)
        token_match = re.search(r'name="_token" value="(.*?)"', r_home.text)
        token = token_match.group(1) if token_match else ""

        if not token:
            _status(f"📁 <b>AMBIL FILE</b>\n\n📧 Email: <code>{email}</code>\n❌ Gagal ambil token. Cookie mungkin expired.")
            return

        r = session.post(EXPORT_URL, headers=headers, data={"_token": token}, stream=True)

        if r.status_code != 200 or "text/html" in r.headers.get("Content-Type", ""):
            r = session.get(EXPORT_URL, headers=headers, stream=True)

        if "/login" in r.url:
            _status(f"📁 <b>AMBIL FILE</b>\n\n📧 Email: <code>{email}</code>\n❌ Cookie expired. Perbarui cookie.")
            return

        if r.status_code != 200:
            _status(f"📁 <b>AMBIL FILE</b>\n\n📧 Email: <code>{email}</code>\n❌ HTTP {r.status_code}")
            return

        filename = "ivas_export.xlsx"
        cd = r.headers.get("Content-Disposition", "")
        if "filename" in cd:
            filename = re.findall('filename="?(.+?)"?$', cd)[0]

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{now}_{filename}"
        os.makedirs("file", exist_ok=True)
        filepath = f"file/{filename}"

        with open(filepath, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)

        if status_msg_id:
            delete_msg(chat_id, status_msg_id)

        with open(filepath, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={
                    "chat_id": chat_id,
                    "caption": (
                        f"📁 <b>FILE IVAS BERHASIL DIAMBIL</b>\n\n"
                        f"<blockquote>"
                        f"📧 Email  : <code>{email}</code>\n"
                        f"📄 File   : <code>{filename}</code>\n"
                        f"🕐 Waktu  : <code>{now}</code>\n"
                        f"✅ Status : Berhasil"
                        f"</blockquote>"
                    ),
                    "parse_mode": "HTML"
                },
                files={"document": (filename, f)}
            )
        os.remove(filepath)

    except Exception as e:
        _status(f"📁 <b>AMBIL FILE</b>\n\n📧 Email: <code>{email}</code>\n❌ Error: <code>{e}</code>")
        
def del_account(text):
    try:
        _, email = text.split()
        global accounts
        accounts = [a for a in accounts if a["email"] != email]
        save_accounts()
        tg_active(f"  Akun dihapus: {email}")
    except:
        tg_active("  Format salah /delakun email")

def detect_language(text):
    try:
        if not text or len(text) < 10: return "#Unknown"
        text = re.sub(r"\d+", "", text).strip()
        if len(text) < 5: return "#Unknown"
        lang_code = detect(text)
        return LANG_CODE_MAP.get(lang_code, f"#{lang_code.upper()}")
    except LangDetectException:
        return "#Unknown"
        
def list_accounts(chat_id, user_id):
    try:
        if not accounts:
            send_msg(chat_id, "Belum ada akun")
            return
        msg = "  <b>LIST AKUN</b>\n\n"
        now = time.time()
        for i, acc in enumerate(accounts, 1):
            email = acc.get("email", "Unknown")
            safe_email = email if user_id == OWNER_ID else mask_email(email)
            last_login = acc.get("last_login", 0)
            status = "ACTIVE  " if now - last_login < LOGIN_COOLDOWN else "OFFLINE  "
            msg += f"{i}. {safe_email} | {status}\n"
        send_msg(chat_id, msg)
    except Exception as e:
        send_msg(chat_id, f"  Error list akun: {e}")
        
def add_premium(text, chat_id):
    try:
        parts = text.split()
        if len(parts) < 4:
            send_msg(chat_id, "  Format:\n/addprem user_id hari limit")
            return
        uid, hari, limit = parts[1], int(parts[2]), int(parts[3])
        expired = time.time() + (hari * 86400)
        premium_users[str(uid)] = {"expired": expired, "limit": limit, "used": 0, "last_reset": datetime.now().strftime("%Y-%m-%d")}
        save_premium(premium_users)
        send_msg(chat_id, f"  USER {uid} TELAH MENJADI PREMIUM\n  Durasi :  {hari} hari\n  Limit :  {limit}/hari")
    except Exception as e:
        send_msg(chat_id, f"  Error: {e}")
        
def add_cookie_premium(text, chat_id, user_id):
    cmd_addcookie(chat_id, user_id)  
        
def del_cookie_premium(text, chat_id, user_id):
    try:
        if not is_premium(user_id): return
        _, email = text.split()
        premium_cookies = load_premium_cookies()
        if email not in premium_cookies: return send_msg(chat_id, "  Cookie tidak ditemukan")
        del premium_cookies[email]
        save_premium_cookies(premium_cookies)
        send_msg(chat_id, f"  Cookie dihapus:\n{email}")
    except:
        send_msg(chat_id, "  Format:\n/delcookie email")                    
        
def check_limit(user_id):
    if user_id == OWNER_ID: return True
    user = premium_users.get(str(user_id))
    if not user: return False
    reset_limit_if_needed(user_id)
    if user["used"] >= user["limit"]: return False
    user["used"] += 1
    save_premium(premium_users)
    return True        

def del_premium(text, chat_id):
    try:
        _, uid = text.split()
        if uid not in premium_users: return send_msg(chat_id, "  User bukan premium")
        del premium_users[uid]
        save_premium(premium_users)
        send_msg(chat_id, f"  User {uid} dihapus dari PREMIUM")
    except: send_msg(chat_id, "  Format:\n/delprem user_id")

def is_owner(user_id): return user_id == OWNER_ID
                                
def list_premium(chat_id):
    if not premium_users: return send_msg(chat_id, "Belum ada user premium")
    msg = "  <b>LIST PREMIUM</b>\n\n"
    for i, (uid, data) in enumerate(premium_users.items(), 1):
        sisa = int((data["expired"] - time.time()) // 86400)
        msg += f"{i}. {uid} | {sisa} hari | {data['limit']}/hari\n"
    send_msg(chat_id, msg)                    
    
def send_msg(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}) 
    
def cek_premium(chat_id, user_id):
    if user_id == OWNER_ID:
        return send_msg(chat_id, "  <b>STATUS PREMIUM</b>\n\n  OWNER MODE\n   Unlimited Access\n  Tanpa Limit")
    user = premium_users.get(str(user_id))
    if not user: return send_msg(chat_id, "  Kamu bukan user premium")
    if time.time() > user["expired"]:
        del premium_users[str(user_id)]
        save_premium(premium_users)
        return send_msg(chat_id, "  Premium kamu sudah expired")
    reset_limit_if_needed(user_id)
    sisa_detik = int(user["expired"] - time.time())
    sisa_hari = max(0, sisa_detik // 86400)
    msg = f"  <b>STATUS PREMIUM</b>\n\n  Sisa Hari : {sisa_hari} hari\n  Limit     : {user['used']}/{user['limit']}\n  Reset     : Setiap hari\n"
    send_msg(chat_id, msg)
    
def reset_limit_if_needed(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    user = premium_users.get(str(user_id))
    if not user: return
    if user.get("last_reset") != today:
        user["used"] = 0
        user["last_reset"] = today
        save_premium(premium_users)                        

# ================= MENU & COMMANDS SYSTEM =================
def handle_start(user_id, chat_id):
    owner = is_owner(user_id)
    is_prem = is_premium(user_id)
    THUMBNAIL_PATH = "./thumbnail.png"

    if owner or is_prem:
        if owner:
            caption = (
                "🤖 <b>BOT OTP IVAS V7</b>\n"
                "<i>SMS/OTP monitoring — Platform IVAS</i>\n\n"
                "👑 <b>OWNER</b>\n"
                "<blockquote>"
                "/setcookie\n"
                "/addakun\n"
                "/delakun\n"
                "/listakun\n"
                "/addprem\n"
                "/delprem\n"
                "/listprem\n"
                "/statsms"
                "</blockquote>\n\n"
                "🌟 <b>PREMIUM</b>\n"
                "<blockquote>"
                "/addcookie\n"
                "/addemail\n"
                "/listemail\n"
                "/delcookie\n"
                "/addnum\n"
                "/delnumall\n"
                "/myrange\n"
                "/ambilfile\n"
                "/cekivas\n"
                "/cekprem"
                "</blockquote>\n\n"
                "💬 <b>GROUP</b>\n"
                "<blockquote>"
                "/addgrup\n"
                "/delgrup\n"
                "/listgrup"
                "</blockquote>"
            )
        else:
            caption = (
                "🤖 <b>BOT OTP IVAS V7</b>\n"
                "<i>SMS/OTP monitoring — Platform IVAS</i>\n\n"
                "🌟 <b>PREMIUM</b>\n"
                "<blockquote>"
                "/addcookie\n"
                "/addemail\n"
                "/listemail\n"
                "/delcookie\n"
                "/addnum\n"
                "/delnumall\n"
                "/myrange\n"
                "/ambilfile\n"
                "/cekivas\n"
                "/cekprem"
                "</blockquote>\n\n"
                "💬 <b>GROUP</b>\n"
                "<blockquote>"
                "/addgrup\n"
                "/delgrup\n"
                "/listgrup"
                "</blockquote>"
            )
    else:
        caption = (
            "🔒 <b>BOT OTP IVAS V7</b>\n\n"
            "❌ <b>Akses Ditolak</b> — Kamu belum premium.\n\n"
            "💎 <b>PRICELIST</b>\n"
            "<blockquote>"
            "🟢 <b>BASIC</b>  — 3 Hari / 20 Req  → Rp10.000\n"
            "🔵 <b>PRO</b>    — 7 Hari / 50 Req  → Rp25.000\n"
            "🟣 <b>SULTAN</b> — 30 Hari / 100 Req → Rp40.000"
            "</blockquote>\n\n"
            "📩 @maklocuki untuk beli akses."
        )

    try:
        if os.path.exists(THUMBNAIL_PATH):
            with open(THUMBNAIL_PATH, "rb") as photo:
                r = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                    files={"photo": photo},
                    timeout=15
                )
            if not r.json().get("ok"):
                send_msg(chat_id, caption)
        else:
            send_msg(chat_id, caption)
    except Exception as e:
        send_msg(chat_id, caption)

def code_to_flag(code):
    try: return ''.join(chr(127397 + ord(c)) for c in code.upper())
    except: return "  "
        
def add_email(text, chat_id, user_id, msg_id):
    parts = text.split()
    if len(parts) < 2: return send_msg(chat_id, "  Format:\n/addemail email@gmail.com")
    email = parts[1].strip().lower()
    if "@" not in email: return send_msg(chat_id, "  Email tidak valid!")

    users = load_users()
    user_data = users.get(str(user_id), {"emails": []})
    if len(user_data["emails"]) >= MAX_EMAIL: return send_msg(chat_id, f"  Maksimal {MAX_EMAIL} email!")
    if email in user_data["emails"]: return send_msg(chat_id, "  Email sudah ada!")

    user_data["emails"].append(email)
    users[str(user_id)] = user_data
    save_users(users)
    res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": chat_id, "text": f"  Email ditambahkan:\n{email}"})

def list_email(chat_id, user_id):
    users = load_users()
    if str(user_id) not in users or not users[str(user_id)]["emails"]: return send_msg(chat_id, "  Belum ada email")
    msg = "  <b>LIST EMAIL</b>\n\n"
    for i, em in enumerate(users[str(user_id)]["emails"], 1): msg += f"{i}. {em}\n"
    send_msg(chat_id, msg)        
        
def get_user_emails(user_id):
    """Kembalikan daftar email milik user: owner -> dari accounts, premium -> dari users.json"""
    if is_owner(user_id):
        return [acc["email"] for acc in accounts]
    users = load_users()
    return users.get(str(user_id), {}).get("emails", [])

# ================= ADDNUM FLOW =================
def command_addnum(text, chat_id, user_id):
    emails = get_user_emails(user_id)
    if not emails:
        return send_msg(chat_id, "❌ Belum ada email/akun.\nTambah dulu dengan /addemail atau /addakun")
    buttons = [{"text": f"📧 {em}", "callback_data": f"an:{em}"} for em in emails]
    buttons.append({"text": "❌ Batalkan", "callback_data": "cancel:an"})
    send_inline_keyboard(chat_id,
        "➕ <b>ADD NUMBER</b>\n\n"
        "<blockquote>📋 Cara Penggunaan:\n"
        "1. Pilih email akun IVAS di bawah\n"
        "2. Ketik target nomor atau negara\n"
        "   Contoh: <code>SAUDI ARABIA 15022</code>\n"
        "   Contoh: <code>INDONESIA 500</code>\n"
        "3. Bot akan proses penambahan nomor ke akun\n\n"
        "⚠️ Pastikan cookie sudah aktif sebelum add number</blockquote>\n\n"
        "👇 Pilih email:",
        buttons)

def handle_addnum_email_cb(chat_id, user_id, email, cb_id, msg_id):
    answer_callback_query(cb_id, "✅ Email dipilih!")
    emails = get_user_emails(user_id)
    if email not in emails:
        answer_callback_query(cb_id, "❌ Email tidak ditemukan")
        return
    if not check_limit(user_id):
        delete_and_send(chat_id, msg_id,
            "➕ <b>ADD NUMBER</b>\n\n"
            "❌ <b>Limit premium harian kamu sudah habis.</b>\n"
            "<blockquote>Hubungi @maklocuki untuk upgrade limit.</blockquote>")
        return
    new_msg_id = delete_and_send_with_cancel(chat_id, msg_id,
        f"➕ <b>ADD NUMBER</b>\n\n"
        f"📧 Email: <code>{email}</code>\n\n"
        f"<blockquote>✏️ Ketik range yang ingin ditambahkan:\n\n"
        f"<b>1 Range:</b>\n"
        f"<code>BENIN 851</code>\n\n"
        f"<b>Multi Range (pisah enter/koma):</b>\n"
        f"<code>BENIN 851\nMOZAMBIQUE 4234\nSAUDI ARABIA 15022</code></blockquote>",
        "an"
    )
    pending_addnum[user_id] = {"email": email, "msg_id": new_msg_id}

def _do_addnum_range(acc, session, csrf, target_text, progress_cb=None):
    """Fetch test numbers dan add untuk 1 range. Return dict hasil."""
    test_url = f"{BASE}/portal/numbers/test"
    hdrs = {
        "Accept":           "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer":          test_url,
    }

    def _fetch_test(length):
        p = {
            "draw":                   "1",
            "columns[0][data]":       "range",
            "columns[0][name]":       "terminations.range",
            "columns[1][data]":       "test_number",
            "columns[1][name]":       "terminations.test_number",
            "columns[2][data]":       "id",
            "columns[2][name]":       "id",
            "columns[3][data]":       "limit_did_a2p",
            "columns[3][name]":       "limit_did_a2p",
            "columns[4][data]":       "limit_cli_did_a2p",
            "columns[4][name]":       "limit_cli_did_a2p",
            "order[0][column]":       "0",
            "order[0][dir]":          "asc",
            "start":                  "0",
            "length":                 str(length),
            "search[value]":          target_text,
            "search[regex]":          "false",
        }
        r = session.get(test_url, params=p, headers=hdrs, timeout=20)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")
        return r.json()

    try:
        # Probe dulu untuk tahu total nomor yang tersedia (recordsFiltered)
        probe      = _fetch_test(1)
        total_avail = int(probe.get("recordsFiltered", probe.get("recordsTotal", 0)))
        # Gunakan total_avail agar semua nomor di range bisa di-fetch
        # Minimal fetch 100, maksimal 1000 agar tidak terlalu berat
        fetch_count = max(100, min(total_avail if total_avail > 0 else 1000, 1000))
        data = _fetch_test(fetch_count)
        rows = data.get("data", [])
    except Exception as e:
        return {"success": 0, "fail": 0, "skipped": False, "total": 0,
                "skip_msg": "", "not_found": False, "error": str(e)}

    fallback_fields = ["range", "test_number", "id", "limit_did_a2p", "limit_cli_did_a2p",
                       "term", "A2P", "created_at", "action"]
    rn_lower = target_text.lower().strip()
    items = []
    for row in rows:
        if isinstance(row, list):
            row = dict(zip(fallback_fields, row))
        rng = re.sub(r"<[^>]+>", "", str(row.get("range", ""))).strip()
        if rng.lower().strip() != rn_lower:
            continue
        tid = str(row.get("id", "") or row.get("DT_RowId", "")).strip()
        if tid and not tid.isdigit():
            m2 = re.search(r"(\d+)", tid)
            tid = m2.group(1) if m2 else ""
        if tid:
            items.append({"tid": tid})

    if not items:
        return {"success": 0, "fail": 0, "skipped": False, "total": 0,
                "skip_msg": "", "not_found": True, "error": None}

    add_url  = f"{BASE}/portal/numbers/termination/number/add"
    add_hdrs = {
        "Accept":           "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer":          f"{BASE}/portal/numbers/test",
        "Origin":           BASE,
        "Content-Type":     "application/x-www-form-urlencoded; charset=UTF-8",
    }

    success_count = 0
    fail_count    = 0
    skipped       = False
    skip_msg      = ""
    total_items   = len(items)
    _last_cb_at   = [0]  # track kapan terakhir kirim progress

    for idx, item in enumerate(items):
        tid = item["tid"]
        try:
            resp = session.post(add_url, data={"id": tid, "_token": csrf},
                                headers=add_hdrs, timeout=15)
            try:
                jr      = resp.json()
                message = str(jr.get("message", jr.get("msg", jr.get("error", str(jr)))))
                st      = jr.get("status", jr.get("success", ""))
                ok      = str(st).lower() in ("success", "ok", "true", "1") or st is True or st == 1
                if not ok:
                    ok = any(k in message.lower() for k in
                             ("berhasil", "success", "added", "good job", "successfully", "done"))
                if not ok and any(k in message.lower() for k in
                                  ("too many", "maximum", "limit", "penuh")):
                    skipped  = True
                    skip_msg = message
                    break
            except Exception:
                raw = resp.text.lower()
                ok  = any(k in raw for k in ("berhasil", "success", "added", "good job"))
                if any(k in raw for k in ("too many", "maximum", "limit", "penuh")):
                    skipped  = True
                    skip_msg = f"HTTP {resp.status_code}: limit tercapai"
                    break
            if ok:
                success_count += 1
            else:
                fail_count += 1
            time.sleep(0.25)
        except Exception:
            fail_count += 1

        # Kirim progress callback setiap 10 nomor atau di nomor terakhir
        done = idx + 1
        if progress_cb and (done - _last_cb_at[0] >= 10 or done == total_items):
            try:
                progress_cb(done, total_items, success_count, fail_count)
            except Exception:
                pass
            _last_cb_at[0] = done

    return {"success": success_count, "fail": fail_count, "skipped": skipped,
            "total": total_items, "skip_msg": skip_msg, "not_found": False, "error": None}


def process_addnum_target(chat_id, user_id, target_text):
    state = pending_addnum.pop(user_id, None)
    if not state:
        return False
    email  = state["email"]
    msg_id = state["msg_id"]

    # Parse multi-range: pisah per baris atau koma
    raw_ranges = re.split(r"[\n,]+", target_text)
    ranges = [r.strip() for r in raw_ranges if r.strip()]
    if not ranges:
        return False

    preview = ", ".join(f"<code>{r}</code>" for r in ranges[:3])
    if len(ranges) > 3:
        preview += f" +{len(ranges)-3} lainnya"

    proc_id = delete_and_send(chat_id, msg_id,
        f"➕ <b>ADD NUMBER</b>\n\n"
        f"<blockquote>"
        f"📧 Email: <code>{email}</code>\n"
        f"🎯 {'Range' if len(ranges) == 1 else f'{len(ranges)} Range'}: {preview}\n\n"
        f"⏳ Mencari nomor di range...</blockquote>")

    def _run():
        multi = len(ranges) > 1
        acc = None
        with accounts_lock:
            for a in accounts:
                if a.get("email") == email:
                    acc = a
                    break

        if not acc:
            delete_and_send(chat_id, proc_id,
                f"➕ <b>ADD NUMBER</b>\n\n"
                f"❌ Akun <code>{email}</code> tidak ditemukan.")
            return

        if not ensure_login(acc):
            delete_and_send(chat_id, proc_id,
                f"➕ <b>ADD NUMBER</b>\n\n"
                f"❌ Session akun <code>{email}</code> tidak aktif.\n"
                f"Gunakan /setcookie untuk memperbarui cookie.")
            return

        session = acc["session"]
        csrf    = acc.get("csrf_token", "")
        results = []

        for i, rng_target in enumerate(ranges):
            # Tampilkan status range saat ini (real-time)
            done_lines = ""
            for prev in results:
                if prev.get("error"):
                    st = "❌ Error"
                elif prev.get("not_found"):
                    st = "❌ Tdk ditemukan"
                elif prev["skipped"] and prev["success"] == 0:
                    st = "⚠️ Penuh"
                elif prev["success"] > 0:
                    st = f"✅ {prev['success']} nomor"
                else:
                    st = "❌ Gagal"
                done_lines += f"• <code>{prev['range']}</code>: {st}\n"

            if multi:
                edit_msg(chat_id, proc_id,
                    f"➕ <b>ADD NUMBER</b>\n\n"
                    f"<blockquote>"
                    f"📧 Email: <code>{email}</code>\n"
                    f"⏳ [{i+1}/{len(ranges)}] Proses: <code>{rng_target}</code>...\n"
                    + (f"\n{done_lines.strip()}" if done_lines else "")
                    + f"</blockquote>")
            else:
                edit_msg(chat_id, proc_id,
                    f"➕ <b>ADD NUMBER</b>\n\n"
                    f"<blockquote>"
                    f"📧 Email: <code>{email}</code>\n"
                    f"🎯 Range: <code>{rng_target}</code>\n\n"
                    f"⏳ Memulai add nomor...</blockquote>")

            # Progress callback — update pesan setiap 10 nomor (real-time)
            def make_progress_cb(rng_name, p_id, is_multi, i_idx, tot_ranges, d_lines):
                def _cb(done, total, ok, fail):
                    pct = int(done / total * 100) if total else 0
                    bar_filled = int(pct / 10)
                    bar = "▓" * bar_filled + "░" * (10 - bar_filled)
                    if is_multi:
                        edit_msg(chat_id, p_id,
                            f"➕ <b>ADD NUMBER</b>\n\n"
                            f"<blockquote>"
                            f"📧 Email: <code>{email}</code>\n"
                            f"⏳ [{i_idx+1}/{tot_ranges}] <code>{rng_name}</code>\n"
                            f"[{bar}] {pct}%\n"
                            f"✅ {ok} berhasil | ❌ {fail} gagal | 📊 {done}/{total}\n"
                            + (f"\n{d_lines.strip()}" if d_lines else "")
                            + f"</blockquote>")
                    else:
                        edit_msg(chat_id, p_id,
                            f"➕ <b>ADD NUMBER</b>\n\n"
                            f"<blockquote>"
                            f"📧 Email: <code>{email}</code>\n"
                            f"🎯 Range: <code>{rng_name}</code>\n\n"
                            f"[{bar}] {pct}%\n"
                            f"✅ {ok} berhasil | ❌ {fail} gagal | 📊 {done}/{total}</blockquote>")
                return _cb

            cb = make_progress_cb(rng_target, proc_id, multi, i, len(ranges), done_lines)
            r = _do_addnum_range(acc, session, csrf, rng_target, progress_cb=cb)
            results.append({"range": rng_target, **r})
            if i < len(ranges) - 1:
                time.sleep(0.5)

        if not multi:
            r = results[0]
            if r.get("error"):
                result_text = (
                    f"➕ <b>ADD NUMBER GAGAL</b>\n\n"
                    f"<blockquote>"
                    f"📧 Email: <code>{email}</code>\n"
                    f"🎯 Range: <code>{ranges[0]}</code>\n"
                    f"❌ Gagal fetch IVAS: <code>{r['error'][:100]}</code>"
                    f"</blockquote>"
                )
            elif r.get("not_found"):
                result_text = (
                    f"➕ <b>ADD NUMBER GAGAL</b>\n\n"
                    f"<blockquote>"
                    f"📧 Email: <code>{email}</code>\n"
                    f"🎯 Range: <code>{ranges[0]}</code>\n"
                    f"❌ Range tidak ditemukan di Test Numbers."
                    f"</blockquote>"
                )
            elif r["skipped"] and r["success"] == 0:
                result_text = (
                    f"➕ <b>ADD NUMBER GAGAL</b>\n\n"
                    f"<blockquote>"
                    f"📧 Email: <code>{email}</code>\n"
                    f"🎯 Range: <code>{ranges[0]}</code>\n"
                    f"⚠️ Slot nomor di range ini sudah penuh\n\n"
                    f"Hubungi admin IVAS untuk tambah kuota."
                    f"</blockquote>"
                )
            elif r["skipped"]:
                result_text = (
                    f"➕ <b>ADD NUMBER SELESAI</b>\n\n"
                    f"<blockquote>"
                    f"📧 Email: <code>{email}</code>\n"
                    f"✅ <code>{ranges[0]}</code>\n"
                    f"⚠️ Berhenti: Slot akun sudah penuh"
                    f"</blockquote>"
                )
            else:
                result_text = (
                    f"➕ <b>ADD NUMBER {'BERHASIL' if r['success'] > 0 else 'GAGAL'}</b>\n\n"
                    f"<blockquote>"
                    f"📧 Email: <code>{email}</code>\n"
                    f"{'✅' if r['success'] > 0 else '❌'} <code>{ranges[0]}</code>"
                    f"</blockquote>"
                )
        else:
            total_ok   = sum(1 for r in results if r.get("success", 0) > 0)
            total_fail = sum(1 for r in results if r.get("success", 0) == 0 and not r.get("skipped") and not r.get("error") and not r.get("not_found"))
            lines = ""
            for r in results:
                if r.get("error"):
                    status = "❌ Error fetch"
                elif r.get("not_found"):
                    status = "❌ Tidak ditemukan"
                elif r["skipped"] and r["success"] == 0:
                    status = "⚠️ Penuh"
                elif r["skipped"]:
                    status = "✅ (lalu penuh)"
                elif r["success"] > 0:
                    status = "✅"
                else:
                    status = "❌ Gagal"
                lines += f"• <code>{r['range']}</code>: {status}\n"

            result_text = (
                f"➕ <b>ADD NUMBER SELESAI</b>\n\n"
                f"<blockquote>"
                f"📧 Email: <code>{email}</code>\n"
                f"🔢 Total: ✅ <b>{total_ok}</b> berhasil | ❌ <b>{total_fail}</b> gagal\n\n"
                f"{lines.strip()}"
                f"</blockquote>"
            )

        if multi:
            edit_msg(chat_id, proc_id, result_text)
        else:
            delete_and_send(chat_id, proc_id, result_text)

    threading.Thread(target=_run, daemon=True).start()
    return True


# ================= DELNUMALL FLOW =================
def command_delnumall(text, chat_id, user_id):
    emails = get_user_emails(user_id)
    if not emails:
        return send_msg(chat_id, "❌ Belum ada email/akun.")
    buttons = [{"text": f"📧 {em}", "callback_data": f"da:{em}"} for em in emails]
    buttons.append({"text": "❌ Batalkan", "callback_data": "cancel:da"})
    send_inline_keyboard(chat_id,
        "🗑️ <b>DELETE ALL NUMBER</b>\n\n"
        "<blockquote>📋 Cara Penggunaan:\n"
        "1. Pilih email akun IVAS di bawah\n"
        "2. Bot akan otomatis return semua nomor yang aktif\n"
        "3. Tunggu konfirmasi selesai\n\n"
        "⚠️ Semua nomor akan dikembalikan ke pool IVAS!</blockquote>\n\n"
        "👇 Pilih email:",
        buttons)

def handle_delnumall_email_cb(chat_id, user_id, email, cb_id, msg_id):
    answer_callback_query(cb_id, "⏳ Memproses...")
    emails = get_user_emails(user_id)
    if email not in emails:
        delete_and_send(chat_id, msg_id,
            "🗑️ <b>DELETE ALL NUMBER</b>\n\n❌ Email tidak ditemukan.")
        return
    proc_id = delete_and_send(chat_id, msg_id,
        f"🗑️ <b>DELETE ALL NUMBER</b>\n\n"
        f"<blockquote>"
        f"📧 Email: <code>{email}</code>\n\n"
        f"⏳ Sedang menghapus semua nomor..."
        f"</blockquote>")

    acc_target = next((a for a in accounts if a["email"] == email), None)
    if not acc_target:
        prem_cookies = load_premium_cookies()
        if email not in prem_cookies:
            delete_and_send(chat_id, proc_id,
                f"🗑️ <b>DELETE ALL NUMBER</b>\n\n"
                f"<blockquote>"
                f"📧 Email: <code>{email}</code>\n"
                f"❌ Akun/cookie tidak ditemukan. Set cookie dulu."
                f"</blockquote>")
            return
        session = make_httpx_client()
        session.cookies.update(prem_cookies[email])
        acc_target = {"email": email, "session": session, "last_login": time.time(),
                      "password": "", "csrf_token": "", "cookies": prem_cookies[email]}

    if not ensure_login(acc_target):
        delete_and_send(chat_id, proc_id,
            f"🗑️ <b>DELETE ALL NUMBER</b>\n\n"
            f"<blockquote>"
            f"📧 Email: <code>{email}</code>\n"
            f"❌ Gagal login/verifikasi session. Perbarui cookie."
            f"</blockquote>")
        return

    ok, res = return_all_base(acc_target)
    if ok:
        delete_and_send(chat_id, proc_id,
            f"🗑️ <b>DELETE ALL NUMBER BERHASIL</b>\n\n"
            f"<blockquote>"
            f"📧 Email: <code>{email}</code>\n"
            f"✅ Semua nomor berhasil dikembalikan ke pool!"
            f"</blockquote>")
    else:
        delete_and_send(chat_id, proc_id,
            f"🗑️ <b>DELETE ALL NUMBER GAGAL</b>\n\n"
            f"<blockquote>"
            f"📧 Email: <code>{email}</code>\n"
            f"❌ {str(res)[:150]}"
            f"</blockquote>")

# ================= MYRANGE FLOW =================
def command_myrange(text, chat_id, user_id):
    emails = get_user_emails(user_id)
    if not emails:
        return send_msg(chat_id, "❌ Belum ada email/akun.")
    buttons = [{"text": f"📧 {em}", "callback_data": f"mr:{em}"} for em in emails]
    buttons.append({"text": "❌ Batalkan", "callback_data": "cancel:mr"})
    send_inline_keyboard(chat_id,
        "📊 <b>MY RANGE</b>\n\n"
        "<blockquote>📋 Cara Penggunaan:\n"
        "1. Pilih email akun IVAS di bawah\n"
        "2. Bot akan menampilkan semua range di My Numbers\n"
        "3. Termasuk jumlah nomor per range</blockquote>\n\n"
        "👇 Pilih email:",
        buttons)

def handle_myrange_email_cb(chat_id, user_id, email, cb_id, msg_id):
    answer_callback_query(cb_id, "⏳ Memproses...")
    emails = get_user_emails(user_id)
    if email not in emails:
        delete_and_send(chat_id, msg_id,
            "📊 <b>MY RANGE</b>\n\n❌ Email tidak ditemukan.")
        return

    proc_id = delete_and_send(chat_id, msg_id,
        f"📊 <b>MY RANGE</b>\n\n"
        f"<blockquote>"
        f"📧 Email: <code>{email}</code>\n\n"
        f"⏳ Sedang mengambil data range..."
        f"</blockquote>")

    acc_target = next((a for a in accounts if a["email"] == email), None)
    if not acc_target:
        prem_cookies = load_premium_cookies()
        if email not in prem_cookies:
            delete_and_send(chat_id, proc_id,
                f"📊 <b>MY RANGE</b>\n\n"
                f"<blockquote>"
                f"📧 Email: <code>{email}</code>\n"
                f"❌ Akun/cookie tidak ditemukan. Set cookie dulu."
                f"</blockquote>")
            return
        session = make_httpx_client()
        session.cookies.update(prem_cookies[email])
        acc_target = {"email": email, "session": session, "last_login": time.time(),
                      "password": "", "csrf_token": "", "cookies": prem_cookies[email]}

    if not ensure_login(acc_target):
        delete_and_send(chat_id, proc_id,
            f"📊 <b>MY RANGE</b>\n\n"
            f"<blockquote>"
            f"📧 Email: <code>{email}</code>\n"
            f"❌ Gagal login/verifikasi session. Perbarui cookie."
            f"</blockquote>")
        return

    try:
        BASE = "https://ivaskicen2.serverkicen.biz.id"
        my_url = f"{BASE}/portal/numbers"
        # Kolom CONFIRMED dari file referensi — harus 8 kolom
        col_data = ["Number", "range", "A2P", "LimitA2P", "limit_did_a2p", "limit_cli_a2p", "number_id", "action"]
        col_name = ["Number", "range", "A2P",  "LimitA2P", "limit_did_a2p", "limit_cli_a2p", "number_id", "action"]
        col_qs = "".join(
            f"&columns[{i}][data]={d}&columns[{i}][name]={n}"
            for i, (d, n) in enumerate(zip(col_data, col_name))
        )
        qs = (
            f"draw=1{col_qs}"
            "&order[0][column]=0&order[0][dir]=asc"
            "&start=0&length=2000"
            "&search[value]=&search[regex]=false"
        )
        hdrs = {
            "Accept":           "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer":          my_url,
        }
        session = acc_target["session"]
        resp = session.get(f"{my_url}?{qs}", headers=hdrs, timeout=20)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}")
        data = resp.json()
        rows = data.get("data", [])
        total = data.get("recordsTotal", 0)

        # Handle rows sebagai list-of-lists (convert ke dict)
        if rows and isinstance(rows[0], list):
            rows = [dict(zip(col_data, r)) for r in rows]

        from collections import Counter
        range_count = Counter()
        for row in rows:
            if isinstance(row, dict):
                rng = re.sub(r"<[^>]+>", "", str(row.get("range", ""))).strip()
                if rng:
                    range_count[rng] += 1

        if not range_count:
            delete_and_send(chat_id, proc_id,
                f"📊 <b>MY RANGE</b>\n\n"
                f"<blockquote>"
                f"📧 Email: <code>{email}</code>\n"
                f"ℹ️ Tidak ada nomor di My Numbers."
                f"</blockquote>")
            return

        lines = ""
        for i, (rng, cnt) in enumerate(sorted(range_count.items()), 1):
            lines += f"{i}. <b>{rng}</b> — {cnt} nomor\n"

        result_text = (
            f"📊 <b>MY RANGE</b>\n\n"
            f"<blockquote>"
            f"📧 Email: <code>{email}</code>\n"
            f"🔢 Total: <b>{total}</b> nomor | <b>{len(range_count)}</b> range\n\n"
            f"{lines.strip()}"
            f"</blockquote>"
        )
        delete_and_send(chat_id, proc_id, result_text)

    except Exception as ex:
        delete_and_send(chat_id, proc_id,
            f"📊 <b>MY RANGE</b>\n\n"
            f"<blockquote>"
            f"📧 Email: <code>{email}</code>\n"
            f"❌ Error: {str(ex)[:150]}"
            f"</blockquote>")

# ================= AMBILFILE FLOW =================
def command_ambilfile(text, chat_id, user_id):
    emails = get_user_emails(user_id)
    if not emails:
        return send_msg(chat_id, "❌ Belum ada email/akun.")
    buttons = [{"text": f"📧 {em}", "callback_data": f"af:{em}"} for em in emails]
    buttons.append({"text": "❌ Batalkan", "callback_data": "cancel:af"})
    send_inline_keyboard(chat_id,
        "📁 <b>AMBIL FILE</b>\n\n"
        "<blockquote>📋 Cara Penggunaan:\n"
        "1. Pilih email akun IVAS di bawah\n"
        "2. Bot akan mengambil data nomor dari IVAS\n"
        "3. File Excel (.xlsx) dikirim otomatis ke chat ini\n\n"
        "💡 File berisi semua nomor aktif beserta range/negara</blockquote>\n\n"
        "👇 Pilih email:",
        buttons)

def handle_ambilfile_email_cb(chat_id, user_id, email, cb_id, msg_id):
    answer_callback_query(cb_id, "⏳ Memproses...")
    emails = get_user_emails(user_id)
    if email not in emails:
        delete_and_send(chat_id, msg_id,
            "📁 <b>AMBIL FILE</b>\n\n❌ Email tidak ditemukan.")
        return
    proc_id = delete_and_send(chat_id, msg_id,
        f"📁 <b>AMBIL FILE</b>\n\n"
        f"<blockquote>"
        f"📧 Email: <code>{email}</code>\n\n"
        f"⏳ Sedang mengambil &amp; menyusun file export..."
        f"</blockquote>")
    export_numbers_ivas(chat_id, email, status_msg_id=proc_id)

def delete_msg(chat_id, message_id):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", data={"chat_id": chat_id, "message_id": message_id}, timeout=10)
    except: pass    

def detect_country_and_flag(full_num, fallback_country="UNKNOWN"):
    try:
        parsed = phonenumbers.parse("+" + full_num, None)
        region = phonenumbers.region_code_for_number(parsed)
        if region:
            flag = code_to_flag(region)
            country_name = geocoder.description_for_number(parsed, "en")
            if not country_name: country_name = fallback_country
            return country_name.upper(), flag
    except Exception as e: print("FLAG ERROR:", e)
    return fallback_country, "  "
    
def parse_cookie_input(raw_text):
    try:
        data = json.loads(raw_text)
        if isinstance(data, list):
            cookie_dict = {}
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookie_dict[item["name"]] = item["value"]
            return cookie_dict if cookie_dict else None
        elif isinstance(data, dict):
            return data
        return None
    except:
        return None

def verify_cookie_session(acc):
    try:
        session = acc["session"]
        r = session.get(f"{BASE}/portal", timeout=15)
        if "/login" in str(r.url):
            return False
        soup = BeautifulSoup(r.text, "html.parser")
        token_input = soup.find("input", {"name": "_token"})
        if token_input:
            acc["csrf_token"] = token_input["value"]
        return True
    except Exception as e:
        print(f"Cookie verify error: {e}")
        return False

def send_inline_keyboard(chat_id, text, buttons):
    keyboard = {"inline_keyboard": [[{"text": b["text"], "callback_data": b["callback_data"]}] for b in buttons]}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": keyboard},
            timeout=10
        )
        return r.json().get("result", {}).get("message_id")
    except:
        return None

def edit_msg(chat_id, message_id, text, remove_keyboard=False):
    try:
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
        if remove_keyboard:
            payload["reply_markup"] = {"inline_keyboard": []}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json=payload, timeout=10)
    except:
        pass

def delete_and_send(chat_id, msg_id, text):
    """Hapus pesan lama, kirim pesan baru. Return message_id baru."""
    delete_msg(chat_id, msg_id)
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        return r.json().get("result", {}).get("message_id")
    except:
        return None

def delete_and_send_keyboard(chat_id, msg_id, text, buttons):
    """Hapus pesan lama, kirim pesan baru dengan inline keyboard. Return message_id baru."""
    delete_msg(chat_id, msg_id)
    return send_inline_keyboard(chat_id, text, buttons)

def send_with_cancel(chat_id, text, cancel_key):
    """Kirim pesan baru dengan tombol ❌ Batalkan. Return message_id."""
    keyboard = {"inline_keyboard": [[{"text": "❌ Batalkan", "callback_data": f"cancel:{cancel_key}"}]]}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": keyboard},
            timeout=10
        )
        return r.json().get("result", {}).get("message_id")
    except:
        return None

def delete_and_send_with_cancel(chat_id, msg_id, text, cancel_key):
    """Hapus pesan lama, kirim pesan baru dengan tombol ❌ Batalkan. Return message_id baru."""
    delete_msg(chat_id, msg_id)
    return send_with_cancel(chat_id, text, cancel_key)

def answer_callback_query(callback_query_id, text=""):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
        data={"callback_query_id": callback_query_id, "text": text}
    )

# ================= SETCOOKIE FLOW (OWNER) =================
def cmd_setcookie(chat_id):
    if not accounts:
        send_msg(chat_id, "❌ Belum ada akun. Tambah dulu dengan /addakun")
        return
    buttons = [{"text": f"📧 {acc['email']}", "callback_data": f"setcookie:{acc['email']}"} for acc in accounts]
    buttons.append({"text": "❌ Batalkan", "callback_data": "cancel:sc"})
    send_inline_keyboard(chat_id,
        "🍪 <b>SET COOKIE — OWNER</b>\n\n"
        "<blockquote>📋 Cara Penggunaan:\n"
        "1. Pilih email akun IVAS di bawah\n"
        "2. Kirim full JSON cookie dari browser\n"
        "3. Bot akan verifikasi session otomatis\n\n"
        "💡 Export cookie: DevTools → Application → Cookies</blockquote>\n\n"
        "👇 Pilih email:",
        buttons
    )

def handle_setcookie_callback(chat_id, user_id, email, callback_query_id, msg_id):
    answer_callback_query(callback_query_id, "✅ Email dipilih!")
    new_msg_id = delete_and_send_with_cancel(chat_id, msg_id,
        f"🍪 <b>SET COOKIE — OWNER</b>\n\n"
        f"📧 Email: <code>{email}</code>\n\n"
        f"<blockquote>📤 Sekarang kirim full JSON cookie kamu.\n\n"
        f"Format array (export browser):\n"
        f"<code>[{{\"name\":\"key\",\"value\":\"val\"}}]</code>\n\n"
        f"Atau format dict:\n"
        f"<code>{{\"laravel_session\":\"...\",\"XSRF-TOKEN\":\"...\"}}</code></blockquote>",
        "sc"
    )
    pending_setcookie[user_id] = {"email": email, "msg_id": new_msg_id}

def process_cookie_input(chat_id, user_id, text):
    state = pending_setcookie.pop(user_id, None)
    if not state:
        return False

    email = state["email"]
    msg_id = state["msg_id"]

    cookie_dict = parse_cookie_input(text)
    if not cookie_dict:
        new_id = delete_and_send_with_cancel(chat_id, msg_id,
            f"🍪 <b>SET COOKIE — OWNER</b>\n\n"
            f"📧 Email: <code>{email}</code>\n\n"
            f"❌ <b>Format JSON tidak valid!</b>\n"
            f"<blockquote>Kirim ulang cookie dalam format yang benar.</blockquote>",
            "sc"
        )
        pending_setcookie[user_id] = {"email": email, "msg_id": new_id}
        return True

    proc_id = delete_and_send(chat_id, msg_id,
        f"🍪 <b>SET COOKIE — OWNER</b>\n\n"
        f"📧 Email: <code>{email}</code>\n\n"
        f"⏳ Menyimpan &amp; memverifikasi cookie..."
    )

    cookies_data = load_cookies()
    cookies_data[email] = cookie_dict
    save_cookies(cookies_data)

    found = False
    with accounts_lock:
        for acc in accounts:
            if acc["email"] == email:
                found = True
                if "session" not in acc or acc["session"] is None:
                    acc["session"] = make_httpx_client()
                acc["cookies"] = cookie_dict
                acc["session"].cookies.clear()
                acc["session"].cookies.update(cookie_dict)

                # Reset session fail flags agar run_bot tidak skip akun ini
                _session_notified[email] = False
                _session_fail_time.pop(email, None)
                _session_retry_time.pop(email, None)
                _session_recovered.pop(email, None)
                acc["last_login"] = 0  # paksa ensure_login re-verify pakai cookie baru

                if verify_cookie_session(acc):
                    acc["last_login"] = time.time()
                    delete_and_send(chat_id, proc_id,
                        f"🍪 <b>SET COOKIE — OWNER</b>\n\n"
                        f"✅ <b>Cookie berhasil disimpan!</b>\n\n"
                        f"<blockquote>"
                        f"📧 Email: <code>{email}</code>\n"
                        f"🔑 Total cookie: <b>{len(cookie_dict)}</b> key\n"
                        f"✔️ Session aktif &amp; terverifikasi"
                        f"</blockquote>"
                    )
                else:
                    delete_and_send(chat_id, proc_id,
                        f"🍪 <b>SET COOKIE — OWNER</b>\n\n"
                        f"⚠️ <b>Cookie disimpan tapi gagal verifikasi</b>\n\n"
                        f"<blockquote>"
                        f"📧 Email: <code>{email}</code>\n"
                        f"🔑 Total cookie: <b>{len(cookie_dict)}</b> key\n"
                        f"❌ Cookie mungkin expired atau salah domain"
                        f"</blockquote>"
                    )
                return True

    if not found:
        delete_and_send(chat_id, proc_id,
            f"🍪 <b>SET COOKIE — OWNER</b>\n\n"
            f"❌ Email <code>{email}</code> tidak ditemukan di daftar akun."
        )
    return True

# ================= ADDCOOKIE FLOW (PREMIUM) =================
def verify_cookie_dict(cookie_dict):
    try:
        session = make_httpx_client(timeout=15)
        session.cookies.update(cookie_dict)
        r = session.get(f"{BASE}/portal", timeout=15)
        return "/login" not in str(r.url)
    except:
        return False

def cmd_addcookie(chat_id, user_id):
    if not is_premium(user_id):
        send_msg(chat_id, "❌ Premium only")
        return
    users = load_users()
    emails = users.get(str(user_id), {}).get("emails", [])
    if not emails:
        send_msg(chat_id, "❌ Belum ada email. Tambah dulu dengan /addemail")
        return
    buttons = [{"text": f"📧 {em}", "callback_data": f"addcookie:{em}"} for em in emails]
    buttons.append({"text": "❌ Batalkan", "callback_data": "cancel:ac"})
    send_inline_keyboard(chat_id,
        "🍪 <b>ADD COOKIE — PREMIUM</b>\n\n"
        "<blockquote>📋 Cara Penggunaan:\n"
        "1. Pilih email IVAS kamu di bawah\n"
        "2. Kirim full JSON cookie dari browser\n"
        "3. Bot akan verifikasi session otomatis\n\n"
        "💡 Export cookie: DevTools → Application → Cookies</blockquote>\n\n"
        "👇 Pilih email:",
        buttons
    )

def handle_addcookie_callback(chat_id, user_id, email, callback_query_id, msg_id):
    answer_callback_query(callback_query_id, "✅ Email dipilih!")
    users = load_users()
    emails = users.get(str(user_id), {}).get("emails", [])
    if email not in emails:
        answer_callback_query(callback_query_id, "❌ Email tidak ditemukan")
        return
    new_msg_id = delete_and_send_with_cancel(chat_id, msg_id,
        f"🍪 <b>ADD COOKIE — PREMIUM</b>\n\n"
        f"📧 Email: <code>{email}</code>\n\n"
        f"<blockquote>📤 Sekarang kirim full JSON cookie kamu.\n\n"
        f"Format array (export browser):\n"
        f"<code>[{{\"name\":\"key\",\"value\":\"val\"}}]</code>\n\n"
        f"Atau format dict:\n"
        f"<code>{{\"laravel_session\":\"...\",\"XSRF-TOKEN\":\"...\"}}</code></blockquote>",
        "ac"
    )
    pending_addcookie[user_id] = {"email": email, "msg_id": new_msg_id}

def process_addcookie_input(chat_id, user_id, text):
    state = pending_addcookie.pop(user_id, None)
    if not state:
        return False

    email = state["email"]
    msg_id = state["msg_id"]

    cookie_dict = parse_cookie_input(text)
    if not cookie_dict:
        new_id = delete_and_send_with_cancel(chat_id, msg_id,
            f"🍪 <b>ADD COOKIE — PREMIUM</b>\n\n"
            f"📧 Email: <code>{email}</code>\n\n"
            f"❌ <b>Format JSON tidak valid!</b>\n"
            f"<blockquote>Kirim ulang cookie dalam format yang benar.</blockquote>",
            "ac"
        )
        pending_addcookie[user_id] = {"email": email, "msg_id": new_id}
        return True

    proc_id = delete_and_send(chat_id, msg_id,
        f"🍪 <b>ADD COOKIE — PREMIUM</b>\n\n"
        f"📧 Email: <code>{email}</code>\n\n"
        f"⏳ Menyimpan &amp; memverifikasi cookie..."
    )

    try:
        prem_cookies = load_premium_cookies()
        prem_cookies[email] = cookie_dict
        save_premium_cookies(prem_cookies)

        valid = verify_cookie_dict(cookie_dict)

        if valid:
            delete_and_send(chat_id, proc_id,
                f"🍪 <b>ADD COOKIE — PREMIUM</b>\n\n"
                f"✅ <b>Cookie berhasil disimpan!</b>\n\n"
                f"<blockquote>"
                f"📧 Email: <code>{email}</code>\n"
                f"🔑 Total cookie: <b>{len(cookie_dict)}</b> key\n"
                f"✔️ Session aktif &amp; terverifikasi"
                f"</blockquote>"
            )
        else:
            delete_and_send(chat_id, proc_id,
                f"🍪 <b>ADD COOKIE — PREMIUM</b>\n\n"
                f"⚠️ <b>Cookie disimpan tapi gagal verifikasi</b>\n\n"
                f"<blockquote>"
                f"📧 Email: <code>{email}</code>\n"
                f"🔑 Total cookie: <b>{len(cookie_dict)}</b> key\n"
                f"❌ Cookie mungkin expired atau salah domain"
                f"</blockquote>"
            )
    except Exception as e:
        delete_and_send(chat_id, proc_id,
            f"🍪 <b>ADD COOKIE — PREMIUM</b>\n\n"
            f"❌ Error saat menyimpan cookie: <code>{e}</code>"
        )
    return True

def ensure_login(acc):
    now = time.time()
    email = acc.get("email", "")
    if now - acc.get("last_login", 0) < LOGIN_COOLDOWN:
        return True

    print(f"  CEK SESSION : {email}")

    if acc.get("cookies"):
        if "session" not in acc or acc["session"] is None:
            acc["session"] = make_httpx_client()
        acc["session"].cookies.clear()
        acc["session"].cookies.update(acc["cookies"])
        if verify_cookie_session(acc):
            acc["last_login"] = now
            print(f"  SESSION VIA COOKIE OK : {email}")
            if _session_notified.get(email):
                _session_notified[email] = False
                _session_fail_time.pop(email, None)
                _session_retry_time.pop(email, None)
                if not _session_recovered.get(email):
                    _session_recovered[email] = True
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        data={"chat_id": OWNER_ID, "text": f"✅ <b>SESSION PULIH</b>\n\n📧 Email: <code>{email}</code>\nSession berhasil aktif kembali secara otomatis.", "parse_mode": "HTML"},
                        timeout=10
                    )
            return True
        print(f"  COOKIE EXPIRED, COBA LOGIN PASSWORD : {email}")

    if login(acc):
        acc["last_login"] = now
        if _session_notified.get(email):
            _session_notified[email] = False
            _session_fail_time.pop(email, None)
            _session_retry_time.pop(email, None)
            if not _session_recovered.get(email):
                _session_recovered[email] = True
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={"chat_id": OWNER_ID, "text": f"✅ <b>SESSION PULIH</b>\n\n📧 Email: <code>{email}</code>\nLogin password berhasil, session aktif kembali.", "parse_mode": "HTML"},
                    timeout=10
                )
        return True

    if not _session_notified.get(email):
        _session_notified[email] = True
        _session_recovered[email] = False
        _session_fail_time[email] = now
        print(f"  SESSION GAGAL, NOTIF OWNER : {email}")
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": OWNER_ID,
                "text": (
                    f"⚠️ <b>SESSION EXPIRED</b>\n\n"
                    f"📧 Email: <code>{email}</code>\n"
                    f"❌ Cookie expired & login password gagal.\n\n"
                    f"Bot akan otomatis retry setiap 10 menit.\n"
                    f"Perbarui cookie dengan /setcookie atau /addcookie."
                ),
                "parse_mode": "HTML"
            },
            timeout=10
        )

    _session_retry_time[email] = now
    return False
 
def cek_ivas(chat_id=None):
    try:
        url = "http://ws.websocket.web.id/api/cekivas?platform=whatsapp"
        r = requests.get(url, timeout=10)
        send_to = chat_id if chat_id else OWNER_ID
        if r.status_code != 200: return send_msg(send_to, "  Gagal ambil data IVAS")
        data = r.json()
        if not data.get("success"): return send_msg(send_to, "  API gagal")
        results = data.get("results", [])
        if not results: return send_msg(send_to, "   Tidak ada data IVAS")

        results = sorted(results, key=lambda x: x["count"], reverse=True)
        msg = "  <b>CEK IVAS WHATSAPP</b>\n\n"
        for i, item in enumerate(results, 1):
            msg += f"{i}. {item.get('country', 'Unknown').upper()} : {item.get('count', 0)} SMS\n"
        send_msg(send_to, msg)
    except Exception as e:
        send_to = chat_id if chat_id else OWNER_ID
        send_msg(send_to, f"  Error cek IVAS: {e}")

# ================= UTILS =================
def extract_otp(text):
    m = re.search(r"\b(\d{3}[- ]?\d{3})\b", text)
    if not m: return None
    otp = m.group(0).replace(" ", "")  
    if len(otp) not in (6, 7): return None
    if len(otp) == 6: otp = otp[:3] + "-" + otp[3:]
    return otp    
        
def return_all_base(acc):
    try:
        session = acc["session"]
        url = RETURN_ALL_URL
        headers = {"X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE}/portal/numbers", "Origin": BASE}
        r = session.post(url, headers=headers, data={"_token": acc.get("csrf_token", "")})
        if r.status_code == 200: return True, r.text
        else: return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)
        
def parse_range(rng):
    country = re.sub(r"\s*\(.*?\)", "", rng)
    country = re.sub(r"\d+", "", country)
    country = re.sub(r"\s+", " ", country).strip().upper()
    code_match = re.search(r"\((\d+)\)", rng)
    code = code_match.group(1) if code_match else ""
    return country, code

def extract_service_short(text):
    m = re.search(r"(WhatsApp|Telegram|Google|Facebook|Instagram|Shopee|Tokopedia|Grab|Gojek|TikTok)", text, re.I)
    if m: return SERVICE_SHORT.get(m.group(1).upper(), "#OT")
    return "#OT"

def mask_email(email):
    try:
        name, domain = email.split("@")
        if len(name) <= 2: return name + "*" + "@" + domain
        return f"{name[0]}{'*' * (len(name)-2)}{name[-1]}@{domain}"
    except:
        return email

def stats_sms():
    total_sms = sms_stats["total_sms"]
    total_otp = sms_stats["total_otp"]
    total_number = len(sms_stats["total_number"])
    msg = f"  <b>STATISTIK SMS OTP</b>\n\n  Total SMS Masuk : {total_sms}\n  Total OTP       : {total_otp}\n  Total Nomor     : {total_number}\n  Total Akun Aktif: {len(accounts)}\n"
    tg_active(msg)                        

def login(acc):
    session = acc["session"]
    email = acc["email"]
    password = acc["password"]

    r = session.get(LOGIN_URL)
    soup = BeautifulSoup(r.text, "html.parser")
    token_input = soup.find("input", {"name": "_token"})

    if not token_input:
        print("  CSRF TOKEN TIDAK DITEMUKAN")
        return False

    token = token_input["value"]
    acc["csrf_token"] = token

    session.headers.update({
        "X-CSRF-TOKEN": token,
        "X-Requested-With": "XMLHttpRequest"
    })

    r2 = session.post(LOGIN_URL, data={
        "_token": token,
        "email": email,
        "password": password
    })

    print("LOGIN RESPONSE URL:", r2.url)

    if "/portal" in str(r2.url) or "Dashboard" in r2.text or "portal" in r2.text.lower():
        print("  LOGIN BERHASIL")
        return True
    else:
        print("  LOGIN GAGAL")
        return False

def get_ranges(acc):
    today = datetime.now().strftime("%Y-%m-%d")
    r = acc["session"].post(GET_RANGE_URL, data={
        "_token": acc.get("csrf_token", ""),
        "from": today,
        "to": today
    })
    soup = BeautifulSoup(r.text, "html.parser")
    ranges = []
    for div in soup.find_all("div", onclick=True):
        if "toggleRange" in div["onclick"]:
            try: ranges.append(div["onclick"].split("'")[1])
            except: pass
    return list(set(ranges))

def get_numbers(acc, rng):
    today = datetime.now().strftime("%Y-%m-%d")
    r = acc["session"].post(GET_NUMBER_URL, data={
        "_token": acc.get("csrf_token", ""),
        "start": today, 
        "end": today, 
        "range": rng
    })
    soup = BeautifulSoup(r.text, "html.parser")
    numbers = []
    for div in soup.find_all("div", onclick=True):
        try:
            val = div["onclick"].split("'")[1]
            if val and val != rng: numbers.append(val)
        except: pass
    return list(set(numbers))

def get_sms(acc, rng, number):  
    today = datetime.now().strftime("%Y-%m-%d")  
    r = acc["session"].post(GET_SMS_URL, data={  
        "_token": acc.get("csrf_token", ""),
        "start": today,  
        "end": today,  
        "Number": number,  
        "Range": rng  
    })  
    soup = BeautifulSoup(r.text, "html.parser")  
    sms_texts = []  
    try:  
        texts = list(soup.stripped_strings)  
        for t in texts:  
            t = t.strip()  
            if t.startswith("<#>"): t = t.replace("<#>", "").strip()  
            if re.fullmatch(r"[A-Za-z0-9]{10,}", t): continue  
            t_low = t.lower()  
            if any(x in t_low for x in ["sender", "revenue", "time"]): continue  
            if re.search(r"\b\d{2}:\d{2}:\d{2}\b", t): continue  
            if "$" in t: continue  
            if t and "No SMS Found" not in t: sms_texts.append(t)  
    except Exception as e: print("ERROR PARSE SMS:", e)  
    return list(dict.fromkeys(sms_texts))  
    
def format_phone_number(number):
    number = str(number).replace("+", "").replace(" ", "")
    if len(number) >= 10:
        return f"{number[:4]}****{number[-4:]}"
    return number    
    
def normalize_number(num, country_code):
    num = str(num).strip().replace(" ", "").replace("-", "").replace("+", "")
    if num.startswith(country_code): return num
    if num.startswith("0"): return country_code + num[1:]
    return num

def tg_active(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": OWNER_ID, "text": msg, "parse_mode": "HTML"})
            
# ================= TELEGRAM LISTENER =================
def listen_command():
    global last_update_id
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            r = httpx.get(url, params={"offset": last_update_id + 1, "timeout": 25}, timeout=30)
            data = r.json()

            for upd in data.get("result", []):
                last_update_id = upd["update_id"]

                # ====== HANDLE CALLBACK QUERY (inline button click) ======
                if "callback_query" in upd:
                    try:
                        cq = upd["callback_query"]
                        cq_id = cq["id"]
                        cq_data = cq.get("data", "")
                        cq_user_id = cq["from"]["id"]
                        cq_chat_id = cq["message"]["chat"]["id"]
                        cq_msg_id = cq["message"]["message_id"]

                        if cq_data.startswith("setcookie:"):
                            if is_owner(cq_user_id):
                                handle_setcookie_callback(cq_chat_id, cq_user_id, cq_data[len("setcookie:"):], cq_id, cq_msg_id)
                            else:
                                answer_callback_query(cq_id, "❌ Khusus OWNER")
                        elif cq_data.startswith("addcookie:"):
                            if is_premium(cq_user_id):
                                handle_addcookie_callback(cq_chat_id, cq_user_id, cq_data[len("addcookie:"):], cq_id, cq_msg_id)
                            else:
                                answer_callback_query(cq_id, "❌ Premium only")
                        elif cq_data.startswith("an:"):
                            if is_premium(cq_user_id):
                                handle_addnum_email_cb(cq_chat_id, cq_user_id, cq_data[3:], cq_id, cq_msg_id)
                            else:
                                answer_callback_query(cq_id, "❌ Premium only")
                        elif cq_data.startswith("da:"):
                            if is_premium(cq_user_id):
                                threading.Thread(target=handle_delnumall_email_cb, args=(cq_chat_id, cq_user_id, cq_data[3:], cq_id, cq_msg_id), daemon=True).start()
                            else:
                                answer_callback_query(cq_id, "❌ Premium only")
                        elif cq_data.startswith("af:"):
                            if is_premium(cq_user_id):
                                threading.Thread(target=handle_ambilfile_email_cb, args=(cq_chat_id, cq_user_id, cq_data[3:], cq_id, cq_msg_id), daemon=True).start()
                            else:
                                answer_callback_query(cq_id, "❌ Premium only")
                        elif cq_data.startswith("mr:"):
                            if is_premium(cq_user_id):
                                threading.Thread(target=handle_myrange_email_cb, args=(cq_chat_id, cq_user_id, cq_data[3:], cq_id, cq_msg_id), daemon=True).start()
                            else:
                                answer_callback_query(cq_id, "❌ Premium only")
                        elif cq_data.startswith("cancel:"):
                            answer_callback_query(cq_id, "❌ Dibatalkan")
                            key = cq_data[7:]
                            if key == "sc":
                                pending_setcookie.pop(cq_user_id, None)
                            elif key == "ac":
                                pending_addcookie.pop(cq_user_id, None)
                            elif key == "an":
                                pending_addnum.pop(cq_user_id, None)
                            delete_msg(cq_chat_id, cq_msg_id)
                            send_msg(cq_chat_id, "❌ <b>Aksi dibatalkan.</b>")
                        else:
                            answer_callback_query(cq_id)
                    except Exception as ex:
                        print(f"Error callback_query: {ex}")
                    continue

                if "message" not in upd: continue
                try:
                    msg = upd["message"]
                    text = msg.get("text", "") or ""
                    user_id = msg["from"]["id"]
                    chat_id = msg["chat"]["id"]
                    msg_id = msg["message_id"]

                    owner = is_owner(user_id)
                    is_group = msg["chat"]["type"] in ["group", "supergroup"]

                    # ====== CEK PENDING SETCOOKIE (owner input cookie JSON) ======
                    if owner and user_id in pending_setcookie and text and not text.startswith("/"):
                        if process_cookie_input(chat_id, user_id, text):
                            continue

                    # ====== CEK PENDING ADDCOOKIE (premium input cookie JSON) ======
                    if is_premium(user_id) and user_id in pending_addcookie and text and not text.startswith("/"):
                        if process_addcookie_input(chat_id, user_id, text):
                            continue

                    # ====== CEK PENDING ADDNUM (premium/owner input target) ======
                    if is_premium(user_id) and user_id in pending_addnum and text and not text.startswith("/"):
                        if process_addnum_target(chat_id, user_id, text):
                            continue

                    # ROUTING COMMAND TEXT
                    if text == "/start": handle_start(user_id, chat_id)
                    elif text.startswith("/cekivas"): cek_ivas(chat_id)
                    elif text.startswith("/cekprem"): cek_premium(chat_id, user_id)
                    
                    elif text.startswith("/listakun"): 
                        if owner: list_accounts(chat_id, user_id)
                        else: send_msg(chat_id, "  Khusus OWNER")
                    elif text.startswith("/addcookie"): add_cookie_premium(text, chat_id, user_id)
                    elif text.startswith("/delcookie"): del_cookie_premium(text, chat_id, user_id)
                    
                    elif text.startswith("/addemail"): 
                        if is_premium(user_id): add_email(text, chat_id, user_id, msg_id)
                        else: send_msg(chat_id, "  Premium only")
                    elif text.startswith("/listemail"): list_email(chat_id, user_id)
                    
                    elif text.startswith("/addgrup"):
                        if is_group:
                            gid = str(chat_id)
                            if gid in groups: send_msg(chat_id, "  Grup sudah ada")
                            else:
                                groups.append(gid)
                                save_groups()
                                send_msg(chat_id, f"  Grup ditambahkan:\n{gid}")
                        else: send_msg(chat_id, "  Jalankan di dalam grup!")

                    elif text.startswith("/delgrup"):
                        gid = str(chat_id)
                        if gid in groups:
                            groups.remove(gid)
                            save_groups()
                            send_msg(chat_id, f"  Grup dihapus:\n{gid}")
                        else: send_msg(chat_id, "  Grup tidak ditemukan")

                    elif text.startswith("/listgrup"):
                        if not groups: send_msg(chat_id, "Belum ada grup")
                        else:
                            msg_out = "  <b>LIST GRUP</b>\n\n"
                            for i, g in enumerate(groups, 1): msg_out += f"{i}. {g}\n"
                            send_msg(chat_id, msg_out)

                    elif text.startswith("/addnum"): 
                        if is_premium(user_id): command_addnum(text, chat_id, user_id)
                        else: send_msg(chat_id, "❌ Premium only")
                        
                    elif text.startswith("/ambilfile"):
                        if is_premium(user_id): command_ambilfile(text, chat_id, user_id)
                        else: send_msg(chat_id, "❌ Premium only")

                    elif text.startswith("/delnumall"): 
                        if is_premium(user_id): command_delnumall(text, chat_id, user_id)
                        else: send_msg(chat_id, "❌ Premium only")

                    elif text.startswith("/myrange"):
                        if is_premium(user_id): command_myrange(text, chat_id, user_id)
                        else: send_msg(chat_id, "❌ Premium only")
                    
                    elif text.startswith("/addprem"): 
                        if owner: add_premium(text, chat_id) 
                        else: send_msg(chat_id, "  Khusus OWNER")
                    elif text.startswith("/delprem"): 
                        if owner: del_premium(text, chat_id) 
                        else: send_msg(chat_id, "  Khusus OWNER")
                    elif text.startswith("/listprem"): 
                        if owner: list_premium(chat_id) 
                        else: send_msg(chat_id, "  Khusus OWNER")
                    elif text.startswith("/addakun"): 
                        if owner: add_account(text) 
                        else: send_msg(chat_id, "  Khusus OWNER")
                    elif text.startswith("/delakun"): 
                        if owner: del_account(text) 
                        else: send_msg(chat_id, "  Khusus OWNER")
                    elif text.startswith("/setcookie"): 
                        if owner: cmd_setcookie(chat_id)
                        else: send_msg(chat_id, "  Khusus OWNER")
                    elif text.startswith("/statsms"): 
                        if owner: stats_sms() 
                        else: send_msg(chat_id, "  Khusus OWNER")
                except Exception as ex: 
                    print(f"Error handling message: {ex}")
            time.sleep(2)
        except Exception as e: 
            print(f"Loop listener error: {e}")
            time.sleep(5)

def send_audio_otp(otp, clean_sms, msg):
    try:
        angka_map = {"0": "nol", "1": "satu", "2": "dua", "3": "tiga", "4": "empat", "5": "lima", "6": "enam", "7": "tujuh", "8": "delapan", "9": "sembilan"}
        result = ["strip" if c == "-" else angka_map.get(c, c) for c in otp]
        text = "Kode verifikasi WhatsApp anda adalah " + " ".join(result)

        tts = gTTS(text=text, lang="id")
        filename = "voice/MyAudioOtp.mp3"
        os.makedirs("voice", exist_ok=True)
        tts.save(filename)

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"

        for gid in groups:
            with open(filename, "rb") as f:
                requests.post(url, data={"chat_id": gid, "caption": msg, "parse_mode": "HTML"}, files={"audio": f})
    except Exception as e:
        print("ERROR AUDIO:", e)
            
# ================= BOT LOOP =================
def run_bot():
    while True:
        try:
            with accounts_lock: current_accounts = list(accounts)
            total_accounts = len(current_accounts)

            for acc in current_accounts:
                email = acc.get("email")
                if not email: continue

                if _session_notified.get(email):
                    last_retry = _session_retry_time.get(email, 0)
                    if time.time() - last_retry < SESSION_RETRY_INTERVAL:
                        continue
                    print(f"  AUTO-RETRY SESSION : {email}")
                    acc["last_login"] = 0

                if not ensure_login(acc): continue

                ranges = get_ranges(acc)
                for rng in ranges:
                    fallback_country, code = parse_range(rng)
                    numbers = get_numbers(acc, rng)

                    for num in numbers:
                        full_num = normalize_number(num, code)
                        if not full_num.isdigit(): continue

                        country, flag = detect_country_and_flag(full_num, fallback_country)
                        sms_list = get_sms(acc, rng, num)

                        for sms in sms_list:
                            clean_sms = re.sub(r"\s+", " ", sms.replace("<#>", "")).strip()
                            sms_uid = hashlib.md5(f"{num}-{clean_sms}".encode()).hexdigest()
                            if sms_uid in sent_cache:
                                continue

                            matches = re.findall(r"\b\d{3}[- ]?\d{3}\b", sms)
                            if not matches:
                                continue

                            otp = matches[0].replace(" ", "-")
                            clean_sms_display = clean_sms[:300]

                            masked_num = format_phone_number(full_num)
                            service_name = extract_service_short(sms)
                            country, flag = detect_country_and_flag(full_num, fallback_country)

                            msg = (
                                f"<b>🔔 OTP BARU DITERIMA!</b>\n\n"
                                f"<blockquote><b>📱 Nomor :</b> <code>{masked_num}</code></blockquote>\n"
                                f"<b>🔑 OTP :</b> <code>{otp}</code>\n"
                                f"<blockquote><b>🛒 Service :</b> {service_name}</blockquote>\n"
                                f"<blockquote><b>🌍 Negara :</b> {country} {flag}</blockquote>\n"
                                f"<blockquote><b>📧 Email :</b> {mask_email(email)}</blockquote>\n"
                                f"<blockquote><b>📊 Total Aktif :</b> {total_accounts} Akun</blockquote>\n\n"
                                f"💬 <b>Pesan:</b>\n"
                                f"<code>{clean_sms_display}</code>"
                            )

                            for gid in groups:
                                try:
                                    requests.post(
                                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                        data={"chat_id": gid, "text": msg, "parse_mode": "HTML"},
                                        timeout=10
                                    )
                                except:
                                    pass

                            sent_cache.add(sms_uid)
                            save_sent_cache()
                            sms_stats["total_sms"] += 1
                            sms_stats["total_otp"] += 1
                            sms_stats["total_number"].add(full_num)

                            print(Fore.GREEN + f"OTP TERKIRIM | {masked_num} | {otp}")

            time.sleep(1)
        except Exception as e:
            print(Fore.RED + f"ERROR BOT: {e}")
            time.sleep(1)

            
# ================= KEEP-ALIVE SERVER =================
from http.server import HTTPServer, BaseHTTPRequestHandler

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args):
        pass

def run_keepalive():
    HTTPServer.allow_reuse_address = True
    server = HTTPServer(("0.0.0.0", 5000), KeepAliveHandler)
    server.serve_forever()

# ================= START BOT =================
threading.Thread(target=run_keepalive, daemon=True).start()
threading.Thread(target=listen_command, daemon=True).start()
run_bot()
