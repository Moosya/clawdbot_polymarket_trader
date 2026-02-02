# Drill-Down Features (TODO)

## Wallet Detail Page

**Route:** `/wallet/:address`

**Shows:**
- Wallet overview (total P&L, ROI, win rate, volume)
- All positions across markets
  - Market name
  - Position size (net shares)
  - Entry price
  - Current price
  - Unrealized P&L
  - Trade count
- Recent trades (last 50)
  - Timestamp
  - Market
  - Side (BUY/SELL)
  - Size
  - Price
- Performance over time (chart)

**Example from whale-tracker:**
```
Click wallet 0xf00e...5791 →
  - Total P&L: $1,250
  - Active in 12 markets
  - Top position: GTA 6 pricing ($500 exposure)
  - Recent: BUY $2K @ $0.75 (2h ago)
```

## Market Detail Page

**Route:** `/market/:id`

**Shows:**
- Market overview
  - Question
  - Current prices (YES/NO)
  - Total volume
  - Liquidity
  - End date
- Whale activity
  - Which tracked wallets are trading this
  - Their positions (long/short)
  - Recent large trades
- Trade history (last 100)
  - Timestamp
  - Wallet (shortened)
  - Side
  - Size
  - Price
- Price chart over time
- Volume chart

**Example:**
```
Click "Will GTA 6 cost $100+?" →
  - 5 whales active
  - Top trader #3: $5K long position
  - Recent: $2K BUY by 0xf00e...5791
  - Price trend: $0.70 → $0.75 (↑7%)
```

## Implementation Plan

### Phase 1: Basic Pages
1. Create `/wallet/:address` route
2. Create `/market/:id` route
3. Make wallet addresses clickable in tables
4. Make market names clickable in tables

### Phase 2: Enhanced Data
1. Add price history tracking
2. Calculate position P&L with current prices
3. Add charts (simple line charts)

### Phase 3: Polish
1. Add filters (time range, profit/loss)
2. Export to CSV
3. Share links to specific wallets/markets

## Technical Notes

**Current gaps:**
- We're not tracking current market prices continuously
- Need to fetch current prices for unrealized P&L calculation
- Price history not stored (only trade prices)

**To fix:**
- Store market snapshot every scan (current YES/NO prices)
- Build price history table: `{marketId, timestamp, yesPrice, noPrice}`
- Use for unrealized P&L: `(currentPrice - entryPrice) × shares`

**From whale-tracker repo to copy:**
- `/app/wallet/[address]/page.tsx` - Wallet detail page
- `/app/market/[id]/page.tsx` - Market detail page
- `/lib/positionTracker.ts` - Position calculation logic (already integrated!)

## Quick Win

**Start with simple version:**
1. `/wallet/:address` - Show all trades + positions for that wallet
2. `/market/:id` - Show all trades for that market
3. No charts/fancy UI, just tables
4. Can add charts later

Estimated time: 2-3 hours for basic drill-down functionality.
