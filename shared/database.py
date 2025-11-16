"""
Database module for HOLDER Price Bot with PostgreSQL support
Supports both SQLite (local) and PostgreSQL (production)
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from shared.timezone_utils import utc_now_iso

logger = logging.getLogger(__name__)

# Check if PostgreSQL is available
DATABASE_URL = os.getenv('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    logger.info("Using PostgreSQL database")
else:
    import sqlite3
    logger.info("Using SQLite database")


class Database:
    """Database manager with support for SQLite and PostgreSQL."""

    def __init__(self, db_path: str = "data/holder_bot.db"):
        self.db_path = db_path
        self.database_url = DATABASE_URL

        if not USE_POSTGRES:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.init_database()

    def get_connection(self):
        """Get database connection (SQLite or PostgreSQL)."""
        if USE_POSTGRES:
            conn = psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
            return conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def init_database(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if USE_POSTGRES:
            # PostgreSQL schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id SERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    price DOUBLE PRECISION NOT NULL,
                    price_usd DOUBLE PRECISION,
                    volume_24h DOUBLE PRECISION,
                    high_24h DOUBLE PRECISION,
                    low_24h DOUBLE PRECISION,
                    change_24h DOUBLE PRECISION,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_timestamp
                ON price_history(timestamp, source)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_alerts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    alert_type TEXT NOT NULL,
                    threshold DOUBLE PRECISION DEFAULT 5.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id, alert_type)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_portfolios (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount DOUBLE PRECISION NOT NULL,
                    buy_price DOUBLE PRECISION NOT NULL,
                    buy_source TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS arbitrage_history (
                    id SERIAL PRIMARY KEY,
                    dex_price DOUBLE PRECISION NOT NULL,
                    cex_price DOUBLE PRECISION NOT NULL,
                    profit_percent DOUBLE PRECISION NOT NULL,
                    buy_on TEXT NOT NULL,
                    sell_on TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        else:
            # SQLite schema (original)
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

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_timestamp
                ON price_history(timestamp, source)
            """)

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

        db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"
        logger.info(f"{db_type} database initialized")

    async def save_price(self, price_data: Dict) -> bool:
        """Save price data to history."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            placeholder = "%s" if USE_POSTGRES else "?"

            cursor.execute(f"""
                INSERT INTO price_history
                (source, pair, price, price_usd, volume_24h, high_24h, low_24h, change_24h, timestamp)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                        {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (
                price_data.get('source'),
                price_data.get('pair'),
                price_data.get('price'),
                price_data.get('price_usd'),
                price_data.get('volume_24h'),
                price_data.get('high_24h'),
                price_data.get('low_24h'),
                price_data.get('change_24h'),
                price_data.get('timestamp', utc_now_iso())
            ))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error saving price to database: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False

        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {e}")

    async def get_price_history(
        self,
        source: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[Dict]:
        """Get price history from database."""
        conn = None
        try:
            # Validate inputs to prevent SQL injection
            hours = int(hours)  # Ensure hours is an integer
            limit = int(limit)  # Ensure limit is an integer

            conn = self.get_connection()
            cursor = conn.cursor()

            if USE_POSTGRES:
                # PostgreSQL doesn't support placeholders in INTERVAL, so we validate and cast to int
                query = f"""
                    SELECT * FROM price_history
                    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                """
            else:
                # SQLite doesn't support placeholders in datetime modifier, validate and cast to int
                query = f"""
                    SELECT * FROM price_history
                    WHERE datetime(timestamp) >= datetime('now', '-{hours} hours')
                """

            params = []
            if source:
                placeholder = "%s" if USE_POSTGRES else "?"
                query += f" AND source = {placeholder}"
                params.append(source)

            # Limit is validated as int above, safe to use in f-string
            query += f" ORDER BY timestamp DESC LIMIT {limit}"

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            return []

        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {e}")

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

            placeholder = "%s" if USE_POSTGRES else "?"

            if USE_POSTGRES:
                # PostgreSQL upsert
                cursor.execute(f"""
                    INSERT INTO user_alerts (user_id, chat_id, alert_type, threshold, is_active)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, TRUE)
                    ON CONFLICT (user_id, chat_id, alert_type)
                    DO UPDATE SET threshold = EXCLUDED.threshold, is_active = TRUE
                """, (user_id, chat_id, alert_type, threshold))
            else:
                # SQLite upsert
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

            placeholder = "%s" if USE_POSTGRES else "?"

            cursor.execute(f"""
                UPDATE user_alerts
                SET is_active = FALSE
                WHERE user_id = {placeholder} AND chat_id = {placeholder} AND alert_type = {placeholder}
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

            query = "SELECT * FROM user_alerts WHERE is_active = TRUE" if USE_POSTGRES else "SELECT * FROM user_alerts WHERE is_active = 1"

            if alert_type:
                placeholder = "%s" if USE_POSTGRES else "?"
                query += f" AND alert_type = {placeholder}"
                cursor.execute(query, (alert_type,))
            else:
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

            placeholder = "%s" if USE_POSTGRES else "?"

            cursor.execute(f"""
                INSERT INTO user_portfolios
                (user_id, amount, buy_price, buy_source, notes)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
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

            placeholder = "%s" if USE_POSTGRES else "?"

            cursor.execute(f"""
                SELECT * FROM user_portfolios
                WHERE user_id = {placeholder}
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

            placeholder = "%s" if USE_POSTGRES else "?"

            cursor.execute(f"""
                DELETE FROM user_portfolios
                WHERE id = {placeholder} AND user_id = {placeholder}
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

            placeholder = "%s" if USE_POSTGRES else "?"

            cursor.execute(f"""
                INSERT INTO arbitrage_history
                (dex_price, cex_price, profit_percent, buy_on, sell_on)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
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

            if USE_POSTGRES:
                cursor.execute("""
                    DELETE FROM price_history
                    WHERE created_at < NOW() - INTERVAL '%s days'
                """ % days)
            else:
                cursor.execute("""
                    DELETE FROM price_history
                    WHERE datetime(created_at) < datetime('now', '-%s days')
                """ % days)

            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            logger.info(f"Cleaned up {deleted} old price records")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return False
