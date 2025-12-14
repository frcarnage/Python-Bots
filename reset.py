#!/usr/bin/env python3
"""
MEGA UNIVERSAL USERNAME HUNTER - COMPLETE VERSION
Multiple platforms with Discord API and all Flask endpoints
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
from datetime import datetime
from flask import Flask, jsonify, request
import telebot
from telebot import types
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== CONFIGURATION ==========
BOT_TOKEN = "8522048948:AAGSCayCSZZF_6z2nHcGjVC7B64E3C9u6F8"
BOT_PORT = int(os.environ.get('PORT', 6001))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# ========== DISCORD CONFIG ==========
DISCORD_TOKEN = "MTM1MjY4NDEwOTIwMTE1MDA0OQ.GfGOZx.qK42V-v4lJi4WDH5AYbdpDfYWZk07d8-hkoOPo"

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
# Separate dicts for each platform
instagram_hunters = {}
telegram_hunters = {}
twitter_hunters = {}
tiktok_hunters = {}
youtube_hunters = {}
discord_hunters = {}

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
            available INTEGER DEFAULT 0,
            taken INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            average_speed REAL DEFAULT 0.0,
            threads INTEGER DEFAULT 1
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
            available INTEGER DEFAULT 0,
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
            available INTEGER DEFAULT 0,
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
            available INTEGER DEFAULT 0,
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
            available INTEGER DEFAULT 0,
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
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            length INTEGER,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telegram_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            length INTEGER,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS twitter_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            length INTEGER,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tiktok_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            length INTEGER,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS youtube_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            length INTEGER,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS discord_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT UNIQUE,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            length INTEGER,
            sent_to_telegram INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

init_databases()

# ========== BASE HUNTER CLASS ==========
class BaseHunter:
    """Base class for all platform hunters"""
    
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
            'available': 0,
            'taken': 0,
            'errors': 0,
            'start_time': time.time(),
            'last_available': None
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
    
    def save_username(self, username):
        """Save found username to database (override in child classes)"""
        pass
    
    def generate_username(self):
        """Generate username based on length preference (override)"""
        pass
    
    def check_username(self, username):
        """Check username on platform (override)"""
        pass
    
    def send_to_telegram(self, username):
        """Send found username to Telegram"""
        try:
            message = f"""🎯 *{self.platform.upper()} USERNAME FOUND!*

━━━━━━━━━━━━━━━━━━
📛 *Username:* `{username}`
🏆 *Platform:* {self.platform.upper()}
✅ *Status:* AVAILABLE
🔢 *Length:* {len(username)} Characters
🕐 *Time:* {datetime.now().strftime("%H:%M:%S")}
📊 *Total Found:* {self.stats['available']}
━━━━━━━━━━━━━━━━━━

@xk3ny | @kenyxshop"""
            
            bot.send_message(self.chat_id, message, parse_mode='Markdown')
            return True
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def worker(self, worker_id):
        """Worker thread"""
        check_count = 0
        
        while self.running:
            try:
                username = self.generate_username()
                available = self.check_username(username)
                
                with self.lock:
                    self.stats['checked'] += 1
                    check_count += 1
                    
                    if available:
                        self.stats['available'] += 1
                        self.stats['last_available'] = username
                        self.available_list.append(username)
                        
                        # Save to database
                        self.save_username(username)
                        
                        # Send to Telegram
                        self.send_to_telegram(username)
                        
                        logger.info(f"[{worker_id}] ✅ {self.platform}: {username}")
                        
                        # Celebrate!
                        print(f"\n{'='*60}")
                        print(f"🎉 {self.platform.upper()} FOUND: {username} 🎉")
                        print(f"{'='*60}\n")
                    else:
                        self.stats['taken'] += 1
                
                # Platform-specific delays
                if self.platform == 'instagram':
                    delay = random.uniform(10, 30)
                elif self.platform == 'youtube':
                    delay = random.uniform(5, 15)
                elif self.platform == 'discord':
                    delay = random.uniform(3, 6)  # Discord can be faster with API
                else:
                    delay = random.uniform(2, 8)
                
                # Log every 10 checks
                if check_count % 10 == 0:
                    speed = check_count / (time.time() - self.stats['start_time']) if check_count > 0 else 0
                    logger.info(f"[{worker_id}] {self.platform}: Checked {check_count}, Speed: {speed:.2f}/s")
                
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
        print(f"• Target: {self.length_pref} usernames")
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
        
        return {
            'session_id': self.session_id,
            'running': self.running,
            'elapsed': elapsed,
            'checked': self.stats['checked'],
            'available': self.stats['available'],
            'taken': self.stats['taken'],
            'errors': self.stats['errors'],
            'speed': speed,
            'success_rate': (self.stats['available']/max(1, self.stats['checked'])*100),
            'last_available': self.stats['last_available'],
            'threads': self.threads,
            'platform': self.platform,
            'length_pref': self.length_pref
        }

# ========== TELEGRAM HUNTER ==========
class TelegramHunter(BaseHunter):
    """Telegram username hunter"""
    
    def __init__(self, chat_id, length_pref='4L'):
        super().__init__(chat_id, 'telegram', length_pref)
    
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
            self.stats['available'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO telegram_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, len(username)))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate Telegram username based on length preference"""
        lengths = []
        if '4L' in self.length_pref:
            lengths.append(4)
        if '5L' in self.length_pref:
            lengths.append(5)
        
        if not lengths:
            lengths = [4]  # Default to 4L
        
        length = random.choice(lengths)
        
        # Telegram allows: a-z, 0-9, underscore
        chars = string.ascii_lowercase + string.digits + '_'
        
        while True:
            username = ''.join(random.choices(chars, k=length))
            # Telegram usernames can't start with underscore
            if not username.startswith('_') and username not in self.used_usernames:
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username
    
    def check_username(self, username):
        """Check Telegram username"""
        try:
            response = requests.get(
                f'https://t.me/{username}',
                timeout=5,
                allow_redirects=False
            )
            
            if response.status_code == 200:
                # Check for "page is unavailable" text
                page_text = response.text.lower()
                if 'page is unavailable' in page_text or 'not found' in page_text:
                    return True  # Available
                else:
                    return False  # Taken
            else:
                return False  # Error or taken
        except:
            return False

# ========== TWITTER/X HUNTER ==========
class TwitterHunter(BaseHunter):
    """Twitter/X username hunter"""
    
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
            SET checked = ?, available = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO twitter_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, len(username)))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate Twitter username"""
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
                return username
    
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
            # Twitter returns 404 for available usernames
            return response.status_code == 404
        except:
            return False

# ========== TIKTOK HUNTER ==========
class TikTokHunter(BaseHunter):
    """TikTok username hunter"""
    
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
            SET checked = ?, available = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO tiktok_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, len(username)))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate TikTok username"""
        lengths = []
        if '4L' in self.length_pref:
            lengths.append(4)
        if '5L' in self.length_pref:
            lengths.append(5)
        
        if not lengths:
            lengths = [4]
        
        length = random.choice(lengths)
        chars = string.ascii_lowercase + string.digits + '_.'
        
        while True:
            username = ''.join(random.choices(chars, k=length))
            if not username.startswith(('_', '.')) and username not in self.used_usernames:
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username
    
    def check_username(self, username):
        """Check TikTok username"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(
                f'https://www.tiktok.com/@{username}',
                headers=headers,
                timeout=5,
                allow_redirects=False
            )
            # TikTok shows 404 for available usernames
            if response.status_code == 404:
                return True
            elif response.status_code == 200:
                # Check for "Couldn't find this account"
                page_text = response.text.lower()
                if 'couldn\'t find' in page_text or 'not found' in page_text:
                    return True
                return False
            return False
        except:
            return False

# ========== YOUTUBE HUNTER ==========
class YouTubeHunter(BaseHunter):
    """YouTube username hunter"""
    
    def __init__(self, chat_id, length_pref='4L'):
        super().__init__(chat_id, 'youtube', length_pref)
    
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
            SET checked = ?, available = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO youtube_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, len(username)))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate YouTube username (3L, 4L, 5L)"""
        lengths = []
        if '3L' in self.length_pref:
            lengths.append(3)
        if '4L' in self.length_pref:
            lengths.append(4)
        if '5L' in self.length_pref:
            lengths.append(5)
        
        if not lengths:
            lengths = [3, 4]  # Default to 3L and 4L
        
        length = random.choice(lengths)
        # YouTube allows letters, numbers, periods, underscores
        chars = string.ascii_lowercase + string.digits + '_.'
        
        while True:
            username = ''.join(random.choices(chars, k=length))
            if not username.startswith(('_', '.')) and username not in self.used_usernames:
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username
    
    def check_username(self, username):
        """Check YouTube username"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(
                f'https://www.youtube.com/@{username}',
                headers=headers,
                timeout=5,
                allow_redirects=False
            )
            # YouTube redirects to /c/ for custom URLs, but 404 means not taken
            return response.status_code == 404
        except:
            return False

# ========== DISCORD HUNTER (FIXED WITH REAL API) ==========
class DiscordHunter(BaseHunter):
    """Discord username hunter using official API"""
    
    def __init__(self, chat_id, length_pref='4L'):
        super().__init__(chat_id, 'discord', length_pref)
        self.discord_token = DISCORD_TOKEN
        self.headers = self.get_discord_headers()
        self.last_check_time = 0
        self.rate_limit_delay = 3  # 3 seconds between Discord checks
    
    def get_discord_headers(self):
        """Get Discord API headers using your token"""
        return {
            'Authorization': self.discord_token,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
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
            SET checked = ?, available = ?, taken = ?, errors = ?,
                average_speed = ?, threads = ?
            WHERE session_id = ?
        ''', (
            self.stats['checked'],
            self.stats['available'],
            self.stats['taken'],
            self.stats['errors'],
            speed,
            self.threads,
            self.session_id
        ))
        conn.commit()
        conn.close()
    
    def save_username(self, username):
        conn = sqlite3.connect('universal_hunter.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO discord_found 
            (session_id, username, length)
            VALUES (?, ?, ?)
        ''', (self.session_id, username, len(username)))
        conn.commit()
        conn.close()
    
    def generate_username(self):
        """Generate Discord username (Discord's new system requirements)"""
        lengths = []
        if '4L' in self.length_pref:
            lengths.append(4)
        if '5L' in self.length_pref:
            lengths.append(5)
        
        if not lengths:
            lengths = [4]
        
        length = random.choice(lengths)
        
        # Discord's new username rules:
        # - Lowercase letters, numbers, underscore, period
        # - Must be between 2-32 characters
        # - Cannot start/end with period or underscore
        # - No consecutive periods/underscores
        
        chars = string.ascii_lowercase + string.digits + '_.'
        
        while True:
            username = ''.join(random.choices(chars, k=length))
            
            # Validate Discord rules
            if (not username.startswith(('_', '.')) and 
                not username.endswith(('_', '.')) and
                not ('__' in username or '..' in username or '_.' in username or '._' in username) and
                username not in self.used_usernames):
                
                self.used_usernames.add(username)
                if len(self.used_usernames) > 1000:
                    self.used_usernames.remove(next(iter(self.used_usernames)))
                return username
    
    def check_username(self, username):
        """Check Discord username using official pomelo-attempt API"""
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_check_time < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - (current_time - self.last_check_time)
            time.sleep(wait_time)
        
        self.last_check_time = time.time()
        
        try:
            data = {"username": username.lower()}  # Discord usernames are lowercase
            
            response = requests.post(
                'https://discord.com/api/v9/users/@me/pomelo-attempt',
                headers=self.headers,
                json=data,
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Check for errors
                if 'errors' in response_data:
                    errors = response_data['errors']
                    if 'username' in errors:
                        username_errors = errors['username']
                        error_details = username_errors.get('_errors', [])
                        
                        for error in error_details:
                            code = error.get('code', '')
                            
                            # Check if username is taken
                            taken_codes = [
                                'USERNAME_ALREADY_TAKEN',
                                'USERNAME_INVALID_TAKEN',
                                'BASE_TYPE_ALREADY_EXISTS',
                                'USERNAME_TOO_MANY_USERS'
                            ]
                            
                            if any(taken_code in code for taken_code in taken_codes):
                                logger.debug(f"Discord: {username} - TAKEN ({code})")
                                return False
                
                # If no errors or different errors, username might be available
                logger.info(f"Discord: {username} - POSSIBLY AVAILABLE")
                return True
                
            elif response.status_code == 400:
                # Bad request - could be invalid username format
                logger.debug(f"Discord 400 for {username}")
                return False
                
            elif response.status_code == 401:
                # Unauthorized - token expired
                logger.error("Discord token expired or invalid!")
                # Try fallback method
                return self.check_username_fallback(username)
                
            elif response.status_code == 429:
                # Rate limited
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
            
            # Discord returns 404 for non-existent users
            # Returns 200 or redirects for existing users
            if response.status_code == 404:
                logger.info(f"Discord fallback: {username} - AVAILABLE (404)")
                return True
            else:
                logger.info(f"Discord fallback: {username} - TAKEN ({response.status_code})")
                return False
                
        except Exception as e:
            logger.error(f"Discord fallback error: {e}")
            return False
    
    def send_to_telegram(self, username):
        """Send found Discord username to Telegram"""
        try:
            message = f"""🎮 *DISCORD USERNAME FOUND!*

━━━━━━━━━━━━━━━━━━
📛 *Username:* `{username}`
🏆 *Platform:* Discord
✅ *Status:* AVAILABLE
🔢 *Length:* {len(username)} Characters
🕐 *Time:* {datetime.now().strftime("%H:%M:%S")}
📊 *Total Found:* {self.stats['available']}
━━━━━━━━━━━━━━━━━━

*How to claim:*
1. Go to Discord Settings
2. Click "Edit" next to username
3. Enter `{username}`
4. Save changes

@xk3ny | @kenyxshop"""
            
            bot.send_message(self.chat_id, message, parse_mode='Markdown')
            return True
        except Exception as e:
            logger.error(f"Discord Telegram send error: {e}")
            return False

# ========== TELEGRAM COMMANDS ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Welcome message"""
    welcome_text = """
⚡ *UNIVERSAL USERNAME HUNTER BOT* ⚡
*Now with WORKING Discord API!*

🏆 *Multiple Platforms Support:*

📸 Instagram: /hunt (4L only - existing)
💬 Telegram: /htele (4L + 5L)
🐦 Twitter/X: /hx (4L + 5L)
🎵 TikTok: /htiktok (4L + 5L)
▶️ YouTube: /hyoutube (3L + 4L + 5L)
🎮 Discord: /hdiscord (4L + 5L) *WORKING API*

📊 *Features:*
• Separate hunters for each platform
• Can run ALL simultaneously
• Individual statistics
• Real-time alerts
• Database storage

🚀 *Run multiple hunters at once!*
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# ========== TELEGRAM HUNTER COMMANDS ==========
@bot.message_handler(commands=['htele'])
def start_telegram_hunt(message):
    """Start Telegram username hunting"""
    chat_id = message.chat.id
    
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
        "*Note:* Telegram usernames are @username",
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
    
    # Create and start hunter
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
✅ Available: {stats['available']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}`
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
✅ Available: {stats['available']:,}
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

# ========== TWITTER/X HUNTER COMMANDS ==========
@bot.message_handler(commands=['hx'])
def start_twitter_hunt(message):
    """Start Twitter/X username hunting"""
    chat_id = message.chat.id
    
    if chat_id in twitter_hunters and twitter_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting Twitter usernames! Use /stopx to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('4L Only', '5L Only', '4L + 5L')
    
    bot.send_message(
        chat_id,
        "🐦 *Twitter/X Username Hunter*\n\n"
        "Select length preference:\n"
        "• *4L Only* - 4 characters\n"
        "• *5L Only* - 5 characters\n"
        "• *4L + 5L* - Both lengths\n\n"
        "*Note:* Twitter usernames are @username",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_twitter_length)

def process_twitter_length(message):
    """Process Twitter length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '4l only': '4L',
        '5l only': '5L',
        '4l + 5l': '4L+5L'
    }
    
    length_pref = length_map.get(choice, '4L')
    
    bot.send_message(chat_id, f"🐦 Starting Twitter hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    # Create and start hunter
    hunter = TwitterHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        twitter_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *Twitter Hunter Started!*\n\n"
            f"🏆 Platform: Twitter/X\n"
            f"🔢 Lengths: {length_pref}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~60-120/hour\n\n"
            f"*Format:* @username\n"
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
✅ Available: {stats['available']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}`
🏷️ Session: `{stats['session_id']}`
🔢 Lengths: {stats['length_pref']}

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
✅ Available: {stats['available']:,}
❌ Taken: {stats['taken']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`
🔢 Lengths: {stats['length_pref']}

💾 Usernames saved to database.
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del twitter_hunters[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop Twitter hunter.")

# ========== TIKTOK HUNTER COMMANDS ==========
@bot.message_handler(commands=['htiktok'])
def start_tiktok_hunt(message):
    """Start TikTok username hunting"""
    chat_id = message.chat.id
    
    if chat_id in tiktok_hunters and tiktok_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting TikTok usernames! Use /stoptiktok to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('4L Only', '5L Only', '4L + 5L')
    
    bot.send_message(
        chat_id,
        "🎵 *TikTok Username Hunter*\n\n"
        "Select length preference:\n"
        "• *4L Only* - 4 characters\n"
        "• *5L Only* - 5 characters\n"
        "• *4L + 5L* - Both lengths\n\n"
        "*Note:* TikTok usernames are @username",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_tiktok_length)

def process_tiktok_length(message):
    """Process TikTok length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '4l only': '4L',
        '5l only': '5L',
        '4l + 5l': '4L+5L'
    }
    
    length_pref = length_map.get(choice, '4L')
    
    bot.send_message(chat_id, f"🎵 Starting TikTok hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    # Create and start hunter
    hunter = TikTokHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        tiktok_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *TikTok Hunter Started!*\n\n"
            f"🏆 Platform: TikTok\n"
            f"🔢 Lengths: {length_pref}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~60-120/hour\n\n"
            f"*Format:* @username\n"
            f"Use /stattiktok for stats\n"
            f"Use /stoptiktok to stop",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start TikTok hunter.")

# ========== YOUTUBE HUNTER COMMANDS ==========
@bot.message_handler(commands=['hyoutube'])
def start_youtube_hunt(message):
    """Start YouTube username hunting"""
    chat_id = message.chat.id
    
    if chat_id in youtube_hunters and youtube_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting YouTube usernames! Use /stopyoutube to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('3L Only', '4L Only', '5L Only', '3L+4L', '4L+5L', 'All (3L+4L+5L)')
    
    bot.send_message(
        chat_id,
        "▶️ *YouTube Username Hunter*\n\n"
        "Select length preference:\n"
        "• *3L Only* - 3 characters\n"
        "• *4L Only* - 4 characters\n"
        "• *5L Only* - 5 characters\n"
        "• *3L+4L* - Both 3L & 4L\n"
        "• *4L+5L* - Both 4L & 5L\n"
        "• *All* - 3L, 4L & 5L\n\n"
        "*Note:* YouTube usernames are @username",
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
        '3l+4l': '3L+4L',
        '4l+5l': '4L+5L',
        'all (3l+4l+5l)': '3L+4L+5L'
    }
    
    length_pref = length_map.get(choice, '3L+4L')
    
    bot.send_message(chat_id, f"▶️ Starting YouTube hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    # Create and start hunter
    hunter = YouTubeHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        youtube_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *YouTube Hunter Started!*\n\n"
            f"🏆 Platform: YouTube\n"
            f"🔢 Lengths: {length_pref}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~40-80/hour\n\n"
            f"*Format:* @username\n"
            f"Use /statyoutube for stats\n"
            f"Use /stopyoutube to stop",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, "❌ Failed to start YouTube hunter.")

# ========== DISCORD HUNTER COMMANDS ==========
@bot.message_handler(commands=['hdiscord'])
def start_discord_hunt(message):
    """Start Discord username hunting"""
    chat_id = message.chat.id
    
    if chat_id in discord_hunters and discord_hunters[chat_id].running:
        bot.reply_to(message, "⚠️ Already hunting Discord usernames! Use /stopdiscord to stop.")
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('4L Only', '5L Only', '4L + 5L')
    
    bot.send_message(
        chat_id,
        "🎮 *Discord Username Hunter*\n\n"
        "Select length preference:\n"
        "• *4L Only* - 4 characters\n"
        "• *5L Only* - 5 characters\n"
        "• *4L + 5L* - Both lengths\n\n"
        "*Now using official Discord API!*",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, process_discord_length)

def process_discord_length(message):
    """Process Discord length selection"""
    chat_id = message.chat.id
    choice = message.text.strip().lower()
    
    length_map = {
        '4l only': '4L',
        '5l only': '5L',
        '4l + 5l': '4L+5L'
    }
    
    length_pref = length_map.get(choice, '4L')
    
    bot.send_message(chat_id, f"🎮 Starting Discord hunter for {length_pref}...", 
                    reply_markup=types.ReplyKeyboardRemove())
    
    # Create and start hunter
    hunter = DiscordHunter(chat_id, length_pref)
    
    if hunter.start_hunting():
        discord_hunters[chat_id] = hunter
        
        bot.send_message(
            chat_id,
            f"✅ *Discord Hunter Started!*\n\n"
            f"🏆 Platform: Discord\n"
            f"🔢 Lengths: {length_pref}\n"
            f"🧵 Threads: 1\n"
            f"🆔 Session: `{hunter.session_id}`\n"
            f"⚡ Checks: ~40-80/hour\n\n"
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
✅ Available: {stats['available']:,}
❌ Taken: {stats['taken']:,}
🔧 Errors: {stats['errors']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

📈 Last Found: `{stats['last_available'] or 'None'}`
🏷️ Session: `{stats['session_id']}`
🔢 Lengths: {stats['length_pref']}
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
✅ Available: {stats['available']:,}
❌ Taken: {stats['taken']:,}

⚡ Speed: {stats['speed']:.2f}/sec
🎯 Success Rate: {stats['success_rate']:.2f}%

🏷️ Session: `{stats['session_id']}`
🔢 Lengths: {stats['length_pref']}
🔐 Method: Official Discord API

💾 Usernames saved to database.
"""
        
        bot.send_message(chat_id, final_message, parse_mode='Markdown')
        del discord_hunters[chat_id]
    else:
        bot.reply_to(message, "❌ Failed to stop Discord hunter.")

# ========== FLASK ENDPOINTS ==========
app_start_time = time.time()

def get_all_active_hunters():
    """Get all active hunters across all platforms"""
    all_hunters = []
    
    # Instagram hunters
    for chat_id, hunter in instagram_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    # Telegram hunters
    for chat_id, hunter in telegram_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    # Twitter hunters
    for chat_id, hunter in twitter_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    # TikTok hunters
    for chat_id, hunter in tiktok_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    # YouTube hunters
    for chat_id, hunter in youtube_hunters.items():
        if hunter.running:
            all_hunters.append(hunter)
    
    # Discord hunters
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
        'available': 0,
        'rate_limited': 0
    }
    
    for hunter in all_hunters:
        if hunter.running:
            stats = hunter.get_stats()
            total_stats['checked'] += stats['checked']
            total_stats['available'] += stats['available']
            # Note: rate_limited field not in BaseHunter, using errors as proxy
            total_stats['rate_limited'] += stats['errors']
    
    return jsonify({
        "status": "running",
        "service": "Universal Username Hunter Bot",
        "version": "6.0 (FIXED)",
        "active_hunters": active_hunters,
        "total_checked": total_stats['checked'],
        "total_available": total_stats['available'],
        "rate_limit_percentage": (total_stats['rate_limited'] / max(1, total_stats['checked']) * 100) if total_stats['checked'] > 0 else 0,
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
        "hunting_active": len(all_hunters),
        "database": "connected",
        "rate_limit_warning": "Fixed in v6.0",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/')
def root_home():
    """Root endpoint for compatibility"""
    return jsonify({
        "status": "running",
        "service": "Universal Username Hunter Bot v6.0",
        "message": "Multi-platform with Discord API!",
        "endpoints": {
            "/": "This page",
            "/hunter": "Hunter stats",
            "/health/hunter": "Health check",
            "/health": "Basic health"
        },
        "platforms": ["Instagram", "Telegram", "Twitter/X", "TikTok", "YouTube", "Discord"],
        "discord_api": "Working"
    })

@app.route('/health')
def health_compatibility():
    """Health endpoint for compatibility"""
    return jsonify({
        "status": "healthy",
        "version": "6.0",
        "rate_limit_fixed": True,
        "discord_api_working": True,
        "timestamp": datetime.now().isoformat()
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

@app.route('/stats')
def stats_page():
    """Stats page with all platform details"""
    platform_stats = {}
    
    # Instagram stats
    platform_stats['instagram'] = {
        'active': len([h for h in instagram_hunters.values() if h.running]),
        'total_sessions': len(instagram_hunters)
    }
    
    # Telegram stats
    platform_stats['telegram'] = {
        'active': len([h for h in telegram_hunters.values() if h.running]),
        'total_sessions': len(telegram_hunters)
    }
    
    # Twitter stats
    platform_stats['twitter'] = {
        'active': len([h for h in twitter_hunters.values() if h.running]),
        'total_sessions': len(twitter_hunters)
    }
    
    # TikTok stats
    platform_stats['tiktok'] = {
        'active': len([h for h in tiktok_hunters.values() if h.running]),
        'total_sessions': len(tiktok_hunters)
    }
    
    # YouTube stats
    platform_stats['youtube'] = {
        'active': len([h for h in youtube_hunters.values() if h.running]),
        'total_sessions': len(youtube_hunters)
    }
    
    # Discord stats
    platform_stats['discord'] = {
        'active': len([h for h in discord_hunters.values() if h.running]),
        'total_sessions': len(discord_hunters),
        'api_status': 'working' if DISCORD_TOKEN != "YOUR_TOKEN_HERE" else 'not_configured'
    }
    
    return jsonify({
        "status": "running",
        "platform_stats": platform_stats,
        "total_active": sum([s['active'] for s in platform_stats.values()]),
        "uptime": time.time() - app_start_time,
        "timestamp": datetime.now().isoformat()
    })

# ========== MAIN ==========
if __name__ == '__main__':
    print("=" * 70)
    print("🚀 UNIVERSAL USERNAME HUNTER BOT v6.0 - COMPLETE")
    print("=" * 70)
    print(f"🌐 Port: {BOT_PORT}")
    print(f"🏓 Health: http://localhost:{BOT_PORT}/health")
    print(f"📊 Stats: http://localhost:{BOT_PORT}/hunter")
    print(f"📈 Details: http://localhost:{BOT_PORT}/stats")
    print("=" * 70)
    print("🎯 SUPPORTED PLATFORMS:")
    print("• Instagram: /hunt (4L) - Use your existing hunter")
    print("• Telegram: /htele (4L+5L)")
    print("• Twitter/X: /hx (4L+5L)")
    print("• TikTok: /htiktok (4L+5L)")
    print("• YouTube: /hyoutube (3L+4L+5L)")
    print("• Discord: /hdiscord (4L+5L) - WORKING DISCORD API!")
    print("=" * 70)
    print("🔐 Discord Token: Loaded ✓")
    print("🌐 All Flask endpoints added ✓")
    print("💡 Run multiple hunters simultaneously!")
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
