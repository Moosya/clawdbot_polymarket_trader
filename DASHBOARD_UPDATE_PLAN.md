# Dashboard Update Plan - Trading Signals Integration

## Changes Needed

### 1. Update latestData Structure (Line ~36)

**Current:**
```typescript
let latestData = {
  arbitrage: [] as any[],
  volumeSpikes: [] as any[],
  newMarkets: [] as any[],
  whaleTrades: [] as any[],
  topTraders: [] as any[],
  lastUpdate: new Date().toISOString(),
  scanCount: 0,
};
```

**Add:**
```typescript
let latestData = {
  arbitrage: [] as any[],
  volumeSpikes: [] as any[],
  newMarkets: [] as any[],
  whaleTrades: [] as any[],
  topTraders: [] as any[],
  tradingSignals: { top_signals: [], whale_clusters: [], smart_money_divergence: [], momentum_reversals: [] },
  paperTrading: { positions: [], closed_positions: [], stats: { total_trades: 0, wins: 0, losses: 0, total_pnl: 0, roi: 0 } },
  lastUpdate: new Date().toISOString(),
  scanCount: 0,
};
```

### 2. Update scanAllSignals Function (Line ~85-105)

Add after the topTraders calculation:

```typescript
// Load trading signals
let tradingSignals = { top_signals: [], whale_clusters: [], smart_money_divergence: [], momentum_reversals: [] };
const fs = require('fs');
const signalsPath = '/workspace/signals/aggregated-signals.json';
if (fs.existsSync(signalsPath)) {
  try {
    tradingSignals = JSON.parse(fs.readFileSync(signalsPath, 'utf8'));
  } catch (e) {
    console.error('Error loading signals:', e);
  }
}

// Load paper trading stats  
let paperTrading = { positions: [], closed_positions: [], stats: { total_trades: 0, wins: 0, losses: 0, total_pnl: 0, roi: 0 } };
const positionsPath = '/workspace/signals/paper-positions.json';
if (fs.existsSync(positionsPath)) {
  try {
    paperTrading = JSON.parse(fs.readFileSync(positionsPath, 'utf8'));
  } catch (e) {
    console.error('Error loading paper trading:', e);
  }
}

// Update cache
latestData = {
  arbitrage,
  volumeSpikes,
  newMarkets,
  whaleTrades,
  topTraders,
  tradingSignals,
  paperTrading,
  lastUpdate: new Date().toISOString(),
  scanCount: latestData.scanCount + 1,
};
```

### 3. Add New HTML Sections (After existing panels in the HTML, around line 500)

Add these new panel sections before the closing `</div><!-- container -->`:

```html
<!-- Trading Signals Panel -->
<div class="panel">
  <div class="panel-header">
    <h2>🎯 Trading Signals</h2>
    <span id="signals-badge" class="badge">0</span>
  </div>
  <div id="signals-list" class="panel-content">
    <div class="empty">Loading...</div>
  </div>
</div>

<!-- Paper Trading Panel -->
<div class="panel">
  <div class="panel-header">
    <h2>💰 Paper Trading</h2>
    <span id="paper-badge" class="badge">0</span>
  </div>
  <div id="paper-trading" class="panel-content">
    <div class="empty">Loading...</div>
  </div>
</div>
```

### 4. Add JavaScript to Update New Panels (in updateData function, around line 670)

Add this after the existing update code:

```javascript
// Update trading signals
const signalsList = document.getElementById('signals-list');
const signals = data.tradingSignals?.top_signals || [];
document.getElementById('signals-badge').textContent = signals.length;

if (signals.length === 0) {
  signalsList.innerHTML = '<div class="empty">No high-confidence signals detected</div>';
} else {
  signalsList.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Signal Type</th>
          <th>Market</th>
          <th>Direction</th>
          <th>Confidence</th>
          <th>Price</th>
        </tr>
      </thead>
      <tbody>
        ${signals.slice(0, 10).map(sig => {
          const emoji = sig.confidence >= 90 ? '🔥' : sig.confidence >= 80 ? '⚡' : '📊';
          const confColor = sig.confidence >= 90 ? '#059669' : sig.confidence >= 80 ? '#d97706' : '#6b7280';
          const typeLabel = sig.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          
          return `
            <tr class="${sig.confidence >= 85 ? 'highlight' : ''}">
              <td style="font-weight: 600;">${emoji} ${typeLabel}</td>
              <td class="market-question">${sig.market_question}</td>
              <td style="font-weight: 700; color: ${sig.signal.includes('BUY') ? '#059669' : '#dc2626'};">${sig.signal}</td>
              <td style="color: ${confColor}; font-weight: 700;">${sig.confidence}%</td>
              <td class="price">$${sig.price.toFixed(2)}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

// Update paper trading
const paperTrading = document.getElementById('paper-trading');
const paperStats = data.paperTrading?.stats || {};
const positions = data.paperTrading?.positions || [];
document.getElementById('paper-badge').textContent = positions.length;

const winRate = paperStats.win_rate || 0;
const winRateColor = winRate >= 0.6 ? '#059669' : winRate >= 0.4 ? '#d97706' : '#dc2626';
const pnlColor = (paperStats.total_pnl || 0) >= 0 ? '#059669' : '#dc2626';

paperTrading.innerHTML = `
  <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem;">
    <div style="text-align: center;">
      <div style="color: #6b7280; font-size: 0.875rem;">Total Trades</div>
      <div style="font-size: 1.5rem; font-weight: 700;">${paperStats.total_trades || 0}</div>
    </div>
    <div style="text-align: center;">
      <div style="color: #6b7280; font-size: 0.875rem;">Win Rate</div>
      <div style="font-size: 1.5rem; font-weight: 700; color: ${winRateColor};">${(winRate * 100).toFixed(0)}%</div>
    </div>
    <div style="text-align: center;">
      <div style="color: #6b7280; font-size: 0.875rem;">Total P&L</div>
      <div style="font-size: 1.5rem; font-weight: 700; color: ${pnlColor};">$${(paperStats.total_pnl || 0).toFixed(0)}</div>
    </div>
  </div>
  ${positions.length > 0 ? `
    <table>
      <thead>
        <tr>
          <th>Market</th>
          <th>Direction</th>
          <th>Entry</th>
          <th>Current</th>
          <th>P&L</th>
        </tr>
      </thead>
      <tbody>
        ${positions.slice(0, 5).map(pos => {
          const pnl = pos.unrealized_pnl || 0;
          const pnlColor = pnl >= 0 ? '#059669' : '#dc2626';
          
          return `
            <tr>
              <td class="market-question">${pos.market_question.substring(0, 60)}...</td>
              <td style="font-weight: 700; color: ${pos.direction === 'BUY' ? '#059669' : '#dc2626'};">${pos.direction} ${pos.outcome}</td>
              <td class="price">$${pos.entry_price.toFixed(2)}</td>
              <td class="price">$${(pos.current_price || pos.entry_price).toFixed(2)}</td>
              <td style="color: ${pnlColor}; font-weight: 700;">$${pnl.toFixed(0)}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  ` : '<div class="empty">No open positions</div>'}
`;
```

## Deployment Steps

1. Backup current server.ts (done ✅)
2. Apply the 4 changes above
3. Rebuild the TypeScript: `cd /workspace/projects/polymarket && npm run build`
4. Restart PM2: `pm2 restart polymarket-dashboard`
5. Visit dashboard to verify new panels appear

## Testing

- Visit `http://localhost:3000` and verify two new panels appear at the bottom
- Check that signals show up when available in `/workspace/signals/aggregated-signals.json`
- Verify paper trading stats display correctly

## Rollback

If something breaks:
```bash
cd /workspace/projects/polymarket/src/web
mv server.ts.backup server.ts
npm run build
pm2 restart polymarket-dashboard
```
