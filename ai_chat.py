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
FALLBACK_MODELS = [x.strip() for x in os.getenv(
    "OPENROUTER_FALLBACK_MODELS",
    "meta-llama/llama-3.3-70b-instruct:free,deepseek/deepseek-r1-0528:free"
).split(",") if x.strip()]
VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL", "nvidia/nemotron-3.5-super-vl:free").strip()
VISION_FALLBACK_MODELS = [x.strip() for x in os.getenv(
    "OPENROUTER_VISION_FALLBACK_MODELS",
    "qwen/qwen2.5-vl-32b-instruct:free,google/gemma-4-31b-it:free"
).split(",") if x.strip()]
MAX_DAILY_QUESTIONS = int(os.getenv("AI_DAILY_LIMIT", "15"))
MAX_HISTORY_MESSAGES = int(os.getenv("AI_HISTORY_MESSAGES", "12"))
MAX_HISTORY_CHARS = 10000
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
logging.basicConfig(level=logging.INFO)


class AIRequestError(Exception):
    """All configured AI models failed or returned invalid output."""


class GeminiChat:
    # History is shared across model fallbacks and stored in process memory.
    _histories = {}
    # Keep the latest image per chat temporarily so follow-up questions can refer to it.
    _last_images = {}

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
    def _extract_text(data):
        """Extract text safely from OpenRouter response formats."""
        choices = data.get("choices") or []
        if not choices:
            raise AIRequestError(f"پاسخ مدل فاقد choices است: {str(data)[:500]}")
        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    # Ignore image blocks; collect all textual blocks.
                    val = item.get("text") or item.get("content")
                    if isinstance(val, str) and val.strip():
                        parts.append(val.strip())
            text = "\\n".join(parts).strip()
        else:
            text = ""

        # Some reasoning models may return reasoning separately.
        if not text:
            reasoning = message.get("reasoning")
            if isinstance(reasoning, str) and reasoning.strip():
                text = reasoning.strip()

        if not text:
            finish = choices[0].get("finish_reason")
            raise AIRequestError(
                f"مدل پاسخ متنی خالی برگرداند (finish_reason={finish}). "
                f"message={json.dumps(message, ensure_ascii=False)[:700]}"
            )
        if text.lower() in {"none", "null"}:
            raise AIRequestError("مدل مقدار None/null برگرداند؛ پاسخ معتبر نیست")
        return text

    @classmethod
    def _request_openrouter(cls, model, messages):
        if not API_KEY:
            raise AIRequestError("OPENROUTER_API_KEY تنظیم نشده است")
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1500,
        }
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://render.com",
                "X-Title": "Arz Online",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise AIRequestError(f"HTTP {exc.code}: {body[:700]}") from exc
        except Exception as exc:
            raise AIRequestError(f"{type(exc).__name__}: {exc}") from exc

        if data.get("error"):
            raise AIRequestError(f"OpenRouter error: {str(data['error'])[:700]}")
        return cls._extract_text(data)

    @classmethod
    async def _generate(cls, messages, vision=False):
        models = ([VISION_MODEL, *VISION_FALLBACK_MODELS] if vision
                  else [PRIMARY_MODEL, *FALLBACK_MODELS])
        models = list(dict.fromkeys(x for x in models if x))
        errors = []
        for model in models:
            try:
                logging.info("OpenRouter trying model=%s vision=%s", model, vision)
                result = await asyncio.to_thread(cls._request_openrouter, model, messages)
                if not isinstance(result, str) or not result.strip():
                    raise AIRequestError("خروجی مدل خالی یا غیرمتنی است")
                logging.info("OpenRouter success model=%s vision=%s chars=%s", model, vision, len(result))
                return result.strip()
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
        history.extend([
            {"role": "user", "content": str(question)},
            {"role": "assistant", "content": str(answer)},
        ])
        history[:] = history[-MAX_HISTORY_MESSAGES:]
        while history and sum(len(str(x.get("content", ""))) for x in history) > MAX_HISTORY_CHARS:
            history.pop(0)

    @classmethod
    def clear_history(cls, chat_id):
        cls._histories.pop(str(chat_id), None)
        cls._last_images.pop(str(chat_id), None)

    @classmethod
    async def ask(cls, chat_id, question):
        question = str(question or "").strip()
        if not question:
            raise AIRequestError("سؤال خالی است")
        # If user asks a follow-up about the latest image, attach that image again.
        last_image = cls._last_images.get(str(chat_id))
        if last_image and any(term in question.lower() for term in (
            "این عکس", "این تصویر", "همین عکس", "همین تصویر", "عکس بالا",
            "تصویر بالا", "گزینه", "سوال تصویر", "سؤال تصویر"
        )):
            encoded, mime = last_image
            content = [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
            ]
            messages = [{"role": "system", "content": cls.system_prompt()},
                       *cls._history(chat_id), {"role": "user", "content": content}]
            answer = await cls._generate(messages, vision=True)
        else:
            messages = [{"role": "system", "content": cls.system_prompt()},
                       *cls._history(chat_id), {"role": "user", "content": question}]
            answer = await cls._generate(messages, vision=False)
        cls._save_history(chat_id, question, answer)
        return answer

    @classmethod
    async def ask_image(cls, chat_id, image_bytes, question="این تصویر را تحلیل کن.", mime_type="image/jpeg"):
        if not image_bytes:
            raise AIRequestError("تصویر دریافت نشد")
        question = str(question or "این تصویر را تحلیل کن.").strip()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        cls._last_images[str(chat_id)] = (encoded, mime_type or "image/jpeg")
        messages = [
            {"role": "system", "content": cls.system_prompt()},
            *cls._history(chat_id),
            {"role": "user", "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type or 'image/jpeg'};base64,{encoded}"}},
            ]},
        ]
        answer = await cls._generate(messages, vision=True)
        cls._save_history(chat_id, question, answer)
        return answer

    @staticmethod
    def day_key():
        return GeminiChat.today_tehran()

    @classmethod
    async def reserve_question(cls, collection, chat_id, special=False):
        if special:
            return True, None
        day = cls.today_tehran()
        key = {"chat_id": str(chat_id), "day": day}
        try:
            doc = await collection.find_one_and_update(
                {**key, "count": {"$lt": MAX_DAILY_QUESTIONS}},
                {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER
            )
            if doc:
                return True, max(0, MAX_DAILY_QUESTIONS - int(doc.get("count", 0)))
            existing = await collection.find_one(key)
            if existing:
                return False, 0
            try:
                await collection.insert_one({
                    **key, "count": 1,
                    "created_at": datetime.now(TEHRAN_TZ).isoformat()
                })
                return True, MAX_DAILY_QUESTIONS - 1
            except Exception:
                doc = await collection.find_one_and_update(
                    {**key, "count": {"$lt": MAX_DAILY_QUESTIONS}},
                    {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER
                )
                if doc:
                    return True, max(0, MAX_DAILY_QUESTIONS - int(doc.get("count", 0)))
                return False, 0
        except Exception as exc:
            raise RuntimeError("MongoDB AI quota error") from exc

    @classmethod
    async def refund_question(cls, collection, chat_id):
        if collection is None:
            return
        key = {"chat_id": str(chat_id), "day": cls.today_tehran()}
        await collection.update_one(key, {"$inc": {"count": -1}})
        await collection.delete_one({**key, "count": {"$lte": 0}})

    @classmethod
    async def get_usage(cls, collection, chat_id):
        doc = await collection.find_one({"chat_id": str(chat_id), "day": cls.today_tehran()})
        return int(doc.get("count", 0)) if doc else 0


async def daily_usage_text(collection, chat_id, special=False):
    if special:
        return "♾️ سهمیه نامحدود کاربر خاص"
    used = await GeminiChat.get_usage(collection, chat_id)
    return f"📊 مصرف امروز: {used}/{MAX_DAILY_QUESTIONS}\\n🟢 باقی‌مانده: {max(0, MAX_DAILY_QUESTIONS-used)}"
