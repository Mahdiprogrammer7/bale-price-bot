
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from google import genai
from google.genai import types

# =========================================================
# تنظیمات Gemini
# =========================================================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

PRIMARY_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
).strip()

FALLBACK_MODEL = os.getenv(
    "GEMINI_FALLBACK_MODEL",
    "gemini-2.5-flash"
).strip()

MAX_DAILY_QUESTIONS = 15
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

SYSTEM_INSTRUCTION = """
تو دستیار هوش مصنوعی فارسی ربات ارز آنلاین هستی.

قوانین:
- به فارسی روان و دوستانه پاسخ بده.
- پاسخ‌ها را دقیق، مفید و قابل فهم بنویس.
- اگر اطلاعات زنده قیمت ارز یا رمزارز در دسترس نیست، قیمت را حدس نزن.
- اگر پاسخ را نمی‌دانی، صادقانه اعلام کن.
- از پاسخ‌های بی‌ربط و طولانی خودداری کن.
"""

client = None

if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
        print(
            f"✅ Gemini client initialized | "
            f"model={PRIMARY_MODEL} | key_present=True",
            flush=True
        )
    except Exception as exc:
        print(f"❌ Gemini initialization error: {exc}", flush=True)
else:
    print("❌ GEMINI_API_KEY is missing!", flush=True)


# =========================================================
# کلاس هوش مصنوعی
# سازگار با main.py فعلی
# =========================================================

class GeminiChat:

    # تاریخچه مکالمات در حافظه
    _histories = {}

    # -----------------------------------------------------
    # تاریخ روز تهران
    # -----------------------------------------------------

    @staticmethod
    def today_tehran():
        return datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")

    # -----------------------------------------------------
    # سهمیه روزانه
    # -----------------------------------------------------

    @staticmethod
    async def reserve_question(collection, chat_id, special=False):

        # کاربران خاص نامحدود هستند
        if special:
            return True, None

        today = GeminiChat.today_tehran()

        # ایجاد رکورد اولیه در صورت نبود
        await collection.update_one(
            {
                "chat_id": chat_id,
                "day": today
            },
            {
                "$setOnInsert": {
                    "chat_id": chat_id,
                    "day": today,
                    "count": 0
                }
            },
            upsert=True
        )

        # افزایش شمارنده در صورتی که هنوز سهمیه دارند
        result = await collection.find_one_and_update(
            {
                "chat_id": chat_id,
                "day": today,
                "count": {"$lt": MAX_DAILY_QUESTIONS}
            },
            {
                "$inc": {"count": 1}
            },
            return_document=True
        )

        if result:
            used = result.get("count", 0)
            remaining = max(0, MAX_DAILY_QUESTIONS - used)
            return True, remaining

        return False, 0

    # -----------------------------------------------------
    # بازگرداندن سهمیه در صورت شکست
    # -----------------------------------------------------

    @staticmethod
    async def refund_question(collection, chat_id):

        today = GeminiChat.today_tehran()

        await collection.update_one(
            {
                "chat_id": chat_id,
                "day": today,
                "count": {"$gt": 0}
            },
            {
                "$inc": {"count": -1}
            }
        )

    # -----------------------------------------------------
    # تعداد سؤال مصرف‌شده
    # -----------------------------------------------------

    @staticmethod
    async def get_usage(collection, chat_id):

        today = GeminiChat.today_tehran()

        record = await collection.find_one(
            {
                "chat_id": chat_id,
                "day": today
            }
        )

        return record.get("count", 0) if record else 0

    # -----------------------------------------------------
    # درخواست Gemini با Retry
    # -----------------------------------------------------

    @staticmethod
    async def _generate_with_retry(model, contents):

        delays = [2, 4, 8]
        last_error = None

        for attempt in range(4):

            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7,
                        max_output_tokens=2048
                    )
                )

                if not response or not response.text:
                    raise RuntimeError(
                        "Gemini returned an empty response"
                    )

                return response.text.strip()

            except Exception as exc:

                last_error = exc
                error_text = str(exc).lower()

                retryable = any(
                    item in error_text
                    for item in (
                        "503",
                        "unavailable",
                        "429",
                        "resource_exhausted",
                        "500",
                        "internal",
                        "timeout",
                        "temporarily"
                    )
                )

                if not retryable:
                    raise

                if attempt < 3:

                    delay = delays[attempt]

                    print(
                        f"⚠️ Gemini retry | model={model} "
                        f"| attempt={attempt + 1}/4 "
                        f"| wait={delay}s",
                        flush=True
                    )

                    await asyncio.sleep(delay)

        raise last_error

    # -----------------------------------------------------
    # پاسخ هوش مصنوعی
    # -----------------------------------------------------

    @staticmethod
    async def ask(chat_id, question):

        if not client:
            raise RuntimeError(
                "Gemini client is not initialized"
            )

        question = str(question).strip()

        if not question:
            return "لطفاً سؤال خود را وارد کنید."

        # تاریخچه قبلی کاربر
        history = GeminiChat._histories.get(chat_id, [])

        contents = list(history)

        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=question)
                ]
            )
        )

        # مدل اصلی و مدل جایگزین
        models_to_try = [PRIMARY_MODEL]

        if (
            FALLBACK_MODEL
            and FALLBACK_MODEL != PRIMARY_MODEL
        ):
            models_to_try.append(FALLBACK_MODEL)

        answer = None
        used_model = None
        last_error = None

        for model in models_to_try:

            try:

                answer = await GeminiChat._generate_with_retry(
                    model,
                    contents
                )

                used_model = model
                break

            except Exception as exc:

                last_error = exc

                print(
                    f"❌ Gemini request failed | "
                    f"model={model} | "
                    f"{type(exc).__name__}: {exc}",
                    flush=True
                )

        # اگر هر دو مدل شکست خوردند
        if not answer:
            raise RuntimeError(
                f"All Gemini models failed: {last_error}"
            )

        # ذخیره سؤال و جواب در تاریخچه
        history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=question)
                ]
            )
        )

        history.append(
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(text=answer)
                ]
            )
        )

        # حداکثر 16 پیام
        GeminiChat._histories[chat_id] = history[-16:]

        print(
            f"✅ Gemini answer | chat_id={chat_id} "
            f"| model={used_model}",
            flush=True
        )

        return answer

    # -----------------------------------------------------
    # پاک کردن تاریخچه
    # -----------------------------------------------------

    @staticmethod
    def clear_history(chat_id):
        GeminiChat._histories.pop(chat_id, None)


# =========================================================
# تابع مستقل مورد نیاز main.py
# =========================================================

async def daily_usage_text(collection, chat_id, special=False):

    if special:
        return "♾️ سهمیه نامحدود (کاربر خاص)"

    used = await GeminiChat.get_usage(
        collection,
        chat_id
    )

    remaining = max(
        0,
        MAX_DAILY_QUESTIONS - used
    )

    return (
        f"📊 سهمیه امروز: {remaining} سؤال باقی مانده "
        f"از {MAX_DAILY_QUESTIONS} سؤال"
    )
