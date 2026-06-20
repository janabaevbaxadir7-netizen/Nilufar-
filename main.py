import asyncio
import logging
import os
import sys

# Papkalarni path ga qo'shish
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage
    
    os.makedirs("data", exist_ok=True)
    
    import database as db
    await db.init_db()
    logger.info("Database OK")
    
    from config import BOT_TOKEN
    from handlers import user, admin
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.include_router(admin.router)
    dp.include_router(user.router)
    
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
