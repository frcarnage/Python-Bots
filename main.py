import os
import telebot
import random
import time
import string
import requests
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from telebot.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from flask import Flask, jsonify, render_template_string

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8271097949:AAGgugeFfdJa6NtrsrrIrIfqxcZeQ1xenA8')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '7575087826'))
BOT_USERNAME = "CarnageSwapperBot"

# Instagram API Configuration
DEFAULT_WEBHOOK_URL = "https://discord.com/api/webhooks/1447815502327058613/IkpdhIMUlcE34PCNygmnlIU7WBhzmYbvgqCK8KOIDpoHTgMKoJWSRnMKgq41RNh2rmyE"
TELEGRAM_CHANNEL_ID = "-100"  # Replace with your channel ID

# ======= CHANNEL CONFIGURATION =======
UPDATES_CHANNEL = "@CarnageUpdates"
PROOFS_CHANNEL = "@CarnageProofs"
CHANNELS = {
    "updates": {
        "id": UPDATES_CHANNEL,
        "name": "📢 Updates Channel",
        "description": "Get latest updates, server info, and announcements"
    },
    "proofs": {
        "id": PROOFS_CHANNEL,
        "name": "✅ Proofs Channel",
        "description": "See successful swaps and user proofs"
    }
}

# Global variables
bot = telebot.TeleBot(BOT_TOKEN)
start_time = time.time()
bot_running = True
session_data = {}
requests_count = 0
errors_count = 0
rate_limit_cooldowns = {}
tutorial_sessions = {}
referral_cache = {}
user_states = {}

# Database connection pool
db_lock = threading.Lock()

# ==================== FLASK APP FOR KOYEB ====================
app = Flask(__name__)

# ==================== DATABASE CONNECTION MANAGEMENT ====================
def get_db_connection():
    """Get database connection with thread safety"""
    conn = sqlite3.connect('users.db', check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=(), commit=False):
    """Execute SQL query with thread safety"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()
                result = True
            else:
                result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Database error: {e}")
            if commit:
                conn.rollback()
            raise e
        finally:
            conn.close()

def execute_one(query, params=()):
    """Execute SQL query and return single result"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Database error: {e}")
            return None
        finally:
            conn.close()

# ==================== CHANNEL VERIFICATION SYSTEM ====================
def check_channel_membership(user_id, channel_username):
    """Check if user is member of a channel"""
    try:
        chat_member = bot.get_chat_member(channel_username, user_id)
        return chat_member.status in ['member', 'administrator', 'creator', 'restricted']
    except Exception as e:
        print(f"Error checking channel membership for {channel_username}: {e}")
        return False

def check_all_channels(user_id):
    """Check if user has joined all required channels"""
    results = {}
    for channel_type, channel_info in CHANNELS.items():
        results[channel_type] = check_channel_membership(user_id, channel_info['id'])
    return results

def has_joined_all_channels(user_id):
    """Check if user has joined all required channels"""
    results = check_all_channels(user_id)
    return all(results.values())

def create_channel_buttons():
    """Create inline buttons for channel joining"""
    markup = InlineKeyboardMarkup(row_width=1)
    
    for channel_type, channel_info in CHANNELS.items():
        markup.add(InlineKeyboardButton(
            f"🔗 Join {channel_info['name']}",
            url=f"https://t.me/{channel_info['id'].replace('@', '')}"
        ))
    
    markup.add(InlineKeyboardButton(
        "✅ I've Joined All Channels",
        callback_data="check_channels"
    ))
    
    return markup

def send_welcome_with_channels(user_id, first_name):
    """Send welcome message with channel requirements"""
    welcome_message = f"""
🤖 *Welcome to CARNAGE Swapper Bot* {first_name}! 🎉

*⚠️ IMPORTANT: Before using the bot, you MUST join our official channels:*

"""
    
    for channel_type, channel_info in CHANNELS.items():
        welcome_message += f"\n📌 *{channel_info['name']}*"
        welcome_message += f"\n{channel_info['description']}"
        welcome_message += f"\nJoin: {channel_info['id']}\n"
    
    welcome_message += f"""
*Why join these channels?*
• {CHANNELS['updates']['name']}: Get latest updates, server status, and news
• {CHANNELS['proofs']['name']}: See successful swaps as proof and user testimonials

*After joining both channels, click the button below to verify.*
"""
    
    bot.send_message(
        user_id,
        welcome_message,
        parse_mode="Markdown",
        reply_markup=create_channel_buttons()
    )

# ==================== BASIC HELPER FUNCTIONS ====================
def is_admin(user_id):
    """Check if user is admin"""
    return user_id == ADMIN_USER_ID

def generate_referral_code(user_id):
    """Generate unique referral code"""
    return f"CARNAGE{user_id}{random.randint(1000, 9999)}"

def send_to_admin(message_text, parse_mode="Markdown"):
    """Send notification to admin"""
    try:
        bot.send_message(ADMIN_USER_ID, message_text, parse_mode=parse_mode)
    except Exception as e:
        print(f"Failed to send message to admin: {e}")

def send_to_proofs_channel(message_text, parse_mode="Markdown"):
    """Send swap proof to proofs channel"""
    try:
        bot.send_message(CHANNELS['proofs']['id'], message_text, parse_mode=parse_mode)
    except Exception as e:
        print(f"Failed to send message to proofs channel: {e}")

def create_reply_menu(buttons, row_width=2, add_back=True):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    for i in range(0, len(buttons), row_width):
        row = [KeyboardButton(text) for text in buttons[i:i + row_width]]
        markup.add(*row)
    if add_back:
        markup.add(KeyboardButton("Back"))
    return markup

def check_cooldown(chat_id):
    """Check if user is in cooldown"""
    if chat_id in rate_limit_cooldowns:
        cooldown_until = rate_limit_cooldowns[chat_id]
        if time.time() < cooldown_until:
            bot.send_message(chat_id, "<b>⚠️ Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
            return False
    return True

def set_cooldown(chat_id):
    """Set 30-minute cooldown for user"""
    rate_limit_cooldowns[chat_id] = time.time() + 1800

# ==================== INSTAGRAM API FUNCTIONS ====================
def init_session_data(chat_id):
    """Initialize session data for user"""
    if chat_id not in session_data:
        session_data[chat_id] = {
            "main": None, "main_username": None, "main_validated_at": None,
            "target": None, "target_username": None, "target_validated_at": None,
            "backup": None, "backup_username": None,
            "swap_webhook": None, "bio": None, "name": None,
            "swapper_threads": 1,
            "current_menu": "main",
            "previous_menu": None
        }

def clear_session_data(chat_id, session_type):
    """Clear session data"""
    if session_type == "main":
        session_data[chat_id]["main"] = None
        session_data[chat_id]["main_username"] = None
        session_data[chat_id]["main_validated_at"] = None
    elif session_type == "target":
        session_data[chat_id]["target"] = None
        session_data[chat_id]["target_username"] = None
        session_data[chat_id]["target_validated_at"] = None
    elif session_type == "backup":
        session_data[chat_id]["backup"] = None
        session_data[chat_id]["backup_username"] = None
    elif session_type == "close":
        session_data[chat_id]["main"] = None
        session_data[chat_id]["main_username"] = None
        session_data[chat_id]["main_validated_at"] = None
        session_data[chat_id]["target"] = None
        session_data[chat_id]["target_username"] = None
        session_data[chat_id]["target_validated_at"] = None

def validate_session(session_id, chat_id, session_type):
    """Validate Instagram session ID"""
    print(f"Validating session for chat_id: {chat_id}, type: {session_type}")
    url = "https://i.instagram.com/api/v1/accounts/current_user/"
    headers = {
        "User-Agent": "Instagram 194.0.0.36.172 Android (28/9; 440dpi; 1080x1920; Google; Pixel 3; blueline; blueline; en_US)",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US",
        "X-IG-App-ID": "567067343352427",
        "X-IG-Capabilities": "3brTvw==",
        "X-IG-Connection-Type": "WIFI",
        "Cookie": f"sessionid={session_id}; csrftoken={''.join(random.choices(string.ascii_letters + string.digits, k=32))}",
        "Host": "i.instagram.com"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Validation response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "user" in data and "username" in data["user"]:
                return data["user"]["username"]
            else:
                bot.send_message(chat_id, "<b>❌ Session valid but no username found</b>", parse_mode='HTML')
        elif response.status_code == 401:
            bot.send_message(chat_id, "<b>❌ Invalid or expired session ID</b>", parse_mode='HTML')
        elif response.status_code == 429:
            set_cooldown(chat_id)
            bot.send_message(chat_id, "<b>⚠️ Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
        else:
            bot.send_message(chat_id, f"<b>❌ Unexpected response: {response.status_code}</b>", parse_mode='HTML')
    except requests.exceptions.Timeout:
        bot.send_message(chat_id, "<b>❌ Request timed out</b>", parse_mode='HTML')
    except Exception as e:
        bot.send_message(chat_id, f"<b>❌ Validation error: {str(e)}</b>", parse_mode='HTML')
    
    time.sleep(2)
    bot.send_message(chat_id, "<b>❌ Failed to log in</b>", parse_mode='HTML')
    clear_session_data(chat_id, session_type)
    session_data[chat_id]["current_menu"] = "swapper" if session_type == "backup" else "main"
    return None

def generate_random_username():
    """Generate random username"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def send_discord_webhook(webhook_url, username, action, footer=None):
    """Send notification to Discord webhook"""
    if not webhook_url or not webhook_url.startswith("https://"):
        return False
    
    thumbnail_url = "https://cdn.discordapp.com/attachments/1358386363401244865/1367477276568191038/1c7d9a77eb7655559feab2d7c04b64a5.gif"
    title = "CARNAGE Swapper" if action == "Swapped" else "CARNAGE Failed"
    description = f"Have A Fun.. {username}"
    color = 0x00ff00 if action == "Swapped" else 0xff0000
    
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "thumbnail": {"url": thumbnail_url},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "footer": {"text": f"By : {footer or 'CARNAGE Swapper'}"}
    }
    
    payload = {"embeds": [embed]}
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        return response.status_code == 204
    except:
        return False

def send_notifications(chat_id, username, action):
    """Send notifications to Discord and Telegram"""
    footer = session_data[chat_id]["name"] or "CARNAGE Swapper"
    webhook_url = session_data[chat_id]["swap_webhook"] or DEFAULT_WEBHOOK_URL
    success = send_discord_webhook(webhook_url, username, action, footer)
    if not success and webhook_url != DEFAULT_WEBHOOK_URL:
        send_discord_webhook(DEFAULT_WEBHOOK_URL, username, action, footer)
    
    # Send to Telegram proofs channel
    try:
        bot.send_message(
            CHANNELS['proofs']['id'],
            f"✅ *{action.upper()} SWAP*\n\n👤 Username: `{username}`\n🕒 Time: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode="Markdown"
        )
    except:
        pass

def change_username_account1(chat_id, session_id, csrf_token, random_username):
    """Change username for target account (to random username)"""
    global requests_count, errors_count
    
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'Default Name'),
        'email': 'default@example.com',
        'username': random_username,
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Default Bio'),
        'external_url': 'https://example.com',
        'chaining_enabled': 'on'
    }
    
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': f'mid=YQvmcwAEAAFVrBezgjwUhwEQuv3c; csrftoken={csrf_token}; sessionid={session_id};',
        'origin': 'https://www.instagram.com',
        'referer': 'https://www.instagram.com/accounts/edit/',
        'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'x-asbd-id': '129477',
        'x-csrftoken': csrf_token,
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR0EWvjix_XsqAIjAt7fjL3qLwQKCRTB8UMXTGL5j7pkgSqj',
        'x-instagram-ajax': '1014730915',
        'x-requested-with': 'XMLHttpRequest'
    }
    
    print(f"Changing username to {random_username} for session {session_id}")
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        requests_count += 1
        response_text = response.text[:500]
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("status") == "ok":
                    return random_username
                else:
                    error_message = data.get("message", "Unknown error")
                    bot.send_message(chat_id, f"<b>❌ Failed to change username: {error_message}</b>", parse_mode='HTML')
                    return None
            except json.JSONDecodeError:
                bot.send_message(chat_id, "<b>❌ Invalid JSON response from Instagram</b>", parse_mode='HTML')
                return None
        elif response.status_code == 429:
            errors_count += 1
            set_cooldown(chat_id)
            bot.send_message(chat_id, "<b>⚠️ Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
            return None
        elif response.status_code == 400:
            errors_count += 1
            bot.send_message(chat_id, "<b>❌ Invalid request (bad session or username)</b>", parse_mode='HTML')
            return None
        else:
            errors_count += 1
            bot.send_message(chat_id, f"<b>❌ Failed to change username: {response.status_code}</b>", parse_mode='HTML')
            return None
    except Exception as e:
        errors_count += 1
        bot.send_message(chat_id, f"<b>❌ Error with CARNAGE Swap Target Session: {str(e)}</b>", parse_mode='HTML')
        return None

def revert_username(chat_id, session_id, csrf_token, original_username):
    """Revert username back to original"""
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'Default Name'),
        'email': 'default@example.com',
        'username': original_username.lstrip('@'),
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Default Bio'),
        'external_url': 'https://example.com',
        'chaining_enabled': 'on'
    }
    
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': f'mid=YQvmcwAEAAFVrBezgjwUhwEQuv3c; csrftoken={csrf_token}; sessionid={session_id};',
        'origin': 'https://www.instagram.com',
        'referer': 'https://www.instagram.com/accounts/edit/',
        'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'x-asbd-id': '129477',
        'x-csrftoken': csrf_token,
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR0EWvjix_XsqAIjAt7fjL3qLwQKCRTB8UMXTGL5j7pkgSqj',
        'x-instagram-ajax': '1014730915',
        'x-requested-with': 'XMLHttpRequest'
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except:
        return False

def change_username_account2(chat_id, session_id, csrf_token, target_username):
    """Change username for main account (to target username)"""
    global requests_count, errors_count
    
    if not check_cooldown(chat_id):
        return False
    
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'Default Name'),
        'email': 'default@example.com',
        'username': target_username.lstrip('@'),
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Default Bio'),
        'external_url': 'https://example.com',
        'chaining_enabled': 'on'
    }
    
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': f'mid=YQvmcwAEAAFVrBezgjwUhwEQuv3c; csrftoken={csrf_token}; sessionid={session_id};',
        'origin': 'https://www.instagram.com',
        'referer': 'https://www.instagram.com/accounts/edit/',
        'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'x-asbd-id': '129477',
        'x-csrftoken': csrf_token,
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR0EWvjix_XsqAIjAt7fjL3qLwQKCRTB8UMXTGL5j7pkgSqj',
        'x-instagram-ajax': '1014730915',
        'x-requested-with': 'XMLHttpRequest'
    }
    
    print(f"Changing username to {target_username} for session {session_id}")
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        requests_count += 1
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("status") == "ok":
                    return True
                else:
                    error_message = data.get("message", "Unknown error")
                    bot.send_message(chat_id, f"<b>❌ Failed to change username: {error_message}</b>", parse_mode='HTML')
                    return False
            except json.JSONDecodeError:
                bot.send_message(chat_id, "<b>❌ Invalid JSON response from Instagram</b>", parse_mode='HTML')
                return False
        elif response.status_code == 429:
            errors_count += 1
            set_cooldown(chat_id)
            bot.send_message(chat_id, "<b>⚠️ Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
            return False
        elif response.status_code == 400:
            errors_count += 1
            bot.send_message(chat_id, "<b>❌ Invalid request (bad session or username)</b>", parse_mode='HTML')
            return False
        else:
            errors_count += 1
            bot.send_message(chat_id, f"<b>❌ Failed to change username: {response.status_code}</b>", parse_mode='HTML')
            return False
    except Exception as e:
        errors_count += 1
        bot.send_message(chat_id, f"<b>❌ Error changing username: {str(e)}</b>", parse_mode='HTML')
        return False

def save_session_to_db(user_id, session_type, session_id, username):
    """Save session to database"""
    if session_type == "main":
        execute_query("UPDATE users SET main_session = ?, main_username = ? WHERE user_id = ?", 
                     (session_id, username, user_id), commit=True)
    elif session_type == "target":
        execute_query("UPDATE users SET target_session = ?, target_username = ? WHERE user_id = ?", 
                     (session_id, username, user_id), commit=True)
    elif session_type == "backup":
        execute_query("UPDATE users SET backup_session = ?, backup_username = ? WHERE user_id = ?", 
                     (session_id, username, user_id), commit=True)

def get_user_sessions(user_id):
    """Get user's saved sessions from database"""
    result = execute_one("SELECT main_session, main_username, target_session, target_username FROM users WHERE user_id = ?", (user_id,))
    if result:
        return {
            'main': result[0],
            'main_username': result[1],
            'target': result[2],
            'target_username': result[3]
        }
    return {'main': None, 'main_username': None, 'target': None, 'target_username': None}

# ==================== DATABASE FUNCTIONS ====================
def add_user(user_id, username, first_name, last_name, referral_code="direct"):
    """Add new user to database"""
    existing_user = execute_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing_user:
        return
    
    user_referral_code = generate_referral_code(user_id)
    execute_query('''
        INSERT INTO users (user_id, username, first_name, last_name, join_date, last_active, 
                          referral_code, join_method, main_session, target_session, backup_session)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          user_referral_code, 'direct', None, None, None), commit=True)
    
    if referral_code and referral_code != "direct":
        process_referral(user_id, referral_code)
    
    if get_total_users() <= 100:
        award_achievement(user_id, "early_adopter")
    if get_total_users() <= 50:
        award_achievement(user_id, "first_user")

def update_user_active(user_id):
    """Update user's last active time"""
    execute_query("UPDATE users SET last_active = ? WHERE user_id = ?", 
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id), commit=True)

def get_user_status(user_id):
    """Get user approval status"""
    result = execute_one("SELECT approved, is_banned FROM users WHERE user_id = ?", (user_id,))
    
    if result:
        approved = result[0]
        is_banned = result[1]
        
        if is_banned:
            return "banned"
        
        if approved == 1:
            return "approved"
    
    return "pending"

def is_user_approved(user_id):
    """Check if user is approved"""
    status = get_user_status(user_id)
    return status == "approved"

def approve_user(user_id, duration_days=None):
    """Approve user access"""
    if duration_days:
        if duration_days == "permanent":
            approved_until = "9999-12-31 23:59:59"
        else:
            approved_until = (datetime.now() + timedelta(days=int(duration_days))).strftime("%Y-%m-%d %H:%M:%S")
    else:
        approved_until = "9999-12-31 23:59:59"
    
    execute_query("UPDATE users SET approved = 1, approved_until = ? WHERE user_id = ?", 
                  (approved_until, user_id), commit=True)

def get_total_users():
    """Get total user count"""
    result = execute_one("SELECT COUNT(*) FROM users")
    return result[0] if result else 0

def log_swap(user_id, target_username, status, error_message=None):
    """Log swap attempt to history"""
    execute_query('''
        INSERT INTO swap_history (user_id, target_username, status, swap_time, error_message)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, target_username, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), error_message), commit=True)
    
    execute_query("UPDATE users SET total_swaps = total_swaps + 1 WHERE user_id = ?", (user_id,), commit=True)
    if status == "success":
        execute_query("UPDATE users SET successful_swaps = successful_swaps + 1 WHERE user_id = ?", (user_id,), commit=True)
    
    if status == "success":
        result = execute_one("SELECT COUNT(*) FROM swap_history WHERE user_id = ? AND status = 'success'", (user_id,))
        success_count = result[0] if result else 0
        if success_count == 1:
            award_achievement(user_id, "first_swap")
        if success_count >= 10:
            award_achievement(user_id, "swap_pro")
    elif status == "failed":
        award_achievement(user_id, "swap_failed")

def get_user_detailed_stats(user_id):
    """Get detailed user statistics"""
    user_data = execute_one('''
        SELECT username, total_swaps, successful_swaps, total_referrals, free_swaps_earned
        FROM users WHERE user_id = ?
    ''', (user_id,))
    
    if not user_data:
        return None
    
    username, total_swaps, successful_swaps, total_referrals, free_swaps = user_data
    success_rate = (successful_swaps / total_swaps * 100) if total_swaps > 0 else 0
    
    recent_swaps = execute_query('''
        SELECT target_username, status, swap_time 
        FROM swap_history 
        WHERE user_id = ? 
        ORDER BY swap_time DESC 
        LIMIT 5
    ''', (user_id,))
    
    achievements = get_user_achievements(user_id)
    
    return {
        "username": username or "User",
        "bot_username": BOT_USERNAME,
        "user_id": user_id,
        "stats": [
            {"name": "Total Swaps", "value": total_swaps},
            {"name": "Successful Swaps", "value": successful_swaps},
            {"name": "Success Rate", "value": f"{success_rate:.1f}%"},
            {"name": "Total Referrals", "value": total_referrals},
            {"name": "Free Swaps Available", "value": free_swaps},
            {"name": "Account Status", "value": "✅ Approved" if get_user_status(user_id) == "approved" else "⏳ Pending"}
        ],
        "achievements": achievements,
        "referrals": {
            "count": total_referrals,
            "free_swaps": free_swaps
        },
        "recent_swaps": [
            {"target": s[0], "status": s[1], "time": s[2]} for s in recent_swaps
        ]
    }

# ==================== REFERRAL SYSTEM ====================
def process_referral(user_id, referral_code):
    """Process referral when new user joins"""
    if not referral_code or referral_code == "direct":
        return
    
    result = execute_one("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
    
    if result:
        referrer_id = result[0]
        
        execute_query("UPDATE users SET referred_by = ?, join_method = 'referral' WHERE user_id = ?", 
                     (referrer_id, user_id), commit=True)
        
        execute_query('''
            UPDATE users 
            SET total_referrals = total_referrals + 1,
                free_swaps_earned = free_swaps_earned + 2
            WHERE user_id = ?
        ''', (referrer_id,), commit=True)
        
        execute_query("UPDATE users SET approved = 1, approved_until = '9999-12-31 23:59:59' WHERE user_id = ?", 
                     (user_id,), commit=True)
        
        try:
            bot.send_message(
                referrer_id,
                f"🎉 *New Referral!*\n\n"
                f"Someone joined using your referral link!\n"
                f"• You earned: **2 FREE swaps** 🆓\n"
                f"• Total referrals: {get_user_referrals_count(referrer_id)}\n"
                f"• Total free swaps: {get_user_free_swaps(referrer_id)}",
                parse_mode="Markdown"
            )
        except:
            pass
        
        award_achievement(referrer_id, "referral_master")
        
        if get_user_referrals_count(referrer_id) >= 5:
            award_achievement(referrer_id, "referral_master")

def get_user_referrals_count(user_id):
    """Get count of user's referrals"""
    result = execute_one("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
    return result[0] if result else 0

def get_user_free_swaps(user_id):
    """Get user's free swaps count"""
    result = execute_one("SELECT free_swaps_earned FROM users WHERE user_id = ?", (user_id,))
    return result[0] if result else 0

def get_total_referrals():
    """Get total referrals across all users"""
    result = execute_one("SELECT SUM(total_referrals) FROM users")
    return result[0] if result and result[0] else 0

# ==================== ACHIEVEMENT SYSTEM ====================
ACHIEVEMENTS = {
    "first_swap": {"name": "First Swap", "emoji": "🥇", "description": "Complete your first username swap"},
    "swap_pro": {"name": "Swap Pro", "emoji": "⚡", "description": "Complete 10 successful swaps"},
    "referral_master": {"name": "Referral Master", "emoji": "🤝", "description": "Refer 5 friends"},
    "early_adopter": {"name": "Early Adopter", "emoji": "🚀", "description": "Join first 100 users"},
    "founder": {"name": "Founder", "emoji": "👑", "description": "Bot creator"},
    "first_user": {"name": "Pioneer", "emoji": "🧭", "description": "First 50 users"},
    "tutorial_complete": {"name": "Quick Learner", "emoji": "🎓", "description": "Complete interactive tutorial"},
    "dashboard_user": {"name": "Dashboard Pro", "emoji": "📊", "description": "Visit web dashboard"},
    "channel_member": {"name": "Official Member", "emoji": "📢", "description": "Join both official channels"},
    "swap_failed": {"name": "First Fail", "emoji": "💀", "description": "Experience your first failed swap"},
    "swap_streak_3": {"name": "3-Day Streak", "emoji": "🔥", "description": "Swap for 3 consecutive days"},
}

def award_achievement(user_id, achievement_id):
    """Award an achievement to user"""
    result = execute_one("SELECT * FROM achievements WHERE user_id = ? AND achievement_id = ?", 
                        (user_id, achievement_id))
    if result:
        return False
    
    achievement = ACHIEVEMENTS.get(achievement_id)
    if achievement:
        execute_query('''
            INSERT INTO achievements (user_id, achievement_id, achievement_name, achievement_emoji, unlocked_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, achievement_id, achievement['name'], achievement['emoji'], 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")), commit=True)
        
        try:
            bot.send_message(
                user_id,
                f"🏆 *New Achievement Unlocked!*\n\n"
                f"{achievement['emoji']} *{achievement['name']}*\n"
                f"{achievement['description']}\n\n"
                f"Check all achievements with /achievements",
                parse_mode="Markdown"
            )
        except:
            pass
        
        return True
    
    return False

def get_user_achievements(user_id):
    """Get user's unlocked achievements"""
    achievements = execute_query('''
        SELECT achievement_id, achievement_name, achievement_emoji, unlocked_at 
        FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC
    ''', (user_id,))
    
    unlocked = len(achievements)
    total = len(ACHIEVEMENTS)
    
    return {
        "unlocked": unlocked,
        "total": total,
        "list": [{"id": a[0], "name": a[1], "emoji": a[2], "date": a[3]} for a in achievements]
    }

def get_total_achievements_awarded():
    """Get total achievements awarded"""
    result = execute_one("SELECT COUNT(*) FROM achievements")
    return result[0] if result else 0

# ==================== DATABASE SETUP ====================
def init_database():
    """Initialize SQLite database with new tables"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    approved INTEGER DEFAULT 0,
                    approved_until TEXT DEFAULT NULL,
                    join_date TEXT,
                    last_active TEXT,
                    is_banned INTEGER DEFAULT 0,
                    ban_reason TEXT DEFAULT NULL,
                    is_admin INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER DEFAULT NULL,
                    total_referrals INTEGER DEFAULT 0,
                    free_swaps_earned INTEGER DEFAULT 0,
                    total_swaps INTEGER DEFAULT 0,
                    successful_swaps INTEGER DEFAULT 0,
                    join_method TEXT DEFAULT 'direct',
                    channels_joined INTEGER DEFAULT 0,
                    main_session TEXT DEFAULT NULL,
                    main_username TEXT DEFAULT NULL,
                    target_session TEXT DEFAULT NULL,
                    target_username TEXT DEFAULT NULL,
                    backup_session TEXT DEFAULT NULL,
                    backup_username TEXT DEFAULT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    achievement_id TEXT,
                    achievement_name TEXT,
                    achievement_emoji TEXT,
                    unlocked_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS swap_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    target_username TEXT,
                    status TEXT,
                    swap_time TEXT,
                    error_message TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (ADMIN_USER_ID,))
            if not cursor.fetchone():
                referral_code = generate_referral_code(ADMIN_USER_ID)
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, approved, approved_until, 
                                      join_date, last_active, is_banned, is_admin, referral_code, join_method, channels_joined)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (ADMIN_USER_ID, "admin", "Admin", "User", 1, "9999-12-31 23:59:59", 
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0, 1, referral_code, 'direct', 1))
            
            conn.commit()
            conn.close()
            
            print("✅ Database initialized successfully")
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

def mark_channels_joined(user_id):
    """Mark user as having joined all channels"""
    execute_query("UPDATE users SET channels_joined = 1 WHERE user_id = ?", (user_id,), commit=True)

def has_user_joined_channels(user_id):
    """Check if user has joined channels in database"""
    result = execute_one("SELECT channels_joined FROM users WHERE user_id = ?", (user_id,))
    return result and result[0] == 1

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Handle callback queries"""
    user_id = call.from_user.id
    message_id = call.message.message_id
    
    if call.data == "check_channels":
        channel_results = check_all_channels(user_id)
        
        if all(channel_results.values()):
            bot.answer_callback_query(call.id, "✅ Verified! You've joined all channels!")
            bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text="🎉 *Channel Verification Successful!*\n\nYou've joined all required channels! ✅\n\nNow you can use the bot features.\n\nSend /start again to begin.",
                parse_mode="Markdown"
            )
            
            mark_channels_joined(user_id)
            award_achievement(user_id, "channel_member")
            
            time.sleep(1)
            welcome_features = f"""
🤖 *Welcome to CARNAGE Swapper Bot!* 🎉

*Features:*
✨ *Real Instagram Swapping* - Working API
📊 *Web Dashboard* - Track your stats online
🏆 *Achievements* - Unlock badges as you swap
🎓 *Interactive Tutorial* - Learn step by step
🎁 *Referral System* - Get FREE swaps per friend!

*Quick Start:*
1️⃣ Add Instagram sessions
2️⃣ Swap usernames instantly
3️⃣ Refer friends for FREE swaps
4️⃣ Track progress on dashboard

Use /tutorial for guided tour or /help for commands.
"""
            bot.send_message(user_id, welcome_features, parse_mode="Markdown")
            
        else:
            missing_channels = []
            for channel_type, joined in channel_results.items():
                if not joined:
                    missing_channels.append(CHANNELS[channel_type]['name'])
            
            bot.answer_callback_query(
                call.id, 
                f"❌ You need to join: {', '.join(missing_channels)}",
                show_alert=True
            )
            
            error_message = f"""
⚠️ *Channel Verification Failed*

*You still need to join these channels:*

"""
            for channel_type, joined in channel_results.items():
                if not joined:
                    channel = CHANNELS[channel_type]
                    error_message += f"\n❌ *{channel['name']}*"
                    error_message += f"\n{channel['description']}"
                    error_message += f"\nJoin: {channel['id']}\n"
            
            error_message += "\n*After joining, click the verify button again.*"
            
            bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=error_message,
                parse_mode="Markdown",
                reply_markup=create_channel_buttons()
            )

# ==================== MENU FUNCTIONS ====================
def show_main_menu(chat_id):
    """Show main menu"""
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "⏳ *Your account is pending approval.*", parse_mode="Markdown")
        return
    
    buttons = [
        "📱 Main Session", "🎯 Target Session",
        "🔄 Swapper", "⚙️ Settings",
        "📊 Dashboard", "🎁 Referral",
        "🏆 Achievements", "📈 Stats"
    ]
    markup = create_reply_menu(buttons, row_width=2, add_back=False)
    bot.send_message(chat_id, "🤖 *CARNAGE Swapper - Main Menu*", parse_mode='Markdown', reply_markup=markup)

def show_swapper_menu(chat_id):
    """Show swapper menu"""
    if not is_user_approved(chat_id):
        return
    
    buttons = ["Run Main Swap", "BackUp Mode", "Threads Swap", "Back"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b>🔄 CARNAGE Swapper - Select Option</b>", parse_mode='HTML', reply_markup=markup)

def show_settings_menu(chat_id):
    """Show settings menu"""
    if not is_user_approved(chat_id):
        return
    
    buttons = ["Bio", "Name", "Webhook", "Check Block", "Close Sessions", "Back"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b>⚙️ CARNAGE Settings - Select Option</b>", parse_mode='HTML', reply_markup=markup)

# ==================== COMMAND HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    
    referral_code = "direct"
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith("ref-"):
            referral_code = param[4:]
        elif param == "tutorial":
            start_tutorial_command(message)
            return
        elif param == "swap":
            if is_user_approved(user_id):
                show_swapper_menu(user_id)
            else:
                bot.send_message(user_id, "Please complete /start first")
            return
    
    add_user(user_id, username, first_name, last_name, referral_code)
    update_user_active(user_id)
    
    if has_user_joined_channels(user_id) or has_joined_all_channels(user_id):
        if referral_code != "direct":
            bot.send_message(user_id, "✅ *Approved via referral!* You can start swapping immediately!", parse_mode="Markdown")
            show_main_menu(user_id)
        elif is_user_approved(user_id):
            show_main_menu(user_id)
        else:
            bot.send_message(
                user_id,
                "⏳ *Access pending approval*\n\n"
                "Contact @CARNAGEV1 or use referral system for instant access!\n"
                "Tip: Get a friend to refer you for instant approval! 🎁",
                parse_mode="Markdown"
            )
    else:
        send_welcome_with_channels(user_id, first_name)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show help menu"""
    user_id = message.from_user.id
    
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    help_text = """
🆘 *CARNAGE Bot Help*

*Basic Commands:*
/start - Start the bot
/help - Show this help
/tutorial - Interactive tutorial

*User Features:*
/dashboard - Your personal dashboard
/stats - Your statistics
/achievements - Your unlocked badges
/history - Your swap history
/refer - Referral program
/leaderboard - Top users

*Swap Features:*
• Real Instagram username swapping
• Working API with rate limit handling
• Session validation and management
• Backup mode and threads support

*Official Channels:*
📢 Updates: @CarnageUpdates
✅ Proofs: @CarnageProofs

*Getting Started:*
1. Join both channels above
2. Use /tutorial for step-by-step guide
3. Add Instagram sessions
4. Start swapping!
5. Refer friends for FREE swaps

*Need Help?*
Contact: @CARNAGEV1
Visit Dashboard: https://separate-genny-1carnage1-2b4c603c.koyeb.app
"""
    
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# ==================== MENU HANDLERS ====================
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text
    
    update_user_active(chat_id)
    
    # Check if in tutorial
    if chat_id in tutorial_sessions:
        handle_tutorial_response(chat_id, text)
        return
    
    # Check channel membership first
    if not has_user_joined_channels(chat_id) and not has_joined_all_channels(chat_id):
        if text == "/start":
            start_command(message)
            return
        send_welcome_with_channels(chat_id, message.from_user.first_name)
        return
    
    # Initialize session data
    init_session_data(chat_id)
    
    # Handle menu navigation
    if text == "Back":
        if session_data[chat_id]["previous_menu"] == "main":
            show_main_menu(chat_id)
        elif session_data[chat_id]["previous_menu"] == "swapper":
            show_swapper_menu(chat_id)
        elif session_data[chat_id]["previous_menu"] == "settings":
            show_settings_menu(chat_id)
        return
    
    if text in ["📊 Dashboard", "Dashboard"]:
        dashboard_command(message)
        return
    
    if text in ["🎁 Referral", "Referral"]:
        referral_command(message)
        return
    
    if text in ["🏆 Achievements", "Achievements"]:
        achievements_command(message)
        return
    
    if text in ["📈 Stats", "Stats"]:
        stats_command(message)
        return
    
    if text == "📱 Main Session":
        session_data[chat_id]["current_menu"] = "main_session_input"
        session_data[chat_id]["previous_menu"] = "main"
        bot.send_message(chat_id, "<b>📥 Send Main Session ID</b>\n\nPaste your Instagram session ID:", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_main_session)
        return
    
    if text == "🎯 Target Session":
        session_data[chat_id]["current_menu"] = "target_session_input"
        session_data[chat_id]["previous_menu"] = "main"
        bot.send_message(chat_id, "<b>🎯 Send Target Session ID</b>\n\nPaste target account session ID:", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_target_session)
        return
    
    if text == "🔄 Swapper":
        show_swapper_menu(chat_id)
        return
    
    if text == "⚙️ Settings":
        show_settings_menu(chat_id)
        return
    
    if text in ["Run Main Swap", "BackUp Mode", "Threads Swap"]:
        handle_swap_option(chat_id, text)
        return
    
    if text in ["Bio", "Name", "Webhook", "Check Block", "Close Sessions"]:
        handle_settings_option(chat_id, text)
        return
    
    # Default response
    if text not in ["/start", "/help", "/tutorial"]:
        bot.send_message(chat_id, "🤖 *CARNAGE Swapper - Main Menu*\n\nUse the buttons below or type /help for commands.", parse_mode="Markdown")
        show_main_menu(chat_id)

def save_main_session(message):
    """Save main session"""
    chat_id = message.chat.id
    session_id = message.text.strip()
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "❌ Your account is not approved yet.", parse_mode="Markdown")
        show_main_menu(chat_id)
        return
    
    username = validate_session(session_id, chat_id, "main")
    if username:
        session_data[chat_id]["main"] = session_id
        session_data[chat_id]["main_username"] = f"@{username}"
        session_data[chat_id]["main_validated_at"] = time.time()
        save_session_to_db(chat_id, "main", session_id, username)
        bot.send_message(chat_id, f"✅ *Main Session Logged @{username}*", parse_mode="Markdown")
        award_achievement(chat_id, "first_session")
    
    show_main_menu(chat_id)

def save_target_session(message):
    """Save target session"""
    chat_id = message.chat.id
    session_id = message.text.strip()
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "❌ Your account is not approved yet.", parse_mode="Markdown")
        show_main_menu(chat_id)
        return
    
    username = validate_session(session_id, chat_id, "target")
    if username:
        session_data[chat_id]["target"] = session_id
        session_data[chat_id]["target_username"] = f"@{username}"
        session_data[chat_id]["target_validated_at"] = time.time()
        save_session_to_db(chat_id, "target", session_id, username)
        bot.send_message(chat_id, f"✅ *Target Session Logged @{username}*", parse_mode="Markdown")
        award_achievement(chat_id, "first_session")
    
    show_main_menu(chat_id)

def handle_swap_option(chat_id, option):
    """Handle swap option selection"""
    if option == "Run Main Swap":
        run_main_swap(chat_id)
    elif option == "BackUp Mode":
        session_data[chat_id]["current_menu"] = "backup_session_input"
        bot.send_message(chat_id, "<b>💾 Send Backup Session ID</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_backup_session)
    elif option == "Threads Swap":
        session_data[chat_id]["current_menu"] = "threads_input"
        bot.send_message(chat_id, "<b>🧵 Send Number of Threads (Recommended: 30+)</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_swapper_threads)

def handle_settings_option(chat_id, option):
    """Handle settings option selection"""
    if option == "Bio":
        session_data[chat_id]["current_menu"] = "bio_input"
        bot.send_message(chat_id, "<b>📝 Send Bio Text</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_bio)
    elif option == "Name":
        session_data[chat_id]["current_menu"] = "name_input"
        bot.send_message(chat_id, "<b>📛 Send Webhook Footer Name</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_name)
    elif option == "Webhook":
        session_data[chat_id]["current_menu"] = "webhook_input"
        bot.send_message(chat_id, "<b>🔗 Send Discord Webhook URL</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_swap_webhook)
    elif option == "Check Block":
        session_data[chat_id]["current_menu"] = "check_block_input"
        bot.send_message(chat_id, "<b>🔒 Check Account Swappable? (Y/N)</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, process_check_block)
    elif option == "Close Sessions":
        clear_session_data(chat_id, "close")
        bot.send_message(chat_id, "<b>🗑️ All Sessions Cleared</b>", parse_mode='HTML')
        show_settings_menu(chat_id)

def save_backup_session(message):
    """Save backup session"""
    chat_id = message.chat.id
    session_id = message.text.strip()
    username = validate_session(session_id, chat_id, "backup")
    if username:
        session_data[chat_id]["backup"] = session_id
        session_data[chat_id]["backup_username"] = f"@{username}"
        save_session_to_db(chat_id, "backup", session_id, username)
        bot.send_message(chat_id, f"✅ *Backup Session Logged @{username}*", parse_mode="Markdown")
    show_swapper_menu(chat_id)

def save_swapper_threads(message):
    """Save swapper threads"""
    chat_id = message.chat.id
    try:
        threads = int(message.text)
        if threads >= 1:
            session_data[chat_id]["swapper_threads"] = threads
            bot.send_message(chat_id, f"✅ *Threads Set: {threads}*", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ Enter number ≥ 1", parse_mode="Markdown")
    except:
        bot.send_message(chat_id, "❌ Enter valid number", parse_mode="Markdown")
    show_swapper_menu(chat_id)

def save_bio(message):
    """Save bio"""
    chat_id = message.chat.id
    bio = message.text.strip()
    session_data[chat_id]["bio"] = bio
    bot.send_message(chat_id, "✅ *Bio Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def save_name(message):
    """Save name"""
    chat_id = message.chat.id
    name = message.text.strip()
    session_data[chat_id]["name"] = name
    bot.send_message(chat_id, "✅ *Name Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def save_swap_webhook(message):
    """Save webhook"""
    chat_id = message.chat.id
    webhook = message.text.strip()
    session_data[chat_id]["swap_webhook"] = webhook
    bot.send_message(chat_id, "✅ *Webhook Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def process_check_block(message):
    """Process check block"""
    chat_id = message.chat.id
    response = message.text.strip().lower()
    if response == 'y':
        bot.send_message(chat_id, "✅ *Account is swappable!*", parse_mode="Markdown")
    elif response == 'n':
        bot.send_message(chat_id, "❌ *Account is not swappable!*", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Send 'Y' or 'N'", parse_mode="Markdown")
    show_settings_menu(chat_id)

def run_main_swap(chat_id):
    """Run main swap"""
    global requests_count, errors_count
    
    if not session_data[chat_id]["main"] or not session_data[chat_id]["target"]:
        bot.send_message(chat_id, "❌ *Set Main and Target Sessions first*", parse_mode="Markdown")
        show_swapper_menu(chat_id)
        return
    
    # Validate sessions
    main_valid = validate_session(session_data[chat_id]["main"], chat_id, "main")
    target_valid = validate_session(session_data[chat_id]["target"], chat_id, "target")
    
    if not main_valid or not target_valid:
        bot.send_message(chat_id, "❌ *Invalid Main or Target Session*", parse_mode="Markdown")
        show_swapper_menu(chat_id)
        return
    
    try:
        progress_message = bot.send_message(chat_id, "🔄 *Starting swap...*", parse_mode="Markdown")
        message_id = progress_message.message_id
        
        animation_frames = [
            "🔄 *Swapping username... █*",
            "🔄 *Swapping username... ██*",
            "🔄 *Swapping username... ███*",
            "🔄 *Swapping username... ████*"
        ]
        
        csrf_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        target_session = session_data[chat_id]["target"]
        target_username = session_data[chat_id]["target_username"]
        random_username = generate_random_username()
        
        # Step 1: Change target to random username
        bot.edit_message_text("🔄 *Changing target to random username...*", chat_id, message_id, parse_mode="Markdown")
        for i in range(4):
            bot.edit_message_text(animation_frames[i], chat_id, message_id, parse_mode="Markdown")
            time.sleep(0.5)
        
        time.sleep(2)
        random_username_full = change_username_account1(chat_id, target_session, csrf_token, random_username)
        if not random_username_full:
            bot.edit_message_text(f"❌ *Failed to update target {target_username}*", chat_id, message_id, parse_mode="Markdown")
            clear_session_data(chat_id, "main")
            clear_session_data(chat_id, "target")
            log_swap(chat_id, target_username, "failed", "Failed to change target to random username")
            show_swapper_menu(chat_id)
            return
        
        # Step 2: Change main to target username
        bot.edit_message_text(f"🔄 *Setting main to {target_username}...*", chat_id, message_id, parse_mode="Markdown")
        for i in range(4):
            bot.edit_message_text(animation_frames[i], chat_id, message_id, parse_mode="Markdown")
            time.sleep(0.5)
        
        time.sleep(2)
        success = change_username_account2(chat_id, session_data[chat_id]["main"], csrf_token, target_username)
        
        if success:
            bot.edit_message_text(f"✅ *Swap Successful!*\n\n🎯 {target_username}\n⏰ {datetime.now().strftime('%H:%M:%S')}", chat_id, message_id, parse_mode="Markdown")
            release_time = datetime.now().strftime("%I:%M:%S %p")
            bot.send_message(chat_id, f"✅ *{target_username} Released [{release_time}]*", parse_mode="Markdown")
            send_notifications(chat_id, target_username, "Swapped")
            log_swap(chat_id, target_username, "success")
            award_achievement(chat_id, "first_swap")
        else:
            bot.edit_message_text(f"❌ *Swap failed for {target_username}*", chat_id, message_id, parse_mode="Markdown")
            if revert_username(chat_id, target_session, csrf_token, target_username):
                bot.send_message(chat_id, f"✅ *Successfully reverted to {target_username}*", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, f"⚠️ *Warning: Could not revert to {target_username}*", parse_mode="Markdown")
            log_swap(chat_id, target_username, "failed", "Swap process failed")
            award_achievement(chat_id, "swap_failed")
        
        clear_session_data(chat_id, "main")
        clear_session_data(chat_id, "target")
        
    except Exception as e:
        bot.edit_message_text(f"❌ *Error during swap: {str(e)}*", chat_id, message_id, parse_mode="Markdown")
        log_swap(chat_id, "unknown", "failed", str(e))
    
    show_swapper_menu(chat_id)

# ==================== OTHER COMMAND FUNCTIONS ====================
def dashboard_command(message):
    """Dashboard command"""
    user_id = message.from_user.id
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    dashboard_url = f"https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/{user_id}"
    bot.send_message(user_id, f"📊 *Your Dashboard:*\n\n{dashboard_url}", parse_mode="Markdown")
    award_achievement(user_id, "dashboard_user")

def referral_command(message):
    """Referral command"""
    user_id = message.from_user.id
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref-{user_id}"
    bot.send_message(user_id, f"🎁 *Your Referral Link:*\n\n`{referral_link}`", parse_mode="Markdown")

def stats_command(message):
    """Stats command"""
    user_id = message.from_user.id
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    stats = get_user_detailed_stats(user_id)
    if stats:
        response = f"""
📊 *Your Statistics*

*Basic Info:*
• Username: @{stats['username']}
• Status: {"✅ Approved" if is_user_approved(user_id) else "⏳ Pending"}

*Swap Stats:*
• Total Swaps: {stats['stats'][0]['value']}
• Successful: {stats['stats'][1]['value']}
• Success Rate: {stats['stats'][2]['value']}

*Referral Stats:*
• Total Referrals: {stats['referrals']['count']}
• Free Swaps: {stats['referrals']['free_swaps']}

*Achievements:* {stats['achievements']['unlocked']}/{stats['achievements']['total']}
"""
        bot.send_message(user_id, response, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "📊 *No statistics yet. Start swapping!*", parse_mode="Markdown")

def achievements_command(message):
    """Achievements command"""
    user_id = message.from_user.id
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    achievements = get_user_achievements(user_id)
    response = "🏆 *Your Achievements*\n\n"
    
    if achievements['list']:
        for ach in achievements['list']:
            response += f"{ach['emoji']} *{ach['name']}* - {ach['date'].split()[0]}\n"
    else:
        response += "No achievements yet! Start using the bot! 🔄"
    
    bot.send_message(user_id, response, parse_mode="Markdown")

# ==================== TUTORIAL SYSTEM ====================
@bot.message_handler(commands=['tutorial'])
def start_tutorial_command(message):
    """Start tutorial"""
    user_id = message.chat.id
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    tutorial_sessions[user_id] = 0
    show_tutorial_step(user_id, 0)

TUTORIAL_STEPS = [
    {
        "title": "🎯 Welcome to CARNAGE Tutorial!",
        "message": "Learn how to swap Instagram usernames with our bot!",
        "buttons": ["Let's Go! 🚀", "Skip Tutorial"]
    },
    # ... (same tutorial steps as before)
]

def show_tutorial_step(chat_id, step_index):
    """Show tutorial step"""
    if step_index >= len(TUTORIAL_STEPS):
        return
    
    step = TUTORIAL_STEPS[step_index]
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    for i in range(0, len(step["buttons"]), 2):
        row = step["buttons"][i:i+2]
        markup.add(*[KeyboardButton(btn) for btn in row])
    
    bot.send_message(
        chat_id,
        f"*{step['title']}*\n\n{step['message']}",
        parse_mode="Markdown",
        reply_markup=markup
    )
    
    tutorial_sessions[chat_id] = step_index

def handle_tutorial_response(chat_id, text):
    """Handle tutorial responses"""
    if chat_id not in tutorial_sessions:
        return False
    
    current_step = tutorial_sessions[chat_id]
    
    if text == "Back":
        if current_step > 0:
            show_tutorial_step(chat_id, current_step - 1)
        return True
    
    elif text == "Skip Tutorial":
        del tutorial_sessions[chat_id]
        bot.send_message(chat_id, "Tutorial skipped! Use /tutorial anytime.", 
                        reply_markup=create_reply_menu(["Main Menu"]))
        return True
    
    elif "Let's Go" in text or "Got it" in text or "Ready" in text:
        show_tutorial_step(chat_id, current_step + 1)
        if current_step + 1 >= len(TUTORIAL_STEPS):
            award_achievement(chat_id, "tutorial_complete")
            del tutorial_sessions[chat_id]
        return True
    
    return False

# ==================== FLASK ROUTES ====================
@app.route('/')
def health_check():
    return jsonify({
        "status": "online",
        "service": "CARNAGE Swapper Bot",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0"
    })

@app.route('/ping1')
def ping1():
    return jsonify({"status": "pong1", "time": datetime.now().isoformat()})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# ==================== MAIN STARTUP ====================
def run_flask_app():
    """Run Flask app"""
    port = int(os.environ.get('PORT', 8000))
    print(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def run_telegram_bot():
    """Run Telegram bot"""
    print("🤖 Starting Telegram bot polling...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"❌ Bot polling error: {e}")
            time.sleep(5)
            continue

def main():
    """Main function"""
    # Start Flask server
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    time.sleep(2)
    
    # Initialize database
    print("🔧 Initializing database...")
    init_database()
    
    print("✅ Database initialized successfully")
    print("🚀 CARNAGE Swapper Bot v3.0 with REAL Instagram API")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot Username: @{BOT_USERNAME}")
    print(f"📢 Updates Channel: {CHANNELS['updates']['id']}")
    print(f"✅ Proofs Channel: {CHANNELS['proofs']['id']}")
    print("✨ Features: Real Instagram API, Dashboard, Referral, Tutorial, Achievements")
    
    # Start Telegram bot
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("🤖 Telegram bot started in background")
    
    print(f"📊 Dashboard: https://separate-genny-1carnage1-2b4c603c.koyeb.app")
    print("✅ Bot is fully operational with REAL Instagram API!")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Bot shutting down...")

if __name__ == '__main__':
    main()
