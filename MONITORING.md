# Monitoring Setup

This bot uses a hybrid monitoring approach where the bot runs on the droplet host and Krabby (the Clawdbot agent) can read logs from its sandbox.

## Setup Steps

### 1. Initial Setup (run once)

```bash
cd ~/clawdbot_polymarket_trader
./setup-monitoring.sh
```

This creates:
- `~/clawdbot_polymarket_trader/logs/` - where the bot writes logs
- `/home/clawdbot/clawd/polymarket_bot/logs/` - symlink Krabby can read from sandbox

### 2. Update & Restart Bot

```bash
cd ~/clawdbot_polymarket_trader
./update-with-logging.sh
```

This:
- Pulls latest code from GitHub
- Rebuilds TypeScript
- Restarts the bot in background
- Logs to `logs/console.log` and `logs/bot.jsonl`

## Log Files

- **`logs/console.log`** - Raw console output (stdout/stderr)
- **`logs/bot.jsonl`** - Structured JSON Lines logs (parseable by Krabby)

## Manual Commands

**View live logs:**
```bash
tail -f ~/clawdbot_polymarket_trader/logs/console.log
```

**Check bot status:**
```bash
ps aux | grep "node dist/main.js"
```

**Stop bot:**
```bash
pkill -f "node dist/main.js"
```

**Start bot manually:**
```bash
cd ~/clawdbot_polymarket_trader
nohup npm start > logs/console.log 2>&1 &
```

## How Krabby Reads Logs

From Krabby's sandbox:
```bash
# Read latest scan results
tail -1 /home/clawdbot/clawd/polymarket_bot/logs/bot.jsonl | jq

# Follow live logs
tail -f /home/clawdbot/clawd/polymarket_bot/logs/console.log
```

This allows Krabby to:
- Monitor scan results
- See opportunities found
- Debug issues
- Push fixes to GitHub when needed
