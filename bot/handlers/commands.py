"""
Command handlers for Telegram bot
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Current Price", callback_data='price'),
            InlineKeyboardButton("📈 24h Stats", callback_data='stats')
        ],
        [
            InlineKeyboardButton("🔄 Compare DEX/CEX", callback_data='compare'),
            InlineKeyboardButton("💹 Arbitrage", callback_data='arbitrage')
        ],
        [
            InlineKeyboardButton("📉 Chart 1h", callback_data='chart_1h'),
            InlineKeyboardButton("📊 Chart 24h", callback_data='chart_24h')
        ],
        [
            InlineKeyboardButton("💼 My Portfolio", callback_data='portfolio'),
            InlineKeyboardButton("🔔 Alerts", callback_data='alerts_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "👋 *Привет! Я бот для мониторинга курса токена $HOLDER*\n\n"
        "📍 Отслеживаю цены на:\n"
        "• *STON.fi DEX* - HOLDER/TON\n"
        "• *WEEX CEX* - HOLDER/USDT\n\n"
        "🎯 Что я умею:\n"
        "✅ Показывать текущие цены\n"
        "✅ Статистику за 24 часа\n"
        "✅ Графики изменения цены\n"
        "✅ Арбитражные возможности\n"
        "✅ Портфолио трекинг\n"
        "✅ Уведомления о резких изменениях\n\n"
        "📱 *Команды:*\n"
        "/price - текущий курс\n"
        "/stats - статистика 24ч\n"
        "/arbitrage - арбитраж DEX/CEX\n"
        "/chart - график цены\n"
        "/portfolio - мой портфель\n"
        "/alerts - настройка уведомлений\n\n"
        "👇 Выбери действие:"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    help_text = (
        "*📖 Справка по командам HOLDER Price Bot*\n\n"
        "*Основные команды:*\n"
        "/start - главное меню\n"
        "/price - показать текущие цены на DEX и CEX\n"
        "/stats - статистика за 24 часа\n"
        "/arbitrage - проверить арбитражные возможности\n\n"
        "*Графики:*\n"
        "/chart - график за последние 24 часа\n"
        "/chart 1h - график за 1 час\n"
        "/chart 7d - график за 7 дней\n"
        "/compare - сравнение DEX и CEX\n\n"
        "*Портфолио:*\n"
        "/portfolio - посмотреть свой портфель\n"
        "/portfolio add <amount> <price> - добавить запись\n"
        "   Пример: /portfolio add 1000 0.05\n"
        "/portfolio remove <id> - удалить запись\n\n"
        "*Уведомления:*\n"
        "/alerts - меню уведомлений\n"
        "/alerts on - включить уведомления\n"
        "/alerts off - выключить уведомления\n"
        "/alerts set <threshold> - установить порог (в %)\n"
        "   Пример: /alerts set 3\n\n"
        "*Дополнительно:*\n"
        "/help - это сообщение\n\n"
        "💡 *Совет:* Используй кнопки для быстрого доступа!"
    )

    await update.message.reply_text(help_text, parse_mode='Markdown')


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get current HOLDER token prices."""
    # Import here to avoid circular imports
    from shared.price_tracker import PriceTracker

    message = update.message or update.callback_query.message
    await message.reply_text("⏳ Получаю актуальные данные...")

    tracker = PriceTracker()
    prices = await tracker.get_all_prices()
    await tracker.close()

    if not prices:
        await message.reply_text("❌ Не удалось получить данные о ценах. Попробуйте позже.")
        return

    # Format price message
    price_text = "💰 *HOLDER Token Prices*\n\n"

    if prices.get('dex'):
        dex = prices['dex']
        price_text += f"🟢 *STON.fi DEX*\n"
        price_text += f"Pair: `{dex.get('pair', 'HOLDER/TON')}`\n"
        price_text += f"Price: `{dex.get('price', 0):.6f} TON`\n"
        change = dex.get('change_24h', 0)
        change_emoji = "📈" if change > 0 else "📉"
        price_text += f"24h Change: `{change:+.2f}%` {change_emoji}\n"
        price_text += f"Volume 24h: `{dex.get('volume_24h', 0):.2f} TON`\n\n"

    if prices.get('cex'):
        cex = prices['cex']
        price_text += f"🔵 *WEEX CEX*\n"
        price_text += f"Pair: `{cex.get('pair', 'HOLDER/USDT')}`\n"
        price_text += f"Price: `${cex.get('price', 0):.6f} USDT`\n"
        change = cex.get('change_24h', 0)
        change_emoji = "📈" if change > 0 else "📉"
        price_text += f"24h Change: `{change:+.2f}%` {change_emoji}\n"
        price_text += f"Volume 24h: `${cex.get('volume_24h', 0):,.2f}`\n"
        price_text += f"Bid/Ask: `${cex.get('bid', 0):.6f}` / `${cex.get('ask', 0):.6f}`\n\n"

    price_text += f"🕐 Updated: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"

    # Add refresh button
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data='price')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(price_text, parse_mode='Markdown', reply_markup=reply_markup)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get 24h statistics for HOLDER token."""
    from shared.price_tracker import PriceTracker

    message = update.message or update.callback_query.message
    await message.reply_text("⏳ Собираю статистику...")

    tracker = PriceTracker()
    stats = await tracker.get_24h_stats()
    await tracker.close()

    if not stats or (not stats.get('dex') and not stats.get('cex')):
        await message.reply_text("❌ Не удалось получить статистику. Попробуйте позже.")
        return

    stats_text = "📈 *24h Statistics for $HOLDER*\n\n"

    if stats.get('dex'):
        dex = stats['dex']
        stats_text += f"🟢 *STON.fi DEX*\n"
        stats_text += f"Current: `{dex.get('current', 0):.6f} TON`\n"
        stats_text += f"High: `{dex.get('high', 0):.6f} TON`\n"
        stats_text += f"Low: `{dex.get('low', 0):.6f} TON`\n"
        stats_text += f"Change: `{dex.get('change', 0):+.2f}%`\n"
        stats_text += f"Volume: `{dex.get('volume', 0):.2f} TON`\n\n"

    if stats.get('cex'):
        cex = stats['cex']
        stats_text += f"🔵 *WEEX CEX*\n"
        stats_text += f"Current: `${cex.get('current', 0):.6f}`\n"
        stats_text += f"High: `${cex.get('high', 0):.6f}`\n"
        stats_text += f"Low: `${cex.get('low', 0):.6f}`\n"
        stats_text += f"Change: `{cex.get('change', 0):+.2f}%`\n"
        stats_text += f"Volume: `${cex.get('volume', 0):,.2f}`\n\n"

    if stats.get('arbitrage') and stats['arbitrage'].get('opportunity'):
        arb = stats['arbitrage']
        stats_text += f"💹 *Arbitrage Opportunity!*\n"
        stats_text += f"Difference: `{arb.get('difference_percent', 0):.2f}%`\n\n"

    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data='stats')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)


async def arbitrage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check for arbitrage opportunities."""
    from shared.price_tracker import PriceTracker

    message = update.message or update.callback_query.message
    await message.reply_text("⏳ Проверяю арбитражные возможности...")

    tracker = PriceTracker()
    prices = await tracker.get_all_prices()
    arb = tracker.check_arbitrage_opportunity(prices, threshold=1.0)  # 1% threshold
    await tracker.close()

    if not arb:
        arb_text = (
            "💹 *Arbitrage Check*\n\n"
            "❌ В данный момент выгодных арбитражных возможностей нет.\n\n"
            "Разница между ценами на DEX и CEX меньше 1%."
        )
    else:
        arb_text = (
            "💹 *Arbitrage Opportunity Found!*\n\n"
            f"🎯 *Strategy:*\n"
            f"1️⃣ Buy on: *{arb['buy_on']}*\n"
            f"   Price: `${arb['buy_price']:.6f}`\n\n"
            f"2️⃣ Sell on: *{arb['sell_on']}*\n"
            f"   Price: `${arb['sell_price']:.6f}`\n\n"
            f"💰 *Potential Profit:* `{arb['profit_percent']:.2f}%`\n\n"
            f"⚠️ *Note:* Учитывай комиссии за транзакции и вывод!"
        )

    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data='arbitrage')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(arb_text, parse_mode='Markdown', reply_markup=reply_markup)
