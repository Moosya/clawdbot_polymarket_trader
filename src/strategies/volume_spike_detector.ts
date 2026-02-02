/**
 * Volume Spike Detector
 * 
 * Monitors 24hr volume changes across markets
 * Alerts when volume spikes significantly above historical average
 * 
 * Signal: High volume = new information entering the market
 * Often precedes price movements or indicates mispricing
 */

import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';

interface VolumeData {
  marketId: string;
  question: string;
  volume24hr: number;
  volumeNum: number;
  timestamp: number;
}

interface VolumeHistory {
  [marketId: string]: VolumeData[];
}

interface VolumeSpike {
  marketId: string;
  question: string;
  current24hrVolume: number;
  avgVolume: number;
  spikeMultiplier: number;
  percentIncrease: number;
  priceYes: number;
  priceNo: number;
  priceRatio: string; // e.g., "75/25"
  priceChange24h: number; // % change
  spread: number;
  liquidity: number;
  timestamp: number;
}

export class VolumeSpikeDetector {
  private historyFile: string;
  private history: VolumeHistory = {};
  private minSpikeMultiplier: number;
  private apiUrl = 'https://gamma-api.polymarket.com';

  constructor(minSpikeMultiplier: number = 2.0, historyFile?: string) {
    this.minSpikeMultiplier = minSpikeMultiplier;
    this.historyFile = historyFile || path.join(process.cwd(), 'volume_history.json');
    this.loadHistory();
  }

  /**
   * Load volume history from disk
   */
  private loadHistory(): void {
    try {
      if (fs.existsSync(this.historyFile)) {
        const data = fs.readFileSync(this.historyFile, 'utf-8');
        this.history = JSON.parse(data);
        console.log(`📊 Loaded volume history for ${Object.keys(this.history).length} markets`);
      }
    } catch (error) {
      console.log('📊 Starting fresh volume history');
      this.history = {};
    }
  }

  /**
   * Save volume history to disk
   */
  private saveHistory(): void {
    try {
      fs.writeFileSync(this.historyFile, JSON.stringify(this.history, null, 2));
    } catch (error) {
      console.error('Error saving volume history:', error);
    }
  }

  /**
   * Record current volume for a market
   */
  private recordVolume(marketId: string, question: string, volume24hr: number, volumeNum: number): void {
    if (!this.history[marketId]) {
      this.history[marketId] = [];
    }

    this.history[marketId].push({
      marketId,
      question,
      volume24hr,
      volumeNum,
      timestamp: Date.now(),
    });

    // Keep last 30 data points per market (enough for ~7 days if scanning every 6 hours)
    if (this.history[marketId].length > 30) {
      this.history[marketId] = this.history[marketId].slice(-30);
    }
  }

  /**
   * Calculate average volume for a market
   */
  private getAverageVolume(marketId: string): number {
    const data = this.history[marketId];
    if (!data || data.length < 2) {
      return 0; // Not enough history
    }

    const sum = data.reduce((acc, d) => acc + d.volume24hr, 0);
    return sum / data.length;
  }

  /**
   * Scan all markets for volume spikes
   */
  async scanForSpikes(): Promise<VolumeSpike[]> {
    try {
      // Fetch active markets
      const response = await axios.get(`${this.apiUrl}/markets`, {
        params: {
          limit: 100,
          active: true,
          closed: false,
        },
      });

      const markets = response.data;
      const spikes: VolumeSpike[] = [];

      for (const market of markets) {
        const marketId = market.condition_id;
        const volume24hr = parseFloat(market.volume24hr) || 0;
        const volume1wk = parseFloat(market.volume1wk) || 0;

        // Skip if no significant volume (minimum $1K in 24hr)
        if (volume24hr < 1000) {
          continue;
        }

        // Calculate average from 1-week volume (more reliable than our stored history)
        const avgVolume = volume1wk / 7;

        // Skip if no historical data
        if (avgVolume === 0) {
          continue;
        }

        // Check for spike
        const spikeMultiplier = volume24hr / avgVolume;
        const percentIncrease = ((volume24hr - avgVolume) / avgVolume) * 100;

        if (spikeMultiplier >= this.minSpikeMultiplier) {
          // Parse outcomePrices (may be JSON string or array)
          let priceYes = 0;
          let priceNo = 0;
          if (market.outcomePrices) {
            try {
              const prices = typeof market.outcomePrices === 'string' 
                ? JSON.parse(market.outcomePrices)
                : market.outcomePrices;
              priceYes = parseFloat(prices[0]) || 0;
              priceNo = parseFloat(prices[1]) || 0;
            } catch (e) {
              // Ignore parse errors
            }
          }

          // Calculate ratio for display (e.g., "75/25")
          const yesPercent = Math.round(priceYes * 100);
          const noPercent = Math.round(priceNo * 100);
          const priceRatio = `${yesPercent}/${noPercent}`;

          // Get price change
          const priceChange24h = parseFloat(market.oneDayPriceChange) || 0;

          // Get spread
          const spread = parseFloat(market.spread) || 0;

          spikes.push({
            marketId,
            question: market.question,
            current24hrVolume: volume24hr,
            avgVolume,
            spikeMultiplier,
            percentIncrease,
            priceYes,
            priceNo,
            priceRatio,
            priceChange24h,
            spread,
            liquidity: parseFloat(market.liquidity) || 0,
            timestamp: Date.now(),
          });
        }
      }

      // Save updated history
      this.saveHistory();

      // Sort by spike multiplier (highest first)
      return spikes.sort((a, b) => b.spikeMultiplier - a.spikeMultiplier);

    } catch (error) {
      console.error('Error scanning for volume spikes:', error);
      throw error;
    }
  }

  /**
   * Format spike for display
   */
  formatSpike(spike: VolumeSpike): string {
    return `
🔥 VOLUME SPIKE DETECTED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 ${spike.question}

💰 Volume:
   Current 24hr: $${spike.current24hrVolume.toLocaleString()}
   Average:      $${spike.avgVolume.toLocaleString()}
   Spike:        ${spike.spikeMultiplier.toFixed(2)}x (${spike.percentIncrease.toFixed(0)}% increase)

💹 Prices:
   YES: $${spike.priceYes.toFixed(4)}
   NO:  $${spike.priceNo.toFixed(4)}
   Combined: $${(spike.priceYes + spike.priceNo).toFixed(4)}

💧 Liquidity: $${spike.liquidity.toLocaleString()}

🔗 Market ID: ${spike.marketId}
⏰ ${new Date(spike.timestamp).toISOString()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
  }

  /**
   * Get summary statistics
   */
  getSummary(): string {
    const marketCount = Object.keys(this.history).length;
    const totalDataPoints = Object.values(this.history).reduce((sum, data) => sum + data.length, 0);
    const avgDataPoints = marketCount > 0 ? (totalDataPoints / marketCount).toFixed(1) : 0;

    return `
📊 Volume Spike Detector Status:
   Markets tracked: ${marketCount}
   Total data points: ${totalDataPoints}
   Avg history per market: ${avgDataPoints}
   Min spike threshold: ${this.minSpikeMultiplier}x
`;
  }
}
