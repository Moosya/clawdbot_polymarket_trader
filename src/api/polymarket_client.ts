import axios, { AxiosInstance } from 'axios';
import * as crypto from 'crypto';
import { Market, OrderBook } from '../types';

export class PolymarketClient {
  private clobApi: AxiosInstance;
  private gammaApi: AxiosInstance;
  private apiKey: string;
  private apiSecret: string;
  private apiPassphrase: string;
  private clobBaseUrl = 'https://clob.polymarket.com';
  private gammaBaseUrl = 'https://gamma-api.polymarket.com';

  constructor(apiKey: string, apiSecret: string, apiPassphrase: string) {
    this.apiKey = apiKey;
    this.apiSecret = apiSecret;
    this.apiPassphrase = apiPassphrase;

    this.clobApi = axios.create({
      baseURL: this.clobBaseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Gamma API for public market data
    this.gammaApi = axios.create({
      baseURL: this.gammaBaseUrl,
      timeout: 10000,
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
      const response = await this.clobApi.get('/markets');
      
      // Handle different response structures
      let markets = response.data;
      
      // If data is wrapped in a property, unwrap it
      if (markets && typeof markets === 'object' && !Array.isArray(markets)) {
        // Try common wrapper properties
        if (Array.isArray(markets.data)) {
          markets = markets.data;
        } else if (Array.isArray(markets.markets)) {
          markets = markets.markets;
        }
      }
      
      if (!Array.isArray(markets)) {
        console.error('⚠️  Unexpected markets response structure:', typeof markets);
        console.error('Response keys:', Object.keys(markets || {}));
        return [];
      }
      
      return markets;
    } catch (error: any) {
      if (error.response) {
        console.error('API Error:', error.response.status, error.response.data);
      } else {
        console.error('Error fetching markets:', error.message);
      }
      return [];
    }
  }

  /**
   * Get orderbook for a specific token/outcome
   */
  async getOrderBook(tokenId: string): Promise<OrderBook | null> {
    try {
      console.log(`   📖 Trying orderbook for token ${tokenId.substring(0, 16)}...`);
      const response = await this.clobApi.get(`/book`, {
        params: { token_id: tokenId },
      });
      
      console.log(`   ✅ Orderbook found! Bids: ${response.data.bids?.length || 0}, Asks: ${response.data.asks?.length || 0}`);
      
      return {
        market_id: response.data.market || tokenId,
        asset_id: tokenId,
        bids: response.data.bids || [],
        asks: response.data.asks || [],
        timestamp: Date.now(),
      };
    } catch (error: any) {
      // Orderbook might not exist for low-volume markets
      if (error.response?.status === 404) {
        console.log(`   ❌ Orderbook 404: No orderbook for this token`);
        return null;
      }
      console.error(`   ❌ Orderbook error (${error.response?.status || 'network'}): ${error.message}`);
      if (error.response?.data) {
        console.error(`   Response:`, JSON.stringify(error.response.data).substring(0, 200));
      }
      return null;
    }
  }

  /**
   * Get the best bid/ask prices from orderbook
   */
  getBestPrices(orderbook: OrderBook): { bid: number; ask: number } | null {
    if (!orderbook.bids.length || !orderbook.asks.length) {
      console.log(`   ⚠️  Orderbook empty (bids: ${orderbook.bids.length}, asks: ${orderbook.asks.length})`);
      return null;
    }
    
    const bestBid = orderbook.bids[0].price;
    const bestAsk = orderbook.asks[0].price;
    
    console.log(`   💰 Best prices: Bid $${bestBid.toFixed(4)}, Ask $${bestAsk.toFixed(4)}`);
    
    return { bid: bestBid, ask: bestAsk };
  }

  /**
   * Fetch market by ID
   */
  async getMarket(marketId: string): Promise<Market | null> {
    try {
      const response = await this.clobApi.get(`/markets/${marketId}`);
      return response.data;
    } catch (error: any) {
      console.error(`Error fetching market ${marketId}:`, error.message);
      return null;
    }
  }

  /**
   * Get token price - tries multiple sources
   * 1. Orderbook (best bid/ask midpoint)
   * 2. Gamma API (last traded price)
   * Returns null if no price available
   */
  async getTokenPrice(tokenId: string, conditionId?: string): Promise<number | null> {
    try {
      // Try 1: Get from orderbook
      const orderbook = await this.getOrderBook(tokenId);
      if (orderbook) {
        const prices = this.getBestPrices(orderbook);
        if (prices) {
          // Return midpoint of bid/ask
          const midpoint = (prices.bid + prices.ask) / 2;
          console.log(`   ✅ Using orderbook midpoint: $${midpoint.toFixed(4)}`);
          return midpoint;
        }
      }

      // Try 2: Get from Gamma API (last traded price)
      if (conditionId) {
        console.log(`   📡 Trying Gamma API for condition ${conditionId.substring(0, 16)}...`);
        try {
          const gammaResponse = await this.gammaApi.get(`/markets/${conditionId}`);
          const market = gammaResponse.data;
          
          // Find the token in the market data
          if (market.tokens) {
            const token = market.tokens.find((t: any) => t.token_id === tokenId);
            if (token && typeof token.price === 'number') {
              console.log(`   ✅ Gamma API price: $${token.price.toFixed(4)}`);
              return token.price;
            } else {
              console.log(`   ⚠️  Gamma API: Token not found or no price`);
            }
          } else {
            console.log(`   ⚠️  Gamma API: No tokens in response`);
          }
        } catch (gammaError: any) {
          console.log(`   ❌ Gamma API error (${gammaError.response?.status || 'network'}): ${gammaError.message}`);
          if (gammaError.response?.data) {
            console.log(`   Response:`, JSON.stringify(gammaError.response.data).substring(0, 200));
          }
        }
      } else {
        console.log(`   ⚠️  No condition_id provided, skipping Gamma API`);
      }

      return null;
    } catch (error: any) {
      console.error(`   ❌ Fatal error getting price for token ${tokenId}:`, error.message);
      return null;
    }
  }
}
