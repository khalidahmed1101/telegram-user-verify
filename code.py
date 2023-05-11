
import os
import psycopg2
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler
from datetime import timedelta
import schedule

# PostgreSQL database connection parameters
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'telegram'
DB_USER = 'khan'
DB_PASSWORD = 'khan123'

# Telegram Bot token
BOT_TOKEN = '5796853731:AAEUdOINfBCClzHBt6_fPE4cpGXxmDhfo_0'

# Telegram private group ID
PRIVATE_GROUP_ID = '5j1KODgZwEZmYzZk'

async def start(update: Update, context):
    """Handle the /start command."""
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    message = f"Your ID: {user_id}\nYour Username: {username}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

async def let_me_in(update: Update, context):
    """Handle the /let-me-in command."""
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    user_id_str = str(user_id)

    # Check if user exists in the remote database
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id_str,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    try:
        invite_link = f"https://t.me/joinchat/{PRIVATE_GROUP_ID}/{user_id_str}"
        await context.bot.send_message(chat_id=update.message.chat_id, text=invite_link)
    
    except Exception as e:
        # Handle any errors that occur during the invite link generation process
        error_message = f"An error occurred: {str(e)}"
        await context.bot.send_message(chat_id=update.message.chat_id, text=error_message)


async def tell_me_my_id(update: Update, context):
    """Handler for the /tell-me-my-id command"""
    user = update.effective_user
    message = f"Your id is {user.id} and your username is {user.first_name}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


def cronjob_task(context) -> None:
    """Cronjob task to ban users from the private channel."""
    # Connect to the remote database
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()

    # Get the list of users to ban from the remote database
    cursor.execute("SELECT user_id FROM banned_users")
    banned_users = cursor.fetchall()

    # Ban each user from the private channel
    bot = context.bot
    for user_id in banned_users:
        bot.kick_chat_member(chat_id=PRIVATE_GROUP_ID, user_id=user_id[0])

    cursor.close()
    conn.close()

def main() -> None:
    """Main function to start the Telegram bot."""
    # Create the updater and dispatcher
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('tellmemyid', tell_me_my_id))
    application.add_handler(CommandHandler('letmein', let_me_in))
    schedule.every(24).hours.do(cronjob_task)  # Run every 24 hours

    # Start the bot
    application.run_polling()

    # Add the cron job to the scheduler
    
if __name__ == '__main__':
    main()
