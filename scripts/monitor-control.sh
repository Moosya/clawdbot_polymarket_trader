#!/bin/bash
# Control script for position monitor daemon

DAEMON_SCRIPT="/workspace/scripts/position-monitor-daemon.py"
LOG_FILE="/workspace/logs/position-monitor.log"
PID_FILE="/workspace/runtime/position-monitor.pid"

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            pid=$(cat "$PID_FILE")
            if kill -0 "$pid" 2>/dev/null; then
                echo "❌ Daemon already running (PID $pid)"
                exit 1
            else
                echo "⚠️  Removing stale PID file"
                rm -f "$PID_FILE"
            fi
        fi
        
        echo "🚀 Starting position monitor daemon..."
        mkdir -p "$(dirname "$LOG_FILE")"
        nohup python3 "$DAEMON_SCRIPT" >> "$LOG_FILE" 2>&1 &
        sleep 2
        
        if [ -f "$PID_FILE" ]; then
            echo "✅ Daemon started (PID $(cat $PID_FILE))"
            echo "📋 Log: $LOG_FILE"
        else
            echo "❌ Failed to start daemon"
            tail -20 "$LOG_FILE"
            exit 1
        fi
        ;;
        
    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "⚠️  Daemon not running (no PID file)"
            exit 0
        fi
        
        pid=$(cat "$PID_FILE")
        echo "🛑 Stopping daemon (PID $pid)..."
        
        if kill -TERM "$pid" 2>/dev/null; then
            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    echo "✅ Daemon stopped gracefully"
                    exit 0
                fi
                sleep 1
            done
            
            # Force kill if still running
            echo "⚠️  Forcing kill..."
            kill -9 "$pid" 2>/dev/null
            echo "✅ Daemon stopped (forced)"
        else
            echo "⚠️  Process $pid not found (cleaning up PID file)"
            rm -f "$PID_FILE"
        fi
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        /workspace/scripts/check-monitor-health.sh
        exit $?
        ;;
        
    logs)
        tail -f "$LOG_FILE"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
