/**
 * Volume Spike Detector - WITH LIQUIDITY & VOLUME FILTERS
 * 
 * Copy this to: src/strategies/volume_spike_detector.ts
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
  priceRatio: string;
  priceChange24h: number;
  spread: number;
  liquidity: number;
  timestamp: number;
}

interface FilterStats {
  totalScanned: number;
  filteredByVolume: number;
  filteredByAvgVolume: number;
  filteredByLiquidity: number;
  filteredBySports: number;
  passedFilters: number;
}

export class VolumeSpikeDetector {
  private historyFile: string;
  private history: VolumeHistory = {};
  private minSpikeMultiplier: number;
  private minAvgVolume: number;
  private minLiquidity: number;
  private min24hrVolume: number;
  private excludeSports: boolean;
  private apiUrl = 'https://gamma-api.polymarket.com';

  constructor(
    minSpikeMultiplier: number = 2.0,
    minAvgVolume: number = 10000,
    minLiquidity: number = 50000,
    min24hrVolume: number = 5000,
    excludeSports: boolean = false,
    historyFile?: string
  ) {
    this.minSpikeMultiplier = minSpikeMultiplier;
    this.minAvgVolume = minAvgVolume;
    this.minLiquidity = minLiquidity;
    this.min24hrVolume = min24hrVolume;
    this.excludeSports = excludeSports;
    this.historyFile = historyFile || path.join(process.cwd(), 'volume_history.json');
    this.loadHistory();
  }

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

  private saveHistory(): void {
    try {
      fs.writeFileSync(this.historyFile, JSON.stringify(this.history, null, 2));
    } catch (error) {
      console.error('Error saving volume history:', error);
    }
  }

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

    if (this.history[marketId].length > 30) {
      this.history[marketId] = this.history[marketId].slice(-30);
    }
  }

  private getAverageVolume(marketId: string): number {
    const data = this.history[marketId];
    if (!data || data.length < 2) {
      return 0;
    }

    const sum = data.reduce((acc, d) => acc + d.volume24hr, 0);
    return sum / data.length;
  }

  private isSportsMarket(question: string): boolean {
    const sportsKeywords = [
      'NFL', 'NBA', 'MLB', 'NHL', 'NCAA', 'FIFA', 'UFC', 'Premier League',
      'Super Bowl', 'playoffs', 'championship', 'Rookie', 'MVP', 'Defensive',
      'Offensive', 'touchdown', 'goal', 'points', 'game', 'season',
      'player', 'team', 'win', 'lose', 'match'
    ];
    
    const lowerQuestion = question.toLowerCase();
    return sportsKeywords.some(keyword => lowerQuestion.includes(keyword.toLowerCase()));
  }

  async scanForSpikes(): Promise<{ spikes: VolumeSpike[], stats: FilterStats }> {
    const stats: FilterStats = {
      totalScanned: 0,
      filteredByVolume: 0,
      filteredByAvgVolume: 0,
      filteredByLiquidity: 0,
      filteredBySports: 0,
      passedFilters: 0,
    };

    try {
      const response = await axios.get(`${this.apiUrl}/markets`, {
        params: {
          limit: 100,
          active: true,
          closed: false,
        },
      });

      const markets = response.data;
      const spikes: VolumeSpike[] = [];
      stats.totalScanned = markets.length;

      for (const market of markets) {
        const marketId = market.condition_id;
        const volume24hr = parseFloat(market.volume24hr) || 0;
        const volume1wk = parseFloat(market.volume1wk) || 0;
        const liquidity = parseFloat(market.liquidity) || 0;

        // FILTER 1: Min 24hr volume
        if (volume24hr < this.min24hrVolume) {
          stats.filteredByVolume++;
          continue;
        }

        const avgVolume = volume1wk / 7;

        // FILTER 2: Min avg volume
        if (avgVolume < this.minAvgVolume) {
          stats.filteredByAvgVolume++;
          continue;
        }

        // FILTER 3: Min liquidity
        if (liquidity < this.minLiquidity) {
          stats.filteredByLiquidity++;
          continue;
        }

        // FILTER 4: Sports markets (optional)
        if (this.excludeSports && this.isSportsMarket(market.question)) {
          stats.filteredBySports++;
          continue;
        }

        // Check for spike
        const spikeMultiplier = volume24hr / avgVolume;
        const percentIncrease = ((volume24hr - avgVolume) / avgVolume) * 100;

        if (spikeMultiplier >= this.minSpikeMultiplier) {
          stats.passedFilters++;

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
              // Ignore
            }
          }

          const yesPercent = Math.round(priceYes * 100);
          const noPercent = Math.round(priceNo * 100);
          const priceRatio = `${yesPercent}/${noPercent}`;
          const priceChange24h = parseFloat(market.oneDayPriceChange) || 0;
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
            liquidity,
            timestamp: Date.now(),
          });
        }
      }

      this.saveHistory();

      return { 
        spikes: spikes.sort((a, b) => b.spikeMultiplier - a.spikeMultiplier),
        stats 
      };

    } catch (error) {
      console.error('Error scanning for volume spikes:', error);
      throw error;
    }
  }

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

  formatFilterStats(stats: FilterStats): string {
    return `
📊 Filter Statistics:
   Total markets scanned: ${stats.totalScanned}
   ├─ Filtered by 24hr volume (<$${this.min24hrVolume.toLocaleString()}): ${stats.filteredByVolume}
   ├─ Filtered by avg volume (<$${this.minAvgVolume.toLocaleString()}): ${stats.filteredByAvgVolume}
   ├─ Filtered by liquidity (<$${this.minLiquidity.toLocaleString()}): ${stats.filteredByLiquidity}
   ├─ Filtered by sports: ${stats.filteredBySports}
   └─ Passed all filters: ${stats.passedFilters}
`;
  }

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
