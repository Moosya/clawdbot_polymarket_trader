/**
 * Trading Database Utils
 * Access signals and paper positions from SQLite
 */

import Database from 'better-sqlite3';
import * as path from 'path';

// Use shared data directory - on host: /opt/polymarket/data/trading.db
const TRADING_DB_PATH = path.resolve(process.env.TRADING_DB_PATH || path.join(__dirname, '../../data/trading.db'));

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
    db = new Database(TRADING_DB_PATH, { readonly: false });
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
 * Get open paper positions
 */
export function getOpenPositions(): PaperPosition[] {
  const dbConn = getDb();
  const stmt = dbConn.prepare(`
    SELECT * FROM paper_positions 
    WHERE status = 'open' 
    ORDER BY entry_time DESC
  `);
  
  return stmt.all() as PaperPosition[];
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
  
  // Get open positions stats
  const openStats = dbConn.prepare(`
    SELECT 
      COUNT(*) as open_count,
      SUM(size) as total_invested
    FROM paper_positions
    WHERE status = 'open'
  `).get() as any;
  
  const totalTrades = closedStats.total_closed || 0;
  const openPositions = openStats.open_count || 0;
  const realizedPnl = closedStats.realized_pnl || 0;
  const wins = closedStats.wins || 0;
  
  // For unrealized P&L, we'd need current prices - TODO: implement price fetching
  const unrealizedPnl = 0; // Placeholder
  
  const STARTING_PORTFOLIO = 1000;
  const totalValue = STARTING_PORTFOLIO + realizedPnl + unrealizedPnl;
  const combinedPnl = realizedPnl + unrealizedPnl;
  const roi = combinedPnl / STARTING_PORTFOLIO;
  const winRate = totalTrades > 0 ? wins / totalTrades : 0;
  
  return {
    total_value: totalValue,
    realized_pnl: realizedPnl,
    unrealized_pnl: unrealizedPnl,
    combined_pnl: combinedPnl,
    total_trades: totalTrades,
    open_positions: openPositions,
    closed_positions: totalTrades,
    win_rate: winRate,
    roi: roi
  };
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
