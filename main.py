import os
import requests
import base64
import telebot
from telebot import types
import time
import sqlite3
import json
from datetime import datetime
from flask import Flask, jsonify, request
import logging
import threading
import csv
import io
import sys

# ========== CONFIGURATION ==========
BOT_TOKEN = "8522048948:AAGSCayCSZZF_6z2nHcGjVC7B64E3C9u6F8"
BOT_PORT = int(os.environ.get('PORT', 6001))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# ========== ADMIN CONFIG ==========
ADMIN_ID = 7575087826
BANNED_USERS = set()

# ========== CHANNEL VERIFICATION ==========
REQUIRED_CHANNEL = "@botupdates_2"  # Channel username

# ========== FACE SWAP CONFIG ==========
FACE_SWAP_API_TOKEN = "0.ufDEMbVMT7mc9_XLsFDSK5CQqdj9Cx_Zjww0DevIvXN5M4fXQr3B9YtPdGkKAHjXBK6UC9rFcEbZbzCfkxxgmdTYV8iPzTby0C03dTKv5V9uXFYfwIVlqwNbIsfOK_rLRHIPB31bQ0ijSTEd-lLbllf3MkEcpkEZFFmmq8HMAuRuliCXFEdCwEB1HoYSJtvJEmDIVsooU3gYdrCm5yOJ8_lZ4DiHCSvy7P8-YxwJKkapJNCMUCFIfJbWDkDzvh8DGPyTRoHbURX8kClfImmPrGcqlfd7kkoNRcudS25IbNf1CGBsh8V96MtEhnTZvOpZfnp5dpV7MfgwOgvx7hUazUaC_wxQE63Aa0uOPuGvJ70BNrmeZIIrY9roD1Koj316L4g2BZ_LLZZF11wcrNNon8UXB0iVudiNCJyDQCxLUmblXUpt4IUvRoiOqXBNtWtLqY0su0ieVB0jjyDf_-zs7wc8WQ_jqp-NsTxgKOgvZYWV6Elz_lf4cNxGHZJ5BdcyLEoRBH3cksvwoncmYOy5Ulco22QT-x2z06xVFBZYZMVulxAcmvQemKfSFKsNaDxwor35p-amn9Vevhyb-GzA_oIoaTmc0fVXSshax2rdFQHQms86fZ_jkTieRpyIuX0mI3C5jLGIiOXzWxNgax9eZeQstYjIh8BIdMiTIUHfyKVTgtoLbK0hjTUTP0xDlCLnOt5qHdwe_iTWedBsswAJWYdtIxw0YUfIU22GMYrJoekOrQErawNlU5yT-LhXquBQY3EBtEup4JMWLendSh68d6HqjN2T3sAfVw0nY5jg7_5LJwj5gqEk57devNN8GGhogJpfdGzYoNGja22IZIuDnPPmWTpGx4VcLOLknSHrzio.tXUN6eooS69z3QtBp-DY1g.d882822dfe05be2b36ed1950554e1bac753abfe304a289adc4289b3f0d517356"

# ========== FLASK APP ==========
app = Flask(__name__)

# ========== TELEGRAM BOT ==========
# Initialize bot once - use either webhook OR polling, not both
bot = telebot.TeleBot(BOT_TOKEN)

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== DATABASE SETUP ==========
def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            verified INTEGER DEFAULT 0,
            swaps_count INTEGER DEFAULT 0,
            successful_swaps INTEGER DEFAULT 0,
            failed_swaps INTEGER DEFAULT 0
        )
    ''')
    
    # Swaps history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS swaps_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            swap_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            processing_time REAL,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Load banned users
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE is_banned = 1')
    for row in cursor.fetchall():
        BANNED_USERS.add(row[0])
    conn.close()

init_database()

# ========== USER DATA FOR FACE SWAP ==========
user_data = {}
WAITING_FOR_SOURCE = 1
WAITING_FOR_TARGET = 2

# ========== USER MANAGEMENT FUNCTIONS ==========
def register_user(user_id, username, first_name, last_name):
    """Register or update user in database"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, last_active)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, username, first_name, last_name))
    
    conn.commit()
    conn.close()
    
    # Check if new user and notify admin
    if is_new_user(user_id):
        notify_admin_new_user(user_id, username, first_name, last_name)

def is_new_user(user_id):
    """Check if user is new"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0

def notify_admin_new_user(user_id, username, first_name, last_name):
    """Notify admin about new user"""
    try:
        total_users = get_total_users()
        
        # Fixed message - removed Markdown formatting that was causing parsing error
        message = f"""👤 NEW USER REGISTERED

━━━━━━━━━━━━━━━━━━
🆔 User ID: {user_id}
👤 Username: @{username or 'N/A'}
📛 Name: {first_name} {last_name or ''}
🕐 Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
📊 Total Users: {total_users}
━━━━━━━━━━━━━━━━━━

Admin Commands:
/ban {user_id} - Ban user
/users - List all users
/botstatus - Check bot status"""
        
        bot.send_message(ADMIN_ID, message)
    except Exception as e:
        logger.error(f"Admin notification error: {e}")

def get_total_users():
    """Get total registered users"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_active_users_count(days=7):
    """Get active users in last X days"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    # FIXED: Proper SQLite parameter binding syntax
    query = f"""
        SELECT COUNT(*) FROM users 
        WHERE last_active >= datetime('now', '-{days} days')
    """
    cursor.execute(query)
    count = cursor.fetchone()[0]
    conn.close()
    return count

def ban_user(user_id):
    """Ban a user"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    BANNED_USERS.add(user_id)
    logger.info(f"User {user_id} banned")

def unban_user(user_id):
    """Unban a user"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    if user_id in BANNED_USERS:
        BANNED_USERS.remove(user_id)
    logger.info(f"User {user_id} unbanned")

def get_all_users():
    """Get all users with details"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, first_name, last_name, 
               join_date, last_active, is_banned, verified,
               swaps_count, successful_swaps, failed_swaps
        FROM users 
        ORDER BY join_date DESC
    ''')
    users = cursor.fetchall()
    conn.close()
    return users

def update_user_stats(user_id, success=True):
    """Update user swap statistics"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    if success:
        cursor.execute('''
            UPDATE users SET 
            swaps_count = swaps_count + 1,
            successful_swaps = successful_swaps + 1,
            last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,))
    else:
        cursor.execute('''
            UPDATE users SET 
            swaps_count = swaps_count + 1,
            failed_swaps = failed_swaps + 1,
            last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,))
    
    conn.commit()
    conn.close()

def add_swap_history(user_id, status, processing_time):
    """Add swap to history"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO swaps_history (user_id, status, processing_time)
        VALUES (?, ?, ?)
    ''', (user_id, status, processing_time))
    conn.commit()
    conn.close()

def check_channel_membership(user_id):
    """Check if user is member of required channel"""
    try:
        chat_member = bot.get_chat_member(REQUIRED_CHANNEL.replace('@', ''), user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Channel check error: {e}")
        return False

def verify_user(user_id):
    """Verify user and update database"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET verified = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# ========== FLASK ENDPOINTS ==========
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "Face Swap Bot",
        "version": "2.0",
        "creator": "@PokiePy",
        "admin_id": ADMIN_ID,
        "endpoints": {
            "/": "This page",
            "/health": "Health check",
            "/stats": "Bot statistics",
            "/users": "User statistics",
            "/ping": "Simple ping endpoint",
            "/ping1": "Another ping endpoint"
        },
        "features": ["Face Swap", "Admin Controls", "Channel Verification", "User Management"]
    })

@app.route('/health')
def health_check():
    try:
        return jsonify({
            "status": "healthy",
            "bot": "running",
            "database": "connected",
            "total_users": get_total_users(),
            "active_users_24h": get_active_users_count(1),
            "banned_users": len(BANNED_USERS),
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/stats')
def stats_api():
    try:
        conn = sqlite3.connect('face_swap_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM swaps_history')
        total_swaps = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM swaps_history WHERE status = "success"')
        successful_swaps = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM swaps_history WHERE status = "failed"')
        failed_swaps = cursor.fetchone()[0]
        
        conn.close()
        
        success_rate = (successful_swaps / max(1, total_swaps)) * 100 if total_swaps > 0 else 0
        
        return jsonify({
            "total_users": get_total_users(),
            "active_users_24h": get_active_users_count(1),
            "banned_users": len(BANNED_USERS),
            "verified_users": len([u for u in get_all_users() if u[7] == 1]),
            "swap_statistics": {
                "total_swaps": total_swaps,
                "successful_swaps": successful_swaps,
                "failed_swaps": failed_swaps,
                "success_rate": round(success_rate, 2)
            },
            "active_sessions": len([uid for uid, data in user_data.items() if data.get('state')]),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Stats API error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/ping')
def ping():
    return jsonify({"status": "pong", "time": datetime.now().isoformat()})

@app.route('/ping1')
def ping1():
    return jsonify({"status": "pong1", "time": datetime.now().isoformat()})

@app.route('/users')
def users_api():
    try:
        users = get_all_users()
        user_list = []
        
        for user in users:
            user_list.append({
                "user_id": user[0],
                "username": user[1],
                "first_name": user[2],
                "last_name": user[3],
                "join_date": user[4],
                "last_active": user[5],
                "is_banned": bool(user[6]),
                "is_verified": bool(user[7]),
                "swaps_count": user[8],
                "successful_swaps": user[9],
                "failed_swaps": user[10]
            })
        
        return jsonify({
            "total_users": len(user_list),
            "users": user_list
        })
    except Exception as e:
        logger.error(f"Users API error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad request', 400

# ========== TELEGRAM COMMANDS ==========
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Check if banned
    if user_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    # Register user
    register_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    # Check channel membership
    if not check_channel_membership(user_id):
        welcome_text = f"""👋 *Welcome to Face Swap Bot!*

To use this bot, you must join our updates channel:

📢 Channel: {REQUIRED_CHANNEL}

*Steps:*
1. Click the button below to join the channel
2. Come back and click '✅ I Have Joined'
3. Start using the bot!

*Note:* The bot needs to verify your membership."""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"))
        markup.add(types.InlineKeyboardButton("✅ I Have Joined", callback_data="verify_join"))
        
        bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=markup)
    else:
        verify_user(user_id)
        show_main_menu(message)

def show_main_menu(message):
    welcome_text = """👋 *Welcome to Face Swap Bot!* 👋

I'm created by @PokiePy. I can swap faces between two photos!

*How to use:*
1. Send me the first photo (face to use as source)
2. Send me the second photo (face to replace)
3. I'll process and send you the result!

*Commands:*
/start - Show this message
/swap - Start a new face swap
/status - Check bot status
/mystats - Your statistics

*Note:* Send clear, front-facing photos for best results! 😊"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_callback(call):
    user_id = call.from_user.id
    
    if check_channel_membership(user_id):
        verify_user(user_id)
        bot.answer_callback_query(call.id, "✅ Verification successful! You can now use the bot.")
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Please join the channel first!", show_alert=True)

@bot.message_handler(commands=['swap'])
def start_swap(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if user_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    # Check if user is verified
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT verified FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or result[0] == 0:
        if not check_channel_membership(user_id):
            bot.reply_to(message, f"❌ Please join {REQUIRED_CHANNEL} first to use the bot!")
            return
    
    user_data[chat_id] = {'state': WAITING_FOR_SOURCE}
    bot.reply_to(message, "📸 *Step 1:* Send me the first photo (the face you want to use).\n\nMake sure it's a clear front-facing photo!")

@bot.message_handler(commands=['status'])
def bot_status(message):
    active_sessions = len([uid for uid, data in user_data.items() if data.get('state')])
    total_users = get_total_users()
    active_users = get_active_users_count(1)
    
    status_text = f"""🤖 *Bot Status*

*Active Sessions:* {active_sessions}
*Total Users:* {total_users}
*Active Users (24h):* {active_users}
*Face Swap API:* ✅ Connected

*Your Status:* {'Processing...' if message.chat.id in user_data and user_data[message.chat.id].get('state') is None else 'Ready'}
*Step:* {get_user_step(message.chat.id)}

Type /swap to start a new face swap!"""
    
    bot.reply_to(message, status_text, parse_mode='Markdown')

@bot.message_handler(commands=['mystats'])
def my_stats(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT swaps_count, successful_swaps, failed_swaps, join_date
        FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        swaps_count, successful, failed, join_date = result
        success_rate = (successful / max(1, swaps_count)) * 100
        
        stats_text = f"""📊 *Your Statistics*

*Total Swaps:* {swaps_count}
*Successful:* {successful}
*Failed:* {failed}
*Success Rate:* {success_rate:.1f}%
*Joined:* {join_date[:10]}

*Channel Status:* {'✅ Verified' if check_channel_membership(user_id) else '❌ Not Joined'}
*Bot Status:* {'✅ Active' if user_id not in BANNED_USERS else '🚫 Banned'}"""
    else:
        stats_text = "📊 No statistics available yet."
    
    bot.reply_to(message, stats_text, parse_mode='Markdown')

def get_user_step(chat_id):
    if chat_id not in user_data:
        return "Not started"
    state = user_data[chat_id].get('state')
    if state == WAITING_FOR_SOURCE:
        return "Waiting for first photo"
    elif state == WAITING_FOR_TARGET:
        return "Waiting for second photo"
    elif state is None and 'source' in user_data[chat_id] and 'target' in user_data[chat_id]:
        return "Processing face swap"
    else:
        return "Ready"

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['users'])
def list_users(message):
    """Admin command: List all users with inline buttons"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    users = get_all_users()
    
    if not users:
        bot.reply_to(message, "📭 No users registered yet.")
        return
    
    # Create pagination
    page = 0
    try:
        page = int(message.text.split()[1]) if len(message.text.split()) > 1 else 0
    except:
        page = 0
    
    users_per_page = 5
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    page_users = users[start_idx:end_idx]
    
    message_text = f"👥 *Registered Users: {len(users)}*\n━━━━━━━━━━━━━━━━━━\n"
    message_text += f"*Page {page+1}/{(len(users)-1)//users_per_page + 1}*\n\n"
    
    for user in page_users:
        user_id, username, first_name, last_name, join_date, last_active, is_banned, verified, swaps_count, successful, failed = user
        
        status = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
        verified_status = "✅" if verified else "❌"
        
        # Calculate activity
        if last_active:
            try:
                if isinstance(last_active, str):
                    last_active_time = datetime.strptime(last_active, '%Y-%m-%d %H:%M:%S')
                else:
                    last_active_time = last_active
                days_ago = (datetime.now() - last_active_time).days
                activity = f"{days_ago}d ago" if days_ago > 0 else "Today"
            except:
                activity = "Unknown"
        else:
            activity = "Never"
        
        message_text += f"🆔 `{user_id}`\n"
        message_text += f"👤 @{username or 'N/A'} {verified_status}\n"
        message_text += f"📛 {first_name} {last_name or ''}\n"
        message_text += f"📅 Joined: {join_date[:10] if join_date else 'Unknown'}\n"
        message_text += f"🕐 Last: {activity}\n"
        message_text += f"🔄 Swaps: {swaps_count} ({successful}✓/{failed}✗)\n"
        message_text += f"📊 Status: {status}\n"
        message_text += "━━━━━━━━━━━━━━━━━━\n\n"
    
    # Create inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    # Add action buttons for each user on this page
    for user in page_users:
        user_id = user[0]
        username = user[1] or f"ID:{user_id}"
        is_banned = bool(user[6])
        
        if is_banned:
            markup.add(types.InlineKeyboardButton(
                f"🟢 Unban {username[:15]}",
                callback_data=f"admin_unban_{user_id}"
            ))
        else:
            markup.add(types.InlineKeyboardButton(
                f"🔴 Ban {username[:15]}",
                callback_data=f"admin_ban_{user_id}"
            ))
    
    # Add pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
    
    if end_idx < len(users):
        nav_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    # Add refresh button
    markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh_users"))
    
    if len(message_text) > 4000:
        # Split message if too long
        chunks = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
        for chunk in chunks[:-1]:
            bot.send_message(ADMIN_ID, chunk, parse_mode='Markdown')
        bot.send_message(ADMIN_ID, chunks[-1], parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, message_text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('users_page_'))
def users_page_callback(call):
    """Handle pagination for users list"""
    page = int(call.data.split('_')[2])
    users = get_all_users()
    
    users_per_page = 5
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    page_users = users[start_idx:end_idx]
    
    message_text = f"👥 *Registered Users: {len(users)}*\n━━━━━━━━━━━━━━━━━━\n"
    message_text += f"*Page {page+1}/{(len(users)-1)//users_per_page + 1}*\n\n"
    
    for user in page_users:
        user_id, username, first_name, last_name, join_date, last_active, is_banned, verified, swaps_count, successful, failed = user
        
        status = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
        verified_status = "✅" if verified else "❌"
        
        if last_active:
            try:
                if isinstance(last_active, str):
                    last_active_time = datetime.strptime(last_active, '%Y-%m-%d %H:%M:%S')
                else:
                    last_active_time = last_active
                days_ago = (datetime.now() - last_active_time).days
                activity = f"{days_ago}d ago" if days_ago > 0 else "Today"
            except:
                activity = "Unknown"
        else:
            activity = "Never"
        
        message_text += f"🆔 `{user_id}`\n"
        message_text += f"👤 @{username or 'N/A'} {verified_status}\n"
        message_text += f"📛 {first_name} {last_name or ''}\n"
        message_text += f"📅 Joined: {join_date[:10] if join_date else 'Unknown'}\n"
        message_text += f"🕐 Last: {activity}\n"
        message_text += f"🔄 Swaps: {swaps_count} ({successful}✓/{failed}✗)\n"
        message_text += f"📊 Status: {status}\n"
        message_text += "━━━━━━━━━━━━━━━━━━\n\n"
    
    # Update inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    for user in page_users:
        user_id = user[0]
        username = user[1] or f"ID:{user_id}"
        is_banned = bool(user[6])
        
        if is_banned:
            markup.add(types.InlineKeyboardButton(
                f"🟢 Unban {username[:15]}",
                callback_data=f"admin_unban_{user_id}"
            ))
        else:
            markup.add(types.InlineKeyboardButton(
                f"🔴 Ban {username[:15]}",
                callback_data=f"admin_ban_{user_id}"
            ))
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
    
    if end_idx < len(users):
        nav_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh_users"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=message_text,
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_ban_'))
def admin_ban_callback(call):
    """Handle ban button click"""
    user_id = int(call.data.split('_')[2])
    
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin only!", show_alert=True)
        return
    
    ban_user(user_id)
    bot.answer_callback_query(call.id, f"✅ User {user_id} banned!")
    
    # Update the message
    users_page_callback(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_unban_'))
def admin_unban_callback(call):
    """Handle unban button click"""
    user_id = int(call.data.split('_')[2])
    
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin only!", show_alert=True)
        return
    
    unban_user(user_id)
    bot.answer_callback_query(call.id, f"✅ User {user_id} unbanned!")
    
    # Update the message
    users_page_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == "refresh_users")
def refresh_users_callback(call):
    """Refresh users list"""
    list_users(call.message)
    bot.answer_callback_query(call.id, "✅ Refreshed!")

@bot.message_handler(commands=['ban'])
def ban_user_command(message):
    """Admin command: Ban a user"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    try:
        user_id = int(message.text.split()[1])
        ban_user(user_id)
        bot.reply_to(message, f"✅ User `{user_id}` has been banned.")
        
        # Notify the banned user
        try:
            bot.send_message(user_id, "🚫 You have been banned from using this bot.")
        except:
            pass
            
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Usage: /ban <user_id>")

@bot.message_handler(commands=['unban'])
def unban_user_command(message):
    """Admin command: Unban a user"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    try:
        user_id = int(message.text.split()[1])
        unban_user(user_id)
        bot.reply_to(message, f"✅ User `{user_id}` has been unbanned.")
        
        # Notify the unbanned user
        try:
            bot.send_message(user_id, "✅ Your ban has been lifted. You can use the bot again.")
        except:
            pass
            
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Usage: /unban <user_id>")

@bot.message_handler(commands=['botstatus'])
def bot_status_admin(message):
    """Admin command: Show detailed bot status"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    try:
        # Get database statistics
        conn = sqlite3.connect('face_swap_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM swaps_history')
        total_swaps = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM swaps_history WHERE status = "success"')
        successful_swaps = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM swaps_history WHERE status = "failed"')
        failed_swaps = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE verified = 1')
        verified_users = cursor.fetchone()[0]
        
        conn.close()
        
        success_rate = (successful_swaps / max(1, total_swaps)) * 100
        
        status_message = f"""🤖 *ADMIN BOT STATUS REPORT*

━━━━━━━━━━━━━━━━━━
📊 *User Statistics:*
• Total Users: {get_total_users()}
• Active Users (24h): {get_active_users_count(1)}
• Verified Users: {verified_users}
• Banned Users: {len(BANNED_USERS)}

🔄 *Swap Statistics:*
• Total Swaps: {total_swaps}
• Successful: {successful_swaps}
• Failed: {failed_swaps}
• Success Rate: {success_rate:.1f}%

📱 *Current Sessions:*
• Active Face Swaps: {len([uid for uid, data in user_data.items() if data.get('state')])}
• Waiting for 1st Photo: {len([uid for uid, data in user_data.items() if data.get('state') == WAITING_FOR_SOURCE])}
• Waiting for 2nd Photo: {len([uid for uid, data in user_data.items() if data.get('state') == WAITING_FOR_TARGET])}

🔧 *System Status:*
• Bot: ✅ RUNNING
• Database: ✅ CONNECTED
• Face Swap API: ✅ AVAILABLE
• Channel Check: ✅ ACTIVE
• Webhook Mode: {'✅ ENABLED' if WEBHOOK_URL else '❌ DISABLED'}

🌐 *Endpoints:*
• Health: `/health` endpoint
• Stats: `/stats` endpoint
• Users API: `/users` endpoint

━━━━━━━━━━━━━━━━━━
*Admin Commands:*
/users - List all users with buttons
/ban <id> - Ban user
/unban <id> - Unban user
/botstatus - This report
/stats - Show statistics
/exportdata - Export user data
/refreshdb - Refresh database
/broadcast <msg> - Broadcast message
━━━━━━━━━━━━━━━━━━
"""
        
        bot.reply_to(message, status_message, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error generating status report: {str(e)}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Show bot statistics"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    # Get quick stats
    total_users = get_total_users()
    active_users = get_active_users_count(1)
    banned_users = len(BANNED_USERS)
    active_sessions = len([uid for uid, data in user_data.items() if data.get('state')])
    
    stats_text = f"""📈 *Quick Statistics*

*Users:*
• Total: {total_users}
• Active (24h): {active_users}
• Banned: {banned_users}

*Sessions:*
• Active: {active_sessions}

*Channel:*
• Required: {REQUIRED_CHANNEL}
• Verification: {'✅ Enabled'}

For detailed report, use /botstatus"""
    
    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['exportdata'])
def export_data(message):
    """Export user data as CSV"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    users = get_all_users()
    
    if not users:
        bot.reply_to(message, "📭 No user data to export.")
        return
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['User ID', 'Username', 'First Name', 'Last Name', 
                     'Join Date', 'Last Active', 'Banned', 'Verified',
                     'Total Swaps', 'Successful', 'Failed'])
    
    # Write data
    for user in users:
        writer.writerow(user[:11])  # First 11 columns
    
    # Get CSV data
    csv_data = output.getvalue()
    output.close()
    
    # Send as file
    bot.send_document(
        message.chat.id,
        ('users_export.csv', csv_data.encode('utf-8')),
        caption=f"📊 User data export ({len(users)} users)"
    )

@bot.message_handler(commands=['refreshdb'])
def refresh_database(message):
    """Refresh database"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    try:
        init_database()
        bot.reply_to(message, "✅ Database refreshed successfully!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error refreshing database: {str(e)}")

@bot.message_handler(commands=['refreshbot'])
def refresh_bot(message):
    """Refresh bot"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    # Clear user data
    user_data.clear()
    
    # Reload banned users
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE is_banned = 1')
    BANNED_USERS.clear()
    for row in cursor.fetchall():
        BANNED_USERS.add(row[0])
    conn.close()
    
    bot.reply_to(message, "✅ Bot refreshed! User data cleared and banned users reloaded.")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    """Broadcast message to all users"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    try:
        # Extract message text (remove /broadcast command)
        broadcast_text = message.text.replace('/broadcast', '', 1).strip()
        
        if not broadcast_text:
            bot.reply_to(message, "❌ Please provide a message to broadcast.\nUsage: /broadcast Your message here")
            return
        
        # Confirmation
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Yes, Send", callback_data=f"confirm_broadcast_{hash(broadcast_text)}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
        )
        
        bot.reply_to(
            message,
            f"📢 *Broadcast Confirmation*\n\n"
            f"*Message:*\n{broadcast_text}\n\n"
            f"*Recipients:* All users ({get_total_users()} users)\n\n"
            f"Are you sure you want to send this broadcast?",
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_broadcast_'))
def confirm_broadcast(call):
    """Send broadcast to all users"""
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin only!", show_alert=True)
        return
    
    broadcast_text = call.message.text.split("*Message:*\n")[1].split("\n\n*Recipients:*")[0]
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📢 *Sending Broadcast...*\n\nPlease wait, this may take a while.",
        parse_mode='Markdown'
    )
    
    users = get_all_users()
    sent_count = 0
    failed_count = 0
    
    for user in users:
        user_id = user[0]
        
        # Skip banned users
        if user_id in BANNED_USERS:
            continue
        
        try:
            bot.send_message(user_id, f"📢 *Announcement from Admin*\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send to {user_id}: {e}")
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ *Broadcast Completed!*\n\n"
             f"*Sent to:* {sent_count} users\n"
             f"*Failed:* {failed_count} users\n"
             f"*Total:* {len(users)} users",
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == "cancel_broadcast")
def cancel_broadcast(call):
    """Cancel broadcast"""
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin only!", show_alert=True)
        return
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="❌ Broadcast cancelled.",
        parse_mode='Markdown'
    )

# ========== FACE SWAP HANDLER ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Check if banned
        if user_id in BANNED_USERS:
            bot.reply_to(message, "🚫 You are banned from using this bot.")
            return
        
        # Get the photo (highest resolution)
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        
        # Download image
        img_data = requests.get(file_url).content
        
        if chat_id not in user_data:
            # Start new swap session
            user_data[chat_id] = {
                'state': WAITING_FOR_TARGET,
                'source': img_data,
                'start_time': time.time()
            }
            bot.reply_to(message, "✅ *Got your first photo!*\n\n📸 *Step 2:* Now send me the second photo (the face you want to replace).")
        else:
            if user_data[chat_id]['state'] == WAITING_FOR_TARGET:
                user_data[chat_id]['target'] = img_data
                user_data[chat_id]['state'] = None
                
                bot.reply_to(message, "🔄 *Processing face swap...*\n\nPlease wait while I swap the faces. This usually takes 10-30 seconds.")
                
                # Convert images to base64
                source_base64 = base64.b64encode(user_data[chat_id]['source']).decode('utf-8')
                target_base64 = base64.b64encode(user_data[chat_id]['target']).decode('utf-8')
                
                # Call face swap API
                api_url = "https://api.deepswapper.com/swap"
                data = {
                    'source': source_base64,
                    'target': target_base64,
                    'security': {
                        'token': FACE_SWAP_API_TOKEN,
                        'type': 'invisible',
                        'id': 'deepswapper'
                    }
                }
                
                headers = {'Content-Type': 'application/json'}
                response = requests.post(api_url, json=data, headers=headers)
                
                processing_time = time.time() - user_data[chat_id]['start_time']
                
                if response.status_code == 200:
                    response_data = response.json()
                    if 'result' in response_data:
                        image_data = base64.b64decode(response_data['result'])
                       
                        # Save to file (optional)
                        if not os.path.exists('results'):
                            os.makedirs('results')
                        
                        filename = f"result_{int(time.time())}.png"
                        filepath = os.path.join('results', filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(image_data)
                        
                        # Send result to user
                        with open(filepath, 'rb') as photo:
                            bot.send_photo(chat_id, photo, caption="✅ *Face swap completed!*\n\nType /swap to start another!")
                       
                        # Update user statistics
                        update_user_stats(user_id, success=True)
                        add_swap_history(user_id, "success", processing_time)
                        
                        logger.info(f"Face swap completed for {chat_id} in {processing_time:.2f}s")
                        
                        # Clean up user data
                        del user_data[chat_id]
                    else:
                        bot.reply_to(message, "❌ *Error:* No result from face swap API. Please try again.")
                        update_user_stats(user_id, success=False)
                        add_swap_history(user_id, "failed", processing_time)
                        if chat_id in user_data:
                            del user_data[chat_id]
                else:
                    bot.reply_to(message, f"❌ *Error:* Face swap API request failed (Status: {response.status_code}). Please try again.")
                    update_user_stats(user_id, success=False)
                    add_swap_history(user_id, "failed", processing_time)
                    if chat_id in user_data:
                        del user_data[chat_id]
                
            else:
                bot.reply_to(message, "⚠️ *Please complete the current swap first or type /swap to start over.*")
    
    except Exception as e:
        logger.error(f"Error processing photo: {str(e)}")
        bot.reply_to(message, f"❌ *An error occurred:* {str(e)}\n\nPlease try again with different photos.")
        if chat_id in user_data:
            del user_data[chat_id]

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    
    if chat_id in user_data:
        state = user_data[chat_id].get('state')
        if state == WAITING_FOR_SOURCE:
            bot.reply_to(message, "📸 Please send the first photo (the face to use).")
        elif state == WAITING_FOR_TARGET:
            bot.reply_to(message, "📸 Please send the second photo (the face to replace).")
        elif state is None and 'source' in user_data[chat_id] and 'target' in user_data[chat_id]:
            bot.reply_to(message, "⏳ Your face swap is being processed. Please wait...")
        else:
            bot.reply_to(message, "Type /swap to start a face swap!")
    else:
        bot.reply_to(message, "👋 Welcome! Type /start to see instructions or /swap to start a face swap!")

# ========== MAIN FUNCTION ==========
def run_bot():
    """Run the bot based on configuration"""
    if WEBHOOK_URL:
        # Use webhook mode
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info(f"Webhook set to: {WEBHOOK_URL}/webhook")
    else:
        # Use polling mode
        logger.info("Starting bot in polling mode...")
        bot.infinity_polling(timeout=30, long_polling_timeout=10)

def run_flask():
    """Run Flask app"""
    app.run(
        host='0.0.0.0',
        port=BOT_PORT,
        debug=False,
        use_reloader=False
    )

# ========== START BOT ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🤖 FACE SWAP BOT WITH ADMIN CONTROLS")
    print("=" * 60)
    print(f"📱 Bot Token: Loaded")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📢 Required Channel: {REQUIRED_CHANNEL}")
    print(f"🌐 Port: {BOT_PORT}")
    print(f"🏓 Health Check: http://localhost:{BOT_PORT}/health")
    print(f"📊 Stats: http://localhost:{BOT_PORT}/stats")
    print("=" * 60)
    print("🎯 Features:")
    print("• Face swapping between two photos")
    print("• Admin controls and user management")
    print("• Channel verification system")
    print("• User statistics and analytics")
    print("• Broadcast messaging")
    print("• Export user data")
    print("=" * 60)
    print("👑 Admin Commands:")
    print("/users - List all users with buttons")
    print("/ban <id> - Ban user")
    print("/unban <id> - Unban user")
    print("/botstatus - Detailed bot report")
    print("/stats - Quick statistics")
    print("/exportdata - Export user data as CSV")
    print("/refreshdb - Refresh database")
    print("/refreshbot - Refresh bot data")
    print("/broadcast <msg> - Broadcast to all users")
    print("=" * 60)
    print("👑 Created by: @PokiePy")
    print("💰 Credit change krne wale ki mkb")
    print("=" * 60)
    
    # Choose mode based on environment
    if WEBHOOK_URL:
        print(f"🌐 Using webhook mode")
        print(f"✅ Webhook URL: {WEBHOOK_URL}")
        
        # Start Flask in main thread
        print("🚀 Starting Flask server...")
        run_flask()
    else:
        print("📡 Using polling mode")
        
        # Start Flask in background thread
        flask_thread = threading.Thread(
            target=run_flask,
            daemon=True
        )
        flask_thread.start()
        
        # Wait for Flask to start
        time.sleep(3)
        
        # Start bot in main thread
        print("🚀 Starting Telegram bot...")
        try:
            run_bot()
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
        except Exception as e:
            logger.error(f"Bot error: {e}")
            print(f"❌ Bot error: {e}")
            sys.exit(1)
