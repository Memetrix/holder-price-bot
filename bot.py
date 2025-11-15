#!/usr/bin/env python3
"""
HOLDER Token Price Monitoring Bot
Monitors HOLDER token price from DEX and CEX exchanges
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from price_tracker import PriceTracker
from config import BOT_TOKEN, CHECK_INTERVAL, ALERT_THRESHOLD

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global price tracker instance
price_tracker = PriceTracker()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    keyboard = [
        [InlineKeyboardButton("📊 Current Price", callback_data='price')],
        [InlineKeyboardButton("📈 24h Stats", callback_data='stats')],
        [InlineKeyboardButton("🔔 Enable Alerts", callback_data='alerts_on')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "👋 Привет! Я бот для мониторинга курса токена $HOLDER\n\n"
        "Я отслеживаю цены на:\n"
        "• DEX (Origami)\n"
        "• CEX (HOLDER/USDT)\n"
        "• CEX (HOLDER/TON)\n\n"
        "Используй кнопки ниже или команды:\n"
        "/price - текущий курс\n"
        "/stats - статистика за 24ч\n"
        "/alerts - включить уведомления о резких изменениях"
    )

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get current HOLDER token prices from all sources."""
    query = update.callback_query

    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message

    await message.reply_text("⏳ Получаю актуальные данные...")

    prices = await price_tracker.get_all_prices()

    if not prices:
        await message.reply_text("❌ Не удалось получить данные о ценах. Попробуйте позже.")
        return

    # Format price message
    price_text = "💰 *HOLDER Token Prices*\n\n"

    if prices.get('dex'):
        dex = prices['dex']
        price_text += f"🔷 *DEX (Origami)*\n"
        price_text += f"Price: `${dex.get('price', 'N/A')}`\n"
        price_text += f"24h Change: `{dex.get('change_24h', 'N/A')}%`\n"
        price_text += f"Volume 24h: `${dex.get('volume_24h', 'N/A')}`\n\n"

    if prices.get('cex_usdt'):
        cex_usdt = prices['cex_usdt']
        price_text += f"🔶 *CEX HOLDER/USDT*\n"
        price_text += f"Price: `${cex_usdt.get('price', 'N/A')}`\n"
        price_text += f"24h Change: `{cex_usdt.get('change_24h', 'N/A')}%`\n\n"

    if prices.get('cex_ton'):
        cex_ton = prices['cex_ton']
        price_text += f"💎 *CEX HOLDER/TON*\n"
        price_text += f"Price: `{cex_ton.get('price', 'N/A')} TON`\n"
        price_text += f"24h Change: `{cex_ton.get('change_24h', 'N/A')}%`\n\n"

    price_text += f"🕐 Updated: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"

    await message.reply_text(price_text, parse_mode='Markdown')


async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get 24h statistics for HOLDER token."""
    query = update.callback_query

    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message

    await message.reply_text("⏳ Собираю статистику...")

    stats = await price_tracker.get_24h_stats()

    if not stats:
        await message.reply_text("❌ Не удалось получить статистику. Попробуйте позже.")
        return

    stats_text = "📈 *24h Statistics for $HOLDER*\n\n"

    if stats.get('dex'):
        dex = stats['dex']
        stats_text += f"🔷 *DEX*\n"
        stats_text += f"High: `${dex.get('high', 'N/A')}`\n"
        stats_text += f"Low: `${dex.get('low', 'N/A')}`\n"
        stats_text += f"Volume: `${dex.get('volume', 'N/A')}`\n\n"

    await message.reply_text(stats_text, parse_mode='Markdown')


async def toggle_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable/disable price alerts for user."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == 'alerts_on':
        context.application.bot_data.setdefault('alert_users', set()).add(user_id)
        await query.message.reply_text(
            f"🔔 Уведомления включены!\n\n"
            f"Вы будете получать оповещения при изменении цены более чем на {ALERT_THRESHOLD}%"
        )
    else:
        context.application.bot_data.get('alert_users', set()).discard(user_id)
        await query.message.reply_text("🔕 Уведомления отключены")


async def price_monitoring_task(application: Application) -> None:
    """Background task to monitor price changes and send alerts."""
    logger.info("Starting price monitoring task...")

    while True:
        try:
            # Get current prices
            prices = await price_tracker.get_all_prices()

            # Check for significant changes
            changes = price_tracker.check_significant_changes(prices)

            if changes and 'alert_users' in application.bot_data:
                alert_users = application.bot_data['alert_users']

                for change in changes:
                    alert_text = (
                        f"⚠️ *Price Alert!*\n\n"
                        f"Source: {change['source']}\n"
                        f"Change: `{change['percent']:.2f}%`\n"
                        f"New Price: `${change['new_price']}`\n"
                        f"Previous: `${change['old_price']}`"
                    )

                    for user_id in alert_users:
                        try:
                            await application.bot.send_message(
                                chat_id=user_id,
                                text=alert_text,
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Failed to send alert to user {user_id}: {e}")

            # Wait before next check
            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            logger.error(f"Error in price monitoring task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying on error


async def post_init(application: Application) -> None:
    """Post initialization hook to start background tasks."""
    # Start price monitoring task
    asyncio.create_task(price_monitoring_task(application))


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Initialize bot_data
    application.bot_data['alert_users'] = set()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", get_price))
    application.add_handler(CommandHandler("stats", get_stats))
    application.add_handler(CallbackQueryHandler(get_price, pattern='^price$'))
    application.add_handler(CallbackQueryHandler(get_stats, pattern='^stats$'))
    application.add_handler(CallbackQueryHandler(toggle_alerts, pattern='^alerts_'))

    # Start the Bot
    logger.info("Starting HOLDER Price Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
