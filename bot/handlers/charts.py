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
    """Generate and send price charts for all sources."""
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

    # Get price history for all sources
    dex_ton_history = await db.get_price_history(source='stonfi_dex', hours=hours, limit=1000)
    dex_usdt_history = await db.get_price_history(source='stonfi_dex_usdt', hours=hours, limit=1000)
    cex_history = await db.get_price_history(source='weex_cex', hours=hours, limit=1000)

    # Check if we have any data
    if not dex_ton_history and not dex_usdt_history and not cex_history:
        await message.reply_text(
            "❌ Недостаточно данных для построения графика.\n"
            "Бот должен проработать некоторое время для накопления истории цен."
        )
        return

    # Generate combined chart with all sources
    chart_buf = chart_gen.generate_multi_source_chart(
        dex_ton_history,
        dex_usdt_history,
        cex_history,
        title="HOLDER Price - All Sources",
        period=period
    )

    if not chart_buf:
        await message.reply_text("❌ Ошибка при генерации графика.")
        return

    # Build caption with data points info
    caption_parts = [f"📊 **HOLDER Price ({period})**\n"]

    if dex_ton_history:
        caption_parts.append(f"🟢 DEX TON: {len(dex_ton_history)} точек")
    if dex_usdt_history:
        caption_parts.append(f"🟢 DEX USDT: {len(dex_usdt_history)} точек")
    if cex_history:
        caption_parts.append(f"🔵 CEX: {len(cex_history)} точек")

    # Send chart
    await message.reply_photo(
        photo=InputFile(chart_buf, filename=f'holder_all_sources_{period}.png'),
        caption="\n".join(caption_parts),
        parse_mode='Markdown'
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
