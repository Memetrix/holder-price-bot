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
ARB_THRESHOLD = float(os.getenv('ARB_THRESHOLD', '2.0'))  # Arbitrage alert threshold

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/holder_bot.db')

# API Endpoints
DEX_API_URL = os.getenv(
    'DEX_API_URL',
    'https://api.ston.fi'
)

CEX_API_URL = os.getenv(
    'CEX_API_URL',
    'https://api.origami.tech/api/market/public/ticker?symbol_id=36380'
)

# HOLDER Token Contract Address
HOLDER_CONTRACT = "EQCDuRLTylau8yKEkx1AMLpHAy6Vog_5D6aC4HNkyG8JN-me"

# Mini App Settings
MINIAPP_PORT = int(os.getenv('MINIAPP_PORT', '8000'))
MINIAPP_HOST = os.getenv('MINIAPP_HOST', '0.0.0.0')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
