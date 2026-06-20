# config.py
# Botning asosiy sozlamalari shu yerda.

# @BotFather dan olingan tokenni shu yerga qo'ying
BOT_TOKEN = "SIZNING_BOT_TOKENINGIZ_BU_YERGA"

# Admin bo'la oladigan Telegram foydalanuvchi ID lari
# O'z ID ingizni bilish uchun @userinfobot ga /start yozing
ADMIN_IDS = [123456789]

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
