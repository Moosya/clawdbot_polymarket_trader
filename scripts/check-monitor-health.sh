#!/bin/bash
# Health check script for position monitor daemon
# Returns 0 if healthy, 1 if unhealthy
# Can be run from cron to restart daemon if needed

HEARTBEAT_FILE="/workspace/runtime/position-monitor-heartbeat.json"
PID_FILE="/workspace/runtime/position-monitor.pid"
MAX_AGE=900  # 15 minutes (3x check interval)

# Check if heartbeat file exists
if [ ! -f "$HEARTBEAT_FILE" ]; then
    echo "❌ UNHEALTHY: Heartbeat file missing"
    exit 1
fi

# Check heartbeat age
last_check=$(jq -r '.last_check // 0' "$HEARTBEAT_FILE")
now=$(date +%s)
age=$((now - last_check))

if [ $age -gt $MAX_AGE ]; then
    echo "❌ UNHEALTHY: Last check was ${age}s ago (max: ${MAX_AGE}s)"
    exit 1
fi

# Check if PID file exists and process is running
if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "❌ UNHEALTHY: PID $pid not running (stale PID file)"
        exit 1
    fi
else
    echo "⚠️  WARNING: PID file missing (daemon may have just restarted)"
fi

echo "✅ HEALTHY: Last check ${age}s ago, PID $(cat $PID_FILE 2>/dev/null || echo 'unknown')"
exit 0
