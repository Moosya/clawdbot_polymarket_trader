#!/bin/bash
# git-push-helper.sh - Complete workflow from container

set -e

export HOME=/tmp
git config --global user.email "clawdbot@polymarket.bot" 2>/dev/null || true
git config --global user.name "Krabby" 2>/dev/null || true

# Load GitHub token
GITHUB_TOKEN=$(grep GITHUB_TOKEN /workspace/.env | cut -d'=' -f2)

cd /tmp && rm -rf repo 2>/dev/null || true
echo "🦀 Cloning repo..."
git clone https://github.com/Moosya/clawdbot_polymarket_trader.git repo

cd /tmp/repo
echo "🦀 Setting up authenticated remote..."
git remote set-url origin https://${GITHUB_TOKEN}@github.com/Moosya/clawdbot_polymarket_trader.git

echo "🦀 Copying changed files from workspace..."
# Copy specific files that changed
for file in /workspace/*.{md,sh,json,js,ts}; do
  if [ -f "$file" ]; then
    cp "$file" /tmp/repo/ 2>/dev/null || true
  fi
done

# Copy directories if they exist
[ -d /workspace/memory ] && cp -r /workspace/memory /tmp/repo/ 2>/dev/null || true
[ -d /workspace/src ] && cp -r /workspace/src /tmp/repo/ 2>/dev/null || true
[ -d /workspace/polymarket_bot ] && cp -r /workspace/polymarket_bot /tmp/repo/ 2>/dev/null || true

echo "🦀 Committing changes..."
git add .
git status --short
git commit -m "${1:-Update from container workspace}"

echo "🦀 Pushing to GitHub..."
git push origin master

echo ""
echo "✅ Successfully pushed to GitHub!"
rm -rf /tmp/repo
