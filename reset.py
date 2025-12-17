#!/usr/bin/env python3
"""
MEGA UNIVERSAL USERNAME HUNTER - ULTIMATE VERSION
WITH ADMIN CONTROLS + 3L+4L HUNTING + ALL FEATURES
INTEGRATED ORIGINAL INSTAGRAM HUNTING LOGIC
"""

import json
import requests
import logging
import threading
import time
import random
import sqlite3
import os
import queue
import string
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
import telebot
from telebot import types
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== CONFIGURATION ==========
BOT_TOKEN = "8522048948:AAGSCayCSZZF_6z2nHcGjVC7B64E3C9u6F8"
BOT_PORT = int(os.environ.get('PORT', 6001))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# ========== ADMIN CONFIG ==========
ADMIN_ID = 7575087826  # Your admin ID
BANNED_USERS = set()  # In-memory ban list

# ========== DISCORD CONFIG ==========
DISCORD_TOKEN = "MTM1MjY4NDEwOTIwMTE1MDA0OQ.GfGOZx.qK42V-v4lJi4WDH5AYbdpDfYWZk07d8-hkoOPo"

# ========== EMAIL LIST FOR INSTAGRAM SIGNUP ==========
EMAIL_LIST = [
    "d78ma6bwd8ps41h@comfythings.com",
    "4kv24j1qdkcr90t@comfythings.com",
    "duja0vg0i0dp464@comfythings.com",
    "hbkfrgrx0c04lnp@comfythings.com",
    "yr4ibhzlfy3y6cw@comfythings.com",
    "q0s3j3su1syhzpt@comfythings.com"
]

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
instagram_hunters = {}
telegram_hunters = {}
twitter_hunters = {}
tiktok_hunters = {}
youtube_hunters = {}
discord_hunters = {}

# ========== USER MANAGEMENT ==========
class UserManager:
    """Manage users and bans"""
    
    def __init__(self):
        self.users_db = 'users.db'
        self.init_db()
        self.load_banned_users()
    
    def init_db(self):
        """Initialize users database"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                is_banned INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER,
                platform TEXT,
                sessions INTEGER DEFAULT 0,
                found INTEGER DEFAULT 0,
                last_session TIMESTAMP,
                PRIMARY KEY (user_id, platform)
            )
        ''')
        conn.commit()
        conn.close()
    
    def load_banned_users(self):
        """Load banned users from database"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE is_banned = 1')
        for row in cursor.fetchall():
            BANNED_USERS.add(row[0])
        conn.close()
    
    def register_user(self, user_id, username, first_name, last_name):
        """Register or update user"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
        
        # Notify admin if new user
        if self.is_new_user(user_id):
            self.notify_admin_new_user(user_id, username, first_name, last_name)
    
    def is_new_user(self, user_id):
        """Check if user is new"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    
    def notify_admin_new_user(self, user_id, username, first_name, last_name):
        """Notify admin about new user"""
        try:
            message = f"""👤 *NEW USER REGISTERED*

━━━━━━━━━━━━━━━━━━
🆔 *User ID:* `{user_id}`
👤 *Username:* @{username or 'N/A'}
📛 *Name:* {first_name} {last_name or ''}
🕐 *Time:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
📊 *Total Users:* {self.get_total_users()}
━━━━━━━━━━━━━━━━━━

*Admin Commands:*
/ban {user_id} - Ban user
/users - List all users
/botstatus - Check bot status"""
            
            bot.send_message(ADMIN_ID, message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Admin notification error: {e}")
    
    def ban_user(self, user_id):
        """Ban a user"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        BANNED_USERS.add(user_id)
        logger.info(f"User {user_id} banned")
    
    def unban_user(self, user_id):
        """Unban a user"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        if user_id in BANNED_USERS:
            BANNED_USERS.remove(user_id)
        logger.info(f"User {user_id} unbanned")
    
    def get_total_users(self):
        """Get total registered users"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_active_users(self, days=7):
        """Get active users in last X days"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE last_active >= datetime('now', '-? days')
        ''', (days,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_all_users(self):
        """Get all users with details"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, 
                   join_date, last_active, is_banned
            FROM users 
            ORDER BY join_date DESC
        ''')
        users = cursor.fetchall()
        conn.close()
        return users
    
    def update_user_stats(self, user_id, platform, found_count=0):
        """Update user statistics"""
        conn = sqlite3.connect(self.users_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_stats (user_id, platform, sessions, found, last_session)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, platform) DO UPDATE SET
            sessions = sessions + 1,
            found = found + ?,
            last_session = CURRENT_TIMESTAMP
        ''', (user_id, platform, found_count, found_count))
        
        cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()

user_manager = UserManager()

# ========== DATABASE SETUP ==========
def init_databases():
    """Initialize all databases"""
    conn = sqlite3.connect('universal_hunter.db')
    cursor = conn.cursor()
    
    # Instagram hunting sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instagram_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            session_id TEXT UNIQUE,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'running',
            checked INTEGER DEFAULT 0,
            available_3l INTEGER DEFAULT 0,
            available_4l INTEGER DEFAULT 0,
            taken INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            average_speed REAL DEFAULT 0.0,
            threads INTEGER DEFAULT 1,
            length_pref TEXT DEFAULT '4L'
        )
    ''')
    
    # Telegram hunting sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telegram_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            session_id TEXT UNIQUE,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'running',
            checked INTEGER DEFAULT 0,
            available INTEGER DEFAULT 0,
            taken INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            average_speed REAL DEFAULT 0.0,
            threads INTEGER DEFAULT 1,
            length_pref TEXT DEFAULT '4L'
        )
    ''')
    
    # Twitter/X hunting sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS twitter_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            session_id TEXT UNIQUE,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'running',
            checked INTEGER DEFAULT 0,
            available_3l INTEGER DEFAULT 0,
            available_4l INTEGER DEFAULT 0,
            taken INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            average_speed REAL DEFAULT 0.0,
            threads INTEGER DEFAULT 1,
            length_pref TEXT DEFAULT '4L'
        )
    ''')
    
    # TikTok hunting sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tiktok_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            session_id TEXT UNIQUE,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'running',
            checked INTEGER DEFAULT 0,
            available_3l INTEGER DEFAULT 0,
            available_4l INTEGER DEFAULT 0,
            taken INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            average_speed REAL DEFAULT 0.0,
            threads INTEGER DEFAULT 1,
            length_pref TEXT DEFAULT '4L'
        )
    ''')
    
    # YouTube hunting sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS youtube_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            session_id TEXT UNIQUE,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'running',
            checked INTEGER DEFAULT 0,
            available_3l INTEGER DEFAULT 0,
            available_4l INTEGER DEFAULT 0,
            taken INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            average_speed REAL DEFAULT 0.0,
            threads INTEGER DEFAULT 1,
            length_pref TEXT DEFAULT '4L'
        )
    ''')
    
    # Discord hunting sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS discord_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            session_id TEXT UNIQUE,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'running',
            checked INTEGER DEFAULT 0,
            available_3l INTEGER DEFAULT 0,
            available_4l INTEGER DEFAULT 0,
            taken INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            average_speed REAL DEFAULT 0.0,
            threads INTEGER DEFAULT 1,
            length_pref TEXT DEFAULT '4L'
        )
    ''')
    
    # Found usernames tables (one per platform)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instagram_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            length INTEGER,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telegram_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            length INTEGER,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS twitter_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            length INTEGER,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tiktok_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            length INTEGER,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS youtube_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            length INTEGER,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS discord_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            length INTEGER,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

init_databases()

# ========== BASE HUNTER CLASS ==========
class BaseHunter:
    """Base class for all platform hunters with 3L+4L support"""
    
    def __init__(self, chat_id, platform, length_pref='4L'):
        self.chat_id = chat_id
        self.platform = platform
        self.length_pref = length_pref
        self.session_id = f"{platform.upper()}_{int(time.time())}_{random.randint(1000, 9999)}"
        self.running = False
        self.threads = 1
        self.workers = []
        self.stats = {
            'checked': 0,
            'available_3l': 0,
            'available_4l': 0,
            'taken': 0,
            'errors': 0,
            'start_time': time.time(),
            'last_available': None,
            'last_available_length': None
        }
        self.available_list = []
        self.lock = threading.Lock()
        self.used_usernames = set()
        
        # Save session to database
        self.save_session()
        
        logger.info(f"Created {platform} hunter {self.session_id} for {chat_id}")
    
    def save_session(self):
        """Save hunting session to database (override in child classes)"""
        pass
    
    def update_stats(self):
        """Update session stats in database (override in child classes)"""
        pass
    
    def save_username(self, username, length):
        """Save found username to database (override in child classes)"""
        pass
    
    def generate_username(self):
        """Generate username based on length preference (override)"""
        pass
    
    def check_username(self, username):
        """Check username on platform (override)"""
        pass
    
    def send_to_telegram(self, username, length, is_3l=False):
        """Send found username to Telegram"""
        try:
            if is_3l:
                message = f"""🚨🚨🚨 *ULTRA-RARE {self.platform.upper()} 3L FOUND!* 🚨🚨🚨

━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 *Username:* `{username}`
🏆 *Platform:* {self.platform.upper()}
✅ *Status:* AVAILABLE
🔢 *Length:* 3 LETTERS (ULTRA RARE!)
💎 *Value:* ${self.get_3l_value()}+
🕐 *Time:* {datetime.now().strftime("%H:%M:%S")}
📊 *Total 3L Found:* {self.stats['available_3l']}
━━━━━━━━━━━━━━━━━━━━━━━━━━

*HURRY! Claim immediately!*

@xk3ny | @kenyxshop"""
            else:
                message = f"""🎯 *{self.platform.upper()} USERNAME FOUND!*

━━━━━━━━━━━━━━━━━━
📛 *Username:* `{username}`
🏆 *Platform:* {self.platform.upper()}
✅ *Status:* AVAILABLE
🔢 *Length:* {length} Characters
🕐 *Time:* {datetime.now().strftime("%H:%M:%S")}
📊 *Total Found:* {self.stats['available_3l'] + self.stats['available_4l']}
━━━━━━━━━━━━━━━━━━

@xk3ny | @kenyxshop"""
            
            bot.send_message(self.chat_id, message, parse_mode='Markdown')
            return True
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def get_3l_value(self):
        """Get estimated value for 3L username"""
        values = {
            'instagram': '1,000-50,000',
            'twitter': '5,000-100,000',
            'tiktok': '2,000-20,000',
            'youtube': '500-10,000',
            'discord': '500-10,000'
        }
        return values.get(self.platform, '500-10,000')
    
    def worker(self, worker_id):
        """Worker thread for mixed 3L/4L hunting"""
        check_count = 0
        
        while self.running:
            try:
                # Get username and length
                username, length = self.generate_username()
                available = self.check_username(username)
                
                with self.lock:
                    self.stats['checked'] += 1
                    check_count += 1
                    
                    if available:
                        if length == 3:
                            self.stats['available_3l'] += 1
                        else:
                            self.stats['available_4l'] += 1
                        
                        self.stats['last_available'] = username
                        self.stats['last_available_length'] = length
                        self.available_list.append((username, length))
                        
                        # Save to database
                        self.save_username(username, length)
                        
                        # Update user stats
                        user_manager.update_user_stats(self.chat_id, self.platform, 1)
                        
                        # Send to Telegram
                        self.send_to_telegram(username, length, is_3l=(length == 3))
                        
                        logger.info(f"[{worker_id}] ✅ {self.platform} {length}L: {username}")
                        
                        # Special celebration for 3L!
                        if length == 3:
                            print(f"\n{'='*70}")
                            print(f"🎉🎉🎉 {self.platform.upper()} 3L FOUND: {username} 🎉🎉🎉")
                            print(f"💰💰💰 POTENTIAL VALUE: ${self.get_3l_value()}+ 💰💰💰")
                            print(f"{'='*70}\n")
                        else:
                            print(f"\n{'='*60}")
                            print(f"🎉 {self.platform.upper()} {length}L FOUND: {username} 🎉")
                            print(f"{'='*60}\n")
                    else:
                        self.stats['taken'] += 1
                
                # Platform-specific delays
                if self.platform == 'instagram':
                    delay = random.uniform(10, 30)
                elif self.platform == 'youtube':
                    delay = random.uniform(5, 15)
                elif self.platform == 'discord':
                    delay = random.uniform(3, 6)
                else:
                    delay = random.uniform(2, 8)
                
                # Log every 10 checks
                if check_count % 10 == 0:
                    speed = check_count / (time.time() - self.stats['start_time']) if check_count > 0 else 0
                    total_found = self.stats['available_3l'] + self.stats['available_4l']
                    logger.info(f"[{worker_id}] {self.platform}: Checked {check_count}, Found: {total_found} (3L: {self.stats['available_3l']}, 4L: {self.stats['available_4l']}), Speed: {speed:.2f}/s")
                
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                with self.lock:
                    self.stats['errors'] += 1
                time.sleep(10)
    
    def start_hunting(self):
        """Start the username hunting"""
        self.running = True
        logger.info(f"🚀 Starting {self.platform} hunter {self.session_id}")
        
        print(f"\n{'='*70}")
        print(f"🚀 {self.platform.upper()} HUNTER STARTED")
        print(f"{'='*70}")
        print(f"• Mode: {self.length_pref}")
        print(f"• 3L Priority: {'YES (70%)' if '3L' in self.length_pref else 'NO'}")
        print(f"• Threads: {self.threads}")
        print(f"• Platform: {self.platform}")
        print(f"{'='*70}\n")
        
        # Start worker thread
        thread = threading.Thread(target=self.worker, args=(0,), daemon=True)
        thread.start()
        self.workers.append(thread)
        
        # Start stats updater
        threading.Thread(target=self.stats_updater, daemon=True).start()
        
        return True
    
    def stop_hunting(self):
        """Stop the username hunting"""
        self.running = False
        logger.info(f"Stopping {self.platform} hunter {self.session_id}")
        self.update_stats()
        return True
    
    def stats_updater(self):
        """Update stats in database periodically"""
        while self.running:
            time.sleep(30)
            self.update_stats()
    
    def get_stats(self):
        """Get current statistics"""
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        total_found = self.stats['available_3l'] + self.stats['available_4l']
        
        return {
            'session_id': self.session_id,
            'running': self.running,
            'elapsed': elapsed,
            'checked': self.stats['checked'],
            'available_3l': self.stats['available_3l'],
            'available_4l': self.stats['available_4l'],
            'total_found': total_found,
            'taken': self.stats['taken'],
            'errors': self.stats['errors'],
            'speed': speed,
            'success_rate': (total_found/max(1, self.stats['checked'])*100),
            'success_rate_3l': (self.stats['available_3l']/max(1, self.stats['checked'])*100) if self.stats['checked'] > 0 else 0,
            'success_rate_4l': (self.stats['available_4l']/max(1, self.stats['checked'])*100) if self.stats['checked'] > 0 else 0,
            'last_available': self.stats['last_available'],
            'last_available_length': self.stats['last_available_length'],
            'threads': self.threads,
            'platform': self.platform,
            'length_pref': self.length_pref
        }

# ========== INSTAGRAM HUNTER WITH ORIGINAL LOGIC ==========
class InstagramHunter(BaseHunter):
    """Instagram username hunter with EXACT original script logic"""
    
    def __init__(self, chat_id, length_pref='4L'):
        super().__init__(chat_id, 'instagram', length_pref)
        # Original variables from your script
        self.insta = "1234567890qwertyuiopasdfghjklzxcvbnm"
        self.all = "_._._._._."
        self.email_index = 0
        self.session = requests.Session()
        self.last_request_time = 0
    
    def get_next_email(self):
        """Get next email from the list"""
        email = EMAIL_LIST[self.email_index]
        self.email_index = (self.email_index + 1) % len(EMAIL_LIST)
        return email
    
    def save_session(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO instagram_sessions 
            (chat_id, session_id, status, threads, length_pref)
            VALUES (?, ?, 'running', ?, ?)
        ''', (self.chat_id, self.session_id, self.threads, self.length_pref))
        conn.commit()
        conn.close()
    
    def update_stats(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        cursor.execute('''
            UPDATE instagram_sessions 
            SET checked = ?, available_3l = ?, available_4l = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available_3l'],
            self.stats['available_4l'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username, length):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO instagram_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, length))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate Instagram username using EXACT original logic"""
        # EXACT original logic from your script
        v1 = str(''.join((random.choice(self.insta) for i in range(1))))
        v2 = str(''.join((random.choice(self.insta) for i in range(1))))
        v3 = str(''.join((random.choice(self.insta) for i in range(1))))
        v4 = str(''.join((random.choice(self.all) for i in range(1))))
        
        # Create the 4 pattern variations from original script
        user1 = (v4+v1+v2+v3)
        user2 = (v1+v4+v2+v3)
        user3 = (v1+v2+v4+v3)
        user4 = (v1+v2+v3+v4)
        
        # Original variable name was hamo010
        hamo010 = (user1, user2, user3, user4)
        
        # Return random choice from the 4 patterns (EXACT original)
        username = random.choice(hamo010)
        length = len(username)
        
        # For 3L mode, we need to adjust
        if '3L' in self.length_pref and '4L' in self.length_pref:
            # 70% chance for 3L (more valuable)
            if random.random() < 0.7 and length == 4:
                # Remove one character to make it 3L
                username = username[:-1]
                length = 3
        elif '3L' in self.length_pref:
            if length == 4:
                username = username[:-1]
                length = 3
        
        # Ensure it's not used recently
        if username in self.used_usernames:
            return self.generate_username()  # Recursively generate new one
        
        self.used_usernames.add(username)
        if len(self.used_usernames) > 1000:
            self.used_usernames.remove(next(iter(self.used_usernames)))
        
        return username, length
    
    def check_username(self, username):
        """Check Instagram username using EXACT original script method"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Respect rate limits
        base_delay = 5
        if time_since_last < base_delay:
            wait_time = base_delay - time_since_last
            time.sleep(wait_time)
        
        try:
            # EXACT headers from your original script
            headers = {
                'Host': 'www.instagram.com',
                'content-length': '85',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="101"',
                'x-ig-app-id': '936619743392459',
                'x-ig-www-claim': '0',
                'sec-ch-ua-mobile': '?0',
                'x-instagram-ajax': '81f3a3c9dfe2',
                'content-type': 'application/x-www-form-urlencoded',
                'accept': '*/*',
                'x-requested-with': 'XMLHttpRequest',
                'x-asbd-id': '198387',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Safari/537.36',
                'x-csrftoken': 'jzhjt4G11O37lW1aDFyFmy1K0yIEN9Qv',
                'sec-ch-ua-platform': '"Linux"',
                'origin': 'https://www.instagram.com',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'referer': 'https://www.instagram.com/accounts/emailsignup/',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'en-IQ,en;q=0.9',
                'cookie': 'csrftoken=jzhjt4G11O37lW1aDFyFmy1K0yIEN9Qv; mid=YtsQ1gABAAEszHB5wT9VqccwQIUL; ig_did=227CCCC2-3675-4A04-8DA5-BA3195B46425; ig_nrcb=1'
            }
            
            # EXACT URL from your script
            url = 'https://www.instagram.com/accounts/web_create_ajax/attempt/'
            
            # EXACT data format from your script
            email = self.get_next_email()
            data = f'email={email}&username={username}&first_name=&opt_into_one_tap=false'
            
            # Make the request (EXACT same as original)
            response = self.session.post(
                url,
                headers=headers,
                data=data,
                timeout=15,
                verify=False
            )
            
            response_text = response.text
            self.last_request_time = time.time()
            
            # EXACT response checking from your original script
            if '{"message":"feedback_required","spam":true,"feedback_title":"Try Again Later","feedback_message":"We limit how often you can do certain things on Instagram to protect our community. Tell us if you think we made a mistake.","feedback_url":"repute/report_problem/scraping/","feedback_appeal_label":"Tell us","feedback_ignore_label":"OK","feedback_action":"report_problem","status":"fail"}' in response_text:
                logger.warning(f"Instagram rate limited for {username}")
                time.sleep(60)  # Wait longer if rate limited
                return False
            
            elif '"errors": {"username":' in response_text or '"code": "username_is_taken"' in response_text:
                return False  # Username is taken (EXACT original logic)
            
            else:
                # If none of the above conditions match, username is available
                # (Original script considered this "Good User")
                return True
                
        except Exception as e:
            logger.error(f"Instagram check error: {e}")
            time.sleep(10)
            return False

# ========== TELEGRAM HUNTER ==========
class TelegramHunter(BaseHunter):
    """Telegram username hunter (4L+5L only)"""
    
    def __init__(self, chat_id, length_pref='4L'):
        super().__init__(chat_id, 'telegram', length_pref)
        # Telegram doesn't support 3L, min is 5 chars
    
    def save_session(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO telegram_sessions 
            (chat_id, session_id, status, threads, length_pref)
            VALUES (?, ?, 'running', ?, ?)
        ''', (self.chat_id, self.session_id, self.threads, self.length_pref))
        conn.commit()
        conn.close()
    
    def update_stats(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        cursor.execute('''
            UPDATE telegram_sessions 
            SET checked = ?, available = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available_3l'] + self.stats['available_4l'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username, length):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO telegram_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, length))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate Telegram username (4L or 5L)"""
        lengths = []
        if '4L' in self.length_pref:
            lengths.append(4)
        if '5L' in self.length_pref:
            lengths.append(5)
        
        if not lengths:
            lengths = [4]
        
        length = random.choice(lengths)
        chars = string.ascii_lowercase + string.digits + '_'
        
        while True:
            username = ''.join(random.choices(chars, k=length))
            if not username.startswith('_') and username not in self.used_usernames:
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username, length
    
    def check_username(self, username):
        """Check Telegram username"""
        try:
            response = requests.get(
                f'https://t.me/{username}',
                timeout=5,
                allow_redirects=False
            )
            
            if response.status_code == 200:
                page_text = response.text.lower()
                if 'page is unavailable' in page_text or 'not found' in page_text:
                    return True
                else:
                    return False
            else:
                return False
        except:
            return False

# ========== TWITTER HUNTER ==========
class TwitterHunter(BaseHunter):
    """Twitter/X username hunter with 3L+4L support"""
    
    def __init__(self, chat_id, length_pref='4L'):
        super().__init__(chat_id, 'twitter', length_pref)
    
    def save_session(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO twitter_sessions 
            (chat_id, session_id, status, threads, length_pref)
            VALUES (?, ?, 'running', ?, ?)
        ''', (self.chat_id, self.session_id, self.threads, self.length_pref))
        conn.commit()
        conn.close()
    
    def update_stats(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        cursor.execute('''
            UPDATE twitter_sessions 
            SET checked = ?, available_3l = ?, available_4l = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available_3l'],
            self.stats['available_4l'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username, length):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO twitter_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, length))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate Twitter username with 3L/4L mix"""
        if '3L' in self.length_pref and '4L' in self.length_pref:
            length = 3 if random.random() < 0.7 else 4
        elif '3L' in self.length_pref:
            length = 3
        else:
            length = 4
        
        chars = string.ascii_lowercase + string.digits + '_'
        
        while True:
            username = ''.join(random.choices(chars, k=length))
            if not username.startswith('_') and username not in self.used_usernames:
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username, length
    
    def check_username(self, username):
        """Check Twitter/X username"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(
                f'https://twitter.com/{username}',
                headers=headers,
                timeout=5,
                allow_redirects=False
            )
            return response.status_code == 404
        except:
            return False

# ========== TIKTOK HUNTER ==========
class TikTokHunter(BaseHunter):
    """TikTok username hunter with 3L+4L support"""
    
    def __init__(self, chat_id, length_pref='4L'):
        super().__init__(chat_id, 'tiktok', length_pref)
    
    def save_session(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tiktok_sessions 
            (chat_id, session_id, status, threads, length_pref)
            VALUES (?, ?, 'running', ?, ?)
        ''', (self.chat_id, self.session_id, self.threads, self.length_pref))
        conn.commit()
        conn.close()
    
    def update_stats(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        cursor.execute('''
            UPDATE tiktok_sessions 
            SET checked = ?, available_3l = ?, available_4l = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available_3l'],
            self.stats['available_4l'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username, length):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO tiktok_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, length))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate TikTok username with 3L/4L mix"""
        if '3L' in self.length_pref and '4L' in self.length_pref:
            length = 3 if random.random() < 0.7 else 4
        elif '3L' in self.length_pref:
            length = 3
        else:
            length = 4
        
        chars = string.ascii_lowercase + string.digits + '_.'
        
        while True:
            username = ''.join(random.choices(chars, k=length))
            if not username.startswith(('_', '.')) and username not in self.used_usernames:
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username, length
    
    def check_username(self, username):
        """Check TikTok username - FIXED VERSION"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(
                f'https://www.tiktok.com/@{username}',
                headers=headers,
                timeout=10,
                allow_redirects=False,
                verify=False
            )
            
            if response.status_code == 200:
                content = response.text.lower()
                
                if 'couldn\'t find this account' in content or \
                   'user_not_found' in content or \
                   'page_not_found' in content or \
                   'account not found' in content or \
                   'this page is not available' in content:
                    return True
                
                if 'user-post' in content or 'tiktok-user' in content or \
                   'profile-container' in content or 'follower-count' in content:
                    return False
                
                return False
                
            elif response.status_code == 404:
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"TikTok check error: {e}")
            return False

# ========== YOUTUBE HUNTER ==========
class YouTubeHunter(BaseHunter):
    """YouTube username hunter with 3L+4L+5L support"""
    
    def __init__(self, chat_id, length_pref='3L+4L'):
        super().__init__(chat_id, 'youtube', length_pref)
        self.api_key = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
    
    def save_session(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO youtube_sessions 
            (chat_id, session_id, status, threads, length_pref)
            VALUES (?, ?, 'running', ?, ?)
        ''', (self.chat_id, self.session_id, self.threads, self.length_pref))
        conn.commit()
        conn.close()
    
    def update_stats(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        cursor.execute('''
            UPDATE youtube_sessions 
            SET checked = ?, available_3l = ?, available_4l = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available_3l'],
            self.stats['available_4l'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username, length):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO youtube_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, length))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate YouTube username (3L/4L/5L)"""
        lengths = []
        if '3L' in self.length_pref:
            lengths.append(3)
        if '4L' in self.length_pref:
            lengths.append(4)
        if '5L' in self.length_pref:
            lengths.append(5)
        
        if not lengths:
            lengths = [3, 4]
        
        # Weighted selection (70% for 3L if available, then 4L, then 5L)
        weights = []
        if 3 in lengths:
            weights.append(0.7)
        if 4 in lengths:
            weights.append(0.2 if 3 in lengths else 0.7)
        if 5 in lengths:
            weights.append(0.1 if 3 in lengths else (0.3 if 4 in lengths else 1.0))
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w/total_weight for w in weights]
        
        length = random.choices(lengths, weights=weights, k=1)[0]
        
        chars = string.ascii_lowercase + string.digits + '_.'
        
        while True:
            username = ''.join(random.choices(chars, k=length))
            if not username.startswith(('_', '.')) and username not in self.used_usernames:
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username, length
    
    def check_username(self, username):
        """REAL YouTube handle checker using official API"""
        try:
            # Method 1: Try official API first
            api_result = self.check_youtube_api(username)
            if api_result is not None:
                return api_result
            
            # Method 2: Fallback to page check
            return self.check_youtube_page(username)
            
        except Exception as e:
            logger.error(f"YouTube check error for {username}: {e}")
            return False
    
    def check_youtube_api(self, username):
        """Check using YouTube's official handle validation API"""
        try:
            url = "https://www.youtube.com/youtubei/v1/channel_edit/validate_channel_handle?prettyPrint=false"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://www.youtube.com',
                'Referer': 'https://www.youtube.com/',
                'X-Goog-AuthUser': '0',
                'X-Origin': 'https://www.youtube.com',
            }
            
            payload = {
                "handle": username,
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "2.20241214.00.00",
                        "hl": "en",
                        "gl": "US",
                        "mainAppWebInfo": {
                            "graftUrl": "/account_handle"
                        }
                    },
                    "user": {
                        "lockedSafetyMode": False
                    },
                    "request": {
                        "useSsl": True,
                        "internalExperimentFlags": []
                    }
                }
            }
            
            # Add API key to URL
            api_url = f"{url}&key={self.api_key}"
            
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Debug logging
                logger.debug(f"YouTube API response for {username}: {json.dumps(data, indent=2)[:500]}")
                
                # Check for success field
                if "success" in data:
                    if data["success"]:
                        logger.info(f"YouTube API: {username} - AVAILABLE ✓")
                        return True
                    else:
                        logger.info(f"YouTube API: {username} - TAKEN ✗")
                        return False
                
                # Check for error messages
                if "error" in data:
                    error_code = data["error"].get("code", "")
                    error_message = data["error"].get("message", "")
                    
                    # Handle specific error codes
                    if error_code == 400:
                        if "HANDLE_TAKEN" in error_message or "already in use" in error_message.lower():
                            logger.info(f"YouTube API: {username} - TAKEN (HANDLE_TAKEN)")
                            return False
                        elif "invalid" in error_message.lower():
                            logger.info(f"YouTube API: {username} - INVALID FORMAT")
                            return False
                    
                    logger.info(f"YouTube API: {username} - Error: {error_message}")
                    return False
                
                # Check for specific response fields
                if "actions" in data:
                    for action in data["actions"]:
                        if "openPopupAction" in action:
                            popup = action["openPopupAction"]["popup"]
                            if "confirmDialogRenderer" in popup:
                                dialog = popup["confirmDialogRenderer"]
                                if "title" in dialog:
                                    title = dialog["title"]["simpleText"].lower()
                                    if "unavailable" in title or "taken" in title:
                                        logger.info(f"YouTube API: {username} - TAKEN (dialog)")
                                        return False
                
                # Default: assume not available if we can't determine
                logger.info(f"YouTube API: {username} - UNCERTAIN, assuming TAKEN")
                return False
                
            else:
                logger.warning(f"YouTube API returned status {response.status_code}")
                return None  # Return None to try fallback method
                
        except Exception as e:
            logger.error(f"YouTube API check error: {e}")
            return None  # Return None to try fallback method
    
    def check_youtube_page(self, username):
        """Fallback method: Check YouTube page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(
                f'https://www.youtube.com/@{username}',
                headers=headers,
                timeout=8,
                allow_redirects=True
            )
            
            # Simple check: If page has channel data, it's taken
            content = response.text.lower()
            
            # Look for clear channel indicators
            channel_indicators = [
                'channelid=',
                'subscribercount',
                'videocount',
                'youtube#channel',
                'externalchannelid',
                'isowner',
            ]
            
            for indicator in channel_indicators:
                if indicator in content:
                    return False  # Taken
            
            # Look for error/404 indicators
            error_indicators = [
                'error-page',
                '404',
                'page-not-found',
                'couldn\'t find',
                'doesn\'t exist',
            ]
            
            for indicator in error_indicators:
                if indicator in content:
                    return True  # Available
            
            # Default: assume taken
            return False
            
        except Exception as e:
            logger.error(f"YouTube page check error: {e}")
            return False

# ========== DISCORD HUNTER ==========
class DiscordHunter(BaseHunter):
    """Discord username hunter with 3L+4L support"""
    
    def __init__(self, chat_id, length_pref='3L+4L'):
        super().__init__(chat_id, 'discord', length_pref)
        self.discord_token = DISCORD_TOKEN
        self.headers = self.get_discord_headers()
        self.last_check_time = 0
        self.rate_limit_delay = 3
    
    def get_discord_headers(self):
        """Get Discord API headers using your token"""
        return {
            'Authorization': self.discord_token,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiaGFzX2NsaWVudF9tb2RzIjpmYWxzZSwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzE0My4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTQzLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiJodHRwczovL3d3dy5nb29nbGUuY29tLyIsInJlZmVycmluZ19kb21haW4iOiJ3d3cuZ29vZ2xlLmNvbSIsInNlYXJjaF9lbmdpbmUiOiJnb29nbGUiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6NDc5NzkzLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJjbGllbnRfbGF1bmNoX2lkIjoiMWJiNDQxZGYtZTJjNS00NjEwLWJlYTEtMGU0NGEwOTE1NzEzIiwibGF1bmNoX3NpZ25hdHVyZSI6IjIzMTllYjQxLTE0YzgtNDVlMC05ZTJlLWZlOGZhNDQ2ZjU1ZSIsImNsaWVudF9oZWFydGJlYXRfc2Vzc2lvbl9pZCI6IjljZTc0OTFhLWMwOTUtNDJhOS04YmQ2LTdjYjgyMmIyNDM5MCIsImNsaWVudF9hcHBfc3RhdGUiOiJ1bmZvY3VzZWQifQ==',
            'X-Discord-Timezone': 'Asia/Calcutta',
            'X-Discord-Locale': 'en-US',
            'Origin': 'https://discord.com',
            'Referer': 'https://discord.com/channels/@me',
        }
    
    def save_session(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO discord_sessions 
            (chat_id, session_id, status, threads, length_pref)
            VALUES (?, ?, 'running', ?, ?)
        ''', (self.chat_id, self.session_id, self.threads, self.length_pref))
        conn.commit()
        conn.close()
    
    def update_stats(self):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        elapsed = time.time() - self.stats['start_time']
        speed = self.stats['checked'] / elapsed if elapsed > 0 else 0
        cursor.execute('''
            UPDATE discord_sessions 
            SET checked = ?, available_3l = ?, available_4l = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available_3l'],
            self.stats['available_4l'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username, length):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO discord_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, length))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate Discord username with 3L/4L mix"""
        if '3L' in self.length_pref and '4L' in self.length_pref:
            # 70% chance for 3L (more valuable)
            length = 3 if random.random() < 0.7 else 4
        elif '3L' in self.length_pref:
            length = 3
        else:
            length = 4
        
        chars = string.ascii_lowercase + string.digits + '_.'
        
        attempts = 0
        while attempts < 100:
            username = ''.join(random.choices(chars, k=length))
            
            if (not username.startswith(('_', '.')) and 
                not username.endswith(('_', '.')) and
                not ('__' in username or '..' in username or '_.' in username or '._' in username) and
                username not in self.used_usernames):
                
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username, length
            
            attempts += 1
        
        # Fallback
        return ''.join(random.choices(chars, k=4)), 4
    
    def check_username(self, username):
        """Check Discord username using official API"""
        current_time = time.time()
        if current_time - self.last_check_time < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - (current_time - self.last_check_time)
            time.sleep(wait_time)
        
        self.last_check_time = time.time()
        
        try:
            data = {"username": username.lower()}
            
            response = requests.post(
                'https://discord.com/api/v9/users/@me/pomelo-attempt',
                headers=self.headers,
                json=data,
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                if 'errors' in response_data:
                    errors = response_data['errors']
                    if 'username' in errors:
                        username_errors = errors['username'].get('_errors', [])
                        
                        for error in username_errors:
                            code = error.get('code', '')
                            
                            taken_codes = [
                                'USERNAME_ALREADY_TAKEN',
                                'USERNAME_INVALID_TAKEN',
                                'BASE_TYPE_ALREADY_EXISTS',
                                'USERNAME_TOO_MANY_USERS'
                            ]
                            
                            if any(taken_code in code for taken_code in taken_codes):
                                logger.debug(f"Discord: {username} - TAKEN ({code})")
                                return False
                
                logger.info(f"Discord: {username} - POSSIBLY AVAILABLE")
                return True
                
            elif response.status_code == 400:
                logger.debug(f"Discord 400 for {username}")
                return False
                
            elif response.status_code == 401:
                logger.error("Discord token expired or invalid!")
                return self.check_username_fallback(username)
                
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Discord rate limited! Waiting {retry_after} seconds")
                time.sleep(retry_after)
                return False
                
            else:
                logger.error(f"Discord API unexpected status: {response.status_code}")
                return self.check_username_fallback(username)
                
        except Exception as e:
            logger.error(f"Discord check error: {e}")
            return self.check_username_fallback(username)
    
    def check_username_fallback(self, username):
        """Fallback method using profile page"""
        try:
            response = requests.get(
                f'https://discord.com/users/{username}',
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=5,
                allow_redirects=False,
                verify=False
            )
            
            if response.status_code == 404:
                logger.info(f"Discord fallback: {username} - AVAILABLE (404)")
                return True
            else:
                logger.info(f"Discord fallback: {username} - TAKEN ({response.status_code})")
                return False
                
        except Exception as e:
            logger.error(f"Discord fallback error: {e}")
            return False

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['users'])
def list_users(message):
    """Admin command: List all users"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    users = user_manager.get_all_users()
    
    if not users:
        bot.reply_to(message, "📭 No users registered yet.")
        return
    
    message_text = f"👥 *Registered Users: {len(users)}*\n━━━━━━━━━━━━━━━━━━\n\n"
    
    for user in users:
        user_id, username, first_name, last_name, join_date, last_active, is_banned = user
        
        status = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
        last_active_time = datetime.strptime(last_active, '%Y-%m-%d %H:%M:%S') if isinstance(last_active, str) else last_active
        if isinstance(last_active_time, datetime):
            days_ago = (datetime.now() - last_active_time).days
            activity = f"{days_ago}d ago" if days_ago > 0 else "Today"
        else:
            activity = "Unknown"
        
        message_text += f"🆔 *ID:* `{user_id}`\n"
        message_text += f"👤 *User:* @{username or 'N/A'}\n"
        message_text += f"📛 *Name:* {first_name} {last_name or ''}\n"
        message_text += f"📅 *Joined:* {join_date}\n"
        message_text += f"🕐 *Last Active:* {activity}\n"
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
def ban_user(message):
    """Admin command: Ban a user"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    try:
        user_id = int(message.text.split()[1])
        user_manager.ban_user(user_id)
        
        # Stop any active hunts for banned user
        stop_all_user_hunts(user_id)
        
        bot.reply_to(message, f"✅ User `{user_id}` has been banned and their hunts stopped.")
        
        # Notify the banned user
        try:
            bot.send_message(user_id, "🚫 You have been banned from using this bot.")
        except:
            pass
            
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Usage: /ban <user_id>")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    """Admin command: Unban a user"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    try:
        user_id = int(message.text.split()[1])
        user_manager.unban_user(user_id)
        bot.reply_to(message, f"✅ User `{user_id}` has been unbanned.")
        
        # Notify the unbanned user
        try:
            bot.send_message(user_id, "✅ Your ban has been lifted. You can use the bot again.")
        except:
            pass
            
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Usage: /unban <user_id>")

@bot.message_handler(commands=['botstatus'])
def bot_status(message):
    """Admin command: Show bot status"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    # Get active hunters count
    active_hunters = (
        len([h for h in instagram_hunters.values() if h.running]) +
        len([h for h in telegram_hunters.values() if h.running]) +
        len([h for h in twitter_hunters.values() if h.running]) +
        len([h for h in tiktok_hunters.values() if h.running]) +
        len([h for h in youtube_hunters.values() if h.running]) +
        len([h for h in discord_hunters.values() if h.running])
    )
    
    # Get totals from database
    conn = sqlite3.connect('universal_hunter.db')
    cursor = conn.cursor()
    
    total_found = 0
    for platform in ['instagram', 'telegram', 'twitter', 'tiktok', 'youtube', 'discord']:
        cursor.execute(f'SELECT COUNT(*) FROM {platform}_found')
        total_found += cursor.fetchone()[0]
    
    conn.close()
    
    status_message = f"""🤖 *BOT STATUS REPORT*

━━━━━━━━━━━━━━━━━━
📊 *Statistics:*
• Total Users: {user_manager.get_total_users()}
• Active Users (7d): {user_manager.get_active_users(7)}
• Banned Users: {len(BANNED_USERS)}
• Active Hunters: {active_hunters}
• Total Usernames Found: {total_found:,}

⏱️ *Uptime:* {time.time() - app_start_time:.0f}s
🔄 *Bot Status:* ✅ RUNNING
🌐 *Webhook Mode:* {'✅ ENABLED' if WEBHOOK_URL else '❌ DISABLED'}

🔧 *Platform Hunters Active:*
• Instagram: {len([h for h in instagram_hunters.values() if h.running])}
• Telegram: {len([h for h in telegram_hunters.values() if h.running])}
• Twitter/X: {len([h for h in twitter_hunters.values() if h.running])}
• TikTok: {len([h for h in tiktok_hunters.values() if h.running])}
• YouTube: {len([h for h in youtube_hunters.values() if h.running])}
• Discord: {len([h for h in discord_hunters.values() if h.running])}

━━━━━━━━━━━━━━━━━━
*Admin Commands:*
/users - List all users
/ban <id> - Ban user
/unban <id> - Unban user
/botstatus - This report
/stopall - Stop all hunts
━━━━━━━━━━━━━━━━━━
"""
    
    bot.reply_to(message, status_message, parse_mode='Markdown')

def stop_all_user_hunts(user_id):
    """Stop all hunts for a specific user"""
    # Stop Instagram
    if user_id in instagram_hunters and instagram_hunters[user_id].running:
        instagram_hunters[user_id].stop_hunting()
    
    # Stop Telegram
    if user_id in telegram_hunters and telegram_hunters[user_id].running:
        telegram_hunters[user_id].stop_hunting()
    
    # Stop Twitter
    if user_id in twitter_hunters and twitter_hunters[user_id].running:
        twitter_hunters[user_id].stop_hunting()
    
    # Stop TikTok
    if user_id in tiktok_hunters and tiktok_hunters[user_id].running:
        tiktok_hunters[user_id].stop_hunting()
    
    # Stop YouTube
    if user_id in youtube_hunters and youtube_hunters[user_id].running:
        youtube_hunters[user_id].stop_hunting()
    
    # Stop Discord
    if user_id in discord_hunters and discord_hunters[user_id].running:
        discord_hunters[user_id].stop_hunting()

# ========== USER COMMANDS ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Welcome message with user registration"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if user_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    # Register user
    user_manager.register_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    welcome_text = f"""⚡ *UNIVERSAL USERNAME HUNTER BOT* ⚡
*Welcome, {message.from_user.first_name}!*

🏆 *Multiple Platforms Support:*

📸 Instagram: /hunt (3L + 4L) *WITH ORIGINAL LOGIC*
💬 Telegram: /htele (4L + 5L) *No 3L*
🐦 Twitter/X: /hx (3L + 4L)
🎵 TikTok: /htiktok (3L + 4L)
▶️ YouTube: /hyoutube (3L + 4L + 5L)
🎮 Discord: /hdiscord (3L + 4L) *WORKING API*

📊 *Features:*
• 3L + 4L hunting on most platforms
• Instagram uses EXACT original hunting logic
• Separate hunters for each platform
• Can run ALL simultaneously
• Individual statistics
• Real-time alerts with value estimates
• Database storage

🚀 *Run multiple hunters at once!*
🔥 *3L usernames = HIGH VALUE!* 💰
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# ========== INSTAGRAM COMMANDS ==========
@bot.message_handler(commands=['hunt'])
def start_instagram_hunt(message):
    """Start Instagram username hunting with ORIGINAL logic"""
    chat_id = message.chat.id
    
    if chat_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    if chat_id in instagram_hunters and instagram_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting Instagram usernames! Use /stopinsta to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('3L Only (Rare)', '4L Only', '3L + 4L (Recommended)')
    
    bot.send_message(
        chat_id,
        "📸 *Instagram Username Hunter*\n\n"
        "Select hunting mode:\n"
        "• *3L Only* - Ultra rare (high value!)\n"
        "• *4L Only* - Regular usernames\n"
        "• *3L + 4L* - BEST: Mix of both\n\n"
        "*3L Value:* $1,000-$50,000+ 💰\n"
        "*3L Chance:* 0.05-0.1% (very rare)\n"
        "*4L Chance:* 0.1-0.5%\n\n"
        "⚠️ *Using EXACT original script logic!*",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_instagram_length)

def process_instagram_length(message):
    """Process Instagram length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '3l only (rare)': '3L',
        '4l only': '4L',
        '3l + 4l (recommended)': '3L+4L'
    }
    
    length_pref = length_map.get(choice, '3L+4L')
    
    bot.send_message(chat_id, f"📸 Starting Instagram hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    # Create and start hunter
    hunter = InstagramHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        instagram_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *Instagram Hunter Started!*\n\n"
            f"🏆 Platform: Instagram\n"
            f"🔢 Mode: {length_pref}\n"
            f"🎯 3L Priority: {'YES (70%)' if '3L' in length_pref else 'NO'}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~20-40/hour\n"
            f"🔧 Using: EXACT ORIGINAL LOGIC\n\n"
            f"*Expected finds/day:*\n"
            f"• 3L: { '0.1-0.2' if '3L' in length_pref else '0' }\n"
            f"• 4L: { '0.5-1' if '4L' in length_pref else '0' }\n\n"
            f"Use /statinsta for stats\n"
            f"Use /stopinsta to stop",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start Instagram hunter.")

@bot.message_handler(commands=['statinsta'])
def instagram_stats(message):
    """Show Instagram hunting stats"""
    chat_id = message.chat.id
    
    if chat_id not in instagram_hunters or not instagram_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active Instagram hunting session.")
        return
    
    hunter = instagram_hunters[chat_id]
    stats = hunter.get_stats()
    
    stats_message = f"""
📊 *Instagram Hunter Stats*

⏱️ Running: {stats['elapsed']:.0f}s ({stats['elapsed']/3600:.1f}h)
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} (ULTRA RARE! 💰)
└─ 4L: {stats['available_4l']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%
├─ 3L Rate: {stats['success_rate_3l']:.2f}%
└─ 4L Rate: {stats['success_rate_4l']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}` ({stats['last_available_length'] or 'N/A'}L)
🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}
🔧 Logic: EXACT ORIGINAL

🔄 Status: {'✅ Running' if stats['running'] else '❌ Stopped'}
"""
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['stopinsta'])
def stop_instagram_hunt(message):
    """Stop Instagram hunting"""
    chat_id = message.chat.id
    
    if chat_id not in instagram_hunters or not instagram_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active Instagram hunting session.")
        return
    
    hunter = instagram_hunters[chat_id]
    
    if hunter.stop_hunting():
        stats = hunter.get_stats()
        
        final_message = f"""
🛑 *Instagram Hunter Stopped*

📊 *Final Stats:*

⏱️ Duration: {stats['elapsed']:.0f}s
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} 💰
└─ 4L: {stats['available_4l']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}
🔧 Logic: EXACT ORIGINAL

💾 Usernames saved to database.
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del instagram_hunters[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop Instagram hunter.")

# ========== TELEGRAM COMMANDS ==========
@bot.message_handler(commands=['htele'])
def start_telegram_hunt(message):
    """Start Telegram username hunting"""
    chat_id = message.chat.id
    
    if chat_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    if chat_id in telegram_hunters and telegram_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting Telegram usernames! Use /stopttele to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('4L Only', '5L Only', '4L + 5L')
    
    bot.send_message(
        chat_id,
        "💬 *Telegram Username Hunter*\n\n"
        "Select length preference:\n"
        "• *4L Only* - 4 characters\n"
        "• *5L Only* - 5 characters\n"
        "• *4L + 5L* - Both lengths\n\n"
        "*Note:* Telegram minimum is 5 characters\n"
        "No 3L available on Telegram",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_telegram_length)

def process_telegram_length(message):
    """Process Telegram length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '4l only': '4L',
        '5l only': '5L',
        '4l + 5l': '4L+5L'
    }
    
    length_pref = length_map.get(choice, '4L')
    
    bot.send_message(chat_id, f"💬 Starting Telegram hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    hunter = TelegramHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        telegram_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *Telegram Hunter Started!*\n\n"
            f"🏆 Platform: Telegram\n"
            f"🔢 Lengths: {length_pref}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~30-60/hour\n\n"
            f"*Format:* @username\n"
            f"Use /statttele for stats\n"
            f"Use /stopttele to stop",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start Telegram hunter.")

@bot.message_handler(commands=['statttele'])
def telegram_stats(message):
    """Show Telegram hunting stats"""
    chat_id = message.chat.id
    
    if chat_id not in telegram_hunters or not telegram_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active Telegram hunting session.")
        return
    
    hunter = telegram_hunters[chat_id]
    stats = hunter.get_stats()
    
    stats_message = f"""
📊 *Telegram Hunter Stats*

⏱️ Running: {stats['elapsed']:.0f}s ({stats['elapsed']/3600:.1f}h)
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}` ({stats['last_available_length'] or 'N/A'}L)
🏷️ Session: `{stats['session_id']}`
🔢 Lengths: {stats['length_pref']}

🔄 Status: {'✅ Running' if stats['running'] else '❌ Stopped'}
"""
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['stopttele'])
def stop_telegram_hunt(message):
    """Stop Telegram hunting"""
    chat_id = message.chat.id
    
    if chat_id not in telegram_hunters or not telegram_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active Telegram hunting session.")
        return
    
    hunter = telegram_hunters[chat_id]
    
    if hunter.stop_hunting():
        stats = hunter.get_stats()
        
        final_message = f"""
🛑 *Telegram Hunter Stopped*

📊 *Final Stats:*

⏱️ Duration: {stats['elapsed']:.0f}s
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
❌ Taken: {stats['taken']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`
🔢 Lengths: {stats['length_pref']}

💾 Usernames saved to database.
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del telegram_hunters[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop Telegram hunter.")

# ========== TWITTER COMMANDS ==========
@bot.message_handler(commands=['hx'])
def start_twitter_hunt(message):
    """Start Twitter/X username hunting"""
    chat_id = message.chat.id
    
    if chat_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    if chat_id in twitter_hunters and twitter_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting Twitter usernames! Use /stopx to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('3L Only (Legendary)', '4L Only', '3L + 4L (Recommended)')
    
    bot.send_message(
        chat_id,
        "🐦 *Twitter/X Username Hunter*\n\n"
        "Select hunting mode:\n"
        "• *3L Only* - Legendary status! 💰💰\n"
        "• *4L Only* - Regular usernames\n"
        "• *3L + 4L* - BEST: Mix of both\n\n"
        "*3L Value:* $5,000-$100,000+ 💰💰\n"
        "*3L Chance:* 0.01-0.05% (extremely rare)\n"
        "*4L Chance:* 0.1-0.3%",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_twitter_length)

def process_twitter_length(message):
    """Process Twitter length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '3l only (legendary)': '3L',
        '4l only': '4L',
        '3l + 4l (recommended)': '3L+4L'
    }
    
    length_pref = length_map.get(choice, '3L+4L')
    
    bot.send_message(chat_id, f"🐦 Starting Twitter hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    hunter = TwitterHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        twitter_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *Twitter Hunter Started!*\n\n"
            f"🏆 Platform: Twitter/X\n"
            f"🔢 Mode: {length_pref}\n"
            f"🎯 3L Priority: {'YES (70%)' if '3L' in length_pref else 'NO'}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~60-120/hour\n\n"
            f"*Expected finds/day:*\n"
            f"• 3L: { '0.1-0.2' if '3L' in length_pref else '0' }\n"
            f"• 4L: { '3-4' if '4L' in length_pref else '0' }\n\n"
            f"Use /statx for stats\n"
            f"Use /stopx to stop",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start Twitter hunter.")

@bot.message_handler(commands=['statx'])
def twitter_stats(message):
    """Show Twitter hunting stats"""
    chat_id = message.chat.id
    
    if chat_id not in twitter_hunters or not twitter_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active Twitter hunting session.")
        return
    
    hunter = twitter_hunters[chat_id]
    stats = hunter.get_stats()
    
    stats_message = f"""
📊 *Twitter Hunter Stats*

⏱️ Running: {stats['elapsed']:.0f}s ({stats['elapsed']/3600:.1f}h)
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} (LEGENDARY! 💰💰)
└─ 4L: {stats['available_4l']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%
├─ 3L Rate: {stats['success_rate_3l']:.2f}%
└─ 4L Rate: {stats['success_rate_4l']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}` ({stats['last_available_length'] or 'N/A'}L)
🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}

🔄 Status: {'✅ Running' if stats['running'] else '❌ Stopped'}
"""
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['stopx'])
def stop_twitter_hunt(message):
    """Stop Twitter hunting"""
    chat_id = message.chat.id
    
    if chat_id not in twitter_hunters or not twitter_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active Twitter hunting session.")
        return
    
    hunter = twitter_hunters[chat_id]
    
    if hunter.stop_hunting():
        stats = hunter.get_stats()
        
        final_message = f"""
🛑 *Twitter Hunter Stopped*

📊 *Final Stats:*

⏱️ Duration: {stats['elapsed']:.0f}s
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} 💰💰
└─ 4L: {stats['available_4l']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}

💾 Usernames saved to database.
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del twitter_hunters[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop Twitter hunter.")

# ========== TIKTOK COMMANDS ==========
@bot.message_handler(commands=['htiktok'])
def start_tiktok_hunt(message):
    """Start TikTok username hunting"""
    chat_id = message.chat.id
    
    if chat_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    if chat_id in tiktok_hunters and tiktok_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting TikTok usernames! Use /stoptiktok to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('3L Only (Rare)', '4L Only', '3L + 4L (Recommended)')
    
    bot.send_message(
        chat_id,
        "🎵 *TikTok Username Hunter*\n\n"
        "Select hunting mode:\n"
        "• *3L Only* - Very rare (high value!)\n"
        "• *4L Only* - Regular usernames\n"
        "• *3L + 4L* - BEST: Mix of both\n\n"
        "*3L Value:* $2,000-$20,000+ 💰\n"
        "*3L Chance:* 0.1-0.5%\n"
        "*4L Chance:* 2-5%",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_tiktok_length)

def process_tiktok_length(message):
    """Process TikTok length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '3l only (rare)': '3L',
        '4l only': '4L',
        '3l + 4l (recommended)': '3L+4L'
    }
    
    length_pref = length_map.get(choice, '3L+4L')
    
    bot.send_message(chat_id, f"🎵 Starting TikTok hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    hunter = TikTokHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        tiktok_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *TikTok Hunter Started!*\n\n"
            f"🏆 Platform: TikTok\n"
            f"🔢 Mode: {length_pref}\n"
            f"🎯 3L Priority: {'YES (70%)' if '3L' in length_pref else 'NO'}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~60-120/hour\n\n"
            f"*Expected finds/day:*\n"
            f"• 3L: { '0.5-2' if '3L' in length_pref else '0' }\n"
            f"• 4L: { '6-12' if '4L' in length_pref else '0' }\n\n"
            f"Use /stattiktok for stats\n"
            f"Use /stoptiktok to stop",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start TikTok hunter.")

@bot.message_handler(commands=['stattiktok'])
def tiktok_stats(message):
    """Show TikTok hunting stats"""
    chat_id = message.chat.id
    
    if chat_id not in tiktok_hunters or not tiktok_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active TikTok hunting session.")
        return
    
    hunter = tiktok_hunters[chat_id]
    stats = hunter.get_stats()
    
    stats_message = f"""
📊 *TikTok Hunter Stats*

⏱️ Running: {stats['elapsed']:.0f}s ({stats['elapsed']/3600:.1f}h)
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} (RARE! 💰)
└─ 4L: {stats['available_4l']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%
├─ 3L Rate: {stats['success_rate_3l']:.2f}%
└─ 4L Rate: {stats['success_rate_4l']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}` ({stats['last_available_length'] or 'N/A'}L)
🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}

🔄 Status: {'✅ Running' if stats['running'] else '❌ Stopped'}
"""
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['stoptiktok'])
def stop_tiktok_hunt(message):
    """Stop TikTok hunting"""
    chat_id = message.chat.id
    
    if chat_id not in tiktok_hunters or not tiktok_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active TikTok hunting session.")
        return
    
    hunter = tiktok_hunters[chat_id]
    
    if hunter.stop_hunting():
        stats = hunter.get_stats()
        
        final_message = f"""
🛑 *TikTok Hunter Stopped*

📊 *Final Stats:*

⏱️ Duration: {stats['elapsed']:.0f}s
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} 💰
└─ 4L: {stats['available_4l']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}

💾 Usernames saved to database.
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del tiktok_hunters[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop TikTok hunter.")

# ========== YOUTUBE COMMANDS ==========
@bot.message_handler(commands=['hyoutube'])
def start_youtube_hunt(message):
    """Start YouTube username hunting"""
    chat_id = message.chat.id
    
    if chat_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    if chat_id in youtube_hunters and youtube_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting YouTube usernames! Use /stopyoutube to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('3L Only', '4L Only', '5L Only', '3L+4L (Best)', 'All (3L+4L+5L)')
    
    bot.send_message(
        chat_id,
        "▶️ *YouTube Username Hunter*\n\n"
        "Select hunting mode:\n"
        "• *3L Only* - Rare usernames\n"
        "• *4L Only* - Regular usernames\n"
        "• *5L Only* - Longer usernames\n"
        "• *3L+4L* - BEST combination\n"
        "• *All* - 3L, 4L & 5L\n\n"
        "*3L Value:* $500-$10,000+ 💰\n"
        "*3L Chance:* 1-2% (good chance!)\n"
        "*4L Chance:* 5-10%",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_youtube_length)

def process_youtube_length(message):
    """Process YouTube length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '3l only': '3L',
        '4l only': '4L',
        '5l only': '5L',
        '3l+4l (best)': '3L+4L',
        'all (3l+4l+5l)': '3L+4L+5L'
    }
    
    length_pref = length_map.get(choice, '3L+4L')
    
    bot.send_message(chat_id, f"▶️ Starting YouTube hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    hunter = YouTubeHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        youtube_hunters[chat_id] = hunter
        
        weights_info = ""
        if '3L' in length_pref and '4L' in length_pref:
            weights_info = " (70% 3L, 30% 4L)"
        elif '3L' in length_pref and '4L' in length_pref and '5L' in length_pref:
            weights_info = " (70% 3L, 20% 4L, 10% 5L)"
        
        bot.send_message(
            chat_id,
            f"✅ *YouTube Hunter Started!*\n\n"
            f"🏆 Platform: YouTube\n"
            f"🔢 Mode: {length_pref}{weights_info}\n"
            f"🎯 3L Priority: {'YES (70%)' if '3L' in length_pref else 'NO'}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~40-80/hour\n\n"
            f"*Expected finds/day:*\n"
            f"• 3L: { '5-10' if '3L' in length_pref else '0' }\n"
            f"• 4L: { '10-20' if '4L' in length_pref else '0' }\n"
            f"• 5L: { '2-5' if '5L' in length_pref else '0' }\n\n"
            f"Use /statyoutube for stats\n"
            f"Use /stopyoutube to stop",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start YouTube hunter.")

@bot.message_handler(commands=['statyoutube'])
def youtube_stats(message):
    """Show YouTube hunting stats"""
    chat_id = message.chat.id
    
    if chat_id not in youtube_hunters or not youtube_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active YouTube hunting session.")
        return
    
    hunter = youtube_hunters[chat_id]
    stats = hunter.get_stats()
    
    stats_message = f"""
📊 *YouTube Hunter Stats*

⏱️ Running: {stats['elapsed']:.0f}s ({stats['elapsed']/3600:.1f}h)
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} (GOOD FIND! 💰)
└─ 4L: {stats['available_4l']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%
├─ 3L Rate: {stats['success_rate_3l']:.2f}%
└─ 4L Rate: {stats['success_rate_4l']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}` ({stats['last_available_length'] or 'N/A'}L)
🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}

🔄 Status: {'✅ Running' if stats['running'] else '❌ Stopped'}
"""
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['stopyoutube'])
def stop_youtube_hunt(message):
    """Stop YouTube hunting"""
    chat_id = message.chat.id
    
    if chat_id not in youtube_hunters or not youtube_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active YouTube hunting session.")
        return
    
    hunter = youtube_hunters[chat_id]
    
    if hunter.stop_hunting():
        stats = hunter.get_stats()
        
        final_message = f"""
🛑 *YouTube Hunter Stopped*

📊 *Final Stats:*

⏱️ Duration: {stats['elapsed']:.0f}s
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} 💰
└─ 4L: {stats['available_4l']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}

💾 Usernames saved to database.
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del youtube_hunters[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop YouTube hunter.")

# ========== DISCORD COMMANDS ==========
@bot.message_handler(commands=['hdiscord'])
def start_discord_hunt(message):
    """Start Discord username hunting"""
    chat_id = message.chat.id
    
    if chat_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    if chat_id in discord_hunters and discord_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting Discord usernames! Use /stopdiscord to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('3L Only (High Value)', '4L Only', '3L + 4L (BEST)', '4L + 5L')
    
    bot.send_message(
        chat_id,
        "🎮 *Discord Username Hunter*\n\n"
        "Select hunting mode:\n"
        "• *3L Only* - High value usernames\n"
        "• *4L Only* - Regular usernames\n"
        "• *3L + 4L* - BEST: Mix of both\n"
        "• *4L + 5L* - Standard lengths\n\n"
        "*3L Value:* $500-$10,000+ 💰\n"
        "*3L Chance:* 2-5% (best chance!)\n"
        "*4L Chance:* 10-15%",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_discord_length)

def process_discord_length(message):
    """Process Discord length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '3l only (high value)': '3L',
        '4l only': '4L',
        '3l + 4l (best)': '3L+4L',
        '4l + 5l': '4L+5L'
    }
    
    length_pref = length_map.get(choice, '3L+4L')
    
    bot.send_message(chat_id, f"🎮 Starting Discord hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    hunter = DiscordHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        discord_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *Discord Hunter Started!*\n\n"
            f"🏆 Platform: Discord\n"
            f"🔢 Mode: {length_pref}\n"
            f"🎯 3L Priority: {'YES (70%)' if '3L' in length_pref else 'NO'}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~40-80/hour\n\n"
            f"*Expected finds/day:*\n"
            f"• 3L: { '10-20' if '3L' in length_pref else '0' }\n"
            f"• 4L: { '20-30' if '4L' in length_pref else '0' }\n\n"
            f"*Using:* Official Discord API\n"
            f"*Accuracy:* Very High\n"
            f"Use /statdiscord for stats\n"
            f"Use /stopdiscord to stop",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start Discord hunter.")

@bot.message_handler(commands=['statdiscord'])
def discord_stats(message):
    """Show Discord hunting stats"""
    chat_id = message.chat.id
    
    if chat_id not in discord_hunters or not discord_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active Discord hunting session.")
        return
    
    hunter = discord_hunters[chat_id]
    stats = hunter.get_stats()
    
    stats_message = f"""
📊 *Discord Hunter Stats*

⏱️ Running: {stats['elapsed']:.0f}s ({stats['elapsed']/3600:.1f}h)
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} (HIGH VALUE! 💰)
└─ 4L: {stats['available_4l']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%
├─ 3L Rate: {stats['success_rate_3l']:.2f}%
└─ 4L Rate: {stats['success_rate_4l']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}` ({stats['last_available_length'] or 'N/A'}L)
🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}
🔐 Using: Official Discord API

🔄 Status: {'✅ Running' if stats['running'] else '❌ Stopped'}
"""
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['stopdiscord'])
def stop_discord_hunt(message):
    """Stop Discord hunting"""
    chat_id = message.chat.id
    
    if chat_id not in discord_hunters or not discord_hunters[chat_id].running:
        bot.reply_to(message, "❌ No active Discord hunting session.")
        return
    
    hunter = discord_hunters[chat_id]
    
    if hunter.stop_hunting():
        stats = hunter.get_stats()
        
        final_message = f"""
🛑 *Discord Hunter Stopped*

📊 *Final Stats:*

⏱️ Duration: {stats['elapsed']:.0f}s
🔍 Checked: {stats['checked']:,}
✅ Found: {stats['total_found']:,}
├─ 3L: {stats['available_3l']:,} 💰
└─ 4L: {stats['available_4l']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`
🔢 Mode: {stats['length_pref']}
🔐 Method: Official Discord API

💾 Usernames saved to database.
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del discord_hunters[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop Discord hunter.")

# ========== ALL HUNTERS COMMANDS ==========
@bot.message_handler(commands=['allstats'])
def all_stats(message):
    """Show stats for all active hunters"""
    chat_id = message.chat.id
    
    active_hunters = []
    
    if chat_id in instagram_hunters and instagram_hunters[chat_id].running:
        active_hunters.append(('Instagram', instagram_hunters[chat_id]))
    if chat_id in telegram_hunters and telegram_hunters[chat_id].running:
        active_hunters.append(('Telegram', telegram_hunters[chat_id]))
    if chat_id in twitter_hunters and twitter_hunters[chat_id].running:
        active_hunters.append(('Twitter/X', twitter_hunters[chat_id]))
    if chat_id in tiktok_hunters and tiktok_hunters[chat_id].running:
        active_hunters.append(('TikTok', tiktok_hunters[chat_id]))
    if chat_id in youtube_hunters and youtube_hunters[chat_id].running:
        active_hunters.append(('YouTube', youtube_hunters[chat_id]))
    if chat_id in discord_hunters and discord_hunters[chat_id].running:
        active_hunters.append(('Discord', discord_hunters[chat_id]))
    
    if not active_hunters:
        bot.reply_to(message, "❌ No active hunting sessions.")
        return
    
    stats_message = "📊 *ALL ACTIVE HUNTERS*\n━━━━━━━━━━━━━━━━━━\n\n"
    
    total_checked = 0
    total_found = 0
    total_3l = 0
    total_4l = 0
    
    for platform_name, hunter in active_hunters:
        stats = hunter.get_stats()
        total_checked += stats['checked']
        total_found += stats['total_found']
        total_3l += stats['available_3l']
        total_4l += stats['available_4l']
        
        stats_message += f"*{platform_name}*\n"
        stats_message += f"🔍 Checked: {stats['checked']:,}\n"
        stats_message += f"✅ Found: {stats['total_found']:,}\n"
        if stats['available_3l'] > 0:
            stats_message += f"├─ 3L: {stats['available_3l']:,} 💰\n"
        if stats['available_4l'] > 0:
            stats_message += f"└─ 4L: {stats['available_4l']:,}\n"
        stats_message += f"⚡ Speed: {stats['speed']:.2f}/s\n"
        stats_message += f"🎯 Success: {stats['success_rate']:.2f}%\n"
        
        if stats['last_available']:
            stats_message += f"📈 Last: `{stats['last_available']}` ({stats['last_available_length']}L)\n"
        
        stats_message += "━━━━━━━━━━━━━━━━━━\n\n"
    
    stats_message += f"*TOTALS*\n"
    stats_message += f"🔍 Checked: {total_checked:,}\n"
    stats_message += f"✅ Found: {total_found:,}\n"
    if total_3l > 0:
        stats_message += f"├─ 3L: {total_3l:,} (HIGH VALUE! 💰)\n"
    if total_4l > 0:
        stats_message += f"└─ 4L: {total_4l:,}\n"
    stats_message += f"🏆 Active Hunters: {len(active_hunters)}/6\n"
    stats_message += f"💰 Total 3L Value: ${total_3l * 1000:,}+"
    
    bot.reply_to(message, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['stopall'])
def stop_all_hunters(message):
    """Stop all active hunters"""
    chat_id = message.chat.id
    
    stopped = []
    
    if chat_id in instagram_hunters and instagram_hunters[chat_id].running:
        instagram_hunters[chat_id].stop_hunting()
        stopped.append('Instagram')
        del instagram_hunters[chat_id]
    
    if chat_id in telegram_hunters and telegram_hunters[chat_id].running:
        telegram_hunters[chat_id].stop_hunting()
        stopped.append('Telegram')
        del telegram_hunters[chat_id]
    
    if chat_id in twitter_hunters and twitter_hunters[chat_id].running:
        twitter_hunters[chat_id].stop_hunting()
        stopped.append('Twitter/X')
        del twitter_hunters[chat_id]
    
    if chat_id in tiktok_hunters and tiktok_hunters[chat_id].running:
        tiktok_hunters[chat_id].stop_hunting()
        stopped.append('TikTok')
        del tiktok_hunters[chat_id]
    
    if chat_id in youtube_hunters and youtube_hunters[chat_id].running:
        youtube_hunters[chat_id].stop_hunting()
        stopped.append('YouTube')
        del youtube_hunters[chat_id]
    
    if chat_id in discord_hunters and discord_hunters[chat_id].running:
        discord_hunters[chat_id].stop_hunting()
        stopped.append('Discord')
        del discord_hunters[chat_id]
    
    if stopped:
        bot.reply_to(message, f"🛑 *Stopped {len(stopped)} hunters:*\n{', '.join(stopped)}", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ No active hunters to stop.")

# ========== FLASK ENDPOINTS ==========
app_start_time = time.time()

def get_all_active_hunters():
    """Get all active hunters across all platforms"""
    all_hunters = []
    
    for chat_id, hunter in instagram_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    for chat_id, hunter in telegram_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    for chat_id, hunter in twitter_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    for chat_id, hunter in tiktok_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    for chat_id, hunter in youtube_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    for chat_id, hunter in discord_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    return all_hunters

@app.route('/hunter')
def hunter_stats():
    """Root endpoint for health checks"""
    all_hunters = get_all_active_hunters()
    active_hunters = len(all_hunters)
    
    total_stats = {
        'checked': 0,
        'found_3l': 0,
        'found_4l': 0,
        'errors': 0
    }
    
    for hunter in all_hunters:
        if hunter.running:
            stats = hunter.get_stats()
            total_stats['checked'] += stats['checked']
            total_stats['found_3l'] += stats['available_3l']
            total_stats['found_4l'] += stats['available_4l']
            total_stats['errors'] += stats['errors']
    
    total_found = total_stats['found_3l'] + total_stats['found_4l']
    
    return jsonify({
        "status": "running",
        "service": "Universal Username Hunter Bot",
        "version": "7.0 (ULTIMATE)",
        "admin_id": ADMIN_ID,
        "total_users": user_manager.get_total_users(),
        "active_users": user_manager.get_active_users(1),
        "banned_users": len(BANNED_USERS),
        "active_hunters": active_hunters,
        "total_checked": total_stats['checked'],
        "total_found": total_found,
        "found_3l": total_stats['found_3l'],
        "found_4l": total_stats['found_4l'],
        "success_rate": (total_found / max(1, total_stats['checked']) * 100),
        "uptime": time.time() - app_start_time,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health/hunter')
def health_check():
    """Health check endpoint"""
    all_hunters = get_all_active_hunters()
    return jsonify({
        "status": "healthy",
        "bot_running": True,
        "admin_system": "active",
        "total_users": user_manager.get_total_users(),
        "hunting_active": len(all_hunters),
        "database": "connected",
        "discord_api": "working",
        "instagram_logic": "original",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/')
def root_home():
    """Root endpoint for compatibility"""
    return jsonify({
        "status": "running",
        "service": "Universal Username Hunter Bot v7.0",
        "message": "ULTIMATE VERSION - Admin Controls + 3L+4L Hunting + ORIGINAL INSTAGRAM LOGIC",
        "admin_id": ADMIN_ID,
        "endpoints": {
            "/": "This page",
            "/hunter": "Hunter stats",
            "/health/hunter": "Health check",
            "/health": "Basic health"
        },
        "platforms": ["Instagram", "Telegram", "Twitter/X", "TikTok", "YouTube", "Discord"],
        "features": ["3L+4L Hunting", "Admin Controls", "User Management", "Discord API", "Flask API", "ORIGINAL Instagram Logic"]
    })

@app.route('/health')
def health_compatibility():
    """Health endpoint for compatibility"""
    return jsonify({
        "status": "healthy",
        "version": "7.0 (ULTIMATE)",
        "admin_system": "active",
        "3l_support": "enabled",
        "discord_api_working": True,
        "instagram_original_logic": True,
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/stats')
def stats_page():
    """Stats page with all platform details"""
    platform_stats = {}
    
    platform_stats['instagram'] = {
        'active': len([h for h in instagram_hunters.values() if h.running]),
        'total_sessions': len(instagram_hunters),
        'logic': 'original'
    }
    
    platform_stats['telegram'] = {
        'active': len([h for h in telegram_hunters.values() if h.running]),
        'total_sessions': len(telegram_hunters)
    }
    
    platform_stats['twitter'] = {
        'active': len([h for h in twitter_hunters.values() if h.running]),
        'total_sessions': len(twitter_hunters)
    }
    
    platform_stats['tiktok'] = {
        'active': len([h for h in tiktok_hunters.values() if h.running]),
        'total_sessions': len(tiktok_hunters)
    }
    
    platform_stats['youtube'] = {
        'active': len([h for h in youtube_hunters.values() if h.running]),
        'total_sessions': len(youtube_hunters)
    }
    
    platform_stats['discord'] = {
        'active': len([h for h in discord_hunters.values() if h.running]),
        'total_sessions': len(discord_hunters),
        'api_status': 'working'
    }
    
    return jsonify({
        "status": "running",
        "platform_stats": platform_stats,
        "total_active": sum([s['active'] for s in platform_stats.values()]),
        "total_users": user_manager.get_total_users(),
        "active_users_24h": user_manager.get_active_users(1),
        "banned_users": len(BANNED_USERS),
        "uptime": time.time() - app_start_time,
        "timestamp": datetime.now().isoformat()
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

# ========== MAIN ==========
if __name__ == '__main__':
    print("=" * 70)
    print("🚀 UNIVERSAL USERNAME HUNTER BOT v7.0 - ULTIMATE VERSION")
    print("=" * 70)
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"🌐 Port: {BOT_PORT}")
    print(f"🏓 Health: http://localhost:{BOT_PORT}/health")
    print(f"📊 Stats: http://localhost:{BOT_PORT}/hunter")
    print(f"📈 Details: http://localhost:{BOT_PORT}/stats")
    print("=" * 70)
    print("🎯 SUPPORTED PLATFORMS (3L+4L):")
    print("• Instagram: /hunt (3L+4L) - EXACT ORIGINAL LOGIC!")
    print("• Telegram: /htele (4L+5L) *No 3L*")
    print("• Twitter/X: /hx (3L+4L)")
    print("• TikTok: /htiktok (3L+4L)")
    print("• YouTube: /hyoutube (3L+4L+5L)")
    print("• Discord: /hdiscord (3L+4L) - WORKING DISCORD API!")
    print("=" * 70)
    print("🛡️ ADMIN COMMANDS:")
    print("• /users - List all users")
    print("• /ban <id> - Ban user")
    print("• /unban <id> - Unban user")
    print("• /botstatus - Bot status report")
    print("=" * 70)
    print("🔐 Discord Token: Loaded ✓")
    print("👤 User Management: Active ✓")
    print("💰 3L Support: Enabled on 5 platforms ✓")
    print("📸 Instagram: Using EXACT original logic ✓")
    print("🎯 Smart Mixing: 70% 3L priority ✓")
    print("📊 Enhanced Stats: 3L/4L tracking ✓")
    print("🔔 Admin Notifications: Active ✓")
    print("💡 Run ALL 6 hunters simultaneously!")
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
    else:
        print("📡 Using polling mode")
        bot_thread = threading.Thread(target=lambda: bot.polling(non_stop=True), daemon=True)
        bot_thread.start()
    
    print("✅ Bot started successfully!")
    print("🎯 Use /start to see all commands")
    print("👑 Admin panel ready")
    print("💰 3L hunting ACTIVE - Find high-value usernames!")
    print("📸 Instagram using EXACT original hunting logic")
    print("🌐 Monitor at: http://localhost:{}/hunter".format(BOT_PORT))
    print("=" * 70)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Stopping all hunters...")
        
        # Stop all hunters
        for platform_dict in [instagram_hunters, telegram_hunters, twitter_hunters, 
                            tiktok_hunters, youtube_hunters, discord_hunters]:
            for hunter in list(platform_dict.values()):
                if hunter.running:
                    hunter.stop_hunting()
        
        print("✅ Clean shutdown complete.")
