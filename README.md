# Telegram AI-agent (shaxsiy akkaunt uchun)

Bu skript sizning shaxsiy Telegram akkauntingizga kirib, siz javob berolmagan
(yoki umuman ishlamagan) paytda kelgan shaxsiy xabarlarga Claude yordamida
avtomatik javob beradi. Til aniqlab (rus/ingliz/o'zbek), o'sha tilda javob yozadi.

⚠️ **Risk haqida eslatma**: Bu — shaxsiy akkauntni avtomatlashtirish (userbot).
Telegram bunday foydalanishni rasmiy tarzda qo'llab-quvvatlamaydi. Juda ko'p va
tez-tez xabar yuborilsa, akkaunt vaqtincha cheklanishi mumkin. Skriptda buni
kamaytirish uchun sun'iy kechikish va kunlik limit bor, lekin xavf butunlay
yo'q emas.

## 1. Kerakli ma'lumotlarni oling

1. **Telegram API_ID / API_HASH**: https://my.telegram.org saytiga kiring →
   "API development tools" → yangi ilova yarating → `api_id` va `api_hash`
   ni nusxalab oling.
2. **Anthropic API kaliti**: https://console.anthropic.com saytidan
   "API Keys" bo'limida yarating.
3. O'zingizning telefon raqamingiz (Telegram akkauntingiz bog'langan),
   xalqaro formatda: `+998901234567`

## 2. Kompyuterda/serverda tayyorlash

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install telethon anthropic langdetect
```

## 3. Muhit o'zgaruvchilarini o'rnatish

Linux/macOS:
```bash
export TG_API_ID="12345678"
export TG_API_HASH="sizning_api_hash"
export TG_PHONE="+998901234567"
export ANTHROPIC_API_KEY="sk-ant-..."
```

Windows (PowerShell):
```powershell
$env:TG_API_ID="12345678"
$env:TG_API_HASH="sizning_api_hash"
$env:TG_PHONE="+998901234567"
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

## 4. Birinchi marta ishga tushirish

```bash
python ai_agent.py
```

Birinchi ishga tushirishda Telegram sizga SMS/ilova orqali tasdiqlash kodi
yuboradi — uni terminalga kiriting. Shundan so'ng `my_userbot_session.session`
nomli fayl yaratiladi — bu sizning login sessiyangiz, uni hech kimga bermang
va git kabi joylarga yuklamang.

## 5. Boshqarish

O'zingizning "Saved Messages" (o'zimga xabar) chatiga quyidagi buyruqlarni
yozib, botni boshqarishingiz mumkin:
- `/ai off` — avtomatik javobni to'xtatish
- `/ai on` — qayta yoqish
- `/ai status` — joriy holat va bugungi javoblar sonini ko'rish

## 6. 24/7 ishlashi uchun (VPS'ga joylash)

Kompyuteringiz o'chirilsa, skript ham to'xtaydi. Doimiy ishlashi uchun arzon
VPS kerak (masalan, Contabo, Timeweb, DigitalOcean — oyiga taxminan 3-5$).

VPS'da (Ubuntu) `systemd` orqali doimiy xizmat qilib qo'yish:

```bash
sudo nano /etc/systemd/system/ai-agent.service
```

Fayl ichiga:
```ini
[Unit]
Description=Telegram AI Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/USERNAME/tg_ai_agent
Environment="TG_API_ID=12345678"
Environment="TG_API_HASH=sizning_api_hash"
Environment="TG_PHONE=+998901234567"
Environment="ANTHROPIC_API_KEY=sk-ant-..."
ExecStart=/home/USERNAME/tg_ai_agent/venv/bin/python ai_agent.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Keyin:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-agent
sudo systemctl start ai-agent
sudo systemctl status ai-agent   # ishlab turganini tekshirish
```

Shu bilan skript server qayta yuklansa ham avtomatik ishga tushadi va 24/7
ishlaydi.

## Sozlashingiz mumkin bo'lgan narsalar (`ai_agent.py` ichida)

- `OWNER_NAME` — javoblarda ishlatiladigan ismingiz
- `DISCLOSE_AI` — birinchi javobda "bu AI" deb ogohlantirish kerakmi
- `MAX_HISTORY_PER_CHAT` — har bir suhbat uchun eslab qolinadigan xabarlar soni
- `MIN_DELAY_SEC` / `MAX_DELAY_SEC` — javob berishdan oldingi kechikish
- `DAILY_REPLY_LIMIT` — kuniga eng ko'p necha marta avtomatik javob berish
- `SYSTEM_PROMPT_TEMPLATE` — AI qanday "xarakter"da javob berishini shu yerda
  o'zgartirishingiz mumkin
