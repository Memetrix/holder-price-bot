"""
Alert management handlers
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from shared.database import Database
import logging

logger = logging.getLogger(__name__)
db = Database()


async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle alerts command."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if there are arguments
    if context.args:
        action = context.args[0].lower()

        if action == 'on':
            # Enable alerts
            await db.add_user_alert(user_id, chat_id, 'price_change', 5.0)
            await db.add_user_alert(user_id, chat_id, 'arbitrage', 2.0)

            await update.message.reply_text(
                "🔔 *Уведомления включены!*\n\n"
                "Вы будете получать алерты:\n"
                "• При изменении цены >5%\n"
                "• При арбитражных возможностях >2%\n\n"
                "Настроить пороги: `/alerts set <процент>`",
                parse_mode='Markdown'
            )
            return

        elif action == 'off':
            # Disable alerts
            await db.remove_user_alert(user_id, chat_id, 'price_change')
            await db.remove_user_alert(user_id, chat_id, 'arbitrage')

            await update.message.reply_text(
                "🔕 *Уведомления отключены*\n\n"
                "Включить снова: `/alerts on`",
                parse_mode='Markdown'
            )
            return

        elif action == 'set' and len(context.args) >= 2:
            # Set threshold
            try:
                threshold = float(context.args[1])

                await db.add_user_alert(user_id, chat_id, 'price_change', threshold)

                await update.message.reply_text(
                    f"✅ Порог уведомлений установлен: `{threshold}%`\n\n"
                    f"Вы получите уведомление, когда цена изменится более чем на {threshold}%",
                    parse_mode='Markdown'
                )
                return

            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат.\n"
                    "Используй: /alerts set <процент>\n"
                    "Пример: /alerts set 3"
                )
                return

    # Show alerts menu
    await show_alerts_menu(update, context)


async def show_alerts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display alerts menu."""
    user_id = update.effective_user.id
    message = update.message or update.callback_query.message

    # Get active alerts
    alerts = await db.get_active_alerts()
    user_alerts = [a for a in alerts if a['user_id'] == user_id]

    price_alert = next((a for a in user_alerts if a['alert_type'] == 'price_change'), None)
    arb_alert = next((a for a in user_alerts if a['alert_type'] == 'arbitrage'), None)

    alerts_text = "🔔 *Настройки уведомлений*\n\n"

    if price_alert:
        alerts_text += f"✅ Алерты изменения цены: *включены*\n"
        alerts_text += f"   Порог: `{price_alert['threshold']}%`\n\n"
    else:
        alerts_text += f"❌ Алерты изменения цены: *выключены*\n\n"

    if arb_alert:
        alerts_text += f"✅ Арбитражные алерты: *включены*\n"
        alerts_text += f"   Порог: `{arb_alert['threshold']}%`\n\n"
    else:
        alerts_text += f"❌ Арбитражные алерты: *выключены*\n\n"

    alerts_text += (
        "*Команды:*\n"
        "`/alerts on` - включить все уведомления\n"
        "`/alerts off` - выключить все уведомления\n"
        "`/alerts set <процент>` - установить порог\n\n"
        "Пример: `/alerts set 3`"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Включить", callback_data='alerts_on'),
            InlineKeyboardButton("❌ Выключить", callback_data='alerts_off')
        ],
        [InlineKeyboardButton("⚙️ Настроить пороги", callback_data='alerts_config')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(alerts_text, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle alert button callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if query.data == 'alerts_on':
        await db.add_user_alert(user_id, chat_id, 'price_change', 5.0)
        await db.add_user_alert(user_id, chat_id, 'arbitrage', 2.0)

        await query.message.reply_text(
            "🔔 *Уведомления включены!*\n\n"
            "Вы будете получать алерты:\n"
            "• При изменении цены >5%\n"
            "• При арбитражных возможностях >2%",
            parse_mode='Markdown'
        )

    elif query.data == 'alerts_off':
        await db.remove_user_alert(user_id, chat_id, 'price_change')
        await db.remove_user_alert(user_id, chat_id, 'arbitrage')

        await query.message.reply_text(
            "🔕 *Уведомления отключены*",
            parse_mode='Markdown'
        )

    elif query.data == 'alerts_config':
        await query.message.reply_text(
            "⚙️ *Настройка порогов*\n\n"
            "Используй команду:\n"
            "`/alerts set <процент>`\n\n"
            "Примеры:\n"
            "`/alerts set 3` - алерт при изменении >3%\n"
            "`/alerts set 10` - алерт при изменении >10%",
            parse_mode='Markdown'
        )
