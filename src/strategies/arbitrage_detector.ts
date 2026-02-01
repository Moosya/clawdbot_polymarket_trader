import { PolymarketClient } from '../api/polymarket_client';
import { ArbitrageOpportunity, Market } from '../types';

export class ArbitrageDetector {
  private client: PolymarketClient;
  private minProfitPercent: number;
  private debugMode: boolean;

  constructor(client: PolymarketClient, minProfitPercent: number = 0.5, debugMode: boolean = false) {
    this.client = client;
    this.minProfitPercent = minProfitPercent;
    this.debugMode = debugMode;
  }

  /**
   * Check a single market for arbitrage opportunities
   * Returns opportunity if YES + NO < $1.00
   */
  async checkMarket(market: Market): Promise<ArbitrageOpportunity | null> {
    try {
      // Skip inactive or closed markets
      if (!market.active || market.closed) {
        return null;
      }

      // Get tokens (Yes and No outcomes)
      const tokens = market.tokens;
      if (!tokens || tokens.length < 2) {
        if (this.debugMode) {
          console.log(`⚠️  Market ${market.id} has ${tokens?.length || 0} tokens`);
        }
        return null;
      }

      const yesToken = tokens.find(t => t.outcome.toLowerCase() === 'yes');
      const noToken = tokens.find(t => t.outcome.toLowerCase() === 'no');

      if (!yesToken || !noToken) {
        if (this.debugMode) {
          console.log(`⚠️  Market ${market.id} missing YES/NO tokens:`, tokens.map(t => t.outcome));
        }
        return null;
      }

      // Get current prices (ask prices - what we'd pay to buy)
      const yesPrice = await this.client.getTokenPrice(yesToken.token_id);
      const noPrice = await this.client.getTokenPrice(noToken.token_id);

      if (this.debugMode) {
        console.log(`Market: ${market.question.substring(0, 50)}...`);
        console.log(`  YES: $${yesPrice.toFixed(4)} | NO: $${noPrice.toFixed(4)} | Combined: $${(yesPrice + noPrice).toFixed(4)}`);
      }

      // Calculate combined cost
      const combinedPrice = yesPrice + noPrice;

      // Check if arbitrage exists (combined < $1.00)
      if (combinedPrice < 1.0) {
        const profitPerShare = 1.0 - combinedPrice;
        const profitPercent = (profitPerShare / combinedPrice) * 100;

        // Only return if profit meets minimum threshold
        if (profitPercent >= this.minProfitPercent) {
          return {
            market_id: market.id,
            question: market.question,
            yes_price: yesPrice,
            no_price: noPrice,
            combined_price: combinedPrice,
            profit_per_share: profitPerShare,
            profit_percent: profitPercent,
            timestamp: Date.now(),
          };
        }
      }

      return null;
    } catch (error) {
      if (this.debugMode) {
        console.error(`Error checking market ${market.id}:`, error);
      }
      return null;
    }
  }

  /**
   * Scan all markets for arbitrage opportunities
   */
  async scanAllMarkets(sampleSize?: number): Promise<ArbitrageOpportunity[]> {
    try {
      console.log('Fetching active markets...');
      const markets = await this.client.getMarkets();
      
      if (!Array.isArray(markets)) {
        console.error('⚠️  Markets response is not an array:', typeof markets);
        return [];
      }

      // If sample size specified, only check that many markets (for debugging)
      const marketsToCheck = sampleSize ? markets.slice(0, sampleSize) : markets;
      
      console.log(`Scanning ${marketsToCheck.length} markets for arbitrage...`);
      if (sampleSize && this.debugMode) {
        console.log('🔍 DEBUG MODE: Showing first market details...\n');
      }
      
      const opportunities: ArbitrageOpportunity[] = [];

      // Check markets in parallel (with some rate limiting)
      const batchSize = 10;
      for (let i = 0; i < marketsToCheck.length; i += batchSize) {
        const batch = marketsToCheck.slice(i, i + batchSize);
        const results = await Promise.all(
          batch.map(market => this.checkMarket(market))
        );

        // Filter out nulls and add to opportunities
        results.forEach(opp => {
          if (opp) {
            opportunities.push(opp);
          }
        });

        // Small delay to avoid rate limiting
        await this.sleep(100);
      }

      return opportunities;
    } catch (error) {
      console.error('Error scanning markets:', error);
      return [];
    }
  }

  /**
   * Format opportunity for console output
   */
  formatOpportunity(opp: ArbitrageOpportunity): string {
    return [
      `\n🦀 ARBITRAGE FOUND!`,
      `Market: ${opp.question}`,
      `YES: $${opp.yes_price.toFixed(4)} | NO: $${opp.no_price.toFixed(4)}`,
      `Combined: $${opp.combined_price.toFixed(4)}`,
      `Profit: $${opp.profit_per_share.toFixed(4)} per share (${opp.profit_percent.toFixed(2)}%)`,
      `Market ID: ${opp.market_id}`,
      `Timestamp: ${new Date(opp.timestamp).toISOString()}`,
    ].join('\n');
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
