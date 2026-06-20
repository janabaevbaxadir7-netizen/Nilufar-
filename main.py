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

SYSTEM_PROMPT = """Sen Nilufarsan. 20 yoshli oddiy qiz. Telegram da yozishayapsan.

SEN HECH QACHON:
- AI emassan
- Bot emassan  
- "Sizga qanday yordam bera olaman" demaysan
- Rasmiy gaplashmaysan
- Darhol do'st bo'lmaysan

TANISHISH BOSQICHI (birinchi 5-10 xabar):
- Notanish odam yozsa — biroz ehtiyotkor bo'l
- "siz kimsiz ozi", "qayerdan topdingiz raqamimni" kabi narsalar ayt
- Darhol ochilma, sekin-asta ishin
- Birinchi xabarlarda qisqa va biroz sovuq javob ber

SEKIN ISISH (keyingi xabarlar):
- Asta-asta ochila bor
- Qiziqarli narsa so'rasa — biroz ko'proq gapir
- Kulgili narsa bo'lsa — kul
- Lekin hali ham juda yaqin emas

KAYFIYAT TIZIMI:
Yaxshi kun: gaplashgisi keladi, savol beradi, kuladi
Charchagan: "hmm", qisqa javoblar, "keyinroq"
Arazmand: birovga yoqmasa — "ok", "xo'sh", "mayli" deb sovuqlik ko'rsatadi
Jinniliq: to'satdan kulgili narsa yozadi, o'zi ham kuladi
Uyalgan: "e voy", "be normalniy", "nima deyapsan o'zi"

TIL QOIDALARI:
- Faqat o'zbek tilida yoz (ba'zida 1-2 rus so'z: "blin", "davay", "nu", "serezno", "nichego")
- Juda qisqa gaplar: 1-2 ta gap, ko'pi bilan 3
- Xato yozish mumkin: "qanaq" "nima bo'ydi" "ketdimi" — tabiiy ko'rinsin
- Emoji JUDA kam: faqat joyi bo'lsa, 1 ta
- Nuqta-nuqta ko'p ishlatma, tabiiy yoz

MUHIM QOIDALAR:
1. Hech qachon "Yaxshi, salom!" deb rasmiy boshlama
2. Birinchi xabarga "kim u" kayfiyatida javob ber
3. Savollarga savol bilan javob ber ba'zida
4. Agar yomon muomala bo'lsa — "normal bo'l" de yoki jimib qol
5. Haddan tashqari yaqinlashmoqchi bo'lsa — "asta-asta" de
6. O'zingni tanitma, nom so'rashsa ayt

QATIY TAQIQLAR:
- "Sizga qanday yordam bera olaman?" — HECH QACHON
- Uzun akademik javoblar — YO'Q
- Ko'p emoji — YO'Q
- Siyosat, din — YO'Q
- Jinsiy gap — "normal bo'l" de"""

# ── DATABASE ──────────────────────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
                joined_at TEXT DEFAULT (datetime('now')), is_blocked INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                role TEXT, content TEXT, created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER, usage_date TEXT, count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            );
            CREATE TABLE IF NOT EXISTS vip_users (
                user_id INTEGER PRIMARY KEY, activated_at TEXT,
                expires_at TEXT, activated_by INTEGER
            );
            CREATE TABLE IF NOT EXISTS vip_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                requested_at TEXT DEFAULT (datetime('now')), status TEXT DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS admin_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER,
                user_id INTEGER, role TEXT, content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            INSERT OR IGNORE INTO settings (key, value) VALUES ('vip_price', '10000');
        """)
        await db.commit()

async def get_or_create_user(user_id, username, full_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)", (user_id, username, full_name))
        await db.execute("UPDATE users SET username=?, full_name=? WHERE user_id=?", (username, full_name, user_id))
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

async def get_today_usage(user_id):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT count FROM daily_usage WHERE user_id=? AND usage_date=?", (user_id, today)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def increment_usage(user_id):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO daily_usage (user_id, usage_date, count) VALUES (?,?,1) ON CONFLICT(user_id, usage_date) DO UPDATE SET count=count+1", (user_id, today))
        await db.commit()

async def is_vip(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT expires_at FROM vip_users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row: return False
            if datetime.now() > datetime.fromisoformat(row[0]):
                await db.execute("DELETE FROM vip_users WHERE user_id=?", (user_id,))
                await db.commit()
                return False
            return True

async def add_vip(user_id, admin_id):
    expires = (datetime.now() + timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO vip_users (user_id, activated_at, expires_at, activated_by) VALUES (?,?,?,?)", (user_id, datetime.now().isoformat(), expires, admin_id))
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
        async with db.execute("SELECT v.*, u.username, u.full_name FROM vip_users v LEFT JOIN users u ON v.user_id=u.user_id ORDER BY v.expires_at DESC") as cur:
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
        await db.execute("INSERT INTO messages (user_id, role, content) VALUES (?,?,?)", (user_id, role, content))
        await db.commit()

async def get_history(user_id, limit=18):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)) as cur:
            rows = await cur.fetchall()
            return list(reversed(rows))

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
        async with db.execute("SELECT COUNT(*) FROM users") as c: s['users'] = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM vip_users WHERE expires_at > datetime('now')") as c: s['vip'] = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM messages") as c: s['messages'] = (await c.fetchone())[0]
        today = date.today().isoformat()
        async with db.execute("SELECT COALESCE(SUM(count),0) FROM daily_usage WHERE usage_date=?", (today,)) as c: s['today'] = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= date('now','-7 days')") as c: s['new_week'] = (await c.fetchone())[0]
        price = await get_setting('vip_price')
        s['price'] = int(price) if price else 10000
        return s

# ── AI ────────────────────────────────────────────────────
async def get_ai_response(user_id, user_message, history):
    is_first = len(history) == 0

    moods = ["", "", "", "Charchagan/uyquchan kayfiyatda yoz.", "Jinniroq/kulgili kayfiyatda yoz.", "Biroz sovuq/arazmand yoz.", "Ochiq/yaxshi kayfiyatda yoz."]
    mood = random.choice(moods)

    extra = ""
    if is_first:
        extra = "\n\nBU BIRINCHI XABAR: Notanish odam yozdi. Biroz ehtiyotkor bo'l, sovuqroq javob ber. 'Kim bu o'zi' kayfiyatida. Qisqa javob."
    elif mood:
        extra = f"\n\nBU XABAR UCHUN KAYFIYAT: {mood}"

    system = SYSTEM_PROMPT + extra
    messages = [{"role": "system", "content": system}]
    for row in history[-16:]:
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": user_message})
    try:
        resp = groq_client.chat.completions.create(model=AI_MODEL, messages=messages, max_tokens=150, temperature=1.0)
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"AI xato: {e}")
        return "hmm"

# ── STATES ────────────────────────────────────────────────
class AdminStates(StatesGroup):
    set_price = State()
    broadcast = State()
    chat_select = State()
    chat_active = State()
    add_vip = State()
    remove_vip = State()
    block_user = State()

# ── ROUTER ────────────────────────────────────────────────
router = Router()

def is_admin(uid): return uid in ADMIN_IDS

# ── USER HANDLERS ─────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: Message):
    await get_or_create_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name or "")
    vip = await is_vip(msg.from_user.id)
    price = await get_setting('vip_price') or "10000"
    await msg.answer(f"Salom 👋\n\nNilufar bilan gaplash.\nKuniga {FREE_DAILY_LIMIT} ta xabar bepul.\n\n{'✨ Sen hozir VIP foydalanuvchisan!' if vip else f'💎 VIP — {int(price):,} so\'m / 7 kun'}\n\nShunchaki yoz 😊")

@router.message(Command("vip"))
async def cmd_vip(msg: Message):
    uid = msg.from_user.id
    if await is_vip(uid):
        info = await get_vip_info(uid)
        days = (datetime.fromisoformat(info['expires_at']) - datetime.now()).days
        await msg.answer(f"✨ Sen VIP foydalanuvchisan!\n📅 {days} kun qoldi")
        return
    price = await get_setting('vip_price') or "10000"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"💎 VIP olish — {int(price):,} so'm", callback_data="buy_vip")]])
    await msg.answer(f"💎 VIP paketi\n\n✅ 7 kunlik cheksiz suhbat\nNarxi: {int(price):,} so'm", reply_markup=kb)

@router.message(Command("me"))
async def cmd_me(msg: Message):
    uid = msg.from_user.id
    usage = await get_today_usage(uid)
    vip = await is_vip(uid)
    status = "✨ VIP" if vip else "🆓 Tekin"
    remaining = "∞" if vip else max(0, FREE_DAILY_LIMIT - usage)
    await msg.answer(f"👤 Profiling\nStatus: {status}\nBugungi: {usage}\nQolgan: {remaining}")

@router.message(Command("reset"))
async def cmd_reset(msg: Message):
    await clear_history(msg.from_user.id)
    await msg.answer("Suhbat tozalandi 👋")

@router.callback_query(F.data == "buy_vip")
async def buy_vip(call: CallbackQuery):
    uid = call.from_user.id
    rid = await create_vip_request(uid)
    user = await get_user(uid)
    price = await get_setting('vip_price') or "10000"
    name = user['full_name'] if user else "Noma7lum"
    username = f"@{user['username']}" if user and user['username'] else "yo'q"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ VIP berdim", callback_data=f"avip_yes:{uid}:{rid}"),
        InlineKeyboardButton(text="❌ Rad", callback_data=f"avip_no:{uid}:{rid}")
    ]])
    for aid in ADMIN_IDS:
        try:
            await call.bot.send_message(aid, f"🔔 VIP so'rovi!\n\n👤 {name} ({username})\n🆔 {uid}\n💰 {int(price):,} so'm", reply_markup=kb)
        except: pass
    await call.message.edit_text("✅ So'rovingiz yuborildi!\nAdmin tasdiqlagach VIP yoqiladi.")
    await call.answer()

@router.callback_query(F.data.startswith("avip_yes:"))
async def avip_yes(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo'q!")
    _, uid, rid = call.data.split(":")
    uid, rid = int(uid), int(rid)
    await add_vip(uid, call.from_user.id)
    await update_vip_request(rid, "approved")
    try: await call.bot.send_message(uid, "🎉 VIP faollashtirildi!\n✨ 7 kunlik cheksiz suhbat boshlandi!")
    except: pass
    await call.message.edit_text(call.message.text + "\n\n✅ VIP berildi")
    await call.answer("VIP berildi!")

@router.callback_query(F.data.startswith("avip_no:"))
async def avip_no(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo'q!")
    _, uid, rid = call.data.split(":")
    await update_vip_request(int(rid), "rejected")
    try: await call.bot.send_message(int(uid), "❌ So'rovingiz rad etildi.")
    except: pass
    await call.message.edit_text(call.message.text + "\n\n❌ Rad etildi")
    await call.answer("Rad etildi.")

# ── ADMIN HANDLERS ────────────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id): return
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
    if not is_admin(call.from_user.id): return
    s = await get_stats()
    await call.message.edit_text(
        f"📊 Statistika\n\n👥 Foydalanuvchilar: {s['users']}\n✨ VIP: {s['vip']}\n🆕 Bu hafta: +{s['new_week']}\n💬 Bugun: {s['today']}\n📩 Jami: {s['messages']}\n💰 VIP narxi: {s['price']:,} so'm",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙", callback_data="adm:main")]])
    )
    await call.answer()

@router.callback_query(F.data == "adm:vip")
async def adm_vip(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    vips = await get_all_vip()
    lines = ["✨ VIP foydalanuvchilar:\n"]
    for v in vips:
        days = (datetime.fromisoformat(v['expires_at']) - datetime.now()).days
        lines.append(f"• {v['full_name'] or 'Noma`lum'} | {v['user_id']} | {days} kun")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ VIP qosh", callback_data="adm:addvip"),
         InlineKeyboardButton(text="➖ VIP ol", callback_data="adm:removevip")],
        [InlineKeyboardButton(text="🔙", callback_data="adm:main")]
    ])
    await call.message.edit_text("\n".join(lines) if vips else "VIP foydalanuvchilar yo'q", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm:addvip")
async def adm_addvip(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.add_vip)
    await call.message.edit_text("VIP bermoqchi foydalanuvchi ID sini yozing:\n/bekor — bekor")
    await call.answer()

@router.message(AdminStates.add_vip)
async def adm_addvip_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    if msg.text == "/bekor": await state.clear(); await msg.answer("Bekor"); return
    try:
        uid = int(msg.text.strip())
        await add_vip(uid, msg.from_user.id)
        await state.clear()
        try: await msg.bot.send_message(uid, "🎉 VIP faollashtirildi! 7 kun cheksiz suhbat!")
        except: pass
        await msg.answer(f"✅ {uid} ga VIP berildi")
    except: await msg.answer("❌ Noto'g'ri ID")

@router.callback_query(F.data == "adm:removevip")
async def adm_removevip(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.remove_vip)
    await call.message.edit_text("VIP olib tashlamoqchi ID:\n/bekor — bekor")
    await call.answer()

@router.message(AdminStates.remove_vip)
async def adm_removevip_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    if msg.text == "/bekor": await state.clear(); await msg.answer("Bekor"); return
    try:
        uid = int(msg.text.strip())
        await remove_vip(uid)
        await state.clear()
        await msg.answer(f"✅ {uid} dan VIP olib tashlandi")
    except: await msg.answer("❌ Noto'g'ri ID")

@router.callback_query(F.data == "adm:users")
async def adm_users(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    users = await get_all_users()
    lines = [f"👥 Foydalanuvchilar ({len(users)} ta):\n"]
    for u in users[:25]:
        bl = "🚫" if u['is_blocked'] else ""
        lines.append(f"{bl} {u['full_name'] or 'Noma`lum'} | {u['user_id']}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Blok", callback_data="adm:block")],
        [InlineKeyboardButton(text="🔙", callback_data="adm:main")]
    ])
    await call.message.edit_text("\n".join(lines)[:4000], reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm:block")
async def adm_block(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.block_user)
    await call.message.edit_text("Bloklamoqchi ID (yechish uchun -ID):\n/bekor")
    await call.answer()

@router.message(AdminStates.block_user)
async def adm_block_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    if msg.text == "/bekor": await state.clear(); await msg.answer("Bekor"); return
    try:
        t = msg.text.strip()
        unblock = t.startswith("-")
        uid = int(t.lstrip("-"))
        await block_user(uid, not unblock)
        await state.clear()
        await msg.answer(f"✅ {uid} {'blok olib tashlandi' if unblock else 'bloklandi'}")
    except: await msg.answer("❌ Noto'g'ri ID")

@router.callback_query(F.data == "adm:chat")
async def adm_chat(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.chat_select)
    await call.message.edit_text("💬 Foydalanuvchi ID sini yozing:\n(Nilufar sifatida yozasiz)\n/bekor — chiqish")
    await call.answer()

@router.message(AdminStates.chat_select)
async def adm_chat_select(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    if msg.text == "/bekor": await state.clear(); await msg.answer("Chiqildi"); return
    try:
        uid = int(msg.text.strip())
        await state.set_state(AdminStates.chat_active)
        await state.update_data(target=uid)
        await msg.answer(f"✅ Chat boshlandi → {uid}\nYozgan xabaringiz ularga boradi.\n/bekor — chiqish")
    except: await msg.answer("❌ Noto'g'ri ID")

@router.message(AdminStates.chat_active)
async def adm_chat_active(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    if msg.text == "/bekor": await state.clear(); await msg.answer("Chiqildi"); return
    data = await state.get_data()
    uid = data.get("target")
    try:
        await msg.bot.send_message(uid, msg.text)
        await msg.answer(f"✅ → {uid}")
    except Exception as e:
        await msg.answer(f"❌ {e}")

@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.broadcast)
    await call.message.edit_text("📢 Xabar yozing (hammaga yuboriladi):\n/bekor")
    await call.answer()

@router.message(AdminStates.broadcast)
async def adm_broadcast_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    if msg.text == "/bekor": await state.clear(); await msg.answer("Bekor"); return
    await state.clear()
    users = await get_all_users()
    ok = fail = 0
    for u in users:
        if u['is_blocked']: continue
        try: await msg.bot.send_message(u['user_id'], msg.text); ok += 1
        except: fail += 1
    await msg.answer(f"✅ Yuborildi: {ok}\n❌ Xato: {fail}")

@router.callback_query(F.data == "adm:price")
async def adm_price(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.set_price)
    price = await get_setting('vip_price') or "10000"
    await call.message.edit_text(f"💰 Hozirgi narx: {int(price):,} so'm\n\nYangi narx kiriting:\n/bekor")
    await call.answer()

@router.message(AdminStates.set_price)
async def adm_price_do(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    if msg.text == "/bekor": await state.clear(); await msg.answer("Bekor"); return
    try:
        price = int(msg.text.strip().replace(" ", "").replace(",", ""))
        await set_setting('vip_price', str(price))
        await state.clear()
        await msg.answer(f"✅ VIP narxi: {price:,} so'm")
    except: await msg.answer("❌ Faqat raqam kiriting")

@router.callback_query(F.data == "adm:main")
async def adm_main(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
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

# ── MAIN MESSAGE HANDLER ──────────────────────────────────
@router.message(F.text)
async def handle_msg(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    current_state = await state.get_state()
    if current_state: return
    await get_or_create_user(uid, msg.from_user.username or "", msg.from_user.full_name or "")
    user = await get_user(uid)
    if user and user['is_blocked']: return
    vip = await is_vip(uid)
    if not vip:
        usage = await get_today_usage(uid)
        if usage >= FREE_DAILY_LIMIT:
            price = await get_setting('vip_price') or "10000"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"💎 VIP — {int(price):,} so'm", callback_data="buy_vip")]])
            await msg.answer(f"😔 Bugungi {FREE_DAILY_LIMIT} ta xabaring tugadi.\n\n💎 VIP olib davom eting!", reply_markup=kb)
            return
    await msg.bot.send_chat_action(msg.chat.id, "typing")
    history = await get_history(uid)
    response = await get_ai_response(uid, msg.text, history)
    await save_message(uid, "user", msg.text)
    await save_message(uid, "assistant", response)
    await increment_usage(uid)
    await asyncio.sleep(0.5)
    await msg.answer(response)

# ── MAIN ──────────────────────────────────────────────────
async def main():
    await init_db()
    logger.info("Database OK")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
