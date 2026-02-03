/**
 * Test script for SignalLogger - demonstrates output format
 * Run: npx ts-node src/test_signal_logger.ts
 */

import { SignalLogger } from './utils/signal_logger';

console.log('🧪 Testing SignalLogger - writing to polymarket_bot/logs/signals.jsonl\n');

// Example 1: Arbitrage signal (passed)
SignalLogger.arbitrage(
  'Will Trump deport 250k-500k people?',
  0.003,  // 0.3% spread (not enough)
  8500,   // $8.5k liquidity
  'PASS'
);

// Example 2: Arbitrage signal (fired)
SignalLogger.arbitrage(
  'Bitcoin above $100k by March?',
  0.015,  // 1.5% spread (good!)
  45000,  // $45k liquidity
  'FIRE'
);

// Example 3: Trade execution
SignalLogger.trade(
  'paper',
  'buy',
  250,  // $250 position
  'yes',
  0.65,
  'Bitcoin above $100k by March?',
  'arbitrage_spread_1.5%'
);

// Example 4: Volume spike detected
SignalLogger.volumeSpike(
  'Trump approval rating above 50%?',
  3.2,   // 320% volume increase
  0.08,  // 8% price move
  'FIRE',
  0.85   // High confidence
);

// Example 5: Whale trade
SignalLogger.whaleTrade(
  'Recession in 2026?',
  25000,  // $25k trade
  'buy',
  0.42,
  'FIRE'
);

// Example 6: Position snapshot
SignalLogger.position(
  'Bitcoin above $100k by March?',
  'yes',
  384.6,     // shares
  0.65,      // avg entry
  0.71,      // current price
  23.08      // $23.08 profit
);

// Example 7: Performance summary
SignalLogger.performance('test_run', {
  signals_fired: 3,
  trades_executed: 1,
  win_rate: 1.0,
  total_pnl: 23.08,
  by_signal: {
    arbitrage: 2,
    volume_spike: 1,
    whale: 1
  }
});

console.log('✅ Test events logged to polymarket_bot/logs/signals.jsonl');
console.log('\nView with:');
console.log('  cat polymarket_bot/logs/signals.jsonl | tail -7');
console.log('  cat polymarket_bot/logs/signals.jsonl | jq');
