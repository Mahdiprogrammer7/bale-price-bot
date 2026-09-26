import os
from bale import Bot, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import requests

# ==================== تنظیمات ====================
# این مقادیر به صورت خودکار از متغیرهای محیطی لیارا خوانده می‌شوند.
# اگر می‌خواهید روی سیستم خودتان (لوکال) تست کنید، می‌توانید مقادیر پیش‌فرض را اینجا بنویسید.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DEVELOPER_NAME = os.environ.get("DEVELOPER_NAME", "مهدی نجفی")
FEEDBACK_ID = os.environ.get("FEEDBACK_ID", "@mahdi8iiii")

CRYPTO_API_URL = 'https://api.abantether.com/api/v1/manager/otc/ticker'
FIAT_API_URL = 'https://raw.githubusercontent.com/HosseinOdd/Navasan-API/main/data/fiat.json'
# ==================================================

bot = Bot(token=BOT_TOKEN)

# --- دیکشنری نام‌های فارسی ارزهای فیات ---
FIAT_NAMES = {
    "USD": "دلار آمریکا", "EUR": "یورو", "GBP": "پوند انگلیس",
    "AED": "درهم امارات", "TRY": "لیر ترکیه", "CNY": "یوان چین",
    "JPY": "ین ژاپن", "CAD": "دلار کانادا", "AUD": "دلار استرالیا",
    "CHF": "فرانک سوئیس", "IQD": "دینار عراق", "SAR": "ریال عربستان",
    "KWD": "دینار کویت", "QAR": "ریال قطر", "OMR": "ریال عمان",
    "BHD": "دینار بحرین", "JOD": "دینار اردن", "RUB": "روبل روسیه",
    "INR": "روپیه هند", "PKR": "روپیه پاکستان", "AFN": "افغانی",
}


# --- توابع کمکی ---

def format_price(price_val):
    """تبدیل قیمت به فرمت زیبا با کاما و واحد پول"""
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
    """فوتر انتهای هر پیام با اطلاعات توسعه‌دهنده"""
    return (
        f"\n\n━━━━━━━━━━━━━━━━━━\n"
        f"👨‍💻 توسعه‌دهنده: **{DEVELOPER_NAME}**\n"
        f"📩 انتقادات و پیشنهادات: {FEEDBACK_ID}"
    )


def fetch_crypto_data(symbol: str):
    """دریافت اطلاعات یک رمزارز از API آبان‌تتر"""
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

            return {
                "symbol": target_key,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "change": change
            }
        return None
    except Exception as e:
        print(f"API Error (Crypto): {e}")
        return None


def fetch_fiat_data(symbol: str):
    """دریافت اطلاعات ارز فیات از Navasan-API (GitHub)"""
    symbol_lower = symbol.strip().lower()
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(FIAT_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if symbol_lower in data:
            price_data = data[symbol_lower]
            if isinstance(price_data, dict):
                price = price_data.get("value")
            else:
                price = price_data
            
            if price is not None:
                # قیمت مستقیماً به تومان است
                price = float(price)
                return {"symbol": symbol.upper(), "price": price}
        
        return None
    except Exception as e:
        print(f"API Error (Fiat - Navasan): {e}")
        return None


async def process_crypto_and_reply(message: Message, symbol: str):
    """پردازش درخواست رمزارز و ارسال پاسخ"""
    data = fetch_crypto_data(symbol)
    if not data:
        await message.reply(f"❌ رمزارز **{symbol.upper()}** یافت نشد.\n\n🔍 دستور `/list` را ارسال کنید." + footer_text())
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
            
    result_text += f"\n🔄 برای دریافت قیمت ارز دیگر، نام آن را ارسال کنید." + footer_text()
    await message.reply(result_text)


async def process_fiat_and_reply(message: Message, symbol: str):
    """پردازش درخواست ارز فیات و ارسال پاسخ"""
    data = fetch_fiat_data(symbol)
    fiat_name = FIAT_NAMES.get(symbol.upper(), symbol.upper())
    
    if not data or data['price'] is None:
        await message.reply(f"❌ ارز **{fiat_name}** یافت نشد.\n\n🔍 دستور `/fiat` را ارسال کنید." + footer_text())
        return
        
    price_str = format_price(data['price'])
    
    result_text = (
        f"💱 **قیمت لحظه‌ای {fiat_name} ({data['symbol']})**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 قیمت: **{price_str} تومان**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        "🔄 برای دریافت قیمت ارز دیگر، نام آن را ارسال کنید." + footer_text()
    )
    await message.reply(result_text)


def get_fiat_keyboard():
    """ساخت دکمه‌های شیشه‌ای برای ارزهای فیات پرطرفدار"""
    markup = InlineKeyboardMarkup()
    
    markup.add(InlineKeyboardButton(text="دلار 🇺🇸", callback_data="FIAT:USD"), row=0)
    markup.add(InlineKeyboardButton(text="یورو 🇪🇺", callback_data="FIAT:EUR"), row=0)
    
    markup.add(InlineKeyboardButton(text="درهم 🇦🇪", callback_data="FIAT:AED"), row=1)
    markup.add(InlineKeyboardButton(text="لیر 🇹🇷", callback_data="FIAT:TRY"), row=1)
    
    markup.add(InlineKeyboardButton(text="دینار عراق 🇮🇶", callback_data="FIAT:IQD"), row=2)
    markup.add(InlineKeyboardButton(text="پوند 🇬🇧", callback_data="FIAT:GBP"), row=2)
    
    markup.add(InlineKeyboardButton(text="📋 لیست کامل ارزهای فیات", callback_data="FIAT:LIST"), row=3)
    
    return markup


# --- رویدادهای ربات ---

@bot.event
async def on_ready():
    print(f"ربات {bot.user.username} با موفقیت روشن شد و آماده به کار است!")


@bot.event
async def on_message(message: Message):
    if message.author.is_bot:
        return

    text = message.content.strip()
    text_upper = text.upper()

    # 1. دستور شروع
    if text == '/start':
        welcome_text = (
            f"سلام {message.author.first_name} عزیز! 👋\n\n"
            "به ربات **قیمت لحظه‌ای ارز و رمزارز** خوش آمدید.\n\n"
            "💡 **روش استفاده:**\n"
            "🔹 **رمزارز:** نام آن را به انگلیسی بفرستید (مثل `BTC`).\n"
            "🔹 **ارز فیات:** دستور `/fiat` را ارسال کنید یا از دکمه‌های زیر استفاده کنید.\n\n"
            "📋 برای دیدن لیست رمزارزها، دستور `/list` را ارسال کنید."
        ) + footer_text()

        reply_markup = InlineKeyboardMarkup()
        reply_markup.add(InlineKeyboardButton(text="BTC", callback_data="CRYPTO:BTC"))
        reply_markup.add(InlineKeyboardButton(text="ETH", callback_data="CRYPTO:ETH"))
        reply_markup.add(InlineKeyboardButton(text="USDT", callback_data="CRYPTO:USDT"))
        reply_markup.add(InlineKeyboardButton(text="💱 ارزهای فیات", callback_data="FIAT:MENU"))
        reply_markup.add(InlineKeyboardButton(text="لیست رمزارزها 📋", callback_data="CRYPTO:LIST"))

        await message.reply(welcome_text, components=reply_markup)
        return

    # 2. دستور نمایش لیست ارزهای فیات
    if text == '/fiat':
        fiat_keyboard = get_fiat_keyboard()
        await message.reply(
            "💱 **ارزهای فیات**\n\n"
            "یکی از ارزهای زیر را انتخاب کنید یا نام آن را به انگلیسی بفرستید:\n"
            "🔸 `USD` (دلار)\n🔸 `EUR` (یورو)\n🔸 `AED` (درهم)\n"
            "🔸 `TRY` (لیر)\n🔸 `IQD` (دینار عراق)\n🔸 `GBP` (پوند)\n\n"
            "📋 برای دیدن لیست کامل، روی دکمه زیر بزنید.",
            components=fiat_keyboard
        )
        return

    # 3. دستور نمایش لیست رمزارزها
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
                if i == len(chunks) - 1:
                    await message.reply("، ".join(chunk) + footer_text())
                else:
                    await message.reply("، ".join(chunk))
        except Exception as e:
            await message.reply("⚠️ خطا در دریافت لیست رمزارزها." + footer_text())
            print(f"Error fetching crypto list: {e}")
        return

    # 4. تشخیص خودکار نوع ارز (فیات یا رمزارز)
    if text_upper in FIAT_NAMES:
        await process_fiat_and_reply(message, text_upper)
    else:
        await process_crypto_and_reply(message, text_upper)


# --- رویداد کلیک روی دکمه‌های شیشه‌ای ---
@bot.event
async def on_callback(callback: CallbackQuery):
    """پردازش کلیک روی دکمه‌های شیشه‌ای"""
    data = callback.data

    if data.startswith("CRYPTO:"):
        action = data.split(":")[1]
        if action == "LIST":
            await callback.message.reply("📋 لطفاً دستور `/list` را ارسال کنید." + footer_text())
        else:
            await process_crypto_and_reply(callback.message, action)

    elif data.startswith("FIAT:"):
        action = data.split(":")[1]
        if action == "MENU":
            fiat_keyboard = get_fiat_keyboard()
            await callback.message.reply(
                "💱 **ارزهای فیات**\n\nیکی از ارزهای زیر را انتخاب کنید:",
                components=fiat_keyboard
            )
        elif action == "LIST":
            fiat_list = "\n".join([f"🔸 `{code}` - {name}" for code, name in FIAT_NAMES.items()])
            await callback.message.reply(f"📋 **لیست کامل ارزهای فیات:**\n\n{fiat_list}" + footer_text())
        else:
            await process_fiat_and_reply(callback.message, action)


# اجرای ربات
bot.run()
