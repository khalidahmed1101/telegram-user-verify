
import os
import psycopg2
from telegram import Update, Bot,ChatPermissions
from telegram.ext import Application, CommandHandler, Job
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
import asyncio


api_id = 0 #Add telethon api id
api_hash = 'Telethon api hash'

# PostgreSQL database connection parameters
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'telegram'
DB_USER = 'user'
DB_PASSWORD = 'password'

# Telegram Bot token
BOT_TOKEN = 'bot token'

# Telegram private group ID
PRIVATE_GROUP_ID = 'group id'
PRIVATE_GROUP_LINK = "group link"

application = None  # Global variable to store the Application object

phone_number = '# phone number to authenticate telethon'

async def get_chat_members():
    async with TelegramClient('py_bot', api_id, api_hash) as client:
        try:
            await client.connect()
        except ConnectionError:
            print('Failed to connect to the Telegram server.')

        try:
            if not await client.is_user_authorized():
                await client.send_code_request(phone_number)
                try:
                    await client.sign_in(phone_number, input('Enter the code: '))
                except SessionPasswordNeededError:
                    await client.sign_in(password=input('Two-step verification is enabled. Please enter your password: '))
            
            participants = await client(GetParticipantsRequest(
                channel=int(PRIVATE_GROUP_ID),
                filter=ChannelParticipantsSearch(''),
                offset=0,
                limit=200,
                hash=0
            ))          

            return participants.participants
        except Exception as e:
            print(f"An error occurred: {e}")

# Ban user
async def ban_user(context,user_id):
    print("banning--------")
    print(user_id)
    chat_id = "-100"+PRIVATE_GROUP_ID
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False
    )
    message = "User with id " + user_id + " has been banned from the group"
    await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id,  until_date=0)
    # await context.bot.kick_chat_member(chat_id=chat_id, user_id=user_id)
    await context.bot.send_message(chat_id=chat_id, text=message)
    print("User restricted in the group.")

# Unban user
async def unban_user(context,user_id):
    print("un----banning")
    print(user_id)
    chat_id = "-100"+PRIVATE_GROUP_ID
      # To unrestrict the user, pass a ChatPermissions object with all True values
    unrestricted_permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=True,
        can_invite_users=True,
        can_pin_messages=True
    )
    message = "User with id " + user_id + " has been unbanned from the group"
    await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
    await context.bot.send_message(chat_id=chat_id, text=message)
    print("User unrestricted in the group.")

async def check_user_exists(user_id,cur,context):
    # Execute the query to check if the row exists for the specified user_id
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    data = cur.fetchone()

    if data is not None:
        is_subscribed = data[3]  # Assuming the last value is the boolean
        if is_subscribed:
            await unban_user(context,user_id)
        else:
            await ban_user(context,user_id)
    else:
        await ban_user(context,user_id)
        
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
    print("*********************** Running Cronjob task to ban/unban users from the private channel. ********************")
    # Connect to the remote database
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()

    members = await get_chat_members()
    memberIds = []
    for item in members:
        if hasattr(item, 'admin_rights'):
            if item.admin_rights:
                print(f"User ID: {item.user_id} is an admin or chat owner.")
            else:
                memberIds.append(str(item.user_id))
        else:
            memberIds.append(str(item.user_id))

    # Create a list to hold the tasks
    tasks = []

    # Iterate over the user_ids and create a task for each user_id
    for user_id in memberIds:
        task = asyncio.ensure_future(check_user_exists(user_id,cursor,context))
        tasks.append(task)

    # Run the tasks concurrently
    await asyncio.gather(*tasks)

    print('Removed unwanted users from group!')
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
    job_queue.run_repeating(cronjob_task, interval=60*60*24) # 24 hour

    # Start the bot
    application.run_polling()

    
if __name__ == '__main__':
    main()
