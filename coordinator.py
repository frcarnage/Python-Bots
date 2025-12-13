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
import atexit

# Create Flask app for coordinator health checks
coordinator_app = Flask(__name__)

# Track running bots
running_bots = {
    "main_bot": False,
    "hunter_bot": False  # Changed from reset_bot to hunter_bot
}

# Track bot health status
bot_health = {
    "main_bot": "unknown",
    "hunter_bot": "unknown"  # Changed from reset_bot to hunter_bot
}

# Store processes for cleanup
processes = []

@coordinator_app.route('/health/runner')
def health():
    """Health check for the coordinator"""
    try:
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
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }), 500

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
                "health_url": "http://localhost:8000/health",
                "type": "Username Swapper Bot",
                "status": bot_health["main_bot"]
            },
            "hunter_bot": {
                "port": 6001,
                "health_url": "http://localhost:6001/health/hunter",
                "type": "Instagram 4L Hunter Bot",
                "status": bot_health["hunter_bot"]
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
        # Check main bot (username swapper)
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                bot_health["main_bot"] = "healthy"
                running_bots["main_bot"] = True
            else:
                bot_health["main_bot"] = f"unhealthy: {data.get('status', 'unknown')}"
                running_bots["main_bot"] = False
        else:
            bot_health["main_bot"] = f"unhealthy: HTTP {response.status_code}"
            running_bots["main_bot"] = False
    except requests.exceptions.Timeout:
        bot_health["main_bot"] = "timeout"
        running_bots["main_bot"] = False
    except requests.exceptions.ConnectionError:
        bot_health["main_bot"] = "connection_refused"
        running_bots["main_bot"] = False
    except Exception as e:
        bot_health["main_bot"] = f"error: {str(e)[:50]}"
        running_bots["main_bot"] = False
    
    try:
        # Check hunter bot (4L username hunter)
        response = requests.get("http://localhost:6001/health/hunter", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                bot_health["hunter_bot"] = "healthy"
                running_bots["hunter_bot"] = True
            else:
                bot_health["hunter_bot"] = f"unhealthy: {data.get('status', 'unknown')}"
                running_bots["hunter_bot"] = False
        else:
            bot_health["hunter_bot"] = f"unhealthy: HTTP {response.status_code}"
            running_bots["hunter_bot"] = False
    except requests.exceptions.Timeout:
        bot_health["hunter_bot"] = "timeout"
        running_bots["hunter_bot"] = False
    except requests.exceptions.ConnectionError:
        bot_health["hunter_bot"] = "connection_refused"
        running_bots["hunter_bot"] = False
    except Exception as e:
        bot_health["hunter_bot"] = f"error: {str(e)[:50]}"
        running_bots["hunter_bot"] = False

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
    bot_key = f"{name.lower()}_bot"
    running_bots[bot_key] = True
    bot_health[bot_key] = "starting"
    
    # Set environment variable for port
    env = os.environ.copy()
    env['PORT'] = str(port)
    
    # Add Python path
    if 'PYTHONPATH' not in env:
        env['PYTHONPATH'] = os.getcwd()
    else:
        env['PYTHONPATH'] = os.getcwd() + ':' + env['PYTHONPATH']
    
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
        line_count = 0
        for line in process.stdout:
            line_text = line.strip()
            if line_text:  # Only print non-empty lines
                print(f"[{name}] {line_text}")
                line_count += 1
                
                # Check for specific messages (first 20 lines)
                if line_count <= 20:
                    if "Starting Flask server on port" in line_text or "🌐 Starting Flask server" in line_text:
                        print(f"✅ {name} Flask started successfully")
                        bot_health[bot_key] = "flask_started"
                    
                    if "Telegram bot started" in line_text or "Bot polling" in line_text or "🤖 Telegram bot" in line_text:
                        print(f"✅ {name} Telegram bot started successfully")
                        bot_health[bot_key] = "telegram_started"
                    
                    if "error" in line_text.lower() or "Error" in line_text or "Exception" in line_text:
                        print(f"⚠️ {name} has error in logs")
                        bot_health[bot_key] = f"error_in_logs"
            
            # Check if process died
            if process.poll() is not None:
                exit_code = process.returncode
                status = "exited" if exit_code == 0 else f"crashed (code: {exit_code})"
                print(f"❌ {name} {status}")
                running_bots[bot_key] = False
                bot_health[bot_key] = f"stopped (code: {exit_code})"
                break
    
    output_thread = Thread(target=stream_output, daemon=True)
    output_thread.start()
    
    return process

def cleanup():
    """Cleanup function called on exit"""
    print("\n🧹 Cleaning up processes...")
    for i, proc in enumerate(processes):
        if proc and proc.poll() is None:
            bot_name = "MAIN" if i == 0 else "HUNTER"
            print(f"   • Terminating {bot_name} bot...")
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except:
                try:
                    proc.kill()
                except:
                    pass
    print("👋 Cleanup complete")

def signal_handler(signum, frame):
    print(f"\n🛑 Received signal {signum}. Stopping bots...")
    for key in running_bots:
        running_bots[key] = False
        bot_health[key] = "stopping"
    cleanup()
    sys.exit(0)

def main():
    """Main coordinator function"""
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 70)
    print("🤖 BOT COORDINATOR - Running both Telegram bots")
    print("=" * 70)
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"📄 Files: {', '.join([f for f in os.listdir('.') if f.endswith('.py')])}")
    print("=" * 70)
    
    # Start Flask server in background thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(3)  # Let Flask start
    
    # Check scripts exist
    if not os.path.exists("main.py"):
        print("⚠️ main.py not found! Running reset.py only")
    else:
        print("✅ Found main.py (Username Swapper Bot)")
    
    if not os.path.exists("reset.py"):
        print("❌ reset.py not found!")
        print("💡 Creating a simple test reset.py...")
        # Create a simple test file if reset.py doesn't exist
        with open("reset.py", "w") as f:
            f.write("""
from flask import Flask, jsonify
import time
app = Flask(__name__)

@app.route('/health/hunter')
def health():
    return jsonify({"status": "healthy", "test": True}), 200

@app.route('/')
def home():
    return jsonify({"service": "Test Hunter Bot"}), 200

if __name__ == '__main__':
    print("🚀 Test hunter bot starting on port 6001")
    app.run(host='0.0.0.0', port=6001, debug=False)
""")
        print("✅ Created test reset.py")
    
    print("\n📡 Available URLs:")
    print("• Coordinator Health: http://localhost:8080/health/runner")
    print("• Coordinator Home:   http://localhost:8080/")
    print("• Main Bot:          http://localhost:8000")
    print("• Main Bot Health:   http://localhost:8000/health")
    print("• Hunter Bot:        http://localhost:6001/hunter")
    print("• Hunter Bot Health: http://localhost:6001/health/hunter")
    print("=" * 70)
    
    try:
        # Start main.py if it exists
        if os.path.exists("main.py"):
            print("\n1️⃣ STARTING MAIN BOT (Username Swapper)...")
            processes.append(run_bot("main.py", "MAIN", 8000))
            time.sleep(15)  # Wait longer for main bot (has database init)
        
        # Start reset.py (4L Hunter Bot)
        print("\n2️⃣ STARTING HUNTER BOT (4L Username Hunter)...")
        processes.append(run_bot("reset.py", "HUNTER", 6001))  # Port changed to 6001
        time.sleep(10)
        
        # Initial health check
        print("\n3️⃣ PERFORMING INITIAL HEALTH CHECKS...")
        check_bot_health()
        
        print("\n" + "=" * 70)
        print("📊 INITIAL STATUS REPORT:")
        print("=" * 70)
        print(f"   • Main Bot:   {'✅' if running_bots['main_bot'] else '❌'} - {bot_health['main_bot']}")
        print(f"   • Hunter Bot: {'✅' if running_bots['hunter_bot'] else '❌'} - {bot_health['hunter_bot']}")
        print(f"   • Total Running: {sum(running_bots.values())}/2 bots")
        print("=" * 70)
        print("\n📈 Monitoring logs... (Press Ctrl+C to stop)")
        print("=" * 70)
        
        # Keep checking bot status
        check_count = 0
        restart_attempts = {"main_bot": 0, "hunter_bot": 0}
        
        while True:
            time.sleep(30)
            check_count += 1
            
            # Health check
            check_bot_health()
            
            # Print status every 3 checks (1.5 minutes)
            if check_count % 3 == 0:
                print(f"\n🔄 Status check #{check_count}:")
                print(f"   • Main Bot:   {'✅' if running_bots['main_bot'] else '❌'} - {bot_health['main_bot']}")
                print(f"   • Hunter Bot: {'✅' if running_bots['hunter_bot'] else '❌'} - {bot_health['hunter_bot']}")
                print(f"   • Uptime: {check_count * 30} seconds")
                
                # Try to restart failed bots (max 3 attempts)
                if os.path.exists("main.py") and not running_bots["main_bot"] and restart_attempts["main_bot"] < 3:
                    print("🔄 Attempting to restart Main Bot...")
                    if len(processes) > 0 and processes[0]:
                        processes[0].terminate()
                        time.sleep(2)
                    processes[0] = run_bot("main.py", "MAIN", 8000)
                    restart_attempts["main_bot"] += 1
                    time.sleep(10)
                
                if not running_bots["hunter_bot"] and restart_attempts["hunter_bot"] < 3:
                    print("🔄 Attempting to restart Hunter Bot...")
                    if len(processes) > 1 and processes[1]:
                        processes[1].terminate()
                        time.sleep(2)
                    processes[1] = run_bot("reset.py", "HUNTER", 6001)
                    restart_attempts["hunter_bot"] += 1
                    time.sleep(10)
            
            # Reset restart attempts every 30 minutes
            if check_count % 60 == 0:
                restart_attempts = {"main_bot": 0, "hunter_bot": 0}
                print("🔄 Reset restart attempt counters")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Keyboard interrupt received. Stopping bots...")
    except Exception as e:
        print(f"\n\n❌ Coordinator error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "=" * 70)
        print("📊 FINAL STATUS:")
        print("=" * 70)
        print(f"   • Main Bot:   {'✅' if running_bots['main_bot'] else '❌'} - {bot_health['main_bot']}")
        print(f"   • Hunter Bot: {'✅' if running_bots['hunter_bot'] else '❌'} - {bot_health['hunter_bot']}")
        print(f"   • Total checks performed: {check_count if 'check_count' in locals() else 0}")
        print("=" * 70)
        
        # Cleanup
        cleanup()
        print("\n👋 Coordinator stopped")
        print("=" * 70)

if __name__ == '__main__':
    main()
