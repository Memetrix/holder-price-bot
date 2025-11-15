"""
Price tracking module for HOLDER token
Integrates STON.fi DEX and Origami/WEEX CEX APIs
"""

import aiohttp
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# HOLDER Token Contract Address on TON
HOLDER_CONTRACT = "EQCDuRLTylau8yKEkx1AMLpHAy6Vog_5D6aC4HNkyG8JN-me"

# TON Native Token Address
TON_CONTRACT = "EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c"


class PriceTracker:
    """Tracks HOLDER token prices across DEX and CEX."""

    def __init__(self):
        self.previous_prices = {}
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_stonfi_price(self) -> Optional[Dict]:
        """
        Get HOLDER price from STON.fi DEX.
        Uses HOLDER/TON pool.
        """
        try:
            session = await self._get_session()

            # Get pool statistics for HOLDER/TON pair
            since = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')
            until = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

            url = f"https://api.ston.fi/v1/stats/pool?since={since}&until={until}"

            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()

                    # Find HOLDER pool in stats
                    for pool in data.get('stats', []):
                        base_addr = pool.get('base_address', '').lower()
                        quote_addr = pool.get('quote_address', '').lower()

                        # Check if this is HOLDER pool
                        if (HOLDER_CONTRACT.lower() in [base_addr, quote_addr]):
                            return {
                                'source': 'stonfi_dex',
                                'pair': f"{pool.get('base_symbol')}/{pool.get('quote_symbol')}",
                                'price': float(pool.get('last_price', 0)),
                                'price_usd': None,  # Will calculate if needed
                                'change_24h': float(pool.get('price_change_percent', 0)),
                                'volume_24h': float(pool.get('quote_volume', 0)),
                                'high_24h': float(pool.get('high_24h', 0)),
                                'low_24h': float(pool.get('low_24h', 0)),
                                'timestamp': datetime.now().isoformat(),
                                'pool_address': pool.get('pool_address')
                            }

                    # If not found in stats, try to get pool directly
                    pool_url = f"https://api.ston.fi/v1/pools/by_market/{HOLDER_CONTRACT}/{TON_CONTRACT}"
                    async with session.get(pool_url, timeout=10) as pool_response:
                        if pool_response.status == 200:
                            pool_data = await pool_response.json()
                            logger.info(f"STON.fi pool data: {pool_data}")

                    logger.warning("HOLDER pool not found in STON.fi stats")
                    return None
                else:
                    logger.error(f"STON.fi API returned status {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching STON.fi price: {e}")
            return None

    async def get_origami_price(self) -> Optional[Dict]:
        """
        Get HOLDER price from Origami API (WEEX CEX data).
        symbol_id=36380 for HOLDER
        """
        try:
            session = await self._get_session()
            url = "https://api.origami.tech/api/market/public/ticker?symbol_id=36380"

            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    # Parse Origami API response
                    return {
                        'source': 'weex_cex',
                        'pair': data.get('symbol') or 'HOLDER/USDT',
                        'price': float(data.get('last_price') or data.get('last') or 0),
                        'price_usd': float(data.get('last_price') or data.get('last') or 0),
                        'change_24h': float(data.get('price_change_percent') or data.get('change_24h') or 0),
                        'volume_24h': float(data.get('volume_24h') or data.get('volume') or 0),
                        'high_24h': float(data.get('high_24h') or data.get('high') or 0),
                        'low_24h': float(data.get('low_24h') or data.get('low') or 0),
                        'timestamp': datetime.now().isoformat(),
                        'bid': float(data.get('bid') or 0),
                        'ask': float(data.get('ask') or 0)
                    }
                else:
                    logger.error(f"Origami API returned status {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching Origami/WEEX price: {e}")
            return None

    async def get_all_prices(self) -> Dict:
        """Get prices from all sources concurrently."""
        import asyncio

        # Fetch all prices concurrently
        stonfi_task = self.get_stonfi_price()
        origami_task = self.get_origami_price()

        stonfi_price, origami_price = await asyncio.gather(
            stonfi_task,
            origami_task,
            return_exceptions=True
        )

        prices = {}

        if stonfi_price and not isinstance(stonfi_price, Exception):
            prices['dex'] = stonfi_price
            self.previous_prices['dex'] = stonfi_price.get('price')

        if origami_price and not isinstance(origami_price, Exception):
            prices['cex'] = origami_price
            self.previous_prices['cex'] = origami_price.get('price')

        return prices

    async def get_24h_stats(self) -> Dict:
        """Get comprehensive 24h statistics."""
        prices = await self.get_all_prices()

        stats = {
            'dex': None,
            'cex': None,
            'arbitrage': None
        }

        if prices.get('dex'):
            dex = prices['dex']
            stats['dex'] = {
                'high': dex.get('high_24h'),
                'low': dex.get('low_24h'),
                'volume': dex.get('volume_24h'),
                'change': dex.get('change_24h'),
                'current': dex.get('price')
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

        # Calculate arbitrage opportunities
        if prices.get('dex') and prices.get('cex'):
            dex_price = prices['dex'].get('price', 0)
            cex_price = prices['cex'].get('price_usd', 0)

            if dex_price and cex_price:
                # Need TON price to convert DEX price to USD
                # For now, calculate percentage difference
                diff_percent = ((cex_price - dex_price) / dex_price * 100) if dex_price else 0

                stats['arbitrage'] = {
                    'dex_price': dex_price,
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
        Check for arbitrage opportunities between DEX and CEX.

        Args:
            prices: Current prices from all sources
            threshold: Minimum percentage difference for opportunity

        Returns:
            Arbitrage opportunity details or None
        """
        if not prices.get('dex') or not prices.get('cex'):
            return None

        dex_price = prices['dex'].get('price')
        cex_price = prices['cex'].get('price_usd')

        if not dex_price or not cex_price:
            return None

        # Calculate percentage difference
        diff_percent = ((cex_price - dex_price) / dex_price * 100)

        if abs(diff_percent) >= threshold:
            buy_on = 'DEX' if diff_percent > 0 else 'CEX'
            sell_on = 'CEX' if diff_percent > 0 else 'DEX'

            return {
                'buy_on': buy_on,
                'sell_on': sell_on,
                'buy_price': dex_price if buy_on == 'DEX' else cex_price,
                'sell_price': cex_price if sell_on == 'CEX' else dex_price,
                'profit_percent': abs(diff_percent),
                'timestamp': datetime.now().isoformat()
            }

        return None

    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
