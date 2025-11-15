"""
Price tracking module for HOLDER token
Fetches prices from DEX and CEX exchanges
"""

import aiohttp
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PriceTracker:
    """Tracks HOLDER token prices across multiple exchanges."""

    def __init__(self):
        self.previous_prices = {}
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_dex_price(self) -> Optional[Dict]:
        """
        Get HOLDER price from DEX (Origami API).
        API: https://api.origami.tech/api/market/public/ticker?symbol_id=36380
        """
        try:
            session = await self._get_session()
            url = "https://api.origami.tech/api/market/public/ticker?symbol_id=36380"

            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    # Parse Origami API response
                    # Adjust fields based on actual API response structure
                    return {
                        'price': data.get('last_price') or data.get('price'),
                        'change_24h': data.get('price_change_percent'),
                        'volume_24h': data.get('volume_24h') or data.get('volume'),
                        'high_24h': data.get('high_24h'),
                        'low_24h': data.get('low_24h'),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    logger.error(f"DEX API returned status {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching DEX price: {e}")
            return None

    async def get_cex_usdt_price(self) -> Optional[Dict]:
        """
        Get HOLDER/USDT price from CEX.
        Note: Replace with actual CEX API endpoint
        """
        try:
            # TODO: Replace with actual CEX API for HOLDER/USDT
            # Example for common exchanges:
            # Binance: https://api.binance.com/api/v3/ticker/24hr?symbol=HOLDERUSDT
            # OKX: https://www.okx.com/api/v5/market/ticker?instId=HOLDER-USDT
            # Gate.io: https://api.gateio.ws/api/v4/spot/tickers?currency_pair=HOLDER_USDT

            session = await self._get_session()

            # Placeholder - replace with actual CEX API
            # url = "https://api.exchange.com/ticker/HOLDER_USDT"
            # async with session.get(url, timeout=10) as response:
            #     if response.status == 200:
            #         data = await response.json()
            #         return {
            #             'price': data.get('last'),
            #             'change_24h': data.get('change_percent'),
            #             'volume_24h': data.get('volume'),
            #             'timestamp': datetime.now().isoformat()
            #         }

            # Temporary mock data - remove when real API is available
            logger.warning("Using mock data for CEX HOLDER/USDT - replace with real API")
            return None

        except Exception as e:
            logger.error(f"Error fetching CEX USDT price: {e}")
            return None

    async def get_cex_ton_price(self) -> Optional[Dict]:
        """
        Get HOLDER/TON price from CEX.
        Note: Replace with actual CEX API endpoint
        """
        try:
            # TODO: Replace with actual CEX API for HOLDER/TON

            session = await self._get_session()

            # Placeholder - replace with actual CEX API
            # url = "https://api.exchange.com/ticker/HOLDER_TON"
            # async with session.get(url, timeout=10) as response:
            #     if response.status == 200:
            #         data = await response.json()
            #         return {
            #             'price': data.get('last'),
            #             'change_24h': data.get('change_percent'),
            #             'volume_24h': data.get('volume'),
            #             'timestamp': datetime.now().isoformat()
            #         }

            # Temporary mock data - remove when real API is available
            logger.warning("Using mock data for CEX HOLDER/TON - replace with real API")
            return None

        except Exception as e:
            logger.error(f"Error fetching CEX TON price: {e}")
            return None

    async def get_all_prices(self) -> Dict:
        """Get prices from all sources."""
        prices = {}

        # Fetch all prices concurrently
        dex_price = await self.get_dex_price()
        cex_usdt = await self.get_cex_usdt_price()
        cex_ton = await self.get_cex_ton_price()

        if dex_price:
            prices['dex'] = dex_price
            self.previous_prices['dex'] = dex_price.get('price')

        if cex_usdt:
            prices['cex_usdt'] = cex_usdt
            self.previous_prices['cex_usdt'] = cex_usdt.get('price')

        if cex_ton:
            prices['cex_ton'] = cex_ton
            self.previous_prices['cex_ton'] = cex_ton.get('price')

        return prices

    async def get_24h_stats(self) -> Dict:
        """Get 24h statistics for HOLDER token."""
        stats = {}

        dex_price = await self.get_dex_price()

        if dex_price:
            stats['dex'] = {
                'high': dex_price.get('high_24h'),
                'low': dex_price.get('low_24h'),
                'volume': dex_price.get('volume_24h'),
                'change': dex_price.get('change_24h')
            }

        return stats

    def check_significant_changes(self, current_prices: Dict, threshold: float = 5.0) -> List[Dict]:
        """
        Check for significant price changes.

        Args:
            current_prices: Current prices from all sources
            threshold: Percentage threshold for alerts (default 5%)

        Returns:
            List of changes that exceed threshold
        """
        changes = []

        for source, price_data in current_prices.items():
            if source not in self.previous_prices:
                continue

            current_price = price_data.get('price')
            previous_price = self.previous_prices.get(source)

            if current_price and previous_price:
                try:
                    current = float(current_price)
                    previous = float(previous_price)

                    percent_change = ((current - previous) / previous) * 100

                    if abs(percent_change) >= threshold:
                        changes.append({
                            'source': source.upper(),
                            'percent': percent_change,
                            'new_price': current,
                            'old_price': previous,
                            'timestamp': datetime.now().isoformat()
                        })
                except (ValueError, TypeError) as e:
                    logger.error(f"Error calculating change for {source}: {e}")

        return changes

    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
