from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
import database as db
from ai.girlfriend import get_ai_response, GIRL_NAME
from config import FREE_DAILY_LIMIT, ADMIN_IDS
import asyncio

router = Router()

# ─── /start ──────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def start(msg: Message):
    await db.get_or_create_user(
        msg.from_user.id,
        msg.from_user.username or "",
        msg.from_user.full_name or ""
    )
    
    vip = await db.is_vip(msg.from_user.id)
    price = await db.get_setting('vip_price') or "10000"
    
    text = (
        f"Salom 👋\n\n"
        f"Bu yerda {GIRL_NAME} bilan gaplasha olasan.\n"
        f"Kuniga {FREE_DAILY_LIMIT} ta xabar bepul.\n\n"
        f"{'✨ Sen hozir VIP foydalanuvchisan!' if vip else f'💎 VIP — {int(price):,} so\'m / 7 kun (cheksiz)'}\n\n"
        f"Shunchaki yoz — suhbat boshlanadi."
    )
    await msg.answer(text)

# ─── /vip ─────────────────────────────────────────────────────────────────────

@router.message(Command("vip"))
async def vip_info(msg: Message):
    user_id = msg.from_user.id
    is_vip_user = await db.is_vip(user_id)
    price = await db.get_setting('vip_price') or "10000"
    
    if is_vip_user:
        info = await db.get_vip_info(user_id)
        from datetime import datetime
        expires = datetime.fromisoformat(info['expires_at'])
        remaining = (expires - datetime.now()).days
        await msg.answer(
            f"✨ Sen VIP foydalanuvchisan!\n"
            f"📅 Amal qilish muddati: {remaining} kun qoldi\n\n"
            f"Cheksiz suhbatdan zavqlan 🎉"
        )
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"💎 VIP olish — {int(price):,} so'm", callback_data="buy_vip")
    ]])
    await msg.answer(
        f"💎 VIP paketi\n\n"
        f"✅ 7 kunlik cheksiz suhbat\n"
        f"✅ Limitlarsiz\n\n"
        f"Narxi: {int(price):,} so'm",
        reply_markup=kb
    )

@router.callback_query(F.data == "buy_vip")
async def buy_vip(call: CallbackQuery):
    user_id = call.from_user.id
    request_id = await db.create_vip_request(user_id)
    
    # Admin(lar)ga xabar yuborish
    user = await db.get_user(user_id)
    price = await db.get_setting('vip_price') or "10000"
    name = user['full_name'] if user else "Noma'lum"
    username = f"@{user['username']}" if user and user['username'] else "username yo'q"
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ VIP berdim", callback_data=f"admin_vip_yes:{user_id}:{request_id}"),
        InlineKeyboardButton(text="❌ Rad", callback_data=f"admin_vip_no:{user_id}:{request_id}")
    ]])
    
    for admin_id in ADMIN_IDS:
        try:
            await call.bot.send_message(
                admin_id,
                f"🔔 Yangi VIP so'rovi!\n\n"
                f"👤 {name} ({username})\n"
                f"🆔 ID: {user_id}\n"
                f"💰 Narx: {int(price):,} so'm\n"
                f"📝 So'rov #{request_id}",
                reply_markup=admin_kb
            )
        except:
            pass
    
    await call.message.edit_text(
        f"✅ So'rovingiz yuborildi!\n\n"
        f"Admin to'lovni tasdiqlash uchun siz bilan bog'lanadi.\n"
        f"Narx: {int(price):,} so'm\n\n"
        f"To'lov tasdiqlangandan so'ng VIP avtomatik yoqiladi."
    )
    await call.answer()

# ─── /me — foydalanuvchi ma'lumoti ───────────────────────────────────────────

@router.message(Command("me"))
async def my_info(msg: Message):
    user_id = msg.from_user.id
    usage = await db.get_today_usage(user_id)
    is_vip_user = await db.is_vip(user_id)
    
    remaining = "∞" if is_vip_user else max(0, FREE_DAILY_LIMIT - usage)
    status = "✨ VIP" if is_vip_user else "🆓 Tekin"
    
    if is_vip_user:
        info = await db.get_vip_info(user_id)
        from datetime import datetime
        expires = datetime.fromisoformat(info['expires_at'])
        remaining_days = (expires - datetime.now()).days
        extra = f"\n📅 VIP: {remaining_days} kun qoldi"
    else:
        extra = ""
    
    await msg.answer(
        f"👤 Profiling\n\n"
        f"Status: {status}{extra}\n"
        f"Bugungi xabarlar: {usage}/{FREE_DAILY_LIMIT if not is_vip_user else '∞'}\n"
        f"Qolgan limit: {remaining}"
    )

# ─── /reset — suhbatni boshlash ───────────────────────────────────────────────

@router.message(Command("reset"))
async def reset_chat(msg: Message):
    await db.clear_history(msg.from_user.id)
    await msg.answer("Suhbat tozalandi. Qaytadan boshlash mumkin 👋")

# ─── Admin VIP callback (user handler da ham ishlashi kerak) ─────────────────

@router.callback_query(F.data.startswith("admin_vip_yes:"))
async def admin_confirm_vip(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Ruxsat yo'q!")
        return
    
    parts = call.data.split(":")
    target_user_id = int(parts[1])
    request_id = int(parts[2])
    
    await db.add_vip(target_user_id, call.from_user.id)
    await db.update_vip_request_status(request_id, "approved")
    
    try:
        await call.bot.send_message(
            target_user_id,
            "🎉 VIP faollashtirildi!\n\n"
            "✨ Endi cheksiz suhbatdan foydalana olasan.\n"
            "Muddat: 7 kun\n\n"
            "Davom eting 😊"
        )
    except:
        pass
    
    await call.message.edit_text(
        call.message.text + f"\n\n✅ VIP berildi (admin: @{call.from_user.username})"
    )
    await call.answer("VIP berildi!")

@router.callback_query(F.data.startswith("admin_vip_no:"))
async def admin_reject_vip(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Ruxsat yo'q!")
        return
    
    parts = call.data.split(":")
    target_user_id = int(parts[1])
    request_id = int(parts[2])
    
    await db.update_vip_request_status(request_id, "rejected")
    
    try:
        await call.bot.send_message(
            target_user_id,
            "❌ So'rovingiz rad etildi.\n\n"
            "To'lov tasdiqlanmadi. Qayta urinib ko'ring yoki admin bilan bog'laning."
        )
    except:
        pass
    
    await call.message.edit_text(
        call.message.text + f"\n\n❌ Rad etildi (admin: @{call.from_user.username})"
    )
    await call.answer("Rad etildi.")

# ─── Asosiy xabar handler ─────────────────────────────────────────────────────

@router.message(F.text)
async def handle_message(msg: Message):
    user_id = msg.from_user.id
    
    # Ro'yxatdan o'tkazish
    await db.get_or_create_user(
        user_id,
        msg.from_user.username or "",
        msg.from_user.full_name or ""
    )
    
    # Bloklangan foydalanuvchi
    user = await db.get_user(user_id)
    if user and user['is_blocked']:
        return
    
    # Admin o'zi foydalanuvchi bilan suhbat yuritayotganmi?
    # Admin chat mode (admin_id:user_id format)
    # Bu admin handler da boshqariladi
    
    # Limit tekshirish
    is_vip_user = await db.is_vip(user_id)
    
    if not is_vip_user:
        usage = await db.get_today_usage(user_id)
        if usage >= FREE_DAILY_LIMIT:
            price = await db.get_setting('vip_price') or "10000"
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=f"💎 VIP olish — {int(price):,} so'm",
                    callback_data="buy_vip"
                )
            ]])
            await msg.answer(
                f"😔 Bugungi {FREE_DAILY_LIMIT} ta xabaring tugadi.\n\n"
                f"💎 VIP olib, cheksiz davom eting!\n"
                f"Narxi: {int(price):,} so'm / 7 kun",
                reply_markup=kb
            )
            return
    
    # Typing animatsiyasi
    await msg.bot.send_chat_action(msg.chat.id, "typing")
    
    # Tarix olish
    history = await db.get_history(user_id)
    
    # AI javob
    response = await get_ai_response(user_id, msg.text, history)
    
    # Saqlash
    await db.save_message(user_id, "user", msg.text)
    await db.save_message(user_id, "assistant", response)
    await db.increment_usage(user_id)
    
    # Kichik kechikish (real qizdek)
    await asyncio.sleep(0.5)
    await msg.answer(response)
