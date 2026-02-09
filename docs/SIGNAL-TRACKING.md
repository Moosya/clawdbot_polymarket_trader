## Signal Performance Tracking System

### Overview

Track all trading signals, their outcomes, and performance over time to validate which signal types actually predict market outcomes.

**Goal:** Prove (or disprove) our trading edge with data.

---

### Architecture

```
Signal Detection → Log Signal → Market Resolves → Update Outcome → Performance Report
     ↓                 ↓                                ↓                    ↓
aggregate-signals  log-signal.py                update-signal-        signal-performance-
    .py                                         outcomes.py            report.py
```

---

### Database Schema

**Table: `signal_history`**
- Signal details (type, confidence, recommendation)
- Market info (slug, name, end date)
- Outcome tracking (resolved, result, correctness)
- Performance metrics (edge, P&L if traded)

**Views:**
- `signal_performance_summary` - Accuracy by signal type
- `pending_signals` - Unresolved signals
- `high_confidence_failures` - Learn from mistakes

---

### Scripts

#### 1. Initialize Database
```bash
./scripts/init-signal-tracking.sh
```
Creates tables and views in `data/trading.db`

#### 2. Log Signals
```bash
./scripts/log-signal.py <signal_type> <market_slug> <market_name> <confidence> <recommendation> <entry_price> [reasoning_json] [market_end_date]
```

**Example:**
```bash
./scripts/log-signal.py \
    smart_money_divergence \
    "btc-up-or-down-feb-9" \
    "Bitcoin Up or Down - February 9" \
    85 \
    BUY_YES \
    0.52 \
    '{"volume_ratio": 3.2}' \
    "2026-02-09T20:00:00Z"
```

**Signal Types:**
- `whale_cluster` - Large whale buys clustered
- `smart_money_divergence` - Top traders differ from crowd
- `momentum_reversal` - Sharp price movement against trend

**Recommendations:**
- `BUY_YES` - Buy YES tokens
- `BUY_NO` - Buy NO tokens
- `SELL_YES` - Sell YES tokens  
- `SELL_NO` - Sell NO tokens

#### 3. Check Outcomes (Run Daily)
```bash
./scripts/update-signal-outcomes.py
```

Checks all pending signals:
- Fetches market resolution from Polymarket API
- Calculates if signal was correct
- Computes edge (potential profit)
- Updates database

**Add to cron:**
```bash
# Check signal outcomes daily at 9am
0 9 * * * cd /opt/polymarket && ./scripts/update-signal-outcomes.py
```

#### 4. Generate Performance Report
```bash
./scripts/signal-performance-report.py
```

Shows:
- Overall accuracy across all signals
- Performance by signal type
- Performance by confidence level
- Recent signals (last 7 days)
- Pending signals count

---

### Integration with Signal Detection

**Manual approach:** After running `aggregate-signals.py`, manually log signals:
```bash
# For each signal detected
./scripts/log-signal.py smart_money_divergence "market-slug" "Market Name" 85 BUY_YES 0.52
```

**Automated approach:** Modify `aggregate-signals.py` to call `log-signal.py` or import logging function directly.

---

### Key Metrics

**Accuracy:** `correct_signals / resolved_signals`
- Overall accuracy
- By signal type
- By confidence level

**Edge:** `(final_price - entry_price) * direction`
- Average edge per signal type
- Shows potential profit if we had traded

**Sample Size:**
- Need 20-30 resolved signals per type for statistical significance
- Track over 2-4 weeks minimum

---

### Today's Example: Iran Strike Signal

**Signal detected:** Feb 9, 2026
- Type: smart_money_divergence
- Confidence: 90%
- Recommendation: BUY YES @ 0.04
- Market: "US strikes Iran by February 9, 2026?"

**Outcome:** NO strike occurred (market resolved NO)
- Signal was WRONG
- Would have lost ~$0.96 per share
- Edge: -0.96

**Lesson:** High-confidence same-day geopolitical signals are unreliable (breaking news driven).

---

### What We'll Learn

After 2-4 weeks of data:

**Questions to answer:**
1. Which signal types are actually predictive?
2. Does higher confidence = higher accuracy?
3. What's our expected edge per trade?
4. Should we filter certain market types?

**Possible outcomes:**
- ✅ **Signals work:** Scale trading, increase position sizes
- ❌ **Signals don't work:** Pivot to different strategy or monetize data
- 🟡 **Mixed results:** Some signals work, refine detection

---

### Best Practices

**Log every signal:**
- Even if we don't trade it
- Even if market 404s
- Even if we think it's bad

**Check outcomes regularly:**
- Run `update-signal-outcomes.py` daily
- Markets can take days/weeks to resolve

**Review performance weekly:**
- Run `signal-performance-report.py` 
- Look for patterns in failures
- Adjust confidence thresholds

**Document learnings:**
- High-confidence failures teach us the most
- Use `high_confidence_failures` view
- Update signal detection based on patterns

---

### Example Workflow

**Day 1-7: Detection**
```bash
# Signals detected by heartbeat/daemon
aggregate-signals.py  # finds 5 signals

# Log each signal
for each signal:
    log-signal.py ...
```

**Day 2-14: Resolution**
```bash
# Daily cron checks outcomes
update-signal-outcomes.py
# → 2 markets resolved
# → Updated signal_history
```

**Day 14: Analysis**
```bash
# Generate performance report
signal-performance-report.py

# Results show:
# - Whale clusters: 75% accurate (12/16)
# - Smart money divergence: 40% accurate (4/10)
# - Momentum reversals: 60% accurate (6/10)

# Decision: Focus on whale clusters, drop smart money
```

---

### Future Enhancements

- Auto-log signals from aggregate-signals.py
- Alert on high-confidence failures (learning opportunities)
- Backtest historical signals
- Signal combination strategies (require 2+ signals to trade)
- Market type filtering based on performance
