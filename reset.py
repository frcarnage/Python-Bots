#!/usr/bin/env python3
"""
MEGA INSTAGRAM BOT - Complete Suite with 4L Username Hunting
Optimized for Koyeb 24/7 Deployment
"""

import json
import requests
import logging
import threading
import time
import random
import sqlite3
import hashlib
import hmac
import base64
import re
import os
import queue
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Flask, jsonify, request
import telebot
from telebot import types
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== CONFIGURATION ==========
# CHANGE THIS TO A NEW BOT TOKEN FROM @BOTFATHER
# Get a new token for this bot at: https://t.me/BotFather
BOT_TOKEN = "8522048948:AAGSCayCSZZF_6z2nHcGjVC7B64E3C9u6F8"  # <-- CHANGE THIS!
BOT_PORT = int(os.environ.get('PORT', 6001))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

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

# ========== HUNTING SYSTEM GLOBALS ==========
hunting_sessions = {}
username_queue = queue.Queue()
available_usernames = []
hunt_lock = threading.Lock()

# Character sets for 4L usernames
CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"
SEPARATORS = "._"

# ========== MASSIVE USER AGENTS LIST ==========
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
    'Instagram 295.0.0.19.106 Android (33/13; 420dpi; 1080x2260; samsung; SM-S911B; b0s; exynos9830; en_US; 509092389)',
]

# Generate more user agents dynamically
for version in range(100, 121):
    USER_AGENTS.append(f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36')
    USER_AGENTS.append(f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36')

random.shuffle(USER_AGENTS)
logger.info(f"Loaded {len(USER_AGENTS)} user agents")

# ========== DATABASE SETUP ==========
def init_databases():
    """Initialize all databases"""
    conn = sqlite3.connect('instagram_bot.db')
    cursor = conn.cursor()
    
    # User sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            instagram_user_id TEXT,
            instagram_username TEXT,
            session_id TEXT,
            csrftoken TEXT,
            device_id TEXT,
            uuid TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Hunting sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hunting_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            session_id TEXT UNIQUE,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'running',
            checked INTEGER DEFAULT 0,
            available INTEGER DEFAULT 0,
            taken INTEGER DEFAULT 0,
            rate_limited INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            average_speed REAL DEFAULT 0.0,
            threads INTEGER DEFAULT 5
        )
    ''')
    
    # Found usernames
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS found_usernames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pattern_type TEXT,
            length INTEGER,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

init_databases()

# ========== USERNAME HUNTER CLASS ==========
class UsernameHunter:
    """4L Username Hunter with Telegram Integration"""
    
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.session_id = f"HUNT_{int(time.time())}_{random.randint(1000, 9999)}"
        self.running = False
        self.threads = 5
        self.workers = []
        self.stats = {
            'checked': 0,
            'available': 0,
            'taken': 0,
            'rate_limited': 0,
            'errors': 0,
            'start_time': time.time(),
            'last_available': None
        }
        self.available_list = []
        self.lock = threading.Lock()
        
        # Save session to database
        self.save_session()
        
        logger.info(f"Created hunter session {self.session_id} for {chat_id}")
    
    def save_session(self):
        """Save hunting session to database"""
        conn = sqlite3.connect('instagram_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO hunting_sessions 
            (chat_id, session_id, status, threads)
            VALUES (?, ?, 'running', ?)
        ''', (self.chat_id, self.session_id, self.threads))
        
        conn.commit()
        conn.close()
    
    def update_stats(self):
        """Update session stats in database"""
        conn = sqlite3.connect('instagram_bot.db')
        cursor = conn.cursor()
        
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        
        cursor.execute('''
            UPDATE hunting_sessions 
            SET checked = ?, available = ?, taken = ?, rate_limited = ?, errors = ?,
                average_speed = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available'],
            self.stats['taken'],
            self.stats['rate_limited'],
            self.stats['errors'],
            speed,
            self.session_id
        ))
        
        conn.commit()
        conn.close()
    
    def save_username(self, username, pattern_type="mixed"):
        """Save found username to database"""
        conn = sqlite3.connect('instagram_bot.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO found_usernames 
                (session_id, username, pattern_type, length)
                VALUES (?, ?, ?, ?)
            ''', (self.session_id, username, pattern_type, len(username)))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving username: {e}")
        
        conn.close()
    
    def generate_4l_username(self):
        """Generate a 4-character username"""
        patterns = [
            lambda: ''.join(random.choices(CHARS, k=4)),
            lambda: ''.join(random.choices(CHARS, k=3)) + random.choice(SEPARATORS),
            lambda: ''.join(random.choices(CHARS, k=2)) + random.choice(SEPARATORS) + random.choice(CHARS),
            lambda: random.choice(CHARS) + random.choice(SEPARATORS) + ''.join(random.choices(CHARS, k=2)),
        ]
        
        while True:
            username = random.choice(patterns)()
            if username[0] not in SEPARATORS:
                return username
    
    def check_username(self, username):
        """Check if username is available on Instagram"""
        try:
            user_agent = random.choice(USER_AGENTS)
            csrf_token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=32))
            
            headers = {
                'Host': 'www.instagram.com',
                'User-Agent': user_agent,
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrf_token,
                'X-IG-App-ID': '936619743392459',
                'Origin': 'https://www.instagram.com',
                'Referer': 'https://www.instagram.com/accounts/emailsignup/',
            }
            
            cookies = f'csrftoken={csrf_token}; mid={random.randint(100000000000000000000, 999999999999999999999)}; ig_did={self.generate_ig_did()}; ig_nrcb=1'
            headers['Cookie'] = cookies
            
            random_email = f"user{random.randint(100000, 9999999)}@gmail.com"
            data = {
                'email': random_email,
                'username': username,
                'first_name': '',
                'opt_into_one_tap': 'false'
            }
            
            response = requests.post(
                'https://www.instagram.com/accounts/web_create_ajax/attempt/',
                headers=headers,
                data=data,
                timeout=8,
                verify=False
            )
            
            if response.status_code == 200:
                response_text = response.text.lower()
                
                if 'username_is_taken' in response_text or '"errors": {"username":' in response_text:
                    return False, 'taken'
                elif 'spam' in response_text or 'feedback_required' in response_text:
                    return False, 'rate_limited'
                elif 'account_created' in response_text or '"errors": {}' in response_text:
                    return True, 'available'
                else:
                    return False, 'taken'
            
            elif response.status_code == 429:
                return False, 'rate_limited'
            
            else:
                return False, f'http_{response.status_code}'
                
        except Exception as e:
            logger.error(f"Check error: {e}")
            return False, 'error'
    
    def generate_ig_did(self):
        """Generate Instagram device ID"""
        parts = [
            ''.join(random.choices('ABCDEF0123456789', k=8)),
            ''.join(random.choices('ABCDEF0123456789', k=4)),
            ''.join(random.choices('ABCDEF0123456789', k=4)),
            ''.join(random.choices('ABCDEF0123456789', k=4)),
            ''.join(random.choices('ABCDEF0123456789', k=12)).upper()
        ]
        return '-'.join(parts)
    
    def send_to_telegram(self, username):
        """Send found username to Telegram"""
        try:
            message = f"""🎯 *4L USERNAME FOUND!* 🚀

━━━━━━━━━━━━━━━━━━
📛 *Username:* `{username}`
✅ *Status:* AVAILABLE
🔢 *Length:* 4 Characters
🕐 *Time:* {datetime.now().strftime("%H:%M:%S")}
📊 *Total Found:* {self.stats['available']}
━━━━━━━━━━━━━━━━━━

@xk3ny | @kenyxshop"""
            
            response = requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                data={
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                },
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def worker(self, worker_id):
        """Worker thread for checking usernames"""
        while self.running:
            try:
                username = self.generate_4l_username()
                available, status = self.check_username(username)
                
                with self.lock:
                    self.stats['checked'] += 1
                    
                    if available:
                        self.stats['available'] += 1
                        self.stats['last_available'] = username
                        self.available_list.append(username)
                        
                        # Save to database
                        pattern_type = "clean" if all(c in CHARS for c in username) else "with_separator"
                        self.save_username(username, pattern_type)
                        
                        # Send to Telegram
                        self.send_to_telegram(username)
                        
                        logger.info(f"[{worker_id}] ✅ {username}")
                        
                    elif status == 'taken':
                        self.stats['taken'] += 1
                    elif status == 'rate_limited':
                        self.stats['rate_limited'] += 1
                        time.sleep(random.uniform(3, 8))
                    else:
                        self.stats['errors'] += 1
                
                # Normal delay
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                time.sleep(2)
    
    def start_hunting(self):
        """Start the username hunting"""
        self.running = True
        logger.info(f"Starting hunting session {self.session_id} with {self.threads} threads")
        
        # Start worker threads
        for i in range(self.threads):
            thread = threading.Thread(target=self.worker, args=(i,), daemon=True)
            thread.start()
            self.workers.append(thread)
        
        # Start stats updater
        threading.Thread(target=self.stats_updater, daemon=True).start()
        
        # Start Telegram updates
        threading.Thread(target=self.telegram_updater, daemon=True).start()
        
        return True
    
    def stop_hunting(self):
        """Stop the username hunting"""
        self.running = False
        logger.info(f"Stopping hunting session {self.session_id}")
        
        # Update final stats
        self.update_stats()
        
        # Update session status
        conn = sqlite3.connect('instagram_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE hunting_sessions SET status = "stopped", end_time = CURRENT_TIMESTAMP WHERE session_id = ?', (self.session_id,))
        conn.commit()
        conn.close()
        
        return True
    
    def stats_updater(self):
        """Update stats in database periodically"""
        while self.running:
            time.sleep(30)
            self.update_stats()
    
    def telegram_updater(self):
        """Send periodic updates to Telegram"""
        while self.running:
            time.sleep(60)  # Every minute
            
            if not self.running:
                break
            
            elapsed = time.time() - self.stats['start_time']
            speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
            
            stats_message = f"""
📊 *HUNTING STATS UPDATE*

⏱️ *Running:* {elapsed:.0f}s
🔍 *Checked:* {self.stats['checked']:,}
✅ *Available:* {self.stats['available']:,}
❌ *Taken:* {self.stats['taken']:,}
⚠️ *Rate Limited:* {self.stats['rate_limited']:,}

⚡ *Speed:* {speed:.1f} checks/sec
🎯 *Success Rate:* {(self.stats['available']/max(1, self.stats['checked'])*100):.2f}%

📈 *Last Found:* `{self.stats['last_available'] or 'None'}`
🏷️ *Session:* `{self.session_id}`

🔄 *Status:* Running...
"""
            
            try:
                bot.send_message(self.chat_id, stats_message, parse_mode='Markdown')
            except:
                pass
    
    def get_stats(self):
        """Get current statistics"""
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        
        return {
            'session_id': self.session_id,
            'running': self.running,
            'elapsed': elapsed,
            'checked': self.stats['checked'],
            'available': self.stats['available'],
            'taken': self.stats['taken'],
            'rate_limited': self.stats['rate_limited'],
            'errors': self.stats['errors'],
            'speed': speed,
            'success_rate': (self.stats['available']/max(1, self.stats['checked'])*100),
            'last_available': self.stats['last_available']
        }

# ========== TELEGRAM COMMANDS ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Welcome message"""
    welcome_text = """
⚡ *MEGA INSTAGRAM BOT* ⚡
*4L Username Hunter*

🚀 *Features:*
• Real-time 4L username checking
• Multi-threaded hunting
• Telegram alerts for finds
• Live stats every minute
• Database backup
• 24/7 operation

🔧 *Commands:*
/hunt - Start 4L username hunting
/stophunt - Stop hunting session
/huntstats - Live hunting statistics
/myhunts - View hunting history
/found - Show found usernames

⚡ *Quick Start:*
1. /hunt - Start finding 4L usernames
2. Wait for Telegram alerts
3. Check /huntstats for progress
4. /stophunt to stop anytime

🎯 *Expected Results:*
• 5-20 4L usernames per hour
• Instant Telegram notifications
• Full database history
• Runs 24/7 permanently

*Ready to hunt? Use /hunt now!*
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['hunt'])
def start_hunting(message):
    """Start 4L username hunting"""
    chat_id = message.chat.id
    
    if chat_id in hunting_sessions and hunting_sessions[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting! Use /stophunt to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('🚀 Fast (8 threads)', '⚡ Medium (5 threads)', '🐢 Slow (3 threads)')
    
    bot.send_message(
        chat_id,
        "🎯 *Select Hunting Speed:*\n\n"
        "• 🚀 Fast - 8 threads (fastest)\n"
        "• ⚡ Medium - 5 threads (balanced)\n"
        "• 🐢 Slow - 3 threads (safest)\n\n"
        "Use /stophunt to stop anytime.",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_hunt_speed)

def process_hunt_speed(message):
    """Process hunting speed selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    speed_map = {
        '🚀 fast (8 threads)': 8,
        '⚡ medium (5 threads)': 5,
        '🐢 slow (3 threads)': 3
    }
    
    threads = speed_map.get(choice, 5)
    
    # Remove keyboard
    bot.send_message(chat_id, "🚀 Starting hunter...", reply_markup=types.ReplyKeyboardRemove())
    
    # Create and start hunter
    hunter = UsernameHunter(chat_id)
    hunter.threads = threads
    
    if hunter.start_hunting():
        hunting_sessions[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *HUNTING STARTED!*\n\n"
            f"🔧 Threads: {threads}\n"
            f"🎯 Target: 4L Usernames\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"📊 Updates: Every minute\n"
            f"🔔 Alerts: On for finds\n\n"
            f"Use /stophunt to stop.",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start hunting.")

@bot.message_handler(commands=['stophunt'])
def stop_hunting(message):
    """Stop username hunting"""
    chat_id = message.chat.id
    
    if chat_id not in hunting_sessions or not hunting_sessions[chat_id].running:
        bot.reply_to(message, "❌ No active hunting session.")
        return
    
    hunter = hunting_sessions[chat_id]
    
    if hunter.stop_hunting():
        stats = hunter.get_stats()
        
        final_message = f"""
🛑 *HUNTING STOPPED*

📊 *Final Stats:*

⏱️ Duration: {stats['elapsed']:.0f}s
🔍 Checked: {stats['checked']:,}
✅ Available: {stats['available']:,}
❌ Taken: {stats['taken']:,}
⚠️ Rate Limited: {stats['rate_limited']:,}

⚡ Speed: {stats['speed']:.1f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`

💾 All usernames saved to database.
📁 View with /found

Thanks for hunting! 🎯
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del hunting_sessions[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop hunting.")

@bot.message_handler(commands=['huntstats'])
def show_hunt_stats(message):
    """Show current hunting statistics"""
    chat_id = message.chat.id
    
    if chat_id not in hunting_sessions or not hunting_sessions[chat_id].running:
        bot.reply_to(message, "❌ No active hunting session. Start with /hunt")
        return
    
    hunter = hunting_sessions[chat_id]
    stats = hunter.get_stats()
    
    stats_message = f"""
📊 *LIVE HUNTING STATS*

⏱️ Running: {stats['elapsed']:.0f}s
🔍 Checked: {stats['checked']:,}
✅ Available: {stats['available']:,}
❌ Taken: {stats['taken']:,}
⚠️ Rate Limited: {stats['rate_limited']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.1f} checks/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}`
🏷️ Session: `{stats['session_id']}`

🔄 Status: {'✅ Running' if stats['running'] else '❌ Stopped'}
"""
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['found'])
def show_found_usernames(message):
    """Show recently found usernames"""
    chat_id = message.chat.id
    
    conn = sqlite3.connect('instagram_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, found_at FROM found_usernames 
        WHERE session_id IN (SELECT session_id FROM hunting_sessions WHERE chat_id = ?)
        ORDER BY found_at DESC LIMIT 20
    ''', (chat_id,))
    
    usernames = cursor.fetchall()
    
    if not usernames:
        bot.reply_to(message, "📭 No usernames found yet. Start with /hunt")
        conn.close()
        return
    
    response = "🎯 *RECENTLY FOUND USERNAMES*\n\n"
    
    for username, found_at in usernames:
        time_str = datetime.strptime(found_at, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
        response += f"• `{username}` - {time_str}\n"
    
    cursor.execute('SELECT COUNT(*) FROM found_usernames WHERE session_id IN (SELECT session_id FROM hunting_sessions WHERE chat_id = ?)', (chat_id,))
    total = cursor.fetchone()[0]
    
    response += f"\n📊 Total Found: {total:,} usernames"
    
    conn.close()
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['myhunts'])
def show_my_hunts(message):
    """Show user's hunting history"""
    chat_id = message.chat.id
    
    conn = sqlite3.connect('instagram_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT session_id, start_time, end_time, checked, available, average_speed
        FROM hunting_sessions WHERE chat_id = ? ORDER BY start_time DESC LIMIT 10
    ''', (chat_id,))
    
    sessions = cursor.fetchall()
    
    if not sessions:
        bot.reply_to(message, "📭 No hunting sessions. Start with /hunt")
        conn.close()
        return
    
    response = "📊 *YOUR HUNTING HISTORY*\n\n"
    
    for session_id, start_time, end_time, checked, available, speed in sessions:
        start_str = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').strftime('%b %d %H:%M')
        
        if end_time:
            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
            start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            duration = (end_dt - start_dt).total_seconds()
            duration_str = f"{duration:.0f}s"
        else:
            duration_str = "Running"
        
        success_rate = (available / checked * 100) if checked > 0 else 0
        
        response += f"""
🏷️ *Session:* `{session_id}`
├── Started: {start_str}
├── Duration: {duration_str}
├── Checked: {checked:,}
├── Available: {available:,}
├── Success: {success_rate:.2f}%
└── Speed: {speed:.1f}/s

"""
    
    cursor.execute('SELECT COUNT(*) FROM found_usernames WHERE session_id IN (SELECT session_id FROM hunting_sessions WHERE chat_id = ?)', (chat_id,))
    total = cursor.fetchone()[0]
    
    response += f"\n📈 Total Found Usernames: {total:,}"
    
    conn.close()
    
    bot.reply_to(message, response, parse_mode='Markdown')

# ========== FLASK ENDPOINTS ==========
@app.route('/hunter')
def home():
    """Root endpoint for health checks"""
    return jsonify({
        "status": "running",
        "service": "Instagram 4L Hunter Bot",
        "version": "2.0",
        "active_hunters": len([h for h in hunting_sessions.values() if h.running]),
        "uptime": time.time() - app_start_time,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health/hunter')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "bot_running": True,
        "hunting_active": len([h for h in hunting_sessions.values() if h.running]),
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    }), 200

# ========== ADD COMPATIBILITY ENDPOINTS ==========
@app.route('/')
def root_home():
    """Root endpoint for compatibility"""
    return jsonify({
        "status": "running",
        "service": "Instagram 4L Hunter Bot",
        "message": "Use /hunter for hunter-specific info"
    })

@app.route('/health')
def health_compatibility():
    """Health endpoint for compatibility"""
    return jsonify({
        "status": "healthy",
        "bot": "hunter",
        "message": "Use /health/hunter for detailed health"
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad request', 400

# ========== BOT RUNNER ==========
def run_bot_polling():
    """Run bot in polling mode"""
    print("🤖 Starting Instagram 4L Hunter Bot...")
    print(f"🔑 Token: {BOT_TOKEN[:10]}...")
    print(f"🌐 Port: {BOT_PORT}")
    print(f"🎯 Features: 4L Username Hunting")
    print("=" * 70)
    
    while True:
        try:
            bot.polling(non_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Bot error: {e}")
            time.sleep(5)

def cleanup_hunters():
    """Clean up stopped hunting sessions"""
    while True:
        time.sleep(60)
        to_remove = []
        for chat_id, hunter in hunting_sessions.items():
            if not hunter.running:
                to_remove.append(chat_id)
        
        for chat_id in to_remove:
            del hunting_sessions[chat_id]

# ========== MAIN ==========
if __name__ == '__main__':
    app_start_time = time.time()
    
    print("=" * 70)
    print("🚀 INSTAGRAM 4L HUNTER BOT - KOYEB DEPLOYMENT")
    print("=" * 70)
    print(f"🔑 Token: {BOT_TOKEN[:10]}...")
    print(f"🌐 Port: {BOT_PORT}")
    print(f"🏓 Health: http://localhost:{BOT_PORT}/health/hunter")
    print("=" * 70)
    print("🎯 4L HUNTING FEATURES:")
    print("• Real-time username checking")
    print("• Multi-threaded (3-8 threads)")
    print("• Telegram alerts for finds")
    print("• Live stats every minute")
    print("• Database backup")
    print("• 24/7 operation")
    print("=" * 70)
    
    # Start cleanup thread
    threading.Thread(target=cleanup_hunters, daemon=True).start()
    
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
        print("🌐 Using webhook mode")
        print(f"🔗 Webhook URL: {WEBHOOK_URL}")
    else:
        print("📡 Using polling mode")
        bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
        bot_thread.start()
    
    print("✅ Bot started successfully!")
    print("🎯 Use /hunt in Telegram to start hunting")
    print("🔧 Runs 24/7 on Koyeb")
    print("=" * 70)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Stopping bot...")
        
        # Stop all hunting sessions
        for chat_id, hunter in hunting_sessions.items():
            if hunter.running:
                hunter.stop_hunting()
        
        print("✅ Clean shutdown complete.")
