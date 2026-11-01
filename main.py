import os
import re
import json
import time
import asyncio
import threading
import certifi
import aiohttp
import feedparser  # <--- اضافه شده برای اخبار
from flask import Flask
from bale import Bot, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

# ==================== تنظیمات ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DEVELOPER_NAME = os.environ.get("DEVELOPER_NAME", "مهدی نجفی")
FEEDBACK_ID = os.environ.get("FEEDBACK_ID", "@mahdi8iiii")
MONGO_URI = os.environ.get("MONGO_URI", "")

CRYPTO_API_URL = 'https://api.abantether.com/api/v1/manager/otc/ticker'
FIAT_API_URL = 'https://cdn.jsdelivr.net/gh/HosseinOdd/Navasan-API@main/data/fiat.json'
GOLD_API_URL = 'https://cdn.jsdelivr.net/gh/HosseinOdd/Navasan-API@main/data/gold.json'

# 📢 کانال اطلاع‌رسانی
CHANNEL_ID = "@nabz_mediaa"
CHANNEL_LINK = "https://ble.ir/nabz_mediaa"
CHANNEL_POST_INTERVAL = 3600
CHANNEL_POST_ENABLED = True

# 📰 تنظیمات اخبار
NEWS_RSS_URL = "https://www.yjc.ir/fa/rss/allnews"
NEWS_CHECK_INTERVAL = 1800  # هر 30 دقیقه چک میکند
NEWS_START_HOUR = 8
NEWS_END_HOUR = 24
_sent_news_ids = set()

# ✅ پروکسی
USE_PROXY = True
PROXY_URL = "https://red-meadow-20f7bale-bot-proxy.najafimahdi13867.workers.dev"
WELCOME_IMAGE_URL = ""

# 🔗 لینک ربات برای سیستم دعوت
BOT_USERNAME = "onlinearzmonybot"  # بدون @

# 👨‍💻 مدیران بات
ADMIN_IDS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
ADMIN_PAGE_SIZE = 8
PRO_INVITE_THRESHOLD = 5
# ==================================================


# ============================================================
#       سیستم ترجمه
# ============================================================
TRANSLATIONS = {
    "fa": {
        "choose_language": "🌐 لطفاً زبان خود را انتخاب کنید:",
        "welcome_new": "سلام! 👋\n\nبه *ارز آنلاین* خوش آمدید.\n\nبرای شروع فقط *نام و نام خانوادگی* خود را وارد کنید:",
        "ask_phone": "",
        "invalid_phone": "❌ شماره موبایل نامعتبر است.\nلطفاً شماره را به فرمت صحیح وارد کنید (مثال: 09123456789):",
        "invalid_name": "❌ نام معتبر نیست (حداقل ۳ حرف). لطفاً دوباره وارد کنید:",
        "register_success": "✅ *ثبت‌نام با موفقیت انجام شد!*\n\n👤 نام: *{name}*\n🌐 زبان: {lang_name}\n\nخوش آمدی! از منوی زیر استفاده کن:",
        "welcome_back": "👋 سلام *{name}* عزیز! خوش برگشتی.\n\nاز منوی زیر استفاده کن:",
        "menu_title": "🏠 *منوی اصلی*\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        "menu_crypto": "🪙 ارز دیجیتال",
        "menu_fiat": "💵 ارزهای فیات",
        "menu_gold": "🥇 طلا و سکه",
        "menu_oil": "🛢️ نفت برنت",
        "menu_convert": "🔄 مبدل ارز",
        "menu_market": "📊 بازار امروز",
        "menu_fav": "⭐ علاقه‌مندی‌ها",
        "menu_alert": "🔔 هشدار قیمت",
        "menu_myalerts": "📋 هشدارهای من",
        "menu_list": "📊 لیست رمزارزها",
        "menu_profile": "👤 پروفایل من",
        "menu_invite": "🎁 دعوت دوستان",
        "menu_leaderboard": "🏆 جدول قهرمانان",
        "menu_help": "ℹ️ راهنما",
        "help_title": "ℹ️ *راهنمای ارز آنلاین*",
        "help_text": "به *ارز آنلاین* خوش آمدی! 👋\n\nاین بات برای دسترسی سریع به قیمت ارزها، رمزارزها، طلا و سکه و چند ابزار کاربردی بازار ساخته شده است.\n\n🪙 *ارز دیجیتال*\nقیمت رمزارزها را ببین و از فهرست رمزارزها استفاده کن.\n\n💵 *ارزهای فیات*\nقیمت ارزهای رایج مثل دلار و یورو را بررسی کن.\n\n🥇 *طلا و سکه*\nقیمت طلا و انواع سکه را مشاهده کن.\n\n🛢️ *نفت برنت*\nقیمت لحظه‌ای نفت برنت را ببین.\n\n🔄 *مبدل ارز*\nمقدار یک ارز را به ارز دیگر تبدیل کن.\n\n⭐ *علاقه‌مندی‌ها*\nدارایی‌های مورد علاقه‌ات را ذخیره کن تا سریع‌تر به آن‌ها دسترسی داشته باشی.\n\n🔔 *هشدار قیمت*\nبرای یک دارایی قیمت هدف تعیین کن تا در صورت رسیدن قیمت به محدوده موردنظر، هشدار دریافت کنی.\n\n📋 *هشدارهای من*\nهشدارهای فعال خودت را ببین و مدیریت کن.\n\n🎁 *دعوت دوستان*\nلینک دعوت اختصاصی بگیر و دوستانت را به بات دعوت کن.\n\n🏆 *جدول قهرمانان*\nآمار دعوت کاربران را مشاهده کن.\n\n👤 *پروفایل من*\nاطلاعات حساب و تنظیمات زبانت را مدیریت کن. از همین بخش می‌توانی از حساب خارج شوی و بعداً دوباره ثبت‌نام کنی.\n\n📌 *چند نکته*\n• برای استفاده از هر قابلیت، کافی است از منوی اصلی گزینه مربوط را انتخاب کنی.\n• قیمت‌ها ممکن است با توجه به منبع داده و زمان بروزرسانی تغییر کنند.\n\n📢 *عضویت در کانال*\nبرای استفاده از بات، ابتدا باید عضو کانال اطلاع‌رسانی ارز آنلاین باشی. بعد از عضویت، دکمه «بررسی عضویت» را بزن تا دسترسی به بات فعال شود.\n\n📢 کانال: {channel}",
        "menu_main": "🏠 منوی اصلی",
        "menu_back": "🔙 بازگشت",
        "menu_cancel": "❌ انصراف",
        "profile_title": "👤 *پروفایل شما*",
        "profile_name": "📝 نام: *{name}*",
        "profile_phone": "📱 شماره: `{phone}`",
        "profile_lang": "🌐 زبان: {lang_name}",
        "profile_joined": "📅 تاریخ عضویت: {date}",
        "profile_invites": "🎁 تعداد دعوت‌شده‌ها: *{count}* نفر",
        "profile_user_type": "👑 نوع حساب: *{user_type}*",
        "user_type_special": "کاربر خاص ⭐",
        "user_type_normal": "کاربر عادی 👤",
        "pro_locked": "🔒 این قابلیت حرفه‌ای است.\n\nبرای فعال شدن دسترسی حرفه‌ای، حداقل *۵ نفر* را با لینک دعوت خودت به بات دعوت کن.\n\n🎁 دعوت موفق بیشتر = امکانات بیشتر",
        "pro_unlocked": "✨ دسترسی حرفه‌ای شما فعال است.",
        "profile_change_lang": "🌐 تغییر زبان",
        "profile_logout": "🚪 خروج از حساب",
        "logout_confirm": "⚠️ با خروج از حساب، پروفایل فعلی شما از حالت فعال خارج می‌شود و برای ورود بعدی باید دوباره ثبت‌نام کنید.\n\nآیا مطمئن هستید؟",
        "logout_done": "✅ از حساب خارج شدید.\n\nبرای ساخت پروفایل جدید، /start را بزنید.",
        "cancel": "✅ عملیات لغو شد.",
        "error": "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
        "not_found": "❌ یافت نشد.",
        "crypto_title": "🪙 *ارز دیجیتال*\n\nیکی از رمزارزها را انتخاب کنید:",
        "fiat_title": "💵 *ارزهای فیات*\n\nیکی از ارزها را انتخاب کنید:",
        "gold_title": "🥇 *طلا و سکه*\n\nیکی از گزینه‌ها را انتخاب کنید:",
        "market_title": "📊 *بازار امروز*",
        "footer": "\n\n━━━━━━━━━━━━━━━━━━\n👨‍💻 توسعه‌دهنده: *{dev}*\n📩 انتقادات: {feedback}",
        "force_join_title": "⚠️ *دسترسی محدود*",
        "force_join_text": "برای استفاده از ربات، لطفاً اول در کانال ما عضو شوید:\n\n📢 {channel}\n\nبعد از عضویت، روی دکمه زیر کلیک کنید:",
        "force_join_btn": "✅ عضو شدم",
        "force_join_verify": "🔄 بررسی عضویت",
        "force_join_not_member": "❌ شما هنوز در کانال عضو نشده‌اید.\n\nلطفاً ابتدا در کانال عضو شوید و سپس دکمه بررسی را بزنید.",
        "invite_title": "🎁 *سیستم دعوت دوستان*",
        "invite_link": "🔗 لینک دعوت اختصاصی شما:",
        "invite_stats": "📊 *آمار شما:*",
        "invite_count": "• تعداد دعوت‌شده‌ها: *{count}* نفر",
        "invite_rank": "• رتبه شما: *#{rank}*",
        "invite_reward": "\n🎁 *پاداش:*\n• ۵ دعوت: 🔔 قابلیت هشدار قیمت حرفه‌ای برای شما باز می‌شود.\n• با دعوت‌های بیشتر: رتبه شما در جدول قهرمانان بالاتر می‌رود.",
        "invite_copy": "📋 کپی لینک دعوت",
        "leaderboard_title": "🏆 *جدول قهرمانان*",
        "leaderboard_you": "\n📍 رتبه شما: *#{rank}* با *{count}* دعوت",
        "leaderboard_empty": "هنوز هیچ کاربری کسی رو دعوت نکرده. اولین نفر باش!",
        "share_btn": "📤 اشتراک‌گذاری با دوستان",
    }
}

LANG_NAMES = {"fa": "فارسی"}


def t(key, lang="fa", **kwargs):
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["fa"])
    text = lang_dict.get(key, TRANSLATIONS["fa"].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    return text


def footer_text(lang="fa"):
    return t("footer", lang, dev=DEVELOPER_NAME, feedback=FEEDBACK_ID)
# ============================================================


# ============================================================
#       پروکسی
# ============================================================
if USE_PROXY:
    _original_aiohttp_request = aiohttp.ClientSession._request

    async def _patched_aiohttp_request(self, method, url, *args, **kwargs):
        url_str = str(url)
        if 'tapi.bale.ai' in url_str:
            new_url = url_str.replace('https://tapi.bale.ai', PROXY_URL).replace('http://tapi.bale.ai', PROXY_URL)
            url_str = new_url
        return await _original_aiohttp_request(self, method, url_str, *args, **kwargs)

    aiohttp.ClientSession._request = _patched_aiohttp_request
    print("✅ Cloudflare Proxy override فعال شد!", flush=True)
# ============================================================


bot = Bot(token=BOT_TOKEN)

user_states = {}
MAIN_LOOP = None
CHANNEL_NUMERIC_ID = None
BOT_ID = None
_sent_channel_message_ids = set()
_channel_thread_started = False
_checker_thread_started = False
_user_lang_cache = {}
_force_join_cache = {}

# ============================================================
#       دیتابیس
# ============================================================
db_client = None
alerts_collection = None
favorites_collection = None
users_collection = None
referrals_collection = None
DB_READY = False


async def init_db():
    global db_client, alerts_collection, favorites_collection, users_collection, referrals_collection, DB_READY
    DB_READY = False
    if not MONGO_URI:
        return False
    try:
        db_client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())
        await db_client.admin.command('ping')
        db = db_client["bale_bot_db"]
        alerts_collection = db["alerts"]
        favorites_collection = db["favorites"]
        users_collection = db["users"]
        referrals_collection = db["referrals"]

        async def ensure_index(collection, keys, *, unique=False, name=None):
            if collection is None: return
            requested_keys = dict(keys) if isinstance(keys, list) else {keys: 1}
            try:
                existing_indexes = await collection.list_indexes().to_list(length=None)
                for idx in existing_indexes:
                    if dict(idx.get("key", {})) == requested_keys:
                        return
                options = {"unique": bool(unique)}
                if name: options["name"] = name
                await collection.create_index(keys, **options)
            except Exception as e:
                print(f"⚠️ Index warning: {e}", flush=True)

        await ensure_index(users_collection, "chat_id", unique=True, name="users_chat_id_unique")
        await ensure_index(alerts_collection, [("chat_id", 1), ("asset", 1)], unique=True, name="alerts_chat_asset_unique")
        await ensure_index(favorites_collection, [("chat_id", 1), ("asset", 1)], unique=True, name="favorites_chat_asset_unique")
        await ensure_index(referrals_collection, [("referrer", 1), ("referred", 1)], unique=True, name="referrals_referrer_referred_unique")

        DB_READY = True
        print("✅ اتصال به MongoDB با موفقیت برقرار شد!", flush=True)
        return True
    except Exception as e:
        print(f"❌ خطا در اتصال به MongoDB: {e}", flush=True)
        return False
# ============================================================


POPULAR_CRYPTOS = ["BTC", "ETH", "USDT", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "TON"]
POPULAR_FIATS = ["USD", "EUR", "AED", "TRY", "GBP", "IQD", "CNY", "JPY", "CAD", "AUD", "CHF", "SAR"]
POPULAR_GOLDS = ["gold_18", "coin_emami", "coin_half", "coin_quarter", "gold_miskal", "coin_bahar", "coin_gerami"]

FIAT_NAMES = {
    "USD": "دلار آمریکا", "EUR": "یورو", "GBP": "پوند انگلیس",
    "AED": "درهم امارات", "TRY": "لیر ترکیه", "CNY": "یوان چین",
    "JPY": "ین ژاپن", "CAD": "دلار کانادا", "AUD": "دلار استرالیا",
    "CHF": "فرانک سوئیس", "IQD": "دینار عراق", "SAR": "ریال عربستان",
    "KWD": "دینار کویت", "QAR": "ریال قطر", "OMR": "ریال عمان",
    "BHD": "دینار بحرین", "JOD": "دینار اردن", "RUB": "روبل روسیه",
    "INR": "روپیه هند", "PKR": "روپیه پاکستان", "AFN": "افغانی",
}

GOLD_NAMES = {
    "gold_18": "طلای ۱۸ عیار", "gold_24": "طلای ۲۴ عیار", "gold_miskal": "مثقال طلا",
    "coin_emami": "سکه امامی", "coin_bahar": "سکه بهار آزادی", "coin_half": "نیم سکه",
    "coin_quarter": "ربع سکه", "coin_gerami": "سکه گرمی",
}


def format_price(price_val):
    if price_val is None: return "نامشخص"
    try:
        price_num = float(price_val)
        return f"{int(price_num):,}" if price_num.is_integer() else f"{price_num:,.2f}"
    except (ValueError, TypeError):
        return str(price_val)


def get_user_id_from_message(message): return str(message.author.id)


def get_user_id_from_callback(callback):
    try:
        if hasattr(callback, 'from_user') and callback.from_user: return str(callback.from_user.id)
    except: pass
    try: return str(callback.message.author.id)
    except:
        try: return str(callback.message.chat.id)
        except: return None


def clear_state(user_id):
    if user_id in user_states: del user_states[user_id]


def get_asset_display_name(asset_key):
    if asset_key in GOLD_NAMES: return GOLD_NAMES[asset_key]
    if asset_key in FIAT_NAMES: return FIAT_NAMES[asset_key]
    if asset_key == "TOMAN": return "تومان"
    return asset_key


def _chat_id_variants(chat_id):
    sid = str(chat_id)
    variants = [sid]
    try:
        iid = int(sid)
        if iid != sid: variants.append(iid)
        elif iid not in variants: variants.append(iid)
    except (TypeError, ValueError): pass
    return variants


def _chat_id_filter(chat_id):
    variants = _chat_id_variants(chat_id)
    return {"chat_id": variants[0]} if len(variants) == 1 else {"chat_id": {"$in": variants}}


async def get_user(chat_id):
    if users_collection is None: return None
    for attempt in range(3):
        try:
            user = await users_collection.find_one(_chat_id_filter(chat_id))
            return user if user else None
        except Exception as e:
            print(f"⚠️ get_user error: {e}", flush=True)
            if attempt < 2: await asyncio.sleep(0.5)
    return None


async def get_active_user(chat_id):
    user = await get_user(chat_id)
    return user if user and user.get("account_status", "active") != "logged_out" else None


async def logout_user(chat_id):
    if users_collection is None: return False
    try:
        user = await get_user(chat_id)
        if not user: return False
        await users_collection.update_one({"_id": user["_id"]}, {"$set": {"account_status": "logged_out", "logged_out_at": time.time(), "updated_at": time.time()}, "$unset": {"phone": ""}})
        clear_state(str(chat_id)); clear_lang_cache(str(chat_id)); clear_force_join_cache(str(chat_id))
        return True
    except Exception as e: return False


async def set_user_blocked(chat_id, blocked=True):
    if users_collection is None: return False
    try:
        user = await get_user(chat_id)
        if not user: return False
        await users_collection.update_one({"_id": user["_id"]}, {"$set": {"blocked": bool(blocked), "updated_at": time.time()}})
        return True
    except Exception as e: return False


async def create_user(chat_id, name, phone=None, language="fa", referred_by=None):
    if users_collection is None: return False
    chat_id = str(chat_id)
    try:
        existing = await users_collection.find_one(_chat_id_filter(chat_id))
        if existing:
            update = {"name": name or existing.get("name", "کاربر"), "language": language or existing.get("language", "fa"), "account_status": "active", "updated_at": time.time(), "last_seen_at": time.time()}
            if phone is not None: update["phone"] = phone
            await users_collection.update_one({"_id": existing["_id"]}, {"$set": update})
            return True

        doc = {"chat_id": chat_id, "name": name or "کاربر", "language": language or "fa", "created_at": time.time(), "updated_at": time.time(), "last_seen_at": time.time(), "account_status": "active", "blocked": False, "special_user": False, "referred_by": str(referred_by) if referred_by else None, "invite_count": 0}
        await users_collection.insert_one(doc)

        if referred_by and str(referred_by) != chat_id and referrals_collection is not None:
            result = await referrals_collection.update_one({"referrer": str(referred_by), "referred": chat_id}, {"$setOnInsert": {"referrer": str(referred_by), "referred": chat_id, "created_at": time.time()}}, upsert=True)
            if result.upserted_id is not None:
                await users_collection.update_one(_chat_id_filter(referred_by), {"$inc": {"invite_count": 1}})
        return True
    except Exception as e: return False


async def touch_user(chat_id):
    if users_collection is None: return
    try: await users_collection.update_one(_chat_id_filter(chat_id), {"$set": {"last_seen_at": time.time()}})
    except: pass


async def get_user_language(chat_id):
    chat_id_str = str(chat_id)
    if chat_id_str in _user_lang_cache: return _user_lang_cache[chat_id_str]
    user = await get_user(chat_id_str)
    lang = user.get("language", "fa") if user else "fa"
    _user_lang_cache[chat_id_str] = lang
    return lang


def clear_lang_cache(chat_id):
    chat_id_str = str(chat_id)
    if chat_id_str in _user_lang_cache: del _user_lang_cache[chat_id_str]


async def get_users_count():
    if users_collection is None: return 0
    try: return await users_collection.count_documents({})
    except: return 0


async def get_invite_count(chat_id):
    if users_collection is None: return 0
    try:
        user = await users_collection.find_one({"chat_id": str(chat_id)})
        return user.get("invite_count", 0) if user else 0
    except: return 0


async def get_user_rank(chat_id):
    if users_collection is None: return 0
    try:
        my_count = await get_invite_count(chat_id)
        return await users_collection.count_documents({"invite_count": {"$gt": my_count}}) + 1
    except: return 0


async def get_leaderboard(limit=10):
    if users_collection is None: return []
    try:
        cursor = users_collection.find({"invite_count": {"$gt": 0}}).sort("invite_count", -1).limit(limit)
        return await cursor.to_list(length=limit)
    except: return []


async def is_special_user(chat_id):
    user = await get_user(chat_id)
    return bool(user and user.get("special_user") is True)


async def get_effective_invite_count(chat_id):
    user = await get_user(chat_id)
    return int(user.get("invite_count", 0) or 0) if user else 0


async def has_pro_access(chat_id):
    user = await get_user(chat_id)
    if not user or user.get("blocked"): return False
    if user.get("special_user") is True: return True
    return int(user.get("invite_count", 0) or 0) >= PRO_INVITE_THRESHOLD


async def set_special_user(chat_id, special=True):
    if users_collection is None: return False
    try:
        user = await get_user(chat_id)
        if not user: return False
        await users_collection.update_one({"_id": user["_id"]}, {"$set": {"special_user": bool(special), "updated_at": time.time()}})
        return True
    except Exception as e: return False


async def get_special_users_count():
    if users_collection is None: return 0
    try: return await users_collection.count_documents({"special_user": True})
    except Exception: return 0


async def add_alert(chat_id, asset_key, target_price, direction):
    if alerts_collection is None: return False
    try:
        target = float(target_price)
        if target <= 0 or direction not in {"above", "below"}: return False
        asset_key = str(asset_key).strip().upper()
        await alerts_collection.delete_many({"chat_id": str(chat_id), "asset": asset_key})
        await alerts_collection.insert_one({"chat_id": str(chat_id), "asset": asset_key, "target_price": target, "direction": direction, "created_at": time.time(), "triggered": False})
        return True
    except Exception as e: return False


async def get_user_alerts(chat_id):
    if alerts_collection is not None:
        cursor = alerts_collection.find({"chat_id": str(chat_id)})
        return await cursor.to_list(length=None)
    return []


async def remove_alert(chat_id, asset_key):
    if alerts_collection is not None: await alerts_collection.delete_one({"chat_id": str(chat_id), "asset": asset_key})


async def get_all_alerts():
    if alerts_collection is not None:
        cursor = alerts_collection.find({})
        return await cursor.to_list(length=None)
    return []


async def remove_all_user_alerts(chat_id):
    if alerts_collection is None: return 0
    result = await alerts_collection.delete_many({"chat_id": str(chat_id)})
    return result.deleted_count


async def add_favorite(chat_id, asset_key):
    if favorites_collection is not None:
        existing = await favorites_collection.find_one({"chat_id": str(chat_id), "asset": asset_key})
        if existing is None:
            await favorites_collection.insert_one({"chat_id": str(chat_id), "asset": asset_key, "created_at": time.time()})
            return True
        return False
    return False


async def remove_favorite(chat_id, asset_key):
    if favorites_collection is not None: await favorites_collection.delete_one({"chat_id": str(chat_id), "asset": asset_key})


async def get_user_favorites(chat_id):
    if favorites_collection is not None:
        cursor = favorites_collection.find({"chat_id": str(chat_id)})
        docs = await cursor.to_list(length=None)
        return [d["asset"] for d in docs]
    return []


async def is_favorite(chat_id, asset_key): return asset_key in await get_user_favorites(chat_id)


async def check_channel_membership(user_id, use_cache=True):
    user_id = str(user_id)
    now = time.time()
    if use_cache and user_id in _force_join_cache:
        cached_at = _force_join_cache[user_id]
        if (now - cached_at) < 60: return True
        _force_join_cache.pop(user_id, None)

    api_url = f"https://tapi.bale.ai/bot{BOT_TOKEN}/getChatMember"
    payload = {"chat_id": CHANNEL_ID, "user_id": int(user_id)}
    try:
        def _direct_membership_request(): return requests.post(api_url, json=payload, timeout=15)
        response = await asyncio.to_thread(_direct_membership_request)
        try: body = response.json()
        except: body = {}

        if response.status_code != 200 or not body.get("ok", False):
            _force_join_cache.pop(user_id, None); return False

        result = body.get("result") or {}
        raw_status = result.get("status")
        status_candidates = {str(raw_status).strip().lower(), str(getattr(raw_status, "value", "")).strip().lower(), str(getattr(raw_status, "name", "")).strip().lower()}
        status_candidates.discard("")

        is_member = bool(status_candidates.intersection({"member", "administrator", "creator", "admin", "owner", "chatmemberstatus.member", "chatmemberstatus.administrator", "chatmemberstatus.creator"}))
        if not is_member:
            for candidate in status_candidates:
                if candidate.endswith(".member") or candidate.endswith(".administrator") or candidate.endswith(".creator"):
                    is_member = True
                    break

        if is_member: _force_join_cache[user_id] = now
        else: _force_join_cache.pop(user_id, None)
        return is_member

    except Exception:
        _force_join_cache.pop(user_id, None)
        try:
            response = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=int(user_id))
            if response is None: return False
            raw_status = getattr(response, "status", None)
            status_candidates = {str(raw_status).strip().lower(), str(getattr(raw_status, "value", "")).strip().lower(), str(getattr(raw_status, "name", "")).strip().lower()}
            status_candidates.discard("")
            is_member = bool(status_candidates.intersection({"member", "administrator", "creator", "admin", "owner", "chatmemberstatus.member", "chatmemberstatus.administrator", "chatmemberstatus.creator"}))
            if not is_member: is_member = any(x.endswith(".member") or x.endswith(".administrator") or x.endswith(".creator") for x in status_candidates)
            if is_member: _force_join_cache[user_id] = now
            return is_member
        except: return False


def clear_force_join_cache(user_id): _force_join_cache.pop(str(user_id), None)

_fiat_cache = {"data": None, "timestamp": 0}
_FIAT_CACHE_TTL = 120
_gold_cache = {}
_GOLD_CACHE_TTL = 45
_price_cache = {}
_PRICE_CACHE_TTL = 20

def _get_all_fiat_data():
    now = time.time()
    if _fiat_cache["data"] and (now - _fiat_cache["timestamp"]) < _FIAT_CACHE_TTL: return _fiat_cache["data"]
    try:
        response = requests.get(FIAT_API_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = response.json()
        if isinstance(data, dict):
            _fiat_cache["data"] = data
            _fiat_cache["timestamp"] = now
            return data
    except: pass
    return _fiat_cache["data"]

def fetch_fiat_data(symbol: str):
    try:
        data = _get_all_fiat_data()
        if not data or symbol.lower() not in data: return None
        price_data = data[symbol.lower()]
        price = price_data.get("value") or price_data.get("price") or price_data.get("rate") if isinstance(price_data, dict) else price_data
        if price is not None:
            price_in_toman = float(str(price).replace(",", ""))
            if price_in_toman > 10_000_000: price_in_toman = price_in_toman / 10
            return {"symbol": symbol.upper(), "price": price_in_toman}
        return None
    except: return None

_abantether_cache = {"data": None, "timestamp": 0}
_ABAN_CACHE_TTL = 60

def _get_abantether_data():
    now = time.time()
    if _abantether_cache["data"] and (now - _abantether_cache["timestamp"]) < _ABAN_CACHE_TTL: return _abantether_cache["data"]
    for attempt, timeout in enumerate([20, 25, 30]):
        try:
            response = requests.get(CRYPTO_API_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
            data = response.json()
            _abantether_cache["data"] = data
            _abantether_cache["timestamp"] = now
            return data
        except:
            time.sleep(2)
    return None

def _fetch_abantether(symbol):
    try:
        market = _get_abantether_data()
        if not market: return None
        markets_data = market.get("data", {}).get("markets", {})
        target_key = None
        data = None
        if isinstance(markets_data, dict):
            if symbol in markets_data: target_key = symbol
            elif f"{symbol}IRT" in markets_data: target_key = f"{symbol}IRT"
            else:
                for key in markets_data.keys():
                    if symbol in key.upper():
                        target_key = key
                        break
            if target_key: data = markets_data[target_key]
        elif isinstance(markets_data, list):
            for item in markets_data:
                item_symbol = str(item.get("symbol", "")).upper()
                if item_symbol == symbol or item_symbol == f"{symbol}IRT" or symbol in item_symbol:
                    target_key = item_symbol; data = item; break
        if target_key and data:
            return {"symbol": target_key, "buy_price": data.get("buy_price"), "sell_price": data.get("sell_price"), "change": data.get("price_change")}
        return None
    except: return None

def _fetch_nobitex_crypto(symbol):
    try:
        response = requests.get(f"https://api.nobitex.ir/v2/orderbook/{symbol}IRT", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = response.json()
        if data.get("status") == "ok":
            last_price = data.get("lastTradePrice")
            if last_price:
                price_in_toman = float(last_price) / 10
                return {"symbol": symbol, "buy_price": price_in_toman, "sell_price": price_in_toman, "change": None}
        return None
    except: return None

def fetch_crypto_data(symbol: str):
    symbol = symbol.strip().upper()
    data = _fetch_abantether(symbol)
    if data: return data
    return _fetch_nobitex_crypto(symbol)

def _get_json_price(data, keys_list):
    if data is None: return None
    if isinstance(data, (int, float, str)):
        try: return float(str(data).replace(",", ""))
        except: return None
    if isinstance(data, dict):
        for key in keys_list:
            if key in data:
                val = data[key]
                if isinstance(val, (int, float, str)):
                    try: return float(str(val).replace(",", ""))
                    except: pass
                elif isinstance(val, dict):
                    for sub_key in ["value", "price", "rate", "close", "p"]:
                        if sub_key in val:
                            try: return float(str(val[sub_key]).replace(",", ""))
                            except: pass
        for val in data.values():
            if isinstance(val, (int, float)): return float(val)
            elif isinstance(val, dict):
                for sub_val in val.values():
                    if isinstance(sub_val, (int, float)): return float(sub_val)
    if isinstance(data, list) and len(data) > 0: return _get_json_price(data[0], keys_list)
    return None

def _fetch_gold_data_uncached(asset_key: str):
    key_map = {"gold_18": "18ayar", "coin_emami": "sekkeh", "coin_bahar": "bahar", "coin_half": "nim", "coin_quarter": "rob", "coin_gerami": "gerami"}
    try:
        response = requests.get(GOLD_API_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = response.json()
        if not isinstance(data, dict): return None
        if asset_key in key_map and key_map[asset_key] in data:
            price = _get_json_price(data[key_map[asset_key]], ["value", "price", "rate"])
            if price is not None: return {"symbol": asset_key, "price": price}
        if asset_key == "gold_24":
            price_18 = _get_json_price(data.get("18ayar"), ["value", "price"])
            if price_18: return {"symbol": asset_key, "price": price_18 * (24 / 18)}
        if asset_key == "gold_miskal":
            price_18 = _get_json_price(data.get("18ayar"), ["value", "price"])
            if price_18: return {"symbol": asset_key, "price": price_18 * 4.608}
        return None
    except: return None

def fetch_gold_data(asset_key: str):
    now = time.time()
    cached = _gold_cache.get(asset_key)
    if cached and (now - cached["timestamp"]) < _GOLD_CACHE_TTL: return cached["data"]
    data = _fetch_gold_data_uncached(asset_key)
    if data:
        _gold_cache[asset_key] = {"data": data, "timestamp": now}
        return data
    return cached["data"] if cached else None

def get_current_price(asset_key: str):
    key = str(asset_key).strip().upper()
    now = time.time()
    cached = _price_cache.get(key)
    if cached and (now - cached["timestamp"]) < _PRICE_CACHE_TTL: return cached["data"]

    if key == "TOMAN": data = {"symbol": "TOMAN", "price": 1.0}
    elif key.lower() in GOLD_NAMES: data = fetch_gold_data(key.lower())
    elif key in FIAT_NAMES: data = fetch_fiat_data(key)
    else:
        crypto = fetch_crypto_data(key)
        data = {"symbol": crypto["symbol"], "price": crypto["buy_price"]} if crypto else None

    if data and data.get("price") is not None: _price_cache[key] = {"data": data, "timestamp": now}
    return data


# ============================================================
#                     کیبوردها
# ============================================================
def language_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="LANG:fa"), row=0)
    return markup

def main_menu_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=t("menu_crypto", lang), callback_data="MENU:CRYPTO"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_fiat", lang), callback_data="MENU:FIAT"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_gold", lang), callback_data="MENU:GOLD"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_oil", lang), callback_data="MENU:OIL"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_convert", lang), callback_data="CONV:NEW"), row=2)
    markup.add(InlineKeyboardButton(text=t("menu_market", lang), callback_data="MENU:MARKET"), row=2)
    markup.add(InlineKeyboardButton(text=t("menu_fav", lang), callback_data="FAV:VIEW"), row=3)
    markup.add(InlineKeyboardButton(text=t("menu_alert", lang), callback_data="ALERT:NEW"), row=3)
    markup.add(InlineKeyboardButton(text=t("menu_myalerts", lang), callback_data="MENU:MYALERTS"), row=4)
    markup.add(InlineKeyboardButton(text=t("menu_list", lang), callback_data="MENU:LIST"), row=4)
    markup.add(InlineKeyboardButton(text=t("menu_invite", lang), callback_data="MENU:INVITE"), row=5)
    markup.add(InlineKeyboardButton(text=t("menu_leaderboard", lang), callback_data="MENU:LEADERBOARD"), row=5)
    markup.add(InlineKeyboardButton(text=t("menu_profile", lang), callback_data="MENU:PROFILE"), row=6)
    markup.add(InlineKeyboardButton(text=t("menu_help", lang), callback_data="MENU:HELP"), row=7)
    return markup

def market_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🪙 رمزارزها", callback_data="MENU:CRYPTO"), row=0)
    markup.add(InlineKeyboardButton(text="💵 ارزها", callback_data="MENU:FIAT"), row=0)
    markup.add(InlineKeyboardButton(text="🥇 طلا و سکه", callback_data="MENU:GOLD"), row=1)
    markup.add(InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="MARKET:REFRESH"), row=2)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=3)
    return markup

def force_join_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=f"📢 {CHANNEL_ID}", url=CHANNEL_LINK), row=0)
    markup.add(InlineKeyboardButton(text=t("force_join_verify", lang), callback_data="FORCEJOIN:VERIFY"), row=1)
    return markup

def invite_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=t("invite_copy", lang), callback_data="INVITE:COPY"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_leaderboard", lang), callback_data="MENU:LEADERBOARD"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
    return markup

def leaderboard_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=t("menu_invite", lang), callback_data="MENU:INVITE"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=1)
    return markup

def help_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=0)
    return markup

def crypto_menu_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    pairs = [POPULAR_CRYPTOS[i:i+2] for i in range(0, len(POPULAR_CRYPTOS), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair: markup.add(InlineKeyboardButton(text=sym, callback_data=f"CRYPTO:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text=t("menu_list", lang), callback_data="MENU:LIST"), row=next_row)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=next_row + 1)
    return markup

def fiat_menu_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    pairs = [POPULAR_FIATS[i:i+2] for i in range(0, len(POPULAR_FIATS), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair: markup.add(InlineKeyboardButton(text=f"{FIAT_NAMES.get(sym, sym)}", callback_data=f"FIAT:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=next_row)
    return markup

def gold_menu_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    pairs = [POPULAR_GOLDS[i:i+2] for i in range(0, len(POPULAR_GOLDS), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair: markup.add(InlineKeyboardButton(text=GOLD_NAMES.get(sym, sym), callback_data=f"GOLD:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=next_row)
    return markup

def profile_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=t("menu_invite", lang), callback_data="MENU:INVITE"), row=0)
    markup.add(InlineKeyboardButton(text=t("profile_change_lang", lang), callback_data="MENU:LANG"), row=1)
    markup.add(InlineKeyboardButton(text=t("profile_logout", lang), callback_data="PROFILE:LOGOUT"), row=2)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=3)
    return markup

def logout_confirm_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="✅ بله، خروج", callback_data="PROFILE:LOGOUT:CONFIRM"), row=0)
    markup.add(InlineKeyboardButton(text="❌ انصراف", callback_data="MENU:PROFILE"), row=1)
    return markup

def alert_asset_category_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🪙 رمزارز", callback_data="ALERT:CAT:crypto"), row=0)
    markup.add(InlineKeyboardButton(text="💱 ارز فیات", callback_data="ALERT:CAT:fiat"), row=0)
    markup.add(InlineKeyboardButton(text="🥇 طلا و سکه", callback_data="ALERT:CAT:gold"), row=1)
    markup.add(InlineKeyboardButton(text="✏️ وارد کردن نام دستی", callback_data="ALERT:MANUAL"), row=2)
    markup.add(InlineKeyboardButton(text=t("menu_cancel", lang), callback_data="ALERT:CANCEL"), row=3)
    return markup

def alert_asset_list_keyboard(category, lang="fa"):
    markup = InlineKeyboardMarkup()
    assets = POPULAR_CRYPTOS[:8] if category == "crypto" else POPULAR_FIATS[:8] if category == "fiat" else POPULAR_GOLDS[:6] if category == "gold" else []
    pairs = [assets[i:i+2] for i in range(0, len(assets), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            markup.add(InlineKeyboardButton(text=GOLD_NAMES.get(sym, FIAT_NAMES.get(sym, sym)), callback_data=f"ALERT:SET:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text=t("menu_back", lang), callback_data="ALERT:NEW"), row=next_row)
    markup.add(InlineKeyboardButton(text=t("menu_cancel", lang), callback_data="ALERT:CANCEL"), row=next_row + 1)
    return markup

def alert_direction_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="📈 وقتی از این قیمت بالا رفت", callback_data="ALERT:DIR:above"), row=0)
    markup.add(InlineKeyboardButton(text="📉 وقتی از این قیمت پایین آمد", callback_data="ALERT:DIR:below"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_cancel", lang), callback_data="ALERT:CANCEL"), row=2)
    return markup

def convert_from_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="دلار 🇺🇸", callback_data="CONV:FROM:USD"), row=0)
    markup.add(InlineKeyboardButton(text="یورو 🇪🇺", callback_data="CONV:FROM:EUR"), row=0)
    markup.add(InlineKeyboardButton(text="تومان 🇮🇷", callback_data="CONV:FROM:TOMAN"), row=1)
    markup.add(InlineKeyboardButton(text="BTC", callback_data="CONV:FROM:BTC"), row=2)
    markup.add(InlineKeyboardButton(text="ETH", callback_data="CONV:FROM:ETH"), row=2)
    markup.add(InlineKeyboardButton(text="USDT", callback_data="CONV:FROM:USDT"), row=2)
    markup.add(InlineKeyboardButton(text="🥇 طلای ۱۸", callback_data="CONV:FROM:gold_18"), row=3)
    markup.add(InlineKeyboardButton(text="🪙 سکه امامی", callback_data="CONV:FROM:coin_emami"), row=3)
    markup.add(InlineKeyboardButton(text=t("menu_cancel", lang), callback_data="CONV:CANCEL"), row=4)
    return markup

def convert_to_keyboard(from_asset, lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="تومان 🇮🇷", callback_data="CONV:TO:TOMAN"), row=0)
    markup.add(InlineKeyboardButton(text="دلار 🇺🇸", callback_data="CONV:TO:USD"), row=0)
    markup.add(InlineKeyboardButton(text="یورو 🇪🇺", callback_data="CONV:TO:EUR"), row=1)
    markup.add(InlineKeyboardButton(text="BTC", callback_data="CONV:TO:BTC"), row=2)
    markup.add(InlineKeyboardButton(text="ETH", callback_data="CONV:TO:ETH"), row=2)
    markup.add(InlineKeyboardButton(text="🪙 سکه امامی", callback_data="CONV:TO:coin_emami"), row=3)
    markup.add(InlineKeyboardButton(text="🥇 طلای ۱۸", callback_data="CONV:TO:gold_18"), row=3)
    markup.add(InlineKeyboardButton(text=t("menu_cancel", lang), callback_data="CONV:CANCEL"), row=4)
    return markup

def alerts_list_keyboard(alerts, user_id, lang="fa"):
    markup = InlineKeyboardMarkup()
    visible = alerts[:12]
    for idx, a in enumerate(visible):
        direction_sym = "↑" if a.get("direction") == "above" else "↓"
        markup.add(InlineKeyboardButton(text=f"🗑 {get_asset_display_name(a.get('asset', ''))} {direction_sym} {format_price(a.get('target_price'))}", callback_data=f"DELALERT:{a.get('asset','')}"), row=idx)
    row = len(visible)
    if len(alerts) > 12:
        markup.add(InlineKeyboardButton(text=f"ℹ️ {len(alerts)-12} هشدار دیگر", callback_data="MENU:MYALERTS"), row=row)
        row += 1
    markup.add(InlineKeyboardButton(text="🗑 حذف همه هشدارها", callback_data="DELALERT:ALL"), row=row)
    markup.add(InlineKeyboardButton(text="➕ هشدار جدید", callback_data="ALERT:NEW"), row=row + 1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=row + 2)
    return markup

def fav_category_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🪙 رمزارز", callback_data="FAV:CAT:crypto"), row=0)
    markup.add(InlineKeyboardButton(text="💱 ارز فیات", callback_data="FAV:CAT:fiat"), row=0)
    markup.add(InlineKeyboardButton(text="🥇 طلا و سکه", callback_data="FAV:CAT:gold"), row=1)
    markup.add(InlineKeyboardButton(text="📋 لیست علاقه‌مندی‌های من", callback_data="FAV:VIEW"), row=2)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=3)
    return markup

def fav_asset_list_keyboard(category, user_favs, lang="fa"):
    markup = InlineKeyboardMarkup()
    assets = POPULAR_CRYPTOS[:8] if category == "crypto" else POPULAR_FIATS[:8] if category == "fiat" else POPULAR_GOLDS[:6] if category == "gold" else []
    pairs = [assets[i:i+2] for i in range(0, len(assets), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            name = GOLD_NAMES.get(sym, FIAT_NAMES.get(sym, sym))
            label = f"✅ {name}" if sym in user_favs else f"➕ {name}"
            callback = f"FAV:DEL:{sym}" if sym in user_favs else f"FAV:ADD:{sym}"
            markup.add(InlineKeyboardButton(text=label, callback_data=callback), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text=t("menu_back", lang), callback_data="FAV:NEW"), row=next_row)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=next_row + 1)
    return markup

def fav_view_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="➕ افزودن دارایی جدید", callback_data="FAV:NEW"), row=0)
    markup.add(InlineKeyboardButton(text="🔄 به‌روزرسانی قیمت‌ها", callback_data="FAV:VIEW"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
    return markup


# ============================================================
#                       پردازش‌ها
# ============================================================
async def show_main_menu(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    user = await get_active_user(user_id)
    name = user.get("name", "کاربر") if user else "کاربر"
    text = f"✨ *ارز آنلاین* ✨\n\n{t('welcome_back', lang, name=name)}\n\n{t('menu_title', lang)}\n\n📌 قیمت لحظه‌ای ارز، رمزارز، طلا و سکه\n⚡ سریع • دقیق • همیشه در دسترس"
    markup = main_menu_keyboard(lang)
    if edit:
        try: await target.edit(text + footer_text(lang), components=markup); return
        except: pass
    await target.reply(text + footer_text(lang), components=markup)

async def show_market_dashboard(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    lines = [t("market_title", lang), "━━━━━━━━━━━━━━━━━━", "🪙 *رمزارزها*"]
    for symbol in ["BTC", "ETH", "USDT"]:
        data = get_current_price(symbol)
        if data and data.get("price") is not None:
            change_text = ""
            if data.get("change"):
                try:
                    val = float(data["change"])
                    change_text = f" {'🟢' if val > 0 else '🔴' if val < 0 else '⚪'} {'+' if val > 0 else ''}{val:.2f}%"
                except: pass
            lines.append(f"• {get_asset_display_name(symbol)}: *{format_price(data['price'])} تومان*{change_text}")
        else: lines.append(f"• {get_asset_display_name(symbol)}: نامشخص")

    lines.append("\n💵 *ارزهای فیات*")
    for symbol in ["USD", "EUR"]:
        data = get_current_price(symbol)
        lines.append(f"• {FIAT_NAMES.get(symbol, symbol)}: *{format_price(data['price']) if data else 'نامشخص'} تومان*")

    lines.append("\n🥇 *طلا و سکه*")
    for symbol in ["gold_18", "coin_emami"]:
        data = get_current_price(symbol)
        lines.append(f"• {GOLD_NAMES.get(symbol, symbol)}: *{format_price(data['price']) if data else 'نامشخص'} تومان*")

    lines.append("\n🕐 قیمت‌ها هنگام باز کردن این صفحه دریافت شده‌اند.")
    markup = market_keyboard(lang)
    if edit:
        try: await target.edit("\n".join(lines) + footer_text(lang), components=markup); return
        except: pass
    await target.reply("\n".join(lines) + footer_text(lang), components=markup)

async def show_help(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    text = t("help_title", lang) + "\n\n" + t("help_text", lang).format(channel=CHANNEL_ID)
    markup = help_keyboard(lang)
    if edit:
        try: await target.edit(text + footer_text(lang), components=markup); return
        except: pass
    await target.reply(text + footer_text(lang), components=markup)

async def show_profile(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    user = await get_user(user_id)
    if not user: return await target.reply(t("error", lang))
    joined = time.strftime('%Y-%m-%d', time.localtime(user.get("created_at", 0))) if user.get("created_at") else "-"
    text = f"{t('profile_title', lang)}\n━━━━━━━━━━━━━━━━━━\n{t('profile_name', lang, name=user.get('name', '-'))}\n{t('profile_phone', lang, phone=user.get('phone', '-'))}\n{t('profile_lang', lang, lang_name=LANG_NAMES.get(lang, lang))}\n{t('profile_joined', lang, date=joined)}\n{t('profile_invites', lang, count=await get_invite_count(user_id))}\n{t('profile_user_type', lang, user_type=t('user_type_special', lang) if user.get('special_user') else t('user_type_normal', lang))}"
    markup = profile_keyboard(lang)
    if edit:
        try: await target.edit(text + footer_text(lang), components=markup); return
        except: pass
    await target.reply(text + footer_text(lang), components=markup)

async def show_invite(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    link = f"https://ble.ir/{BOT_USERNAME}?start={user_id}"
    text = f"{t('invite_title', lang)}\n━━━━━━━━━━━━━━━━━━\n{t('invite_link', lang)}\n`{link}`\n\n{t('invite_stats', lang)}\n{t('invite_count', lang, count=await get_invite_count(user_id))}\n{t('invite_rank', lang, rank=await get_user_rank(user_id))}{t('invite_reward', lang)}"
    markup = invite_keyboard(lang)
    if edit:
        try: await target.edit(text + footer_text(lang), components=markup); return
        except: pass
    await target.reply(text + footer_text(lang), components=markup)

async def show_leaderboard(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    top_users = await get_leaderboard(10)
    if not top_users: text = t("leaderboard_title", lang) + "\n\n" + t("leaderboard_empty", lang)
    else:
        lines = [t("leaderboard_title", lang), "━━━━━━━━━━━━━━━━━━"]
        for idx, u in enumerate(top_users, 1):
            medal = ["🥇", "🥈", "🥉"][idx - 1] if idx <= 3 else f"{idx}."
            lines.append(f"{medal} {u.get('name', 'کاربر')} → *{u.get('invite_count', 0)}* دعوت")
        lines.append("")
        lines.append(t("leaderboard_you", lang, rank=await get_user_rank(user_id), count=await get_invite_count(user_id)))
        text = "\n".join(lines)
    markup = leaderboard_keyboard(lang)
    if edit:
        try: await target.edit(text + footer_text(lang), components=markup); return
        except: pass
    await target.reply(text + footer_text(lang), components=markup)

async def process_crypto_and_reply(message, symbol, user_id=None):
    lang = await get_user_language(user_id) if user_id else "fa"
    data = fetch_crypto_data(symbol)
    if not data: return await message.reply(f"❌ {symbol.upper()} {t('not_found', lang)}" + footer_text(lang))
    result_text = f"📊 **{data['symbol']}**\n━━━━━━━━━━━━━━━━━━\n💵: **{format_price(data['buy_price'])} IRT**\n💰: **{format_price(data['sell_price'])} IRT**\n"
    if data['change'] is not None:
        try:
            val = float(data['change'])
            result_text += f"📈: {'🟢' if val > 0 else '🔴' if val < 0 else '⚪'} **{'+' if val > 0 else ''}{val:.2f}%**\n"
        except: pass
    markup = InlineKeyboardMarkup()
    if user_id:
        markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها" if await is_favorite(user_id, data['symbol']) else "⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:{'DEL' if await is_favorite(user_id, data['symbol']) else 'ADD'}:{data['symbol']}"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_back", lang), callback_data="MENU:CRYPTO"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
    await message.reply(result_text + footer_text(lang), components=markup)

async def process_fiat_and_reply(message, symbol, user_id=None):
    lang = await get_user_language(user_id) if user_id else "fa"
    data = fetch_fiat_data(symbol)
    fiat_name = FIAT_NAMES.get(symbol.upper(), symbol.upper())
    if not data or data['price'] is None: return await message.reply(f"❌ {fiat_name} {t('not_found', lang)}" + footer_text(lang))
    markup = InlineKeyboardMarkup()
    if user_id:
        markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها" if await is_favorite(user_id, symbol.upper()) else "⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:{'DEL' if await is_favorite(user_id, symbol.upper()) else 'ADD'}:{symbol.upper()}"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_back", lang), callback_data="MENU:FIAT"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
    await message.reply(f"💵 **{fiat_name}**\n━━━━━━━━━━━━━━━━━━\n💰: **{format_price(data['price'])} تومان**\n" + footer_text(lang), components=markup)

async def process_gold_and_reply(message, asset_key, user_id=None):
    lang = await get_user_language(user_id) if user_id else "fa"
    data = fetch_gold_data(asset_key)
    gold_name = GOLD_NAMES.get(asset_key, asset_key)
    if not data or data['price'] is None: return await message.reply(f"❌ {gold_name} {t('not_found', lang)}" + footer_text(lang))
    markup = InlineKeyboardMarkup()
    if user_id:
        markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها" if await is_favorite(user_id, asset_key) else "⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:{'DEL' if await is_favorite(user_id, asset_key) else 'ADD'}:{asset_key}"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_back", lang), callback_data="MENU:GOLD"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
    await message.reply(f"🥇 **{gold_name}**\n━━━━━━━━━━━━━━━━━━\n💰: **{format_price(data['price'])} تومان**\n" + footer_text(lang), components=markup)

async def show_my_alerts(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    alerts = await get_user_alerts(user_id)
    if not alerts:
        text = "📭 **هشدار فعالی ندارید.**"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_alert", lang), callback_data="ALERT:NEW"), row=0).add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=1)
        if edit:
            try: await target.edit(text + footer_text(lang), components=markup); return
            except: pass
        return await target.reply(text + footer_text(lang), components=markup)

    lines = ["🔔 **هشدارهای فعال شما**", "━━━━━━━━━━━━━━━━━━"]
    for a in alerts:
        current = get_current_price(str(a.get("asset", "")).upper())
        current_text = format_price(current["price"]) + " تومان" if current and current.get("price") else "نامشخص"
        lines.append(f"🔸 **{get_asset_display_name(a.get('asset', ''))}**\n   💰 فعلی: {current_text}\n   🎯 هدف: {format_price(a.get('target_price'))} تومان\n   📌 شرط: {'بالا ⬆️' if a.get('direction') == 'above' else 'پایین ⬇️'}")
    lines.append("\n💡 هشدار پس از ارسال موفق، خودکار حذف می‌شود.")
    markup = alerts_list_keyboard(alerts, user_id, lang)
    if edit:
        try: await target.edit("\n".join(lines) + footer_text(lang), components=markup); return
        except: pass
    await target.reply("\n".join(lines) + footer_text(lang), components=markup)

async def show_favorites(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    favs = await get_user_favorites(user_id)
    if not favs:
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton(text="➕ افزودن دارایی", callback_data="FAV:NEW"), row=0).add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=1)
        if edit:
            try: await target.edit("⭐ لیست علاقه‌مندی‌های شما خالیه!" + footer_text(lang), components=markup); return
            except: pass
        return await target.reply("⭐ لیست علاقه‌مندی‌های شما خالیه!" + footer_text(lang), components=markup)
    lines = ["⭐ **لیست علاقه‌مندی‌های شما:**\n"]
    for asset in favs:
        data = get_current_price(asset)
        lines.append(f"🔸 **{get_asset_display_name(asset)}** → {format_price(data['price']) + ' تومان' if data else '❌'}")
    markup = fav_view_keyboard(lang)
    if edit:
        try: await target.edit("\n".join(lines) + footer_text(lang), components=markup); return
        except: pass
    await target.reply("\n".join(lines) + footer_text(lang), components=markup)

async def do_convert(target, amount, from_asset, to_asset, user_id=None):
    lang = await get_user_language(user_id) if user_id else "fa"
    from_price = get_current_price(from_asset)
    if not from_price or from_price.get("price") is None: return await target.reply(f"❌ {get_asset_display_name(from_asset)} {t('not_found', lang)}" + footer_text(lang))
    
    if to_asset == "TOMAN":
        result = amount * from_price["price"]
        result_text = f"🔄 **نتیجه تبدیل**\n━━━━━━━━━━━━━━━━━━\n💱 {amount:,.2f} {get_asset_display_name(from_asset)}\n⬇️⬇️⬇️\n💰 **{result:,.0f} تومان**\n━━━━━━━━━━━━━━━━━━\n📊 نرخ: ۱ {get_asset_display_name(from_asset)} = {format_price(from_price['price'])} تومان"
    else:
        to_price = get_current_price(to_asset)
        if not to_price or to_price.get("price") is None: return await target.reply(f"❌ {get_asset_display_name(to_asset)} {t('not_found', lang)}" + footer_text(lang))
        result = amount * from_price["price"] / to_price["price"]
        result_text = f"🔄 **نتیجه تبدیل**\n━━━━━━━━━━━━━━━━━━\n💱 {amount:,.2f} {get_asset_display_name(from_asset)}\n⬇️⬇️⬇️\n💰 **{result:,.4f} {get_asset_display_name(to_asset)}**\n━━━━━━━━━━━━━━━━━━\n📊 نرخ {get_asset_display_name(from_asset)}: {format_price(from_price['price'])} تومان\n📊 نرخ {get_asset_display_name(to_asset)}: {format_price(to_price['price'])} تومان"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(text=t("menu_convert", lang), callback_data="CONV:NEW"), row=0).add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=1)
    await target.reply(result_text + footer_text(lang), components=markup)


# ============================================================
# --- چک‌کننده هشدارها ---
# ============================================================
async def alert_checker_async():
    while True:
        try:
            alerts = await get_all_alerts()
            if not alerts:
                await asyncio.sleep(60)
                continue
            prices = {}
            for alert in alerts:
                asset = str(alert.get("asset", "")).upper()
                if asset and asset not in prices:
                    try: prices[asset] = get_current_price(asset)
                    except: prices[asset] = None

            for alert in alerts:
                current = prices.get(str(alert.get("asset", "")).upper())
                if not current or current.get("price") is None: continue
                try:
                    cp = float(current["price"]); target = float(alert["target_price"])
                except: continue
                triggered = (alert.get("direction") == "above" and cp >= target) or (alert.get("direction") == "below" and cp <= target)
                if not triggered: continue
                try:
                    await bot.send_message(alert["chat_id"], f"🔔 **هشدار قیمت فعال شد!**\n\n📊 {get_asset_display_name(alert['asset'])}\n💰 قیمت فعلی: {format_price(cp)} تومان\n🎯 هدف: {format_price(target)} تومان")
                    await alerts_collection.delete_one({"_id": alert["_id"]})
                except: pass
        except: pass
        await asyncio.sleep(60)


# ============================================================
# --- کانال و اخبار ---
# ============================================================
def build_channel_post_with_stats(users_count):
    lines = ["📊 **نرخ لحظه‌ای بازار**", "━━━━━━━━━━━━━━━━━━", "💵 **ارزهای فیات:**"]
    for sym in ["USD", "EUR", "AED", "TRY"]:
        data = fetch_fiat_data(sym)
        if data and data.get("price"): lines.append(f"  • {FIAT_NAMES.get(sym, sym)}: **{format_price(data['price'])} تومان**")
    lines.append("\n🥇 **طلا و سکه:**")
    for asset in ["gold_18", "coin_emami", "coin_half"]:
        data = fetch_gold_data(asset)
        if data and data.get("price"): lines.append(f"  • {GOLD_NAMES.get(asset, asset)}: **{format_price(data['price'])} تومان**")
    lines.append("\n🪙 **رمزارزها:**")
    for sym in ["BTC", "ETH", "USDT", "BNB", "SOL"]:
        data = fetch_crypto_data(sym)
        if data and data.get("buy_price"):
            p_num = float(data['buy_price'])
            formatted = f"{p_num / 1_000_000_000_000:,.2f} همت" if p_num >= 1_000_000_000_000 else f"{p_num / 1_000_000_000:,.2f} میلیارد" if p_num >= 1_000_000_000 else f"{p_num / 1_000_000:,.2f} میلیون" if p_num >= 1_000_000 else format_price(p_num)
            lines.append(f"  • {sym}: **{formatted} تومان**")
    lines.append("\n━━━━━━━━━━━━━━━━━━")
    lines.append(f"👥 **کاربران ربات:** *{users_count:,}* نفر")
    lines.append(f"🕐 {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"📢 {CHANNEL_ID}")
    return "\n".join(lines)

def channel_poster():
    global CHANNEL_NUMERIC_ID
    while True:
        try:
            time.sleep(CHANNEL_POST_INTERVAL)
            if CHANNEL_POST_ENABLED and CHANNEL_ID:
                users_count = 0
                try:
                    if MAIN_LOOP is not None:
                        future_count = asyncio.run_coroutine_threadsafe(get_users_count(), MAIN_LOOP)
                        users_count = future_count.result(timeout=10)
                except: pass
                post_text = build_channel_post_with_stats(users_count)
                try:
                    if MAIN_LOOP is not None:
                        future = asyncio.run_coroutine_threadsafe(bot.send_message(CHANNEL_ID, post_text), MAIN_LOOP)
                        result = future.result(timeout=30)
                        if result and hasattr(result, 'message_id'): _sent_channel_message_ids.add(str(result.message_id))
                        if result and hasattr(result, 'chat') and result.chat: CHANNEL_NUMERIC_ID = str(result.chat.id)
                except: pass
        except: pass

def news_poster():
    print("📰 News poster started!", flush=True)
    while True:
        try:
            if NEWS_START_HOUR <= time.localtime().tm_hour < NEWS_END_HOUR:
                feed = feedparser.parse(NEWS_RSS_URL)
                sent_count = 0
                # بررسی ۵ خبر آخر به ترتیب از قدیم به جدید تا جدیدترین‌ها ارسال شن
                for entry in reversed(feed.entries[:5]):
                    news_id = entry.get('id', entry.get('link'))
                    if news_id not in _sent_news_ids:
                        title = entry.get('title', '')
                        summary = re.sub(r'<[^>]+>', '', entry.get('summary', '')).strip()
                        if len(summary) > 300: summary = summary[:300] + "..."
                        
                        final_text = f"📰 **{title}**\n\n{summary}\n\n📢 {CHANNEL_LINK}"
                        
                        if MAIN_LOOP is not None:
                            try:
                                future = asyncio.run_coroutine_threadsafe(bot.send_message(CHANNEL_ID, final_text), MAIN_LOOP)
                                future.result(30)
                                _sent_news_ids.add(news_id)
                                print(f"✅ خبر ارسال شد: {title[:30]}", flush=True)
                                sent_count += 1
                                time.sleep(2) # جلوگیری از Rate Limit بله
                            except Exception as e:
                                print(f"❌ خطا در ارسال خبر: {e}", flush=True)
                    
                    if sent_count >= 2: break # نهایتا ۲ خبر جدید در هر بازه
                
                if len(_sent_news_ids) > 500: _sent_news_ids.clear()
            time.sleep(NEWS_CHECK_INTERVAL)
        except Exception as e:
            print(f"❌ News poster error: {e}", flush=True)
            time.sleep(60)


# ============================================================
#                    👨‍💻 پنل مدیریت حرفه‌ای
# ============================================================
def is_admin(user_id): return str(user_id) in ADMIN_IDS

def admin_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="📊 داشبورد", callback_data="ADMIN:STATS"), row=0)
    markup.add(InlineKeyboardButton(text="👥 کاربران", callback_data="ADMIN:USERS:0"), row=1)
    markup.add(InlineKeyboardButton(text="🔎 جستجوی کاربر", callback_data="ADMIN:SEARCH"), row=1)
    markup.add(InlineKeyboardButton(text="📢 ارسال پیام همگانی", callback_data="ADMIN:BROADCAST"), row=2)
    markup.add(InlineKeyboardButton(text="🔔 هشدارها", callback_data="ADMIN:ALERTS"), row=2)
    markup.add(InlineKeyboardButton(text="⭐ افراد خاص", callback_data="ADMIN:SPECIAL"), row=3)
    markup.add(InlineKeyboardButton(text="⭐ علاقه‌مندی‌ها", callback_data="ADMIN:FAVS"), row=3)
    markup.add(InlineKeyboardButton(text="🩺 وضعیت سیستم", callback_data="ADMIN:HEALTH"), row=3)
    markup.add(InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="ADMIN:HOME"), row=4)
    return markup

def admin_back_keyboard(): return InlineKeyboardMarkup().add(InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="ADMIN:HOME"), row=0)

async def admin_stats_text():
    now = time.time()
    tot = await users_collection.count_documents({}) if users_collection else 0
    act = await users_collection.count_documents({"account_status": {"$ne": "logged_out"}, "blocked": {"$ne": True}}) if users_collection else 0
    active_24h = await users_collection.count_documents({"last_seen_at": {"$gte": now - 86400}, "account_status": {"$ne": "logged_out"}}) if users_collection else 0
    new_24h = await users_collection.count_documents({"created_at": {"$gte": now - 86400}}) if users_collection else 0
    alerts = await alerts_collection.count_documents({}) if alerts_collection else 0
    favs = await favorites_collection.count_documents({}) if favorites_collection else 0
    refs = await referrals_collection.count_documents({}) if referrals_collection else 0
    return f"👨‍💻 **داشبورد مدیریت**\n━━━━━━━━━━━━━━━━━━\n👥 کل پروفایل‌ها: **{tot:,}**\n🟢 فعال: **{act:,}**\n🟢 فعال ۲۴ ساعت: **{active_24h:,}**\n🆕 ثبت‌نام ۲۴ ساعت: **{new_24h:,}**\n━━━━━━━━━━━━━━━━━━\n🔔 هشدارها: **{alerts:,}**\n⭐ علاقه‌مندی: **{favs:,}**\n🎁 Referral: **{refs:,}**\n⭐ افراد خاص: **{await get_special_users_count():,}**\n━━━━━━━━━━━━━━━━━━\n🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}"

async def admin_users_page(page=0):
    page = max(0, int(page))
    if not users_collection: return "❌ دیتابیس متصل نیست.", admin_back_keyboard()
    total = await users_collection.count_documents({})
    docs = await users_collection.find({}).sort("created_at", -1).skip(page * ADMIN_PAGE_SIZE).limit(ADMIN_PAGE_SIZE).to_list(length=ADMIN_PAGE_SIZE)
    lines = [f"👥 **کاربران (صفحه {page + 1})**", "━━━━━━━━━━━━━━━━━━"]
    markup = InlineKeyboardMarkup()
    for i, u in enumerate(docs):
        name = str(u.get("name", "بدون نام"))[:28]
        status = "🚫" if u.get("blocked") else ("🚪" if u.get("account_status") == "logged_out" else "🟢") + ("⭐" if u.get("special_user") else "")
        lines.append(f"{page * ADMIN_PAGE_SIZE + i + 1}. {status} **{name}**\n   ID: `{u.get('chat_id', '-')}`")
        markup.add(InlineKeyboardButton(text=f"👤 {name[:20]}", callback_data=f"ADMIN:USER:{u.get('chat_id')}"), row=i)
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"ADMIN:USERS:{page-1}"))
    if page + 1 < max(1, (total + ADMIN_PAGE_SIZE - 1) // ADMIN_PAGE_SIZE): nav.append(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"ADMIN:USERS:{page+1}"))
    if nav: markup.add(nav[0], nav[1] if len(nav) > 1 else None) # Bale markup doesn't support list directly, use loop
    if nav:
        for btn in nav: markup.add(btn, row=len(docs))
    markup.add(InlineKeyboardButton(text="🔙 پنل", callback_data="ADMIN:HOME"), row=len(docs) + 1)
    return "\n".join(lines), markup

async def admin_user_detail(chat_id):
    user = await get_user(chat_id)
    if not user: return "❌ کاربر پیدا نشد.", admin_back_keyboard()
    text = f"👤 **جزئیات**\n━━━━━━━━━━━━━━━━━━\n📝 نام: **{user.get('name', 'بدون نام')}**\n🆔 ID: `{user.get('chat_id')}`\n🎁 دعوت‌ها: **{user.get('invite_count', 0)}**\n👑 نوع: **{'خاص ⭐' if user.get('special_user') else 'عادی 👤'}**\n📌 وضعیت: **{'مسدود' if user.get('blocked') else 'فعال'}**"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🟢 رفع مسدودی" if user.get("blocked") else "🚫 مسدود کردن", callback_data=f"ADMIN:{'UNBLOCK' if user.get('blocked') else 'BLOCK'}:{chat_id}"), row=0)
    markup.add(InlineKeyboardButton(text="⭐ حذف از خاص‌ها" if user.get("special_user") else "⭐ افزودن به خاص‌ها", callback_data=f"ADMIN:{'UNSPECIAL' if user.get('special_user') else 'SPECIAL'}:{chat_id}"), row=1)
    markup.add(InlineKeyboardButton(text="🔙 کاربران", callback_data="ADMIN:USERS:0"), row=2)
    markup.add(InlineKeyboardButton(text="🏠 پنل", callback_data="ADMIN:HOME"), row=3)
    return text, markup

async def admin_special_users_text():
    if not users_collection: return "❌ دیتابیس متصل نیست.", admin_back_keyboard()
    docs = await users_collection.find({"special_user": True}).limit(50).to_list(length=50)
    lines = ["⭐ **افراد خاص**", "━━━━━━━━━━━━━━━━━━"]
    markup = InlineKeyboardMarkup()
    for i, u in enumerate(docs):
        lines.append(f"{i+1}. **{str(u.get('name', 'کاربر'))[:25]}** — `{u.get('chat_id', '-')}`")
        markup.add(InlineKeyboardButton(text=f"⭐ {str(u.get('name', 'کاربر'))[:20]}", callback_data=f"ADMIN:USER:{u.get('chat_id')}"), row=i)
    markup.add(InlineKeyboardButton(text="🔙 پنل", callback_data="ADMIN:HOME"), row=len(docs) + 1)
    return "\n".join(lines), markup

async def admin_broadcast(admin_id, text):
    if not users_collection: return 0, 0
    sent, failed = 0, 0
    async for doc in users_collection.find({"account_status": {"$ne": "logged_out"}, "blocked": {"$ne": True}}):
        try:
            await bot.send_message(doc["chat_id"], text)
            sent += 1
            await asyncio.sleep(0.04)
        except: failed += 1
    return sent, failed

# ============================================================
#                       رویدادها
# ============================================================
@bot.event
async def on_ready():
    global MAIN_LOOP, BOT_ID, _channel_thread_started, _checker_thread_started
    print(f"ربات {bot.user.username} روشن شد!", flush=True)
    MAIN_LOOP = asyncio.get_running_loop()
    BOT_ID = str(bot.user.id)
    await init_db()
    if not _checker_thread_started:
        asyncio.create_task(alert_checker_async()); _checker_thread_started = True
    if not _channel_thread_started:
        threading.Thread(target=channel_poster, daemon=True).start()
        threading.Thread(target=news_poster, daemon=True).start()
        _channel_thread_started = True

async def wait_for_database_ready(timeout=12):
    global DB_READY
    if DB_READY and users_collection: return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        if DB_READY and users_collection: return True
        await asyncio.sleep(0.5)
    return bool(DB_READY and users_collection)

@bot.event
async def on_message(message: Message):
    try:
        if str(getattr(message, 'message_id', '')) in _sent_channel_message_ids: return
        if BOT_ID and message.author and str(getattr(message.author, 'id', '')) == BOT_ID: return
        if getattr(message.chat, 'type', None) != 'private': return
        if CHANNEL_NUMERIC_ID and str(getattr(message.chat, 'id', '')) == CHANNEL_NUMERIC_ID: return
    except: return
    if not message.author or message.author.is_bot or not message.content: return

    content = message.content
    if 'انتقادات و پیشنهادات:' in content or '📊 **نرخ لحظه‌ای بازار**' in content or content.count('تومان') >= 3: return

    user_id = get_user_id_from_message(message)
    text = message.content.strip()
    text_upper = text.upper()

    if not await wait_for_database_ready(12):
        return await message.reply("⏳ در حال اتصال به پایگاه داده...")

    if text == "/myid":
        return await message.reply(f"🆔 Chat ID: `{user_id}`")

    if is_admin(user_id):
        if text == "/admin":
            clear_state(user_id); return await message.reply(await admin_stats_text(), components=admin_keyboard())
        if user_id in user_states and user_states[user_id].get("state") == "admin_broadcast_waiting":
            user_states[user_id] = {"state": "admin_broadcast_confirm", "data": {"text": text}}
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton(text="✅ ارسال", callback_data="ADMIN:BROADCAST:CONFIRM"), row=0).add(InlineKeyboardButton(text="❌ لغو", callback_data="ADMIN:HOME"), row=1)
            return await message.reply("📢 **پیش‌نمایش:**\n\n" + text, components=markup)
        if user_id in user_states and user_states[user_id].get("state") == "admin_search_waiting":
            docs = await users_collection.find({"$or": [{"chat_id": text}, {"name": {"$regex": text, "$options": "i"}}]}).limit(10).to_list(length=10)
            clear_state(user_id)
            if not docs: return await message.reply("❌ یافت نشد.", components=admin_back_keyboard())
            markup = InlineKeyboardMarkup()
            lines = ["🔎 **نتایج:**"]
            for idx, doc in enumerate(docs):
                lines.append(f"{idx+1}. **{doc.get('name', 'کاربر')}** — `{doc.get('chat_id')}`")
                markup.add(InlineKeyboardButton(text=f"👤 {doc.get('name', 'کاربر')[:20]}", callback_data=f"ADMIN:USER:{doc.get('chat_id')}"), row=idx)
            markup.add(InlineKeyboardButton(text="🔙 پنل", callback_data="ADMIN:HOME"), row=len(docs))
            return await message.reply("\n".join(lines), components=markup)

    existing_for_activity = await get_active_user(user_id)
    if existing_for_activity: await touch_user(user_id)

    raw_user_for_block = await get_user(user_id)
    if raw_user_for_block and raw_user_for_block.get("blocked") and not is_admin(user_id):
        return await message.reply("🚫 دسترسی محدود شده است.")

    existing_user = await get_active_user(user_id)
    if existing_user:
        if not await check_channel_membership(user_id):
            return await message.reply(t("force_join_title", existing_user.get("language", "fa")) + "\n\n" + t("force_join_text", existing_user.get("language", "fa"), channel=CHANNEL_ID), components=force_join_keyboard(existing_user.get("language", "fa")))
    elif user_id in user_states and user_states[user_id].get("state") in {"awaiting_language", "awaiting_name", "awaiting_phone"}:
        if not await check_channel_membership(user_id):
            return await message.reply(t("force_join_title", "fa") + "\n\n" + t("force_join_text", "fa", channel=CHANNEL_ID), components=force_join_keyboard("fa"))

    if user_id in user_states:
        state = user_states[user_id]["state"]
        data = user_states[user_id].get("data", {})
        lang = data.get("lang", "fa")

        if state == "awaiting_channel_join":
            return await message.reply(t("force_join_title", "fa") + "\n\n" + t("force_join_text", "fa", channel=CHANNEL_ID), components=force_join_keyboard("fa"))

        if state == "awaiting_name":
            if len(text) < 3: return await message.reply(t("invalid_name", lang))
            data["name"] = text
            ok = await create_user(user_id, text, None, lang, referred_by=data.get("referred_by"))
            clear_state(user_id); clear_lang_cache(user_id)
            if not ok: return await message.reply(t("error", lang))
            return await message.reply(t("register_success", lang, name=text, lang_name=LANG_NAMES.get(lang, lang)) + footer_text(lang), components=main_menu_keyboard(lang))

        if state == "alert_awaiting_price":
            try:
                price = float(text.replace(",", ""))
                data["target_price"] = price
                user_states[user_id]["state"] = "alert_awaiting_direction"
                return await message.reply(f"🎯 قیمت هدف: **{format_price(price)} تومان**\n\nحالا شرط را انتخاب کنید:" + footer_text(lang), components=alert_direction_keyboard(lang))
            except: return await message.reply("❌ عدد معتبر وارد کنید.")

        if state == "alert_awaiting_manual_asset":
            if text_upper in GOLD_NAMES or text_upper in FIAT_NAMES or fetch_crypto_data(text_upper):
                data["asset"] = text_upper
                user_states[user_id]["state"] = "alert_awaiting_price"
                return await message.reply(f"✅ {get_asset_display_name(text_upper)}\n\n💰 قیمت هدف را وارد کنید:")
            return await message.reply(f"❌ {text_upper} یافت نشد.", components=alert_asset_category_keyboard(lang))

        if state == "convert_awaiting_amount":
            try:
                amount = float(text.replace(",", ""))
                data["amount"] = amount
                user_states[user_id]["state"] = "convert_awaiting_to"
                return await message.reply(f"✅ مقدار: **{format_price(amount)} {get_asset_display_name(data['from_asset'])}**\n\n🔄 ارز مقصد را انتخاب کنید:", components=convert_to_keyboard(data["from_asset"], lang))
            except: return await message.reply("❌ عدد معتبر وارد کنید.")

    if text.startswith('/start'):
        referred_by = None
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit() and parts[1] != user_id: referred_by = parts[1]
        
        user = await get_active_user(user_id)
        if user:
            lang = user.get("language", "fa")
            _user_lang_cache[user_id] = lang
            if not await check_channel_membership(user_id):
                return await message.reply(t("force_join_title", lang) + "\n\n" + t("force_join_text", lang, channel=CHANNEL_ID), components=force_join_keyboard(lang))
            return await show_main_menu(message, user_id)

        clear_force_join_cache(user_id)
        if not await check_channel_membership(user_id, use_cache=False):
            user_states[user_id] = {"state": "awaiting_channel_join", "data": {"referred_by": referred_by}}
            return await message.reply(t("force_join_title", "fa") + "\n\n" + t("force_join_text", "fa", channel=CHANNEL_ID), components=force_join_keyboard("fa"))

        user_states[user_id] = {"state": "awaiting_language", "data": {"referred_by": referred_by}}
        return await message.reply(t("choose_language", "fa"), components=language_keyboard())

    if text == '/cancel':
        clear_state(user_id); lang = await get_user_language(user_id)
        return await message.reply(t("cancel", lang), components=main_menu_keyboard(lang))
    if text == '/profile': return await show_profile(message, user_id)
    if text == '/help' or text == 'راهنما': return await show_help(message, user_id)
    if text == '/invite': return await show_invite(message, user_id)
    if text == '/top': return await show_leaderboard(message, user_id)
    if text == '/menu': return await show_main_menu(message, user_id)

    lang = await get_user_language(user_id)

    if text == '/myalerts':
        if not await has_pro_access(user_id):
            return await message.reply(t("pro_locked", lang) + f"\n\n📊 دعوت‌های شما: **{await get_effective_invite_count(user_id)}** از **{PRO_INVITE_THRESHOLD}**")
        return await show_my_alerts(message, user_id)
    if text == '/fav' or text == '/favorites': return await show_favorites(message, user_id)

    if text_upper in FIAT_NAMES: return await process_fiat_and_reply(message, text_upper, user_id)
    if not await get_user(user_id):
        user_states[user_id] = {"state": "awaiting_language", "data": {}}
        return await message.reply(t("choose_language", "fa"), components=language_keyboard())
    await process_crypto_and_reply(message, text_upper, user_id)

@bot.event
async def on_callback(callback: CallbackQuery):
    data = callback.data
    user_id = get_user_id_from_callback(callback)
    if not user_id or callback.message.chat.type != 'private': return

    if is_admin(user_id) and data.startswith("ADMIN:"):
        try:
            if data in ("ADMIN:HOME", "ADMIN:STATS"): return await callback.message.edit(await admin_stats_text(), components=admin_keyboard())
            if data.startswith("ADMIN:USERS:"):
                txt, kb = await admin_users_page(int(data.split(":")[2])); return await callback.message.edit(txt, components=kb)
            if data.startswith("ADMIN:USER:"):
                txt, kb = await admin_user_detail(data.split(":", 2)[2]); return await callback.message.edit(txt, components=kb)
            if data.startswith("ADMIN:BLOCK:") or data.startswith("ADMIN:UNBLOCK:"):
                parts = data.split(":", 2); await set_user_blocked(parts[2], parts[1] == "BLOCK")
                txt, kb = await admin_user_detail(parts[2]); return await callback.message.edit(txt, components=kb)
            if data == "ADMIN:SEARCH": user_states[user_id] = {"state": "admin_search_waiting"}; return await callback.message.reply("🔎 نام یا Chat ID را بفرستید:")
            if data == "ADMIN:BROADCAST": user_states[user_id] = {"state": "admin_broadcast_waiting"}; return await callback.message.reply("📢 متن پیام را بفرستید:")
            if data == "ADMIN:BROADCAST:CONFIRM":
                txt = user_states.get(user_id, {}).get("data", {}).get("text")
                if txt:
                    clear_state(user_id); await callback.message.edit("⏳ در حال ارسال...")
                    sent, failed = await admin_broadcast(user_id, txt)
                    return await callback.message.reply(f"✅ ارسال شد.\n📨 موفق: {sent}\n❌ ناموفق: {failed}", components=admin_keyboard())
            if data == "ADMIN:SPECIAL":
                txt, kb = await admin_special_users_text(); return await callback.message.edit(txt, components=kb)
            if data.startswith("ADMIN:SPECIAL:") or data.startswith("ADMIN:UNSPECIAL:"):
                parts = data.split(":", 2); await set_special_user(parts[2], parts[1] == "SPECIAL")
                txt, kb = await admin_user_detail(parts[2]); return await callback.message.edit(txt, components=kb)
            if data == "ADMIN:HEALTH": return await callback.message.edit("🩺 سیستم فعال است.", components=admin_back_keyboard())
        except: pass
        return

    if data == "PROFILE:LOGOUT":
        user = await get_active_user(user_id); lang = user.get("language", "fa") if user else "fa"
        return await callback.message.edit(t("logout_confirm", lang), components=logout_confirm_keyboard(lang))
    if data == "PROFILE:LOGOUT:CONFIRM":
        user = await get_active_user(user_id); lang = user.get("language", "fa") if user else "fa"
        if await logout_user(user_id): return await callback.message.edit(t("logout_done", lang))
        return await callback.message.reply(t("error", lang))

    raw_callback_user = await get_user(user_id)
    if raw_callback_user and raw_callback_user.get("blocked") and not is_admin(user_id):
        return await callback.message.reply("🚫 دسترسی محدود شده است.")

    if data == "FORCEJOIN:VERIFY":
        clear_force_join_cache(user_id)
        user = await get_active_user(user_id)
        pending_data = user_states.get(user_id, {}).get("data", {})
        if not await check_channel_membership(user_id, use_cache=False):
            lang = user.get("language", "fa") if user else "fa"
            return await callback.message.edit(t("force_join_not_member", lang), components=force_join_keyboard(lang))
        if not user:
            user_states[user_id] = {"state": "awaiting_language", "data": {"referred_by": pending_data.get("referred_by")}}
            return await callback.message.edit(t("choose_language", "fa"), components=language_keyboard())
        clear_state(user_id); return await show_main_menu(callback.message, user_id, edit=True)

    existing_user = await get_user(user_id)
    if existing_user and not await check_channel_membership(user_id):
        lang = existing_user.get("language", "fa")
        return await callback.message.edit(t("force_join_title", lang) + "\n\n" + t("force_join_text", lang, channel=CHANNEL_ID), components=force_join_keyboard(lang))

    user = existing_user
    if not user and data.startswith("LANG:") and user_states.get(user_id, {}).get("state") != "awaiting_language":
        return await callback.message.edit(t("force_join_title", "fa") + "\n\n" + t("force_join_text", "fa", channel=CHANNEL_ID), components=force_join_keyboard("fa"))

    if data.startswith("LANG:"):
        new_lang = data.split(":")[1] if data.split(":")[1] in ["fa", "en"] else "fa"
        if user_id in user_states and user_states[user_id]["state"] == "changing_language":
            if await get_user(user_id):
                await create_user(user_id, user.get("name", ""), user.get("phone", ""), new_lang)
                clear_lang_cache(user_id); clear_state(user_id); return await show_main_menu(callback.message, user_id, edit=True)
        referred_by = user_states.get(user_id, {}).get("data", {}).get("referred_by")
        user_states[user_id] = {"state": "awaiting_name", "data": {"lang": new_lang, "referred_by": referred_by}}
        return await callback.message.edit(t("welcome_new", new_lang))

    user = await get_user(user_id)
    if not user: return await callback.message.reply(t("choose_language", "fa"), components=language_keyboard())
    lang = await get_user_language(user_id)

    if (data in {"MENU:MYALERTS", "ALERT:NEW"} or data.startswith("ALERT:")) and not await has_pro_access(user_id):
        return await callback.message.reply(t("pro_locked", lang) + f"\n\n📊 دعوت‌های شما: **{await get_effective_invite_count(user_id)}** از **{PRO_INVITE_THRESHOLD}**" + footer_text(lang), components=main_menu_keyboard(lang))

    if data == "MENU:MAIN": clear_state(user_id); return await show_main_menu(callback.message, user_id, edit=True)
    if data == "MENU:HELP": return await show_help(callback.message, user_id, edit=True)
    if data == "MENU:PROFILE": return await show_profile(callback.message, user_id, edit=True)
    if data == "MENU:INVITE": return await show_invite(callback.message, user_id, edit=True)
    if data == "MENU:LEADERBOARD": return await show_leaderboard(callback.message, user_id, edit=True)
    
    if data == "INVITE:COPY":
        link = f"https://ble.ir/{BOT_USERNAME}?start={user_id}"
        return await callback.message.reply(f"📋 لینک دعوت شما:\n`{link}`\n\nروی متن بالا کلیک کنید تا کپی شود." + footer_text(lang))
    
    if data == "MENU:LANG":
        user_states[user_id] = {"state": "changing_language", "data": {}}
        return await callback.message.edit(t("choose_language", lang), components=language_keyboard())
    
    if data in ("MENU:MARKET", "MARKET:REFRESH"): clear_state(user_id); return await show_market_dashboard(callback.message, user_id, edit=True)
    
    if data == "MENU:CRYPTO": clear_state(user_id); return await callback.message.edit(t("crypto_title", lang) + footer_text(lang), components=crypto_menu_keyboard(lang))
    if data == "MENU:FIAT": clear_state(user_id); return await callback.message.edit(t("fiat_title", lang) + footer_text(lang), components=fiat_menu_keyboard(lang))
    if data == "MENU:GOLD": clear_state(user_id); return await callback.message.edit(t("gold_title", lang) + footer_text(lang), components=gold_menu_keyboard(lang))
    if data == "MENU:MYALERTS": return await show_my_alerts(callback.message, user_id, edit=True)

    if data.startswith("CRYPTO:"): return await process_crypto_and_reply(callback.message, data.split(":")[1], user_id)
    if data.startswith("FIAT:"): return await process_fiat_and_reply(callback.message, data.split(":")[1], user_id)
    if data.startswith("GOLD:"): return await process_gold_and_reply(callback.message, data.split(":")[1], user_id)

    if data == "FAV:VIEW": clear_state(user_id); return await show_favorites(callback.message, user_id, edit=True)
    if data == "FAV:NEW": clear_state(user_id); return await callback.message.edit("⭐ **افزودن**\n\nکدام دسته؟", components=fav_category_keyboard(lang))
    
    if data.startswith("FAV:CAT:"):
        category = data.split(":")[2] if len(data.split(":")) >= 3 else None
        if category:
            user_favs = await get_user_favorites(user_id)
            return await callback.message.edit("⭐ **انتخاب دارایی:**", components=fav_asset_list_keyboard(category, user_favs, lang))
    
    if data.startswith("FAV:ADD:"):
        asset = data.split(":")[2]
        added = await add_favorite(user_id, asset)
        await callback.message.reply(f"{'✅' if added else 'ℹ️'} **{get_asset_display_name(asset)}** {'اضافه شد!' if added else 'قبلاً بود.'}")
        category = "crypto" if asset in POPULAR_CRYPTOS else "fiat" if asset in POPULAR_FIATS else "gold"
        user_favs = await get_user_favorites(user_id)
        return await callback.message.edit("⭐ **انتخاب دارایی:**", components=fav_asset_list_keyboard(category, user_favs, lang))
    
    if data.startswith("FAV:DEL:"):
        asset = data.split(":")[2]
        await remove_favorite(user_id, asset)
        await callback.message.reply(f"🗑 **{get_asset_display_name(asset)}** حذف شد.")
        category = "crypto" if asset in POPULAR_CRYPTOS else "fiat" if asset in POPULAR_FIATS else "gold"
        user_favs = await get_user_favorites(user_id)
        return await callback.message.edit("⭐ **انتخاب دارایی:**", components=fav_asset_list_keyboard(category, user_favs, lang))

    if data.startswith("DELALERT:"):
        asset = data.split(":")[1]
        if asset == "ALL":
            count = await remove_all_user_alerts(user_id)
            await callback.message.reply(f"🗑 **{count} هشدار حذف شد.**")
        else:
            await remove_alert(user_id, asset)
            await callback.message.reply(f"🗑 هشدار **{get_asset_display_name(asset)}** حذف شد.")
        return await show_my_alerts(callback.message, user_id, edit=False)

    if data == "ALERT:NEW": clear_state(user_id); return await callback.message.edit("🔔 **ثبت هشدار**\n\nدسته‌بندی:", components=alert_asset_category_keyboard(lang))
    if data.startswith("ALERT:CAT:"): return await callback.message.edit("🔔 **انتخاب دارایی:**", components=alert_asset_list_keyboard(data.split(":")[2], lang))
    
    if data == "ALERT:MANUAL":
        user_states[user_id] = {"state": "alert_awaiting_manual_asset", "data": {"lang": lang}}
        return await callback.message.reply("✏️ **نام دارایی را وارد کنید:**")
    
    if data.startswith("ALERT:SET:"):
        asset = data.split(":")[2]
        user_states[user_id] = {"state": "alert_awaiting_price", "data": {"asset": asset, "lang": lang}}
        current = get_current_price(asset)
        current_text = f"\n💰 قیمت فعلی: {format_price(current['price'])} تومان" if current else ""
        return await callback.message.edit(f"✅ **{get_asset_display_name(asset)}**{current_text}\n\n🎯 قیمت هدف را وارد کنید:")
    
    if data.startswith("ALERT:DIR:"):
        direction = data.split(":")[2]
        if user_id not in user_states or "asset" not in user_states[user_id]["data"] or "target_price" not in user_states[user_id]["data"]:
            return await callback.message.reply("❌ خطا. دوباره شروع کنید.", components=main_menu_keyboard(lang))
        asset = user_states[user_id]["data"]["asset"]
        target_price = user_states[user_id]["data"]["target_price"]
        await add_alert(user_id, asset, target_price, direction)
        clear_state(user_id)
        return await callback.message.edit(f"✅ **هشدار ثبت شد!**\n\n🔔 **{get_asset_display_name(asset)}**\n🎯 هدف: **{format_price(target_price)} تومان**\n📊 {'بالا 📈' if direction == 'above' else 'پایین 📉'}", components=main_menu_keyboard(lang))

    if data == "ALERT:CANCEL": clear_state(user_id); return await callback.message.reply(t("cancel", lang), components=main_menu_keyboard(lang))

    if data == "CONV:NEW": clear_state(user_id); return await callback.message.edit("🔄 **مبدل ارز**\n\nمرحله ۱: **ارز مبدأ؟**", components=convert_from_keyboard(lang))
    if data.startswith("CONV:FROM:"):
        user_states[user_id] = {"state": "convert_awaiting_amount", "data": {"from_asset": data.split(":")[2], "lang": lang}}
        return await callback.message.edit(f"✅ **{get_asset_display_name(data.split(':')[2])}**\n\nمرحله ۲: **مقدار؟**")
    if data.startswith("CONV:TO:"):
        if user_id not in user_states or "from_asset" not in user_states[user_id]["data"] or "amount" not in user_states[user_id]["data"]:
            return await callback.message.reply("❌ خطا. دوباره شروع کنید.", components=main_menu_keyboard(lang))
        f, amt = user_states[user_id]["data"]["from_asset"], user_states[user_id]["data"]["amount"]
        clear_state(user_id)
        return await do_convert(callback.message, amt, f, data.split(":")[2], user_id)
    if data == "CONV:CANCEL": clear_state(user_id); return await callback.message.reply(t("cancel", lang), components=main_menu_keyboard(lang))


# --- سرور وب ---
app = Flask(__name__)

@app.route('/')
def home(): return "Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

bot.run()
