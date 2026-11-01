import os
import re
import time
import asyncio
import threading
import certifi
import aiohttp
import feedparser
from flask import Flask
from bale import Bot, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from oilpriceapi import OilPriceAPI

# ==================== تنظیمات ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DEVELOPER_NAME = os.environ.get("DEVELOPER_NAME", "مهدی نجفی")
FEEDBACK_ID = os.environ.get("FEEDBACK_ID", "@mahdi8iiii")
MONGO_URI = os.environ.get("MONGO_URI", "")
OIL_PRICE_API_KEY = os.environ.get("OIL_PRICE_API_KEY", "")

CRYPTO_API_URL = 'https://api.abantether.com/api/v1/manager/otc/ticker'
FIAT_API_URL = 'https://cdn.jsdelivr.net/gh/HosseinOdd/Navasan-API@main/data/fiat.json'
GOLD_API_URL = 'https://cdn.jsdelivr.net/gh/HosseinOdd/Navasan-API@main/data/gold.json'

CHANNEL_ID = "@nabz_mediaa"
CHANNEL_LINK = "https://ble.ir/nabz_mediaa"
CHANNEL_POST_INTERVAL = 3600

# 📰 تنظیمات اخبار
NEWS_RSS_URL = "https://www.yjc.ir/fa/rss/allnews"
NEWS_CHECK_INTERVAL = 1800
NEWS_START_HOUR = 8
NEWS_END_HOUR = 24
_sent_news_ids = set()

USE_PROXY = True
PROXY_URL = "https://red-meadow-20f7bale-bot-proxy.najafimahdi13867.workers.dev"
BOT_USERNAME = "onlinearzmonybot"
ADMIN_IDS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
PRO_INVITE_THRESHOLD = 5

TRANSLATIONS = {
    "fa": {
        "choose_language": "🌐 لطفاً زبان خود را انتخاب کنید:",
        "welcome_new": "سلام! 👋\n\nبه *ارز آنلاین* خوش آمدید.\n\nبرای شروع فقط *نام و نام خانوادگی* خود را وارد کنید:",
        "invalid_name": "❌ نام معتبر نیست (حداقل ۳ حرف). لطفاً دوباره وارد کنید:",
        "register_success": "✅ *ثبت‌نام با موفقیت انجام شد!*\n\n👤 نام: *{name}*\n\nخوش آمدی! از منوی زیر استفاده کن:",
        "welcome_back": "👋 سلام *{name}* عزیز! خوش برگشتی.\n\nاز منوی زیر استفاده کن:",
        "menu_title": "🏠 *منوی اصلی*\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        "menu_crypto": "🪙 ارز دیجیتال", "menu_fiat": "💵 ارزهای فیات", "menu_gold": "🥇 طلا و سکه",
        "menu_oil": "🛢️ نفت برنت", "menu_convert": "🔄 مبدل ارز", "menu_market": "📊 بازار امروز",
        "menu_fav": "⭐ علاقه‌مندی‌ها", "menu_alert": "🔔 هشدار قیمت", "menu_myalerts": "📋 هشدارهای من",
        "menu_list": "📊 لیست رمزارزها", "menu_profile": "👤 پروفایل من", "menu_invite": "🎁 دعوت دوستان",
        "menu_leaderboard": "🏆 جدول قهرمانان", "menu_help": "ℹ️ راهنما",
        "menu_main": "🏠 منوی اصلی", "menu_back": "🔙 بازگشت", "menu_cancel": "❌ انصراف",
        "profile_title": "👤 *پروفایل شما*", "profile_name": "📝 نام: *{name}*", "profile_lang": "🌐 زبان: {lang_name}",
        "profile_joined": "📅 تاریخ عضویت: {date}", "profile_invites": "🎁 تعداد دعوت‌شده‌ها: *{count}* نفر",
        "profile_user_type": "👑 نوع حساب: *{user_type}*", "user_type_special": "کاربر خاص ⭐", "user_type_normal": "کاربر عادی 👤",
        "pro_locked": "🔒 این قابلیت حرفه‌ای است.\n\nبرای فعال شدن دسترسی حرفه‌ای، حداقل *۵ نفر* را با لینک دعوت خودت به بات دعوت کن.",
        "profile_logout": "🚪 خروج از حساب", "logout_done": "✅ از حساب خارج شدید.\n\nبرای ساخت پروفایل جدید، /start را بزنید.",
        "cancel": "✅ عملیات لغو شد.", "error": "❌ خطایی رخ داد.", "not_found": "❌ یافت نشد.",
        "crypto_title": "🪙 *ارز دیجیتال*\n\nیکی از رمزارزها را انتخاب کنید:", "fiat_title": "💵 *ارزهای فیات*\n\nیکی از ارزها را انتخاب کنید:",
        "gold_title": "🥇 *طلا و سکه*\n\nیکی از گزینه‌ها را انتخاب کنید:", "market_title": "📊 *بازار امروز*",
        "footer": "\n\n━━━━━━━━━━━━━━━━━━\n👨‍💻 توسعه‌دهنده: *{dev}*\n📩 انتقادات: {feedback}",
        "force_join_title": "⚠️ *دسترسی محدود*", "force_join_text": "برای استفاده از ربات، لطفاً اول در کانال ما عضو شوید:\n\n📢 {channel}\n\nبعد از عضویت، روی دکمه زیر کلیک کنید:",
        "force_join_verify": "🔄 بررسی عضویت", "force_join_not_member": "❌ شما هنوز در کانال عضو نشده‌اید.",
        "invite_title": "🎁 *سیستم دعوت دوستان*", "invite_link": "🔗 لینک دعوت اختصاصی شما:", "invite_stats": "📊 *آمار شما:*",
        "invite_count": "• تعداد دعوت‌شده‌ها: *{count}* نفر", "invite_rank": "• رتبه شما: *#{rank}*",
        "invite_reward": "\n🎁 *پاداش:*\n• ۵ دعوت: 🔔 قابلیت هشدار قیمت حرفه‌ای برای شما باز می‌شود.",
        "invite_copy": "📋 کپی لینک دعوت", "leaderboard_title": "🏆 *جدول قهرمانان*",
        "leaderboard_you": "\n📍 رتبه شما: *#{rank}* با *{count}* دعوت", "leaderboard_empty": "هنوز هیچ کاربری کسی رو دعوت نکرده. اولین نفر باش!",
        "help_title": "ℹ️ *راهنمای ارز آنلاین*", "help_text": "به *ارز آنلاین* خوش آمدی! 👋\n\nاین بات برای دسترسی سریع به قیمت‌ها و اخبار بازار ساخته شده است."
    }
}
LANG_NAMES = {"fa": "فارسی"}

def t(key, **kwargs):
    text = TRANSLATIONS["fa"].get(key, key)
    if kwargs:
        try: text = text.format(**kwargs)
        except: pass
    return text

def footer_text(): return t("footer", dev=DEVELOPER_NAME, feedback=FEEDBACK_ID)

# ==================== پروکسی ====================
if USE_PROXY:
    _orig_req = aiohttp.ClientSession._request
    async def _patched_req(self, method, url, *args, **kwargs):
        url_str = str(url)
        if 'tapi.bale.ai' in url_str:
            url_str = url_str.replace('https://tapi.bale.ai', PROXY_URL).replace('http://tapi.bale.ai', PROXY_URL)
        return await _orig_req(self, method, url_str, *args, **kwargs)
    aiohttp.ClientSession._request = _patched_req

bot = Bot(token=BOT_TOKEN)
user_states, _force_join_cache = {}, {}
MAIN_LOOP, CHANNEL_NUMERIC_ID = None, None
_sent_channel_message_ids = set()

# ==================== دیتابیس ====================
db_client = None
alerts_collection, favorites_collection, users_collection, referrals_collection = None, None, None, None

async def init_db():
    global db_client, alerts_collection, favorites_collection, users_collection, referrals_collection
    if not MONGO_URI: return False
    try:
        db_client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())
        db = db_client["bale_bot_db"]
        alerts_collection, favorites_collection, users_collection, referrals_collection = db["alerts"], db["favorites"], db["users"], db["referrals"]
        await users_collection.create_index("chat_id", unique=True)
        await alerts_collection.create_index([("chat_id", 1), ("asset", 1)], unique=True)
        await favorites_collection.create_index([("chat_id", 1), ("asset", 1)], unique=True)
        await referrals_collection.create_index([("referrer", 1), ("referred", 1)], unique=True)
        print("✅ DB Connected", flush=True)
        return True
    except Exception as e:
        print(f"❌ DB Error: {e}"); return False

POPULAR_CRYPTOS = ["BTC", "ETH", "USDT", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "TON"]
POPULAR_FIATS = ["USD", "EUR", "AED", "TRY", "GBP", "IQD", "CNY", "JPY", "CAD", "AUD", "CHF", "SAR"]
POPULAR_GOLDS = ["gold_18", "coin_emami", "coin_half", "coin_quarter", "gold_miskal", "coin_bahar", "coin_gerami"]
FIAT_NAMES = {"USD": "دلار", "EUR": "یورو", "GBP": "پوند", "AED": "درهم", "TRY": "لیر", "CNY": "یوان", "JPY": "ین", "CAD": "دلار کانادا", "AUD": "دلار استرالیا", "CHF": "فرانک", "IQD": "دینار عراق", "SAR": "ریال عربستان"}
GOLD_NAMES = {"gold_18": "طلای ۱۸", "gold_24": "طلای ۲۴", "gold_miskal": "مثقال", "coin_emami": "سکه امامی", "coin_bahar": "سکه بهار", "coin_half": "نیم سکه", "coin_quarter": "ربع سکه", "coin_gerami": "سکه گرمی"}

def format_price(val):
    if val is None: return "نامشخص"
    try: return f"{float(val):,.0f}"
    except: return str(val)

def get_asset_display_name(k): return GOLD_NAMES.get(k, FIAT_NAMES.get(k, "تومان" if k=="TOMAN" else k))

def _chat_filter(cid):
    sid = str(cid)
    return {"chat_id": {"$in": [sid, int(sid)]}} if sid.isdigit() else {"chat_id": sid}

async def get_user(cid): return await users_collection.find_one(_chat_filter(cid)) if users_collection is not None else None
async def get_active_user(cid):
    u = await get_user(cid)
    return u if u and u.get("account_status", "active") != "logged_out" else None

async def create_user(cid, name, ref=None):
    cid = str(cid); ex = await users_collection.find_one(_chat_filter(cid))
    if ex:
        await users_collection.update_one({"_id": ex["_id"]}, {"$set": {"name": name, "account_status": "active", "last_seen_at": time.time()}})
        return True
    doc = {"chat_id": cid, "name": name, "language": "fa", "created_at": time.time(), "updated_at": time.time(), "last_seen_at": time.time(), "account_status": "active", "blocked": False, "special_user": False, "referred_by": str(ref) if ref else None, "invite_count": 0}
    await users_collection.insert_one(doc)
    if ref and str(ref) != cid:
        res = await referrals_collection.update_one({"referrer": str(ref), "referred": cid}, {"$setOnInsert": {"created_at": time.time()}}, upsert=True)
        if res.upserted_id: await users_collection.update_one(_chat_filter(ref), {"$inc": {"invite_count": 1}})
    return True

async def get_inv_count(cid):
    u = await get_user(cid); return u.get("invite_count", 0) if u else 0

async def get_rank(cid):
    my = await get_inv_count(cid); return await users_collection.count_documents({"invite_count": {"$gt": my}}) + 1

async def has_pro(cid):
    u = await get_user(cid)
    return bool(u and (u.get("special_user") is True or int(u.get("invite_count", 0)) >= PRO_INVITE_THRESHOLD))

async def check_member(uid, cache=True):
    if cache and str(uid) in _force_join_cache and (time.time() - _force_join_cache[str(uid)]) < 60: return True
    try:
        res = await asyncio.to_thread(lambda: requests.post(f"https://tapi.bale.ai/bot{BOT_TOKEN}/getChatMember", json={"chat_id": CHANNEL_ID, "user_id": int(uid)}, timeout=10))
        body = res.json()
        if body.get("ok"):
            st = str(body.get("result", {}).get("status", "")).lower()
            if st in ["member", "administrator", "creator"]:
                _force_join_cache[str(uid)] = time.time(); return True
    except: pass
    _force_join_cache.pop(str(uid), None); return False

_fiat_cache, _gold_cache, _oil_cache = {"data": None, "ts": 0}, {}, {"data": None, "ts": 0}

def get_fiat(sym):
    try:
        if not _fiat_cache["data"] or (time.time() - _fiat_cache["ts"]) > 120:
            _fiat_cache["data"] = requests.get(FIAT_API_URL, timeout=10).json()
            _fiat_cache["ts"] = time.time()
        if sym.lower() in _fiat_cache["data"]:
            p = _fiat_cache["data"][sym.lower()].get("value") if isinstance(_fiat_cache["data"][sym.lower()], dict) else _fiat_cache["data"][sym.lower()]
            p = float(str(p).replace(",", "")); return p/10 if p>10_000_000 else p
    except: pass
    return None

def get_gold(asset):
    try:
        res = requests.get(GOLD_API_URL, timeout=10).json(); k_map = {"gold_18": "18ayar", "coin_emami": "sekkeh", "coin_bahar": "bahar", "coin_half": "nim", "coin_quarter": "rob", "coin_gerami": "gerami"}
        if asset in k_map and k_map[asset] in res: return float(res[k_map[asset]]["value"])
        if asset == "gold_miskal": return float(res["18ayar"]["value"]) * 4.608
    except: pass
    return None

def get_crypto(sym):
    try:
        res = requests.get(CRYPTO_API_URL, timeout=10).json(); m = res.get("data", {}).get("markets", {})
        if sym in m: return {"symbol": sym, "buy_price": float(m[sym]["buy_price"]), "sell_price": float(m[sym]["sell_price"])}
    except: pass
    return None

def get_oil():
    if _oil_cache["data"] and (time.time() - _oil_cache["ts"]) < 300: return _oil_cache["data"]
    try:
        if not OIL_PRICE_API_KEY: return None
        res = OilPriceAPI(api_key=OIL_PRICE_API_KEY).prices.get("BRENT_CRUDE_USD")
        _oil_cache["data"] = {"price": res.value, "currency": res.currency}; _oil_cache["ts"] = time.time(); return _oil_cache["data"]
    except: return None

def get_price(asset):
    if asset == "TOMAN": return 1.0
    if asset in GOLD_NAMES: return get_gold(asset)
    if asset in FIAT_NAMES: return get_fiat(asset)
    c = get_crypto(asset); return c["buy_price"] if c else None

# ==================== کیبوردها ====================
def force_join_kb():
    return InlineKeyboardMarkup().add(InlineKeyboardButton(text=f"📢 {CHANNEL_ID}", url=CHANNEL_LINK), row=0).add(InlineKeyboardButton(text=t("force_join_verify"), callback_data="FORCEJOIN:VERIFY"), row=1)

def main_kb():
    return InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_crypto"), callback_data="MENU:CRYPTO"), row=0).add(InlineKeyboardButton(text=t("menu_fiat"), callback_data="MENU:FIAT"), row=0)\
        .add(InlineKeyboardButton(text=t("menu_gold"), callback_data="MENU:GOLD"), row=1).add(InlineKeyboardButton(text=t("menu_oil"), callback_data="MENU:OIL"), row=1)\
        .add(InlineKeyboardButton(text=t("menu_convert"), callback_data="CONV:NEW"), row=2).add(InlineKeyboardButton(text=t("menu_market"), callback_data="MENU:MARKET"), row=2)\
        .add(InlineKeyboardButton(text=t("menu_fav"), callback_data="FAV:VIEW"), row=3).add(InlineKeyboardButton(text=t("menu_alert"), callback_data="ALERT:NEW"), row=3)\
        .add(InlineKeyboardButton(text=t("menu_myalerts"), callback_data="MENU:MYALERTS"), row=4).add(InlineKeyboardButton(text=t("menu_invite"), callback_data="MENU:INVITE"), row=4)\
        .add(InlineKeyboardButton(text=t("menu_leaderboard"), callback_data="MENU:LEADERBOARD"), row=5).add(InlineKeyboardButton(text=t("menu_profile"), callback_data="MENU:PROFILE"), row=6)\
        .add(InlineKeyboardButton(text=t("menu_help"), callback_data="MENU:HELP"), row=6)

def get_assets_kb(prefix, assets, cancel="MENU:MAIN"):
    kb = InlineKeyboardMarkup()
    for i in range(0, len(assets), 2):
        for sym in assets[i:i+2]:
            kb.add(InlineKeyboardButton(text=get_asset_display_name(sym), callback_data=f"{prefix}:{sym}"), row=i//2)
    kb.add(InlineKeyboardButton(text=t("menu_cancel"), callback_data=cancel), row=len(assets)//2 + 1)
    return kb

def alert_cat_kb(): return InlineKeyboardMarkup().add(InlineKeyboardButton(text="🪙 رمزارز", callback_data="ALERT:CAT:crypto"), row=0).add(InlineKeyboardButton(text="💱 فیات", callback_data="ALERT:CAT:fiat"), row=0).add(InlineKeyboardButton(text="🥇 طلا", callback_data="ALERT:CAT:gold"), row=1).add(InlineKeyboardButton(text=t("menu_cancel"), callback_data="MENU:MAIN"), row=2)
def dir_kb(): return InlineKeyboardMarkup().add(InlineKeyboardButton(text="📈 بالا", callback_data="ALERT:DIR:above"), row=0).add(InlineKeyboardButton(text="📉 پایین", callback_data="ALERT:DIR:below"), row=1)

# ==================== پنل ادمین ====================
def is_admin(uid): return str(uid) in ADMIN_IDS
def admin_kb(): return InlineKeyboardMarkup().add(InlineKeyboardButton(text="📊 آمار", callback_data="ADMIN:STATS"), row=0).add(InlineKeyboardButton(text="🔎 جستجو", callback_data="ADMIN:SEARCH"), row=1).add(InlineKeyboardButton(text="📢 پیام همگانی", callback_data="ADMIN:BC"), row=2).add(InlineKeyboardButton(text="🔙 بستن پنل", callback_data="MENU:MAIN"), row=3)
def admin_back(): return InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙", callback_data="ADMIN:HOME"), row=0)

async def admin_stats():
    tot = await users_collection.count_documents({}) if users_collection is not None else 0
    act = await users_collection.count_documents({"account_status": {"$ne": "logged_out"}}) if users_collection is not None else 0
    al = await alerts_collection.count_documents({}) if alerts_collection is not None else 0
    return f"👨‍💻 **داشبورد مدیریت**\n\n👥 کل پروفایل‌ها: **{tot:,}**\n🟢 حساب‌های فعال: **{act:,}**\n🔔 هشدارهای فعال: **{al:,}**"

async def show_menu(t, uid, edit=False):
    u = await get_user(uid); name = u.get("name", "کاربر") if u else "کاربر"
    txt = f"✨ *ارز آنلاین* ✨\n\n{t('welcome_back', name=name)}\n\n{t('menu_title')}"
    if edit:
        try: await t.edit(txt + footer_text(), components=main_kb()); return
        except: pass
    await t.reply(txt + footer_text(), components=main_kb())

# ==================== تسک‌های پس‌زمینه ====================
async def alert_checker():
    while True:
        await asyncio.sleep(60)
        if alerts_collection is None: continue
        for a in await alerts_collection.find({}).to_list(1000):
            p = get_price(a["asset"])
            if p:
                trig = (a["direction"]=="above" and p>=a["target_price"]) or (a["direction"]=="below" and p<=a["target_price"])
                if trig:
                    try:
                        await bot.send_message(a["chat_id"], f"🔔 **هشدار!**\n{get_asset_display_name(a['asset'])} به {format_price(p)} رسید.")
                        await alerts_collection.delete_one({"_id": a["_id"]})
                    except: pass

def channel_poster():
    while True:
        time.sleep(CHANNEL_POST_INTERVAL)
        if CHANNEL_ID:
            try:
                txt = f"📊 **نرخ بازار**\n💵 دلار: {format_price(get_price('USD'))}\n🥇 طلا: {format_price(get_price('gold_18'))}\n🪙 BTC: {format_price(get_price('BTC'))}\n🛢️ نفت: {format_price(get_oil()['price'] if get_oil() else 0)}\n📢 {CHANNEL_ID}"
                fut = asyncio.run_coroutine_threadsafe(bot.send_message(CHANNEL_ID, txt), MAIN_LOOP)
                res = fut.result(30)
                if res and hasattr(res, 'message_id'): _sent_channel_message_ids.add(str(res.message_id))
            except: pass

def news_poster():
    print("📰 News started!")
    while True:
        if NEWS_START_HOUR <= time.localtime().tm_hour < NEWS_END_HOUR:
            try:
                feed = feedparser.parse(NEWS_RSS_URL)
                for e in feed.entries[:5]:
                    nid = e.get('id', e.get('link'))
                    if nid not in _sent_news_ids:
                        s = re.sub(r'<[^>]+>', '', e.get('summary', ''))[:150]
                        txt = f"📰 **{e.get('title')}**\n\n{s}...\n\n📢 {CHANNEL_LINK}"
                        fut = asyncio.run_coroutine_threadsafe(bot.send_message(CHANNEL_ID, txt), MAIN_LOOP)
                        fut.result(30)
                        _sent_news_ids.add(nid)
                if len(_sent_news_ids) > 500: _sent_news_ids.clear()
            except: pass
        time.sleep(NEWS_CHECK_INTERVAL)

# ==================== رویدادها ====================
@bot.event
async def on_ready():
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()
    print("🤖 Bot is ready!", flush=True)
    await init_db()
    asyncio.create_task(alert_checker())
    threading.Thread(target=channel_poster, daemon=True).start()
    threading.Thread(target=news_poster, daemon=True).start()

@bot.event
async def on_message(message: Message):
    if not message.content or message.author.is_bot or message.chat.type != 'private': return
    if str(getattr(message, 'message_id', '')) in _sent_channel_message_ids: return
    
    cid = str(message.author.id)
    txt = message.content.strip()
    state = user_states.get(cid, {})
    
    if txt == "/myid":
        await message.reply(f"🆔 Chat ID: `{cid}`"); return

    # ----- ثبت‌نام و شروع -----
    if txt.startswith("/start"):
        u = await get_active_user(cid)
        if is_admin(cid): await message.reply("👨‍💻 پنل مدیریت:", components=admin_kb())
        if u:
            if not await check_member(cid): await message.reply(t("force_join_title") + "\n\n" + t("force_join_text", channel=CHANNEL_ID), components=force_join_kb()); return
            await show_menu(message, cid)
        else:
            ref = txt.split()[1] if len(txt.split()) > 1 and txt.split()[1].isdigit() else None
            user_states[cid] = {"state": "awaiting_name", "data": {"ref": ref}}
            await message.reply(t("welcome_new"))
        return

    # ----- مدیران -----
    if is_admin(cid):
        if txt == "/admin": await message.reply(await admin_stats(), components=admin_kb()); return
        if state.get("state") == "admin_search":
            docs = await users_collection.find({"$or": [{"chat_id": txt}, {"name": {"$regex": txt, "$options": "i"}}]}).limit(10).to_list(10)
            kb = InlineKeyboardMarkup()
            for i, d in enumerate(docs): kb.add(InlineKeyboardButton(text=d['name'], callback_data=f"ADMIN:USER:{d['chat_id']}"), row=i)
            kb.add(InlineKeyboardButton(text="🔙", callback_data="ADMIN:HOME"), row=len(docs))
            await message.reply("🔎 نتایج:", components=kb); user_states.pop(cid, None); return
        if state.get("state") == "admin_broadcast":
            user_states[cid] = {"state": "admin_broadcast_confirm", "data": {"text": txt}}
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton(text="✅ تایید", callback_data="ADMIN:BC:YES"), row=0).add(InlineKeyboardButton(text="❌ لغو", callback_data="ADMIN:HOME"), row=1)
            await message.reply(f"پیش‌نمایش:\n\n{txt}", components=kb); return

    # ----- ثبت‌نام -----
    if state.get("state") == "awaiting_name":
        if len(txt) < 3: await message.reply(t("invalid_name")); return
        await create_user(cid, txt, state["data"].get("ref"))
        user_states.pop(cid, None)
        await message.reply(t("register_success", name=txt) + footer_text(), components=main_kb()); return

    # ----- مبدل -----
    if state.get("state") == "conv_amount":
        try:
            amt = float(txt.replace(",", ""))
            f, to = state["data"]["from"], state["data"]["to"]
            p1, p2 = get_price(f), get_price(to)
            if p1 and p2:
                res = amt * p1 / p2
                user_states.pop(cid, None)
                await message.reply(f"🔄 {amt:,.2f} {get_asset_display_name(f)} = **{res:,.4f} {get_asset_display_name(to)}**", components=main_kb()); return
        except: await message.reply("❌ عدد معتبر وارد کنید."); return

    # ----- هشدار -----
    if state.get("state") == "alert_price":
        try:
            pr = float(txt.replace(",", ""))
            user_states[cid] = {"state": "alert_dir", "data": {**state["data"], "price": pr}}
            await message.reply(f"🎯 قیمت: {format_price(pr)}\nشرط:", components=dir_kb()); return
        except: await message.reply("❌ عدد معتبر وارد کنید."); return

    await message.reply("❌ از منو استفاده کنید.")

@bot.event
async def on_callback(callback: CallbackQuery):
    cid = str(callback.message.author.id); data = callback.data
    if not cid or callback.message.chat.type != 'private': return

    # ----- ادمین -----
    if data.startswith("ADMIN:") and is_admin(cid):
        if data in ("ADMIN:HOME", "ADMIN:STATS"): await callback.message.edit(await admin_stats(), components=admin_kb()); return
        if data == "ADMIN:SEARCH": user_states[cid] = {"state": "admin_search"}; await callback.message.edit("🔎 نام یا آیدی:", components=admin_back()); return
        if data == "ADMIN:BC": user_states[cid] = {"state": "admin_broadcast"}; await callback.message.edit("📢 متن پیام:", components=admin_back()); return
        if data == "ADMIN:BC:YES":
            txt = user_states.get(cid, {}).get("data", {}).get("text")
            if txt:
                user_states.pop(cid, None); await callback.message.edit("⏳ در حال ارسال...")
                sent = 0
                async for u in users_collection.find({"account_status": "active", "blocked": False}):
                    try: await bot.send_message(u["chat_id"], txt); sent += 1
                    except: pass
                await callback.message.reply(f"✅ ارسال شد به {sent} کاربر.", components=admin_kb()); return
        return

    # ----- عضویت اجباری -----
    if data == "FORCEJOIN:VERIFY":
        _force_join_cache.pop(cid, None)
        if await check_member(cid, False):
            u = await get_active_user(cid)
            if u: await show_menu(callback.message, cid, True)
            else:
                user_states[cid] = {"state": "awaiting_name", "data": {}}
                await callback.message.edit(t("welcome_new"))
        else: await callback.message.edit(t("force_join_not_member"), components=force_join_kb())
        return

    if not await get_user(cid): return

    # ----- منوی اصلی و لیست‌ها -----
    if data == "MENU:MAIN": user_states.pop(cid, None); await show_menu(callback.message, cid, True); return
    if data == "MENU:CRYPTO": await callback.message.edit(t("crypto_title"), components=get_assets_kb("CRYPTO", POPULAR_CRYPTOS)); return
    if data == "MENU:FIAT": await callback.message.edit(t("fiat_title"), components=get_assets_kb("FIAT", POPULAR_FIATS)); return
    if data == "MENU:GOLD": await callback.message.edit(t("gold_title"), components=get_assets_kb("GOLD", POPULAR_GOLDS)); return
    
    if data == "MENU:OIL":
        o = get_oil(); txt = f"🛢️ **نفت برنت**\n💰 {format_price(o['price'])} {o['currency']}" if o else "❌ نامشخص"
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN"))); return

    if data.startswith(("CRYPTO:", "FIAT:", "GOLD:")):
        sym = data.split(":")[1]; p = get_price(sym)
        txt = f"💰 **{get_asset_display_name(sym)}**: **{format_price(p)} تومان**" if p else "❌ یافت نشد."
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN"))); return

    if data == "MENU:INVITE":
        link = f"https://ble.ir/{BOT_USERNAME}?start={cid}"; count = await get_inv_count(cid)
        txt = f"{t('invite_title')}\n\n{t('invite_link')}\n`{link}`\n\n{t('invite_count', count=count)}\n{t('invite_rank', rank=await get_rank(cid))}{t('invite_reward')}"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton(text="📤 اشتراک", url=f"https://ble.ir/share/url?url={link}"), row=0).add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN"), row=1)
        await callback.message.edit(txt + footer_text(), components=kb); return

    if data == "MENU:LEADERBOARD":
        top = await users_collection.find({"invite_count": {"$gt": 0}}).sort("invite_count", -1).limit(10).to_list(10)
        if not top: txt = t("leaderboard_title") + "\n\n" + t("leaderboard_empty")
        else:
            lines = [t("leaderboard_title"), "━━━━━━━━━━━━━━━━━━"]
            for i, u in enumerate(top):
                m = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                lines.append(f"{m} {u['name']} → *{u.get('invite_count', 0)}* دعوت")
            lines.append(t("leaderboard_you", rank=await get_rank(cid), count=await get_inv_count(cid)))
            txt = "\n".join(lines)
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN"))); return

    if data == "MENU:PROFILE":
        u = await get_user(cid); ut = t("user_type_special") if u.get('special_user') else t("user_type_normal")
        txt = f"{t('profile_title')}\n📝 {u['name']}\n👑 {ut}\n🎁 دعوت‌ها: {u.get('invite_count', 0)}"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("profile_logout"), callback_data="PROF:OUT"), row=0).add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN"), row=1)
        await callback.message.edit(txt + footer_text(), components=kb); return

    if data == "PROF:OUT":
        await users_collection.update_one({"chat_id": cid}, {"$set": {"account_status": "logged_out"}})
        await callback.message.edit(t("logout_done")); return

    if data == "MENU:HELP":
        txt = f"ℹ️ **راهنمای ارز آنلاین**\n\nبه ربات جامع *ارز آنلاین* خوش آمدید! 👋\nاین ربات در ابتدا در پیام‌رسان *بله* فعالیت خود را آغاز کرد و حالا به عنوان شعبه دوم، در تلگرام نیز در خدمت شماست! 🚀\n\n🌟 امکانات: قیمت لحظه‌ای ارز، طلا، نفت، مبدل، هشدار، دعوت و..."
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN"))); return

    if data == "MENU:MARKET":
        txt = f"📊 *بازار امروز*\n💵 دلار: {format_price(get_price('USD'))}\n🥇 طلا: {format_price(get_price('gold_18'))}\n🪙 BTC: {format_price(get_price('BTC'))}\n🛢️ نفت: {format_price(get_oil()['price'] if get_oil() else 0)}"
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN"))); return

    # ----- هشدار قیمت -----
    if data in ("ALERT:NEW", "MENU:MYALERTS") or data.startswith("ALERT:"):
        if not await has_pro(cid):
            await callback.message.edit(t("pro_locked") + footer_text(), components=main_kb()); return

    if data == "ALERT:NEW": await callback.message.edit("🔔 دسته:", components=alert_cat_kb()); return
    if data.startswith("ALERT:CAT:"):
        cat = data.split(":")[2]; assets = POPULAR_CRYPTOS if cat == "crypto" else POPULAR_FIATS if cat == "fiat" else POPULAR_GOLDS
        await callback.message.edit("🔔 دارایی:", components=get_assets_kb("ALERT:SET", assets)); return
    if data.startswith("ALERT:SET:"):
        user_states[cid] = {"state": "alert_price", "data": {"asset": data.split(":")[2]}}
        await callback.message.edit("🎯 قیمت هدف (تومان):"); return
    if data.startswith("ALERT:DIR:"):
        d = data.split(":")[2]; asset = user_states[cid]["data"]["asset"]; p = user_states[cid]["data"]["price"]
        await alerts_collection.update_one({"chat_id": cid, "asset": asset}, {"$set": {"target_price": p, "direction": d, "created_at": time.time()}}, upsert=True)
        user_states.pop(cid, None); await callback.message.edit(f"✅ هشدار ثبت شد: {get_asset_display_name(asset)} → {format_price(p)}", components=main_kb()); return

    # ----- مبدل ارز -----
    if data == "CONV:NEW": await callback.message.edit("🔄 مبدا:", components=get_assets_kb("CONV:FROM", ["TOMAN", "USD", "BTC", "ETH", "USDT", "gold_18", "coin_emami"])); return
    if data.startswith("CONV:FROM:"): await callback.message.edit("🔄 مقصد:", components=get_assets_kb(f"CONV:TO:{data.split(':')[2]}", ["TOMAN", "USD", "BTC", "ETH", "USDT", "gold_18", "coin_emami"])); return
    if data.startswith("CONV:TO:"):
        parts = data.split(":")
        user_states[cid] = {"state": "conv_amount", "data": {"from": parts[2], "to": parts[3]}}
        await callback.message.edit(f"✅ {get_asset_display_name(parts[2])} به {get_asset_display_name(parts[3])}\n\nمقدار را تایپ کنید:"); return

    # ----- علاقه‌مندی‌ها -----
    if data == "FAV:VIEW":
        favs = await favorites_collection.find({"chat_id": cid}).to_list(20)
        if not favs: return await callback.message.edit("⭐ لیست خالیه!", components=InlineKeyboardMarkup().add(InlineKeyboardButton(text="➕", callback_data="FAV:ADD")).add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN")))
        txt = "⭐ **علاقه‌مندی‌ها:**\n\n" + "\n".join([f"🔸 {get_asset_display_name(f['asset'])}: {format_price(get_price(f['asset']))}" for f in favs])
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_main"), callback_data="MENU:MAIN"))); return
    if data == "FAV:ADD":
        await callback.message.edit("⭐ دارایی:", components=get_assets_kb("FAV:SET", ["BTC", "ETH", "USDT", "USD", "EUR", "gold_18", "coin_emami"])); return
    if data.startswith("FAV:SET:"):
        asset = data.split(":")[2]
        await favorites_collection.update_one({"chat_id": cid, "asset": asset}, {"$set": {"created_at": time.time()}}, upsert=True)
        await callback.message.edit(f"✅ {get_asset_display_name(asset)} اضافه شد.", components=main_kb()); return

# ==================== اجرا ====================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080)); app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()
    bot.run()
