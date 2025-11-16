"""Vercel serverless entry point - simplified version without DB"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional
import aiohttp
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HOLDER Price Monitor API",
    description="Backend API for HOLDER Token Mini App (Serverless)",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
HOLDER_CONTRACT = "EQCDuRLTylau8yKEkx1AMLpHAy6Vog_5D6aC4HNkyG8JN-me"
TON_CONTRACT = "EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c"
USDT_CONTRACT = "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"

# Cache for Origami API (to avoid rate limiting)
_origami_cache = {"data": None, "timestamp": None}
CACHE_TTL = 30  # Cache for 30 seconds

# Persistent session for better connection reuse
_session: Optional[aiohttp.ClientSession] = None


async def get_stonfi_price():
    """Get HOLDER/TON price from STON.fi"""
    try:
        async with aiohttp.ClientSession() as session:
            pool_url = f"https://api.ston.fi/v1/pools/by_market/{HOLDER_CONTRACT}/{TON_CONTRACT}"
            async with session.get(pool_url) as response:
                if response.status == 200:
                    data = await response.json()
                    pool_list = data.get('pool_list', [])

                    if pool_list and len(pool_list) > 0:
                        pool = pool_list[0]
                        reserve0 = float(pool.get('reserve0', 0))  # TON (9 decimals)
                        reserve1 = float(pool.get('reserve1', 0))  # HOLDER (9 decimals)

                        # Normalize decimals: both TON and HOLDER have 9 decimals
                        reserve0_normalized = reserve0 / (10 ** 9)
                        reserve1_normalized = reserve1 / (10 ** 9)

                        price_in_ton = (reserve0_normalized / reserve1_normalized) if reserve1_normalized > 0 else 0
                        volume_24h = float(pool.get('volume_24h_usd', 0))

                        return {
                            'source': 'stonfi_dex',
                            'pair': 'HOLDER/TON',
                            'price': price_in_ton,
                            'price_usd': None,
                            'volume_24h': volume_24h,
                            'high_24h': price_in_ton,
                            'low_24h': price_in_ton,
                            'change_24h': 0,
                            'timestamp': datetime.now().isoformat()
                        }
    except Exception as e:
        logger.error(f"Error fetching STON.fi price: {e}")
    return None


async def get_stonfi_usdt_price():
    """Get HOLDER/USDT price from STON.fi"""
    try:
        async with aiohttp.ClientSession() as session:
            pool_url = f"https://api.ston.fi/v1/pools/by_market/{HOLDER_CONTRACT}/{USDT_CONTRACT}"
            async with session.get(pool_url) as response:
                if response.status == 200:
                    data = await response.json()
                    pool_list = data.get('pool_list', [])

                    if pool_list and len(pool_list) > 0:
                        pool = pool_list[0]
                        reserve0 = float(pool.get('reserve0', 0))  # USDT (6 decimals)
                        reserve1 = float(pool.get('reserve1', 0))  # HOLDER (9 decimals)

                        # Normalize decimals: USDT has 6 decimals, HOLDER has 9
                        reserve0_normalized = reserve0 / (10 ** 6)
                        reserve1_normalized = reserve1 / (10 ** 9)

                        price = (reserve0_normalized / reserve1_normalized) if reserve1_normalized > 0 else 0
                        volume_24h = float(pool.get('volume_24h_usd', 0))

                        return {
                            'source': 'stonfi_dex_usdt',
                            'pair': 'HOLDER/USDT',
                            'price': price,
                            'price_usd': price,
                            'volume_24h': volume_24h,
                            'high_24h': price,
                            'low_24h': price,
                            'change_24h': 0,
                            'timestamp': datetime.now().isoformat()
                        }
    except Exception as e:
        logger.error(f"Error fetching STON.fi USDT price: {e}")
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
        dex_ton, dex_usdt, cex = await asyncio.gather(
            get_stonfi_price(),
            get_stonfi_usdt_price(),
            get_origami_price(),
            return_exceptions=True
        )

        prices = {}
        if dex_ton and not isinstance(dex_ton, Exception):
            prices['dex_ton'] = dex_ton
        if dex_usdt and not isinstance(dex_usdt, Exception):
            prices['dex_usdt'] = dex_usdt
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
    Generate mock historical data for demo purposes.
    In production, this would come from a database.
    """
    import random
    from datetime import timedelta

    try:
        # Get current price to base mock data on
        price_data = await get_price()
        if not price_data or not price_data.get('data'):
            return {
                "success": True,
                "data": [],
                "count": 0,
                "timestamp": datetime.now().isoformat()
            }

        # Determine which source to use
        data_sources = price_data.get('data', {})
        logger.info(f"Available sources: {list(data_sources.keys())}, requested: {source}")

        if source:
            if source not in data_sources:
                return {
                    "success": True,
                    "data": [],
                    "count": 0,
                    "timestamp": datetime.now().isoformat()
                }
            source_data = data_sources[source]
            base_price = source_data.get('price_usd') if source_data.get('price_usd') is not None else source_data.get('price')
            source_name = source
        else:
            # Default to CEX if available, otherwise first available
            if 'cex' in data_sources:
                base_price = data_sources['cex'].get('price_usd')
                source_name = 'cex'
            else:
                source_name = list(data_sources.keys())[0]
                source_data = data_sources[source_name]
                base_price = source_data.get('price_usd') if source_data.get('price_usd') is not None else source_data.get('price')

        # Generate mock historical data
        history = []
        now = datetime.now()
        points = min(limit, 500)  # Limit to 500 points

        # Calculate time interval between points
        time_delta = timedelta(hours=hours) / points

        # Generate data points with realistic price variation
        for i in range(points):
            timestamp = now - timedelta(hours=hours) + (time_delta * i)

            # Add some realistic variation (±5% from base price)
            variation = random.uniform(-0.05, 0.05)
            price = base_price * (1 + variation)

            # Generate OHLC data for candlestick
            high = price * random.uniform(1.0, 1.02)
            low = price * random.uniform(0.98, 1.0)

            history.append({
                'source': source_name,
                'pair': data_sources[source_name].get('pair', 'HOLDER/USDT'),
                'price': price,
                'price_usd': price,
                'high_24h': high,
                'low_24h': low,
                'volume_24h': random.uniform(100, 300),
                'timestamp': timestamp.isoformat(),
                'created_at': timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })

        return {
            "success": True,
            "data": history,
            "count": len(history),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating history: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "count": 0,
            "timestamp": datetime.now().isoformat()
        }
