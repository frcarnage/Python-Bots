#!/usr/bin/env python3
"""
MEGA INSTAGRAM BOT - Complete Suite with 4L Username Hunting
Combines: Account Recovery + 4L Username Hunter
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
from pathlib import Path
from flask import Flask, jsonify
import telebot
from telebot import types
import secrets
from concurrent.futures import ThreadPoolExecutor
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== CONFIGURATION ==========
BOT_TOKEN = "8522048948:AAH4DVdoM63rhxmiqRtpl_z2O0Lk6w7L3uo"
BOT_PORT = int(os.environ.get('PORT', 6000))

# ========== FLASK APP ==========
app = Flask(__name__)

# ========== TELEGRAM BOT ==========
bot = telebot.TeleBot(BOT_TOKEN)

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== HUNTING SYSTEM GLOBALS ==========
hunting_sessions = {}
hunting_stats = {}
username_queue = queue.Queue()
available_usernames = []
hunt_lock = threading.Lock()

# Character sets for 4L usernames
CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"
SEPARATORS = "._"

# ========== MASSIVE USER AGENTS LIST ==========
USER_AGENTS = [
    # Chrome Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
    # Chrome Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
    # Chrome Linux
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
    # Firefox
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
    
    # Safari
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    
    # Mobile
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
    
    # Instagram App
    'Instagram 295.0.0.19.106 Android (33/13; 420dpi; 1080x2260; samsung; SM-S911B; b0s; exynos9830; en_US; 509092389)',
    'Instagram 295.0.0.19.106 (iPhone14,2; iOS 17_2; en_US; en; scale=3.00; 1170x2532; 509092389)',
]

# Generate more user agents dynamically
for version in range(80, 121):
    USER_AGENTS.append(f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36')
    USER_AGENTS.append(f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36')

random.shuffle(USER_AGENTS)
logger.info(f"Loaded {len(USER_AGENTS)} user agents")

# ========== DATABASE SETUP ==========
def init_databases():
    """Initialize all databases"""
    conn = sqlite3.connect('instagram_bot.db')
    cursor = conn.cursor()
    
    # User sessions (existing)
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
            is_active INTEGER DEFAULT 1,
            tags TEXT,
            integrity_score INTEGER DEFAULT 0
        )
    ''')
    
    # Account appeals (existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            username TEXT,
            email TEXT,
            phone TEXT,
            full_name TEXT,
            appeal_type TEXT,
            appeal_reason TEXT,
            status TEXT DEFAULT 'pending',
            appeal_id TEXT UNIQUE,
            instagram_ticket_id TEXT,
            facebook_case_id TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            result TEXT,
            priority INTEGER DEFAULT 1,
            tags TEXT,
            integrity_score INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 1,
            verification_status TEXT DEFAULT 'unverified',
            appeal_source TEXT DEFAULT 'bot',
            api_method_used TEXT,
            response_data TEXT,
            last_checked TIMESTAMP,
            next_check TIMESTAMP
        )
    ''')
    
    # NEW: Username hunting sessions
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
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pattern_type TEXT DEFAULT 'mixed',
            threads INTEGER DEFAULT 5,
            auto_telegram INTEGER DEFAULT 1
        )
    ''')
    
    # NEW: Found usernames
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS found_usernames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pattern_type TEXT,
            length INTEGER,
            sent_to_telegram INTEGER DEFAULT 0,
            registered INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (session_id) REFERENCES hunting_sessions(session_id)
        )
    ''')
    
    # Action logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            action_type TEXT,
            target TEXT,
            result TEXT,
            status_code INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            details TEXT
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
            'last_available': None,
            'patterns_used': ['LLLL', 'LLLS', 'LLSL', 'LSLL']
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
            (chat_id, session_id, status, pattern_type, threads, auto_telegram)
            VALUES (?, ?, 'running', ?, ?, 1)
        ''', (self.chat_id, self.session_id, 'mixed', self.threads))
        
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
                average_speed = ?, last_update = CURRENT_TIMESTAMP
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
            
            # Mark as sent to telegram
            cursor.execute('''
                UPDATE found_usernames 
                SET sent_to_telegram = 1 
                WHERE username = ? AND session_id = ?
            ''', (username, self.session_id))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error saving username: {e}")
        
        conn.close()
    
    def generate_4l_username(self):
        """Generate a 4-character username"""
        patterns = [
            lambda: ''.join(random.choices(CHARS, k=4)),  # LLLL
            lambda: ''.join(random.choices(CHARS, k=3)) + random.choice(SEPARATORS),  # LLLS
            lambda: ''.join(random.choices(CHARS, k=2)) + random.choice(SEPARATORS) + random.choice(CHARS),  # LLSL
            lambda: random.choice(CHARS) + random.choice(SEPARATORS) + ''.join(random.choices(CHARS, k=2)),  # LSLL
            lambda: random.choice(CHARS) + random.choice(SEPARATORS) + random.choice(CHARS) + random.choice(SEPARATORS),  # LSLS
        ]
        
        while True:
            username = random.choice(patterns)()
            if username[0] not in SEPARATORS:  # Can't start with separator
                return username
    
    def check_username(self, username):
        """Check if username is available on Instagram"""
        try:
            # Generate fresh headers for each request
            user_agent = random.choice(USER_AGENTS)
            csrf_token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=32))
            
            headers = {
                'Host': 'www.instagram.com',
                'User-Agent': user_agent,
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-Instagram-AJAX': str(random.randint(1000000000, 9999999999)),
                'X-CSRFToken': csrf_token,
                'X-IG-App-ID': '936619743392459',
                'Origin': 'https://www.instagram.com',
                'Referer': 'https://www.instagram.com/accounts/emailsignup/',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            cookies = {
                'csrftoken': csrf_token,
                'mid': ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', k=21)),
                'ig_did': self.generate_ig_did(),
                'ig_nrcb': '1'
            }
            
            # Prepare cookies string
            cookies_str = '; '.join([f'{k}={v}' for k, v in cookies.items()])
            headers['Cookie'] = cookies_str
            
            # Prepare data
            random_email = f"user{random.randint(100000, 9999999)}@gmail.com"
            data = {
                'email': random_email,
                'username': username,
                'first_name': '',
                'opt_into_one_tap': 'false'
            }
            
            # Make request
            response = requests.post(
                'https://www.instagram.com/accounts/web_create_ajax/attempt/',
                headers=headers,
                data=data,
                timeout=8,
                verify=False,
                allow_redirects=False
            )
            
            # Parse response
            if response.status_code == 200:
                response_text = response.text.lower()
                
                # Check for taken username
                if 'username_is_taken' in response_text or '"errors": {"username":' in response_text:
                    return False, 'taken'
                
                # Check for rate limiting
                elif 'spam' in response_text or 'feedback_required' in response_text or 'rate limit' in response_text:
                    return False, 'rate_limited'
                
                # Check for available
                elif 'account_created' in response_text or '"errors": {}' in response_text:
                    return True, 'available'
                
                # Default to taken
                else:
                    return False, 'taken'
            
            elif response.status_code == 429:  # Too Many Requests
                return False, 'rate_limited'
            
            else:
                return False, f'http_{response.status_code}'
                
        except requests.exceptions.Timeout:
            return False, 'timeout'
        except requests.exceptions.ConnectionError:
            return False, 'connection_error'
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
            message = f"""🎯 *4L USERNAME FOUND!* 🎯

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
        consecutive_errors = 0
        
        while self.running:
            try:
                # Generate username
                username = self.generate_4l_username()
                
                # Check username
                available, status = self.check_username(username)
                
                # Update statistics
                with self.lock:
                    self.stats['checked'] += 1
                    
                    if available:
                        self.stats['available'] += 1
                        self.stats['last_available'] = username
                        self.available_list.append(username)
                        
                        # Save to database
                        pattern_type = self.detect_pattern(username)
                        self.save_username(username, pattern_type)
                        
                        # Send to Telegram
                        telegram_sent = self.send_to_telegram(username)
                        
                        logger.info(f"[{worker_id:02d}] ✅ AVAILABLE: {username}")
                        
                        # Reset error counter on success
                        consecutive_errors = 0
                        
                    elif status == 'taken':
                        self.stats['taken'] += 1
                        consecutive_errors = 0
                    
                    elif status == 'rate_limited':
                        self.stats['rate_limited'] += 1
                        logger.warning(f"[{worker_id:02d}] ⚠️ RATE LIMITED: {username}")
                        consecutive_errors += 1
                        
                        # If too many rate limits, sleep longer
                        if consecutive_errors > 3:
                            sleep_time = random.uniform(10, 20)
                            logger.warning(f"Many rate limits, sleeping {sleep_time:.1f}s...")
                            time.sleep(sleep_time)
                            consecutive_errors = 0
                        else:
                            time.sleep(random.uniform(3, 8))
                    
                    else:
                        self.stats['errors'] += 1
                        logger.error(f"[{worker_id:02d}] 🔧 {status.upper()}: {username}")
                        consecutive_errors += 1
                
                # Normal delay between requests
                if status != 'rate_limited':
                    time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                consecutive_errors += 1
                time.sleep(2)
    
    def detect_pattern(self, username):
        """Detect username pattern type"""
        if any(s in username for s in SEPARATORS):
            sep_count = sum(1 for s in SEPARATORS if s in username)
            if sep_count == 1:
                return "single_separator"
            else:
                return "multiple_separators"
        else:
            return "clean"
    
    def start_hunting(self):
        """Start the username hunting"""
        self.running = True
        logger.info(f"Starting hunting session {self.session_id} with {self.threads} threads")
        
        # Start worker threads
        for i in range(self.threads):
            thread = threading.Thread(target=self.worker, args=(i,), daemon=True)
            thread.start()
            self.workers.append(thread)
        
        # Start stats updater thread
        stats_thread = threading.Thread(target=self.stats_updater, daemon=True)
        stats_thread.start()
        
        # Start Telegram updates thread
        telegram_thread = threading.Thread(target=self.telegram_updater, daemon=True)
        telegram_thread.start()
        
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
        
        cursor.execute('''
            UPDATE hunting_sessions 
            SET status = 'stopped', end_time = CURRENT_TIMESTAMP 
            WHERE session_id = ?
        ''', (self.session_id,))
        
        conn.commit()
        conn.close()
        
        return True
    
    def stats_updater(self):
        """Update stats in database periodically"""
        while self.running:
            time.sleep(30)  # Update every 30 seconds
            self.update_stats()
    
    def telegram_updater(self):
        """Send periodic updates to Telegram"""
        last_update = time.time()
        
        while self.running:
            time.sleep(60)  # Send update every minute
            
            if not self.running:
                break
            
            elapsed = time.time() - self.stats['start_time']
            speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
            
            stats_message = f"""
📊 *HUNTING STATS - Update*

⏱️ *Running:* {elapsed:.0f}s
🔍 *Checked:* {self.stats['checked']:,}
✅ *Available:* {self.stats['available']:,}
❌ *Taken:* {self.stats['taken']:,}
⚠️ *Rate Limited:* {self.stats['rate_limited']:,}
🔧 *Errors:* {self.stats['errors']:,}

⚡ *Speed:* {speed:.1f} checks/sec
🎯 *Success Rate:* {(self.stats['available']/max(1, self.stats['checked'])*100):.2f}%

📈 *Last Available:* `{self.stats['last_available'] or 'None'}`
🏷️ *Session ID:* `{self.session_id}`

🔄 *Status:* Running...
"""
            
            try:
                bot.send_message(self.chat_id, stats_message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to send stats update: {e}")
    
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
            'last_available': self.stats['last_available'],
            'available_list': self.available_list[-10:]  # Last 10 available
        }

# ========== EXISTING CODE (InstagramAppealAPI, IntegrityChecker, etc.) ==========
# [Keep all existing code from the previous bot for appeal functionality]
# [IntegrityChecker, InstagramAppealAPI, InstagramClient, DatabaseManager classes remain unchanged]
# [Appeal-related functions remain unchanged]

# ========== NEW HUNTING COMMANDS ==========
@bot.message_handler(commands=['hunt'])
def start_hunting(message):
    """Start 4L username hunting"""
    chat_id = message.chat.id
    
    # Check if already hunting
    if chat_id in hunting_sessions and hunting_sessions[chat_id].running:
        bot.reply_to(message, "⚠️ You already have an active hunting session! Use /stophunt to stop it.")
        return
    
    # Ask for configuration
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('🚀 Fast (8 threads)', '⚡ Medium (5 threads)', '🐢 Slow (3 threads)', '❌ Cancel')
    
    bot.send_message(
        chat_id,
        "🎯 *4L USERNAME HUNTER*\n\n"
        "This will search for available 4-character Instagram usernames.\n\n"
        "*Select hunting speed:*\n"
        "• 🚀 Fast - 8 threads (fastest, more rate limits)\n"
        "• ⚡ Medium - 5 threads (balanced)\n"
        "• 🐢 Slow - 3 threads (safer, fewer rate limits)\n\n"
        "*Features:*\n"
        "• Auto Telegram notifications for finds\n"
        "• Live stats every minute\n"
        "• Database backup\n"
        "• Rate limit handling\n\n"
        "Press /stophunt to stop anytime.",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_hunt_speed)

def process_hunt_speed(message):
    """Process hunting speed selection"""
    chat_id = message.chat.id
    choice = message.text.strip()
    
    if choice == '❌ Cancel':
        bot.send_message(chat_id, "❌ Hunting cancelled.", reply_markup=types.ReplyKeyboardRemove())
        return
    
    # Map choice to thread count
    speed_map = {
        '🚀 fast (8 threads)': 8,
        '⚡ medium (5 threads)': 5,
        '🐢 slow (3 threads)': 3
    }
    
    threads = speed_map.get(choice.lower(), 5)
    
    # Remove keyboard
    bot.send_message(chat_id, "Setting up hunter...", reply_markup=types.ReplyKeyboardRemove())
    
    # Create hunter instance
    hunter = UsernameHunter(chat_id)
    hunter.threads = threads
    
    # Start hunting
    if hunter.start_hunting():
        hunting_sessions[chat_id] = hunter
        
        # Send confirmation
        bot.send_message(
            chat_id,
            f"✅ *HUNTING STARTED!*\n\n"
            f"🔧 *Config:* {threads} threads\n"
            f"🎯 *Target:* 4L Usernames\n"
            f"🆔 *Session:* `{hunter.session_id}`\n"
            f"📊 *Updates:* Every minute\n"
            f"🔔 *Alerts:* On for available usernames\n\n"
            f"*You will receive:*\n"
            f"1. Immediate alerts for finds\n"
            f"2. Stats updates every minute\n"
            f"3. Database backup of all finds\n\n"
            f"Use /stophunt to stop hunting.",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start hunting session.")

@bot.message_handler(commands=['stophunt'])
def stop_hunting(message):
    """Stop username hunting"""
    chat_id = message.chat.id
    
    if chat_id not in hunting_sessions or not hunting_sessions[chat_id].running:
        bot.reply_to(message, "❌ No active hunting session found.")
        return
    
    hunter = hunting_sessions[chat_id]
    
    # Stop hunting
    if hunter.stop_hunting():
        # Get final stats
        stats = hunter.get_stats()
        
        # Send final report
        final_message = f"""
🛑 *HUNTING STOPPED*

📊 *Final Statistics:*

⏱️ *Duration:* {stats['elapsed']:.0f}s
🔍 *Total Checked:* {stats['checked']:,}
✅ *Available Found:* {stats['available']:,}
❌ *Taken:* {stats['taken']:,}
⚠️ *Rate Limited:* {stats['rate_limited']:,}
🔧 *Errors:* {stats['errors']:,}

⚡ *Average Speed:* {stats['speed']:.1f} checks/sec
🎯 *Success Rate:* {stats['success_rate']:.2f}%

🏷️ *Session ID:* `{stats['session_id']}`

💾 *All found usernames saved to database.*
📁 *You can view them with /myhunts*

Thanks for hunting! 🎯
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        
        # Clean up
        del hunting_sessions[chat_id]
        
    else:
        bot.reply_to(message, "❌ Failed to stop hunting session.")

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

⏱️ *Running:* {stats['elapsed']:.0f}s
🔍 *Checked:* {stats['checked']:,}
✅ *Available:* {stats['available']:,}
❌ *Taken:* {stats['taken']:,}
⚠️ *Rate Limited:* {stats['rate_limited']:,}
🔧 *Errors:* {stats['errors']:,}

⚡ *Speed:* {stats['speed']:.1f} checks/sec
🎯 *Success Rate:* {stats['success_rate']:.2f}%

📈 *Last 10 Available:*
"""
    
    if stats['available_list']:
        for username in stats['available_list']:
            stats_message += f"• `{username}`\n"
    else:
        stats_message += "None yet\n"
    
    stats_message += f"\n🏷️ *Session ID:* `{stats['session_id']}`"
    stats_message += f"\n🔄 *Status:* {'✅ Running' if stats['running'] else '❌ Stopped'}"
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['myhunts'])
def show_my_hunts(message):
    """Show user's hunting history"""
    chat_id = message.chat.id
    
    conn = sqlite3.connect('instagram_bot.db')
    cursor = conn.cursor()
    
    # Get hunting sessions
    cursor.execute('''
        SELECT session_id, start_time, end_time, status, checked, available, 
               taken, rate_limited, errors, average_speed
        FROM hunting_sessions 
        WHERE chat_id = ?
        ORDER BY start_time DESC
        LIMIT 10
    ''', (chat_id,))
    
    sessions = cursor.fetchall()
    
    if not sessions:
        bot.reply_to(message, "📭 No hunting sessions found. Start with /hunt")
        conn.close()
        return
    
    response = "📊 *YOUR HUNTING HISTORY*\n\n"
    
    for session in sessions:
        (session_id, start_time, end_time, status, checked, available, 
         taken, rate_limited, errors, avg_speed) = session
        
        # Format times
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        start_str = start_dt.strftime('%b %d, %H:%M')
        
        duration = "Running"
        if end_time:
            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
            duration_sec = (end_dt - start_dt).total_seconds()
            duration = f"{duration_sec:.0f}s"
        
        status_emoji = "🟢" if status == 'running' else "🔴" if status == 'stopped' else "🟡"
        success_rate = (available / checked * 100) if checked > 0 else 0
        
        response += f"""
{status_emoji} *Session:* `{session_id}`
├── Started: {start_str}
├── Duration: {duration}
├── Checked: {checked:,}
├── Available: {available:,}
├── Success: {success_rate:.2f}%
└── Speed: {avg_speed:.1f}/s

"""
    
    # Get total found usernames
    cursor.execute('''
        SELECT COUNT(DISTINCT username) FROM found_usernames 
        WHERE session_id IN (SELECT session_id FROM hunting_sessions WHERE chat_id = ?)
    ''', (chat_id,))
    
    total_found = cursor.fetchone()[0]
    
    response += f"\n📈 *Total Found Usernames:* {total_found:,}"
    response += f"\n💾 *All usernames saved to database*"
    
    conn.close()
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['found'])
def show_found_usernames(message):
    """Show recently found usernames"""
    chat_id = message.chat.id
    
    conn = sqlite3.connect('instagram_bot.db')
    cursor = conn.cursor()
    
    # Get recent found usernames
    cursor.execute('''
        SELECT f.username, f.found_at, f.pattern_type, h.session_id
        FROM found_usernames f
        JOIN hunting_sessions h ON f.session_id = h.session_id
        WHERE h.chat_id = ?
        ORDER BY f.found_at DESC
        LIMIT 20
    ''', (chat_id,))
    
    usernames = cursor.fetchall()
    
    if not usernames:
        bot.reply_to(message, "📭 No usernames found yet. Start hunting with /hunt")
        conn.close()
        return
    
    response = "🎯 *RECENTLY FOUND USERNAMES*\n\n"
    
    for username, found_at, pattern_type, session_id in usernames:
        found_dt = datetime.strptime(found_at, '%Y-%m-%d %H:%M:%S')
        time_str = found_dt.strftime('%H:%M')
        
        pattern_emoji = {
            'clean': '🔤',
            'single_separator': '🔡',
            'multiple_separators': '🔣'
        }.get(pattern_type, '❓')
        
        response += f"{pattern_emoji} `{username}` - {time_str}\n"
    
    # Get stats
    cursor.execute('''
        SELECT COUNT(*) FROM found_usernames f
        JOIN hunting_sessions h ON f.session_id = h.session_id
        WHERE h.chat_id = ?
    ''', (chat_id,))
    
    total_found = cursor.fetchone()[0]
    
    response += f"\n📊 *Total Found:* {total_found:,} usernames"
    response += f"\n💾 *All usernames are saved in database*"
    
    conn.close()
    
    bot.reply_to(message, response, parse_mode='Markdown')

# ========== EXISTING COMMANDS (Keep all existing appeal commands) ==========
# [All existing commands from the previous bot remain unchanged]
# [start, help, appeal, mystatus, checkappeal, integrity, reset, etc.]

# ========== UPDATED START COMMAND ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Welcome message with both features"""
    welcome_text = """
⚡ *MEGA INSTAGRAM BOT v5.0* ⚡
*Account Recovery + 4L Username Hunter*

🚀 *DUAL SYSTEM:*
1. **Instagram Account Recovery** - Real appeal APIs
2. **4L Username Hunter** - Find available 4-character usernames

🎯 *HUNTING FEATURES:*
• Real-time 4L username checking
• Multi-threaded (3-8 threads)
• Telegram alerts for finds
• Live stats every minute
• Database backup
• Rate limit bypass
• Pattern detection

🔐 *RECOVERY FEATURES:*
• Official Instagram Appeals
• Multi-Method Submission
• Live Status Checks
• Integrity Verification
• Smart Password Reset

🔧 *HUNTING COMMANDS:*
/hunt - Start 4L username hunting
/stophunt - Stop hunting session
/huntstats - Live hunting statistics
/myhunts - View hunting history
/found - Show found usernames

📋 *RECOVERY COMMANDS:*
/appeal - Submit Instagram appeal
/mystatus - Check appeal status
/integrity - Account integrity check
/reset - Password reset
/checkappeal - Check specific appeal

⚡ *QUICK START:*
1. /hunt - Start finding 4L usernames
2. /appeal - Recover suspended account
3. Check /help for complete guide

⚠️ *Important:*
• Hunting runs in background
• Auto-saves all finds
• Instant Telegram alerts
• Stop anytime with /stophunt

*Ready to hunt 4L usernames? Use /hunt now!*
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# ========== FLASK ENDPOINTS ==========
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "Mega Instagram Bot v5.0",
        "version": "5.0",
        "features": [
            "real_instagram_appeals",
            "4l_username_hunting",
            "multi_threaded_hunter",
            "telegram_alerts",
            "database_backup"
        ],
        "active_hunters": len([h for h in hunting_sessions.values() if h.running]),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "bot_running": True,
        "hunting_active": len([h for h in hunting_sessions.values() if h.running]),
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/huntstats/<chat_id>')
def get_hunt_stats(chat_id):
    """API endpoint to get hunting stats"""
    if chat_id in hunting_sessions:
        hunter = hunting_sessions[chat_id]
        return jsonify(hunter.get_stats())
    else:
        return jsonify({"error": "No active hunting session"}), 404

# ========== BOT RUNNER ==========
def run_telegram_bot():
    print("🤖 Starting Mega Instagram Bot v5.0...")
    print(f"🔑 Token: {BOT_TOKEN[:10]}...")
    print(f"🎯 Features: Recovery + 4L Username Hunting")
    print(f"📊 Active Hunters: {len([h for h in hunting_sessions.values() if h.running])}")
    print("=" * 70)
    
    while True:
        try:
            bot.polling(non_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Bot polling error: {e}")
            time.sleep(5)
            continue

def run_flask_server():
    print(f"🌐 Starting Flask server on port {BOT_PORT}")
    app.run(
        host='0.0.0.0', 
        port=BOT_PORT, 
        debug=False, 
        use_reloader=False,
        threaded=True
    )

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
            logger.info(f"Cleaned up stopped hunter for {chat_id}")

def main():
    print("=" * 70)
    print("🚀 MEGA INSTAGRAM BOT v5.0 - RECOVERY + 4L HUNTER")
    print("=" * 70)
    print(f"🔑 Token: {BOT_TOKEN[:10]}...")
    print(f"📡 Port: {BOT_PORT}")
    print(f"🏓 Health: http://localhost:{BOT_PORT}/health")
    print("=" * 70)
    print("🎯 4L HUNTING FEATURES:")
    print("• Real-time username checking")
    print("• Multi-threaded (3-8 threads)")
    print("• Telegram alerts for finds")
    print("• Live stats every minute")
    print("• Database backup")
    print("• Rate limit handling")
    print("=" * 70)
    print("🔐 RECOVERY FEATURES:")
    print("• Instagram Web Form Appeals")
    print("• Mobile App API Integration")
    print("• Business Account Support")
    print("• Real-Time Status Tracking")
    print("=" * 70)
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_hunters, daemon=True)
    cleanup_thread.start()
    
    # Start Flask
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    time.sleep(2)
    
    # Start Telegram bot
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    print("✅ Bot started with DUAL functionality!")
    print("🎯 Use /hunt to start 4L username hunting")
    print("🔐 Use /appeal for account recovery")
    print("=" * 70)
    
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

if __name__ == '__main__':
    main()
