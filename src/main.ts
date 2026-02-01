import * as dotenv from 'dotenv';
import { PolymarketClient } from './api/polymarket_client';
import { ArbitrageDetector } from './strategies/arbitrage_detector';

// Load environment variables
dotenv.config();

async function main() {
  console.log('🦀 Polymarket Arbitrage Bot - Milestone 1\n');

  // Validate environment variables
  const apiKey = process.env.CLOB_API_KEY;
  const apiSecret = process.env.CLOB_API_SECRET;
  const apiPassphrase = process.env.CLOB_API_PASSPHRASE;

  if (!apiKey || !apiSecret || !apiPassphrase) {
    console.error('❌ Missing API credentials in .env file');
    console.error('Required: CLOB_API_KEY, CLOB_API_SECRET, CLOB_API_PASSPHRASE');
    process.exit(1);
  }

  console.log('✅ API credentials loaded');
  console.log('✅ Running in PAPER TRADING mode\n');

  // Initialize client
  const client = new PolymarketClient(apiKey, apiSecret, apiPassphrase);

  // First, let's inspect the raw API response
  console.log('🔍 DEBUG: Fetching markets to inspect structure...\n');
  const markets = await client.getMarkets();
  
  console.log(`📦 Got ${markets.length} markets from API`);
  
  if (markets.length > 0) {
    const firstMarket = markets[0];
    console.log('\n📋 First market structure:');
    console.log(JSON.stringify(firstMarket, null, 2));
    console.log('\n' + '─'.repeat(80) + '\n');
    
    // Check what fields exist
    console.log('Available fields:', Object.keys(firstMarket));
    console.log('Has "active":', 'active' in firstMarket, '=', firstMarket.active);
    console.log('Has "closed":', 'closed' in firstMarket, '=', firstMarket.closed);
    console.log('Has "tokens":', 'tokens' in firstMarket);
    if ('tokens' in firstMarket) {
      console.log('  Number of tokens:', firstMarket.tokens?.length);
      console.log('  Token outcomes:', firstMarket.tokens?.map((t: any) => t.outcome));
    }
    console.log('\n' + '─'.repeat(80) + '\n');
  }
  
  console.log('Stopping after inspection. Fix the code based on actual structure.\n');
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n🦀 Shutting down gracefully...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n\n🦀 Shutting down gracefully...');
  process.exit(0);
});

// Start the bot
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
