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
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, jsonify

# ==================== FLASK APP FOR KOYEB ====================
app = Flask(__name__)

# Required HTTP routes for Koyeb health checks
@app.route('/')
def health_check():
    """Required route for Koyeb to keep service alive"""
    return jsonify({
        "status": "online",
        "service": "CARNAGE Telegram Bot",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time() - start_time,
        "endpoints": ["/", "/health", "/stats", "/users"]
    })
# Add these routes to your bot.py
@app.route('/ping1')
def ping1():
    return jsonify({"status": "pong1", "time": datetime.now().isoformat()})

@app.route('/ping2')
def ping2():
    return jsonify({"status": "pong2", "time": datetime.now().isoformat()})

@app.route('/ping3')
def ping3():
    return jsonify({"status": "pong3", "time": datetime.now().isoformat()})
    
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/stats')
def web_stats():
    """Web stats endpoint"""
    return jsonify({
        "total_users": get_total_users(),
        "active_sessions": len(session_data),
        "requests_count": requests_count,
        "errors_count": errors_count,
        "bot_running": bot_running
    })

@app.route('/users')
def web_users():
    """Web users endpoint"""
    users = get_all_users()
    return jsonify({
        "total": len(users),
        "approved": sum(1 for u in users if u[3] == 1),
        "pending": sum(1 for u in users if u[3] == 0),
        "banned": sum(1 for u in users if u[5] == 1)
    })

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8271097949:AAGgugeFfdJa6NtrsrrIrIfqxcZeQ1xenA8')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '1002227808698')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '7575087826'))

# Global variables
bot = telebot.TeleBot(BOT_TOKEN)
start_time = time.time()
bot_running = True
session_data = {}
requests_count = 0
errors_count = 0
rate_limit_cooldowns = {}

# ==================== DATABASE SETUP ====================
def init_database():
    """Initialize SQLite database for user management"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Users table
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
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # Insert admin if not exists
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (ADMIN_USER_ID,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, approved, approved_until, join_date, last_active, is_banned, is_admin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ADMIN_USER_ID, "admin", "Admin", "User", 1, "9999-12-31 23:59:59", 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0, 1))
    
    conn.commit()
    conn.close()

# Initialize database at startup
init_database()

# ==================== DATABASE FUNCTIONS ====================
def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('users.db')

def add_user(user_id, username, first_name, last_name):
    """Add new user to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, join_date, last_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    
    conn.close()

def update_user_active(user_id):
    """Update user's last active time"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_active = ? WHERE user_id = ?", 
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()
    conn.close()

def get_user_status(user_id):
    """Get user approval status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT approved, approved_until, is_banned FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        approved = result[0]
        approved_until = result[1]
        is_banned = result[2]
        
        if is_banned:
            return "banned"
        
        if approved == 1:
            if approved_until and approved_until != "9999-12-31 23:59:59":
                try:
                    expiry_date = datetime.strptime(approved_until, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() > expiry_date:
                        return "expired"
                    else:
                        return "approved"
                except:
                    return "approved"
            else:
                return "approved"
    
    return "pending"

def approve_user(user_id, duration_days=None):
    """Approve user access"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if duration_days:
        if duration_days == "permanent":
            approved_until = "9999-12-31 23:59:59"
        else:
            approved_until = (datetime.now() + timedelta(days=int(duration_days))).strftime("%Y-%m-%d %H:%M:%S")
    else:
        approved_until = "9999-12-31 23:59:59"
    
    cursor.execute("UPDATE users SET approved = 1, approved_until = ? WHERE user_id = ?", 
                   (approved_until, user_id))
    conn.commit()
    conn.close()

def approve_all_users():
    """Approve all pending users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET approved = 1, approved_until = '9999-12-31 23:59:59' WHERE approved = 0 AND is_banned = 0")
    conn.commit()
    conn.close()

def disapprove_all_users():
    """Disapprove all non-admin users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET approved = 0, approved_until = NULL WHERE is_admin = 0")
    conn.commit()
    conn.close()

def ban_user(user_id, reason="No reason provided"):
    """Ban a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?", 
                   (reason, user_id))
    conn.commit()
    conn.close()

def unban_user(user_id):
    """Unban a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?", 
                   (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    """Get all users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, approved, approved_until, is_banned FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def get_total_users():
    """Get total user count"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_active_users_count():
    """Get count of users active in last 24 hours"""
    conn = get_db_connection()
    cursor = conn.cursor()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > ?", (yesterday,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def broadcast_message():
    """Get all user IDs for broadcasting"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE approved = 1 AND is_banned = 0")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# ==================== WELCOME MESSAGE ====================
WELCOME_MESSAGE = """
🤖 *Welcome to CARNAGE Swapper Bot* 🤖

*What this bot does:*
✨ *Instagram Username Swapping* - Swap usernames between accounts
🔒 *Secure Session Management* - Your sessions are encrypted
⚡ *Fast & Reliable* - High success rate swapping
📱 *Admin Notifications* - Get swap notifications directly
🔧 *Multiple Modes* - Main swap, backup mode, thread swapping

*How to get access:*
1️⃣ Send /start to begin
2️⃣ Contact admin @CARNAGEV1 for approval
3️⃣ Wait for admin to approve your access
4️⃣ Once approved, you can use all features

*Note:* Only approved users can access bot features. 
Please be patient while waiting for approval.

*Admin Commands:* /approve, /users, /broadcast, /ban, /unban, /stats
"""

# ==================== HELPER FUNCTIONS ====================
def is_admin(user_id):
    """Check if user is admin"""
    return user_id == ADMIN_USER_ID

def is_user_approved(user_id):
    """Check if user is approved"""
    status = get_user_status(user_id)
    return status == "approved"

def send_to_admin(message_text, parse_mode="Markdown"):
    """Send notification to admin"""
    try:
        bot.send_message(ADMIN_USER_ID, message_text, parse_mode=parse_mode)
    except Exception as e:
        print(f"Failed to send message to admin: {e}")

def init_session_data(chat_id):
    if chat_id not in session_data:
        session_data[chat_id] = {
            "main": None, "main_username": None, "main_validated_at": None,
            "target": None, "target_username": None, "target_validated_at": None,
            "backup": None, "backup_username": None,
            "bio": None, "name": None,
            "swapper_threads": 1,
            "current_menu": "main",
            "previous_menu": None
        }

def clear_session_data(chat_id, session_type):
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

def check_cooldown(chat_id):
    if chat_id in rate_limit_cooldowns:
        cooldown_until = rate_limit_cooldowns[chat_id]
        if time.time() < cooldown_until:
            bot.send_message(chat_id, "<b>⚠️ Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
            return False
    return True

def set_cooldown(chat_id):
    rate_limit_cooldowns[chat_id] = time.time() + 1800  # 30-minute cooldown

def create_reply_menu(buttons, row_width=2, add_back=True):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    for i in range(0, len(buttons), row_width):
        row = [KeyboardButton(text) for text in buttons[i:i + row_width]]
        markup.add(*row)
    if add_back:
        markup.add(KeyboardButton("Back"))
    return markup

def validate_session(session_id, chat_id, session_type):
    print(f"Validating session for chat_id: {chat_id}, type: {session_type}, session_id: {session_id}")
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
    back_menu = "swapper" if session_type == "backup" else "main"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Validation response: {response.status_code}, {response.text[:100]}")
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
    session_data[chat_id]["current_menu"] = back_menu
    return None

def send_admin_notification(username, action, user_info=""):
    """Send swap notification to admin"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if action == "Swapped":
        notification = f"""
🔄 *CARNAGE Swap Notification*

✅ *Successful Swap*
👤 Username: `{username}`
🕒 Time: {current_time}
{user_info}

📍 Status: Successfully swapped!
📊 Bot: CARNAGE Swapper
        """
    elif action == "Failed":
        notification = f"""
🔄 *CARNAGE Swap Notification*

❌ *Failed Swap*
👤 Username: `{username}`
🕒 Time: {current_time}
{user_info}

📍 Status: Swap failed!
📊 Bot: CARNAGE Swapper
        """
    
    send_to_admin(notification)

def send_channel_notification(username, action):
    """Send notification to Telegram channel (optional)"""
    if TELEGRAM_CHANNEL_ID and TELEGRAM_CHANNEL_ID != "-100":
        try:
            username_clean = username.lstrip('@')
            message = f"<b>🔁 [#] {username} {action}!</b>"
            bot.send_message(TELEGRAM_CHANNEL_ID, message, parse_mode="HTML")
        except:
            pass

def generate_random_username():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def change_username_account1(chat_id, session_id, csrf_token, random_username):
    global requests_count, errors_count
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'CARNAGE User'),
        'email': 'carnage@example.com',
        'username': random_username,
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Swapped by CARNAGE'),
        'external_url': 'https://t.me/CARNAGEV1',
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
        requests_count += 1
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
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'CARNAGE User'),
        'email': 'carnage@example.com',
        'username': original_username.lstrip('@'),
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Swapped by CARNAGE'),
        'external_url': 'https://t.me/CARNAGEV1',
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
    global requests_count, errors_count
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'CARNAGE User'),
        'email': 'carnage@example.com',
        'username': target_username.lstrip('@'),
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Swapped by CARNAGE'),
        'external_url': 'https://t.me/CARNAGEV1',
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
        if not check_cooldown(chat_id):
            return False
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

def show_main_menu(chat_id):
    if not is_user_approved(chat_id):
        return
    
    session_data[chat_id]["current_menu"] = "main"
    session_data[chat_id]["previous_menu"] = None
    buttons = [
        "Main Session", "Check Block", "Target Session",
        "Swapper", "Settings", "Close Bot"
    ]
    markup = create_reply_menu(buttons, row_width=2, add_back=False)
    bot.send_message(chat_id, "<b>🤖 CARNAGE Swapper - Choose A Mode</b>", parse_mode='HTML', reply_markup=markup)

def show_swapper_menu(chat_id):
    if not is_user_approved(chat_id):
        return
    
    session_data[chat_id]["current_menu"] = "swapper"
    session_data[chat_id]["previous_menu"] = "main"
    buttons = ["Run Main Swap", "BackUp Mode", "Threads Swap"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b>🔄 CARNAGE Swapper - Select Option</b>", parse_mode='HTML', reply_markup=markup)

def show_settings_menu(chat_id):
    if not is_user_approved(chat_id):
        return
    
    session_data[chat_id]["current_menu"] = "settings"
    session_data[chat_id]["previous_menu"] = "main"
    buttons = ["Bio", "Name"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b>⚙️ CARNAGE Settings - Select Option</b>", parse_mode='HTML', reply_markup=markup)

# ==================== COMMAND HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    
    add_user(user_id, username, first_name, last_name)
    
    bot.send_message(user_id, WELCOME_MESSAGE, parse_mode="Markdown")
    
    admin_notification = f"""
🆕 *New User Started CARNAGE Bot*
    
👤 User ID: `{user_id}`
📛 Name: {first_name} {last_name}
🔗 Username: @{username if username else 'N/A'}
⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📍 Status: Pending Approval
🔧 Action: Use /approve {user_id} to grant access
"""
    send_to_admin(admin_notification)
    
    if is_user_approved(user_id):
        init_session_data(user_id)
        show_main_menu(user_id)
    else:
        bot.send_message(
            user_id,
            "⏳ *Your access is pending approval.*\n\n"
            "Please contact @CARNAGEV1 for access approval.\n"
            "You'll be notified once approved.",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['approve'])
def approve_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 *Admin access required!*", parse_mode="Markdown")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, 
                        "⚠️ *Usage:* `/approve <user_id> [duration]`\n"
                        "Example: `/approve 123456789 7d` for 7 days\n"
                        "Example: `/approve 123456789 permanent` for permanent",
                        parse_mode="Markdown")
            return
        
        target_user_id = int(args[1])
        duration = None
        
        if len(args) > 2:
            duration_str = args[2].lower()
            if duration_str == "permanent":
                duration = "permanent"
            elif duration_str.endswith('d'):
                try:
                    days = int(duration_str[:-1])
                    duration = days
                except:
                    bot.reply_to(message, "❌ Invalid duration format. Use like '7d' or 'permanent'")
                    return
        
        approve_user(target_user_id, duration)
        
        duration_text = "permanent" if duration == "permanent" else f"{duration} days" if duration else "permanent"
        bot.reply_to(message, f"✅ User `{target_user_id}` approved for {duration_text}")
        
        try:
            if duration:
                expiry_text = f"for {duration} days" if duration != "permanent" else "permanently"
            else:
                expiry_text = "permanently"
            
            bot.send_message(
                target_user_id,
                f"🎉 *Access Approved!*\n\n"
                f"Your access to CARNAGE Swapper Bot has been approved {expiry_text}!\n"
                f"You can now use all features of the bot.\n\n"
                f"Send /start again to begin.",
                parse_mode="Markdown"
            )
        except:
            pass
        
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID format")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['approveall'])
def approve_all_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 *Admin access required!*", parse_mode="Markdown")
        return
    
    approve_all_users()
    bot.reply_to(message, "✅ All pending users have been approved!")

@bot.message_handler(commands=['disapproveall'])
def disapprove_all_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 *Admin access required!*", parse_mode="Markdown")
        return
    
    disapprove_all_users()
    bot.reply_to(message, "✅ All non-admin users have been disapproved!")

@bot.message_handler(commands=['users'])
def users_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 *Admin access required!*", parse_mode="Markdown")
        return
    
    users = get_all_users()
    
    if not users:
        bot.reply_to(message, "📭 No users found")
        return
    
    response = "👥 *CARNAGE Bot Users*\n\n"
    for user in users:
        user_id, username, first_name, approved, approved_until, is_banned = user
        
        status = "✅ Approved" if approved == 1 else "⏳ Pending"
        if is_banned == 1:
            status = "🚫 Banned"
        
        username_display = f"@{username}" if username else "No username"
        name_display = f"{first_name}" if first_name else "Unknown"
        
        expiry_text = ""
        if approved_until and approved_until != "9999-12-31 23:59:59":
            try:
                expiry_date = datetime.strptime(approved_until, "%Y-%m-%d %H:%M:%S")
                if expiry_date < datetime.now():
                    expiry_text = " (Expired)"
                else:
                    expiry_text = f" (Expires: {expiry_date.strftime('%Y-%m-%d')})"
            except:
                pass
        
        response += f"🆔 `{user_id}`\n"
        response += f"👤 {name_display} {username_display}\n"
        response += f"📊 {status}{expiry_text}\n"
        response += "─" * 20 + "\n"
    
    total_users = get_total_users()
    active_users = get_active_users_count()
    
    response += f"\n📈 *Statistics*\n"
    response += f"• Total Users: {total_users}\n"
    response += f"• Active (24h): {active_users}\n"
    response += f"• Pending Approval: {sum(1 for u in users if u[3] == 0 and u[5] == 0)}\n"
    response += f"• Banned: {sum(1 for u in users if u[5] == 1)}\n"
    
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            bot.send_message(message.chat.id, part, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 *Admin access required!*", parse_mode="Markdown")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, 
                        "⚠️ *Usage:* `/ban <user_id> [reason]`\n"
                        "Example: `/ban 123456789 Spamming`",
                        parse_mode="Markdown")
            return
        
        target_user_id = int(args[1])
        reason = " ".join(args[2:]) if len(args) > 2 else "No reason provided"
        
        ban_user(target_user_id, reason)
        
        bot.reply_to(message, f"🚫 User `{target_user_id}` has been banned.\nReason: {reason}")
        
        try:
            bot.send_message(
                target_user_id,
                f"🚫 *Account Banned*\n\n"
                f"Your access to CARNAGE Swapper Bot has been suspended.\n"
                f"Reason: {reason}\n\n"
                f"Contact @CARNAGEV1 if you believe this is a mistake.",
                parse_mode="Markdown"
            )
        except:
            pass
        
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID format")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['unban'])
def unban_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 *Admin access required!*", parse_mode="Markdown")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, 
                        "⚠️ *Usage:* `/unban <user_id>`\n"
                        "Example: `/unban 123456789`",
                        parse_mode="Markdown")
            return
        
        target_user_id = int(args[1])
        unban_user(target_user_id)
        
        bot.reply_to(message, f"✅ User `{target_user_id}` has been unbanned")
        
        try:
            bot.send_message(
                target_user_id,
                f"✅ *Account Unbanned*\n\n"
                f"Your access to CARNAGE Swapper Bot has been restored.\n"
                f"You can now use the bot again.",
                parse_mode="Markdown"
            )
        except:
            pass
        
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID format")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 *Admin access required!*", parse_mode="Markdown")
        return
    
    try:
        if message.reply_to_message:
            broadcast_text = message.reply_to_message.text
        else:
            broadcast_text = message.text.split(' ', 1)[1] if len(message.text.split(' ', 1)) > 1 else None
        
        if not broadcast_text:
            bot.reply_to(message, 
                        "⚠️ *Usage:* Reply to a message with /broadcast\n"
                        "OR\n"
                        "/broadcast <your message>",
                        parse_mode="Markdown")
            return
        
        users = broadcast_message()
        
        if not users:
            bot.reply_to(message, "📭 No users to broadcast to")
            return
        
        bot.reply_to(message, f"📢 Broadcasting to {len(users)} users...")
        
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                bot.send_message(user, broadcast_text)
                success_count += 1
                time.sleep(0.1)
            except:
                fail_count += 1
        
        bot.reply_to(message, 
                    f"✅ Broadcast Complete!\n"
                    f"• Successfully sent: {success_count}\n"
                    f"• Failed: {fail_count}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 *Admin access required!*", parse_mode="Markdown")
        return
    
    total_users = get_total_users()
    active_users = get_active_users_count()
    
    stats_text = f"""
📊 *CARNAGE Bot Statistics*

👥 *Users:*
• Total Users: {total_users}
• Active (24h): {active_users}
• Pending Approval: {sum(1 for u in get_all_users() if u[3] == 0 and u[5] == 0)}
• Banned Users: {sum(1 for u in get_all_users() if u[5] == 1)}

⚙️ *Bot Performance:*
• Total Requests: {requests_count}
• Total Errors: {errors_count}
• Active Sessions: {len(session_data)}
• Cooldown Users: {len(rate_limit_cooldowns)}

🕒 *Uptime:* Running
📅 *Last Check:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    bot.reply_to(message, stats_text, parse_mode="Markdown")

# ==================== MENU HANDLERS ====================
@bot.message_handler(func=lambda message: message.text in [
    "Main Session", "Check Block", "Target Session", "Swapper", "Settings", "Close Bot",
    "Run Main Swap", "BackUp Mode", "Threads Swap", "Bio", "Name", "Back", "Stop CARNAGE"
])
def handle_menu_navigation(message):
    chat_id = message.chat.id
    update_user_active(chat_id)
    
    if not is_user_approved(chat_id):
        bot.reply_to(message, "🚫 *Access restricted to approved users only.*", parse_mode='HTML')
        return
    
    text = message.text
    
    if text == "Back":
        previous_menu = session_data[chat_id]["previous_menu"]
        if previous_menu == "main":
            show_main_menu(chat_id)
        elif previous_menu == "swapper":
            show_swapper_menu(chat_id)
        elif previous_menu == "settings":
            show_settings_menu(chat_id)
        return
    
    if text == "Stop CARNAGE":
        bot.send_message(chat_id, "<b>🛑 CARNAGE Stopped</b>", parse_mode='HTML')
        show_swapper_menu(chat_id)
        return
    
    init_session_data(chat_id)
    
    if session_data[chat_id]["current_menu"] == "main":
        if text == "Main Session":
            session_data[chat_id]["current_menu"] = "main_session_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b>📥 Send Main Session ID</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_main_session)
        elif text == "Check Block":
            session_data[chat_id]["current_menu"] = "check_block_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b>🔒 Do You Want To Check Block (Y/N):</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, process_check_block)
        elif text == "Target Session":
            session_data[chat_id]["current_menu"] = "target_session_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b>🎯 Send Target Session ID</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_target_session)
        elif text == "Swapper":
            show_swapper_menu(chat_id)
        elif text == "Settings":
            show_settings_menu(chat_id)
        elif text == "Close Bot":
            clear_session_data(chat_id, "close")
            bot.send_message(chat_id, "<b>🔄 Main and Target Sessions Reset</b>", parse_mode='HTML')
            show_main_menu(chat_id)
    
    elif session_data[chat_id]["current_menu"] == "swapper":
        if text == "Run Main Swap":
            run_main_swap(chat_id)
        elif text == "BackUp Mode":
            session_data[chat_id]["current_menu"] = "backup_session_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b>💾 Send Backup Session ID</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_backup_session)
        elif text == "Threads Swap":
            session_data[chat_id]["current_menu"] = "threads_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b>🔢 Send Number of Threads (Recommended: 30+)</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_swapper_threads)
    
    elif session_data[chat_id]["current_menu"] == "settings":
        if text == "Bio":
            session_data[chat_id]["current_menu"] = "bio_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b>📝 Send Bio Text</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_bio)
        elif text == "Name":
            session_data[chat_id]["current_menu"] = "name_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b>👤 Send Profile Name</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_name)

def save_main_session(message):
    chat_id = message.chat.id
    update_user_active(chat_id)
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "<b>🚫 Access restricted to approved users only.</b>", parse_mode='HTML')
        return
    
    init_session_data(chat_id)
    session_id = message.text.strip()
    username = validate_session(session_id, chat_id, "main")
    if username:
        session_data[chat_id]["main"] = session_id
        session_data[chat_id]["main_username"] = f"@{username}"
        session_data[chat_id]["main_validated_at"] = time.time()
        bot.send_message(chat_id, f"<b>✅ Main Session Logged: @{username}</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "main"
    show_main_menu(chat_id)

def process_check_block(message):
    chat_id = message.chat.id
    update_user_active(chat_id)
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "<b>🚫 Access restricted to approved users only.</b>", parse_mode='HTML')
        return
    
    init_session_data(chat_id)
    response = message.text.strip().lower()
    if response == 'y':
        bot.send_message(chat_id, "<b>✅ Your Account Is Swappable!</b>", parse_mode='HTML')
    elif response == 'n':
        bot.send_message(chat_id, "<b>❌ Your Account Doesn't Swappable!</b>", parse_mode='HTML')
    else:
        bot.send_message(chat_id, "<b>⚠️ Please send 'Y' or 'N'</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, process_check_block)
        return
    session_data[chat_id]["current_menu"] = "main"
    show_main_menu(chat_id)

def save_target_session(message):
    chat_id = message.chat.id
    update_user_active(chat_id)
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "<b>🚫 Access restricted to approved users only.</b>", parse_mode='HTML')
        return
    
    init_session_data(chat_id)
    session_id = message.text.strip()
    username = validate_session(session_id, chat_id, "target")
    if username:
        session_data[chat_id]["target"] = session_id
        session_data[chat_id]["target_username"] = f"@{username}"
        session_data[chat_id]["target_validated_at"] = time.time()
        bot.send_message(chat_id, f"<b>✅ Target Session Logged: @{username}</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "main"
    show_main_menu(chat_id)

def save_backup_session(message):
    chat_id = message.chat.id
    update_user_active(chat_id)
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "<b>🚫 Access restricted to approved users only.</b>", parse_mode='HTML')
        return
    
    init_session_data(chat_id)
    session_id = message.text.strip()
    username = validate_session(session_id, chat_id, "backup")
    if username:
        session_data[chat_id]["backup"] = session_id
        session_data[chat_id]["backup_username"] = f"@{username}"
        bot.send_message(chat_id, f"<b>✅ Backup Session Logged: @{username}</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "swapper"
    show_swapper_menu(chat_id)

def save_swapper_threads(message):
    chat_id = message.chat.id
    update_user_active(chat_id)
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "<b>🚫 Access restricted to approved users only.</b>", parse_mode='HTML')
        return
    
    init_session_data(chat_id)
    try:
        threads = int(message.text)
        if threads >= 1:
            session_data[chat_id]["swapper_threads"] = threads
            bot.send_message(chat_id, f"<b>✅ Threads Saved: {threads}</b>", parse_mode='HTML')
        else:
            bot.send_message(chat_id, "<b>⚠️ Enter a number greater than or equal to 1</b>", parse_mode='HTML')
            bot.register_next_step_handler_by_chat_id(chat_id, save_swapper_threads)
            return
    except ValueError:
        bot.send_message(chat_id, "<b>⚠️ Enter a valid number</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_swapper_threads)
        return
    session_data[chat_id]["current_menu"] = "swapper"
    show_swapper_menu(chat_id)

def save_bio(message):
    chat_id = message.chat.id
    update_user_active(chat_id)
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "<b>🚫 Access restricted to approved users only.</b>", parse_mode='HTML')
        return
    
    init_session_data(chat_id)
    bio = message.text.strip()
    session_data[chat_id]["bio"] = bio
    bot.send_message(chat_id, "<b>✅ Bio Set</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "settings"
    show_settings_menu(chat_id)

def save_name(message):
    chat_id = message.chat.id
    update_user_active(chat_id)
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "<b>🚫 Access restricted to approved users only.</b>", parse_mode='HTML')
        return
    
    init_session_data(chat_id)
    name = message.text.strip()
    session_data[chat_id]["name"] = name
    bot.send_message(chat_id, "<b>✅ Name Saved</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "settings"
    show_settings_menu(chat_id)

def run_main_swap(chat_id):
    global requests_count, errors_count
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "<b>🚫 Access restricted to approved users only.</b>", parse_mode='HTML')
        return
    
    init_session_data(chat_id)
    
    if not session_data[chat_id]["main"] or not session_data[chat_id]["target"]:
        bot.send_message(
            chat_id, "<b>❌ Set Main and Target Sessions first.</b>", parse_mode='HTML',
            reply_markup=create_reply_menu([], add_back=True)
        )
        session_data[chat_id]["current_menu"] = "swapper"
        return
    
    main_valid = session_data[chat_id]["main_username"].lstrip('@') if session_data[chat_id]["main_validated_at"] and time.time() - session_data[chat_id]["main_validated_at"] < 3600 else validate_session(session_data[chat_id]["main"], chat_id, "main")
    target_valid = session_data[chat_id]["target_username"].lstrip('@') if session_data[chat_id]["target_validated_at"] and time.time() - session_data[chat_id]["target_validated_at"] < 3600 else validate_session(session_data[chat_id]["target"], chat_id, "target")
    
    if not main_valid or not target_valid:
        bot.send_message(
            chat_id, "<b>❌ Invalid Main or Target Session.</b>", parse_mode='HTML',
            reply_markup=create_reply_menu([], add_back=True)
        )
        session_data[chat_id]["current_menu"] = "swapper"
        return
    
    try:
        progress_message = bot.send_message(chat_id, "<b>🔄 Starting CARNAGE swap...</b>", parse_mode='HTML')
        message_id = progress_message.message_id

        animation_frames = [
            "<b>🔄 Swapping username... █</b>",
            "<b>🔄 Swapping username... ██</b>",
            "<b>🔄 Swapping username... ███</b>",
            "<b>🔄 Swapping username... ████</b>"
        ]
        
        csrf_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        target_session = session_data[chat_id]["target"]
        target_username = session_data[chat_id]["target_username"]
        random_username = generate_random_username()

        # Step 1: Change target to random username
        bot.edit_message_text(
            "<b>🔄 Changing target to random username...</b>", chat_id, message_id, parse_mode='HTML'
        )
        for i in range(4):
            bot.edit_message_text(animation_frames[i], chat_id, message_id, parse_mode='HTML')
            time.sleep(0.5)
        time.sleep(2)
        
        random_username_full = change_username_account1(chat_id, target_session, csrf_token, random_username)
        if not random_username_full:
            bot.edit_message_text(
                f"<b>❌ Failed to update target {target_username}.</b>", chat_id, message_id, parse_mode='HTML'
            )
            clear_session_data(chat_id, "main")
            clear_session_data(chat_id, "target")
            
            # Send failure notification to admin
            user_info = f"👤 User ID: `{chat_id}`\n🎯 Target: {target_username}"
            send_admin_notification(target_username, "Failed", user_info)
            
            show_swapper_menu(chat_id)
            return

        # Step 2: Change main to target username
        bot.edit_message_text(
            f"<b>🔄 Setting main to {target_username}...</b>", chat_id, message_id, parse_mode='HTML'
        )
        for i in range(4):
            bot.edit_message_text(animation_frames[i], chat_id, message_id, parse_mode='HTML')
            time.sleep(0.5)
        time.sleep(2)
        
        success = change_username_account2(chat_id, session_data[chat_id]["main"], csrf_token, target_username)
        if success:
            bot.edit_message_text(
                f"<b>✅ CARNAGE Swap Success!\n🎯 {target_username}\n📍 Username swapped successfully!</b>", chat_id, message_id, parse_mode='HTML'
            )
            release_time = datetime.now().strftime("%I:%M:%S %p")
            bot.send_message(
                chat_id, f"<b>🕒 {target_username} Released [{release_time}]</b>", parse_mode='HTML'
            )
            
            # Send success notification to admin
            user_info = f"👤 User ID: `{chat_id}`\n🎯 Target: {target_username}\n🕒 Time: {release_time}"
            send_admin_notification(target_username, "Swapped", user_info)
            
            # Optional: Send to channel
            send_channel_notification(target_username, "Swapped")
        else:
            bot.edit_message_text(
                f"<b>❌ Swap failed for {target_username}.</b>", chat_id, message_id, parse_mode='HTML'
            )
            
            # Send failure notification to admin
            user_info = f"👤 User ID: `{chat_id}`\n🎯 Target: {target_username}"
            send_admin_notification(target_username, "Failed", user_info)
            
            if revert_username(chat_id, target_session, csrf_token, target_username):
                bot.send_message(
                    chat_id, f"<b>✅ Successfully reverted to {target_username}.</b>", parse_mode='HTML'
                )
            else:
                bot.send_message(
                    chat_id, f"<b>⚠️ Warning: Could not revert to {target_username}.</b>", parse_mode='HTML'
                )
        
        clear_session_data(chat_id, "main")
        clear_session_data(chat_id, "target")
        
    except Exception as e:
        bot.edit_message_text(
            f"<b>❌ Error during swap: {str(e)}</b>", chat_id, message_id, parse_mode='HTML'
        )
        
        # Send error notification to admin
        error_info = f"👤 User ID: `{chat_id}`\n🎯 Target: {target_username}\n❌ Error: {str(e)}"
        send_admin_notification(target_username, "Failed", error_info)
    
    show_swapper_menu(chat_id)

# ==================== TELEGRAM BOT POLLING THREAD ====================
def run_telegram_bot():
    """Run Telegram bot in separate thread"""
    print("🤖 Starting Telegram bot polling...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"❌ Bot polling error: {e}")
            time.sleep(5)
            continue

# ==================== MAIN STARTUP ====================
def main():
    """Start everything"""
    print("🚀 CARNAGE Swapper Bot with Admin System")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print("📊 Database initialized")
    
    # Start Telegram bot in background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("🤖 Telegram bot started in background")
    
    # Get port from environment (Koyeb provides PORT)
    port = int(os.environ.get('PORT', 8080))
    
    # Start Flask app (main thread)
    print(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
