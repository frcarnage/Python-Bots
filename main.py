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
BOT_USERNAME = "CarnageSwapperBot"  # Change to your bot's username

# ======= CHANNEL CONFIGURATION =======
UPDATES_CHANNEL = "@CarnageUpdates"  # Your updates channel
PROOFS_CHANNEL = "@CarnageProofs"    # Your proofs channel
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

# ======= REQUIRED CHANNEL SETUP =======
# 1. Create these two channels on Telegram
# 2. Add your bot as ADMIN to both channels
# 3. Make sure bot has permission to check members
# 4. Update the @channel usernames above

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
        # Try to get chat member - bot must be admin in channel
        chat_member = bot.get_chat_member(channel_username, user_id)
        # Check if user is member, administrator, creator, or restricted
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

# ==================== DATABASE FUNCTIONS ====================
def add_user(user_id, username, first_name, last_name, referral_code="direct"):
    """Add new user to database with referral support"""
    # Check if user already exists
    existing_user = execute_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing_user:
        return
    
    user_referral_code = generate_referral_code(user_id)
    execute_query('''
        INSERT INTO users (user_id, username, first_name, last_name, join_date, last_active, referral_code, join_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          user_referral_code, 'direct'), commit=True)
    
    # Process referral if any
    if referral_code and referral_code != "direct":
        process_referral(user_id, referral_code)
    
    # Award early adopter achievement for first 100 users
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
    result = execute_one("SELECT approved, approved_until, is_banned FROM users WHERE user_id = ?", (user_id,))
    
    if result:
        approved = result[0]
        is_banned = result[2]
        
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

def ban_user(user_id, reason="No reason provided"):
    """Ban a user"""
    execute_query("UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?", 
                  (reason, user_id), commit=True)

def get_all_users():
    """Get all users"""
    return execute_query("SELECT user_id, username, first_name, approved, approved_until, is_banned, total_referrals FROM users")

def get_total_users():
    """Get total user count"""
    result = execute_one("SELECT COUNT(*) FROM users")
    return result[0] if result else 0

def get_active_users_count():
    """Get count of users active in last 24 hours"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    result = execute_one("SELECT COUNT(*) FROM users WHERE last_active > ?", (yesterday,))
    return result[0] if result else 0

def log_swap(user_id, target_username, status, error_message=None):
    """Log swap attempt to history"""
    execute_query('''
        INSERT INTO swap_history (user_id, target_username, status, swap_time, error_message)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, target_username, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), error_message), commit=True)
    
    # Update user stats
    execute_query("UPDATE users SET total_swaps = total_swaps + 1 WHERE user_id = ?", (user_id,), commit=True)
    if status == "success":
        execute_query("UPDATE users SET successful_swaps = successful_swaps + 1 WHERE user_id = ?", (user_id,), commit=True)
    
    # Award first swap achievement
    if status == "success":
        result = execute_one("SELECT COUNT(*) FROM swap_history WHERE user_id = ? AND status = 'success'", (user_id,))
        success_count = result[0] if result else 0
        if success_count == 1:
            award_achievement(user_id, "first_swap")
        if success_count >= 10:
            award_achievement(user_id, "swap_pro")
        
        # Send to proofs channel
        send_swap_proof(user_id, target_username, "success")
    elif status == "failed":
        # Send failed swap to proofs channel
        send_swap_proof(user_id, target_username, "failed", error_message)

def send_swap_proof(user_id, target_username, status, error_message=None):
    """Send swap proof to proofs channel"""
    user_info = execute_one("SELECT username, first_name FROM users WHERE user_id = ?", (user_id,))
    username = f"@{user_info[0]}" if user_info and user_info[0] else f"User {user_id}"
    first_name = user_info[1] if user_info and user_info[1] else "User"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if status == "success":
        proof_message = f"""
✅ *SUCCESSFUL SWAP PROOF*

👤 *User:* {first_name} ({username})
🎯 *Target Username:* `{target_username}`
🕒 *Time:* {current_time}
🏆 *Status:* Successfully Swapped!

⚡ *Bot:* CARNAGE Swapper v3.0
🔗 *Proof ID:* CARNAGE-{random.randint(10000, 99999)}
"""
    else:
        proof_message = f"""
❌ *FAILED SWAP ATTEMPT*

👤 *User:* {first_name} ({username})
🎯 *Target Username:* `{target_username}`
🕒 *Time:* {current_time}
⚠️ *Status:* Failed
📝 *Error:* {error_message or 'Unknown error'}

⚡ *Bot:* CARNAGE Swapper v3.0
"""
    
    try:
        send_to_proofs_channel(proof_message)
    except Exception as e:
        print(f"Failed to send proof to channel: {e}")

def get_total_swaps():
    """Get total swaps across all users"""
    result = execute_one("SELECT SUM(total_swaps) FROM users")
    return result[0] if result and result[0] else 0

def get_user_detailed_stats(user_id):
    """Get detailed user statistics for dashboard"""
    # Get basic user info
    user_data = execute_one('''
        SELECT username, total_swaps, successful_swaps, total_referrals, free_swaps_earned
        FROM users WHERE user_id = ?
    ''', (user_id,))
    
    if not user_data:
        return None
    
    username, total_swaps, successful_swaps, total_referrals, free_swaps = user_data
    
    # Calculate success rate
    success_rate = (successful_swaps / total_swaps * 100) if total_swaps > 0 else 0
    
    # Get recent swaps
    recent_swaps = execute_query('''
        SELECT target_username, status, swap_time 
        FROM swap_history 
        WHERE user_id = ? 
        ORDER BY swap_time DESC 
        LIMIT 5
    ''', (user_id,))
    
    # Get achievements
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
    
    # Find referrer by code
    result = execute_one("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
    
    if result:
        referrer_id = result[0]
        
        # Update referred user
        execute_query("UPDATE users SET referred_by = ?, join_method = 'referral' WHERE user_id = ?", 
                     (referrer_id, user_id), commit=True)
        
        # Update referrer stats
        execute_query('''
            UPDATE users 
            SET total_referrals = total_referrals + 1,
                free_swaps_earned = free_swaps_earned + 2
            WHERE user_id = ?
        ''', (referrer_id,), commit=True)
        
        # Award free swaps to new user (no approval needed)
        execute_query("UPDATE users SET approved = 1, approved_until = '9999-12-31 23:59:59' WHERE user_id = ?", 
                     (user_id,), commit=True)
        
        # Notify referrer
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
        
        # Award achievements
        award_achievement(referrer_id, "referral_master")
        
        # Check if reached 5 referrals for special achievement
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
    "swap_streak_3": {"name": "3-Day Streak", "emoji": "🔥", "description": "Swap for 3 consecutive days"},
    "referral_master": {"name": "Referral Master", "emoji": "🤝", "description": "Refer 5 friends"},
    "swap_pro": {"name": "Swap Pro", "emoji": "⚡", "description": "Complete 10 successful swaps"},
    "early_adopter": {"name": "Early Adopter", "emoji": "🚀", "description": "Join first 100 users"},
    "founder": {"name": "Founder", "emoji": "👑", "description": "Bot creator"},
    "first_user": {"name": "Pioneer", "emoji": "🧭", "description": "First 50 users"},
    "tutorial_complete": {"name": "Quick Learner", "emoji": "🎓", "description": "Complete interactive tutorial"},
    "dashboard_user": {"name": "Dashboard Pro", "emoji": "📊", "description": "Visit web dashboard"},
    "channel_member": {"name": "Official Member", "emoji": "📢", "description": "Join both official channels"},
}

def award_achievement(user_id, achievement_id):
    """Award an achievement to user"""
    # Check if already awarded
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
        
        # Notify user
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
                    is_admin INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER DEFAULT NULL,
                    total_referrals INTEGER DEFAULT 0,
                    free_swaps_earned INTEGER DEFAULT 0,
                    total_swaps INTEGER DEFAULT 0,
                    successful_swaps INTEGER DEFAULT 0,
                    join_method TEXT DEFAULT 'direct',
                    channels_joined INTEGER DEFAULT 0
                )
            ''')
            
            # Achievements table
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
            
            # Swap history table
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
            
            # Check if admin exists
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
        # Try to continue anyway

def mark_channels_joined(user_id):
    """Mark user as having joined all channels"""
    execute_query("UPDATE users SET channels_joined = 1 WHERE user_id = ?", (user_id,), commit=True)

def has_user_joined_channels(user_id):
    """Check if user has joined channels in database"""
    result = execute_one("SELECT channels_joined FROM users WHERE user_id = ?", (user_id,))
    return result and result[0] == 1

# ==================== TUTORIAL SYSTEM ====================
TUTORIAL_STEPS = [
    {
        "title": "🎯 Welcome to CARNAGE Tutorial!",
        "message": "I'll guide you through using the bot step by step.\n\n*Ready to become a swap master?*",
        "buttons": ["Let's Go! 🚀", "Skip Tutorial"]
    },
    {
        "title": "📱 Step 1: Get Instagram Session",
        "message": "You need an Instagram *session ID* to swap.\n\n*How to get it:*\n1. Login to Instagram\n2. Use browser DevTools (F12)\n3. Copy 'sessionid' cookie\n\n*Need help?* Google 'get Instagram sessionid'",
        "buttons": ["Got it! ✅", "Show Example"]
    },
    {
        "title": "🤖 Step 2: Add Main Session",
        "message": "Now add your session to the bot:\n\n1. Click *'Main Session'* in menu\n2. Paste your session ID\n3. Bot will validate it\n\n*Tip:* This is the account that will GET the new username",
        "buttons": ["Try Now", "Back"]
    },
    {
        "title": "🎯 Step 3: Add Target Session",
        "message": "Add the target account session:\n\n1. Click *'Target Session'*\n2. Paste target session ID\n3. This account will LOSE its username\n\n*Note:* Both accounts must be logged in",
        "buttons": ["Got it", "Back"]
    },
    {
        "title": "⚡ Step 4: Run Your First Swap!",
        "message": "Time to swap usernames!\n\n1. Go to *'Swapper'* menu\n2. Click *'Run Main Swap'*\n3. Watch the magic happen! ✨\n\n*Bonus:* Each swap is logged in your history!",
        "buttons": ["Ready to Swap!", "Back"]
    },
    {
        "title": "🏆 Step 5: Earn Free Swaps!",
        "message": "Share your referral link to get *FREE swaps*!\n\n*How it works:*\n1. Use /refer command\n2. Share your link\n3. Get 2 FREE swaps per referral!\n\n*No approval needed for referrals!*",
        "buttons": ["Show My Link", "Back"]
    },
    {
        "title": "🎓 Tutorial Complete!",
        "message": "You're now a CARNAGE Pro! 🎉\n\n*Quick Commands:*\n/start - Main menu\n/dashboard - Web dashboard\n/stats - Your statistics\n/refer - Get referral link\n/tutorial - Repeat tutorial\n\n*Happy Swapping!* 🔄",
        "buttons": ["Start Swapping!", "View Dashboard"]
    }
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
    
    # Store current step
    tutorial_sessions[chat_id] = step_index

def handle_tutorial_response(chat_id, text):
    """Handle tutorial button clicks"""
    if chat_id not in tutorial_sessions:
        return False
    
    current_step = tutorial_sessions[chat_id]
    
    if text == "Back":
        if current_step > 0:
            show_tutorial_step(chat_id, current_step - 1)
        return True
    
    elif text == "Skip Tutorial":
        del tutorial_sessions[chat_id]
        bot.send_message(chat_id, "Tutorial skipped! Use /tutorial anytime to restart.", 
                        reply_markup=create_reply_menu(["Main Menu"]))
        return True
    
    elif "Let's Go" in text or "Got it" in text or "Ready" in text or "Try Now" in text:
        show_tutorial_step(chat_id, current_step + 1)
        if current_step + 1 >= len(TUTORIAL_STEPS):
            award_achievement(chat_id, "tutorial_complete")
            del tutorial_sessions[chat_id]
        return True
    
    elif text == "Show Example":
        bot.send_message(
            chat_id,
            "*Session ID Example:*\n\n"
            "`1234567890%3Aabc123%3Axyz456`\n\n"
            "It usually looks like random letters/numbers with % symbols.",
            parse_mode="Markdown"
        )
        return True
    
    elif text == "Show My Link":
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref-{chat_id}"
        bot.send_message(
            chat_id,
            f"*Your Referral Link:*\n\n{referral_link}\n\n"
            f"Share this link to get 2 FREE swaps per friend who joins! 🆓",
            parse_mode="Markdown"
        )
        return True
    
    elif text == "View Dashboard":
        dashboard_url = f"https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/{chat_id}"
        bot.send_message(
            chat_id,
            f"*Your Dashboard:*\n\n{dashboard_url}\n\n"
            f"Visit to see your stats, achievements, and referrals! 📊",
            parse_mode="Markdown"
        )
        award_achievement(chat_id, "dashboard_user")
        return True
    
    elif text == "Start Swapping!":
        del tutorial_sessions[chat_id]
        show_main_menu(chat_id)
        return True
    
    return False

# ==================== MENU FUNCTIONS ====================
def show_main_menu(chat_id):
    if not is_user_approved(chat_id):
        return
    
    buttons = [
        "📱 Main Session", "🎯 Target Session",
        "🔄 Swapper", "⚙️ Settings",
        "📊 Dashboard", "🎁 Referral",
        "🏆 Achievements", "📈 Stats"
    ]
    markup = create_reply_menu(buttons, row_width=2, add_back=False)
    bot.send_message(chat_id, "🤖 *CARNAGE Swapper - Main Menu*", parse_mode='HTML', reply_markup=markup)

def show_swapper_menu(chat_id):
    if not is_user_approved(chat_id):
        return
    
    buttons = ["Run Main Swap", "BackUp Mode", "Threads Swap", "Back"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b>🔄 CARNAGE Swapper - Select Option</b>", parse_mode='HTML', reply_markup=markup)

def show_settings_menu(chat_id):
    if not is_user_approved(chat_id):
        return
    
    buttons = ["Bio", "Name", "Back"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b>⚙️ CARNAGE Settings - Select Option</b>", parse_mode='HTML', reply_markup=markup)

# ==================== FLASK ROUTES ====================
@app.route('/')
def health_check():
    """Required route for Koyeb to keep service alive"""
    return jsonify({
        "status": "online",
        "service": "CARNAGE Telegram Bot",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "features": ["dashboard", "referral", "tutorial", "achievements", "analytics"]
    })

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
        "total_referrals": get_total_referrals(),
        "total_swaps": get_total_swaps(),
        "total_achievements": get_total_achievements_awarded()
    })

@app.route('/dashboard/<int:user_id>')
def user_dashboard(user_id):
    """Web dashboard for users"""
    user_stats = get_user_detailed_stats(user_id)
    achievements = get_user_achievements(user_id)
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CARNAGE Dashboard - @{{username}}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #0f0f0f; color: white; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .card { background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 15px; }
            .stat { display: flex; justify-content: space-between; margin: 10px 0; }
            .badge { background: #667eea; padding: 5px 10px; border-radius: 20px; font-size: 12px; }
            .achievement { display: inline-block; background: #2a2a2a; padding: 10px; margin: 5px; border-radius: 5px; }
            .referral-link { background: #2a2a2a; padding: 15px; border-radius: 5px; word-break: break-all; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 CARNAGE Dashboard</h1>
                <p>Welcome, @{{username}}! 👋</p>
            </div>
            
            <div class="card">
                <h2>📊 Your Statistics</h2>
                {% for stat in stats %}
                <div class="stat">
                    <span>{{stat.name}}:</span>
                    <strong>{{stat.value}}</strong>
                </div>
                {% endfor %}
            </div>
            
            <div class="card">
                <h2>🏆 Achievements ({{achievements.unlocked}}/{{achievements.total}})</h2>
                {% for ach in achievements.list %}
                <div class="achievement">
                    {{ach.emoji}} {{ach.name}}
                </div>
                {% endfor %}
            </div>
            
            <div class="card">
                <h2>👥 Referral Program</h2>
                <p>Your Referrals: <strong>{{referrals.count}}</strong></p>
                <p>Free Swaps Earned: <strong>{{referrals.free_swaps}}</strong></p>
                <div class="referral-link">
                    <strong>Your Referral Link:</strong><br>
                    https://t.me/{{bot_username}}?start=ref-{{user_id}}
                </div>
                <p style="font-size: 12px; color: #888; margin-top: 10px;">
                    ⭐ Each referral gives you 2 FREE swaps! No approval needed!
                </p>
            </div>
            
            <div class="card">
                <h2>🚀 Quick Actions</h2>
                <p><a href="https://t.me/{{bot_username}}?start=swap" style="color: #667eea;">Start New Swap</a></p>
                <p><a href="https://t.me/{{bot_username}}?start=tutorial" style="color: #667eea;">Interactive Tutorial</a></p>
                <p><a href="https://t.me/{{bot_username}}" style="color: #667eea;">Open Bot in Telegram</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_template, **user_stats)

# ==================== KEEP ALIVE LOOP ====================
def keep_alive_loop():
    """Internal loop to keep bot awake"""
    while True:
        try:
            # Make request to self
            requests.get("https://separate-genny-1carnage1-2b4c603c.koyeb.app/ping1", timeout=10)
        except:
            pass
        time.sleep(300)  # 5 minutes

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Handle callback queries"""
    user_id = call.from_user.id
    message_id = call.message.message_id
    
    if call.data == "check_channels":
        # Check if user has joined all channels
        channel_results = check_all_channels(user_id)
        
        if all(channel_results.values()):
            # User has joined all channels
            bot.answer_callback_query(call.id, "✅ Verified! You've joined all channels!")
            bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text="🎉 *Channel Verification Successful!*\n\nYou've joined all required channels! ✅\n\nNow you can use the bot features.\n\nSend /start again to begin.",
                parse_mode="Markdown"
            )
            
            # Mark user as having joined channels
            mark_channels_joined(user_id)
            
            # Award achievement
            award_achievement(user_id, "channel_member")
            
            # Send welcome message with features
            time.sleep(1)
            welcome_features = f"""
🤖 *Welcome to CARNAGE Swapper Bot!* 🎉

*What's New in v3.0:*
✨ *Referral System* - Get 2 FREE swaps per friend!
📊 *Web Dashboard* - Track your stats online
🏆 *Achievements* - Unlock badges as you swap
🎓 *Interactive Tutorial* - Learn step by step
📈 *Detailed Analytics* - See your swap history

*Quick Start:*
1️⃣ Add Instagram sessions
2️⃣ Swap usernames instantly
3️⃣ Refer friends for FREE swaps
4️⃣ Track progress on dashboard

*Referral Bonus:* 🎁
• Share your link → Get 2 FREE swaps per friend!
• No approval needed for referrals!

Use /tutorial for guided tour or /help for commands.
"""
            bot.send_message(user_id, welcome_features, parse_mode="Markdown")
            
        else:
            # User hasn't joined all channels
            missing_channels = []
            for channel_type, joined in channel_results.items():
                if not joined:
                    missing_channels.append(CHANNELS[channel_type]['name'])
            
            bot.answer_callback_query(
                call.id, 
                f"❌ You need to join: {', '.join(missing_channels)}",
                show_alert=True
            )
            
            # Update message to show missing channels
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

# ==================== COMMAND HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    
    # Check for referral parameter
    referral_code = "direct"
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith("ref-"):
            referral_code = param[4:]  # Remove "ref-" prefix
        elif param == "tutorial":
            start_tutorial_command(message)
            return
        elif param == "swap":
            if is_user_approved(user_id):
                show_swapper_menu(user_id)
            else:
                bot.send_message(user_id, "Please complete /start first")
            return
    
    # Add user to database
    add_user(user_id, username, first_name, last_name, referral_code)
    update_user_active(user_id)
    
    # Check if user has joined channels (either in DB or live check)
    if has_user_joined_channels(user_id) or has_joined_all_channels(user_id):
        # User has already joined channels
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
        # User needs to join channels first
        send_welcome_with_channels(user_id, first_name)

@bot.message_handler(commands=['tutorial'])
def start_tutorial_command(message):
    """Start interactive tutorial"""
    user_id = message.chat.id
    
    # Check channel membership first
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    tutorial_sessions[user_id] = 0
    show_tutorial_step(user_id, 0)

@bot.message_handler(commands=['dashboard'])
def dashboard_command(message):
    """Send user their dashboard link"""
    user_id = message.from_user.id
    
    # Check channel membership first
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    dashboard_url = f"https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/{user_id}"
    
    bot.send_message(
        user_id,
        f"📊 *Your Personal Dashboard*\n\n"
        f"Visit: {dashboard_url}\n\n"
        f"• View your statistics 📈\n"
        f"• Track achievements 🏆\n"
        f"• Check referral progress 👥\n"
        f"• See swap history 🔄",
        parse_mode="Markdown"
    )
    
    # Award achievement
    award_achievement(user_id, "dashboard_user")

@bot.message_handler(commands=['refer'])
def referral_command(message):
    """Generate referral link"""
    user_id = message.from_user.id
    
    # Check channel membership first
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref-{user_id}"
    referrals_count = get_user_referrals_count(user_id)
    free_swaps = get_user_free_swaps(user_id)
    
    response = f"""
🎁 *CARNAGE Referral Program*

*Your Referral Link:*
`{referral_link}`

*How it works:*
1. Share your link with friends
2. When they join using your link:
   • They get instant approval ✅
   • You get 2 FREE swaps! 🆓
3. No limits - refer unlimited friends!

*Your Stats:*
• Total Referrals: {referrals_count}
• Free Swaps Earned: {free_swaps}
• Pending Approval: {"No - Instant for referrals!"}

*Pro Tip:* Share in Instagram/Twitter bios for maximum referrals!
"""
    
    bot.send_message(user_id, response, parse_mode="Markdown")
    
    # Create share button
    markup = InlineKeyboardMarkup()
    share_text = f"Join CARNAGE Swapper Bot for Instagram username swapping! Get instant approval with my link: {referral_link}"
    markup.add(InlineKeyboardButton("📤 Share Link", switch_inline_query=share_text))
    
    bot.send_message(user_id, "Click below to share:", reply_markup=markup)

@bot.message_handler(commands=['achievements'])
def achievements_command(message):
    """Show user's achievements"""
    user_id = message.from_user.id
    
    # Check channel membership first
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    achievements = get_user_achievements(user_id)
    
    response = f"""
🏆 *Your Achievements*

*Progress:* {achievements['unlocked']}/{achievements['total']} unlocked

*Unlocked Achievements:*
"""
    
    if achievements['list']:
        for ach in achievements['list']:
            response += f"\n{ach['emoji']} *{ach['name']}* - {ach['date'].split()[0]}"
    else:
        response += "\nNo achievements yet! Start swapping to unlock them! 🔄"
    
    # Add locked achievements preview
    response += "\n\n*Locked Achievements:*"
    locked_count = 0
    for ach_id, ach_data in ACHIEVEMENTS.items():
        if ach_id not in [a['id'] for a in achievements['list']]:
            if locked_count < 5:  # Show only 5 locked
                response += f"\n🔒 {ach_data['name']}"
                locked_count += 1
    
    if locked_count >= 5:
        response += f"\n... and {achievements['total'] - achievements['unlocked'] - 5} more"
    
    bot.send_message(user_id, response, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show user statistics"""
    user_id = message.from_user.id
    
    # Check channel membership first
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    stats = get_user_detailed_stats(user_id)
    
    if not stats:
        bot.send_message(user_id, "No statistics available yet.")
        return
    
    response = f"""
📊 *Your Statistics*

*Basic Info:*
• Username: @{stats['username']}
• User ID: `{user_id}`
• Status: {"✅ Approved" if is_user_approved(user_id) else "⏳ Pending"}

*Swap Stats:*
• Total Swaps: {stats['stats'][0]['value']}
• Successful: {stats['stats'][1]['value']}
• Success Rate: {stats['stats'][2]['value']}

*Referral Stats:*
• Total Referrals: {stats['referrals']['count']}
• Free Swaps Available: {stats['referrals']['free_swaps']}

*Achievements:* {stats['achievements']['unlocked']}/{stats['achievements']['total']} unlocked

*Dashboard:* https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/{user_id}
"""
    
    bot.send_message(user_id, response, parse_mode="Markdown")

@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
    """Show leaderboard"""
    user_id = message.from_user.id
    
    # Check channel membership first
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    # Top by successful swaps
    top_swappers = execute_query('''
        SELECT username, successful_swaps, total_referrals 
        FROM users 
        WHERE username IS NOT NULL 
        ORDER BY successful_swaps DESC 
        LIMIT 10
    ''')
    
    # Top by referrals
    top_referrers = execute_query('''
        SELECT username, total_referrals, successful_swaps
        FROM users 
        WHERE username IS NOT NULL 
        ORDER BY total_referrals DESC 
        LIMIT 10
    ''')
    
    response = """
🏆 *CARNAGE Leaderboard*

*Top Swappers:*
"""
    
    for i, (username, swaps, refs) in enumerate(top_swappers, 1):
        emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1]
        response += f"\n{emoji} @{username}: {swaps} swaps"
    
    response += "\n\n*Top Referrers:*"
    
    for i, (username, refs, swaps) in enumerate(top_referrers, 1):
        emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1]
        response += f"\n{emoji} @{username}: {refs} referrals"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(commands=['history'])
def history_command(message):
    """Show user's swap history"""
    user_id = message.from_user.id
    
    # Check channel membership first
    if not has_user_joined_channels(user_id) and not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    history = execute_query('''
        SELECT target_username, status, swap_time 
        FROM swap_history 
        WHERE user_id = ? 
        ORDER BY swap_time DESC 
        LIMIT 10
    ''', (user_id,))
    
    if not history:
        bot.send_message(user_id, "No swap history yet. Start swapping! 🔄")
        return
    
    response = "📜 *Your Recent Swaps*\n\n"
    
    for target, status, swap_time in history:
        status_emoji = "✅" if status == "success" else "❌"
        date_str = datetime.strptime(swap_time, "%Y-%m-%d %H:%M:%S").strftime("%b %d")
        response += f"{status_emoji} *{target}* - {date_str}\n"
    
    response += f"\nView full history on your dashboard!"
    
    bot.send_message(user_id, response, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show help menu"""
    user_id = message.from_user.id
    
    # Check channel membership first
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

*Admin Commands:* (Admin only)
/approve - Approve user access
/users - List all users
/broadcast - Send message to all
/ban - Ban user

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

# ==================== INLINE QUERY HANDLER ====================
@bot.inline_handler(lambda query: True)
def inline_query_handler(inline_query):
    """Handle inline queries"""
    try:
        user_id = inline_query.from_user.id
        
        results = [
            InlineQueryResultArticle(
                id='1',
                title='📊 My Dashboard',
                description='View your personal dashboard',
                input_message_content=InputTextMessageContent(
                    f"📊 *My CARNAGE Dashboard*\n\n"
                    f"https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/{user_id}\n\n"
                    f"Track stats, achievements, and referrals!",
                    parse_mode='Markdown'
                ),
                thumb_url='https://img.icons8.com/color/96/000000/dashboard.png'
            ),
            InlineQueryResultArticle(
                id='2',
                title='🎁 Referral Link',
                description='Share to get FREE swaps!',
                input_message_content=InputTextMessageContent(
                    f"🎁 *Join CARNAGE Swapper Bot!*\n\n"
                    f"Get instant approval with my link:\n"
                    f"https://t.me/{BOT_USERNAME}?start=ref-{user_id}\n\n"
                    f"• Instagram username swapping\n"
                    f"• No approval needed for referrals\n"
                    f"• 2 FREE swaps per referral!",
                    parse_mode='Markdown'
                ),
                thumb_url='https://img.icons8.com/color/96/000000/gift.png'
            ),
            InlineQueryResultArticle(
                id='3',
                title='📈 Bot Statistics',
                description='View bot stats',
                input_message_content=InputTextMessageContent(
                    f"🤖 *CARNAGE Bot Stats*\n\n"
                    f"• Total Users: {get_total_users()}\n"
                    f"• Total Swaps: {get_total_swaps()}\n"
                    f"• Total Referrals: {get_total_referrals()}\n\n"
                    f"Join: https://t.me/{BOT_USERNAME}",
                    parse_mode='Markdown'
                ),
                thumb_url='https://img.icons8.com/color/96/000000/statistics.png'
            ),
            InlineQueryResultArticle(
                id='4',
                title='🔄 Quick Swap',
                description='Start a new swap',
                input_message_content=InputTextMessageContent(
                    "🔄 *Start a New Swap*\n\n"
                    "1. Add Main Session\n"
                    "2. Add Target Session\n"
                    "3. Run Swap\n\n"
                    f"Start: https://t.me/{BOT_USERNAME}?start=swap",
                    parse_mode='Markdown'
                ),
                thumb_url='https://img.icons8.com/color/96/000000/swap.png'
            ),
        ]
        
        bot.answer_inline_query(inline_query.id, results, cache_time=1)
    except Exception as e:
        print(f"Inline query error: {e}")

# ==================== ADMIN COMMANDS ====================
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
        user_id, username, first_name, approved, approved_until, is_banned, referrals = user
        
        status = "✅ Approved" if approved == 1 else "⏳ Pending"
        if is_banned == 1:
            status = "🚫 Banned"
        
        username_display = f"@{username}" if username else "No username"
        name_display = f"{first_name}" if first_name else "Unknown"
        
        response += f"🆔 `{user_id}`\n"
        response += f"👤 {name_display} {username_display}\n"
        response += f"📊 {status} | 👥 {referrals} refs\n"
        response += "─" * 20 + "\n"
    
    total_users = get_total_users()
    active_users = get_active_users_count()
    
    response += f"\n📈 *Statistics*\n"
    response += f"• Total Users: {total_users}\n"
    response += f"• Active (24h): {active_users}\n"
    response += f"• Pending Approval: {sum(1 for u in users if u[3] == 0 and u[5] == 0)}\n"
    response += f"• Banned: {sum(1 for u in users if u[5] == 1)}\n"
    response += f"• Total Referrals: {get_total_referrals()}\n"
    
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            bot.send_message(message.chat.id, part, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, response, parse_mode="Markdown")

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
        
        users = execute_query("SELECT user_id FROM users WHERE approved = 1 AND is_banned = 0")
        user_ids = [row[0] for row in users]
        
        if not user_ids:
            bot.reply_to(message, "📭 No users to broadcast to")
            return
        
        bot.reply_to(message, f"📢 Broadcasting to {len(user_ids)} users...")
        
        success_count = 0
        fail_count = 0
        
        for user_id in user_ids:
            try:
                bot.send_message(user_id, broadcast_text)
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

# ==================== MENU HANDLERS ====================
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text
    
    # Update user activity
    update_user_active(chat_id)
    
    # Check if in tutorial
    if handle_tutorial_response(chat_id, text):
        return
    
    # Handle menu navigation
    if text == "Back":
        show_main_menu(chat_id)
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
        bot.send_message(chat_id, "<b>📥 Send Main Session ID</b>", parse_mode='HTML')
        return
    
    if text == "🎯 Target Session":
        bot.send_message(chat_id, "<b>🎯 Send Target Session ID</b>", parse_mode='HTML')
        return
    
    if text == "🔄 Swapper":
        show_swapper_menu(chat_id)
        return
    
    if text == "⚙️ Settings":
        show_settings_menu(chat_id)
        return
    
    # Default response
    if text not in ["/start", "/help", "/tutorial"]:
        bot.send_message(chat_id, "Use /help to see available commands or /tutorial for guided tour!")

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

# ==================== FLASK SERVER THREAD ====================
def run_flask_app():
    """Run Flask app in separate thread"""
    port = int(os.environ.get('PORT', 8000))
    print(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ==================== MAIN STARTUP ====================
def main():
    """Start everything"""
    # Start Flask server immediately in background thread
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Wait a moment for Flask to start
    time.sleep(2)
    
    # Initialize database
    print("🔧 Initializing database...")
    init_database()
    
    print("✅ Database initialized successfully")
    print("🚀 CARNAGE Swapper Bot v3.0 with Advanced Features")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot Username: @{BOT_USERNAME}")
    print(f"📢 Updates Channel: {CHANNELS['updates']['id']}")
    print(f"✅ Proofs Channel: {CHANNELS['proofs']['id']}")
    print("✨ Features: Dashboard, Referral, Tutorial, Achievements, Analytics")
    
    # Start Telegram bot in background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("🤖 Telegram bot started in background")
    
    # Start keep-alive loop
    threading.Thread(target=keep_alive_loop, daemon=True).start()
    
    # Keep main thread alive
    print(f"📊 Dashboard: https://separate-genny-1carnage1-2b4c603c.koyeb.app")
    print("✅ Bot is fully operational!")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Bot shutting down...")

if __name__ == '__main__':
    main()
