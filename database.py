import aiosqlite
import asyncio
from datetime import datetime, date
from config import DEFAULT_VIP_PRICE

DB_PATH = "data/bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TEXT DEFAULT (datetime('now')),
                is_blocked INTEGER DEFAULT 0
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

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS admin_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            INSERT OR IGNORE INTO settings (key, value) VALUES ('vip_price', '10000');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('vip_enabled', '1');
        """)
        await db.commit()

# ─── USER ───────────────────────────────────────────────────────────────────

async def get_or_create_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        await db.execute(
            "UPDATE users SET username=?, full_name=? WHERE user_id=?",
            (username, full_name, user_id)
        )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY joined_at DESC") as cur:
            return await cur.fetchall()

async def block_user(user_id: int, blocked: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=? WHERE user_id=?", (int(blocked), user_id))
        await db.commit()

# ─── DAILY USAGE ─────────────────────────────────────────────────────────────

async def get_today_usage(user_id: int) -> int:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT count FROM daily_usage WHERE user_id=? AND usage_date=?",
            (user_id, today)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def increment_usage(user_id: int):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO daily_usage (user_id, usage_date, count) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, usage_date) DO UPDATE SET count=count+1",
            (user_id, today)
        )
        await db.commit()

# ─── VIP ─────────────────────────────────────────────────────────────────────

async def is_vip(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT expires_at FROM vip_users WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return False
            expires = datetime.fromisoformat(row[0])
            if datetime.now() > expires:
                await db.execute("DELETE FROM vip_users WHERE user_id=?", (user_id,))
                await db.commit()
                return False
            return True

async def add_vip(user_id: int, admin_id: int):
    from datetime import timedelta
    expires = (datetime.now() + timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO vip_users (user_id, activated_at, expires_at, activated_by) "
            "VALUES (?, ?, ?, ?)",
            (user_id, datetime.now().isoformat(), expires, admin_id)
        )
        await db.commit()

async def remove_vip(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM vip_users WHERE user_id=?", (user_id,))
        await db.commit()

async def get_vip_info(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM vip_users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def get_all_vip_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT v.*, u.username, u.full_name
            FROM vip_users v LEFT JOIN users u ON v.user_id = u.user_id
            ORDER BY v.expires_at DESC
        """) as cur:
            return await cur.fetchall()

# ─── VIP REQUESTS ─────────────────────────────────────────────────────────────

async def create_vip_request(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO vip_requests (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()
        return cur.lastrowid

async def update_vip_request_status(request_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE vip_requests SET status=? WHERE id=?", (status, request_id)
        )
        await db.commit()

# ─── MESSAGES ─────────────────────────────────────────────────────────────────

async def save_message(user_id: int, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()

async def get_history(user_id: int, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            rows = await cur.fetchall()
            return list(reversed(rows))

async def clear_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
        await db.commit()

# ─── ADMIN CHAT ───────────────────────────────────────────────────────────────

async def save_admin_chat(admin_id: int, user_id: int, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO admin_chat (admin_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (admin_id, user_id, role, content)
        )
        await db.commit()

# ─── SETTINGS ────────────────────────────────────────────────────────────────

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()

# ─── STATS ───────────────────────────────────────────────────────────────────

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            stats['total_users'] = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM vip_users WHERE expires_at > datetime('now')") as cur:
            stats['active_vip'] = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM messages") as cur:
            stats['total_messages'] = (await cur.fetchone())[0]
        today = date.today().isoformat()
        async with db.execute(
            "SELECT COALESCE(SUM(count), 0) FROM daily_usage WHERE usage_date=?", (today,)
        ) as cur:
            stats['today_messages'] = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= date('now','-7 days')") as cur:
            stats['new_week'] = (await cur.fetchone())[0]
        vip_price = await get_setting('vip_price')
        stats['vip_price'] = int(vip_price) if vip_price else DEFAULT_VIP_PRICE
        return stats
