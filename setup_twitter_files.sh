#!/bin/bash
# Setup Twitter signal monitoring files

cd ~/clawdbot_polymarket_trader

echo "Creating Twitter monitoring files..."

# Create twitter_monitor.ts
cat > src/signals/twitter_monitor.ts << 'ENDFILE'
import { TwitterApi } from 'twitter-api-v2';
import * as dotenv from 'dotenv';

dotenv.config();

interface TrendingTopic {
  name: string;
  url: string;
  tweet_volume?: number;
  promoted_content?: boolean;
}

interface Tweet {
  id: string;
  text: string;
  created_at: string;
  author_id: string;
  public_metrics?: {
    retweet_count: number;
    reply_count: number;
    like_count: number;
    quote_count: number;
  };
}

export class TwitterMonitor {
  private client: TwitterApi;

  constructor() {
    const apiKey = process.env.TWITTER_API_KEY;
    const apiSecret = process.env.TWITTER_API_SECRET;
    const accessToken = process.env.TWITTER_ACCESS_TOKEN;
    const accessTokenSecret = process.env.TWITTER_ACCESS_TOKEN_SECRET;

    if (!apiKey || !apiSecret || !accessToken || !accessTokenSecret) {
      throw new Error('Missing Twitter API credentials in .env file');
    }

    this.client = new TwitterApi({
      appKey: apiKey,
      appSecret: apiSecret,
      accessToken: accessToken,
      accessSecret: accessTokenSecret,
    });
  }

  async getTrending(woeid: number = 1): Promise<TrendingTopic[]> {
    try {
      const trends = await this.client.v1.trendsByPlace(woeid);
      
      if (!trends || trends.length === 0) {
        return [];
      }

      return trends[0].trends.map(trend => ({
        name: trend.name,
        url: trend.url,
        tweet_volume: trend.tweet_volume || undefined,
        promoted_content: trend.promoted_content || false
      }));
    } catch (error) {
      console.error('Error fetching trending topics:', error);
      return [];
    }
  }

  async searchTweets(query: string, maxResults: number = 20): Promise<Tweet[]> {
    try {
      const response = await this.client.v2.search(query, {
        max_results: Math.min(maxResults, 100),
        'tweet.fields': ['created_at', 'public_metrics', 'author_id'],
      });

      return response.data.data.map(tweet => ({
        id: tweet.id,
        text: tweet.text,
        created_at: tweet.created_at || '',
        author_id: tweet.author_id || '',
        public_metrics: tweet.public_metrics
      }));
    } catch (error) {
      console.error(\`Error searching tweets for "\${query}":\`, error);
      return [];
    }
  }

  filterPredictionMarketTopics(trends: TrendingTopic[]): TrendingTopic[] {
    const keywords = [
      'election', 'vote', 'poll', 'predict', 'odds', 'bet', 'polymarket',
      'trump', 'biden', 'president', 'senate', 'congress',
      'sports', 'nfl', 'nba', 'super bowl', 'playoffs',
      'bitcoin', 'crypto', 'stock', 'market'
    ];

    return trends.filter(trend => {
      const name = trend.name.toLowerCase();
      
      if (trend.promoted_content) {
        return false;
      }

      if (trend.tweet_volume && trend.tweet_volume < 5000) {
        return false;
      }

      return keywords.some(keyword => name.includes(keyword));
    });
  }

  extractKeyPhrases(trend: TrendingTopic): string[] {
    const phrases: string[] = [];
    
    const cleanName = trend.name.replace(/^#/, '');
    phrases.push(cleanName);

    const quotedMatches = trend.name.match(/"([^"]+)"/g);
    if (quotedMatches) {
      phrases.push(...quotedMatches.map(m => m.replace(/"/g, '')));
    }

    const nameMatches = cleanName.match(/\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b/g);
    if (nameMatches) {
      phrases.push(...nameMatches);
    }

    return [...new Set(phrases)];
  }

  analyzeSentiment(tweets: Tweet[]): {
    positive: number;
    negative: number;
    neutral: number;
    engagement: number;
  } {
    const positiveWords = ['win', 'won', 'success', 'great', 'good', 'up', 'rise', 'gain', 'bullish', 'moon'];
    const negativeWords = ['lose', 'lost', 'fail', 'bad', 'down', 'fall', 'drop', 'bearish', 'crash'];

    let positive = 0;
    let negative = 0;
    let neutral = 0;
    let totalEngagement = 0;

    tweets.forEach(tweet => {
      const text = tweet.text.toLowerCase();
      
      const metrics = tweet.public_metrics;
      if (metrics) {
        const engagement = metrics.like_count + metrics.retweet_count + metrics.reply_count;
        totalEngagement += engagement;
      }

      const hasPositive = positiveWords.some(word => text.includes(word));
      const hasNegative = negativeWords.some(word => text.includes(word));

      if (hasPositive && !hasNegative) {
        positive++;
      } else if (hasNegative && !hasPositive) {
        negative++;
      } else {
        neutral++;
      }
    });

    return {
      positive,
      negative,
      neutral,
      engagement: totalEngagement
    };
  }
}
ENDFILE

echo "✅ Created src/signals/twitter_monitor.ts"
echo "Done! Files ready to commit."
