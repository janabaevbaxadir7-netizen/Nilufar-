import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
import database as db
from handlers import user, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    # DB papkasini yaratish
    os.makedirs("data", exist_ok=True)
    
    # Ma'lumotlar bazasini ishga tushirish
    await db.init_db()
    logger.info("Database initialized")
    
    # Bot va Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Handlerlarni ro'yxatdan o'tkazish
    # Admin handler birinchi (priority uchun)
    dp.include_router(admin.router)
    dp.include_router(user.router)
    
    logger.info("Bot starting...")
    
    # Polling
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
