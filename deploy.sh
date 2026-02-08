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

echo "♻️ Restarting service..." | tee -a $LOGFILE
pm2 restart polymarket-dashboard 2>&1 | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "✅ Deployment complete!" | tee -a $LOGFILE
pm2 status | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

echo "📊 Recent logs:" | tee -a $LOGFILE
pm2 logs polymarket-dashboard --lines 20 --nostream 2>&1 | tee -a $LOGFILE
