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

PROXY_URL = "https://red-meadow-20f7bale-bot-proxy.najafimahdi13867.workers.dev"
WELCOME_IMAGE_URL = ""
# ==================================================


# ============================================================
#       استفاده از Cloudflare Proxy برای دور زدن محدودیت IP
# ============================================================
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
bot_users = set()

# ============================================================
#       اتصال به دیتابیس MongoDB
# ============================================================
db_client = None
alerts_collection = None

async def init_db():
    global db_client, alerts_collection
    print(f"🔍 DEBUG: init_db called. MONGO_URI starts with: {MONGO_URI[:30] if MONGO_URI else 'EMPTY'}", flush=True)
    if not MONGO_URI:
        print("⚠️ MONGO_URI تنظیم نشده است. از فایل alerts.json استفاده می‌شود.", flush=True)
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


# --- توابع دیتابیس ---

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


# --- دریافت قیمت‌ها ---

def fetch_crypto_data(symbol: str):
    symbol = symbol.strip().upper()
    try:
        response = requests.get(CRYPTO_API_URL, timeout=10)
        response.raise_for_status()
        market = response.json()
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
        print(f"API Error (Crypto): {e}", flush=True)
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
    markup.add(InlineKeyboardButton(text="🔔 هشدار قیمت", callback_data="ALERT:NEW"), row=2)
    markup.add(InlineKeyboardButton(text="📋 هشدارهای من", callback_data="MENU:MYALERTS"), row=2)
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


async def process_crypto_and_reply(message, symbol):
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
    markup.add(InlineKeyboardButton(text="🔙 بازگشت به رمزارزها", callback_data="MENU:CRYPTO"), row=0)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=1)
    await message.reply(result_text + footer_text(), components=markup)


async def process_fiat_and_reply(message, symbol):
    data = fetch_fiat_data(symbol)
    fiat_name = FIAT_NAMES.get(symbol.upper(), symbol.upper())
    if not data or data['price'] is None:
        await message.reply(f"❌ ارز **{fiat_name}** یافت نشد." + footer_text())
        return
    price_str = format_price(data['price'])
    result_text = f"💵 **قیمت لحظه‌ای {fiat_name}**\n━━━━━━━━━━━━━━━━━━\n💰 قیمت: **{price_str} تومان**\n"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🔙 بازگشت به ارزهای فیات", callback_data="MENU:FIAT"), row=0)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=1)
    await message.reply(result_text + footer_text(), components=markup)


async def process_gold_and_reply(message, asset_key):
    data = fetch_gold_data(asset_key)
    gold_name = GOLD_NAMES.get(asset_key, asset_key)
    if not data or data['price'] is None:
        await message.reply(f"❌ قیمت **{gold_name}** در دسترس نیست." + footer_text())
        return
    price_str = format_price(data['price'])
    result_text = f"🥇 **قیمت لحظه‌ای {gold_name}**\n━━━━━━━━━━━━━━━━━━\n💰 قیمت: **{price_str} تومان**\n"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🔙 بازگشت به طلا و سکه", callback_data="MENU:GOLD"), row=0)
    markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=1)
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
                        await alerts_collection.delete_one({"_id": alert["_id"]})
                    else:
                        await remove_alert(alert["chat_id"], alert["asset"])
        except Exception as e:
            print(f"Alert checker error: {e}", flush=True)
        await asyncio.sleep(60)


# ============================================================
#                       رویدادها
# ============================================================

@bot.event
async def on_ready():
    print("=" * 60, flush=True)
    print("🚀 ON_READY CALLED!", flush=True)
    print("=" * 60, flush=True)
    print(f"ربات {bot.user.username} با موفقیت روشن شد و آماده به کار است!", flush=True)

    try:
        db_ok = await init_db()
        if db_ok:
            print("✅ MongoDB متصل شد و آماده استفاده است!", flush=True)
        else:
            print("❌ MongoDB متصل نشد! از فایل alerts.json استفاده می‌شود.", flush=True)
    except Exception as e:
        print(f"❌ خطا در init_db: {e}", flush=True)
        import traceback
        traceback.print_exc()

    try:
        # ✅ اصلاح اصلی: استفاده از asyncio.create_task به جای thread جداگانه
        asyncio.create_task(alert_checker_async())
        print("✅ سیستم هشدار قیمت فعال شد!", flush=True)
    except Exception as e:
        print(f"❌ خطا در شروع alert_checker: {e}", flush=True)
        import traceback
        traceback.print_exc()


@bot.event
async def on_message(message: Message):
    if message.author.is_bot:
        return
    user_id = get_user_id_from_message(message)
    text = message.content.strip()
    text_upper = text.upper()
    bot_users.add(user_id)

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
                        f"❌ دارایی **{asset_key}** یافت نشد.\nلطفاً نام معتبر وارد کنید یا از دکمه‌های موجود استفاده کنید." + footer_text(),
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
        members_count = len(bot_users)
        welcome_text = (
            f"سلام {message.author.first_name} عزیز! 👋\n\n"
            "🌟 به ربات **نرخ آنلاین | ارز، طلا، رمزارز** خوش آمدی!\n\n"
            "📊 مرجع اطلاع‌رسانی قیمت لحظه‌ای بازار\n\n"
            f"👥 **تعداد کاربران:** {members_count} نفر\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "✨ **من می‌تونم بهت کمک کنم:**\n\n"
            "🪙 قیمت لحظه‌ای رمزارزها\n"
            "💵 قیمت دلار، یورو، درهم و...\n"
            "🥇 قیمت طلا، سکه و مثقال\n"
            "🔄 تبدیل ارز به ارز دیگه\n"
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
        try:
            response = requests.get(CRYPTO_API_URL, timeout=10)
            markets_data = response.json().get("data", {}).get("markets", {})
            symbols = []
            if isinstance(markets_data, dict):
                symbols = list(markets_data.keys())
            elif isinstance(markets_data, list):
                symbols = [item.get("symbol") for item in markets_data if item.get("symbol")]
            clean_symbols = [s.replace("IRT", "") for s in symbols if "IRT" in s] or symbols
            if not clean_symbols:
                await message.reply("⚠️ لیست رمزارزها در دسترس نیست." + footer_text())
                return
            chunk_size = 50
            chunks = [clean_symbols[i:i + chunk_size] for i in range(0, len(clean_symbols), chunk_size)]
            await message.reply("📋 **لیست رمزارزهای موجود:**\n")
            for i, chunk in enumerate(chunks):
                await message.reply("، ".join(chunk))
        except Exception as e:
            await message.reply("⚠️ خطا در دریافت لیست رمزارزها." + footer_text())
            print(f"Error fetching crypto list: {e}", flush=True)
        return
    if text == '/myalerts':
        await show_my_alerts(message, user_id)
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
        await process_fiat_and_reply(message, text_upper)
        return
    await process_crypto_and_reply(message, text_upper)


@bot.event
async def on_callback(callback: CallbackQuery):
    data = callback.data
    user_id = get_user_id_from_callback(callback)
    if user_id:
        bot_users.add(user_id)

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
        try:
            response = requests.get(CRYPTO_API_URL, timeout=10)
            markets_data = response.json().get("data", {}).get("markets", {})
            symbols = []
            if isinstance(markets_data, dict):
                symbols = list(markets_data.keys())
            elif isinstance(markets_data, list):
                symbols = [item.get("symbol") for item in markets_data if item.get("symbol")]
            clean_symbols = [s.replace("IRT", "") for s in symbols if "IRT" in s] or symbols
            if not clean_symbols:
                await callback.message.reply("⚠️ لیست در دسترس نیست." + footer_text())
                return
            chunk_size = 50
            chunks = [clean_symbols[i:i + chunk_size] for i in range(0, len(clean_symbols), chunk_size)]
            await callback.message.reply("📋 **لیست رمزارزها:**\n")
            for chunk in chunks:
                await callback.message.reply("، ".join(chunk))
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="MENU:MAIN"), row=0)
            await callback.message.reply("🔙", components=markup)
        except Exception as e:
            await callback.message.reply("⚠️ خطا." + footer_text())
            print(f"Error: {e}", flush=True)
        return
    if data.startswith("CRYPTO:"):
        parts = data.split(":")
        if len(parts) >= 2:
            await process_crypto_and_reply(callback.message, parts[1])
        return
    if data.startswith("FIAT:"):
        parts = data.split(":")
        if len(parts) >= 2:
            await process_fiat_and_reply(callback.message, parts[1])
        return
    if data.startswith("GOLD:"):
        parts = data.split(":")
        if len(parts) >= 2:
            await process_gold_and_reply(callback.message, parts[1])
        return
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
