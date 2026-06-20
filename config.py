# config.py
# Botning asosiy sozlamalari shu yerda.
#
# Bu fayl avval Railway "Variables" bo'limidan BOT_TOKEN va ADMIN_IDS ni
# o'qishga harakat qiladi. Agar topilmasa, pastdagi standart qiymatlardan
# foydalanadi (lokal kompyuterda sinab ko'rish uchun qulay).

import os

# @BotFather dan olingan token.
# Railway: Variables bo'limida BOT_TOKEN nomi bilan qo'shilgan bo'lishi kerak.
BOT_TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ_BU_YERGA")

# Admin bo'la oladigan Telegram foydalanuvchi ID lari.
# Railway: Variables bo'limida ADMIN_IDS nomi bilan, bir nechta bo'lsa
# vergul bilan ajratib yoziladi, masalan: 809455015,123456789
_admin_ids_raw = os.getenv("ADMIN_IDS", "123456789")
ADMIN_IDS = [int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip()]

# Ma'lumotlar bazasi fayli nomi
DB_PATH = "kino_bot.db"

# --- VIP / Monetizatsiya sozlamalari ---

# VIP obuna narxi Telegram Stars da (XTR)
VIP_PRICE_STARS = 100

# VIP necha kunga beriladi
VIP_DURATION_DAYS = 30

# Referal orqali bonus: necha kishi taklif qilsa necha kun VIP beriladi
REFERRALS_FOR_BONUS = 5
REFERRAL_BONUS_DAYS = 3

# Bepul foydalanuvchilarga premium kino ko'rishdan oldin
# reklama/sponsor xabari ko'rsatiladimi
SHOW_AD_BEFORE_PREMIUM = True

# Reklama/sponsor xabari matni (kanal reklamasi, sponsor linki va h.k.)
AD_MESSAGE = (
    "📢 <b>Sponsor</b>\n\n"
    "Bu yerga reklama beruvchining matni yoki kanal havolasi qo'yiladi.\n"
    "Reklamasiz tomosha qilish uchun VIP bo'ling 👇"
)
