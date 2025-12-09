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
from flask import Flask, jsonify, render_template_string, request, render_template
import hashlib
import html

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8165377023:AAENQLmAiS2QcZr93R6uYcwXG0gs6AuVduA')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '7575087826'))
BOT_USERNAME = "CarnageSwapperBot"

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

# ======= MARKETPLACE GROUP & CHANNEL =======
MARKETPLACE_GROUP_ID = "-1003282021421"  # Marketplace group
MARKETPLACE_CHANNEL_ID = "-1003364960970"  # Marketplace channel

# ======= ADMIN GROUP CONFIGURATION =======
ADMIN_GROUP_ID = "-1001234567890"  # Replace with your admin group ID
ESCROW_ADMINS = [ADMIN_USER_ID]  # List of admin IDs who can handle escrow

# ======= PAYMENT CONFIGURATION =======
INR_RATE = 100  # 1 credit = 100 INR

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
            
            // Smooth scrolling
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
                anchor.addEventListener('click', function (e) {{
                    e.preventDefault();
                    document.querySelector(this.getAttribute('href')).scrollIntoView({{
                        behavior: 'smooth'
                    }});
                }});
            }});
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
            
            .pagination {{
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-top: 30px;
            }}
            
            .page-btn {{
                padding: 8px 12px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s;
            }}
            
            .page-btn.active {{
                background: linear-gradient(45deg, #00dbde, #fc00ff);
            }}
            
            .page-btn:hover {{
                background: rgba(255, 255, 255, 0.2);
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
            
            <div class="tabs" id="tabs">
                <div class="tab active" onclick="showTab('users')">
                    <i class="fas fa-users"></i> Users
                </div>
                <div class="tab" onclick="showTab('transactions')">
                    <i class="fas fa-exchange-alt"></i> Transactions
                </div>
                <div class="tab" onclick="showTab('marketplace')">
                    <i class="fas fa-store"></i> Marketplace
                </div>
                <div class="tab" onclick="showTab('swaps')">
                    <i class="fas fa-sync-alt"></i> Swaps
                </div>
                <div class="tab" onclick="showTab('system')">
                    <i class="fas fa-cog"></i> System
                </div>
            </div>
            
            <input type="text" class="search-box" placeholder="Search..." id="searchInput" onkeyup="searchTable()">
            
            <div class="content" id="content">
                <!-- Content will be loaded here by JavaScript -->
                {initial_content}
            </div>
            
            <div class="pagination" id="pagination">
                <!-- Pagination will be loaded here by JavaScript -->
            </div>
        </div>
        
        <script>
            let currentTab = 'users';
            let currentPage = 1;
            const itemsPerPage = 10;
            
            function showTab(tabName) {{
                currentTab = tabName;
                currentPage = 1;
                
                // Update active tab
                document.querySelectorAll('.tab').forEach(tab => {{
                    tab.classList.remove('active');
                }});
                event.target.classList.add('active');
                
                // Load tab content
                loadTabContent();
            }}
            
            function loadTabContent() {{
                fetch(`/admin/api/${{currentTab}}?page=${{currentPage}}`)
                    .then(response => response.json())
                    .then(data => {{
                        updateContent(data);
                        updatePagination(data.total, data.pages);
                    }});
            }}
            
            function updateContent(data) {{
                const content = document.getElementById('content');
                
                if (currentTab === 'users') {{
                    let html = `<h3><i class="fas fa-users"></i> Users Management</h3>`;
                    html += `<table id="usersTable">
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
                        <tbody>`;
                    
                    data.users.forEach(user => {{
                        const statusClass = user.is_banned ? 'badge-danger' : 
                                          user.approved ? 'badge-success' : 'badge-warning';
                        const statusText = user.is_banned ? 'Banned' : 
                                         user.approved ? 'Approved' : 'Pending';
                        
                        html += `<tr>
                            <td>${{user.user_id}}</td>
                            <td>${{user.username || 'N/A'}}</td>
                            <td><span class="badge">${{user.tier.toUpperCase()}}</span></td>
                            <td>${{user.total_swaps}} (${{user.successful_swaps}}✅)</td>
                            <td>${{user.credits}}</td>
                            <td><span class="badge ${{statusClass}}">${{statusText}}</span></td>
                            <td>
                                <button class="btn btn-small" onclick="adminAction('approve', ${{user.user_id}})">Approve</button>
                                <button class="btn btn-small" onclick="adminAction('ban', ${{user.user_id}})">Ban</button>
                                <button class="btn btn-small" onclick="adminAction('addcredits', ${{user.user_id}})">Add Credits</button>
                            </td>
                        </tr>`;
                    }});
                    
                    html += `</tbody></table>`;
                    content.innerHTML = html;
                }}
                else if (currentTab === 'transactions') {{
                    // Similar structure for other tabs
                }}
            }}
            
            function updatePagination(total, pages) {{
                const pagination = document.getElementById('pagination');
                let html = '';
                
                for (let i = 1; i <= pages; i++) {{
                    html += `<div class="page-btn ${{i === currentPage ? 'active' : ''}}" 
                             onclick="changePage(${{i}})">${{i}}</div>`;
                }}
                
                pagination.innerHTML = html;
            }}
            
            function changePage(page) {{
                currentPage = page;
                loadTabContent();
            }}
            
            function searchTable() {{
                // Implement search functionality
            }}
            
            function adminAction(action, userId) {{
                const reason = prompt('Enter reason (optional):');
                fetch('/admin/api/action', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{action, userId, reason}})
                }})
                .then(response => response.json())
                .then(data => {{
                    alert(data.message);
                    loadTabContent();
                }});
            }}
            
            // Load initial content
            loadTabContent();
            
            // Auto-refresh every 60 seconds
            setInterval(loadTabContent, 60000);
        </script>
    </body>
    </html>
    '''
}

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
    """Initialize SQLite database with all tables"""
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
                    credits INTEGER DEFAULT 0,
                    tier TEXT DEFAULT 'free',
                    subscription_until TEXT DEFAULT NULL,
                    total_swaps INTEGER DEFAULT 0,
                    successful_swaps INTEGER DEFAULT 0,
                    join_method TEXT DEFAULT 'direct',
                    channels_joined INTEGER DEFAULT 0,
                    main_session TEXT DEFAULT NULL,
                    main_username TEXT DEFAULT NULL,
                    target_session TEXT DEFAULT NULL,
                    target_username TEXT DEFAULT NULL,
                    backup_session TEXT DEFAULT NULL,
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
            
            # Check if admin exists
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (ADMIN_USER_ID,))
            if not cursor.fetchone():
                referral_code = generate_referral_code(ADMIN_USER_ID)
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, approved, 
                                      approved_until, join_date, last_active, is_admin, 
                                      referral_code, tier, credits, free_swaps_earned)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ADMIN_USER_ID, "admin", "Admin", "User", 1, 
                    "9999-12-31 23:59:59",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    1, referral_code, "vip", 1000000, 100
                ))
            
            conn.commit()
            conn.close()
            
            print("✅ Database initialized successfully")
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# ==================== BASIC HELPER FUNCTIONS ====================
def is_admin(user_id):
    """Check if user is admin"""
    return user_id == ADMIN_USER_ID or user_id in ESCROW_ADMINS

def generate_referral_code(user_id):
    """Generate unique referral code"""
    return f"CARNAGE{user_id}{random.randint(1000, 9999)}"

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

def validate_session(session_id, chat_id, session_type):
    """Validate Instagram session ID"""
    print(f"Validating session for chat_id: {chat_id}, type: {session_type}")
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
    session_data[chat_id]["current_menu"] = "swapper" if session_type == "backup" else "main"
    return None

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
        response_text = response.text[:500]
        
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
    """Revert username back to original"""
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'Default Name'),
        'email': 'default@example.com',
        'username': original_username.lstrip('@'),
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
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except:
        return False

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

def save_session_to_db(user_id, session_type, session_id, username):
    """Save session to database"""
    if session_type == "main":
        execute_query("UPDATE users SET main_session = ?, main_username = ? WHERE user_id = ?", 
                     (session_id, username, user_id), commit=True)
    elif session_type == "target":
        execute_query("UPDATE users SET target_session = ?, target_username = ? WHERE user_id = ?", 
                     (session_id, username, user_id), commit=True)
    elif session_type == "backup":
        execute_query("UPDATE users SET backup_session = ?, backup_username = ? WHERE user_id = ?", 
                     (session_id, username, user_id), commit=True)

def get_user_sessions(user_id):
    """Get user's saved sessions from database"""
    result = execute_one("SELECT main_session, main_username, target_session, target_username FROM users WHERE user_id = ?", (user_id,))
    if result:
        return {
            'main': result[0],
            'main_username': result[1],
            'target': result[2],
            'target_username': result[3]
        }
    return {'main': None, 'main_username': None, 'target': None, 'target_username': None}

# ==================== DATABASE FUNCTIONS ====================
def add_user(user_id, username, first_name, last_name, referral_code="direct"):
    """Add new user to database"""
    existing_user = execute_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing_user:
        return
    
    user_referral_code = generate_referral_code(user_id)
    execute_query('''
        INSERT INTO users (user_id, username, first_name, last_name, join_date, last_active, 
                          referral_code, join_method, main_session, target_session, backup_session, credits)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          user_referral_code, 'direct', None, None, None, 100), commit=True)
    
    if referral_code and referral_code != "direct":
        process_referral(user_id, referral_code)
    
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
    
    if status == "success":
        result = execute_one("SELECT COUNT(*) FROM swap_history WHERE user_id = ? AND status = 'success'", (user_id,))
        success_count = result[0] if result else 0
        if success_count == 1:
            award_achievement(user_id, "first_swap")
        if success_count >= 10:
            award_achievement(user_id, "swap_pro")
    elif status == "failed":
        award_achievement(user_id, "swap_failed")

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
    
    achievements = get_user_achievements(user_id)
    
    return {
        "username": username or "User",
        "bot_username": BOT_USERNAME,
        "user_id": user_id,
        "join_date": join_date,
        "last_active": last_active,
        "tier": tier,
        "credits": credits,
        "stats": [
            {"name": "Total Swaps", "value": total_swaps},
            {"name": "Successful Swaps", "value": successful_swaps},
            {"name": "Success Rate", "value": f"{success_rate:.1f}%"},
            {"name": "Total Referrals", "value": total_referrals},
            {"name": "Free Swaps Available", "value": free_swaps},
            {"name": "Credits Balance", "value": credits},
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
        
        award_achievement(referrer_id, "referral_master")
        
        if get_user_referrals_count(referrer_id) >= 5:
            award_achievement(referrer_id, "referral_master")

def get_user_referrals_count(user_id):
    """Get count of user's referrals"""
    result = execute_one("SELECT COUNT(*) FROM referral_tracking WHERE referrer_id = ?", (user_id,))
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
    "swap_pro": {"name": "Swap Pro", "emoji": "⚡", "description": "Complete 10 successful swaps"},
    "referral_master": {"name": "Referral Master", "emoji": "🤝", "description": "Refer 5 friends"},
    "early_adopter": {"name": "Early Adopter", "emoji": "🚀", "description": "Join first 100 users"},
    "founder": {"name": "Founder", "emoji": "👑", "description": "Bot creator"},
    "first_user": {"name": "Pioneer", "emoji": "🧭", "description": "First 50 users"},
    "tutorial_complete": {"name": "Quick Learner", "emoji": "🎓", "description": "Complete interactive tutorial"},
    "dashboard_user": {"name": "Dashboard Pro", "emoji": "📊", "description": "Visit web dashboard"},
    "channel_member": {"name": "Official Member", "emoji": "📢", "description": "Join both official channels"},
    "swap_failed": {"name": "First Fail", "emoji": "💀", "description": "Experience your first failed swap"},
    "swap_streak_3": {"name": "3-Day Streak", "emoji": "🔥", "description": "Swap for 3 consecutive days"},
    "first_session": {"name": "Session Master", "emoji": "🔐", "description": "Add first Instagram session"},
    "marketplace_seller": {"name": "Marketplace Seller", "emoji": "💰", "description": "List first username for sale"},
}

def award_achievement(user_id, achievement_id):
    """Award an achievement to user"""
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
    
    achievement_list = []
    for ach in achievements:
        achievement_list.append({
            "id": ach[0],
            "name": ach[1],
            "emoji": ach[2],
            "date": ach[3],
            "unlocked": True
        })
    
    # Add locked achievements
    unlocked_ids = [ach[0] for ach in achievements]
    for ach_id, ach_data in ACHIEVEMENTS.items():
        if ach_id not in unlocked_ids:
            achievement_list.append({
                "id": ach_id,
                "name": ach_data["name"],
                "emoji": ach_data["emoji"],
                "date": None,
                "unlocked": False
            })
    
    return {
        "unlocked": unlocked,
        "total": total,
        "list": achievement_list
    }

def get_total_achievements_awarded():
    """Get total achievements awarded"""
    result = execute_one("SELECT COUNT(*) FROM achievements")
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
        "🏆 Achievements", "📈 Stats"
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
@bot.message_handler(commands=['users'])
def admin_users(message):
    """List all users - ADMIN ONLY"""
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
        
        # Check if user exists
        user = execute_one("SELECT username FROM users WHERE user_id = ?", (target_id,))
        if not user:
            bot.reply_to(message, "❌ User not found")
            return
        
        # Unban user
        execute_query('''
            UPDATE users 
            SET is_banned = 0, ban_reason = NULL
            WHERE user_id = ?
        ''', (target_id,), commit=True)
        
        # Notify user
        try:
            bot.send_message(target_id, "✅ Your ban has been lifted. You can now use the bot again.")
        except:
            pass
        
        bot.reply_to(message, f"✅ User {target_id} has been unbanned.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['approve'])
def admin_approve(message):
    """Approve a user - ADMIN ONLY"""
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

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    """Broadcast message to all users - ADMIN ONLY"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Admin only command")
        return
    
    try:
        if len(message.text.split()) < 2:
            bot.reply_to(message, "Usage: /broadcast <message>")
            return
        
        broadcast_msg = message.text.split(' ', 1)[1]
        
        # Get all user IDs
        users = execute_query("SELECT user_id FROM users WHERE is_banned = 0")
        
        bot.reply_to(message, f"📢 Broadcasting to {len(users)} users...")
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                bot.send_message(
                    user["user_id"],
                    f"📢 *Announcement from CARNAGE*\n\n{broadcast_msg}\n\n— Team CARNAGE",
                    parse_mode="Markdown"
                )
                sent += 1
                time.sleep(0.1)  # Rate limiting
            except:
                failed += 1
        
        bot.reply_to(message, f"✅ Broadcast completed!\nSent: {sent} | Failed: {failed}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addcredits'])
def admin_addcredits(message):
    """Add credits to user - ADMIN ONLY"""
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
            f"• API Status: {'✅ Online' if check_api_status() else '❌ Offline'}\n\n"
            
            f"💾 *Database:*\n"
            f"• Size: {get_database_size()} KB\n"
            f"• Tables: 5\n"
        )
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def check_api_status():
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
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    
    referral_code = "direct"
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith("ref-"):
            referral_code = param[4:]
        elif param == "tutorial":
            start_tutorial_command(message)
            return
        elif param == "swap":
            if is_user_approved(user_id):
                show_swapper_menu(user_id)
            else:
                bot.send_message(user_id, "Please complete /start first")
            return
    
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
/transactions - Your transaction history

*Swap Features:*
• Real Instagram username swapping
• Working API with rate limit handling
• Session validation and management
• Backup mode and threads support

*Admin Commands (Admin only):*
/users - List all users
/ban <id> <reason> - Ban user
/unban <id> - Unban user
/approve <id> <duration> - Approve user
/broadcast <msg> - Broadcast to all users
/addcredits <id> <amount> - Add credits
/stats - Bot statistics

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
"""
    
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['dashboard'])
def dashboard_command(message):
    """Dashboard command"""
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    dashboard_url = f"https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/{user_id}"
    bot.send_message(user_id, f"📊 *Your Dashboard:*\n\n{dashboard_url}", parse_mode="Markdown")
    award_achievement(user_id, "dashboard_user")

@bot.message_handler(commands=['referral', 'refer'])
def referral_command(message):
    """Referral command"""
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
• Total Swaps: {stats['stats'][0]['value']}
• Successful: {stats['stats'][1]['value']}
• Success Rate: {stats['stats'][2]['value']}

*Referral Stats:*
• Total Referrals: {stats['referrals']['count']}
• Free Swaps Available: {stats['referrals']['free_swaps']}

*Credits:*
• Balance: {stats['credits']} 🪙

*Achievements:* {stats['achievements']['unlocked']}/{stats['achievements']['total']}
"""
        bot.send_message(user_id, response, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "📊 *No statistics yet. Start swapping!*", parse_mode="Markdown")

@bot.message_handler(commands=['achievements'])
def achievements_command(message):
    """Achievements command"""
    user_id = message.from_user.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    achievements = get_user_achievements(user_id)
    response = "🏆 *Your Achievements*\n\n"
    
    if achievements['list']:
        unlocked = 0
        for ach in achievements['list']:
            if ach['unlocked']:
                unlocked += 1
                response += f"✅ {ach['emoji']} *{ach['name']}* - {ach['date'].split()[0]}\n"
            else:
                response += f"🔒 {ach['emoji']} {ach['name']}\n"
        
        response += f"\n*Progress:* {unlocked}/{achievements['total']} unlocked"
    else:
        response += "No achievements yet! Start using the bot to unlock badges! 🔄"
    
    bot.send_message(user_id, response, parse_mode="Markdown")

# ==================== MENU HANDLERS ====================
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
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
    chat_id = message.chat.id
    session_id = message.text.strip()
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "❌ Your account is not approved yet.", parse_mode="Markdown")
        show_main_menu(chat_id)
        return
    
    username = validate_session(session_id, chat_id, "main")
    if username:
        session_data[chat_id]["main"] = session_id
        session_data[chat_id]["main_username"] = f"@{username}"
        session_data[chat_id]["main_validated_at"] = time.time()
        save_session_to_db(chat_id, "main", session_id, username)
        bot.send_message(chat_id, f"✅ *Main Session Logged @{username}*", parse_mode="Markdown")
        award_achievement(chat_id, "first_session")
    
    show_main_menu(chat_id)

def save_target_session(message):
    """Save target session"""
    chat_id = message.chat.id
    session_id = message.text.strip()
    
    if not is_user_approved(chat_id):
        bot.send_message(chat_id, "❌ Your account is not approved yet.", parse_mode="Markdown")
        show_main_menu(chat_id)
        return
    
    username = validate_session(session_id, chat_id, "target")
    if username:
        session_data[chat_id]["target"] = session_id
        session_data[chat_id]["target_username"] = f"@{username}"
        session_data[chat_id]["target_validated_at"] = time.time()
        save_session_to_db(chat_id, "target", session_id, username)
        bot.send_message(chat_id, f"✅ *Target Session Logged @{username}*", parse_mode="Markdown")
        award_achievement(chat_id, "first_session")
    
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
    chat_id = message.chat.id
    session_id = message.text.strip()
    username = validate_session(session_id, chat_id, "backup")
    if username:
        session_data[chat_id]["backup"] = session_id
        session_data[chat_id]["backup_username"] = f"@{username}"
        save_session_to_db(chat_id, "backup", session_id, username)
        bot.send_message(chat_id, f"✅ *Backup Session Logged @{username}*", parse_mode="Markdown")
    show_swapper_menu(chat_id)

def save_swapper_threads(message):
    """Save swapper threads"""
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
    chat_id = message.chat.id
    bio = message.text.strip()
    session_data[chat_id]["bio"] = bio
    bot.send_message(chat_id, "✅ *Bio Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def save_name(message):
    """Save name"""
    chat_id = message.chat.id
    name = message.text.strip()
    session_data[chat_id]["name"] = name
    bot.send_message(chat_id, "✅ *Name Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def save_swap_webhook(message):
    """Save webhook"""
    chat_id = message.chat.id
    webhook = message.text.strip()
    session_data[chat_id]["swap_webhook"] = webhook
    bot.send_message(chat_id, "✅ *Webhook Saved*", parse_mode="Markdown")
    show_settings_menu(chat_id)

def process_check_block(message):
    """Process check block"""
    chat_id = message.chat.id
    response = message.text.strip().lower()
    if response == 'y':
        bot.send_message(chat_id, "✅ *Account is swappable!*", parse_mode="Markdown")
    elif response == 'n':
        bot.send_message(chat_id, "❌ *Account is not swappable!*", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Send 'Y' or 'N'", parse_mode="Markdown")
    show_settings_menu(chat_id)

def run_main_swap(chat_id):
    """Run main swap"""
    global requests_count, errors_count
    
    if not session_data[chat_id]["main"] or not session_data[chat_id]["target"]:
        bot.send_message(chat_id, "❌ *Set Main and Target Sessions first*", parse_mode="Markdown")
        show_swapper_menu(chat_id)
        return
    
    # Validate sessions
    main_valid = validate_session(session_data[chat_id]["main"], chat_id, "main")
    target_valid = validate_session(session_data[chat_id]["target"], chat_id, "target")
    
    if not main_valid or not target_valid:
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
            award_achievement(chat_id, "first_swap")
        else:
            bot.edit_message_text(f"❌ *Swap failed for {target_username}*", chat_id, message_id, parse_mode="Markdown")
            if revert_username(chat_id, target_session, csrf_token, target_username):
                bot.send_message(chat_id, f"✅ *Successfully reverted to {target_username}*", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, f"⚠️ *Warning: Could not revert to {target_username}*", parse_mode="Markdown")
            log_swap(chat_id, target_username, "failed", "Swap process failed")
            award_achievement(chat_id, "swap_failed")
        
        clear_session_data(chat_id, "main")
        clear_session_data(chat_id, "target")
        
    except Exception as e:
        bot.edit_message_text(f"❌ *Error during swap: {str(e)}*", chat_id, message_id, parse_mode="Markdown")
        log_swap(chat_id, "unknown", "failed", str(e))
    
    show_swapper_menu(chat_id)

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Handle callback queries"""
    user_id = call.from_user.id
    message_id = call.message.message_id
    
    if call.data == "check_channels":
        channel_results = check_all_channels(user_id)
        
        if all(channel_results.values()):
            bot.answer_callback_query(call.id, "✅ Verified! You've joined all channels!")
            bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text="🎉 *Channel Verification Successful!*\n\nYou've joined all required channels! ✅\n\nNow you can use the bot features.\n\nSend /start again to begin.",
                parse_mode="Markdown"
            )
            
            execute_query("UPDATE users SET channels_joined = 1 WHERE user_id = ?", (user_id,), commit=True)
            award_achievement(user_id, "channel_member")
            
            time.sleep(1)
            welcome_features = f"""
🤖 *Welcome to CARNAGE Swapper Bot!* 🎉

*Features:*
✨ *Real Instagram Swapping* - Working API
📊 *Web Dashboard* - Track your stats online
🏆 *Achievements* - Unlock badges as you swap
🎓 *Interactive Tutorial* - Learn step by step
🎁 *Referral System* - Get 2 FREE swaps per friend!

*Quick Start:*
1️⃣ Add Instagram sessions
2️⃣ Swap usernames instantly
3️⃣ Refer friends for FREE swaps
4️⃣ Track progress on dashboard

Use /tutorial for guided tour or /help for commands.
"""
            bot.send_message(user_id, welcome_features, parse_mode="Markdown")
            
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

# ==================== TUTORIAL SYSTEM ====================
@bot.message_handler(commands=['tutorial'])
def start_tutorial_command(message):
    """Start tutorial"""
    user_id = message.chat.id
    if not has_joined_all_channels(user_id):
        send_welcome_with_channels(user_id, message.from_user.first_name)
        return
    
    tutorial_sessions[user_id] = 0
    show_tutorial_step(user_id, 0)

TUTORIAL_STEPS = [
    {
        "title": "🎯 Welcome to CARNAGE Tutorial!",
        "message": "Learn how to swap Instagram usernames with our bot!",
        "buttons": ["Let's Go! 🚀", "Skip Tutorial"]
    },
    {
        "title": "📱 Session Management",
        "message": "1. Get Instagram session ID from browser cookies\n2. Use 'Main Session' for your account\n3. Use 'Target Session' for account you want to swap with\n4. Sessions are validated automatically",
        "buttons": ["Got it! 👍", "Back"]
    },
    {
        "title": "🔄 Swapping Process",
        "message": "1. Add both Main and Target sessions\n2. Click 'Run Main Swap'\n3. Bot changes target to random username\n4. Bot changes main to target username\n5. Success notification sent",
        "buttons": ["Ready to Swap! 🔄", "Back"]
    },
    {
        "title": "⚙️ Settings & Features",
        "message": "• Bio/Name: For Instagram profile\n• Webhook: Discord notifications\n• Check Block: Verify account status\n• Dashboard: Web statistics\n• Referral: Earn FREE swaps",
        "buttons": ["Awesome! 🌟", "Back"]
    },
    {
        "title": "🎁 Referral System",
        "message": "• Share your referral link\n• Each friend = 2 FREE swaps for you\n• Friend gets instant approval\n• Track referrals in dashboard",
        "buttons": ["Let's Start! 🏁", "Back"]
    }
]

def show_tutorial_step(chat_id, step_index):
    """Show tutorial step"""
    if step_index >= len(TUTORIAL_STEPS):
        del tutorial_sessions[chat_id]
        award_achievement(chat_id, "tutorial_complete")
        bot.send_message(chat_id, "🎉 *Tutorial Completed!*\n\nYou're now ready to start swapping!\n\nUse /help for commands or go to Main Menu.", parse_mode="Markdown")
        show_main_menu(chat_id)
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
    
    tutorial_sessions[chat_id] = step_index

def handle_tutorial_response(chat_id, text):
    """Handle tutorial responses"""
    if chat_id not in tutorial_sessions:
        return False
    
    current_step = tutorial_sessions[chat_id]
    
    if text == "Back":
        if current_step > 0:
            show_tutorial_step(chat_id, current_step - 1)
        return True
    
    elif text == "Skip Tutorial":
        del tutorial_sessions[chat_id]
        bot.send_message(chat_id, "Tutorial skipped! Use /tutorial anytime.", 
                        reply_markup=create_reply_menu(["Main Menu"]))
        return True
    
    elif "Let's Go" in text or "Got it" in text or "Ready" in text or "Awesome" in text or "Let's Start" in text:
        show_tutorial_step(chat_id, current_step + 1)
        return True
    
    return False

# ==================== FLASK ROUTES ====================
@app.route('/')
def health_check():
    return jsonify({
        "status": "online",
        "service": "CARNAGE Swapper Bot",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0",
        "users": get_total_users(),
        "swaps": execute_one("SELECT COUNT(*) FROM swap_history")[0] or 0
    })

@app.route('/dashboard/<int:user_id>')
def user_dashboard(user_id):
    """User dashboard HTML page"""
    try:
        # Get user data
        stats = get_user_detailed_stats(user_id)
        if not stats:
            return "User not found", 404
        
        # Format achievements HTML
        achievements_html = ""
        for ach in stats['achievements']['list'][:6]:  # Show first 6
            if ach['unlocked']:
                achievements_html += f'''
                <div class="achievement unlocked">
                    <div class="achievement emoji">{ach['emoji']}</div>
                    <div class="achievement name">{ach['name']}</div>
                </div>
                '''
            else:
                achievements_html += f'''
                <div class="achievement">
                    <div class="achievement emoji">{ach['emoji']}</div>
                    <div class="achievement name">{ach['name']}</div>
                </div>
                '''
        
        # Format recent swaps HTML
        recent_swaps_html = ""
        if stats['recent_swaps']:
            for swap in stats['recent_swaps'][:5]:
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
            total_swaps=stats['stats'][0]['value'],
            successful_swaps=stats['stats'][1]['value'],
            success_rate=stats['stats'][2]['value'].replace('%', ''),
            total_referrals=stats['referrals']['count'],
            free_swaps=stats['referrals']['free_swaps'],
            achievements_unlocked=stats['achievements']['unlocked'],
            achievements_total=stats['achievements']['total'],
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
    if auth != os.environ.get('ADMIN_SECRET', 'carnage123'):
        return "Unauthorized", 401
    
    try:
        # Get admin stats
        total_users = get_total_users()
        active_users = execute_one("SELECT COUNT(*) FROM users WHERE last_active > ?",
                                 ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),))[0]
        
        total_swaps = execute_one("SELECT COUNT(*) FROM swap_history")[0] or 0
        successful_swaps = execute_one("SELECT COUNT(*) FROM swap_history WHERE status = 'success'")[0] or 0
        success_rate = (successful_swaps / total_swaps * 100) if total_swaps > 0 else 0
        
        # Get users for initial table
        users = execute_query('''
            SELECT user_id, username, first_name, tier, approved, is_banned, 
                   credits, total_swaps, successful_swaps
            FROM users 
            ORDER BY user_id
            LIMIT 10
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
                <td>{user[7]} ({user[8]}✅)</td>
                <td>{user[6]}</td>
                <td><span class="badge {status_class}">{status_text}</span></td>
                <td>
                    <button class="btn btn-small" onclick="adminAction('approve', {user[0]})">Approve</button>
                    <button class="btn btn-small" onclick="adminAction('ban', {user[0]})">Ban</button>
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
            total_listings=0,
            pending_transactions=0,
            initial_content=initial_content
        )
        
        return html_content
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/admin/api/<action>')
def admin_api(action):
    """Admin API endpoints"""
    # Implement API endpoints for admin panel
    return jsonify({"status": "ok", "action": action})

@app.route('/ping')
def ping():
    return jsonify({"status": "pong", "time": datetime.now().isoformat()})

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "users": get_total_users(),
        "uptime": time.time() - start_time
    })

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
    print("🔧 Initializing database...")
    init_database()
    
    print("✅ Database initialized successfully")
    print("🚀 CARNAGE Swapper Bot v4.0")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot Username: @{BOT_USERNAME}")
    print(f"📢 Updates Channel: {CHANNELS['updates']['id']}")
    print(f"✅ Proofs Channel: {CHANNELS['proofs']['id']}")
    print(f"🛒 Marketplace Group: {MARKETPLACE_GROUP_ID}")
    print(f"📢 Marketplace Channel: {MARKETPLACE_CHANNEL_ID}")
    print("✨ Features: Dashboard, Admin Panel, Referral (2 swaps per ref), HTML Interface")
    print(f"💰 Referral Rewards: 1 referral = 2 FREE swaps")
    
    # Start Telegram bot
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("🤖 Telegram bot started in background")
    
    print(f"📊 Dashboard: https://separate-genny-1carnage1-2b4c603c.koyeb.app/dashboard/USER_ID")
    print(f"👑 Admin Panel: https://separate-genny-1carnage1-2b4c603c.koyeb.app/admin?auth=carnage123")
    print("✅ Bot is fully operational with HTML Dashboard & Admin Panel!")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Bot shutting down...")

if __name__ == '__main__':
    main()
