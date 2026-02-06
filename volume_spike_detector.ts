import * as fs from 'fs';

interface VolumeSpike {
  marketId: string;
  question: string;
  volume24hr: number;
  volume1wk: number;
  avgVolume: number;
  liquidity: number;
  spikeMultiplier: number;
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
  private minSpikeMultiplier: number;
  private minAvgVolume: number;
  private minLiquidity: number;
  private min24hrVolume: number;
  private excludeSports: boolean;
  private historyFile?: string;

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
    this.historyFile = historyFile;
  }

  private isSportsMarket(question: string): boolean {
    const sportsKeywords = [
      'NFL', 'NBA', 'MLB', 'NHL', 'NCAA', 'FIFA', 'UFC',
      'Super Bowl', 'playoffs', 'Rookie', 'MVP', 'Defensive',
      'player', 'team', 'game', 'season'
    ];
    const lowerQuestion = question.toLowerCase();
    return sportsKeywords.some(keyword => 
      lowerQuestion.includes(keyword.toLowerCase())
    );
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

    const spikes: VolumeSpike[] = [];

    try {
      const response = await fetch('https://gamma-api.polymarket.com/markets?limit=500&active=true');
      const markets = await response.json();

      for (const market of markets) {
        stats.totalScanned++;

        const volume24hr = parseFloat(market.volume24hr) || 0;
        const volume1wk = parseFloat(market.volume) || 0;
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

        // FILTER 4: Sports markets
        if (this.excludeSports && this.isSportsMarket(market.question)) {
          stats.filteredBySports++;
          continue;
        }

        // Now check for spike
        if (avgVolume > 0) {
          const spikeMultiplier = volume24hr / avgVolume;
          
          if (spikeMultiplier >= this.minSpikeMultiplier) {
            stats.passedFilters++;
            
            spikes.push({
              marketId: market.conditionId,
              question: market.question,
              volume24hr,
              volume1wk,
              avgVolume,
              liquidity,
              spikeMultiplier,
              timestamp: Date.now()
            });
          }
        }
      }

      // Sort by spike multiplier descending
      const sortedSpikes = spikes.sort((a, b) => b.spikeMultiplier - a.spikeMultiplier);

      return { spikes: sortedSpikes, stats };

    } catch (error) {
      console.error('Error scanning for volume spikes:', error);
      return { spikes: [], stats };
    }
  }

  formatFilterStats(stats: FilterStats): string {
    return `
📊 Filter Stats:
   Total: ${stats.totalScanned}
   ├─ 24hr vol: ${stats.filteredByVolume}
   ├─ Avg vol: ${stats.filteredByAvgVolume}
   ├─ Liquidity: ${stats.filteredByLiquidity}
   ├─ Sports: ${stats.filteredBySports}
   └─ ✅ Passed: ${stats.passedFilters}
`;
  }

  formatSpike(spike: VolumeSpike): string {
    return `
🔥 Volume Spike Detected!
   Market: ${spike.question}
   24hr Volume: $${spike.volume24hr.toLocaleString()}
   Avg Volume: $${spike.avgVolume.toLocaleString()}
   Liquidity: $${spike.liquidity.toLocaleString()}
   Spike: ${spike.spikeMultiplier.toFixed(2)}x
   ID: ${spike.marketId}
`;
  }
}
