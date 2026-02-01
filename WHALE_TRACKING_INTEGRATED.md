# 🐋 Whale Tracking - Integrated!

**Just added to the dashboard:** Real-time whale tracking + profitable traders leaderboard!

## What's New

### 🐋 Whale Trades Tab
Shows recent large trades (>$1000) with:
- Market name
- BUY/SELL direction (green = buying, red = selling)
- Trade size
- Price
- Wallet address (shortened)
- Time ago

**Why it matters:** Whales move markets. When you see multiple large BUYs on the same market, that's a signal.

### 💎 Top Profitable Traders
Leaderboard of the 20 most profitable wallets (minimum 5 trades):
- **Total P&L**: Unrealized + Realized profit
- **ROI %**: Efficiency (profit / volume)
- **Win Rate**: % of closed positions that were profitable
- **Active Positions**: Current open positions
- **Color coding**: Green = profitable, Red = losing

**Why it matters:** Copy the winners! These are the wallets making real money.

## How It Works

### Trade Feed
- Uses Polymarket Data API (`https://data-api.polymarket.com/trades`)
- **Public API - no authentication needed!**
- Fetches 200 most recent trades every 2 minutes
- Stores up to 50,000 trades in `data/trades.json`

### Position Tracking
- Tracks each wallet's positions per market
- BUYs add to position, SELLs reduce it
- Calculates volume-weighted average entry price
- Estimates unrealized P&L based on current prices
- Tracks realized P&L from closed positions

### P&L Calculation
**Unrealized (Open Positions):**
```
P&L = (Current Price - Entry Price) × Position Size
```

**Realized (Closed Positions):**
```
P&L = Total SELL proceeds - Total BUY cost
```

**ROI:**
```
ROI % = (Total P&L / Total Volume) × 100
```

## New Files

```
src/api/trade_feed.ts          - Fetch trades from Data API
src/utils/trade_database.ts    - Store trades in JSON file
src/strategies/position_tracker.ts - Calculate P&L, ROI, win rates
```

## Data Storage

**Persistent storage in `data/` folder:**
- `data/trades.json` - Up to 50,000 trades
- Survives restarts
- Human-readable JSON
- Auto-rotates oldest trades

**First run:** Will show "Building trader history..." because there's no data yet. After a few scans (6-10 minutes), you'll start seeing top traders.

## Dashboard Sections

1. **Arbitrage Opportunities** (existing)
2. **Volume Spikes** (existing)
3. **New Markets** (existing)
4. **🐋 Whale Trades** (NEW)
5. **💎 Top Profitable Traders** (NEW)

## Key Features

### Copy the Winners
- See which wallets are making money
- Track their positions in real-time
- Filter by ROI (efficiency) or total profit

### Avoid the Losers
- Red highlighting shows losing traders
- Win rate shows consistency
- Some high-volume traders lose money!

### Direction Signals
- BUY = Bullish (expecting YES outcome)
- SELL = Bearish (expecting NO outcome)
- Multiple whales buying = strong signal

## Trade Signal Hierarchy

**Strongest signals (combine multiple):**
1. 🐋 Whale buying + 💰 Arbitrage = Immediate opportunity
2. 💎 Multiple profitable traders agree + 🔥 Volume spike = High conviction
3. 🆕 New market + 🐋 Whale accumulation = Early mover edge
4. 💎 Top trader enters + 💰 Arbitrage = Smart money sees mispricing

## Limitations

**P&L is estimated:**
- Uses last trade price (not order book depth)
- No slippage accounting
- No trading fees included
- Only knows trades in our database window

**For precise positions:** Check on-chain via Polygonscan or Polymarket directly

## What's Next (Future Ideas)

### Smart Money Consensus
- Show markets where multiple profitable traders agree
- Highlight when they're all buying/selling same side
- Weighted by trader performance

### Wallet Watchlist
- Add specific wallets to watch
- Get alerts when they trade
- Track their full history

### On-chain Verification
- Link to Polygonscan for each trade
- Verify actual positions on-chain
- Real balance checking

## Usage Tips

**Look for patterns:**
- Same whales trading same markets repeatedly = conviction
- Profitable traders switching direction = important
- New whale entering market = potential catalyst

**Combine signals:**
- Whale BUY + Arbitrage = immediate trade
- Volume spike + profitable traders = investigate why
- New market + whale accumulation = early edge

**Monitor top traders:**
- Check which markets they're active in
- See if they're buying or selling
- Follow their direction (carefully!)

## Data Persistence

The database survives:
- Server restarts
- Code updates (git pull)
- npm rebuilds
- Process crashes

Just don't delete `data/trades.json`!

## Quick Start

```bash
git pull
npm run web
```

Dashboard at: **http://localhost:3000**

Watch the whale trades and top traders sections populate over the next 10-15 minutes as trades are collected!

---

**Built in ~2 hours** by integrating features from the whale-tracker repo. 🦀
