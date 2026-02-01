/**
 * New Market Monitor
 * 
 * Tracks when new markets appear on Polymarket
 * Early detection = early mover advantage before markets become efficient
 * 
 * Signal: Fresh markets often have mispricing before crowd discovers them
 */

import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';

interface NewMarket {
  marketId: string;
  question: string;
  description: string;
  outcomes: string[];
  endDate: string;
  startDate: string;
  priceYes: number;
  priceNo: number;
  liquidity: number;
  volume: number;
  discoveredAt: number;
  ageMinutes: number;
}

interface KnownMarkets {
  [marketId: string]: {
    question: string;
    firstSeen: number;
  };
}

export class NewMarketMonitor {
  private knownMarketsFile: string;
  private knownMarkets: KnownMarkets = {};
  private apiUrl = 'https://gamma-api.polymarket.com';
  private maxAgeHours: number;

  constructor(maxAgeHours: number = 24, knownMarketsFile?: string) {
    this.maxAgeHours = maxAgeHours;
    this.knownMarketsFile = knownMarketsFile || path.join(process.cwd(), 'known_markets.json');
    this.loadKnownMarkets();
  }

  /**
   * Load known markets from disk
   */
  private loadKnownMarkets(): void {
    try {
      if (fs.existsSync(this.knownMarketsFile)) {
        const data = fs.readFileSync(this.knownMarketsFile, 'utf-8');
        this.knownMarkets = JSON.parse(data);
        console.log(`📋 Loaded ${Object.keys(this.knownMarkets).length} known markets`);
      }
    } catch (error) {
      console.log('📋 Starting fresh market database');
      this.knownMarkets = {};
    }
  }

  /**
   * Save known markets to disk
   */
  private saveKnownMarkets(): void {
    try {
      fs.writeFileSync(this.knownMarketsFile, JSON.stringify(this.knownMarkets, null, 2));
    } catch (error) {
      console.error('Error saving known markets:', error);
    }
  }

  /**
   * Calculate market age in minutes
   */
  private getMarketAge(startDate: string): number {
    const start = new Date(startDate);
    const now = new Date();
    return (now.getTime() - start.getTime()) / (1000 * 60);
  }

  /**
   * Scan for new markets
   */
  async scanForNewMarkets(): Promise<NewMarket[]> {
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
      const newMarkets: NewMarket[] = [];
      const now = Date.now();

      for (const market of markets) {
        const marketId = market.condition_id;

        // Check if we've seen this market before
        if (!this.knownMarkets[marketId]) {
          // New market discovered!
          const ageMinutes = this.getMarketAge(market.startDate);

          // Only alert if market is within our max age threshold
          // (avoids alerting on old markets when first running the monitor)
          if (ageMinutes <= this.maxAgeHours * 60) {
            newMarkets.push({
              marketId,
              question: market.question,
              description: market.description || '',
              outcomes: market.outcomes || [],
              endDate: market.endDate,
              startDate: market.startDate,
              priceYes: parseFloat(market.outcomePrices?.[0]) || 0,
              priceNo: parseFloat(market.outcomePrices?.[1]) || 0,
              liquidity: parseFloat(market.liquidity) || 0,
              volume: parseFloat(market.volumeNum) || 0,
              discoveredAt: now,
              ageMinutes,
            });
          }

          // Record as known
          this.knownMarkets[marketId] = {
            question: market.question,
            firstSeen: now,
          };
        }
      }

      // Clean up very old markets from known list (older than 30 days)
      const thirtyDaysAgo = now - (30 * 24 * 60 * 60 * 1000);
      Object.keys(this.knownMarkets).forEach(id => {
        if (this.knownMarkets[id].firstSeen < thirtyDaysAgo) {
          delete this.knownMarkets[id];
        }
      });

      // Save updated known markets
      this.saveKnownMarkets();

      // Sort by age (newest first)
      return newMarkets.sort((a, b) => a.ageMinutes - b.ageMinutes);

    } catch (error) {
      console.error('Error scanning for new markets:', error);
      throw error;
    }
  }

  /**
   * Format new market for display
   */
  formatNewMarket(market: NewMarket): string {
    const ageStr = market.ageMinutes < 60 
      ? `${market.ageMinutes.toFixed(0)} minutes`
      : `${(market.ageMinutes / 60).toFixed(1)} hours`;

    const arbOpportunity = (market.priceYes + market.priceNo < 1.0) 
      ? `⚠️  ARBITRAGE: ${((1 - market.priceYes - market.priceNo) * 100).toFixed(2)}%`
      : '';

    return `
🆕 NEW MARKET DETECTED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 ${market.question}

⏰ Age: ${ageStr} old
📅 End Date: ${new Date(market.endDate).toLocaleDateString()}

💹 Current Prices:
   YES: $${market.priceYes.toFixed(4)}
   NO:  $${market.priceNo.toFixed(4)}
   Combined: $${(market.priceYes + market.priceNo).toFixed(4)}
   ${arbOpportunity}

💧 Liquidity: $${market.liquidity.toLocaleString()}
💰 Volume: $${market.volume.toLocaleString()}

🎯 Outcomes: ${market.outcomes.join(', ')}

🔗 Market ID: ${market.marketId}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
  }

  /**
   * Get summary statistics
   */
  getSummary(): string {
    const totalKnown = Object.keys(this.knownMarkets).length;
    const recentCount = Object.values(this.knownMarkets).filter(m => 
      Date.now() - m.firstSeen < 24 * 60 * 60 * 1000
    ).length;

    return `
📋 New Market Monitor Status:
   Total markets tracked: ${totalKnown}
   Discovered in last 24h: ${recentCount}
   Alert threshold: ${this.maxAgeHours}h old
`;
  }
}
