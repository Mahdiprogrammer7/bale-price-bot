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
CHANNEL_POST_ENABLED = True

# 📰 تنظیمات اخبار (از ۸ صبح تا ۱۲ شب)
NEWS_RSS_URL = "https://www.yjc.ir/fa/rss/allnews"
NEWS_CHECK_INTERVAL = 1800  # هر 30 دقیقه چک میکند
NEWS_START_HOUR = 8
NEWS_END_HOUR = 24
_sent_news_ids = set()

# ✅ پروکسی
USE_PROXY = True
PROXY_URL = "https://red-meadow-20f7bale-bot-proxy.najafimahdi13867.workers.dev"
WELCOME_IMAGE_URL = ""

BOT_USERNAME = "onlinearzmonybot"
ADMIN_IDS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
ADMIN_PAGE_SIZE = 8
PRO_INVITE_THRESHOLD = 5

# ==================== سیستم ترجمه ====================
TRANSLATIONS = {
    "fa": {
        "choose_language": "🌐 لطفاً زبان خود را انتخاب کنید:",
        "welcome_new": "سلام! 👋\n\nبه *ارز آنلاین* خوش آمدید.\n\nبرای شروع فقط *نام و نام خانوادگی* خود را وارد کنید:",
        "invalid_name": "❌ نام معتبر نیست (حداقل ۳ حرف). لطفاً دوباره وارد کنید:",
        "register_success": "✅ *ثبت‌نام با موفقیت انجام شد!*\n\n👤 نام: *{name}*\n🌐 زبان: {lang_name}\n\nخوش آمدی! از منوی زیر استفاده کن:",
        "welcome_back": "👋 سلام *{name}* عزیز! خوش برگشتی.\n\nاز منوی زیر استفاده کن:",
        "menu_title": "🏠 *منوی اصلی*\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        "menu_crypto": "🪙 ارز دیجیتال", "menu_fiat": "💵 ارزهای فیات", "menu_gold": "🥇 طلا و سکه",
        "menu_oil": "🛢️ نفت برنت", "menu_convert": "🔄 مبدل ارز", "menu_market": "📊 بازار امروز",
        "menu_fav": "⭐ علاقه‌مندی‌ها", "menu_alert": "🔔 هشدار قیمت", "menu_myalerts": "📋 هشدارهای من",
        "menu_list": "📊 لیست رمزارزها", "menu_profile": "👤 پروفایل من", "menu_invite": "🎁 دعوت دوستان",
        "menu_leaderboard": "🏆 جدول قهرمانان", "menu_help": "ℹ️ راهنما",
        "menu_main": "🏠 منوی اصلی", "menu_back": "🔙 بازگشت", "menu_cancel": "❌ انصراف",
        "profile_title": "👤 *پروفایل شما*", "profile_name": "📝 نام: *{name}*", "profile_phone": "📱 شماره: `{phone}`",
        "profile_lang": "🌐 زبان: {lang_name}", "profile_joined": "📅 تاریخ عضویت: {date}",
        "profile_invites": "🎁 تعداد دعوت‌شده‌ها: *{count}* نفر", "profile_user_type": "👑 نوع حساب: *{user_type}*",
        "user_type_special": "کاربر خاص ⭐", "user_type_normal": "کاربر عادی 👤",
        "pro_locked": "🔒 این قابلیت حرفه‌ای است.\n\nبرای فعال شدن دسترسی حرفه‌ای، حداقل *۵ نفر* را با لینک دعوت خودت به بات دعوت کن.\n\n🎁 دعوت موفق بیشتر = امکانات بیشتر",
        "profile_change_lang": "🌐 تغییر زبان", "profile_logout": "🚪 خروج از حساب",
        "logout_confirm": "⚠️ با خروج از حساب، پروفایل فعلی شما از حالت فعال خارج می‌شود.\n\nآیا مطمئن هستید؟",
        "logout_done": "✅ از حساب خارج شدید.\n\nبرای ساخت پروفایل جدید، /start را بزنید.",
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

def t(key, lang="fa", **kwargs):
    text = TRANSLATIONS.get(lang, TRANSLATIONS["fa"]).get(key, key)
    if kwargs:
        try: text = text.format(**kwargs)
        except: pass
    return text

def footer_text(lang="fa"): return t("footer", lang, dev=DEVELOPER_NAME, feedback=FEEDBACK_ID)

# ==================== پروکسی ====================
if USE_PROXY:
    _orig_req = aiohttp.ClientSession._request
    async def _patched_req(self, method, url, *args, **kwargs):
        url_str = str(url)
        if 'tapi.bale.ai' in url_str:
            url_str = url_str.replace('https://tapi.bale.ai', PROXY_URL).replace('http://tapi.bale.ai', PROXY_URL)
        return await _orig_req(self, method, url_str, *args, **kwargs)
    aiohttp.ClientSession._request = _patched_req
    print("✅ Cloudflare Proxy override فعال شد!", flush=True)

bot = Bot(token=BOT_TOKEN)
user_states, _user_lang_cache, _force_join_cache = {}, {}, {}
MAIN_LOOP, CHANNEL_NUMERIC_ID, BOT_ID = None, None, None
_sent_channel_message_ids = set()
_channel_thread_started, _checker_thread_started = False, False

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

async def get_lang(cid):
    cid = str(cid)
    if cid in _user_lang_cache: return _user_lang_cache[cid]
    u = await get_user(cid)
    lang = u.get("language", "fa") if u else "fa"
    _user_lang_cache[cid] = lang
    return lang

def clear_lang(cid):
    if str(cid) in _user_lang_cache: del _user_lang_cache[str(cid)]

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
def language_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="LANG:fa"), row=0)
    return markup

def main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🪙 ارز دیجیتال", callback_data="MENU:CRYPTO"), row=0)
    markup.add(InlineKeyboardButton(text="💵 ارزهای فیات", callback_data="MENU:FIAT"), row=0)
    markup.add(InlineKeyboardButton(text="🥇 طلا و سکه", callback_data="MENU:GOLD"), row=1)
    markup.add(InlineKeyboardButton(text="🛢️ نفت برنت", callback_data="MENU:OIL"), row=1)
    markup.add(InlineKeyboardButton(text="🔄 مبدل ارز", callback_data="CONV:NEW"), row=2)
    markup.add(InlineKeyboardButton(text="📊 بازار امروز", callback_data="MENU:MARKET"), row=2)
    markup.add(InlineKeyboardButton(text="⭐ علاقه‌مندی‌ها", callback_data="FAV:VIEW"), row=3)
    markup.add(InlineKeyboardButton(text="🔔 هشدار قیمت", callback_data="ALERT:NEW"), row=3)
    markup.add(InlineKeyboardButton(text="📋 هشدارهای من", callback_data="MENU:MYALERTS"), row=4)
    markup.add(InlineKeyboardButton(text="📊 لیست رمزارزها", callback_data="MENU:LIST"), row=4)
    markup.add(InlineKeyboardButton(text="🎁 دعوت دوستان", callback_data="MENU:INVITE"), row=5)
    markup.add(InlineKeyboardButton(text="🏆 جدول قهرمانان", callback_data="MENU:LEADERBOARD"), row=5)
    markup.add(InlineKeyboardButton(text="👤 پروفایل من", callback_data="MENU:PROFILE"), row=6)
    markup.add(InlineKeyboardButton(text="ℹ️ راهنما", callback_data="MENU:HELP"), row=7)
    return markup

def force_join_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=f"📢 {CHANNEL_ID}", url=CHANNEL_LINK), row=0)
    markup.add(InlineKeyboardButton(text="🔄 بررسی عضویت", callback_data="FORCEJOIN:VERIFY"), row=1)
    return markup

def get_assets_kb(prefix, assets, cancel="MENU:MAIN"):
    kb = InlineKeyboardMarkup()
    for i in range(0, len(assets), 2):
        for sym in assets[i:i+2]:
            kb.add(InlineKeyboardButton(text=get_asset_display_name(sym), callback_data=f"{prefix}:{sym}"), row=i//2)
    kb.add(InlineKeyboardButton(text="❌ انصراف", callback_data=cancel), row=len(assets)//2 + 1)
    return kb

def alert_cat_kb(): 
    return InlineKeyboardMarkup().add(InlineKeyboardButton(text="🪙 رمزارز", callback_data="ALERT:CAT:crypto"), row=0).add(InlineKeyboardButton(text="💱 فیات", callback_data="ALERT:CAT:fiat"), row=0).add(InlineKeyboardButton(text="🥇 طلا", callback_data="ALERT:CAT:gold"), row=1).add(InlineKeyboardButton(text="❌ انصراف", callback_data="ALERT:CANCEL"), row=2)

def dir_kb(): 
    return InlineKeyboardMarkup().add(InlineKeyboardButton(text="📈 بالا", callback_data="ALERT:DIR:above"), row=0).add(InlineKeyboardButton(text="📉 پایین", callback_data="ALERT:DIR:below"), row=1)

# ==================== پنل ادمین ====================
def is_admin(uid): return str(uid) in ADMIN_IDS
def admin_kb(): 
    return InlineKeyboardMarkup().add(InlineKeyboardButton(text="📊 آمار", callback_data="ADMIN:STATS"), row=0).add(InlineKeyboardButton(text="🔎 جستجو", callback_data="ADMIN:SEARCH"), row=1).add(InlineKeyboardButton(text="📢 پیام همگانی", callback_data="ADMIN:BC"), row=2).add(InlineKeyboardButton(text="🔙 بستن پنل", callback_data="MENU:MAIN"), row=3)
def admin_back(): 
    return InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙", callback_data="ADMIN:HOME"), row=0)

async def admin_stats():
    tot = await users_collection.count_documents({}) if users_collection is not None else 0
    act = await users_collection.count_documents({"account_status": {"$ne": "logged_out"}}) if users_collection is not None else 0
    al = await alerts_collection.count_documents({}) if alerts_collection is not None else 0
    return f"👨‍💻 **داشبورد مدیریت**\n\n👥 کل پروفایل‌ها: **{tot:,}**\n🟢 حساب‌های فعال: **{act:,}**\n🔔 هشدارهای فعال: **{al:,}**"

# ==================== نمایش منو ====================
async def show_main_menu(target, uid, edit=False):
    lang = await get_lang(uid)
    u = await get_user(uid)
    name = u.get("name", "کاربر") if u else "کاربر"
    txt = f"✨ *ارز آنلاین* ✨\n\n{t('welcome_back', lang, name=name)}\n\n{t('menu_title', lang)}\n\n📌 قیمت لحظه‌ای ارز، رمزارز، طلا و سکه\n⚡ سریع • دقیق • همیشه در دسترس"
    if edit:
        try: await target.edit(txt + footer_text(lang), components=main_menu_keyboard()); return
        except: pass
    await target.reply(txt + footer_text(lang), components=main_menu_keyboard())

# ==================== تسک‌های پس‌زمینه ====================
async def alert_checker_async():
    while True:
        try:
            alerts = await alerts_collection.find({}).to_list(1000)
            for a in alerts:
                p = get_price(a["asset"])
                if p:
                    trig = (a["direction"]=="above" and p>=a["target_price"]) or (a["direction"]=="below" and p<=a["target_price"])
                    if trig:
                        try:
                            await bot.send_message(a["chat_id"], f"🔔 **هشدار!**\n{get_asset_display_name(a['asset'])} به {format_price(p)} تومان رسید.")
                            await alerts_collection.delete_one({"_id": a["_id"]})
                        except: pass
        except: pass
        await asyncio.sleep(60)

def channel_poster():
    while True:
        try:
            time.sleep(CHANNEL_POST_INTERVAL)
            if CHANNEL_POST_ENABLED and CHANNEL_ID:
                txt = f"📊 **نرخ بازار**\n💵 دلار: {format_price(get_price('USD'))}\n🥇 طلا: {format_price(get_price('gold_18'))}\n🪙 BTC: {format_price(get_price('BTC'))}\n🛢️ نفت: {format_price(get_oil()['price'] if get_oil() else 0)}\n📢 {CHANNEL_ID}"
                if MAIN_LOOP is not None:
                    fut = asyncio.run_coroutine_threadsafe(bot.send_message(CHANNEL_ID, txt), MAIN_LOOP)
                    res = fut.result(30)
                    if res and hasattr(res, 'message_id'): _sent_channel_message_ids.add(str(res.message_id))
        except: pass

def news_poster():
    print("📰 News poster started!", flush=True)
    while True:
        try:
            current_hour = time.localtime().tm_hour
            if NEWS_START_HOUR <= current_hour < NEWS_END_HOUR:
                feed = feedparser.parse(NEWS_RSS_URL)
                for entry in feed.entries[:5]:
                    news_id = entry.get('id', entry.get('link'))
                    if news_id not in _sent_news_ids:
                        title = entry.get('title', '')
                        summary = re.sub(r'<[^>]+>', '', entry.get('summary', ''))[:150]
                        final_text = f"📰 **{title}**\n\n{summary}...\n\n📢 {CHANNEL_LINK}"
                        
                        if MAIN_LOOP is not None:
                            try:
                                future = asyncio.run_coroutine_threadsafe(bot.send_message(CHANNEL_ID, final_text), MAIN_LOOP)
                                future.result(30)
                                _sent_news_ids.add(news_id)
                                print(f"✅ خبر ارسال شد: {title[:30]}", flush=True)
                            except Exception as e:
                                print(f"❌ خطا در ارسال خبر: {e}", flush=True)
                if len(_sent_news_ids) > 500:
                    _sent_news_ids.clear()
            time.sleep(NEWS_CHECK_INTERVAL)
        except Exception as e:
            print(f"❌ News poster error: {e}", flush=True)
            time.sleep(60)

# ==================== رویدادها ====================
@bot.event
async def on_ready():
    global MAIN_LOOP, BOT_ID, _channel_thread_started, _checker_thread_started
    print(f"🤖 Bot is ready!", flush=True)
    MAIN_LOOP = asyncio.get_running_loop()
    BOT_ID = str(bot.user.id)
    await init_db()
    
    if not _checker_thread_started:
        asyncio.create_task(alert_checker_async())
        _checker_thread_started = True
        
    if not _channel_thread_started:
        threading.Thread(target=channel_poster, daemon=True).start()
        threading.Thread(target=news_poster, daemon=True).start()
        _channel_thread_started = True

@bot.event
async def on_message(message: Message):
    if not message.content or message.author.is_bot or message.chat.type != 'private': return
    if str(getattr(message, 'message_id', '')) in _sent_channel_message_ids: return
    
    cid = str(message.author.id)
    txt = message.content.strip()
    state = user_states.get(cid, {})
    
    if txt == "/myid":
        await message.reply(f"🆔 Chat ID: `{cid}`"); return

    if txt.startswith("/start"):
        u = await get_active_user(cid)
        if is_admin(cid): await message.reply("👨‍💻 پنل مدیریت:", components=admin_kb())
        if u:
            if not await check_member(cid): await message.reply(t("force_join_title") + "\n\n" + t("force_join_text", channel=CHANNEL_ID), components=force_join_keyboard()); return
            await show_main_menu(message, cid)
        else:
            ref = txt.split()[1] if len(txt.split()) > 1 and txt.split()[1].isdigit() else None
            user_states[cid] = {"state": "awaiting_name", "data": {"ref": ref}}
            await message.reply(t("welcome_new"))
        return

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

    if state.get("state") == "awaiting_name":
        if len(txt) < 3: await message.reply(t("invalid_name")); return
        await create_user(cid, txt, state["data"].get("ref"))
        user_states.pop(cid, None); clear_lang(cid)
        await message.reply(t("register_success", name=txt, lang_name="فارسی") + footer_text(), components=main_menu_keyboard()); return

    if state.get("state") == "conv_amount":
        try:
            amt = float(txt.replace(",", ""))
            f, to = state["data"]["from"], state["data"]["to"]
            p1, p2 = get_price(f), get_price(to)
            if p1 and p2:
                res = amt * p1 / p2
                user_states.pop(cid, None)
                await message.reply(f"🔄 {amt:,.2f} {get_asset_display_name(f)} = **{res:,.4f} {get_asset_display_name(to)}**", components=main_menu_keyboard()); return
        except: await message.reply("❌ عدد معتبر وارد کنید."); return

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

    if data == "LANG:fa":
        user_states[cid] = {"state": "awaiting_name", "data": user_states.get(cid, {}).get("data", {})}
        await callback.message.edit(t("welcome_new")); return

    if data == "FORCEJOIN:VERIFY":
        _force_join_cache.pop(cid, None)
        if await check_member(cid, False):
            u = await get_active_user(cid)
            if u: await show_main_menu(callback.message, cid, True)
            else:
                user_states[cid] = {"state": "awaiting_name", "data": {}}
                await callback.message.edit(t("welcome_new"))
        else: await callback.message.edit(t("force_join_not_member"), components=force_join_keyboard())
        return

    if not await get_user(cid): return

    if data == "MENU:MAIN": user_states.pop(cid, None); await show_main_menu(callback.message, cid, True); return
    if data == "MENU:CRYPTO": await callback.message.edit(t("crypto_title"), components=get_assets_kb("CRYPTO", POPULAR_CRYPTOS)); return
    if data == "MENU:FIAT": await callback.message.edit(t("fiat_title"), components=get_assets_kb("FIAT", POPULAR_FIATS)); return
    if data == "MENU:GOLD": await callback.message.edit(t("gold_title"), components=get_assets_kb("GOLD", POPULAR_GOLDS)); return
    
    if data == "MENU:OIL":
        o = get_oil(); txt = f"🛢️ **نفت برنت**\n💰 {format_price(o['price'])} {o['currency']}" if o else "❌ نامشخص"
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN"))); return

    if data.startswith(("CRYPTO:", "FIAT:", "GOLD:")):
        sym = data.split(":")[1]; p = get_price(sym)
        txt = f"💰 **{get_asset_display_name(sym)}**: **{format_price(p)} تومان**" if p else "❌ یافت نشد."
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN"))); return

    if data == "MENU:INVITE":
        link = f"https://ble.ir/{BOT_USERNAME}?start={cid}"; count = await get_inv_count(cid)
        txt = f"🎁 **دعوت دوستان**\n\n🔗 `{link}`\n\n👥 تعداد دعوت: **{count}**\n📍 رتبه شما: **{await get_rank(cid)}**"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton(text="📤 اشتراک", url=f"https://ble.ir/share/url?url={link}"), row=0).add(InlineKeyboardButton(text="🏆 جدول قهرمانان", callback_data="MENU:LEADERBOARD"), row=1).add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN"), row=2)
        await callback.message.edit(txt + footer_text(), components=kb); return

    if data == "MENU:LEADERBOARD":
        top = await users_collection.find({"invite_count": {"$gt": 0}}).sort("invite_count", -1).limit(10).to_list(10)
        if not top: txt = "🏆 **جدول قهرمانان**\n\nهنوز هیچ کاربری کسی رو دعوت نکرده. اولین نفر باش!"
        else:
            lines = ["🏆 **جدول قهرمانان**", "━━━━━━━━━━━━━━━━━━"]
            for i, u in enumerate(top):
                m = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                lines.append(f"{m} {u['name']} → *{u.get('invite_count', 0)}* دعوت")
            lines.append(f"\n📍 رتبه شما: **{await get_rank(cid)}** با **{await get_inv_count(cid)}** دعوت")
            txt = "\n".join(lines)
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN"))); return

    if data == "MENU:PROFILE":
        u = await get_user(cid); ut = "کاربر خاص ⭐" if u.get('special_user') else "کاربر عادی 👤"
        txt = f"👤 **پروفایل شما**\n\n📝 نام: {u['name']}\n👑 نوع حساب: {ut}\n🎁 دعوت‌ها: {u.get('invite_count', 0)}"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton(text="🚪 خروج از حساب", callback_data="PROF:OUT"), row=0).add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN"), row=1)
        await callback.message.edit(txt + footer_text(), components=kb); return

    if data == "PROF:OUT":
        await users_collection.update_one({"chat_id": cid}, {"$set": {"account_status": "logged_out"}})
        await callback.message.edit("✅ از حساب خارج شدید.\n\nبرای ساخت پروفایل جدید، /start را بزنید."); return

    if data == "MENU:HELP":
        txt = f"ℹ️ **راهنمای ارز آنلاین**\n\nبه ربات جامع *ارز آنلاین* خوش آمدید! 👋\nاین ربات در ابتدا در پیام‌رسان *بله* فعالیت خود را آغاز کرد و حالا به عنوان شعبه دوم، در تلگرام نیز در خدمت شماست! 🚀\n\n🌟 **امکانات ربات:**\n🪙 مشاهده قیمت لحظه‌ای رمزارزها\n💵 قیمت دلار، یورو و...\n🥇 قیمت طلا و سکه\n🛢️ قیمت نفت برنت\n🔄 مبدل ارز\n⭐ علاقه‌مندی‌ها\n🔔 هشدار قیمت (ویژه کاربران حرفه‌ای)\n🎁 دعوت دوستان و پاداش\n\n🔒 برای استفاده از «هشدار قیمت»، باید حداقل ۵ نفر را با لینک دعوت خود بیاورید."
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN"))); return

    if data == "MENU:MARKET":
        txt = f"📊 *بازار امروز*\n💵 دلار: {format_price(get_price('USD'))}\n🥇 طلا: {format_price(get_price('gold_18'))}\n🪙 BTC: {format_price(get_price('BTC'))}\n🛢️ نفت: {format_price(get_oil()['price'] if get_oil() else 0)}"
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="MENU:MARKET"), row=0).add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN"), row=1)); return

    if data in ("ALERT:NEW", "MENU:MYALERTS") or data.startswith("ALERT:"):
        if not await has_pro(cid):
            await callback.message.edit("🔒 **دسترسی محدود**\n\nاین قابلیت مخصوص کاربران حرفه‌ای است.\nبرای باز شدن، باید حداقل **۵ نفر** را با لینک دعوت خود به ربات بیاورید.\n\nاز منوی اصلی به بخش «🎁 دعوت دوستان» بروید.", components=main_menu_keyboard()); return

    if data == "ALERT:NEW": await callback.message.edit("🔔 دسته‌بندی:", components=alert_cat_kb()); return
    if data.startswith("ALERT:CAT:"):
        cat = data.split(":")[2]; assets = POPULAR_CRYPTOS if cat == "crypto" else POPULAR_FIATS if cat == "fiat" else POPULAR_GOLDS
        await callback.message.edit("🔔 دارایی:", components=get_assets_kb("ALERT:SET", assets)); return
    if data.startswith("ALERT:SET:"):
        user_states[cid] = {"state": "alert_price", "data": {"asset": data.split(":")[2]}}
        await callback.message.edit("🎯 قیمت هدف (تومان):"); return
    if data.startswith("ALERT:DIR:"):
        d = data.split(":")[2]; asset = user_states[cid]["data"]["asset"]; p = user_states[cid]["data"]["price"]
        await alerts_collection.update_one({"chat_id": cid, "asset": asset}, {"$set": {"target_price": p, "direction": d, "created_at": time.time()}}, upsert=True)
        user_states.pop(cid, None); await callback.message.edit(f"✅ هشدار ثبت شد: {get_asset_display_name(asset)} → {format_price(p)}", components=main_menu_keyboard()); return

    if data == "CONV:NEW": await callback.message.edit("🔄 مرحله ۱: ارز مبدا:", components=get_assets_kb("CONV:FROM", ["TOMAN", "USD", "EUR", "BTC", "ETH", "USDT", "gold_18", "coin_emami"])); return
    if data.startswith("CONV:FROM:"): await callback.message.edit("🔄 مرحله ۲: ارز مقصد:", components=get_assets_kb(f"CONV:TO:{data.split(':')[2]}", ["TOMAN", "USD", "EUR", "BTC", "ETH", "USDT", "gold_18", "coin_emami"])); return
    if data.startswith("CONV:TO:"):
        parts = data.split(":")
        user_states[cid] = {"state": "conv_amount", "data": {"from": parts[2], "to": parts[3]}}
        await callback.message.edit(f"✅ {get_asset_display_name(parts[2])} به {get_asset_display_name(parts[3])}\n\nحالا مقدار را تایپ کنید:"); return

    if data == "FAV:VIEW":
        favs = await favorites_collection.find({"chat_id": cid}).to_list(20)
        if not favs: return await callback.message.edit("⭐ لیست خالیه!", components=InlineKeyboardMarkup().add(InlineKeyboardButton(text="➕ افزودن", callback_data="FAV:ADD")).add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN")))
        txt = "⭐ **علاقه‌مندی‌ها:**\n\n" + "\n".join([f"🔸 {get_asset_display_name(f['asset'])}: {format_price(get_price(f['asset']))}" for f in favs])
        await callback.message.edit(txt + footer_text(), components=InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="MENU:MAIN"))); return
    if data == "FAV:ADD":
        await callback.message.edit("⭐ دارایی:", components=get_assets_kb("FAV:SET", ["BTC", "ETH", "USDT", "USD", "EUR", "gold_18", "coin_emami"])); return
    if data.startswith("FAV:SET:"):
        asset = data.split(":")[2]
        await favorites_collection.update_one({"chat_id": cid, "asset": asset}, {"$set": {"created_at": time.time()}}, upsert=True)
        await callback.message.edit(f"✅ {get_asset_display_name(asset)} اضافه شد.", components=main_menu_keyboard()); return

# ==================== اجرا ====================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080)); app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()
    bot.run()
