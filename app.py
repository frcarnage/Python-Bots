# app.py - Main entry point that runs both bots
import subprocess
import threading
import os
import time
import sys
from flask import Flask, jsonify

app = Flask(__name__)

# Global to track bot status
bots_status = {
    "main_bot": "stopped",
    "reset_bot": "stopped",
    "start_time": time.time()
}

def run_main_bot():
    """Run your main.py bot"""
    print("🚀 Starting Main Bot (main.py)...")
    bots_status["main_bot"] = "running"
    
    # Run main.py as a subprocess
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Stream logs
    for line in process.stdout:
        print(f"[MAIN BOT] {line.strip()}")
    
    bots_status["main_bot"] = "stopped"
    return process

def run_reset_bot():
    """Run your reset.py bot"""
    print("🚀 Starting Reset Bot (reset.py)...")
    bots_status["reset_bot"] = "running"
    
    # Run reset.py as a subprocess
    process = subprocess.Popen(
        [sys.executable, "reset.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Stream logs
    for line in process.stdout:
        print(f"[RESET BOT] {line.strip()}")
    
    bots_status["reset_bot"] = "stopped"
    return process

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "bots": {
            "main_bot": bots_status["main_bot"],
            "reset_bot": bots_status["reset_bot"]
        },
        "uptime_seconds": time.time() - bots_status["start_time"]
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    })

def start_bots():
    """Start both bots in background threads"""
    print("🤖 Starting both bots...")
    
    # Start main bot
    main_thread = threading.Thread(target=run_main_bot, daemon=True)
    main_thread.start()
    
    # Start reset bot  
    reset_thread = threading.Thread(target=run_reset_bot, daemon=True)
    reset_thread.start()
    
    # Keep threads alive
    main_thread.join()
    reset_thread.join()

if __name__ == '__main__':
    # Start bots in background thread
    bot_thread = threading.Thread(target=start_bots, daemon=True)
    bot_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
