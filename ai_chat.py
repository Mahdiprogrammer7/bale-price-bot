
import os
import json
import asyncio
import logging
import urllib.request
import urllib.error
import base64
from datetime import datetime
from zoneinfo import ZoneInfo

from pymongo import ReturnDocument


# =========================================================
# تنظیمات
# =========================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

PRIMARY_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
).strip()

FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv(
        "OPENROUTER_FALLBACK_MODELS",
        ""
    ).split(",")
    if model.strip()
]

VISION_MODEL = os.getenv(
    "OPENROUTER_VISION_MODEL",
    "google/gemma-3-4b-it:free"
).strip()

MAX_DAILY_QUESTIONS = int(
    os.getenv("AI_DAILY_LIMIT", "15")
)

MAX_HISTORY_MESSAGES = int(
    os.getenv("AI_HISTORY_MESSAGES", "12")
)

MAX_HISTORY_CHARS = 10000

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

logging.basicConfig(level=logging.INFO)


# =========================================================
# خطاهای هوش مصنوعی
# =========================================================

class AIRequestError(Exception):
    pass


# =========================================================
# کلاس اصلی
# =========================================================

class GeminiChat:

    _histories = {}

    # -----------------------------------------------------
    # تاریخ امروز تهران
    # -----------------------------------------------------

    @staticmethod
    def today_tehran():
        return datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")

    # -----------------------------------------------------
    # سیستم پرامپت
    # -----------------------------------------------------

    @staticmethod
    def system_prompt():

        return """
تو دستیار هوشمند ربات ارز آنلاین هستی.

وظایف:
- پاسخ دقیق، مفید و قابل فهم به کاربران.
- زبان پیش‌فرض فارسی است.
- لحن دوستانه، حرفه‌ای و محترمانه داشته باش.
- اگر سؤال فنی بود، مرحله‌به‌مرحله توضیح بده.
- اگر پاسخ را نمی‌دانی، صادقانه بگو.
- اطلاعات قیمت لحظه‌ای، اخبار و اطلاعات زنده را
  بدون دسترسی واقعی به آن‌ها جعل نکن.
- برای تحلیل تصویر، فقط اطلاعاتی را بگو که واقعاً
  از تصویر قابل مشاهده است.
- اگر تصویر نامفهوم یا بی‌کیفیت است، اطلاع بده.
- خودت را دستیار هوش مصنوعی ارز آنلاین معرفی کن.
"""

    # -----------------------------------------------------
    # درخواست OpenRouter
    # -----------------------------------------------------

    @staticmethod
    def _request_openrouter(model, messages):

        if not API_KEY:
            raise AIRequestError(
                "OPENROUTER_API_KEY تنظیم نشده است."
            )

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1500
        }

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://render.com",
            "X-Title": "Arz Online"
        }

        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=60
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as error:

            body = error.read().decode(
                "utf-8",
                errors="ignore"
            )

            raise AIRequestError(
                f"HTTP {error.code}: {body[:500]}"
            )

        except Exception as error:

            raise AIRequestError(
                f"Request error: {error}"
            )

        choices = result.get("choices", [])

        if not choices:
            raise AIRequestError(
                "مدل پاسخ خالی برگرداند."
            )

        content = choices[0].get(
            "message", {}
        ).get("content", "")

        # بعضی مدل‌ها محتوا را به صورت لیست می‌دهند
        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(
                            item.get("text", "")
                        )

            content = "\n".join(parts)

        content = str(content).strip()

        if not content:
            raise AIRequestError(
                "پاسخ مدل خالی بود."
            )

        return content

    # -----------------------------------------------------
    # اجرای مدل اصلی و جایگزین‌ها
    # -----------------------------------------------------

    @classmethod
    async def _generate(cls, messages, vision=False):

        models = []

        if vision:
            models.append(VISION_MODEL)
        else:
            models.append(PRIMARY_MODEL)
            models.extend(FALLBACK_MODELS)

        # حذف مدل تکراری
        models = list(dict.fromkeys(models))

        errors = []

        for model in models:

            try:

                logging.info(
                    "AI model attempt: %s", model
                )

                result = await asyncio.to_thread(
                    cls._request_openrouter,
                    model,
                    messages
                )

                logging.info(
                    "AI model success: %s", model
                )

                return result

            except Exception as error:

                logging.warning(
                    "AI model failed %s: %s",
                    model,
                    error
                )

                errors.append(
                    f"{model}: {error}"
                )

        raise AIRequestError(
            "All AI models failed: "
            + " | ".join(errors)
        )

    # -----------------------------------------------------
    # مدیریت تاریخچه
    # -----------------------------------------------------

    @classmethod
    def _get_history(cls, chat_id):

        return cls._histories.get(
            str(chat_id), []
        )

    @classmethod
    def _save_history(
        cls,
        chat_id,
        question,
        answer
    ):

        chat_id = str(chat_id)

        history = cls._get_history(chat_id)

        history.extend([
            {
                "role": "user",
                "content": question
            },
            {
                "role": "assistant",
                "content": answer
            }
        ])

        history = history[
            -MAX_HISTORY_MESSAGES:
        ]

        total_chars = sum(
            len(str(item.get("content", "")))
            for item in history
        )

        while (
            history
            and total_chars > MAX_HISTORY_CHARS
        ):

            removed = history.pop(0)

            total_chars -= len(
                str(removed.get("content", ""))
            )

        cls._histories[chat_id] = history

    @classmethod
    def clear_history(cls, chat_id):

        cls._histories.pop(
            str(chat_id), None
        )

    # -----------------------------------------------------
    # چت متنی
    # -----------------------------------------------------

    @classmethod
    async def ask(cls, chat_id, question):

        question = str(question).strip()

        if not question:
            raise AIRequestError(
                "سؤال خالی است."
            )

        history = cls._get_history(chat_id)

        messages = [
            {
                "role": "system",
                "content": cls.system_prompt()
            }
        ]

        messages.extend(history)

        messages.append({
            "role": "user",
            "content": question
        })

        try:

            answer = await cls._generate(
                messages,
                vision=False
            )

            # فقط پاسخ موفق وارد تاریخچه می‌شود
            cls._save_history(
                chat_id,
                question,
                answer
            )

            return answer

        except Exception as error:

            logging.exception(
                "AI chat failed"
            )

            # خطا به main.py منتقل می‌شود
            # تا سهمیه برگردانده شود
            raise AIRequestError(
                "همه مدل‌های هوش مصنوعی "
                "در حال حاضر در دسترس نیستند."
            ) from error

    # -----------------------------------------------------
    # تحلیل تصویر
    # -----------------------------------------------------

    @classmethod
    async def ask_image(
        cls,
        chat_id,
        image_bytes,
        question="این تصویر را تحلیل کن."
    ):

        if not image_bytes:
            raise AIRequestError(
                "تصویر دریافت نشد."
            )

        encoded_image = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        image_url = (
            "data:image/jpeg;base64,"
            + encoded_image
        )

        history = cls._get_history(chat_id)

        messages = [
            {
                "role": "system",
                "content": cls.system_prompt()
            }
        ]

        messages.extend(history)

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": question
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                }
            ]
        })

        try:

            answer = await cls._generate(
                messages,
                vision=True
            )

            cls._save_history(
                chat_id,
                question,
                answer
            )

            return answer

        except Exception as error:

            logging.exception(
                "AI image analysis failed"
            )

            raise AIRequestError(
                "مدل تحلیل تصویر در دسترس نیست."
            ) from error

    # -----------------------------------------------------
    # رزرو سهمیه
    # -----------------------------------------------------

    @classmethod
    async def reserve_question(
        cls,
        collection,
        chat_id,
        special=False
    ):

        if special:
            return True, None

        today = cls.today_tehran()

        query = {
            "chat_id": int(chat_id),
            "day": today,
            "count": {
                "$lt": MAX_DAILY_QUESTIONS
            }
        }

        document = await collection.find_one_and_update(
            query,
            {"$inc": {"count": 1}},
            return_document=ReturnDocument.AFTER
        )

        if document:

            remaining = (
                MAX_DAILY_QUESTIONS
                - document["count"]
            )

            return True, remaining

        # اگر رکورد امروز وجود دارد یعنی سهمیه تمام شده
        existing = await collection.find_one({
            "chat_id": int(chat_id),
            "day": today
        })

        if existing:

            return False, 0

        # ایجاد رکورد اولین سؤال روز
        try:

            await collection.insert_one({
                "chat_id": int(chat_id),
                "day": today,
                "count": 1
            })

            return True, (
                MAX_DAILY_QUESTIONS - 1
            )

        except Exception:

            # اگر هم‌زمان درخواست دیگری ثبت شده باشد
            document = await collection.find_one_and_update(
                query,
                {"$inc": {"count": 1}},
                return_document=ReturnDocument.AFTER
            )

            if document:

                return True, (
                    MAX_DAILY_QUESTIONS
                    - document["count"]
                )

            return False, 0

    # -----------------------------------------------------
    # بازگرداندن سهمیه
    # -----------------------------------------------------

    @classmethod
    async def refund_question(
        cls,
        collection,
        chat_id
    ):

        today = cls.today_tehran()

        await collection.update_one(
            {
                "chat_id": int(chat_id),
                "day": today,
                "count": {"$gt": 0}
            },
            {
                "$inc": {"count": -1}
            }
        )

    # -----------------------------------------------------
    # دریافت مصرف امروز
    # -----------------------------------------------------

    @classmethod
    async def get_usage(
        cls,
        collection,
        chat_id
    ):

        today = cls.today_tehran()

        document = await collection.find_one({
            "chat_id": int(chat_id),
            "day": today
        })

        return document.get(
            "count", 0
        ) if document else 0


# =========================================================
# متن سهمیه
# =========================================================

async def daily_usage_text(
    collection,
    chat_id,
    special=False
):

    if special:

        return (
            "♾️ سهمیه نامحدود "
            "کاربر خاص"
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
        f"📊 مصرف امروز: {used}/"
        f"{MAX_DAILY_QUESTIONS}\n"
        f"🟢 باقی‌مانده: {remaining}"
    )
