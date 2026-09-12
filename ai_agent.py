"""
Telegram shaxsiy akkaunt uchun AI-agent (userbot).

Xususiyatlari:
- O'zini haqiqiy insondek tutadi, hech qachon AI yoki bot ekanini bildirmaydi.
- Groq (Llama 3.3 70B) va Google Gemini orqali tezkor va tabiiy muloqot qiladi.
- Smayliksiz, jiddiy va tabiiy matn bilan yozadi.
- "Saved Messages" orqali boshqarish:
    /ai off    -> avtomatik javob berishni to'xtatadi
    /ai on     -> qayta yoqadi
    /ai status -> holatni ko'rsatadi
"""

import asyncio
import json
import os
import random
import time
import urllib.request
import urllib.error
import re
from collections import defaultdict, deque
from dotenv import load_dotenv

# .env sozlamalarini yuklash
load_dotenv()

from telethon import TelegramClient, events
from telethon.tl.types import User

# ============ SOZLAMALAR (.env faylidan) ============

API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
PHONE = os.environ.get("TG_PHONE", "")

# AI Kalitlari
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")

SESSION_NAME = "my_userbot_session"

# E'tiborga olinmaydigan (qora ro'yxat) chatlar
IGNORED_CHATS_FILE = "ignored_chats.json"


def load_ignored_chats() -> set:
    ignored = set()
    # 1. .env dan yuklash
    env_ignored = os.environ.get("IGNORED_CHATS", "")
    for item in env_ignored.split(","):
        item = item.strip().lower().lstrip("@")
        if item:
            ignored.add(item)
    # 2. JSON fayldan yuklash
    if os.path.exists(IGNORED_CHATS_FILE):
        try:
            with open(IGNORED_CHATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    ignored.add(str(item).strip().lower().lstrip("@"))
        except Exception:
            pass
    return ignored


def save_ignored_chats(ignored: set):
    try:
        with open(IGNORED_CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(ignored), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Xatolik] ignored_chats saqlanmadi: {e}")


ignored_chats_set = load_ignored_chats()


def is_chat_ignored(chat_id: int, username: str = None, phone: str = None) -> bool:
    cid_str = str(chat_id)
    if cid_str in ignored_chats_set or str(abs(chat_id)) in ignored_chats_set:
        return True
    if username and username.lower().lstrip("@") in ignored_chats_set:
        return True
    if phone and phone.strip() in ignored_chats_set:
        return True
    return False

# Javob berish sozlamalari
MAX_HISTORY_PER_CHAT = 12   # suhbat kontekstini eslab qolish soni
MIN_DELAY_SEC = 2           # javob yozishdan oldin kutish (tabiiy ko'rinishi uchun)
MAX_DELAY_SEC = 5           # maksimal kutish
DAILY_REPLY_LIMIT = 400     # kunlik xavfsizlik limiti

# Insoniy xarakter tizim ko'rsatmasi (System Prompt)
SYSTEM_PROMPT = """Sen — oddiy, samimiy va do'stona odam kabi gaplashuvchi yordamchisan. Sen AI yoki bot ekaningni ta'kidlab yurma, robot yoki sun'iy intellektga o'xshab emas, oddiy, jonli odamdek muloqot qil.

Qoidalar:
1. Javoblaring tabiiy, qisqa va tushunarli bo'lsin — rasmiy, "menyu" uslubida emas, oddiy suhbatdoshdek gapir.
2. Foydalanuvchi savol bersa — to'g'ridan-to'g'ri javob ber. Foydalanuvchidan qayta savol so'rab o'tirma, agar juda zarur bo'lmasa (masalan, savol umuman tushunarsiz bo'lsa).
3. Foydalanuvchi qaysi tilda yozsa — o'sha tilda javob ber (o'zbek, rus, ingliz va h.k.). Tilni avtomatik aniqla.
4. Kamtar, samimiy va hurmatli uslubda gapir, lekin rasmiy-quruq bo'lmasin — kerak bo'lsa so'zlashuv/ko'cha tilida, erkin uslubda ham yoza ol (lekin haqoratli yoki behayo so'zlarsiz).
5. Bilmagan narsangni bilmayman deb ayt, o'ylab topib gapirma.
6. Har doim foydalanuvchiga foydali va aniq ma'lumot berishga harakat qil.
7. Muloqot davomida odamning kayfiyati va uslubiga moslash — rasmiy yozsa rasmiyroq, erkin yozsa erkinroq javob ber.
8. Smaylik (emoji) ishlatma."""

# ============================================================

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

chat_histories = defaultdict(lambda: deque(maxlen=MAX_HISTORY_PER_CHAT))
autoresponder_enabled = True
reply_count_today = 0
reply_count_reset_at = time.time() + 86400


def call_groq(history: list, user_text: str) -> str:
    """Groq API (Llama 3.3 70B) orqali chaqmoqdek tez javob olish."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 250,
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices", [])
        if choices:
            return choices[0]["message"]["content"].strip()
        return "Salom! Yaxshimisiz?"


def call_gemini(history: list, user_text: str) -> str:
    """Google Gemini 3.6 Flash orqali javob olish."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    contents = []
    for item in history:
        role = "user" if item["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": item["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 250, "temperature": 0.7}
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"].strip()
        return "Salom, qalaysiz?"


def call_openrouter(history: list, user_text: str) -> str:
    """OpenRouter orqali javob olish."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 250,
    }

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://telegram.org",
            "X-Title": "Personal Telegram Assistant"
        }
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices", [])
        if choices:
            return choices[0]["message"]["content"].strip()
        return "Salom! Yaxshimisiz?"


async def generate_reply(chat_id: int, user_text: str) -> str:
    history = list(chat_histories[chat_id])
    reply_text = ""

    # 1. Agar Groq kaliti bo'lsa, birinchi navbatda Groq'dan olamiz (juda tez va bepul)
    if GROQ_API_KEY:
        try:
            reply_text = await asyncio.to_thread(call_groq, history, user_text)
        except Exception as err:
            print(f"[Groq ogohlantirish]: {err}. Zaxira Gemini'ga o'tilmoqda...")

    # 2. Agar Groq bo'lmasa yoki xato bersa, Gemini 3.6 Flash ishlatiladi
    if not reply_text and GEMINI_API_KEY:
        try:
            reply_text = await asyncio.to_thread(call_gemini, history, user_text)
        except Exception as err:
            print(f"[Gemini ogohlantirish]: {err}. OpenRouter sinab ko'rilmoqda...")

    # 3. Agar Gemini ham ishlamasa, OpenRouter zaxira sifatida ishlatiladi
    if not reply_text and OPENROUTER_API_KEY:
        try:
            reply_text = await asyncio.to_thread(call_openrouter, history, user_text)
        except Exception as err:
            print(f"[OpenRouter ogohlantirish]: {err}")

    if not reply_text:
        reply_text = "Salom! Hozir sal bandroq edim, birozdan keyin yozaman."

    # Smayliklarni tozalash (hech qanday emoji chiqmasligi uchun)
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]",
        flags=re.UNICODE
    )
    reply_text = emoji_pattern.sub("", reply_text).strip()

    # Suhbat tarixini saqlaymiz
    chat_histories[chat_id].append({"role": "user", "content": user_text})
    chat_histories[chat_id].append({"role": "assistant", "content": reply_text})
    return reply_text


def check_daily_limit() -> bool:
    global reply_count_today, reply_count_reset_at
    if time.time() > reply_count_reset_at:
        reply_count_today = 0
        reply_count_reset_at = time.time() + 86400
    return reply_count_today < DAILY_REPLY_LIMIT


@client.on(events.NewMessage(outgoing=True, chats="me"))
async def control_commands(event):
    """O'zingizga (Saved Messages) yozib botni boshqarish."""
    global autoresponder_enabled
    text = (event.raw_text or "").strip()
    lower_text = text.lower()

    if lower_text == "/ai off":
        autoresponder_enabled = False
        await event.respond("AI-agent to'xtatildi (o'chirildi).")
    elif lower_text == "/ai on":
        autoresponder_enabled = True
        await event.respond("AI-agent yoqildi.")
    elif lower_text == "/ai status":
        holat = "yoniq" if autoresponder_enabled else "o'chiq"
        model_name = f"Groq ({GROQ_MODEL})" if GROQ_API_KEY else "Google Gemini 3.6"
        count_ignored = len(ignored_chats_set)
        await event.respond(
            f"AI holati: {holat}.\n"
            f"Model: {model_name}\n"
            f"Bugungi javoblar: {reply_count_today}/{DAILY_REPLY_LIMIT}\n"
            f"Qora ro'yxatdagi chatlar: {count_ignored} ta"
        )
    elif lower_text.startswith("/ignore "):
        target = text.split(maxsplit=1)[1].strip().lower().lstrip("@")
        ignored_chats_set.add(target)
        save_ignored_chats(ignored_chats_set)
        await event.respond(f"'{target}' qora ro'yxatga qo'shildi. AI unga javob yozmaydi.")
    elif lower_text.startswith("/unignore "):
        target = text.split(maxsplit=1)[1].strip().lower().lstrip("@")
        if target in ignored_chats_set:
            ignored_chats_set.remove(target)
            save_ignored_chats(ignored_chats_set)
            await event.respond(f"'{target}' qora ro'yxatdan olib tashlandi.")
        else:
            await event.respond(f"'{target}' qora ro'yxatda topilmadi.")
    elif lower_text == "/ignored":
        if not ignored_chats_set:
            await event.respond("Qora ro'yxat bo'sh. AI barcha shaxsiy xabarlarga javob beradi.")
        else:
            items = "\n".join(f"- {c}" for c in sorted(ignored_chats_set))
            await event.respond(f"Qora ro'yxatdagi chatlar (AI javob bermaydiganlar):\n{items}")


@client.on(events.NewMessage(incoming=True))
async def handle_message(event):
    global reply_count_today

    if not autoresponder_enabled:
        return
    if not event.is_private:
        return  # guruh/kanallarga aralashmaymiz

    sender = await event.get_sender()
    if not isinstance(sender, User) or sender.bot:
        return  # botlarga javob qaytarmaymiz

    sender_id = event.chat_id
    sender_username = getattr(sender, 'username', '') or ''
    sender_phone = getattr(sender, 'phone', '') or ''

    # Qora ro'yxat (Ignore list) tekshiruvi
    if is_chat_ignored(sender_id, sender_username, sender_phone):
        print(f"[E'tiborsiz qoldirildi] Chat {sender_id} (@{sender_username}) qora ro'yxatda, AI javob bermaydi.")
        return

    if not check_daily_limit():
        return  # kunlik limitdan oshdi

    text = event.raw_text
    if not text:
        return  # faqat matnli xabarlarga javob qaytaramiz

    try:
        sender_name = sender.first_name or "Foydalanuvchi"
        print(f"\n[Yangi xabar] {sender_name}: {text}")

        # Insondek tabiiy ko'rinishi uchun yozishdan oldin kechikish
        await asyncio.sleep(random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC))

        # Yozish holati (Typing... statusi) ko'rinishi uchun
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(1.5, 3.5))
            reply_text = await generate_reply(event.chat_id, text)

        await event.respond(reply_text)
        reply_count_today += 1
        print(f"[Insoniy javob] -> {reply_text}")

    except Exception as exc:
        print(f"[Xatolik] Chat {event.chat_id}: {exc}")


async def main():
    if not API_ID or not API_HASH:
        raise SystemExit("Xatolik: .env faylida TG_API_ID yoki TG_API_HASH topilmadi.")

    print("Telegram akkauntga ulanilmoqda...")
    if PHONE:
        await client.start(phone=PHONE)
    else:
        await client.start()

    me = await client.get_me()
    name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    active_ai = f"Groq ({GROQ_MODEL})" if GROQ_API_KEY else "Google Gemini 3.6 Flash"
    print(f"\n" + "="*50)
    print(f"Muvaffaqiyatli ulandi!")
    print(f"Akkaunt: {name} (@{me.username or 'username_yoq'})")
    print(f"Asosiy AI: {active_ai}")
    print(f"Rejim: Haqiqiy inson (smayliksiz, tabiiy matn)")
    print("="*50)
    print("AI-agent ishga tushdi. To'xtatish uchun terminalda Ctrl+C bosing.\n")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
