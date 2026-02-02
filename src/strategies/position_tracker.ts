/**
 * Position Tracker
 * 
 * Calculates P&L, ROI, win rates for traders
 * Tracks positions per wallet per market
 */

import type { TradeFeedTrade } from '../api/trade_feed';

export interface Position {
  wallet: string;
  marketId: string;
  marketQuestion: string;
  netShares: number; // positive = long, negative = short
  totalBuyVolume: number;
  totalSellVolume: number;
  avgEntryPrice: number;
  lastTradeTimestamp: number;
  tradeCount: number;
}

export interface WalletPerformance {
  wallet: string;
  totalVolume: number;
  totalTrades: number;
  activePositions: number;
  closedPositions: number;
  winningPositions: number;
  unrealizedPnL: number;
  realizedPnL: number;
  totalPnL: number;
  winRate: number; // % of closed positions that were profitable
  avgTradeSize: number;
  largestPosition: number;
  lastActivityTimestamp: number;
  profitPerTrade: number;
  roi: number; // totalPnL / totalVolume as percentage
}

/**
 * Calculate positions from trade history
 */
export function calculatePositions(trades: TradeFeedTrade[]): Map<string, Position> {
  const positionMap = new Map<string, Position>();

  // Process trades chronologically (oldest first)
  const chronological = [...trades].sort((a, b) => a.timestamp - b.timestamp);

  for (const trade of chronological) {
    const key = `${trade.trader.toLowerCase()}_${trade.marketId}`;
    const existing = positionMap.get(key);

    if (!existing) {
      const shares = trade.side === 'BUY' ? trade.sizeUsd : -trade.sizeUsd;
      positionMap.set(key, {
        wallet: trade.trader.toLowerCase(),
        marketId: trade.marketId,
        marketQuestion: trade.marketQuestion,
        netShares: shares,
        totalBuyVolume: trade.side === 'BUY' ? trade.sizeUsd : 0,
        totalSellVolume: trade.side === 'SELL' ? trade.sizeUsd : 0,
        avgEntryPrice: trade.price,
        lastTradeTimestamp: trade.timestamp,
        tradeCount: 1,
      });
    } else {
      // Update position
      if (trade.side === 'BUY') {
        // Buying increases position
        const newTotal = existing.totalBuyVolume + trade.sizeUsd;
        existing.avgEntryPrice = (existing.avgEntryPrice * existing.totalBuyVolume + trade.price * trade.sizeUsd) / newTotal;
        existing.totalBuyVolume = newTotal;
        existing.netShares += trade.sizeUsd;
      } else {
        // Selling decreases position
        existing.totalSellVolume += trade.sizeUsd;
        existing.netShares -= trade.sizeUsd;
      }
      existing.lastTradeTimestamp = trade.timestamp;
      existing.tradeCount++;
    }
  }

  return positionMap;
}

/**
 * Calculate wallet performance metrics
 */
export function calculateWalletPerformance(
  trades: TradeFeedTrade[],
  positions: Map<string, Position>,
  currentPrices?: Map<string, number> // marketId -> currentPrice
): WalletPerformance[] {
  const walletMap = new Map<string, WalletPerformance>();

  // Group positions by wallet
  const walletPositions = new Map<string, Position[]>();
  for (const position of positions.values()) {
    const existing = walletPositions.get(position.wallet) || [];
    existing.push(position);
    walletPositions.set(position.wallet, existing);
  }

  // Calculate performance for each wallet
  for (const [wallet, positions] of walletPositions.entries()) {
    const walletTrades = trades.filter((t) => t.trader.toLowerCase() === wallet);
    
    const totalVolume = walletTrades.reduce((sum, t) => sum + t.sizeUsd, 0);
    const totalTrades = walletTrades.length;
    const avgTradeSize = totalVolume / totalTrades;
    const lastActivityTimestamp = Math.max(...walletTrades.map((t) => t.timestamp));

    // Calculate P&L
    let unrealizedPnL = 0;
    let realizedPnL = 0;
    let activePositions = 0;
    let closedPositions = 0;
    let winningPositions = 0;
    let largestPosition = 0;

    for (const position of positions) {
      const isOpen = Math.abs(position.netShares) > 0.01; // Small threshold for floating point
      
      if (isOpen) {
        activePositions++;
        largestPosition = Math.max(largestPosition, Math.abs(position.netShares));
        
        // Estimate unrealized P&L
        const currentPrice = currentPrices?.get(position.marketId) || position.avgEntryPrice;
        unrealizedPnL += (currentPrice - position.avgEntryPrice) * position.netShares;
      } else {
        // Closed position
        closedPositions++;
        const pnl = position.totalSellVolume - position.totalBuyVolume;
        realizedPnL += pnl;
        if (pnl > 0) {
          winningPositions++;
        }
      }
    }

    const totalPnL = unrealizedPnL + realizedPnL;
    const winRate = closedPositions > 0 ? (winningPositions / closedPositions) * 100 : 0;
    const roi = totalVolume > 0 ? (totalPnL / totalVolume) * 100 : 0;
    const profitPerTrade = totalTrades > 0 ? totalPnL / totalTrades : 0;

    walletMap.set(wallet, {
      wallet,
      totalVolume,
      totalTrades,
      activePositions,
      closedPositions,
      winningPositions,
      unrealizedPnL,
      realizedPnL,
      totalPnL,
      winRate,
      avgTradeSize,
      largestPosition,
      lastActivityTimestamp,
      profitPerTrade,
      roi,
    });
  }

  return Array.from(walletMap.values());
}

/**
 * Get top traders by profitability
 */
export function getTopTraders(
  performance: WalletPerformance[],
  minTrades: number = 5,
  limit: number = 20
): WalletPerformance[] {
  return performance
    .filter((p) => p.totalTrades >= minTrades)
    // Only show if they have P&L (either closed positions or unrealized)
    .filter((p) => p.totalPnL !== 0 || p.closedPositions > 0)
    .sort((a, b) => b.totalPnL - a.totalPnL)
    .slice(0, limit);
}

/**
 * Get top traders by ROI
 */
export function getTopTradersByROI(
  performance: WalletPerformance[],
  minTrades: number = 5,
  limit: number = 20
): WalletPerformance[] {
  return performance
    .filter((p) => p.totalTrades >= minTrades)
    .sort((a, b) => b.roi - a.roi)
    .slice(0, limit);
}

/**
 * Get top traders by win rate
 */
export function getTopTradersByWinRate(
  performance: WalletPerformance[],
  minTrades: number = 5,
  minClosedPositions: number = 3,
  limit: number = 20
): WalletPerformance[] {
  return performance
    .filter((p) => p.totalTrades >= minTrades && p.closedPositions >= minClosedPositions)
    .sort((a, b) => b.winRate - a.winRate)
    .slice(0, limit);
}
