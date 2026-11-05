
import os
import json
import asyncio
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

from pymongo import ReturnDocument


# =========================================================
# CONFIG
# =========================================================

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY", ""
).strip()

PRIMARY_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
).strip()

FALLBACK_MODEL = os.getenv(
    "OPENROUTER_FALLBACK_MODEL",
    ""
).strip()

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

MAX_DAILY_QUESTIONS = 15

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

MAX_HISTORY_MESSAGES = 8
MAX_HISTORY_CHARS = 8000

RETRY_HISTORY_MESSAGES = 2
RETRY_HISTORY_CHARS = 2000

logger = logging.getLogger(__name__)


# =========================================================
# SYSTEM INSTRUCTION
# =========================================================

SYSTEM_INSTRUCTION = """
تو دستیار هوشمند و فارسی‌زبان ربات ارز آنلاین هستی.

========================
هویت و اطلاعات اختصاصی
========================

- نام تو: ارز آنلاین
- تو دستیار هوشمند پروژه ارز آنلاین هستی.
- سازنده و توسعه‌دهنده اصلی پروژه ارز آنلاین: مهدی نجفی.
- مهدی نجفی خالق و برنامه‌نویس پروژه ارز آنلاین است.
- ارز آنلاین یک ربات در پیام‌رسان بله است.
- هدف پروژه ارز آنلاین ارائه ابزارها و خدمات کاربردی در حوزه ارزهای دیجیتال،
  بازارهای مالی، برنامه‌نویسی و اطلاعات مرتبط است.
- وقتی کاربر درباره سازنده، مالک، توسعه‌دهنده یا هویت خودت سؤال کرد،
  از اطلاعات بالا استفاده کن.
- اگر کاربر پرسید چه کسی تو را ساخته، بگو:
  «من توسط مهدی نجفی ساخته و توسعه داده شده‌ام.»
- اگر کاربر پرسید ارز آنلاین را چه کسی ساخته،
  بگو پروژه ارز آنلاین توسط مهدی نجفی توسعه داده شده است.
- اگر کاربر درباره مهدی نجفی سؤال کرد،
  فقط اطلاعاتی را بیان کن که در این دستور آمده است.
- درباره سازنده، اطلاعات شخصی، سوابق، سن، محل زندگی،
  شماره تماس یا اطلاعات دیگری که در اختیار نداری اختراع نکن.
- اگر اطلاعات بیشتری درباره مهدی نجفی خواسته شد که در این دستور وجود ندارد،
  صادقانه بگو اطلاعات بیشتری در اختیار نداری.
- اطلاعات هویتی بالا را با اطلاعات عمومی اینترنت اشتباه نگیر.
- خودت را سازنده ارز آنلاین معرفی نکن؛ تو دستیار آن هستی.

========================
رفتار و پاسخ‌گویی
========================

- به زبان فارسی و روان پاسخ بده.
- پاسخ‌ها را واضح، کاربردی و قابل فهم ارائه کن.
- لحن دوستانه، حرفه‌ای و محترمانه داشته باش.
- پاسخ‌ها را متناسب با سؤال کاربر تنظیم کن.
- از پاسخ‌های غیرضروری و بیش از حد طولانی خودداری کن.
- اگر کاربر سؤال برنامه‌نویسی پرسید، مرحله‌به‌مرحله راهنمایی کن.
- اگر سؤال درباره ارز دیجیتال بود، اطلاعات را با احتیاط بیان کن.
- قیمت‌ها و اطلاعات لحظه‌ای را بدون دریافت داده معتبر حدس نزن.
- اگر اطلاعات کافی نداری، صادقانه اعلام کن.
- اگر کاربر اطلاعات یا داده‌ای ارسال کرد، می‌توانی همان داده‌ها را تحلیل کنی.
- هیچ‌وقت ادعا نکن به اینترنت، قیمت لحظه‌ای یا اطلاعات زنده دسترسی داری،
  مگر اینکه واقعاً در درخواست جاری داده معتبر در اختیار تو قرار گرفته باشد.
"""


# =========================================================
# AI CHAT
# =========================================================

class GeminiChat:

    # تاریخچه مکالمه کاربران
    _histories = {}

    # -----------------------------------------------------
    # TIME
    # -----------------------------------------------------

    @staticmethod
    def today_tehran():
        return datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    @classmethod
    def clear_history(cls, chat_id):
        cls._histories.pop(chat_id, None)

    @classmethod
    def _get_history(cls, chat_id):
        return cls._histories.setdefault(chat_id, [])

    @staticmethod
    def _trim_history(
        history,
        max_messages=MAX_HISTORY_MESSAGES,
        max_chars=MAX_HISTORY_CHARS
    ):
        history = history[-max_messages:]

        result = []
        total_chars = 0

        for item in reversed(history):
            content = str(item.get("content", ""))

            if total_chars + len(content) > max_chars:
                break

            result.insert(0, item)
            total_chars += len(content)

        return result

    # -----------------------------------------------------
    # OPENROUTER REQUEST
    # -----------------------------------------------------

    @staticmethod
    def _request_openrouter(model, messages):

        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY تنظیم نشده است."
            )

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1200
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            OPENROUTER_URL,
            data=data,
            headers={
                "Authorization": (
                    f"Bearer {OPENROUTER_API_KEY}"
                ),
                "Content-Type": "application/json",
                "HTTP-Referer": "https://arz-online.ir",
                "X-Title": "Arz Online"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=60
            ) as response:

                response_data = response.read().decode(
                    "utf-8"
            )

            result = json.loads(response_data)

            choices = result.get("choices", [])

            if not choices:
                raise RuntimeError(
                    "OpenRouter پاسخ خالی برگرداند."
                )

            answer = (
                choices[0]
                .get("message", {})
                .get("content", "")
            )

            if isinstance(answer, list):
                answer = "".join(
                    str(item.get("text", ""))
                    if isinstance(item, dict)
                    else str(item)
                    for item in answer
                )

            if not answer:
                raise RuntimeError(
                    "متن پاسخ OpenRouter خالی است."
                )

            return answer.strip()

        except urllib.error.HTTPError as error:

            error_body = error.read().decode(
                "utf-8",
                errors="ignore"
            )

            logger.error(
                "OpenRouter HTTP error | status=%s | body=%s",
                error.code,
                error_body[:1500]
            )

            raise RuntimeError(
                f"OpenRouter HTTP {error.code}: "
                f"{error_body[:500]}"
            ) from error

        except urllib.error.URLError as error:

            logger.error(
                "OpenRouter connection error: %s",
                error
            )

            raise RuntimeError(
                "اتصال به OpenRouter برقرار نشد."
            ) from error

    # -----------------------------------------------------
    # ERROR DETECTION
    # -----------------------------------------------------

    @staticmethod
    def _is_message_too_long(error):

        text = str(error).lower()

        return (
            "message is too long" in text
            or "context length" in text
            or "maximum context" in text
            or "token limit" in text
            or "too many tokens" in text
        )

    @staticmethod
    def _is_model_error(error):

        text = str(error).lower()

        return (
            "404" in text
            or "model not found" in text
            or "no endpoints" in text
            or "not available" in text
        )

    # -----------------------------------------------------
    # GENERATE WITH RETRY
    # -----------------------------------------------------

    @staticmethod
    async def _generate_with_retry(
        messages,
        history,
        current_question,
        chat_id
    ):

        # تلاش اول
        try:

            return await asyncio.to_thread(
                GeminiChat._request_openrouter,
                PRIMARY_MODEL,
                messages
            )

        except Exception as error:

            # ---------------------------------------------
            # HISTORY TOO LONG
            # ---------------------------------------------

            if GeminiChat._is_message_too_long(error):

                logger.warning(
                    "⚠️ Message too long | "
                    "retrying with smaller history | chat_id=%s",
                    chat_id
                )

                small_history = GeminiChat._trim_history(
                    history,
                    max_messages=RETRY_HISTORY_MESSAGES,
                    max_chars=RETRY_HISTORY_CHARS
                )

                retry_messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_INSTRUCTION
                    }
                ]

                retry_messages.extend(small_history)

                retry_messages.append({
                    "role": "user",
                    "content": current_question
                })

                try:

                    return await asyncio.to_thread(
                        GeminiChat._request_openrouter,
                        PRIMARY_MODEL,
                        retry_messages
                    )

                except Exception as retry_error:

                    logger.error(
                        "❌ Short history retry failed | "
                        "chat_id=%s | error=%s",
                        chat_id,
                        retry_error
                    )

                    # آخرین تلاش بدون تاریخچه
                    if GeminiChat._is_message_too_long(
                        retry_error
                    ):

                        no_history_messages = [
                            {
                                "role": "system",
                                "content": SYSTEM_INSTRUCTION
                            },
                            {
                                "role": "user",
                                "content": current_question
                            }
                        ]

                        return await asyncio.to_thread(
                            GeminiChat._request_openrouter,
                            PRIMARY_MODEL,
                            no_history_messages
                        )

                    raise retry_error

            # ---------------------------------------------
            # FALLBACK MODEL
            # ---------------------------------------------

            if (
                FALLBACK_MODEL
                and GeminiChat._is_model_error(error)
            ):

                logger.warning(
                    "⚠️ Primary model unavailable | fallback=%s",
                    FALLBACK_MODEL
                )

                return await asyncio.to_thread(
                    GeminiChat._request_openrouter,
                    FALLBACK_MODEL,
                    messages
                )

            raise error

    # -----------------------------------------------------
    # ASK
    # IMPORTANT: main.py calls GeminiChat.ask directly
    # -----------------------------------------------------

    @classmethod
    async def ask(cls, chat_id, question):

        question = str(question).strip()

        if not question:
            return "❌ پیام شما خالی است."

        if not OPENROUTER_API_KEY:
            return "❌ سرویس هوش مصنوعی تنظیم نشده است."

        history = cls._get_history(chat_id)

        trimmed_history = cls._trim_history(
            history,
            MAX_HISTORY_MESSAGES,
            MAX_HISTORY_CHARS
        )

        messages = [
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION
            }
        ]

        messages.extend(trimmed_history)

        messages.append({
            "role": "user",
            "content": question
        })

        logger.info(
            "🤖 OpenRouter processing | model=%s | "
            "chat_id=%s | history=%s",
            PRIMARY_MODEL,
            chat_id,
            len(trimmed_history)
        )

        try:

            answer = await cls._generate_with_retry(
                messages=messages,
                history=trimmed_history,
                current_question=question,
                chat_id=chat_id
            )

            # ذخیره فقط بعد از پاسخ موفق
            history.append({
                "role": "user",
                "content": question
            })

            history.append({
                "role": "assistant",
                "content": answer
            })

            cls._histories[chat_id] = cls._trim_history(
                history,
                MAX_HISTORY_MESSAGES,
                MAX_HISTORY_CHARS
            )

            logger.info(
                "✅ OpenRouter answer | chat_id=%s | model=%s",
                chat_id,
                PRIMARY_MODEL
            )

            return answer

        except Exception as error:

            logger.error(
                "❌ AI chat error | chat_id=%s | error=%s",
                chat_id,
                error
            )

            if cls._is_message_too_long(error):

                return (
                    "⚠️ پیام یا سابقه گفتگو بیش از حد طولانی است.\n"
                    "لطفاً سؤال کوتاه‌تری بپرسید."
                )

            return (
                "❌ در حال حاضر امکان دریافت پاسخ وجود ندارد.\n"
                "لطفاً چند لحظه دیگر دوباره تلاش کنید."
            )

    # =====================================================
    # DAILY USAGE / MOTOR MONGODB
    # =====================================================

    # -----------------------------------------------------
    # RESERVE QUESTION
    # Returns: allowed, remaining
    # -----------------------------------------------------

    @staticmethod
    async def reserve_question(
        collection,
        chat_id,
        special=False
    ):

        if special:
            return True, None

        today = GeminiChat.today_tehran()

        # افزایش اتمیک شمارنده
        document = await collection.find_one_and_update(
            {
                "chat_id": chat_id,
                "date": today,
                "count": {
                    "$lt": MAX_DAILY_QUESTIONS
                }
            },
            {
                "$inc": {
                    "count": 1
                }
            },
            return_document=ReturnDocument.AFTER
        )

        if document:

            used = int(document.get("count", 0))

            remaining = max(
                0,
                MAX_DAILY_QUESTIONS - used
            )

            return True, remaining

        # بررسی سند امروز
        existing = await collection.find_one({
            "chat_id": chat_id,
            "date": today
        })

        if existing:
            return False, 0

        # اولین سؤال امروز
        try:

            await collection.insert_one({
                "chat_id": chat_id,
                "date": today,
                "count": 1
            })

            return True, MAX_DAILY_QUESTIONS - 1

        except Exception:

            # احتمال درخواست همزمان
            document = await collection.find_one_and_update(
                {
                    "chat_id": chat_id,
                    "date": today,
                    "count": {
                        "$lt": MAX_DAILY_QUESTIONS
                    }
                },
                {
                    "$inc": {
                        "count": 1
                    }
                },
                return_document=ReturnDocument.AFTER
            )

            if document:

                used = int(document.get("count", 0))

                return True, max(
                    0,
                    MAX_DAILY_QUESTIONS - used
                )

            return False, 0

    # -----------------------------------------------------
    # REFUND QUESTION
    # -----------------------------------------------------

    @staticmethod
    async def refund_question(
        collection,
        chat_id
    ):

        today = GeminiChat.today_tehran()

        await collection.update_one(
            {
                "chat_id": chat_id,
                "date": today,
                "count": {
                    "$gt": 0
                }
            },
            {
                "$inc": {
                    "count": -1
                }
            }
        )

    # -----------------------------------------------------
    # GET USAGE
    # -----------------------------------------------------

    @staticmethod
    async def get_usage(
        collection,
        chat_id
    ):

        today = GeminiChat.today_tehran()

        document = await collection.find_one({
            "chat_id": chat_id,
            "date": today
        })

        if not document:
            return 0

        return int(document.get("count", 0))

    # -----------------------------------------------------
    # DAILY USAGE TEXT
    # -----------------------------------------------------

    @staticmethod
    async def daily_usage_text(
        collection,
        chat_id,
        special=False
    ):

        if special:

            return (
                "⭐ وضعیت حساب: کاربر خاص\n"
                "♾ محدودیت روزانه سؤال: نامحدود"
            )

        used = await GeminiChat.get_usage(
            collection,
            chat_id
        )

        remaining = max(
            0,
            MAX_DAILY_QUESTIONS - used
        )

        return (
            "🤖 وضعیت هوش مصنوعی\n\n"
            f"📊 سؤال‌های استفاده‌شده امروز: "
            f"{used}/{MAX_DAILY_QUESTIONS}\n"
            f"🟢 سؤال‌های باقی‌مانده: {remaining}"
        )


# =========================================================
# MODULE LEVEL FUNCTION
# main.py imports daily_usage_text directly
# =========================================================

async def daily_usage_text(
    collection,
    chat_id,
    special=False
):

    return await GeminiChat.daily_usage_text(
        collection,
        chat_id,
        special
    )
