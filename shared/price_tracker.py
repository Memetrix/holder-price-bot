"""
Price tracking module for HOLDER token
Integrates STON.fi DEX and Origami/WEEX CEX APIs
"""

import aiohttp
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from shared.timezone_utils import utc_now_iso
from shared.cache import SimpleCache

logger = logging.getLogger(__name__)

# HOLDER Token Contract Address on TON
HOLDER_CONTRACT = "EQCDuRLTylau8yKEkx1AMLpHAy6Vog_5D6aC4HNkyG8JN-me"

# TON Native Token Address
TON_CONTRACT = "EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c"

# USDT (jUSDT) Token Address on TON
USDT_CONTRACT = "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"


class PriceTracker:
    """Tracks HOLDER token prices across DEX and CEX."""

    def __init__(self):
        self.previous_prices = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache = SimpleCache()  # In-memory cache with TTL

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_stonfi_price(self) -> Optional[Dict]:
        """
        Get HOLDER price from STON.fi DEX.
        Uses HOLDER/TON pool with stats API for volume data.
        """
        try:
            session = await self._get_session()

            # First, get pool data for current price
            pool_url = f"https://api.ston.fi/v1/pools/by_market/{HOLDER_CONTRACT}/{TON_CONTRACT}"
            async with session.get(pool_url, timeout=10) as pool_response:
                if pool_response.status != 200:
                    logger.warning("HOLDER/TON pool not found on STON.fi")
                    return None

                pool_data = await pool_response.json()
                pool_list = pool_data.get('pool_list', [])
                if not pool_list:
                    return None

                pool = pool_list[0]

                # Calculate price from reserves
                reserve0 = float(pool.get('reserve0', 0))  # TON
                reserve1 = float(pool.get('reserve1', 0))  # HOLDER

                # Price = reserve0 / reserve1 (TON per HOLDER)
                price_in_ton = (reserve0 / reserve1) if reserve1 > 0 else 0

                # Get TON/USDT price to calculate USD equivalent
                ton_usdt_price = await self._get_ton_usdt_price()
                price_in_usd = price_in_ton * ton_usdt_price if ton_usdt_price else None

                # Now get volume from stats API
                since = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')
                until = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
                stats_url = f"https://api.ston.fi/v1/stats/pool?since={since}&until={until}"

                volume_ton = 0
                async with session.get(stats_url, timeout=15) as stats_response:
                    if stats_response.status == 200:
                        stats_data = await stats_response.json()

                        # Find HOLDER pool in stats
                        for stat_pool in stats_data.get('stats', []):
                            base_id = stat_pool.get('base_id', '').lower()
                            quote_id = stat_pool.get('quote_id', '').lower()

                            # Check if this is HOLDER/TON pool (pTON is base, HOLDER is quote)
                            if (quote_id == HOLDER_CONTRACT.lower() and
                                stat_pool.get('base_symbol') in ['pTON', 'TON']):
                                volume_ton = float(stat_pool.get('base_volume', 0))
                                break

                return {
                    'source': 'stonfi_dex',
                    'pair': 'HOLDER/TON',
                    'price': price_in_ton,
                    'price_usd': price_in_usd,  # USD equivalent calculated from TON/USDT
                    'change_24h': 0,  # Calculated from DB
                    'volume_24h': volume_ton,
                    'high_24h': 0,  # Calculated from DB
                    'low_24h': 0,  # Calculated from DB
                    'timestamp': utc_now_iso(),
                    'pool_address': pool.get('address'),
                    'liquidity_usd': float(pool.get('lp_total_supply_usd', 0))
                }

        except Exception as e:
            logger.error(f"Error fetching STON.fi price: {e}")
            return None

    async def _get_ton_usdt_price(self) -> Optional[float]:
        """
        Get TON/USDT exchange rate from STON.fi.
        Returns the price of 1 TON in USDT.
        """
        try:
            session = await self._get_session()

            # Get TON/USDT pool
            pool_url = f"https://api.ston.fi/v1/pools/by_market/{TON_CONTRACT}/{USDT_CONTRACT}"
            async with session.get(pool_url, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"TON/USDT pool not found on STON.fi (status {response.status})")
                    return None

                pool_data = await response.json()
                pool_list = pool_data.get('pool_list', [])
                if not pool_list:
                    logger.warning("No TON/USDT pools found")
                    return None

                pool = pool_list[0]

                # Extract reserves
                # Note: API returns reserves in token address order, not query order
                # token0_address = USDT, token1_address = TON
                reserve0 = float(pool.get('reserve0', 0))  # USDT (6 decimals)
                reserve1 = float(pool.get('reserve1', 0))  # TON (9 decimals)

                # Normalize decimals
                usdt_normalized = reserve0 / (10 ** 6)
                ton_normalized = reserve1 / (10 ** 9)

                # Calculate TON/USDT price (USDT per 1 TON)
                ton_usdt_price = (usdt_normalized / ton_normalized) if ton_normalized > 0 else None

                if ton_usdt_price:
                    logger.info(f"TON/USDT rate from STON.fi: ${ton_usdt_price:.4f}")

                return ton_usdt_price

        except Exception as e:
            logger.error(f"Error fetching TON/USDT price: {e}")
            return None

    async def get_stonfi_usdt_price(self) -> Optional[Dict]:
        """
        Get HOLDER/USDT price from STON.fi DEX with stats for volume.
        """
        try:
            session = await self._get_session()

            # Get pool for HOLDER/USDT pair
            pool_url = f"https://api.ston.fi/v1/pools/by_market/{HOLDER_CONTRACT}/{USDT_CONTRACT}"
            async with session.get(pool_url, timeout=10) as pool_response:
                if pool_response.status != 200:
                    logger.warning(f"STON.fi USDT pool API returned status {pool_response.status}")
                    return None

                pool_data = await pool_response.json()
                pool_list = pool_data.get('pool_list', [])
                if not pool_list:
                    return None

                pool = pool_list[0]

                # Calculate price from reserves
                reserve0 = float(pool.get('reserve0', 0))  # USDT (6 decimals)
                reserve1 = float(pool.get('reserve1', 0))  # HOLDER (9 decimals)

                # Normalize decimals and calculate price
                # USDT has 6 decimals, HOLDER has 9 decimals
                usdt_normalized = reserve0 / (10 ** 6)
                holder_normalized = reserve1 / (10 ** 9)

                # Price in USDT per HOLDER
                price_in_usdt = (usdt_normalized / holder_normalized) if holder_normalized > 0 else 0

                # Get volume from stats API
                since = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')
                until = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
                stats_url = f"https://api.ston.fi/v1/stats/pool?since={since}&until={until}"

                volume_usdt = 0
                async with session.get(stats_url, timeout=15) as stats_response:
                    if stats_response.status == 200:
                        stats_data = await stats_response.json()

                        # Find HOLDER/USDT pool in stats
                        for stat_pool in stats_data.get('stats', []):
                            base_id = stat_pool.get('base_id', '').lower()
                            quote_id = stat_pool.get('quote_id', '').lower()

                            # Check if this is HOLDER/USDT pool (USDT is base, HOLDER is quote)
                            if (quote_id == HOLDER_CONTRACT.lower() and
                                stat_pool.get('base_symbol') in ['USD₮', 'USDT']):
                                volume_usdt = float(stat_pool.get('base_volume', 0))
                                break

                return {
                    'source': 'stonfi_dex_usdt',
                    'pair': 'HOLDER/USDT',
                    'price': price_in_usdt,
                    'price_usd': price_in_usdt,
                    'change_24h': 0,  # Calculated from DB
                    'volume_24h': volume_usdt,
                    'high_24h': 0,  # Calculated from DB
                    'low_24h': 0,  # Calculated from DB
                    'timestamp': utc_now_iso(),
                    'pool_address': pool.get('address'),
                    'liquidity_usd': float(pool.get('lp_total_supply_usd', 0))
                }

        except Exception as e:
            logger.error(f"Error fetching STON.fi USDT price: {e}")
            return None

    async def get_origami_price(self) -> Optional[Dict]:
        """
        Get HOLDER price from Origami API (WEEX CEX data).
        symbol_id=36380 for HOLDER
        Note: This API only returns last_price, no other market data.
        Includes retry logic with exponential backoff for rate limiting.
        """
        import asyncio

        session = await self._get_session()
        url = "https://api.origami.tech/api/market/public/ticker?symbol_id=36380"

        max_retries = 3

        for attempt in range(max_retries):
            try:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        response_data = await response.json()

                        # Extract data object from response
                        data = response_data.get('data', {})

                        # Origami API only returns last_price
                        last_price = float(data.get('last_price', 0))

                        return {
                            'source': 'weex_cex',
                            'pair': 'HOLDER/USDT',
                            'price': last_price,
                            'price_usd': last_price,
                            'change_24h': 0,  # Calculated from DB
                            'volume_24h': 0,  # Not available from API
                            'high_24h': 0,  # Calculated from DB
                            'low_24h': 0,  # Calculated from DB
                            'timestamp': utc_now_iso(),
                            'bid': 0,  # Not available from API
                            'ask': 0  # Not available from API
                        }

                    elif response.status == 429:
                        # Rate limit - wait longer with exponential backoff
                        wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                        logger.warning(f"Origami API rate limit (429), attempt {attempt + 1}/{max_retries}, waiting {wait_time}s")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error("Origami API rate limit - all retries exhausted")
                            return None

                    else:
                        logger.error(f"Origami API returned status {response.status}")
                        return None

            except asyncio.TimeoutError:
                logger.warning(f"Origami API timeout, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error("Origami API timeout - all retries exhausted")
                    return None

            except Exception as e:
                logger.error(f"Error fetching Origami/WEEX price: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    return None

        return None

    async def get_all_prices(self) -> Dict:
        """
        Get prices from all sources concurrently.
        Cached for 30 seconds to reduce API load.
        """
        # Check cache first (30 second TTL)
        cached = self.cache.get('all_prices', max_age_seconds=30)
        if cached is not None:
            logger.debug("Returning cached prices")
            return cached

        # Cache miss - fetch fresh data
        import asyncio

        # Fetch all prices concurrently
        stonfi_ton_task = self.get_stonfi_price()
        stonfi_usdt_task = self.get_stonfi_usdt_price()
        origami_task = self.get_origami_price()

        stonfi_ton_price, stonfi_usdt_price, origami_price = await asyncio.gather(
            stonfi_ton_task,
            stonfi_usdt_task,
            origami_task,
            return_exceptions=True
        )

        prices = {}

        if stonfi_ton_price and not isinstance(stonfi_ton_price, Exception):
            prices['dex_ton'] = stonfi_ton_price
            self.previous_prices['dex_ton'] = stonfi_ton_price.get('price')

        if stonfi_usdt_price and not isinstance(stonfi_usdt_price, Exception):
            prices['dex_usdt'] = stonfi_usdt_price
            self.previous_prices['dex_usdt'] = stonfi_usdt_price.get('price')

        if origami_price and not isinstance(origami_price, Exception):
            prices['cex'] = origami_price
            self.previous_prices['cex'] = origami_price.get('price')

        # Enrich with database statistics
        await self.enrich_with_db_stats(prices)

        # Only cache if we have complete data (at least one DEX and CEX)
        has_dex = 'dex_ton' in prices or 'dex_usdt' in prices
        has_cex = 'cex' in prices

        if has_dex and has_cex:
            self.cache.set('all_prices', prices)
            logger.debug("Cached complete price data (DEX + CEX)")
        else:
            logger.warning(f"Not caching incomplete price data (has_dex={has_dex}, has_cex={has_cex})")

        return prices

    async def enrich_with_db_stats(self, prices: Dict) -> None:
        """
        Enrich price data with 24h statistics from database.
        Calculates change_24h, high_24h, low_24h from historical data.
        """
        from shared.database import Database

        try:
            db = Database()

            for source_key, price_data in prices.items():
                source = price_data.get('source')
                current_price = price_data.get('price', 0)

                if not source or not current_price:
                    continue

                # Get 24h price history from database
                history = await db.get_price_history(
                    source=source,
                    hours=24,
                    limit=1000
                )

                if history and len(history) > 1:
                    # Extract prices from history (newest to oldest)
                    historical_prices = [float(h.get('price', 0)) for h in history if h.get('price')]

                    if historical_prices:
                        # Calculate high and low
                        price_data['high_24h'] = max(historical_prices + [current_price])
                        price_data['low_24h'] = min(historical_prices + [current_price])

                        # Calculate change from oldest price in 24h window (last item in list)
                        oldest_price = historical_prices[-1]
                        if oldest_price > 0:
                            change_percent = ((current_price - oldest_price) / oldest_price) * 100
                            price_data['change_24h'] = change_percent

        except Exception as e:
            logger.error(f"Error enriching with DB stats: {e}")
            # Continue without enrichment if there's an error

    async def get_24h_stats(self) -> Dict:
        """Get comprehensive 24h statistics."""
        prices = await self.get_all_prices()

        stats = {
            'dex_ton': None,
            'dex_usdt': None,
            'cex': None,
            'arbitrage': None
        }

        if prices.get('dex_ton'):
            dex_ton = prices['dex_ton']
            stats['dex_ton'] = {
                'high': dex_ton.get('high_24h'),
                'low': dex_ton.get('low_24h'),
                'volume': dex_ton.get('volume_24h'),
                'change': dex_ton.get('change_24h'),
                'current': dex_ton.get('price'),
                'price_usd': dex_ton.get('price_usd'),  # USD equivalent
                'liquidity': dex_ton.get('liquidity_usd')
            }

        if prices.get('dex_usdt'):
            dex_usdt = prices['dex_usdt']
            stats['dex_usdt'] = {
                'high': dex_usdt.get('high_24h'),
                'low': dex_usdt.get('low_24h'),
                'volume': dex_usdt.get('volume_24h'),
                'change': dex_usdt.get('change_24h'),
                'current': dex_usdt.get('price'),
                'liquidity': dex_usdt.get('liquidity_usd')
            }

        if prices.get('cex'):
            cex = prices['cex']
            stats['cex'] = {
                'high': cex.get('high_24h'),
                'low': cex.get('low_24h'),
                'volume': cex.get('volume_24h'),
                'change': cex.get('change_24h'),
                'current': cex.get('price')
            }

        # Calculate arbitrage opportunities between DEX USDT and CEX
        if prices.get('dex_usdt') and prices.get('cex'):
            dex_usdt_price = prices['dex_usdt'].get('price', 0)
            cex_price = prices['cex'].get('price_usd', 0)

            if dex_usdt_price and cex_price:
                diff_percent = ((dex_usdt_price - cex_price) / cex_price * 100) if cex_price else 0

                stats['arbitrage'] = {
                    'dex_price': dex_usdt_price,
                    'cex_price': cex_price,
                    'difference_percent': diff_percent,
                    'opportunity': abs(diff_percent) > 2.0  # Flag if >2% difference
                }

        return stats

    def check_significant_changes(
        self,
        current_prices: Dict,
        threshold: float = 5.0
    ) -> List[Dict]:
        """
        Check for significant price changes.

        Args:
            current_prices: Current prices from all sources
            threshold: Percentage threshold for alerts (default 5%)

        Returns:
            List of significant changes
        """
        changes = []

        for source_key, price_data in current_prices.items():
            if source_key not in self.previous_prices:
                continue

            current_price = price_data.get('price')
            previous_price = self.previous_prices.get(source_key)

            if current_price and previous_price:
                try:
                    current = float(current_price)
                    previous = float(previous_price)

                    percent_change = ((current - previous) / previous) * 100

                    if abs(percent_change) >= threshold:
                        changes.append({
                            'source': price_data.get('source', source_key),
                            'pair': price_data.get('pair', 'HOLDER'),
                            'percent': percent_change,
                            'new_price': current,
                            'old_price': previous,
                            'timestamp': datetime.now().isoformat()
                        })
                except (ValueError, TypeError) as e:
                    logger.error(f"Error calculating change for {source_key}: {e}")

        return changes

    def check_arbitrage_opportunity(
        self,
        prices: Dict,
        threshold: float = 2.0
    ) -> Optional[Dict]:
        """
        Check for arbitrage opportunities between DEX USDT and CEX.

        Args:
            prices: Current prices from all sources
            threshold: Minimum percentage difference for opportunity

        Returns:
            Arbitrage opportunity details or None
        """
        if not prices.get('dex_usdt') or not prices.get('cex'):
            return None

        dex_usdt_price = prices['dex_usdt'].get('price')
        cex_price = prices['cex'].get('price_usd')

        if not dex_usdt_price or not cex_price:
            return None

        # Calculate percentage difference
        diff_percent = ((dex_usdt_price - cex_price) / cex_price * 100)

        if abs(diff_percent) >= threshold:
            buy_on = 'STON.fi DEX' if diff_percent > 0 else 'WEEX CEX'
            sell_on = 'WEEX CEX' if diff_percent > 0 else 'STON.fi DEX'

            return {
                'buy_on': buy_on,
                'sell_on': sell_on,
                'buy_price': cex_price if buy_on == 'WEEX CEX' else dex_usdt_price,
                'sell_price': dex_usdt_price if sell_on == 'STON.fi DEX' else cex_price,
                'profit_percent': abs(diff_percent),
                'timestamp': datetime.now().isoformat()
            }

        return None

    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
