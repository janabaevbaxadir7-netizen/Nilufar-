from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db
from config import ADMIN_IDS, FREE_DAILY_LIMIT
from datetime import datetime

router = Router()

# FSM States
class AdminStates(StatesGroup):
    set_price = State()
    broadcast = State()
    chat_with_user = State()
    add_vip_manual = State()
    remove_vip_manual = State()
    block_user = State()

# ─── Admin filter ─────────────────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ─── /admin — asosiy panel ───────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
        [InlineKeyboardButton(text="👑 VIP boshqaruv", callback_data="adm:vip_menu")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users")],
        [InlineKeyboardButton(text="💬 Foydalanuvchi bilan chat", callback_data="adm:chat_select")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="adm:settings")],
    ])
    await msg.answer("🛠 Admin Panel\n\nNimani boshqarmoqchisiz?", reply_markup=kb)

# ─── Statistika ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:stats")
async def show_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    stats = await db.get_stats()
    
    text = (
        f"📊 Bot Statistikasi\n\n"
        f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
        f"✨ Faol VIP: {stats['active_vip']}\n"
        f"🆕 Bu hafta qo'shilgan: {stats['new_week']}\n\n"
        f"💬 Jami xabarlar: {stats['total_messages']}\n"
        f"📅 Bugun xabarlar: {stats['today_messages']}\n\n"
        f"💰 VIP narxi: {stats['vip_price']:,} so'm"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:main")
    ]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

# ─── VIP Menyusi ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:vip_menu")
async def vip_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ VIP qo'shish", callback_data="adm:add_vip")],
        [InlineKeyboardButton(text="➖ VIP olib tashlash", callback_data="adm:remove_vip")],
        [InlineKeyboardButton(text="📋 VIP foydalanuvchilar", callback_data="adm:vip_list")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:main")],
    ])
    await call.message.edit_text("👑 VIP Boshqaruv", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm:vip_list")
async def vip_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    vips = await db.get_all_vip_users()
    
    if not vips:
        text = "😔 Hozircha VIP foydalanuvchilar yo'q."
    else:
        lines = ["✨ VIP Foydalanuvchilar:\n"]
        for v in vips:
            expires = datetime.fromisoformat(v['expires_at'])
            remaining = (expires - datetime.now()).days
            name = v['full_name'] or "Noma'lum"
            username = f"@{v['username']}" if v['username'] else ""
            lines.append(f"• {name} {username}\n  ID: {v['user_id']} | {remaining} kun qoldi")
        text = "\n".join(lines)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:vip_menu")
    ]])
    await call.message.edit_text(text[:4000], reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm:add_vip")
async def add_vip_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.add_vip_manual)
    await call.message.edit_text(
        "VIP bermoqchi bo'lgan foydalanuvchining ID sini yuboring:\n\n"
        "Masalan: 123456789\n\n"
        "/bekor — bekor qilish"
    )
    await call.answer()

@router.message(AdminStates.add_vip_manual)
async def add_vip_confirm(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor qilindi.")
        return
    
    try:
        target_id = int(msg.text.strip())
    except:
        await msg.answer("❌ Noto'g'ri ID. Raqam kiriting.")
        return
    
    await db.add_vip(target_id, msg.from_user.id)
    await state.clear()
    
    try:
        await msg.bot.send_message(
            target_id,
            "🎉 VIP faollashtirildi!\n\n"
            "✨ 7 kunlik cheksiz suhbatdan foydalana olasan.\n\n"
            "Davom eting 😊"
        )
    except:
        pass
    
    await msg.answer(f"✅ Foydalanuvchi {target_id} ga VIP berildi (7 kun).")

@router.callback_query(F.data == "adm:remove_vip")
async def remove_vip_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.remove_vip_manual)
    await call.message.edit_text(
        "VIPni olib tashlamoqchi foydalanuvchi ID sini yuboring:\n\n"
        "/bekor — bekor qilish"
    )
    await call.answer()

@router.message(AdminStates.remove_vip_manual)
async def remove_vip_confirm(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor qilindi.")
        return
    
    try:
        target_id = int(msg.text.strip())
    except:
        await msg.answer("❌ Noto'g'ri ID.")
        return
    
    await db.remove_vip(target_id)
    await state.clear()
    await msg.answer(f"✅ Foydalanuvchi {target_id} dan VIP olib tashlandi.")

# ─── Foydalanuvchilar ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:users")
async def users_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    users = await db.get_all_users()
    total = len(users)
    
    lines = [f"👥 Foydalanuvchilar ({total} ta):\n"]
    for u in users[:30]:  # max 30 ko'rsatish
        name = u['full_name'] or "Noma'lum"
        username = f"@{u['username']}" if u['username'] else ""
        blocked = "🚫" if u['is_blocked'] else ""
        lines.append(f"{blocked} {name} {username} | ID: {u['user_id']}")
    
    if total > 30:
        lines.append(f"\n... va yana {total - 30} ta")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Blok qo'yish", callback_data="adm:block_user")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:main")],
    ])
    await call.message.edit_text("\n".join(lines)[:4000], reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm:block_user")
async def block_user_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.block_user)
    await call.message.edit_text(
        "Bloklamoqchi foydalanuvchi ID sini yuboring:\n"
        "(Blokni olib tashlash uchun ID oldiga - qo'ying)\n\n"
        "Masalan: 123456 yoki -123456\n\n"
        "/bekor — bekor qilish"
    )
    await call.answer()

@router.message(AdminStates.block_user)
async def block_user_action(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor qilindi.")
        return
    
    text = msg.text.strip()
    unblock = text.startswith("-")
    try:
        target_id = int(text.lstrip("-"))
    except:
        await msg.answer("❌ Noto'g'ri ID.")
        return
    
    await db.block_user(target_id, not unblock)
    await state.clear()
    action = "blok olib tashlandi" if unblock else "bloklandi"
    await msg.answer(f"✅ Foydalanuvchi {target_id} {action}.")

# ─── Foydalanuvchi bilan shaxsan chat ─────────────────────────────────────────

@router.callback_query(F.data == "adm:chat_select")
async def chat_select(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.chat_with_user)
    await call.message.edit_text(
        "💬 Foydalanuvchi bilan chat\n\n"
        "Foydalanuvchi ID sini yuboring:\n\n"
        "DIQQAT: Siz NILUFAR nomidan yozasiz!\n"
        "Foydalanuvchi siz bilan emas — bot bilan gaplashyapti deb o'ylaydi.\n\n"
        "/bekor — chiqish"
    )
    await call.answer()

@router.message(AdminStates.chat_with_user)
async def admin_chat_handler(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    
    if msg.text == "/bekor":
        await state.clear()
        data = await state.get_data()
        await msg.answer("Chat rejimidan chiqildi.")
        return
    
    data = await state.get_data()
    target_id = data.get("chat_target_id")
    
    if not target_id:
        # ID kiritish
        try:
            target_id = int(msg.text.strip())
            await state.update_data(chat_target_id=target_id)
            user = await db.get_user(target_id)
            name = user['full_name'] if user else "Noma'lum"
            await msg.answer(
                f"✅ Chat boshlandi: {name} (ID: {target_id})\n\n"
                f"Endi yozgan har bir xabaringiz foydalanuvchiga yuboriladi.\n"
                f"Foydalanuvchi siz Nilufar deb o'ylaydi.\n\n"
                f"/bekor — chiqish"
            )
        except:
            await msg.answer("❌ Noto'g'ri ID. Qaytadan kiriting.")
        return
    
    # Admin yozgan xabarni foydalanuvchiga yuborish
    try:
        await msg.bot.send_message(target_id, msg.text)
        await db.save_admin_chat(msg.from_user.id, target_id, "assistant", msg.text)
        # Admin ga tasdiqlash
        await msg.answer(f"✅ Yuborildi → {target_id}")
    except Exception as e:
        await msg.answer(f"❌ Yuborib bo'lmadi: {e}")

# ─── Broadcast ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.broadcast)
    await call.message.edit_text(
        "📢 Broadcast\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n"
        "/bekor — bekor qilish"
    )
    await call.answer()

@router.message(AdminStates.broadcast)
async def broadcast_send(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor qilindi.")
        return
    
    await state.clear()
    users = await db.get_all_users()
    
    success = 0
    failed = 0
    status_msg = await msg.answer(f"📤 Yuborilmoqda... (0/{len(users)})")
    
    for i, user in enumerate(users):
        if user['is_blocked']:
            continue
        try:
            await msg.bot.send_message(user['user_id'], msg.text)
            success += 1
        except:
            failed += 1
        
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"📤 Yuborilmoqda... ({i+1}/{len(users)})")
            except:
                pass
    
    await status_msg.edit_text(
        f"✅ Broadcast yakunlandi!\n\n"
        f"✅ Yuborildi: {success}\n"
        f"❌ Xato: {failed}"
    )

# ─── Sozlamalar ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:settings")
async def settings_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    price = await db.get_setting('vip_price') or "10000"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 VIP narxi: {int(price):,} so'm", callback_data="adm:change_price")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:main")],
    ])
    await call.message.edit_text("⚙️ Sozlamalar", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm:change_price")
async def change_price_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.set_price)
    await call.message.edit_text(
        "💰 Yangi VIP narxini kiriting (so'mda):\n\n"
        "Masalan: 15000\n\n"
        "/bekor — bekor qilish"
    )
    await call.answer()

@router.message(AdminStates.set_price)
async def change_price_save(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return
    
    if msg.text == "/bekor":
        await state.clear()
        await msg.answer("Bekor qilindi.")
        return
    
    try:
        price = int(msg.text.strip().replace(" ", "").replace(",", ""))
        if price < 1000:
            await msg.answer("❌ Narx kamida 1000 so'm bo'lishi kerak.")
            return
    except:
        await msg.answer("❌ Noto'g'ri son. Faqat raqam kiriting.")
        return
    
    await db.set_setting('vip_price', str(price))
    await state.clear()
    await msg.answer(f"✅ VIP narxi yangilandi: {price:,} so'm")

# ─── Orqaga tugmasi ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:main")
async def back_to_main(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
        [InlineKeyboardButton(text="👑 VIP boshqaruv", callback_data="adm:vip_menu")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users")],
        [InlineKeyboardButton(text="💬 Foydalanuvchi bilan chat", callback_data="adm:chat_select")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="adm:settings")],
    ])
    await call.message.edit_text("🛠 Admin Panel\n\nNimani boshqarmoqchisiz?", reply_markup=kb)
    await call.answer()
