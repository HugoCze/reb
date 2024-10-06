import os
import asyncio
import telebot
import threading
import sqlite3
from datetime import datetime
from telebot.types import ChatInviteLink
from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantCreator, MessageActionChatDeleteUser

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
GROUP_ID = int(os.getenv('GROUP_ID'))


bot = telebot.TeleBot(BOT_TOKEN)
client = TelegramClient('bot_session', API_ID, API_HASH)


def get_or_create_invite_link(chat_id: str) -> str:
    try:
        invite_link: ChatInviteLink = bot.create_chat_invite_link(chat_id)
        return invite_link.invite_link
    except Exception as e:
        print(f"Error creating invite link: {e}")
        return "Unable to generate invite link at the moment."


def get_tasks():
    return {
        "task1": f"Join our GambieGroup: {get_or_create_invite_link(GROUP_ID)}",
        "task2": f"Join our Bonus Collectors channel: https://t.me/{CHANNEL_ID}"
    }


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! I'm your Telegram Gambie bot. Use /tasks to see available tasks.")


@bot.message_handler(commands=['tasks'])
def send_tasks_list(message):
    tasks = get_tasks()
    task_list = "\n".join([f"/task_{i+1}: {task.split(':')[0]}" for i, task in enumerate(tasks.values())])
    bot.reply_to(message, f"Available tasks:\n{task_list}")


@bot.message_handler(commands=['task_1', 'task_2'])
def send_task(message):
    tasks = get_tasks()
    task_num = message.text.split('_')[1]
    task_key = f"task{task_num}"
    if task_key in tasks:
        bot.reply_to(message, tasks[task_key])
    else:
        bot.reply_to(message, "Invalid task number.")


async def send_message_to_user(user_id, message):
    try:
        await client.send_message(user_id, message)
        print(f"Message sent successfully to user {user_id}")
    except Exception as e:
        print(f"Failed to send message to user {user_id}. Error: {e}")


def create_database():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY,
                  points INTEGER DEFAULT 0,
                  last_updated TIMESTAMP,
                  group_member BOOLEAN DEFAULT FALSE,
                  channel_member BOOLEAN DEFAULT FALSE)''')
    conn.commit()
    conn.close()


def update_user_points(user_id, points_change, is_group=False, is_channel=False):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (id, points, last_updated) VALUES (?, 0, ?)",
              (user_id, datetime.now()))
    c.execute("UPDATE users SET points = points + ?, last_updated = ? WHERE id = ?",
              (points_change, datetime.now(), user_id))
    if is_group:
        c.execute("UPDATE users SET group_member = ? WHERE id = ?", (points_change > 0, user_id))
    if is_channel:
        c.execute("UPDATE users SET channel_member = ? WHERE id = ?", (points_change > 0, user_id))
    conn.commit()
    current_points = c.execute("SELECT points FROM users WHERE id = ?", (user_id,)).fetchone()[0]
    conn.close()
    return current_points


def check_membership(user_id, is_group=False, is_channel=False):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    if is_group:
        result = c.execute("SELECT group_member FROM users WHERE id = ?", (user_id,)).fetchone()
    elif is_channel:
        result = c.execute("SELECT channel_member FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return result[0] if result else False


@client.on(events.ChatAction(chats=CHANNEL_ID))
async def handle_channel_join(event):
    print(f"channel:\n{event}")
    user_id = event.user_id
    if (event.user_joined or event.user_added) and not isinstance(event.original_update.new_participant, ChannelParticipantCreator) and not isinstance(event, MessageActionChatDeleteUser):
        # User joined the channel
        current_points = update_user_points(user_id, 100, is_channel=True)
        await send_message_to_user(int(user_id), 
                        f"Thank you for joining our channel!\n100 points transferred to your account! Your total: {current_points} points")
    elif event.user_left == True or event.user_kicked == True:
        # Check if user was a member before updating points
        if check_membership(user_id, is_channel=True):
            current_points = update_user_points(user_id, -100, is_channel=True)
            await send_message_to_user(int(user_id), 
                            f"Sorry to see you leave the channel.\n100 points deducted from your account. Your total: {current_points} points")


@client.on(events.ChatAction(chats=GROUP_ID))
async def handle_group_join(event):
    print(f"group:\n{event}")
    user_id = event.user_id
    if (event.user_joined or event.user_added) and not isinstance(event, MessageActionChatDeleteUser):
        # User joined the group
        current_points = update_user_points(user_id, 100, is_group=True)
        await send_message_to_user(int(user_id), 
                        f"Thank you for joining our group!\n100 points transferred to your account! Your total: {current_points} points")
    elif event.user_left == True or event.user_kicked == True:
        # Check if user was a member before updating points
        if check_membership(user_id, is_group=True):
            current_points = update_user_points(user_id, -100, is_group=True)
            await send_message_to_user(int(user_id), 
                            f"Sorry to see you leave the group.\n100 points deducted from your account. Your total: {current_points} points")


def bot_polling():
    bot.polling(none_stop=True, interval=0)


async def main():
    print("Starting bot and client...")
    create_database()
    await client.start(bot_token=BOT_TOKEN)
    
    polling_thread = threading.Thread(target=bot_polling)
    polling_thread.start()
    
    print(f"Bot is running. Tracking new user joins for group {GROUP_ID} and channel {CHANNEL_ID}. Press Ctrl+C to stop.")
    try:
        await client.run_until_disconnected()
    finally:
        bot.stop_polling()
        polling_thread.join()

if __name__ == '__main__':
    asyncio.run(main())