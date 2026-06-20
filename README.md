# Kino Telegram Bot

Qidiruv, janrlar bo'yicha ko'rish, VIP obuna (Telegram Stars orqali to'lov) va
referal tizimiga ega kino-bot.

## Imkoniyatlari

- Kino nomi bo'yicha qidirish
- Janrlar bo'yicha ko'rish
- VIP obuna — Telegram Stars orqali to'g'ridan-to'g'ri to'lov (tashqi to'lov tizimi shart emas)
- Referal tizimi — har 5 ta do'st taklif qilinsa, 3 kunlik bepul VIP beriladi
- Bepul kino ko'rishdan oldin reklama/sponsor xabari ko'rsatiladi
- Admin panel (botning o'zida, alohida sayt kerak emas):
  - `/add_kino` — yangi kino qo'shish
  - `/kinolar` — kinolar ro'yxati va o'chirish
  - `/statistika` — foydalanuvchilar, VIP va kinolar soni

## O'rnatish

1. Python 3.10+ kerak.
2. Kutubxonalarni o'rnating:
   ```
   pip install -r requirements.txt
   ```
3. `config.py` faylini oching va quyidagilarni to'ldiring:
   - `BOT_TOKEN` — @BotFather dan oling (Telegram'da @BotFather ga yozib, `/newbot` buyrug'i bilan yangi bot yarating)
   - `ADMIN_IDS` — o'zingizning Telegram ID raqamingiz (buni @userinfobot orqali bilib olasiz)
4. Botni ishga tushiring:
   ```
   python bot.py
   ```

## Telegram Stars orqali to'lov

Bot Telegram'ning o'z ichki valyutasi — **Stars** orqali ishlaydi. Bu degani:

- Click yoki Payme kabi tashqi to'lov tizimiga ulanish, yuridik shaxs ochish shart emas
- Foydalanuvchi to'g'ridan-to'g'ri Telegram ichida Stars sotib olib, botga to'laydi
- Stars'ni keyinchalik haqiqiy pulga aylantirish Telegram'ning rasmiy qoidalariga bog'liq —
  bu haqida [Telegram Stars hujjatlarini](https://core.telegram.org/bots/payments-stars) o'qib chiqish tavsiya etiladi

Agar kelajakda Click/Payme orqali so'm bilan to'lov qabul qilishni xohlasangiz,
bu alohida modul sifatida qo'shilishi mumkin.

## Muhim eslatmalar (mualliflik huquqi va texnik cheklovlar)

- Oddiy Bot API orqali yuborilgan video fayl hajmi **50MB** bilan cheklangan.
  Kattaroq fayllar uchun video hostingga yuklab, `video_url` orqali link sifatida
  saqlash yoki Local Bot API Server ishlatish kerak bo'ladi.
- Mualliflik huquqi himoyalangan kontentni ruxsatsiz tarqatish O'zbekiston va
  xalqaro qonunchilikka zid bo'lishi mumkin. Tavsiya: faqat ruxsat etilgan/ochiq
  litsenziyali kontent yoki o'zingiz egasi bo'lgan materiallarni joylashtiring,
  yoki botni "sharh + tashqi rasmiy platformaga havola" formatida qiling.
- Ma'lumotlar bazasi hozircha SQLite (`kino_bot.db` fayli). Foydalanuvchilar soni
  ko'paysa, PostgreSQL'ga o'tish tavsiya etiladi.

## Joylashtirish (hosting)

SQLite fayli doimiy saqlanishi uchun **doimiy disk** beradigan platforma kerak
(masalan, oddiy VPS, yoki doimiy volume qo'llab-quvvatlaydigan bulutli xizmat).
Bepul "serverless" platformalar odatda har safar qayta ishga tushganda
fayllarni o'chirib yuboradi — bu SQLite uchun mos emas.

## Keyingi qadamlar (taklif)

- Kanalga sponsor reklama joylashtirish (Telegram Ads yoki to'g'ridan-to'g'ri sponsorlar)
- Inline rejim (`@bot_nomi kino nomi` — boshqa chatlarda ham qidirish)
- Click/Payme integratsiyasi (so'mda to'lov uchun)
- Admin uchun kino tahrirlash (hozircha faqat qo'shish/o'chirish bor)
