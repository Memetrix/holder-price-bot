"""
Chart generation module for HOLDER Price Bot
Creates matplotlib charts for Telegram bot
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict, Optional
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generates price charts for Telegram bot."""

    def __init__(self):
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')

    def generate_price_chart(
        self,
        price_data: List[Dict],
        title: str = "HOLDER Price History",
        period: str = "24h"
    ) -> Optional[BytesIO]:
        """
        Generate price chart from historical data.

        Args:
            price_data: List of price records with timestamp and price
            title: Chart title
            period: Time period label

        Returns:
            BytesIO object containing PNG image or None if error
        """
        try:
            if not price_data:
                logger.warning("No price data to generate chart")
                return None

            # Sort by timestamp
            sorted_data = sorted(price_data, key=lambda x: x['timestamp'])

            # Extract timestamps and prices
            timestamps = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')) for d in sorted_data]
            prices = [float(d['price']) for d in sorted_data]

            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))

            # Plot price line
            ax.plot(timestamps, prices, color='#2E86DE', linewidth=2, label='Price')

            # Fill area under curve
            ax.fill_between(timestamps, prices, alpha=0.3, color='#2E86DE')

            # Format
            ax.set_title(f'{title} ({period})', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Price (USDT)', fontsize=12)

            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.xticks(rotation=45)

            # Grid
            ax.grid(True, alpha=0.3)

            # Add current price annotation
            if prices:
                last_price = prices[-1]
                ax.annotate(
                    f'${last_price:.4f}',
                    xy=(timestamps[-1], last_price),
                    xytext=(10, 10),
                    textcoords='offset points',
                    fontsize=11,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7)
                )

            plt.tight_layout()

            # Save to BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf

        except Exception as e:
            logger.error(f"Error generating price chart: {e}")
            plt.close('all')
            return None

    def generate_comparison_chart(
        self,
        dex_data: List[Dict],
        cex_data: List[Dict],
        title: str = "DEX vs CEX Price Comparison"
    ) -> Optional[BytesIO]:
        """
        Generate comparison chart for DEX and CEX prices.

        Args:
            dex_data: DEX price history
            cex_data: CEX price history
            title: Chart title

        Returns:
            BytesIO object containing PNG image or None if error
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            # Plot DEX data
            if dex_data:
                dex_sorted = sorted(dex_data, key=lambda x: x['timestamp'])
                dex_times = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')) for d in dex_sorted]
                dex_prices = [float(d['price']) for d in dex_sorted]
                ax.plot(dex_times, dex_prices, color='#27AE60', linewidth=2, label='DEX (STON.fi)', marker='o')

            # Plot CEX data
            if cex_data:
                cex_sorted = sorted(cex_data, key=lambda x: x['timestamp'])
                cex_times = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')) for d in cex_sorted]
                cex_prices = [float(d['price_usd']) if d.get('price_usd') else float(d['price']) for d in cex_sorted]
                ax.plot(cex_times, cex_prices, color='#E74C3C', linewidth=2, label='CEX (WEEX)', marker='s')

            # Format
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Price (USDT)', fontsize=12)

            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.xticks(rotation=45)

            # Grid and legend
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best', fontsize=11)

            plt.tight_layout()

            # Save to BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf

        except Exception as e:
            logger.error(f"Error generating comparison chart: {e}")
            plt.close('all')
            return None

    def generate_volume_chart(
        self,
        volume_data: List[Dict],
        title: str = "24h Trading Volume"
    ) -> Optional[BytesIO]:
        """
        Generate trading volume chart.

        Args:
            volume_data: Volume history data
            title: Chart title

        Returns:
            BytesIO object containing PNG image or None if error
        """
        try:
            if not volume_data:
                return None

            sorted_data = sorted(volume_data, key=lambda x: x['timestamp'])

            timestamps = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')) for d in sorted_data]
            volumes = [float(d.get('volume_24h', 0)) for d in sorted_data]

            fig, ax = plt.subplots(figsize=(12, 5))

            # Bar chart for volume
            ax.bar(timestamps, volumes, color='#3498DB', alpha=0.7, width=0.02)

            # Format
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Volume (USDT)', fontsize=12)

            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.xticks(rotation=45)

            # Grid
            ax.grid(True, alpha=0.3, axis='y')

            plt.tight_layout()

            # Save to BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf

        except Exception as e:
            logger.error(f"Error generating volume chart: {e}")
            plt.close('all')
            return None

    def generate_arbitrage_chart(
        self,
        arb_data: List[Dict],
        title: str = "Arbitrage Opportunities"
    ) -> Optional[BytesIO]:
        """
        Generate arbitrage opportunities chart.

        Args:
            arb_data: Arbitrage history data
            title: Chart title

        Returns:
            BytesIO object containing PNG image or None if error
        """
        try:
            if not arb_data:
                return None

            sorted_data = sorted(arb_data, key=lambda x: x['timestamp'])

            timestamps = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')) for d in sorted_data]
            profit_percents = [float(d['profit_percent']) for d in sorted_data]

            fig, ax = plt.subplots(figsize=(12, 6))

            # Color bars based on profit direction
            colors = ['#27AE60' if p > 0 else '#E74C3C' for p in profit_percents]
            ax.bar(timestamps, profit_percents, color=colors, alpha=0.7)

            # Add horizontal line at 0
            ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

            # Format
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Profit Potential (%)', fontsize=12)

            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.xticks(rotation=45)

            # Grid
            ax.grid(True, alpha=0.3, axis='y')

            plt.tight_layout()

            # Save to BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf

        except Exception as e:
            logger.error(f"Error generating arbitrage chart: {e}")
            plt.close('all')
            return None
