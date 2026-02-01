#!/usr/bin/env node
/**
 * Scan Twitter for trading signals
 * 
 * Combines trending topics with Polymarket markets to find opportunities
 */

import { TrendMarketMatcher } from './signals/trend_market_matcher';

async function main() {
  console.log('🦀 Twitter → Polymarket Signal Scanner\n');
  console.log('=' .repeat(60));

  const matcher = new TrendMarketMatcher();
  
  try {
    const signals = await matcher.scan();
    
    console.log('\n' + '='.repeat(60));
    console.log(matcher.formatSignals(signals));

    if (signals.length > 0) {
      // Save to file for later analysis
      const fs = require('fs');
      const timestamp = new Date().toISOString();
      const logEntry = {
        timestamp,
        signalCount: signals.length,
        signals: signals.slice(0, 10) // Top 10
      };

      fs.appendFileSync(
        'twitter_signals.jsonl',
        JSON.stringify(logEntry) + '\n'
      );
      console.log('\n📝 Signals logged to twitter_signals.jsonl');
    }

  } catch (error) {
    console.error('❌ Error scanning signals:', error);
    process.exit(1);
  }
}

main();
