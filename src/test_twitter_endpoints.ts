#!/usr/bin/env node
/**
 * Twitter API Endpoint Tester
 * 
 * Tests which v2 endpoints work with Free tier credentials
 * Shows rate limits, example responses, and what's blocked
 */

import { TwitterApi } from 'twitter-api-v2';
import * as dotenv from 'dotenv';

dotenv.config();

interface EndpointTest {
  name: string;
  description: string;
  test: (client: TwitterApi) => Promise<any>;
}

async function main() {
  console.log('🧪 Twitter API Endpoint Tester\n');
  console.log('=' .repeat(70));

  // Initialize client
  const apiKey = process.env.TWITTER_API_KEY;
  const apiSecret = process.env.TWITTER_API_SECRET;
  const accessToken = process.env.TWITTER_ACCESS_TOKEN;
  const accessTokenSecret = process.env.TWITTER_ACCESS_TOKEN_SECRET;

  if (!apiKey || !apiSecret || !accessToken || !accessTokenSecret) {
    console.error('❌ Missing Twitter API credentials in .env file');
    process.exit(1);
  }

  const client = new TwitterApi({
    appKey: apiKey,
    appSecret: apiSecret,
    accessToken: accessToken,
    accessSecret: accessTokenSecret,
  });

  // Define endpoint tests
  const tests: EndpointTest[] = [
    {
      name: 'Recent Tweet Search',
      description: 'Search last 7 days (keyword: "polymarket")',
      test: async (c) => {
        const result = await c.v2.search('polymarket', {
          max_results: 10,
          'tweet.fields': ['created_at', 'public_metrics'],
        });
        return {
          count: result.data.data?.length || 0,
          tweets: result.data.data?.slice(0, 3).map((t: any) => ({
            text: t.text.substring(0, 80) + '...',
            likes: t.public_metrics?.like_count,
            retweets: t.public_metrics?.retweet_count,
          })),
          rateLimit: result.rateLimit,
        };
      },
    },
    {
      name: 'User Lookup by Username',
      description: 'Get user info (@elonmusk)',
      test: async (c) => {
        const result = await c.v2.userByUsername('elonmusk', {
          'user.fields': ['public_metrics', 'verified'],
        });
        return {
          user: result.data.name,
          username: result.data.username,
          followers: result.data.public_metrics?.followers_count,
          verified: result.data.verified,
          rateLimit: result.rateLimit,
        };
      },
    },
    {
      name: 'Tweet Lookup by ID',
      description: 'Get specific tweet details',
      test: async (c) => {
        // Use a recent tweet ID (this is Elon's "Let that sink in" tweet)
        const result = await c.v2.singleTweet('1587312517679878144', {
          'tweet.fields': ['created_at', 'public_metrics'],
        });
        return {
          text: result.data.text,
          created: result.data.created_at,
          likes: result.data.public_metrics?.like_count,
          rateLimit: result.rateLimit,
        };
      },
    },
    {
      name: 'Trending Topics',
      description: 'Get trending topics (US)',
      test: async (c) => {
        const result = await c.v1.trendsAvailable();
        return {
          available: result.length > 0,
          count: result.length,
        };
      },
    },
    {
      name: 'User Timeline',
      description: 'Get recent tweets from a user',
      test: async (c) => {
        // Get Polymarket's tweets
        const user = await c.v2.userByUsername('Polymarket');
        const tweets = await c.v2.userTimeline(user.data.id, {
          max_results: 5,
          'tweet.fields': ['created_at', 'public_metrics'],
        });
        return {
          user: user.data.username,
          tweetCount: tweets.data.data?.length || 0,
          recentTweets: tweets.data.data?.slice(0, 2).map((t: any) => ({
            text: t.text.substring(0, 60) + '...',
            likes: t.public_metrics?.like_count,
          })),
          rateLimit: tweets.rateLimit,
        };
      },
    },
    {
      name: 'Tweet Counts (volume)',
      description: 'Count tweets for a query (last 7 days)',
      test: async (c) => {
        const result = await c.v2.tweetCountRecent('bitcoin', {
          granularity: 'hour',
        });
        return {
          totalCount: result.data.meta?.total_tweet_count,
          hourlyData: result.data.data?.slice(0, 3).map((d: any) => ({
            start: d.start,
            count: d.tweet_count,
          })),
          rateLimit: result.rateLimit,
        };
      },
    },
  ];

  // Run tests
  const results: any[] = [];

  for (const test of tests) {
    console.log(`\n📝 Testing: ${test.name}`);
    console.log(`   ${test.description}`);

    try {
      const result = await test.test(client);
      
      console.log('   ✅ SUCCESS');
      console.log('   Response:', JSON.stringify(result, null, 2).split('\n').map(line => '   ' + line).join('\n'));
      
      if (result.rateLimit) {
        console.log(`   📊 Rate Limit: ${result.rateLimit.remaining}/${result.rateLimit.limit} (resets: ${new Date(result.rateLimit.reset * 1000).toLocaleTimeString()})`);
      }

      results.push({
        endpoint: test.name,
        status: 'AVAILABLE',
        result,
      });

    } catch (error: any) {
      if (error.code === 403) {
        console.log('   ❌ BLOCKED (Free tier restriction)');
        console.log(`   Error: ${error.errors?.[0]?.message || error.message}`);
        
        results.push({
          endpoint: test.name,
          status: 'BLOCKED',
          error: error.errors?.[0]?.message || error.message,
        });
      } else {
        console.log('   ⚠️  ERROR');
        console.log(`   ${error.message}`);
        
        results.push({
          endpoint: test.name,
          status: 'ERROR',
          error: error.message,
        });
      }
    }

    // Rate limit pause
    await sleep(1000);
  }

  // Summary
  console.log('\n' + '='.repeat(70));
  console.log('📊 SUMMARY\n');

  const available = results.filter(r => r.status === 'AVAILABLE');
  const blocked = results.filter(r => r.status === 'BLOCKED');
  const errors = results.filter(r => r.status === 'ERROR');

  console.log(`✅ Available: ${available.length}`);
  available.forEach(r => console.log(`   - ${r.endpoint}`));

  console.log(`\n❌ Blocked: ${blocked.length}`);
  blocked.forEach(r => console.log(`   - ${r.endpoint}`));

  if (errors.length > 0) {
    console.log(`\n⚠️  Errors: ${errors.length}`);
    errors.forEach(r => console.log(`   - ${r.endpoint}: ${r.error}`));
  }

  console.log('\n💡 RECOMMENDATIONS FOR FREE TIER:\n');
  
  if (available.some(r => r.endpoint.includes('Recent Tweet Search'))) {
    console.log('✓ Use keyword search for market-related discussions');
  }
  if (available.some(r => r.endpoint.includes('Tweet Counts'))) {
    console.log('✓ Monitor discussion volume spikes');
  }
  if (available.some(r => r.endpoint.includes('User Timeline'))) {
    console.log('✓ Watch specific influential accounts');
  }
  if (available.some(r => r.endpoint.includes('User Lookup'))) {
    console.log('✓ Weight signals by user credibility (followers, verified)');
  }

  console.log('\n' + '='.repeat(70));
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
