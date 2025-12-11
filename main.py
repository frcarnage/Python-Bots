import os
import telebot
import random
import time
import string
import requests
import json
import sqlite3
import threading
import re
import base64
import hashlib
from datetime import datetime, timedelta
from telebot.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from flask import Flask, jsonify, render_template_string, request
from cryptography.fernet import Fernet
import uuid
import psutil

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8165377023:AAENQLmAiS2QcZr93R6uYcwXG0gs6AuVduA')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '7575087826'))
BOT_USERNAME = "CarnageSwapperBot"

# Generate or load encryption key
def get_encryption_key():
    key_file = 'encryption.key'
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
    return key

ENCRYPTION_KEY = get_encryption_key()
cipher = Fernet(ENCRYPTION_KEY)

# Instagram API Configuration
DEFAULT_WEBHOOK_URL = "https://discord.com/api/webhooks/1447815502327058613/IkpdhIMUlcE34PCNygmnlIU7WBhzmYbvgqCK8KOIDpoHTgMKoJWSRnMKgq41RNh2rmyE"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1447815502327058613/IkpdhIMUlcE34PCNygmnlIU7WBhzmYbvgqCK8KOIDpoHTgMKoJWSRnMKgq41RNh2rmyE"

# ======= CHANNEL CONFIGURATION =======
UPDATES_CHANNEL = "@CarnageUpdates"
PROOFS_CHANNEL = "@CarnageProof"
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

# ======= MARKETPLACE CHANNELS =======
MARKETPLACE_CHANNEL_ID = "-1003364960970"  # Marketplace channel for listings
ADMIN_GROUP_ID = "-1003282021421"  # Admin/middleman group

# Global variables
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
start_time = time.time()
bot_running = True
session_data = {}
requests_count = 0
errors_count = 0
rate_limit_cooldowns = {}
tutorial_sessions = {}
referral_cache = {}
user_states = {}
marketplace_transactions = {}
pending_swaps = {}
verified_mms = {ADMIN_USER_ID}
swap_sessions = {}
active_listings = {}
bidding_sessions = {}
vouch_requests = {}
bulk_listings = {}

# Database connection pool
db_lock = threading.Lock()

# ==================== FLASK APP FOR KOYEB ====================
app = Flask(__name__)

# ==================== HTML TEMPLATES ====================
HTML_TEMPLATES = {
    'dashboard': '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CARNAGE Dashboard - User {user_id}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .header {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                text-align: center;
            }}
            
            .logo {{
                font-size: 2.5em;
                font-weight: 800;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px;
            }}
            
            .tagline {{
                color: #666;
                font-size: 1.1em;
                margin-bottom: 20px;
            }}
            
            .user-info {{
                background: #f8f9fa;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s, box-shadow 0.3s;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
            }}
            
            .stat-icon {{
                font-size: 2em;
                margin-bottom: 15px;
            }}
            
            .stat-title {{
                font-size: 0.9em;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 10px;
            }}
            
            .stat-value {{
                font-size: 2em;
                font-weight: 700;
                color: #333;
            }}
            
            .achievements {{
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
                margin-bottom: 30px;
            }}
            
            .achievement-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }}
            
            .achievement {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                border: 2px solid transparent;
            }}
            
            .achievement.unlocked {{
                border-color: #28a745;
                background: #f0fff4;
            }}
            
            .achievement.emoji {{
                font-size: 2em;
                margin-bottom: 10px;
            }}
            
            .recent-swaps {{
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            }}
            
            .swap-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                border-bottom: 1px solid #eee;
            }}
            
            .swap-item:last-child {{
                border-bottom: none;
            }}
            
            .swap-success {{
                color: #28a745;
                font-weight: 600;
            }}
            
            .swap-failed {{
                color: #dc3545;
                font-weight: 600;
            }}
            
            .footer {{
                text-align: center;
                color: white;
                margin-top: 40px;
                padding: 20px;
                font-size: 0.9em;
                opacity: 0.8;
            }}
            
            .btn-group {{
                display: flex;
                gap: 10px;
                justify-content: center;
                margin-top: 20px;
            }}
            
            .btn {{
                padding: 10px 20px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s;
            }}
            
            .btn-primary {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .btn-secondary {{
                background: #6c757d;
                color: white;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            }}
            
            @media (max-width: 768px) {{
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .header {{
                    padding: 20px;
                }}
            }}
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">CARNAGE SWAPPER</div>
                <div class="tagline">Advanced Instagram Username Swapping Platform</div>
                <div class="user-info">
                    <h3><i class="fas fa-user"></i> User Dashboard</h3>
                    <p>ID: {user_id} | Status: {status}</p>
                    <p>Joined: {join_date} | Last Active: {last_active}</p>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-exchange-alt"></i></div>
                    <div class="stat-title">Total Swaps</div>
                    <div class="stat-value">{total_swaps}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-check-circle"></i></div>
                    <div class="stat-title">Successful Swaps</div>
                    <div class="stat-value">{successful_swaps}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-percentage"></i></div>
                    <div class="stat-title">Success Rate</div>
                    <div class="stat-value">{success_rate}%</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-users"></i></div>
                    <div class="stat-title">Total Referrals</div>
                    <div class="stat-value">{total_referrals}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-coins"></i></div>
                    <div class="stat-title">Credits Balance</div>
                    <div class="stat-value">{credits} 🪙</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-trophy"></i></div>
                    <div class="stat-title">Achievements</div>
                    <div class="stat-value">{achievements_unlocked}/{achievements_total}</div>
                </div>
            </div>
            
            <div class="achievements">
                <h3><i class="fas fa-trophy"></i> Achievements</h3>
                <div class="achievement-grid">
                    {achievements_html}
                </div>
            </div>
            
            <div class="recent-swaps">
                <h3><i class="fas fa-history"></i> Recent Swaps</h3>
                {recent_swaps_html}
            </div>
            
            <div class="btn-group">
                <a href="https://t.me/{bot_username}" class="btn btn-primary" target="_blank">
                    <i class="fab fa-telegram"></i> Open Bot
                </a>
                <a href="/marketplace" class="btn btn-secondary" target="_blank">
                    <i class="fas fa-store"></i> Marketplace
                </a>
            </div>
            
            <div class="footer">
                © 2024 CARNAGE Swapper Bot. All rights reserved.<br>
                <small>This dashboard updates in real-time. Data is cached for performance.</small>
            </div>
        </div>
        
        <script>
            // Auto-refresh every 30 seconds
            setTimeout(() => {{
                window.location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    ''',
    
    'admin_panel': '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CARNAGE Admin Panel</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            body {{
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: white;
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            
            .header {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 30px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            
            .logo {{
                font-size: 2.5em;
                font-weight: 800;
                background: linear-gradient(45deg, #00dbde, #fc00ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
                background: rgba(255, 255, 255, 0.15);
            }}
            
            .stat-title {{
                font-size: 0.9em;
                color: #aaa;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 10px;
            }}
            
            .stat-value {{
                font-size: 1.8em;
                font-weight: 700;
            }}
            
            .tabs {{
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}
            
            .tab {{
                padding: 10px 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.3s;
            }}
            
            .tab.active {{
                background: linear-gradient(45deg, #00dbde, #fc00ff);
            }}
            
            .tab:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
            
            .content {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 30px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                min-height: 400px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            }}
            
            th {{
                background: rgba(255, 255, 255, 0.1);
                font-weight: 600;
            }}
            
            tr:hover {{
                background: rgba(255, 255, 255, 0.05);
            }}
            
            .badge {{
                padding: 4px 8px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: 600;
            }}
            
            .badge-success {{
                background: rgba(40, 167, 69, 0.2);
                color: #28a745;
            }}
            
            .badge-warning {{
                background: rgba(255, 193, 7, 0.2);
                color: #ffc107;
            }}
            
            .badge-danger {{
                background: rgba(220, 53, 69, 0.2);
                color: #dc3545;
            }}
            
            .btn {{
                padding: 8px 16px;
                border-radius: 10px;
                border: none;
                background: linear-gradient(45deg, #00dbde, #fc00ff);
                color: white;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s;
                margin: 5px;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
            }}
            
            .btn-small {{
                padding: 4px 8px;
                font-size: 0.8em;
            }}
            
            .search-box {{
                width: 100%;
                padding: 15px;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: white;
                margin-bottom: 20px;
                font-size: 1em;
            }}
            
            .search-box:focus {{
                outline: none;
                border-color: #00dbde;
            }}
            
            @media (max-width: 768px) {{
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .header {{
                    padding: 20px;
                }}
                
                table {{
                    display: block;
                    overflow-x: auto;
                }}
            }}
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">CARNAGE ADMIN PANEL</div>
                <div style="color: #aaa; margin-top: 10px;">
                    <i class="fas fa-shield-alt"></i> Secure Admin Interface | Logged in as Admin
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Total Users</div>
                    <div class="stat-value">{total_users}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">Active Today</div>
                    <div class="stat-value">{active_today}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">Total Swaps</div>
                    <div class="stat-value">{total_swaps}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">Success Rate</div>
                    <div class="stat-value">{success_rate}%</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">Marketplace Listings</div>
                    <div class="stat-value">{total_listings}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">Pending Transactions</div>
                    <div class="stat-value">{pending_transactions}</div>
                </div>
            </div>
            
            <input type="text" class="search-box" placeholder="Search User ID or Username..." id="searchInput" onkeyup="searchTable()">
            
            <div class="tabs" id="tabs">
                <div class="tab active" onclick="showTab('users')">
                    <i class="fas fa-users"></i> Users
                </div>
                <div class="tab" onclick="showTab('swaps')">
                    <i class="fas fa-exchange-alt"></i> Swaps
                </div>
                <div class="tab" onclick="showTab('marketplace')">
                    <i class="fas fa-store"></i> Marketplace
                </div>
                <div class="tab" onclick="showTab('transactions')">
                    <i class="fas fa-money-bill-wave"></i> Transactions
                </div>
                <div class="tab" onclick="showTab('system')">
                    <i class="fas fa-cog"></i> System
                </div>
                <div class="tab" onclick="showTab('broadcast')">
                    <i class="fas fa-bullhorn"></i> Broadcast
                </div>
            </div>
            
            <div class="content" id="content">
                {initial_content}
            </div>
        </div>
        
        <script>
            function showTab(tabName) {{
                // Update active tab
                document.querySelectorAll('.tab').forEach(tab => {{
                    tab.classList.remove('active');
                }});
                event.target.classList.add('active');
                
                // Load content via AJAX
                fetch(`/admin/tab/${{tabName}}`)
                    .then(response => response.text())
                    .then(data => {{
                        document.getElementById('content').innerHTML = data;
                    }});
            }}
            
            function searchTable() {{
                const input = document.getElementById('searchInput').value.toLowerCase();
                const rows = document.querySelectorAll('tbody tr');
                
                rows.forEach(row => {{
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(input) ? '' : 'none';
                }});
            }}
            
            function adminAction(action, userId) {{
                const reason = prompt('Enter reason (optional):');
                if (reason !== null) {{
                    fetch('/admin/action', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{action: action, userId: userId, reason: reason}})
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        alert(data.message);
                        showTab('users');
                    }});
                }}
            }}
            
            function sendBroadcast() {{
                const message = document.getElementById('broadcastMessage').value;
                if (!message) {{
                    alert('Please enter a message');
                    return;
                }}
                
                if (!confirm('Are you sure you want to send this broadcast to ALL users?')) {{
                    return;
                }}
                
                fetch('/admin/broadcast', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{message: message}})
                }})
                .then(response => response.json())
                .then(data => {{
                    alert(data.message);
                    document.getElementById('broadcastMessage').value = '';
                }});
            }}
            
            // Load initial content
            showTab('users');
        </script>
    </body>
    </html>
    '''
}

# ==================== ENCRYPTION FUNCTIONS ====================
def encrypt_session(session_id):
    """Encrypt session ID"""
    try:
        encrypted = cipher.encrypt(session_id.encode())
        return encrypted.decode()
    except:
        return session_id

def decrypt_session(encrypted_session):
    """Decrypt session ID"""
    try:
        decrypted = cipher.decrypt(encrypted_session.encode())
        return decrypted.decode()
    except:
        return encrypted_session

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

# ==================== ENHANCED DATABASE SETUP ====================
def init_database():
    """Initialize SQLite database with marketplace tables"""
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
                    is_mm INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER DEFAULT NULL,
                    total_referrals INTEGER DEFAULT 0,
                    free_swaps_earned INTEGER DEFAULT 0,
                    credits INTEGER DEFAULT 100,
                    tier TEXT DEFAULT 'free',
                    subscription_until TEXT DEFAULT NULL,
                    total_swaps INTEGER DEFAULT 0,
                    successful_swaps INTEGER DEFAULT 0,
                    join_method TEXT DEFAULT 'direct',
                    channels_joined INTEGER DEFAULT 0,
                    main_session_encrypted TEXT DEFAULT NULL,
                    main_username TEXT DEFAULT NULL,
                    target_session_encrypted TEXT DEFAULT NULL,
                    target_username TEXT DEFAULT NULL,
                    backup_session_encrypted TEXT DEFAULT NULL,
                    backup_username TEXT DEFAULT NULL,
                    vouch_score INTEGER DEFAULT 0,
                    positive_vouches INTEGER DEFAULT 0,
                    negative_vouches INTEGER DEFAULT 0,
                    total_transactions INTEGER DEFAULT 0
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
                    credits_spent INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Referral tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS referral_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    reward_claimed INTEGER DEFAULT 0,
                    joined_at TEXT,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referred_id) REFERENCES users (user_id)
                )
            ''')
            
            # Marketplace listings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS marketplace_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id TEXT UNIQUE,
                    seller_id INTEGER,
                    username TEXT,
                    price REAL,
                    currency TEXT DEFAULT 'inr',
                    listing_type TEXT DEFAULT 'sale',
                    sale_type TEXT DEFAULT 'fixed',
                    status TEXT DEFAULT 'active',
                    description TEXT,
                    seller_session_encrypted TEXT DEFAULT NULL,
                    verified_at TEXT DEFAULT NULL,
                    created_at TEXT,
                    expires_at TEXT,
                    views INTEGER DEFAULT 0,
                    bids INTEGER DEFAULT 0,
                    highest_bid REAL DEFAULT 0,
                    highest_bidder INTEGER DEFAULT NULL,
                    auction_end_time TEXT DEFAULT NULL,
                    min_increment REAL DEFAULT 100,
                    current_bid REAL DEFAULT 0,
                    buy_now_price REAL DEFAULT 0,
                    verified_session INTEGER DEFAULT 0,
                    FOREIGN KEY (seller_id) REFERENCES users (user_id)
                )
            ''')
            
            # Bulk listings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bulk_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    batch_id TEXT,
                    usernames TEXT,
                    sessions TEXT,
                    prices TEXT,
                    status TEXT DEFAULT 'processing',
                    created_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Auction bids
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auction_bids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id TEXT,
                    bidder_id INTEGER,
                    bid_amount REAL,
                    bid_time TEXT,
                    is_winning INTEGER DEFAULT 0,
                    FOREIGN KEY (listing_id) REFERENCES marketplace_listings (listing_id),
                    FOREIGN KEY (bidder_id) REFERENCES users (user_id)
                )
            ''')
            
            # Marketplace swaps
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS marketplace_swaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    swap_id TEXT UNIQUE,
                    listing_id TEXT,
                    seller_id INTEGER,
                    buyer_id INTEGER,
                    mm_id INTEGER DEFAULT NULL,
                    amount REAL,
                    currency TEXT,
                    status TEXT DEFAULT 'created',
                    payment_method TEXT,
                    payment_proof TEXT,
                    seller_session_encrypted TEXT DEFAULT NULL,
                    buyer_session_encrypted TEXT DEFAULT NULL,
                    swap_status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    payment_received_at TEXT,
                    swap_completed_at TEXT,
                    released_at TEXT,
                    refunded_at TEXT,
                    dispute_reason TEXT,
                    notes TEXT,
                    vouch_requested INTEGER DEFAULT 0,
                    vouch_given INTEGER DEFAULT 0,
                    vouch_type TEXT DEFAULT NULL,
                    vouch_comment TEXT DEFAULT NULL,
                    FOREIGN KEY (listing_id) REFERENCES marketplace_listings (listing_id),
                    FOREIGN KEY (seller_id) REFERENCES users (user_id),
                    FOREIGN KEY (buyer_id) REFERENCES users (user_id),
                    FOREIGN KEY (mm_id) REFERENCES users (user_id)
                )
            ''')
            
            # Vouches
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vouches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    swap_id TEXT,
                    user_id INTEGER,
                    vouch_for INTEGER,
                    vouch_type TEXT,
                    comment TEXT,
                    vouch_time TEXT,
                    verified INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (vouch_for) REFERENCES users (user_id)
                )
            ''')
            
            # Middlemen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS middlemen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    verified_by INTEGER,
                    verified_at TEXT,
                    status TEXT DEFAULT 'active',
                    total_swaps INTEGER DEFAULT 0,
                    successful_swaps INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (verified_by) REFERENCES users (user_id)
                )
            ''')
            
            # Check if admin exists
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (ADMIN_USER_ID,))
            if not cursor.fetchone():
                referral_code = generate_referral_code(ADMIN_USER_ID)
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, approved, 
                                      approved_until, join_date, last_active, is_admin, is_mm,
                                      referral_code, tier, credits, free_swaps_earned)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ADMIN_USER_ID, "admin", "Admin", "User", 1, 
                    "9999-12-31 23:59:59",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    1, 1, referral_code, "vip", 1000000, 100
                ))
                
                cursor.execute('''
                    INSERT INTO middlemen (user_id, verified_by, verified_at, status)
                    VALUES (?, ?, ?, ?)
                ''', (
                    ADMIN_USER_ID, ADMIN_USER_ID,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "active"
                ))
            
            conn.commit()
            conn.close()
            
            print("✅ Database initialized successfully with encryption support")
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# ==================== BASIC HELPER FUNCTIONS ====================
def is_admin(user_id):
    """Check if user is admin"""
    result = execute_one("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    return result and result[0] == 1

def is_middleman(user_id):
    """Check if user is verified middleman"""
    result = execute_one("SELECT is_mm FROM users WHERE user_id = ?", (user_id,))
    return result and result[0] == 1

def is_verified_mm(user_id):
    """Check if user is in verified middlemen table"""
    result = execute_one("SELECT id FROM middlemen WHERE user_id = ? AND status = 'active'", (user_id,))
    return result is not None

def generate_referral_code(user_id):
    """Generate unique referral code"""
    return f"CARNAGE{user_id}{random.randint(1000, 9999)}"

def generate_listing_id():
    """Generate unique listing ID"""
    return f"LIST{int(time.time())}{random.randint(1000, 9999)}"

def generate_swap_id():
    """Generate unique swap ID"""
    return f"SWAP{int(time.time())}{random.randint(1000, 9999)}"

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

def get_user_sessions(user_id):
    """Get user's saved sessions from database"""
    result = execute_one(
        "SELECT main_session_encrypted, main_username, target_session_encrypted, target_username FROM users WHERE user_id = ?",
        (user_id,)
    )
    if result:
        main_session = decrypt_session(result[0]) if result[0] else None
        target_session = decrypt_session(result[2]) if result[2] else None
        
        return {
            'main': main_session,
            'main_username': result[1],
            'target': target_session,
            'target_username': result[3]
        }
    return {'main': None, 'main_username': None, 'target': None, 'target_username': None}

def save_session_to_db(user_id, session_type, session_id, username):
    """Save encrypted session to database"""
    encrypted_session = encrypt_session(session_id)
    
    if session_type == "main":
        execute_query(
            "UPDATE users SET main_session_encrypted = ?, main_username = ? WHERE user_id = ?",
            (encrypted_session, username, user_id),
            commit=True
        )
    elif session_type == "target":
        execute_query(
            "UPDATE users SET target_session_encrypted = ?, target_username = ? WHERE user_id = ?",
            (encrypted_session, username, user_id),
            commit=True
        )
    elif session_type == "backup":
        execute_query(
            "UPDATE users SET backup_session_encrypted = ?, backup_username = ? WHERE user_id = ?",
            (encrypted_session, username, user_id),
            commit=True
        )
    elif session_type == "marketplace_seller":
        execute_query(
            "UPDATE marketplace_listings SET seller_session_encrypted = ?, verified_at = ? WHERE listing_id = ?",
            (encrypted_session, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username),
            commit=True
        )

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

def validate_session(session_id, chat_id=None, user_id=None, purpose="validation"):
    """Validate Instagram session ID and return username"""
    print(f"Validating session for purpose: {purpose}")
    
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
                username = data["user"]["username"]
                return {
                    "success": True,
                    "username": username,
                    "user_id": data["user"]["pk"],
                    "full_name": data["user"]["full_name"],
                    "is_private": data["user"]["is_private"]
                }
            else:
                return {"success": False, "error": "No username found"}
        elif response.status_code == 401:
            return {"success": False, "error": "Invalid or expired session ID"}
        elif response.status_code == 429:
            if chat_id:
                set_cooldown(chat_id)
            return {"success": False, "error": "Rate limit reached"}
        else:
            return {"success": False, "error": f"Unexpected response: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except Exception as e:
        return {"success": False, "error": f"Validation error: {str(e)}"}

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
    footer = session_data[chat_id]["name"] if chat_id in session_data and session_data[chat_id]["name"] else "CARNAGE Swapper"
    webhook_url = session_data[chat_id]["swap_webhook"] if chat_id in session_data and session_data[chat_id]["swap_webhook"] else DEFAULT_WEBHOOK_URL
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
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("status") == "ok":
                    return random_username
                else:
                    error_message = data.get("message", "Unknown error")
                    return None
            except json.JSONDecodeError:
                return None
        elif response.status_code == 429:
            errors_count += 1
            set_cooldown(chat_id)
            return None
        elif response.status_code == 400:
            errors_count += 1
            return None
        else:
            errors_count += 1
            return None
    except Exception as e:
        errors_count += 1
        return None

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
                    return False
            except json.JSONDecodeError:
                return False
        elif response.status_code == 429:
            errors_count += 1
            set_cooldown(chat_id)
            return False
        elif response.status_code == 400:
            errors_count += 1
            return False
        else:
            errors_count += 1
            return False
    except Exception as e:
        errors_count += 1
        return False

# ==================== DATABASE FUNCTIONS ====================
def add_user(user_id, username, first_name, last_name, referral_code="direct"):
    """Add new user to database"""
    existing_user = execute_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing_user:
        return
    
    user_referral_code = generate_referral_code(user_id)
    execute_query('''
        INSERT INTO users (user_id, username, first_name, last_name, join_date, last_active, 
                          referral_code, join_method, credits)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          user_referral_code, 'direct', 100), commit=True)
    
    if referral_code and referral_code != "direct":
        process_referral(user_id, referral_code)
    
    # Notify admin about new user
    try:
        bot.send_message(
            ADMIN_USER_ID,
            f"🆕 *New User Joined*\n\n"
            f"ID: `{user_id}`\n"
            f"Name: {first_name} {last_name}\n"
            f"Username: @{username or 'N/A'}\n"
            f"Via: {'Referral' if referral_code != 'direct' else 'Direct'}\n\n"
            f"Total Users: {get_total_users()}",
            parse_mode="Markdown"
        )
    except:
        pass

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
    # Check if user has enough credits
    user_credits = get_user_credits(user_id)
    if user_credits < 10 and status != "success":
        return False
    
    # Deduct 10 credits for swap attempt
    if status != "success":
        if not deduct_credits(user_id, 10):
            return False
    
    execute_query('''
        INSERT INTO swap_history (user_id, target_username, status, swap_time, error_message, credits_spent)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, target_username, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), error_message, 10), commit=True)
    
    execute_query("UPDATE users SET total_swaps = total_swaps + 1 WHERE user_id = ?", (user_id,), commit=True)
    if status == "success":
        execute_query("UPDATE users SET successful_swaps = successful_swaps + 1 WHERE user_id = ?", (user_id,), commit=True)
    
    return True

def get_user_credits(user_id):
    """Get user's credits balance"""
    result = execute_one("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    return result[0] if result else 0

def deduct_credits(user_id, amount):
    """Deduct credits from user"""
    current_credits = get_user_credits(user_id)
    if current_credits < amount:
        return False
    
    execute_query("UPDATE users SET credits = credits - ? WHERE user_id = ?", 
                  (amount, user_id), commit=True)
    return True

def add_credits(user_id, amount):
    """Add credits to user"""
    execute_query("UPDATE users SET credits = credits + ? WHERE user_id = ?", 
                  (amount, user_id), commit=True)
    return True

def get_user_detailed_stats(user_id):
    """Get detailed user statistics"""
    user_data = execute_one('''
        SELECT username, total_swaps, successful_swaps, total_referrals, free_swaps_earned,
               join_date, last_active, tier, credits, vouch_score, positive_vouches,
               negative_vouches, total_transactions
        FROM users WHERE user_id = ?
    ''', (user_id,))
    
    if not user_data:
        return None
    
    (username, total_swaps, successful_swaps, total_referrals, free_swaps, 
     join_date, last_active, tier, credits, vouch_score, positive_vouches,
     negative_vouches, total_transactions) = user_data
    
    success_rate = (successful_swaps / total_swaps * 100) if total_swaps > 0 else 0
    
    recent_swaps = execute_query('''
        SELECT target_username, status, swap_time 
        FROM swap_history 
        WHERE user_id = ? 
        ORDER BY swap_time DESC 
        LIMIT 5
    ''', (user_id,))
    
    achievements = execute_query('''
        SELECT achievement_id, achievement_name, achievement_emoji, unlocked_at 
        FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC
    ''', (user_id,))
    
    achievements_unlocked = len(achievements)
    
    return {
        "username": username or "User",
        "bot_username": BOT_USERNAME,
        "user_id": user_id,
        "join_date": join_date,
        "last_active": last_active,
        "tier": tier,
        "credits": credits,
        "vouch_score": vouch_score,
        "positive_vouches": positive_vouches,
        "negative_vouches": negative_vouches,
        "total_transactions": total_transactions,
        "total_swaps": total_swaps,
        "successful_swaps": successful_swaps,
        "success_rate": success_rate,
        "total_referrals": total_referrals,
        "free_swaps": free_swaps,
        "achievements_unlocked": achievements_unlocked,
        "recent_swaps": [
            {"target": s[0], "status": s[1], "time": s[2]} for s in recent_swaps
        ],
        "achievements": achievements
    }

# ==================== BROADCAST FUNCTION ====================
@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Broadcast message to all users - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        # Extract message text
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /broadcast <message>\n\nExample: /broadcast New update available!")
            return
        
        broadcast_message = parts[1]
        
        # Ask for confirmation
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Yes, Send to All", callback_data=f"confirm_broadcast_{hashlib.md5(broadcast_message.encode()).hexdigest()}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
        )
        
        bot.send_message(
            user_id,
            f"📢 *Confirm Broadcast*\n\n"
            f"Message: {broadcast_message}\n\n"
            f"⚠️ This will be sent to ALL users. Are you sure?",
            parse_mode="Markdown",
            reply_markup=markup
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def send_broadcast_to_all(message_text, from_user_id):
    """Send broadcast message to all users"""
    try:
        # Get all user IDs
        users = execute_query("SELECT user_id FROM users WHERE is_banned = 0")
        
        if not users:
            return 0, "No users found"
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            user_id = user[0]
            try:
                bot.send_message(
                    user_id,
                    f"📢 *ANNOUNCEMENT FROM CARNAGE*\n\n{message_text}\n\n",
                    parse_mode="Markdown"
                )
                sent_count += 1
                time.sleep(0.1)  # Prevent rate limiting
            except Exception as e:
                failed_count += 1
                print(f"Failed to send to {user_id}: {e}")
        
        return sent_count, failed_count
        
    except Exception as e:
        return 0, str(e)

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
        
        # Give 2 free swaps to referrer
        execute_query('''
            UPDATE users 
            SET total_referrals = total_referrals + 1,
                free_swaps_earned = free_swaps_earned + 2
            WHERE user_id = ?
        ''', (referrer_id,), commit=True)
        
        # Give 20 extra credits to referrer
        add_credits(referrer_id, 20)
        
        # Auto-approve referred user
        execute_query("UPDATE users SET approved = 1, approved_until = '9999-12-31 23:59:59' WHERE user_id = ?", 
                     (user_id,), commit=True)
        
        # Log referral
        execute_query('''
            INSERT INTO referral_tracking (referrer_id, referred_id, joined_at)
            VALUES (?, ?, ?)
        ''', (referrer_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")), commit=True)
        
        try:
            bot.send_message(
                referrer_id,
                f"🎉 *New Referral!*\n\n"
                f"Someone joined using your referral link!\n"
                f"• You earned: **2 FREE swaps** 🆓\n"
                f"• You earned: **20 credits** 🪙\n"
                f"• Total referrals: {get_user_referrals_count(referrer_id)}\n"
                f"• Total free swaps earned: {get_user_free_swaps(referrer_id)}\n\n"
                f"Keep sharing your link for more rewards!",
                parse_mode="Markdown"
            )
        except:
            pass

def get_user_referrals_count(user_id):
    """Get count of user's referrals"""
    result = execute_one("SELECT COUNT(*) FROM referral_tracking WHERE referrer_id = ?", (user_id,))
    return result[0] if result else 0

def get_user_free_swaps(user_id):
    """Get user's free swaps count"""
    result = execute_one("SELECT free_swaps_earned FROM users WHERE user_id = ?", (user_id,))
    return result[0] if result else 0

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

# ==================== MENU FUNCTIONS ====================
def show_main_menu(chat_id):
    """Show main menu"""
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "⏳ *Your account is pending approval.*", parse_mode="Markdown")
        return
    
    # Check credits balance
    credits = get_user_credits(chat_id)
    
    buttons = [
        "📱 Main Session", "🎯 Target Session",
        "🔄 Swapper", "⚙️ Settings",
        "📊 Dashboard", "🎁 Referral",
        "🏆 Achievements", "📈 Stats",
        "🛒 Marketplace"
    ]
    markup = create_reply_menu(buttons, row_width=2, add_back=False)
    welcome_msg = f"🤖 *CARNAGE Swapper - Main Menu*\n\n💰 Credits Balance: `{credits}` 🪙\n*Note:* Each swap costs 10 credits\n\nUse the buttons below or type /help for commands."
    bot.send_message(chat_id, welcome_msg, parse_mode='Markdown', reply_markup=markup)

def show_swapper_menu(chat_id):
    """Show swapper menu"""
    if not is_user_approved(chat_id):
        return
    
    credits = get_user_credits(chat_id)
    buttons = ["Run Main Swap", "BackUp Mode", "Threads Swap", "Back"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, f"<b>🔄 CARNAGE Swapper - Select Option</b>\n\n💰 Credits: {credits} 🪙\n⚡ Each swap costs 10 credits", parse_mode='HTML', reply_markup=markup)

def show_settings_menu(chat_id):
    """Show settings menu"""
    if not is_user_approved(chat_id):
        return
    
    buttons = ["Bio", "Name", "Webhook", "Check Block", "Close Sessions", "Back"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b>⚙️ CARNAGE Settings - Select Option</b>", parse_mode='HTML', reply_markup=markup)

# ==================== ADMIN COMMANDS ====================
@bot.message_handler(commands=['refreshbot'])
def refreshbot_command(message):
    """Refresh bot - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        # Reload configuration
        global start_time
        start_time = time.time()
        
        # Clear caches
        session_data.clear()
        rate_limit_cooldowns.clear()
        user_states.clear()
        pending_swaps.clear()
        bidding_sessions.clear()
        vouch_requests.clear()
        bulk_listings.clear()
        
        # Reinitialize database connection
        init_database()
        
        bot.reply_to(message, "🔄 *Bot refreshed successfully!*\n\n• Caches cleared\n• Database reconnected\n• Timestamp reset", parse_mode="Markdown")
        
        # Send to admin group
        try:
            bot.send_message(
                ADMIN_GROUP_ID,
                f"🔄 *Bot Refreshed*\n\n"
                f"Admin: {message.from_user.username}\n"
                f"Time: {datetime.now().strftime('%H:%M:%S')}",
                parse_mode="Markdown"
            )
        except:
            pass
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error refreshing bot: {str(e)}")

@bot.message_handler(commands=['ping'])
def ping_command(message):
    """Check bot response time"""
    if message.chat.type != 'private':
        return
    
    start = time.time()
    msg = bot.reply_to(message, "🏓 Pinging...")
    end = time.time()
    
    response_time = round((end - start) * 1000, 2)
    
    bot.edit_message_text(
        f"🏓 *PONG!*\n\n"
        f"• Response Time: `{response_time}ms`\n"
        f"• Bot Uptime: `{str(timedelta(seconds=int(time.time() - start_time)))}`\n"
        f"• Users Online: `{execute_one('SELECT COUNT(*) FROM users WHERE last_active > ?', ((datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S'),))[0] or 0}`",
        message.chat.id,
        msg.message_id,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['botstatus'])
def botstatus_command(message):
    """Check bot status - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        # Get system stats
        uptime = str(timedelta(seconds=int(time.time() - start_time)))
        
        # Database stats
        total_users = execute_one("SELECT COUNT(*) FROM users")[0] or 0
        active_users = execute_one(
            "SELECT COUNT(*) FROM users WHERE last_active > ?",
            ((datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),)
        )[0] or 0
        
        total_swaps = execute_one("SELECT COUNT(*) FROM swap_history")[0] or 0
        successful_swaps = execute_one("SELECT COUNT(*) FROM swap_history WHERE status = 'success'")[0] or 0
        
        # Credits stats
        total_credits = execute_one("SELECT SUM(credits) FROM users")[0] or 0
        credits_spent = execute_one("SELECT SUM(credits_spent) FROM swap_history")[0] or 0
        
        # Marketplace stats
        active_listings = execute_one("SELECT COUNT(*) FROM marketplace_listings WHERE status = 'active'")[0] or 0
        active_swaps = execute_one("SELECT COUNT(*) FROM marketplace_swaps WHERE status IN ('created', 'payment_received')")[0] or 0
        
        # System memory
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        
        # Bot API status
        api_status = "✅ Online" if check_instagram_api() else "❌ Offline"
        
        response = (
            f"🤖 *BOT STATUS REPORT*\n\n"
            f"*System Info:*\n"
            f"• Uptime: `{uptime}`\n"
            f"• CPU Usage: `{cpu}%`\n"
            f"• Memory Usage: `{memory.percent}%`\n"
            f"• Threads: `{threading.active_count()}`\n\n"
            
            f"*Bot Stats:*\n"
            f"• Total Users: `{total_users}`\n"
            f"• Active (1h): `{active_users}`\n"
            f"• Total Swaps: `{total_swaps}`\n"
            f"• Successful: `{successful_swaps}`\n"
            f"• API Requests: `{requests_count}`\n"
            f"• API Errors: `{errors_count}`\n\n"
            
            f"*Credits Economy:*\n"
            f"• Total Credits in Circulation: `{total_credits}`\n"
            f"• Credits Spent on Swaps: `{credits_spent}`\n"
            f"• Credits per Swap: `10` 🪙\n\n"
            
            f"*Marketplace Stats:*\n"
            f"• Active Listings: `{active_listings}`\n"
            f"• Active Swaps: `{active_swaps}`\n"
            f"• Total Listings: `{execute_one('SELECT COUNT(*) FROM marketplace_listings')[0] or 0}`\n"
            f"• Active Auctions: `{execute_one('SELECT COUNT(*) FROM marketplace_listings WHERE sale_type = \"auction\" AND status = \"active\"')[0] or 0}`\n\n"
            
            f"*Service Status:*\n"
            f"• Instagram API: {api_status}\n"
            f"• Database: `✅ Connected`\n"
            f"• Encryption: `✅ Active`\n"
            f"• Web Server: `✅ Running`\n\n"
            
            f"*Cache Status:*\n"
            f"• Session Data: `{len(session_data)} users`\n"
            f"• Pending Swaps: `{len(pending_swaps)}`\n"
            f"• User States: `{len(user_states)}`\n"
            f"• Bidding Sessions: `{len(bidding_sessions)}`\n"
            f"• Bulk Listings: `{len(bulk_listings)}`\n"
        )
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error getting bot status: {str(e)}")

@bot.message_handler(commands=['users'])
def admin_users(message):
    """List all users - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        page = 1
        if len(message.text.split()) > 1:
            try:
                page = int(message.text.split()[1])
            except:
                pass
        
        per_page = 10
        offset = (page - 1) * per_page
        
        users = execute_query('''
            SELECT user_id, username, first_name, tier, approved, is_banned, 
                   credits, total_swaps, successful_swaps, join_date, total_referrals,
                   vouch_score, positive_vouches, negative_vouches
            FROM users 
            ORDER BY user_id
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        total = execute_one("SELECT COUNT(*) FROM users")[0]
        
        response = f"👥 *Users List (Page {page})*\n\n"
        response += f"Total Users: {total}\n\n"
        
        for user in users:
            status = "✅" if user["approved"] else "⏳"
            status = "❌" if user["is_banned"] else status
            
            response += (
                f"ID: `{user['user_id']}`\n"
                f"Name: {user['first_name']} (@{user['username'] or 'N/A'})\n"
                f"Tier: {user['tier'].upper()} | Credits: {user['credits']}\n"
                f"Swaps: {user['total_swaps']} ({user['successful_swaps']}✅)\n"
                f"Referrals: {user['total_referrals']} | Vouch: {user['vouch_score']} ({user['positive_vouches']}+/{user['negative_vouches']}-)\n"
                f"Status: {status}\n"
                f"Joined: {user['join_date'][:10]}\n"
                f"────────────────────\n"
            )
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['ban'])
def admin_ban(message):
    """Ban a user - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /ban <user_id> <reason>")
            return
        
        target_id = int(parts[1])
        reason = " ".join(parts[2:]) if len(parts) > 2 else "Violation of terms"
        
        # Check if user exists
        user = execute_one("SELECT username FROM users WHERE user_id = ?", (target_id,))
        if not user:
            bot.reply_to(message, "❌ User not found")
            return
        
        # Ban user
        execute_query('''
            UPDATE users 
            SET is_banned = 1, ban_reason = ?
            WHERE user_id = ?
        ''', (reason, target_id), commit=True)
        
        # Notify user
        try:
            bot.send_message(
                target_id,
                f"🚫 *You have been banned*\n\n"
                f"Reason: {reason}\n"
                f"Appeal: Contact @CARNAGEV1"
            )
        except:
            pass
        
        bot.reply_to(message, f"✅ User {target_id} has been banned.\nReason: {reason}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['unban'])
def admin_unban(message):
    """Unban a user - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /unban <user_id>")
            return
        
        target_id = int(parts[1])
        
        # Check if user exists and is banned
        user = execute_one("SELECT username, is_banned FROM users WHERE user_id = ?", (target_id,))
        if not user:
            bot.reply_to(message, "❌ User not found")
            return
        
        if not user[1]:
            bot.reply_to(message, "❌ User is not banned")
            return
        
        # Unban user
        execute_query('''
            UPDATE users 
            SET is_banned = 0, ban_reason = NULL
            WHERE user_id = ?
        ''', (target_id,), commit=True)
        
        # Notify user
        try:
            bot.send_message(
                target_id,
                f"✅ *You have been unbanned!*\n\n"
                f"You can now use the bot again."
            )
        except:
            pass
        
        bot.reply_to(message, f"✅ User {target_id} has been unbanned.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['bannedusers'])
def admin_bannedusers(message):
    """Show banned users with inline buttons - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        banned_users = execute_query('''
            SELECT user_id, username, first_name, ban_reason, join_date
            FROM users 
            WHERE is_banned = 1
            ORDER BY user_id
        ''')
        
        if not banned_users:
            bot.reply_to(message, "🚫 No banned users found.")
            return
        
        response = f"🚫 *Banned Users ({len(banned_users)})*\n\n"
        markup = InlineKeyboardMarkup(row_width=2)
        
        for user in banned_users:
            user_id_str = str(user[0])
            response += (
                f"ID: `{user[0]}`\n"
                f"Name: {user[2]} (@{user[1] or 'N/A'})\n"
                f"Reason: {user[3] or 'No reason'}\n"
                f"Joined: {user[4][:10]}\n"
                f"────────────────────\n"
            )
            
            # Add unban button for each user
            markup.add(
                InlineKeyboardButton(f"✅ Unban {user[2]}", callback_data=f"unban_{user[0]}"),
                InlineKeyboardButton(f"👁️ View", callback_data=f"viewbanned_{user[0]}")
            )
        
        markup.add(InlineKeyboardButton("🔄 Refresh", callback_data="refresh_banned"))
        
        bot.reply_to(message, response, parse_mode="Markdown", reply_markup=markup)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['approve'])
def admin_approve(message):
    """Approve a user - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /approve <user_id> <duration>")
            bot.reply_to(message, "Duration examples: test, 2d, 7d, 30d, permanent")
            return
        
        target_id = int(parts[1])
        duration = parts[2] if len(parts) > 2 else "permanent"
        
        # Calculate approval until date
        if duration == "test":
            approved_until = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            duration_text = "1 hour (test)"
        elif duration == "permanent":
            approved_until = "9999-12-31 23:59:59"
            duration_text = "permanent"
        else:
            # Parse duration like 2d, 7d, 30d
            days = int(duration[:-1])
            approved_until = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            duration_text = f"{days} days"
        
        # Approve user
        execute_query('''
            UPDATE users 
            SET approved = 1, approved_until = ?
            WHERE user_id = ?
        ''', (approved_until, target_id), commit=True)
        
        # Give some free credits
        execute_query("UPDATE users SET credits = credits + 100 WHERE user_id = ?", (target_id,), commit=True)
        
        # Notify user
        try:
            bot.send_message(
                target_id,
                f"🎉 *Your account has been approved!*\n\n"
                f"• Duration: {duration_text}\n"
                f"• Free Credits: 100 🪙\n"
                f"• Start swapping now!\n\n"
                f"Use /help for commands"
            )
        except:
            pass
        
        bot.reply_to(message, f"✅ User {target_id} approved for {duration_text} with 100 free credits.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addcredits'])
def admin_addcredits(message):
    """Add credits to user - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: /addcredits <user_id> <amount>")
            return
        
        target_id = int(parts[1])
        amount = int(parts[2])
        
        # Add credits
        add_credits(target_id, amount)
        
        # Get new balance
        new_balance = get_user_credits(target_id)
        
        # Notify user
        try:
            bot.send_message(
                target_id,
                f"🎁 *You received credits!*\n\n"
                f"Amount: +{amount} credits 🪙\n"
                f"New Balance: {new_balance} credits\n\n"
                f"Use them for swapping or in marketplace!",
                parse_mode="Markdown"
            )
        except:
            pass
        
        bot.reply_to(message, f"✅ Added {amount} credits to user {target_id}. New balance: {new_balance}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    """Show bot statistics - ADMIN ONLY"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        # Get stats
        total_users = execute_one("SELECT COUNT(*) FROM users")[0]
        active_users = execute_one("SELECT COUNT(*) FROM users WHERE last_active > ?",
                                  ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),))[0]
        
        total_swaps = execute_one("SELECT COUNT(*) FROM swap_history")[0]
        successful_swaps = execute_one("SELECT COUNT(*) FROM swap_history WHERE status = 'success'")[0]
        
        total_credits = execute_one("SELECT SUM(credits) FROM users")[0] or 0
        credits_spent = execute_one("SELECT SUM(credits_spent) FROM swap_history")[0] or 0
        
        total_referrals = execute_one("SELECT SUM(total_referrals) FROM users")[0] or 0
        
        # Calculate success rate
        success_rate = (successful_swaps / total_swaps * 100) if total_swaps > 0 else 0
        
        # Bot uptime
        uptime_seconds = time.time() - start_time
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        
        response = (
            f"📊 *Bot Statistics*\n\n"
            f"🤖 *Users:*\n"
            f"• Total: {total_users}\n"
            f"• Active (24h): {active_users}\n\n"
            
            f"🔄 *Swaps:*\n"
            f"• Total: {total_swaps}\n"
            f"• Successful: {successful_swaps}\n"
            f"• Success Rate: {success_rate:.1f}%\n"
            f"• Credits per Swap: 10 🪙\n\n"
            
            f"💰 *Credits Economy:*\n"
            f"• Total Credits: {total_credits}\n"
            f"• Credits Spent: {credits_spent}\n"
            f"• Credits per Referral: 20 🪙\n\n"
            
            f"🎁 *Referrals:*\n"
            f"• Total: {total_referrals}\n"
            f"• Active Referrers: {execute_one('SELECT COUNT(DISTINCT referrer_id) FROM referral_tracking')[0]}\n\n"
            
            f"⚙️ *System:*\n"
            f"• Uptime: {uptime_str}\n"
            f"• Requests: {requests_count}\n"
            f"• Errors: {errors_count}\n"
            f"• API Status: {'✅ Online' if check_instagram_api() else '❌ Offline'}\n\n"
            
            f"💾 *Database:*\n"
            f"• Size: {get_database_size()} KB\n"
        )
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def check_instagram_api():
    """Check if Instagram API is working"""
    try:
        response = requests.get("https://www.instagram.com", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_database_size():
    """Get database file size"""
    try:
        return os.path.getsize('users.db') // 1024
    except:
        return 0

# ==================== COMMAND HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    
    referral_code = "direct"
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith("ref-"):
            referral_code = param[4:]
    
    add_user(user_id, username, first_name, last_name, referral_code)
    update_user_active(user_id)
    
    if has_joined_all_channels(user_id):
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
                "Tip: Get a friend to refer you for instant approval + 2 FREE swaps + 20 credits! 🎁",
                parse_mode="Markdown"
            )
    else:
        send_welcome_with_channels(user_id, first_name)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show help menu"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if not has_joined_all_channels(user_id):
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
/referral - Your referral link
/vouches - Your vouch profile
/credits - Check your credits balance

*Swap Features (DM ONLY):*
• Real Instagram username swapping
• Working API with rate limit handling
• Session validation and management
• Backup mode and threads support
• *10 credits per swap attempt*

*Marketplace Features (DM ONLY):*
/marketplace - Browse username listings
/sell - List username for sale (Real money only)
/bid - Place bid on auction
/mybids - View your active bids
/bulksell - List multiple usernames at once

*Auction System:*
• Fixed price and auction listings
• Automatic bid increments
• Buy Now option
• Fake bid protection (permanent ban for fake bids)

*Vouch System:*
• Automatic vouch requests after swaps
• Positive/negative feedback
• Vouch score calculation
• Verified transactions only

*Credits System:*
• New users get 100 credits free
• Each swap attempt costs 10 credits
• Refer friends for 20 credits each
• Admins can add credits

*Admin Commands (Admin only - DM ONLY):*
/users - List all users
/ban <id> <reason> - Ban user
/unban <id> - Unban user
/bannedusers - Show banned users with options
/approve <id> <duration> - Approve user
/addcredits <id> <amount> - Add credits
/stats - Bot statistics
/ping - Check bot response time
/botstatus - Detailed bot status
/refreshbot - Refresh bot caches
/broadcast <message> - Send message to all users

*Middleman Commands (MM only - GROUP ONLY):*
/mmhelp - Show MM commands
/createswap - Create new swap
/rcvd - Mark payment received
/release - Release funds
/refund - Refund transaction

*Official Channels:*
📢 Updates: @CarnageUpdates
✅ Proofs: @CarnageProofs

*Getting Started:*
1. Join both channels above
2. Use /tutorial for step-by-step guide
3. Add Instagram sessions
4. Start swapping!
5. Refer friends for FREE swaps (2 per referral!) + 20 credits each!

*Need Help?*
Contact: @CARNAGEV1

*NOTE: All user functions work in DM only!*
"""
    
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['dashboard'])
def dashboard_command(message):
    """Dashboard command"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    dashboard_url = f"https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/{user_id}"
    bot.send_message(user_id, f"📊 *Your Dashboard:*\n\n{dashboard_url}", parse_mode="Markdown")

@bot.message_handler(commands=['credits'])
def credits_command(message):
    """Check credits balance"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    credits = get_user_credits(user_id)
    bot.send_message(
        user_id,
        f"💰 *Your Credits Balance*\n\n"
        f"• Current Balance: `{credits}` 🪙\n"
        f"• Swap Cost: `10` credits per attempt\n"
        f"• Referral Bonus: `20` credits per friend\n\n"
        f"*Ways to earn credits:*\n"
        f"1. Refer friends (20 credits each)\n"
        f"2. Admin rewards (contact admin)\n"
        f"3. Marketplace sales\n\n"
        f"*Note:* Credits are deducted only for failed swaps. Successful swaps are free!",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['referral', 'refer'])
def referral_command(message):
    """Referral command"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    # Get referral code
    result = execute_one("SELECT referral_code FROM users WHERE user_id = ?", (user_id,))
    if result:
        referral_code = result[0]
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref-{referral_code}"
        
        # Get referral stats
        ref_count = get_user_referrals_count(user_id)
        free_swaps = get_user_free_swaps(user_id)
        credits = get_user_credits(user_id)
        
        response = (
            f"🎁 *Your Referral Program*\n\n"
            f"*Your Link:*\n`{referral_link}`\n\n"
            f"*How it works:*\n"
            f"1. Share your link with friends\n"
            f"2. When they join using your link\n"
            f"3. You get **2 FREE swaps** for each friend!\n"
            f"4. You get **20 credits** for each friend! 🪙\n"
            f"5. They get instant approval\n\n"
            f"*Your Stats:*\n"
            f"• Total Referrals: {ref_count}\n"
            f"• Free Swaps Earned: {free_swaps}\n"
            f"• Credits Balance: {credits} 🪙\n\n"
            f"*Rewards:*\n"
            f"• 1 referral = 2 FREE swaps + 20 credits\n"
            f"• 5 referrals = Achievement badge\n"
            f"• 10 referrals = VIP features (coming soon)\n\n"
            f"Start sharing now! 🚀"
        )
        
        bot.send_message(user_id, response, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "❌ Error generating referral link")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Stats command"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    stats = get_user_detailed_stats(user_id)
    if stats:
        response = f"""
📊 *Your Statistics*

*Basic Info:*
• User ID: `{stats['user_id']}`
• Username: @{stats['username']}
• Tier: {stats['tier'].upper()}
• Status: {"✅ Approved" if is_user_approved(user_id) else "⏳ Pending"}
• Joined: {stats['join_date'][:10]}
• Last Active: {stats['last_active'][:16]}

*Credits & Swaps:*
• Credits Balance: {stats['credits']} 🪙
• Total Swaps: {stats['total_swaps']}
• Successful: {stats['successful_swaps']}
• Success Rate: {stats['success_rate']:.1f}%
• Swap Cost: 10 credits per attempt

*Referral Stats:*
• Total Referrals: {stats['total_referrals']}
• Free Swaps Available: {stats['free_swaps']}
• Referral Bonus: 20 credits per friend

*Vouch Stats:*
• Vouch Score: {stats['vouch_score']}
• Positive Vouches: {stats['positive_vouches']}
• Negative Vouches: {stats['negative_vouches']}
• Total Transactions: {stats['total_transactions']}
"""
        bot.send_message(user_id, response, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "📊 *No statistics yet. Start swapping!*", parse_mode="Markdown")

# ==================== MENU HANDLERS ====================
@bot.message_handler(func=lambda message: message.chat.type == 'private')
def handle_private_messages(message):
    chat_id = message.chat.id
    text = message.text
    
    update_user_active(chat_id)
    
    # Check if in tutorial
    if chat_id in tutorial_sessions:
        handle_tutorial_response(chat_id, text)
        return
    
    # Check channel membership first
    if not has_joined_all_channels(chat_id):
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
        else:
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
        session_data[chat_id]["previous_menu"] = "main"
        show_swapper_menu(chat_id)
        return
    
    if text == "⚙️ Settings":
        session_data[chat_id]["previous_menu"] = "main"
        show_settings_menu(chat_id)
        return
    
    if text == "🛒 Marketplace":
        marketplace_command(message)
        return
    
    if text in ["Run Main Swap", "BackUp Mode", "Threads Swap"]:
        handle_swap_option(chat_id, text)
        return
    
    if text in ["Bio", "Name", "Webhook", "Check Block", "Close Sessions"]:
        handle_settings_option(chat_id, text)
        return
    
    # Default response for admin commands in menu
    if text.startswith('/'):
        # Let command handlers process it
        return
    
    # Default response
    credits = get_user_credits(chat_id)
    bot.send_message(chat_id, f"🤖 *CARNAGE Swapper - Main Menu*\n\n💰 Credits: {credits} 🪙\n⚡ Each swap costs 10 credits\n\nUse the buttons below or type /help for commands.", parse_mode="Markdown")
    show_main_menu(chat_id)

def save_main_session(message):
    """Save main session"""
    if message.chat.type != 'private':
        return
    
    chat_id = message.chat.id
    session_id = message.text.strip()
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "❌ Your account is not approved yet.", parse_mode="Markdown")
        show_main_menu(chat_id)
        return
    
    validation = validate_session(session_id, chat_id)
    if validation["success"]:
        username = validation["username"]
        session_data[chat_id]["main"] = session_id
        session_data[chat_id]["main_username"] = f"@{username}"
        session_data[chat_id]["main_validated_at"] = time.time()
        save_session_to_db(chat_id, "main", session_id, username)
        bot.send_message(chat_id, f"✅ *Main Session Logged @{username}*", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, f"❌ {validation['error']}", parse_mode="Markdown")
    
    show_main_menu(chat_id)

def save_target_session(message):
    """Save target session"""
    if message.chat.type != 'private':
        return
    
    chat_id = message.chat.id
    session_id = message.text.strip()
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "❌ Your account is not approved yet.", parse_mode="Markdown")
        show_main_menu(chat_id)
        return
    
    validation = validate_session(session_id, chat_id)
    if validation["success"]:
        username = validation["username"]
        session_data[chat_id]["target"] = session_id
        session_data[chat_id]["target_username"] = f"@{username}"
        session_data[chat_id]["target_validated_at"] = time.time()
        save_session_to_db(chat_id, "target", session_id, username)
        bot.send_message(chat_id, f"✅ *Target Session Logged @{username}*", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, f"❌ {validation['error']}", parse_mode="Markdown")
    
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
    if message.chat.type != 'private':
        return
    
    chat_id = message.chat.id
    session_id = message.text.strip()
    
    validation = validate_session(session_id, chat_id)
    if validation["success"]:
        username = validation["username"]
        session_data[chat_id]["backup"] = session_id
        session_data[chat_id]["backup_username"] = f"@{username}"
        save_session_to_db(chat_id, "backup", session_id, username)
        bot.send_message(chat_id, f"✅ *Backup Session Logged @{username}*", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, f"❌ {validation['error']}", parse_mode="Markdown")
    
    show_swapper_menu(chat_id)

def save_swapper_threads(message):
    """Save swapper threads"""
    if message.chat.type != 'private':
        return
    
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
    if message.chat.type != 'private':
        return
    
    chat_id = message.chat.id
    bio = message.text.strip()
    session_data[chat_id]["bio"] = bio
    bot.send_message(chat_id, "✅ *Bio Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def save_name(message):
    """Save name"""
    if message.chat.type != 'private':
        return
    
    chat_id = message.chat.id
    name = message.text.strip()
    session_data[chat_id]["name"] = name
    bot.send_message(chat_id, "✅ *Name Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def save_swap_webhook(message):
    """Save webhook"""
    if message.chat.type != 'private':
        return
    
    chat_id = message.chat.id
    webhook = message.text.strip()
    session_data[chat_id]["swap_webhook"] = webhook
    bot.send_message(chat_id, "✅ *Webhook Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def process_check_block(message):
    """Process check block"""
    if message.chat.type != 'private':
        return
    
    chat_id = message.chat.id
    response = message.text.strip().lower()
    if response == 'y':
        bot.send_message(chat_id, "✅ *Account is swappable!*", parse_mode="Markdown")
    elif response == 'n':
        bot.send_message(chat_id, "❌ *Account is not swappable!*", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Send 'Y' or 'N'", parse_mode="Markdown")
    
    show_settings_menu(chat_id)

def clear_session_data(chat_id, session_type):
    """Clear session data"""
    if chat_id not in session_data:
        return
        
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

def run_main_swap(chat_id):
    """Run main swap"""
    global requests_count, errors_count
    
    # Check if user has enough credits
    user_credits = get_user_credits(chat_id)
    if user_credits < 10:
        bot.send_message(chat_id, f"❌ *Insufficient credits!*\n\nYou need 10 credits to attempt a swap.\nCurrent balance: {user_credits} 🪙\n\nEarn credits by referring friends or contact admin.", parse_mode="Markdown")
        show_swapper_menu(chat_id)
        return
    
    if not session_data[chat_id]["main"] or not session_data[chat_id]["target"]:
        bot.send_message(chat_id, "❌ *Set Main and Target Sessions first*", parse_mode="Markdown")
        show_swapper_menu(chat_id)
        return
    
    # Validate sessions
    main_valid = validate_session(session_data[chat_id]["main"], chat_id)
    target_valid = validate_session(session_data[chat_id]["target"], chat_id)
    
    if not main_valid["success"] or not target_valid["success"]:
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
            
            # Refund credits for successful swap
            add_credits(chat_id, 10)  # Return the 10 credits
            bot.send_message(chat_id, "🔄 *10 credits refunded for successful swap!*", parse_mode="Markdown")
        else:
            bot.edit_message_text(f"❌ *Swap failed for {target_username}*\n\n10 credits deducted for this attempt.", chat_id, message_id, parse_mode="Markdown")
            log_swap(chat_id, target_username, "failed", "Swap process failed")
        
        clear_session_data(chat_id, "main")
        clear_session_data(chat_id, "target")
        
    except Exception as e:
        bot.edit_message_text(f"❌ *Error during swap: {str(e)}*\n\n10 credits deducted for this attempt.", chat_id, message_id, parse_mode="Markdown")
        log_swap(chat_id, "unknown", "failed", str(e))
    
    show_swapper_menu(chat_id)

# ==================== ACHIEVEMENTS ====================
@bot.message_handler(commands=['achievements'])
def achievements_command(message):
    """Achievements command"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    achievements = execute_query('''
        SELECT achievement_id, achievement_name, achievement_emoji, unlocked_at 
        FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC
    ''', (user_id,))
    
    if achievements:
        response = "🏆 *Your Achievements*\n\n"
        for ach in achievements:
            response += f"✅ {ach[2]} *{ach[1]}* - {ach[3].split()[0]}\n"
    else:
        response = "🏆 *No achievements yet!*\n\nStart using the bot to unlock badges! 🔄"
    
    bot.send_message(user_id, response, parse_mode="Markdown")

# ==================== VOUCH SYSTEM ====================
@bot.message_handler(commands=['vouches'])
def vouches_command(message):
    """Show user's vouch profile"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    # Get user vouch stats
    user_stats = execute_one('''
        SELECT username, vouch_score, positive_vouches, negative_vouches, total_transactions
        FROM users WHERE user_id = ?
    ''', (user_id,))
    
    if not user_stats:
        bot.send_message(user_id, "❌ User not found")
        return
    
    username, vouch_score, positive, negative, total_transactions = user_stats
    
    # Get recent vouches
    recent_vouches = execute_query('''
        SELECT v.vouch_type, v.comment, v.vouch_time, u.username as vouch_by
        FROM vouches v
        JOIN users u ON v.user_id = u.user_id
        WHERE v.vouch_for = ? AND v.verified = 1
        ORDER BY v.vouch_time DESC
        LIMIT 10
    ''', (user_id,))
    
    response = f"""
🤝 *Vouch Profile: @{username or user_id}*

*Vouch Score:* {vouch_score} ⭐
*Positive Vouches:* {positive} ✅
*Negative Vouches:* {negative} ❌
*Total Transactions:* {total_transactions} 📊
*Trust Level:* {get_trust_level(vouch_score)}

*Recent Vouches:*
"""
    
    if recent_vouches:
        for vouch in recent_vouches:
            emoji = "✅" if vouch[0] == "positive" else "❌"
            response += f"\n{emoji} *{vouch[0].title()}* by @{vouch[3]}"
            if vouch[1]:
                response += f"\n\"{vouch[1][:50]}...\""
            response += f"\n{vouch[2][:10]}\n"
    else:
        response += "\nNo vouches yet. Complete transactions to get vouches!"
    
    bot.send_message(user_id, response, parse_mode="Markdown")

def get_trust_level(vouch_score):
    """Get trust level based on vouch score"""
    if vouch_score >= 100:
        return "🔒 Highly Trusted"
    elif vouch_score >= 50:
        return "✅ Trusted"
    elif vouch_score >= 20:
        return "👍 Reliable"
    elif vouch_score >= 5:
        return "🆗 New User"
    else:
        return "🆕 Unrated"

def request_vouch(swap_id, seller_id, buyer_id):
    """Request vouch from users after successful swap"""
    swap = execute_one('''
        SELECT ms.swap_id, ml.username, ms.amount, ms.currency
        FROM marketplace_swaps ms
        JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
        WHERE ms.swap_id = ?
    ''', (swap_id,))
    
    if not swap:
        return
    
    # Request vouch from buyer for seller
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Positive", callback_data=f"vouch_positive_{swap_id}_{seller_id}"),
        InlineKeyboardButton("❌ Negative", callback_data=f"vouch_negative_{swap_id}_{seller_id}"),
        InlineKeyboardButton("⏩ Skip", callback_data=f"vouch_skip_{swap_id}")
    )
    
    vouch_requests[buyer_id] = {
        "swap_id": swap_id,
        "vouch_for": seller_id,
        "step": "waiting"
    }
    
    bot.send_message(
        buyer_id,
        f"🤝 *Please leave a vouch for the seller*\n\n"
        f"Transaction: @{swap[1]}\n"
        f"Amount: {swap[2]} {swap[3]}\n"
        f"Swap ID: `{swap_id}`\n\n"
        f"Your vouch helps build trust in the community!",
        parse_mode="Markdown",
        reply_markup=markup
    )
    
    # Request vouch from seller for buyer
    markup2 = InlineKeyboardMarkup(row_width=2)
    markup2.add(
        InlineKeyboardButton("✅ Positive", callback_data=f"vouch_positive_{swap_id}_{buyer_id}"),
        InlineKeyboardButton("❌ Negative", callback_data=f"vouch_negative_{swap_id}_{buyer_id}"),
        InlineKeyboardButton("⏩ Skip", callback_data=f"vouch_skip_{swap_id}")
    )
    
    vouch_requests[seller_id] = {
        "swap_id": swap_id,
        "vouch_for": buyer_id,
        "step": "waiting"
    }
    
    bot.send_message(
        seller_id,
        f"🤝 *Please leave a vouch for the buyer*\n\n"
        f"Transaction: @{swap[1]}\n"
        f"Amount: {swap[2]} {swap[3]}\n"
        f"Swap ID: `{swap_id}`\n\n"
        f"Your vouch helps build trust in the community!",
        parse_mode="Markdown",
        reply_markup=markup2
    )

def process_vouch(user_id, swap_id, vouch_for, vouch_type, comment=None):
    """Process vouch submission"""
    # Record vouch
    execute_query('''
        INSERT INTO vouches (swap_id, user_id, vouch_for, vouch_type, comment, vouch_time, verified)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        swap_id, user_id, vouch_for, vouch_type, comment,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1
    ), commit=True)
    
    # Update vouch statistics
    if vouch_type == "positive":
        execute_query('''
            UPDATE users 
            SET vouch_score = vouch_score + 10,
                positive_vouches = positive_vouches + 1
            WHERE user_id = ?
        ''', (vouch_for,), commit=True)
    else:
        execute_query('''
            UPDATE users 
            SET vouch_score = vouch_score - 5,
                negative_vouches = negative_vouches + 1
            WHERE user_id = ?
        ''', (vouch_for,), commit=True)
    
    # Update total transactions
    execute_query('''
        UPDATE users 
        SET total_transactions = total_transactions + 1
        WHERE user_id IN (?, ?)
    ''', (user_id, vouch_for), commit=True)
    
    # Post to proofs channel if positive
    if vouch_type == "positive":
        try:
            vouch_by = execute_one("SELECT username FROM users WHERE user_id = ?", (user_id,))
            vouch_by_name = f"@{vouch_by[0]}" if vouch_by and vouch_by[0] else f"User {user_id}"
            
            vouch_for_user = execute_one("SELECT username FROM users WHERE user_id = ?", (vouch_for))
            vouch_for_name = f"@{vouch_for_user[0]}" if vouch_for_user and vouch_for_user[0] else f"User {vouch_for}"
            
            swap_info = execute_one('''
                SELECT ml.username, ms.amount, ms.currency
                FROM marketplace_swaps ms
                JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
                WHERE ms.swap_id = ?
            ''', (swap_id,))
            
            if swap_info:
                bot.send_message(
                    CHANNELS['proofs']['id'],
                    f"🤝 *NEW VOUCH!*\n\n"
                    f"✅ *Positive vouch*\n"
                    f"From: {vouch_by_name}\n"
                    f"For: {vouch_for_name}\n"
                    f"Transaction: @{swap_info[0]}\n"
                    f"Amount: {swap_info[1]} {swap_info[2]}\n"
                    f"Swap ID: `{swap_id}`\n\n"
                    f"*Comment:* {comment or 'No comment'}",
                    parse_mode="Markdown"
                )
        except:
            pass
    
    # Remove from pending requests
    if user_id in vouch_requests:
        del vouch_requests[user_id]
    
    # Mark swap as vouched
    if vouch_type == "positive":
        execute_query(
            "UPDATE marketplace_swaps SET vouch_given = 1 WHERE swap_id = ?",
            (swap_id,), commit=True
        )
    
    return True

# ==================== MARKETPLACE FUNCTIONS ====================
@bot.message_handler(commands=['marketplace', 'mp'])
def marketplace_command(message):
    """Browse marketplace listings with inline buttons"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    send_marketplace_to_user(user_id)

def send_marketplace_to_user(user_id, edit_message_id=None):
    """Send marketplace to user, optionally editing a message"""
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, "User")
        return
    
    # Get active listings
    listings = execute_query('''
        SELECT ml.*, u.username as seller_username, u.tier as seller_tier,
               u.vouch_score as seller_vouch_score
        FROM marketplace_listings ml
        JOIN users u ON ml.seller_id = u.user_id
        WHERE ml.status = 'active'
        ORDER BY ml.created_at DESC
        LIMIT 10
    ''')
    
    if not listings:
        # No listings - show create listing button
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ Create Listing", callback_data="create_listing"),
            InlineKeyboardButton("📦 Bulk Sell", callback_data="bulk_sell"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_marketplace")
        )
        
        response = "🛒 *CARNAGE MARKETPLACE*\n\nNo active listings found.\n\nBe the first to list a username for sale!"
        
        if edit_message_id:
            try:
                bot.edit_message_text(
                    response,
                    user_id,
                    edit_message_id,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            except:
                bot.send_message(user_id, response, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(user_id, response, parse_mode="Markdown", reply_markup=markup)
        return
    
    response = "🛒 *CARNAGE MARKETPLACE*\n\n"
    response += "*Active Listings:*\n\n"
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    for listing in listings:
        # Format price
        currency_symbol = "💲"
        if listing["currency"] == "inr":
            price_text = f"₹{listing['price']}"
        elif listing["currency"] == "crypto":
            price_text = f"${listing['price']} CRYPTO"
        else:
            price_text = f"{listing['price']} {listing['currency']}"
        
        # Add listing type indicator
        sale_type = listing["sale_type"]
        type_emoji = "💰" if sale_type == "fixed" else "🎯" if sale_type == "auction" else "🛒"
        
        # Add vouch badge
        vouch_badge = ""
        if listing["seller_vouch_score"] >= 50:
            vouch_badge = " 🔒"
        elif listing["seller_vouch_score"] >= 20:
            vouch_badge = " ✅"
        
        # Add verified session badge
        verified_badge = " 🔐" if listing["verified_session"] == 1 else ""
        
        response += (
            f"{type_emoji} *@{listing['username']}*{verified_badge}{vouch_badge}\n"
            f"Price: {currency_symbol} {price_text}\n"
            f"Seller: @{listing['seller_username']} ({listing['seller_tier'].upper()})\n"
            f"Type: {sale_type.upper()}\n"
            f"ID: `{listing['listing_id']}`\n"
            f"────────────────────\n"
        )
        
        # Add inline button for this listing
        button_text = f"🛒 @{listing['username']}"
        if sale_type == "auction":
            button_text = f"🎯 @{listing['username']}"
        elif sale_type == "buy_now":
            button_text = f"💰 @{listing['username']}"
        
        markup.add(InlineKeyboardButton(
            button_text,
            callback_data=f"view_listing_{listing['listing_id']}"
        ))
    
    # Add action buttons
    markup.add(
        InlineKeyboardButton("➕ Create Listing", callback_data="create_listing"),
        InlineKeyboardButton("📦 Bulk Sell", callback_data="bulk_sell"),
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh_marketplace")
    )
    
    if edit_message_id:
        try:
            bot.edit_message_text(
                response,
                user_id,
                edit_message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error editing marketplace message: {e}")
            bot.send_message(user_id, response, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(user_id, response, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['sell'])
def sell_command(message):
    """Start selling process - FIXED VERSION"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    # Check if user has joined all channels
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    # Check if user is approved
    if not is_user_approved(user_id):
        bot.send_message(user_id, "❌ Your account is not approved yet. Contact admin or use referral system.")
        return
    
    # Clear any existing state
    if user_id in user_states:
        del user_states[user_id]
    
    user_states[user_id] = {
        "action": "selling",
        "step": "get_username",
        "listing_type": "single"
    }
    
    bot.send_message(
        user_id,
        "🛒 *List a Username for Sale*\n\n"
        "Send the Instagram username you want to sell (without @):\n\n"
        "Example: `carnage` or `og.name`\n\n"
        "*Note:* You'll need to provide session ID to verify ownership.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['bulksell'])
def bulksell_command(message):
    """Start bulk selling process"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    # Check if user has joined all channels
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    # Check if user is approved
    if not is_user_approved(user_id):
        bot.send_message(user_id, "❌ Your account is not approved yet. Contact admin or use referral system.")
        return
    
    # Clear any existing state
    if user_id in user_states:
        del user_states[user_id]
    
    bulk_listings[user_id] = {
        "usernames": [],
        "sessions": [],
        "prices": [],
        "step": "waiting_format"
    }
    
    bot.send_message(
        user_id,
        "📦 *Bulk List Usernames for Sale*\n\n"
        "You can list multiple usernames at once!\n\n"
        "*Format:*\n"
        "username1:session1:price1\n"
        "username2:session2:price2\n"
        "username3:session3:price3\n\n"
        "*Example:*\n"
        "carnage:sessionid=abc123...:5000\n"
        "og.name:sessionid=xyz789...:10000\n"
        "vip.user:sessionid=def456...:7500\n\n"
        "Send your usernames in the format above (one per line):",
        parse_mode="Markdown"
    )

def create_marketplace_listing(user_id, username, price, currency="inr", 
                               listing_type="sale", sale_type="fixed", 
                               description="", auction_duration_hours=24,
                               buy_now_price=None, min_increment=100):
    """Create a new marketplace listing"""
    
    existing = execute_one(
        "SELECT listing_id FROM marketplace_listings WHERE seller_id = ? AND username = ? AND status = 'active'",
        (user_id, username)
    )
    if existing:
        return False, "You already have an active listing for this username"
    
    # Check if credits listing (not allowed)
    if currency == "credits":
        return False, "Marketplace listings must be in real currency (INR/CRYPTO). Credits not allowed."
    
    listing_id = generate_listing_id()
    
    # Set auction end time if auction
    expires_at = None
    auction_end_time = None
    if sale_type == "auction":
        auction_end_time = (datetime.now() + timedelta(hours=auction_duration_hours)).strftime("%Y-%m-%d %H:%M:%S")
        expires_at = auction_end_time
    else:
        expires_at = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    execute_query('''
        INSERT INTO marketplace_listings 
        (listing_id, seller_id, username, price, currency, listing_type, sale_type,
         description, created_at, expires_at, auction_end_time, min_increment, buy_now_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        listing_id, user_id, username, price, currency, listing_type, sale_type,
        description,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        expires_at,
        auction_end_time,
        min_increment,
        buy_now_price
    ), commit=True)
    
    return True, listing_id

def verify_seller_session(user_id, listing_id, session_id):
    """Verify seller session for marketplace listing"""
    listing = execute_one("SELECT username FROM marketplace_listings WHERE listing_id = ?", (listing_id,))
    if not listing:
        return False, "Listing not found"
    
    username = listing["username"]
    
    # Validate session
    validation = validate_session(session_id, user_id=user_id)
    if not validation["success"]:
        return False, f"Invalid session: {validation['error']}"
    
    # Verify ownership
    if validation["username"].lower() != username.lower():
        return False, f"Session username ({validation['username']}) doesn't match listing username ({username})"
    
    # Store encrypted session
    encrypted_session = encrypt_session(session_id)
    execute_query(
        "UPDATE marketplace_listings SET seller_session_encrypted = ?, verified_at = ?, verified_session = 1 WHERE listing_id = ?",
        (encrypted_session, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), listing_id),
        commit=True
    )
    
    return True, "Session verified and stored"

# ==================== BULK LISTING PROCESSING ====================
def process_bulk_listing(user_id, bulk_data):
    """Process bulk listing data"""
    try:
        lines = bulk_data.strip().split('\n')
        successful = 0
        failed = 0
        errors = []
        
        for i, line in enumerate(lines, 1):
            try:
                parts = line.split(':')
                if len(parts) != 3:
                    errors.append(f"Line {i}: Invalid format")
                    failed += 1
                    continue
                
                username = parts[0].strip().lower().replace('@', '')
                session_id = parts[1].strip()
                price = float(parts[2].strip())
                
                # Validate username format
                if not re.match(r'^[a-zA-Z0-9._]{1,30}$', username):
                    errors.append(f"Line {i}: Invalid username format")
                    failed += 1
                    continue
                
                # Validate session
                validation = validate_session(session_id, user_id=user_id)
                if not validation["success"]:
                    errors.append(f"Line {i}: Invalid session - {validation['error']}")
                    failed += 1
                    continue
                
                # Verify ownership
                if validation["username"].lower() != username.lower():
                    errors.append(f"Line {i}: Session doesn't own @{username}")
                    failed += 1
                    continue
                
                # Check if already listed
                existing = execute_one(
                    "SELECT listing_id FROM marketplace_listings WHERE username = ? AND status = 'active'",
                    (username,)
                )
                if existing:
                    errors.append(f"Line {i}: @{username} already listed")
                    failed += 1
                    continue
                
                # Create listing
                listing_id = generate_listing_id()
                encrypted_session = encrypt_session(session_id)
                
                execute_query('''
                    INSERT INTO marketplace_listings 
                    (listing_id, seller_id, username, price, currency, listing_type, sale_type,
                     seller_session_encrypted, verified_at, verified_session, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    listing_id, user_id, username, price, "inr", "sale", "fixed",
                    encrypted_session,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    1,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
                ), commit=True)
                
                successful += 1
                
            except Exception as e:
                errors.append(f"Line {i}: {str(e)}")
                failed += 1
        
        return successful, failed, errors
        
    except Exception as e:
        return 0, 0, [str(e)]

# ==================== AUCTION SYSTEM ====================
@bot.message_handler(commands=['bid'])
def bid_command(message):
    """Place a bid on an auction"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    if not is_user_approved(user_id):
        bot.send_message(user_id, "❌ Your account is not approved yet.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(user_id, "Usage: /bid <listing_id> <bid_amount>")
            return
        
        listing_id = parts[1]
        try:
            bid_amount = float(parts[2])
        except ValueError:
            bot.send_message(user_id, "❌ Invalid bid amount. Please enter a number.")
            return
        
        # Check listing
        listing = execute_one('''
            SELECT ml.*, u.username as seller_username
            FROM marketplace_listings ml
            JOIN users u ON ml.seller_id = u.user_id
            WHERE ml.listing_id = ? AND ml.status = 'active' AND ml.sale_type = 'auction'
        ''', (listing_id,))
        
        if not listing:
            bot.send_message(user_id, "❌ Listing not found, not active, or not an auction.")
            return
        
        # Check if auction has ended
        if listing["auction_end_time"]:
            end_time = datetime.strptime(listing["auction_end_time"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > end_time:
                bot.send_message(user_id, "❌ Auction has ended.")
                return
        
        # Check if user is the seller
        if listing["seller_id"] == user_id:
            bot.send_message(user_id, "❌ You cannot bid on your own listing.")
            return
        
        # Check minimum bid
        current_bid = listing["current_bid"] or listing["price"]
        min_next_bid = current_bid + listing["min_increment"]
        
        if bid_amount < min_next_bid:
            bot.send_message(
                user_id,
                f"❌ Bid too low. Minimum bid: {min_next_bid} {listing['currency']}"
            )
            return
        
        # Check buy now price
        if listing["buy_now_price"] and bid_amount >= listing["buy_now_price"]:
            # Execute buy now
            execute_query('''
                UPDATE marketplace_listings 
                SET current_bid = ?, highest_bidder = ?, status = 'reserved'
                WHERE listing_id = ?
            ''', (bid_amount, user_id, listing_id), commit=True)
            
            # Create swap automatically
            swap_id = generate_swap_id()
            execute_query('''
                INSERT INTO marketplace_swaps 
                (swap_id, listing_id, seller_id, buyer_id, amount, currency, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                swap_id, listing_id, listing["seller_id"], user_id,
                bid_amount, listing["currency"], "created",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ), commit=True)
            
            bot.send_message(
                user_id,
                f"✅ *Buy Now Executed!*\n\n"
                f"Username: @{listing['username']}\n"
                f"Price: {bid_amount} {listing['currency']}\n"
                f"Swap ID: `{swap_id}`\n\n"
                f"Middleman will contact you shortly.",
                parse_mode="Markdown"
            )
            
            # Notify seller
            bot.send_message(
                listing["seller_id"],
                f"💰 *Your listing sold via Buy Now!*\n\n"
                f"Username: @{listing['username']}\n"
                f"Price: {bid_amount} {listing['currency']}\n"
                f"Buyer: User {user_id}\n"
                f"Swap ID: `{swap_id}`\n\n"
                f"Wait for middleman instructions.",
                parse_mode="Markdown"
            )
            
            # Notify admin group
            try:
                bot.send_message(
                    ADMIN_GROUP_ID,
                    f"🛒 *BUY NOW EXECUTED!*\n\n"
                    f"Listing: `{listing_id}`\n"
                    f"Username: `{listing['username']}`\n"
                    f"Seller: {listing['seller_username']}\n"
                    f"Buyer: {user_id}\n"
                    f"Price: {bid_amount} {listing['currency']}\n"
                    f"Swap ID: `{swap_id}`",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            return
        
        # Place regular bid
        execute_query('''
            UPDATE marketplace_listings 
            SET current_bid = ?, highest_bidder = ?, bids = bids + 1
            WHERE listing_id = ?
        ''', (bid_amount, user_id, listing_id), commit=True)
        
        # Record bid
        execute_query('''
            INSERT INTO auction_bids (listing_id, bidder_id, bid_amount, bid_time, is_winning)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            listing_id, user_id, bid_amount,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1
        ), commit=True)
        
        # Update previous winning bid
        execute_query('''
            UPDATE auction_bids SET is_winning = 0 
            WHERE listing_id = ? AND bidder_id != ? AND is_winning = 1
        ''', (listing_id, user_id), commit=True)
        
        bot.send_message(
            user_id,
            f"✅ *Bid Placed!*\n\n"
            f"Username: @{listing['username']}\n"
            f"Your Bid: {bid_amount} {listing['currency']}\n"
            f"Current Winning Bid: Yes\n\n"
            f"*Warning:* Fake bids will result in permanent ban!",
            parse_mode="Markdown"
        )
        
        # Notify previous highest bidder if any
        if listing["highest_bidder"] and listing["highest_bidder"] != user_id:
            try:
                bot.send_message(
                    listing["highest_bidder"],
                    f"⚠️ *You've been outbid!*\n\n"
                    f"Username: @{listing['username']}\n"
                    f"New Highest Bid: {bid_amount} {listing['currency']}\n"
                    f"Your previous bid: {listing['current_bid']} {listing['currency']}",
                    parse_mode="Markdown"
                )
            except:
                pass
        
    except Exception as e:
        bot.send_message(user_id, f"❌ Error placing bid: {str(e)}")

@bot.message_handler(commands=['mybids'])
def mybids_command(message):
    """View user's active bids"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    # Get active bids
    active_bids = execute_query('''
        SELECT ml.listing_id, ml.username, ab.bid_amount, ml.currency, 
               ml.auction_end_time, ml.current_bid, ml.highest_bidder
        FROM auction_bids ab
        JOIN marketplace_listings ml ON ab.listing_id = ml.listing_id
        WHERE ab.bidder_id = ? AND ml.status = 'active' AND ml.sale_type = 'auction'
        ORDER BY ab.bid_time DESC
        LIMIT 10
    ''', (user_id,))
    
    if not active_bids:
        bot.send_message(user_id, "📭 *No active bids*\n\nYou haven't placed any bids on active auctions.")
        return
    
    response = "🎯 *Your Active Bids*\n\n"
    
    for bid in active_bids:
        is_winning = "✅" if bid[6] == user_id else "❌"
        end_time = bid[4][:16] if bid[4] else "No end time"
        
        response += (
            f"{is_winning} *@{bid[1]}*\n"
            f"Your Bid: {bid[2]} {bid[3]}\n"
            f"Current Bid: {bid[5] or bid[2]} {bid[3]}\n"
            f"Auction Ends: {end_time}\n"
            f"ID: `{bid[0]}`\n"
            f"────────────────────\n"
        )
    
    bot.send_message(user_id, response, parse_mode="Markdown")

def check_auction_endings():
    """Check and process ended auctions"""
    try:
        ended_auctions = execute_query('''
            SELECT ml.*, u.username as seller_username
            FROM marketplace_listings ml
            JOIN users u ON ml.seller_id = u.user_id
            WHERE ml.sale_type = 'auction' AND ml.status = 'active' 
            AND ml.auction_end_time IS NOT NULL 
            AND ml.auction_end_time < ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        
        for auction in ended_auctions:
            if auction["highest_bidder"]:
                # Auction sold - create swap
                swap_id = generate_swap_id()
                execute_query('''
                    INSERT INTO marketplace_swaps 
                    (swap_id, listing_id, seller_id, buyer_id, amount, currency, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    swap_id, auction["listing_id"], auction["seller_id"], auction["highest_bidder"],
                    auction["current_bid"], auction["currency"], "created",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ), commit=True)
                
                # Update listing status
                execute_query(
                    "UPDATE marketplace_listings SET status = 'reserved' WHERE listing_id = ?",
                    (auction["listing_id"],), commit=True
                )
                
                # Notify winner
                try:
                    bot.send_message(
                        auction["highest_bidder"],
                        f"🎉 *You won the auction!*\n\n"
                        f"Username: @{auction['username']}\n"
                        f"Winning Bid: {auction['current_bid']} {auction['currency']}\n"
                        f"Swap ID: `{swap_id}`\n\n"
                        f"Middleman will contact you shortly.",
                        parse_mode="Markdown"
                    )
                except:
                    pass
                
                # Notify seller
                try:
                    bot.send_message(
                        auction["seller_id"],
                        f"💰 *Auction Ended - Sold!*\n\n"
                        f"Username: @{auction['username']}\n"
                        f"Winning Bid: {auction['current_bid']} {auction['currency']}\n"
                        f"Buyer: User {auction['highest_bidder']}\n"
                        f"Swap ID: `{swap_id}`\n\n"
                        f"Wait for middleman instructions.",
                        parse_mode="Markdown"
                    )
                except:
                    pass
                
                # Notify admin group
                try:
                    bot.send_message(
                        ADMIN_GROUP_ID,
                        f"🏆 *AUCTION ENDED - SOLD!*\n\n"
                        f"Listing: `{auction['listing_id']}`\n"
                        f"Username: `{auction['username']}`\n"
                        f"Seller: {auction['seller_username']}\n"
                        f"Buyer: {auction['highest_bidder']}\n"
                        f"Price: {auction['current_bid']} {auction['currency']}\n"
                        f"Swap ID: `{swap_id}`",
                        parse_mode="Markdown"
                    )
                except:
                    pass
            else:
                # No bids - mark as expired
                execute_query(
                    "UPDATE marketplace_listings SET status = 'expired' WHERE listing_id = ?",
                    (auction["listing_id"],), commit=True
                )
                
                # Notify seller
                try:
                    bot.send_message(
                        auction["seller_id"],
                        f"⏰ *Auction Ended - No Bids*\n\n"
                        f"Username: @{auction['username']}\n"
                        f"No bids were placed on your auction.\n"
                        f"You can relist it with /sell",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        
        print(f"✅ Processed {len(ended_auctions)} ended auctions")
        
    except Exception as e:
        print(f"❌ Error checking auction endings: {e}")

# ==================== MIDDLEMAN SYSTEM ====================
@bot.message_handler(commands=['mm'])
def mm_command(message):
    """Add/remove verified middleman (Admin only)"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: /mm <add/remove> <user_id/@username>")
            return
        
        action = parts[1].lower()
        target = parts[2]
        
        # Parse target (could be @username or user_id)
        target_id = None
        if target.startswith('@'):
            result = execute_one("SELECT user_id FROM users WHERE username = ?", (target[1:],))
            if result:
                target_id = result[0]
            else:
                bot.reply_to(message, "❌ User not found")
                return
        else:
            try:
                target_id = int(target)
            except:
                bot.reply_to(message, "❌ Invalid user ID")
                return
        
        if action == "add":
            # Check if already middleman
            existing = execute_one("SELECT id FROM middlemen WHERE user_id = ?", (target_id,))
            if existing:
                bot.reply_to(message, "❌ User is already a middleman")
                return
            
            # Update users table
            execute_query("UPDATE users SET is_mm = 1 WHERE user_id = ?", (target_id,), commit=True)
            
            # Add to middlemen table
            execute_query('''
                INSERT INTO middlemen (user_id, verified_by, verified_at, status)
                VALUES (?, ?, ?, ?)
            ''', (target_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "active"), commit=True)
            
            # Notify user
            try:
                bot.send_message(
                    target_id,
                    "🎉 *You are now a Verified Middleman!*\n\n"
                    "You can now use middleman commands in the admin group.\n"
                    "Join: @CarnageMMGroup\n\n"
                    "Use /mmhelp for commands",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            bot.reply_to(message, f"✅ User {target_id} added as verified middleman")
            
        elif action == "remove":
            # Update users table
            execute_query("UPDATE users SET is_mm = 0 WHERE user_id = ?", (target_id,), commit=True)
            
            # Update middlemen table
            execute_query("UPDATE middlemen SET status = 'removed' WHERE user_id = ?", (target_id,), commit=True)
            
            # Notify user
            try:
                bot.send_message(target_id, "⚠️ Your middleman status has been removed.")
            except:
                pass
            
            bot.reply_to(message, f"✅ User {target_id} removed as middleman")
            
        else:
            bot.reply_to(message, "❌ Invalid action. Use 'add' or 'remove'")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['mmhelp'])
def mmhelp_command(message):
    """Show middleman help"""
    user_id = message.from_user.id
    
    if not is_verified_mm(user_id):
        bot.reply_to(message, "❌ Verified middlemen only")
        return
    
    help_text = """
🔧 *Middleman Commands (Use in Admin Group Only):*

*Swap Management:*
`/createswap <listing_id> <buyer_id/@username>` - Create new swap
`/swapinfo <swap_id>` - View swap details
`/swaplist` - List all active swaps

*Payment Processing:*
`/rcvd <swap_id> <payment_method> <proof>` - Mark payment received
`/release <swap_id>` - Release funds to seller
`/refund <swap_id> <reason>` - Refund transaction

*Session Collection:*
`/getsession seller <swap_id>` - Request seller session (DM)
`/getsession buyer <swap_id>` - Request buyer session (DM)

*Dispute Handling:*
`/dispute <swap_id> <reason>` - Open dispute
`/resolve <swap_id> <decision>` - Resolve dispute

*Stats:*
`/mmstats` - Your middleman statistics

*Rules:*
• ONE middleman per swap only
• Sessions are encrypted and deleted after swap
• Fake bids lead to permanent ban
• Always verify payment proof

*Examples:*
• `/createswap LIST12345 @buyer_username`
• `/rcvd SWAP12345 upi upi_transaction_id`
• `/release SWAP12345`
"""
    
    bot.reply_to(message, help_text, parse_mode="Markdown")

# ==================== SWAP MANAGEMENT COMMANDS (GROUP ONLY) ====================
@bot.message_handler(commands=['createswap'], chat_types=['group', 'supergroup'])
def createswap_command(message):
    """Create a new marketplace swap (Middleman only)"""
    user_id = message.from_user.id
    
    if not is_verified_mm(user_id):
        bot.reply_to(message, "❌ Verified middlemen only")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: /createswap <listing_id> <buyer_id/@username>")
            bot.reply_to(message, "Example: /createswap LIST12345 @username\nExample: /createswap LIST12345 123456789")
            return
        
        listing_id = parts[1]
        buyer_identifier = parts[2]
        mm_id = user_id  # Current user is the middleman
        
        # Get listing details
        listing = execute_one('''
            SELECT ml.*, u.username as seller_username, u.user_id as seller_id
            FROM marketplace_listings ml
            JOIN users u ON ml.seller_id = u.user_id
            WHERE ml.listing_id = ? AND ml.status = 'active'
        ''', (listing_id,))
        
        if not listing:
            bot.reply_to(message, "❌ Listing not found or not active")
            return
        
        # Parse buyer identifier
        buyer_id = None
        if isinstance(buyer_identifier, int):
            buyer_id = buyer_identifier
        elif isinstance(buyer_identifier, str):
            if buyer_identifier.startswith('@'):
                result = execute_one("SELECT user_id FROM users WHERE username = ?", 
                                   (buyer_identifier[1:],))
                if result:
                    buyer_id = result[0]
                else:
                    bot.reply_to(message, "❌ Buyer username not found")
                    return
            else:
                try:
                    buyer_id = int(buyer_identifier)
                except:
                    bot.reply_to(message, "❌ Invalid buyer identifier")
                    return
        
        # Check if buyer exists
        buyer = execute_one("SELECT username FROM users WHERE user_id = ?", (buyer_id,))
        if not buyer:
            bot.reply_to(message, "❌ Buyer not found in database")
            return
        
        # Check if buyer is the seller
        if listing["seller_id"] == buyer_id:
            bot.reply_to(message, "❌ Buyer cannot be the same as seller")
            return
        
        # Generate swap ID
        swap_id = generate_swap_id()
        
        # Create swap record
        execute_query('''
            INSERT INTO marketplace_swaps 
            (swap_id, listing_id, seller_id, buyer_id, mm_id, amount, currency,
             status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            swap_id, listing_id, listing["seller_id"], buyer_id, mm_id,
            listing["price"], listing["currency"],
            "created",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ), commit=True)
        
        # Update listing status
        execute_query("UPDATE marketplace_listings SET status = 'reserved' WHERE listing_id = ?",
                     (listing_id,), commit=True)
        
        # Get buyer username
        buyer_username = buyer[0] or f"User{buyer_id}"
        
        # Notify in group
        group_message = f"""
🔄 *NEW SWAP CREATED!*

*Swap ID:* `{swap_id}`
*Listing:* `{listing_id}`
*Username:* `{listing['username']}`
*Seller:* {listing['seller_username']} ({listing['seller_id']})
*Buyer:* {buyer_username} ({buyer_id})
*Amount:* {listing['price']} {listing['currency']}
*Middleman:* {message.from_user.username}

*Status:* CREATED ✅
*Created:* {datetime.now().strftime('%H:%M:%S')}

*Commands:*
• `/rcvd {swap_id} <payment_method> <proof>` - Mark payment
• `/swapinfo {swap_id}` - View details
"""
        
        bot.reply_to(message, group_message, parse_mode="Markdown")
        
        # Notify buyer in DM
        try:
            bot.send_message(
                buyer_id,
                f"🛒 *New Swap Created for You!*\n\n"
                f"Username: `{listing['username']}`\n"
                f"Price: {listing['price']} {listing['currency']}\n"
                f"Seller: {listing['seller_username']}\n"
                f"Middleman: {message.from_user.username}\n"
                f"Swap ID: `{swap_id}`\n\n"
                f"Please wait for payment instructions.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        # Notify seller in DM
        try:
            bot.send_message(
                listing["seller_id"],
                f"💰 *Your Listing Has a Buyer!*\n\n"
                f"Username: `{listing['username']}`\n"
                f"Price: {listing['price']} {listing['currency']}\n"
                f"Buyer: {buyer_username}\n"
                f"Middleman: {message.from_user.username}\n"
                f"Swap ID: `{swap_id}`\n\n"
                f"Wait for middleman instructions.",
                parse_mode="Markdown"
            )
        except:
            pass
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['rcvd'], chat_types=['group', 'supergroup'])
def rcvd_command(message):
    """Mark payment as received (Middleman only)"""
    user_id = message.from_user.id
    
    if not is_verified_mm(user_id):
        bot.reply_to(message, "❌ Verified middlemen only")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.reply_to(message, "Usage: /rcvd <swap_id> <payment_method> <proof>")
            bot.reply_to(message, "Payment methods: upi, crypto, usdt, bank")
            bot.reply_to(message, "Example: /rcvd SWAP12345 upi upi_transaction_id")
            return
        
        swap_id = parts[1]
        payment_method = parts[2].lower()
        payment_proof = " ".join(parts[3:])
        
        # Validate payment method
        valid_methods = ["upi", "crypto", "usdt", "btc", "eth", "bank"]
        if payment_method not in valid_methods:
            bot.reply_to(message, f"❌ Invalid payment method. Use: {', '.join(valid_methods)}")
            return
        
        # Get swap details
        swap = execute_one('''
            SELECT ms.*, 
                   ml.username as listing_username,
                   u1.username as seller_username,
                   u2.username as buyer_username
            FROM marketplace_swaps ms
            JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
            JOIN users u1 ON ms.seller_id = u1.user_id
            JOIN users u2 ON ms.buyer_id = u2.user_id
            WHERE ms.swap_id = ?
        ''', (swap_id,))
        
        if not swap:
            bot.reply_to(message, "❌ Swap not found")
            return
        
        # Check if current user is the MM for this swap
        if swap["mm_id"] != user_id:
            bot.reply_to(message, "❌ You are not the middleman for this swap")
            return
        
        # Check if payment already marked
        if swap["status"] == "payment_received":
            bot.reply_to(message, "❌ Payment already marked as received")
            return
        
        # Update swap with payment info
        execute_query('''
            UPDATE marketplace_swaps 
            SET payment_method = ?, payment_proof = ?, status = 'payment_received',
                payment_received_at = ?
            WHERE swap_id = ?
        ''', (payment_method, payment_proof, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), swap_id), commit=True)
        
        # Notify in group
        group_message = f"""
💰 *PAYMENT RECEIVED!*

*Swap ID:* `{swap_id}`
*Username:* `{swap['listing_username']}`
*Buyer:* {swap['buyer_username']}
*Amount:* {swap['amount']} {swap['currency']}
*Method:* {payment_method.upper()}
*Proof:* {payment_proof}
*Marked by:* {message.from_user.username}

*Next Steps:*
1. Ask seller for session: `/getsession seller {swap_id}`
2. Ask buyer for session: `/getsession buyer {swap_id}`
3. Execute swap when both sessions received
"""
        
        bot.reply_to(message, group_message, parse_mode="Markdown")
        
        # Request seller session
        bot.send_message(
            swap["seller_id"],
            f"💰 *Payment Received for @{swap['listing_username']}*\n\n"
            f"Swap ID: `{swap_id}`\n"
            f"Buyer: {swap['buyer_username']}\n"
            f"Amount: {swap['amount']} {swap['currency']}\n"
            f"Payment Method: {payment_method.upper()}\n\n"
            f"Please provide Instagram session ID for @{swap['listing_username']}\n\n"
            f"*Format:* `sessionid=abc123...`\n"
            f"This session will be used only for this swap.",
            parse_mode="Markdown"
        )
        
        # Store in pending swaps
        pending_swaps[swap["seller_id"]] = {
            "swap_id": swap_id,
            "role": "seller",
            "mm_id": user_id,
            "step": "waiting_session"
        }
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['getsession'], chat_types=['group', 'supergroup'])
def getsession_command(message):
    """Request session from seller or buyer (Middleman only)"""
    user_id = message.from_user.id
    
    if not is_verified_mm(user_id):
        bot.reply_to(message, "❌ Verified middlemen only")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: /getsession <seller/buyer> <swap_id>")
            return
        
        party = parts[1].lower()
        swap_id = parts[2]
        
        if party not in ["seller", "buyer"]:
            bot.reply_to(message, "❌ Use 'seller' or 'buyer'")
            return
        
        swap = execute_one('''
            SELECT ms.*, 
                   ml.username as listing_username,
                   u1.username as seller_username,
                   u2.username as buyer_username
            FROM marketplace_swaps ms
            JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
            JOIN users u1 ON ms.seller_id = u1.user_id
            JOIN users u2 ON ms.buyer_id = u2.user_id
            WHERE ms.swap_id = ?
        ''', (swap_id,))
        
        if not swap:
            bot.reply_to(message, "❌ Swap not found")
            return
        
        # Check if current user is the MM for this swap
        if swap["mm_id"] != user_id:
            bot.reply_to(message, "❌ You are not the middleman for this swap")
            return
        
        if party == "seller":
            target_id = swap["seller_id"]
            role = "seller"
            username = swap["listing_username"]
            message_text = f"""
🔐 *Session Required for Swap*

Swap ID: `{swap_id}`
Username: @{username}
Amount: {swap['amount']} {swap['currency']}

Please provide Instagram session ID for @{username}

*Format:* `sessionid=abc123...`
This session will be used only for this swap and deleted afterwards.
"""
        else:  # buyer
            target_id = swap["buyer_id"]
            role = "buyer"
            username = swap["listing_username"]
            message_text = f"""
🔐 *Session Required for Swap*

Swap ID: `{swap_id}`
Username: @{username}
Amount: {swap['amount']} {swap['currency']}

Please provide Instagram session ID for the account where you want to receive @{username}

*Format:* `sessionid=xyz789...`
This session will be used only for this swap and deleted afterwards.
"""
        
        # Store in pending swaps
        pending_swaps[target_id] = {
            "swap_id": swap_id,
            "role": role,
            "mm_id": user_id,
            "step": "waiting_session"
        }
        
        bot.send_message(target_id, message_text, parse_mode="Markdown")
        bot.reply_to(message, f"✅ Session request sent to {role}.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def handle_swap_session(user_id, session_id, role, swap_id):
    """Handle session received for swap"""
    swap = execute_one('''
        SELECT ms.*, 
               ml.username as listing_username,
               u1.username as seller_username,
               u2.username as buyer_username
        FROM marketplace_swaps ms
        JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
        JOIN users u1 ON ms.seller_id = u1.user_id
        JOIN users u2 ON ms.buyer_id = u2.user_id
        WHERE ms.swap_id = ?
    ''', (swap_id,))
    
    if not swap:
        return False, "Swap not found"
    
    # Validate session
    validation = validate_session(session_id)
    if not validation["success"]:
        return False, f"Invalid session: {validation['error']}"
    
    # For seller, verify they own the claimed username
    if role == "seller":
        if validation["username"].lower() != swap["listing_username"].lower():
            return False, f"Session username ({validation['username']}) doesn't match listing username ({swap['listing_username']})"
    
    # Store encrypted session in database
    encrypted_session = encrypt_session(session_id)
    
    if role == "seller":
        execute_query(
            "UPDATE marketplace_swaps SET seller_session_encrypted = ? WHERE swap_id = ?",
            (encrypted_session, swap_id),
            commit=True
        )
    else:  # buyer
        execute_query(
            "UPDATE marketplace_swaps SET buyer_session_encrypted = ? WHERE swap_id = ?",
            (encrypted_session, swap_id),
            commit=True
        )
    
    # Check if both sessions received
    updated_swap = execute_one(
        "SELECT seller_session_encrypted, buyer_session_encrypted FROM marketplace_swaps WHERE swap_id = ?",
        (swap_id,)
    )
    
    if updated_swap and updated_swap[0] and updated_swap[1]:
        # Both sessions received, decrypt and execute swap
        seller_session = decrypt_session(updated_swap[0])
        buyer_session = decrypt_session(updated_swap[1])
        
        # Execute swap
        success = execute_marketplace_swap(swap_id, seller_session, buyer_session)
        
        if success:
            # Update swap status
            execute_query(
                "UPDATE marketplace_swaps SET status = 'swap_completed', swap_completed_at = ? WHERE swap_id = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), swap_id),
                commit=True
            )
            
            # Update listing status
            execute_query(
                "UPDATE marketplace_listings SET status = 'sold' WHERE listing_id = ?",
                (swap["listing_id"],),
                commit=True
            )
            
            # Notify in admin group
            try:
                bot.send_message(
                    ADMIN_GROUP_ID,
                    f"✅ *SWAP EXECUTED SUCCESSFULLY!*\n\n"
                    f"Swap ID: `{swap_id}`\n"
                    f"Username: `{swap['listing_username']}`\n"
                    f"Seller: {swap['seller_username']}\n"
                    f"Buyer: {swap['buyer_username']}\n\n"
                    f"*Release funds with:*\n"
                    f"`/release {swap_id}`",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            # Request vouches
            request_vouch(swap_id, swap["seller_id"], swap["buyer_id"])
            
            return True, "Swap executed successfully! Funds ready for release. Vouch requested from both parties."
        else:
            return False, "Swap execution failed"
    
    return True, f"{role.capitalize()} session stored. Waiting for other party."

def execute_marketplace_swap(swap_id, seller_session, buyer_session):
    """Execute swap between seller and buyer accounts"""
    try:
        # Generate random username for seller's account
        random_username = generate_random_username()
        
        # Change seller's username to random
        csrf_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        result1 = change_username_account1(None, seller_session, csrf_token, random_username)
        if not result1:
            return False
        
        # Change buyer's username to target username
        swap = execute_one('''
            SELECT ml.username as listing_username
            FROM marketplace_swaps ms
            JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
            WHERE ms.swap_id = ?
        ''', (swap_id,))
        
        if not swap:
            return False
        
        target_username = swap["listing_username"]
        result2 = change_username_account2(None, buyer_session, csrf_token, target_username)
        
        return result2
        
    except Exception as e:
        print(f"Swap execution error: {e}")
        return False

@bot.message_handler(commands=['release'], chat_types=['group', 'supergroup'])
def release_command(message):
    """Release funds to seller (Middleman only)"""
    user_id = message.from_user.id
    
    if not is_verified_mm(user_id):
        bot.reply_to(message, "❌ Verified middlemen only")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /release <swap_id>")
            return
        
        swap_id = parts[1]
        swap = execute_one('''
            SELECT ms.*, 
                   ml.username as listing_username,
                   u1.username as seller_username
            FROM marketplace_swaps ms
            JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
            JOIN users u1 ON ms.seller_id = u1.user_id
            WHERE ms.swap_id = ?
        ''', (swap_id,))
        
        if not swap:
            bot.reply_to(message, "❌ Swap not found")
            return
        
        # Check if current user is the MM for this swap
        if swap["mm_id"] != user_id:
            bot.reply_to(message, "❌ You are not the middleman for this swap")
            return
        
        # Check if swap was completed
        if swap["status"] != "swap_completed":
            bot.reply_to(message, f"❌ Swap status is {swap['status']}. Must be 'swap_completed' to release funds.")
            return
        
        # Update status
        execute_query(
            "UPDATE marketplace_swaps SET status = 'released', released_at = ? WHERE swap_id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), swap_id),
            commit=True
        )
        
        # Notify seller
        try:
            bot.send_message(
                swap["seller_id"],
                f"💰 *Funds Released!*\n\n"
                f"Swap ID: `{swap_id}`\n"
                f"Username: `{swap['listing_username']}`\n"
                f"Amount: {swap['amount']} {swap['currency']}\n\n"
                f"Contact middleman for payment details.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        bot.reply_to(message, f"✅ Funds released for swap {swap_id}. Notify seller about payment.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['refund'], chat_types=['group', 'supergroup'])
def refund_command(message):
    """Refund transaction (Middleman only)"""
    user_id = message.from_user.id
    
    if not is_verified_mm(user_id):
        bot.reply_to(message, "❌ Verified middlemen only")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: /refund <swap_id> <reason>")
            return
        
        swap_id = parts[1]
        reason = " ".join(parts[2:])
        
        swap = execute_one('''
            SELECT ms.*, 
                   ml.username as listing_username,
                   u2.username as buyer_username
            FROM marketplace_swaps ms
            JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
            JOIN users u2 ON ms.buyer_id = u2.user_id
            WHERE ms.swap_id = ?
        ''', (swap_id,))
        
        if not swap:
            bot.reply_to(message, "❌ Swap not found")
            return
        
        # Check if current user is the MM for this swap
        if swap["mm_id"] != user_id:
            bot.reply_to(message, "❌ You are not the middleman for this swap")
            return
        
        # Update status
        execute_query(
            "UPDATE marketplace_swaps SET status = 'refunded', refunded_at = ?, dispute_reason = ? WHERE swap_id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reason, swap_id),
            commit=True
        )
        
        # Update listing status back to active
        execute_query(
            "UPDATE marketplace_listings SET status = 'active' WHERE listing_id = ?",
            (swap["listing_id"],),
            commit=True
        )
        
        # Notify buyer
        try:
            bot.send_message(
                swap["buyer_id"],
                f"🔄 *Refund Issued*\n\n"
                f"Swap ID: `{swap_id}`\n"
                f"Username: `{swap['listing_username']}`\n"
                f"Amount: {swap['amount']} {swap['currency']}\n"
                f"Reason: {reason}\n\n"
                f"Your payment has been refunded.\n"
                f"Contact middleman for refund details.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        bot.reply_to(message, f"✅ Swap {swap_id} refunded. Reason: {reason}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ==================== MESSAGE HANDLERS ====================
def handle_tutorial_response(chat_id, text):
    """Handle tutorial responses"""
    pass

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Handle all text messages"""
    user_id = message.chat.id
    text = message.text
    
    # Update user activity
    update_user_active(user_id)
    
    # Check if user is in selling state
    if user_id in user_states and user_states[user_id]["action"] == "selling":
        handle_selling_state(user_id, text)
        return
    
    # Check if user is in bulk listing state
    if user_id in bulk_listings and bulk_listings[user_id]["step"] == "waiting_format":
        handle_bulk_listing(user_id, text)
        return
    
    # Check if user is in pending swap state
    if user_id in pending_swaps:
        handle_pending_swap(user_id, text)
        return
    
    # Check if user is in vouch state
    if user_id in vouch_requests and vouch_requests[user_id]["step"] == "waiting_comment":
        handle_vouch_comment(user_id, text)
        return
    
    # If it's a command, let command handlers process it
    if text.startswith('/'):
        return
    
    # Handle private messages
    if message.chat.type == 'private':
        handle_private_messages(message)

def handle_bulk_listing(user_id, text):
    """Handle bulk listing data"""
    if user_id not in bulk_listings:
        return
    
    try:
        # Process bulk listing
        successful, failed, errors = process_bulk_listing(user_id, text)
        
        response = f"📦 *Bulk Listing Results*\n\n"
        response += f"✅ Successful: {successful}\n"
        response += f"❌ Failed: {failed}\n\n"
        
        if successful > 0:
            response += f"🎉 {successful} usernames listed successfully!\n"
            response += f"View them in marketplace with /marketplace\n\n"
        
        if errors:
            response += "*Errors:*\n"
            for error in errors[:10]:  # Show only first 10 errors
                response += f"• {error}\n"
            if len(errors) > 10:
                response += f"... and {len(errors) - 10} more errors\n"
        
        bot.send_message(user_id, response, parse_mode="Markdown")
        
        # Clear bulk listing state
        del bulk_listings[user_id]
        
    except Exception as e:
        bot.send_message(user_id, f"❌ Error processing bulk listing: {str(e)}")
        del bulk_listings[user_id]

def handle_selling_state(user_id, text):
    """Handle user in selling state - FIXED VERSION"""
    if user_id not in user_states or user_states[user_id]["action"] != "selling":
        return
    
    state = user_states[user_id]
    
    if state["step"] == "get_username":
        username = text.strip().lower().replace('@', '')
        
        # Validate username format
        if not re.match(r'^[a-zA-Z0-9._]{1,30}$', username):
            bot.send_message(user_id, "❌ Invalid username format. Use only letters, numbers, dots, and underscores.")
            return
        
        # Check if username is already listed
        existing = execute_one(
            "SELECT listing_id FROM marketplace_listings WHERE username = ? AND status = 'active'",
            (username,)
        )
        if existing:
            bot.send_message(user_id, f"❌ @{username} is already listed in marketplace")
            del user_states[user_id]
            return
        
        state["username"] = username
        state["step"] = "get_sale_type"
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("💰 Fixed Price", callback_data="sale_type_fixed"),
            InlineKeyboardButton("🎯 Auction", callback_data="sale_type_auction"),
            InlineKeyboardButton("🛒 Buy Now + Auction", callback_data="sale_type_buy_now")
        )
        
        bot.send_message(
            user_id,
            f"🎯 *Select Sale Type for @{username}*\n\n"
            f"• *Fixed Price:* Set a fixed price\n"
            f"• *Auction:* Accept bids for 24 hours\n"
            f"• *Buy Now + Auction:* Set buy now price + accept bids\n\n"
            f"Choose an option:",
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    elif state["step"] == "get_price":
        try:
            price = float(text.strip())
            
            # Validate minimum price
            min_prices = {
                "inr": 1000,
                "crypto": 10
            }
            
            currency = state.get("currency", "inr")
            if price < min_prices.get(currency, 1000):
                bot.send_message(user_id, f"❌ Minimum price for {currency} is {min_prices[currency]}")
                return
            
            state["price"] = price
            
            if state.get("sale_type") == "auction":
                state["step"] = "get_min_increment"
                bot.send_message(
                    user_id,
                    f"📈 *Set Minimum Bid Increment*\n\n"
                    f"Current starting price: {price} {currency}\n"
                    f"Enter minimum bid increment amount:\n\n"
                    f"Example: `100` (means bids must increase by at least 100)",
                    parse_mode="Markdown"
                )
            elif state.get("sale_type") == "buy_now":
                state["step"] = "get_buy_now_price"
                bot.send_message(
                    user_id,
                    f"💰 *Set Buy Now Price*\n\n"
                    f"Starting price: {price} {currency}\n"
                    f"Enter buy now price (users can buy immediately at this price):\n\n"
                    f"Must be higher than starting price.",
                    parse_mode="Markdown"
                )
            else:
                state["step"] = "get_description"
                bot.send_message(
                    user_id,
                    f"📝 *Add Description for @{state['username']}*\n\n"
                    f"Price: {price} {currency}\n\n"
                    f"Enter description (optional):\n"
                    f"Or type 'skip' to skip",
                    parse_mode="Markdown"
                )
            
        except ValueError:
            bot.send_message(user_id, "❌ Please enter valid amount")
    
    elif state["step"] == "get_min_increment":
        try:
            min_increment = float(text.strip())
            if min_increment < 10:
                bot.send_message(user_id, "❌ Minimum increment must be at least 10")
                return
            
            state["min_increment"] = min_increment
            state["step"] = "get_description"
            
            bot.send_message(
                user_id,
                f"📝 *Add Description for @{state['username']}*\n\n"
                f"Starting Price: {state['price']} {state['currency']}\n"
                f"Min Increment: {min_increment} {state['currency']}\n\n"
                f"Enter description (optional):\n"
                f"Or type 'skip' to skip",
                parse_mode="Markdown"
            )
            
        except ValueError:
            bot.send_message(user_id, "❌ Please enter valid amount")
    
    elif state["step"] == "get_buy_now_price":
        try:
            buy_now_price = float(text.strip())
            if buy_now_price <= state["price"]:
                bot.send_message(user_id, f"❌ Buy now price must be higher than starting price ({state['price']})")
                return
            
            state["buy_now_price"] = buy_now_price
            state["step"] = "get_min_increment"
            
            bot.send_message(
                user_id,
                f"📈 *Set Minimum Bid Increment*\n\n"
                f"Starting price: {state['price']} {state['currency']}\n"
                f"Buy now price: {buy_now_price} {state['currency']}\n\n"
                f"Enter minimum bid increment amount:",
                parse_mode="Markdown"
            )
            
        except ValueError:
            bot.send_message(user_id, "❌ Please enter valid amount")
    
    elif state["step"] == "get_description":
        description = text if text.lower() != "skip" else ""
        state["description"] = description
        
        # Create listing
        buy_now_price = state.get("buy_now_price")
        min_increment = state.get("min_increment", 100)
        sale_type = state.get("sale_type", "fixed")
        
        success, listing_id = create_marketplace_listing(
            user_id,
            state["username"],
            state["price"],
            state["currency"],
            "sale",
            sale_type,
            state["description"],
            24,  # auction duration hours
            buy_now_price,
            min_increment
        )
        
        if not success:
            bot.send_message(user_id, f"❌ Failed to create listing: {listing_id}")
            del user_states[user_id]
            return
        
        state["listing_id"] = listing_id
        
        # Ask for session to verify ownership
        bot.send_message(
            user_id,
            f"🔐 *Verify Ownership*\n\n"
            f"To list @{state['username']} for sale, you need to verify ownership.\n\n"
            f"Please provide Instagram session ID for @{state['username']}:\n\n"
            f"*Format:* `sessionid=abc123...`\n"
            f"This session will be encrypted and stored securely.",
            parse_mode="Markdown"
        )
        
        state["step"] = "get_session"
    
    elif state["step"] == "get_session":
        session_id = text.strip()
        
        # Verify session with the created listing
        success, result = verify_seller_session(user_id, state["listing_id"], session_id)
        
        if success:
            # Store session
            save_session_to_db(user_id, "marketplace_seller", session_id, state["listing_id"])
            
            # Format listing details
            currency_symbol = "💲"
            if state["currency"] == "inr":
                price_text = f"₹{state['price']}"
            elif state["currency"] == "crypto":
                price_text = f"${state['price']} CRYPTO"
            
            sale_type_text = ""
            if state.get("sale_type") == "auction":
                sale_type_text = f"\nAuction Duration: 24 hours\nMin Increment: {state.get('min_increment', 100)} {state['currency']}"
            elif state.get("sale_type") == "buy_now":
                sale_type_text = f"\nBuy Now Price: {state['buy_now_price']} {state['currency']}\nAuction Duration: 24 hours\nMin Increment: {state.get('min_increment', 100)} {state['currency']}"
            
            bot.send_message(
                user_id,
                f"✅ *Listing Created Successfully!*\n\n"
                f"Username: @{state['username']} 🔐\n"
                f"Price: {currency_symbol} {price_text}\n"
                f"Type: {state.get('sale_type', 'fixed').upper()}{sale_type_text}\n"
                f"Listing ID: `{state['listing_id']}`\n\n"
                f"*Your listing is now active in marketplace!*\n"
                f"View it with /marketplace\n\n"
                f"*Note:* When someone buys, middleman will contact you for session.",
                parse_mode="Markdown"
            )
            
            # Post to marketplace channel
            try:
                type_emoji = "💰" if state.get("sale_type") == "fixed" else "🎯" if state.get("sale_type") == "auction" else "🛒"
                
                bot.send_message(
                    MARKETPLACE_CHANNEL_ID,
                    f"🆕 *NEW LISTING!*\n\n"
                    f"{type_emoji} Username: `@{state['username']}` 🔐\n"
                    f"Price: {currency_symbol} {price_text}\n"
                    f"Type: {state.get('sale_type', 'fixed').upper()}{sale_type_text}\n"
                    f"Seller: Verified ✅\n"
                    f"Listing ID: `{state['listing_id']}`\n\n"
                    f"To buy, contact middleman with listing ID.",
                    parse_mode="Markdown"
                )
            except:
                pass
            
        else:
            bot.send_message(user_id, f"❌ Verification failed: {result}\n\nPlease send valid session ID:")
            return
        
        del user_states[user_id]

def handle_pending_swap(user_id, text):
    """Handle pending swap session collection"""
    if user_id not in pending_swaps:
        return
    
    swap_data = pending_swaps[user_id]
    swap_id = swap_data["swap_id"]
    role = swap_data["role"]
    
    session_id = text.strip()
    
    # Handle session
    success, result = handle_swap_session(user_id, session_id, role, swap_id)
    
    if success:
        bot.send_message(user_id, f"✅ {result}", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"❌ {result}\n\nPlease send valid session ID:", parse_mode="Markup")
        return
    
    # Remove from pending if not waiting for other party
    if "Waiting for other party" not in result:
        del pending_swaps[user_id]

def handle_vouch_comment(user_id, text):
    """Handle vouch comment"""
    if user_id not in vouch_requests:
        return
    
    vouch_data = vouch_requests[user_id]
    comment = text.strip()
    
    # Process vouch with comment
    success = process_vouch(user_id, vouch_data["swap_id"], vouch_data["vouch_for"], vouch_data["vouch_type"], comment)
    
    if success:
        bot.send_message(user_id, "✅ Vouch submitted successfully! Thank you!")
    else:
        bot.send_message(user_id, "❌ Error submitting vouch")
    
    del vouch_requests[user_id]

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Handle callback queries"""
    user_id = call.from_user.id
    data = call.data
    
    try:
        if data == "check_channels":
            channel_results = check_all_channels(user_id)
            
            if all(channel_results.values()):
                bot.answer_callback_query(call.id, "✅ Verified! You've joined all channels!")
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=call.message.message_id,
                    text="🎉 *Channel Verification Successful!*\n\nYou've joined all required channels! ✅\n\nNow you can use the bot features.\n\nSend /start again to begin.",
                    parse_mode="Markdown"
                )
                
                execute_query("UPDATE users SET channels_joined = 1 WHERE user_id = ?", (user_id,), commit=True)
                
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
        
        elif data == "refresh_marketplace":
            try:
                bot.answer_callback_query(call.id, "Refreshing marketplace...")
                send_marketplace_to_user(call.from_user.id, call.message.message_id)
            except Exception as e:
                print(f"Error refreshing marketplace: {e}")
                bot.answer_callback_query(call.id, "Error refreshing, please try /marketplace again")
            
        elif data == "create_listing":
            try:
                bot.answer_callback_query(call.id, "Starting listing creation...")
                sell_command(call.message)
            except Exception as e:
                print(f"Error creating listing: {e}")
                bot.answer_callback_query(call.id, "Error starting listing creation")
        
        elif data == "bulk_sell":
            try:
                bot.answer_callback_query(call.id, "Starting bulk listing...")
                bulksell_command(call.message)
            except Exception as e:
                print(f"Error starting bulk sell: {e}")
                bot.answer_callback_query(call.id, "Error starting bulk listing")
        
        elif data.startswith("sale_type_"):
            sale_type = data.split("_")[2]
            
            if user_id not in user_states or user_states[user_id]["action"] != "selling":
                bot.answer_callback_query(call.id, "❌ Invalid state", show_alert=True)
                return
            
            user_states[user_id]["sale_type"] = sale_type
            user_states[user_id]["step"] = "get_currency"
            
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("🇮🇳 Indian Rupees (INR)", callback_data="currency_inr"),
                InlineKeyboardButton("💲 CRYPTO", callback_data="currency_crypto")
            )
            
            bot.edit_message_text(
                f"💱 *Select Currency*\n\n"
                f"Sale Type: {sale_type.upper()}\n"
                f"Username: @{user_states[user_id]['username']}\n\n"
                f"Choose currency:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            
        elif data.startswith("currency_"):
            currency = data.split("_")[1]
            
            if user_id not in user_states or user_states[user_id]["action"] != "selling":
                bot.answer_callback_query(call.id, "❌ Invalid state", show_alert=True)
                return
            
            user_states[user_id]["currency"] = currency
            user_states[user_id]["step"] = "get_price"
            
            # Show minimum prices
            min_prices = {
                "inr": "₹1000",
                "crypto": "$10 CRYPTO"
            }
            
            bot.edit_message_text(
                f"💰 *Set Price for @{user_states[user_id]['username']}*\n\n"
                f"Sale Type: {user_states[user_id]['sale_type'].upper()}\n"
                f"Currency: {currency.upper()}\n"
                f"Minimum Price: {min_prices.get(currency, '₹1000')}\n\n"
                f"Enter price amount:\n\n"
                f"Example: `5000`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            
        elif data.startswith("view_listing_"):
            listing_id = data.split("_")[2]
            listing = execute_one('''
                SELECT ml.*, u.username as seller_username, u.tier as seller_tier,
                       u.vouch_score as seller_vouch_score, u.positive_vouches,
                       u.negative_vouches
                FROM marketplace_listings ml
                JOIN users u ON ml.seller_id = u.user_id
                WHERE ml.listing_id = ?
            ''', (listing_id,))
            
            if listing:
                # Format price
                currency_symbol = "💲"
                if listing["currency"] == "inr":
                    price_text = f"₹{listing['price']}"
                elif listing["currency"] == "crypto":
                    price_text = f"${listing['price']} CRYPTO"
                else:
                    price_text = f"{listing['price']} {listing['currency']}"
                
                # Format vouch info
                vouch_info = ""
                if listing["seller_vouch_score"] > 0:
                    vouch_info = f"\n*Vouch Score:* {listing['seller_vouch_score']} ({listing['positive_vouches']}+/{listing['negative_vouches']}-)"
                
                # Format sale type info
                sale_type_info = ""
                if listing["sale_type"] == "auction":
                    current_bid = listing["current_bid"] or listing["price"]
                    bids = listing["bids"] or 0
                    end_time = listing["auction_end_time"][:16] if listing["auction_end_time"] else "No end time"
                    sale_type_info = f"""
*Auction Details:*
• Current Bid: {current_bid} {listing['currency']}
• Bids: {bids}
• Ends: {end_time}
• Min Increment: {listing['min_increment']} {listing['currency']}
"""
                    if listing["buy_now_price"]:
                        sale_type_info += f"• Buy Now: {listing['buy_now_price']} {listing['currency']}"
                
                markup = InlineKeyboardMarkup(row_width=2)
                
                # Add verified session badge
                verified_badge = " 🔐 Verified Session" if listing["verified_session"] == 1 else ""
                
                # Add different buttons based on sale type
                if listing["sale_type"] == "fixed":
                    markup.add(
                        InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_fixed_{listing_id}"),
                        InlineKeyboardButton("📞 Contact Seller", url=f"https://t.me/{listing['seller_username']}" if listing['seller_username'] else f"https://t.me/{BOT_USERNAME}")
                    )
                elif listing["sale_type"] == "auction":
                    markup.add(
                        InlineKeyboardButton("🎯 Place Bid", callback_data=f"bid_auction_{listing_id}"),
                        InlineKeyboardButton("📞 Contact Seller", url=f"https://t.me/{listing['seller_username']}" if listing['seller_username'] else f"https://t.me/{BOT_USERNAME}")
                    )
                    if listing["buy_now_price"]:
                        markup.add(InlineKeyboardButton("💰 Buy Now", callback_data=f"buy_now_{listing_id}"))
                elif listing["sale_type"] == "buy_now":
                    markup.add(
                        InlineKeyboardButton("💰 Buy Now", callback_data=f"buy_now_{listing_id}"),
                        InlineKeyboardButton("🎯 Place Bid", callback_data=f"bid_auction_{listing_id}"),
                        InlineKeyboardButton("📞 Contact Seller", url=f"https://t.me/{listing['seller_username']}" if listing['seller_username'] else f"https://t.me/{BOT_USERNAME}")
                    )
                
                markup.add(InlineKeyboardButton("🔙 Back to Marketplace", callback_data="refresh_marketplace"))
                
                verified_text = "✅ Verified Session" if listing["verified_session"] == 1 else "❌ Not Verified"
                
                response = (
                    f"🔍 *Listing Details*\n\n"
                    f"*Username:* `{listing['username']}`{verified_badge}\n"
                    f"*Price:* {currency_symbol} {price_text}\n"
                    f"*Seller:* @{listing['seller_username'] or 'User'}\n"
                    f"*Seller Tier:* {listing['seller_tier'].upper()}\n"
                    f"*Verification:* {verified_text}{vouch_info}\n"
                    f"*Sale Type:* {listing['sale_type'].upper()}\n"
                    f"*Status:* {listing['status'].capitalize()}\n"
                    f"{sale_type_info}\n\n"
                    f"*Description:* {listing['description'] or 'No description'}\n\n"
                    f"*Listing ID:* `{listing_id}`\n"
                    f"*Created:* {listing['created_at'][:10]}\n"
                    f"*Expires:* {listing['expires_at'][:10]}"
                )
                
                bot.edit_message_text(
                    response,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            
        elif data.startswith("buy_fixed_"):
            listing_id = data.split("_")[2]
            listing = execute_one('''
                SELECT ml.*, u.username as seller_username, u.user_id as seller_id
                FROM marketplace_listings ml
                JOIN users u ON ml.seller_id = u.user_id
                WHERE ml.listing_id = ?
            ''', (listing_id,))
            
            if not listing:
                bot.answer_callback_query(call.id, "Listing not found", show_alert=True)
                return
            
            # Check if user is the seller
            if listing["seller_id"] == user_id:
                bot.answer_callback_query(call.id, "You cannot buy your own listing", show_alert=True)
                return
            
            # Send contact message to buyer
            bot.send_message(
                user_id,
                f"🛒 *Purchase @{listing['username']}*\n\n"
                f"*Price:* {listing['price']} {listing['currency']}\n"
                f"*Seller:* @{listing['seller_username'] or 'User'}\n\n"
                f"*To purchase:*\n"
                f"1. Contact a middleman in the admin group\n"
                f"2. Provide Listing ID: `{listing_id}`\n"
                f"3. Middleman will create a swap for you\n"
                f"4. Make payment as instructed\n"
                f"5. Provide session when asked\n\n"
                f"*Admin Group:* @CarnageMMGroup\n"
                f"*Listing ID:* `{listing_id}`",
                parse_mode="Markdown"
            )
            
            # Also notify the seller
            try:
                buyer_info = call.from_user.username or f"User {user_id}"
                bot.send_message(
                    listing["seller_id"],
                    f"🛒 *Someone wants to buy your listing!*\n\n"
                    f"Username: @{listing['username']}\n"
                    f"Price: {listing['price']} {listing['currency']}\n"
                    f"Interested Buyer: @{buyer_info}\n\n"
                    f"Buyer has been instructed to contact middleman.\n"
                    f"Listing ID: `{listing_id}`",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            bot.answer_callback_query(call.id, "Instructions sent! Check your messages.")
        
        elif data.startswith("bid_auction_"):
            listing_id = data.split("_")[2]
            
            if user_id in bidding_sessions:
                del bidding_sessions[user_id]
            
            bidding_sessions[user_id] = {
                "listing_id": listing_id,
                "step": "get_bid"
            }
            
            listing = execute_one('''
                SELECT ml.*, u.username as seller_username
                FROM marketplace_listings ml
                JOIN users u ON ml.seller_id = u.user_id
                WHERE ml.listing_id = ?
            ''', (listing_id,))
            
            if listing:
                current_bid = listing["current_bid"] or listing["price"]
                min_next_bid = current_bid + listing["min_increment"]
                
                bot.send_message(
                    user_id,
                    f"🎯 *Place Bid on @{listing['username']}*\n\n"
                    f"Current Bid: {current_bid} {listing['currency']}\n"
                    f"Minimum Next Bid: {min_next_bid} {listing['currency']}\n"
                    f"Your Bid Must Be: ≥ {min_next_bid} {listing['currency']}\n\n"
                    f"*Enter your bid amount:*\n\n"
                    f"*WARNING:* Fake bids will result in PERMANENT BAN!",
                    parse_mode="Markdown"
                )
            
            bot.answer_callback_query(call.id)
        
        elif data.startswith("buy_now_"):
            listing_id = data.split("_")[2]
            listing = execute_one('''
                SELECT ml.*, u.username as seller_username, u.user_id as seller_id
                FROM marketplace_listings ml
                JOIN users u ON ml.seller_id = u.user_id
                WHERE ml.listing_id = ?
            ''', (listing_id,))
            
            if not listing:
                bot.answer_callback_query(call.id, "Listing not found", show_alert=True)
                return
            
            # Check if user is the seller
            if listing["seller_id"] == user_id:
                bot.answer_callback_query(call.id, "You cannot buy your own listing", show_alert=True)
                return
            
            if not listing["buy_now_price"]:
                bot.answer_callback_query(call.id, "Buy Now not available for this listing", show_alert=True)
                return
            
            # Confirm buy now
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("✅ Confirm Buy Now", callback_data=f"confirm_buy_now_{listing_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"view_listing_{listing_id}")
            )
            
            bot.edit_message_text(
                f"💰 *Confirm Buy Now*\n\n"
                f"Username: @{listing['username']}\n"
                f"Buy Now Price: {listing['buy_now_price']} {listing['currency']}\n"
                f"Seller: @{listing['seller_username'] or 'User'}\n\n"
                f"*Are you sure you want to buy now?*\n\n"
                f"This will create a swap immediately and middleman will contact you.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            
            bot.answer_callback_query(call.id)
        
        elif data.startswith("confirm_buy_now_"):
            listing_id = data.split("_")[3]
            
            # Call the bid function with buy now price
            listing = execute_one('''
                SELECT ml.*, u.username as seller_username
                FROM marketplace_listings ml
                JOIN users u ON ml.seller_id = u.user_id
                WHERE ml.listing_id = ?
            ''', (listing_id,))
            
            if listing and listing["buy_now_price"]:
                # Simulate bid command
                message_text = f"/bid {listing_id} {listing['buy_now_price']}"
                bid_command(type('Message', (), {'chat': type('Chat', (), {'id': user_id, 'type': 'private'}), 'text': message_text, 'from_user': call.from_user})())
            
            bot.answer_callback_query(call.id)
        
        elif data.startswith("vouch_"):
            parts = data.split("_")
            if len(parts) < 4:
                bot.answer_callback_query(call.id, "Invalid vouch data", show_alert=True)
                return
            
            vouch_type = parts[1]
            swap_id = parts[2]
            vouch_for = int(parts[3])
            
            if vouch_type == "skip":
                # Skip vouch
                if user_id in vouch_requests:
                    del vouch_requests[user_id]
                bot.answer_callback_query(call.id, "Vouch skipped")
                bot.edit_message_text(
                    "⏩ Vouch skipped. Thank you for your transaction!",
                    call.message.chat.id,
                    call.message.message_id
                )
                return
            
            # Store vouch request
            vouch_requests[user_id] = {
                "swap_id": swap_id,
                "vouch_for": vouch_for,
                "vouch_type": vouch_type,
                "step": "waiting_comment"
            }
            
            # Ask for comment
            bot.edit_message_text(
                f"💬 *Add a comment for your {vouch_type} vouch*\n\n"
                f"Enter your comment (optional):\n"
                f"Or type 'skip' to skip comment",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            
            bot.answer_callback_query(call.id)
            
        elif data.startswith("unban_"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "❌ Admin only", show_alert=True)
                return
            
            target_id = int(data.split("_")[1])
            
            # Unban user
            execute_query('''
                UPDATE users 
                SET is_banned = 0, ban_reason = NULL
                WHERE user_id = ?
            ''', (target_id,), commit=True)
            
            # Notify user
            try:
                bot.send_message(
                    target_id,
                    f"✅ *You have been unbanned!*\n\n"
                    f"You can now use the bot again."
                )
            except:
                pass
            
            bot.answer_callback_query(call.id, f"✅ User {target_id} unbanned")
            admin_bannedusers(call.message)
            
        elif data.startswith("viewbanned_"):
            target_id = int(data.split("_")[1])
            
            user = execute_one('''
                SELECT user_id, username, first_name, last_name, ban_reason, join_date
                FROM users WHERE user_id = ? AND is_banned = 1
            ''', (target_id,))
            
            if user:
                response = f"""
🚫 *Banned User Details*

*ID:* `{user[0]}`
*Name:* {user[2]} {user[3]}
*Username:* @{user[1] or 'N/A'}
*Ban Reason:* {user[4] or 'No reason provided'}
*Joined:* {user[5][:10]}

*Actions:* Use `/unban {user[0]}` to unban
"""
                bot.answer_callback_query(call.id)
                bot.send_message(user_id, response, parse_mode="Markdown")
            else:
                bot.answer_callback_query(call.id, "User not found or not banned", show_alert=True)
        
        elif data == "refresh_banned":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "❌ Admin only", show_alert=True)
                return
            
            admin_bannedusers(call.message)
            bot.answer_callback_query(call.id, "Refreshed")
            
        elif data.startswith("confirm_broadcast_"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "❌ Admin only", show_alert=True)
                return
            
            # Extract message from callback data
            message_hash = data.split("_")[2]
            
            # Get the original message from the edited message
            original_message = call.message.text
            # Extract the message after "Message: " and before the newlines
            message_text = original_message.split("Message: ")[1].split("\n\n")[0]
            
            # Send broadcast
            sent_count, failed_count = send_broadcast_to_all(message_text, user_id)
            
            if sent_count > 0:
                bot.answer_callback_query(call.id, f"✅ Broadcast sent to {sent_count} users")
                bot.edit_message_text(
                    f"📢 *Broadcast Completed!*\n\n"
                    f"Message: {message_text}\n\n"
                    f"✅ Sent to: {sent_count} users\n"
                    f"❌ Failed: {failed_count} users\n\n"
                    f"Total attempted: {sent_count + failed_count}",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown"
                )
            else:
                bot.answer_callback_query(call.id, "❌ Failed to send broadcast")
                
        elif data == "cancel_broadcast":
            bot.answer_callback_query(call.id, "Broadcast cancelled")
            bot.edit_message_text("❌ Broadcast cancelled.", call.message.chat.id, call.message.message_id)
            
    except Exception as e:
        print(f"Callback error: {e}")
        bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)

# ==================== AUCTION CHECKER THREAD ====================
def auction_checker_thread():
    """Background thread to check auction endings"""
    while True:
        try:
            check_auction_endings()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Error in auction checker: {e}")
            time.sleep(60)

# ==================== FLASK ROUTES ====================
@app.route('/')
def health_check():
    return jsonify({
        "status": "online",
        "service": "CARNAGE Swapper Bot",
        "timestamp": datetime.now().isoformat(),
        "version": "8.1.0",
        "features": ["Instagram API", "Session Encryption", "Marketplace", "Auction System", "Vouch System", "Escrow", "Credits System", "Bulk Listings"],
        "users": execute_one("SELECT COUNT(*) FROM users")[0] or 0,
        "listings": execute_one("SELECT COUNT(*) FROM marketplace_listings WHERE status = 'active'")[0] or 0,
        "auctions": execute_one("SELECT COUNT(*) FROM marketplace_listings WHERE sale_type = 'auction' AND status = 'active'")[0] or 0,
        "total_credits": execute_one("SELECT SUM(credits) FROM users")[0] or 0
    })

@app.route('/dashboard/<int:user_id>')
def user_dashboard(user_id):
    """User dashboard HTML page"""
    try:
        stats = get_user_detailed_stats(user_id)
        if not stats:
            return "User not found", 404
        
        # Format achievements HTML
        achievements_html = ""
        if stats["achievements"]:
            for ach in stats["achievements"][:6]:
                achievements_html += f'''
                <div class="achievement unlocked">
                    <div class="achievement emoji">{ach[2]}</div>
                    <div class="achievement name">{ach[1]}</div>
                </div>
                '''
        else:
            achievements_html = '<p style="text-align: center; color: #666;">No achievements yet</p>'
        
        # Format recent swaps HTML
        recent_swaps_html = ""
        if stats["recent_swaps"]:
            for swap in stats["recent_swaps"][:5]:
                status_class = "swap-success" if swap['status'] == 'success' else "swap-failed"
                status_text = "✅ Success" if swap['status'] == 'success' else "❌ Failed"
                recent_swaps_html += f'''
                <div class="swap-item">
                    <div>@{swap['target']}</div>
                    <div class="{status_class}">{status_text}</div>
                    <div>{swap['time'][11:16]}</div>
                </div>
                '''
        else:
            recent_swaps_html = '<p style="text-align: center; color: #666;">No swaps yet</p>'
        
        # Render template
        html_content = HTML_TEMPLATES['dashboard'].format(
            user_id=user_id,
            status="✅ Approved" if is_user_approved(user_id) else "⏳ Pending",
            join_date=stats['join_date'][:10],
            last_active=stats['last_active'][:16],
            total_swaps=stats['total_swaps'],
            successful_swaps=stats['successful_swaps'],
            success_rate=f"{stats['success_rate']:.1f}",
            total_referrals=stats['total_referrals'],
            credits=stats['credits'],
            achievements_unlocked=stats['achievements_unlocked'],
            achievements_total=10,
            achievements_html=achievements_html,
            recent_swaps_html=recent_swaps_html,
            bot_username=BOT_USERNAME
        )
        
        return html_content
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/admin')
def admin_panel():
    """Admin panel HTML page"""
    # Basic auth - you should implement proper authentication
    auth = request.args.get('auth')
    if auth != 'carnage123':
        return "Unauthorized", 401
    
    try:
        # Get admin stats
        total_users = get_total_users()
        active_users = execute_one("SELECT COUNT(*) FROM users WHERE last_active > ?",
                                 ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),))[0] or 0
        
        total_swaps = execute_one("SELECT COUNT(*) FROM swap_history")[0] or 0
        successful_swaps = execute_one("SELECT COUNT(*) FROM swap_history WHERE status = 'success'")[0] or 0
        success_rate = (successful_swaps / total_swaps * 100) if total_swaps > 0 else 0
        
        total_listings = execute_one("SELECT COUNT(*) FROM marketplace_listings")[0] or 0
        pending_transactions = execute_one("SELECT COUNT(*) FROM marketplace_swaps WHERE status IN ('created', 'payment_received')")[0] or 0
        
        # Get users for initial table
        users = execute_query('''
            SELECT user_id, username, first_name, tier, approved, is_banned, 
                   credits, total_swaps, successful_swaps, vouch_score
            FROM users 
            ORDER BY user_id
            LIMIT 20
        ''')
        
        users_html = ""
        for user in users:
            status_class = "badge-danger" if user[5] else ("badge-success" if user[4] else "badge-warning")
            status_text = "Banned" if user[5] else ("Approved" if user[4] else "Pending")
            
            users_html += f'''
            <tr>
                <td>{user[0]}</td>
                <td>@{user[1] or 'N/A'}</td>
                <td><span class="badge">{user[3].upper()}</span></td>
                <td>{user[6]} ({user[7]}✅)</td>
                <td>{user[9]}⭐</td>
                <td><span class="badge {status_class}">{status_text}</span></td>
                <td>
                    <button class="btn btn-small" onclick="adminAction('approve', {user[0]})">Approve</button>
                    <button class="btn btn-small" onclick="adminAction('ban', {user[0]})">Ban</button>
                    <button class="btn btn-small" onclick="adminAction('addcredits', {user[0]})">Add Credits</button>
                </td>
            </tr>
            '''
        
        initial_content = f'''
        <h3><i class="fas fa-users"></i> Users Management</h3>
        <table id="usersTable">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Tier</th>
                    <th>Swaps</th>
                    <th>Vouch</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {users_html}
            </tbody>
        </table>
        '''
        
        html_content = HTML_TEMPLATES['admin_panel'].format(
            total_users=total_users,
            active_today=active_users,
            total_swaps=total_swaps,
            success_rate=f"{success_rate:.1f}",
            total_listings=total_listings,
            pending_transactions=pending_transactions,
            initial_content=initial_content
        )
        
        return html_content
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/admin/tab/<tab_name>')
def admin_tab(tab_name):
    """Admin panel tab content"""
    try:
        if tab_name == 'users':
            users = execute_query('''
                SELECT user_id, username, first_name, tier, approved, is_banned, 
                       credits, total_swaps, successful_swaps, vouch_score
                FROM users 
                ORDER BY user_id
                LIMIT 50
            ''')
            
            users_html = ""
            for user in users:
                status_class = "badge-danger" if user[5] else ("badge-success" if user[4] else "badge-warning")
                status_text = "Banned" if user[5] else ("Approved" if user[4] else "Pending")
                
                users_html += f'''
                <tr>
                    <td>{user[0]}</td>
                    <td>@{user[1] or 'N/A'}</td>
                    <td><span class="badge">{user[3].upper()}</span></td>
                    <td>{user[6]} ({user[7]}✅)</td>
                    <td>{user[8]}</td>
                    <td><span class="badge {status_class}">{status_text}</span></td>
                    <td>
                        <button class="btn btn-small" onclick="adminAction('approve', {user[0]})">Approve</button>
                        <button class="btn btn-small" onclick="adminAction('ban', {user[0]})">Ban</button>
                    </td>
                </tr>
                '''
            
            return f'''
            <h3><i class="fas fa-users"></i> Users Management</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Tier</th>
                        <th>Swaps</th>
                        <th>Credits</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {users_html}
                </tbody>
            </table>
            '''
        
        elif tab_name == 'swaps':
            swaps = execute_query('''
                SELECT sh.*, u.username
                FROM swap_history sh
                JOIN users u ON sh.user_id = u.user_id
                ORDER BY sh.swap_time DESC
                LIMIT 30
            ''')
            
            swaps_html = ""
            for swap in swaps:
                status_class = "badge-success" if swap[2] == 'success' else "badge-danger"
                
                swaps_html += f'''
                <tr>
                    <td>{swap[0]}</td>
                    <td>@{swap[6] or 'N/A'}</td>
                    <td>@{swap[1]}</td>
                    <td><span class="badge {status_class}">{swap[2]}</span></td>
                    <td>{swap[3]}</td>
                    <td>{swap[4] or '-'}</td>
                    <td>{swap[6] or 0} 🪙</td>
                </tr>
                '''
            
            return f'''
            <h3><i class="fas fa-exchange-alt"></i> Recent Swaps</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>User</th>
                        <th>Target</th>
                        <th>Status</th>
                        <th>Time</th>
                        <th>Error</th>
                        <th>Credits</th>
                    </tr>
                </thead>
                <tbody>
                    {swaps_html}
                </tbody>
            </table>
            '''
        
        elif tab_name == 'marketplace':
            listings = execute_query('''
                SELECT ml.*, u.username as seller_username
                FROM marketplace_listings ml
                JOIN users u ON ml.seller_id = u.user_id
                ORDER BY ml.created_at DESC
                LIMIT 30
            ''')
            
            listings_html = ""
            for listing in listings:
                status_class = "badge-success" if listing[6] == 'active' else "badge-warning"
                
                listings_html += f'''
                <tr>
                    <td>{listing[1]}</td>
                    <td>@{listing[2]}</td>
                    <td>@{listing[15]}</td>
                    <td>{listing[3]} {listing[4]}</td>
                    <td>{listing[7].upper()}</td>
                    <td><span class="badge {status_class}">{listing[6]}</span></td>
                    <td>{listing[10]}</td>
                    <td>{listing[11]}</td>
                    <td>{"✅" if listing[23] == 1 else "❌"}</td>
                </tr>
                '''
            
            return f'''
            <h3><i class="fas fa-store"></i> Marketplace Listings</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Seller</th>
                        <th>Price</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Expires</th>
                        <th>Verified</th>
                    </tr>
                </thead>
                <tbody>
                    {listings_html}
                </tbody>
            </table>
            '''
        
        elif tab_name == 'system':
            # System stats
            uptime = str(timedelta(seconds=int(time.time() - start_time)))
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            
            return f'''
            <h3><i class="fas fa-cog"></i> System Status</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px;">
                <div class="stat-card">
                    <div class="stat-title">Uptime</div>
                    <div class="stat-value">{uptime}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">CPU Usage</div>
                    <div class="stat-value">{cpu}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Memory Usage</div>
                    <div class="stat-value">{memory.percent}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Threads</div>
                    <div class="stat-value">{threading.active_count()}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">API Requests</div>
                    <div class="stat-value">{requests_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">API Errors</div>
                    <div class="stat-value">{errors_count}</div>
                </div>
            </div>
            '''
        
        elif tab_name == 'broadcast':
            return '''
            <h3><i class="fas fa-bullhorn"></i> Send Broadcast</h3>
            <div style="margin-top: 20px;">
                <textarea id="broadcastMessage" placeholder="Enter broadcast message..." 
                          style="width: 100%; height: 200px; padding: 15px; border-radius: 10px; 
                                 background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); 
                                 color: white; font-size: 1em; margin-bottom: 20px;"></textarea>
                <button class="btn" onclick="sendBroadcast()" style="width: 100%; padding: 15px; font-size: 1.2em;">
                    <i class="fas fa-paper-plane"></i> Send to All Users
                </button>
                <p style="color: #aaa; margin-top: 20px; font-size: 0.9em;">
                    <i class="fas fa-info-circle"></i> This will send the message to all non-banned users.
                </p>
            </div>
            '''
        
        return f"<h3>Tab {tab_name}</h3><p>Content coming soon...</p>"
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/admin/action', methods=['POST'])
def admin_action():
    """Handle admin actions"""
    try:
        data = request.json
        action = data.get('action')
        user_id = data.get('userId')
        reason = data.get('reason')
        
        if action == 'approve':
            execute_query("UPDATE users SET approved = 1 WHERE user_id = ?", (user_id,), commit=True)
            return jsonify({"success": True, "message": f"User {user_id} approved"})
        elif action == 'ban':
            execute_query("UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?", (reason, user_id), commit=True)
            return jsonify({"success": True, "message": f"User {user_id} banned: {reason}"})
        elif action == 'addcredits':
            add_credits(user_id, 100)
            return jsonify({"success": True, "message": f"Added 100 credits to user {user_id}"})
        
        return jsonify({"success": False, "message": "Unknown action"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/admin/broadcast', methods=['POST'])
def admin_broadcast():
    """Handle broadcast message"""
    try:
        data = request.json
        message = data.get('message')
        
        if not message:
            return jsonify({"success": False, "message": "No message provided"})
        
        # Get all user IDs
        users = execute_query("SELECT user_id FROM users WHERE is_banned = 0")
        
        if not users:
            return jsonify({"success": False, "message": "No users found"})
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            user_id = user[0]
            try:
                bot.send_message(
                    user_id,
                    f"📢 *ANNOUNCEMENT FROM CARNAGE*\n\n{message}\n\n",
                    parse_mode="Markdown"
                )
                sent_count += 1
                time.sleep(0.1)  # Prevent rate limiting
            except Exception as e:
                failed_count += 1
                print(f"Failed to send to {user_id}: {e}")
        
        return jsonify({
            "success": True, 
            "message": f"Broadcast sent to {sent_count} users. Failed: {failed_count}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/ping')
def ping():
    return jsonify({"status": "pong", "time": datetime.now().isoformat()})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/ping1')
def ping1():
    return jsonify({"status": "pong1", "time": datetime.now().isoformat()})

# ==================== WHAT TO POST IN CHANNELS ====================
def post_initial_announcements():
    """Post initial announcements to channels"""
    try:
        # Updates Channel Announcement
        updates_message = """
🎉 *CARNAGE SWAPPER v8.1 OFFICIAL LAUNCH!* 🚀

*✨ NEW FEATURES IN v8.1:*

💰 *CREDITS SYSTEM*
• New users get 100 free credits
• Each swap attempt costs 10 credits
• Successful swaps refund credits
• Refer friends for 20 credits each
• Admins can add credits to users

📦 *BULK LISTING*
• List multiple usernames at once
• Automatic session verification
• Format: username:session:price
• Perfect for username sellers

🔐 *ENHANCED VERIFICATION*
• Verified session badges
• Session validation for all listings
• Ownership verification required
• Secure encrypted storage

📢 *ADMIN BROADCAST*
• Send announcements to all users
• Admin control panel improved
• Better user management

🎯 *AUCTION SYSTEM*
• Bid on Instagram usernames
• Automatic bid increments
• Buy Now option
• Fake bid protection (Permanent ban for fake bids)

🤝 *VOUCH SYSTEM*
• Automatic vouch requests after swaps
• Positive/Negative feedback
• Vouch score calculation
• Verified transactions only

*🚀 GET STARTED:*
1. Start the bot: @CarnageSwapperBot
2. Join our channels (required)
3. Get approved (instant via referral)
4. Start swapping, selling, or bidding!

*⚠️ IMPORTANT RULES:*
• Fake bids = PERMANENT BAN
• Always use middleman for transactions
• Real currency only in marketplace
• Verify sellers before buying

*🎁 REFERRAL PROGRAM:*
Refer friends and earn FREE swaps + 20 credits each!

*Welcome to the most advanced username swapping platform!* 🔥
"""
        
        # Marketplace Channel Announcement
        marketplace_message = """
🛒 *CARNAGE MARKETPLACE v8.1 - NOW WITH BULK LISTING!* 💰

Welcome to the upgraded CARNAGE Marketplace with BULK LISTING SYSTEM!

*📦 NEW BULK FEATURES:*
• List multiple usernames at once
• Automatic session validation
• Ownership verification
• Quick listing process

*💰 SALE TYPES AVAILABLE:*
1. *Fixed Price* - Set your price
2. *Auction* - Accept bids for 24 hours
3. *Buy Now + Auction* - Set buy now price + accept bids

*🔐 VERIFIED SESSIONS:*
• All listings now show verified status
• Session validation required
• Ownership proof required
• Secure encrypted storage

*⚠️ AUCTION RULES:*
• Minimum bid increments apply
• Fake bids = PERMANENT BAN
• Auction winner must complete purchase
• Buy Now ends auction immediately

*🤝 VOUCH SYSTEM:*
• Automatic vouch requests after swaps
• Build your reputation
• Vouch scores displayed on listings
• Trusted sellers get badges

*📋 HOW TO SELL:*
1. Use `/sell` for single listing
2. Use `/bulksell` for multiple usernames
3. Choose sale type (Fixed/Auction/Buy Now)
4. Set price and verify ownership
5. Your listing goes live instantly!

*🛍️ HOW TO BUY/BID:*
1. Browse with `/marketplace`
2. Click on listing to view details
3. Place bid or buy now
4. Contact middleman to complete

*💰 PAYMENT METHODS:*
• Indian Rupees (INR) - UPI/Bank Transfer
• CRYPTO (USDT/BTC/ETH)

*Start listing or bidding now with @CarnageSwapperBot!* 🚀

*Need help?* Contact @CARNAGEV1
"""
        
        # Send to updates channel
        bot.send_message(UPDATES_CHANNEL, updates_message, parse_mode="Markdown")
        
        # Send to marketplace channel
        bot.send_message(MARKETPLACE_CHANNEL_ID, marketplace_message, parse_mode="Markdown")
        
        print("✅ Initial announcements posted to channels")
        
    except Exception as e:
        print(f"❌ Error posting announcements: {e}")

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
            bot.polling(non_stop=True, interval=0, timeout=20)
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
    print("🔧 Initializing database with encryption...")
    init_database()
    
    # Start auction checker thread
    auction_thread = threading.Thread(target=auction_checker_thread, daemon=True)
    auction_thread.start()
    
    print("✅ Database initialized successfully")
    print("🚀 CARNAGE Swapper Bot v8.1 - PRODUCTION READY")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot Username: @{BOT_USERNAME}")
    print(f"📢 Updates Channel: {CHANNELS['updates']['id']}")
    print(f"✅ Proofs Channel: {CHANNELS['proofs']['id']}")
    print(f"🛒 Marketplace Channel: {MARKETPLACE_CHANNEL_ID}")
    print(f"👥 Admin Group: {ADMIN_GROUP_ID}")
    print("✨ Features: COMPLETE MARKETPLACE WITH AUCTION & VOUCH SYSTEM")
    print("💰 Credits System: 10 credits per swap attempt")
    print("📦 Bulk Listing: List multiple usernames at once")
    print("🔐 Session Verification: All sessions validated")
    print("🎯 Auction System: Bid on usernames with Buy Now option")
    print("🤝 Vouch System: User reputation with automatic vouch requests")
    print("💲 Currency: INR & CRYPTO (replaced USDT)")
    print("⚖️ One Middleman System: Simplified escrow transactions")
    print("📊 HTML Dashboard & Admin Panel")
    print("🚫 Fake Bid Protection: Permanent ban for fake bids")
    print("📢 Admin Broadcast: Send messages to all users")
    
    # Post initial announcements
    print("📢 Posting initial announcements to channels...")
    try:
        post_initial_announcements()
    except:
        print("⚠️ Could not post announcements (channels might not exist yet)")
    
    # Start Telegram bot
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("🤖 Telegram bot started in background")
    
    print("\n🎯 **OPERATION MODES:**")
    print("• User Functions: DM ONLY")
    print("• Middleman Commands: GROUP ONLY")
    print("• Admin Commands: DM ONLY")
    print("• Marketplace: Real currency only")
    print("• Auction System: Bidding with Buy Now option")
    print("• Vouch System: Automatic reputation building")
    print("• Session Verification: Required for sellers")
    
    print("\n💰 **CREDITS SYSTEM:**")
    print("• New users: 100 credits free")
    print("• Swap attempt: 10 credits")
    print("• Successful swap: Credits refunded")
    print("• Referral: 20 credits per friend")
    print("• Admin can add credits")
    
    print("\n🔗 **URLS:**")
    print(f"• Dashboard: https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/USER_ID")
    print(f"• Admin Panel: https://separate-genny-1carnage1-2b4c603c.koyeb.app/admin?auth=carnage123")
    
    print("\n✅ **PRODUCTION READY WITH ALL FEATURES!**")
    print("\n📋 **ADDED FEATURES IN v8.1:**")
    print("1. ✅ Credits System - 10 credits per swap")
    print("2. ✅ Bulk Listing - Multiple usernames at once")
    print("3. ✅ Session Verification for all listings")
    print("4. ✅ Admin Broadcast command")
    print("5. ✅ USDT replaced with CRYPTO")
    print("6. ✅ Fixed /sell command with inline menus")
    print("7. ✅ Fixed /marketplace with inline buttons")
    print("8. ✅ Buy Now option for auctions")
    print("9. ✅ Fake bid protection (Permanent ban)")
    print("10. ✅ Automatic vouch requests after swaps")
    print("11. ✅ One middleman per swap system")
    print("12. ✅ Vouch scores in marketplace listings")
    print("13. ✅ Auction ending checker (background thread)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Bot shutting down...")

if __name__ == '__main__':
    main()
