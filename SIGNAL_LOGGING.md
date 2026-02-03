# Signal Logging Integration

## Overview
Created `src/utils/signal_logger.ts` for machine-readable signal tracking via JSON Lines format.

## Output File
`polymarket_bot/logs/signals.jsonl` - one JSON object per line

## Integration Examples

### 1. Arbitrage Scanner (src/strategies/arbitrage_detector.ts)

```typescript
import { SignalLogger } from '../utils/signal_logger';

// When scanning a market
const spread = yesPrice + noPrice - 1.0;
const liquidity = estimateLiquidity(market);

if (spread < -minProfit) {
  // Opportunity found!
  SignalLogger.arbitrage(
    market.question,
    Math.abs(spread),
    liquidity,
    liquidity >= MIN_LIQUIDITY ? 'FIRE' : 'PASS'
  );
  
  if (liquidity >= MIN_LIQUIDITY) {
    // Execute trade
    SignalLogger.trade(
      'paper',
      'buy',
      calculatePosition(spread),
      'yes',
      yesPrice,
      market.question,
      `arbitrage_spread_${(spread * 100).toFixed(2)}%`
    );
  }
} else {
  // Track near-misses for analysis
  if (spread > -0.002) { // Within 0.2% of arbitrage
    SignalLogger.arbitrage(market.question, Math.abs(spread), liquidity, 'PASS');
  }
}
```

### 2. Volume Spike Detector (src/strategies/volume_spike_detector.ts)

```typescript
import { SignalLogger } from '../utils/signal_logger';

const volumeChange = currentVolume / avgVolume;
const priceMove = Math.abs(currentPrice - priceHistory[0]) / priceHistory[0];

if (volumeChange > VOLUME_THRESHOLD) {
  const confidence = calculateConfidence(volumeChange, priceMove, liquidity);
  
  SignalLogger.volumeSpike(
    market.question,
    volumeChange,
    priceMove,
    confidence > 0.7 ? 'FIRE' : 'PASS',
    confidence
  );
}
```

### 3. Whale Tracker (src/strategies/whale_tracker.ts)

```typescript
import { SignalLogger } from '../utils/signal_logger';

onTrade(trade => {
  if (trade.size > WHALE_THRESHOLD) {
    SignalLogger.whaleTrade(
      trade.market,
      trade.size,
      trade.side,
      trade.price,
      shouldFollow(trade) ? 'FIRE' : 'PASS'
    );
    
    if (shouldFollow(trade)) {
      SignalLogger.trade(
        'paper',
        trade.side,
        calculateFollowSize(trade),
        trade.outcome,
        trade.price,
        trade.market,
        `whale_follow_${trade.size}`
      );
    }
  }
});
```

### 4. Position Tracker (src/strategies/position_tracker.ts)

```typescript
import { SignalLogger } from '../utils/signal_logger';

// Log position updates every scan or on significant moves
positions.forEach(pos => {
  const pnl = (pos.currentPrice - pos.avgPrice) * pos.shares;
  
  SignalLogger.position(
    pos.market,
    pos.outcome,
    pos.shares,
    pos.avgPrice,
    pos.currentPrice,
    pnl
  );
});
```

### 5. Performance Summary (src/main.ts)

```typescript
import { SignalLogger } from './utils/signal_logger';

// Every hour or at end of session
SignalLogger.performance('1h', {
  signals_fired: stats.totalSignals,
  trades_executed: stats.totalTrades,
  win_rate: stats.wins / stats.totalTrades,
  total_pnl: stats.pnl,
  by_signal_type: {
    arbitrage: stats.arbitrageCount,
    volume_spike: stats.volumeCount,
    whale: stats.whaleCount
  }
});
```

## Analysis Examples

Once running, I can analyze with simple commands:

```bash
# Count signals by type
grep '"type":"SIGNAL"' signals.jsonl | grep -o '"signal":"[^"]*"' | sort | uniq -c

# All fired signals
grep '"action":"FIRE"' signals.jsonl

# Arbitrage opportunities only
grep '"signal":"arbitrage"' signals.jsonl

# Trades executed
grep '"type":"TRADE"' signals.jsonl

# Performance summaries
grep '"type":"PERFORMANCE"' signals.jsonl | tail -5

# Calculate win rate from positions
grep '"type":"POSITION"' signals.jsonl | jq -r 'select(.pnl > 0) | .market'
```

## Benefits

✅ **Easy to parse** - Each line is valid JSON  
✅ **Appendable** - No need to read entire file  
✅ **Queryable** - grep, jq, awk work perfectly  
✅ **Time-series** - Every event has ISO timestamp  
✅ **Extensible** - Add new fields without breaking parsing  

## Next Steps

1. Integrate into existing strategies (arbitrage, volume, whale)
2. Add logging to main.ts for periodic performance snapshots
3. Run on server - I'll analyze signals.jsonl in real-time
4. Iterate on signal quality based on what we see
