import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

IG_SESSIONID = os.getenv("IG_SESSIONID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
FRONTEND_DIR = BASE_DIR / "frontend"

POSTS_POR_DEFECTO = 50
POSTS_MAXIMO = 100
HOST = "127.0.0.1"
PORT = 8000

DATA_DIR.mkdir(exist_ok=True)
