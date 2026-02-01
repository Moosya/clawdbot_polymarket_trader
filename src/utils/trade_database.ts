/**
 * Simple JSON File-Based Trade Database
 * Stores trades and performance metrics persistently
 */

import * as fs from 'fs';
import * as path from 'path';
import type { TradeFeedTrade } from '../api/trade_feed';

const DATA_DIR = path.join(process.cwd(), 'data');
const TRADES_FILE = path.join(DATA_DIR, 'trades.json');
const MAX_TRADES = 50000; // Keep last 50k trades

// Ensure data directory exists
function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

// Read trades from file
export function readTrades(): TradeFeedTrade[] {
  try {
    if (!fs.existsSync(TRADES_FILE)) {
      return [];
    }
    const data = fs.readFileSync(TRADES_FILE, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Failed to read trades file:', error);
    return [];
  }
}

// Write trades to file
function writeTrades(trades: TradeFeedTrade[]): void {
  try {
    ensureDataDir();
    fs.writeFileSync(TRADES_FILE, JSON.stringify(trades, null, 2));
  } catch (error) {
    console.error('Failed to write trades file:', error);
  }
}

// Store trades (upsert and deduplicate)
export function storeTrades(newTrades: TradeFeedTrade[]): void {
  const existing = readTrades();
  const tradeMap = new Map(existing.map((t) => [t.id, t]));
  
  // Add/update new trades
  for (const trade of newTrades) {
    tradeMap.set(trade.id, trade);
  }
  
  // Convert back to array, sort by timestamp, limit size
  const allTrades = Array.from(tradeMap.values())
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, MAX_TRADES);
  
  writeTrades(allTrades);
  console.log(`💾 Stored ${newTrades.length} new trades (${allTrades.length} total in DB)`);
}

// Get recent trades
export function getRecentTrades(limit: number = 200, sinceTimestamp?: number): TradeFeedTrade[] {
  const trades = readTrades();
  
  let filtered = trades;
  if (sinceTimestamp) {
    filtered = trades.filter((t) => t.timestamp >= sinceTimestamp);
  }
  
  return filtered.slice(0, limit);
}

// Get trades for a specific wallet
export function getWalletTrades(wallet: string, limit: number = 100): TradeFeedTrade[] {
  const trades = readTrades();
  return trades
    .filter((t) => t.trader.toLowerCase() === wallet.toLowerCase())
    .slice(0, limit);
}

// Get trades for a specific market
export function getMarketTrades(marketId: string, limit: number = 100): TradeFeedTrade[] {
  const trades = readTrades();
  return trades
    .filter((t) => t.marketId === marketId)
    .slice(0, limit);
}

// Get database stats
export function getDatabaseStats() {
  const trades = readTrades();
  const uniqueWallets = new Set(trades.map((t) => t.trader.toLowerCase())).size;
  const uniqueMarkets = new Set(trades.map((t) => t.marketId)).size;
  const totalVolume = trades.reduce((sum, t) => sum + t.sizeUsd, 0);
  
  return {
    totalTrades: trades.length,
    uniqueWallets,
    uniqueMarkets,
    totalVolume,
    oldestTrade: trades.length > 0 ? new Date(trades[trades.length - 1].timestamp * 1000) : null,
    newestTrade: trades.length > 0 ? new Date(trades[0].timestamp * 1000) : null,
  };
}
