# Polymarket Trading Scripts

## Directory Structure

### `signal-detection/`
Signal detection algorithms that analyze whale trade data:

- **`detect-whale-clusters.py`** - Finds coordinated whale activity (3+ whales, same market/outcome, within 1 hour)
- **`detect-smart-money-divergence.py`** - Identifies when whales bet opposite to crowd sentiment
- **`detect-momentum-reversal.py`** - Detects when whales counter-position against price momentum
- **`aggregate-signals.py`** - Unified aggregator that runs all detectors and ranks by confidence

**Output:** `/workspace/signals/aggregated-signals.json`

### `trading/`
Automated trading execution and tracking:

- **`auto-trader.py`** - Main auto-trading engine
  - Reads signals from `aggregated-signals.json`
  - Opens positions for ≥70% confidence signals
  - Alerts on Telegram for ≥80% signals
  - Validates markets before trading
  - Filters: sports markets, high-frequency markets (≤15 min)
  - Stores positions in shared database
  
- **`paper-trading-tracker.py`** - Position tracking and P&L calculation
  - CLI tool for managing paper positions
  - Commands: stats, open, close, update
  - Calculates realized/unrealized P&L, ROI, win rate

**Database:** `/opt/polymarket/data/trading.db` (shared with dashboard)

### Root Scripts

- **`apply-trading-schema.py`** - Initializes trading database schema
- **`schema-trading.sql`** - SQL schema for signals, positions, portfolio snapshots

## Configuration

**Position sizing:** $50 per trade (5% of $1000 portfolio)
**Auto-trade threshold:** ≥70% confidence
**Alert threshold:** ≥80% confidence (sends Telegram notification)

## Execution Flow

1. **Heartbeat (every ~30 min)** triggers:
   ```bash
   python3 scripts/signal-detection/aggregate-signals.py
   python3 scripts/trading/auto-trader.py
   ```

2. **Signal Detection:**
   - Queries `/workspace/polymarket_runtime/data/trades.db` (read-only whale data)
   - Generates signals with confidence scores
   - Outputs to JSON file

3. **Auto-Trading:**
   - Validates markets (checks URLs)
   - Opens positions ≥70% confidence
   - Logs to Mission Control API
   - Stores in shared database

4. **Dashboard:**
   - Host-side dashboard reads same database
   - Shows positions, P&L, portfolio stats
   - Auto-refreshes every 30 seconds

## Data Sources

**Input:** `/workspace/polymarket_runtime/data/trades.db`
- Whale trades collected by polymarket bot
- Read-only from sandbox

**Output:** `/opt/polymarket/data/trading.db`
- Trading signals and positions
- Shared read-write between container and host
- Accessible to dashboard at `/opt/polymarket/data/`

## Filters & Risk Management

**Market Filters:**
- ❌ Sports markets (NBA, NFL, NHL, MLB, soccer, etc.)
- ❌ High-frequency markets (≤15 min duration)
- ❌ Already have open position on same market/outcome
- ❌ Market URL returns 404 (delisted/doesn't exist)

**Risk Management:**
- Max position size: $50 (5% of portfolio)
- Total portfolio: $1000 paper money
- No more than 1 position per market/outcome

## Development

To test signal detection:
```bash
python3 scripts/signal-detection/aggregate-signals.py
cat /workspace/signals/aggregated-signals.json
```

To test auto-trader:
```bash
python3 scripts/trading/auto-trader.py
# Check output for opened positions and alerts
```

To check paper trading stats:
```bash
python3 scripts/trading/paper-trading-tracker.py stats
```

## Database Schema

See `schema-trading.sql` for full schema. Key tables:

- `signals` - All detected signals (stored even if not traded)
- `paper_positions` - Open and closed positions
- `portfolio_snapshots` - Historical portfolio performance

## Integration Points

**Mission Control:** POST to `http://localhost:3001/api/activities`
**Telegram Alerts:** Sent for signals ≥80% confidence
**Dashboard:** Reads from shared trading database
