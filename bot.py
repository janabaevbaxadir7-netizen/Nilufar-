# bot.py
# Kino Telegram Bot — qidiruv, janrlar, VIP obuna (Telegram Stars), referal tizimi, admin panel.

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, ReplyKeyboardMarkup, KeyboardButton
)

import config
import database as db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Qidirish"), KeyboardButton(text="🎬 Janrlar")],
            [KeyboardButton(text="👤 Profil"), KeyboardButton(text="💎 VIP olish")],
        ],
        resize_keyboard=True
    )


def movie_list_kb(movies, prefix="movie"):
    rows = []
    for m in movies:
        label = f"{m['title']} ({m['year']})" if m["year"] else m["title"]
        if m["is_premium"]:
            label = "💎 " + label
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}:{m['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def watch_kb(movie_id, locked: bool):
    if locked:
        rows = [[InlineKeyboardButton(text="💎 VIP bo'lib ko'rish", callback_data="buyvip")]]
    else:
        rows = [[InlineKeyboardButton(text="▶️ Tomosha qilish", callback_data=f"watch:{movie_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


class AddMovie(StatesGroup):
    title = State()
    genre = State()
    year = State()
    description = State()
    premium = State()
    file = State()


# ---------------- /start ----------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split(maxsplit=1)
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            candidate = int(args[1].replace("ref_", ""))
            if candidate != message.from_user.id:
                referred_by = candidate
        except ValueError:
            pass

    existing = db.get_user(message.from_user.id)
    is_new = existing is None
    db.get_or_create_user(message.from_user.id, message.from_user.username, referred_by)

    if is_new and referred_by:
        count = db.increment_referral(referred_by)
        if count % config.REFERRALS_FOR_BONUS == 0:
            db.grant_vip(referred_by, config.REFERRAL_BONUS_DAYS)
            try:
                await bot.send_message(
                    referred_by,
                    f"🎉 Siz {config.REFERRALS_FOR_BONUS} ta do'stingizni taklif qildingiz va "
                    f"{config.REFERRAL_BONUS_DAYS} kunlik bepul VIP yutib oldingiz!"
                )
            except Exception:
                pass

    await message.answer(
        "🎬 <b>Kino botga xush kelibsiz!</b>\n\n"
        "Bu yerda minglab kino va seriallarni tomosha qilishingiz mumkin.\n"
        "Pastdagi tugmalardan birini tanlang 👇",
        reply_markup=main_menu_kb()
    )


# ---------------- Qidirish ----------------

@router.message(F.text == "🔍 Qidirish")
async def ask_search(message: Message):
    await message.answer("Kino nomini yozing:")


@router.message(F.text == "🎬 Janrlar")
async def show_genres(message: Message):
    genres = db.get_all_genres()
    if not genres:
        await message.answer("Hozircha janrlar mavjud emas.")
        return
    rows = [[InlineKeyboardButton(text=g, callback_data=f"genre:{g}")] for g in genres]
    await message.answer("Janrni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("genre:"))
async def cb_genre(callback: CallbackQuery):
    genre = callback.data.split(":", 1)[1]
    movies = db.get_movies_by_genre(genre)
    if not movies:
        await callback.message.answer("Bu janrda hozircha kino yo'q.")
        await callback.answer()
        return
    await callback.message.answer(f"🎬 {genre} janridagi kinolar:", reply_markup=movie_list_kb(movies))
    await callback.answer()


@router.message(F.text == "👤 Profil")
async def show_profile(message: Message):
    user = db.get_or_create_user(message.from_user.id, message.from_user.username)
    vip = db.is_user_vip(message.from_user.id)
    vip_text = "✅ Faol" if vip else "❌ Yo'q"
    vip_until = ""
    if vip and user["vip_until"]:
        vip_until = f"\nTugash sanasi: {user['vip_until'][:10]}"

    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{message.from_user.id}"

    await message.answer(
        f"👤 <b>Profil</b>\n\n"
        f"ID: <code>{message.from_user.id}</code>\n"
        f"VIP: {vip_text}{vip_until}\n"
        f"Taklif qilingan do'stlar: {user['referral_count']}\n\n"
        f"🔗 Referal havolangiz:\n{ref_link}\n\n"
        f"Har {config.REFERRALS_FOR_BONUS} ta do'st uchun {config.REFERRAL_BONUS_DAYS} kunlik bepul VIP olasiz!"
    )


@router.message(F.text == "💎 VIP olish")
async def ask_vip(message: Message):
    await send_vip_invoice(message.chat.id)


async def send_vip_invoice(chat_id):
    await bot.send_invoice(
        chat_id=chat_id,
        title="VIP obuna",
        description=f"{config.VIP_DURATION_DAYS} kunlik VIP — reklamasiz va premium kinolarga to'liq kirish.",
        payload="vip_subscription",
        currency="XTR",
        prices=[LabeledPrice(label="VIP obuna", amount=config.VIP_PRICE_STARS)],
    )


@router.callback_query(F.data == "buyvip")
async def cb_buyvip(callback: CallbackQuery):
    await send_vip_invoice(callback.message.chat.id)
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    until = db.grant_vip(message.from_user.id, config.VIP_DURATION_DAYS)
    await message.answer(
        f"✅ To'lov muvaffaqiyatli! Sizga VIP {config.VIP_DURATION_DAYS} kunga faollashtirildi.\n"
        f"Tugash sanasi: {until.date()}"
    )


# ---------------- Kino qidirish va ko'rsatish ----------------

@router.message(F.text & ~F.text.startswith("/"))
async def text_search(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return  # admin FSM jarayonida bo'lsa, bu handler aralashmaydi

    if message.text in ("🔍 Qidirish", "🎬 Janrlar", "👤 Profil", "💎 VIP olish"):
        return

    movies = db.search_movies(message.text)
    if not movies:
        await message.answer("Hech narsa topilmadi. Boshqa nom bilan urinib ko'ring.")
        return
    await message.answer("Topilgan natijalar:", reply_markup=movie_list_kb(movies))


@router.callback_query(F.data.startswith("movie:"))
async def cb_movie(callback: CallbackQuery):
    movie_id = int(callback.data.split(":", 1)[1])
    movie = db.get_movie(movie_id)
    if movie is None:
        await callback.answer("Topilmadi", show_alert=True)
        return

    locked = bool(movie["is_premium"]) and not db.is_user_vip(callback.from_user.id)
    text = (
        f"🎬 <b>{movie['title']}</b> ({movie['year']})\n"
        f"Janr: {movie['genre']}\n\n"
        f"{movie['description'] or ''}"
    )
    if locked:
        text += "\n\n💎 Bu premium kino. Ko'rish uchun VIP bo'ling."

    await callback.message.answer(text, reply_markup=watch_kb(movie_id, locked))
    await callback.answer()


@router.callback_query(F.data.startswith("watch:"))
async def cb_watch(callback: CallbackQuery):
    movie_id = int(callback.data.split(":", 1)[1])
    movie = db.get_movie(movie_id)
    if movie is None:
        await callback.answer("Topilmadi", show_alert=True)
        return

    if movie["is_premium"] and not db.is_user_vip(callback.from_user.id):
        await callback.answer("Bu kino faqat VIP uchun", show_alert=True)
        return

    if not movie["is_premium"] and config.SHOW_AD_BEFORE_PREMIUM:
        await callback.message.answer(config.AD_MESSAGE)

    db.increment_views(movie_id)

    if movie["file_id"]:
        await callback.message.answer_video(movie["file_id"], caption=movie["title"])
    elif movie["video_url"]:
        await callback.message.answer(f"🔗 Tomosha qilish: {movie['video_url']}")
    else:
        await callback.message.answer("Kechirasiz, bu kino fayli hozircha mavjud emas.")

    await callback.answer()


# ---------------- Admin: kino qo'shish ----------------

@router.message(Command("add_kino"))
async def admin_add_movie_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddMovie.title)
    await message.answer("Kino nomini kiriting:")


@router.message(AddMovie.title)
async def add_movie_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddMovie.genre)
    await message.answer("Janrini kiriting (masalan: Drama, Komediya, Jangari):")


@router.message(AddMovie.genre)
async def add_movie_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await state.set_state(AddMovie.year)
    await message.answer("Chiqqan yilini kiriting (masalan: 2024):")


@router.message(AddMovie.year)
async def add_movie_year(message: Message, state: FSMContext):
    try:
        year = int(message.text)
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 2024):")
        return
    await state.update_data(year=year)
    await state.set_state(AddMovie.description)
    await message.answer("Qisqacha tavsif yozing:")


@router.message(AddMovie.description)
async def add_movie_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddMovie.premium)
    await message.answer("Bu kino premium (faqat VIP) bo'lsinmi? ha / yo'q")


@router.message(AddMovie.premium)
async def add_movie_premium(message: Message, state: FSMContext):
    is_premium = message.text.strip().lower() in ("ha", "ha.", "yes", "+")
    await state.update_data(premium=is_premium)
    await state.set_state(AddMovie.file)
    await message.answer("Endi video faylni yuboring (yoki tashqi havola/link yozing):")


@router.message(AddMovie.file)
async def add_movie_file(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = None
    video_url = None

    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.text:
        video_url = message.text.strip()
    else:
        await message.answer("Video fayl yoki link yuboring.")
        return

    movie_id = db.add_movie(
        title=data["title"],
        genre=data["genre"],
        year=data["year"],
        description=data["description"],
        file_id=file_id,
        video_url=video_url,
        is_premium=data["premium"],
    )
    await state.clear()
    await message.answer(f"✅ Kino qo'shildi! ID: {movie_id}", reply_markup=main_menu_kb())


# ---------------- Admin: ro'yxat, o'chirish, statistika ----------------

@router.message(Command("kinolar"))
async def admin_list_movies(message: Message):
    if not is_admin(message.from_user.id):
        return
    movies = db.get_all_movies()
    if not movies:
        await message.answer("Kinolar mavjud emas.")
        return
    rows = [
        [InlineKeyboardButton(text=f"❌ {m['title']}", callback_data=f"admin_del:{m['id']}")]
        for m in movies
    ]
    await message.answer("Kinolar ro'yxati (o'chirish uchun bosing):",
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("admin_del:"))
async def admin_delete_movie(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    movie_id = int(callback.data.split(":", 1)[1])
    db.delete_movie(movie_id)
    await callback.message.edit_text("✅ O'chirildi.")
    await callback.answer()


@router.message(Command("statistika"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"Foydalanuvchilar: {db.count_users()}\n"
        f"VIP foydalanuvchilar: {db.count_vip_users()}\n"
        f"Kinolar soni: {db.count_movies()}"
    )


# ---------------- Ishga tushirish ----------------

async def main():
    db.init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot, parse_mode="HTML")


if __name__ == "__main__":
    asyncio.run(main())
