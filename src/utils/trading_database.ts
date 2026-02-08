/**
 * Trading Database Utils
 * Access signals and paper positions from SQLite
 */

import Database from 'better-sqlite3';
import * as path from 'path';

// Use shared data directory - same location as trades.db
// On host: /opt/polymarket/data/trading.db
// In sandbox: /workspace/polymarket_runtime/data/trading.db (for testing)
const TRADING_DB_PATH = process.env.TRADING_DB_PATH 
  || path.join(process.cwd(), 'data', 'trading.db');

export interface Signal {
  id: number;
  type: string;
  confidence: number;
  market_slug: string;
  market_question: string;
  outcome: string;
  direction: string;
  price: number;
  details: string;
  timestamp: number;
  position_opened: number;
  created_at: string;
}

export interface PaperPosition {
  id: number;
  signal_id?: number;
  market_slug: string;
  market_question: string;
  outcome: string;
  direction: string;
  entry_price: number;
  entry_time: number;
  size: number;
  confidence?: number;
  status: string;
  exit_price?: number;
  exit_time?: number;
  pnl?: number;
  roi?: number;
  close_reason?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface PortfolioStats {
  total_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  combined_pnl: number;
  total_trades: number;
  open_positions: number;
  closed_positions: number;
  win_rate: number;
  roi: number;
}

let db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!db) {
    console.log(`[Trading DB] Connecting to: ${TRADING_DB_PATH}`);
    try {
      db = new Database(TRADING_DB_PATH, { readonly: false });
      console.log(`[Trading DB] Connected successfully`);
    } catch (error) {
      console.error(`[Trading DB] Failed to connect:`, error);
      throw error;
    }
  }
  return db;
}

/**
 * Get recent signals, optionally filtered by confidence
 */
export function getRecentSignals(minConfidence: number = 0, limit: number = 50): Signal[] {
  const dbConn = getDb();
  const stmt = dbConn.prepare(`
    SELECT * FROM signals 
    WHERE confidence >= ? 
    ORDER BY timestamp DESC 
    LIMIT ?
  `);
  
  return stmt.all(minConfidence, limit) as Signal[];
}

/**
 * Get open paper positions (with current prices parsed from notes)
 */
export function getOpenPositions(): PaperPosition[] {
  const dbConn = getDb();
  const stmt = dbConn.prepare(`
    SELECT * FROM paper_positions 
    WHERE status = 'open' 
    ORDER BY entry_time DESC
  `);
  
  const positions = stmt.all() as PaperPosition[];
  
  // Parse price data from notes field
  return positions.map(pos => {
    if (pos.notes) {
      try {
        const notes = JSON.parse(pos.notes);
        if (notes.price_data) {
          return {
            ...pos,
            current_price: notes.price_data.current_price,
            unrealized_pnl: notes.price_data.unrealized_pnl,
            last_price_update: notes.price_data.last_updated
          } as any;
        }
      } catch (e) {
        // Failed to parse, return as-is
      }
    }
    return pos;
  });
}

/**
 * Get closed paper positions
 */
export function getClosedPositions(limit: number = 100): PaperPosition[] {
  const dbConn = getDb();
  const stmt = dbConn.prepare(`
    SELECT * FROM paper_positions 
    WHERE status = 'closed' 
    ORDER BY exit_time DESC 
    LIMIT ?
  `);
  
  return stmt.all(limit) as PaperPosition[];
}

/**
 * Get portfolio statistics
 */
export function getPortfolioStats(): PortfolioStats {
  const dbConn = getDb();
  
  // Get closed positions stats
  const closedStats = dbConn.prepare(`
    SELECT 
      COUNT(*) as total_closed,
      SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
      SUM(pnl) as realized_pnl
    FROM paper_positions
    WHERE status = 'closed'
  `).get() as any;
  
  // Get open positions with price data
  const openPositions = getOpenPositions();
  const openCount = openPositions.length;
  
  // Calculate unrealized P&L from price data in notes
  let unrealizedPnl = 0;
  for (const pos of openPositions) {
    if ((pos as any).unrealized_pnl !== undefined) {
      unrealizedPnl += (pos as any).unrealized_pnl;
    }
  }
  
  const totalTrades = closedStats.total_closed || 0;
  const realizedPnl = closedStats.realized_pnl || 0;
  const wins = closedStats.wins || 0;
  
  const STARTING_PORTFOLIO = 1000;
  const totalValue = STARTING_PORTFOLIO + realizedPnl + unrealizedPnl;
  const combinedPnl = realizedPnl + unrealizedPnl;
  const roi = combinedPnl / STARTING_PORTFOLIO;
  const winRate = totalTrades > 0 ? wins / totalTrades : 0;
  
  const stats = {
    total_value: totalValue,
    realized_pnl: realizedPnl,
    unrealized_pnl: unrealizedPnl,
    combined_pnl: combinedPnl,
    total_trades: totalTrades,
    open_positions: openCount,
    closed_positions: totalTrades,
    win_rate: winRate,
    roi: roi
  };
  
  console.log('[Trading DB] Portfolio stats:', JSON.stringify(stats, null, 2));
  return stats;
}

/**
 * Get all data for dashboard
 */
export function getTradingDashboardData() {
  return {
    signals: getRecentSignals(70), // Only show ≥70% signals
    openPositions: getOpenPositions(),
    closedPositions: getClosedPositions(20),
    stats: getPortfolioStats(),
    lastUpdate: new Date().toISOString()
  };
}

/**
 * Close database connection
 */
export function closeDb() {
  if (db) {
    db.close();
    db = null;
  }
}
