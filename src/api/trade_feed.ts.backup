/**
 * Trade Feed API
 * 
 * Fetches real-time trades from Polymarket Data API
 * Public API - no authentication required!
 */

import axios from 'axios';

export interface TradeFeedTrade {
  id: string;
  timestamp: number;
  marketId: string;
  marketSlug: string;
  marketQuestion: string;
  marketCategory?: string | null;
  outcome: string;
  side: 'BUY' | 'SELL'; // BUY = bullish, SELL = bearish
  price: number;
  sizeUsd: number;
  trader: string; // wallet address
  conditionId?: string | null;
  tokenId?: string | null;
}

const DATA_API_URL = 'https://data-api.polymarket.com';
const GAMMA_API_URL = 'https://gamma-api.polymarket.com';

/**
 * Fetch recent trades from Polymarket Data API
 */
export async function getRecentTrades(limit: number = 200): Promise<TradeFeedTrade[]> {
  try {
    const response = await axios.get(`${DATA_API_URL}/trades`, {
      params: { limit },
    });

    const trades = Array.isArray(response.data) ? response.data : [];

    return trades
      .map((trade: any) => ({
        id: trade.transactionHash || trade.id || `trade-${trade.timestamp}`,
        timestamp: typeof trade.timestamp === 'number' ? trade.timestamp : Date.parse(trade.timestamp) / 1000,
        marketId: trade.asset || trade.conditionId || trade.condition_id,
        marketSlug: trade.slug || trade.eventSlug || trade.market_slug || '',
        marketQuestion: trade.title || trade.question || trade.name || 'Unknown',
        marketCategory: trade.category || trade.marketCategory || null,
        outcome: trade.outcome || trade.name || trade.outcome_name || 'Unknown',
        side: (trade.side === 'BUY' || trade.side === 'SELL') ? trade.side : 'BUY',
        price: parseFloat(trade.price) || 0,
        sizeUsd: parseFloat(trade.size || trade.size_usd || trade.amount || 0),
        trader: trade.proxyWallet || trade.proxy_wallet || trade.trader || trade.wallet || 'unknown',
        conditionId: trade.conditionId || trade.condition_id || null,
        tokenId: trade.token_id || trade.tokenId || null,
      }))
      .filter((trade) => trade.sizeUsd > 0 && trade.timestamp > 0)
      .sort((a, b) => b.timestamp - a.timestamp);
  } catch (error) {
    console.error('Error fetching trades:', error);
    return [];
  }
}

/**
 * Fetch whale trades (above size threshold)
 */
export async function getWhaleTrades(minSizeUsd: number = 1000, limit: number = 200): Promise<TradeFeedTrade[]> {
  const allTrades = await getRecentTrades(limit);
  return allTrades.filter((trade) => trade.sizeUsd >= minSizeUsd);
}

/**
 * Fetch trades for a specific market
 */
export async function getMarketTrades(marketId: string, limit: number = 100): Promise<TradeFeedTrade[]> {
  const allTrades = await getRecentTrades(limit);
  return allTrades.filter((trade) => trade.marketId === marketId);
}

/**
 * Fetch trades for a specific wallet
 */
export async function getWalletTrades(wallet: string, limit: number = 100): Promise<TradeFeedTrade[]> {
  const allTrades = await getRecentTrades(limit);
  return allTrades.filter((trade) => trade.trader.toLowerCase() === wallet.toLowerCase());
}
