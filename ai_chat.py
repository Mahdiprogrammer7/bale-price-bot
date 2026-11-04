
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from google import genai
from google.genai import types
from pymongo import ReturnDocument

# =========================================================
# CONFIG
# =========================================================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

PRIMARY_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
).strip()

# مدل جایگزین را می‌توان در Render تغییر داد
FALLBACK_MODEL = os.getenv(
    "GEMINI_FALLBACK_MODEL",
    "gemini-2.5-flash"
).strip()

MAX_DAILY_QUESTIONS = 15

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

logger = logging.getLogger("gemini_chat")

client = None

if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
        print(f"✅ Gemini client initialized | model={PRIMARY_MODEL} | key_present=True")
    except Exception as exc:
        print(f"❌ Gemini client initialization failed: {exc}")
else:
    print("❌ GEMINI_API_KEY is missing!")


# =========================================================
# GEMINI CHAT
# =========================================================

class GeminiChat:

    def __init__(self, db):
        self.db = db
        self.collection = db["ai_usage"]
        self._histories = {}

    # -----------------------------------------------------
    # تاریخ امروز تهران
    # -----------------------------------------------------

    @staticmethod
    def today_tehran():
        return datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")

    # -----------------------------------------------------
    # کاربر ویژه
    # -----------------------------------------------------

    async def is_special(self, chat_id):
        user = await self.db["users"].find_one(
            {"chat_id": chat_id},
            {"special_user": 1}
        )

        return bool(user and user.get("special_user"))

    # -----------------------------------------------------
    # رزرو سهمیه
    # -----------------------------------------------------

    async def reserve_question(self, chat_id):

        if await self.is_special(chat_id):
            return True, None

        today = self.today_tehran()

        result = await self.collection.find_one_and_update(
            {
                "chat_id": chat_id,
                "day": today,
                "count": {"$lt": MAX_DAILY_QUESTIONS}
            },
            {
                "$inc": {"count": 1}
            },
            return_document=ReturnDocument.AFTER
        )

        if result:
            return True, result["count"]

        # ایجاد رکورد در صورت نبود
        try:
            await self.collection.update_one(
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
        except Exception:
            pass

        record = await self.collection.find_one(
            {
                "chat_id": chat_id,
                "day": today
            }
        )

        count = record.get("count", 0) if record else 0

        if count >= MAX_DAILY_QUESTIONS:
            return False, count

        result = await self.collection.find_one_and_update(
            {
                "chat_id": chat_id,
                "day": today,
                "count": {"$lt": MAX_DAILY_QUESTIONS}
            },
            {
                "$inc": {"count": 1}
            },
            return_document=ReturnDocument.AFTER
        )

        if result:
            return True, result["count"]

        return False, count

    # -----------------------------------------------------
    # بازگرداندن سهمیه در صورت خطا
    # -----------------------------------------------------

    async def refund_question(self, chat_id):

        if await self.is_special(chat_id):
            return

        today = self.today_tehran()

        await self.collection.update_one(
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
    # تعداد استفاده امروز
    # -----------------------------------------------------

    async def daily_usage(self, chat_id):

        if await self.is_special(chat_id):
            return {
                "special": True,
                "count": 0,
                "remaining": None
            }

        record = await self.collection.find_one(
            {
                "chat_id": chat_id,
                "day": self.today_tehran()
            }
        )

        count = record.get("count", 0) if record else 0

        return {
            "special": False,
            "count": count,
            "remaining": max(0, MAX_DAILY_QUESTIONS - count)
        }

    # -----------------------------------------------------
    # متن سهمیه
    # -----------------------------------------------------

    async def daily_usage_text(self, chat_id):

        usage = await self.daily_usage(chat_id)

        if usage["special"]:
            return "⭐ حساب کاربر ویژه | استفاده نامحدود از هوش مصنوعی"

        return (
            f"🤖 سهمیه هوش مصنوعی امروز:\n\n"
            f"🔹 استفاده‌شده: {usage['count']} از {MAX_DAILY_QUESTIONS}\n"
            f"🔹 باقی‌مانده: {usage['remaining']}"
        )

    # -----------------------------------------------------
    # پاک کردن تاریخچه
    # -----------------------------------------------------

    def clear_history(self, chat_id):
        self._histories.pop(chat_id, None)

    # -----------------------------------------------------
    # درخواست به Gemini با Retry
    # -----------------------------------------------------

    async def _generate_with_retry(self, model, contents):

        delays = [2, 4, 8]

        last_error = None

        for attempt in range(4):

            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "تو دستیار هوش مصنوعی فارسی ربات ارز آنلاین هستی. "
                            "پاسخ‌ها را واضح، دوستانه و دقیق بده. "
                            "اگر سؤال درباره قیمت لحظه‌ای ارز یا رمزارز است "
                            "و داده زنده در اختیار نداری، قیمت را حدس نزن."
                        ),
                        temperature=0.7,
                        max_output_tokens=2048
                    )
                )

                if not response or not response.text:
                    raise RuntimeError("Gemini returned an empty response")

                return response.text.strip()

            except Exception as exc:

                last_error = exc

                error_text = str(exc).lower()

                retryable = any(
                    item in error_text
                    for item in [
                        "503",
                        "unavailable",
                        "429",
                        "resource_exhausted",
                        "500",
                        "internal",
                        "timeout",
                        "temporarily"
                    ]
                )

                if not retryable:
                    raise

                if attempt < 3:
                    delay = delays[attempt]

                    print(
                        f"⚠️ Gemini retry | model={model} "
                        f"| attempt={attempt + 1}/4 "
                        f"| wait={delay}s"
                    )

                    await asyncio.sleep(delay)

        raise last_error

    # -----------------------------------------------------
    # پاسخ گرفتن از Gemini
    # -----------------------------------------------------

    async def ask(self, chat_id, question):

        if not client:
            return (
                "❌ سرویس هوش مصنوعی تنظیم نشده است.\n"
                "لطفاً بعداً دوباره امتحان کنید."
            )

        question = str(question).strip()

        if not question:
            return "لطفاً سؤال خود را وارد کنید."

        allowed, count = await self.reserve_question(chat_id)

        if not allowed:
            return (
                "⛔ سهمیه امروز شما تمام شده است.\n\n"
                f"🔹 سقف روزانه: {MAX_DAILY_QUESTIONS} سؤال\n"
                "🔹 سهمیه فردا دوباره شارژ می‌شود."
            )

        history = self._histories.get(chat_id, [])

        contents = list(history)
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=question)]
            )
        )

        models_to_try = [PRIMARY_MODEL]

        if FALLBACK_MODEL and FALLBACK_MODEL != PRIMARY_MODEL:
            models_to_try.append(FALLBACK_MODEL)

        answer = None
        used_model = None
        last_error = None

        for model in models_to_try:

            try:
                answer = await self._generate_with_retry(
                    model,
                    contents
                )

                used_model = model
                break

            except Exception as exc:

                last_error = exc

                print(
                    f"❌ Gemini API request failed "
                    f"| model={model} "
                    f"| {type(exc).__name__}: {exc}"
                )

        if not answer:

            await self.refund_question(chat_id)

            print(f"❌ AI chat error: {last_error}")

            return (
                "⚠️ سرور هوش مصنوعی فعلاً شلوغ است "
                "یا پاسخ نمی‌دهد.\n\n"
                "🔄 سهمیه شما کسر نشد؛ "
                "چند دقیقه دیگر دوباره امتحان کنید."
            )

        # ذخیره تاریخچه مکالمه
        history.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=question)]
            )
        )

        history.append(
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=answer)]
            )
        )

        # نگهداری حداکثر 16 پیام
        self._histories[chat_id] = history[-16:]

        print(
            f"✅ Gemini answer | chat_id={chat_id} "
            f"| model={used_model}"
        )

        return answer

