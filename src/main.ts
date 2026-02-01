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
  console.log('✅ Running in PAPER TRADING mode');
  
  // DEBUG MODE ON to see what's failing
  const DEBUG_MODE = true;
  const SAMPLE_SIZE = 3; // Check just 3 markets to see detailed errors
  
  console.log('🔍 DEBUG MODE: Checking first 3 markets with detailed logging\n');
  console.log('💡 Arbitrage = when Outcome1 + Outcome2 < $1.00\n');

  // Initialize client
  const client = new PolymarketClient(apiKey, apiSecret, apiPassphrase);

  // Initialize arbitrage detector (minimum 0.5% profit)
  const detector = new ArbitrageDetector(client, 0.5, DEBUG_MODE);

  // Main loop: scan for arbitrage every 60 seconds
  const scanInterval = 60000; // 60 seconds
  let scanCount = 0;

  console.log(`Starting arbitrage scanner (checking every ${scanInterval / 1000}s)...\n`);

  while (true) {
    try {
      scanCount++;
      const startTime = Date.now();

      console.log(`[Scan #${scanCount}] ${new Date().toISOString()}`);

      // Scan markets (sample size for debugging)
      const { opportunities, closest, marketsChecked } = await detector.scanAllMarkets(SAMPLE_SIZE);

      const duration = ((Date.now() - startTime) / 1000).toFixed(2);

      console.log(`✅ Successfully priced ${marketsChecked} markets`);

      if (opportunities.length > 0) {
        console.log(`\n🎉 Found ${opportunities.length} arbitrage opportunities!\n`);

        // Sort by profit percent (highest first)
        opportunities.sort((a, b) => b.profit_percent - a.profit_percent);

        // Print all opportunities
        opportunities.forEach(opp => {
          console.log(detector.formatOpportunity(opp));
        });
      } else {
        console.log(`❌ No arbitrage opportunities found (scan took ${duration}s)`);
      }

      // Show closest markets (to prove we have real data)
      console.log(detector.formatClosest(closest));

      console.log('\n' + '─'.repeat(80) + '\n');

      // Wait before next scan
      await sleep(scanInterval);
    } catch (error) {
      console.error('Error in main loop:', error);
      console.log('Retrying in 60 seconds...\n');
      await sleep(60000);
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
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
