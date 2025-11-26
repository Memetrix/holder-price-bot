"""Vercel serverless entry point - with PostgreSQL DB support"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import aiohttp
import asyncio
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')


def get_db_connection():
    """Get PostgreSQL database connection."""
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set, history will use mock data")
        return None
    try:
        import psycopg2
        # Handle Render's postgres:// vs postgresql:// URL
        db_url = DATABASE_URL
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None


async def get_price_history_from_db(source: str = None, hours: int = 24, limit: int = 1000) -> List[Dict]:
    """Get price history from PostgreSQL database."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        # Build query based on source filter
        if source:
            query = """
                SELECT id, source, pair, price, price_usd, volume_24h, high_24h, low_24h,
                       change_24h, liquidity_usd, timestamp, created_at
                FROM price_history
                WHERE source = %s AND timestamp >= NOW() - INTERVAL '%s hours'
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (source, hours, limit))
        else:
            query = """
                SELECT id, source, pair, price, price_usd, volume_24h, high_24h, low_24h,
                       change_24h, liquidity_usd, timestamp, created_at
                FROM price_history
                WHERE timestamp >= NOW() - INTERVAL '%s hours'
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (hours, limit))

        columns = ['id', 'source', 'pair', 'price', 'price_usd', 'volume_24h', 'high_24h',
                   'low_24h', 'change_24h', 'liquidity_usd', 'timestamp', 'created_at']

        results = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # Convert datetime to ISO string
            if record.get('timestamp'):
                record['timestamp'] = record['timestamp'].isoformat()
            if record.get('created_at'):
                record['created_at'] = record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            # Convert Decimal to float
            for key in ['price', 'price_usd', 'volume_24h', 'high_24h', 'low_24h', 'change_24h', 'liquidity_usd']:
                if record.get(key) is not None:
                    record[key] = float(record[key])
            results.append(record)

        cursor.close()
        conn.close()
        return results

    except Exception as e:
        logger.error(f"Error fetching price history: {e}")
        if conn:
            conn.close()
        return []

# CORS configuration
ALLOWED_ORIGINS = os.getenv(
    'ALLOWED_ORIGINS',
    'https://frontend-xi-umber-55.vercel.app'
).split(',')

# Create FastAPI app
app = FastAPI(
    title="HOLDER Price Monitor API",
    description="Backend API for HOLDER Token Mini App (Serverless)",
    version="1.0.0"
)

# CORS middleware with whitelist
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only allow needed methods
    allow_headers=["*"],
)

# GeckoTerminal Pool Addresses
STONFI_TON_POOL = "EQBFfO1KN9KFXOkcURnYTm3q76Rg6yF63fOGh60hWF7e35MW"   # STON.fi HOLDER/TON
STONFI_USDT_POOL = "EQB7QzomEu1neLq4jvE89hFBX6bigCgRqvKLjZKJRPASgdSY"  # STON.fi HOLDER/USDT
DEDUST_POOL = "EQA5Svd-50VLKBdAizIASaBFLgWJ11XQbdaeDy4FtTa_ybIt"       # DeDust HOLDER/TON

# Cache for Origami API (to avoid rate limiting)
_origami_cache = {"data": None, "timestamp": None}
CACHE_TTL = 30  # Cache for 30 seconds

# Persistent session for better connection reuse
_session: Optional[aiohttp.ClientSession] = None


async def get_stonfi_price():
    """Get HOLDER/TON price from STON.fi via GeckoTerminal API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.geckoterminal.com/api/v2/networks/ton/pools/{STONFI_TON_POOL}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    pool_data = data.get('data', {})
                    attrs = pool_data.get('attributes', {})

                    price_usd = float(attrs.get('base_token_price_usd', 0))
                    price_ton = float(attrs.get('base_token_price_native_currency', 0))
                    volume_24h_usd = float(attrs.get('volume_usd', {}).get('h24', 0))
                    reserve_usd = float(attrs.get('reserve_in_usd', 0))
                    price_change_24h = float(attrs.get('price_change_percentage', {}).get('h24', 0))

                    return {
                        'source': 'stonfi_dex',
                        'pair': 'HOLDER/TON',
                        'price': price_ton,
                        'price_usd': price_usd,
                        'change_24h': price_change_24h,
                        'volume_24h': volume_24h_usd,
                        'high_24h': price_usd,
                        'low_24h': price_usd,
                        'timestamp': datetime.now().isoformat(),
                        'liquidity_usd': reserve_usd
                    }
                else:
                    logger.error(f"GeckoTerminal STON.fi TON API returned status {response.status}")
    except Exception as e:
        logger.error(f"Error fetching STON.fi TON price: {e}")
    return None


async def get_stonfi_usdt_price():
    """Get HOLDER/USDT price from STON.fi via GeckoTerminal API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.geckoterminal.com/api/v2/networks/ton/pools/{STONFI_USDT_POOL}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    pool_data = data.get('data', {})
                    attrs = pool_data.get('attributes', {})

                    price_usd = float(attrs.get('base_token_price_usd', 0))
                    volume_24h_usd = float(attrs.get('volume_usd', {}).get('h24', 0))
                    reserve_usd = float(attrs.get('reserve_in_usd', 0))
                    price_change_24h = float(attrs.get('price_change_percentage', {}).get('h24', 0))

                    return {
                        'source': 'stonfi_dex_usdt',
                        'pair': 'HOLDER/USDT',
                        'price': price_usd,
                        'price_usd': price_usd,
                        'change_24h': price_change_24h,
                        'volume_24h': volume_24h_usd,
                        'high_24h': price_usd,
                        'low_24h': price_usd,
                        'timestamp': datetime.now().isoformat(),
                        'liquidity_usd': reserve_usd
                    }
                else:
                    logger.error(f"GeckoTerminal STON.fi USDT API returned status {response.status}")
    except Exception as e:
        logger.error(f"Error fetching STON.fi USDT price: {e}")
    return None


async def get_dedust_price():
    """Get HOLDER/TON price from DeDust DEX via GeckoTerminal API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.geckoterminal.com/api/v2/networks/ton/pools/{DEDUST_POOL}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    pool_data = data.get('data', {})
                    attrs = pool_data.get('attributes', {})

                    price_usd = float(attrs.get('base_token_price_usd', 0))
                    price_ton = float(attrs.get('base_token_price_native_currency', 0))
                    volume_24h_usd = float(attrs.get('volume_usd', {}).get('h24', 0))
                    reserve_usd = float(attrs.get('reserve_in_usd', 0))
                    price_change_24h = float(attrs.get('price_change_percentage', {}).get('h24', 0))

                    return {
                        'source': 'dedust_dex',
                        'pair': 'HOLDER/TON',
                        'price': price_ton,
                        'price_usd': price_usd,
                        'change_24h': price_change_24h,
                        'volume_24h': volume_24h_usd,
                        'high_24h': price_usd,
                        'low_24h': price_usd,
                        'timestamp': datetime.now().isoformat(),
                        'liquidity_usd': reserve_usd
                    }
                else:
                    logger.error(f"GeckoTerminal API returned status {response.status}")
    except Exception as e:
        logger.error(f"Error fetching DeDust price: {e}")
    return None


async def _get_session():
    """Get or create persistent aiohttp session"""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def get_origami_price():
    """Get HOLDER price from Origami (WEEX CEX) with caching and retry logic"""
    global _origami_cache

    # Check cache first
    if _origami_cache["data"] and _origami_cache["timestamp"]:
        cache_age = (datetime.now() - _origami_cache["timestamp"]).total_seconds()
        if cache_age < CACHE_TTL:
            logger.info(f"Using cached Origami data (age: {cache_age:.1f}s)")
            return _origami_cache["data"]

    # Retry logic: 3 attempts with exponential backoff
    url = "https://api.origami.tech/api/market/public/ticker?symbol_id=36380"
    max_retries = 3

    for attempt in range(max_retries):
        try:
            session = await _get_session()

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    response_data = await response.json()
                    data = response_data.get('data', {})
                    last_price = float(data.get('last_price', 0))

                    result = {
                        'source': 'weex_cex',
                        'pair': 'HOLDER/USDT',
                        'price': last_price,
                        'price_usd': last_price,
                        'volume_24h': 0,
                        'high_24h': last_price,
                        'low_24h': last_price,
                        'change_24h': 0,
                        'timestamp': datetime.now().isoformat()
                    }

                    # Update cache only on successful fetch
                    _origami_cache["data"] = result
                    _origami_cache["timestamp"] = datetime.now()
                    logger.info("Origami price fetched successfully")

                    return result

                elif response.status == 429:
                    # Rate limit - wait longer and retry
                    logger.warning(f"Origami API rate limit (429), retry {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue

                elif response.status >= 500:
                    # Server error - retry
                    logger.warning(f"Origami API server error ({response.status}), retry {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff for 5xx
                        continue
                else:
                    logger.error(f"Origami API returned status {response.status}")
                    break  # Don't retry on client errors (4xx except 429)

        except asyncio.TimeoutError:
            logger.warning(f"Origami API timeout, retry {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
        except Exception as e:
            logger.error(f"Error fetching Origami price: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue

    # All retries failed - return cached data if available
    if _origami_cache["data"]:
        cache_age = (datetime.now() - _origami_cache["timestamp"]).total_seconds()
        logger.warning(f"Using stale cache (age: {cache_age:.1f}s) after all retries failed")
        return _origami_cache["data"]

    return None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "HOLDER Price Monitor API (Serverless)",
        "version": "1.0.0",
        "endpoints": {
            "price": "/api/price",
            "stats": "/api/stats",
            "arbitrage": "/api/arbitrage"
        }
    }


@app.get("/api/price")
async def get_price():
    """Get current prices from all sources."""
    try:
        # Fetch all prices in parallel
        import asyncio
        dex_ton, dex_usdt, dedust, cex = await asyncio.gather(
            get_stonfi_price(),
            get_stonfi_usdt_price(),
            get_dedust_price(),
            get_origami_price(),
            return_exceptions=True
        )

        prices = {}
        if dex_ton and not isinstance(dex_ton, Exception):
            prices['dex_ton'] = dex_ton
        if dex_usdt and not isinstance(dex_usdt, Exception):
            prices['dex_usdt'] = dex_usdt
        if dedust and not isinstance(dedust, Exception):
            prices['dedust'] = dedust
        if cex and not isinstance(cex, Exception):
            prices['cex'] = cex

        if not prices:
            raise HTTPException(status_code=503, detail="No price data available")

        return {
            "success": True,
            "data": prices,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get 24h statistics."""
    try:
        # For serverless, we can't calculate real stats without DB
        # Return current prices as stats
        price_data = await get_price()

        stats = {}
        data = price_data.get('data', {})

        for key, value in data.items():
            stats[key] = {
                'current': value.get('price_usd') or value.get('price'),
                'high': value.get('high_24h'),
                'low': value.get('low_24h'),
                'change': value.get('change_24h'),
                'volume': value.get('volume_24h')
            }

        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/arbitrage")
async def get_arbitrage():
    """Check for arbitrage opportunities."""
    try:
        price_data = await get_price()
        data = price_data.get('data', {})

        # Compare DEX USDT and CEX prices
        dex_usdt = data.get('dex_usdt', {}).get('price_usd')
        cex = data.get('cex', {}).get('price_usd')

        if dex_usdt and cex:
            diff = abs(dex_usdt - cex)
            percent = (diff / min(dex_usdt, cex)) * 100

            if percent >= 1.0:
                if dex_usdt < cex:
                    arb = {
                        'buy_on': 'DEX (USDT)',
                        'sell_on': 'CEX',
                        'buy_price': dex_usdt,
                        'sell_price': cex,
                        'profit_percent': percent
                    }
                else:
                    arb = {
                        'buy_on': 'CEX',
                        'sell_on': 'DEX (USDT)',
                        'buy_price': cex,
                        'sell_price': dex_usdt,
                        'profit_percent': percent
                    }

                return {
                    "success": True,
                    "data": arb,
                    "has_opportunity": True,
                    "timestamp": datetime.now().isoformat()
                }

        return {
            "success": True,
            "data": None,
            "has_opportunity": False,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error checking arbitrage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history(source: str = None, hours: int = 24, limit: int = 1000):
    """
    Get historical price data from PostgreSQL database.
    Falls back to empty response if DB is not available.
    """
    try:
        # Map frontend source names to DB source names
        source_mapping = {
            'dex_ton': 'stonfi_dex',
            'dex_usdt': 'stonfi_dex_usdt',
            'dedust': 'dedust_dex',
            'cex': 'weex_cex',
            # Also support direct DB source names
            'stonfi_dex': 'stonfi_dex',
            'stonfi_dex_usdt': 'stonfi_dex_usdt',
            'dedust_dex': 'dedust_dex',
            'weex_cex': 'weex_cex',
        }

        db_source = source_mapping.get(source, source) if source else None
        logger.info(f"Fetching history: source={source} -> db_source={db_source}, hours={hours}, limit={limit}")

        # Try to get real data from database
        history = await get_price_history_from_db(source=db_source, hours=hours, limit=limit)

        if history:
            logger.info(f"Got {len(history)} records from database")
            return {
                "success": True,
                "data": history,
                "count": len(history),
                "source": "database",
                "timestamp": datetime.now().isoformat()
            }

        # No data from DB
        logger.warning(f"No data from database for source={db_source}")
        return {
            "success": True,
            "data": [],
            "count": 0,
            "source": "database",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching history: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "count": 0,
            "timestamp": datetime.now().isoformat()
        }
