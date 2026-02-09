#!/usr/bin/env python3
"""
Position Monitor Daemon
Continuously monitors open positions, updates prices, checks stop-losses and exit signals.
Runs independently of heartbeat for faster reaction times.
"""

import json
import time
import signal
import sys
import os
from pathlib import Path
from datetime import datetime

# Detect base directory (container vs host)
if Path("/opt/polymarket").exists():
    BASE_DIR = Path("/opt/polymarket")
else:
    BASE_DIR = Path("/workspace")

# Configuration
CHECK_INTERVAL = 300  # 5 minutes in seconds
HEARTBEAT_FILE = BASE_DIR / "runtime" / "position-monitor-heartbeat.json"
PID_FILE = BASE_DIR / "runtime" / "position-monitor.pid"

# Ensure runtime directory exists
HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)

running = True

def signal_handler(sig, frame):
    """Handle shutdown gracefully"""
    global running
    print(f"\n🛑 Received signal {sig}, shutting down gracefully...")
    running = False

def update_heartbeat():
    """Write heartbeat timestamp for health monitoring"""
    try:
        HEARTBEAT_FILE.write_text(json.dumps({
            "last_check": int(time.time()),
            "last_check_iso": datetime.now().isoformat(),
            "pid": os.getpid()
        }, indent=2))
    except Exception as e:
        print(f"⚠️  Warning: Could not update heartbeat file: {e}")

def write_pid():
    """Write PID file"""
    try:
        PID_FILE.write_text(str(os.getpid()))
    except Exception as e:
        print(f"⚠️  Warning: Could not write PID file: {e}")

def remove_pid():
    """Remove PID file on shutdown"""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        print(f"⚠️  Warning: Could not remove PID file: {e}")

def run_position_checks():
    """Run all position monitoring checks"""
    import subprocess
    
    checks = [
        ("Update Prices", [sys.executable, str(BASE_DIR / "scripts" / "update-position-prices.py")]),
        ("Check Exits", [sys.executable, str(BASE_DIR / "scripts" / "check-exit-signals.py")]),
        ("Check Stops", [sys.executable, str(BASE_DIR / "scripts" / "check-stop-losses.py")]),
    ]
    
    for name, cmd in checks:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(BASE_DIR))
            if result.returncode != 0 and result.stderr:
                stderr_clean = result.stderr.strip()
                # Only print if not just "file not found" (scripts may not exist yet)
                if stderr_clean and "No such file" not in stderr_clean:
                    print(f"⚠️  {name} error: {stderr_clean}")
            elif result.stdout and result.stdout.strip():
                # Only print if there's meaningful output
                output = result.stdout.strip()
                if output and output != "NO_ALERTS":
                    print(f"✅ {name}: {output}")
        except subprocess.TimeoutExpired:
            print(f"⏱️  {name} timed out (>60s)")
        except FileNotFoundError:
            print(f"⚠️  {name} script not found (skipping)")
        except Exception as e:
            print(f"❌ {name} failed: {e}")

def main():
    """Main daemon loop"""
    global running
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    write_pid()
    
    print(f"🤖 Position Monitor Daemon Starting")
    print(f"   Base directory: {BASE_DIR}")
    print(f"   Check interval: {CHECK_INTERVAL}s ({CHECK_INTERVAL/60:.1f} minutes)")
    print(f"   Heartbeat file: {HEARTBEAT_FILE}")
    print(f"   PID file: {PID_FILE}")
    print(f"   Started at: {datetime.now().isoformat()}\n")
    
    try:
        while running:
            check_start = time.time()
            
            print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running position checks...")
            
            try:
                run_position_checks()
                update_heartbeat()
                print(f"✅ Check complete ({time.time() - check_start:.1f}s)")
            except Exception as e:
                print(f"❌ Check failed: {e}")
            
            # Sleep in small intervals to allow responsive shutdown
            sleep_remaining = CHECK_INTERVAL
            while running and sleep_remaining > 0:
                time.sleep(min(1, sleep_remaining))
                sleep_remaining -= 1
                
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    finally:
        remove_pid()
        print(f"👋 Position Monitor Daemon stopped at {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
