import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOOKS_FILE = BASE_DIR / "books.json"


def get_bot_token() -> str:
    """Читает токен бота из файла .env или переменных окружения."""
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token in ("ВАШ_ТОКЕН_ЗДЕСЬ", "your_telegram_bot_token_here"):
        raise ValueError("Укажите реальный BOT_TOKEN в файле .env!")
    return token