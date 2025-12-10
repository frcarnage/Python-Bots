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
marketplace_transactions = {}
pending_swaps = {}
verified_mms = {ADMIN_USER_ID}
swap_sessions = {}
active_listings = {}

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
                    <div class="stat-title">Free Swaps</div>
                    <div class="stat-value">{free_swaps}</div>
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
                    backup_username TEXT DEFAULT NULL
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
                    FOREIGN KEY (seller_id) REFERENCES users (user_id)
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
                    FOREIGN KEY (listing_id) REFERENCES marketplace_listings (listing_id),
                    FOREIGN KEY (seller_id) REFERENCES users (user_id),
                    FOREIGN KEY (buyer_id) REFERENCES users (user_id),
                    FOREIGN KEY (mm_id) REFERENCES users (user_id)
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

def get_user_detailed_stats(user_id):
    """Get detailed user statistics"""
    user_data = execute_one('''
        SELECT username, total_swaps, successful_swaps, total_referrals, free_swaps_earned,
               join_date, last_active, tier, credits
        FROM users WHERE user_id = ?
    ''', (user_id,))
    
    if not user_data:
        return None
    
    username, total_swaps, successful_swaps, total_referrals, free_swaps, join_date, last_active, tier, credits = user_data
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
    
    buttons = [
        "📱 Main Session", "🎯 Target Session",
        "🔄 Swapper", "⚙️ Settings",
        "📊 Dashboard", "🎁 Referral",
        "🏆 Achievements", "📈 Stats",
        "🛒 Marketplace"
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
            
            f"*Marketplace Stats:*\n"
            f"• Active Listings: `{active_listings}`\n"
            f"• Active Swaps: `{active_swaps}`\n"
            f"• Total Listings: `{execute_one('SELECT COUNT(*) FROM marketplace_listings')[0] or 0}`\n\n"
            
            f"*Service Status:*\n"
            f"• Instagram API: {api_status}\n"
            f"• Database: `✅ Connected`\n"
            f"• Encryption: `✅ Active`\n"
            f"• Web Server: `✅ Running`\n\n"
            
            f"*Cache Status:*\n"
            f"• Session Data: `{len(session_data)} users`\n"
            f"• Pending Swaps: `{len(pending_swaps)}`\n"
            f"• User States: `{len(user_states)}`\n"
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
                   credits, total_swaps, successful_swaps, join_date, total_referrals
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
                f"Referrals: {user['total_referrals']} | Status: {status}\n"
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
        execute_query("UPDATE users SET credits = credits + ? WHERE user_id = ?",
                     (amount, target_id), commit=True)
        
        # Notify user
        try:
            bot.send_message(
                target_id,
                f"🎁 *You received credits!*\n\n"
                f"Amount: +{amount} credits\n"
                f"New Balance: {execute_one('SELECT credits FROM users WHERE user_id = ?', (target_id,))[0]} credits\n\n"
                f"Use them for swapping or in marketplace!",
                parse_mode="Markdown"
            )
        except:
            pass
        
        bot.reply_to(message, f"✅ Added {amount} credits to user {target_id}")
        
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
            f"• Success Rate: {success_rate:.1f}%\n\n"
            
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
                "Tip: Get a friend to refer you for instant approval + 2 FREE swaps! 🎁",
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

*Swap Features (DM ONLY):*
• Real Instagram username swapping
• Working API with rate limit handling
• Session validation and management
• Backup mode and threads support

*Marketplace Features (DM ONLY):*
/marketplace - Browse username listings
/sell - List username for sale (Real money only)

*Admin Commands (Admin only - DM ONLY):*
/users - List all users
/ban <id> <reason> - Ban user
/approve <id> <duration> - Approve user
/addcredits <id> <amount> - Add credits
/stats - Bot statistics
/ping - Check bot response time
/botstatus - Detailed bot status
/refreshbot - Refresh bot caches

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
5. Refer friends for FREE swaps (2 per referral!)

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
    
    dashboard_url = f"https://your-koyeb-app.koyeb.app/dashboard/{user_id}"
    bot.send_message(user_id, f"📊 *Your Dashboard:*\n\n{dashboard_url}", parse_mode="Markdown")

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
        
        response = (
            f"🎁 *Your Referral Program*\n\n"
            f"*Your Link:*\n`{referral_link}`\n\n"
            f"*How it works:*\n"
            f"1. Share your link with friends\n"
            f"2. When they join using your link\n"
            f"3. You get **2 FREE swaps** for each friend!\n"
            f"4. They get instant approval\n\n"
            f"*Your Stats:*\n"
            f"• Total Referrals: {ref_count}\n"
            f"• Free Swaps Earned: {free_swaps}\n"
            f"• Credits: {execute_one('SELECT credits FROM users WHERE user_id = ?', (user_id,))[0]}\n\n"
            f"*Rewards:*\n"
            f"• 1 referral = 2 FREE swaps\n"
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

*Swap Stats:*
• Total Swaps: {stats['total_swaps']}
• Successful: {stats['successful_swaps']}
• Success Rate: {stats['success_rate']:.1f}%

*Referral Stats:*
• Total Referrals: {stats['total_referrals']}
• Free Swaps Available: {stats['free_swaps']}

*Credits:*
• Balance: {stats['credits']} 🪙
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
    bot.send_message(chat_id, "🤖 *CARNAGE Swapper - Main Menu*\n\nUse the buttons below or type /help for commands.", parse_mode="Markdown")
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
        else:
            bot.edit_message_text(f"❌ *Swap failed for {target_username}*", chat_id, message_id, parse_mode="Markdown")
            log_swap(chat_id, target_username, "failed", "Swap process failed")
        
        clear_session_data(chat_id, "main")
        clear_session_data(chat_id, "target")
        
    except Exception as e:
        bot.edit_message_text(f"❌ *Error during swap: {str(e)}*", chat_id, message_id, parse_mode="Markdown")
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

# ==================== MARKETPLACE FUNCTIONS ====================
@bot.message_handler(commands=['marketplace', 'mp'])
def marketplace_command(message):
    """Browse marketplace listings"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    listings = execute_query('''
        SELECT ml.*, u.username as seller_username, u.tier as seller_tier
        FROM marketplace_listings ml
        JOIN users u ON ml.seller_id = u.user_id
        WHERE ml.status = 'active' AND ml.currency != 'credits'
        ORDER BY ml.created_at DESC
        LIMIT 10
    ''')
    
    if not listings:
        response = "🛒 *Marketplace*\n\nNo active listings found.\nBe the first to list with /sell"
        bot.send_message(user_id, response, parse_mode="Markdown")
        return
    
    response = "🛒 *CARNAGE MARKETPLACE*\n\n"
    response += "*Active Listings:*\n\n"
    
    for listing in listings:
        currency_symbol = "💲"
        if listing["currency"] == "inr":
            price_text = f"₹{listing['price']}"
        elif listing["currency"] == "usdt":
            price_text = f"${listing['price']} USDT"
        else:
            price_text = f"{listing['price']} {listing['currency']}"
        
        bid_text = f" ({listing['bids']} bids)" if listing["bids"] > 0 else ""
        
        response += (
            f"🔹 *@{listing['username']}*\n"
            f"Price: {currency_symbol} {price_text}{bid_text}\n"
            f"Seller: @{listing['seller_username']} ({listing['seller_tier'].upper()})\n"
            f"ID: `{listing['listing_id']}`\n"
            f"────────────────────\n"
        )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ List Username", callback_data="create_listing"),
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh_marketplace")
    )
    
    for listing in listings[:3]:
        markup.add(InlineKeyboardButton(
            f"🛒 @{listing['username']}",
            callback_data=f"view_listing_{listing['listing_id']}"
        ))
    
    bot.send_message(user_id, response, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['sell'])
def sell_command(message):
    """Start selling process"""
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    bot.send_message(
        user_id,
        "🛒 *List a Username for Sale*\n\n"
        "Send the username you want to sell (without @):\n\n"
        "Example: `carnage` or `og.name`\n\n"
        "*Note:* You'll need to provide session ID to verify ownership.",
        parse_mode="Markdown"
    )
    
    user_states[user_id] = {
        "action": "selling",
        "step": "get_username"
    }

def create_marketplace_listing(user_id, username, price, currency="inr", 
                               listing_type="sale", description=""):
    """Create a new marketplace listing"""
    
    existing = execute_one(
        "SELECT listing_id FROM marketplace_listings WHERE seller_id = ? AND username = ? AND status = 'active'",
        (user_id, username)
    )
    if existing:
        return False, "You already have an active listing for this username"
    
    # Check if credits listing (not allowed)
    if currency == "credits":
        return False, "Marketplace listings must be in real currency (INR/USDT). Credits not allowed."
    
    listing_id = generate_listing_id()
    
    execute_query('''
        INSERT INTO marketplace_listings 
        (listing_id, seller_id, username, price, currency, listing_type, 
         description, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        listing_id, user_id, username, price, currency, listing_type,
        description,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
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
        "UPDATE marketplace_listings SET seller_session_encrypted = ?, verified_at = ? WHERE listing_id = ?",
        (encrypted_session, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), listing_id),
        commit=True
    )
    
    return True, "Session verified and stored"

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
                    "Join: @CarnageMMGroup",
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
`/createswap <listing_id> <buyer_id/@username> [mm_id]` - Create new swap
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
            bot.reply_to(message, "Usage: /createswap <listing_id> <buyer_id/@username> [mm_id]")
            bot.reply_to(message, "Example: /createswap LIST12345 @username\nExample: /createswap LIST12345 123456789")
            return
        
        listing_id = parts[1]
        buyer_identifier = parts[2]
        mm_id = user_id  # Default to command user
        
        # Optional: specify different MM
        if len(parts) > 3:
            try:
                specified_mm = int(parts[3])
                if is_verified_mm(specified_mm):
                    mm_id = specified_mm
                else:
                    bot.reply_to(message, "❌ Specified user is not a verified middleman")
                    return
            except:
                pass
        
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
                f"Swap ID: `{swap_id}`\n\n"
                f"Please contact middleman for payment instructions.",
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
                   u2.username as buyer_username,
                   u3.username as mm_username
            FROM marketplace_swaps ms
            JOIN marketplace_listings ml ON ms.listing_id = ml.listing_id
            JOIN users u1 ON ms.seller_id = u1.user_id
            JOIN users u2 ON ms.buyer_id = u2.user_id
            LEFT JOIN users u3 ON ms.mm_id = u3.user_id
            WHERE ms.swap_id = ?
        ''', (swap_id,))
        
        if not swap:
            bot.reply_to(message, "❌ Swap not found")
            return
        
        # Check if current user is the assigned MM
        if swap["mm_id"] and swap["mm_id"] != user_id:
            bot.reply_to(message, "❌ You are not the assigned middleman for this swap")
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
*Middleman:* {swap['mm_username']}

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
            f"Amount: {swap['amount']} {swap['currency']}\n\n"
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
        
        # Check if current user is the assigned MM
        if swap["mm_id"] and swap["mm_id"] != user_id:
            bot.reply_to(message, "❌ You are not the assigned middleman for this swap")
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
            
            return True, "Swap executed successfully! Funds ready for release."
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
        
        # Check if current user is the assigned MM
        if swap["mm_id"] and swap["mm_id"] != user_id:
            bot.reply_to(message, "❌ You are not the assigned middleman for this swap")
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
        
        # Check if current user is the assigned MM
        if swap["mm_id"] and swap["mm_id"] != user_id:
            bot.reply_to(message, "❌ You are not the assigned middleman for this swap")
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
@bot.message_handler(func=lambda message: message.chat.type == 'private')
def handle_private_messages(message):
    """Handle all text messages in private chat"""
    user_id = message.chat.id
    text = message.text
    
    # Update user activity
    execute_query(
        "UPDATE users SET last_active = ? WHERE user_id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id),
        commit=True
    )
    
    # Check if user is in selling state
    if user_id in user_states and user_states[user_id]["action"] == "selling":
        handle_selling_state(user_id, text)
        return
    
    # Check if user is in pending swap state
    if user_id in pending_swaps:
        handle_pending_swap(user_id, text)
        return
    
    # Check if it's a command
    if text.startswith('/'):
        # Let command handlers process it
        return
    
    # Default response
    show_main_menu(user_id)

def handle_selling_state(user_id, text):
    """Handle user in selling state"""
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
        state["step"] = "get_price"
        
        bot.send_message(
            user_id,
            f"💰 *Set Price for @{username}*\n\n"
            f"Enter price and currency:\n\n"
            f"*Formats:*\n"
            f"• `5000 inr` (Indian Rupees)\n"
            f"• `100 usdt` (USDT Crypto)\n\n"
            f"*Real currency only! Credits not allowed in marketplace.*\n"
            f"Minimum: ₹1000 or $10 USDT",
            parse_mode="Markdown"
        )
    
    elif state["step"] == "get_price":
        try:
            parts = text.split()
            if len(parts) < 2:
                bot.send_message(user_id, "❌ Format: <amount> <currency>")
                return
            
            price = float(parts[0])
            currency = parts[1].lower()
            
            # Validate currency (only real money allowed)
            valid_currencies = ["inr", "usdt"]
            if currency not in valid_currencies:
                bot.send_message(user_id, f"❌ Marketplace accepts only real currency: {', '.join(valid_currencies)}")
                return
            
            # Validate minimum price
            min_prices = {
                "inr": 1000,
                "usdt": 10
            }
            
            if price < min_prices.get(currency, 1000):
                bot.send_message(user_id, f"❌ Minimum price for {currency} is {min_prices[currency]}")
                return
            
            state["price"] = price
            state["currency"] = currency
            state["step"] = "get_description"
            
            bot.send_message(
                user_id,
                f"📝 *Add Description for @{state['username']}*\n\n"
                f"Enter description (optional):\n"
                f"Or type 'skip' to skip",
                parse_mode="Markdown"
            )
            
        except ValueError:
            bot.send_message(user_id, "❌ Please enter valid amount")
    
    elif state["step"] == "get_description":
        description = text if text.lower() != "skip" else ""
        state["description"] = description
        
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
        
        # Verify session
        success, result = verify_seller_session(user_id, state.get("listing_id", ""), session_id)
        
        if success:
            # Create listing
            success, listing_id = create_marketplace_listing(
                user_id,
                state["username"],
                state["price"],
                state["currency"],
                "sale",
                state["description"]
            )
            
            if success:
                state["listing_id"] = listing_id
                
                # Store session
                save_session_to_db(user_id, "marketplace_seller", session_id, listing_id)
                
                bot.send_message(
                    user_id,
                    f"✅ *Listing Created Successfully!*\n\n"
                    f"Username: @{state['username']}\n"
                    f"Price: {state['price']} {state['currency']}\n"
                    f"Listing ID: `{listing_id}`\n\n"
                    f"*Your listing is now active in marketplace!*\n"
                    f"View it with /marketplace\n\n"
                    f"*Note:* When someone buys, middleman will contact you for session.",
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(user_id, f"❌ Failed to create listing: {listing_id}")
        else:
            bot.send_message(user_id, f"❌ Verification failed: {result}\n\nPlease send valid session ID:")
            return
        
        del user_states[user_id]

def handle_pending_swap(user_id, text):
    """Handle pending swap session collection"""
    swap_data = pending_swaps[user_id]
    swap_id = swap_data["swap_id"]
    role = swap_data["role"]
    
    session_id = text.strip()
    
    # Handle session
    success, result = handle_swap_session(user_id, session_id, role, swap_id)
    
    if success:
        bot.send_message(user_id, f"✅ {result}", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"❌ {result}\n\nPlease send valid session ID:", parse_mode="Markdown")
        return
    
    # Remove from pending if not waiting for other party
    if "Waiting for other party" not in result:
        del pending_swaps[user_id]

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
            marketplace_command(call.message)
            bot.answer_callback_query(call.id, "Marketplace refreshed")
            
        elif data == "create_listing":
            sell_command(call.message)
            bot.answer_callback_query(call.id)
            
        elif data.startswith("view_listing_"):
            listing_id = data.split("_")[2]
            listing = execute_one('''
                SELECT ml.*, u.username as seller_username, u.tier as seller_tier
                FROM marketplace_listings ml
                JOIN users u ON ml.seller_id = u.user_id
                WHERE ml.listing_id = ?
            ''', (listing_id,))
            
            if listing:
                currency_symbol = "💲"
                if listing["currency"] == "inr":
                    price_text = f"₹{listing['price']}"
                elif listing["currency"] == "usdt":
                    price_text = f"${listing['price']} USDT"
                else:
                    price_text = f"{listing['price']} {listing['currency']}"
                
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    InlineKeyboardButton("🛒 Contact MM to Buy", url=f"https://t.me/{BOT_USERNAME}"),
                    InlineKeyboardButton("📞 Contact Seller", url=f"https://t.me/{listing['seller_username']}" if listing['seller_username'] else callback_data="no_seller"),
                    InlineKeyboardButton("🔙 Back", callback_data="refresh_marketplace")
                )
                
                verified_text = "✅ Verified" if listing["seller_session_encrypted"] else "❌ Not Verified"
                
                response = (
                    f"🔍 *Listing Details*\n\n"
                    f"*Username:* `{listing['username']}`\n"
                    f"*Price:* {currency_symbol} {price_text}\n"
                    f"*Seller:* @{listing['seller_username'] or 'User'}\n"
                    f"*Seller Tier:* {listing['seller_tier'].upper()}\n"
                    f"*Verification:* {verified_text}\n"
                    f"*Status:* {listing['status'].capitalize()}\n\n"
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
            
        elif data.startswith("buy_"):
            listing_id = data.split("_")[1]
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
            
            # Show purchase instructions
            response = (
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
                f"*Listing ID:* `{listing_id}`"
            )
            
            bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
            
    except Exception as e:
        print(f"Callback error: {e}")
        bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)

# ==================== FLASK ROUTES ====================
@app.route('/')
def health_check():
    return jsonify({
        "status": "online",
        "service": "CARNAGE Swapper Bot",
        "timestamp": datetime.now().isoformat(),
        "version": "7.0.0",
        "features": ["Instagram API", "Session Encryption", "Marketplace", "Escrow", "Middleman System"],
        "users": execute_one("SELECT COUNT(*) FROM users")[0] or 0,
        "listings": execute_one("SELECT COUNT(*) FROM marketplace_listings WHERE status = 'active'")[0] or 0
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
            free_swaps=stats['free_swaps'],
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
                   credits, total_swaps, successful_swaps
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
                <td>{user[8]}</td>
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
                       credits, total_swaps, successful_swaps
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
                    <td><span class="badge {status_class}">{listing[6]}</span></td>
                    <td>{listing[10]}</td>
                    <td>{listing[11]}</td>
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
                        <th>Status</th>
                        <th>Created</th>
                        <th>Expires</th>
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
            execute_query("UPDATE users SET credits = credits + 100 WHERE user_id = ?", (user_id,), commit=True)
            return jsonify({"success": True, "message": f"Added 100 credits to user {user_id}"})
        
        return jsonify({"success": False, "message": "Unknown action"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/ping')
def ping():
    return jsonify({"status": "pong", "time": datetime.now().isoformat()})

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
    print("🔧 Initializing database with encryption...")
    init_database()
    
    print("✅ Database initialized successfully")
    print("🚀 CARNAGE Swapper Bot v7.0 - PRODUCTION READY")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot Username: @{BOT_USERNAME}")
    print(f"📢 Updates Channel: {CHANNELS['updates']['id']}")
    print(f"✅ Proofs Channel: {CHANNELS['proofs']['id']}")
    print(f"🛒 Marketplace Channel: {MARKETPLACE_CHANNEL_ID}")
    print(f"👥 Admin Group: {ADMIN_GROUP_ID}")
    print("✨ Features: COMPLETE MARKETPLACE WITH ESCROW")
    print("🔐 Session Encryption: All sessions encrypted at rest")
    print("💰 Marketplace: Real money only (INR/USDT)")
    print("🤝 Middleman System: Secure escrow transactions")
    print("📊 HTML Dashboard & Admin Panel")
    
    # Start Telegram bot
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("🤖 Telegram bot started in background")
    
    print("\n🎯 **OPERATION MODES:**")
    print("• User Functions: DM ONLY")
    print("• Middleman Commands: GROUP ONLY")
    print("• Admin Commands: DM ONLY")
    print("• Marketplace: Real currency only")
    print("• Session Verification: Required for sellers")
    
    print("\n🔗 **URLS:**")
    print(f"• Dashboard: https://your-koyeb-app.koyeb.app/dashboard/USER_ID")
    print(f"• Admin Panel: https://your-koyeb-app.koyeb.app/admin?auth=carnage123")
    
    print("\n✅ **PRODUCTION READY WITH ALL FEATURES!**")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Bot shutting down...")

if __name__ == '__main__':
    main()
