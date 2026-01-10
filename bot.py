import telebot
import subprocess
import time

TOKEN = "8206837693:AAGQB86CiT7g2wZOFg73daDA4Jg4MMZWE8c"

# 👑 DAFTAR USER YANG BOLEH MENGGUNAKAN BOT
# Tambahkan ID Telegram siapa saja di sini
ALLOWED_USERS = [
    6095762919,   # kamu
    8458676120,   # user lain
]

bot = telebot.TeleBot(TOKEN)

# SESSION LOGIN
sessions = {}
TIMEOUT = 60  # detik

def is_allowed(message):
    return message.from_user.id in ALLOWED_USERS

def deny(message):
    bot.reply_to(message, "⛔ Kamu tidak diizinkan menggunakan bot ini")

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    if not is_allowed(message):
        deny(message)
        return

    bot.reply_to(
        message,
        "🤖 Bot Rank King CPM Aktif\n\n"
        "📌 Command:\n"
        "/rankcpm1\n"
        "/rankcpm2"
    )

# ================= CPM1 =================
@bot.message_handler(commands=['rankcpm1'])
def cpm1_start(message):
    if not is_allowed(message):
        deny(message)
        return

    sessions[message.from_user.id] = {
        "step": "email",
        "tool": "cpm1",
        "time": time.time()
    }

    bot.reply_to(message, "📧 Masukkan EMAIL CPM1:")

# ================= CPM2 =================
@bot.message_handler(commands=['rankcpm2'])
def cpm2_start(message):
    if not is_allowed(message):
        deny(message)
        return

    sessions[message.from_user.id] = {
        "step": "email",
        "tool": "cpm2",
        "time": time.time()
    }

    bot.reply_to(message, "📧 Masukkan EMAIL CPM2:")

# ================= LOGIN FLOW =================
@bot.message_handler(func=lambda m: m.from_user.id in sessions)
def login_flow(message):
    user_id = message.from_user.id
    sess = sessions[user_id]

    # timeout
    if time.time() - sess["time"] > TIMEOUT:
        del sessions[user_id]
        bot.reply_to(message, "⌛ Waktu login habis, ulangi command.")
        return

    if sess["step"] == "email":
        sess["email"] = message.text
        sess["step"] = "password"
        sess["time"] = time.time()
        bot.reply_to(message, "🔒 Masukkan PASSWORD:")
        return

    if sess["step"] == "password":
        password = message.text
        email = sess["email"]
        tool = sess["tool"]

        del sessions[user_id]

        bot.reply_to(message, "🔐 Logging in, mohon tunggu...")

        script = "cpm1.py" if tool == "cpm1" else "cpm2.py"
        cmd = f'printf "{email}\\n{password}\\n" | python {script}'

        try:
            result = subprocess.getoutput(cmd)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error:\n{e}")
            return

        # batasi output panjang
        if len(result) > 3500:
            with open("result.txt", "w") as f:
                f.write(result)
            with open("result.txt", "rb") as f:
                bot.send_document(message.chat.id, f)
        else:
            bot.send_message(message.chat.id, result)

print("🤖 Bot berjalan | Login via Telegram")
bot.infinity_polling()
