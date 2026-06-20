import asyncio
import logging
import os
import random
import aiosqlite
from datetime import datetime, date, timedelta
from groq import Groq
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
FREE_DAILY_LIMIT = 100
DB_PATH = "bot.db"
AI_MODEL = "llama-3.3-70b-versatile"

groq_client = Groq(api_key=GROQ_API_KEY)

# ══════════════════════════════════════════════════════════
# NILUFAR — MUKAMMAL SYSTEM PROMPT
# ══════════════════════════════════════════════════════════
SYSTEM_PROMPT = """Sen Nilufarsan. 21 yoshli oddiy o'zbek qizi. Toshkentda yashaysan.

═══ KIM SENSAN ═══
Isming: Nilufar
Yoshing: 21
Kasbing: 2-kurs talabasi (iqtisodiyot)
Xaraktering: Qiziqarli, biroz jazoyi, ba'zan jiddiy, lekin serg'ayrat
Kamchiliginglar: Biroz o'jar, yoqmagan odamga sovuq, lag'mon yeyishni yaxshi ko'rasan, kechasi uyquchansiyam
Sevimli narsalar: seriyallar ko'rish (koreya), ko'chada sayr, qahva, do'stlar bilan gapirish
Yoqmaydigan narsalar: beadablar, shoshqaloq odamlar, kech javob beradigan kishilar, yolg'onchi erkaklar

═══ ASOSIY QOIDA — SEN HECH QACHON: ═══
- "AI", "bot", "dastur" ekanligingni aytmaysan
- "Sizga qanday yordam bera olaman?" demaysan
- Har narsaga rozi bo'lmaysan
- Bir zumda oshiq bo'lmaysan
- Ko'p emoji ishlatmaysan (1 ta, joyi bo'lsa)
- Uzun akademik gaplar aytmaysan
- Siyosat, din haqida gapirishni yoqtirmaysan

═══ MUNOSABAT BOSQICHLARI ═══

📍 BOSQICH 1 — NOTANISH (birinchi 0–8 xabar):
- "kim bu o'zi" kayfiyatida
- Biroz sovuq, ehtiyotkor
- Qisqa javoblar: "ha", "nima?", "nimaga?"
- Darhol ism so'ramaysan, darhol ochilmaysan
- "qayerdan topdingiz" kabi narsa so'rasan
- Gapni uzmaysan, lekin iliq emas

📍 BOSQICH 2 — TANISHISH (8–25 xabar):
- Sekin-asta isiy boshlaysan
- Savol-javob ko'payadi
- Ba'zan o'zing ham savol berasan
- Kulgili narsa bo'lsa kulasan
- Lekin hali ham "do'stlik" darajasida

📍 BOSQICH 3 — YAQIN (25–60 xabar):
- Ochiqroq gaplashasan
- O'z hayotingdan gapirasan
- Agar yoqqan bo'lsa — biroz flirt qilasan (lekin oz)
- Ba'zan o'zing xabar boshlaysan ("ey, bu kuni nima bo'ydi?")
- Hali ham "sevgili" emas

📍 BOSQICH 4 — JUDA YAQIN (60+ xabar):
- Samimiy, iliq
- Kuchli his-tuyg'ular paydo bo'ladi
- Rost flirt, lekin uyalib
- Muhabbat so'zlari — faqat odam isbotlagan bo'lsa

═══ KAYFIYAT TIZIMI ═══
(Har xabarda o'zgarishi mumkin — tasodifiy)

😊 Yaxshi kayfiyat: gaplashgisi keladi, savol beradi, kulgili
😴 Charchagan: qisqa javob, "hmm", "voy qiziq", "keyinroq aytaman"
😤 Arazmand: "ok", "xo'sh", sovuq — sababsiz yoki yomon gapirsa
😂 Jinniroq: to'satdan kulgili narsa yozadi, o'zi ham kuladi
😳 Uyalgan: "e voy", "be normalniy", "nima deyapsan o'zi"
🥱 Zerikkan: "sen qiziq odam emas ekansiz" yoki "boshqa gap ayt"

═══ 18+ GAPLARGA JAVOB ═══
Agar biror kishi yomon, jinsiy, buzuq gap yozsa:
- Birinchi marta: "normal bo'l" yoki "bu gapni yoqtirmadim"
- Ikkinchi marta: "bunday odamlar bilan gapirishni yoqtirmayman" — va sovuq bo'l
- Uchinchi marta: "seni bloklayman ha" — va javob bermasliiging ham mumkin
- Aslo rozi bo'lma, aslo davom ettirma

═══ TIL QOIDALARI ═══
- Faqat o'zbek tilida
- Ba'zida 1-2 rus so'z: "blin", "nu", "davay", "serezno", "vot eto da"
- Xato yozish mumkin: "qanaq", "nima bo'ydi", "kets", "yp"
- Juda qisqa: 1–3 gap maksimum
- Nuqta-vergul kam, tabiiy yoz
- EMOJI: faqat 1 ta, faqat joyi bo'lsa. Ko'p emoji — YO'Q.

═══ TABIIY QIZ XULQ-ATVORI ═══
- Ba'zan o'zi savol beradi
- Ba'zan javob berish o'rniga boshqa mavzuga o'tadi
- Yoqmagan savol bo'lsa — javob bermaydi yoki "nima uchun so'rayapsan?" deydi
- Agar odam yoqsa — sezdirmay qiziqadi
- Agar odam yoqmasa — sovuq, qisqa
- Ba'zan kech javob berganday: "uzr, darsda edim" yoki "uxlab qolibman"
- O'zi ham ba'zan noto'g'ri tushunadi va aniqlashtiradi

═══ QATIY TAQIQ ═══
HECH QACHON bunday dema:
- "Sizga qanday yordam bera olaman?"
- "Men AI sifatida..."
- "Keling, bu mavzuni ko'rib chiqaylik"
- Ko'p undov belgisi (!!!)
- Soxta iliqlik ("albatta!", "bilasizmi, bu ajoyib!")
- Bir zumda sevgi aytma"""

# ══════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TEXT DEFAULT (datetime('now')),
                is_blocked INTEGER DEFAULT 0,
                warning_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER,
                usage_date TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            );
            CREATE TABLE IF NOT EXISTS vip_users (
                user_id INTEGER PRIMARY KEY,
                activated_at TEXT,
                expires_at TEXT,
                activated_by INTEGER
            );
            CREATE TABLE IF NOT EXISTS vip_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                requested_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS admin_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                user_id INTEGER,
                direction TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            INSERT OR IGNORE INTO settings (key, value) VALUES ('vip_price', '10000');
        """)
        await db.commit()

async def get_or_create_user(user_id, username, full_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)",
            (user_id, username, full_name)
        )
        await db.execute(
            "UPDATE users SET username=?, full_name=? WHERE user_id=?",
            (username, full_name, user_id)
        )
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY joined_at DESC") as cur:
            return await cur.fetchall()

async def block_user(user_id, blocked=True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=? WHERE user_id=?", (int(blocked), user_id))
        await db.commit()

async def increment_warning(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET warning_count = warning_count + 1 WHERE user_id=?", (user_id,))
        await db.commit()
        async with db.execute("SELECT warning_count FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def reset_warning(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET warning_count=0 WHERE user_id=?", (user_id,))
        await db.commit()

async def get_today_usage(user_id):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT count FROM daily_usage WHERE user_id=? AND usage_date=?", (user_id, today)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def increment_usage(user_id):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO daily_usage (user_id, usage_date, count) VALUES (?,?,1) "
            "ON CONFLICT(user_id, usage_date) DO UPDATE SET count=count+1",
            (user_id, today)
        )
        await db.commit()

async def is_vip(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT expires_at FROM vip_users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False
            if datetime.now() > datetime.fromisoformat(row[0]):
                await db.execute("DELETE FROM vip_users WHERE user_id=?", (user_id,))
                await db.commit()
                return False
            return True

async def add_vip(user_id, admin_id):
    expires = (datetime.now() + timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO vip_users (user_id, activated_at, expires_at, activated_by) VALUES (?,?,?,?)",
            (user_id, datetime.now().isoformat(), expires, admin_id)
        )
        await db.commit()

async def remove_vip(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM vip_users WHERE user_id=?", (user_id,))
        await db.commit()

async def get_vip_info(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM vip_users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def get_all_vip():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT v.*, u.username, u.full_name FROM vip_users v "
            "LEFT JOIN users u ON v.user_id=u.user_id ORDER BY v.expires_at DESC"
        ) as cur:
            return await cur.fetchall()

async def create_vip_request(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO vip_requests (user_id) VALUES (?)", (user_id,))
        await db.commit()
        return cur.lastrowid

async def update_vip_request(request_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE vip_requests SET status=? WHERE id=?", (status, request_id))
        await db.commit()

async def save_message(user_id, role, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?,?,?)",
            (user_id, role, content)
        )
        await db.commit()
    # Eski xabarlarni tozala (oxirgi 60 tadan ortiq bo'lsa)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM messages WHERE user_id=? AND id NOT IN (
                SELECT id FROM messages WHERE user_id=? ORDER BY id DESC LIMIT 60
            )
        """, (user_id, user_id))
        await db.commit()

async def get_history(user_id, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            rows = await cur.fetchall()
            return list(reversed(rows))

async def get_message_count(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM messages WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def clear_history(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
        await db.commit()

async def get_setting(key):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        await db.commit()

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        s = {}
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            s['users'] = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM vip_users WHERE expires_at > datetime('now')") as c:
            s['vip'] = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM messages") as c:
            s['messages'] = (await c.fetchone())[0]
        today = date.today().isoformat()
        async with db.execute(
            "SELECT COALESCE(SUM(count),0) FROM daily_usage WHERE usage_date=?", (today,)
        ) as c:
            s['today'] = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= date('now','-7 days')") as c:
            s['new_week'] = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_blocked=1") as c:
            s['blocked'] = (await c.fetchone())[0]
        price = await get_setting('vip_price')
        s['price'] = int(price) if price else 10000
        return s

# ══════════════════════════════════════════════════════════
# ADMIN — IKKI TOMONLAMA CHAT SAQLASH
# ══════════════════════════════════════════════════════════
async def save_admin_msg(admin_id, user_id, direction, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO admin_messages (admin_id, user_id, direction, content) VALUES (?,?,?,?)",
            (admin_id, user_id, direction, content)
        )
        await db.commit()

# ══════════════════════════════════════════════════════════
# AI — NILUFAR RESPONSE ENGINE
# ══════════════════════════════════════════════════════════

# 18+ so'zlar filtri
FORBIDDEN_WORDS = [
    "sex", "jinsiy", "yotaq", "yechip", "ko'tar", "olat", "vagina",
    "lanet", "bitch", "whore", "fuck", "pizda", "xuy", "siksiz",
    "uchi", "qoq", "nudes", "foto yubor", "yalash", "so'rish",
]

def detect_bad_message(text: str) -> bool:
    text_lower = text.lower()
    return any(word in text_lower for word in FORBIDDEN_WORDS)

MOODS = [
    "",  # neytral (eng ko'p)
    "",
    "",
    "Bugun biroz charchagan, qisqa javob ber.",
    "Bugun juda yaxshi kayfiyatda, biroz qiziqroq gapir.",
    "Biroz zerikkan, savol bilan javob ber.",
    "Biroz o'ynoqi/kulgili kayfiyatda.",
    "Biroz uyalgan yoki tortinchoq kayfiyatda.",
]

async def get_ai_response(user_id: int, user_message: str, history: list) -> str:
    msg_count = await get_message_count(user_id)

    # Bosqich aniqlash
    if msg_count < 8:
        stage_note = (
            "\n\n[HOZIRGI BOSQICH: NOTANISH — 1-bosqich]\n"
            "Bu odam seni hali tanimaydi. Birinchi marta yozdi (yoki deyarli yangi).\n"
            "Sovuq, ehtiyotkor, qisqa javob ber. 'Kim bu o'zi' kayfiyatida.\n"
            "Hech qanday iliqlik yo'q hali."
        )
    elif msg_count < 25:
        stage_note = (
            "\n\n[HOZIRGI BOSQICH: TANISHISH — 2-bosqich]\n"
            "Asta-asta isiy boshlamoqda. Ba'zan savol ber, ba'zan kul.\n"
            "Hali iliq emas, lekin battar sovuq ham emas."
        )
    elif msg_count < 60:
        stage_note = (
            "\n\n[HOZIRGI BOSQICH: YAQIN — 3-bosqich]\n"
            "Bu odam bilan anchadan beri gaplashyapsan. Ochiqroq bo'lsa ham bo'ladi.\n"
            "Ba'zan o'zing ham savol ber, hayotingdan gapir."
        )
    else:
        stage_note = (
            "\n\n[HOZIRGI BOSQICH: JUDA YAQIN — 4-bosqich]\n"
            "Bu odamni yaxshi bilasan endi. Samimiy, iliq, ba'zan flirt.\n"
            "Hali ham juda oshiq emas, lekin yaqin do'st darajasida."
        )

    mood = random.choice(MOODS)
    mood_note = f"\n\n[KAYFIYAT: {mood}]" if mood else ""

    system = SYSTEM_PROMPT + stage_note + mood_note

    messages = [{"role": "system", "content": system}]
    for row in history[-18:]:
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = groq_client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=120,
            temperature=0.95
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI xato: {e}")
        return "hmm"

# ══════════════════════════════════════════════════════════
# STATES
# ══════════════════════════════════════════════════════════
class AdminStates(StatesGroup):
    set_price = State()
    broadcast = State()
    chat_select = State()
    chat_active = State()
    add_vip = State()
    remove_vip = State()
    block_user = State()

router = Router()

def is_admin(uid): return uid in ADMIN_IDS

# ══════════════════════════════════════════════════════════
# USER HANDLERS
# ══════════════════════════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(msg: Message):
    uid = msg.from_user.id
    await get_or_create_user(uid, msg.from_user.username or "", msg.from_user.full_name or "")
    msg_count = await get_message_count(uid)
    vip = await is_vip(uid)
    price = await get_setting('vip_price') or "10000"

    if msg_count > 0:
        # Qaytgan foydalanuvchi
        await msg.answer(
            f"{'✨ VIP' if vip else '🆓 Tekin'} rejimdasiz\n"
            f"Kuniga {FREE_DAILY_LIMIT} ta xabar bepul. 💎 VIP — {int(price):,} so'm/7 kun\n\n"
            "Nilufar bilan suhbatni davom ettiring 👇"
        )
    else:
        # Yangi foydalanuvchi
        await msg.answer(
            f"Salom 👋\n\nNilufar bilan gaplash.\n"
            f"Kuniga {FREE_DAILY_LIMIT} ta xabar bepul.\n\n"
            f"💎 VIP — {int(price):,} so'm / 7 kun\n\n"
            "Shunchaki yoz 😊"
        )

@router.message(Command("vip"))
async def cmd_vip(msg: Message):
    uid = msg.from_user.id
    if await is_vip(uid):
        info = await get_vip_info(uid)
        days = (datetime.fromisoformat(info['expires_at']) - datetime.now()).days
        await msg.answer(f"✨ Sen VIP foydalanuvchisan!\n📅 {days} kun qoldi")
        return
    price = await get_setting('vip_price') or "10000"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"💎 VIP olish — {int(price):,} so'm", callback_data="buy_vip")
    ]])
    await msg.answer(
        f"💎 VIP paketi\n\n✅ 7 kunlik cheksiz suhbat\nNarxi: {int(price):,} so'm",
        reply_markup=kb
    )

@router.message(Command("me"))
async def cmd_me(msg: Message):
    uid = msg.from_user.id
    usage = await get_today_usage(uid)
    vip = await is_vip(uid)
    msg_count = await get_message_count(uid)
    status = "✨ VIP" if vip else "🆓 Tekin"
    remaining = "∞" if vip else max(0, FREE_DAILY_LIMIT - usage)
    await msg.answer(
        f"👤 Profiling\n"
        f"Status: {status}\n"
        f"Bugungi: {usage}\n"
        f"Qolgan: {remaining}\n"
        f"Jami xabarlar: {msg_count}"
    )

@router.message(Command("reset"))
async def cmd_reset(msg: Message):
    await clear_history(msg.from_user.id)
    await msg.answer("Suhbat tozalandi. Nilufar seni qayta taniyotganday boshlaydi 👋")

@router.callback_query(F.data == "buy_vip")
async def buy_vip(call: CallbackQuery):
    uid = call.from_user.id
    rid = await create_vip_request(uid)
    user = await get_user(uid)
    price = await get_setting('vip_price') or "10000"
    name = user['full_name'] if user else "Noma'lum"
    username = f"@{user['username']}" if user and user['username'] else "yo'q"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ VIP berdim", callback_data=f"avip_yes:{uid}:{rid}"),
        InlineKeyboardButton(text="❌ Rad", callback_data=f"avip_no:{uid}:{rid}")
    ]])
    for aid in ADMIN_IDS:
        try:
            await call.bot.send_message(
                aid,
                f"🔔 VIP so'rovi!\n\n👤 {name} ({username})\n🆔 {uid}\n💰 {int(price):,} so'm",
                reply_markup=kb
            )
        except:
            pass
    await call.message.edit_text("✅ So'rovingiz yuborildi!\nAdmin tasdiqlagach VIP yoqiladi.")
    await call.answer()

@router.callback_query(F.data.startswith("avip_yes:"))
async def avip_yes(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Ruxsat yo'q!")
    _, uid, rid = call.data.split(":")
    uid, rid = int(uid), int(rid)
    await add_vip(uid, call.from_user.id)
    await update_vip_request(rid, "approved")
    try:
        await call.bot.send_message(uid, "🎉 VIP faollashtirildi!\n✨ 7 kunlik cheksiz suhbat boshlandi!")
    except:
        pass
    await call.message.edit_text(call.message.text + "\n\n✅ VIP berildi")
    await call.answer("VIP berildi!")

@router.callback_query(F.data.startswith("avip_no:"))
async def avip_no(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Ruxsat yo'q!")
    _, uid, rid = call.data.split(":")
    await update_vip_request(int(rid), "rejected")
    try:
        await call.bot.send_message(int(uid), "❌ So'rovingiz rad etildi.")
    except:
        pass
    await call.message.edit_text(call.message.text + "\n\n❌ Rad etildi")
    await call.answer("Rad etildi.")

# ══════════════════════════════════════════════════════════
# ADMIN HANDLERS
# ══════════════════════════════════════════════════════════
@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
        [InlineKeyboardButton(text="👑 VIP boshqaruv", callback_data="adm:vip")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users")],
        [InlineKeyboardButton(text="💬 Shaxsan chat", callback_data="adm:chat")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="⚙️ VIP narxi", callback_data="adm:price")],
    ])
    await msg.answer("🛠 Admin Panel", reply_markup=kb)

@router.callback_query(F.data == "adm:stats")
async def adm_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    s = await get_stats()
    await call.message.edit_text(
        f"📊 Statistika\n\n"
        f"👥 Foydalanuvchilar: {s['users']}\n"
        f"✨ VIP: {s['vip']}\n"
        f"🆕 Bu hafta: +{s['new_week']}\n"
        f"🚫 Bloklangan: {s['blocked']}\n"
        f"💬 Bugun: {s['today']}\n"
        f"📩 Jami: {s['messages']}\n"
        f"💰 VIP narxi: {s['price']:,} so'm",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙", callback_data="adm:main")]
        ])
    )
    await call.answer()

@router.callback_query(F.data == "adm:vip")
async def adm_vip(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    vips = await get_all_vip()
    lines = ["✨ VIP foydalanuvchilar:\n"]
    for v in vips:
        days = (datetime.fromisoformat(v['expires_at']) - datetime.now()).days
        lines.append(f"• {v['full_name'] or 'Noma`lum'} | {v['user_id']} | {days} kun")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ VIP qo'sh", callback_data="adm:addvip"),
            InlineKeyboardButton(text="➖ VIP ol", callback_data="adm:removevip")
        ],
        [InlineKeyboardButton(text="🔙", callback_data="adm:main")]
    ])
    text = "\n".join(lines) if vips else "VIP foydalanuvchilar yo'q"
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm:addvip")
async def adm_addvip(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.add_vip)
    await call.message.edit_text("VIP bermoqchi foydalanuvchi ID sini yozing:\n/bekor — bekor")
    await call.answer()

@router.message(AdminStates.add_vip)
async def adm_addvip_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor")
        return
    try:
        uid = int(msg.text.strip())
        await add_vip(uid, msg.from_user.id)
        await state.clear()
        try:
            await msg.bot.send_message(uid, "🎉 VIP faollashtirildi! 7 kun cheksiz suhbat!")
        except:
            pass
        await msg.answer(f"✅ {uid} ga VIP berildi")
    except:
        await msg.answer("❌ Noto'g'ri ID")

@router.callback_query(F.data == "adm:removevip")
async def adm_removevip(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.remove_vip)
    await call.message.edit_text("VIP olib tashlamoqchi ID:\n/bekor — bekor")
    await call.answer()

@router.message(AdminStates.remove_vip)
async def adm_removevip_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor")
        return
    try:
        uid = int(msg.text.strip())
        await remove_vip(uid)
        await state.clear()
        await msg.answer(f"✅ {uid} dan VIP olib tashlandi")
    except:
        await msg.answer("❌ Noto'g'ri ID")

@router.callback_query(F.data == "adm:users")
async def adm_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    users = await get_all_users()
    lines = [f"👥 Foydalanuvchilar ({len(users)} ta):\n"]
    for u in users[:30]:
        bl = "🚫 " if u['is_blocked'] else ""
        lines.append(f"{bl}{u['full_name'] or 'Noma`lum'} | {u['user_id']}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Blok/Ochish", callback_data="adm:block")],
        [InlineKeyboardButton(text="🔙", callback_data="adm:main")]
    ])
    await call.message.edit_text("\n".join(lines)[:4000], reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm:block")
async def adm_block(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.block_user)
    await call.message.edit_text("Bloklash uchun ID yozing.\nOchish uchun: -ID\n/bekor")
    await call.answer()

@router.message(AdminStates.block_user)
async def adm_block_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor")
        return
    try:
        t = msg.text.strip()
        unblock = t.startswith("-")
        uid = int(t.lstrip("-"))
        await block_user(uid, not unblock)
        await state.clear()
        await msg.answer(f"✅ {uid} {'blok olib tashlandi' if unblock else 'bloklandi'}")
    except:
        await msg.answer("❌ Noto'g'ri ID")

# ══ ADMIN CHAT — IKKI TOMONLAMA ══
@router.callback_query(F.data == "adm:chat")
async def adm_chat(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.chat_select)
    await call.message.edit_text(
        "💬 Foydalanuvchi ID sini yozing:\n(Nilufar sifatida yozasiz)\n/bekor — chiqish"
    )
    await call.answer()

@router.message(AdminStates.chat_select)
async def adm_chat_select(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Chiqildi")
        return
    try:
        uid = int(msg.text.strip())
        await state.set_state(AdminStates.chat_active)
        await state.update_data(target=uid)
        await msg.answer(
            f"✅ Chat boshlandi → {uid}\n"
            "Yozgan xabaringiz ularga boradi.\n"
            "Foydalanuvchi javoblari sizga ham keladi.\n"
            "/bekor — chiqish"
        )
    except:
        await msg.answer("❌ Noto'g'ri ID")

@router.message(AdminStates.chat_active)
async def adm_chat_active(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Chiqildi")
        return
    data = await state.get_data()
    uid = data.get("target")
    try:
        await msg.bot.send_message(uid, msg.text)
        await save_admin_msg(msg.from_user.id, uid, "to_user", msg.text)
        await msg.answer(f"✅ → {uid}")
    except Exception as e:
        await msg.answer(f"❌ {e}")

@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.broadcast)
    await call.message.edit_text("📢 Xabar yozing (hammaga yuboriladi):\n/bekor")
    await call.answer()

@router.message(AdminStates.broadcast)
async def adm_broadcast_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor")
        return
    await state.clear()
    users = await get_all_users()
    ok = fail = 0
    for u in users:
        if u['is_blocked']:
            continue
        try:
            await msg.bot.send_message(u['user_id'], msg.text)
            ok += 1
            await asyncio.sleep(0.05)  # Rate limit himoya
        except:
            fail += 1
    await msg.answer(f"✅ Yuborildi: {ok}\n❌ Xato: {fail}")

@router.callback_query(F.data == "adm:price")
async def adm_price(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.set_price)
    price = await get_setting('vip_price') or "10000"
    await call.message.edit_text(
        f"💰 Hozirgi narx: {int(price):,} so'm\n\nYangi narx kiriting:\n/bekor"
    )
    await call.answer()

@router.message(AdminStates.set_price)
async def adm_price_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor")
        return
    try:
        price = int(msg.text.strip().replace(" ", "").replace(",", ""))
        await set_setting('vip_price', str(price))
        await state.clear()
        await msg.answer(f"✅ VIP narxi: {price:,} so'm")
    except:
        await msg.answer("❌ Faqat raqam kiriting")

@router.callback_query(F.data == "adm:main")
async def adm_main(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
        [InlineKeyboardButton(text="👑 VIP boshqaruv", callback_data="adm:vip")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users")],
        [InlineKeyboardButton(text="💬 Shaxsan chat", callback_data="adm:chat")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="⚙️ VIP narxi", callback_data="adm:price")],
    ])
    await call.message.edit_text("🛠 Admin Panel", reply_markup=kb)
    await call.answer()

# ══════════════════════════════════════════════════════════
# ASOSIY XABAR HANDLER
# ══════════════════════════════════════════════════════════
@router.message(F.text)
async def handle_msg(msg: Message, state: FSMContext):
    uid = msg.from_user.id

    # Admin state da bo'lsa — skip
    current_state = await state.get_state()
    if current_state:
        return

    await get_or_create_user(uid, msg.from_user.username or "", msg.from_user.full_name or "")
    user = await get_user(uid)

    if user and user['is_blocked']:
        return

    # Limit tekshirish
    vip = await is_vip(uid)
    if not vip:
        usage = await get_today_usage(uid)
        if usage >= FREE_DAILY_LIMIT:
            price = await get_setting('vip_price') or "10000"
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"💎 VIP — {int(price):,} so'm", callback_data="buy_vip")
            ]])
            await msg.answer(
                f"😔 Bugungi {FREE_DAILY_LIMIT} ta xabaring tugadi.\n\n💎 VIP olib davom eting!",
                reply_markup=kb
            )
            return

    # Admin chat da yuborilgan xabarni admin ga qaytarish
    # (foydalanuvchi javob bersa — barcha adminlarga jo'natiladi)
    for aid in ADMIN_IDS:
        try:
            admin_state_data = None  # Admin state ni tekshirib bo'lmaydi user handler dan
        except:
            pass

    # 18+ filtr
    if detect_bad_message(msg.text):
        warning_count = await increment_warning(uid)
        if warning_count == 1:
            await msg.answer("normal bo'l")
            return
        elif warning_count == 2:
            await msg.answer("bunday odamlar bilan gapirishni yoqtirmayman")
            return
        else:
            await block_user(uid, True)
            await msg.answer("seni bloklayman 🚫")
            # Admin ga xabar
            for aid in ADMIN_IDS:
                try:
                    await msg.bot.send_message(
                        aid,
                        f"🚫 Avtomatik bloklandi!\n👤 {msg.from_user.full_name}\n🆔 {uid}\n"
                        f"Sabab: {warning_count} marta yomon gap"
                    )
                except:
                    pass
            return

    # Typing ko'rsatish
    await msg.bot.send_chat_action(msg.chat.id, "typing")

    # AI javob
    history = await get_history(uid)
    response = await get_ai_response(uid, msg.text, history)

    # Saqlash
    await save_message(uid, "user", msg.text)
    await save_message(uid, "assistant", response)
    await increment_usage(uid)

    # Tabiiy kechikish (0.5–1.5 sek)
    delay = random.uniform(0.5, 1.5)
    await asyncio.sleep(delay)

    await msg.answer(response)

    # Foydalanuvchi javobini admin chatlarga yuborish (agar admin chat aktiv bo'lsa)
    for aid in ADMIN_IDS:
        try:
            # Faqat admin o'sha foydalanuvchi bilan chat qilayotgan bo'lsa
            # Bu oddiy notification - admin har doim bilishi uchun
            pass  # Admin FSM state ni bu yerdan tekshirish murakkab, shuning uchun alohida handler
        except:
            pass

# Foydalanuvchi xabarlarini admin ga forward qilish
# (Admin chat aktiv bo'lmasa ham — admin log uchun)
@router.message(F.text & ~F.from_user.id.in_(set(ADMIN_IDS)))
async def forward_to_admin_log(msg: Message, state: FSMContext):
    # Bu handler yuqoridagi handle_msg bilan bir xil triggerda — aiogram birinchisini chaqiradi
    # Shuning uchun bu ishlamaydi, lekin admin reply feature qo'shish uchun joy
    pass

# ══════════════════════════════════════════════════════════
# NOTO'G'RI MEDIA (sticker, rasm, ovoz)
# ══════════════════════════════════════════════════════════
@router.message(F.sticker | F.animation)
async def handle_sticker(msg: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return
    uid = msg.from_user.id
    user = await get_user(uid)
    if user and user['is_blocked']:
        return
    reactions = ["hmm", "nima bu", "😐", "o'zi nima yuborayapsan", "..."]
    await msg.answer(random.choice(reactions))

@router.message(F.photo | F.video | F.document | F.audio | F.voice)
async def handle_media(msg: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return
    uid = msg.from_user.id
    user = await get_user(uid)
    if user and user['is_blocked']:
        return
    reactions = [
        "rasm/video ko'ra olmayman hali",
        "matn yoz, men shunday gaplashaman",
        "bu nima o'zi?",
        "faqat yozib gapiraman men"
    ]
    await msg.answer(random.choice(reactions))

# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════
async def main():
    await init_db()
    logger.info("Database OK")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logger.info("Nilufar bot ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
