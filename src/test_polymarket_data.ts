#!/usr/bin/env node
/**
 * Polymarket Data Explorer
 * 
 * Tests what data is available from Polymarket APIs
 * Identifies potential trading signals from market data itself
 */

import axios from 'axios';

interface DataTest {
  name: string;
  description: string;
  test: () => Promise<any>;
}

const GAMMA_API = 'https://gamma-api.polymarket.com';
const CLOB_API = 'https://clob.polymarket.com';

async function main() {
  console.log('🦀 Polymarket Data Explorer\n');
  console.log('=' .repeat(70));

  const tests: DataTest[] = [
    {
      name: 'Market List with Metadata',
      description: 'Get markets with volume, liquidity, activity data',
      test: async () => {
        const response = await axios.get(`${GAMMA_API}/markets`, {
          params: {
            limit: 5,
            active: true,
            closed: false,
          },
        });
        
        const markets = response.data;
        return {
          count: markets.length,
          examples: markets.slice(0, 2).map((m: any) => ({
            question: m.question,
            volume: m.volume,
            liquidity: m.liquidity,
            volumeNum: m.volumeNum,
            volume24hr: m.volume24hr,
            lastTradePrice: m.lastTradePrice,
            bestBid: m.bestBid,
            bestAsk: m.bestAsk,
            spread: m.bestAsk && m.bestBid ? (m.bestAsk - m.bestBid).toFixed(4) : null,
            outcomes: m.outcomes,
            outcomePrices: m.outcomePrices,
            startDate: m.startDate,
            endDate: m.endDate,
          })),
        };
      },
    },
    {
      name: 'Single Market Details',
      description: 'Deep dive into one market',
      test: async () => {
        // First get a market ID
        const marketsResp = await axios.get(`${GAMMA_API}/markets`, {
          params: { limit: 1, active: true },
        });
        const marketId = marketsResp.data[0]?.condition_id;
        
        if (!marketId) return { error: 'No markets found' };

        const response = await axios.get(`${GAMMA_API}/markets/${marketId}`);
        const m = response.data;
        
        return {
          question: m.question,
          description: m.description,
          icon: m.icon,
          volume: m.volume,
          volumeNum: m.volumeNum,
          liquidity: m.liquidity,
          volume24hr: m.volume24hr,
          clobTokenIds: m.clobTokenIds,
          outcomes: m.outcomes,
          outcomePrices: m.outcomePrices,
          hasRewards: !!m.rewards,
          enableOrderBook: m.enableOrderBook,
        };
      },
    },
    {
      name: 'Price History',
      description: 'Get historical prices for a market',
      test: async () => {
        // Get a market
        const marketsResp = await axios.get(`${GAMMA_API}/markets`, {
          params: { limit: 1, active: true },
        });
        const market = marketsResp.data[0];
        
        if (!market) return { error: 'No markets found' };

        try {
          const response = await axios.get(`${GAMMA_API}/markets/${market.condition_id}/prices`, {
            params: {
              interval: '1h', // Options: 1m, 5m, 1h, 1d
            },
          });
          
          return {
            market: market.question,
            dataPoints: response.data.history?.length || 0,
            recentPrices: response.data.history?.slice(-5).map((h: any) => ({
              t: new Date(h.t * 1000).toISOString(),
              p: h.p,
            })),
            available: true,
          };
        } catch (error: any) {
          return {
            market: market.question,
            available: false,
            error: error.message,
          };
        }
      },
    },
    {
      name: 'Events (grouped markets)',
      description: 'Get event containers with multiple markets',
      test: async () => {
        const response = await axios.get(`${GAMMA_API}/events`, {
          params: {
            limit: 3,
            active: true,
          },
        });
        
        return {
          count: response.data.length,
          examples: response.data.slice(0, 2).map((e: any) => ({
            title: e.title,
            slug: e.slug,
            marketsCount: e.markets?.length || 0,
            volume: e.volume,
            liquidity: e.liquidity,
            markets: e.markets?.slice(0, 2).map((m: any) => m.question),
          })),
        };
      },
    },
    {
      name: 'Order Book Depth',
      description: 'Get live order book for a market',
      test: async () => {
        // Get a market with order book enabled
        const marketsResp = await axios.get(`${GAMMA_API}/markets`, {
          params: { limit: 10, active: true },
        });
        
        const marketWithOB = marketsResp.data.find((m: any) => m.enableOrderBook);
        
        if (!marketWithOB) return { error: 'No markets with order books found' };

        const tokenId = marketWithOB.clobTokenIds?.[0];
        
        if (!tokenId) return { error: 'No token ID found' };

        try {
          const response = await axios.get(`${CLOB_API}/book`, {
            params: {
              token_id: tokenId,
            },
          });
          
          return {
            market: marketWithOB.question,
            tokenId: tokenId,
            bids: response.data.bids?.slice(0, 3),
            asks: response.data.asks?.slice(0, 3),
            bidDepth: response.data.bids?.length || 0,
            askDepth: response.data.asks?.length || 0,
            spread: response.data.spread,
          };
        } catch (error: any) {
          return {
            market: marketWithOB.question,
            available: false,
            error: error.message,
          };
        }
      },
    },
    {
      name: 'Market Search',
      description: 'Search for markets by keyword',
      test: async () => {
        const keywords = ['Trump', 'Bitcoin', 'election'];
        const results: any = {};
        
        for (const keyword of keywords) {
          const response = await axios.get(`${GAMMA_API}/markets`, {
            params: {
              _search: keyword,
              limit: 5,
            },
          });
          results[keyword] = {
            count: response.data.length,
            topMarket: response.data[0]?.question,
            totalVolume: response.data.reduce((sum: number, m: any) => 
              sum + (parseFloat(m.volumeNum) || 0), 0
            ).toFixed(0),
          };
        }
        
        return results;
      },
    },
    {
      name: 'Hot/Trending Markets',
      description: 'Markets sorted by recent activity',
      test: async () => {
        // Try sorting by volume24hr
        const response = await axios.get(`${GAMMA_API}/markets`, {
          params: {
            limit: 10,
            active: true,
            // Note: API may support _sort param
          },
        });
        
        // Sort client-side by 24hr volume
        const sorted = response.data.sort((a: any, b: any) => 
          (parseFloat(b.volume24hr) || 0) - (parseFloat(a.volume24hr) || 0)
        );
        
        return {
          top5ByVolume24hr: sorted.slice(0, 5).map((m: any) => ({
            question: m.question,
            volume24hr: m.volume24hr,
            volumeNum: m.volumeNum,
            lastPrice: m.lastTradePrice,
          })),
        };
      },
    },
    {
      name: 'Price Movement Detection',
      description: 'Find markets with significant price changes',
      test: async () => {
        const response = await axios.get(`${GAMMA_API}/markets`, {
          params: {
            limit: 20,
            active: true,
          },
        });
        
        const movements = response.data
          .filter((m: any) => m.outcomePrices && m.outcomePrices.length >= 2)
          .map((m: any) => {
            const yesPrice = parseFloat(m.outcomePrices[0]) || 0;
            const noPrice = parseFloat(m.outcomePrices[1]) || 0;
            const spread = Math.abs(yesPrice - noPrice);
            const arb = (yesPrice + noPrice) < 1.0 ? (1.0 - yesPrice - noPrice) : 0;
            
            return {
              question: m.question,
              yesPrice,
              noPrice,
              spread: spread.toFixed(4),
              arbitrage: arb.toFixed(4),
              volume24hr: m.volume24hr,
            };
          })
          .sort((a: any, b: any) => parseFloat(b.arbitrage) - parseFloat(a.arbitrage));
        
        return {
          topArbitrageOpportunities: movements.slice(0, 5),
          closeMarkets: movements.filter((m: any) => 
            parseFloat(m.spread) < 0.1
          ).length,
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
      const result = await test.test();
      
      console.log('   ✅ SUCCESS');
      console.log('   Response:', JSON.stringify(result, null, 2).split('\n').map(line => '   ' + line).join('\n'));

      results.push({
        test: test.name,
        status: 'SUCCESS',
        result,
      });

    } catch (error: any) {
      console.log('   ❌ ERROR');
      console.log(`   ${error.message}`);
      
      results.push({
        test: test.name,
        status: 'ERROR',
        error: error.message,
      });
    }

    // Be polite to API
    await sleep(500);
  }

  // Summary
  console.log('\n' + '='.repeat(70));
  console.log('📊 TRADING SIGNALS WE CAN BUILD\n');

  console.log('✅ Volume-based signals:');
  console.log('   - Track 24hr volume spikes (new information entering market)');
  console.log('   - Monitor volume/liquidity ratio (thin markets = opportunity)');
  
  console.log('\n✅ Price-based signals:');
  console.log('   - Arbitrage detection (YES + NO < $1.00)');
  console.log('   - Spread monitoring (tight spread = efficient, wide = mispricing)');
  console.log('   - Price momentum (rapid changes = breaking news)');
  
  console.log('\n✅ Market structure signals:');
  console.log('   - New markets (early mover advantage)');
  console.log('   - Market clustering (events with multiple related markets)');
  console.log('   - Order book depth (liquidity for execution)');

  console.log('\n💡 NO EXTERNAL DATA NEEDED!');
  console.log('   Polymarket API gives us everything for systematic trading.');
  
  console.log('\n' + '='.repeat(70));
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
