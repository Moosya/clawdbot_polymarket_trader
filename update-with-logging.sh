#!/bin/bash
# Update and restart bot with logging to shared volume

set -e

cd ~/clawdbot_polymarket_trader

echo "🦀 Updating Polymarket bot..."

# Pull latest code
git pull origin master
echo "✅ Pulled latest code"

# Install dependencies
npm install
echo "✅ Installed dependencies"

# Build
npm run build
echo "✅ Built TypeScript"

# Kill old process if running
pkill -f "node dist/main.js" || echo "No existing process found"
sleep 2

# Create shared logs directory (accessible from sandbox)
SHARED_LOGS="/home/clawdbot/clawd/polymarket_bot/logs"
mkdir -p "$SHARED_LOGS"

# Start with logging to shared volume (background + nohup)
echo "🚀 Starting bot with logging to shared volume..."
cd ~/clawdbot_polymarket_trader
nohup npm start > "$SHARED_LOGS/console.log" 2>&1 &
PID=$!

echo "✅ Bot started! PID: $PID"
echo "📋 Logs: $SHARED_LOGS/"
echo "📋 Krabby can read from: /workspace/polymarket_bot/logs/"
echo ""
echo "To view logs: tail -f $SHARED_LOGS/console.log"
echo "To stop bot: kill $PID"
