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
import hashlib
import pickle
from cryptography.fernet import Fernet

# ========== CONFIGURATION ==========
BOT_TOKEN = "8522048948:AAGSCayCSZZF_6z2nHcGjVC7B64E3C9u6F8"
BOT_PORT = int(os.environ.get('PORT', 6001))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# ========== ADMIN CONFIG ==========
ADMIN_ID = 7575087826
BANNED_USERS = set()

# ========== CHANNEL VERIFICATION ==========
REQUIRED_CHANNEL = "@botupdates_2"

# ========== FACE SWAP CONFIG ==========
FACE_SWAP_API_TOKEN = "0.ufDEMbVMT7mc9_XLsFDSK5CQqdj9Cx_Zjww0DevIvXN5M4fXQr3B9YtPdGkKAHjXBK6UC9rFcEbZbzCfkxxgmdTYV8iPzTby0C03dTKv5V9uXFYfwIVlqwNbIsfOK_rLRHIPB31bQ0ijSTEd-lLbllf3MkEcpkEZFFmmq8HMAuRuliCXFEdCwEB1HoYSJtvJEmDIVsooU3gYdrCm5yOJ8_lZ4DiHCSvy7P8-YxwJKkapJNCMUCFIfJbWDkDzvh8DGPyTRoHbURX8kClfImmPrGcqlfd7kkoNRcudS25IbNf1CGBsh8V96MtEhnTZvOpZfnp5dpV7MfgwOgvx7hUazUaC_wxQE63Aa0uOPuGvJ70BNrmeZIIrY9roD1Koj316L4g2BZ_LLZZF11wcrNNon8UXB0iVudiNCJyDQCxLUmblXUpt4IUvRoiOqXBNtWtLqY0su0ieVB0jjyDf_-zs7wc8WQ_jqp-NsTxgKOgvZYWV6Elz_lf4cNxGHZJ5BdcyLEoRBH3cksvwoncmYOy5Ulco22QT-x2z06xVFBZYZMVulxAcmvQemKfSFKsNaDxwor35p-amn9Vevhyb-GzA_oIoaTmc0fVXSshax2rdFQHQms86fZ_jkTieRpyIuX0mI3C5jLGIiOXzWxNgax9eZeQstYjIh8BIdMiTIUHfyKVTgtoLbK0hjTUTP0xDlCLnOt5qHdwe_iTWedBsswAJWYdtIxw0YUfIU22GMYrJoekOrQErawNlU5yT-LhXquBQY3EBtEup4JMWLendSh68d6HqjN2T3sAfVw0nY5jg7_5LJwj5gqEk57devNN8GGhogJpfdGzYoNGja22IZIuDnPPmWTpGx4VcLOLknSHrzio.tXUN6eooS69z3QtBp-DY1g.d882822dfe05be2b36ed1950554e1bac753abfe304a289adc4289b3f0d517356"

# ========== ENCRYPTION CONFIG ==========
ENCRYPTION_KEY = Fernet.generate_key()
cipher = Fernet(ENCRYPTION_KEY)

# ========== NSFW DETECTION CONFIG ==========
NSFW_DETECTION_ENABLED = True

# ========== FLASK APP ==========
app = Flask(__name__)

# ========== TELEGRAM BOT ==========
if WEBHOOK_URL:
    bot = telebot.TeleBot(BOT_TOKEN)
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
else:
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
            failed_swaps INTEGER DEFAULT 0,
            reports_received INTEGER DEFAULT 0,
            favorites_count INTEGER DEFAULT 0,
            encryption_key BLOB
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
            source_image_hash TEXT,
            target_image_hash TEXT,
            result_image_hash TEXT,
            nsfw_check INTEGER DEFAULT 0,
            reported INTEGER DEFAULT 0,
            favorite INTEGER DEFAULT 0,
            encrypted INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reported_user_id INTEGER,
            swap_id INTEGER,
            reason TEXT,
            report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            admin_action TEXT,
            FOREIGN KEY (swap_id) REFERENCES swaps_history (id)
        )
    ''')
    
    # Favorites table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            swap_id INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (swap_id) REFERENCES swaps_history (id),
            UNIQUE(user_id, swap_id)
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
swap_progress = {}
WAITING_FOR_SOURCE = 1
WAITING_FOR_TARGET = 2
PROCESSING = 3

# ========== HELPER FUNCTIONS ==========
def generate_image_hash(image_data):
    """Generate hash for image data"""
    return hashlib.sha256(image_data).hexdigest()

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
    cursor.execute('''
        SELECT COUNT(*) FROM users 
        WHERE last_active >= datetime('now', '-? days')
    ''', (days,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def ban_user(user_id, reason="Violation of terms"):
    """Ban a user"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    BANNED_USERS.add(user_id)
    logger.info(f"User {user_id} banned: {reason}")

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
               swaps_count, successful_swaps, failed_swaps,
               reports_received, favorites_count
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

def add_swap_history(user_id, status, processing_time, source_hash, target_hash, result_hash, nsfw_check=0, reported=0):
    """Add swap to history"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO swaps_history 
        (user_id, status, processing_time, source_image_hash, target_image_hash, 
         result_image_hash, nsfw_check, reported)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, status, processing_time, source_hash, target_hash, 
          result_hash, nsfw_check, reported))
    
    swap_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return swap_id

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
        "version": "3.0",
        "creator": "@PokiePy",
        "admin_id": ADMIN_ID,
        "endpoints": {
            "/": "This page",
            "/health": "Health check",
            "/health/hunter": "Extended health check",
            "/stats": "Bot statistics",
            "/users": "User statistics"
        },
        "features": [
            "Face Swap", 
            "Admin Controls", 
            "Channel Verification", 
            "User Management",
            "Progress Tracking"
        ]
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "bot": "running",
        "database": "connected",
        "face_swap_api": "configured",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/health/hunter')
def health_check_hunter():
    """Extended health check endpoint"""
    try:
        conn = sqlite3.connect('face_swap_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM swaps_history')
        total_swaps = cursor.fetchone()[0]
        conn.close()
        
        bot_status = "running"
        try:
            bot.get_me()
        except:
            bot_status = "disconnected"
        
        return jsonify({
            "status": "healthy",
            "bot_status": bot_status,
            "database_status": "connected",
            "channel_verification": "active",
            "statistics": {
                "total_users": total_users,
                "active_users_24h": get_active_users_count(1),
                "total_swaps": total_swaps,
                "active_sessions": len(user_data),
                "banned_users": len(BANNED_USERS)
            },
            "system": {
                "uptime": time.time() - app_start_time,
                "swap_progress_tracking": "active"
            },
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/stats')
def stats_api():
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
        "swap_statistics": {
            "total_swaps": total_swaps,
            "successful_swaps": successful_swaps,
            "failed_swaps": failed_swaps,
            "success_rate": success_rate
        },
        "active_sessions": len([uid for uid, data in user_data.items() if data.get('state')]),
        "progress_tracking": len(swap_progress),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/users')
def users_api():
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
            "failed_swaps": user[10],
            "reports_received": user[11],
            "favorites_count": user[12]
        })
    
    return jsonify({
        "total_users": len(user_list),
        "users": user_list
    })

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
/cancel - Cancel ongoing swap

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
    bot.reply_to(message, "📸 *Step 1:* Send me the first photo (the face you want to use).\n\nMake sure it's a clear front-facing photo!\n\nYou can cancel anytime with /cancel")

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    chat_id = message.chat.id
    
    if chat_id in user_data:
        if chat_id in swap_progress:
            del swap_progress[chat_id]
        del user_data[chat_id]
        bot.reply_to(message, "❌ Swap cancelled successfully.")
    else:
        bot.reply_to(message, "⚠️ No active swap to cancel.")

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

*Your Status:* {get_user_step(message.chat.id)}

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
    
    # Get recent swaps - FIXED LINE (line 1204)
    cursor.execute('''
        SELECT status, processing_time 
        FROM swaps_history 
        WHERE user_id = ? 
        ORDER BY swap_date DESC 
        LIMIT 5
    ''', (user_id,))
    recent_swaps = cursor.fetchall()
    conn.close()
    
    if result:
        swaps_count, successful, failed, join_date = result
        success_rate = (successful / max(1, swaps_count)) * 100
        
        # Format recent swaps
        recent_swaps_text = ""
        if recent_swaps:
            for s in recent_swaps:
                recent_swaps_text += f"• {s[0]} ({s[1]:.1f}s)\n"
        else:
            recent_swaps_text = "No recent swaps"
        
        stats_text = f"""📊 *Your Statistics*

*Swaps:*
• Total: {swaps_count}
• Successful: {successful}
• Failed: {failed}
• Success Rate: {success_rate:.1f}%

*Account:*
• Joined: {join_date[:10]}
• Channel Status: {'✅ Verified' if check_channel_membership(user_id) else '❌ Not Joined'}
• Bot Status: {'✅ Active' if user_id not in BANNED_USERS else '🚫 Banned'}

*Recent Swaps:*
{recent_swaps_text}"""
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
    elif state == PROCESSING:
        return "Processing face swap"
    else:
        return "Ready"

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['users'])
def list_users(message):
    """Admin command: List all users"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    users = get_all_users()
    
    if not users:
        bot.reply_to(message, "📭 No users registered yet.")
        return
    
    message_text = f"👥 *Registered Users: {len(users)}*\n━━━━━━━━━━━━━━━━━━\n\n"
    
    for user in users:
        user_id, username, first_name, last_name, join_date, last_active, is_banned, verified, swaps_count, successful, failed, reports, favorites = user
        
        status = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
        
        if last_active:
            try:
                last_active_time = datetime.strptime(last_active, '%Y-%m-%d %H:%M:%S')
                days_ago = (datetime.now() - last_active_time).days
                activity = f"{days_ago}d ago" if days_ago > 0 else "Today"
            except:
                activity = "Unknown"
        else:
            activity = "Never"
        
        message_text += f"🆔 *ID:* `{user_id}`\n"
        message_text += f"👤 *User:* @{username or 'N/A'}\n"
        message_text += f"📛 *Name:* {first_name} {last_name or ''}\n"
        message_text += f"📅 *Joined:* {join_date}\n"
        message_text += f"🕐 *Last Active:* {activity}\n"
        message_text += f"🔄 *Swaps:* {swaps_count} ({successful}✓/{failed}✗)\n"
        message_text += f"📊 *Status:* {status}\n"
        message_text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    # Split message if too long
    if len(message_text) > 4000:
        chunks = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
        for chunk in chunks:
            bot.send_message(ADMIN_ID, chunk, parse_mode='Markdown')
    else:
        bot.send_message(ADMIN_ID, message_text, parse_mode='Markdown')

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
    
    success_rate = (successful_swaps / max(1, total_swaps)) * 100 if total_swaps > 0 else 0
    
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
• Active Swaps: {len([uid for uid, data in user_data.items() if data.get('state')])}
• Waiting for 1st Photo: {len([uid for uid, data in user_data.items() if data.get('state') == WAITING_FOR_SOURCE])}
• Waiting for 2nd Photo: {len([uid for uid, data in user_data.items() if data.get('state') == WAITING_FOR_TARGET])}

🔧 *System Status:*
• Bot: ✅ RUNNING
• Database: ✅ CONNECTED
• Face Swap API: ✅ AVAILABLE
• Channel Check: ✅ ACTIVE
• Webhook Mode: {'✅ ENABLED' if WEBHOOK_URL else '❌ DISABLED'}

━━━━━━━━━━━━━━━━━━
*Admin Commands:*
/users - List all users
/ban <id> - Ban user
/unban <id> - Unban user
/botstatus - This report
━━━━━━━━━━━━━━━━━━
"""
    
    bot.reply_to(message, status_message, parse_mode='Markdown')

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

@bot.message_handler(commands=['refreshbot'])
def refresh_bot(message):
    """Refresh bot"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    # Clear user data
    user_data.clear()
    swap_progress.clear()
    
    # Reload banned users
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE is_banned = 1')
    BANNED_USERS.clear()
    for row in cursor.fetchall():
        BANNED_USERS.add(row[0])
    conn.close()
    
    bot.reply_to(message, "✅ Bot refreshed! User data cleared and banned users reloaded.")

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
                'start_time': time.time(),
                'user_id': user_id
            }
            bot.reply_to(message, "✅ *Got your first photo!*\n\n📸 *Step 2:* Now send me the second photo (the face you want to replace).\n\nYou can cancel anytime with /cancel")
        else:
            if user_data[chat_id]['state'] == WAITING_FOR_TARGET:
                user_data[chat_id]['target'] = img_data
                user_data[chat_id]['state'] = PROCESSING
                
                # Initialize progress tracking
                swap_progress[chat_id] = {
                    'progress': 10,
                    'message': "Starting face swap...",
                    'start_time': time.time()
                }
                
                # Send processing message
                processing_msg = bot.send_message(chat_id, "🔄 *Processing face swap...*")
                swap_progress[chat_id]['message_id'] = processing_msg.message_id
                
                # Process the face swap
                process_face_swap_sync(chat_id)
    
    except Exception as e:
        logger.error(f"Error processing photo: {str(e)}")
        bot.reply_to(message, f"❌ *An error occurred:* {str(e)}\n\nPlease try again with different photos.")
        if chat_id in user_data:
            del user_data[chat_id]
        if chat_id in swap_progress:
            try:
                bot.delete_message(chat_id, swap_progress[chat_id].get('message_id'))
            except:
                pass
            del swap_progress[chat_id]

def process_face_swap_sync(chat_id):
    """Process face swap synchronously"""
    try:
        if chat_id not in user_data:
            return
        
        user_id = user_data[chat_id]['user_id']
        source_img = user_data[chat_id]['source']
        target_img = user_data[chat_id]['target']
        start_time = user_data[chat_id]['start_time']
        
        # Update progress
        if chat_id in swap_progress:
            swap_progress[chat_id]['progress'] = 30
            swap_progress[chat_id]['message'] = "Processing faces..."
            try:
                bot.edit_message_text(
                    f"🔄 *Processing: 30%*\n█░░░░░░░░░\nProcessing faces...",
                    chat_id=chat_id,
                    message_id=swap_progress[chat_id]['message_id'],
                    parse_mode='Markdown'
                )
            except:
                pass
        
        # Generate image hashes
        source_hash = generate_image_hash(source_img)
        target_hash = generate_image_hash(target_img)
        
        # Update progress
        if chat_id in swap_progress:
            swap_progress[chat_id]['progress'] = 50
            swap_progress[chat_id]['message'] = "Preparing images..."
            try:
                bot.edit_message_text(
                    f"🔄 *Processing: 50%*\n███░░░░░░░\nPreparing images...",
                    chat_id=chat_id,
                    message_id=swap_progress[chat_id]['message_id'],
                    parse_mode='Markdown'
                )
            except:
                pass
        
        # Convert images to base64
        source_base64 = base64.b64encode(source_img).decode('utf-8')
        target_base64 = base64.b64encode(target_img).decode('utf-8')
        
        # Update progress
        if chat_id in swap_progress:
            swap_progress[chat_id]['progress'] = 70
            swap_progress[chat_id]['message'] = "Swapping faces with AI..."
            try:
                bot.edit_message_text(
                    f"🔄 *Processing: 70%*\n█████░░░░░\nSwapping faces with AI...",
                    chat_id=chat_id,
                    message_id=swap_progress[chat_id]['message_id'],
                    parse_mode='Markdown'
                )
            except:
                pass
        
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
        
        processing_time = time.time() - start_time
        
        # Update progress
        if chat_id in swap_progress:
            swap_progress[chat_id]['progress'] = 90
            swap_progress[chat_id]['message'] = "Finalizing..."
            try:
                bot.edit_message_text(
                    f"🔄 *Processing: 90%*\n████████░░\nFinalizing...",
                    chat_id=chat_id,
                    message_id=swap_progress[chat_id]['message_id'],
                    parse_mode='Markdown'
                )
            except:
                pass
        
        if response.status_code == 200:
            response_data = response.json()
            if 'result' in response_data:
                image_data = base64.b64decode(response_data['result'])
                result_hash = generate_image_hash(image_data)
               
                # Save to file (optional)
                if not os.path.exists('results'):
                    os.makedirs('results')
                
                filename = f"result_{int(time.time())}.png"
                filepath = os.path.join('results', filename)
                
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                
                # Update progress to complete
                if chat_id in swap_progress:
                    try:
                        bot.delete_message(chat_id, swap_progress[chat_id]['message_id'])
                    except:
                        pass
                
                # Add to history
                swap_id = add_swap_history(
                    user_id, "success", processing_time, 
                    source_hash, target_hash, result_hash
                )
                
                # Update user statistics
                update_user_stats(user_id, success=True)
                
                # Send result to user
                with open(filepath, 'rb') as photo:
                    bot.send_photo(
                        chat_id, 
                        photo, 
                        caption=f"✅ *Face swap completed!*\n\nTime: {processing_time:.1f}s\n\nType /swap to make another!",
                        parse_mode='Markdown'
                    )
                
                logger.info(f"Face swap completed for {chat_id} in {processing_time:.2f}s")
                
            else:
                # Clean up progress message
                if chat_id in swap_progress:
                    try:
                        bot.delete_message(chat_id, swap_progress[chat_id]['message_id'])
                    except:
                        pass
                
                bot.send_message(chat_id, "❌ *Error:* No result from face swap API. Please try again.")
                
                # Add to history as failed
                add_swap_history(user_id, "failed", processing_time, source_hash, target_hash, "")
                update_user_stats(user_id, success=False)
        else:
            # Clean up progress message
            if chat_id in swap_progress:
                try:
                    bot.delete_message(chat_id, swap_progress[chat_id]['message_id'])
                except:
                    pass
            
            bot.send_message(chat_id, f"❌ *Error:* Face swap API request failed (Status: {response.status_code}). Please try again.")
            
            # Add to history as failed
            add_swap_history(user_id, "failed", processing_time, source_hash, target_hash, "")
            update_user_stats(user_id, success=False)
                
    except Exception as e:
        logger.error(f"Face swap processing error: {e}")
        
        if chat_id in swap_progress:
            try:
                bot.delete_message(chat_id, swap_progress[chat_id]['message_id'])
            except:
                pass
        
        bot.send_message(chat_id, f"❌ *An error occurred during processing:* {str(e)}\n\nPlease try again.")
        
        if chat_id in user_data:
            if 'user_id' in user_data[chat_id]:
                user_id = user_data[chat_id]['user_id']
                update_user_stats(user_id, success=False)
    
    # Clean up
    if chat_id in user_data:
        del user_data[chat_id]
    if chat_id in swap_progress:
        del swap_progress[chat_id]

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    
    if chat_id in user_data:
        state = user_data[chat_id].get('state')
        if state == WAITING_FOR_SOURCE:
            bot.reply_to(message, "📸 Please send the first photo (the face to use).")
        elif state == WAITING_FOR_TARGET:
            bot.reply_to(message, "📸 Please send the second photo (the face to replace).")
        elif state == PROCESSING:
            bot.reply_to(message, "⏳ Your face swap is being processed. Please wait...")
        else:
            bot.reply_to(message, "Type /swap to start a face swap!")
    else:
        bot.reply_to(message, "👋 Welcome! Type /start to see instructions or /swap to start a face swap!")

# ========== START BOT ==========
app_start_time = time.time()

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 FACE SWAP BOT")
    print("=" * 70)
    print(f"📱 Bot Token: Loaded")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📢 Required Channel: {REQUIRED_CHANNEL}")
    print(f"🌐 Port: {BOT_PORT}")
    print(f"🏓 Health Check: http://localhost:{BOT_PORT}/health")
    print(f"🏓 Health (Extended): http://localhost:{BOT_PORT}/health/hunter")
    print(f"📊 Stats: http://localhost:{BOT_PORT}/stats")
    print("=" * 70)
    print("🎯 Features:")
    print("✅ Face swapping between two photos")
    print("✅ Admin controls and user management")
    print("✅ Channel verification system")
    print("✅ Progress tracking with visual bar")
    print("✅ Cancel swap option (/cancel)")
    print("=" * 70)
    print("👑 Admin Commands:")
    print("/users - List all users")
    print("/ban <id> - Ban user")
    print("/unban <id> - Unban user")
    print("/botstatus - Detailed bot report")
    print("/stats - Quick statistics")
    print("/refreshbot - Refresh bot data")
    print("=" * 70)
    print("👤 User Commands:")
    print("/swap - Start new face swap")
    print("/cancel - Cancel ongoing swap")
    print("/mystats - Your statistics")
    print("/status - Check bot status")
    print("=" * 70)
    print("👑 Created by: @PokiePy")
    print("=" * 70)
    
    # Start Flask in background
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host='0.0.0.0',
            port=BOT_PORT,
            debug=False,
            use_reloader=False
        ),
        daemon=True
    )
    flask_thread.start()
    
    # Wait for Flask to start
    time.sleep(2)
    
    # Start bot
    if WEBHOOK_URL:
        print(f"🌐 Using webhook: {WEBHOOK_URL}")
        print(f"✅ Webhook set successfully!")
    else:
        print("📡 Using polling mode")
        bot_thread = threading.Thread(target=lambda: bot.polling(non_stop=True), daemon=True)
        bot_thread.start()
        print("✅ Bot polling started!")
    
    print("🎯 Bot is ready! Use /start in Telegram to begin.")
    print(f"🌐 API available at: http://localhost:{BOT_PORT}")
    print("=" * 70)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped.")
