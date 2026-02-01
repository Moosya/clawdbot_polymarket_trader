#!/bin/bash
# Setup script for hybrid monitoring (host bot + sandbox log access)

set -e

echo "🦀 Setting up Polymarket bot monitoring..."

# 1. Create logs directory
mkdir -p ~/clawdbot_polymarket_trader/logs
echo "✅ Created logs directory"

# 2. Find Clawdbot workspace (where sandbox can read)
CLAWDBOT_WORKSPACE="/home/clawdbot/clawd"
if [ ! -d "$CLAWDBOT_WORKSPACE" ]; then
    echo "⚠️  Clawdbot workspace not found at $CLAWDBOT_WORKSPACE"
    echo "Looking for alternative locations..."
    CLAWDBOT_WORKSPACE="/workspace"
fi

# 3. Create monitoring directory in Clawdbot workspace
mkdir -p "$CLAWDBOT_WORKSPACE/polymarket_bot"
echo "✅ Created monitoring directory at $CLAWDBOT_WORKSPACE/polymarket_bot"

# 4. Create symlink from bot logs to Clawdbot workspace
ln -sf ~/clawdbot_polymarket_trader/logs "$CLAWDBOT_WORKSPACE/polymarket_bot/logs"
echo "✅ Created symlink: $CLAWDBOT_WORKSPACE/polymarket_bot/logs -> ~/clawdbot_polymarket_trader/logs"

# 5. Create status file
echo "{\"status\":\"setup_complete\",\"timestamp\":\"$(date -Iseconds)\"}" > "$CLAWDBOT_WORKSPACE/polymarket_bot/status.json"
echo "✅ Created status file"

# 6. Set permissions
chmod -R 755 ~/clawdbot_polymarket_trader/logs
chmod -R 755 "$CLAWDBOT_WORKSPACE/polymarket_bot"
echo "✅ Set permissions"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Sandbox can now read logs at: $CLAWDBOT_WORKSPACE/polymarket_bot/logs/"
echo "Bot will write logs to: ~/clawdbot_polymarket_trader/logs/"
echo ""
echo "Next steps:"
echo "1. Run the bot: cd ~/clawdbot_polymarket_trader && npm start"
echo "2. Krabby will be able to tail logs from the sandbox"
