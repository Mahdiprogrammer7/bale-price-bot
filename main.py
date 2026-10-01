import os
import re
import json
import time
import asyncio
import threading
import certifi
import aiohttp
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

# ✅ پروکسی
USE_PROXY = True
PROXY_URL = "https://red-meadow-20f7bale-bot-proxy.najafimahdi13867.workers.dev"
WELCOME_IMAGE_URL = ""

# 🔗 لینک ربات برای سیستم دعوت
BOT_USERNAME = "onlinearzmonybot"  # بدون @

# 👨‍💻 مدیران بات - در Render به صورت ENV تنظیم کن:
# ADMIN_IDS=123456789,987654321
ADMIN_IDS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
ADMIN_PAGE_SIZE = 8
# 🎁 دسترسی حرفه‌ای: ۵ دعوت یا بیشتر
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
        "menu_convert": "🔄 مبدل ارز",
        "menu_fav": "⭐ علاقه‌مندی‌ها",
        "menu_alert": "🔔 هشدار قیمت",
        "menu_myalerts": "📋 هشدارهای من",
        "menu_list": "📊 لیست رمزارزها",
        "menu_profile": "👤 پروفایل من",
        "menu_invite": "🎁 دعوت دوستان",
        "menu_leaderboard": "🏆 جدول قهرمانان",
        "menu_help": "ℹ️ راهنما",
        "help_title": "ℹ️ *راهنمای ارز آنلاین*",
        "help_text": "به *ارز آنلاین* خوش آمدی! 👋\n\nاین بات برای دسترسی سریع به قیمت ارزها، رمزارزها، طلا و سکه و چند ابزار کاربردی بازار ساخته شده است.\n\n🪙 *ارز دیجیتال*\nقیمت رمزارزها را ببین و از فهرست رمزارزها استفاده کن.\n\n💵 *ارزهای فیات*\nقیمت ارزهای رایج مثل دلار و یورو را بررسی کن.\n\n🥇 *طلا و سکه*\nقیمت طلا و انواع سکه را مشاهده کن.\n\n🔄 *مبدل ارز*\nمقدار یک ارز را به ارز دیگر تبدیل کن.\n\n⭐ *علاقه‌مندی‌ها*\nدارایی‌های مورد علاقه‌ات را ذخیره کن تا سریع‌تر به آن‌ها دسترسی داشته باشی.\n\n🔔 *هشدار قیمت*\nبرای یک دارایی قیمت هدف تعیین کن تا در صورت رسیدن قیمت به محدوده موردنظر، هشدار دریافت کنی.\n\n📋 *هشدارهای من*\nهشدارهای فعال خودت را ببین و مدیریت کن.\n\n🎁 *دعوت دوستان*\nلینک دعوت اختصاصی بگیر و دوستانت را به بات دعوت کن.\n\n🏆 *جدول قهرمانان*\nآمار دعوت کاربران را مشاهده کن.\n\n👤 *پروفایل من*\nاطلاعات حساب و تنظیمات زبانت را مدیریت کن. از همین بخش می‌توانی از حساب خارج شوی و بعداً دوباره ثبت‌نام کنی.\n\n📌 *چند نکته*\n• برای استفاده از هر قابلیت، کافی است از منوی اصلی گزینه مربوط را انتخاب کنی.\n• قیمت‌ها ممکن است با توجه به منبع داده و زمان بروزرسانی تغییر کنند.\n• اگر مشکلی دیدی، از راه ارتباطی درج‌شده در پایین پیام‌ها استفاده کن.\n\n📢 *عضویت در کانال*\nبرای استفاده از بات، ابتدا باید عضو کانال اطلاع‌رسانی ارز آنلاین باشی. بعد از عضویت، دکمه «بررسی عضویت» را بزن تا دسترسی به بات فعال شود.\n\n📢 کانال: {channel}",
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
        "logout_confirm": "⚠️ با خروج از حساب، پروفایل فعلی شما از حالت فعال خارج می‌شود و برای ورود بعدی باید دوباره ثبت‌نام کنید. اطلاعات قدیمی کاربران دیگر با این کار آسیب نمی‌بیند.\n\nآیا مطمئن هستید؟",
        "logout_done": "✅ از حساب خارج شدید.\n\nبرای ساخت پروفایل جدید، /start را بزنید.",
        "cancel": "✅ عملیات لغو شد.",
        "error": "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
        "not_found": "❌ یافت نشد.",
        "crypto_title": "🪙 *ارز دیجیتال*\n\nیکی از رمزارزها را انتخاب کنید:",
        "fiat_title": "💵 *ارزهای فیات*\n\nیکی از ارزها را انتخاب کنید:",
        "gold_title": "🥇 *طلا و سکه*\n\nیکی از گزینه‌ها را انتخاب کنید:",
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
        "invite_reward": "\n🎁 *پاداش:*\n• ۵ دعوت: 🔔 قابلیت هشدار قیمت حرفه‌ای برای شما باز می‌شود.\n• با دعوت‌های بیشتر: رتبه شما در جدول قهرمانان بالاتر می‌رود و به رشد جامعه ارز آنلاین کمک می‌کنید.",
        "invite_copy": "📋 کپی لینک دعوت",
        "leaderboard_title": "🏆 *جدول قهرمانان*",
        "leaderboard_you": "\n📍 رتبه شما: *#{rank}* با *{count}* دعوت",
        "leaderboard_empty": "هنوز هیچ کاربری کسی رو دعوت نکرده. اولین نفر باش!",
        "share_btn": "📤 اشتراک‌گذاری با دوستان",
    },
    "en": {
        "choose_language": "🌐 Please choose your language:",
        "welcome_new": "Hello! 👋\n\nWelcome to *Arz Online*.\n\nPlease enter your *full name* to get started:",
        "ask_phone": "",
        "invalid_phone": "❌ Invalid phone number.\nPlease enter a valid Iranian mobile number (Example: 09123456789):",
        "invalid_name": "❌ Invalid name (at least 3 characters). Please try again:",
        "register_success": "✅ *Registration successful!*\n\n👤 Name: *{name}*\n🌐 Language: {lang_name}\n\nWelcome! Use the menu below:",
        "welcome_back": "👋 Hello *{name}*! Welcome back.\n\nUse the menu below:",
        "menu_title": "🏠 *Main Menu*\n\nPlease choose one of the options below:",
        "menu_crypto": "🪙 Cryptocurrency",
        "menu_fiat": "💵 Fiat Currencies",
        "menu_gold": "🥇 Gold & Coins",
        "menu_convert": "🔄 Currency Converter",
        "menu_fav": "⭐ Favorites",
        "menu_alert": "🔔 Price Alert",
        "menu_myalerts": "📋 My Alerts",
        "menu_list": "📊 Crypto List",
        "menu_profile": "👤 My Profile",
        "menu_invite": "🎁 Invite Friends",
        "menu_leaderboard": "🏆 Leaderboard",
        "menu_help": "ℹ️ Help",
        "help_title": "ℹ️ *Arz Online Guide*",
        "help_text": "Welcome to *Arz Online*! 👋\n\nThis bot gives you quick access to cryptocurrency, fiat currency, gold and coin prices, plus useful market tools.\n\n🪙 *Cryptocurrency*\nView cryptocurrency prices and browse the available coins.\n\n💵 *Fiat Currencies*\nCheck prices for common currencies such as USD and EUR.\n\n🥇 *Gold & Coins*\nView gold and coin prices.\n\n🔄 *Currency Converter*\nConvert an amount from one supported currency or asset to another.\n\n⭐ *Favorites*\nSave assets you use often for quicker access.\n\n🔔 *Price Alert*\nSet a target price and receive an alert when the selected asset reaches it.\n\n📋 *My Alerts*\nView and manage your active price alerts.\n\n🎁 *Invite Friends*\nGet your personal invite link and invite friends to the bot.\n\n🏆 *Leaderboard*\nView invitation statistics and rankings.\n\n👤 *My Profile*\nManage your account information and language. You can also log out and register again later.\n\n📌 *A few notes*\n• Choose any feature directly from the main menu.\n• Prices may change depending on the data source and update time.\n• If you have a problem, use the contact information shown at the bottom of messages.\n\n📢 *Channel Membership*\nTo use the bot, first join the Arz Online information channel. After joining, press the membership verification button to activate access.\n\n📢 Channel: {channel}",
        "menu_main": "🏠 Main Menu",
        "menu_back": "🔙 Back",
        "menu_cancel": "❌ Cancel",
        "profile_title": "👤 *Your Profile*",
        "profile_name": "📝 Name: *{name}*",
        "profile_phone": "📱 Phone: `{phone}`",
        "profile_lang": "🌐 Language: {lang_name}",
        "profile_joined": "📅 Joined: {date}",
        "profile_invites": "🎁 Invited: *{count}* users",
        "profile_user_type": "👑 Account type: *{user_type}*",
        "user_type_special": "Special User ⭐",
        "user_type_normal": "Normal User 👤",
        "pro_locked": "🔒 This is a professional feature.\n\nInvite at least *5 people* using your referral link to unlock professional access.",
        "pro_unlocked": "✨ Your professional access is active.",
        "profile_change_lang": "🌐 Change Language",
        "profile_logout": "🚪 Log out",
        "logout_confirm": "⚠️ Logging out deactivates your current profile. You can register again with /start. Existing users are not affected.\n\nAre you sure?",
        "logout_done": "✅ You have logged out.\n\nUse /start to create/register your profile again.",
        "cancel": "✅ Operation cancelled.",
        "error": "❌ An error occurred. Please try again.",
        "not_found": "❌ Not found.",
        "crypto_title": "🪙 *Cryptocurrency*\n\nChoose a coin:",
        "fiat_title": "💵 *Fiat Currencies*\n\nChoose a currency:",
        "gold_title": "🥇 *Gold & Coins*\n\nChoose an option:",
        "footer": "\n\n━━━━━━━━━━━━━━━━━━\n👨‍💻 Developer: *{dev}*\n📩 Feedback: {feedback}",
        "force_join_title": "⚠️ *Access Restricted*",
        "force_join_text": "To use the bot, please join our channel first:\n\n📢 {channel}\n\nAfter joining, click the button below:",
        "force_join_btn": "✅ I Joined",
        "force_join_verify": "🔄 Verify Membership",
        "force_join_not_member": "❌ You haven't joined the channel yet.\n\nPlease join first, then click verify.",
        "invite_title": "🎁 *Referral System*",
        "invite_link": "🔗 Your personal invite link:",
        "invite_stats": "📊 *Your Stats:*",
        "invite_count": "• Invited users: *{count}*",
        "invite_rank": "• Your rank: *#{rank}*",
        "invite_reward": "\n🎁 *Rewards:*\n• 5 invites: Free special alert\n• 10 invites: VIP support\n• 20 invites: Special access",
        "invite_copy": "📋 Copy invite link",
        "leaderboard_title": "🏆 *Leaderboard*",
        "leaderboard_you": "\n📍 Your rank: *#{rank}* with *{count}* invites",
        "leaderboard_empty": "Nobody has invited anyone yet. Be the first!",
        "share_btn": "📤 Share with friends",
    }
}

LANG_NAMES = {"fa": "فارسی", "en": "English"}


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
_force_join_cache = {}  # {user_id: timestamp} - فقط کش کوتاه‌مدت تأیید عضویت

# ============================================================
#       دیتابیس
# ============================================================
db_client = None
alerts_collection = None
favorites_collection = None
users_collection = None
referrals_collection = None


async def init_db():
    global db_client, alerts_collection, favorites_collection, users_collection, referrals_collection
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

        try:
            await alerts_collection.create_index([("chat_id", 1), ("asset", 1)])
            await alerts_collection.create_index([("asset", 1), ("direction", 1)])
            await users_collection.create_index([("account_status", 1), ("last_seen_at", -1)])
        except Exception as e:
            print(f"⚠️ index setup: {e}", flush=True)

        # Indexها باعث می‌شوند شناسایی کاربر و Queryهای پرتکرار سریع و پایدار بمانند.
        # هر Index جداگانه مدیریت می‌شود تا اگر دیتای قدیمی duplicate داشت،
        # کل اتصال دیتابیس به خاطر یک Index از کار نیفتد.
        index_jobs = [
            (users_collection, "chat_id", {"unique": True}),
            (alerts_collection, [("chat_id", 1), ("asset", 1)], {"unique": True}),
            (favorites_collection, [("chat_id", 1), ("asset", 1)], {"unique": True}),
            (referrals_collection, [("referrer", 1), ("referred", 1)], {"unique": True}),
        ]
        for collection, keys, options in index_jobs:
            try:
                await collection.create_index(keys, **options)
            except Exception as index_error:
                print(f"⚠️ Index warning ({getattr(collection, 'name', 'unknown')}): {index_error}", flush=True)
                # اگر دیتای قدیمی duplicate بود، یک Index معمولی هم می‌سازیم.
                try:
                    await collection.create_index(keys)
                except Exception as fallback_error:
                    print(f"⚠️ Fallback index failed: {fallback_error}", flush=True)

        print("✅ اتصال به MongoDB با موفقیت برقرار شد + Indexها بررسی شدند!", flush=True)
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
    if price_val is None:
        return "نامشخص"
    try:
        price_num = float(price_val)
        if price_num.is_integer():
            return f"{int(price_num):,}"
        return f"{price_num:,.2f}"
    except (ValueError, TypeError):
        return str(price_val)


def get_user_id_from_message(message):
    return str(message.author.id)


def get_user_id_from_callback(callback):
    try:
        if hasattr(callback, 'from_user') and callback.from_user:
            return str(callback.from_user.id)
    except:
        pass
    try:
        return str(callback.message.author.id)
    except:
        try:
            return str(callback.message.chat.id)
        except:
            return None


def clear_state(user_id):
    if user_id in user_states:
        del user_states[user_id]


def get_asset_display_name(asset_key):
    if asset_key in GOLD_NAMES:
        return GOLD_NAMES[asset_key]
    if asset_key in FIAT_NAMES:
        return FIAT_NAMES[asset_key]
    if asset_key == "TOMAN":
        return "تومان"
    return asset_key


# --- توابع دیتابیس: کاربران ---
def _chat_id_variants(chat_id):
    """شناسه کاربر را به شکل‌های سازگار با نسخه‌های قدیمی/جدید آماده می‌کند.

    نسخه‌های قدیمی ممکن است chat_id را به صورت عددی در MongoDB ذخیره کرده باشند،
    در حالی که نسخه جدید آن را به صورت رشته ذخیره می‌کند. برای جلوگیری از
    ثبت‌نام مجدد کاربران قدیمی، هر دو نوع را جستجو می‌کنیم.
    """
    sid = str(chat_id)
    variants = [sid]
    try:
        iid = int(sid)
        if iid != sid:
            variants.append(iid)
        elif iid not in variants:
            variants.append(iid)
    except (TypeError, ValueError):
        pass
    return variants


def _chat_id_filter(chat_id):
    variants = _chat_id_variants(chat_id)
    if len(variants) == 1:
        return {"chat_id": variants[0]}
    return {"chat_id": {"$in": variants}}


async def get_user(chat_id):
    if users_collection is None:
        return None
    try:
        # سازگاری با کاربران ثبت‌نام‌شده در نسخه‌های قبلی:
        # chat_id ممکن است int یا str باشد.
        return await users_collection.find_one(_chat_id_filter(chat_id))
    except Exception as e:
        print(f"⚠️ get_user error: {e}", flush=True)
        return None


async def get_active_user(chat_id):
    """فقط حساب فعال را برمی‌گرداند؛ حسابی که کاربر عمداً از آن خارج شده فعال محسوب نمی‌شود."""
    user = await get_user(chat_id)
    if user and user.get("account_status", "active") != "logged_out":
        return user
    return None


async def logout_user(chat_id):
    """خروج نرم: رکورد حذف نمی‌شود تا سابقه و آمار حفظ شود، اما حساب برای /start بعدی غیرفعال می‌شود."""
    if users_collection is None:
        return False
    try:
        user = await get_user(chat_id)
        if not user:
            return False
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "account_status": "logged_out",
                "logged_out_at": time.time(),
                "updated_at": time.time()
            }, "$unset": {"phone": ""}}
        )
        clear_state(str(chat_id))
        clear_lang_cache(str(chat_id))
        clear_force_join_cache(str(chat_id))
        return True
    except Exception as e:
        print(f"❌ logout_user error: {e}", flush=True)
        return False


async def set_user_blocked(chat_id, blocked=True):
    if users_collection is None:
        return False
    try:
        user = await get_user(chat_id)
        if not user:
            return False
        await users_collection.update_one({"_id": user["_id"]}, {"$set": {"blocked": bool(blocked), "updated_at": time.time()}})
        return True
    except Exception as e:
        print(f"❌ set_user_blocked error: {e}", flush=True)
        return False


async def create_user(chat_id, name, phone=None, language="fa", referred_by=None):
    """ثبت/به‌روزرسانی کاربر.

    نکته مهم سازگاری:
    - کاربران قدیمی که phone دارند دست‌نخورده می‌مانند.
    - کاربران جدید از این نسخه به بعد اصلاً phone دریافت نمی‌کنند.
    - تغییر زبان یا اطلاعات کاربر قدیمی، phone قبلی را پاک نمی‌کند.
    """
    if users_collection is None:
        return False
    chat_id = str(chat_id)
    try:
        # ابتدا هم رکوردهای جدید (chat_id رشته‌ای) و هم رکوردهای قدیمی
        # (chat_id عددی) را پیدا می‌کنیم.
        existing = await users_collection.find_one(_chat_id_filter(chat_id))
        if existing:
            update = {
                "name": name or existing.get("name", "کاربر"),
                "language": language or existing.get("language", "fa"),
                "account_status": "active",
                "updated_at": time.time(),
                "last_seen_at": time.time(),
            }
            # فقط اگر صراحتاً phone داده شده باشد، مقدار قبلی را تغییر بده.
            # ثبت‌نام جدید phone=None دارد و بنابراین شماره قدیمی کاربران قبلی حذف نمی‌شود.
            if phone is not None:
                update["phone"] = phone

            # با _id خود رکورد آپدیت می‌کنیم تا چه chat_id قدیمی عددی باشد
            # چه رشته‌ای، همان کاربر قبلی حفظ شود.
            await users_collection.update_one({"_id": existing["_id"]}, {"$set": update})
            return True

        doc = {
            "chat_id": chat_id,
            "name": name or "کاربر",
            "language": language or "fa",
            "created_at": time.time(),
            "updated_at": time.time(),
            "last_seen_at": time.time(),
            "account_status": "active",
            "blocked": False,
            "special_user": False,
            "referred_by": str(referred_by) if referred_by else None,
            "invite_count": 0,
        }
        # phone عمداً برای کاربران جدید ذخیره نمی‌شود.
        await users_collection.insert_one(doc)

        if referred_by and str(referred_by) != chat_id and referrals_collection is not None:
            try:
                result = await referrals_collection.update_one(
                    {"referrer": str(referred_by), "referred": chat_id},
                    {"$setOnInsert": {
                        "referrer": str(referred_by),
                        "referred": chat_id,
                        "created_at": time.time()
                    }},
                    upsert=True
                )
                if result.upserted_id is not None:
                    await users_collection.update_one(
                        _chat_id_filter(referred_by),
                        {"$inc": {"invite_count": 1}}
                    )
            except Exception as referral_error:
                print(f"⚠️ referral error: {referral_error}", flush=True)
        return True
    except Exception as e:
        print(f"❌ create_user error: {e}", flush=True)
        return False


async def touch_user(chat_id):
    if users_collection is None:
        return
    try:
        await users_collection.update_one(
            _chat_id_filter(chat_id),
            {"$set": {"last_seen_at": time.time()}}
        )
    except Exception:
        pass


async def get_user_language(chat_id):
    chat_id_str = str(chat_id)
    if chat_id_str in _user_lang_cache:
        return _user_lang_cache[chat_id_str]
    user = await get_user(chat_id_str)
    lang = user.get("language", "fa") if user else "fa"
    _user_lang_cache[chat_id_str] = lang
    return lang


def clear_lang_cache(chat_id):
    chat_id_str = str(chat_id)
    if chat_id_str in _user_lang_cache:
        del _user_lang_cache[chat_id_str]


async def get_users_count():
    if users_collection is None:
        return 0
    try:
        return await users_collection.count_documents({})
    except:
        return 0


async def get_invite_count(chat_id):
    if users_collection is None:
        return 0
    try:
        user = await users_collection.find_one({"chat_id": str(chat_id)})
        return user.get("invite_count", 0) if user else 0
    except:
        return 0


async def get_user_rank(chat_id):
    """رتبه کاربر بر اساس تعداد دعوت‌شده"""
    if users_collection is None:
        return 0
    try:
        # تعداد کاربرانی که بیشتر از این کاربر دعوت کردن
        my_count = await get_invite_count(chat_id)
        higher = await users_collection.count_documents({"invite_count": {"$gt": my_count}})
        return higher + 1
    except:
        return 0


async def get_leaderboard(limit=10):
    """گرفتن برترین دعوت‌کنندگان"""
    if users_collection is None:
        return []
    try:
        cursor = users_collection.find({"invite_count": {"$gt": 0}}).sort("invite_count", -1).limit(limit)
        return await cursor.to_list(length=limit)
    except:
        return []


# --- توابع دیتابیس: هشدارها ---
async def is_special_user(chat_id):
    user = await get_user(chat_id)
    return bool(user and user.get("special_user") is True)


async def get_effective_invite_count(chat_id):
    user = await get_user(chat_id)
    if not user:
        return 0
    return int(user.get("invite_count", 0) or 0)


async def has_pro_access(chat_id):
    """دسترسی حرفه‌ای: کاربر خاص یا حداقل آستانه دعوت."""
    user = await get_user(chat_id)
    if not user or user.get("blocked"):
        return False
    if user.get("special_user") is True:
        return True
    return int(user.get("invite_count", 0) or 0) >= PRO_INVITE_THRESHOLD


async def set_special_user(chat_id, special=True):
    if users_collection is None:
        return False
    try:
        user = await get_user(chat_id)
        if not user:
            return False
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"special_user": bool(special), "updated_at": time.time()}}
        )
        return True
    except Exception as e:
        print(f"❌ set_special_user error: {e}", flush=True)
        return False


async def get_special_users_count():
    if users_collection is None:
        return 0
    try:
        return await users_collection.count_documents({"special_user": True})
    except Exception:
        return 0


async def add_alert(chat_id, asset_key, target_price, direction):
    if alerts_collection is None:
        return False
    try:
        target = float(target_price)
        if target <= 0 or direction not in {"above", "below"}:
            return False
        asset_key = str(asset_key).strip().upper()
        await alerts_collection.delete_many({"chat_id": str(chat_id), "asset": asset_key})
        await alerts_collection.insert_one({
            "chat_id": str(chat_id),
            "asset": asset_key,
            "target_price": target,
            "direction": direction,
            "created_at": time.time(),
            "triggered": False
        })
        return True
    except Exception as e:
        print(f"❌ add_alert error: {e}", flush=True)
        return False


async def get_user_alerts(chat_id):
    if alerts_collection is not None:
        cursor = alerts_collection.find({"chat_id": str(chat_id)})
        return await cursor.to_list(length=None)
    return []


async def remove_alert(chat_id, asset_key):
    if alerts_collection is not None:
        await alerts_collection.delete_one({"chat_id": str(chat_id), "asset": asset_key})


async def get_all_alerts():
    if alerts_collection is not None:
        cursor = alerts_collection.find({})
        return await cursor.to_list(length=None)
    return []


async def remove_all_user_alerts(chat_id):
    if alerts_collection is None:
        return 0
    result = await alerts_collection.delete_many({"chat_id": str(chat_id)})
    return result.deleted_count


# --- توابع دیتابیس: علاقه‌مندی‌ها ---
async def add_favorite(chat_id, asset_key):
    if favorites_collection is not None:
        existing = await favorites_collection.find_one({"chat_id": str(chat_id), "asset": asset_key})
        if existing is None:
            await favorites_collection.insert_one({"chat_id": str(chat_id), "asset": asset_key, "created_at": time.time()})
            return True
        return False
    return False


async def remove_favorite(chat_id, asset_key):
    if favorites_collection is not None:
        await favorites_collection.delete_one({"chat_id": str(chat_id), "asset": asset_key})


async def get_user_favorites(chat_id):
    if favorites_collection is not None:
        cursor = favorites_collection.find({"chat_id": str(chat_id)})
        docs = await cursor.to_list(length=None)
        return [d["asset"] for d in docs]
    return []


async def is_favorite(chat_id, asset_key):
    favs = await get_user_favorites(chat_id)
    return asset_key in favs


# --- عضویت اجباری ---
async def check_channel_membership(user_id, use_cache=True):
    """بررسی حرفه‌ای عضویت کاربر در کانال بله.

    نکات مهم:
    - برای جلوگیری از مشکل پروکسی سفارشی، بررسی عضویت مستقیماً از Bale Bot API انجام می‌شود.
    - نتیجه status هم در حالت رشته و هم در حالت Enum/آبجکت مدیریت می‌شود.
    - در صورت خطا، کاربر عضو فرض نمی‌شود (fail-closed).
    - دکمه «بررسی عضویت» همیشه cache را دور می‌زند.

    طبق مستندات python-bale-bot، get_chat_member برای بررسی کاربران دیگر
    عملاً نیازمند دسترسی مدیریتی مناسب بات در کانال است.
    """
    user_id = str(user_id)
    now = time.time()

    if use_cache and user_id in _force_join_cache:
        cached_at = _force_join_cache[user_id]
        if (now - cached_at) < 60:
            return True
        _force_join_cache.pop(user_id, None)

    # اول API مستقیم Bale را امتحان می‌کنیم تا Proxy سفارشی روی بررسی عضویت اثر نگذارد.
    api_url = f"https://tapi.bale.ai/bot{BOT_TOKEN}/getChatMember"
    payload = {
        "chat_id": CHANNEL_ID,
        "user_id": int(user_id),
    }

    try:
        def _direct_membership_request():
            return requests.post(api_url, json=payload, timeout=15)

        response = await asyncio.to_thread(_direct_membership_request)

        try:
            body = response.json()
        except Exception:
            body = {}

        if response.status_code != 200 or not body.get("ok", False):
            description = body.get("description", "پاسخ نامعتبر از API بله")
            print(
                f"❌ Force Join API | user={user_id} | http={response.status_code} | {description}",
                flush=True,
            )
            _force_join_cache.pop(user_id, None)
            return False

        result = body.get("result") or {}
        raw_status = result.get("status")

        # Bale API معمولاً status را به صورت member / administrator / creator برمی‌گرداند.
        # این نرمال‌سازی برای نسخه‌هایی که status را به شکل Enum یا رشته نمایشی می‌دهند هم هست.
        status_candidates = {
            str(raw_status).strip().lower(),
            str(getattr(raw_status, "value", "")).strip().lower(),
            str(getattr(raw_status, "name", "")).strip().lower(),
        }
        status_candidates.discard("")

        is_member = bool(status_candidates.intersection({
            "member",
            "administrator",
            "creator",
            "admin",
            "owner",
            "chatmemberstatus.member",
            "chatmemberstatus.administrator",
            "chatmemberstatus.creator",
        }))

        # بعض نسخه‌ها ممکن است status را با قالب enum چاپ کنند؛ انتهای مقدار را هم بررسی می‌کنیم.
        if not is_member:
            for candidate in status_candidates:
                if candidate.endswith(".member") or candidate.endswith(".administrator") or candidate.endswith(".creator"):
                    is_member = True
                    break

        if is_member:
            _force_join_cache[user_id] = now
        else:
            _force_join_cache.pop(user_id, None)

        print(
            f"🔎 Force Join | user={user_id} | channel={CHANNEL_ID} | status={raw_status!r} | normalized={sorted(status_candidates)} | member={is_member}",
            flush=True,
        )
        return is_member

    except Exception as direct_error:
        _force_join_cache.pop(user_id, None)
        print(
            f"❌ Force Join direct API error | user={user_id} | {type(direct_error).__name__}: {direct_error}",
            flush=True,
        )

        # اگر API مستقیم در دسترس نبود، یک fallback به خود کتابخانه Bale می‌زنیم.
        # این fallback هم fail-closed است.
        try:
            response = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=int(user_id))
            if response is None:
                return False

            raw_status = getattr(response, "status", None)
            status_candidates = {
                str(raw_status).strip().lower(),
                str(getattr(raw_status, "value", "")).strip().lower(),
                str(getattr(raw_status, "name", "")).strip().lower(),
            }
            status_candidates.discard("")

            is_member = bool(status_candidates.intersection({
                "member", "administrator", "creator", "admin", "owner",
                "chatmemberstatus.member",
                "chatmemberstatus.administrator",
                "chatmemberstatus.creator",
            }))
            if not is_member:
                is_member = any(
                    x.endswith(".member") or x.endswith(".administrator") or x.endswith(".creator")
                    for x in status_candidates
                )

            print(
                f"🔎 Force Join fallback | user={user_id} | status={raw_status!r} | member={is_member}",
                flush=True,
            )
            if is_member:
                _force_join_cache[user_id] = now
            return is_member
        except Exception as fallback_error:
            print(
                f"❌ Force Join fallback error | user={user_id} | {type(fallback_error).__name__}: {fallback_error}",
                flush=True,
            )
            return False


def clear_force_join_cache(user_id):
    """حذف نتیجه کش عضویت برای بررسی مجدد واقعی."""
    _force_join_cache.pop(str(user_id), None)


# --- قیمت‌ها ---
_fiat_cache = {"data": None, "timestamp": 0}
_FIAT_CACHE_TTL = 120
_gold_cache = {}  # {asset: {"data": ..., "timestamp": ...}}
_GOLD_CACHE_TTL = 45
_price_cache = {}  # {asset: {"data": ..., "timestamp": ...}}
_PRICE_CACHE_TTL = 20


def _get_all_fiat_data():
    now = time.time()
    if _fiat_cache["data"] and (now - _fiat_cache["timestamp"]) < _FIAT_CACHE_TTL:
        return _fiat_cache["data"]
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(FIAT_API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            _fiat_cache["data"] = data
            _fiat_cache["timestamp"] = now
            return data
    except Exception as e:
        print(f"⚠️ Navasan fiat failed: {type(e).__name__}", flush=True)
    return _fiat_cache["data"]


def fetch_fiat_data(symbol: str):
    symbol_lower = symbol.strip().lower()
    try:
        data = _get_all_fiat_data()
        if not data:
            return None
        if symbol_lower in data:
            price_data = data[symbol_lower]
            price = None
            if isinstance(price_data, dict):
                price = price_data.get("value") or price_data.get("price") or price_data.get("rate")
            else:
                price = price_data
            if price is not None:
                price_in_toman = float(str(price).replace(",", ""))
                if price_in_toman > 10_000_000:
                    price_in_toman = price_in_toman / 10
                return {"symbol": symbol.upper(), "price": price_in_toman}
        return None
    except Exception as e:
        print(f"⚠️ Navasan fiat failed for {symbol}: {type(e).__name__}", flush=True)
        return None


_abantether_cache = {"data": None, "timestamp": 0}
_ABAN_CACHE_TTL = 60


def _get_abantether_data():
    now = time.time()
    if _abantether_cache["data"] and (now - _abantether_cache["timestamp"]) < _ABAN_CACHE_TTL:
        return _abantether_cache["data"]
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt, timeout in enumerate([20, 25, 30]):
        try:
            response = requests.get(CRYPTO_API_URL, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            _abantether_cache["data"] = data
            _abantether_cache["timestamp"] = now
            return data
        except Exception as e:
            print(f"⚠️ Abantether attempt {attempt+1} failed: {type(e).__name__}", flush=True)
            time.sleep(2)
    return None


def _fetch_abantether(symbol):
    try:
        market = _get_abantether_data()
        if not market:
            return None
        markets_data = market.get("data", {}).get("markets", {})
        if not markets_data:
            return None
        target_key = None
        data = None
        if isinstance(markets_data, dict):
            if symbol in markets_data:
                target_key = symbol
            elif f"{symbol}IRT" in markets_data:
                target_key = f"{symbol}IRT"
            else:
                for key in markets_data.keys():
                    if symbol in key.upper():
                        target_key = key
                        break
            if target_key:
                data = markets_data[target_key]
        elif isinstance(markets_data, list):
            for item in markets_data:
                item_symbol = str(item.get("symbol", "")).upper()
                if item_symbol == symbol or item_symbol == f"{symbol}IRT" or symbol in item_symbol:
                    target_key = item_symbol
                    data = item
                    break
        if target_key and data:
            buy_price = data.get("buy_price")
            sell_price = data.get("sell_price")
            change = None
            for key in data.keys():
                if "change" in key.lower() or "percent" in key.lower():
                    change = data[key]
                    break
            return {"symbol": target_key, "buy_price": buy_price, "sell_price": sell_price, "change": change}
        return None
    except Exception as e:
        print(f"⚠️ Abantether parse failed: {type(e).__name__}", flush=True)
        return None


def _fetch_nobitex_crypto(symbol):
    try:
        url = f"https://api.nobitex.ir/v2/orderbook/{symbol}IRT"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok":
            last_price = data.get("lastTradePrice")
            if last_price:
                price_in_toman = float(last_price) / 10
                return {"symbol": symbol, "buy_price": price_in_toman, "sell_price": price_in_toman, "change": None}
        return None
    except Exception as e:
        print(f"⚠️ Nobitex crypto failed: {type(e).__name__}", flush=True)
        return None


def fetch_crypto_data(symbol: str):
    symbol = symbol.strip().upper()
    data = _fetch_abantether(symbol)
    if data:
        return data
    data = _fetch_nobitex_crypto(symbol)
    if data:
        return data
    return None


def _get_json_price(data, keys_list):
    if data is None:
        return None
    if isinstance(data, (int, float, str)):
        try:
            return float(str(data).replace(",", ""))
        except (ValueError, TypeError):
            return None
    if isinstance(data, dict):
        for key in keys_list:
            if key in data:
                val = data[key]
                if isinstance(val, (int, float, str)):
                    try:
                        return float(str(val).replace(",", ""))
                    except (ValueError, TypeError):
                        pass
                elif isinstance(val, dict):
                    for sub_key in ["value", "price", "rate", "close", "p"]:
                        if sub_key in val:
                            try:
                                return float(str(val[sub_key]).replace(",", ""))
                            except (ValueError, TypeError):
                                pass
        for val in data.values():
            if isinstance(val, (int, float)):
                return float(val)
            elif isinstance(val, dict):
                for sub_val in val.values():
                    if isinstance(sub_val, (int, float)):
                        return float(sub_val)
    if isinstance(data, list) and len(data) > 0:
        return _get_json_price(data[0], keys_list)
    return None


def _fetch_gold_data_uncached(asset_key: str):
    key_map = {"gold_18": "18ayar", "coin_emami": "sekkeh", "coin_bahar": "bahar",
               "coin_half": "nim", "coin_quarter": "rob", "coin_gerami": "gerami"}
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(GOLD_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return None
        if asset_key in key_map:
            json_key = key_map[asset_key]
            if json_key in data:
                price = _get_json_price(data[json_key], ["value", "price", "rate"])
                if price is not None:
                    return {"symbol": asset_key, "price": price}
        if asset_key == "gold_24":
            price_18 = _get_json_price(data.get("18ayar"), ["value", "price"])
            if price_18:
                return {"symbol": asset_key, "price": price_18 * (24 / 18)}
        if asset_key == "gold_miskal":
            price_18 = _get_json_price(data.get("18ayar"), ["value", "price"])
            if price_18:
                return {"symbol": asset_key, "price": price_18 * 4.608}
        return None
    except Exception as e:
        print(f"API Error (Gold): {e}", flush=True)
        return None


def fetch_gold_data(asset_key: str):
    """دریافت قیمت طلا با Cache کوتاه‌مدت برای کاهش فشار روی API."""
    now = time.time()
    cached = _gold_cache.get(asset_key)
    if cached and (now - cached["timestamp"]) < _GOLD_CACHE_TTL:
        return cached["data"]
    data = _fetch_gold_data_uncached(asset_key)
    if data:
        _gold_cache[asset_key] = {"data": data, "timestamp": now}
        return data
    # در خطای موقت API، آخرین مقدار سالم را برگردانیم؛ فقط اگر وجود داشته باشد.
    return cached["data"] if cached else None


def invalidate_price_cache(asset_key=None):
    if asset_key is None:
        _price_cache.clear()
        return
    _price_cache.pop(str(asset_key).upper(), None)



def get_current_price(asset_key: str):
    """قیمت واحد با Cache مرکزی؛ منابع اصلی خودشان نیز Cache دارند."""
    key = str(asset_key).strip().upper()
    now = time.time()
    cached = _price_cache.get(key)
    if cached and (now - cached["timestamp"]) < _PRICE_CACHE_TTL:
        return cached["data"]

    if key == "TOMAN":
        data = {"symbol": "TOMAN", "price": 1.0}
    elif key.lower() in GOLD_NAMES:
        data = fetch_gold_data(key.lower())
    elif key in FIAT_NAMES:
        data = fetch_fiat_data(key)
    else:
        crypto = fetch_crypto_data(key)
        data = {"symbol": crypto["symbol"], "price": crypto["buy_price"]} if crypto else None

    if data and data.get("price") is not None:
        _price_cache[key] = {"data": data, "timestamp": now}
    return data


# ============================================================
#                     کیبوردها
# ============================================================

def language_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="LANG:fa"), row=0)
    markup.add(InlineKeyboardButton(text="🇬🇧 English", callback_data="LANG:en"), row=0)
    return markup


def main_menu_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=t("menu_crypto", lang), callback_data="MENU:CRYPTO"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_fiat", lang), callback_data="MENU:FIAT"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_gold", lang), callback_data="MENU:GOLD"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_convert", lang), callback_data="CONV:NEW"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_fav", lang), callback_data="FAV:VIEW"), row=2)
    markup.add(InlineKeyboardButton(text=t("menu_alert", lang), callback_data="ALERT:NEW"), row=2)
    markup.add(InlineKeyboardButton(text=t("menu_myalerts", lang), callback_data="MENU:MYALERTS"), row=3)
    markup.add(InlineKeyboardButton(text=t("menu_list", lang), callback_data="MENU:LIST"), row=3)
    markup.add(InlineKeyboardButton(text=t("menu_invite", lang), callback_data="MENU:INVITE"), row=4)
    markup.add(InlineKeyboardButton(text=t("menu_leaderboard", lang), callback_data="MENU:LEADERBOARD"), row=4)
    markup.add(InlineKeyboardButton(text=t("menu_profile", lang), callback_data="MENU:PROFILE"), row=5)
    markup.add(InlineKeyboardButton(text=t("menu_help", lang), callback_data="MENU:HELP"), row=6)
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
        for sym in pair:
            markup.add(InlineKeyboardButton(text=sym, callback_data=f"CRYPTO:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text=t("menu_list", lang), callback_data="MENU:LIST"), row=next_row)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=next_row + 1)
    return markup


def fiat_menu_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    pairs = [POPULAR_FIATS[i:i+2] for i in range(0, len(POPULAR_FIATS), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            markup.add(InlineKeyboardButton(text=f"{FIAT_NAMES.get(sym, sym)}", callback_data=f"FIAT:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=next_row)
    return markup


def gold_menu_keyboard(lang="fa"):
    markup = InlineKeyboardMarkup()
    pairs = [POPULAR_GOLDS[i:i+2] for i in range(0, len(POPULAR_GOLDS), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            markup.add(InlineKeyboardButton(text=GOLD_NAMES.get(sym, sym), callback_data=f"GOLD:{sym}"), row=row_idx)
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
    if category == "crypto":
        assets = POPULAR_CRYPTOS[:8]
    elif category == "fiat":
        assets = POPULAR_FIATS[:8]
    elif category == "gold":
        assets = POPULAR_GOLDS[:6]
    else:
        assets = []
    pairs = [assets[i:i+2] for i in range(0, len(assets), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            name = GOLD_NAMES.get(sym, FIAT_NAMES.get(sym, sym))
            markup.add(InlineKeyboardButton(text=name, callback_data=f"ALERT:SET:{sym}"), row=row_idx)
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
        name = get_asset_display_name(a.get("asset", ""))
        direction_sym = "↑" if a.get("direction") == "above" else "↓"
        label = f"🗑 {name} {direction_sym} {format_price(a.get('target_price'))}"
        markup.add(InlineKeyboardButton(text=label, callback_data=f"DELALERT:{a.get('asset','')}"), row=idx)
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
    if category == "crypto":
        assets = POPULAR_CRYPTOS[:8]
    elif category == "fiat":
        assets = POPULAR_FIATS[:8]
    elif category == "gold":
        assets = POPULAR_GOLDS[:6]
    else:
        assets = []
    pairs = [assets[i:i+2] for i in range(0, len(assets), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            name = GOLD_NAMES.get(sym, FIAT_NAMES.get(sym, sym))
            if sym in user_favs:
                label = f"✅ {name}"
                callback = f"FAV:DEL:{sym}"
            else:
                label = f"➕ {name}"
                callback = f"FAV:ADD:{sym}"
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
    text = (
        f"✨ *ارز آنلاین* ✨\n\n"
        f"{t('welcome_back', lang, name=name)}\n\n"
        f"{t('menu_title', lang)}\n\n"
        "📌 قیمت لحظه‌ای ارز، رمزارز، طلا و سکه\n"
        "⚡ سریع • دقیق • همیشه در دسترس"
    )
    markup = main_menu_keyboard(lang)
    if edit:
        try:
            await target.edit(text + footer_text(lang), components=markup)
            return
        except:
            pass
    await target.reply(text + footer_text(lang), components=markup)


async def show_help(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    text = t("help_title", lang) + "\n\n" + t("help_text", lang).format(channel=CHANNEL_ID)
    markup = help_keyboard(lang)
    if edit:
        try:
            await target.edit(text + footer_text(lang), components=markup)
            return
        except:
            pass
    await target.reply(text + footer_text(lang), components=markup)


async def show_profile(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    user = await get_user(user_id)
    if not user:
        await target.reply(t("error", lang))
        return
    name = user.get("name", "-")
    phone = user.get("phone", "-")
    created_at = user.get("created_at", 0)
    joined = time.strftime('%Y-%m-%d', time.localtime(created_at)) if created_at else "-"
    lang_name = LANG_NAMES.get(lang, lang)
    invite_count = await get_invite_count(user_id)
    text = (
        f"{t('profile_title', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{t('profile_name', lang, name=name)}\n"
        f"{t('profile_phone', lang, phone=phone)}\n"
        f"{t('profile_lang', lang, lang_name=lang_name)}\n"
        f"{t('profile_joined', lang, date=joined)}\n"
        f"{t('profile_invites', lang, count=invite_count)}\n"
        f"{t('profile_user_type', lang, user_type=t('user_type_special', lang) if user.get('special_user') else t('user_type_normal', lang))}"
    )
    markup = profile_keyboard(lang)
    if edit:
        try:
            await target.edit(text + footer_text(lang), components=markup)
            return
        except:
            pass
    await target.reply(text + footer_text(lang), components=markup)


async def show_invite(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    invite_count = await get_invite_count(user_id)
    rank = await get_user_rank(user_id)
    invite_link = f"https://ble.ir/{BOT_USERNAME}?start={user_id}"
    text = (
        f"{t('invite_title', lang)}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{t('invite_link', lang)}\n"
        f"`{invite_link}`\n\n"
        f"{t('invite_stats', lang)}\n"
        f"{t('invite_count', lang, count=invite_count)}\n"
        f"{t('invite_rank', lang, rank=rank)}"
        f"{t('invite_reward', lang)}"
    )
    markup = invite_keyboard(lang)
    if edit:
        try:
            await target.edit(text + footer_text(lang), components=markup)
            return
        except:
            pass
    await target.reply(text + footer_text(lang), components=markup)


async def show_leaderboard(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    top_users = await get_leaderboard(10)
    my_count = await get_invite_count(user_id)
    my_rank = await get_user_rank(user_id)

    if not top_users:
        text = t("leaderboard_title", lang) + "\n\n" + t("leaderboard_empty", lang)
    else:
        lines = [t("leaderboard_title", lang), "━━━━━━━━━━━━━━━━━━"]
        medals = ["🥇", "🥈", "🥉"]
        for idx, u in enumerate(top_users, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}."
            name = u.get("name", "کاربر")
            count = u.get("invite_count", 0)
            lines.append(f"{medal} {name} → *{count}* دعوت")
        # اضافه کردن رتبه کاربر
        lines.append("")
        lines.append(t("leaderboard_you", lang, rank=my_rank, count=my_count))
        text = "\n".join(lines)

    markup = leaderboard_keyboard(lang)
    if edit:
        try:
            await target.edit(text + footer_text(lang), components=markup)
            return
        except:
            pass
    await target.reply(text + footer_text(lang), components=markup)


async def process_crypto_and_reply(message, symbol, user_id=None):
    lang = await get_user_language(user_id) if user_id else "fa"
    data = fetch_crypto_data(symbol)
    if not data:
        await message.reply(f"❌ {symbol.upper()} {t('not_found', lang)}" + footer_text(lang))
        return
    buy_price_str = format_price(data['buy_price'])
    sell_price_str = format_price(data['sell_price'])
    result_text = (
        f"📊 **{data['symbol']}**\n━━━━━━━━━━━━━━━━━━\n"
        f"💵: **{buy_price_str} IRT**\n💰: **{sell_price_str} IRT**\n"
    )
    if data['change'] is not None:
        try:
            change_val = float(data['change'])
            sign = "+" if change_val > 0 else ""
            change_color = "🟢" if change_val > 0 else "🔴" if change_val < 0 else "⚪"
            result_text += f"📈: {change_color} **{sign}{change_val:.2f}%**\n"
        except (ValueError, TypeError):
            pass
    markup = InlineKeyboardMarkup()
    if user_id:
        if await is_favorite(user_id, data['symbol']):
            markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها", callback_data=f"FAV:DEL:{data['symbol']}"), row=0)
        else:
            markup.add(InlineKeyboardButton(text="⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:ADD:{data['symbol']}"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_back", lang), callback_data="MENU:CRYPTO"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
    await message.reply(result_text + footer_text(lang), components=markup)


async def process_fiat_and_reply(message, symbol, user_id=None):
    lang = await get_user_language(user_id) if user_id else "fa"
    data = fetch_fiat_data(symbol)
    fiat_name = FIAT_NAMES.get(symbol.upper(), symbol.upper())
    if not data or data['price'] is None:
        await message.reply(f"❌ {fiat_name} {t('not_found', lang)}" + footer_text(lang))
        return
    price_str = format_price(data['price'])
    result_text = f"💵 **{fiat_name}**\n━━━━━━━━━━━━━━━━━━\n💰: **{price_str} تومان**\n"
    markup = InlineKeyboardMarkup()
    if user_id:
        if await is_favorite(user_id, symbol.upper()):
            markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها", callback_data=f"FAV:DEL:{symbol.upper()}"), row=0)
        else:
            markup.add(InlineKeyboardButton(text="⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:ADD:{symbol.upper()}"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_back", lang), callback_data="MENU:FIAT"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
    await message.reply(result_text + footer_text(lang), components=markup)


async def process_gold_and_reply(message, asset_key, user_id=None):
    lang = await get_user_language(user_id) if user_id else "fa"
    data = fetch_gold_data(asset_key)
    gold_name = GOLD_NAMES.get(asset_key, asset_key)
    if not data or data['price'] is None:
        await message.reply(f"❌ {gold_name} {t('not_found', lang)}" + footer_text(lang))
        return
    price_str = format_price(data['price'])
    result_text = f"🥇 **{gold_name}**\n━━━━━━━━━━━━━━━━━━\n💰: **{price_str} تومان**\n"
    markup = InlineKeyboardMarkup()
    if user_id:
        if await is_favorite(user_id, asset_key):
            markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها", callback_data=f"FAV:DEL:{asset_key}"), row=0)
        else:
            markup.add(InlineKeyboardButton(text="⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:ADD:{asset_key}"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_back", lang), callback_data="MENU:GOLD"), row=1)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
    await message.reply(result_text + footer_text(lang), components=markup)


async def show_my_alerts(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    alerts = await get_user_alerts(user_id)
    if not alerts:
        text = "📭 **هشدار فعالی ندارید.**\n\nبا ثبت هشدار، وقتی قیمت به شرط شما برسد، بات به شما پیام می‌دهد."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=t("menu_alert", lang), callback_data="ALERT:NEW"), row=0)
        markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=1)
        if edit:
            try:
                await target.edit(text + footer_text(lang), components=markup); return
            except: pass
        await target.reply(text + footer_text(lang), components=markup)
        return

    lines = ["🔔 **هشدارهای فعال شما**", "━━━━━━━━━━━━━━━━━━"]
    for a in alerts:
        asset = str(a.get("asset", "")).upper()
        name = get_asset_display_name(asset)
        direction_text = "بالا ⬆️" if a.get("direction") == "above" else "پایین ⬇️"
        current = get_current_price(asset)
        current_text = format_price(current["price"]) + " تومان" if current and current.get("price") is not None else "نامشخص"
        lines.append(
            f"🔸 **{name}**\n"
            f"   💰 فعلی: {current_text}\n"
            f"   🎯 هدف: {format_price(a.get('target_price'))} تومان\n"
            f"   📌 شرط: {direction_text}"
        )
    lines.append("\n💡 هشدار پس از ارسال موفق، خودکار حذف می‌شود.")
    text = "\n".join(lines)
    markup = alerts_list_keyboard(alerts, user_id, lang)
    if edit:
        try:
            await target.edit(text + footer_text(lang), components=markup); return
        except: pass
    await target.reply(text + footer_text(lang), components=markup)


async def show_favorites(target, user_id, edit=False):
    lang = await get_user_language(user_id)
    favs = await get_user_favorites(user_id)
    if not favs:
        text = "⭐ لیست علاقه‌مندی‌های شما خالیه!"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="➕ افزودن دارایی", callback_data="FAV:NEW"), row=0)
        markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=1)
        if edit:
            try:
                await target.edit(text + footer_text(lang), components=markup)
                return
            except:
                pass
        await target.reply(text + footer_text(lang), components=markup)
        return
    lines = ["⭐ **لیست علاقه‌مندی‌های شما:**\n"]
    for asset in favs:
        name = get_asset_display_name(asset)
        data = get_current_price(asset)
        if data and data.get("price") is not None:
            lines.append(f"🔸 **{name}** → {format_price(data['price'])} تومان")
        else:
            lines.append(f"🔸 **{name}** → ❌")
    text = "\n".join(lines)
    markup = fav_view_keyboard(lang)
    if edit:
        try:
            await target.edit(text + footer_text(lang), components=markup)
            return
        except:
            pass
    await target.reply(text + footer_text(lang), components=markup)


async def do_convert(target, amount, from_asset, to_asset, user_id=None):
    lang = await get_user_language(user_id) if user_id else "fa"
    from_price = get_current_price(from_asset)
    if not from_price or from_price.get("price") is None:
        await target.reply(f"❌ {get_asset_display_name(from_asset)} {t('not_found', lang)}" + footer_text(lang))
        return
    from_name = get_asset_display_name(from_asset)
    to_name = get_asset_display_name(to_asset)
    if to_asset == "TOMAN":
        result = amount * from_price["price"]
        result_text = (
            f"🔄 **نتیجه تبدیل**\n━━━━━━━━━━━━━━━━━━\n"
            f"💱 {amount:,.2f} {from_name}\n⬇️⬇️⬇️\n"
            f"💰 **{result:,.0f} تومان**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 نرخ: ۱ {from_name} = {format_price(from_price['price'])} تومان"
        )
    else:
        to_price = get_current_price(to_asset)
        if not to_price or to_price.get("price") is None:
            await target.reply(f"❌ {to_name} {t('not_found', lang)}" + footer_text(lang))
            return
        result = amount * from_price["price"] / to_price["price"]
        result_text = (
            f"🔄 **نتیجه تبدیل**\n━━━━━━━━━━━━━━━━━━\n"
            f"💱 {amount:,.2f} {from_name}\n⬇️⬇️⬇️\n"
            f"💰 **{result:,.4f} {to_name}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 نرخ {from_name}: {format_price(from_price['price'])} تومان\n"
            f"📊 نرخ {to_name}: {format_price(to_price['price'])} تومان"
        )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=t("menu_convert", lang), callback_data="CONV:NEW"), row=0)
    markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=1)
    await target.reply(result_text + footer_text(lang), components=markup)


# ============================================================
# --- چک‌کننده هشدارها ---
# ============================================================

async def alert_checker_async():
    """بررسی هشدارها با یک دریافت قیمت برای هر دارایی، نه یک API call برای هر کاربر."""
    print("🔔 Alert checker started!", flush=True)
    while True:
        try:
            alerts = await get_all_alerts()
            if not alerts:
                await asyncio.sleep(60)
                continue

            # هر دارایی فقط یک بار قیمت‌گذاری می‌شود؛ نتیجه بین همه هشدارها مشترک است.
            prices = {}
            for alert in alerts:
                asset = str(alert.get("asset", "")).upper()
                if asset and asset not in prices:
                    try:
                        prices[asset] = get_current_price(asset)
                    except Exception as e:
                        print(f"⚠️ Alert price error | asset={asset} | {e}", flush=True)
                        prices[asset] = None

            for alert in alerts:
                asset = str(alert.get("asset", "")).upper()
                current = prices.get(asset)
                if not current or current.get("price") is None:
                    continue
                try:
                    current_price = float(current["price"])
                    target = float(alert["target_price"])
                except (TypeError, ValueError):
                    continue

                direction = alert.get("direction")
                triggered = (direction == "above" and current_price >= target) or (direction == "below" and current_price <= target)
                if not triggered:
                    continue

                name = get_asset_display_name(asset)
                direction_text = "بالا رفت 📈" if direction == "above" else "پایین آمد 📉"
                notification = (
                    f"🔔 **هشدار قیمت فعال شد!**\n━━━━━━━━━━━━━━━━━━\n"
                    f"📊 دارایی: **{name}**\n"
                    f"💰 قیمت فعلی: **{format_price(current_price)} تومان**\n"
                    f"🎯 قیمت هدف: **{format_price(target)} تومان**\n"
                    f"📈 وضعیت: قیمت {direction_text}\n"
                    f"🕐 زمان: {time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                sent = False
                try:
                    await bot.send_message(alert["chat_id"], notification)
                    sent = True
                except Exception as e:
                    print(f"❌ Error sending alert | user={alert.get('chat_id')} | {e}", flush=True)

                # هشدار one-shot است؛ فقط بعد از ارسال موفق حذف می‌شود تا پیام گم نشود.
                if sent and alerts_collection is not None:
                    try:
                        await alerts_collection.delete_one({"_id": alert["_id"]})
                    except Exception as e:
                        print(f"⚠️ Alert delete error: {e}", flush=True)
        except Exception as e:
            print(f"❌ Alert checker error: {e}", flush=True)
        await asyncio.sleep(60)


# ============================================================
# --- کانال اطلاع‌رسانی ---
# ============================================================

def build_channel_post():
    lines = ["📊 **نرخ لحظه‌ای بازار**", "━━━━━━━━━━━━━━━━━━"]
    lines.append("💵 **ارزهای فیات:**")
    for sym in ["USD", "EUR", "AED", "TRY"]:
        try:
            data = fetch_fiat_data(sym)
            if data and data.get("price"):
                name = FIAT_NAMES.get(sym, sym)
                lines.append(f"  • {name}: **{format_price(data['price'])} تومان**")
        except:
            pass
    lines.append("")
    lines.append("🥇 **طلا و سکه:**")
    for asset in ["gold_18", "coin_emami", "coin_half"]:
        try:
            data = fetch_gold_data(asset)
            if data and data.get("price"):
                name = GOLD_NAMES.get(asset, asset)
                lines.append(f"  • {name}: **{format_price(data['price'])} تومان**")
        except:
            pass
    lines.append("")
    lines.append("🪙 **رمزارزها:**")
    for sym in ["BTC", "ETH", "USDT", "BNB", "SOL"]:
        try:
            data = fetch_crypto_data(sym)
            if data and data.get("buy_price"):
                price_val = data['buy_price']
                try:
                    price_num = float(price_val)
                    if price_num >= 1_000_000_000_000:
                        formatted = f"{price_num / 1_000_000_000_000:,.2f} همت"
                    elif price_num >= 1_000_000_000:
                        formatted = f"{price_num / 1_000_000_000:,.2f} میلیارد"
                    elif price_num >= 1_000_000:
                        formatted = f"{price_num / 1_000_000:,.2f} میلیون"
                    else:
                        formatted = format_price(price_num)
                except:
                    formatted = format_price(price_val)
                lines.append(f"  • {sym}: **{formatted} تومان**")
        except:
            pass
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    # آمار زنده کاربران
    try:
        import asyncio as _asyncio
        # نمي‌توانيم مستقيماً اينجا await کنيم چون thread جداگانه است
        # پس از يه روش ساده‌تر استفاده مي‌کنيم
        pass
    except:
        pass
    lines.append(f"🕐 {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"📢 {CHANNEL_ID}")
    return "\n".join(lines)


def build_channel_post_with_stats(users_count):
    """نسخه کامل پست کانال با آمار زنده کاربران"""
    lines = ["📊 **نرخ لحظه‌ای بازار**", "━━━━━━━━━━━━━━━━━━"]
    lines.append("💵 **ارزهای فیات:**")
    for sym in ["USD", "EUR", "AED", "TRY"]:
        try:
            data = fetch_fiat_data(sym)
            if data and data.get("price"):
                name = FIAT_NAMES.get(sym, sym)
                lines.append(f"  • {name}: **{format_price(data['price'])} تومان**")
        except:
            pass
    lines.append("")
    lines.append("🥇 **طلا و سکه:**")
    for asset in ["gold_18", "coin_emami", "coin_half"]:
        try:
            data = fetch_gold_data(asset)
            if data and data.get("price"):
                name = GOLD_NAMES.get(asset, asset)
                lines.append(f"  • {name}: **{format_price(data['price'])} تومان**")
        except:
            pass
    lines.append("")
    lines.append("🪙 **رمزارزها:**")
    for sym in ["BTC", "ETH", "USDT", "BNB", "SOL"]:
        try:
            data = fetch_crypto_data(sym)
            if data and data.get("buy_price"):
                price_val = data['buy_price']
                try:
                    price_num = float(price_val)
                    if price_num >= 1_000_000_000_000:
                        formatted = f"{price_num / 1_000_000_000_000:,.2f} همت"
                    elif price_num >= 1_000_000_000:
                        formatted = f"{price_num / 1_000_000_000:,.2f} میلیارد"
                    elif price_num >= 1_000_000:
                        formatted = f"{price_num / 1_000_000:,.2f} میلیون"
                    else:
                        formatted = format_price(price_num)
                except:
                    formatted = format_price(price_val)
                lines.append(f"  • {sym}: **{formatted} تومان**")
        except:
            pass
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"👥 **کاربران ربات:** *{users_count:,}* نفر")
    lines.append(f"🕐 {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"📢 {CHANNEL_ID}")
    return "\n".join(lines)


def channel_poster():
    global CHANNEL_NUMERIC_ID
    print(f"ℹ️ channel_poster started, interval={CHANNEL_POST_INTERVAL}s", flush=True)
    while True:
        try:
            time.sleep(CHANNEL_POST_INTERVAL)
            if CHANNEL_POST_ENABLED and CHANNEL_ID:
                # گرفتن آمار کاربران از thread اصلی
                users_count = 0
                try:
                    if MAIN_LOOP is not None:
                        future_count = asyncio.run_coroutine_threadsafe(get_users_count(), MAIN_LOOP)
                        users_count = future_count.result(timeout=10)
                except Exception as e:
                    print(f"⚠️ get count error: {e}", flush=True)

                post_text = build_channel_post_with_stats(users_count)
                try:
                    if MAIN_LOOP is not None:
                        future = asyncio.run_coroutine_threadsafe(bot.send_message(CHANNEL_ID, post_text), MAIN_LOOP)
                        result = future.result(timeout=30)
                        print(f"✅ پست کانال ارسال شد.", flush=True)
                        try:
                            if result and hasattr(result, 'message_id'):
                                _sent_channel_message_ids.add(str(result.message_id))
                        except:
                            pass
                        try:
                            if result and hasattr(result, 'chat') and result.chat:
                                CHANNEL_NUMERIC_ID = str(result.chat.id)
                        except:
                            pass
                except Exception as e:
                    print(f"❌ خطا در ارسال پست: {type(e).__name__}: {e}", flush=True)
        except Exception as e:
            print(f"Channel poster error: {e}", flush=True)


# ============================================================
#                    👨‍💻 پنل مدیریت حرفه‌ای
# ============================================================
def is_admin(user_id):
    return str(user_id) in ADMIN_IDS


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


def admin_back_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="ADMIN:HOME"), row=0)
    return markup


async def admin_stats_text():
    now = time.time()
    users_count = await users_collection.count_documents({}) if users_collection is not None else 0
    active_users = await users_collection.count_documents({"account_status": {"$ne": "logged_out"}, "blocked": {"$ne": True}}) if users_collection is not None else 0
    logged_out = await users_collection.count_documents({"account_status": "logged_out"}) if users_collection is not None else 0
    blocked = await users_collection.count_documents({"blocked": True}) if users_collection is not None else 0
    active_24h = await users_collection.count_documents({"last_seen_at": {"$gte": now - 86400}, "account_status": {"$ne": "logged_out"}}) if users_collection is not None else 0
    active_7d = await users_collection.count_documents({"last_seen_at": {"$gte": now - 7*86400}, "account_status": {"$ne": "logged_out"}}) if users_collection is not None else 0
    active_30d = await users_collection.count_documents({"last_seen_at": {"$gte": now - 30*86400}, "account_status": {"$ne": "logged_out"}}) if users_collection is not None else 0
    new_24h = await users_collection.count_documents({"created_at": {"$gte": now - 86400}}) if users_collection is not None else 0
    new_7d = await users_collection.count_documents({"created_at": {"$gte": now - 7*86400}}) if users_collection is not None else 0
    alerts_count = await alerts_collection.count_documents({}) if alerts_collection is not None else 0
    favs_count = await favorites_collection.count_documents({}) if favorites_collection is not None else 0
    refs_count = await referrals_collection.count_documents({}) if referrals_collection is not None else 0
    legacy_phone_count = await users_collection.count_documents({"phone": {"$exists": True, "$ne": ""}}) if users_collection is not None else 0
    return (
        "👨‍💻 **داشبورد مدیریت ارز آنلاین**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👥 کل پروفایل‌ها: **{users_count:,}**\n"
        f"🟢 حساب‌های فعال: **{active_users:,}**\n"
        f"🚪 خارج‌شده‌ها: **{logged_out:,}**\n"
        f"🚫 مسدودشده‌ها: **{blocked:,}**\n"
        f"🟢 فعال ۲۴ ساعت: **{active_24h:,}**\n"
        f"📅 فعال ۷ روز: **{active_7d:,}** | فعال ۳۰ روز: **{active_30d:,}**\n"
        f"🆕 ثبت‌نام ۲۴ ساعت: **{new_24h:,}** | ۷ روز: **{new_7d:,}**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔔 هشدارهای فعال: **{alerts_count:,}**\n"
        f"⭐ علاقه‌مندی‌ها: **{favs_count:,}**\n"
        f"🎁 Referralها: **{refs_count:,}**\n"
        f"⭐ افراد خاص: **{await get_special_users_count():,}**\n"
        f"📱 کاربران دارای شماره قدیمی: **{legacy_phone_count:,}**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕐 بروزرسانی: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )


async def admin_users_page(page=0):
    page = max(0, int(page))
    if users_collection is None:
        return "❌ دیتابیس متصل نیست.", admin_back_keyboard()
    total = await users_collection.count_documents({})
    skip = page * ADMIN_PAGE_SIZE
    docs = await users_collection.find({}).sort("created_at", -1).skip(skip).limit(ADMIN_PAGE_SIZE).to_list(length=ADMIN_PAGE_SIZE)
    lines = [
        "👥 **کاربران ثبت‌نام‌شده**",
        f"صفحه **{page + 1}** از **{max(1, (total + ADMIN_PAGE_SIZE - 1) // ADMIN_PAGE_SIZE)}**",
        "━━━━━━━━━━━━━━━━━━"
    ]
    if not docs:
        lines.append("هنوز کاربری ثبت‌نام نکرده است.")
    else:
        for i, u in enumerate(docs, start=skip + 1):
            name = str(u.get("name", "بدون نام"))[:28]
            uid = str(u.get("chat_id", "-"))
            phone_mark = "📱" if u.get("phone") else "👤"
            status_mark = "🚫" if u.get("blocked") else ("🚪" if u.get("account_status") == "logged_out" else "🟢")
            if u.get("special_user"):
                status_mark += "⭐"
            lines.append(f"{i}. {status_mark}{phone_mark} **{name}**\n   ID: `{uid}`")
    markup = InlineKeyboardMarkup()
    for idx, u in enumerate(docs):
        uid = str(u.get("chat_id"))
        name = str(u.get("name", "کاربر"))[:20]
        markup.add(InlineKeyboardButton(text=f"👤 {name}", callback_data=f"ADMIN:USER:{uid}"), row=idx)
    nav_row = len(docs)
    total_pages = max(1, (total + ADMIN_PAGE_SIZE - 1) // ADMIN_PAGE_SIZE)
    if page > 0:
        markup.add(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"ADMIN:USERS:{page-1}"), row=nav_row)
    if page + 1 < total_pages:
        markup.add(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"ADMIN:USERS:{page+1}"), row=nav_row)
    markup.add(InlineKeyboardButton(text="🔙 پنل مدیریت", callback_data="ADMIN:HOME"), row=nav_row + 1)
    return "\n".join(lines), markup


async def admin_user_detail(chat_id):
    user = await get_user(chat_id)
    if not user:
        return "❌ کاربر پیدا نشد.", admin_back_keyboard()
    alerts_count = await alerts_collection.count_documents({"chat_id": str(chat_id)}) if alerts_collection is not None else 0
    favs_count = await favorites_collection.count_documents({"chat_id": str(chat_id)}) if favorites_collection is not None else 0
    joined = time.strftime("%Y-%m-%d %H:%M", time.localtime(user.get("created_at", time.time())))
    last_seen = time.strftime("%Y-%m-%d %H:%M", time.localtime(user.get("last_seen_at", user.get("updated_at", time.time()))))
    phone = user.get("phone")
    phone_line = f"📱 شماره قدیمی: `{phone}`\n" if phone else "📱 شماره: ثبت نشده (کاربر جدید)\n"
    text = (
        "👤 **جزئیات کاربر**\n━━━━━━━━━━━━━━━━━━\n"
        f"📝 نام: **{user.get('name', 'بدون نام')}**\n"
        f"🆔 Chat ID: `{user.get('chat_id')}`\n"
        f"{phone_line}"
        f"🌐 زبان: **{LANG_NAMES.get(user.get('language', 'fa'), user.get('language', 'fa'))}**\n"
        f"📅 ثبت‌نام: **{joined}**\n"
        f"🟢 آخرین فعالیت: **{last_seen}**\n"
        f"🎁 دعوت‌ها: **{user.get('invite_count', 0)}**\n"
        f"👑 نوع کاربر: **{'کاربر خاص ⭐' if user.get('special_user') else 'کاربر عادی 👤'}**\n"
        f"🔔 هشدارها: **{alerts_count}**\n"
        f"⭐ علاقه‌مندی‌ها: **{favs_count}**\n"
        f"🔗 معرف: `{user.get('referred_by') or '-'} `\n"
        f"📌 وضعیت حساب: **{'مسدود' if user.get('blocked') else ('خارج‌شده' if user.get('account_status') == 'logged_out' else 'فعال')}**"
    )
    markup = InlineKeyboardMarkup()
    if user.get("blocked"):
        markup.add(InlineKeyboardButton(text="🟢 رفع مسدودی", callback_data=f"ADMIN:UNBLOCK:{chat_id}"), row=0)
    else:
        markup.add(InlineKeyboardButton(text="🚫 مسدود کردن", callback_data=f"ADMIN:BLOCK:{chat_id}"), row=0)
    if user.get("special_user"):
        markup.add(InlineKeyboardButton(text="⭐ حذف از افراد خاص", callback_data=f"ADMIN:UNSPECIAL:{chat_id}"), row=1)
    else:
        markup.add(InlineKeyboardButton(text="⭐ افزودن به افراد خاص", callback_data=f"ADMIN:SPECIAL:{chat_id}"), row=1)
    markup.add(InlineKeyboardButton(text="🔙 کاربران", callback_data="ADMIN:USERS:0"), row=2)
    markup.add(InlineKeyboardButton(text="🏠 پنل مدیریت", callback_data="ADMIN:HOME"), row=3)
    return text, markup


async def admin_special_users_text():
    if users_collection is None:
        return "❌ دیتابیس متصل نیست.", admin_back_keyboard()
    docs = await users_collection.find({"special_user": True}).sort("updated_at", -1).limit(50).to_list(length=50)
    lines = ["⭐ **افراد خاص**", "━━━━━━━━━━━━━━━━━━"]
    if not docs:
        lines.append("هنوز کاربری به افراد خاص اضافه نشده است.")
    else:
        for i, u in enumerate(docs, 1):
            lines.append(f"{i}. **{str(u.get('name', 'کاربر'))[:25]}** — `{u.get('chat_id', '-')}`")
    markup = InlineKeyboardMarkup()
    for i, u in enumerate(docs):
        uid = str(u.get("chat_id"))
        name = str(u.get("name", "کاربر"))[:20]
        markup.add(InlineKeyboardButton(text=f"⭐ {name}", callback_data=f"ADMIN:USER:{uid}"), row=i)
    markup.add(InlineKeyboardButton(text="🔙 پنل مدیریت", callback_data="ADMIN:HOME"), row=len(docs)+1)
    return "\n".join(lines), markup


async def admin_alerts_text():
    count = await alerts_collection.count_documents({}) if alerts_collection is not None else 0
    return (
        "🔔 **وضعیت هشدارها**\n━━━━━━━━━━━━━━━━━━\n"
        f"تعداد هشدارهای فعال: **{count:,}**\n\n"
        "سیستم بررسی هشدارها به‌صورت خودکار در پس‌زمینه اجرا می‌شود."
    )


async def admin_health_text():
    mongo = "🟢 متصل" if db_client is not None else "🔴 قطع"
    loop = "🟢 فعال" if MAIN_LOOP is not None else "🔴 نامشخص"
    return (
        "🩺 **وضعیت سیستم**\n━━━━━━━━━━━━━━━━━━\n"
        f"🗄️ MongoDB: **{mongo}**\n"
        f"⚙️ Event Loop: **{loop}**\n"
        f"🤖 Bot ID: `{BOT_ID or '-'} `\n"
        f"📢 Channel: `{CHANNEL_ID}`\n"
        f"🔔 Alert Checker: **{'فعال' if _checker_thread_started else 'غیرفعال'}**\n"
        f"📡 Channel Poster: **{'فعال' if _channel_thread_started else 'غیرفعال'}**"
    )


async def admin_broadcast(admin_id, text):
    if users_collection is None:
        return 0, 0
    sent = 0
    failed = 0
    cursor = users_collection.find({"account_status": {"$ne": "logged_out"}, "blocked": {"$ne": True}}, {"chat_id": 1})
    async for doc in cursor:
        uid = str(doc.get("chat_id", ""))
        if not uid:
            continue
        try:
            await bot.send_message(uid, text)
            sent += 1
            await asyncio.sleep(0.04)
        except Exception as e:
            failed += 1
            print(f"⚠️ Broadcast failed for {uid}: {e}", flush=True)
    return sent, failed


# ============================================================
#                       رویدادها
# ============================================================

@bot.event
async def on_ready():
    global MAIN_LOOP, BOT_ID, _channel_thread_started, _checker_thread_started
    print(f"ربات {bot.user.username} با موفقیت روشن شد!", flush=True)
    MAIN_LOOP = asyncio.get_running_loop()
    try:
        BOT_ID = str(bot.user.id)
    except:
        pass
    try:
        await init_db()
    except Exception as e:
        print(f"❌ init_db error: {e}", flush=True)

    if not _checker_thread_started:
        try:
            asyncio.create_task(alert_checker_async())
            _checker_thread_started = True
        except:
            pass

    if not _channel_thread_started:
        try:
            channel_thread = threading.Thread(target=channel_poster, daemon=True)
            channel_thread.start()
            _channel_thread_started = True
        except:
            pass


@bot.event
async def on_message(message: Message):
    try:
        msg_id = str(getattr(message, 'message_id', ''))
        if msg_id and msg_id in _sent_channel_message_ids:
            return
    except:
        pass
    try:
        if BOT_ID and message.author and str(getattr(message.author, 'id', '')) == BOT_ID:
            return
    except:
        pass
    try:
        chat_type = getattr(message.chat, 'type', None) if message.chat else None
        if chat_type != 'private':
            return
    except:
        return
    try:
        chat_id = str(getattr(message.chat, 'id', '')) if message.chat else ''
        if CHANNEL_NUMERIC_ID and chat_id == CHANNEL_NUMERIC_ID:
            return
    except:
        pass
    if message.author is None or message.author.is_bot or not message.content:
        return

    content = message.content
    if 'انتقادات و پیشنهادات:' in content or 'توسعه‌دهنده:' in content:
        return
    if '📊 **نرخ لحظه‌ای بازار**' in content or 'نرخ لحظه‌ای بازار' in content:
        return
    if content.count('تومان') >= 3:
        return

    user_id = get_user_id_from_message(message)
    text = message.content.strip()
    text_upper = text.upper()

    if text == "/myid":
        await message.reply(f"🆔 Chat ID شما:\n`{user_id}`\n\nاین شناسه را برای ADMIN_IDS در Render استفاده کن.")
        return

    # 👨‍💻 مدیران قبل از Force Join پردازش می‌شوند.
    if is_admin(user_id):
        if text == "/admin":
            clear_state(user_id)
            await message.reply(await admin_stats_text(), components=admin_keyboard())
            return
        if text == "/admin_close":
            clear_state(user_id)
            await message.reply("✅ پنل مدیریت بسته شد.")
            return
        if user_id in user_states and user_states[user_id].get("state") == "admin_broadcast_waiting":
            broadcast_text = text
            user_states[user_id] = {"state": "admin_broadcast_confirm", "data": {"text": broadcast_text}}
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="✅ ارسال به همه", callback_data="ADMIN:BROADCAST:CONFIRM"), row=0)
            markup.add(InlineKeyboardButton(text="❌ لغو", callback_data="ADMIN:HOME"), row=1)
            await message.reply(
                "📢 **پیش‌نمایش پیام همگانی**\n\n" + broadcast_text + "\n\n⚠️ این پیام برای تمام کاربران ثبت‌نام‌شده ارسال می‌شود.",
                components=markup
            )
            return
        if user_id in user_states and user_states[user_id].get("state") == "admin_search_waiting":
            query = text.strip()
            if users_collection is None:
                await message.reply("❌ دیتابیس متصل نیست.", components=admin_back_keyboard())
                clear_state(user_id)
                return
            search_filter = {"name": {"$regex": re.escape(query), "$options": "i"}}
            if query:
                variants = _chat_id_variants(query)
                search_filter = {"$or": [{"chat_id": v} for v in variants] + [{"name": {"$regex": re.escape(query), "$options": "i"}}]}
            docs = await users_collection.find(search_filter).limit(10).to_list(length=10)
            if not docs:
                await message.reply("❌ کاربری با این مشخصات پیدا نشد.", components=admin_back_keyboard())
                clear_state(user_id)
                return
            markup = InlineKeyboardMarkup()
            lines = ["🔎 **نتیجه جستجو**\n━━━━━━━━━━━━━━━━━━"]
            for idx, doc in enumerate(docs):
                uid = str(doc.get("chat_id"))
                name = str(doc.get("name", "کاربر"))[:25]
                lines.append(f"{idx+1}. **{name}** — `{uid}`")
                markup.add(InlineKeyboardButton(text=f"👤 {name}", callback_data=f"ADMIN:USER:{uid}"), row=idx)
            markup.add(InlineKeyboardButton(text="🔙 پنل مدیریت", callback_data="ADMIN:HOME"), row=len(docs))
            clear_state(user_id)
            await message.reply("\n".join(lines), components=markup)
            return

    # ثبت آخرین فعالیت کاربران ثبت‌نام‌شده. این فیلد به Force Join یا ثبت‌نام جدید وابسته نیست.
    existing_for_activity = await get_active_user(user_id)
    if existing_for_activity:
        await touch_user(user_id)

    # حساب مسدودشده حتی در صورت عضویت کانال نباید از امکانات استفاده کند.
    raw_user_for_block = await get_user(user_id)
    if raw_user_for_block and raw_user_for_block.get("blocked") and not is_admin(user_id):
        await message.reply("🚫 دسترسی این حساب توسط مدیریت محدود شده است.")
        return

    # ============================================================
    #       بررسی عضویت اجباری (Force Join)
    # ============================================================
    # کاربر جدید هم قبل از شروع ثبت‌نام باید عضو کانال باشد.
    # اگر کاربر در مرحله ثبت‌نام است ولی هنوز عضو نشده، ادامه ثبت‌نام متوقف می‌شود.
    existing_user = await get_active_user(user_id)
    if existing_user:
        is_member = await check_channel_membership(user_id)
        if not is_member:
            lang = existing_user.get("language", "fa")
            await message.reply(
                t("force_join_title", lang) + "\n\n" + t("force_join_text", lang, channel=CHANNEL_ID),
                components=force_join_keyboard(lang)
            )
            return
    elif user_id in user_states:
        pending_state = user_states[user_id].get("state")
        if pending_state in {"awaiting_language", "awaiting_name", "awaiting_phone"}:
            is_member = await check_channel_membership(user_id)
            if not is_member:
                await message.reply(
                    t("force_join_title", "fa") + "\n\n" + t("force_join_text", "fa", channel=CHANNEL_ID),
                    components=force_join_keyboard("fa")
                )
                return

    # ============================================================
    #       وضعیت‌های ثبت‌نام / زبان
    # ============================================================
    if user_id in user_states:
        state = user_states[user_id]["state"]
        data = user_states[user_id].get("data", {})
        lang = data.get("lang", "fa")

        if state == "awaiting_channel_join":
            # هیچ متن مستقیمی نباید ثبت‌نام را جلو ببرد؛ کاربر باید Verify را بزند.
            await message.reply(
                t("force_join_title", "fa") + "\n\n" +
                t("force_join_text", "fa", channel=CHANNEL_ID),
                components=force_join_keyboard("fa")
            )
            return

        if state == "awaiting_name":
            if len(text) < 3:
                await message.reply(t("invalid_name", lang))
                return
            data["name"] = text
            referred_by = data.get("referred_by")
            ok = await create_user(user_id, data.get("name", ""), None, lang, referred_by=referred_by)
            clear_state(user_id)
            clear_lang_cache(user_id)
            if not ok:
                await message.reply(t("error", lang))
                return
            lang_name = LANG_NAMES.get(lang, lang)
            success_text = t("register_success", lang, name=data.get("name", ""), lang_name=lang_name)
            await message.reply(success_text + footer_text(lang), components=main_menu_keyboard(lang))
            return

        # سازگاری با stateهای قدیمی: اگر کاربری به‌دلیل Deploy قبلی در awaiting_phone مانده باشد،
        # شماره از او نمی‌گیریم؛ متن فعلی را به عنوان نام تلقی می‌کنیم و ثبت‌نام را کامل می‌کنیم.
        if state == "awaiting_phone":
            # اگر این state از نسخه قدیمی باقی مانده، نام قبلی را حفظ می‌کنیم و
            # متن جدید (که ممکن است شماره باشد) را به عنوان نام ذخیره نمی‌کنیم.
            legacy_name = data.get("name") or text
            if len(legacy_name.strip()) < 3:
                await message.reply(t("invalid_name", lang))
                return
            old_phone = data.get("phone")
            if old_phone:
                ok = await create_user(user_id, legacy_name, old_phone, lang, referred_by=data.get("referred_by"))
            else:
                ok = await create_user(user_id, legacy_name, None, lang, referred_by=data.get("referred_by"))
            clear_state(user_id)
            clear_lang_cache(user_id)
            if not ok:
                await message.reply(t("error", lang))
                return
            success_text = t("register_success", lang, name=legacy_name, lang_name=LANG_NAMES.get(lang, lang))
            await message.reply(success_text + footer_text(lang), components=main_menu_keyboard(lang))
            return

        if state == "alert_awaiting_price":
            try:
                price = float(text.replace(",", "").replace("،", ""))
                data["target_price"] = price
                user_states[user_id]["state"] = "alert_awaiting_direction"
                msg = f"🎯 قیمت هدف: **{format_price(price)} تومان**\n\nحالا انتخاب کنید:"
                await message.reply(msg + footer_text(lang), components=alert_direction_keyboard(lang))
            except ValueError:
                await message.reply("❌ عدد معتبر وارد کنید." + footer_text(lang))
            return

        if state == "alert_awaiting_manual_asset":
            asset_key = text_upper
            if asset_key in GOLD_NAMES or asset_key in FIAT_NAMES:
                data["asset"] = asset_key
                user_states[user_id]["state"] = "alert_awaiting_price"
                await message.reply(f"✅ {get_asset_display_name(asset_key)}\n\n💰 قیمت هدف را وارد کنید:" + footer_text(lang))
            else:
                crypto_data = fetch_crypto_data(asset_key)
                if crypto_data:
                    data["asset"] = asset_key
                    user_states[user_id]["state"] = "alert_awaiting_price"
                    await message.reply(f"✅ {asset_key}\n\n💰 قیمت هدف را وارد کنید:" + footer_text(lang))
                else:
                    await message.reply(f"❌ {asset_key} یافت نشد." + footer_text(lang), components=alert_asset_category_keyboard(lang))
            return

        if state == "convert_awaiting_amount":
            try:
                amount = float(text.replace(",", "").replace("،", ""))
                data["amount"] = amount
                user_states[user_id]["state"] = "convert_awaiting_to"
                from_name = get_asset_display_name(data["from_asset"])
                await message.reply(f"✅ مقدار: **{format_price(amount)} {from_name}**\n\n🔄 ارز مقصد را انتخاب کنید:" + footer_text(lang), components=convert_to_keyboard(data["from_asset"], lang))
            except ValueError:
                await message.reply("❌ عدد معتبر وارد کنید." + footer_text(lang))
            return

    # ============================================================
    #                       دستور /start
    # ============================================================
    if text.startswith('/start'):
        # استخراج پارامتر referral
        referred_by = None
        parts = text.split()
        if len(parts) > 1:
            referrer_id = parts[1].strip()
            if referrer_id.isdigit() and referrer_id != user_id:
                referred_by = referrer_id
                print(f"🎁 New user {user_id} referred by {referred_by}", flush=True)

        # مهم: get_user هر دو نوع chat_id (قدیمی عددی و جدید رشته‌ای) را پیدا می‌کند؛
        # بنابراین کاربران قدیمی بعد از Deploy نباید دوباره ثبت‌نام شوند.
        user = await get_active_user(user_id)
        if user:
            lang = user.get("language", "fa")
            _user_lang_cache[user_id] = lang
            # چک عضویت
            is_member = await check_channel_membership(user_id)
            if not is_member:
                await message.reply(
                    t("force_join_title", lang) + "\n\n" + t("force_join_text", lang, channel=CHANNEL_ID),
                    components=force_join_keyboard(lang)
                )
                return
            await show_main_menu(message, user_id)
        else:
            # کاربر جدید: اول عضویت کانال، بعد ثبت‌نام.
            # referred_by را در RAM نگه می‌داریم تا بعد از عضویت و تکمیل ثبت‌نام از بین نرود.
            clear_force_join_cache(user_id)
            is_member = await check_channel_membership(user_id, use_cache=False)
            if not is_member:
                user_states[user_id] = {
                    "state": "awaiting_channel_join",
                    "data": {"referred_by": referred_by}
                }
                await message.reply(
                    t("force_join_title", "fa") + "\n\n" +
                    t("force_join_text", "fa", channel=CHANNEL_ID),
                    components=force_join_keyboard("fa")
                )
                return

            user_states[user_id] = {
                "state": "awaiting_language",
                "data": {"referred_by": referred_by}
            }
            await message.reply(t("choose_language", "fa"), components=language_keyboard())
        return

    if text == '/cancel':
        clear_state(user_id)
        lang = await get_user_language(user_id)
        await message.reply(t("cancel", lang), components=main_menu_keyboard(lang))
        return

    if text == '/profile':
        await show_profile(message, user_id)
        return

    if text == '/language':
        user = await get_user(user_id)
        if not user:
            # کاربر جدید باید از مسیر /start و عضویت کانال وارد شود.
            user_states[user_id] = {
                "state": "awaiting_channel_join",
                "data": user_states.get(user_id, {}).get("data", {})
            }
            await message.reply(
                t("force_join_title", "fa") + "\n\n" +
                t("force_join_text", "fa", channel=CHANNEL_ID),
                components=force_join_keyboard("fa")
            )
            return
        user_states[user_id] = {"state": "changing_language", "data": {}}
        await message.reply(t("choose_language", "fa") + " / " + t("choose_language", "en"), components=language_keyboard())
        return

    if text == '/help' or text == 'راهنما':
        await show_help(message, user_id)
        return

    if text == '/invite':
        await show_invite(message, user_id)
        return

    if text == '/top':
        await show_leaderboard(message, user_id)
        return

    if text == '/menu':
        await show_main_menu(message, user_id)
        return

    lang = await get_user_language(user_id)

    if text == '/list':
        try:
            response = requests.get(CRYPTO_API_URL, timeout=20)
            markets_data = response.json().get("data", {}).get("markets", {})
            symbols = []
            if isinstance(markets_data, dict):
                symbols = list(markets_data.keys())
            elif isinstance(markets_data, list):
                symbols = [item.get("symbol") for item in markets_data if item.get("symbol")]
            clean_symbols = [s.replace("IRT", "") for s in symbols if "IRT" in s] or symbols
            chunks = [clean_symbols[i:i + 50] for i in range(0, len(clean_symbols), 50)]
            await message.reply("📋 **لیست رمزارزها:**\n")
            for chunk in chunks:
                await message.reply("، ".join(chunk))
        except Exception as e:
            print(f"Error: {e}", flush=True)
        return

    if text == '/myalerts':
        if not await has_pro_access(user_id):
            invite_count = await get_effective_invite_count(user_id)
            await message.reply(t("pro_locked", lang) + f"\n\n📊 دعوت‌های شما: **{invite_count}** از **{PRO_INVITE_THRESHOLD}**" + footer_text(lang))
            return
        await show_my_alerts(message, user_id)
        return
    if text == '/fav' or text == '/favorites':
        await show_favorites(message, user_id)
        return

    # فرمت هشدار
    alert_match = re.match(r'^هشدار\s+([A-Za-z_0-9]+)\s+(\d+(?:\.\d+)?)\s+(بالا|پایین|بیشتر|کمتر)$', text, re.IGNORECASE)
    if alert_match:
        if not await has_pro_access(user_id):
            invite_count = await get_effective_invite_count(user_id)
            await message.reply(t("pro_locked", lang) + f"\n\n📊 دعوت‌های شما: **{invite_count}** از **{PRO_INVITE_THRESHOLD}**" + footer_text(lang))
            return
        asset_key = alert_match.group(1)
        target_price = float(alert_match.group(2))
        direction_word = alert_match.group(3)
        direction = "above" if direction_word in ("بالا", "بیشتر") else "below"
        asset_upper = asset_key.upper()
        if asset_upper in FIAT_NAMES:
            asset_key = asset_upper
        elif asset_key in GOLD_NAMES:
            pass
        else:
            asset_key = asset_upper
        current = get_current_price(asset_key)
        if not current:
            await message.reply(t("not_found", lang) + footer_text(lang))
            return
        await add_alert(user_id, asset_key, target_price, direction)
        asset_name = get_asset_display_name(asset_key)
        direction_text = "بالا برود" if direction == "above" else "پایین بیاید"
        await message.reply(
            f"✅ **هشدار ثبت شد!**\n\n🔔 {asset_name} → {format_price(target_price)} تومان ({direction_text})\n💰 قیمت فعلی: {format_price(current['price'])} تومان" + footer_text(lang),
            components=main_menu_keyboard(lang)
        )
        return

    # فرمت مبدل
    conv_match = re.match(r'^(\d+(?:\.\d+)?)\s+([A-Za-z_]{2,10})\s+(?:به|to|in)\s+([A-Za-z_]{2,10})$', text, re.IGNORECASE)
    if conv_match:
        amount = float(conv_match.group(1))
        from_asset = conv_match.group(2)
        to_asset = conv_match.group(3)
        if from_asset.upper() in ("TOMAN", "IRT", "تومان"):
            from_asset = "TOMAN"
        elif from_asset.upper() in FIAT_NAMES:
            from_asset = from_asset.upper()
        elif from_asset in GOLD_NAMES:
            pass
        else:
            from_asset = from_asset.upper()
        if to_asset.upper() in ("TOMAN", "IRT", "تومان"):
            to_asset = "TOMAN"
        elif to_asset.upper() in FIAT_NAMES:
            to_asset = to_asset.upper()
        elif to_asset in GOLD_NAMES:
            pass
        else:
            to_asset = to_asset.upper()
        await do_convert(message, amount, from_asset, to_asset, user_id)
        return

    if text_upper in FIAT_NAMES:
        await process_fiat_and_reply(message, text_upper, user_id)
        return

    user = await get_user(user_id)
    if not user:
        user_states[user_id] = {"state": "awaiting_language", "data": {}}
        await message.reply(t("choose_language", "fa"), components=language_keyboard())
        return

    await process_crypto_and_reply(message, text_upper, user_id)


# ============================================================
#     رویداد کلیک روی دکمه‌ها
# ============================================================
@bot.event
async def on_callback(callback: CallbackQuery):
    data = callback.data
    user_id = get_user_id_from_callback(callback)
    if not user_id:
        return

    try:
        if hasattr(callback, 'message') and callback.message:
            if hasattr(callback.message, 'chat') and callback.message.chat:
                chat_type = getattr(callback.message.chat, 'type', None)
                if chat_type != 'private':
                    return
    except:
        return

    # ============================================================
    # 👨‍💻 پنل مدیریت - فقط برای ADMIN_IDS
    # ============================================================
    if is_admin(user_id) and data.startswith("ADMIN:"):
        try:
            if data == "ADMIN:HOME":
                clear_state(user_id)
                await callback.message.edit(await admin_stats_text(), components=admin_keyboard())
                return

            if data == "ADMIN:STATS":
                await callback.message.edit(await admin_stats_text(), components=admin_keyboard())
                return

            if data.startswith("ADMIN:USERS:"):
                page = int(data.split(":")[2])
                text, markup = await admin_users_page(page)
                await callback.message.edit(text, components=markup)
                return

            if data.startswith("ADMIN:USER:"):
                uid = data.split(":", 2)[2]
                text, markup = await admin_user_detail(uid)
                await callback.message.edit(text, components=markup)
                return

            if data.startswith("ADMIN:BLOCK:") or data.startswith("ADMIN:UNBLOCK:"):
                parts = data.split(":", 2)
                uid = parts[2]
                blocked = parts[1] == "BLOCK"
                ok = await set_user_blocked(uid, blocked)
                if ok:
                    text, markup = await admin_user_detail(uid)
                    await callback.message.edit(text, components=markup)
                else:
                    await callback.message.reply("❌ تغییر وضعیت کاربر انجام نشد.", components=admin_back_keyboard())
                return

            if data == "ADMIN:SEARCH":
                user_states[user_id] = {"state": "admin_search_waiting", "data": {}}
                await callback.message.reply("🔎 **جستجوی کاربر**\n\nنام یا Chat ID کاربر را ارسال کن:")
                return

            if data == "ADMIN:BROADCAST":
                user_states[user_id] = {"state": "admin_broadcast_waiting", "data": {}}
                await callback.message.reply("📢 **ارسال پیام همگانی**\n\nمتن پیامی که می‌خواهی برای تمام کاربران ثبت‌نام‌شده ارسال شود را در یک پیام بفرست:")
                return

            if data == "ADMIN:BROADCAST:CONFIRM":
                state = user_states.get(user_id, {})
                broadcast_text = state.get("data", {}).get("text")
                if not broadcast_text:
                    await callback.message.reply("❌ پیام برای ارسال پیدا نشد.", components=admin_keyboard())
                    clear_state(user_id)
                    return
                clear_state(user_id)
                await callback.message.edit("⏳ **در حال ارسال پیام همگانی...**")
                sent, failed = await admin_broadcast(user_id, broadcast_text)
                await callback.message.reply(
                    f"✅ **ارسال همگانی تمام شد.**\n\n📨 موفق: **{sent:,}**\n❌ ناموفق: **{failed:,}**",
                    components=admin_keyboard()
                )
                return

            if data == "ADMIN:SPECIAL":
                text, markup = await admin_special_users_text()
                await callback.message.edit(text, components=markup)
                return

            if data.startswith("ADMIN:SPECIAL:") or data.startswith("ADMIN:UNSPECIAL:"):
                parts = data.split(":", 2)
                uid = parts[2]
                special = parts[1] == "SPECIAL"
                ok = await set_special_user(uid, special)
                if ok:
                    text, markup = await admin_user_detail(uid)
                    await callback.message.edit(text, components=markup)
                else:
                    await callback.message.reply("❌ تغییر وضعیت کاربر انجام نشد.", components=admin_back_keyboard())
                return

            if data == "ADMIN:ALERTS":
                await callback.message.edit(await admin_alerts_text(), components=admin_back_keyboard())
                return

            if data == "ADMIN:FAVS":
                count = await favorites_collection.count_documents({}) if favorites_collection is not None else 0
                await callback.message.edit(
                    f"⭐ **آمار علاقه‌مندی‌ها**\n\nتعداد کل آیتم‌های ذخیره‌شده: **{count:,}**",
                    components=admin_back_keyboard()
                )
                return

            if data == "ADMIN:HEALTH":
                await callback.message.edit(await admin_health_text(), components=admin_back_keyboard())
                return
        except Exception as admin_error:
            print(f"❌ Admin callback error: {admin_error}", flush=True)
            try:
                await callback.message.reply("❌ خطایی در پنل مدیریت رخ داد.", components=admin_keyboard())
            except:
                pass
            return

    # ============================================================
    # خروج از حساب
    # ============================================================
    if data == "PROFILE:LOGOUT":
        user = await get_active_user(user_id)
        lang = user.get("language", "fa") if user else "fa"
        try:
            await callback.message.edit(t("logout_confirm", lang), components=logout_confirm_keyboard(lang))
        except:
            await callback.message.reply(t("logout_confirm", lang), components=logout_confirm_keyboard(lang))
        return

    if data == "PROFILE:LOGOUT:CONFIRM":
        user = await get_active_user(user_id)
        lang = user.get("language", "fa") if user else "fa"
        ok = await logout_user(user_id)
        if ok:
            await callback.message.edit(t("logout_done", lang))
        else:
            await callback.message.reply(t("error", lang))
        return

    raw_callback_user = await get_user(user_id)
    if raw_callback_user and raw_callback_user.get("blocked") and not is_admin(user_id):
        await callback.message.reply("🚫 دسترسی این حساب توسط مدیریت محدود شده است.")
        return

    # ============================================================
    # Force Join باید قبل از هر Callback مربوط به ثبت‌نام اجرا شود.
    # این ترتیب جلوی دور زدن عضویت با کلیک روی LANG را می‌گیرد.
    # ============================================================
    if data == "FORCEJOIN:VERIFY":
        clear_force_join_cache(user_id)
        user = await get_active_user(user_id)
        pending = user_states.get(user_id, {})
        pending_data = pending.get("data", {})

        is_member = await check_channel_membership(user_id, use_cache=False)
        if not is_member:
            lang = user.get("language", "fa") if user else "fa"
            try:
                await callback.message.edit(
                    t("force_join_not_member", lang),
                    components=force_join_keyboard(lang)
                )
            except:
                await callback.message.reply(
                    t("force_join_not_member", lang),
                    components=force_join_keyboard(lang)
                )
            return

        # کاربر جدیدی که هنوز در users نیست: بعد از تأیید عضویت وارد ثبت‌نام می‌شود.
        if not user:
            referred_by = pending_data.get("referred_by")
            user_states[user_id] = {
                "state": "awaiting_language",
                "data": {"referred_by": referred_by}
            }
            try:
                await callback.message.edit(
                    t("choose_language", "fa"),
                    components=language_keyboard()
                )
            except:
                await callback.message.reply(
                    t("choose_language", "fa"),
                    components=language_keyboard()
                )
            return

        # کاربر قدیمی: بعد از تأیید عضویت مستقیم وارد منوی اصلی می‌شود.
        clear_state(user_id)
        await show_main_menu(callback.message, user_id, edit=True)
        return

    # ============================================================
    # محافظت از تمام Callbackها برای کاربران ثبت‌نام‌شده
    # اگر کاربر بعداً از کانال خارج شده باشد، حتی با دکمه‌های قدیمی
    # هم نباید بتواند از قابلیت‌های ربات استفاده کند.
    # ============================================================
    existing_user = await get_user(user_id)
    if existing_user:
        is_member = await check_channel_membership(user_id)
        if not is_member:
            lang = existing_user.get("language", "fa")
            try:
                await callback.message.edit(
                    t("force_join_title", lang) + "\n\n" +
                    t("force_join_text", lang, channel=CHANNEL_ID),
                    components=force_join_keyboard(lang)
                )
            except:
                try:
                    await callback.message.reply(
                        t("force_join_title", lang) + "\n\n" +
                        t("force_join_text", lang, channel=CHANNEL_ID),
                        components=force_join_keyboard(lang)
                    )
                except:
                    pass
            return

    # کاربر جدیدی که هنوز عضو نشده، حق عبور از مرحله Force Join را ندارد.
    user = existing_user
    if not user and data.startswith("LANG:"):
        pending = user_states.get(user_id, {})
        if pending.get("state") != "awaiting_language":
            try:
                await callback.message.edit(
                    t("force_join_title", "fa") + "\n\n" +
                    t("force_join_text", "fa", channel=CHANNEL_ID),
                    components=force_join_keyboard("fa")
                )
            except:
                pass
            return

    # انتخاب / تغییر زبان
    if data.startswith("LANG:"):
        new_lang = data.split(":")[1]
        if new_lang not in ["fa", "en"]:
            new_lang = "fa"

        if user_id in user_states and user_states[user_id]["state"] == "changing_language":
            user = await get_user(user_id)
            if user:
                await create_user(user_id, user.get("name", ""), user.get("phone", ""), new_lang)
                clear_lang_cache(user_id)
                clear_state(user_id)
                await show_main_menu(callback.message, user_id, edit=True)
                return

        # کاربر جدید در حال ثبت‌نام - حفظ referred_by
        current_data = user_states.get(user_id, {}).get("data", {})
        referred_by = current_data.get("referred_by")
        user_states[user_id] = {"state": "awaiting_name", "data": {"lang": new_lang, "referred_by": referred_by}}
        try:
            await callback.message.edit(t("welcome_new", new_lang))
        except:
            await callback.message.reply(t("welcome_new", new_lang))
        return

    user = await get_user(user_id)
    if not user:
        try:
            await callback.message.reply(t("choose_language", "fa"), components=language_keyboard())
        except:
            pass
        return

    lang = await get_user_language(user_id)

    # 🔒 قابلیت‌های حرفه‌ای: افراد خاص همیشه دسترسی دارند؛ بقیه با ۵ دعوت یا بیشتر.
    if data in {"MENU:MYALERTS", "ALERT:NEW"} or data.startswith("ALERT:"):
        if not await has_pro_access(user_id):
            invite_count = await get_effective_invite_count(user_id)
            await callback.message.reply(
                t("pro_locked", lang) + f"\n\n📊 دعوت‌های شما: **{invite_count}** از **{PRO_INVITE_THRESHOLD}**" + footer_text(lang),
                components=main_menu_keyboard(lang)
            )
            return

    if data == "MENU:MAIN":
        clear_state(user_id)
        await show_main_menu(callback.message, user_id, edit=True)
        return

    if data == "MENU:HELP":
        await show_help(callback.message, user_id, edit=True)
        return

    if data == "MENU:PROFILE":
        await show_profile(callback.message, user_id, edit=True)
        return

    if data == "MENU:INVITE":
        await show_invite(callback.message, user_id, edit=True)
        return

    if data == "MENU:LEADERBOARD":
        await show_leaderboard(callback.message, user_id, edit=True)
        return

    if data == "INVITE:COPY":
        invite_link = f"https://ble.ir/{BOT_USERNAME}?start={user_id}"
        await callback.message.reply(
            f"📋 لینک دعوت شما:\n`{invite_link}`\n\n"
            "روی متن بالا کلیک کنید تا کپی شود." + footer_text(lang)
        )
        return

    if data == "MENU:LANG":
        user_states[user_id] = {"state": "changing_language", "data": {}}
        try:
            await callback.message.edit(t("choose_language", lang), components=language_keyboard())
        except:
            await callback.message.reply(t("choose_language", lang), components=language_keyboard())
        return

    if data == "MENU:CRYPTO":
        clear_state(user_id)
        try:
            await callback.message.edit(t("crypto_title", lang) + footer_text(lang), components=crypto_menu_keyboard(lang))
        except:
            await callback.message.reply(t("crypto_title", lang) + footer_text(lang), components=crypto_menu_keyboard(lang))
        return

    if data == "MENU:FIAT":
        clear_state(user_id)
        try:
            await callback.message.edit(t("fiat_title", lang) + footer_text(lang), components=fiat_menu_keyboard(lang))
        except:
            await callback.message.reply(t("fiat_title", lang) + footer_text(lang), components=fiat_menu_keyboard(lang))
        return

    if data == "MENU:GOLD":
        clear_state(user_id)
        try:
            await callback.message.edit(t("gold_title", lang) + footer_text(lang), components=gold_menu_keyboard(lang))
        except:
            await callback.message.reply(t("gold_title", lang) + footer_text(lang), components=gold_menu_keyboard(lang))
        return

    if data == "MENU:MYALERTS":
        await show_my_alerts(callback.message, user_id, edit=True)
        return

    if data == "MENU:LIST":
        try:
            response = requests.get(CRYPTO_API_URL, timeout=20)
            markets_data = response.json().get("data", {}).get("markets", {})
            symbols = []
            if isinstance(markets_data, dict):
                symbols = list(markets_data.keys())
            elif isinstance(markets_data, list):
                symbols = [item.get("symbol") for item in markets_data if item.get("symbol")]
            clean_symbols = [s.replace("IRT", "") for s in symbols if "IRT" in s] or symbols
            chunks = [clean_symbols[i:i + 50] for i in range(0, len(clean_symbols), 50)]
            await callback.message.reply("📋 **لیست:**\n")
            for chunk in chunks:
                await callback.message.reply("، ".join(chunk))
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=0)
            await callback.message.reply("🔙", components=markup)
        except Exception as e:
            print(f"Error: {e}", flush=True)
        return

    if data.startswith("CRYPTO:"):
        parts = data.split(":")
        if len(parts) >= 2:
            await process_crypto_and_reply(callback.message, parts[1], user_id)
        return

    if data.startswith("FIAT:"):
        parts = data.split(":")
        if len(parts) >= 2:
            await process_fiat_and_reply(callback.message, parts[1], user_id)
        return

    if data.startswith("GOLD:"):
        parts = data.split(":")
        if len(parts) >= 2:
            await process_gold_and_reply(callback.message, parts[1], user_id)
        return

    if data == "FAV:VIEW":
        clear_state(user_id)
        await show_favorites(callback.message, user_id, edit=True)
        return

    if data == "FAV:NEW":
        clear_state(user_id)
        try:
            await callback.message.edit("⭐ **افزودن**\n\nکدام دسته؟" + footer_text(lang), components=fav_category_keyboard(lang))
        except:
            await callback.message.reply("⭐ **افزودن**\n\nکدام دسته؟" + footer_text(lang), components=fav_category_keyboard(lang))
        return

    if data.startswith("FAV:CAT:"):
        parts = data.split(":")
        category = parts[2] if len(parts) >= 3 else None
        if not category:
            return
        user_favs = await get_user_favorites(user_id)
        try:
            await callback.message.edit("⭐ **انتخاب دارایی:**" + footer_text(lang), components=fav_asset_list_keyboard(category, user_favs, lang))
        except:
            await callback.message.reply("⭐ **انتخاب دارایی:**" + footer_text(lang), components=fav_asset_list_keyboard(category, user_favs, lang))
        return

    if data.startswith("FAV:ADD:"):
        parts = data.split(":")
        asset = parts[2] if len(parts) >= 3 else None
        if not asset:
            return
        added = await add_favorite(user_id, asset)
        asset_name = get_asset_display_name(asset)
        await callback.message.reply(f"{'✅' if added else 'ℹ️'} **{asset_name}** {'اضافه شد!' if added else 'قبلاً بود.'}" + footer_text(lang))
        category = "crypto" if asset in POPULAR_CRYPTOS else "fiat" if asset in POPULAR_FIATS else "gold"
        user_favs = await get_user_favorites(user_id)
        try:
            await callback.message.edit("⭐ **انتخاب دارایی:**" + footer_text(lang), components=fav_asset_list_keyboard(category, user_favs, lang))
        except:
            pass
        return

    if data.startswith("FAV:DEL:"):
        parts = data.split(":")
        asset = parts[2] if len(parts) >= 3 else None
        if not asset:
            return
        await remove_favorite(user_id, asset)
        asset_name = get_asset_display_name(asset)
        await callback.message.reply(f"🗑 **{asset_name}** حذف شد." + footer_text(lang))
        category = "crypto" if asset in POPULAR_CRYPTOS else "fiat" if asset in POPULAR_FIATS else "gold"
        user_favs = await get_user_favorites(user_id)
        try:
            await callback.message.edit("⭐ **انتخاب دارایی:**" + footer_text(lang), components=fav_asset_list_keyboard(category, user_favs, lang))
        except:
            pass
        return

    if data.startswith("DELALERT:"):
        parts = data.split(":")
        if len(parts) >= 2:
            asset = parts[1]
            if asset == "ALL":
                count = await remove_all_user_alerts(user_id)
                await callback.message.reply(f"🗑 **{count} هشدار حذف شد.**" + footer_text(lang))
                await show_my_alerts(callback.message, user_id, edit=False)
            else:
                await remove_alert(user_id, asset)
                await callback.message.reply(f"🗑 هشدار **{get_asset_display_name(asset)}** حذف شد." + footer_text(lang))
                await show_my_alerts(callback.message, user_id, edit=False)
        return

    if data == "ALERT:NEW":
        clear_state(user_id)
        try:
            await callback.message.edit("🔔 **ثبت هشدار**\n\nدسته‌بندی:" + footer_text(lang), components=alert_asset_category_keyboard(lang))
        except:
            await callback.message.reply("🔔 **ثبت هشدار**\n\nدسته‌بندی:" + footer_text(lang), components=alert_asset_category_keyboard(lang))
        return

    if data.startswith("ALERT:CAT:"):
        parts = data.split(":")
        category = parts[2] if len(parts) >= 3 else None
        if not category:
            return
        try:
            await callback.message.edit("🔔 **انتخاب دارایی:**", components=alert_asset_list_keyboard(category, lang))
        except:
            await callback.message.reply("🔔 **انتخاب دارایی:**", components=alert_asset_list_keyboard(category, lang))
        return

    if data == "ALERT:MANUAL":
        user_states[user_id] = {"state": "alert_awaiting_manual_asset", "data": {"lang": lang}}
        await callback.message.reply("✏️ **نام دارایی را وارد کنید:**\n\n🔸 `BTC`\n🔸 `USD`\n🔸 `coin_emami`" + footer_text(lang))
        return

    if data.startswith("ALERT:SET:"):
        parts = data.split(":")
        asset = parts[2] if len(parts) >= 3 else None
        if not asset:
            return
        user_states[user_id] = {"state": "alert_awaiting_price", "data": {"asset": asset, "lang": lang}}
        current = get_current_price(asset)
        current_text = f"\n💰 قیمت فعلی: {format_price(current['price'])} تومان" if current else ""
        try:
            await callback.message.edit(f"✅ **{get_asset_display_name(asset)}**{current_text}\n\n🎯 قیمت هدف را وارد کنید:" + footer_text(lang))
        except:
            await callback.message.reply(f"✅ **{get_asset_display_name(asset)}**{current_text}\n\n🎯 قیمت هدف را وارد کنید:" + footer_text(lang))
        return

    if data.startswith("ALERT:DIR:"):
        parts = data.split(":")
        direction = parts[2] if len(parts) >= 3 else None
        if not direction:
            return
        if user_id not in user_states or "asset" not in user_states[user_id]["data"] or "target_price" not in user_states[user_id]["data"]:
            await callback.message.reply("❌ خطا. دوباره شروع کنید.", components=main_menu_keyboard(lang))
            return
        asset = user_states[user_id]["data"]["asset"]
        target_price = user_states[user_id]["data"]["target_price"]
        current = get_current_price(asset)
        if not current or current.get("price") is None:
            await callback.message.reply("❌ در حال حاضر قیمت این دارایی در دسترس نیست. لطفاً کمی بعد دوباره تلاش کنید." + footer_text(lang))
            return
        ok = await add_alert(user_id, asset, target_price, direction)
        if not ok:
            await callback.message.reply("❌ ثبت هشدار انجام نشد. دوباره تلاش کنید." + footer_text(lang))
            return
        clear_state(user_id)
        direction_text = "بالا برود 📈" if direction == "above" else "پایین بیاید 📉"
        text = (
            f"✅ **هشدار ثبت شد!**\n━━━━━━━━━━━━━━━━━━\n🔔 **{get_asset_display_name(asset)}**\n"
            f"🎯 قیمت هدف: **{format_price(target_price)} تومان**\n"
            f"📊 {direction_text}\n━━━━━━━━━━━━━━━━━━" + footer_text(lang)
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=t("menu_alert", lang), callback_data="ALERT:NEW"), row=0)
        markup.add(InlineKeyboardButton(text=t("menu_myalerts", lang), callback_data="MENU:MYALERTS"), row=1)
        markup.add(InlineKeyboardButton(text=t("menu_main", lang), callback_data="MENU:MAIN"), row=2)
        try:
            await callback.message.edit(text, components=markup)
        except:
            await callback.message.reply(text, components=markup)
        return

    if data == "ALERT:CANCEL":
        clear_state(user_id)
        await callback.message.reply(t("cancel", lang), components=main_menu_keyboard(lang))
        return

    if data == "CONV:NEW":
        clear_state(user_id)
        try:
            await callback.message.edit("🔄 **مبدل ارز**\n\nمرحله ۱: **ارز مبدأ؟**" + footer_text(lang), components=convert_from_keyboard(lang))
        except:
            await callback.message.reply("🔄 **مبدل ارز**\n\nمرحله ۱: **ارز مبدأ؟**" + footer_text(lang), components=convert_from_keyboard(lang))
        return

    if data.startswith("CONV:FROM:"):
        parts = data.split(":")
        from_asset = parts[2] if len(parts) >= 3 else None
        if not from_asset:
            return
        user_states[user_id] = {"state": "convert_awaiting_amount", "data": {"from_asset": from_asset, "lang": lang}}
        try:
            await callback.message.edit(f"✅ **{get_asset_display_name(from_asset)}**\n\nمرحله ۲: **مقدار؟**" + footer_text(lang))
        except:
            await callback.message.reply(f"✅ **{get_asset_display_name(from_asset)}**\n\nمرحله ۲: **مقدار؟**" + footer_text(lang))
        return

    if data.startswith("CONV:TO:"):
        parts = data.split(":")
        to_asset = parts[2] if len(parts) >= 3 else None
        if not to_asset:
            return
        if user_id not in user_states or "from_asset" not in user_states[user_id]["data"] or "amount" not in user_states[user_id]["data"]:
            await callback.message.reply("❌ خطا. دوباره شروع کنید.", components=main_menu_keyboard(lang))
            return
        from_asset = user_states[user_id]["data"]["from_asset"]
        amount = user_states[user_id]["data"]["amount"]
        clear_state(user_id)
        await do_convert(callback.message, amount, from_asset, to_asset, user_id)
        return

    if data == "CONV:CANCEL":
        clear_state(user_id)
        await callback.message.reply(t("cancel", lang), components=main_menu_keyboard(lang))
        return


# --- سرور وب ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

bot.run()
