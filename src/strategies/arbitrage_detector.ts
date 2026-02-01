import { PolymarketClient } from '../api/polymarket_client';
import { ArbitrageOpportunity, Market } from '../types';

interface MarketCheck {
  market_id: string;
  question: string;
  yes_price: number;
  no_price: number;
  combined_price: number;
  profit_per_share: number;
  profit_percent: number;
}

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
  async checkMarket(market: Market): Promise<{ opportunity: ArbitrageOpportunity | null, check: MarketCheck | null }> {
    try {
      // Skip inactive or closed markets
      if (!market.active || market.closed) {
        return { opportunity: null, check: null };
      }

      // Get tokens (Yes and No outcomes)
      const tokens = market.tokens;
      if (!tokens || tokens.length < 2) {
        if (this.debugMode) {
          console.log(`⚠️  Market ${market.id} has ${tokens?.length || 0} tokens`);
        }
        return { opportunity: null, check: null };
      }

      const yesToken = tokens.find(t => t.outcome.toLowerCase() === 'yes');
      const noToken = tokens.find(t => t.outcome.toLowerCase() === 'no');

      if (!yesToken || !noToken) {
        if (this.debugMode) {
          console.log(`⚠️  Market ${market.id} missing YES/NO tokens:`, tokens.map(t => t.outcome));
        }
        return { opportunity: null, check: null };
      }

      // Get current prices (ask prices - what we'd pay to buy)
      const yesPrice = await this.client.getTokenPrice(yesToken.token_id);
      const noPrice = await this.client.getTokenPrice(noToken.token_id);

      // Calculate combined cost
      const combinedPrice = yesPrice + noPrice;
      const profitPerShare = 1.0 - combinedPrice;
      const profitPercent = (profitPerShare / combinedPrice) * 100;

      // Create check record for all markets (for "closest to opportunity" tracking)
      const check: MarketCheck = {
        market_id: market.id,
        question: market.question,
        yes_price: yesPrice,
        no_price: noPrice,
        combined_price: combinedPrice,
        profit_per_share: profitPerShare,
        profit_percent: profitPercent,
      };

      if (this.debugMode) {
        console.log(`\n📊 ${market.question.substring(0, 60)}...`);
        console.log(`   YES: $${yesPrice.toFixed(4)} | NO: $${noPrice.toFixed(4)}`);
        console.log(`   Combined: $${combinedPrice.toFixed(4)} | Profit: $${profitPerShare.toFixed(4)} (${profitPercent.toFixed(2)}%)`);
        
        if (combinedPrice < 1.0) {
          if (profitPercent >= this.minProfitPercent) {
            console.log(`   ✅ QUALIFIES as arbitrage!`);
          } else {
            console.log(`   ⚠️  Arbitrage exists but profit too small (need ${this.minProfitPercent}%)`);
          }
        } else {
          console.log(`   ❌ No arbitrage (combined ≥ $1.00)`);
        }
      }

      // Check if arbitrage exists AND meets minimum threshold
      if (combinedPrice < 1.0 && profitPercent >= this.minProfitPercent) {
        const opportunity: ArbitrageOpportunity = {
          market_id: market.id,
          question: market.question,
          yes_price: yesPrice,
          no_price: noPrice,
          combined_price: combinedPrice,
          profit_per_share: profitPerShare,
          profit_percent: profitPercent,
          timestamp: Date.now(),
        };
        return { opportunity, check };
      }

      return { opportunity: null, check };
    } catch (error) {
      if (this.debugMode) {
        console.error(`Error checking market ${market.id}:`, error);
      }
      return { opportunity: null, check: null };
    }
  }

  /**
   * Scan all markets for arbitrage opportunities
   */
  async scanAllMarkets(sampleSize?: number): Promise<{ opportunities: ArbitrageOpportunity[], closest: MarketCheck[] }> {
    try {
      console.log('Fetching active markets...');
      const markets = await this.client.getMarkets();
      
      if (!Array.isArray(markets)) {
        console.error('⚠️  Markets response is not an array:', typeof markets);
        return { opportunities: [], closest: [] };
      }

      // If sample size specified, only check that many markets (for debugging)
      const marketsToCheck = sampleSize ? markets.slice(0, sampleSize) : markets;
      
      console.log(`Scanning ${marketsToCheck.length} markets for arbitrage...`);
      if (sampleSize && this.debugMode) {
        console.log('🔍 DEBUG MODE: Detailed analysis\n');
      }
      
      const opportunities: ArbitrageOpportunity[] = [];
      const allChecks: MarketCheck[] = [];

      // Check markets in parallel (with some rate limiting)
      const batchSize = 10;
      for (let i = 0; i < marketsToCheck.length; i += batchSize) {
        const batch = marketsToCheck.slice(i, i + batchSize);
        const results = await Promise.all(
          batch.map(market => this.checkMarket(market))
        );

        // Collect opportunities and checks
        results.forEach(result => {
          if (result.opportunity) {
            opportunities.push(result.opportunity);
          }
          if (result.check) {
            allChecks.push(result.check);
          }
        });

        // Small delay to avoid rate limiting
        await this.sleep(100);
      }

      // Sort checks by combined price (lowest = closest to opportunity)
      const closest = allChecks
        .sort((a, b) => a.combined_price - b.combined_price)
        .slice(0, 5);

      return { opportunities, closest };
    } catch (error) {
      console.error('Error scanning markets:', error);
      return { opportunities: [], closest: [] };
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

  /**
   * Format closest markets (even if they don't qualify)
   */
  formatClosest(checks: MarketCheck[]): string {
    if (checks.length === 0) {
      return 'No valid markets checked.';
    }

    let output = '\n📊 Top 5 Closest to Arbitrage:\n';
    output += '─'.repeat(80) + '\n';
    
    checks.forEach((check, idx) => {
      const isArb = check.combined_price < 1.0;
      const emoji = isArb ? '💰' : '📈';
      
      output += `\n${idx + 1}. ${emoji} ${check.question.substring(0, 60)}...\n`;
      output += `   YES: $${check.yes_price.toFixed(4)} | NO: $${check.no_price.toFixed(4)} | Combined: $${check.combined_price.toFixed(4)}\n`;
      
      if (isArb) {
        output += `   ✅ Arbitrage exists! Profit: $${check.profit_per_share.toFixed(4)}/share (${check.profit_percent.toFixed(2)}%)\n`;
        if (check.profit_percent < this.minProfitPercent) {
          output += `   ⚠️  But profit < ${this.minProfitPercent}% threshold\n`;
        }
      } else {
        const overprice = check.combined_price - 1.0;
        output += `   ❌ Overpriced by $${overprice.toFixed(4)} (no arbitrage)\n`;
      }
    });
    
    return output;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
