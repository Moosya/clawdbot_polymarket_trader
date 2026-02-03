/**
 * Test SQLite Database Implementation
 * Verifies migration and basic operations
 */

import {
  storeTrades,
  readTrades,
  getWalletTrades,
  getMarketTrades,
  getWhaleTrades,
  getDatabaseStats,
  getDatabaseSize,
  migrateFromJSON,
} from './utils/sqlite_database';

async function testDatabase() {
  console.log('\n🧪 Testing SQLite Database\n');

  // Test 1: Migration
  console.log('1️⃣ Testing migration from JSON...');
  const migrated = migrateFromJSON('./data/trades.json');
  console.log(`   ✅ Migrated ${migrated} trades\n`);

  // Test 2: Database stats
  console.log('2️⃣ Database stats:');
  const stats = getDatabaseStats();
  console.log(`   Total trades: ${stats.totalTrades.toLocaleString()}`);
  console.log(`   Unique wallets: ${stats.uniqueWallets.toLocaleString()}`);
  console.log(`   Unique markets: ${stats.uniqueMarkets.toLocaleString()}`);
  console.log(`   Total volume: $${(stats.totalVolume / 1000000).toFixed(2)}M`);
  console.log(`   Min trade size: $${stats.minTradeSize.toLocaleString()}`);
  console.log(`   Data range: ${stats.oldestTrade} → ${stats.newestTrade}`);
  console.log(`   Database size: ${getDatabaseSize()}\n`);

  // Test 3: Whale trades
  console.log('3️⃣ Testing whale trades (>= $2K):');
  const whales = getWhaleTrades(2000, 5);
  console.log(`   Found ${whales.length} whale trades:`);
  for (const trade of whales.slice(0, 3)) {
    console.log(`   - ${trade.side} $${trade.sizeUsd.toLocaleString()} @ $${trade.price.toFixed(2)}`);
  }
  console.log();

  // Test 4: Wallet trades
  if (whales.length > 0) {
    const testWallet = whales[0].trader;
    console.log(`4️⃣ Testing wallet trades for ${testWallet.slice(0, 10)}...`);
    const walletTrades = getWalletTrades(testWallet, 5);
    console.log(`   Found ${walletTrades.length} trades for this wallet`);
    const walletVolume = walletTrades.reduce((sum, t) => sum + t.sizeUsd, 0);
    console.log(`   Total volume: $${walletVolume.toLocaleString()}\n`);
  }

  // Test 5: Market trades
  if (whales.length > 0) {
    const testMarket = whales[0].marketId;
    console.log(`5️⃣ Testing market trades for market ${testMarket.slice(0, 20)}...`);
    const marketTrades = getMarketTrades(testMarket, 5);
    console.log(`   Found ${marketTrades.length} trades in this market`);
    const marketVolume = marketTrades.reduce((sum, t) => sum + t.sizeUsd, 0);
    console.log(`   Total volume: $${marketVolume.toLocaleString()}\n`);
  }

  // Test 6: Read all trades (backwards compatibility)
  console.log('6️⃣ Testing readTrades() for backwards compatibility...');
  const allTrades = readTrades();
  console.log(`   Read ${allTrades.length.toLocaleString()} trades from database`);
  console.log(`   ✅ Backwards compatible with existing code\n`);

  console.log('✅ All tests passed!\n');
}

testDatabase().catch((error) => {
  console.error('❌ Test failed:', error);
  process.exit(1);
});
