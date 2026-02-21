/**
 * SQLite Trade Database
 * Stores trades and performance metrics persistently
 */

import Database from 'better-sqlite3';
import * as path from 'path';
import type { TradeFeedTrade } from '../api/trade_feed';

const DATA_DIR = path.join(process.cwd(), 'data');
const TRADES_DB_PATH = path.join(DATA_DIR, 'trades.db');

let db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!db) {
    console.log(`[Trade DB] Connecting to: ${TRADES_DB_PATH}`);
    try {
      db = new Database(TRADES_DB_PATH, { readonly: true });
      console.log(`[Trade DB] Connected successfully`);
    } catch (error) {
      console.error(`[Trade DB] Failed to connect:`, error);
      throw error;
    }
  }
  return db;
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
    conditionId: null,
    tokenId: null,
  };
}

// Read trades from database
export function readTrades(): TradeFeedTrade[] {
  try {
    const dbConn = getDb();
    const rows = dbConn.prepare('SELECT * FROM trades ORDER BY timestamp DESC').all();
    return rows.map(rowToTrade);
  } catch (error) {
    console.error('Failed to read trades from database:', error);
    return [];
  }
}

// Get recent trades
export function getRecentTrades(limit: number = 200, sinceTimestamp?: number): TradeFeedTrade[] {
  try {
    const dbConn = getDb();
    
    let query = 'SELECT * FROM trades';
    const params: any[] = [];
    
    if (sinceTimestamp) {
      query += ' WHERE timestamp >= ?';
      params.push(sinceTimestamp);
    }
    
    query += ' ORDER BY timestamp DESC LIMIT ?';
    params.push(limit);
    
    const rows = dbConn.prepare(query).all(...params);
    return rows.map(rowToTrade);
  } catch (error) {
    console.error('Failed to get recent trades:', error);
    return [];
  }
}

// Get trades for a specific wallet
export function getWalletTrades(wallet: string, limit: number = 100): TradeFeedTrade[] {
  try {
    const dbConn = getDb();
    const rows = dbConn.prepare(`
      SELECT * FROM trades 
      WHERE LOWER(trader) = LOWER(?)
      ORDER BY timestamp DESC 
      LIMIT ?
    `).all(wallet, limit);
    return rows.map(rowToTrade);
  } catch (error) {
    console.error('Failed to get wallet trades:', error);
    return [];
  }
}

// Get trades for a specific market
export function getMarketTrades(marketId: string, limit: number = 100): TradeFeedTrade[] {
  try {
    const dbConn = getDb();
    const rows = dbConn.prepare(`
      SELECT * FROM trades 
      WHERE marketId = ?
      ORDER BY timestamp DESC 
      LIMIT ?
    `).all(marketId, limit);
    return rows.map(rowToTrade);
  } catch (error) {
    console.error('Failed to get market trades:', error);
    return [];
  }
}

// Get database stats
export function getDatabaseStats() {
  try {
    const dbConn = getDb();
    
    const stats = dbConn.prepare(`
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
      totalTrades: stats.totalTrades || 0,
      uniqueWallets: stats.uniqueWallets || 0,
      uniqueMarkets: stats.uniqueMarkets || 0,
      totalVolume: stats.totalVolume || 0,
      oldestTrade: stats.oldestTimestamp ? new Date(stats.oldestTimestamp * 1000) : null,
      newestTrade: stats.newestTimestamp ? new Date(stats.newestTimestamp * 1000) : null,
    };
  } catch (error) {
    console.error('Failed to get database stats:', error);
    return {
      totalTrades: 0,
      uniqueWallets: 0,
      uniqueMarkets: 0,
      totalVolume: 0,
      oldestTrade: null,
      newestTrade: null,
    };
  }
}

// Note: storeTrades() removed - only the collector (sqlite_database.ts) writes to trades.db
// This module is now read-only for dashboard/reporting

// Close database connection
export function closeDb() {
  if (db) {
    db.close();
    db = null;
  }
}
