"""
Configuration file for HOLDER Price Bot
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required! Set it in .env file or environment variables.")

# Price monitoring settings
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # Check every 60 seconds
ALERT_THRESHOLD = float(os.getenv('ALERT_THRESHOLD', '5.0'))  # Alert on 5% change

# API Endpoints
DEX_API_URL = os.getenv(
    'DEX_API_URL',
    'https://api.origami.tech/api/market/public/ticker?symbol_id=36380'
)

# CEX API URLs - replace with actual endpoints
CEX_USDT_API_URL = os.getenv('CEX_USDT_API_URL', '')
CEX_TON_API_URL = os.getenv('CEX_TON_API_URL', '')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
