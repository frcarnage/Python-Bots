# runner.py - Simple runner for both bots
import os
import subprocess
import time

print("🤖 Starting both bots...")

# Run main.py
main_process = subprocess.Popen(["python", "main.py"])

# Run reset.py  
reset_process = subprocess.Popen(["python", "reset.py"])

print("✅ Both bots started!")

# Keep alive
try:
    while True:
        time.sleep(60)
        print("🏃 Both bots still running...")
except KeyboardInterrupt:
    print("🛑 Stopping bots...")
    main_process.terminate()
    reset_process.terminate()
