import { PolymarketClient } from '../api/polymarket_client';
import { ArbitrageOpportunity, Market } from '../types';

interface MarketCheck {
  market_id: string;
  question: string;
  outcome1: string;
  outcome2: string;
  price1: number;
  price2: number;
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
   * Works for any 2-outcome market (YES/NO, Team A/Team B, etc.)
   */
  async checkMarket(market: Market): Promise<{ opportunity: ArbitrageOpportunity | null, check: MarketCheck | null }> {
    try {
      // Filter: must be active, not closed, and accepting orders
      if (!market.active || market.closed || !market.accepting_orders) {
        if (this.debugMode) {
          console.log(`⏭️  Skipping: ${market.question.substring(0, 50)}... (active=${market.active}, closed=${market.closed}, accepting=${market.accepting_orders})`);
        }
        return { opportunity: null, check: null };
      }

      // Must have exactly 2 outcomes for arbitrage
      const tokens = market.tokens;
      if (!tokens || tokens.length !== 2) {
        if (this.debugMode) {
          console.log(`⚠️  Market ${market.id} has ${tokens?.length || 0} tokens (need 2)`);
        }
        return { opportunity: null, check: null };
      }

      const [token1, token2] = tokens;

      // Get current prices
      const price1 = await this.client.getTokenPrice(token1.token_id);
      const price2 = await this.client.getTokenPrice(token2.token_id);

      // Calculate combined cost
      const combinedPrice = price1 + price2;
      const profitPerShare = 1.0 - combinedPrice;
      const profitPercent = (profitPerShare / combinedPrice) * 100;

      // Create check record
      const check: MarketCheck = {
        market_id: market.condition_id || market.question_id || market.id || "unknown",
        question: market.question,
        outcome1: token1.outcome,
        outcome2: token2.outcome,
        price1: price1,
        price2: price2,
        combined_price: combinedPrice,
        profit_per_share: profitPerShare,
        profit_percent: profitPercent,
      };

      if (this.debugMode) {
        console.log(`\n📊 ${market.question.substring(0, 60)}...`);
        console.log(`   ${token1.outcome}: $${price1.toFixed(4)} | ${token2.outcome}: $${price2.toFixed(4)}`);
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
          market_id: market.condition_id || market.question_id || market.id || "unknown",
          question: market.question,
          yes_price: price1,
          no_price: price2,
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
        console.error(`Error checking market ${market.question}:`, error);
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
      const allMarkets = await this.client.getMarkets();
      
      if (!Array.isArray(allMarkets)) {
        console.error('⚠️  Markets response is not an array:', typeof allMarkets);
        return { opportunities: [], closest: [] };
      }

      // Filter for tradeable markets only
      const tradeableMarkets = allMarkets.filter(m => 
        m.active && !m.closed && m.accepting_orders && m.tokens?.length === 2
      );

      console.log(`Found ${tradeableMarkets.length} tradeable markets (out of ${allMarkets.length} total)`);

      // If sample size specified, only check that many markets (for debugging)
      const marketsToCheck = sampleSize ? tradeableMarkets.slice(0, sampleSize) : tradeableMarkets;
      
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
      `Option 1: $${opp.yes_price.toFixed(4)} | Option 2: $${opp.no_price.toFixed(4)}`,
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
      output += `   ${check.outcome1}: $${check.price1.toFixed(4)} | ${check.outcome2}: $${check.price2.toFixed(4)} | Combined: $${check.combined_price.toFixed(4)}\n`;
      
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
