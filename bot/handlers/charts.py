"""
Chart generation handlers
"""

from telegram import Update, InputFile
from telegram.ext import ContextTypes
from shared.database import Database
from shared.charts import ChartGenerator
import logging

logger = logging.getLogger(__name__)
db = Database()
chart_gen = ChartGenerator()


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send price chart."""
    message = update.message or update.callback_query.message

    # Parse period from args or callback data
    period = '24h'
    hours = 24

    if context.args and len(context.args) > 0:
        period_arg = context.args[0].lower()
        if period_arg == '1h':
            period = '1h'
            hours = 1
        elif period_arg == '7d':
            period = '7d'
            hours = 168
        elif period_arg == '30d':
            period = '30d'
            hours = 720

    if update.callback_query:
        if 'chart_1h' in update.callback_query.data:
            period = '1h'
            hours = 1
        elif 'chart_24h' in update.callback_query.data:
            period = '24h'
            hours = 24
        elif 'chart_7d' in update.callback_query.data:
            period = '7d'
            hours = 168

    await message.reply_text(f"📊 Генерирую график за {period}...")

    # Get price history from database
    price_history = await db.get_price_history(source='weex_cex', hours=hours, limit=1000)

    if not price_history:
        await message.reply_text(
            "❌ Недостаточно данных для построения графика.\n"
            "Бот должен проработать некоторое время для накопления истории цен."
        )
        return

    # Generate chart
    chart_buf = chart_gen.generate_price_chart(
        price_history,
        title=f"HOLDER Price ({period})",
        period=period
    )

    if not chart_buf:
        await message.reply_text("❌ Ошибка при генерации графика.")
        return

    # Send chart
    await message.reply_photo(
        photo=InputFile(chart_buf, filename=f'holder_price_{period}.png'),
        caption=f"📈 График цены HOLDER за {period}"
    )


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate comparison chart for DEX vs CEX."""
    message = update.message or update.callback_query.message

    await message.reply_text("📊 Генерирую сравнительный график DEX vs CEX...")

    # Get price history for both sources
    dex_history = await db.get_price_history(source='stonfi_dex', hours=24, limit=500)
    cex_history = await db.get_price_history(source='weex_cex', hours=24, limit=500)

    if not dex_history and not cex_history:
        await message.reply_text(
            "❌ Недостаточно данных для построения графика.\n"
            "Бот должен проработать некоторое время для накопления истории цен."
        )
        return

    # Generate comparison chart
    chart_buf = chart_gen.generate_comparison_chart(
        dex_history,
        cex_history,
        title="HOLDER: DEX vs CEX (24h)"
    )

    if not chart_buf:
        await message.reply_text("❌ Ошибка при генерации графика.")
        return

    # Calculate average difference
    if dex_history and cex_history:
        # Simple average for caption
        avg_dex = sum(float(d['price']) for d in dex_history) / len(dex_history)
        avg_cex = sum(float(d['price_usd']) if d.get('price_usd') else float(d['price']) for d in cex_history) / len(cex_history)
        diff_percent = ((avg_cex - avg_dex) / avg_dex * 100) if avg_dex else 0

        caption = (
            f"📊 Сравнение DEX vs CEX (24h)\n\n"
            f"Средняя разница: {diff_percent:+.2f}%\n"
            f"{'CEX дороже' if diff_percent > 0 else 'DEX дороже'}"
        )
    else:
        caption = "📊 Сравнение DEX vs CEX (24h)"

    # Send chart
    await message.reply_photo(
        photo=InputFile(chart_buf, filename='holder_dex_vs_cex.png'),
        caption=caption
    )
