"""
Portfolio management handlers
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from shared.database import Database
import logging

logger = logging.getLogger(__name__)
db = Database()


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle portfolio command."""
    user_id = update.effective_user.id

    # Check if there are arguments
    if context.args:
        action = context.args[0].lower()

        if action == 'add' and len(context.args) >= 3:
            # Add portfolio entry
            try:
                amount = float(context.args[1])
                buy_price = float(context.args[2])
                notes = ' '.join(context.args[3:]) if len(context.args) > 3 else ''

                await db.add_portfolio_entry(user_id, amount, buy_price, 'manual', notes)

                await update.message.reply_text(
                    f"✅ Добавлено в портфель:\n"
                    f"Количество: `{amount:,.2f}` HOLDER\n"
                    f"Цена покупки: `${buy_price:.6f}`\n"
                    f"Общая стоимость: `${amount * buy_price:,.2f}`",
                    parse_mode='Markdown'
                )
                return

            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат.\n"
                    "Используй: /portfolio add <количество> <цена>\n"
                    "Пример: /portfolio add 1000 0.05"
                )
                return

        elif action == 'remove' and len(context.args) >= 2:
            # Remove portfolio entry
            try:
                entry_id = int(context.args[1])
                await db.delete_portfolio_entry(user_id, entry_id)

                await update.message.reply_text(
                    f"✅ Запись #{entry_id} удалена из портфеля",
                    parse_mode='Markdown'
                )
                return

            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат.\n"
                    "Используй: /portfolio remove <id>"
                )
                return

    # Show portfolio
    await show_portfolio(update, context)


async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display user portfolio."""
    from shared.tracker_instance import tracker

    user_id = update.effective_user.id
    message = update.message or update.callback_query.message

    # Get portfolio entries
    portfolio = await db.get_user_portfolio(user_id)

    if not portfolio:
        await message.reply_text(
            "💼 *Ваш портфель пуст*\n\n"
            "Добавь запись командой:\n"
            "`/portfolio add <количество> <цена>`\n\n"
            "Пример:\n"
            "`/portfolio add 1000 0.05`",
            parse_mode='Markdown'
        )
        return

    # Get current price
    prices = await tracker.get_all_prices()

    current_price = prices.get('cex', {}).get('price', 0) if prices.get('cex') else 0

    # Calculate totals
    total_amount = 0
    total_invested = 0
    total_value = 0

    portfolio_text = "💼 *Ваш портфель HOLDER*\n\n"

    for idx, entry in enumerate(portfolio, 1):
        amount = entry['amount']
        buy_price = entry['buy_price']
        invested = amount * buy_price
        current_value = amount * current_price if current_price else 0
        profit = current_value - invested if current_price else 0
        profit_percent = (profit / invested * 100) if invested else 0

        total_amount += amount
        total_invested += invested
        total_value += current_value

        profit_emoji = "🟢" if profit >= 0 else "🔴"

        portfolio_text += (
            f"*#{entry['id']}* - {entry['created_at'][:10]}\n"
            f"Количество: `{amount:,.2f}` HOLDER\n"
            f"Цена покупки: `${buy_price:.6f}`\n"
            f"Вложено: `${invested:,.2f}`\n"
            f"Текущая стоимость: `${current_value:,.2f}`\n"
            f"P/L: `${profit:,.2f}` ({profit_percent:+.2f}%) {profit_emoji}\n\n"
        )

    # Add totals
    total_profit = total_value - total_invested
    total_profit_percent = (total_profit / total_invested * 100) if total_invested else 0
    total_emoji = "🟢" if total_profit >= 0 else "🔴"

    portfolio_text += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*ИТОГО:*\n"
        f"Всего HOLDER: `{total_amount:,.2f}`\n"
        f"Вложено: `${total_invested:,.2f}`\n"
        f"Текущая стоимость: `${total_value:,.2f}`\n"
        f"*P/L: `${total_profit:,.2f}` ({total_profit_percent:+.2f}%)* {total_emoji}\n\n"
        f"Текущая цена: `${current_price:.6f}`\n\n"
        f"💡 Добавить: `/portfolio add <кол-во> <цена>`\n"
        f"🗑 Удалить: `/portfolio remove <id>`"
    )

    # Import navigation helper
    from bot.handlers.commands import get_back_to_menu_keyboard

    keyboard = get_back_to_menu_keyboard(refresh_callback='portfolio')
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(portfolio_text, parse_mode='Markdown', reply_markup=reply_markup)
