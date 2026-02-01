#!/usr/bin/env node
/**
 * Test New Market Monitor
 * 
 * Discovers fresh markets on Polymarket
 */

import { NewMarketMonitor } from './strategies/new_market_monitor';

async function main() {
  console.log('🦀 New Market Monitor - Test Run\n');
  console.log('=' .repeat(70));

  // Initialize monitor (24hr threshold)
  const monitor = new NewMarketMonitor(24);

  console.log(monitor.getSummary());
  console.log('\n🔍 Scanning for new markets...\n');

  try {
    const newMarkets = await monitor.scanForNewMarkets();

    if (newMarkets.length === 0) {
      console.log('✅ No new markets detected');
      console.log('   (This is normal if all current markets are already known)');
      console.log('   Run this script periodically to catch fresh markets as they appear\n');
    } else {
      console.log(`🆕 Found ${newMarkets.length} new markets!\n`);

      newMarkets.forEach(market => {
        console.log(monitor.formatNewMarket(market));
      });
    }

    console.log(monitor.getSummary());

    console.log('\n💡 TRADING STRATEGY:');
    console.log('   1. New markets are often mispriced (crowd hasn\'t found them yet)');
    console.log('   2. Check for arbitrage opportunities (YES + NO < $1.00)');
    console.log('   3. Low liquidity = higher slippage but bigger opportunity');
    console.log('   4. Early positions can be unwound when market matures\n');

    console.log('💡 NEXT STEPS:');
    console.log('   1. Run this script hourly to catch new markets ASAP');
    console.log('   2. Or integrate into main bot loop');
    console.log('   3. Combine with arbitrage + volume spike detectors');
    console.log('   4. Consider setting up alerts (email/telegram) for new markets\n');

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

main();
