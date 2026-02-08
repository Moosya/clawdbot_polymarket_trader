import { appendFileSync } from 'fs';
import { join } from 'path';

const LOG_DIR = process.env.LOG_DIR || './polymarket_bot/logs';
const SIGNAL_LOG = join(LOG_DIR, 'signals.jsonl');

export interface SignalEvent {
  ts?: string;  // Optional because log() adds it automatically
  type: 'SIGNAL' | 'TRADE' | 'POSITION' | 'PERFORMANCE';
  [key: string]: any;
}

export class SignalLogger {
  /**
   * Log a structured event to signals.jsonl
   * Each line is a complete JSON object for easy parsing
   */
  static log(event: SignalEvent): void {
    const entry = {
      ts: new Date().toISOString(),
      ...event
    };
    
    try {
      appendFileSync(SIGNAL_LOG, JSON.stringify(entry) + '\n');
    } catch (error) {
      console.error('❌ Failed to write signal log:', error);
    }
  }

  /**
   * Log an arbitrage signal detection
   */
  static arbitrage(market: string, spread: number, liquidity: number, action: 'PASS' | 'FIRE'): void {
    this.log({
      type: 'SIGNAL',
      signal: 'arbitrage',
      market,
      spread,
      liquidity,
      action
    });
  }

  /**
   * Log a volume spike detection
   */
  static volumeSpike(market: string, volumeChange: number, priceMove: number, action: 'PASS' | 'FIRE', confidence?: number): void {
    this.log({
      type: 'SIGNAL',
      signal: 'volume_spike',
      market,
      volume_change: volumeChange,
      price_move: priceMove,
      action,
      ...(confidence !== undefined && { confidence })
    });
  }

  /**
   * Log a whale trade detection
   */
  static whaleTrade(market: string, size: number, side: 'buy' | 'sell', price: number, action: 'PASS' | 'FIRE'): void {
    this.log({
      type: 'SIGNAL',
      signal: 'whale_trade',
      market,
      trade_size: size,
      side,
      price,
      action
    });
  }

  /**
   * Log a paper/live trade execution
   */
  static trade(mode: 'paper' | 'live', side: 'buy' | 'sell', amount: number, outcome: string, price: number, market: string, reason: string): void {
    this.log({
      type: 'TRADE',
      mode,
      side,
      amount,
      outcome,
      price,
      market,
      reason
    });
  }

  /**
   * Log a position update
   */
  static position(market: string, outcome: string, shares: number, avgPrice: number, currentPrice: number, pnl: number): void {
    this.log({
      type: 'POSITION',
      market,
      outcome,
      shares,
      avg_price: avgPrice,
      current_price: currentPrice,
      pnl,
      pnl_pct: ((currentPrice - avgPrice) / avgPrice * 100).toFixed(2)
    });
  }

  /**
   * Log performance summary
   */
  static performance(period: string, stats: {
    signals_fired: number;
    trades_executed: number;
    win_rate?: number;
    total_pnl?: number;
    [key: string]: any;
  }): void {
    this.log({
      type: 'PERFORMANCE',
      period,
      ...stats
    });
  }

  /**
   * Log generic market state snapshot
   */
  static marketSnapshot(markets: Array<{name: string, volume: number, liquidity: number, volatility?: number}>): void {
    this.log({
      type: 'SIGNAL',
      count: markets.length,
      top_markets: markets.slice(0, 10)
    });
  }
}
