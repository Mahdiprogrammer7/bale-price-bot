"""Gemini chat integration for Arz Online."""
import os
import asyncio
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import types
from pymongo import ReturnDocument

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
        print(f"✅ Gemini client initialized | model={MODEL} | key_present=True", flush=True)
    except Exception as init_error:
        print(f"❌ Gemini client initialization failed: {type(init_error).__name__}: {init_error}", flush=True)
else:
    print("❌ GEMINI_API_KEY is empty/not available in environment", flush=True)
# گفتگو در حافظه اجرای فعلی نگه داشته می‌شود؛ سهمیه در MongoDB پایدار است.
_histories = {}
MAX_DAILY_QUESTIONS = 15
TEHRAN = timezone(timedelta(hours=3, minutes=30))

class GeminiChat:
    @staticmethod
    def day_key():
        return datetime.now(TEHRAN).strftime("%Y-%m-%d")

    @staticmethod
    async def reserve_question(collection, chat_id, special=False):
        if special:
            return True, None
        day = GeminiChat.day_key()
        key = {"chat_id": str(chat_id), "day": day}
        # Update pipeline ensures the counter cannot exceed 15 under concurrent messages.
        try:
            doc = await collection.find_one_and_update(
                {**key, "count": {"$lt": MAX_DAILY_QUESTIONS}},
                {"$inc": {"count": 1}, "$setOnInsert": {"created_at": datetime.now(TEHRAN).isoformat()}},
                upsert=False, return_document=ReturnDocument.AFTER
            )
            if doc:
                return True, max(0, MAX_DAILY_QUESTIONS - int(doc.get("count", 0)))
            existing = await collection.find_one(key)
            if existing:
                return False, 0
            try:
                await collection.insert_one({**key, "count": 1, "created_at": datetime.now(TEHRAN).isoformat()})
                return True, MAX_DAILY_QUESTIONS - 1
            except Exception:
                # Race on first insert: attempt a normal guarded increment.
                doc = await collection.find_one_and_update(
                    {**key, "count": {"$lt": MAX_DAILY_QUESTIONS}},
                    {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER
                )
                if doc:
                    return True, max(0, MAX_DAILY_QUESTIONS - int(doc.get("count", 0)))
                return False, 0
        except Exception as exc:
            raise RuntimeError("MongoDB AI quota error") from exc

    @staticmethod
    async def refund_question(collection, chat_id):
        """در صورت خطای Gemini، سؤال رزرو شده به سهمیه برگردد."""
        if collection is None:
            return
        key = {"chat_id": str(chat_id), "day": GeminiChat.day_key()}
        try:
            await collection.update_one(key, {"$inc": {"count": -1}})
            await collection.delete_one({**key, "count": {"$lte": 0}})
        except Exception as exc:
            print(f"⚠️ AI quota refund failed: {type(exc).__name__}: {exc}", flush=True)

    @staticmethod
    async def ask(chat_id, prompt):
        if not client:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        prompt = str(prompt).strip()
        if not prompt:
            return "لطفاً سؤال خود را بنویسید."
        history = _histories.setdefault(str(chat_id), [])
        contents = list(history) + [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction="تو دستیار فارسی‌زبان بات ارز آنلاین هستی. پاسخ‌ها دقیق، مفید و محترمانه باشند. درباره قیمت لحظه‌ای ادعا نکن مگر داده زنده در اختیار داشته باشی. اگر لازم است بگو اطلاعات بازار ممکن است به‌روز نباشد.",
                    temperature=0.7,
                    max_output_tokens=1200,
                ),
            )
        except Exception as exc:
            print(f"❌ Gemini API request failed | model={MODEL} | {type(exc).__name__}: {exc}", flush=True)
            raise
        answer = (response.text or "پاسخی دریافت نشد.").strip()
        history.extend([
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
            types.Content(role="model", parts=[types.Part.from_text(text=answer)]),
        ])
        # جلوگیری از رشد بی‌نهایت تاریخچه
        if len(history) > 16:
            del history[:-16]
        return answer

async def daily_usage_text(collection, chat_id, special=False):
    if special:
        return "♾️ سهمیه: نامحدود (کاربر خاص)"
    if collection is None:
        return "سهمیه: در دسترس نیست"
    doc = await collection.find_one({"chat_id": str(chat_id), "day": GeminiChat.day_key()})
    used = int((doc or {}).get("count", 0))
    return f"📊 سهمیه امروز: {max(0, MAX_DAILY_QUESTIONS-used)} از ۱۵ سؤال باقی مانده"
