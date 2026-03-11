# MEMORY.md - Long-Term Memory
*Last updated: 2026-02-22*

## ⚠️ IMPORTANT: Verify Before Acting
Before diagnosing any issue, verify actual system state with real commands.
Never trust memory alone — check logs, ls, sqlite3 first. Memory may be outdated.

## System Architecture

### Single Repo (verified 2026-02-21)
- ONE repo: `/opt/polymarket/` (github: Moosya/clawdbot_polymarket_trader)
- Contains: collector (`src/main.ts`), dashboard (`src/web/`), scanner (`src/strategies/`)
- Source mounted in container at: `/workspace/polymarket_src/` (rw)
- **deploy.sh**: /opt/polymarket/deploy.sh - comprehensive and reliable
- Workflow: git pull → npm install → build → pm2 restart → daemon setup
- Run as: sudo -u clawdbot /opt/polymarket/deploy.sh
- Logs to: /opt/polymarket/logs/last_deployment.log

### Frank's Code Workflow
1. Edit source in `/workspace/polymarket_src/src/`
2. Commit and push to GitHub
3. Tell Drei what changed
4. Drei runs build and restart on host
5. Frank never runs npm build or pm2 commands directly

### Container Environment
- Frank runs in Docker sandbox — this is normal and expected
- Path mapping (container → host):
  - `/home/clawdbot/polymarket_src/` → `/opt/polymarket/` (rw)
  - `/home/clawdbot/polymarket_runtime/data/` → `/opt/polymarket/data/` (rw)
  - `/home/clawdbot/polymarket_runtime/logs/` → `/opt/polymarket/logs/` (ro)
  - `/workspace/clawd/` → `/home/clawdbot/clawd/` (home)
- Frank cannot see host processes — use logs to check service health

### Service Health (check via logs, not ps aux)
```bash
tail -20 /home/clawdbot/polymarket_runtime/logs/console.log        # trade collector
tail -20 /home/clawdbot/polymarket_runtime/logs/position-monitor.log  # position monitor
tail -20 /home/clawdbot/polymarket_runtime/logs/dashboard-out.log  # dashboard
tail -20 /home/clawdbot/polymarket_runtime/logs/scanner-out.log    # scanner
```

## Database & File Locations
- **Trades DB**: `/home/clawdbot/polymarket_runtime/data/trades.db` (whale trades, collector writes here)
- **Trading DB**: `/home/clawdbot/polymarket_runtime/data/trading.db` (signals, paper positions)
- **Scripts**: `/workspace/clawd/scripts/`
- **Gmail token**: `/workspace/clawd/.credentials/gmail-token.pickle`

## Known Issues (as of 2026-02-21)
- **Dashboard Total Trades shows 0** — `trade_database.ts` reads deleted `trades.json` instead of `trades.db`. Fix in progress.

## Email & Communication
- **Gmail API**: ✅ Working — OAuth via token at `/workspace/clawd/.credentials/gmail-token.pickle`
- **SMTP blocked**: DigitalOcean blocks ports 25/465/587 — always use Gmail API
- **Telegram heartbeat**: via `openclaw message send --channel telegram --target 1049249843`
- **Backup token**: `/opt/secrets/gmail-token.pickle` — restore by running `openclaw-restore` as root

## Infrastructure
- **Server**: DigitalOcean droplet, Ubuntu
- **Gateway logs**: `/home/clawdbot/openclaw-gateway.log`
- **Restore script**: `/usr/local/bin/openclaw-restore` (run as root after any OpenClaw update)
- **Backup script**: `/usr/local/bin/openclaw-backup` (run as root before any OpenClaw update)
- **Update procedure**: `openclaw-backup && openclaw update && openclaw-restore`

## Trading System
### Current State
- **Paper trading only** — accumulating outcomes for calibration
- **Thresholds**: Auto-trade ≥70%, Alert ≥80%, Whale threshold $2,000
- **Calibration**: Ready once 5+ closed positions exist
- **Arbitrage scanner**: REMOVED 2026-02-28 (0 opportunities in 176,435+ scans over 20 days)

### Superforecasting Integration
- **Base rates**: 65% (whale trades), 70% (smart money divergence), 60% (momentum reversals)
- **Weekly review**: `/workspace/clawd/scripts/weekly-calibration-review.py` — Mondays 9am EST
- **Base rate file**: `/workspace/clawd/memory/signal-base-rates.json`

### Polymarket Platform Notes
- BUY/SELL translation: "SELL No" = "BUY Yes" (No/Yes are inverted)
- Function: `translate_to_polymarket_action()` in auto-trader.py

## Privacy (CRITICAL)
- **NEVER disclose** trading strategies, signal methods, or thresholds publicly
- Includes: Moltbook, Twitter, Discord, GitHub public repos
- Safe to discuss: general risk management, Kelly Criterion, forecasting theory
- **When in doubt: DON'T. Ask Drei first.**

## Family Contacts
- **Drei** (user): EST timezone
- **Alina** (wife): Birthday Feb 15
- **Sasha** (oldest, "Queen of Queens"): FSU student
- **Yosh** (son): Fordham
- **Alek** (son): Fordham
- **Tosh** (younger): College

## Next Milestones
1. Fix dashboard Total Trades (trade_database.ts → SQLite)
2. Accumulate 5+ closed positions → run calibration review
3. Integrate base rates into signal detectors (Phase 2)
4. Deploy Grok validation (with Drei confirmation)
5. Deploy signal market filtering (with Drei confirmation)

## Active Services (as of 2026-02-28)

### polymarket-dashboard (PM2)
**What it actually does:**
- Web UI and API endpoints (port 3000)
- Trade collection (fetches 200 trades every 2 min, stores ≥$2000 to trades.db)
- Signal detection (whale clusters, smart money divergence, volume spikes)
- Position tracking and portfolio stats
- Reads from: trades.db, trading.db
- Writes to: trades.db, trading.db

**Note:** Despite the name "dashboard," this is the complete trading system backend + UI.

**Status:** Operational since Feb 7, 2026. Continuously collecting trades (14,236+ as of Feb 28).
**False alarm history:** Frank's heartbeat checks incorrectly reported "7-day outage" on Feb 28 - this was a monitoring bug, not a real outage. Collector has been healthy throughout.

### position-monitor (daemon)
- Monitors paper trading positions
- Updates unrealized P&L
- Runs as cron job (every 10 min)

### REMOVED Services

**polymarket-scanner (removed 2026-02-28)**
- Was: Arbitrage opportunity detection
- Ran: 176,435+ scans over 20 days
- Found: 0 arbitrage opportunities
- Why removed: Prediction market arbitrage too rare, HFT bots capture in milliseconds
- Code preserved: src/main.ts, src/strategies/arbitrage_detector.ts (for reference)

## 🚨 CRITICAL: Email Formatting for Family (2026-03-06)

**I keep forgetting this and reverting to plain text. READ THIS EVERY TIME BEFORE SENDING FAMILY EMAILS!**

**RULE: Family emails = HTML with emojis, colors, sections, warmth**
- ❌ NEVER plain text to family (boring, looks like spam)
- ✅ ALWAYS HTML with gradients, colored boxes, emojis
- Template saved in: memory/2026-03-06.md (Email Formatting Policy section)

**Recipients: Maria (mom), Alina, Sasha, Alek, Anton - all family emails need pizzazz!**
