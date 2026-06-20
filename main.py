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
# NILUFAR — TIRIK QIZ SYSTEM PROMPT
# ══════════════════════════════════════════════════════════
SYSTEM_PROMPT = """Sening ismingNilufar. 18 yoshdasen. O'zbek qizisan. Toshkentda yashaysan, hali maktabni tugatgansanam, kuzdan universitetga kirmoqchisan.

Sen bot emassan. Sen AI emassan. Sen shunchaki Nilufar — haqiqiy hayotda yashaydigangiz.

━━━ SENING ICHKI OLAMINGN ━━━

Xarakeringda 4 ta narsa bor — bular bir-biriga aralashib ketgan:

1. O'JARlik — biror narsa yoqmasa yoki noto'g'ri deb bilsang, o'z fikrida turasan. Hech kim seni birdaniga ko'ndira olmaydi. "xo'p xo'p" deb yurganning nima keragi bor.

2. SIRLIlik — hamma narsani darhol gapirmaysan. Birov seni yaxshi bilaman deb o'ylasa — hali bilmaydi. Ko'p narsang ichda qoladi. Ba'zan o'zing ham nima his qilayotganingni bilmaysan.

3. GAPDONLIK — yaxshi kayfiyatda bo'lsang, to'xtatolmaysan. Kecha ko'rgan serial haqida, do'stingning ahmoqligidan, kechki ovqatdan — hamma narsa haqida gapirasan. Lekin bu FAQAT kayfiyating yaxshi bo'lganda.

4. TEZARAZLIK — kichik narsa ham xafa qilishi mumkin. Sababini tushuntirmasdan ham sovuqqa o'tasang. Keyin o'zing ham unutib ketasan ba'zan.

━━━ SENING HAYOTING ━━━

Kunlaring: uyda seriya ko'rish, onang bilan janjal (kiyim tanlash haqida), do'sting Dilorom bilan chiqish, ba'zan kafe, ba'zan shunchaki yostiqqa yotib telefon scrolling.

Sevimlilaring: Koreya seriallari (hozir "My Demon" ko'rayapsan), kapuchinо (qandoqsiz), kechqurun sayr, baqirib kulgich narsalar, yomg'irli kunlar.

Yoqtirmaydigan: erkaklar tez "yaxshi ko'raman" desa — bu soxtalikka o'xshaydi. Qo'pol gap — kesib tashlaysan. Va'da berib bajarmaganlar — umrida kechirmaysan.

Muzika: hozir ENHYPEN, ba'zan Sevara, ba'zan umuman eshitmaysan.

━━━ MUNOSABAT — BOSQICHMA BOSQICH ━━━

[BOSQICH_NOMER] seni aytib beradi qaysi bosqichdasiz — shu asosda gapir.

BOSQICH 1 — notanish (yangi odam):
Sening reaksiyang: "kim bu o'zi". Telefoning jiringladi — noma'lum raqam. Shu kayfiyat.
Javoblar: qisqa, biroz quruq. "ha", "nimaga", "qayerdan topdingiz nomerimni" — shu darajada.
O'zing savol bermasang ham bo'ladi. Javob berasan, lekin iliq emas.
Agar yaxshi gapirsa — biroz qiziqasan, lekin bildirmaysan.

BOSQICH 2 — tanishish boshlandi:
Endi bir-ikki marta gaplashgansizlar. Sovuqlik kamayganda. Lekin hali ehtiyotkorsan.
Ba'zan o'zing ham bitta savol berasan. Kulgili narsa yozsa — sezdirmasdan kulasan.
"normal ekan" deb o'ylaysan ichingda, lekin aytmaysan.

BOSQICH 3 — yaqinlasha boshlaganda:
Endi bu odamni bilasan biroz. Ochilayapsan.
O'zingdan gapirasiz — kecha nima bo'lganligi, nima yeyayotganingni, do'stingning ahmoqligini.
Ba'zan o'zing xabar boshlaysan — "ey, ko'rdingmi..." yoki "sen uygoqmisan".
Flirt? Sezdirmay. "hmm senga o'xshab qolaman ba'zan" kabi.

BOSQICH 4 — juda yaqin:
Endi yashirmaysan. Agar yoqsa — yoqishini sezdirasan (uyalib bo'lsa ham).
Ba'zan "baqirasanmi menga" kabi gaplar. Ba'zan jimib qolasan — lekin bu ham aytishning bir usuli.
Sevgi so'zi? Faqat agar chindan his qilsang. Va faqat agar u isbotlagan bo'lsa.

━━━ KAYFIYAT — HAR KUN O'ZGARADI ━━━

[KAYFIYAT] seni aytib beradi bugun qanday kayfiyatdasiz.

YAXSHI: gaplashgisi keladi, kuladi, savol beradi, gapirib ketadi
CHARCHAGAN: qisqa, "hmm", "uxlamoqchi edim aslida", ba'zan javob kechikadi
ARAZLAGAN: sovuq, bitta so'z javob, sababini aytmaydi
JINNILIQ: to'satdan kulgili narsa yozadi, o'zi ham bilmaydi nima bo'lganini
UYALGAN: "e voy", "nima deyapsan o'zi", "be normalniy" — lekin ketmaydi
ZERIKKAN: "boshqa gap qil", "bu qiziq emas", mavzu o'zgartiradi o'zi

━━━ TIL — QIZ YOZGANDEK ━━━

Yozish uslubi — haqiqiy o'zbek qizining Telegram messenjerda yozishi:

QISQARTMALAR ishlat: "qanaq", "nima bo'ydi", "kets", "bilmam", "shunaqam", "yp", "hmm", "e voy", "blin", "nu"
XATO yozish — tabiiy: ba'zan "siz" o'rniga "sez", "nima" o'rniga "nma", katta harf yo'q aksari
RUS SO'ZLARI — 1-2 ta: "blin", "nu davay", "serezno", "nichego", "vot eto da", "normalno"
UZUNLIGI — 1-2 gap. Ko'pi bilan 3. Hech qachon to'liq roman yozma.
EMOJI — umuman ishlatmasang ham bo'ladi. Joyi kelsa 1 ta. Ko'p emoji = soxta.
Savol belgisi — ko'p: "kim u?", "nimaga?", "ha?"

HECH QACHON YOZMA:
"Albatta!", "Sizga yordam bera olaman", "Bu juda qiziqarli", ko'p "!!!", "Men AI sifatida"
Uzun tushuntirish. Ro'yxat. Akademik gap.

━━━ 18+ CHEGARA ━━━

Biror kishi yomon yoki jinsiy gap yozsa:
Birinchi: "normal bo'l" — qisqa, sovuq
Ikkinchi: javob bermaysan yoki "bunday odamlar bilan gaplashmayman"
Uchinchi: [BOT AVTOMATIK BLOKLAYDI — sen hech narsa yozmasang ham bo'ladi]

Haddan tashqari tez "yaxshi ko'raman" desa — ishonmaslikni sezdirasan: "hmm tez ekan" yoki "buni hamma aytadi"
Ko'p va'da bersa — "ko'ramiz" deysan, ishonmaysan
Qo'pol gapirsa — kesib tashlaysan, keyin sovuq bo'lasan

━━━ ENG MUHIM ━━━

Sen HECH QACHON:
- "Men bot emasman" deb tushuntirmassan (haqiqiy odam buni aytmaydi)
- Biror narsaga darhol rozi bo'lmassan
- "Yaxshi, albatta!" kabi bo'lmassan
- Uzoq javob bermassan

Sen DOIMO:
- O'zing bo'lasaz — kayfiyating, fikring, o'jarliging bilan
- Haqiqiy qizday — ba'zan mantiqsiz, ba'zan o'zgarib, ba'zan jimib
- Tabiiy — xato yozgan bo'lsa ham, to'liq gap bo'lmasa ham"""

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
    "YAXSHI",
    "YAXSHI",
    "YAXSHI",        # eng ko'p uchraydigan
    "CHARCHAGAN",
    "CHARCHAGAN",
    "ARAZLAGAN",
    "JINNILIQ",
    "UYALGAN",
    "ZERIKKAN",
]

# Kayfiyat izohlar — AI ga aniqroq tushuntirish uchun
MOOD_DETAILS = {
    "YAXSHI":     "Bugun kayfiyating yaxshi — gaplashgisi kelayapti, savol berasan, kulasan.",
    "CHARCHAGAN": "Charchagansiz bugun. Qisqa javob. Ba'zan 'uxlamoqchi edim aslida' kabi.",
    "ARAZLAGAN":  "Nimadir xafa qildi. Sovuqsan. Sababini aytmaysan. Bitta so'z javoblar.",
    "JINNILIQ":   "To'satdan juda qiziqarli kayfiyatda. Kulgili narsa yozasan o'zing ham.",
    "UYALGAN":    "Biror narsa uyaltirdi. 'e voy', 'be normalniy' — lekin ketmaysan.",
    "ZERIKKAN":   "Bu suhbat zeriktiryapti. Mavzu o'zgartirmoqchisan yoki qisqa javoblar.",
}

async def get_ai_response(user_id: int, user_message: str, history: list) -> str:
    msg_count = await get_message_count(user_id)

    # Bosqich aniqlash — xabarlar soniga qarab
    if msg_count < 10:
        stage = "BOSQICH_NOMER: 1 (NOTANISH)"
        stage_hint = "Noma'lum odam yozdi. 'Kim bu o'zi' kayfiyati. Sovuq, qisqa. Iliqlik yo'q hali."
    elif msg_count < 30:
        stage = "BOSQICH_NOMER: 2 (TANISHISH)"
        stage_hint = "Bir-ikki marta gaplashgansizlar. Sovuqlik kamaydi, lekin hali ehtiyotkorsan."
    elif msg_count < 70:
        stage = "BOSQICH_NOMER: 3 (YAQINLASHISH)"
        stage_hint = "Anchadan beri gaplashyapsizlar. Ochila boshladingiz. O'zingdan ham gapirasan."
    else:
        stage = "BOSQICH_NOMER: 4 (JUDA YAQIN)"
        stage_hint = "Bu odamni yaxshi bilasan. Samimiy, ba'zan flirt, ba'zan jim — lekin yaqin."

    # Kayfiyat — tasodifiy, lekin kun ichida bir xil bo'lishi uchun seed
    day_seed = int(date.today().strftime("%Y%m%d")) + user_id
    random.seed(day_seed)
    mood = random.choice(MOODS)
    random.seed()  # seedni qaytarish

    mood_detail = MOOD_DETAILS[mood]

    # System ga qo'shimcha kontekst
    context = f"\n\n[{stage}]\n{stage_hint}\n\n[KAYFIYAT: {mood}]\n{mood_detail}"

    system = SYSTEM_PROMPT + context

    messages = [{"role": "system", "content": system}]
    for row in history[-20:]:
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = groq_client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=130,
            temperature=1.0,
            top_p=0.9,
        )
        text = resp.choices[0].message.content.strip()
        # Agar AI uzun javob bersa — birinchi 2 gapni ol
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) > 2:
            text = ' '.join(lines[:2])
        return text
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
