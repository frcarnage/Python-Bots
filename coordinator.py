# coordinator.py - Runs both bots without conflicts
import subprocess
import time
import os
import sys
import signal
from threading import Thread
from flask import Flask, jsonify
import threading
import requests

# Create Flask app for coordinator health checks
coordinator_app = Flask(__name__)

# Track running bots
running_bots = {
    "main_bot": False,
    "reset_bot": False
}

# Track bot health status
bot_health = {
    "main_bot": "unknown",
    "reset_bot": "unknown"
}

@coordinator_app.route('/health/runner')
def health():
    """Health check for the coordinator"""
    # Check bot health
    check_bot_health()
    
    return jsonify({
        "status": "healthy",
        "coordinator": True,
        "running_bots": running_bots,
        "bot_health": bot_health,
        "total_bots": sum(running_bots.values()),
        "timestamp": time.time()
    }), 200

@coordinator_app.route('/')
def home():
    """Home page"""
    return jsonify({
        "service": "Bot Coordinator",
        "description": "Manages multiple Telegram bots",
        "bots": {
            "main_bot": {
                "port": 8000,
                "url": "http://localhost:8000",
                "type": "Username Swapper Bot"
            },
            "reset_bot": {
                "port": 5001,
                "health_url": "http://localhost:5001/health/reset",
                "type": "Instagram Reset Bot"
            }
        },
        "coordinator": {
            "port": 8080,
            "health_url": "http://localhost:8080/health/runner"
        }
    })

def check_bot_health():
    """Check if bots are responding"""
    try:
        # Check main bot
        response = requests.get("http://localhost:8000", timeout=3)
        if response.status_code == 200:
            bot_health["main_bot"] = "healthy"
            running_bots["main_bot"] = True
        else:
            bot_health["main_bot"] = f"unhealthy: HTTP {response.status_code}"
            running_bots["main_bot"] = False
    except:
        bot_health["main_bot"] = "unreachable"
        running_bots["main_bot"] = False
    
    try:
        # Check reset bot
        response = requests.get("http://localhost:5001/health/reset", timeout=3)
        if response.status_code == 200:
            bot_health["reset_bot"] = "healthy"
            running_bots["reset_bot"] = True
        else:
            bot_health["reset_bot"] = f"unhealthy: HTTP {response.status_code}"
            running_bots["reset_bot"] = False
    except:
        bot_health["reset_bot"] = "unreachable"
        running_bots["reset_bot"] = False

def run_flask():
    """Run Flask server for coordinator"""
    port = 8080  # Different port for coordinator
    print(f"🌐 Coordinator Flask starting on port {port}")
    coordinator_app.run(
        host='0.0.0.0', 
        port=port, 
        debug=False, 
        use_reloader=False,
        threaded=True
    )

def run_bot(script_name, name, port):
    """Run a bot script and update status"""
    print(f"🚀 Starting {name} ({script_name}) on port {port}...")
    running_bots[f"{name.lower()}_bot"] = True
    bot_health[f"{name.lower()}_bot"] = "starting"
    
    # Set environment variable for port
    env = os.environ.copy()
    env['PORT'] = str(port)
    
    process = subprocess.Popen(
        [sys.executable, script_name],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Stream output
    def stream_output():
        for line in process.stdout:
            line_text = line.strip()
            print(f"[{name}] {line_text}")
            
            # Check for specific messages
            if "Starting Flask server on port" in line_text:
                print(f"✅ {name} Flask started successfully")
                bot_health[f"{name.lower()}_bot"] = "starting_flask"
            
            if "Telegram bot started" in line_text or "Bot polling" in line_text:
                print(f"✅ {name} Telegram bot started successfully")
                bot_health[f"{name.lower()}_bot"] = "starting_telegram"
            
            # Check if process died
            if process.poll() is not None:
                print(f"❌ {name} stopped unexpectedly")
                running_bots[f"{name.lower()}_bot"] = False
                bot_health[f"{name.lower()}_bot"] = "stopped"
                break
    
    output_thread = Thread(target=stream_output, daemon=True)
    output_thread.start()
    
    return process

def signal_handler(signum, frame):
    print(f"\n🛑 Received signal {signum}. Stopping bots...")
    for key in running_bots:
        running_bots[key] = False
        bot_health[key] = "stopping"
    sys.exit(0)

def main():
    """Main coordinator function"""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("🤖 BOT COORDINATOR - Running both Telegram bots")
    print("=" * 60)
    
    # Start Flask server in background thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(2)  # Let Flask start
    
    # Check scripts exist
    if not os.path.exists("main.py"):
        print("⚠️ main.py not found! Running reset.py only")
    else:
        print("✅ Found main.py (Username Swapper Bot)")
    
    if not os.path.exists("reset.py"):
        print("❌ reset.py not found!")
        sys.exit(1)
    
    print("\n📡 Available URLs:")
    print("• Coordinator: http://localhost:8080/health/runner")
    print("• Main Bot:    http://localhost:8000")
    print("• Reset Bot:   http://localhost:5001/health/reset")
    print("=" * 60)
    
    processes = []
    
    try:
        # Start main.py if it exists
        if os.path.exists("main.py"):
            processes.append(run_bot("main.py", "MAIN", 8000))
            time.sleep(10)  # Wait longer for main bot (has database init)
        
        # Start reset.py
        processes.append(run_bot("reset.py", "RESET", 5001))
        time.sleep(5)
        
        # Initial health check
        check_bot_health()
        
        print("\n" + "=" * 60)
        print("✅ Bots started! Status:")
        print(f"   • Main Bot:  {'✅' if running_bots['main_bot'] else '❌'} - {bot_health['main_bot']}")
        print(f"   • Reset Bot: {'✅' if running_bots['reset_bot'] else '❌'} - {bot_health['reset_bot']}")
        print(f"   • Total: {sum(running_bots.values())}/2 bots running")
        print("=" * 60)
        print("\n📊 Monitoring logs... (Press Ctrl+C to stop)")
        print("=" * 60)
        
        # Keep checking bot status
        check_count = 0
        while True:
            time.sleep(30)
            check_count += 1
            
            # Health check every cycle
            check_bot_health()
            
            # Print status every 5 checks (2.5 minutes)
            if check_count % 5 == 0:
                print(f"\n🔄 Status check #{check_count}:")
                print(f"   • Main Bot:  {'✅' if running_bots['main_bot'] else '❌'} - {bot_health['main_bot']}")
                print(f"   • Reset Bot: {'✅' if running_bots['reset_bot'] else '❌'} - {bot_health['reset_bot']}")
                print(f"   • Total: {sum(running_bots.values())}/2 bots")
                
                # Try to restart failed bots
                if os.path.exists("main.py") and not running_bots["main_bot"]:
                    print("🔄 Attempting to restart Main Bot...")
                    processes[0] = run_bot("main.py", "MAIN", 8000)
                    time.sleep(5)
                
                if not running_bots["reset_bot"]:
                    print("🔄 Attempting to restart Reset Bot...")
                    # If processes[1] exists, replace it, otherwise append
                    if len(processes) > 1:
                        processes[1] = run_bot("reset.py", "RESET", 5001)
                    else:
                        processes.append(run_bot("reset.py", "RESET", 5001))
                    time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping bots...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Update status
        for key in running_bots:
            running_bots[key] = False
            bot_health[key] = "stopped"
        
        # Terminate processes
        print("🛑 Terminating bot processes...")
        for i, proc in enumerate(processes):
            if proc and proc.poll() is None:
                bot_name = "MAIN" if i == 0 else "RESET"
                print(f"   • Stopping {bot_name} bot...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except:
                    proc.kill()
        
        print("👋 Coordinator stopped gracefully")
        print("=" * 60)

if __name__ == '__main__':
    main()
