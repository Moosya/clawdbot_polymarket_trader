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
import { getRecentTrades, getWhaleTrades } from '../api/trade_feed';
import { storeTrades, readTrades } from '../utils/trade_database';
import { calculatePositions, calculateWalletPerformance, getTopTraders } from '../strategies/position_tracker';

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
    const volumeSpikes = await volumeDetector.scanForSpikes();

    // Scan for new markets
    const newMarkets = await newMarketMonitor.scanForNewMarkets();

    // Fetch and store recent trades
    const recentTrades = await getRecentTrades(200);
    if (recentTrades.length > 0) {
      storeTrades(recentTrades);
    }

    // Get whale trades (> $1000)
    const whaleTrades = await getWhaleTrades(1000, 100);

    // Calculate positions and top traders
    const allTrades = readTrades();
    const positions = calculatePositions(allTrades);
    const performance = calculateWalletPerformance(allTrades, positions);
    const topTraders = getTopTraders(performance, 5, 20);

    // Update cache
    latestData = {
      arbitrage,
      volumeSpikes,
      newMarkets,
      whaleTrades,
      topTraders,
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
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
    .price { font-family: 'SF Mono', monospace; font-weight: 600; }
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

    <!-- Arbitrage Section -->
    <div class="section">
      <div class="section-title">
        💰 Arbitrage Opportunities
        <span class="badge green" id="arb-badge">0</span>
      </div>
      <div id="arbitrage-list"></div>
    </div>

    <!-- Volume Spikes Section -->
    <div class="section">
      <div class="section-title">
        🔥 Volume Spikes
        <span class="badge orange" id="volume-badge">0</span>
      </div>
      <div id="volume-list"></div>
    </div>

    <!-- New Markets Section -->
    <div class="section">
      <div class="section-title">
        🆕 New Markets
        <span class="badge blue" id="new-badge">0</span>
      </div>
      <div id="new-markets-list"></div>
    </div>

    <!-- Whale Trades Section -->
    <div class="section">
      <div class="section-title">
        🐋 Whale Trades (>$1000)
        <span class="badge" style="background: #8b5cf6; color: white;" id="whale-badge">0</span>
      </div>
      <div id="whale-list"></div>
    </div>

    <!-- Top Traders Section -->
    <div class="section">
      <div class="section-title">
        💎 Top Profitable Traders
        <span class="badge" style="background: #10b981; color: white;" id="traders-badge">0</span>
      </div>
      <div id="traders-list"></div>
    </div>

    <div class="last-update">
      Last updated: <span id="last-update">-</span>
    </div>
  </div>

  <script>
    async function updateData() {
      try {
        const response = await fetch('/api/signals');
        const data = await response.json();
        
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
                    <td class="price">$\${opp.yes_price.toFixed(4)}</td>
                    <td class="price">$\${opp.no_price.toFixed(4)}</td>
                    <td class="price">$\${opp.combined_price.toFixed(4)}</td>
                    <td class="price profit">$\${opp.profit_per_share.toFixed(4)}</td>
                    <td class="profit">\${opp.profit_percent.toFixed(2)}%</td>
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
                  <th>Avg Vol</th>
                  <th>Spike</th>
                  <th>Increase</th>
                  <th>YES</th>
                  <th>NO</th>
                </tr>
              </thead>
              <tbody>
                \${data.volumeSpikes.map(spike => \`
                  <tr>
                    <td class="market-question">\${spike.question}</td>
                    <td class="price">$\${spike.current24hrVolume.toLocaleString()}</td>
                    <td class="price">$\${spike.avgVolume.toLocaleString()}</td>
                    <td class="spike">\${spike.spikeMultiplier.toFixed(2)}x</td>
                    <td class="spike">+\${spike.percentIncrease.toFixed(0)}%</td>
                    <td class="price">$\${spike.priceYes.toFixed(4)}</td>
                    <td class="price">$\${spike.priceNo.toFixed(4)}</td>
                  </tr>
                \`).join('')}
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
                      <td class="price">$\${market.priceYes.toFixed(4)}</td>
                      <td class="price">$\${market.priceNo.toFixed(4)}</td>
                      <td class="price">$\${(market.priceYes + market.priceNo).toFixed(4)}</td>
                      <td class="price">$\${market.liquidity.toLocaleString()}</td>
                      <td class="price">$\${market.volume.toLocaleString()}</td>
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
                      <td class="price">$\${trade.sizeUsd.toLocaleString()}</td>
                      <td class="price">$\${trade.price.toFixed(4)}</td>
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
                      <td class="price" style="color: \${pnlColor}; font-weight: 700;">$\${trader.totalPnL.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</td>
                      <td class="price" style="color: \${roiColor}; font-weight: 700;">\${trader.roi.toFixed(1)}%</td>
                      <td class="price" style="color: \${winRateColor};">\${trader.winRate.toFixed(0)}%</td>
                      <td>\${trader.totalTrades}</td>
                      <td class="price">$\${trader.totalVolume.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</td>
                      <td>\${trader.activePositions}</td>
                    </tr>
                  \`;
                }).join('')}
              </tbody>
            </table>
          \`;
        }
        
        // Update timestamp
        document.getElementById('last-update').textContent = new Date(data.lastUpdate).toLocaleString();
        
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    }
    
    // Initial load
    updateData();
    
    // Auto-refresh every 30 seconds
    setInterval(updateData, 30000);
  </script>
</body>
</html>
  `);
});

// Start server
async function start() {
  console.log('🦀 Polymarket Trading Dashboard\n');
  
  // Initialize
  const hasArbitrageKeys = initArbitrageDetector();
  if (!hasArbitrageKeys) {
    console.log('⚠️  No Polymarket API keys - arbitrage detection disabled');
  }

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
