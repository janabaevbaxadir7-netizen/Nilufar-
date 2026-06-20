# database.py
# SQLite bilan ishlovchi barcha funksiyalar shu yerda.
# Loyiha kattalashsa, buni PostgreSQL ga ko'chirish tavsiya etiladi.

import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Bot birinchi marta ishga tushganda jadvallarni yaratadi."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            genre TEXT NOT NULL,
            year INTEGER,
            description TEXT,
            file_id TEXT,
            video_url TEXT,
            is_premium INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_at TEXT DEFAULT (datetime('now')),
            is_vip INTEGER DEFAULT 0,
            vip_until TEXT,
            referred_by INTEGER,
            referral_count INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# ---------- FILMLAR ----------

def add_movie(title, genre, year, description, file_id, video_url, is_premium):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO movies (title, genre, year, description, file_id, video_url, is_premium)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, genre, year, description, file_id, video_url, int(is_premium)))
    conn.commit()
    movie_id = cur.lastrowid
    conn.close()
    return movie_id


def delete_movie(movie_id):
    conn = get_conn()
    conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    conn.commit()
    conn.close()


def get_movie(movie_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    conn.close()
    return row


def search_movies(query, limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies WHERE title LIKE ? ORDER BY views DESC LIMIT ?",
        (f"%{query}%", limit)
    ).fetchall()
    conn.close()
    return rows


def get_movies_by_genre(genre, limit=20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies WHERE genre = ? ORDER BY created_at DESC LIMIT ?",
        (genre, limit)
    ).fetchall()
    conn.close()
    return rows


def get_all_genres():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT genre FROM movies ORDER BY genre").fetchall()
    conn.close()
    return [r["genre"] for r in rows]


def increment_views(movie_id):
    conn = get_conn()
    conn.execute("UPDATE movies SET views = views + 1 WHERE id = ?", (movie_id,))
    conn.commit()
    conn.close()


def get_all_movies(limit=50):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM movies ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def count_movies():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM movies").fetchone()["c"]
    conn.close()
    return n


# ---------- FOYDALANUVCHILAR ----------

def get_or_create_user(user_id, username, referred_by=None):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users (user_id, username, referred_by) VALUES (?, ?, ?)",
            (user_id, username, referred_by)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def is_user_vip(user_id):
    conn = get_conn()
    row = conn.execute("SELECT is_vip, vip_until FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None or not row["is_vip"]:
        return False
    if row["vip_until"] is None:
        return True
    return datetime.fromisoformat(row["vip_until"]) > datetime.now()


def grant_vip(user_id, days):
    conn = get_conn()
    row = conn.execute("SELECT vip_until FROM users WHERE user_id = ?", (user_id,)).fetchone()
    now = datetime.now()
    if row and row["vip_until"]:
        current_until = datetime.fromisoformat(row["vip_until"])
        base = max(current_until, now)
    else:
        base = now
    new_until = base + timedelta(days=days)
    conn.execute(
        "UPDATE users SET is_vip = 1, vip_until = ? WHERE user_id = ?",
        (new_until.isoformat(), user_id)
    )
    conn.commit()
    conn.close()
    return new_until


def increment_referral(referrer_id):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
        (referrer_id,)
    )
    conn.commit()
    row = conn.execute("SELECT referral_count FROM users WHERE user_id = ?", (referrer_id,)).fetchone()
    conn.close()
    return row["referral_count"] if row else 0


def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def count_users():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    conn.close()
    return n


def count_vip_users():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_vip = 1").fetchone()["c"]
    conn.close()
    return n
