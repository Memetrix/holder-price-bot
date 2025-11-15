"""
Database module for HOLDER Price Bot
Stores price history, user data, and portfolios
"""

import sqlite3
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database manager for price history and user data."""

    def __init__(self, db_path: str = "data/holder_bot.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Price history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                pair TEXT NOT NULL,
                price REAL NOT NULL,
                price_usd REAL,
                volume_24h REAL,
                high_24h REAL,
                low_24h REAL,
                change_24h REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index on timestamp for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_timestamp
            ON price_history(timestamp, source)
        """)

        # User alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                threshold REAL DEFAULT 5.0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, chat_id, alert_type)
            )
        """)

        # User portfolios table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                buy_price REAL NOT NULL,
                buy_source TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Arbitrage alerts history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arbitrage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dex_price REAL NOT NULL,
                cex_price REAL NOT NULL,
                profit_percent REAL NOT NULL,
                buy_on TEXT NOT NULL,
                sell_on TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        logger.info(f"Database initialized at {self.db_path}")

    async def save_price(self, price_data: Dict) -> bool:
        """Save price data to history."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO price_history
                (source, pair, price, price_usd, volume_24h, high_24h, low_24h, change_24h, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                price_data.get('source'),
                price_data.get('pair'),
                price_data.get('price'),
                price_data.get('price_usd'),
                price_data.get('volume_24h'),
                price_data.get('high_24h'),
                price_data.get('low_24h'),
                price_data.get('change_24h'),
                price_data.get('timestamp', datetime.now().isoformat())
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error saving price to database: {e}")
            return False

    async def get_price_history(
        self,
        source: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[Dict]:
        """Get price history from database."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT * FROM price_history
                WHERE datetime(timestamp) >= datetime('now', '-{} hours')
            """.format(hours)

            if source:
                query += f" AND source = '{source}'"

            query += f" ORDER BY timestamp DESC LIMIT {limit}"

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            return []

    async def add_user_alert(
        self,
        user_id: int,
        chat_id: int,
        alert_type: str = 'price_change',
        threshold: float = 5.0
    ) -> bool:
        """Add or update user alert."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO user_alerts
                (user_id, chat_id, alert_type, threshold, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (user_id, chat_id, alert_type, threshold))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error adding user alert: {e}")
            return False

    async def remove_user_alert(self, user_id: int, chat_id: int, alert_type: str) -> bool:
        """Remove user alert."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE user_alerts
                SET is_active = 0
                WHERE user_id = ? AND chat_id = ? AND alert_type = ?
            """, (user_id, chat_id, alert_type))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error removing user alert: {e}")
            return False

    async def get_active_alerts(self, alert_type: Optional[str] = None) -> List[Dict]:
        """Get all active user alerts."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM user_alerts WHERE is_active = 1"

            if alert_type:
                query += f" AND alert_type = '{alert_type}'"

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching active alerts: {e}")
            return []

    async def add_portfolio_entry(
        self,
        user_id: int,
        amount: float,
        buy_price: float,
        buy_source: str = 'manual',
        notes: str = ''
    ) -> bool:
        """Add portfolio entry for user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO user_portfolios
                (user_id, amount, buy_price, buy_source, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, amount, buy_price, buy_source, notes))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error adding portfolio entry: {e}")
            return False

    async def get_user_portfolio(self, user_id: int) -> List[Dict]:
        """Get user's portfolio entries."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM user_portfolios
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching user portfolio: {e}")
            return []

    async def delete_portfolio_entry(self, user_id: int, entry_id: int) -> bool:
        """Delete portfolio entry."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM user_portfolios
                WHERE id = ? AND user_id = ?
            """, (entry_id, user_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error deleting portfolio entry: {e}")
            return False

    async def save_arbitrage_opportunity(self, arb_data: Dict) -> bool:
        """Save arbitrage opportunity to history."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO arbitrage_history
                (dex_price, cex_price, profit_percent, buy_on, sell_on)
                VALUES (?, ?, ?, ?, ?)
            """, (
                arb_data.get('buy_price') if arb_data.get('buy_on') == 'DEX' else arb_data.get('sell_price'),
                arb_data.get('buy_price') if arb_data.get('buy_on') == 'CEX' else arb_data.get('sell_price'),
                arb_data.get('profit_percent'),
                arb_data.get('buy_on'),
                arb_data.get('sell_on')
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error saving arbitrage opportunity: {e}")
            return False

    async def cleanup_old_data(self, days: int = 30):
        """Clean up old price history data."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM price_history
                WHERE datetime(created_at) < datetime('now', '-{} days')
            """.format(days))

            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            logger.info(f"Cleaned up {deleted} old price records")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return False
