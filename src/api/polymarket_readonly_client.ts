import axios, { AxiosInstance } from 'axios';
import { Market, OrderBook } from '../types';

/**
 * Read-only Polymarket client for fetching market data
 * No private key needed - perfect for paper trading and research
 */
export class PolymarketReadOnlyClient {
  private api: AxiosInstance;
  private baseUrl = 'https://clob.polymarket.com';

  constructor() {
    this.api = axios.create({
      baseURL: this.baseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Fetch all active markets
   * Public endpoint - no auth required
   */
  async getMarkets(): Promise<Market[]> {
    try {
      const response = await this.api.get('/markets');
      
      // Transform response to our Market type
      return response.data.map((m: any) => ({
        id: m.condition_id || m.id,
        question: m.question,
        end_date_iso: m.end_date_iso,
        active: m.active !== false && !m.closed,
        closed: m.closed === true,
        tokens: m.tokens?.map((t: any) => ({
          token_id: t.token_id,
          outcome: t.outcome,
          price: t.price,
        })),
      }));
    } catch (error: any) {
      console.error('Error fetching markets:', error.message);
      throw error;
    }
  }

  /**
   * Get orderbook for a specific token
   * Public endpoint - no auth required
   */
  async getOrderBook(tokenId: string): Promise<OrderBook> {
    try {
      const response = await this.api.get('/book', {
        params: { token_id: tokenId },
      });
      
      return {
        market_id: response.data.market || tokenId,
        asset_id: tokenId,
        bids: (response.data.bids || []).map((b: any) => ({
          price: parseFloat(b.price),
          size: parseFloat(b.size),
        })),
        asks: (response.data.asks || []).map((a: any) => ({
          price: parseFloat(a.price),
          size: parseFloat(a.size),
        })),
        timestamp: Date.now(),
      };
    } catch (error: any) {
      console.error(`Error fetching orderbook for ${tokenId}:`, error.message);
      throw error;
    }
  }

  /**
   * Get best bid/ask prices from orderbook
   */
  getBestPrices(orderbook: OrderBook): { bid: number; ask: number } {
    const bestBid = orderbook.bids.length > 0 ? orderbook.bids[0].price : 0;
    const bestAsk = orderbook.asks.length > 0 ? orderbook.asks[0].price : 1;
    
    return { bid: bestBid, ask: bestAsk };
  }

  /**
   * Get mid price for a token (for paper trading)
   */
  async getTokenPrice(tokenId: string): Promise<number> {
    try {
      const orderbook = await this.getOrderBook(tokenId);
      const { bid, ask } = this.getBestPrices(orderbook);
      
      // For buying (arbitrage), use ask price
      // For midpoint: (bid + ask) / 2
      return ask > 0 ? ask : 0.5;
    } catch (error) {
      console.error(`Error getting price for token ${tokenId}:`, error);
      return 0.5; // Fallback
    }
  }

  /**
   * Get market by condition ID
   */
  async getMarket(conditionId: string): Promise<Market | null> {
    try {
      const markets = await this.getMarkets();
      return markets.find(m => m.id === conditionId) || null;
    } catch (error) {
      console.error(`Error fetching market ${conditionId}:`, error);
      return null;
    }
  }

  /**
   * Get sampling prices - fetch a few markets to test connectivity
   */
  async testConnection(): Promise<boolean> {
    try {
      const markets = await this.getMarkets();
      console.log(`✅ Connection successful - ${markets.length} markets available`);
      return true;
    } catch (error) {
      console.error('❌ Connection failed:', error);
      return false;
    }
  }
}
