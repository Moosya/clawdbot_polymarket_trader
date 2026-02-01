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

  // First, debug: check what's filtering out markets
  console.log('🔍 DEBUG: Analyzing market filters...\n');
  const allMarkets = await client.getMarkets();
  
  console.log(`📦 Total markets: ${allMarkets.length}`);
  
  const activeCount = allMarkets.filter(m => m.active).length;
  const notClosedCount = allMarkets.filter(m => !m.closed).length;
  const acceptingOrdersCount = allMarkets.filter(m => m.accepting_orders).length;
  const has2TokensCount = allMarkets.filter(m => m.tokens?.length === 2).length;
  
  console.log(`  ✅ active=true: ${activeCount}`);
  console.log(`  ✅ closed=false: ${notClosedCount}`);
  console.log(`  ✅ accepting_orders=true: ${acceptingOrdersCount}`);
  console.log(`  ✅ has 2 tokens: ${has2TokensCount}`);
  
  const activeNotClosed = allMarkets.filter(m => m.active && !m.closed).length;
  const activeNotClosedAccepting = allMarkets.filter(m => m.active && !m.closed && m.accepting_orders).length;
  const fullFilter = allMarkets.filter(m => m.active && !m.closed && m.accepting_orders && m.tokens?.length === 2).length;
  
  console.log(`\n🔗 Combined filters:`);
  console.log(`  active && !closed: ${activeNotClosed}`);
  console.log(`  active && !closed && accepting_orders: ${activeNotClosedAccepting}`);
  console.log(`  active && !closed && accepting_orders && 2 tokens: ${fullFilter}`);
  
  // Show a few examples of markets that fail the filter
  console.log(`\n📋 Sample of first 3 markets:\n`);
  allMarkets.slice(0, 3).forEach((m, idx) => {
    console.log(`${idx + 1}. ${m.question.substring(0, 60)}...`);
    console.log(`   active=${m.active}, closed=${m.closed}, accepting_orders=${m.accepting_orders}, tokens=${m.tokens?.length}`);
  });
  
  console.log('\n' + '─'.repeat(80));
  console.log('Stopping after analysis. Check the filters!\n');
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
