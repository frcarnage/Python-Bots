# start_bots.py - Better bot runner
import subprocess
import time
import os
import sys
import signal
from threading import Thread
from flask import Flask, jsonify

app = Flask(__name__)

# Store processes
processes = []

@app.route('/')
def home():
    return "🤖 Both Bots Running", 200

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "bots": 2}), 200

def run_bot(script_name, log_prefix):
    """Run a bot script and log output"""
    print(f"🚀 Starting {script_name}...")
    
    # Run the script
    process = subprocess.Popen(
        [sys.executable, script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    processes.append(process)
    
    # Read output in real-time
    while True:
        output = process.stdout.readline()
        if output:
            print(f"[{log_prefix}] {output.strip()}")
        
        # Check if process ended
        if process.poll() is not None:
            break
    
    print(f"❌ {script_name} stopped. Exit code: {process.returncode}")

def start_flask():
    """Start Flask server"""
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {signum}. Stopping bots...")
    for proc in processes:
        proc.terminate()
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 50)
    print("🤖 MULTI-BOT RUNNER")
    print("=" * 50)
    
    # Check if scripts exist
    if not os.path.exists("main.py"):
        print("❌ main.py not found!")
        sys.exit(1)
    
    if not os.path.exists("reset.py"):
        print("❌ reset.py not found!")
        sys.exit(1)
    
    # Start bots in threads
    bot1_thread = Thread(target=lambda: run_bot("main.py", "MAIN"), daemon=True)
    bot2_thread = Thread(target=lambda: run_bot("reset.py", "RESET"), daemon=True)
    
    bot1_thread.start()
    time.sleep(2)  # Small delay
    bot2_thread.start()
    
    # Start Flask in main thread
    start_flask()
