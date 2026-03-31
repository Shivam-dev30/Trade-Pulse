import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Credentials
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_KEY = os.getenv("ANGEL_TOTP_KEY")

# Delta Exchange Credentials
DELTA_API_KEY = os.getenv("DELTA_API_KEY")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET")

# Email Configuration
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))

# Trading Configuration
TIMEFRAME = 15  # 15 minutes
SUPERTREND_PERIOD = 31
SUPERTREND_MULTIPLIER = 2.0

# Symbols to Monitor (Example mapping: Symbol -> Token)
# You would typically fetch these dynamically or load from a JSON, 
# but for now we'll support a simple list or map.
# Ideally, we need the Exchange Token for the WebSocket.
# Format: {"SYMBOL_NAME": "TOKEN"}
# Delta Exchange Watchlist (Populated dynamically)
DELTA_WATCHLIST = []

# Note: In a real scenario, we might need to look up tokens. 
# For the purpose of this bot, we can populate this in main.py or a separate config.
