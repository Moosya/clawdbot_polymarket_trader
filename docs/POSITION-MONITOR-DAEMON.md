# Position Monitor Daemon

## Overview

The position monitor daemon runs continuously to check open positions, update prices, and execute stop-losses/exits. Unlike heartbeat-driven checks (every ~30 minutes), the daemon runs every 5 minutes for faster reaction times.

## Architecture

**Before (Heartbeat-driven):**
- Clawdbot heartbeat every ~30 minutes
- Slow response to market changes
- Token-heavy for frequent checks

**After (Daemon-driven):**
- Independent Python daemon running 24/7
- Checks every 5 minutes (configurable)
- No token usage for monitoring
- Faster risk management

## Components

### 1. Main Daemon
**File:** `scripts/position-monitor-daemon.py`

Runs continuously and executes:
- `update-position-prices.py` - Update current market prices
- `check-exit-signals.py` - Look for exit opportunities
- `check-stop-losses.py` - Execute stop-losses if triggered

**Configuration:**
```python
CHECK_INTERVAL = 300  # 5 minutes
```

**Health tracking:**
- Writes heartbeat: `/workspace/runtime/position-monitor-heartbeat.json`
- Writes PID file: `/workspace/runtime/position-monitor.pid`

### 2. Health Check
**File:** `scripts/check-monitor-health.sh`

Returns 0 if healthy, 1 if unhealthy. Checks:
- Heartbeat file exists and is recent (<15 min old)
- Process is running (PID check)

### 3. Watchdog/Supervisor
**File:** `scripts/ensure-monitor-running.sh`

Checks health and restarts daemon if needed. Run from cron:
```bash
*/10 * * * * /workspace/scripts/ensure-monitor-running.sh
```

### 4. Control Script
**File:** `scripts/monitor-control.sh`

Manage daemon lifecycle:
```bash
# Start daemon
./scripts/monitor-control.sh start

# Stop daemon
./scripts/monitor-control.sh stop

# Restart daemon
./scripts/monitor-control.sh restart

# Check status
./scripts/monitor-control.sh status

# Tail logs
./scripts/monitor-control.sh logs
```

## Usage

### Manual Operation

Start the daemon:
```bash
./scripts/monitor-control.sh start
```

Check it's running:
```bash
./scripts/monitor-control.sh status
# ✅ HEALTHY: Last check 247s ago, PID 12345
```

View live logs:
```bash
./scripts/monitor-control.sh logs
```

Stop the daemon:
```bash
./scripts/monitor-control.sh stop
```

### Production Deployment

Add to crontab for automatic recovery:
```bash
# Check every 10 minutes and restart if needed
*/10 * * * * /workspace/scripts/ensure-monitor-running.sh
```

Or use systemd service (recommended for production):
```ini
[Unit]
Description=Polymarket Position Monitor
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/workspace
ExecStart=/usr/bin/python3 /workspace/scripts/position-monitor-daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Logs

**Location:** `/workspace/logs/position-monitor.log`

Includes:
- Daemon startup/shutdown events
- Each check cycle with timestamp
- Errors from position checks
- Watchdog restart events

## Integration with Heartbeat

The Clawdbot heartbeat still runs for:
- Email checks
- Calendar checks
- Daily memory maintenance
- Signal aggregation (every 3rd heartbeat)

But **position monitoring** now runs independently via the daemon.

## Troubleshooting

### Daemon won't start
```bash
# Check recent logs
tail -50 /workspace/logs/position-monitor.log

# Look for Python errors
python3 /workspace/scripts/position-monitor-daemon.py
```

### Daemon keeps dying
```bash
# Check system resources
top
df -h

# Look for errors in individual check scripts
python3 /workspace/scripts/update-position-prices.py
python3 /workspace/scripts/check-exit-signals.py
python3 /workspace/scripts/check-stop-losses.py
```

### Health check always fails
```bash
# Verify heartbeat file
cat /workspace/runtime/position-monitor-heartbeat.json

# Check timestamps
date +%s
# Compare to last_check in heartbeat file
```

## Configuration

Edit `scripts/position-monitor-daemon.py`:

```python
# Check every 2 minutes instead of 5
CHECK_INTERVAL = 120

# Change file paths
HEARTBEAT_FILE = Path("/custom/path/heartbeat.json")
PID_FILE = Path("/custom/path/daemon.pid")
```

## Security Notes

- Daemon runs with same permissions as user who starts it
- PID file prevents multiple instances
- Graceful shutdown on SIGTERM/SIGINT
- All output logged for audit trail

## Future Enhancements

- [ ] Configurable check interval via env var
- [ ] Metrics export (Prometheus/Grafana)
- [ ] Alert integration (Telegram notifications on errors)
- [ ] Multiple check strategies (fast/slow modes)
- [ ] Database connection pooling for efficiency
