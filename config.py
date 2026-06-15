"""
Configuration — loads everything from .env
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
_raw_ids = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = [int(x.strip()) for x in _raw_ids.split(",") if x.strip()] if _raw_ids else []

# OpenAI
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY  # ensure SDK picks it up

# Google Drive
GOOGLE_DRIVE_FOLDER_ID = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
_sa_json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if _sa_json_str:
    GOOGLE_SERVICE_ACCOUNT_JSON = json.loads(_sa_json_str)
else:
    _sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "config/service_account.json")
    with open(_sa_path) as f:
        GOOGLE_SERVICE_ACCOUNT_JSON = json.load(f)

# Naukri
NAUKRI_EMAIL = os.environ["NAUKRI_EMAIL"]
NAUKRI_PASSWORD = os.environ["NAUKRI_PASSWORD"]
