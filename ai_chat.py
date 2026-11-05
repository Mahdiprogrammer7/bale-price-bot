
import os
import asyncio
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# =========================================================
# تنظیمات OpenRouter
# =========================================================

API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

PRIMARY_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-20b:free"
).strip()

FALLBACK_MODEL = os.getenv(
    "OPENROUTER_FALLBACK_MODEL",
    "meta-llama/llama-3.3-70b-instruct:free"
).strip()

API_URL = "https://openrouter.ai/api/v1/chat/completions"

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

# =========================================================
# وضعیت اولیه
# =========================================================

if API_KEY:
    print(
        f"✅ OpenRouter client ready | model={PRIMARY_MODEL}",
        flush=True
    )
else:
    print("❌ OPENROUTER_API_KEY is missing!", flush=True)


# =========================================================
# کلاس هوش مصنوعی
# نام GeminiChat برای سازگاری main.py حفظ شده
# =========================================================

class GeminiChat:

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

        if special:
            return True, None

        today = GeminiChat.today_tehran()

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
    # ارسال درخواست به OpenRouter
    # -----------------------------------------------------

    @staticmethod
    def _request_openrouter(model, messages):

        if not API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is missing")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }

        body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://arz-online.onrender.com",
                "X-Title": "Arz Online"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=90
            ) as response:

                raw = response.read().decode("utf-8")
                data = json.loads(raw)

        except urllib.error.HTTPError as exc:

            error_body = exc.read().decode(
                "utf-8",
                errors="replace"
            )

            raise RuntimeError(
                f"OpenRouter HTTP {exc.code}: {error_body}"
            ) from exc

        except urllib.error.URLError as exc:

            raise RuntimeError(
                f"OpenRouter connection error: {exc}"
            ) from exc

        choices = data.get("choices", [])

        if not choices:
            raise RuntimeError(
                f"OpenRouter returned no choices: {data}"
            )

        message = choices[0].get("message", {})
        content = message.get("content")

        if isinstance(content, str):
            answer = content.strip()

        elif isinstance(content, list):
            answer = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            ).strip()

        else:
            answer = ""

        if not answer:
            raise RuntimeError(
                "OpenRouter returned an empty response"
            )

        return answer

    # -----------------------------------------------------
    # درخواست با Retry
    # -----------------------------------------------------

    @staticmethod
    async def _generate_with_retry(model, messages):

        delays = [2, 4, 8]
        last_error = None

        for attempt in range(4):

            try:

                answer = await asyncio.to_thread(
                    GeminiChat._request_openrouter,
                    model,
                    messages
                )

                return answer

            except Exception as exc:

                last_error = exc
                error_text = str(exc).lower()

                retryable = any(
                    item in error_text
                    for item in (
                        "429",
                        "500",
                        "502",
                        "503",
                        "504",
                        "timeout",
                        "temporarily",
                        "connection",
                        "rate limit"
                    )
                )

                if not retryable:
                    raise

                if attempt < 3:

                    delay = delays[attempt]

                    print(
                        f"⚠️ OpenRouter retry | model={model} "
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

        if not API_KEY:
            raise RuntimeError(
                "OpenRouter client is not initialized"
            )

        question = str(question).strip()

        if not question:
            return "لطفاً سؤال خود را وارد کنید."

        # تاریخچه کاربر
        history = GeminiChat._histories.get(chat_id, [])

        # تبدیل تاریخچه به فرمت OpenRouter
        messages = [
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION
            }
        ]

        messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": question
            }
        )

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

                print(
                    f"🤖 OpenRouter processing | "
                    f"model={model} | chat_id={chat_id}",
                    flush=True
                )

                answer = await GeminiChat._generate_with_retry(
                    model,
                    messages
                )

                used_model = model
                break

            except Exception as exc:

                last_error = exc

                print(
                    f"❌ OpenRouter request failed | "
                    f"model={model} | "
                    f"{type(exc).__name__}: {exc}",
                    flush=True
                )

        if not answer:
            raise RuntimeError(
                f"All OpenRouter models failed: {last_error}"
            )

        # ذخیره تاریخچه
        history.append(
            {
                "role": "user",
                "content": question
            }
        )

        history.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        # حداکثر 16 پیام
        GeminiChat._histories[chat_id] = history[-16:]

        print(
            f"✅ OpenRouter answer | "
            f"chat_id={chat_id} | model={used_model}",
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
# تابع سهمیه مورد نیاز main.py
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
