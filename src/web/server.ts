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
    let arbitrage = [];
    if (arbitrageDetector) {
      arbitrage = await arbitrageDetector.scanAllMarkets();
    }

    // Scan for volume spikes
    const volumeSpikes = await volumeDetector.scanForSpikes();

    // Scan for new markets
    const newMarkets = await newMarketMonitor.scanForNewMarkets();

    // Update cache
    latestData = {
      arbitrage,
      volumeSpikes,
      newMarkets,
      lastUpdate: new Date().toISOString(),
      scanCount: latestData.scanCount + 1,
    };

    console.log(`  ✅ Arbitrage: ${arbitrage.length}, Volume Spikes: ${volumeSpikes.length}, New Markets: ${newMarkets.length}`);
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
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0a0e27;
      color: #e0e0e0;
      padding: 20px;
    }
    .container { max-width: 1400px; margin: 0 auto; }
    h1 {
      font-size: 2.5em;
      margin-bottom: 10px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .status {
      display: flex;
      gap: 20px;
      margin: 20px 0;
      flex-wrap: wrap;
    }
    .stat-card {
      background: #1a1f3a;
      border: 1px solid #2a3154;
      border-radius: 12px;
      padding: 20px;
      flex: 1;
      min-width: 200px;
    }
    .stat-label { font-size: 0.9em; color: #9ca3af; margin-bottom: 8px; }
    .stat-value { font-size: 2em; font-weight: bold; color: #fff; }
    .stat-value.green { color: #10b981; }
    .stat-value.orange { color: #f59e0b; }
    .stat-value.blue { color: #3b82f6; }
    
    .section {
      background: #1a1f3a;
      border: 1px solid #2a3154;
      border-radius: 12px;
      padding: 25px;
      margin: 20px 0;
    }
    .section-title {
      font-size: 1.5em;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 0.75em;
      font-weight: bold;
      background: #374151;
      color: #fff;
    }
    .badge.green { background: #10b981; }
    .badge.orange { background: #f59e0b; }
    .badge.blue { background: #3b82f6; }
    
    .opportunity {
      background: #0f1629;
      border: 1px solid #374151;
      border-radius: 8px;
      padding: 20px;
      margin: 15px 0;
    }
    .opportunity.highlight {
      border-color: #10b981;
      box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
    }
    .opportunity-title {
      font-size: 1.1em;
      font-weight: 600;
      margin-bottom: 15px;
      color: #fff;
    }
    .opportunity-details {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 15px;
    }
    .detail {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .detail-label { font-size: 0.85em; color: #9ca3af; }
    .detail-value { font-size: 1.1em; font-weight: 600; }
    
    .empty {
      text-align: center;
      padding: 40px;
      color: #6b7280;
      font-style: italic;
    }
    
    .last-update {
      margin-top: 30px;
      text-align: center;
      color: #6b7280;
      font-size: 0.9em;
    }
    
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    .loading { animation: pulse 2s infinite; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🦀 Polymarket Trading Signals</h1>
    <p style="color: #9ca3af; margin-bottom: 20px;">Live market analysis • Auto-refreshes every 30s</p>
    
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
          arbList.innerHTML = data.arbitrage.map(opp => \`
            <div class="opportunity highlight">
              <div class="opportunity-title">\${opp.question}</div>
              <div class="opportunity-details">
                <div class="detail">
                  <span class="detail-label">YES Price</span>
                  <span class="detail-value">$\${opp.yes_price.toFixed(4)}</span>
                </div>
                <div class="detail">
                  <span class="detail-label">NO Price</span>
                  <span class="detail-value">$\${opp.no_price.toFixed(4)}</span>
                </div>
                <div class="detail">
                  <span class="detail-label">Combined</span>
                  <span class="detail-value">$\${opp.combined_price.toFixed(4)}</span>
                </div>
                <div class="detail">
                  <span class="detail-label">Profit</span>
                  <span class="detail-value" style="color: #10b981;">
                    $\${opp.profit_per_share.toFixed(4)} (\${opp.profit_percent.toFixed(2)}%)
                  </span>
                </div>
              </div>
            </div>
          \`).join('');
        }
        
        // Update volume spikes
        const volList = document.getElementById('volume-list');
        if (data.volumeSpikes.length === 0) {
          volList.innerHTML = '<div class="empty">No volume spikes detected (building history...)</div>';
        } else {
          volList.innerHTML = data.volumeSpikes.map(spike => \`
            <div class="opportunity">
              <div class="opportunity-title">\${spike.question}</div>
              <div class="opportunity-details">
                <div class="detail">
                  <span class="detail-label">Current 24hr Volume</span>
                  <span class="detail-value">$\${spike.current24hrVolume.toLocaleString()}</span>
                </div>
                <div class="detail">
                  <span class="detail-label">Average Volume</span>
                  <span class="detail-value">$\${spike.avgVolume.toLocaleString()}</span>
                </div>
                <div class="detail">
                  <span class="detail-label">Spike Multiplier</span>
                  <span class="detail-value" style="color: #f59e0b;">\${spike.spikeMultiplier.toFixed(2)}x</span>
                </div>
                <div class="detail">
                  <span class="detail-label">Increase</span>
                  <span class="detail-value">+\${spike.percentIncrease.toFixed(0)}%</span>
                </div>
              </div>
            </div>
          \`).join('');
        }
        
        // Update new markets
        const newList = document.getElementById('new-markets-list');
        if (data.newMarkets.length === 0) {
          newList.innerHTML = '<div class="empty">No new markets in last 24h</div>';
        } else {
          newList.innerHTML = data.newMarkets.map(market => {
            const ageStr = market.ageMinutes < 60 
              ? \`\${market.ageMinutes.toFixed(0)} minutes\`
              : \`\${(market.ageMinutes / 60).toFixed(1)} hours\`;
            const hasArb = (market.priceYes + market.priceNo) < 1.0;
            
            return \`
            <div class="opportunity \${hasArb ? 'highlight' : ''}">
              <div class="opportunity-title">
                \${market.question}
                \${hasArb ? '<span class="badge green">ARBITRAGE</span>' : ''}
              </div>
              <div class="opportunity-details">
                <div class="detail">
                  <span class="detail-label">Age</span>
                  <span class="detail-value">\${ageStr}</span>
                </div>
                <div class="detail">
                  <span class="detail-label">YES Price</span>
                  <span class="detail-value">$\${market.priceYes.toFixed(4)}</span>
                </div>
                <div class="detail">
                  <span class="detail-label">NO Price</span>
                  <span class="detail-value">$\${market.priceNo.toFixed(4)}</span>
                </div>
                <div class="detail">
                  <span class="detail-label">Liquidity</span>
                  <span class="detail-value">$\${market.liquidity.toLocaleString()}</span>
                </div>
              </div>
            </div>
          \`;
          }).join('');
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
