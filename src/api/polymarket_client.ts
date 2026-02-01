import axios, { AxiosInstance } from 'axios';
import * as crypto from 'crypto';
import { Market, OrderBook } from '../types';

export class PolymarketClient {
  private api: AxiosInstance;
  private apiKey: string;
  private apiSecret: string;
  private apiPassphrase: string;
  private baseUrl = 'https://clob.polymarket.com';

  constructor(apiKey: string, apiSecret: string, apiPassphrase: string) {
    this.apiKey = apiKey;
    this.apiSecret = apiSecret;
    this.apiPassphrase = apiPassphrase;

    this.api = axios.create({
      baseURL: this.baseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Generate authentication headers for signed requests
   */
  private generateAuthHeaders(
    method: string,
    path: string,
    body?: string
  ): Record<string, string> {
    const timestamp = Date.now().toString();
    const message = timestamp + method.toUpperCase() + path + (body || '');
    
    const signature = crypto
      .createHmac('sha256', Buffer.from(this.apiSecret, 'base64'))
      .update(message)
      .digest('base64');

    return {
      'POLY-ADDRESS': this.apiKey,
      'POLY-SIGNATURE': signature,
      'POLY-TIMESTAMP': timestamp,
      'POLY-PASSPHRASE': this.apiPassphrase,
    };
  }

  /**
   * Fetch all active markets
   */
  async getMarkets(): Promise<Market[]> {
    try {
      const response = await this.api.get('/markets');
      return response.data;
    } catch (error) {
      console.error('Error fetching markets:', error);
      throw error;
    }
  }

  /**
   * Get orderbook for a specific token/outcome
   */
  async getOrderBook(tokenId: string): Promise<OrderBook> {
    try {
      const response = await this.api.get(`/book`, {
        params: { token_id: tokenId },
      });
      
      return {
        market_id: response.data.market || tokenId,
        asset_id: tokenId,
        bids: response.data.bids || [],
        asks: response.data.asks || [],
        timestamp: Date.now(),
      };
    } catch (error) {
      console.error(`Error fetching orderbook for ${tokenId}:`, error);
      throw error;
    }
  }

  /**
   * Get the best bid/ask prices from orderbook
   */
  getBestPrices(orderbook: OrderBook): { bid: number; ask: number } {
    const bestBid = orderbook.bids.length > 0 ? orderbook.bids[0].price : 0;
    const bestAsk = orderbook.asks.length > 0 ? orderbook.asks[0].price : 1;
    
    return { bid: bestBid, ask: bestAsk };
  }

  /**
   * Fetch market by ID
   */
  async getMarket(marketId: string): Promise<Market> {
    try {
      const response = await this.api.get(`/markets/${marketId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching market ${marketId}:`, error);
      throw error;
    }
  }

  /**
   * Get simplified price for Yes/No (for paper trading)
   * Returns midpoint of bid/ask
   */
  async getTokenPrice(tokenId: string): Promise<number> {
    try {
      const orderbook = await this.getOrderBook(tokenId);
      const { bid, ask } = this.getBestPrices(orderbook);
      
      // Return midpoint
      return (bid + ask) / 2;
    } catch (error) {
      console.error(`Error getting price for token ${tokenId}:`, error);
      return 0.5; // Default fallback
    }
  }
}
