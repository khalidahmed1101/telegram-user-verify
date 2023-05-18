
import os
import psycopg2
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, Job
from datetime import datetime, timedelta
import pyshorteners

# PostgreSQL database connection parameters
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'telegram'
DB_USER = 'user'
DB_PASSWORD = 'password'

# Telegram Bot token
BOT_TOKEN = ''

# Telegram private group ID
PRIVATE_GROUP_ID = ''
PRIVATE_GROUP_LINK = ""

application = None  # Global variable to store the Application object

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

    if user:
        print("User ID found in the database.")
        current_time = datetime.now()
        expiry_time = current_time + timedelta(hours=1)

        invite_link = await context.bot.createChatInviteLink(
            chat_id="-100"+PRIVATE_GROUP_ID,
            expire_date= expiry_time,
            member_limit=1,
        )

        try:
            await context.bot.send_message(chat_id=update.message.chat_id, text=invite_link.invite_link)
        
        except Exception as e:
            # Handle any errors that occur during the invite link generation process
            error_message = f"An error occurred: {str(e)}"
            await context.bot.send_message(chat_id=update.message.chat_id, text=error_message)

    else:
        print("User ID not found in the database.")
        await context.bot.send_message(chat_id=update.message.chat_id, text="You are not allowed to join!")
        return

async def tell_me_my_id(update: Update, context):
    """Handler for the /tell-me-my-id command"""
    user = update.effective_user
    message = f"Your id is {user.id} and your username is {user.first_name}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)



# async def cronjob_task_wrapper(application: Application):
async def cronjob_task(context: Application):
    print("*********************** Running Cronjob task to ban users from the private channel. ********************")
    # Connect to the remote database
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()

    # Get the list of users to ban from the remote database
    cursor.execute("SELECT user_id FROM banned_users")
    banned_users = cursor.fetchall()

    # Ban each user from the private channel
    bot = context.bot
    parsed_results = [int(result[0]) for result in banned_users]
    for user_id in parsed_results:
        print(int(user_id))
        try:
            await bot.banChatMember(chat_id="-100"+PRIVATE_GROUP_ID , user_id=user_id)
        except Exception as e:
            print("User with id "+str(user_id)+" isn't available in the group!")

    print('Removed users from group banned!')
    cursor.close()
    conn.close()
    # await cronjob_task(application)

def main() -> None:
    global application

    """Main function to start the Telegram bot."""
    # Create the updater and dispatcher
    application = Application.builder().token(BOT_TOKEN).read_timeout(60).write_timeout(60).build()

    # Register command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('tellmemyid', tell_me_my_id))
    application.add_handler(CommandHandler('letmein', let_me_in))

    job_queue = application.job_queue
    job_queue.run_repeating(cronjob_task, interval=24*60*60) # 24 hour

    # Start the bot
    application.run_polling()

    
if __name__ == '__main__':
    main()
