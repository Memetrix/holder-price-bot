"""
Simple in-memory cache with TTL (Time To Live) support
Used for caching API responses to reduce external API calls
"""

import time
from typing import Optional, Any, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Thread-safe in-memory cache with TTL support.

    Usage:
        cache = SimpleCache()

        # Set value
        cache.set('prices', {'dex': 0.005, 'cex': 0.0048})

        # Get value with TTL check
        prices = cache.get('prices', max_age_seconds=30)
        if prices is None:
            # Cache miss or expired - fetch fresh data
            prices = fetch_prices()
            cache.set('prices', prices)
    """

    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str, max_age_seconds: int = 60) -> Optional[Any]:
        """
        Get value from cache if it exists and not expired.

        Args:
            key: Cache key
            max_age_seconds: Maximum age in seconds (TTL)

        Returns:
            Cached value if found and fresh, None otherwise
        """
        if key not in self._cache:
            logger.debug(f"Cache MISS: {key} (not found)")
            return None

        value, timestamp = self._cache[key]
        age = time.time() - timestamp

        if age > max_age_seconds:
            logger.debug(f"Cache EXPIRED: {key} (age: {age:.1f}s, max: {max_age_seconds}s)")
            # Remove expired entry
            del self._cache[key]
            return None

        logger.debug(f"Cache HIT: {key} (age: {age:.1f}s)")
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Store value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, time.time())
        logger.debug(f"Cache SET: {key}")

    def invalidate(self, key: str) -> None:
        """
        Remove key from cache.

        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache INVALIDATE: {key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.debug(f"Cache CLEAR: {count} entries removed")

    def cleanup_expired(self, max_age_seconds: int = 600) -> int:
        """
        Remove all expired entries older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age threshold

        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if now - timestamp > max_age_seconds
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries")

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        now = time.time()
        ages = [now - timestamp for _, timestamp in self._cache.values()]

        return {
            'total_entries': len(self._cache),
            'oldest_entry_age': max(ages) if ages else 0,
            'newest_entry_age': min(ages) if ages else 0,
            'average_age': sum(ages) / len(ages) if ages else 0
        }
