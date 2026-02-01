# Polymarket Trading Bot 🦀

Automated trading bot for Polymarket using systematic arbitrage, market making, and momentum strategies.

**Current Status:** Milestone 1 - Basic Arbitrage Detection

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Your `.env` file is already set up with Polymarket API credentials.

### 3. Build

```bash
npm run build
```

### 4. Run

```bash
npm start
```

Or for development with hot reload:

```bash
npm run dev
```

## What It Does (Milestone 1)

The bot currently:
- ✅ Connects to Polymarket CLOB API
- ✅ Fetches all active markets
- ✅ Checks for arbitrage opportunities (YES + NO < $1.00)
- ✅ Prints opportunities to console with profit calculations
- ✅ Scans continuously every 10 seconds

**Example Output:**

```
🦀 ARBITRAGE FOUND!
Market: Will Bitcoin hit $50,000 by end of month?
YES: $0.2700 | NO: $0.7100
Combined: $0.9800
Profit: $0.0200 per share (2.04%)
Market ID: 0x1234...
```

## Project Structure

```
src/
├── api/
│   └── polymarket_client.ts    # Polymarket CLOB API wrapper
├── strategies/
│   └── arbitrage_detector.ts   # Binary complement arbitrage
├── types.ts                     # TypeScript interfaces
└── main.ts                      # Entry point
```

## Roadmap

See `ROADMAP.md` for full development plan.

**Next Up (Milestone 2):**
- Paper trading engine (virtual wallet)
- Simulate trade execution
- Track P&L
- Log trades to file

## Configuration

Edit `.env` to adjust settings:

```env
# Paper Trading
PAPER_TRADING=true
STARTING_BALANCE=10000

# Minimum profit threshold (%)
MIN_PROFIT_PERCENT=0.5
```

## Development

**Watch mode** (auto-recompile on file changes):
```bash
npm run watch
```

**Build only:**
```bash
npm run build
```

## Documentation

- `RESEARCH.md` - Trading strategy research
- `PROJECT.md` - Project architecture and status
- `ROADMAP.md` - Development milestones
- `memory/` - Daily development logs

## Support

Questions? Message on Telegram.

---

**Built by:** Krabby 🦀  
**For:** Andrei  
**Phase:** 2 - Infrastructure Development
