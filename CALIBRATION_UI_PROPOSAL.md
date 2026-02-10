# Superforecaster Calibration UI - Comprehensive Proposal

## Executive Summary

This proposal adds Tetlock-style calibration tracking to the Polymarket dashboard, transforming it from a signal viewer into a learning system that measures and improves forecasting accuracy over time.

**Core Question:** Are our 75% confidence signals actually winning 75% of the time?

---

## 📊 Current State Analysis

### Existing Dashboard Architecture
- **Stack:** Express + TypeScript, SQLite (trading data), JSON (signals)
- **Update Cycle:** 2-min scans, 30s frontend refresh
- **Existing Panels:**
  - 🎯 Trading Signals (top opportunities)
  - 💰 Paper Trading (open positions + P&L)
  - 🔥 Volume Spikes (collapsible)
  - 🐋 Whale Trades (collapsible)
  - 🆕 New Markets (collapsible)
  - 💎 Top Traders (collapsible)
  - 💰 Arbitrage (rarely triggers)

### Design Philosophy
- **Compact & Data-Dense:** Mobile-friendly, minimal scrolling
- **Progressive Disclosure:** High-priority expanded, low-priority collapsed
- **Actionable Over Pretty:** Tables > charts when appropriate
- **No Data Gracefully:** Clear "building history..." messages

### Data Available (from calibration-tracker.py)
```python
# Per forecast:
{
  'signal_type': 'whale_cluster',
  'confidence': 85,
  'forecast_prob': 0.85,
  'actual_outcome': 1,  # 1=win, 0=loss
  'brier_score': 0.0225,
  'pnl': 12.50,
  'roi': 0.25,
  'market': "Will GTA VI release in 2025?",
  'exit_time': '2024-03-15T14:30:00Z'
}

# Aggregated:
- Overall Brier score (0.10 = superforecaster)
- Calibration by bucket (70%, 75%, 80%, etc.)
- Overconfidence patterns by signal type
- Historical trend (improving/worsening)
```

---

## 🎯 A) Information Architecture

### What Data to Show & Where

#### 1. **Hero Stats (Top of Panel)**
```
┌─────────────────────────────────────────────────────┐
│  Brier Score: 0.142   Grade: ⭐ GOOD                │
│  Forecasts: 47   Win Rate: 68%   Avg Confidence: 82%│
└─────────────────────────────────────────────────────┘
```

**Why:** Single-number health check. User should instantly know if we're improving.

**Visual Treatment:**
- Brier score: Large number, color-coded
  - 🟢 Green (<0.15) "Good to Superforecaster"
  - 🟡 Orange (0.15-0.20) "Average, room to improve"
  - 🔴 Red (>0.20) "Below average, investigate"
- Tetlock grade: Emoji + text label
- Small supplementary stats: gray, smaller font

#### 2. **Calibration Curve (Primary Visualization)**

**ASCII Mockup:**
```
Predicted vs Actual Win Rates
────────────────────────────────────────
100% │                            ● (3)
     │                       ●
 80% │              ● (12)  ╱
     │         ● (18)    ╱  ← Perfect calibration line
 60% │    ● (8)       ╱
     │  ╱          ╱
 40% │╱         ╱
     ├─────────────────────────────────
      60%  70%  80%  90% 100%
           PREDICTED WIN RATE

● = Actual outcome
Number in () = trade count
Points on line = well calibrated
Points above = underconfident (could raise threshold)
Points below = OVERCONFIDENT (danger zone!)
```

**Implementation:**
- **Library:** Chart.js or vanilla SVG (dashboard has no existing charts)
- **Chart Type:** Scatter plot with diagonal reference line
- **Data Points:** One per confidence bucket (70%, 75%, 80%, etc.)
- **Size:** 400px wide x 300px tall
- **Colors:**
  - Well-calibrated (±10pp): 🟢 Green
  - Underconfident: 🟡 Orange
  - Overconfident: 🔴 Red (priority to fix!)
- **Interaction:** Hover shows bucket details

**Why This Chart?**
- Core superforecasting metric
- Visual pattern recognition (easier than table)
- Instantly shows if we're overconfident

#### 3. **Calibration Table (Backup/Detail View)**

For users who prefer numbers or mobile users where chart is hard to tap:

```
┌──────────────────────────────────────────────────────────┐
│ Confidence │ Trades │ Predicted │ Actual │ Error │ Brier │
├──────────────────────────────────────────────────────────┤
│ ✅ 70%     │   8    │   70%     │  75%   │  5pp  │ 0.16  │
│ ⚠️  80%     │  18    │   80%     │  67%   │ 13pp  │ 0.18  │ ← Overconfident!
│ ✅ 85%     │  12    │   85%     │  83%   │  2pp  │ 0.12  │
│ ✅ 90%     │   3    │   90%     │ 100%   │ 10pp  │ 0.08  │ ← Small sample
└──────────────────────────────────────────────────────────┘

Legend:
✅ Well-calibrated (< 10pp error)
⚠️  Needs attention (> 10pp error)
```

#### 4. **Signal Type Breakdown**

```
┌──────────────────────────────────────────────────────────┐
│ Signal Type             │ Trades │ Win Rate │ Avg Conf  │
├──────────────────────────────────────────────────────────┤
│ ⚠️  Whale Cluster        │  15    │   60%    │  82%      │ ← Overconfident by 22pp
│ ✅ Smart Money Div      │   8    │   75%    │  78%      │
│ ✅ Momentum Shift       │  12    │   70%    │  75%      │
└──────────────────────────────────────────────────────────┘

⚠️  Recommendation: Lower whale_cluster threshold by ~20pp
```

**Why:** Identifies which signals need recalibration.

#### 5. **Historical Trend (Learning Curve)**

```
Brier Score Over Time (7-day rolling avg)
─────────────────────────────────────
0.25 │●
     │  ●
0.20 │    ●
     │      ●───●  ← Getting better!
0.15 │          ●───●  (goal)
     │
0.10 │─ ─ ─ ─ ─ ─ ─ ─ Superforecaster
     ├──────────────────────────────
      Week 1  2  3  4  5  6  7
```

**Data:** Calculate rolling 7-day Brier average from closed positions
**Chart Type:** Simple line chart
**Why:** Shows if we're learning or stagnating

#### 6. **Recent Post-Mortems (Learning Log)**

```
┌──────────────────────────────────────────────────────────┐
│ 🔴 MISS: GTA VI 2025 Release (85% → Lost)               │
│    • Overconfident on insider rumor (narrative fallacy)  │
│    • Ignored base rate: AAA delays ~60% common           │
│    • Lesson: Discount hype, weight base rates more       │
├──────────────────────────────────────────────────────────┤
│ 🟢 HIT: Fed Rate Cut March (78% → Won)                  │
│    • Good: Combined whale + smart money signals          │
│    • Lucky: Unexpected jobs report helped                │
│    • Lesson: Multi-signal confluence works               │
└──────────────────────────────────────────────────────────┘
```

**Data Source:** Manual entry or auto-generate from notes field
**Storage:** `/workspace/memory/signal-learnings/YYYY-MM.md`
**Why:** Tetlock: "Superforecasters obsessively review their mistakes"

#### 7. **Overconfidence Warnings (Alert Box)**

```
┌──────────────────────────────────────────────────────────┐
│ ⚠️  OVERCONFIDENCE ALERT                                 │
├──────────────────────────────────────────────────────────┤
│ • Whale Cluster signals: 82% confidence but 60% win rate │
│   → Reduce threshold by 20pp or improve signal logic     │
│                                                           │
│ • Last 10 trades: 7 losses at 80%+ confidence            │
│   → Review recent mistakes for pattern                   │
└──────────────────────────────────────────────────────────┘
```

**Trigger:** When any bucket has >15pp calibration error AND >5 trades
**Why:** Proactive correction before bad habits compound

---

## 🎨 B) UI Layout - Specific Design

### Option 1: Single Unified Panel (RECOMMENDED)

```
┌────────────────────────────────────────────────────────────────┐
│ 🎯 Superforecaster Calibration          [Collapse ▼]          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Brier Score: 0.142 ⭐ GOOD                              │  │
│  │ 47 forecasts • 68% win rate • Avg confidence: 82%       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [Calibration Curve]  [Signal Breakdown]                       │
│  (2-column grid on desktop, stacked on mobile)                 │
│                                                                 │
│  📊 Calibration Curve         │  📈 Signal Performance         │
│  ┌────────────────────────┐  │  ┌───────────────────────────┐ │
│  │                        │  │  │ Type      Win Rate  Conf   │ │
│  │   [Scatter plot]       │  │  │ Whale     60%       82% ⚠️  │ │
│  │                        │  │  │ SmartMon  75%       78% ✅  │ │
│  │                        │  │  │ Momentum  70%       75% ✅  │ │
│  └────────────────────────┘  │  └───────────────────────────┘ │
│                               │                                │
│  ⚠️  Overconfidence Alert:    │  📝 Recent Learnings          │
│  Whale signals 22pp too high  │  • GTA VI: Ignored base rate  │
│  → Lower threshold            │  • Fed Cut: Multi-sig worked  │
│                                                                 │
│  🕐 Historical Trend: [Mini sparkline] ↗ Improving!            │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Placement:** Between "Paper Trading" and "Volume Spikes"
**Default State:** Expanded (this is high-value learning data)
**Mobile:** Single column, chart full-width, scroll vertically

### Option 2: Multiple Panels

```
┌─ 📊 Calibration Health ─────────────────┐
│ Brier: 0.142 ⭐ GOOD                    │
│ [Chart] [Stats]                         │
└─────────────────────────────────────────┘

┌─ ⚠️  Overconfidence Warnings ───────────┐
│ • Whale signals: -22pp                  │
│ • Recent losses at high confidence      │
└─────────────────────────────────────────┘

┌─ 📚 Learning Log ───────────────────────┐
│ [Recent post-mortems]                   │
│ [Collapsible, low priority]             │
└─────────────────────────────────────────┘
```

**Pros:** Modular, easier to collapse irrelevant sections
**Cons:** More vertical scrolling, fragments the story

**Verdict:** Option 1 is better for this use case (unified learning narrative)

### Panel Ordering (Top to Bottom)

1. **Header Stats** (scan count, last update)
2. 🎯 **Trading Signals** (actionable opportunities)
3. 💰 **Paper Trading** (active positions + P&L)
4. 🧠 **Superforecaster Calibration** ← NEW (learning/improvement)
5. 🔥 **Volume Spikes** (collapsed - contextual)
6. 🐋 **Whale Trades** (collapsed - contextual)
7. 🆕 **New Markets** (collapsed - low priority)
8. 💎 **Top Traders** (collapsed - informational)
9. 💰 **Arbitrage** (rarely triggers)

**Rationale:** Calibration is more important than raw signals because it tells you if your signals are good!

---

## 📐 C) Technical Implementation

### Data Flow

#### 1. **Backend: Add Calibration Data to API**

**New endpoint: `/api/calibration`**

```typescript
// In server.ts
app.get('/api/calibration', (req, res) => {
  try {
    // Execute Python calibration script
    const { execSync } = require('child_process');
    const output = execSync('python3 /workspace/scripts/calibration-tracker.py --json', {
      encoding: 'utf-8',
      cwd: '/workspace'
    });
    
    const data = JSON.parse(output);
    res.json(data);
  } catch (error) {
    console.error('Error fetching calibration:', error);
    res.status(500).json({ error: 'Calibration calculation failed' });
  }
});
```

**Modify calibration-tracker.py to output JSON:**

```python
def get_calibration_json():
    forecasts = get_calibration_data()
    
    if not forecasts:
        return {
            'status': 'no_data',
            'message': 'Need at least 5 closed positions to calculate calibration'
        }
    
    calibration = analyze_calibration(forecasts)
    brier = calculate_overall_brier_score(forecasts)
    grade = tetlock_superforecaster_grade(brier)
    issues = identify_overconfidence_patterns(forecasts)
    
    return {
        'status': 'ok',
        'overall': {
            'brier_score': brier,
            'grade': grade,
            'total_forecasts': len(forecasts),
            'win_rate': sum(f['actual_outcome'] for f in forecasts) / len(forecasts),
            'avg_confidence': sum(f['confidence'] for f in forecasts) / len(forecasts)
        },
        'calibration': calibration,  # By confidence bucket
        'issues': issues,  # Overconfidence warnings
        'recent_forecasts': forecasts[-10:],  # Last 10 for post-mortems
        'historical': calculate_historical_trend(forecasts)
    }

if __name__ == '__main__':
    if '--json' in sys.argv:
        print(json.dumps(get_calibration_json()))
    else:
        format_calibration_report()
```

#### 2. **Update Frequency**

**Option A: On-Demand (RECOMMENDED)**
- Calibration only updates when new positions close
- No need to recalculate every 2 minutes
- Frontend requests `/api/calibration` on page load
- Cache result for 5 minutes

**Option B: Include in scanAllSignals()**
- Calculate calibration every scan
- Pros: Simpler architecture
- Cons: Wastes CPU if no new closures

**Verdict:** Option A (on-demand) is cleaner

#### 3. **Data Persistence**

**Current:**
- Signals: JSON (`/workspace/signals/aggregated-signals.json`)
- Positions: SQLite (`/workspace/polymarket_runtime/data/trading.db`)

**New:**
- Calibration: Calculated on-the-fly from SQLite (no new storage needed!)
- Historical trend: Store rolling averages in SQLite

**Add table:**
```sql
CREATE TABLE calibration_history (
  date TEXT PRIMARY KEY,
  brier_score REAL,
  total_forecasts INTEGER,
  win_rate REAL
);
```

**Update daily via cron:**
```bash
# /workspace/scripts/daily-calibration-snapshot.sh
python3 /workspace/scripts/calibration-tracker.py --save-snapshot
```

#### 4. **Frontend Updates**

**Add to updateData() in dashboard:**

```javascript
// Fetch calibration data (separate call, cached)
const calibrationResponse = await fetch('/api/calibration');
const calibration = await calibrationResponse.json();

// Update calibration panel
updateCalibrationPanel(calibration);
```

**Render function:**

```javascript
function updateCalibrationPanel(data) {
  const panel = document.getElementById('calibration-panel');
  
  if (data.status === 'no_data') {
    panel.innerHTML = `
      <div class="empty">
        <p>Building calibration history...</p>
        <p style="color: #6b7280; font-size: 0.9em; margin-top: 8px;">
          Need at least 5 closed positions to measure accuracy.
          Check back after a few markets resolve!
        </p>
      </div>
    `;
    return;
  }
  
  // Render hero stats
  const gradeColor = data.overall.brier_score < 0.15 ? '#059669' : 
                     data.overall.brier_score < 0.20 ? '#d97706' : '#dc2626';
  
  let html = `
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem;">
      <div style="text-align: center;">
        <div style="color: #6b7280; font-size: 0.875rem;">Brier Score</div>
        <div style="font-size: 1.75rem; font-weight: 700; color: ${gradeColor};">
          ${data.overall.brier_score.toFixed(3)}
        </div>
        <div style="color: ${gradeColor}; font-size: 0.875rem; font-weight: 600;">
          ${data.overall.grade}
        </div>
      </div>
      <div style="text-align: center;">
        <div style="color: #6b7280; font-size: 0.875rem;">Forecasts</div>
        <div style="font-size: 1.75rem; font-weight: 700;">${data.overall.total_forecasts}</div>
      </div>
      <div style="text-align: center;">
        <div style="color: #6b7280; font-size: 0.875rem;">Win Rate</div>
        <div style="font-size: 1.75rem; font-weight: 700;">
          ${(data.overall.win_rate * 100).toFixed(0)}%
        </div>
      </div>
      <div style="text-align: center;">
        <div style="color: #6b7280; font-size: 0.875rem;">Avg Confidence</div>
        <div style="font-size: 1.75rem; font-weight: 700;">
          ${data.overall.avg_confidence.toFixed(0)}%
        </div>
      </div>
    </div>
  `;
  
  // Render calibration table (chart comes in v2)
  html += renderCalibrationTable(data.calibration);
  
  // Render signal breakdown
  html += renderSignalBreakdown(data.issues);
  
  // Render overconfidence warnings
  if (data.issues.length > 0) {
    html += `<div class="alert warning" style="margin-top: 1rem; padding: 1rem; background: #fed7aa; border-left: 4px solid #d97706; border-radius: 4px;">
      <strong>⚠️  Overconfidence Alert</strong><br>`;
    data.issues.forEach(issue => {
      html += `<p style="margin: 0.5rem 0;">• ${issue.signal_type}: Predicting ${issue.avg_confidence.toFixed(0)}% but winning ${issue.actual_win_rate.toFixed(0)}%<br>
      <span style="color: #92400e;">→ ${issue.recommendation}</span></p>`;
    });
    html += `</div>`;
  }
  
  panel.innerHTML = html;
}
```

### Chart Library Decision

**Option 1: Chart.js**
- Pros: Popular, well-documented, handles responsive
- Cons: 200KB bundle size, overkill for one chart
- Install: `npm install chart.js`

**Option 2: Vanilla SVG**
- Pros: No dependencies, <2KB code, full control
- Cons: More manual work
- Example: `/workspace/projects/polymarket/src/web/calibration-chart.ts`

**Option 3: ASCII/Text Fallback (MVP)**
- Pros: Ship immediately, accessible
- Cons: Less visual
- Example: Use Unicode box-drawing characters

**Verdict:** Start with **Option 3 (table + sparklines)** for MVP, add Chart.js in v2

---

## 🚀 D) Priority Recommendations

### **Phase 1: MVP (Ship This Week)**

**Goal:** Surface calibration data, identify overconfidence

**Tasks:**
1. ✅ Modify `calibration-tracker.py` to output JSON (`--json` flag)
2. ✅ Add `/api/calibration` endpoint to server.ts
3. ✅ Add "Superforecaster Calibration" panel to dashboard HTML
4. ✅ Render hero stats (Brier, grade, forecast count)
5. ✅ Render calibration table (text-based, no chart)
6. ✅ Render overconfidence warnings (alert box)
7. ✅ Handle "no data yet" state gracefully

**What users get:**
- Clear answer to "Are we any good?"
- Specific recommendations (e.g., "Lower whale_cluster threshold by 20pp")
- Historical context (improving/worsening)

**Effort:** ~4 hours
**Impact:** HIGH (enables data-driven signal tuning)

### **Phase 2: Visual Enhancements (Next Sprint)**

**Goal:** Make calibration intuitive at a glance

**Tasks:**
1. ✅ Add Chart.js dependency
2. ✅ Implement calibration curve (scatter plot)
3. ✅ Implement historical trend line chart
4. ✅ Add hover tooltips to charts
5. ✅ Color-code signal breakdown table

**What users get:**
- Visual pattern recognition (easier to spot overconfidence)
- Trend awareness (are we learning?)

**Effort:** ~3 hours
**Impact:** MEDIUM (makes existing data prettier)

### **Phase 3: Learning System (Future)**

**Goal:** Close the feedback loop

**Tasks:**
1. ✅ Add "Post-Mortem" UI for manual notes on closed positions
2. ✅ Auto-generate learning insights from patterns
3. ✅ Daily calibration snapshot cron job
4. ✅ Email/Telegram alerts for calibration drift
5. ✅ A/B test signal variants (e.g., whale_cluster v1 vs v2)

**What users get:**
- Structured learning from mistakes
- Proactive alerts when calibration degrades
- Experimentation framework

**Effort:** ~8 hours
**Impact:** HIGH (long-term compounding improvement)

---

## 🎨 Quick Win: Immediate Ship

**Minimal Implementation (1 hour):**

Add to existing dashboard, below Paper Trading:

```html
<div class="section">
  <div class="section-title">
    🧠 Calibration Check
    <span class="badge" id="cal-badge">?</span>
  </div>
  <div id="calibration-simple"></div>
</div>
```

```javascript
// In updateData()
fetch('/api/calibration')
  .then(r => r.json())
  .then(cal => {
    if (cal.status === 'no_data') {
      document.getElementById('calibration-simple').innerHTML = 
        '<div class="empty">Building history... (need 5+ closed positions)</div>';
      return;
    }
    
    const gradeEmoji = cal.overall.brier_score < 0.15 ? '🟢' : 
                       cal.overall.brier_score < 0.20 ? '🟡' : '🔴';
    
    document.getElementById('calibration-simple').innerHTML = `
      <p><strong>Brier Score:</strong> ${gradeEmoji} ${cal.overall.brier_score.toFixed(3)} (${cal.overall.grade})</p>
      <p><strong>Win Rate:</strong> ${(cal.overall.win_rate * 100).toFixed(0)}% 
         (predicted ${cal.overall.avg_confidence.toFixed(0)}%)</p>
      ${cal.issues.length > 0 ? `
        <p style="color: #d97706; margin-top: 8px;"><strong>⚠️  Warning:</strong> 
        ${cal.issues[0].signal_type} is overconfident by ${cal.issues[0].gap.toFixed(0)}pp</p>
      ` : ''}
    `;
    
    document.getElementById('cal-badge').textContent = cal.overall.total_forecasts;
  });
```

**Result:** Users see calibration health in <1 minute of dev work.

---

## 📱 Mobile Responsiveness

### Breakpoints

- **Desktop (>768px):** 2-column grid, full charts, expanded by default
- **Mobile (<768px):** Single column, smaller charts, collapsed by default

### Specific Adjustments

```css
@media (max-width: 768px) {
  .calibration-grid {
    grid-template-columns: 1fr !important;
  }
  
  .calibration-chart {
    height: 200px !important; /* Shorter on mobile */
  }
  
  .hero-stats {
    grid-template-columns: repeat(2, 1fr) !important; /* 2x2 instead of 4x1 */
  }
  
  .section.calibration {
    /* Collapse by default on mobile to reduce scrolling */
  }
}
```

### Table Overflow

```css
.calibration-table {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.calibration-table table {
  min-width: 500px; /* Prevent column crush */
}
```

---

## 🎨 ASCII Mockup: Full Panel

```
┌────────────────────────────────────────────────────────────────┐
│ 🧠 Superforecaster Calibration                      [Collapse ▼]│
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Brier Score    Forecasts    Win Rate    Avg Confidence   │  │
│  │ 0.142 ⭐ GOOD      47         68%            82%          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  📊 Are we well-calibrated?                                     │
│  ───────────────────────────────────────────────────────────   │
│                                                                 │
│  When we say 75%, do we actually win 75% of the time?          │
│                                                                 │
│  Confidence │ Trades │ Predicted │ Actual │ Error │ Status    │
│  ──────────────────────────────────────────────────────────   │
│  70%        │   8    │   70%     │  75%   │  5pp  │ ✅ Good   │
│  80%        │  18    │   80%     │  67%   │ 13pp  │ ⚠️  Over  │
│  85%        │  12    │   85%     │  83%   │  2pp  │ ✅ Good   │
│  90%        │   3    │   90%     │ 100%   │ 10pp  │ ✅ Small  │
│                                                                 │
│  ⚠️  OVERCONFIDENCE ALERT                                       │
│  ──────────────────────────────────────────────────────────   │
│  • Whale Cluster: Predicting 82% but winning only 60%          │
│    → Overconfident by 22 percentage points                     │
│    → Recommendation: Lower threshold to 60% or improve signal  │
│                                                                 │
│  📈 Signal Type Breakdown                                       │
│  ──────────────────────────────────────────────────────────   │
│  Type                 │ Trades │ Win Rate │ Confidence │ Gap   │
│  ─────────────────────────────────────────────────────────────│
│  ⚠️  Whale Cluster     │  15    │   60%    │    82%     │ -22pp│
│  ✅ Smart Money Div   │   8    │   75%    │    78%     │  -3pp│
│  ✅ Momentum Shift    │  12    │   70%    │    75%     │  -5pp│
│                                                                 │
│  📚 Recent Learnings                                            │
│  ──────────────────────────────────────────────────────────   │
│  🔴 MISS: GTA VI 2025 (85% → Lost)                             │
│     • Overweighted insider rumor (narrative fallacy)           │
│     • Ignored base rate: AAA delays are common (~60%)          │
│     • Lesson: Always start with outside view                   │
│                                                                 │
│  🟢 HIT: Fed Rate Cut (78% → Won)                              │
│     • Combined whale + smart money signals (ensemble)          │
│     • Lesson: Multi-signal confluence increases accuracy       │
│                                                                 │
│  🕐 Improving? [▁▂▃▅▆] Last 7 days: Brier trending down        │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 🎬 Implementation Roadmap

### Week 1: Foundation
- [ ] Modify calibration-tracker.py for JSON output
- [ ] Add `/api/calibration` endpoint
- [ ] Add empty panel to dashboard HTML
- [ ] Implement "no data" state

### Week 2: MVP Launch
- [ ] Hero stats (Brier, grade, counts)
- [ ] Calibration table (text-based)
- [ ] Overconfidence alerts
- [ ] Signal breakdown table
- [ ] Deploy + monitor

### Week 3: Polish
- [ ] Add Chart.js
- [ ] Calibration curve scatter plot
- [ ] Historical trend line
- [ ] Mobile responsive tweaks

### Week 4: Learning Loop
- [ ] Post-mortem UI
- [ ] Daily snapshot cron
- [ ] Telegram alerts for calibration drift
- [ ] Documentation updates

---

## 🔍 Success Metrics

### Leading Indicators (Week 1)
- ✅ Panel ships without errors
- ✅ "No data" state displays correctly
- ✅ Calibration calculates accurately (spot-check vs manual)

### Lagging Indicators (Month 1)
- 📈 Brier score improves by >0.05 (e.g., 0.20 → 0.15)
- 📊 Calibration error drops below 10pp for all buckets
- 🎯 At least 1 signal threshold adjusted based on data
- 📝 Post-mortems written for 80%+ of closed positions

### North Star
- 🏆 Achieve Superforecaster grade (Brier < 0.10)

---

## 💡 Additional Considerations

### Privacy
- No PII in calibration data (only aggregates)
- Market questions shown but no wallet addresses

### Performance
- Calibration calculation: ~50ms for 100 forecasts (negligible)
- Cache API response for 5 minutes
- Dashboard load time impact: <100ms

### Accessibility
- Color-blind friendly: Use shapes + colors (✅ ⚠️ ❌)
- Screen readers: Proper ARIA labels on charts
- Keyboard navigation: All interactive elements focusable

### Error Handling
- Python script fails → Show cached data + timestamp
- No closed positions → Clear "building history" message
- Malformed data → Log error, render empty state

---

## 📚 Documentation Needs

Update these files after implementation:

1. **README.md** - Add calibration section
2. **SUPERFORECASTING.md** - Link to dashboard
3. **DASHBOARD_UPDATE_PLAN.md** - Document calibration panel
4. **AGENTS.md** - Add calibration review to heartbeat checklist

---

## 🎯 Conclusion

**Bottom Line:** Add a single, information-dense panel that answers "Are we getting better?" and surfaces specific improvements.

**Core Philosophy:** 
> "The goal is not to eliminate uncertainty. The goal is to be less wrong over time."

**MVP ships in <4 hours. Full implementation in 2 weeks. Compound learning over months.**

This isn't just a dashboard update—it's a learning system that makes us smarter with every closed position.

---

**Questions? Feedback?**
Ping @clawdbot with calibration thoughts 🦀
