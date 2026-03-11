# Trading System Workspace

This directory contains the Python-based trading logic and monitoring scripts that work alongside the TypeScript data collection system.

## Structure

### `/scripts/` - Python Trading Scripts

**Signal Detection:**
- `detect-whale-clusters.py` - Finds when multiple whales bet the same direction
- `detect-smart-money-divergence.py` - Finds contrarian whale bets against crowd
- Writes signals to `data/trading.db`

**Trading:**
- `auto-trader.py` - Paper trades based on signals ≥70% confidence
- Runs every 15 minutes via cron

**Analysis:**
- `trader_performance.py` - Library for whale profitability tracking (Case #1: trades, Case #2: resolutions)
- `update-whale-profitability.py` - Daily whale P&L updates
- `calculate-trader-performance.py` - Rankings report

**Monitoring:**
- `heartbeat-check.py` - System health checks every 4 hours
- Telegram alerts via OpenClaw

**Utilities:**
- `market_filters.py` - Filter sports/entertainment/high-frequency markets
- Email scripts for family communications
- Various helper scripts

### `/docs/` - System Documentation

- `AGENTS.md` - Operating instructions for the AI assistant
- `HEARTBEAT.md` - Monitoring tasks and alert definitions
- `MEMORY.md` - Long-term knowledge base
- `SOUL.md` - AI personality/behavior guidelines
- `SYSTEM_ARCHITECTURE.md` - System overview
- `TRADING_PRIVACY.md` - Security guidelines
- `PATH_GUIDE.md` - File path mappings (container vs host)

## Data Flow

1. **TypeScript collector** (`src/main.ts`) → Writes whale trades to `data/trades.db`
2. **Python detectors** (run every 10 min) → Read trades, write signals to `data/trading.db`
3. **Auto-trader** (runs every 15 min) → Reads signals, creates paper positions
4. **Dashboard** (`src/web/`) → Reads both databases, displays via web UI
5. **Heartbeat** (runs every 4 hours) → Checks everything, sends Telegram alerts

## Requirements

- Python 3.11+
- Node.js (for TypeScript collector)
- PM2 (process management)
- OpenClaw (for Telegram integration)

## Setup

See main README for full setup instructions.

## Migration Notes

These scripts were originally in `/home/clawdbot/clawd/scripts/` but are now version-controlled here for easier deployment and backup.
