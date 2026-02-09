#!/bin/bash
set -e

# Safety check: must run as clawdbot (UID 1000)
if [ "$(id -u)" -ne 1000 ]; then
  echo "❌ ERROR: This script must be run as clawdbot (UID 1000)"
  echo "   Current user: $(whoami) (UID $(id -u))"
  echo ""
  echo "   Run this instead:"
  echo "   sudo -u clawdbot /opt/polymarket/deploy.sh"
  echo ""
  exit 1
fi

LOGFILE="/opt/polymarket/logs/last_deployment.log"

echo "🚀 Deploying Polymarket Dashboard..." | tee $LOGFILE
echo "📅 $(date)" | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

cd /opt/polymarket

echo "📥 Pulling latest code..." | tee -a $LOGFILE
git pull origin master 2>&1 | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "📦 Installing dependencies..." | tee -a $LOGFILE
npm install 2>&1 | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "🔨 Building..." | tee -a $LOGFILE
npm run build 2>&1 | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "📌 Injecting version..." | tee -a $LOGFILE
COMMIT=$(git log -1 --format="%h")
sed -i "s/v[0-9a-f]\{7\}/v${COMMIT}/g" dist/web/server.js
echo "   Version: v${COMMIT}" | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "♻️ Restarting dashboard service..." | tee -a $LOGFILE
pm2 restart polymarket-dashboard 2>&1 | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "🤖 Setting up position monitor daemon..." | tee -a $LOGFILE

# Stop old daemon if running
if [ -f /workspace/runtime/position-monitor.pid ]; then
  echo "   Stopping old daemon..." | tee -a $LOGFILE
  /opt/polymarket/scripts/monitor-control.sh stop 2>&1 | tee -a $LOGFILE || true
  sleep 2
fi

# Start daemon
echo "   Starting daemon..." | tee -a $LOGFILE
/opt/polymarket/scripts/monitor-control.sh start 2>&1 | tee -a $LOGFILE

# Verify it's running
sleep 3
if /opt/polymarket/scripts/check-monitor-health.sh 2>&1 | tee -a $LOGFILE; then
  echo "   ✅ Daemon healthy" | tee -a $LOGFILE
else
  echo "   ⚠️  Daemon health check failed" | tee -a $LOGFILE
fi
echo "" | tee -a $LOGFILE

# Set up cron watchdog (idempotent)
echo "⏰ Setting up cron watchdog..." | tee -a $LOGFILE
CRON_LINE="*/10 * * * * /opt/polymarket/scripts/ensure-monitor-running.sh"
(crontab -l 2>/dev/null | grep -v "ensure-monitor-running.sh" || true; echo "$CRON_LINE") | crontab -
echo "   Cron job installed: check every 10 minutes" | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "✅ Deployment complete!" | tee -a $LOGFILE
pm2 status | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "📊 Recent dashboard logs:" | tee -a $LOGFILE
pm2 logs polymarket-dashboard --lines 20 --nostream 2>&1 | tee -a $LOGFILE
