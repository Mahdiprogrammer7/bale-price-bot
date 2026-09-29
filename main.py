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

FIAT_API_URL = 'https://cdn.jsdelivr.net/gh/HosseinOdd/Navasan-API@main/data/fiat.json'
GOLD_API_URL = 'https://cdn.jsdelivr.net/gh/HosseinOdd/Navasan-API@main/data/gold.json'

# 📢 کانال اطلاع‌رسانی
CHANNEL_ID = "@nabz_mediaa"
CHANNEL_POST_INTERVAL = 3600  # هر 1 ساعت
CHANNEL_POST_ENABLED = True

# ✅ پروکسی (روی Render باید True باشه)
USE_PROXY = True
PROXY_URL = "https://red-meadow-20f7bale-bot-proxy.najafimahdi13867.workers.dev"
WELCOME_IMAGE_URL = ""
# ==================================================


# ============================================================
#       استفاده از Cloudflare Proxy برای دور زدن محدودیت IP
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
else:
    print("ℹ️ Cloudflare Proxy غیرفعال است. اتصال مستقیم به بله.", flush=True)
# ============================================================


bot = Bot(token=BOT_TOKEN)

user_states = {}
MAIN_LOOP = None
CHANNEL_NUMERIC_ID = None
BOT_ID = None
_sent_channel_message_ids = set()
_channel_thread_started = False
_checker_thread_started = False

# ============================================================
#       اتصال به دیتابیس MongoDB
# ============================================================
db_client = None
alerts_collection = None
favorites_collection = None

async def init_db():
    global db_client, alerts_collection, favorites_collection
    print(f"🔍 DEBUG: init_db called. MONGO_URI starts with: {MONGO_URI[:30] if MONGO_URI else 'EMPTY'}", flush=True)
    if not MONGO_URI:
        print("⚠️ MONGO_URI تنظیم نشده است. از فایل‌های JSON استفاده می‌شود.", flush=True)
        return False
    try:
        db_client = AsyncIOMotorClient(
            MONGO_URI,
            server_api=ServerApi('1'),
            tlsCAFile=certifi.where()
        )
        await db_client.admin.command('ping')
        db = db_client["bale_bot_db"]
        alerts_collection = db["alerts"]
        favorites_collection = db["favorites"]
        print("✅ اتصال به MongoDB با موفقیت برقرار شد!", flush=True)
        return True
    except Exception as e:
        print(f"❌ خطا در اتصال به MongoDB: {e}", flush=True)
        import traceback
        traceback.print_exc()
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

# نگاشت نمادها به شناسه‌های CoinGecko
COINGECKO_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether",
    "BNB": "binancecoin", "SOL": "solana", "XRP": "ripple",
    "ADA": "cardano", "DOGE": "dogecoin", "TRX": "tron",
    "TON": "the-open-network", "MATIC": "matic-network",
    "DOT": "polkadot", "LTC": "litecoin", "AVAX": "avalanche-2",
    "LINK": "chainlink", "SHIB": "shiba-inu", "DAI": "dai",
    "ATOM": "cosmos", "UNI": "uniswap", "XLM": "stellar",
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


def footer_text():
    return (
        f"\n\n━━━━━━━━━━━━━━━━━━\n"
        f"👨‍💻 توسعه‌دهنده: **{DEVELOPER_NAME}**\n"
        f"📩 انتقادات و پیشنهادات: {FEEDBACK_ID}"
    )


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


# ============================================================
# --- توابع دیتابیس: هشدارها ---
# ============================================================

async def add_alert(chat_id, asset_key, target_price, direction):
    if alerts_collection is not None:
        await alerts_collection.delete_many({"chat_id": str(chat_id), "asset": asset_key})
        await alerts_collection.insert_one({
            "chat_id": str(chat_id),
            "asset": asset_key,
            "target_price": float(target_price),
            "direction": direction,
            "created_at": time.time()
        })
    else:
        alerts = []
        try:
            with open('alerts.json', 'r', encoding='utf-8') as f:
                alerts = json.load(f)
        except:
            pass
        alerts = [a for a in alerts if not (a["chat_id"] == str(chat_id) and a["asset"] == asset_key)]
        alerts.append({"chat_id": str(chat_id), "asset": asset_key, "target_price": float(target_price), "direction": direction, "created_at": time.time()})
        with open('alerts.json', 'w', encoding='utf-8') as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)


async def get_user_alerts(chat_id):
    if alerts_collection is not None:
        cursor = alerts_collection.find({"chat_id": str(chat_id)})
        return await cursor.to_list(length=None)
    else:
        try:
            with open('alerts.json', 'r', encoding='utf-8') as f:
                alerts = json.load(f)
            return [a for a in alerts if a["chat_id"] == str(chat_id)]
        except:
            return []


async def remove_alert(chat_id, asset_key):
    if alerts_collection is not None:
        await alerts_collection.delete_one({"chat_id": str(chat_id), "asset": asset_key})
    else:
        try:
            with open('alerts.json', 'r', encoding='utf-8') as f:
                alerts = json.load(f)
            alerts = [a for a in alerts if not (a["chat_id"] == str(chat_id) and a["asset"] == asset_key)]
            with open('alerts.json', 'w', encoding='utf-8') as f:
                json.dump(alerts, f, ensure_ascii=False, indent=2)
        except:
            pass


async def get_all_alerts():
    if alerts_collection is not None:
        cursor = alerts_collection.find({})
        return await cursor.to_list(length=None)
    else:
        try:
            with open('alerts.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []


# ============================================================
# --- توابع دیتابیس: علاقه‌مندی‌ها ---
# ============================================================

async def add_favorite(chat_id, asset_key):
    if favorites_collection is not None:
        existing = await favorites_collection.find_one({"chat_id": str(chat_id), "asset": asset_key})
        if existing is None:
            await favorites_collection.insert_one({"chat_id": str(chat_id), "asset": asset_key, "created_at": time.time()})
            return True
        return False
    else:
        favorites = []
        try:
            with open('favorites.json', 'r', encoding='utf-8') as f:
                favorites = json.load(f)
        except:
            pass
        exists = any(f["chat_id"] == str(chat_id) and f["asset"] == asset_key for f in favorites)
        if not exists:
            favorites.append({"chat_id": str(chat_id), "asset": asset_key, "created_at": time.time()})
            with open('favorites.json', 'w', encoding='utf-8') as f:
                json.dump(favorites, f, ensure_ascii=False, indent=2)
            return True
        return False


async def remove_favorite(chat_id, asset_key):
    if favorites_collection is not None:
        await favorites_collection.delete_one({"chat_id": str(chat_id), "asset": asset_key})
    else:
        try:
            with open('favorites.json', 'r', encoding='utf-8') as f:
                favorites = json.load(f)
            favorites = [f for f in favorites if not (f["chat_id"] == str(chat_id) and f["asset"] == asset_key)]
            with open('favorites.json', 'w', encoding='utf-8') as f:
                json.dump(favorites, f, ensure_ascii=False, indent=2)
        except:
            pass


async def get_user_favorites(chat_id):
    if favorites_collection is not None:
        cursor = favorites_collection.find({"chat_id": str(chat_id)})
        docs = await cursor.to_list(length=None)
        return [d["asset"] for d in docs]
    else:
        try:
            with open('favorites.json', 'r', encoding='utf-8') as f:
                favorites = json.load(f)
            return [f["asset"] for f in favorites if f["chat_id"] == str(chat_id)]
        except:
            return []


async def is_favorite(chat_id, asset_key):
    favs = await get_user_favorites(chat_id)
    return asset_key in favs


# ============================================================
# --- دریافت قیمت رمزارز از CoinGecko (API جهانی) ---
# ============================================================

# کش برای نرخ دلار (برای جلوگیری از درخواست‌های تکراری)
_usd_rate_cache = {"price": None, "timestamp": 0}
_USD_CACHE_TTL = 300  # 5 دقیقه


def _get_usd_to_toman():
    """دریافت نرخ دلار به تومان با کش"""
    now = time.time()
    if _usd_rate_cache["price"] and (now - _usd_rate_cache["timestamp"]) < _USD_CACHE_TTL:
        return _usd_rate_cache["price"]

    try:
        data = fetch_fiat_data("USD")
        if data and data.get("price"):
            _usd_rate_cache["price"] = data["price"]
            _usd_rate_cache["timestamp"] = now
            return data["price"]
    except Exception as e:
        print(f"⚠️ Error fetching USD/IRT rate: {type(e).__name__}", flush=True)

    # اگه کش قبلی داشت، ازش استفاده کن
    return _usd_rate_cache["price"]


def fetch_crypto_data(symbol: str):
    """دریافت قیمت رمزارز از CoinGecko و تبدیل به تومان"""
    symbol = symbol.strip().upper()

    coin_id = COINGECKO_MAP.get(symbol)
    if not coin_id:
        print(f"⚠️ Symbol {symbol} not supported in CoinGecko map", flush=True)
        return None

    # ۱. دریافت قیمت دلاری از CoinGecko
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if coin_id not in data:
            print(f"⚠️ CoinGecko has no data for {symbol}", flush=True)
            return None

        usd_price = data[coin_id].get("usd")
        change_24h = data[coin_id].get("usd_24h_change")

        if usd_price is None:
            return None

    except Exception as e:
        print(f"⚠️ CoinGecko failed for {symbol}: {type(e).__name__}", flush=True)
        return None

    # ۲. دریافت نرخ دلار به تومان
    usd_to_toman = _get_usd_to_toman()
    if not usd_to_toman:
        print(f"⚠️ Could not fetch USD/IRT rate for {symbol}", flush=True)
        return None

    # ۳. تبدیل قیمت دلاری به تومان
    price_in_toman = float(usd_price) * float(usd_to_toman)

    # ۴. برگرداندن داده‌ها در قالب مورد انتظار
    return {
        "symbol": symbol,
        "buy_price": price_in_toman,
        "sell_price": price_in_toman,
        "change": change_24h
    }


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


def fetch_fiat_data(symbol: str):
    symbol_lower = symbol.strip().lower()
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(FIAT_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return None
        if symbol_lower in data:
            price = _get_json_price(data[symbol_lower], ["value", "price", "rate"])
            if price is not None:
                return {"symbol": symbol.upper(), "price": price}
        return None
    except Exception as e:
        print(f"API Error (Fiat): {e}", flush=True)
        return None


def fetch_gold_data(asset_key: str):
    key_map = {
        "gold_18": "18ayar", "coin_emami": "sekkeh", "coin_bahar": "bahar",
        "coin_half": "nim", "coin_quarter": "rob", "coin_gerami": "gerami",
    }
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


def get_current_price(asset_key: str):
    if asset_key == "TOMAN":
        return {"symbol": "TOMAN", "price": 1.0}
    if asset_key in GOLD_NAMES:
        return fetch_gold_data(asset_key)
    elif asset_key in FIAT_NAMES:
        return fetch_fiat_data(asset_key)
    else:
        data = fetch_crypto_data(asset_key)
        if data:
            return {"symbol": data["symbol"], "price": data["buy_price"]}
        return None


# ============================================================
#                     کیبوردها
# ============================================================

def main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🪙 ارز دیجیتال", callback_data="MENU:CRYPTO"), row=0)
    markup.add(InlineKeyboardButton(text="💵 ارزهای فیات", callback_data="MENU:FIAT"), row=0)
    markup.add(InlineKeyboardButton(text="🥇 طلا و سکه", callback_data="MENU:GOLD"), row=1)
    markup.add(InlineKeyboardButton(text="🔄 مبدل ارز", callback_data="CONV:NEW"), row=1)
    markup.add(InlineKeyboardButton(text="⭐ علاقه‌مندی‌ها", callback_data="FAV:VIEW"), row=2)
    markup.add(InlineKeyboardButton(text="🔔 هشدار قیمت", callback_data="ALERT:NEW"), row=2)
    markup.add(InlineKeyboardButton(text="📋 هشدارهای من", callback_data="MENU:MYALERTS"), row=3)
    markup.add(InlineKeyboardButton(text="📊 لیست رمزارزها", callback_data="MENU:LIST"), row=3)
    return markup


def crypto_menu_keyboard():
    markup = InlineKeyboardMarkup()
    pairs = [POPULAR_CRYPTOS[i:i+2] for i in range(0, len(POPULAR_CRYPTOS), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            markup.add(InlineKeyboardButton(text=sym, callback_data=f"CRYPTO:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text="📊 لیست کامل رمزارزها", callback_data="MENU:LIST"), row=next_row)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=next_row + 1)
    return markup


def fiat_menu_keyboard():
    markup = InlineKeyboardMarkup()
    pairs = [POPULAR_FIATS[i:i+2] for i in range(0, len(POPULAR_FIATS), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            markup.add(InlineKeyboardButton(text=f"{FIAT_NAMES.get(sym, sym)}", callback_data=f"FIAT:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=next_row)
    return markup


def gold_menu_keyboard():
    markup = InlineKeyboardMarkup()
    pairs = [POPULAR_GOLDS[i:i+2] for i in range(0, len(POPULAR_GOLDS), 2)]
    for row_idx, pair in enumerate(pairs):
        for sym in pair:
            markup.add(InlineKeyboardButton(text=GOLD_NAMES.get(sym, sym), callback_data=f"GOLD:{sym}"), row=row_idx)
    next_row = len(pairs)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=next_row)
    return markup


def alert_asset_category_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🪙 رمزارز", callback_data="ALERT:CAT:crypto"), row=0)
    markup.add(InlineKeyboardButton(text="💱 ارز فیات", callback_data="ALERT:CAT:fiat"), row=0)
    markup.add(InlineKeyboardButton(text="🥇 طلا و سکه", callback_data="ALERT:CAT:gold"), row=1)
    markup.add(InlineKeyboardButton(text="✏️ وارد کردن نام دستی", callback_data="ALERT:MANUAL"), row=2)
    markup.add(InlineKeyboardButton(text="❌ انصراف", callback_data="ALERT:CANCEL"), row=3)
    return markup


def alert_asset_list_keyboard(category):
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
    markup.add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="ALERT:NEW"), row=next_row)
    markup.add(InlineKeyboardButton(text="❌ انصراف", callback_data="ALERT:CANCEL"), row=next_row + 1)
    return markup


def alert_direction_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="📈 وقتی از این قیمت بالا رفت", callback_data="ALERT:DIR:above"), row=0)
    markup.add(InlineKeyboardButton(text="📉 وقتی از این قیمت پایین آمد", callback_data="ALERT:DIR:below"), row=1)
    markup.add(InlineKeyboardButton(text="❌ انصراف", callback_data="ALERT:CANCEL"), row=2)
    return markup


def convert_from_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="دلار 🇺🇸", callback_data="CONV:FROM:USD"), row=0)
    markup.add(InlineKeyboardButton(text="یورو 🇪🇺", callback_data="CONV:FROM:EUR"), row=0)
    markup.add(InlineKeyboardButton(text="تومان 🇮🇷", callback_data="CONV:FROM:TOMAN"), row=1)
    markup.add(InlineKeyboardButton(text="BTC", callback_data="CONV:FROM:BTC"), row=2)
    markup.add(InlineKeyboardButton(text="ETH", callback_data="CONV:FROM:ETH"), row=2)
    markup.add(InlineKeyboardButton(text="USDT", callback_data="CONV:FROM:USDT"), row=2)
    markup.add(InlineKeyboardButton(text="🥇 طلای ۱۸", callback_data="CONV:FROM:gold_18"), row=3)
    markup.add(InlineKeyboardButton(text="🪙 سکه امامی", callback_data="CONV:FROM:coin_emami"), row=3)
    markup.add(InlineKeyboardButton(text="❌ انصراف", callback_data="CONV:CANCEL"), row=4)
    return markup


def convert_to_keyboard(from_asset):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="تومان 🇮🇷", callback_data="CONV:TO:TOMAN"), row=0)
    markup.add(InlineKeyboardButton(text="دلار 🇺🇸", callback_data="CONV:TO:USD"), row=0)
    markup.add(InlineKeyboardButton(text="یورو 🇪🇺", callback_data="CONV:TO:EUR"), row=1)
    markup.add(InlineKeyboardButton(text="BTC", callback_data="CONV:TO:BTC"), row=2)
    markup.add(InlineKeyboardButton(text="ETH", callback_data="CONV:TO:ETH"), row=2)
    markup.add(InlineKeyboardButton(text="🪙 سکه امامی", callback_data="CONV:TO:coin_emami"), row=3)
    markup.add(InlineKeyboardButton(text="🥇 طلای ۱۸", callback_data="CONV:TO:gold_18"), row=3)
    markup.add(InlineKeyboardButton(text="❌ انصراف", callback_data="CONV:CANCEL"), row=4)
    return markup


def alerts_list_keyboard(alerts, user_id):
    markup = InlineKeyboardMarkup()
    for idx, a in enumerate(alerts):
        name = get_asset_display_name(a["asset"])
        direction_sym = "↑" if a["direction"] == "above" else "↓"
        label = f"🗑 {name} {direction_sym} {format_price(a['target_price'])}"
        markup.add(InlineKeyboardButton(text=label, callback_data=f"DELALERT:{a['asset']}"), row=idx)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=len(alerts))
    return markup


def fav_category_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🪙 رمزارز", callback_data="FAV:CAT:crypto"), row=0)
    markup.add(InlineKeyboardButton(text="💱 ارز فیات", callback_data="FAV:CAT:fiat"), row=0)
    markup.add(InlineKeyboardButton(text="🥇 طلا و سکه", callback_data="FAV:CAT:gold"), row=1)
    markup.add(InlineKeyboardButton(text="📋 لیست علاقه‌مندی‌های من", callback_data="FAV:VIEW"), row=2)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=3)
    return markup


def fav_asset_list_keyboard(category, user_favs):
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
    markup.add(InlineKeyboardButton(text="🔙 بازگشت", callback_data="FAV:NEW"), row=next_row)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=next_row + 1)
    return markup


def fav_view_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="➕ افزودن دارایی جدید", callback_data="FAV:NEW"), row=0)
    markup.add(InlineKeyboardButton(text="🔄 به‌روزرسانی قیمت‌ها", callback_data="FAV:VIEW"), row=1)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=2)
    return markup


# ============================================================
#                       پردازش‌ها
# ============================================================

async def show_main_menu(target, edit=False):
    text = (
        f"🏠 **منوی اصلی**\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:\n\n"
        "🪙 **ارز دیجیتال** — قیمت لحظه‌ای رمزارزها\n"
        "💵 **ارزهای فیات** — قیمت دلار، یورو، درهم و...\n"
        "🥇 **طلا و سکه** — قیمت طلا، سکه و مثقال\n"
        "🔄 **مبدل ارز** — تبدیل ارزها به یکدیگر\n"
        "⭐ **علاقه‌مندی‌ها** — لیست شخصی شما\n"
        "🔔 **هشدار قیمت** — دریافت اطلاع‌رسانی خودکار\n"
        "📋 **هشدارهای من** — مشاهده هشدارهای فعال"
    ) + footer_text()
    markup = main_menu_keyboard()
    if edit:
        try:
            await target.edit(text, components=markup)
            return
        except:
            pass
    await target.reply(text, components=markup)


async def process_crypto_and_reply(message, symbol, user_id=None):
    data = fetch_crypto_data(symbol)
    if not data:
        await message.reply(f"❌ رمزارز **{symbol.upper()}** یافت نشد." + footer_text())
        return
    buy_price_str = format_price(data['buy_price'])
    sell_price_str = format_price(data['sell_price'])
    result_text = (
        f"📊 **قیمت لحظه‌ای {data['symbol']}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💵 قیمت خرید: **{buy_price_str} IRT**\n"
        f"💰 قیمت فروش: **{sell_price_str} IRT**\n"
    )
    if data['change'] is not None:
        try:
            change_val = float(data['change'])
            sign = "+" if change_val > 0 else ""
            change_color = "🟢" if change_val > 0 else "🔴" if change_val < 0 else "⚪"
            result_text += f"📈 تغییرات ۲۴ ساعته: {change_color} **{sign}{change_val:.2f}%**\n"
        except (ValueError, TypeError):
            pass
    markup = InlineKeyboardMarkup()
    if user_id:
        if await is_favorite(user_id, data['symbol']):
            markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها", callback_data=f"FAV:DEL:{data['symbol']}"), row=0)
        else:
            markup.add(InlineKeyboardButton(text="⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:ADD:{data['symbol']}"), row=0)
    markup.add(InlineKeyboardButton(text="🔙 بازگشت به رمزارزها", callback_data="MENU:CRYPTO"), row=1)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=2)
    await message.reply(result_text + footer_text(), components=markup)


async def process_fiat_and_reply(message, symbol, user_id=None):
    data = fetch_fiat_data(symbol)
    fiat_name = FIAT_NAMES.get(symbol.upper(), symbol.upper())
    if not data or data['price'] is None:
        await message.reply(f"❌ ارز **{fiat_name}** یافت نشد." + footer_text())
        return
    price_str = format_price(data['price'])
    result_text = f"💵 **قیمت لحظه‌ای {fiat_name}**\n━━━━━━━━━━━━━━━━━━\n💰 قیمت: **{price_str} تومان**\n"
    markup = InlineKeyboardMarkup()
    if user_id:
        if await is_favorite(user_id, symbol.upper()):
            markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها", callback_data=f"FAV:DEL:{symbol.upper()}"), row=0)
        else:
            markup.add(InlineKeyboardButton(text="⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:ADD:{symbol.upper()}"), row=0)
    markup.add(InlineKeyboardButton(text="🔙 بازگشت به ارزهای فیات", callback_data="MENU:FIAT"), row=1)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=2)
    await message.reply(result_text + footer_text(), components=markup)


async def process_gold_and_reply(message, asset_key, user_id=None):
    data = fetch_gold_data(asset_key)
    gold_name = GOLD_NAMES.get(asset_key, asset_key)
    if not data or data['price'] is None:
        await message.reply(f"❌ قیمت **{gold_name}** در دسترس نیست." + footer_text())
        return
    price_str = format_price(data['price'])
    result_text = f"🥇 **قیمت لحظه‌ای {gold_name}**\n━━━━━━━━━━━━━━━━━━\n💰 قیمت: **{price_str} تومان**\n"
    markup = InlineKeyboardMarkup()
    if user_id:
        if await is_favorite(user_id, asset_key):
            markup.add(InlineKeyboardButton(text="⭐ حذف از علاقه‌مندی‌ها", callback_data=f"FAV:DEL:{asset_key}"), row=0)
        else:
            markup.add(InlineKeyboardButton(text="⭐ افزودن به علاقه‌مندی‌ها", callback_data=f"FAV:ADD:{asset_key}"), row=0)
    markup.add(InlineKeyboardButton(text="🔙 بازگشت به طلا و سکه", callback_data="MENU:GOLD"), row=1)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=2)
    await message.reply(result_text + footer_text(), components=markup)


async def show_my_alerts(target, user_id, edit=False):
    alerts = await get_user_alerts(user_id)
    if not alerts:
        text = "📭 **شما هیچ هشدار قیمتی ثبت نکرده‌اید.**\n\nبرای ثبت هشدار، روی دکمه زیر کلیک کنید:" + footer_text()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="🔔 ثبت هشدار جدید", callback_data="ALERT:NEW"), row=0)
        markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=1)
        if edit:
            try:
                await target.edit(text, components=markup)
                return
            except:
                pass
        await target.reply(text, components=markup)
        return

    lines = ["🔔 **هشدارهای فعال شما:**\n"]
    for a in alerts:
        name = get_asset_display_name(a["asset"])
        direction_text = "بالا ⬆️" if a["direction"] == "above" else "پایین ⬇️"
        lines.append(f"🔸 **{name}**\n   📊 هدف: {format_price(a['target_price'])} تومان ({direction_text})")
    lines.append("\n🗑 برای حذف، روی دکمه مربوطه کلیک کنید.")
    text = "\n".join(lines) + footer_text()
    markup = alerts_list_keyboard(alerts, user_id)
    if edit:
        try:
            await target.edit(text, components=markup)
            return
        except:
            pass
    await target.reply(text, components=markup)


async def show_favorites(target, user_id, edit=False):
    favs = await get_user_favorites(user_id)
    if not favs:
        text = "⭐ **لیست علاقه‌مندی‌های شما خالیه!**\n\nبرای افزودن دارایی، روی دکمه زیر کلیک کنید:" + footer_text()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="➕ افزودن دارایی", callback_data="FAV:NEW"), row=0)
        markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=1)
        if edit:
            try:
                await target.edit(text, components=markup)
                return
            except:
                pass
        await target.reply(text, components=markup)
        return

    lines = ["⭐ **لیست علاقه‌مندی‌های شما:**\n"]
    for asset in favs:
        name = get_asset_display_name(asset)
        data = get_current_price(asset)
        if data and data.get("price") is not None:
            lines.append(f"🔸 **{name}** → {format_price(data['price'])} تومان")
        else:
            lines.append(f"🔸 **{name}** → ❌ نامشخص")
    text = "\n".join(lines) + footer_text()
    markup = fav_view_keyboard()
    if edit:
        try:
            await target.edit(text, components=markup)
            return
        except:
            pass
    await target.reply(text, components=markup)


async def do_convert(target, amount, from_asset, to_asset):
    from_price = get_current_price(from_asset)
    if not from_price or from_price.get("price") is None:
        await target.reply(f"❌ قیمت **{get_asset_display_name(from_asset)}** یافت نشد." + footer_text())
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
            await target.reply(f"❌ قیمت **{to_name}** یافت نشد." + footer_text())
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
    markup.add(InlineKeyboardButton(text="🔄 تبدیل جدید", callback_data="CONV:NEW"), row=0)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=1)
    await target.reply(result_text + footer_text(), components=markup)


# ============================================================
# --- چک‌کننده هشدارها ---
# ============================================================

async def alert_checker_async():
    print("🔔 Alert checker started!", flush=True)
    while True:
        try:
            alerts = await get_all_alerts()
            if not alerts:
                await asyncio.sleep(60)
                continue
            for alert in alerts[:]:
                current = get_current_price(alert["asset"])
                if not current or current.get("price") is None:
                    continue
                current_price = float(current["price"])
                target = alert["target_price"]
                direction = alert["direction"]
                triggered = False
                if direction == "above" and current_price >= target:
                    triggered = True
                elif direction == "below" and current_price <= target:
                    triggered = True
                if triggered:
                    name = get_asset_display_name(alert["asset"])
                    direction_text = "بالا رفت 📈" if direction == "above" else "پایین آمد 📉"
                    notification = (
                        f"🔔 **هشدار قیمت!**\n━━━━━━━━━━━━━━━━━━\n"
                        f"📊 دارایی: **{name}**\n"
                        f"💰 قیمت فعلی: **{format_price(current_price)} تومان**\n"
                        f"🎯 قیمت هدف: {format_price(target)} تومان\n"
                        f"📈 وضعیت: قیمت از هدف شما {direction_text}\n"
                        f"━━━━━━━━━━━━━━━━━━" + footer_text()
                    )
                    try:
                        await bot.send_message(alert["chat_id"], notification)
                    except Exception as e:
                        print(f"Error sending alert: {e}", flush=True)
                    if alerts_collection is not None:
                        try:
                            await alerts_collection.delete_one({"_id": alert["_id"]})
                        except:
                            pass
                    else:
                        await remove_alert(alert["chat_id"], alert["asset"])
        except Exception as e:
            print(f"Alert checker error: {e}", flush=True)
        await asyncio.sleep(60)


# ============================================================
# --- کانال اطلاع‌رسانی ---
# ============================================================

def build_channel_post():
    """ساخت متن پست کانال با همه بخش‌ها"""
    lines = ["📊 **نرخ لحظه‌ای بازار**", "━━━━━━━━━━━━━━━━━━"]

    # ===== ارزهای فیات =====
    lines.append("💵 **ارزهای فیات:**")
    fiat_found = False
    for sym in ["USD", "EUR", "AED", "TRY"]:
        try:
            data = fetch_fiat_data(sym)
            if data and data.get("price"):
                name = FIAT_NAMES.get(sym, sym)
                lines.append(f"  • {name}: **{format_price(data['price'])} تومان**")
                fiat_found = True
        except Exception as e:
            print(f"Error fetching fiat {sym}: {e}", flush=True)
    if not fiat_found:
        lines.append("  ⚠️ در دسترس نیست")
    lines.append("")

    # ===== طلا و سکه =====
    lines.append("🥇 **طلا و سکه:**")
    gold_found = False
    for asset in ["gold_18", "coin_emami", "coin_half"]:
        try:
            data = fetch_gold_data(asset)
            if data and data.get("price"):
                name = GOLD_NAMES.get(asset, asset)
                lines.append(f"  • {name}: **{format_price(data['price'])} تومان**")
                gold_found = True
        except Exception as e:
            print(f"Error fetching gold {asset}: {e}", flush=True)
    if not gold_found:
        lines.append("  ⚠️ در دسترس نیست")
    lines.append("")

    # ===== رمزارزها =====
    lines.append("🪙 **رمزارزها:**")
    crypto_found = False
    for sym in ["BTC", "ETH", "USDT", "BNB", "SOL"]:
        try:
            data = fetch_crypto_data(sym)
            if data and data.get("buy_price"):
                price_val = data['buy_price']
                # فرمت‌دهی هوشمند برای اعداد بزرگ
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
                crypto_found = True
            else:
                lines.append(f"  • {sym}: ⚠️ در دسترس نیست")
        except Exception as e:
            print(f"Error fetching crypto {sym}: {e}", flush=True)
            lines.append(f"  • {sym}: ⚠️ خطا")
    if not crypto_found:
        lines.append("  ⚠️ هیچ رمزارزی در دسترس نیست")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"🕐 {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("📢 @nabz_mediaa")

    return "\n".join(lines)


def channel_poster():
    global CHANNEL_NUMERIC_ID
    print(f"ℹ️ channel_poster started, interval={CHANNEL_POST_INTERVAL}s", flush=True)
    while True:
        try:
            time.sleep(CHANNEL_POST_INTERVAL)
            if CHANNEL_POST_ENABLED and CHANNEL_ID:
                post_text = build_channel_post()
                print(f"🔍 در حال ارسال پست به کانال: {CHANNEL_ID}", flush=True)
                try:
                    if MAIN_LOOP is not None:
                        future = asyncio.run_coroutine_threadsafe(bot.send_message(CHANNEL_ID, post_text), MAIN_LOOP)
                        result = future.result(timeout=30)
                        print(f"✅ پست کانال ارسال شد.", flush=True)
                        try:
                            if result and hasattr(result, 'message_id'):
                                _sent_channel_message_ids.add(str(result.message_id))
                                print(f"ℹ️ ذخیره شد message_id: {result.message_id}", flush=True)
                        except:
                            pass
                        try:
                            if result and hasattr(result, 'chat') and result.chat:
                                CHANNEL_NUMERIC_ID = str(result.chat.id)
                                print(f"ℹ️ CHANNEL_NUMERIC_ID = {CHANNEL_NUMERIC_ID}", flush=True)
                        except:
                            pass
                except Exception as e:
                    print(f"❌ خطا در ارسال پست کانال: {type(e).__name__}: {e}", flush=True)
            else:
                print("⚠️ کانال غیرفعال است.", flush=True)
        except Exception as e:
            print(f"Channel poster error: {e}", flush=True)


# ============================================================
#                       رویدادها
# ============================================================

@bot.event
async def on_ready():
    global MAIN_LOOP, BOT_ID, _channel_thread_started, _checker_thread_started
    print("=" * 60, flush=True)
    print("🚀 ON_READY CALLED!", flush=True)
    print("=" * 60, flush=True)
    print(f"ربات {bot.user.username} با موفقیت روشن شد و آماده به کار است!", flush=True)

    MAIN_LOOP = asyncio.get_running_loop()
    try:
        BOT_ID = str(bot.user.id)
        print(f"ℹ️ BOT_ID = {BOT_ID}", flush=True)
    except:
        pass

    try:
        db_ok = await init_db()
        if db_ok:
            print("✅ MongoDB متصل شد و آماده استفاده است!", flush=True)
        else:
            print("❌ MongoDB متصل نشد! از فایل‌های JSON استفاده می‌شود.", flush=True)
    except Exception as e:
        print(f"❌ خطا در init_db: {e}", flush=True)
        import traceback
        traceback.print_exc()

    if CHANNEL_POST_ENABLED and CHANNEL_ID:
        print(f"ℹ️ کانال اطلاع‌رسانی فعال است: {CHANNEL_ID}", flush=True)

    if not _checker_thread_started:
        try:
            asyncio.create_task(alert_checker_async())
            _checker_thread_started = True
            print("✅ سیستم هشدار قیمت فعال شد!", flush=True)
        except Exception as e:
            print(f"❌ خطا در شروع alert_checker: {e}", flush=True)

    if not _channel_thread_started:
        try:
            channel_thread = threading.Thread(target=channel_poster, daemon=True)
            channel_thread.start()
            _channel_thread_started = True
            print("✅ سیستم پست کانال فعال شد!", flush=True)
        except Exception as e:
            print(f"❌ خطا در شروع channel_poster: {e}", flush=True)


@bot.event
async def on_message(message: Message):
    # فیلتر ۱: message_id در لیست پیام‌های ارسالی ما
    try:
        msg_id = str(getattr(message, 'message_id', ''))
        if msg_id and msg_id in _sent_channel_message_ids:
            return
    except:
        pass

    # فیلتر ۲: نویسنده خود ربات
    try:
        if BOT_ID and message.author and str(getattr(message.author, 'id', '')) == BOT_ID:
            return
    except:
        pass

    # فیلتر ۳: فقط چت خصوصی
    try:
        chat_type = getattr(message.chat, 'type', None) if message.chat else None
        if chat_type != 'private':
            return
    except:
        return

    # فیلتر ۴: chat.id با کانال یکسانه
    try:
        chat_id = str(getattr(message.chat, 'id', '')) if message.chat else ''
        if CHANNEL_NUMERIC_ID and chat_id == CHANNEL_NUMERIC_ID:
            return
    except:
        pass

    if message.author is None:
        return
    if message.author.is_bot:
        return
    if not message.content:
        return

    # فیلتر ۵: محتوای پیام‌های خود ربات
    content = message.content
    if 'انتقادات و پیشنهادات:' in content:
        return
    if 'توسعه‌دهنده:' in content:
        return
    if '📊 **نرخ لحظه‌ای بازار**' in content:
        return
    if 'نرخ لحظه‌ای بازار' in content:
        return
    if content.count('تومان') >= 3:
        return

    user_id = get_user_id_from_message(message)
    text = message.content.strip()
    text_upper = text.upper()

    if user_id in user_states:
        state = user_states[user_id]["state"]
        data = user_states[user_id]["data"]

        if state == "alert_awaiting_price":
            try:
                price = float(text.replace(",", "").replace("،", ""))
                data["target_price"] = price
                user_states[user_id]["state"] = "alert_awaiting_direction"
                asset_name = get_asset_display_name(data["asset"])
                msg = (
                    f"🎯 **قیمت هدف ثبت شد**\n\n"
                    f"📊 دارایی: **{asset_name}**\n"
                    f"💰 قیمت هدف: **{format_price(price)} تومان**\n\n"
                    f"حالا انتخاب کنید که چه زمانی به شما اطلاع بدم:"
                ) + footer_text()
                await message.reply(msg, components=alert_direction_keyboard())
            except ValueError:
                await message.reply("❌ لطفاً یک عدد معتبر ارسال کنید (مثلاً 250000)." + footer_text())
            return

        if state == "alert_awaiting_manual_asset":
            asset_key = text_upper
            if asset_key in GOLD_NAMES or asset_key in FIAT_NAMES:
                data["asset"] = asset_key
                user_states[user_id]["state"] = "alert_awaiting_price"
                asset_name = get_asset_display_name(asset_key)
                msg = f"✅ دارایی انتخاب شده: **{asset_name}**\n\n💰 حالا **قیمت هدف** را به تومان وارد کنید:\n(فقط عدد، مثلاً: `250000`)" + footer_text()
                await message.reply(msg)
            else:
                crypto_data = fetch_crypto_data(asset_key)
                if crypto_data:
                    data["asset"] = asset_key
                    user_states[user_id]["state"] = "alert_awaiting_price"
                    msg = f"✅ رمزارز انتخاب شده: **{asset_key}**\n\n💰 حالا **قیمت هدف** را به تومان وارد کنید:\n(فقط عدد، مثلاً: `5000000000`)" + footer_text()
                    await message.reply(msg)
                else:
                    await message.reply(
                        f"❌ دارایی **{asset_key}** یافت نشد.\nلطفاً نام معتبر وارد کنید." + footer_text(),
                        components=alert_asset_category_keyboard()
                    )
            return

        if state == "convert_awaiting_amount":
            try:
                amount = float(text.replace(",", "").replace("،", ""))
                data["amount"] = amount
                user_states[user_id]["state"] = "convert_awaiting_to"
                from_name = get_asset_display_name(data["from_asset"])
                msg = f"✅ مقدار: **{format_price(amount)} {from_name}**\n\n🔄 حالا ارز **مقصد** را انتخاب کنید:" + footer_text()
                await message.reply(msg, components=convert_to_keyboard(data["from_asset"]))
            except ValueError:
                await message.reply("❌ لطفاً یک عدد معتبر ارسال کنید (مثلاً 100)." + footer_text())
            return

    if text == '/start':
        welcome_text = (
            f"سلام {message.author.first_name} عزیز! 👋\n\n"
            "🌟 به ربات **نرخ آنلاین | ارز، طلا، رمزارز** خوش آمدی!\n\n"
            "📊 مرجع اطلاع‌رسانی قیمت لحظه‌ای بازار\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "✨ **من می‌تونم بهت کمک کنم:**\n\n"
            "🪙 قیمت لحظه‌ای رمزارزها\n"
            "💵 قیمت دلار، یورو، درهم و...\n"
            "🥇 قیمت طلا، سکه و مثقال\n"
            "🔄 تبدیل ارز به ارز دیگه\n"
            "⭐ ذخیره علاقه‌مندی‌ها\n"
            "🔔 هشدار قیمت خودکار\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "👇 از منوی زیر شروع کن:"
        ) + footer_text()
        markup = main_menu_keyboard()
        if WELCOME_IMAGE_URL and WELCOME_IMAGE_URL.strip():
            try:
                await bot.send_photo(chat_id=user_id, photo=WELCOME_IMAGE_URL, caption=welcome_text, components=markup)
                return
            except Exception as e:
                print(f"Error sending welcome photo: {e}", flush=True)
        await message.reply(welcome_text, components=markup)
        return

    if text == '/menu':
        await show_main_menu(message)
        return
    if text == '/cancel':
        clear_state(user_id)
        await message.reply("✅ عملیات لغو شد.", components=main_menu_keyboard())
        return
    if text == '/list':
        # لیست رمزارزهای CoinGecko
        crypto_list = list(COINGECKO_MAP.keys())
        await message.reply("📋 **لیست رمزارزهای موجود:**\n\n" + "، ".join(crypto_list) + footer_text())
        return
    if text == '/myalerts':
        await show_my_alerts(message, user_id)
        return
    if text == '/fav' or text == '/favorites':
        await show_favorites(message, user_id)
        return

    alert_match = re.match(r'^هشدار\s+([A-Za-z_0-9]+)\s+(\d+(?:\.\d+)?)\s+(بالا|پایین|بیشتر|کمتر)$', text, re.IGNORECASE)
    if alert_match:
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
            await message.reply(f"❌ دارایی **{asset_key}** یافت نشد." + footer_text())
            return
        await add_alert(user_id, asset_key, target_price, direction)
        asset_name = get_asset_display_name(asset_key)
        direction_text = "بالا برود" if direction == "above" else "پایین بیاید"
        await message.reply(
            f"✅ **هشدار ثبت شد!**\n\n🔔 {asset_name} → {format_price(target_price)} تومان ({direction_text})\n💰 قیمت فعلی: {format_price(current['price'])} تومان" + footer_text(),
            components=main_menu_keyboard()
        )
        return

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
        await do_convert(message, amount, from_asset, to_asset)
        return

    if text_upper in FIAT_NAMES:
        await process_fiat_and_reply(message, text_upper, user_id)
        return
    await process_crypto_and_reply(message, text_upper, user_id)


@bot.event
async def on_callback(callback: CallbackQuery):
    data = callback.data
    user_id = get_user_id_from_callback(callback)

    # فقط چت خصوصی
    try:
        if hasattr(callback, 'message') and callback.message:
            if hasattr(callback.message, 'chat') and callback.message.chat:
                chat_type = getattr(callback.message.chat, 'type', None)
                if chat_type != 'private':
                    return
    except:
        return

    if data == "MENU:MAIN":
        clear_state(user_id)
        await show_main_menu(callback.message, edit=True)
        return
    if data == "MENU:CRYPTO":
        clear_state(user_id)
        text = "🪙 **ارز دیجیتال**\n\nیکی از رمزارزهای زیر را انتخاب کنید:"
        try:
            await callback.message.edit(text + footer_text(), components=crypto_menu_keyboard())
        except:
            await callback.message.reply(text + footer_text(), components=crypto_menu_keyboard())
        return
    if data == "MENU:FIAT":
        clear_state(user_id)
        text = "💵 **ارزهای فیات**\n\nیکی از ارزهای زیر را انتخاب کنید تا قیمت لحظه‌ای آن را ببینید:"
        try:
            await callback.message.edit(text + footer_text(), components=fiat_menu_keyboard())
        except:
            await callback.message.reply(text + footer_text(), components=fiat_menu_keyboard())
        return
    if data == "MENU:GOLD":
        clear_state(user_id)
        text = "🥇 **طلا و سکه**\n\nیکی از گزینه‌ها را انتخاب کنید:"
        try:
            await callback.message.edit(text + footer_text(), components=gold_menu_keyboard())
        except:
            await callback.message.reply(text + footer_text(), components=gold_menu_keyboard())
        return
    if data == "MENU:MYALERTS":
        await show_my_alerts(callback.message, user_id, edit=True)
        return
    if data == "MENU:LIST":
        crypto_list = list(COINGECKO_MAP.keys())
        await callback.message.reply("📋 **لیست رمزارزهای موجود:**\n\n" + "، ".join(crypto_list) + footer_text())
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

    # --- علاقه‌مندی‌ها ---
    if data == "FAV:VIEW":
        clear_state(user_id)
        await show_favorites(callback.message, user_id, edit=True)
        return
    if data == "FAV:NEW":
        clear_state(user_id)
        text = "⭐ **افزودن به علاقه‌مندی‌ها**\n\nاز کدام دسته می‌خواهید دارایی اضافه کنید؟" + footer_text()
        try:
            await callback.message.edit(text, components=fav_category_keyboard())
        except:
            await callback.message.reply(text, components=fav_category_keyboard())
        return
    if data.startswith("FAV:CAT:"):
        parts = data.split(":")
        category = parts[2] if len(parts) >= 3 else None
        if not category:
            return
        cat_names = {"crypto": "رمزارز", "fiat": "ارز فیات", "gold": "طلا و سکه"}
        user_favs = await get_user_favorites(user_id)
        text = f"⭐ **افزودن {cat_names.get(category, category)}**\n\n✅ = در لیست شماست | ➕ = می‌تونی اضافه کنی" + footer_text()
        try:
            await callback.message.edit(text, components=fav_asset_list_keyboard(category, user_favs))
        except:
            await callback.message.reply(text, components=fav_asset_list_keyboard(category, user_favs))
        return
    if data.startswith("FAV:ADD:"):
        parts = data.split(":")
        asset = parts[2] if len(parts) >= 3 else None
        if not asset:
            return
        added = await add_favorite(user_id, asset)
        asset_name = get_asset_display_name(asset)
        if added:
            await callback.message.reply(f"✅ **{asset_name}** به علاقه‌مندی‌هات اضافه شد!" + footer_text())
        else:
            await callback.message.reply(f"ℹ️ **{asset_name}** قبلاً توی لیستت بود." + footer_text())
        category = "crypto" if asset in POPULAR_CRYPTOS else "fiat" if asset in POPULAR_FIATS else "gold"
        user_favs = await get_user_favorites(user_id)
        text = f"⭐ **افزودن {category}**\n\n✅ = در لیست شماست | ➕ = می‌تونی اضافه کنی" + footer_text()
        try:
            await callback.message.edit(text, components=fav_asset_list_keyboard(category, user_favs))
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
        await callback.message.reply(f"🗑 **{asset_name}** از علاقه‌مندی‌هات حذف شد." + footer_text())
        category = "crypto" if asset in POPULAR_CRYPTOS else "fiat" if asset in POPULAR_FIATS else "gold"
        user_favs = await get_user_favorites(user_id)
        text = f"⭐ **افزودن {category}**\n\n✅ = در لیست شماست | ➕ = می‌تونی اضافه کنی" + footer_text()
        try:
            await callback.message.edit(text, components=fav_asset_list_keyboard(category, user_favs))
        except:
            pass
        return

    # --- هشدارها ---
    if data.startswith("DELALERT:"):
        parts = data.split(":")
        if len(parts) >= 2:
            asset = parts[1]
            await remove_alert(user_id, asset)
            await callback.message.reply(f"✅ هشدار **{get_asset_display_name(asset)}** حذف شد." + footer_text())
            await show_my_alerts(callback.message, user_id, edit=True)
        return
    if data == "ALERT:NEW":
        clear_state(user_id)
        text = "🔔 **ثبت هشدار قیمت**\n\nمی‌خواهید وقتی قیمت چه چیزی تغییر کرد به شما خبر بدم؟\nدسته‌بندی مورد نظر را انتخاب کنید:" + footer_text()
        try:
            await callback.message.edit(text, components=alert_asset_category_keyboard())
        except:
            await callback.message.reply(text, components=alert_asset_category_keyboard())
        return
    if data.startswith("ALERT:CAT:"):
        parts = data.split(":")
        category = parts[2] if len(parts) >= 3 else None
        if not category:
            return
        cat_names = {"crypto": "رمزارز", "fiat": "ارز فیات", "gold": "طلا و سکه"}
        text = f"🔔 **ثبت هشدار — {cat_names.get(category, category)}**\n\nدارایی مورد نظر را انتخاب کنید:"
        try:
            await callback.message.edit(text + footer_text(), components=alert_asset_list_keyboard(category))
        except:
            await callback.message.reply(text + footer_text(), components=alert_asset_list_keyboard(category))
        return
    if data == "ALERT:MANUAL":
        user_states[user_id] = {"state": "alert_awaiting_manual_asset", "data": {}}
        await callback.message.reply(
            "✏️ **نام دارایی را وارد کنید:**\n\n🔸 رمزارز: `BTC`\n🔸 ارز فیات: `USD`\n🔸 طلا/سکه: `coin_emami` یا `gold_18`\n\n❌ برای لغو: `/cancel`" + footer_text()
        )
        return
    if data.startswith("ALERT:SET:"):
        parts = data.split(":")
        asset = parts[2] if len(parts) >= 3 else None
        if not asset:
            return
        user_states[user_id] = {"state": "alert_awaiting_price", "data": {"asset": asset}}
        asset_name = get_asset_display_name(asset)
        current = get_current_price(asset)
        current_text = f"\n💰 قیمت فعلی: {format_price(current['price'])} تومان" if current else ""
        text = f"✅ دارایی انتخاب شده: **{asset_name}**{current_text}\n\n🎯 حالا **قیمت هدف** را به تومان وارد کنید:\n(فقط عدد، مثلاً: `250000`)\n\n❌ برای لغو: `/cancel`" + footer_text()
        try:
            await callback.message.edit(text)
        except:
            await callback.message.reply(text)
        return
    if data.startswith("ALERT:DIR:"):
        parts = data.split(":")
        direction = parts[2] if len(parts) >= 3 else None
        if not direction:
            return
        if user_id not in user_states or "asset" not in user_states[user_id]["data"] or "target_price" not in user_states[user_id]["data"]:
            await callback.message.reply("❌ خطا. لطفاً دوباره شروع کنید.", components=main_menu_keyboard())
            return
        asset = user_states[user_id]["data"]["asset"]
        target_price = user_states[user_id]["data"]["target_price"]
        await add_alert(user_id, asset, target_price, direction)
        clear_state(user_id)
        asset_name = get_asset_display_name(asset)
        direction_text = "بالا برود 📈" if direction == "above" else "پایین بیاید 📉"
        text = f"✅ **هشدار با موفقیت ثبت شد!**\n━━━━━━━━━━━━━━━━━━\n🔔 دارایی: **{asset_name}**\n🎯 قیمت هدف: **{format_price(target_price)} تومان**\n📊 شرط: وقتی قیمت {direction_text}\n━━━━━━━━━━━━━━━━━━\n📩 به محض رسیدن به این قیمت، به شما اطلاع می‌دهم." + footer_text()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="🔔 هشدار جدید", callback_data="ALERT:NEW"), row=0)
        markup.add(InlineKeyboardButton(text="📋 هشدارهای من", callback_data="MENU:MYALERTS"), row=1)
        markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=2)
        try:
            await callback.message.edit(text, components=markup)
        except:
            await callback.message.reply(text, components=markup)
        return
    if data == "ALERT:CANCEL":
        clear_state(user_id)
        await callback.message.reply("❌ عملیات لغو شد." + footer_text(), components=main_menu_keyboard())
        return

    # --- مبدل ---
    if data == "CONV:NEW":
        clear_state(user_id)
        text = "🔄 **مبدل ارز**\n\nمرحله ۱ از ۳: **از چه ارزی** می‌خواهید تبدیل کنید؟" + footer_text()
        try:
            await callback.message.edit(text, components=convert_from_keyboard())
        except:
            await callback.message.reply(text, components=convert_from_keyboard())
        return
    if data.startswith("CONV:FROM:"):
        parts = data.split(":")
        from_asset = parts[2] if len(parts) >= 3 else None
        if not from_asset:
            return
        user_states[user_id] = {"state": "convert_awaiting_amount", "data": {"from_asset": from_asset}}
        from_name = get_asset_display_name(from_asset)
        text = f"✅ ارز مبدأ: **{from_name}**\n\nمرحله ۲ از ۳: **چه مقدار** می‌خواهید تبدیل کنید؟\n(فقط عدد، مثلاً: `100`)\n\n❌ برای لغو: `/cancel`" + footer_text()
        try:
            await callback.message.edit(text)
        except:
            await callback.message.reply(text)
        return
    if data.startswith("CONV:TO:"):
        parts = data.split(":")
        to_asset = parts[2] if len(parts) >= 3 else None
        if not to_asset:
            return
        if user_id not in user_states or "from_asset" not in user_states[user_id]["data"] or "amount" not in user_states[user_id]["data"]:
            await callback.message.reply("❌ خطا. لطفاً دوباره شروع کنید.", components=main_menu_keyboard())
            return
        from_asset = user_states[user_id]["data"]["from_asset"]
        amount = user_states[user_id]["data"]["amount"]
        clear_state(user_id)
        await do_convert(callback.message, amount, from_asset, to_asset)
        return
    if data == "CONV:CANCEL":
        clear_state(user_id)
        await callback.message.reply("❌ عملیات لغو شد." + footer_text(), components=main_menu_keyboard())
        return


# --- سرور وب برای Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()


# --- اجرای ربات ---
bot.run()
