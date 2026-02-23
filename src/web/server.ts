/**
 * Simple Web Dashboard
 * 
 * Displays trading signals in a clean web interface
 * Auto-refreshes to show live data
 */

import express from 'express';
import * as dotenv from 'dotenv';
import { ArbitrageDetector } from '../strategies/arbitrage_detector';
import { VolumeSpikeDetector } from '../strategies/volume_spike_detector';
import { NewMarketMonitor } from '../strategies/new_market_monitor';
import { PolymarketClient } from '../api/polymarket_client';
import { getRecentTrades as fetchRecentTrades } from '../api/trade_feed';
import { 
  storeTrades, 
  readTrades, 
  getWhaleTrades,
  getDatabaseStats,
  getDatabaseSize,
  migrateFromJSON 
} from '../utils/sqlite_database';
import { calculatePositions, calculateWalletPerformance, getTopTraders } from '../strategies/position_tracker';
import { getTradingDashboardData, getRecentSignals, getOpenPositions, getPortfolioStats } from '../utils/trading_database';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Initialize detectors
let arbitrageDetector: ArbitrageDetector | null = null;
const volumeDetector = new VolumeSpikeDetector(2.0);
const newMarketMonitor = new NewMarketMonitor(24);

// Cache for latest data
let latestData = {
  arbitrage: [] as any[],
  volumeSpikes: [] as any[],
  newMarkets: [] as any[],
  whaleTrades: [] as any[],
  topTraders: [] as any[],
  tradingSignals: { top_signals: [], whale_clusters: [], smart_money_divergence: [], momentum_reversals: [] } as any,
  paperTrading: { positions: [], closedPositions: [], stats: { total_trades: 0, wins: 0, losses: 0, total_pnl: 0, total_value: 1000, roi: 0, win_rate: 0, open_positions: 0, closed_positions: 0 } } as any,
  lastUpdate: new Date().toISOString(),
  scanCount: 0,
};

// Initialize arbitrage detector
function initArbitrageDetector() {
  const apiKey = process.env.CLOB_API_KEY;
  const apiSecret = process.env.CLOB_API_SECRET;
  const apiPassphrase = process.env.CLOB_API_PASSPHRASE;

  if (apiKey && apiSecret && apiPassphrase) {
    const client = new PolymarketClient(apiKey, apiSecret, apiPassphrase);
    arbitrageDetector = new ArbitrageDetector(client, 0.5);
    return true;
  }
  return false;
}

// Scan all signals
async function scanAllSignals() {
  console.log(`[${new Date().toISOString()}] Running scan #${latestData.scanCount + 1}...`);
  
  try {
    // Scan for arbitrage
    let arbitrage: any[] = [];
    if (arbitrageDetector) {
      arbitrage = await arbitrageDetector.scanAllMarkets();
    }

    // Scan for volume spikes
    const allVolumeSpikes = await volumeDetector.scanForSpikes();
    
    // Filter out sports markets (no information edge for whales)
    const sportsPatterns = ['nba', 'nfl', 'nhl', 'mlb', 'super bowl', 'stanley cup', 
                            'world cup', 'premier league', 'champions league',
                            ' vs ', ' vs. ', 'seahawks', 'patriots', 'lakers', 
                            'finals?', 'semifinal', 'championship'];
    
    const volumeSpikes = allVolumeSpikes.filter(spike => {
      const questionLower = spike.question.toLowerCase();
      return !sportsPatterns.some(pattern => questionLower.includes(pattern));
    });

    // Scan for new markets
    const newMarkets = await newMarketMonitor.scanForNewMarkets();

    // Fetch and store recent trades
    const recentTrades = await fetchRecentTrades(200);
    if (recentTrades.length > 0) {
      storeTrades(recentTrades);
    }

    // Get whale trades (>= $2000) from database
    const whaleTrades = getWhaleTrades(2000, 100);

    // Calculate positions and top traders
    const allTrades = readTrades();
    const positions = calculatePositions(allTrades);
    const performance = calculateWalletPerformance(allTrades, positions);
    const topTraders = getTopTraders(performance, 5, 20);


    // Load trading signals from aggregated file (still JSON for now)
    let tradingSignals = { top_signals: [], whale_clusters: [], smart_money_divergence: [], momentum_reversals: [] } as any;
    const fs = require("fs");
    const signalsPath = "/workspace/signals/aggregated-signals.json";
    if (fs.existsSync(signalsPath)) {
      try {
        tradingSignals = JSON.parse(fs.readFileSync(signalsPath, "utf8"));
      } catch (e) { console.error("Error loading signals:", e); }
    }

    // Load paper trading from SQLite database (NEW)
    let paperTrading = { positions: [], closedPositions: [], stats: {} } as any;
    try {
      const tradingData = getTradingDashboardData();
      paperTrading = {
        signals: tradingData.signals,
        positions: tradingData.openPositions,
        closedPositions: tradingData.closedPositions,
        stats: tradingData.stats
      };
    } catch (e) { 
      console.error("Error loading trading database:", e); 
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

    console.log(`  ✅ Arbitrage: ${arbitrage.length}, Volume Spikes: ${volumeSpikes.length}, New Markets: ${newMarkets.length}, Whales: ${whaleTrades.length}, Top Traders: ${topTraders.length}`);
  } catch (error) {
    console.error('Error scanning:', error);
  }
}

// API endpoint for latest data
app.get('/api/signals', (req, res) => {
  res.json(latestData);
});

// NEW: Trading dashboard data (signals + positions + P&L)
app.get('/api/trading', (req, res) => {
  try {
    const data = getTradingDashboardData();
    res.json(data);
  } catch (error) {
    console.error('Error fetching trading data:', error);
    res.status(500).json({ error: 'Failed to fetch trading data' });
  }
});

// NEW: Recent high-confidence signals only
app.get('/api/trading/signals', (req, res) => {
  try {
    const minConfidence = parseInt(req.query.minConfidence as string) || 70;
    const signals = getRecentSignals(minConfidence, 50);
    res.json({ signals });
  } catch (error) {
    console.error('Error fetching signals:', error);
    res.status(500).json({ error: 'Failed to fetch signals' });
  }
});

// NEW: Open paper positions
app.get('/api/trading/positions', (req, res) => {
  try {
    const positions = getOpenPositions();
    res.json({ positions });
  } catch (error) {
    console.error('Error fetching positions:', error);
    res.status(500).json({ error: 'Failed to fetch positions' });
  }
});

// NEW: Portfolio stats
app.get('/api/trading/stats', (req, res) => {
  try {
    const stats = getPortfolioStats();
    res.json(stats);
  } catch (error) {
    console.error('Error fetching portfolio stats:', error);
    res.status(500).json({ error: 'Failed to fetch stats' });
  }
});

// API endpoint for operational stats
app.get('/api/stats', (req, res) => {
  const dbStats = getDatabaseStats();
  const allTrades = readTrades();
  
  const oldestTimestamp = dbStats.oldestTrade ? dbStats.oldestTrade.getTime() / 1000 : 0;
  const newestTimestamp = dbStats.newestTrade ? dbStats.newestTrade.getTime() / 1000 : 0;
  const dataRangeHours = (newestTimestamp - oldestTimestamp) / 3600;
  
  // Market activity
  const marketActivity = new Map<string, number>();
  for (const trade of allTrades) {
    marketActivity.set(trade.marketId, (marketActivity.get(trade.marketId) || 0) + 1);
  }
  const topMarkets = Array.from(marketActivity.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([id, count]) => ({
      marketId: id,
      question: allTrades.find(t => t.marketId === id)?.marketQuestion || 'Unknown',
      tradeCount: count,
    }));
  
  res.json({
    dataCollection: {
      totalTrades: dbStats.totalTrades,
      uniqueWallets: dbStats.uniqueWallets,
      uniqueMarkets: dbStats.uniqueMarkets,
      oldestTrade: dbStats.oldestTrade ? dbStats.oldestTrade.toISOString() : null,
      newestTrade: dbStats.newestTrade ? dbStats.newestTrade.toISOString() : null,
      dataRangeHours: dataRangeHours.toFixed(1),
      tradesPerHour: dataRangeHours > 0 ? (dbStats.totalTrades / dataRangeHours).toFixed(1) : 0,
      fileSizeMB: getDatabaseSize(),
      totalVolume: dbStats.totalVolume,
      minTradeSize: dbStats.minTradeSize,
    },
    scannerHealth: {
      totalScans: latestData.scanCount,
      lastScan: latestData.lastUpdate,
    },
    signalDetection: {
      currentArbitrage: latestData.arbitrage.length,
      currentWhales: latestData.whaleTrades.length,
      currentVolumeSpikes: latestData.volumeSpikes.length,
      profitableTraders: latestData.topTraders.length,
    },
    marketCoverage: {
      activeMarkets: dbStats.uniqueMarkets,
      topMarkets,
    },
  });
});

// Stats page HTML
app.get('/stats', (req, res) => {
  res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🦀 Operational Stats</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
      background: #f8f9fa;
      color: #1a1a1a;
      padding: 12px;
      font-size: 13px;
    }
    .container { max-width: 1400px; margin: 0 auto; }
    h1 {
      font-size: 1.5em;
      margin-bottom: 4px;
      color: #1a1a1a;
      font-weight: 600;
    }
    .subtitle {
      color: #666;
      font-size: 0.85em;
      margin-bottom: 16px;
    }
    .nav {
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid #d1d5db;
    }
    .nav a {
      color: #2563eb;
      text-decoration: none;
      margin-right: 16px;
      font-weight: 500;
    }
    .nav a:hover { text-decoration: underline; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .card {
      background: #fff;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      padding: 12px;
    }
    .card-title {
      font-size: 1em;
      font-weight: 600;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 2px solid #e5e7eb;
    }
    .stat-row {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px solid #f3f4f6;
    }
    .stat-row:last-child { border-bottom: none; }
    .stat-label { color: #6b7280; font-size: 0.9em; }
    .stat-value { font-weight: 600; color: #1a1a1a; }
    .stat-value.green { color: #059669; }
    .stat-value.orange { color: #d97706; }
    .stat-value.blue { color: #2563eb; }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9em;
      margin-top: 8px;
    }
    th {
      text-align: left;
      padding: 6px 8px;
      background: #f3f4f6;
      border-bottom: 2px solid #d1d5db;
      font-weight: 600;
      font-size: 0.75em;
      text-transform: uppercase;
      color: #4b5563;
    }
    td {
      padding: 6px 8px;
      border-bottom: 1px solid #e5e7eb;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🦀 Operational Stats</h1>
    <p class="subtitle">System health and data collection metrics • Auto-refreshes every 30s</p>
    
    <div class="nav">
      <a href="/">← Back to Dashboard</a>
    </div>

    <div class="grid">
      <div class="card">
        <div class="card-title">📊 Data Collection</div>
        <div class="stat-row">
          <span class="stat-label">Total Trades</span>
          <span class="stat-value" id="total-trades">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Unique Wallets</span>
          <span class="stat-value" id="unique-wallets">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Unique Markets</span>
          <span class="stat-value" id="unique-markets">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Data Range</span>
          <span class="stat-value" id="data-range">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Collection Rate</span>
          <span class="stat-value green" id="collection-rate">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Database Size</span>
          <span class="stat-value" id="db-size">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Total Volume</span>
          <span class="stat-value" id="total-volume">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Min Trade Size</span>
          <span class="stat-value" id="min-trade-size">$2,000</span>
        </div>
      </div>

      <div class="card">
        <div class="card-title">🔍 Scanner Health</div>
        <div class="stat-row">
          <span class="stat-label">Total Scans</span>
          <span class="stat-value" id="total-scans">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Last Scan</span>
          <span class="stat-value" id="last-scan">-</span>
        </div>
      </div>

      <div class="card">
        <div class="card-title">💰 Signal Detection</div>
        <div class="stat-row">
          <span class="stat-label">Arbitrage Opportunities</span>
          <span class="stat-value green" id="current-arb">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Whale Trades</span>
          <span class="stat-value orange" id="current-whales">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Volume Spikes</span>
          <span class="stat-value orange" id="current-spikes">-</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Profitable Traders</span>
          <span class="stat-value blue" id="current-traders">-</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">📈 Top 10 Most Active Markets</div>
      <table id="top-markets-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Market</th>
            <th>Trades</th>
          </tr>
        </thead>
        <tbody id="top-markets">
          <tr><td colspan="3" style="text-align: center; color: #9ca3af;">Loading...</td></tr>
        </tbody>
      </table>
    </div>

    <div style="margin-top: 16px; text-align: right; color: #9ca3af; font-size: 0.75em;">
      Last updated: <span id="last-update">-</span>
    </div>
  </div>

  <script>
    function formatVolume(num) {
      if (num >= 1000000) {
        return '$' + (num / 1000000).toFixed(1) + 'M';
      } else if (num >= 1000) {
        return '$' + (num / 1000).toFixed(0) + 'K';
      } else {
        return '$' + num.toFixed(0);
      }
    }

    async function updateStats() {
      try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        // Data collection
        document.getElementById('total-trades').textContent = data.dataCollection.totalTrades.toLocaleString();
        document.getElementById('unique-wallets').textContent = data.dataCollection.uniqueWallets.toLocaleString();
        document.getElementById('unique-markets').textContent = data.dataCollection.uniqueMarkets.toLocaleString();
        document.getElementById('data-range').textContent = data.dataCollection.dataRangeHours + 'h';
        document.getElementById('collection-rate').textContent = data.dataCollection.tradesPerHour + ' trades/hr';
        document.getElementById('db-size').textContent = data.dataCollection.fileSizeMB;
        document.getElementById('total-volume').textContent = formatVolume(data.dataCollection.totalVolume);
        
        // Scanner health
        document.getElementById('total-scans').textContent = data.scannerHealth.totalScans;
        const lastScan = new Date(data.scannerHealth.lastScan);
        const now = new Date();
        const secondsAgo = Math.floor((now - lastScan) / 1000);
        document.getElementById('last-scan').textContent = secondsAgo < 60 
          ? secondsAgo + 's ago'
          : Math.floor(secondsAgo / 60) + 'm ago';
        
        // Signal detection
        document.getElementById('current-arb').textContent = data.signalDetection.currentArbitrage;
        document.getElementById('current-whales').textContent = data.signalDetection.currentWhales;
        document.getElementById('current-spikes').textContent = data.signalDetection.currentVolumeSpikes;
        document.getElementById('current-traders').textContent = data.signalDetection.profitableTraders;
        
        // Top markets
        const topMarketsBody = document.getElementById('top-markets');
        if (data.marketCoverage.topMarkets.length === 0) {
          topMarketsBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #9ca3af;">No data yet</td></tr>';
        } else {
          topMarketsBody.innerHTML = data.marketCoverage.topMarkets.map((market, idx) => \`
            <tr>
              <td style="font-weight: 700;">#\${idx + 1}</td>
              <td>\${market.question}</td>
              <td style="font-weight: 600;">\${market.tradeCount}</td>
            </tr>
          \`).join('');
        }
        
        document.getElementById('last-update').textContent = new Date().toLocaleString();
        
      } catch (error) {
        console.error('Error fetching stats:', error);
      }
    }
    
    // Initial load
    updateStats();
    
    // Auto-refresh every 30 seconds
    setInterval(updateStats, 30000);
  </script>
</body>
</html>
  `);
});

// Main dashboard HTML
app.get('/', (req, res) => {
  res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🦀 Polymarket Trading Signals</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
      background: #f8f9fa;
      color: #1a1a1a;
      padding: 12px;
      font-size: 13px;
    }
    .container { max-width: 100%; margin: 0 auto; }
    h1 {
      font-size: 1.5em;
      margin-bottom: 4px;
      color: #1a1a1a;
      font-weight: 600;
    }
    .subtitle {
      color: #666;
      font-size: 0.85em;
      margin-bottom: 10px;
    }
    .status {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }
    .stat-card {
      background: #fff;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      padding: 8px 12px;
    }
    .stat-label { font-size: 0.75em; color: #666; margin-bottom: 2px; text-transform: uppercase; }
    .stat-value { font-size: 1.5em; font-weight: 700; color: #1a1a1a; }
    .stat-value.green { color: #059669; }
    .stat-value.orange { color: #d97706; }
    .stat-value.blue { color: #2563eb; }
    
    .section {
      background: #fff;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      padding: 10px;
      margin-bottom: 10px;
    }
    .section.collapsible .section-title {
      cursor: pointer;
      user-select: none;
    }
    .section.collapsible .section-title:hover {
      background: #f3f4f6;
      margin: -10px -10px 8px -10px;
      padding: 10px;
      border-radius: 4px 4px 0 0;
    }
    .section.collapsed .section-content {
      display: none;
    }
    .collapse-icon {
      margin-left: auto;
      font-size: 0.8em;
      color: #9ca3af;
      transition: transform 0.2s;
    }
    .section.collapsed .collapse-icon {
      transform: rotate(-90deg);
    }
    .section-title {
      font-size: 1em;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      padding-bottom: 6px;
      border-bottom: 2px solid #e5e7eb;
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 3px;
      font-size: 0.7em;
      font-weight: 700;
      background: #e5e7eb;
      color: #374151;
    }
    .badge.green { background: #d1fae5; color: #065f46; }
    .badge.orange { background: #fed7aa; color: #92400e; }
    .badge.blue { background: #dbeafe; color: #1e40af; }
    
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9em;
    }
    th {
      text-align: left;
      padding: 6px 8px;
      background: #f3f4f6;
      border-bottom: 2px solid #d1d5db;
      font-weight: 600;
      font-size: 0.75em;
      text-transform: uppercase;
      color: #4b5563;
    }
    td {
      padding: 6px 8px;
      border-bottom: 1px solid #e5e7eb;
    }
    tr:hover {
      background: #f9fafb;
    }
    tr.highlight {
      background: #ecfdf5;
      border-left: 3px solid #059669;
    }
    tr.highlight:hover {
      background: #d1fae5;
    }
    
    .market-question {
      font-weight: 500;
      color: #1a1a1a;
      max-width: 500px;
    }
    .price { font-weight: 600; }
    .profit { color: #059669; font-weight: 700; }
    .spike { color: #d97706; font-weight: 700; }
    .age { color: #6b7280; font-size: 0.85em; }
    
    .empty {
      text-align: center;
      padding: 20px;
      color: #9ca3af;
      font-style: italic;
      font-size: 0.9em;
    }
    
    .last-update {
      margin-top: 12px;
      text-align: right;
      color: #9ca3af;
      font-size: 0.75em;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🦀 Polymarket Trading Signals</h1>
    <p class="subtitle">Live market analysis • Auto-refreshes every 30s</p>
    
    <div style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #d1d5db;">
      <a href="/stats" style="color: #2563eb; text-decoration: none; font-weight: 500; font-size: 0.9em;">📊 View Stats</a>
    </div>
    
    <div class="status">
      <div class="stat-card">
        <div class="stat-label">Arbitrage Opportunities</div>
        <div class="stat-value green" id="arbitrage-count">-</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Volume Spikes</div>
        <div class="stat-value orange" id="volume-count">-</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">New Markets</div>
        <div class="stat-value blue" id="new-markets-count">-</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Scans</div>
        <div class="stat-value" id="scan-count">-</div>
      </div>
    </div>

    <!-- Trading Signals Panel -->
    <div class="panel">
      <div class="panel-header">
        <h2>🎯 Trading Signals</h2>
        <span id="signals-badge" class="badge">0</span>
      </div>
      
      <!-- Threshold Controls -->
      <div style="background:#f9fafb;padding:8px 12px;border-radius:6px;margin-bottom:8px;display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div>
          <label style="display:block;margin-bottom:4px;">
            <span style="font-size:0.75rem;font-weight:600;color:#374151;">View ≥ <span id="view-threshold-value" style="color:#3b82f6;">50%</span></span>
          </label>
          <input type="range" id="view-threshold" min="50" max="100" value="50" step="5" 
                 style="width:100%;accent-color:#3b82f6;" 
                 oninput="updateViewThreshold(this.value)">
        </div>
        
        <div>
          <label style="display:block;margin-bottom:4px;">
            <span style="font-size:0.75rem;font-weight:600;color:#374151;">Trade ≥ <span id="trade-threshold-value" style="color:#059669;">60%</span></span>
          </label>
          <input type="range" id="trade-threshold" min="50" max="100" value="60" step="5" 
                 style="width:100%;accent-color:#059669;" 
                 oninput="updateTradeThreshold(this.value)">
        </div>
      </div>
      <div style="font-size: 0.8em; color: #6b7280; margin-bottom: 8px;">
        <span id="signals-description">Showing signals >=50%. Auto-trading signals >=60%.</span>
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
      <div style="font-size: 0.8em; color: #6b7280; margin-bottom: 8px;">
        Simulated positions to validate signal performance.
      </div>
      <div id="paper-trading" class="panel-content">
        <div class="empty">Loading...</div>
      </div>
    </div>

    <!-- Volume Spikes Section -->
    <div class="section collapsible collapsed" id="volume-section">
      <div class="section-title" onclick="toggleSection('volume-section')">
        🔥 Volume Spikes
        <span class="badge orange" id="volume-badge">0</span>
        <span class="collapse-icon">▼</span>
      </div>
      <div class="section-content">
        <div style="font-size: 0.8em; color: #6b7280; margin-bottom: 8px;">
          Markets with unusually high 24hr volume compared to 7-day average (non-sports, ≥$5K avg). High volume = new information entering market.
        </div>
        <div id="volume-list"></div>
      </div>
    </div>

    <!-- Whale Trades Section -->
    <div class="section collapsible collapsed" id="whale-section">
      <div class="section-title" onclick="toggleSection('whale-section')">
        🐋 Whale Trades (>$1000)
        <span class="badge" style="background: #8b5cf6; color: white;" id="whale-badge">0</span>
        <span class="collapse-icon">▼</span>
      </div>
      <div class="section-content">
        <div style="font-size: 0.8em; color: #6b7280; margin-bottom: 8px;">
          Large trades from the last 2 minutes. BUY (green) = bullish, SELL (red) = bearish. Multiple whales buying = strong signal.
        </div>
        <div id="whale-list"></div>
      </div>
    </div>

    <!-- New Markets Section -->
    <div class="section collapsible collapsed" id="newmarkets-section">
      <div class="section-title" onclick="toggleSection('newmarkets-section')">
        🆕 New Markets
        <span class="badge blue" id="new-badge">0</span>
        <span class="collapse-icon">▼</span>
      </div>
      <div class="section-content">
        <div id="new-markets-list"></div>
      </div>
    </div>

    <!-- Top Traders Section -->
    <div class="section collapsible collapsed" id="traders-section">
      <div class="section-title" onclick="toggleSection('traders-section')">
        💎 Top Profitable Traders (Min 5 trades)
        <span class="badge" style="background: #10b981; color: white;" id="traders-badge">0</span>
        <span class="collapse-icon">▼</span>
      </div>
      <div class="section-content">
      <div style="font-size: 0.8em; color: #6b7280; margin-bottom: 8px;">
        Ranked by total P&L (profit/loss). ROI = profit efficiency. Win Rate = % of closed positions that were profitable. Green = profitable, Red = losing.
        <br><strong>Note:</strong> Requires traders to have closed positions (bought AND sold). May take 24-48h to accumulate data.
      </div>
      <div id="traders-list"></div>
      </div>
    </div>

    <!-- Arbitrage Section (Low Priority - Usually Empty) -->
    <div class="section">
      <div class="section-title">
        💰 Arbitrage Opportunities
        <span class="badge green" id="arb-badge">0</span>
      </div>
      <div style="font-size: 0.8em; color: #6b7280; margin-bottom: 8px;">
        Same-market arbitrage (rare). Moved to bottom since rarely triggers.
      </div>
      <div id="arbitrage-list">
        <div class="empty">No arbitrage opportunities found</div>
      </div>
    </div>

    </div>

    <div class="last-update">
      Last updated: <span id="last-update">-</span> | <span style="color: #9ca3af; font-size: 0.9em;">v7d7f4f4</span>
    </div>
  </div>

  <script>
    // Threshold Management
    let viewThreshold = parseInt(localStorage.getItem('viewThreshold')) || 50;
    let tradeThreshold = parseInt(localStorage.getItem('tradeThreshold')) || 60;
    
    // Initialize sliders on page load
    document.addEventListener('DOMContentLoaded', () => {
      document.getElementById('view-threshold').value = viewThreshold;
      document.getElementById('trade-threshold').value = tradeThreshold;
      document.getElementById('view-threshold-value').textContent = viewThreshold + '%';
      document.getElementById('trade-threshold-value').textContent = tradeThreshold + '%';
      updateSignalsDescription();
    });
    
    function updateViewThreshold(value) {
      viewThreshold = parseInt(value);
      localStorage.setItem('viewThreshold', viewThreshold);
      document.getElementById('view-threshold-value').textContent = viewThreshold + '%';
      updateSignalsDescription();
      updateData();  // Refresh data with new threshold
    }
    
    function updateTradeThreshold(value) {
      tradeThreshold = parseInt(value);
      localStorage.setItem('tradeThreshold', tradeThreshold);
      document.getElementById('trade-threshold-value').textContent = tradeThreshold + '%';
      updateSignalsDescription();
      updateData();  // Refresh display to show new trade badges
    }
    
    function updateSignalsDescription() {
      const desc = document.getElementById('signals-description');
      desc.textContent = 'Showing signals >=' + viewThreshold + '%. Auto-trading signals >=' + tradeThreshold + '%.';
    }
    // Toggle collapsible sections
    function toggleSection(sectionId) {
      const section = document.getElementById(sectionId);
      section.classList.toggle('collapsed');
    }
    
    // Format large numbers as K/M
    function formatVolume(num) {
      if (num >= 1000000) {
        return '$' + (num / 1000000).toFixed(1) + 'M';
      } else if (num >= 1000) {
        return '$' + (num / 1000).toFixed(0) + 'K';
      } else {
        return '$' + num.toFixed(0);
      }
    }
    
    async function updateData() {
      try {
        const response = await fetch('/api/signals');
        const data = await response.json();
        
        // Fetch trading signals with dynamic threshold
        const signalsResponse = await fetch('/api/trading/signals?minConfidence=' + viewThreshold);
        const signalsData = await signalsResponse.json();
        data.tradingSignals = { top_signals: signalsData.signals || [] };
        
        // Update counts
        document.getElementById('arbitrage-count').textContent = data.arbitrage.length;
        document.getElementById('volume-count').textContent = data.volumeSpikes.length;
        document.getElementById('new-markets-count').textContent = data.newMarkets.length;
        document.getElementById('scan-count').textContent = data.scanCount;
        
        document.getElementById('arb-badge').textContent = data.arbitrage.length;
        document.getElementById('volume-badge').textContent = data.volumeSpikes.length;
        document.getElementById('new-badge').textContent = data.newMarkets.length;
        
        // Update arbitrage list
        const arbList = document.getElementById('arbitrage-list');
        if (data.arbitrage.length === 0) {
          arbList.innerHTML = '<div class="empty">No arbitrage opportunities found</div>';
        } else {
          arbList.innerHTML = \`
            <table>
              <thead>
                <tr>
                  <th>Market</th>
                  <th>YES</th>
                  <th>NO</th>
                  <th>Combined</th>
                  <th>Profit/Share</th>
                  <th>Profit %</th>
                </tr>
              </thead>
              <tbody>
                \${data.arbitrage.map(opp => \`
                  <tr class="highlight">
                    <td class="market-question">\${opp.question}</td>
                    <td class="price">$\${opp.yes_price.toFixed(2)}</td>
                    <td class="price">$\${opp.no_price.toFixed(2)}</td>
                    <td class="price">$\${opp.combined_price.toFixed(2)}</td>
                    <td class="price profit">$\${opp.profit_per_share.toFixed(2)}</td>
                    <td class="profit">\${opp.profit_percent.toFixed(1)}%</td>
                  </tr>
                \`).join('')}
              </tbody>
            </table>
          \`;
        }
        
        // Update volume spikes
        const volList = document.getElementById('volume-list');
        if (data.volumeSpikes.length === 0) {
          volList.innerHTML = '<div class="empty">No volume spikes detected (building history...)</div>';
        } else {
          volList.innerHTML = \`
            <table>
              <thead>
                <tr>
                  <th>Market</th>
                  <th>24hr Vol</th>
                  <th>Avg Vol (7d)</th>
                  <th>Spike</th>
                  <th>Vol Δ</th>
                  <th>Price</th>
                  <th>24h Δ</th>
                  <th>Spread</th>
                </tr>
              </thead>
              <tbody>
                \${data.volumeSpikes.map(spike => {
                  // Color code price ratio
                  const yesPercent = Math.round(spike.priceYes * 100);
                  const priceColor = yesPercent > 60 ? '#059669' : yesPercent < 40 ? '#dc2626' : '#6b7280';
                  
                  // Color code price change
                  const changeColor = spike.priceChange24h > 0 ? '#059669' : spike.priceChange24h < 0 ? '#dc2626' : '#6b7280';
                  const changeIcon = spike.priceChange24h > 0 ? '↗' : spike.priceChange24h < 0 ? '↘' : '→';
                  
                  return \`
                  <tr>
                    <td class="market-question">\${spike.question}</td>
                    <td class="price">\${formatVolume(spike.current24hrVolume)}</td>
                    <td class="price">\${formatVolume(spike.avgVolume)}</td>
                    <td class="spike">\${spike.spikeMultiplier.toFixed(1)}x</td>
                    <td class="spike">+\${spike.percentIncrease.toFixed(0)}%</td>
                    <td class="price" style="color: \${priceColor}; font-weight: 600;">\${spike.priceRatio}</td>
                    <td style="color: \${changeColor}; font-weight: 600;">\${changeIcon} \${Math.abs(spike.priceChange24h).toFixed(0)}%</td>
                    <td class="price">\${spike.spread.toFixed(2)}</td>
                  </tr>
                \`;
                }).join('')}
              </tbody>
            </table>
          \`;
        }
        
        // Update new markets
        const newList = document.getElementById('new-markets-list');
        if (data.newMarkets.length === 0) {
          newList.innerHTML = '<div class="empty">No new markets in last 24h</div>';
        } else {
          newList.innerHTML = \`
            <table>
              <thead>
                <tr>
                  <th>Market</th>
                  <th>Age</th>
                  <th>YES</th>
                  <th>NO</th>
                  <th>Combined</th>
                  <th>Liquidity</th>
                  <th>Volume</th>
                </tr>
              </thead>
              <tbody>
                \${data.newMarkets.map(market => {
                  const ageStr = market.ageMinutes < 60 
                    ? \`\${market.ageMinutes.toFixed(0)}m\`
                    : \`\${(market.ageMinutes / 60).toFixed(1)}h\`;
                  const hasArb = (market.priceYes + market.priceNo) < 1.0;
                  
                  return \`
                    <tr class="\${hasArb ? 'highlight' : ''}">
                      <td class="market-question">\${market.question}</td>
                      <td class="age">\${ageStr}</td>
                      <td class="price">$\${market.priceYes.toFixed(2)}</td>
                      <td class="price">$\${market.priceNo.toFixed(2)}</td>
                      <td class="price">$\${(market.priceYes + market.priceNo).toFixed(2)}</td>
                      <td class="price">\${formatVolume(market.liquidity)}</td>
                      <td class="price">\${formatVolume(market.volume)}</td>
                    </tr>
                  \`;
                }).join('')}
              </tbody>
            </table>
          \`;
        }
        
        // Update whale trades
        const whaleList = document.getElementById('whale-list');
        document.getElementById('whale-badge').textContent = (data.whaleTrades || []).length;
        if (!data.whaleTrades || data.whaleTrades.length === 0) {
          whaleList.innerHTML = '<div class="empty">No recent whale trades (>$1000)</div>';
        } else {
          whaleList.innerHTML = \`
            <table>
              <thead>
                <tr>
                  <th>Market</th>
                  <th>Side</th>
                  <th>Size</th>
                  <th>Price</th>
                  <th>Wallet</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                \${data.whaleTrades.map(trade => {
                  const walletShort = trade.trader.substring(0, 6) + '...' + trade.trader.substring(trade.trader.length - 4);
                  const timeAgo = Math.floor((Date.now() / 1000 - trade.timestamp) / 60);
                  const timeStr = timeAgo < 60 ? \`\${timeAgo}m ago\` : \`\${Math.floor(timeAgo / 60)}h ago\`;
                  const sideColor = trade.side === 'BUY' ? '#059669' : '#dc2626';
                  
                  return \`
                    <tr>
                      <td class="market-question">\${trade.marketQuestion}</td>
                      <td style="color: \${sideColor}; font-weight: 700;">\${trade.side}</td>
                      <td class="price">\${formatVolume(trade.sizeUsd)}</td>
                      <td class="price">$\${trade.price.toFixed(2)}</td>
                      <td class="age" style="font-family: 'SF Mono', monospace;">\${walletShort}</td>
                      <td class="age">\${timeStr}</td>
                    </tr>
                  \`;
                }).join('')}
              </tbody>
            </table>
          \`;
        }
        
        // Update top traders
        const tradersList = document.getElementById('traders-list');
        document.getElementById('traders-badge').textContent = (data.topTraders || []).length;
        if (!data.topTraders || data.topTraders.length === 0) {
          tradersList.innerHTML = '<div class="empty">Building trader history... (need at least 5 trades per wallet)</div>';
        } else {
          tradersList.innerHTML = \`
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Wallet</th>
                  <th>Total P&L</th>
                  <th>ROI %</th>
                  <th>Win Rate</th>
                  <th>Trades</th>
                  <th>Volume</th>
                  <th>Active</th>
                </tr>
              </thead>
              <tbody>
                \${data.topTraders.map((trader, idx) => {
                  const walletShort = trader.wallet.substring(0, 6) + '...' + trader.wallet.substring(trader.wallet.length - 4);
                  const pnlColor = trader.totalPnL >= 0 ? '#059669' : '#dc2626';
                  const roiColor = trader.roi >= 0 ? '#059669' : '#dc2626';
                  const winRateColor = trader.winRate >= 60 ? '#059669' : trader.winRate >= 40 ? '#d97706' : '#6b7280';
                  
                  return \`
                    <tr class="\${trader.totalPnL > 0 ? 'highlight' : ''}">
                      <td style="font-weight: 700;">#\${idx + 1}</td>
                      <td style="font-family: 'SF Mono', monospace;">\${walletShort}</td>
                      <td class="price" style="color: \${pnlColor}; font-weight: 700;">\${formatVolume(trader.totalPnL)}</td>
                      <td class="price" style="color: \${roiColor}; font-weight: 700;">\${trader.roi.toFixed(0)}%</td>
                      <td class="price" style="color: \${winRateColor};">\${trader.winRate.toFixed(0)}%</td>
                      <td>\${trader.totalTrades}</td>
                      <td class="price">\${formatVolume(trader.totalVolume)}</td>
                      <td>\${trader.activePositions}</td>
                    </tr>
                  \`;
                }).join('')}
              </tbody>
            </table>
          \`;
        }
        

        // Update trading signals
        const signalsList = document.getElementById('signals-list');
        const signals = data.tradingSignals?.top_signals || [];
        document.getElementById('signals-badge').textContent = signals.length;

        if (signals.length === 0) {
          signalsList.innerHTML = '<div class="empty">No signals >=' + viewThreshold + '% detected</div>';
        } else {
          let html = '<table><thead><tr><th>Signal Type</th><th>Market</th><th>Direction</th><th>Confidence</th><th>Price</th><th>Status</th></tr></thead><tbody>';
          signals.slice(0, 20).forEach(sig => {
            const emoji = sig.confidence >= 90 ? '🔥' : sig.confidence >= 80 ? '⚡' : '📊';
            const confColor = sig.confidence >= 90 ? '#059669' : sig.confidence >= 80 ? '#d97706' : '#6b7280';
            const willTrade = sig.confidence >= tradeThreshold;
            const rowStyle = willTrade ? 'background:#f0fdf4;border-left:3px solid #059669;' : '';
            const statusBadge = willTrade 
              ? '<span style="background:#059669;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:600;">WILL TRADE</span>'
              : '<span style="background:#e5e7eb;color:#6b7280;padding:2px 8px;border-radius:4px;font-size:0.75rem;">View Only</span>';
            
            html += \`<tr style="\${rowStyle}" class="\${sig.confidence >= 85 ? 'highlight' : ''}">\`;
            html += '<td style="font-weight:600;">' + emoji + ' ' + sig.type.replace(/_/g, ' ') + '</td>';
            html += '<td class="market-question">' + sig.market_question + '</td>';
            html += '<td style="font-weight:700;color:' + (sig.signal.includes('BUY') ? '#059669' : '#dc2626') + ';">' + sig.signal + '</td>';
            html += '<td style="color:' + confColor + ';font-weight:700;">' + sig.confidence + '%</td>';
            html += '<td class="price">$' + sig.price.toFixed(2) + '</td>';
            html += '<td>' + statusBadge + '</td></tr>';
          });
          signalsList.innerHTML = html + '</tbody></table>';
        }


        // Update paper trading
        const paperTrading = document.getElementById('paper-trading');
        const paperStats = data.paperTrading?.stats || {};
        const positions = data.paperTrading?.positions || [];
        document.getElementById('paper-badge').textContent = positions.length;
        const winRate = paperStats.win_rate || 0;
        const winRateColor = winRate >= 0.6 ? '#059669' : winRate >= 0.4 ? '#d97706' : '#dc2626';
        const combinedPnl = paperStats.combined_pnl || 0;
        const realizedPnl = paperStats.realized_pnl || 0;
        const unrealizedPnl = paperStats.unrealized_pnl || 0;
        const pnlColor = combinedPnl >= 0 ? '#059669' : '#dc2626';
        let pHTML = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1rem;">';
        pHTML += '<div style="text-align:center;"><div style="color:#6b7280;font-size:0.875rem;">Total Trades</div><div style="font-size:1.5rem;font-weight:700;">' + (paperStats.total_trades || 0) + '</div></div>';
        pHTML += '<div style="text-align:center;"><div style="color:#6b7280;font-size:0.875rem;">Win Rate</div><div style="font-size:1.5rem;font-weight:700;color:' + winRateColor + ';">' + (winRate * 100).toFixed(0) + '%</div></div>';
        pHTML += '<div style="text-align:center;"><div style="color:#6b7280;font-size:0.875rem;">Total P&L</div><div style="font-size:1.5rem;font-weight:700;color:' + pnlColor + ';">$' + combinedPnl.toFixed(0) + '</div>';
        pHTML += '<div style="color:#6b7280;font-size:0.75rem;margin-top:0.25rem;">Realized: $' + realizedPnl.toFixed(0) + ' | Unrealized: $' + unrealizedPnl.toFixed(0) + '</div></div></div>';
        if (positions.length > 0) {
          pHTML += '<table><thead><tr><th style="min-width:300px;">Market</th><th title="BUY = betting price will rise, SELL = betting price will fall">Direction</th><th>Size</th><th>Entry</th><th>Current</th><th>P&L</th><th>Days Left</th><th>Why</th></tr></thead><tbody>';
          positions.slice(0, 5).forEach((pos, idx) => {
            const pnl = pos.unrealized_pnl || 0;
            const directionExplain = pos.direction === 'BUY' ? 'Betting price will rise' : 'Betting price will fall';
            
            // Parse reasoning, event_url, and days_until_close from notes
            let reasoning = 'No reasoning available';
            let marketUrl = 'https://polymarket.com/search?q=' + encodeURIComponent(pos.market_question.substring(0, 50));
            let daysLeft = '?';
            let daysLeftColor = '#6b7280';
            let fullTitle = pos.market_question;
            try {
              const notes = typeof pos.notes === 'string' ? JSON.parse(pos.notes) : pos.notes;
              reasoning = notes.reasoning || reasoning;
              marketUrl = notes.event_url || marketUrl;
              fullTitle = notes.full_title || pos.market_question;
              if (notes.days_until_close !== undefined) {
                daysLeft = notes.days_until_close;
                if (daysLeft < 0) {
                  daysLeftColor = '#dc2626'; // Red - already closed!
                  daysLeft = 'CLOSED';
                } else if (daysLeft < 7) {
                  daysLeftColor = '#d97706'; // Orange - closing soon
                } else if (daysLeft > 180) {
                  daysLeftColor = '#6b7280'; // Gray - far future
                  daysLeft = Math.floor(daysLeft / 30) + 'mo';
                }
              }
            } catch (e) {}
            
            pHTML += '<tr>';
            pHTML += '<td class="market-question" title="' + fullTitle + '"><a href="' + marketUrl + '" target="_blank" style="color:#3b82f6;text-decoration:none;">' + fullTitle.substring(0, 80) + (fullTitle.length > 80 ? '...' : '') + '</a></td>';
            pHTML += '<td style="font-weight:700;color:' + (pos.direction === 'BUY' ? '#059669' : '#dc2626') + ';" title="' + directionExplain + '">' + pos.direction + ' ' + pos.outcome + '</td>';
            pHTML += '<td class="price">$' + (pos.size || 50).toFixed(0) + '</td>';
            pHTML += '<td class="price">$' + pos.entry_price.toFixed(2) + '</td>';
            pHTML += '<td class="price">$' + (pos.current_price || pos.entry_price).toFixed(2) + '</td>';
            pHTML += '<td style="color:' + (pnl >= 0 ? '#059669' : '#dc2626') + ';font-weight:700;">$' + pnl.toFixed(0) + '</td>';
            pHTML += '<td style="color:' + daysLeftColor + ';font-weight:700;font-size:0.875rem;">' + daysLeft + '</td>';
            pHTML += '<td><button data-toggle-id="reason-' + idx + '" class="btn-toggle-reason" style="background:#3b82f6;color:white;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:0.75rem;">📊</button></td>';
            pHTML += '</tr>';
            pHTML += '<tr id="reason-' + idx + '" style="display:none;"><td colspan="8" style="background:#f9fafb;padding:0.75rem;font-size:0.875rem;color:#4b5563;border-left:3px solid #3b82f6;">' + reasoning + '</td></tr>';
          });
          pHTML += '</tbody></table>';
        } else { pHTML += '<div class="empty">No open positions</div>'; }
        paperTrading.innerHTML = pHTML;

        // Update timestamp
        document.getElementById('last-update').textContent = new Date(data.lastUpdate).toLocaleString();
        
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    }
    
    // Initial load
    updateData();
    
    // Event delegation for toggle buttons
    document.addEventListener('click', function(e) {
      if (e.target.classList.contains('btn-toggle-reason')) {
        const targetId = e.target.getAttribute('data-toggle-id');
        const el = document.getElementById(targetId);
        if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
      }
    });
    
    // Auto-refresh every 30 seconds
    setInterval(updateData, 30000);
  </script>
</body>
</html>
  `);
});


// Serve calibration mockup
app.get('/calibration-mockup', (req, res) => {
  const path = require('path');
  const mockupPath = path.join(__dirname, '../../calibration-panel-mockup.html');
  res.sendFile(mockupPath);
});
// Start server
async function start() {
  console.log('🦀 Polymarket Trading Dashboard\n');
  
  // Initialize
  const hasArbitrageKeys = initArbitrageDetector();
  if (!hasArbitrageKeys) {
    console.log('⚠️  No Polymarket API keys - arbitrage detection disabled');
  }

  // Migrate from JSON to SQLite if needed
  const path = require('path');
  const jsonFile = path.join(process.cwd(), 'data', 'trades.json');
  migrateFromJSON(jsonFile);

  // Initial scan
  await scanAllSignals();

  // Start periodic scanning (every 2 minutes)
  setInterval(scanAllSignals, 2 * 60 * 1000);

  // Start web server
  app.listen(PORT, () => {
    console.log(`\n✅ Dashboard running at http://localhost:${PORT}`);
    console.log(`📊 Auto-scanning every 2 minutes`);
    console.log(`🌐 Web UI refreshes every 30 seconds\n`);
  });
}

start().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});

