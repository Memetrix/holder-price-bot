#!/usr/bin/env python3
"""
HOLDER Token Price Monitoring Bot
Main bot file with all handlers and background tasks
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from shared.database import Database
from shared.tracker_instance import tracker as price_tracker
from bot.handlers.commands import (
    start_command,
    help_command,
    price_command,
    stats_command,
    arbitrage_command
)
from bot.handlers.portfolio import portfolio_command, show_portfolio
from bot.handlers.alerts import alerts_command, show_alerts_menu, handle_alert_callback
from bot.handlers.charts import chart_command, compare_command

# Load config
from config import BOT_TOKEN, CHECK_INTERVAL, ALERT_THRESHOLD

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global instances
db = Database()


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries from inline buttons."""
    query = update.callback_query
    await query.answer()

    # Route based on callback data
    if query.data == 'start':
        await start_command(update, context)
    elif query.data == 'price':
        await price_command(update, context)
    elif query.data == 'stats':
        await stats_command(update, context)
    elif query.data == 'arbitrage':
        await arbitrage_command(update, context)
    elif query.data == 'compare':
        await compare_command(update, context)
    elif query.data == 'portfolio':
        await show_portfolio(update, context)
    elif query.data.startswith('chart_'):
        await chart_command(update, context)
    elif query.data.startswith('alerts_'):
        if query.data == 'alerts_menu':
            await show_alerts_menu(update, context)
        else:
            await handle_alert_callback(update, context)


async def price_monitoring_task(application: Application) -> None:
    """
    Background task to monitor prices and send alerts.
    Runs continuously and checks for price changes.
    """
    logger.info("Starting price monitoring task...")

    while True:
        try:
            # Get current prices
            prices = await price_tracker.get_all_prices()

            # Save prices to database
            if prices.get('dex_ton'):
                await db.save_price(prices['dex_ton'])
            if prices.get('dex_usdt'):
                await db.save_price(prices['dex_usdt'])
            if prices.get('cex'):
                await db.save_price(prices['cex'])

            # Check for significant price changes
            changes = price_tracker.check_significant_changes(prices, threshold=ALERT_THRESHOLD)

            if changes:
                # Get users with active price alerts
                alerts = await db.get_active_alerts('price_change')

                for change in changes:
                    alert_text = (
                        f"⚠️ *Price Alert!*\n\n"
                        f"Source: *{change['source'].upper()}*\n"
                        f"Pair: `{change['pair']}`\n"
                        f"Change: `{change['percent']:+.2f}%`\n"
                        f"New Price: `${change['new_price']:.6f}`\n"
                        f"Previous: `${change['old_price']:.6f}`"
                    )

                    for alert in alerts:
                        if abs(change['percent']) >= alert['threshold']:
                            try:
                                await application.bot.send_message(
                                    chat_id=alert['chat_id'],
                                    text=alert_text,
                                    parse_mode='Markdown'
                                )
                            except Exception as e:
                                logger.error(f"Failed to send alert to chat {alert['chat_id']}: {e}")

            # Check for arbitrage opportunities
            arb = price_tracker.check_arbitrage_opportunity(prices, threshold=2.0)

            if arb:
                # Save to database
                await db.save_arbitrage_opportunity(arb)

                # Get users with active arbitrage alerts
                arb_alerts = await db.get_active_alerts('arbitrage')

                arb_text = (
                    f"💹 *Arbitrage Opportunity!*\n\n"
                    f"🎯 Buy on: *{arb['buy_on']}*\n"
                    f"   Price: `${arb['buy_price']:.6f}`\n\n"
                    f"💰 Sell on: *{arb['sell_on']}*\n"
                    f"   Price: `${arb['sell_price']:.6f}`\n\n"
                    f"📈 Potential Profit: `{arb['profit_percent']:.2f}%`\n\n"
                    f"⚠️ Don't forget about fees!"
                )

                for alert in arb_alerts:
                    if arb['profit_percent'] >= alert['threshold']:
                        try:
                            await application.bot.send_message(
                                chat_id=alert['chat_id'],
                                text=arb_text,
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Failed to send arbitrage alert to chat {alert['chat_id']}: {e}")

            # Wait before next check
            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            logger.error(f"Error in price monitoring task: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait 1 minute before retrying on error


async def cleanup_task(application: Application) -> None:
    """
    Background task to clean up old data.
    Runs once per day.
    """
    logger.info("Starting cleanup task...")

    while True:
        try:
            # Wait 24 hours
            await asyncio.sleep(86400)

            # Cleanup old price data (keep 30 days)
            await db.cleanup_old_data(days=30)

            logger.info("Cleanup task completed")

        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


async def post_init(application: Application) -> None:
    """Post initialization hook to start background tasks."""
    logger.info("Starting background tasks...")

    # Start price monitoring task
    asyncio.create_task(price_monitoring_task(application))

    # Start cleanup task
    asyncio.create_task(cleanup_task(application))


async def post_shutdown(application: Application) -> None:
    """Cleanup on shutdown."""
    logger.info("Shutting down...")
    await price_tracker.close()


def main() -> None:
    """Start the bot."""
    logger.info("=" * 50)
    logger.info("HOLDER Price Monitoring Bot Starting...")
    logger.info("=" * 50)

    # Create the Application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("arbitrage", arbitrage_command))
    application.add_handler(CommandHandler("chart", chart_command))
    application.add_handler(CommandHandler("compare", compare_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("alerts", alerts_command))

    # Register callback query handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    # Start the Bot
    logger.info("Bot started! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
