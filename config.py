import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

FREE_DAILY_LIMIT = 100
VIP_DURATION_DAYS = 7
DEFAULT_VIP_PRICE = 10000

AI_MODEL = "llama-3.3-70b-versatile"
