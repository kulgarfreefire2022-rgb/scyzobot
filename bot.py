import telebot
import subprocess

TOKEN = "8206837693:AAGQB86CiT7g2wZOFg73daDA4Jg4MMZWE8c"

# 👑 DAFTAR USER YANG BOLEH MENGGUNAKAN BOT
# Tambahkan ID Telegram siapa saja di sini
ALLOWED_USERS = [
    6095762919,   # kamu
    8458676120,   # user lain
]

bot = telebot.TeleBot(TOKEN)

def is_allowed(message):
    return message.from_user.id in ALLOWED_USERS

def deny(message):
    bot.reply_to(message, "⛔ Kamu tidak diizinkan menggunakan bot ini")

@bot.message_handler(commands=['start'])
def start(message):
    if not is_allowed(message):
        deny(message)
        return

    bot.reply_to(
        message,
        "🤖 Bot Rank King CPM Aktif\n\n"
        "👑 Mode:USER\n\n"
        "📌 Command:\n"
        "/rankcpm1\n"
        "/rankcpm2"
    )

@bot.message_handler(commands=['rankcpm1'])
def rankcpm1(message):
    if not is_allowed(message):
        deny(message)
        return

    bot.reply_to(message, "⏳ Menjalankan Rank King CPM 1...")
    result = subprocess.getoutput("python cpm1.py")
    bot.send_message(message.chat.id, f"✅ Hasil CPM1:\n{result}")

@bot.message_handler(commands=['rankcpm2'])
def rankcpm2(message):
    if not is_allowed(message):
        deny(message)
        return

    bot.reply_to(message, "⏳ Menjalankan Rank King CPM 2...")
    result = subprocess.getoutput("python cpm2.py")
    bot.send_message(message.chat.id, f"✅ Hasil CPM2:\n{result}")

print("🤖 Bot berjalan")
bot.infinity_polling()
