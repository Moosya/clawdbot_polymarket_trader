#!/bin/bash
# Watchdog script to ensure position monitor daemon is running
# Call from cron every 5-10 minutes

# Detect base directory (container vs host)
if [ -d "/opt/polymarket" ]; then
    BASE_DIR="/opt/polymarket"
else
    BASE_DIR="/workspace"
fi

DAEMON_SCRIPT="$BASE_DIR/scripts/position-monitor-daemon.py"
CONTROL_SCRIPT="$BASE_DIR/scripts/monitor-control.sh"
HEALTH_CHECK="$BASE_DIR/scripts/check-monitor-health.sh"
LOG_FILE="$BASE_DIR/logs/position-monitor.log"
PID_FILE="$BASE_DIR/runtime/position-monitor.pid"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Check health
if "$HEALTH_CHECK" > /dev/null 2>&1; then
    # Daemon is healthy
    exit 0
fi

echo "[$(date -Iseconds)] Daemon unhealthy, attempting restart..." >> "$LOG_FILE"

# Kill stale process if PID file exists
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        echo "[$(date -Iseconds)] Killing stale process $old_pid" >> "$LOG_FILE"
        kill -TERM "$old_pid"
        sleep 2
        kill -9 "$old_pid" 2>/dev/null
    fi
    rm -f "$PID_FILE"
fi

# Start daemon
echo "[$(date -Iseconds)] Starting position monitor daemon..." >> "$LOG_FILE"
nohup python3 "$DAEMON_SCRIPT" >> "$LOG_FILE" 2>&1 &

sleep 2

# Verify it started
if "$HEALTH_CHECK" >> "$LOG_FILE" 2>&1; then
    echo "[$(date -Iseconds)] ✅ Daemon restarted successfully" >> "$LOG_FILE"
    exit 0
else
    echo "[$(date -Iseconds)] ❌ Daemon failed to restart" >> "$LOG_FILE"
    exit 1
fi
