# coordinator.py - Runs both bots without conflicts
import subprocess
import time
import os
import sys
import signal
from threading import Thread
from flask import Flask, jsonify
import threading

# Create Flask app for coordinator health checks
coordinator_app = Flask(__name__)

# Track running bots
running_bots = {
    "main_bot": False,
    "reset_bot": False
}

@coordinator_app.route('/health/runner')
def health():
    """Health check for the coordinator"""
    return jsonify({
        "status": "healthy",
        "coordinator": True,
        "running_bots": {
            "main_bot": running_bots["main_bot"],
            "reset_bot": running_bots["reset_bot"]
        },
        "total_bots": sum(running_bots.values()),
        "timestamp": time.time()
    }), 200

@coordinator_app.route('/')
def home():
    """Home page"""
    return jsonify({
        "service": "Bot Coordinator",
        "description": "Manages multiple Telegram bots",
        "endpoints": {
            "/": "This page",
            "/health/runner": "Coordinator health check",
            "main_bot": "http://localhost:8000",
            "reset_bot_health": "http://localhost:5001/health/reset"
        }
    })

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

def run_bot(script_name, name):
    """Run a bot script and update status"""
    print(f"🚀 Starting {name} ({script_name})...")
    running_bots[f"{name.lower()}_bot"] = True
    
    process = subprocess.Popen(
        [sys.executable, script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Stream output
    def stream_output():
        for line in process.stdout:
            print(f"[{name}] {line.strip()}")
            # Check if process died
            if process.poll() is not None:
                print(f"❌ {name} stopped unexpectedly")
                running_bots[f"{name.lower()}_bot"] = False
                break
    
    output_thread = Thread(target=stream_output, daemon=True)
    output_thread.start()
    
    return process

def signal_handler(signum, frame):
    print(f"\n🛑 Received signal {signum}. Stopping bots...")
    for key in running_bots:
        running_bots[key] = False
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 50)
    print("🤖 BOT COORDINATOR - Running both bots")
    print("=" * 50)
    
    # Start Flask server in background thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(1)  # Let Flask start
    
    # Check scripts exist
    if not os.path.exists("main.py"):
        print("⚠️ main.py not found! Running reset.py only")
    else:
        print("✅ Found main.py")
    
    if not os.path.exists("reset.py"):
        print("❌ reset.py not found!")
        sys.exit(1)
    
    print("\n📡 Available URLs:")
    print("• Coordinator: http://localhost:8080/health/runner")
    print("• Main Bot:    http://localhost:8000")
    print("• Reset Bot:   http://localhost:5001/health/reset")
    print("=" * 50)
    
    processes = []
    
    try:
        # Start main.py if it exists
        if os.path.exists("main.py"):
            processes.append(run_bot("main.py", "MAIN"))
            time.sleep(5)  # Wait for main bot to start
        
        # Start reset.py
        processes.append(run_bot("reset.py", "RESET"))
        
        print("\n✅ Bots started! Status:")
        print(f"   • Main Bot:  {'✅' if running_bots['main_bot'] else '❌'}")
        print(f"   • Reset Bot: {'✅' if running_bots['reset_bot'] else '❌'}")
        print("\n📊 Monitoring logs...")
        print("=" * 50)
        
        # Keep checking bot status
        check_count = 0
        while True:
            time.sleep(30)
            check_count += 1
            
            # Print status every 5 checks (2.5 minutes)
            if check_count % 5 == 0:
                print(f"\n🔄 Status check #{check_count}:")
                print(f"   • Main Bot:  {'✅' if running_bots['main_bot'] else '❌'}")
                print(f"   • Reset Bot: {'✅' if running_bots['reset_bot'] else '❌'}")
                print(f"   • Total: {sum(running_bots.values())}/2 bots")
                
                # Try to restart failed bots
                if os.path.exists("main.py") and not running_bots["main_bot"]:
                    print("🔄 Attempting to restart Main Bot...")
                    processes[0] = run_bot("main.py", "MAIN")
                
                if not running_bots["reset_bot"]:
                    print("🔄 Attempting to restart Reset Bot...")
                    processes[1] = run_bot("reset.py", "RESET")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping bots...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Update status
        for key in running_bots:
            running_bots[key] = False
        
        # Terminate processes
        for proc in processes:
            if proc and proc.poll() is None:
                print(f"🛑 Terminating process...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except:
                    proc.kill()
        
        print("👋 Coordinator stopped")
