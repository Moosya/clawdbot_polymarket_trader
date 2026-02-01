import { TwitterMonitor } from './twitter_monitor';
import axios from 'axios';

interface PolymarketMarket {
  id: string;
  question: string;
  description: string;
  outcomes: string[];
  volume: number;
  liquidity: number;
  endDate: string;
}

interface TradingSignal {
  trendHeadline: string;
  trendVolume: number;
  marketQuestion: string;
  marketId: string;
  matchScore: number;
  twitterSentiment: {
    positive: number;
    negative: number;
    neutral: number;
    engagement: number;
  };
  reasoning: string;
}

export class TrendMarketMatcher {
  private twitterMonitor: TwitterMonitor;
  private polymarketBaseUrl = 'https://gamma-api.polymarket.com';

  constructor() {
    this.twitterMonitor = new TwitterMonitor();
  }

  /**
   * Search Polymarket markets
   */
  async searchMarkets(query: string): Promise<PolymarketMarket[]> {
    try {
      const response = await axios.get(`${this.polymarketBaseUrl}/markets`, {
        params: {
          limit: 20,
          _search: query
        }
      });
      return response.data;
    } catch (error) {
      console.error(`Error searching Polymarket for "${query}":`, error);
      return [];
    }
  }

  /**
   * Calculate match score between trend and market
   */
  private calculateMatchScore(trendHeadline: string, marketQuestion: string): number {
    const trendWords = trendHeadline.toLowerCase().split(/\s+/);
    const marketWords = marketQuestion.toLowerCase().split(/\s+/);

    // Count matching words
    const matchingWords = trendWords.filter(word => 
      word.length > 3 && marketWords.some(mw => mw.includes(word) || word.includes(mw))
    );

    // Score: percentage of trend words found in market
    return matchingWords.length / trendWords.length;
  }

  /**
   * Scan for trading opportunities
   */
  async scan(): Promise<TradingSignal[]> {
    console.log('🐦 Fetching Twitter trending topics...');
    const trends = await this.twitterMonitor.getTrending();
    
    console.log(`📊 Found ${trends.length} trending topics`);
    const relevantTrends = this.twitterMonitor.filterPredictionMarketTopics(trends);
    
    console.log(`🎯 ${relevantTrends.length} relevant for prediction markets`);

    const signals: TradingSignal[] = [];

    for (const trend of relevantTrends.slice(0, 5)) { // Top 5 to avoid rate limits
      console.log(`\n🔍 Analyzing: "${trend.headline}"`);
      
      // Extract search phrases
      const keyPhrases = this.twitterMonitor.extractKeyPhrases(trend);
      console.log(`   Key phrases: ${keyPhrases.slice(0, 3).join(', ')}`);

      // Search Polymarket for matching markets
      let allMarkets: PolymarketMarket[] = [];
      for (const phrase of keyPhrases.slice(0, 3)) { // Top 3 phrases
        const markets = await this.searchMarkets(phrase);
        allMarkets.push(...markets);
      }

      // Deduplicate markets by ID
      const uniqueMarkets = Array.from(
        new Map(allMarkets.map(m => [m.id, m])).values()
      );

      if (uniqueMarkets.length === 0) {
        console.log(`   ❌ No matching Polymarket markets found`);
        continue;
      }

      console.log(`   ✅ Found ${uniqueMarkets.length} potential markets`);

      // Get Twitter sentiment
      const tweets = await this.twitterMonitor.searchTweets(trend.headline, 20);
      const sentiment = this.twitterMonitor.analyzeSentiment(tweets);

      // Score each market
      for (const market of uniqueMarkets) {
        const matchScore = this.calculateMatchScore(trend.headline, market.question);
        
        if (matchScore > 0.3) { // At least 30% word overlap
          signals.push({
            trendHeadline: trend.headline,
            trendVolume: trend.postCount || 0,
            marketQuestion: market.question,
            marketId: market.id,
            matchScore,
            twitterSentiment: sentiment,
            reasoning: this.generateReasoning(trend, market, sentiment, matchScore)
          });
        }
      }
    }

    // Sort by match score
    return signals.sort((a, b) => b.matchScore - a.matchScore);
  }

  /**
   * Generate human-readable reasoning for signal
   */
  private generateReasoning(
    trend: any,
    market: PolymarketMarket,
    sentiment: any,
    matchScore: number
  ): string {
    const parts: string[] = [];

    parts.push(`Twitter trending: "${trend.headline}"`);
    
    if (trend.postCount) {
      parts.push(`${trend.postCount.toLocaleString()} posts`);
    }

    parts.push(`Match: ${(matchScore * 100).toFixed(0)}%`);

    const total = sentiment.positive + sentiment.negative + sentiment.neutral;
    if (total > 0) {
      const positivePct = (sentiment.positive / total * 100).toFixed(0);
      parts.push(`Sentiment: ${positivePct}% positive`);
    }

    parts.push(`Engagement: ${sentiment.engagement.toLocaleString()}`);

    return parts.join(' | ');
  }

  /**
   * Format signals for display
   */
  formatSignals(signals: TradingSignal[]): string {
    if (signals.length === 0) {
      return '❌ No trading signals found';
    }

    let output = `🎯 Found ${signals.length} trading signals:\n\n`;

    signals.forEach((signal, i) => {
      output += `${i + 1}. ${signal.marketQuestion}\n`;
      output += `   ${signal.reasoning}\n`;
      output += `   Market ID: ${signal.marketId}\n\n`;
    });

    return output;
  }
}
