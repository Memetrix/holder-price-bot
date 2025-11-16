"""
Global PriceTracker instance shared across all modules.
Ensures cache consistency and reduces API calls.
"""

from shared.price_tracker import PriceTracker

# Singleton instance used by bot, handlers, and background tasks
tracker = PriceTracker()
