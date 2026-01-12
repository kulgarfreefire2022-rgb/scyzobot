import telebot
import subprocess
import time
import json
import os
import requests
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= KONFIGURASI =================
TOKEN = "8206837693:AAEqLu_sWDCXGZzdV3HcxEakWh6gJraXzcM"

OWNER_ID = 6095762919  # OWNER UTAMA (1 ORANG)

TIMEOUT = 300

LIMIT_FILE = "usage_limit.json"
LOGIN_FILE = "profile_login.json"
PREMIUM_FILE = "premium_users.json"
ADMINS_FILE = "admins.json"
PURCHASE_LOG = "purchase_log.json"
EXPIRE_NOTIFY_FILE = "expire_notify.json"

bot = telebot.TeleBot(TOKEN)
sessions = {}

# ================= JSON UTILS =================
def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

usage_data = load_json(LIMIT_FILE, {})
premium_users = load_json(PREMIUM_FILE, {})
admins = load_json(ADMINS_FILE, [])
expire_notified = load_json(EXPIRE_NOTIFY_FILE, {})

# ================= ROLE =================
def is_owner(uid):
    return uid == OWNER_ID

def is_admin(uid):
    return uid in admins or is_owner(uid)

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
    days = max((expire - datetime.now()).days, 0)
    return f"💎 PREMIUM ({days} hari)"

# ================= FREE LIMIT (1x / BULAN) =================
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

    return usage_data[uid]["count"] < 1

def increase_usage(uid):
    uid = str(uid)
    usage_data[uid]["count"] += 1
    save_json(LIMIT_FILE, usage_data)

def remaining(uid):
    if is_premium(uid):
        return "♾ Unlimited"
    uid = str(uid)
    return f"{1 - usage_data.get(uid, {'count':0})['count']}x"

# ================= NOTIF =================
def notify_owner_admin_add_premium(admin_id, uid, ptype, expire):
    try:
        text = (
            "🔔 *ADMIN ADD PREMIUM*\n\n"
            f"👤 User: `{uid}`\n"
            f"💎 Type: *{ptype}*\n"
            f"⏳ Expire: *{expire if expire else 'UNLIMITED'}*\n"
            f"🛠 Admin ID: `{admin_id}`"
        )
        bot.send_message(OWNER_ID, text, parse_mode="Markdown")
    except:
        pass

def notify_user_premium(uid, ptype, expire):
    try:
        text = (
            "🎉 *PREMIUM AKTIF* 🎉\n\n"
            f"💎 Type: *{ptype.upper()}*\n"
            f"⏳ Expire: *{expire if expire else 'UNLIMITED'}*\n\n"
            "Terima kasih telah membeli / memperpanjang premium 🙏"
        )
        bot.send_message(int(uid), text, parse_mode="Markdown")
    except:
        pass

def notify_user_expire_soon(uid, ptype, expire):
    try:
        text = (
            "⏰ *PREMIUM AKAN HABIS (H-1)* ⏰\n\n"
            f"💎 Type: *{ptype.upper()}*\n"
            f"⏳ Expire: *{expire}*\n\n"
            "Segera perpanjang agar tetap bisa menggunakan fitur premium 🙏"
        )
        bot.send_message(int(uid), text, parse_mode="Markdown")
    except:
        pass

# ================= AUTO CEK EXPIRED =================
def expire_checker():
    while True:
        try:
            now = datetime.now().date()
            for uid, info in premium_users.items():
                if info["type"] == "unlimited":
                    continue

                exp = datetime.strptime(info["expire"], "%Y-%m-%d").date()
                days = (exp - now).days

                if days == 1:
                    key = f"{uid}_{info['expire']}"
                    if key not in expire_notified:
                        notify_user_expire_soon(uid, info["type"], info["expire"])
                        expire_notified[key] = True
                        save_json(EXPIRE_NOTIFY_FILE, expire_notified)

        except:
            pass

        time.sleep(3600)

# ================= MENU =================
def main_menu(uid):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🚘 CPM 1", callback_data="menu_cpm1"),
        InlineKeyboardButton("🚖 CPM 2", callback_data="menu_cpm2")
    )
    if is_admin(uid):
        kb.add(InlineKeyboardButton("⚙️ ADMIN PANEL", callback_data="admin_panel"))
    if is_owner(uid):
        kb.add(InlineKeyboardButton("👑 OWNER PANEL", callback_data="owner_panel"))
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("➕ Premium 7 Day", callback_data="add_7day"),
        InlineKeyboardButton("➕ Premium 1 Month", callback_data="add_1month"),
        InlineKeyboardButton("➕ Unlimited", callback_data="add_unli"),
        InlineKeyboardButton("⬅️ Back", callback_data="back")
    )
    return kb

def owner_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("➕ Add Admin", callback_data="owner_add_admin"),
        InlineKeyboardButton("❌ Del Admin", callback_data="owner_del_admin"),
        InlineKeyboardButton("📋 List Admin", callback_data="owner_list_admin"),
        InlineKeyboardButton("➕ Premium 7 Day", callback_data="owner_add_7day"),
        InlineKeyboardButton("➕ Premium 1 Month", callback_data="owner_add_1month"),
        InlineKeyboardButton("➕ Unlimited", callback_data="owner_add_unli"),
        InlineKeyboardButton("⬅️ Back", callback_data="back")
    )
    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    bot.send_message(
        message.chat.id,
        f"⭐ *RANK KING CPM BOT*\n\n"
        f"Status: *{premium_status(uid)}*\n"
        f"Sisa Limit: *{remaining(uid)}*\n\n"
        "Pilih menu di bawah 👇",
        reply_markup=main_menu(uid),
        parse_mode="Markdown"
    )

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id

    if call.data == "admin_panel" and is_admin(uid):
        bot.edit_message_text("⚙️ ADMIN PANEL", call.message.chat.id,
                              call.message.message_id,
                              reply_markup=admin_menu(), parse_mode="Markdown")

    elif call.data == "owner_panel" and is_owner(uid):
        bot.edit_message_text("👑 OWNER PANEL", call.message.chat.id,
                              call.message.message_id,
                              reply_markup=owner_menu(), parse_mode="Markdown")

    elif call.data.startswith(("add_", "owner_add_")) and is_admin(uid):
        sessions[uid] = {"step": call.data, "time": time.time()}
        bot.send_message(call.message.chat.id, "Masukkan UID Telegram:")

    elif call.data == "owner_list_admin" and is_owner(uid):
        text = "📋 *DAFTAR ADMIN*\n\n"
        text += "\n".join([f"- `{a}`" for a in admins]) if admins else "Belum ada admin"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    elif call.data == "back":
        bot.edit_message_text("⬅️ Menu Utama", call.message.chat.id,
                              call.message.message_id,
                              reply_markup=main_menu(uid))

# ================= TEXT HANDLER =================
@bot.message_handler(content_types=["text"])
def text_handler(message):
    uid = message.from_user.id
    if uid not in sessions:
        return

    sess = sessions[uid]
    if time.time() - sess["time"] > TIMEOUT:
        del sessions[uid]
        bot.reply_to(message, "⌛ Timeout.")
        return

    # ADD PREMIUM
    if sess["step"].startswith(("add_", "owner_add_")):
        target = message.text.strip()
        now = datetime.now()

        if sess["step"].endswith("unli"):
            premium_users[target] = {"type": "unlimited", "expire": None}
            save_json(PREMIUM_FILE, premium_users)

            if not is_owner(uid):
                notify_owner_admin_add_premium(uid, target, "unlimited", None)
            notify_user_premium(target, "unlimited", None)

            bot.reply_to(message, "✅ Unlimited aktif")

        else:
            days = 7 if "7day" in sess["step"] else 30
            base = now

            if target in premium_users and premium_users[target]["expire"]:
                old = datetime.strptime(premium_users[target]["expire"], "%Y-%m-%d")
                if old > now:
                    base = old

            expire = base + timedelta(days=days)
            ptype = "7day" if days == 7 else "1month"

            premium_users[target] = {
                "type": ptype,
                "expire": expire.strftime("%Y-%m-%d")
            }
            save_json(PREMIUM_FILE, premium_users)

            if not is_owner(uid):
                notify_owner_admin_add_premium(uid, target, ptype, expire.strftime("%Y-%m-%d"))
            notify_user_premium(target, ptype, expire.strftime("%Y-%m-%d"))

            bot.reply_to(message, f"✅ Premium aktif sampai {expire.strftime('%Y-%m-%d')}")

        del sessions[uid]
        return

# ================= RUN =================
threading.Thread(target=expire_checker, daemon=True).start()
print("🤖 BOT ONLINE | SISTEM BARU AKTIF")
bot.infinity_polling()
