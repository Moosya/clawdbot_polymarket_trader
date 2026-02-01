#!/bin/bash
# Safe web server starter - kills existing process on port 3000 first

PORT=3000

echo "🔍 Checking for existing processes on port $PORT..."

# Find process using port 3000
PID=$(lsof -ti:$PORT)

if [ ! -z "$PID" ]; then
  echo "⚠️  Found process $PID using port $PORT"
  echo "🔪 Killing process $PID..."
  kill -9 $PID
  sleep 1
  echo "✅ Port $PORT is now free"
else
  echo "✅ Port $PORT is already free"
fi

echo "🚀 Starting web dashboard..."
npm run web
