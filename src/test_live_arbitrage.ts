#!/usr/bin/env node
/**
 * Test script to scan live Polymarket data for arbitrage opportunities
 * Uses read-only client - no private key needed for market data
 */

import * as dotenv from 'dotenv';
import { PolymarketReadOnlyClient } from './api/polymarket_readonly_client';
import { ArbitrageDetector } from './strategies/arbitrage_detector';

// Load environment variables
dotenv.config();

async function main() {
  console.log('🦀 Starting Live Arbitrage Scanner...\n');

  try {
    // Create read-only client (no credentials needed)
    const client = new PolymarketReadOnlyClient();

    console.log('✅ Client initialized');

    // Test connection
    await client.testConnection();
    console.log();

    // Create arbitrage detector with 0.5% minimum profit threshold
    const detector = new ArbitrageDetector(client as any, 0.5);

    console.log('🔍 Fetching markets...\n');
    
    // Scan all markets
    const opportunities = await detector.scanAllMarkets();

    console.log(`\n📊 Scan complete!`);
    console.log(`Markets scanned: ${opportunities.length > 0 ? 'Multiple' : 'N/A'}`);
    console.log(`Arbitrage opportunities found: ${opportunities.length}\n`);

    if (opportunities.length === 0) {
      console.log('❌ No arbitrage opportunities found at this time.');
      console.log('This is normal - arbitrage windows are rare and close quickly.');
      console.log('Try running this script multiple times or lowering the profit threshold.\n');
    } else {
      console.log('🎯 OPPORTUNITIES DETECTED:\n');
      opportunities.forEach((opp, index) => {
        console.log(`\n${index + 1}. ${detector.formatOpportunity(opp)}`);
      });

      // Show summary stats
      const avgProfit = opportunities.reduce((sum, o) => sum + o.profit_percent, 0) / opportunities.length;
      const bestProfit = Math.max(...opportunities.map(o => o.profit_percent));
      
      console.log('\n📈 Summary Stats:');
      console.log(`Average profit: ${avgProfit.toFixed(2)}%`);
      console.log(`Best opportunity: ${bestProfit.toFixed(2)}%`);
    }

  } catch (error) {
    console.error('❌ Error during scan:', error);
    console.error('\nThis might be due to:');
    console.error('- Network connectivity issues');
    console.error('- Polymarket API rate limiting');
    console.error('- API endpoint changes\n');
  }
}

// Run the scanner
main();
