/**
 * SQLite Trade Database
 * Persistent storage for high-value trades ($2K+)
 * Replaces JSON file storage for scalability
 */

import Database from 'better-sqlite3';
import * as path from 'path';
import * as fs from 'fs';
import type { TradeFeedTrade } from '../api/trade_feed';

const DATA_DIR = path.join(process.cwd(), 'data');
const DB_FILE = path.join(DATA_DIR, 'trades.db');
const MIN_TRADE_SIZE = 2000; // $2,000 minimum

// Ensure data directory exists
function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

// Initialize database connection
let db: Database.Database | null = null;

function getDatabase(): Database.Database {
  if (!db) {
    ensureDataDir();
    db = new Database(DB_FILE);
    db.pragma('journal_mode = WAL'); // Better concurrency
    initializeSchema();
  }
  return db;
}

// Create tables and indexes
function initializeSchema() {
  const db = getDatabase();
  
  // Check if old schema exists with 'size' column
  const tableInfo = db.pragma('table_info(trades)');
  const hasOldSizeColumn = tableInfo.some((col: any) => col.name === 'size');
  
  if (hasOldSizeColumn) {
    console.log('🔄 Migrating database: removing unused "size" column...');
    
    // SQLite doesn't support DROP COLUMN, so we recreate the table
    db.exec(`
      -- Create new table without size column, add missing fields
      CREATE TABLE trades_new (
        id TEXT PRIMARY KEY,
        trader TEXT NOT NULL,
        marketId TEXT NOT NULL,
        marketSlug TEXT,
        marketQuestion TEXT,
        marketCategory TEXT,
        outcome TEXT,
        side TEXT NOT NULL,
        price REAL NOT NULL,
        sizeUsd REAL NOT NULL,
        timestamp INTEGER NOT NULL,
        feeRateBps INTEGER,
        makerAddress TEXT
      );
      
      -- Copy data (excluding size column, new fields will be NULL for old data)
      INSERT INTO trades_new (id, trader, marketId, side, price, sizeUsd, timestamp, feeRateBps, makerAddress)
      SELECT id, trader, marketId, side, price, sizeUsd, timestamp, feeRateBps, makerAddress
      FROM trades;
      
      -- Drop old table and rename new one
      DROP TABLE trades;
      ALTER TABLE trades_new RENAME TO trades;
      
      -- Recreate indexes
      CREATE INDEX idx_trader ON trades(trader);
      CREATE INDEX idx_market ON trades(marketId);
      CREATE INDEX idx_timestamp ON trades(timestamp DESC);
      CREATE INDEX idx_trader_market ON trades(trader, marketId);
      CREATE INDEX idx_size ON trades(sizeUsd DESC);
    `);
    
    console.log('✅ Database migration complete');
  } else {
    // Fresh database or already migrated
    db.exec(`
      CREATE TABLE IF NOT EXISTS trades (
        id TEXT PRIMARY KEY,
        trader TEXT NOT NULL,
        marketId TEXT NOT NULL,
        marketSlug TEXT,
        marketQuestion TEXT,
        marketCategory TEXT,
        outcome TEXT,
        side TEXT NOT NULL,
        price REAL NOT NULL,
        sizeUsd REAL NOT NULL,
        timestamp INTEGER NOT NULL,
        feeRateBps INTEGER,
        makerAddress TEXT
      );
      
      CREATE INDEX IF NOT EXISTS idx_trader ON trades(trader);
      CREATE INDEX IF NOT EXISTS idx_market ON trades(marketId);
      CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp DESC);
      CREATE INDEX IF NOT EXISTS idx_trader_market ON trades(trader, marketId);
      CREATE INDEX IF NOT EXISTS idx_size ON trades(sizeUsd DESC);
    `);
    
    console.log('✅ SQLite schema initialized');
  }
}

// Store trades (with $2K minimum filter)
export function storeTrades(newTrades: TradeFeedTrade[]): void {
  const db = getDatabase();
  
  // Filter out trades below $2K
  const filteredTrades = newTrades.filter(t => t.sizeUsd >= MIN_TRADE_SIZE);
  
  if (filteredTrades.length === 0) {
    console.log(`💾 Skipped ${newTrades.length} trades (all below $${MIN_TRADE_SIZE})`);
    return;
  }
  
  const insert = db.prepare(`
    INSERT OR REPLACE INTO trades (
      id, trader, marketId, marketSlug, marketQuestion, marketCategory, outcome,
      side, price, sizeUsd, timestamp, feeRateBps, makerAddress
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  
  const insertMany = db.transaction((trades: TradeFeedTrade[]) => {
    for (const trade of trades) {
      insert.run(
        trade.id,
        trade.trader,
        trade.marketId,
        trade.marketSlug || null,
        trade.marketQuestion || null,
        trade.marketCategory || null,
        trade.outcome || null,
        trade.side,
        trade.price,
        trade.sizeUsd,
        trade.timestamp,
        null,  // feeRateBps - not in TradeFeedTrade interface
        null   // makerAddress - not in TradeFeedTrade interface
      );
    }
  });
  
  insertMany(filteredTrades);
  
  const skipped = newTrades.length - filteredTrades.length;
  console.log(`💾 Stored ${filteredTrades.length} trades (${skipped} skipped <$${MIN_TRADE_SIZE}, ${getTradeCount()} total in DB)`);
}

// Read all trades (for backwards compatibility)
export function readTrades(): TradeFeedTrade[] {
  const db = getDatabase();
  const rows = db.prepare('SELECT * FROM trades ORDER BY timestamp DESC').all();
  return rows.map(rowToTrade);
}

// Get recent trades
export function getRecentTrades(limit: number = 200, sinceTimestamp?: number): TradeFeedTrade[] {
  const db = getDatabase();
  
  let query = 'SELECT * FROM trades';
  const params: any[] = [];
  
  if (sinceTimestamp) {
    query += ' WHERE timestamp >= ?';
    params.push(sinceTimestamp);
  }
  
  query += ' ORDER BY timestamp DESC LIMIT ?';
  params.push(limit);
  
  const rows = db.prepare(query).all(...params);
  return rows.map(rowToTrade);
}

// Get trades for a specific wallet
export function getWalletTrades(wallet: string, limit: number = 1000): TradeFeedTrade[] {
  const db = getDatabase();
  const rows = db.prepare(`
    SELECT * FROM trades 
    WHERE LOWER(trader) = LOWER(?)
    ORDER BY timestamp DESC 
    LIMIT ?
  `).all(wallet, limit);
  return rows.map(rowToTrade);
}

// Get trades for a specific market
export function getMarketTrades(marketId: string, limit: number = 1000): TradeFeedTrade[] {
  const db = getDatabase();
  const rows = db.prepare(`
    SELECT * FROM trades 
    WHERE marketId = ?
    ORDER BY timestamp DESC 
    LIMIT ?
  `).all(marketId, limit);
  return rows.map(rowToTrade);
}

// Get whale trades (above threshold)
export function getWhaleTrades(minSize: number = 2000, limit: number = 100): TradeFeedTrade[] {
  const db = getDatabase();
  const rows = db.prepare(`
    SELECT * FROM trades 
    WHERE sizeUsd >= ?
    ORDER BY timestamp DESC 
    LIMIT ?
  `).all(minSize, limit);
  return rows.map(rowToTrade);
}

// Get trade count
export function getTradeCount(): number {
  const db = getDatabase();
  const result = db.prepare('SELECT COUNT(*) as count FROM trades').get() as { count: number };
  return result.count;
}

// Get database stats
export function getDatabaseStats() {
  const db = getDatabase();
  
  const stats = db.prepare(`
    SELECT 
      COUNT(*) as totalTrades,
      COUNT(DISTINCT LOWER(trader)) as uniqueWallets,
      COUNT(DISTINCT marketId) as uniqueMarkets,
      SUM(sizeUsd) as totalVolume,
      MIN(timestamp) as oldestTimestamp,
      MAX(timestamp) as newestTimestamp
    FROM trades
  `).get() as any;
  
  return {
    totalTrades: stats.totalTrades,
    uniqueWallets: stats.uniqueWallets,
    uniqueMarkets: stats.uniqueMarkets,
    totalVolume: stats.totalVolume || 0,
    oldestTrade: stats.oldestTimestamp ? new Date(stats.oldestTimestamp * 1000) : null,
    newestTrade: stats.newestTimestamp ? new Date(stats.newestTimestamp * 1000) : null,
    minTradeSize: MIN_TRADE_SIZE,
  };
}

// Get database file size
export function getDatabaseSize(): string {
  try {
    const stats = fs.statSync(DB_FILE);
    const mb = stats.size / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  } catch {
    return '0 MB';
  }
}

// Migrate from JSON to SQLite
export function migrateFromJSON(jsonFilePath: string): number {
  try {
    if (!fs.existsSync(jsonFilePath)) {
      console.log('No JSON file to migrate');
      return 0;
    }
    
    const jsonData = JSON.parse(fs.readFileSync(jsonFilePath, 'utf-8'));
    const trades = Array.isArray(jsonData) ? jsonData : [];
    
    if (trades.length === 0) {
      console.log('No trades in JSON file');
      return 0;
    }
    
    console.log(`📦 Migrating ${trades.length} trades from JSON to SQLite...`);
    storeTrades(trades);
    
    const migrated = trades.filter(t => t.sizeUsd >= MIN_TRADE_SIZE).length;
    console.log(`✅ Migration complete: ${migrated} trades imported (${trades.length - migrated} skipped <$${MIN_TRADE_SIZE})`);
    
    return migrated;
  } catch (error) {
    console.error('Migration failed:', error);
    return 0;
  }
}

// Convert database row to TradeFeedTrade
function rowToTrade(row: any): TradeFeedTrade {
  return {
    id: row.id,
    trader: row.trader,
    marketId: row.marketId,
    marketSlug: row.marketSlug || '',
    marketQuestion: row.marketQuestion || '',
    marketCategory: row.marketCategory || null,
    outcome: row.outcome || '',
    side: row.side,
    price: row.price,
    sizeUsd: row.sizeUsd,
    timestamp: row.timestamp,
    // conditionId and tokenId not stored in DB, will be null
    conditionId: null,
    tokenId: null,
  };
}

// Close database connection (for cleanup)
export function closeDatabase() {
  if (db) {
    db.close();
    db = null;
  }
}

// Initialize on import
getDatabase();
