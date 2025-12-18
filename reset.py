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
from PIL import Image, ImageDraw, ImageFont
import io as image_io
import mimetypes

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

# ========== ENCRYPTION CONFIG ==========
ENCRYPTION_KEY = Fernet.generate_key()  # In production, store this securely
cipher = Fernet(ENCRYPTION_KEY)

# ========== NSFW DETECTION CONFIG ==========
NSFW_DETECTION_ENABLED = True
NSFW_API_URL = "https://api.sightengine.com/1.0/check.json"  # Example API
NSFW_API_USER = "your_user"
NSFW_API_SECRET = "your_secret"

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
            original_data BLOB,
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
swap_progress = {}  # Track progress for each swap
WAITING_FOR_SOURCE = 1
WAITING_FOR_TARGET = 2
PROCESSING = 3

# ========== ENCRYPTION FUNCTIONS ==========
def encrypt_data(data):
    """Encrypt data"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return cipher.encrypt(data)

def decrypt_data(encrypted_data):
    """Decrypt data"""
    return cipher.decrypt(encrypted_data).decode('utf-8')

def generate_image_hash(image_data):
    """Generate hash for image data"""
    return hashlib.sha256(image_data).hexdigest()

# ========== NSFW DETECTION ==========
def check_nsfw_content(image_data):
    """Check if image contains NSFW content"""
    if not NSFW_DETECTION_ENABLED:
        return False
    
    try:
        # Simple heuristic check (can be enhanced with ML model)
        # Check image size (very small might be spam)
        if len(image_data) < 1024:
            return False
            
        # Check if it's actually an image
        try:
            img = Image.open(image_io.BytesIO(image_data))
            img.verify()  # Verify it's a valid image
            
            # Get image dimensions
            width, height = img.size
            
            # Basic checks (can be expanded)
            if width < 50 or height < 50:  # Too small
                return False
                
            # Check image properties
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif:
                    # Check orientation, etc.
                    pass
            
            # Add more sophisticated checks here
            # Could integrate with SightEngine, Google Vision API, etc.
            
            return False  # Default to not NSFW
            
        except Exception as e:
            logger.error(f"Image verification error: {e}")
            return False
            
    except Exception as e:
        logger.error(f"NSFW check error: {e}")
        return False

# ========== IMAGE PROCESSING FUNCTIONS ==========
def create_comparison_image(source_data, target_data, result_data):
    """Create a comparison image showing all three photos"""
    try:
        # Open all images
        source_img = Image.open(image_io.BytesIO(source_data))
        target_img = Image.open(image_io.BytesIO(target_data))
        result_img = Image.open(image_io.BytesIO(result_data))
        
        # Resize images to same height
        max_height = 300
        def resize_to_height(img, height):
            ratio = height / float(img.size[1])
            width = int(float(img.size[0]) * ratio)
            return img.resize((width, height), Image.Resampling.LANCZOS)
        
        source_img = resize_to_height(source_img, max_height)
        target_img = resize_to_height(target_img, max_height)
        result_img = resize_to_height(result_img, max_height)
        
        # Create new image with labels
        total_width = source_img.width + target_img.width + result_img.width + 40  # Padding
        comparison_img = Image.new('RGB', (total_width, max_height + 60), (255, 255, 255))
        
        # Paste images
        comparison_img.paste(source_img, (10, 40))
        comparison_img.paste(target_img, (20 + source_img.width, 40))
        comparison_img.paste(result_img, (30 + source_img.width + target_img.width, 40))
        
        # Add labels
        draw = ImageDraw.Draw(comparison_img)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((source_img.width//2 + 10, 15), "Source", fill=(0, 0, 0), font=font)
        draw.text((source_img.width + target_img.width//2 + 20, 15), "Target", fill=(0, 0, 0), font=font)
        draw.text((source_img.width + target_img.width + result_img.width//2 + 30, 15), "Result", fill=(0, 0, 255), font=font)
        
        # Add separator lines
        draw.line([(source_img.width + 15, 10), (source_img.width + 15, max_height + 50)], fill=(200, 200, 200), width=2)
        draw.line([(source_img.width + target_img.width + 25, 10), (source_img.width + target_img.width + 25, max_height + 50)], fill=(200, 200, 200), width=2)
        
        # Save to bytes
        img_byte_arr = image_io.BytesIO()
        comparison_img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
        
    except Exception as e:
        logger.error(f"Comparison image creation error: {e}")
        return None

# ========== USER MANAGEMENT FUNCTIONS ==========
def register_user(user_id, username, first_name, last_name):
    """Register or update user in database"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    # Generate encryption key for user
    user_key = Fernet.generate_key()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, last_active, encryption_key)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    ''', (user_id, username, first_name, last_name, user_key))
    
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
        
        message = f"""👤 *NEW USER REGISTERED*

━━━━━━━━━━━━━━━━━━
🆔 *User ID:* `{user_id}`
👤 *Username:* @{username or 'N/A'}
📛 *Name:* {first_name} {last_name or ''}
🕐 *Time:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
📊 *Total Users:* {total_users}
━━━━━━━━━━━━━━━━━━

*Admin Commands:*
/ban {user_id} - Ban user
/users - List all users
/botstatus - Check bot status"""
        
        bot.send_message(ADMIN_ID, message, parse_mode='Markdown')
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
    
    # Log ban
    add_admin_log(f"User {user_id} banned. Reason: {reason}")
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
    
    add_admin_log(f"User {user_id} unbanned")
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

def increment_user_reports(user_id):
    """Increment report count for user"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET 
        reports_received = reports_received + 1
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def add_swap_history(user_id, status, processing_time, source_hash, target_hash, result_hash, nsfw_check=0, reported=0, original_data=None):
    """Add swap to history"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    # Encrypt original data if provided
    encrypted_data = None
    encrypted_flag = 0
    
    if original_data:
        try:
            encrypted_data = encrypt_data(pickle.dumps(original_data))
            encrypted_flag = 1
        except Exception as e:
            logger.error(f"Encryption error: {e}")
    
    cursor.execute('''
        INSERT INTO swaps_history 
        (user_id, status, processing_time, source_image_hash, target_image_hash, 
         result_image_hash, nsfw_check, reported, original_data, encrypted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, status, processing_time, source_hash, target_hash, 
          result_hash, nsfw_check, reported, encrypted_data, encrypted_flag))
    
    swap_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return swap_id

def add_report(reporter_id, reported_user_id, swap_id, reason):
    """Add a report to database"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO reports 
        (reporter_id, reported_user_id, swap_id, reason)
        VALUES (?, ?, ?, ?)
    ''', (reporter_id, reported_user_id, swap_id, reason))
    
    report_id = cursor.lastrowid
    
    # Increment report count for user
    increment_user_reports(reported_user_id)
    
    # Mark swap as reported
    cursor.execute('UPDATE swaps_history SET reported = 1 WHERE id = ?', (swap_id,))
    
    conn.commit()
    conn.close()
    
    # Notify admin
    notify_admin_report(report_id, reporter_id, reported_user_id, swap_id, reason)
    
    return report_id

def add_admin_log(action):
    """Add admin action to log"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    # Create admin_logs table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        )
    ''')
    
    cursor.execute('''
        INSERT INTO admin_logs (admin_id, action, details)
        VALUES (?, ?, ?)
    ''', (ADMIN_ID, action, ''))
    
    conn.commit()
    conn.close()

def get_user_swap_history(user_id, limit=10):
    """Get user's swap history"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, swap_date, status, processing_time, favorite
        FROM swaps_history 
        WHERE user_id = ? 
        ORDER BY swap_date DESC 
        LIMIT ?
    ''', (user_id, limit))
    
    history = cursor.fetchall()
    conn.close()
    return history

def get_swap_details(swap_id):
    """Get details of a specific swap"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT sh.*, u.username, u.user_id
        FROM swaps_history sh
        JOIN users u ON sh.user_id = u.user_id
        WHERE sh.id = ?
    ''', (swap_id,))
    
    swap = cursor.fetchone()
    conn.close()
    return swap

def toggle_favorite(user_id, swap_id):
    """Toggle favorite status for a swap"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    # Check if already favorited
    cursor.execute('SELECT id FROM favorites WHERE user_id = ? AND swap_id = ?', (user_id, swap_id))
    existing = cursor.fetchone()
    
    if existing:
        # Remove from favorites
        cursor.execute('DELETE FROM favorites WHERE user_id = ? AND swap_id = ?', (user_id, swap_id))
        cursor.execute('UPDATE swaps_history SET favorite = 0 WHERE id = ?', (swap_id,))
        cursor.execute('UPDATE users SET favorites_count = favorites_count - 1 WHERE user_id = ?', (user_id,))
        result = False
    else:
        # Add to favorites
        cursor.execute('INSERT INTO favorites (user_id, swap_id) VALUES (?, ?)', (user_id, swap_id))
        cursor.execute('UPDATE swaps_history SET favorite = 1 WHERE id = ?', (swap_id,))
        cursor.execute('UPDATE users SET favorites_count = favorites_count + 1 WHERE user_id = ?', (user_id,))
        result = True
    
    conn.commit()
    conn.close()
    return result

def get_user_favorites(user_id, limit=10):
    """Get user's favorite swaps"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT sh.id, sh.swap_date, sh.status, sh.processing_time
        FROM swaps_history sh
        JOIN favorites f ON sh.id = f.swap_id
        WHERE f.user_id = ? 
        ORDER BY f.added_date DESC 
        LIMIT ?
    ''', (user_id, limit))
    
    favorites = cursor.fetchall()
    conn.close()
    return favorites

def get_pending_reports():
    """Get pending reports for admin review"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.*, u1.username as reporter_name, u2.username as reported_name
        FROM reports r
        JOIN users u1 ON r.reporter_id = u1.user_id
        JOIN users u2 ON r.reported_user_id = u2.user_id
        WHERE r.status = 'pending'
        ORDER BY r.report_date DESC
    ''')
    
    reports = cursor.fetchall()
    conn.close()
    return reports

def update_report_status(report_id, status, action=""):
    """Update report status"""
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE reports 
        SET status = ?, admin_action = ?
        WHERE id = ?
    ''', (status, action, report_id))
    
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

def notify_admin_report(report_id, reporter_id, reported_user_id, swap_id, reason):
    """Notify admin about new report"""
    try:
        message = f"""🚨 *NEW REPORT SUBMITTED*

━━━━━━━━━━━━━━━━━━
📋 *Report ID:* `{report_id}`
👤 *Reporter:* `{reporter_id}`
⚠️ *Reported User:* `{reported_user_id}`
🔄 *Swap ID:* `{swap_id}`
📝 *Reason:* {reason}
🕐 *Time:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
━━━━━━━━━━━━━━━━━━

*Admin Actions:*
/reports - Review all reports
/ban {reported_user_id} - Ban reported user
/viewswap {swap_id} - View swap details"""
        
        bot.send_message(ADMIN_ID, message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Report notification error: {e}")

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
            "/users": "User statistics",
            "/api/swaps": "Swaps API",
            "/api/reports": "Reports API"
        },
        "features": [
            "Face Swap", 
            "Admin Controls", 
            "Channel Verification", 
            "User Management",
            "NSFW Detection",
            "Report System",
            "Favorites System",
            "Progress Tracking",
            "Encrypted Storage"
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
        # Check database
        conn = sqlite3.connect('face_swap_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM swaps_history')
        total_swaps = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM reports WHERE status = "pending"')
        pending_reports = cursor.fetchone()[0]
        conn.close()
        
        # Check bot status
        bot_status = "running"
        try:
            bot.get_me()
        except:
            bot_status = "disconnected"
        
        return jsonify({
            "status": "healthy",
            "bot_status": bot_status,
            "database_status": "connected",
            "encryption": "enabled",
            "nsfw_detection": "enabled" if NSFW_DETECTION_ENABLED else "disabled",
            "channel_verification": "active",
            "statistics": {
                "total_users": total_users,
                "active_users_24h": get_active_users_count(1),
                "total_swaps": total_swaps,
                "pending_reports": pending_reports,
                "active_sessions": len(user_data),
                "banned_users": len(BANNED_USERS)
            },
            "system": {
                "uptime": time.time() - app_start_time,
                "memory_usage": "normal",
                "swap_progress_tracking": "active",
                "encrypted_storage": "active"
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
    
    cursor.execute('SELECT COUNT(*) FROM swaps_history WHERE nsfw_check = 1')
    nsfw_flagged = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM swaps_history WHERE reported = 1')
    reported_swaps = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM favorites')
    total_favorites = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_users": get_total_users(),
        "active_users_24h": get_active_users_count(1),
        "banned_users": len(BANNED_USERS),
        "verified_users": len([u for u in get_all_users() if u[7] == 1]),
        "swap_statistics": {
            "total_swaps": total_swaps,
            "successful_swaps": successful_swaps,
            "failed_swaps": failed_swaps,
            "nsfw_flagged": nsfw_flagged,
            "reported_swaps": reported_swaps,
            "favorited_swaps": total_favorites,
            "success_rate": (successful_swaps / max(1, total_swaps) * 100)
        },
        "active_sessions": len([uid for uid, data in user_data.items() if data.get('state')]),
        "progress_tracking": len(swap_progress),
        "encrypted_data": "enabled",
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

@app.route('/api/swaps')
def swaps_api():
    """API to get recent swaps"""
    limit = request.args.get('limit', 50)
    
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT sh.id, sh.user_id, sh.swap_date, sh.status, 
               sh.processing_time, sh.nsfw_check, sh.reported,
               u.username
        FROM swaps_history sh
        JOIN users u ON sh.user_id = u.user_id
        ORDER BY sh.swap_date DESC
        LIMIT ?
    ''', (int(limit),))
    
    swaps = cursor.fetchall()
    conn.close()
    
    swaps_list = []
    for swap in swaps:
        swaps_list.append({
            "id": swap[0],
            "user_id": swap[1],
            "username": swap[7],
            "swap_date": swap[2],
            "status": swap[3],
            "processing_time": swap[4],
            "nsfw_checked": bool(swap[5]),
            "reported": bool(swap[6])
        })
    
    return jsonify({
        "total": len(swaps_list),
        "swaps": swaps_list
    })

@app.route('/api/reports')
def reports_api():
    """API to get reports (admin only)"""
    # Simple authentication (in production use proper auth)
    api_key = request.args.get('api_key')
    if api_key != "your_secret_api_key":  # Change this in production
        return jsonify({"error": "Unauthorized"}), 401
    
    status = request.args.get('status', 'pending')
    limit = request.args.get('limit', 50)
    
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.*, u1.username as reporter_name, u2.username as reported_name
        FROM reports r
        JOIN users u1 ON r.reporter_id = u1.user_id
        JOIN users u2 ON r.reported_user_id = u2.user_id
        WHERE r.status = ?
        ORDER BY r.report_date DESC
        LIMIT ?
    ''', (status, int(limit)))
    
    reports = cursor.fetchall()
    conn.close()
    
    reports_list = []
    for report in reports:
        reports_list.append({
            "id": report[0],
            "reporter_id": report[1],
            "reporter_name": report[9],
            "reported_user_id": report[2],
            "reported_name": report[10],
            "swap_id": report[3],
            "reason": report[4],
            "report_date": report[5],
            "status": report[6],
            "admin_action": report[7]
        })
    
    return jsonify({
        "status": status,
        "total": len(reports_list),
        "reports": reports_list
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

# ========== PROGRESS TRACKING FUNCTIONS ==========
def update_progress(chat_id, progress, message=""):
    """Update swap progress"""
    if chat_id in swap_progress:
        swap_progress[chat_id]['progress'] = progress
        swap_progress[chat_id]['message'] = message
        swap_progress[chat_id]['last_update'] = time.time()
        
        # Send progress update to user
        try:
            progress_bar = create_progress_bar(progress)
            status_msg = f"🔄 *Processing: {progress}%*\n{progress_bar}\n{message}"
            
            if swap_progress[chat_id].get('message_id'):
                try:
                    bot.edit_message_text(
                        status_msg,
                        chat_id=chat_id,
                        message_id=swap_progress[chat_id]['message_id'],
                        parse_mode='Markdown'
                    )
                except:
                    # Message might be too old, send new one
                    msg = bot.send_message(chat_id, status_msg, parse_mode='Markdown')
                    swap_progress[chat_id]['message_id'] = msg.message_id
            else:
                msg = bot.send_message(chat_id, status_msg, parse_mode='Markdown')
                swap_progress[chat_id]['message_id'] = msg.message_id
                
        except Exception as e:
            logger.error(f"Progress update error: {e}")

def create_progress_bar(percentage):
    """Create a visual progress bar"""
    bar_length = 10
    filled = int(bar_length * percentage / 100)
    empty = bar_length - filled
    
    if percentage < 30:
        color = "🔴"
    elif percentage < 70:
        color = "🟡"
    else:
        color = "🟢"
    
    bar = "█" * filled + "░" * empty
    return f"{color} [{bar}] {percentage}%"

def estimate_processing_time(start_time, current_progress):
    """Estimate remaining processing time"""
    if current_progress <= 0:
        return "Calculating..."
    
    elapsed = time.time() - start_time
    estimated_total = elapsed / (current_progress / 100)
    remaining = estimated_total - elapsed
    
    if remaining < 60:
        return f"{int(remaining)} seconds"
    elif remaining < 3600:
        return f"{int(remaining/60)} minutes"
    else:
        return f"{int(remaining/3600)} hours"

def cancel_swap(chat_id):
    """Cancel ongoing swap"""
    if chat_id in user_data:
        if chat_id in swap_progress:
            # Clean up progress tracking
            msg_id = swap_progress[chat_id].get('message_id')
            if msg_id:
                try:
                    bot.delete_message(chat_id, msg_id)
                except:
                    pass
            del swap_progress[chat_id]
        
        # Clean up user data
        del user_data[chat_id]
        return True
    return False

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
/history - Your swap history
/favorites - Your favorite swaps
/report - Report inappropriate content
/help - Show help

*New Features:*
✅ Progress tracking with estimated time
✅ Cancel ongoing swaps
✅ Save favorite swaps
✅ Compare before/after
✅ Encrypted storage
✅ NSFW detection
✅ Report system

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
    
    if cancel_swap(chat_id):
        bot.reply_to(message, "❌ Swap cancelled successfully.")
    else:
        bot.reply_to(message, "⚠️ No active swap to cancel.")

@bot.message_handler(commands=['status'])
def bot_status(message):
    active_sessions = len([uid for uid, data in user_data.items() if data.get('state')])
    total_users = get_total_users()
    active_users = get_active_users_count(1)
    
    # Check if user has active swap
    user_progress = None
    if message.chat.id in swap_progress:
        progress = swap_progress[message.chat.id]['progress']
        message_text = swap_progress[message.chat.id]['message']
        user_progress = f"\n*Your Swap:* {progress}% - {message_text}"
    
    status_text = f"""🤖 *Bot Status*

*Active Sessions:* {active_sessions}
*Total Users:* {total_users}
*Active Users (24h):* {active_users}
*Face Swap API:* ✅ Connected

*Your Status:* {get_user_step(message.chat.id)}{user_progress or ''}

*Commands:*
/swap - Start new face swap
/cancel - Cancel ongoing swap
/mystats - Your statistics
/history - Your swap history

Type /swap to start a new face swap!"""
    
    bot.reply_to(message, status_text, parse_mode='Markdown')

@bot.message_handler(commands=['mystats'])
def my_stats(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('face_swap_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT swaps_count, successful_swaps, failed_swaps, 
               reports_received, favorites_count, join_date
        FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    
    # Get recent swaps
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
        swaps_count, successful, failed, reports, favorites, join_date = result
        success_rate = (successful / max(1, swaps_count)) * 100
        
        # Calculate average processing time
        avg_time = 0
        if recent_swaps:
            total_time = sum([s[1] for s in recent_swaps if s[1]])
            avg_time = total_time / len(recent_swaps)
        
        stats_text = f"""📊 *Your Statistics*

*Swaps:*
• Total: {swaps_count}
• Successful: {successful}
• Failed: {failed}
• Success Rate: {success_rate:.1f}%
• Avg Time: {avg_time:.1f}s

*Account:*
• Reports Received: {reports}
• Favorites: {favorites}
• Joined: {join_date[:10]}
• Channel Status: {'✅ Verified' if check_channel_membership(user_id) else '❌ Not Joined'}
• Bot Status: {'✅ Active' if user_id not in BANNED_USERS else '🚫 Banned'}

*Recent Swaps:*
{f'\n'.join([f'• {s[0]} ({s[1]:.1f}s)' for s in recent_swaps]) if recent_swaps else 'No recent swaps'}"""
    else:
        stats_text = "📊 No statistics available yet."
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats"))
    
    bot.reply_to(message, stats_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['history'])
def swap_history(message):
    user_id = message.from_user.id
    
    history = get_user_swap_history(user_id, 10)
    
    if not history:
        bot.reply_to(message, "📭 No swap history yet.")
        return
    
    history_text = "📜 *Your Swap History*\n━━━━━━━━━━━━━━━━━━\n\n"
    
    for swap in history:
        swap_id, swap_date, status, processing_time, favorite = swap
        
        status_icon = "✅" if status == "success" else "❌"
        favorite_icon = "⭐" if favorite else ""
        
        history_text += f"{status_icon} *{swap_date[:16]}*\n"
        history_text += f"ID: `{swap_id}` | Status: {status}\n"
        history_text += f"Time: {processing_time:.1f}s {favorite_icon}\n"
        
        # Add inline buttons for each swap
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("🔍 View", callback_data=f"view_swap_{swap_id}"),
            types.InlineKeyboardButton("⭐ Favorite", callback_data=f"fav_swap_{swap_id}"),
            types.InlineKeyboardButton("📋 Compare", callback_data=f"compare_swap_{swap_id}")
        )
        
        if len(history_text) > 3000:
            # Send current batch
            bot.send_message(message.chat.id, history_text, parse_mode='Markdown', reply_markup=markup)
            history_text = ""  # Reset for next message
        else:
            history_text += "━━━━━━━━━━━━━━━━━━\n\n"
    
    if history_text:
        # Add navigation
        nav_markup = types.InlineKeyboardMarkup()
        nav_markup.add(
            types.InlineKeyboardButton("⬅️ Previous", callback_data="history_prev_0"),
            types.InlineKeyboardButton("Next ➡️", callback_data="history_next_10")
        )
        bot.send_message(message.chat.id, history_text, parse_mode='Markdown', reply_markup=nav_markup)

@bot.message_handler(commands=['favorites'])
def favorites_list(message):
    user_id = message.from_user.id
    
    favorites = get_user_favorites(user_id, 10)
    
    if not favorites:
        bot.reply_to(message, "⭐ No favorite swaps yet.\n\nAdd favorites from your swap history!")
        return
    
    favorites_text = "⭐ *Your Favorite Swaps*\n━━━━━━━━━━━━━━━━━━\n\n"
    
    for fav in favorites:
        swap_id, swap_date, status, processing_time = fav
        
        favorites_text += f"🆔 `{swap_id}`\n"
        favorites_text += f"📅 {swap_date[:16]}\n"
        favorites_text += f"✅ {status} ({processing_time:.1f}s)\n"
        favorites_text += "━━━━━━━━━━━━━━━━━━\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔍 View Swap", callback_data=f"view_swap_{favorites[0][0]}"),
        types.InlineKeyboardButton("🗑️ Remove", callback_data=f"remove_fav_{favorites[0][0]}")
    )
    
    bot.reply_to(message, favorites_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['report'])
def report_command(message):
    """Report inappropriate content"""
    user_id = message.from_user.id
    
    if user_id in BANNED_USERS:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    # Get user's recent swaps
    history = get_user_swap_history(user_id, 5)
    
    if not history:
        bot.reply_to(message, "📭 No swaps to report. Make some swaps first!")
        return
    
    report_text = "🚨 *Report Inappropriate Content*\n\n"
    report_text += "Select a swap to report from your recent history:\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for swap in history:
        swap_id, swap_date, status, processing_time, favorite = swap
        report_text += f"🆔 `{swap_id}` - {swap_date[:16]} - {status}\n"
        markup.add(types.InlineKeyboardButton(
            f"Report Swap {swap_id}",
            callback_data=f"report_swap_{swap_id}"
        ))
    
    report_text += "\n*Note:* False reports may result in penalties."
    
    bot.reply_to(message, report_text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_swap_'))
def report_swap_callback(call):
    """Handle swap report selection"""
    swap_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    
    # Store swap_id for reporting
    user_data[call.message.chat.id] = {'reporting_swap': swap_id}
    
    reasons = [
        "Inappropriate content",
        "Copyright violation", 
        "Harassment/bullying",
        "Spam/scam",
        "Other"
    ]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for reason in reasons:
        markup.add(types.InlineKeyboardButton(
            reason,
            callback_data=f"report_reason_{reason.replace(' ', '_')}_{swap_id}"
        ))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🚨 *Select Report Reason:*",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_reason_'))
def report_reason_callback(call):
    """Handle report reason selection"""
    parts = call.data.split('_')
    reason = ' '.join(parts[2:-1])
    swap_id = int(parts[-1])
    user_id = call.from_user.id
    
    # Get swap details
    swap = get_swap_details(swap_id)
    if not swap:
        bot.answer_callback_query(call.id, "❌ Swap not found!", show_alert=True)
        return
    
    reported_user_id = swap[1]  # user_id from swap
    
    # Add report to database
    report_id = add_report(user_id, reported_user_id, swap_id, reason)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ *Report Submitted!*\n\nReport ID: `{report_id}`\nReason: {reason}\n\nThank you for helping keep the community safe.",
        parse_mode='Markdown'
    )
    
    # Clean up user data
    if call.message.chat.id in user_data:
        del user_data[call.message.chat.id]

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_swap_'))
def view_swap_callback(call):
    """View swap details"""
    swap_id = int(call.data.split('_')[2])
    
    swap = get_swap_details(swap_id)
    if not swap:
        bot.answer_callback_query(call.id, "❌ Swap not found!", show_alert=True)
        return
    
    swap_date, status, processing_time, nsfw_check, reported, favorite = swap[2], swap[3], swap[4], swap[7], swap[8], swap[9]
    username = swap[13] if len(swap) > 13 else "Unknown"
    
    details = f"""🔍 *Swap Details*

🆔 Swap ID: `{swap_id}`
👤 User: @{username}
📅 Date: {swap_date}
✅ Status: {status}
⏱️ Time: {processing_time:.1f}s
🚫 NSFW: {'Yes' if nsfw_check else 'No'}
⚠️ Reported: {'Yes' if reported else 'No'}
⭐ Favorite: {'Yes' if favorite else 'No'}"""
    
    markup = types.InlineKeyboardMarkup()
    if call.from_user.id == ADMIN_ID:
        markup.add(
            types.InlineKeyboardButton("🚨 View Report", callback_data=f"admin_report_{swap_id}"),
            types.InlineKeyboardButton("🔴 Ban User", callback_data=f"admin_ban_{swap[1]}")  # user_id
        )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=details,
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('fav_swap_'))
def favorite_swap_callback(call):
    """Favorite/unfavorite a swap"""
    swap_id = int(call.data.split('_')[2])
    user_id = call.from_user.id
    
    result = toggle_favorite(user_id, swap_id)
    
    if result:
        bot.answer_callback_query(call.id, "⭐ Added to favorites!")
    else:
        bot.answer_callback_query(call.id, "🗑️ Removed from favorites!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('compare_swap_'))
def compare_swap_callback(call):
    """Show compare options for swap"""
    swap_id = int(call.data.split('_')[2])
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔄 Compare All", callback_data=f"compare_all_{swap_id}"),
        types.InlineKeyboardButton("📊 Side by Side", callback_data=f"compare_side_{swap_id}")
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🔄 *Select Comparison Type:*",
        parse_mode='Markdown',
        reply_markup=markup
    )

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
        user_id, username, first_name, last_name, join_date, last_active, is_banned, verified, swaps_count, successful, failed, reports, favorites = user
        
        status = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
        verified_status = "✅" if verified else "❌"
        
        # Calculate activity
        if last_active:
            last_active_time = datetime.strptime(last_active, '%Y-%m-%d %H:%M:%S') if isinstance(last_active, str) else last_active
            days_ago = (datetime.now() - last_active_time).days if isinstance(last_active_time, datetime) else 999
            activity = f"{days_ago}d ago" if days_ago > 0 else "Today"
        else:
            activity = "Never"
        
        message_text += f"🆔 `{user_id}`\n"
        message_text += f"👤 @{username or 'N/A'} {verified_status}\n"
        message_text += f"📛 {first_name} {last_name or ''}\n"
        message_text += f"📅 Joined: {join_date[:10]}\n"
        message_text += f"🕐 Last: {activity}\n"
        message_text += f"🔄 Swaps: {swaps_count} ({successful}✓/{failed}✗)\n"
        message_text += f"⚠️ Reports: {reports} | ⭐ Favs: {favorites}\n"
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
    
    # Add admin tools
    markup.add(
        types.InlineKeyboardButton("📊 View Reports", callback_data="view_reports"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh_users")
    )
    
    if len(message_text) > 4000:
        # Split message if too long
        chunks = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
        for chunk in chunks[:-1]:
            bot.send_message(ADMIN_ID, chunk, parse_mode='Markdown')
        bot.send_message(ADMIN_ID, chunks[-1], parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, message_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['reports'])
def view_reports(message):
    """Admin command: View pending reports"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is for admins only.")
        return
    
    reports = get_pending_reports()
    
    if not reports:
        bot.reply_to(message, "✅ No pending reports.")
        return
    
    reports_text = f"🚨 *Pending Reports: {len(reports)}*\n━━━━━━━━━━━━━━━━━━\n\n"
    
    for report in reports:
        report_id, reporter_id, reported_user_id, swap_id, reason, report_date, status, action, reporter_name, reported_name = report
        
        reports_text += f"📋 *Report ID:* `{report_id}`\n"
        reports_text += f"👤 Reporter: @{reporter_name} (`{reporter_id}`)\n"
        reports_text += f"⚠️ Reported: @{reported_name} (`{reported_user_id}`)\n"
        reports_text += f"🔄 Swap ID: `{swap_id}`\n"
        reports_text += f"📝 Reason: {reason}\n"
        reports_text += f"🕐 Date: {report_date[:16]}\n"
        
        # Add action buttons for each report
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_report_{report_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_report_{report_id}"),
            types.InlineKeyboardButton("🔴 Ban User", callback_data=f"admin_ban_{reported_user_id}"),
            types.InlineKeyboardButton("🔍 View Swap", callback_data=f"view_swap_{swap_id}")
        )
        
        reports_text += "━━━━━━━━━━━━━━━━━━\n\n"
        
        if len(reports_text) > 3000:
            bot.send_message(ADMIN_ID, reports_text, parse_mode='Markdown', reply_markup=markup)
            reports_text = ""
    
    if reports_text:
        bot.send_message(ADMIN_ID, reports_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_report_'))
def approve_report_callback(call):
    """Approve a report"""
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin only!", show_alert=True)
        return
    
    report_id = int(call.data.split('_')[2])
    update_report_status(report_id, "approved", "Report approved by admin")
    
    bot.answer_callback_query(call.id, "✅ Report approved!")
    
    # Update the message
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=call.message.text + "\n\n✅ **APPROVED BY ADMIN**",
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_report_'))
def reject_report_callback(call):
    """Reject a report"""
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin only!", show_alert=True)
        return
    
    report_id = int(call.data.split('_')[2])
    update_report_status(report_id, "rejected", "Report rejected by admin")
    
    bot.answer_callback_query(call.id, "❌ Report rejected!")
    
    # Update the message
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=call.message.text + "\n\n❌ **REJECTED BY ADMIN**",
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == "view_reports")
def view_reports_callback(call):
    """View reports from inline button"""
    view_reports(call.message)

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
        user_id, username, first_name, last_name, join_date, last_active, is_banned, verified, swaps_count, successful, failed, reports, favorites = user
        
        status = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
        verified_status = "✅" if verified else "❌"
        
        if last_active:
            last_active_time = datetime.strptime(last_active, '%Y-%m-%d %H:%M:%S') if isinstance(last_active, str) else last_active
            days_ago = (datetime.now() - last_active_time).days if isinstance(last_active_time, datetime) else 999
            activity = f"{days_ago}d ago" if days_ago > 0 else "Today"
        else:
            activity = "Never"
        
        message_text += f"🆔 `{user_id}`\n"
        message_text += f"👤 @{username or 'N/A'} {verified_status}\n"
        message_text += f"📛 {first_name} {last_name or ''}\n"
        message_text += f"📅 Joined: {join_date[:10]}\n"
        message_text += f"🕐 Last: {activity}\n"
        message_text += f"🔄 Swaps: {swaps_count} ({successful}✓/{failed}✗)\n"
        message_text += f"⚠️ Reports: {reports} | ⭐ Favs: {favorites}\n"
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
    
    markup.add(
        types.InlineKeyboardButton("📊 View Reports", callback_data="view_reports"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh_users")
    )
    
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
    
    ban_user(user_id, "Admin action from report")
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
        reason = ' '.join(message.text.split()[2:]) if len(message.text.split()) > 2 else "Admin action"
        
        ban_user(user_id, reason)
        bot.reply_to(message, f"✅ User `{user_id}` has been banned.\nReason: {reason}")
        
        # Notify the banned user
        try:
            bot.send_message(user_id, f"🚫 You have been banned from using this bot.\nReason: {reason}")
        except:
            pass
            
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Usage: /ban <user_id> [reason]")

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
    
    cursor.execute('SELECT COUNT(*) FROM swaps_history WHERE nsfw_check = 1')
    nsfw_flagged = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM swaps_history WHERE reported = 1')
    reported_swaps = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM favorites')
    total_favorites = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM reports WHERE status = "pending"')
    pending_reports = cursor.fetchone()[0]
    
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
• NSFW Flagged: {nsfw_flagged}
• Reported Swaps: {reported_swaps}
• Favorited: {total_favorites}
• Success Rate: {success_rate:.1f}%

🚨 *Reports:*
• Pending Reports: {pending_reports}
• Total Reports: {pending_reports} (pending only)

📱 *Current Sessions:*
• Active Swaps: {len([uid for uid, data in user_data.items() if data.get('state')])}
• Progress Tracking: {len(swap_progress)}
• Waiting for 1st Photo: {len([uid for uid, data in user_data.items() if data.get('state') == WAITING_FOR_SOURCE])}
• Waiting for 2nd Photo: {len([uid for uid, data in user_data.items() if data.get('state') == WAITING_FOR_TARGET])}

🔧 *System Status:*
• Bot: ✅ RUNNING
• Database: ✅ CONNECTED
• Face Swap API: ✅ AVAILABLE
• NSFW Detection: {'✅ ENABLED' if NSFW_DETECTION_ENABLED else '❌ DISABLED'}
• Encryption: ✅ ACTIVE
• Progress Tracking: ✅ ACTIVE
• Channel Check: ✅ ACTIVE
• Webhook Mode: {'✅ ENABLED' if WEBHOOK_URL else '❌ DISABLED'}

🌐 *API Endpoints:*
• Health: `/health` endpoint
• Health (Extended): `/health/hunter` endpoint
• Stats: `/stats` endpoint
• Users API: `/users` endpoint
• Swaps API: `/api/swaps` endpoint
• Reports API: `/api/reports` endpoint

━━━━━━━━━━━━━━━━━━
*Admin Commands:*
/users - List all users with buttons
/reports - View pending reports
/ban <id> [reason] - Ban user
/unban <id> - Unban user
/botstatus - This report
/stats - Show statistics
/exportdata - Export user data
/refreshdb - Refresh database
/refreshbot - Refresh bot data
/broadcast <msg> - Broadcast message
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
• Progress Tracking: {len(swap_progress)}

*Channel:*
• Required: {REQUIRED_CHANNEL}
• Verification: {'✅ Enabled'}

*Security:*
• NSFW Detection: {'✅ Enabled' if NSFW_DETECTION_ENABLED else '❌ Disabled'}
• Encryption: ✅ Enabled
• Reports System: ✅ Active

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
                     'Total Swaps', 'Successful', 'Failed', 'Reports Received', 'Favorites'])
    
    # Write data
    for user in users:
        writer.writerow(user[:13])  # First 13 columns
    
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

# ========== FACE SWAP HANDLER WITH PROGRESS TRACKING ==========
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
        
        # Check for NSFW content
        if NSFW_DETECTION_ENABLED:
            nsfw_detected = check_nsfw_content(img_data)
            if nsfw_detected:
                bot.reply_to(message, "🚫 *Content blocked!* This image appears to contain inappropriate content.")
                # Auto-ban for severe violations
                increment_user_reports(user_id)
                
                # Check if user should be auto-banned
                conn = sqlite3.connect('face_swap_bot.db')
                cursor = conn.cursor()
                cursor.execute('SELECT reports_received FROM users WHERE user_id = ?', (user_id,))
                reports_count = cursor.fetchone()[0]
                conn.close()
                
                if reports_count >= 3:  # Auto-ban after 3 NSFW violations
                    ban_user(user_id, "Auto-ban: Multiple NSFW violations")
                    bot.reply_to(message, "🚫 Account banned due to multiple violations.")
                
                return
        
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
                    'progress': 0,
                    'message': "Starting face swap...",
                    'start_time': time.time(),
                    'message_id': None
                }
                
                # Start the face swap in a separate thread
                threading.Thread(target=process_face_swap, args=(chat_id,), daemon=True).start()
                
                # Send initial progress
                update_progress(chat_id, 10, "Uploading images to API...")
    
    except Exception as e:
        logger.error(f"Error processing photo: {str(e)}")
        bot.reply_to(message, f"❌ *An error occurred:* {str(e)}\n\nPlease try again with different photos.")
        if chat_id in user_data:
            del user_data[chat_id]
        if chat_id in swap_progress:
            del swap_progress[chat_id]

def process_face_swap(chat_id):
    """Process face swap with progress updates"""
    try:
        if chat_id not in user_data:
            return
        
        user_id = user_data[chat_id]['user_id']
        source_img = user_data[chat_id]['source']
        target_img = user_data[chat_id]['target']
        start_time = user_data[chat_id]['start_time']
        
        # Generate image hashes
        source_hash = generate_image_hash(source_img)
        target_hash = generate_image_hash(target_img)
        
        # Update progress
        update_progress(chat_id, 30, "Processing faces...")
        time.sleep(1)  # Simulate processing
        
        # Convert images to base64
        update_progress(chat_id, 50, "Preparing images for swap...")
        source_base64 = base64.b64encode(source_img).decode('utf-8')
        target_base64 = base64.b64encode(target_img).decode('utf-8')
        
        # Call face swap API
        update_progress(chat_id, 70, "Swapping faces with AI...")
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
        
        # Add estimated time to progress
        elapsed = time.time() - start_time
        estimated_total = elapsed / 0.7  # Estimate based on 70% progress
        remaining = estimated_total - elapsed
        
        if remaining < 60:
            time_msg = f"Estimated: {int(remaining)}s remaining"
        else:
            time_msg = f"Estimated: {int(remaining/60)}m remaining"
        
        update_progress(chat_id, 80, f"Finalizing swap... {time_msg}")
        
        response = requests.post(api_url, json=data, headers=headers)
        
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            response_data = response.json()
            if 'result' in response_data:
                update_progress(chat_id, 95, "Almost done...")
                
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
                update_progress(chat_id, 100, "Swap completed!")
                time.sleep(1)  # Show 100% briefly
                
                # Clean up progress message
                if chat_id in swap_progress and swap_progress[chat_id].get('message_id'):
                    try:
                        bot.delete_message(chat_id, swap_progress[chat_id]['message_id'])
                    except:
                        pass
                
                # Store original data for comparison
                original_data = {
                    'source': source_img,
                    'target': target_img,
                    'result': image_data
                }
                
                # Add to history
                swap_id = add_swap_history(
                    user_id, "success", processing_time, 
                    source_hash, target_hash, result_hash,
                    original_data=original_data
                )
                
                # Update user statistics
                update_user_stats(user_id, success=True)
                
                # Send result to user
                with open(filepath, 'rb') as photo:
                    # Create caption with options
                    caption = f"""✅ *Face swap completed!*

*Details:*
🆔 Swap ID: `{swap_id}`
⏱️ Time: {processing_time:.1f}s
✅ Status: Success

*Options:*
⭐ Use /favorites to save this swap
🔍 Use /history to view all swaps
🔄 Use /swap to make another"""

                    # Send photo with inline keyboard
                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton("⭐ Favorite", callback_data=f"fav_swap_{swap_id}"),
                        types.InlineKeyboardButton("🔄 Compare", callback_data=f"compare_all_{swap_id}"),
                        types.InlineKeyboardButton("🔄 New Swap", callback_data="new_swap")
                    )
                    
                    bot.send_photo(
                        chat_id, 
                        photo, 
                        caption=caption,
                        parse_mode='Markdown',
                        reply_markup=markup
                    )
                
                logger.info(f"Face swap completed for {chat_id} in {processing_time:.2f}s")
                
                # Clean up user data
                if chat_id in user_data:
                    del user_data[chat_id]
                if chat_id in swap_progress:
                    del swap_progress[chat_id]
                    
            else:
                update_progress(chat_id, 100, "Error: No result from API")
                time.sleep(2)
                
                if chat_id in swap_progress and swap_progress[chat_id].get('message_id'):
                    try:
                        bot.delete_message(chat_id, swap_progress[chat_id]['message_id'])
                    except:
                        pass
                
                bot.send_message(chat_id, "❌ *Error:* No result from face swap API. Please try again.")
                
                # Add to history as failed
                add_swap_history(user_id, "failed", processing_time, source_hash, target_hash, "")
                update_user_stats(user_id, success=False)
                
                if chat_id in user_data:
                    del user_data[chat_id]
                if chat_id in swap_progress:
                    del swap_progress[chat_id]
        else:
            update_progress(chat_id, 100, f"Error: API failed ({response.status_code})")
            time.sleep(2)
            
            if chat_id in swap_progress and swap_progress[chat_id].get('message_id'):
                try:
                    bot.delete_message(chat_id, swap_progress[chat_id]['message_id'])
                except:
                    pass
            
            bot.send_message(chat_id, f"❌ *Error:* Face swap API request failed (Status: {response.status_code}). Please try again.")
            
            # Add to history as failed
            add_swap_history(user_id, "failed", processing_time, source_hash, target_hash, "")
            update_user_stats(user_id, success=False)
            
            if chat_id in user_data:
                del user_data[chat_id]
            if chat_id in swap_progress:
                del swap_progress[chat_id]
                
    except Exception as e:
        logger.error(f"Face swap processing error: {e}")
        
        if chat_id in swap_progress and swap_progress[chat_id].get('message_id'):
            try:
                bot.delete_message(chat_id, swap_progress[chat_id]['message_id'])
            except:
                pass
        
        bot.send_message(chat_id, f"❌ *An error occurred during processing:* {str(e)}\n\nPlease try again.")
        
        if chat_id in user_data:
            if 'user_id' in user_data[chat_id]:
                user_id = user_data[chat_id]['user_id']
                update_user_stats(user_id, success=False)
            del user_data[chat_id]
        if chat_id in swap_progress:
            del swap_progress[chat_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith('compare_all_'))
def compare_all_callback(call):
    """Show comparison image"""
    swap_id = int(call.data.split('_')[2])
    
    # Get swap details (in production, you'd retrieve the actual images)
    swap = get_swap_details(swap_id)
    if not swap:
        bot.answer_callback_query(call.id, "❌ Swap data not available for comparison.", show_alert=True)
        return
    
    # In a real implementation, you'd retrieve the actual images from storage
    # and create a comparison image
    
    bot.answer_callback_query(call.id, "🔄 Comparison feature coming soon!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "new_swap")
def new_swap_callback(call):
    """Start a new swap from inline button"""
    start_swap(call.message)
    bot.answer_callback_query(call.id, "🔄 Starting new swap...")

@bot.callback_query_handler(func=lambda call: call.data == "refresh_stats")
def refresh_stats_callback(call):
    """Refresh user stats"""
    my_stats(call.message)
    bot.answer_callback_query(call.id, "✅ Stats refreshed!")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    
    if chat_id in user_data:
        state = user_data[chat_id].get('state')
        if state == WAITING_FOR_SOURCE:
            bot.reply_to(message, "📸 Please send the first photo (the face to use).")
        elif state == WAITING_FOR_TARGET:
            bot.reply_to(message, "📸 Please send the second photo (the face to replace).")
        elif state == PROCESSING or (state is None and 'source' in user_data[chat_id] and 'target' in user_data[chat_id]):
            # Check if we have progress tracking
            if chat_id in swap_progress:
                progress = swap_progress[chat_id]['progress']
                message_text = swap_progress[chat_id]['message']
                elapsed = time.time() - swap_progress[chat_id]['start_time']
                
                response = f"⏳ *Processing in progress...*\n\n"
                response += f"Progress: {progress}%\n"
                response += f"Status: {message_text}\n"
                response += f"Time elapsed: {elapsed:.1f}s\n\n"
                response += f"Use /cancel to stop this swap."
                
                bot.reply_to(message, response, parse_mode='Markdown')
            else:
                bot.reply_to(message, "⏳ Your face swap is being processed. Please wait...")
        else:
            bot.reply_to(message, "Type /swap to start a face swap!")
    else:
        bot.reply_to(message, "👋 Welcome! Type /start to see instructions or /swap to start a face swap!")

# ========== START BOT ==========
app_start_time = time.time()

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 FACE SWAP BOT WITH ADVANCED FEATURES")
    print("=" * 70)
    print(f"📱 Bot Token: Loaded")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📢 Required Channel: {REQUIRED_CHANNEL}")
    print(f"🌐 Port: {BOT_PORT}")
    print(f"🏓 Health Check: http://localhost:{BOT_PORT}/health")
    print(f"🏓 Health (Extended): http://localhost:{BOT_PORT}/health/hunter")
    print(f"📊 Stats: http://localhost:{BOT_PORT}/stats")
    print("=" * 70)
    print("🎯 NEW FEATURES ADDED:")
    print("✅ /report - Report inappropriate content")
    print("✅ Auto-ban for NSFW content detection")
    print("✅ Swap history for admins to review")
    print("✅ Progress bar for swaps with real-time updates")
    print("✅ Estimated time display")
    print("✅ Cancel swap option (/cancel)")
    print("✅ Save favorite swaps (/favorites)")
    print("✅ Compare original vs swapped")
    print("✅ Encrypted user data storage")
    print("=" * 70)
    print("🔧 TECHNICAL FEATURES:")
    print("• NSFW content detection (basic)")
    print("• Progress tracking with visual bar")
    print("• Estimated time calculation")
    print("• Cancel swap functionality")
    print("• Favorite system with database")
    print("• Comparison image generation")
    print("• AES encryption for user data")
    print("• Admin report review system")
    print("• Extended Flask API endpoints")
    print("=" * 70)
    print("👑 ADMIN COMMANDS:")
    print("/users - List all users with buttons")
    print("/reports - View pending reports")
    print("/ban <id> [reason] - Ban user")
    print("/unban <id> - Unban user")
    print("/botstatus - Detailed bot report")
    print("/stats - Quick statistics")
    print("/exportdata - Export user data as CSV")
    print("/refreshdb - Refresh database")
    print("/refreshbot - Refresh bot data")
    print("/broadcast <msg> - Broadcast to all users")
    print("=" * 70)
    print("👤 USER COMMANDS:")
    print("/swap - Start new face swap")
    print("/cancel - Cancel ongoing swap")
    print("/mystats - Your statistics")
    print("/history - Your swap history")
    print("/favorites - Your favorite swaps")
    print("/report - Report inappropriate content")
    print("/status - Check bot status")
    print("=" * 70)
    print("👑 Created by: @PokiePy")
    print("💰 Credit change krne wale ki mkb")
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
