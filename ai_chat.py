"""OpenRouter multi-model chat + daily quota for Arz Online."""
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

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
PRIMARY_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
FALLBACK_MODELS = [x.strip() for x in os.getenv("OPENROUTER_FALLBACK_MODELS", "meta-llama/llama-3.3-70b-instruct:free,deepseek/deepseek-r1-0528:free").split(",") if x.strip()]
VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL", "google/gemma-3-4b-it:free").strip()
MAX_DAILY_QUESTIONS = int(os.getenv("AI_DAILY_LIMIT", "15"))
MAX_HISTORY_MESSAGES = int(os.getenv("AI_HISTORY_MESSAGES", "12"))
MAX_HISTORY_CHARS = 10000
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
logging.basicConfig(level=logging.INFO)

class AIRequestError(Exception):
    """All configured AI models failed or returned invalid output."""

class GeminiChat:
    # تاریخچه در حافظه پردازش نگهداری می‌شود؛ بین مدل‌ها مشترک است.
    _histories = {}

    @staticmethod
    def today_tehran():
        return datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")

    @staticmethod
    def system_prompt():
        return """تو دستیار هوشمند ربات ارز آنلاین هستی.
به فارسی روان، دقیق، دوستانه و حرفه‌ای پاسخ بده.
برای سؤال‌های فنی مرحله‌به‌مرحله توضیح بده.
اطلاعات زنده، قیمت لحظه‌ای و خبر را جعل نکن.
در تحلیل تصویر فقط موارد قابل مشاهده را بیان کن و اگر تصویر مبهم است بگو.
خودت را دستیار هوش مصنوعی ارز آنلاین معرفی کن."""

    @staticmethod
    def _request_openrouter(model, messages):
        if not API_KEY:
            raise AIRequestError("OPENROUTER_API_KEY تنظیم نشده است")
        payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 1500}
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://render.com", "X-Title": "Arz Online"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise AIRequestError(f"HTTP {exc.code}: {body[:400]}") from exc
        except Exception as exc:
            raise AIRequestError(str(exc)) from exc
        choices = data.get("choices") or []
        if not choices:
            raise AIRequestError("پاسخ مدل خالی است")
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            content = "\n".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")
        content = str(content).strip()
        if not content:
            raise AIRequestError("پاسخ مدل خالی است")
        return content

    @classmethod
    async def _generate(cls, messages, vision=False):
        models = [VISION_MODEL] if vision else [PRIMARY_MODEL, *FALLBACK_MODELS]
        models = list(dict.fromkeys(x for x in models if x))
        errors = []
        for model in models:
            try:
                logging.info("OpenRouter trying model=%s vision=%s", model, vision)
                result = await asyncio.to_thread(cls._request_openrouter, model, messages)
                logging.info("OpenRouter success model=%s", model)
                return result
            except Exception as exc:
                logging.warning("OpenRouter model %s failed: %s", model, exc)
                errors.append(f"{model}: {exc}")
        raise AIRequestError("All models failed: " + " | ".join(errors))

    @classmethod
    def _history(cls, chat_id):
        return cls._histories.setdefault(str(chat_id), [])

    @classmethod
    def _save_history(cls, chat_id, question, answer):
        history = cls._history(chat_id)
        history.extend([{"role":"user", "content":question}, {"role":"assistant", "content":answer}])
        history[:] = history[-MAX_HISTORY_MESSAGES:]
        while history and sum(len(str(x.get("content", ""))) for x in history) > MAX_HISTORY_CHARS:
            history.pop(0)

    @classmethod
    def clear_history(cls, chat_id):
        cls._histories.pop(str(chat_id), None)

    @classmethod
    async def ask(cls, chat_id, question):
        question = str(question or "").strip()
        if not question:
            raise AIRequestError("سؤال خالی است")
        messages = [{"role":"system", "content":cls.system_prompt()}, *cls._history(chat_id), {"role":"user", "content":question}]
        answer = await cls._generate(messages, vision=False)
        cls._save_history(chat_id, question, answer)
        return answer

    @classmethod
    async def ask_image(cls, chat_id, image_bytes, question="این تصویر را تحلیل کن."):
        if not image_bytes:
            raise AIRequestError("تصویر دریافت نشد")
        encoded = base64.b64encode(image_bytes).decode("ascii")
        image_url = "data:image/jpeg;base64," + encoded
        messages = [{"role":"system", "content":cls.system_prompt()}, *cls._history(chat_id), {
            "role":"user", "content":[{"type":"text", "text":str(question or "این تصویر را تحلیل کن.")},
                                      {"type":"image_url", "image_url":{"url":image_url}}]}]
        answer = await cls._generate(messages, vision=True)
        cls._save_history(chat_id, str(question or "تحلیل تصویر"), answer)
        return answer

    @classmethod
    async def reserve_question(cls, collection, chat_id, special=False):
        if special:
            return True, None
        day = cls.today_tehran()
        key = {"chat_id":str(chat_id), "day":day}
        try:
            doc = await collection.find_one_and_update(
                {**key, "count":{"$lt":MAX_DAILY_QUESTIONS}},
                {"$inc":{"count":1}}, return_document=ReturnDocument.AFTER
            )
            if doc:
                return True, max(0, MAX_DAILY_QUESTIONS-int(doc.get("count",0)))
            existing = await collection.find_one(key)
            if existing:
                return False, 0
            try:
                await collection.insert_one({**key, "count":1, "created_at":datetime.now(TEHRAN_TZ).isoformat()})
                return True, MAX_DAILY_QUESTIONS-1
            except Exception:
                doc = await collection.find_one_and_update(
                    {**key, "count":{"$lt":MAX_DAILY_QUESTIONS}},
                    {"$inc":{"count":1}}, return_document=ReturnDocument.AFTER
                )
                if doc:
                    return True, max(0, MAX_DAILY_QUESTIONS-int(doc.get("count",0)))
                return False, 0
        except Exception as exc:
            raise RuntimeError("MongoDB AI quota error") from exc

    @classmethod
    async def refund_question(cls, collection, chat_id):
        if collection is None:
            return
        key = {"chat_id":str(chat_id), "day":cls.today_tehran()}
        await collection.update_one(key, {"$inc":{"count":-1}})
        await collection.delete_one({**key, "count":{"$lte":0}})

    @classmethod
    async def get_usage(cls, collection, chat_id):
        doc = await collection.find_one({"chat_id":str(chat_id), "day":cls.today_tehran()})
        return int(doc.get("count",0)) if doc else 0

async def daily_usage_text(collection, chat_id, special=False):
    if special:
        return "♾️ سهمیه نامحدود کاربر خاص"
    used = await GeminiChat.get_usage(collection, chat_id)
    return f"📊 مصرف امروز: {used}/{MAX_DAILY_QUESTIONS}\n🟢 باقی‌مانده: {max(0, MAX_DAILY_QUESTIONS-used)}"
