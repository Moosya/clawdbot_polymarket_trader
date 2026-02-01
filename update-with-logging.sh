#!/bin/bash
# Update and restart bot with logging enabled

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

# Start with logging (background + nohup)
echo "🚀 Starting bot with logging..."
nohup npm start > logs/console.log 2>&1 &
PID=$!

echo "✅ Bot started! PID: $PID"
echo "📋 Logs: ~/clawdbot_polymarket_trader/logs/"
echo ""
echo "To view logs: tail -f ~/clawdbot_polymarket_trader/logs/console.log"
echo "To stop bot: kill $PID"
