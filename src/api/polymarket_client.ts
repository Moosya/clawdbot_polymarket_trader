import axios, { AxiosInstance } from 'axios';
import * as crypto from 'crypto';
import { Market, OrderBook } from '../types';

interface GammaMarket {
  id: string;
  question: string;
  conditionId: string;
  outcomes: string; // JSON array as string
  outcomePrices: string; // JSON array as string ["0.50", "0.50"]
  active: boolean;
  closed: boolean;
  acceptingOrders: boolean;
  clobTokenIds: string; // JSON array as string
  endDateIso: string;
}

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

    // Gamma API for public market data (primary source now!)
    this.gammaApi = axios.create({
      baseURL: this.gammaBaseUrl,
      timeout: 10000,
    });
  }

  /**
   * Fetch all active markets from Gamma API (has prices!)
   */
  async getMarkets(): Promise<Market[]> {
    try {
      console.log('Fetching markets from Gamma API (has built-in prices)...');
      const response = await this.gammaApi.get('/markets', {
        params: {
          closed: false,
          limit: 100, // Get first 100 open markets
        },
      });
      
      const gammaMarkets: GammaMarket[] = response.data;
      
      if (!Array.isArray(gammaMarkets)) {
        console.error('⚠️  Unexpected Gamma response:', typeof gammaMarkets);
        return [];
      }
      
      console.log(`✅ Got ${gammaMarkets.length} markets from Gamma API`);
      
      // Convert Gamma format to our Market format
      const markets: Market[] = gammaMarkets.map(gm => {
        const outcomes = JSON.parse(gm.outcomes || '[]');
        const prices = JSON.parse(gm.outcomePrices || '[]');
        const tokenIds = JSON.parse(gm.clobTokenIds || '[]');
        
        return {
          id: gm.id,
          condition_id: gm.conditionId,
          question: gm.question,
          end_date_iso: gm.endDateIso,
          active: gm.active,
          closed: gm.closed,
          accepting_orders: gm.acceptingOrders,
          tokens: outcomes.map((outcome: string, idx: number) => ({
            token_id: tokenIds[idx] || '',
            outcome: outcome,
            price: parseFloat(prices[idx] || '0'),
          })),
        };
      });
      
      return markets;
    } catch (error: any) {
      if (error.response) {
        console.error('Gamma API Error:', error.response.status, error.response.data);
      } else {
        console.error('Error fetching Gamma markets:', error.message);
      }
      return [];
    }
  }

  /**
   * Get token price - NOW SIMPLE! Just use the price from market data
   */
  async getTokenPrice(tokenId: string, market?: Market): Promise<number | null> {
    try {
      // If we have the market data, just get the price from tokens array
      if (market && market.tokens) {
        const token = market.tokens.find(t => t.token_id === tokenId);
        if (token && typeof token.price === 'number') {
          console.log(`   ✅ Price from market data: $${token.price.toFixed(4)}`);
          return token.price;
        }
      }
      
      console.log(`   ⚠️  No price available for token ${tokenId.substring(0, 16)}...`);
      return null;
    } catch (error: any) {
      console.error(`   ❌ Error getting price: ${error.message}`);
      return null;
    }
  }

  // Keep these for potential future use
  async getOrderBook(tokenId: string): Promise<OrderBook | null> {
    try {
      const response = await this.clobApi.get(`/book`, {
        params: { token_id: tokenId },
      });
      
      return {
        market_id: response.data.market || tokenId,
        asset_id: tokenId,
        bids: response.data.bids || [],
        asks: response.data.asks || [],
        timestamp: Date.now(),
      };
    } catch (error: any) {
      return null;
    }
  }

  getBestPrices(orderbook: OrderBook): { bid: number; ask: number } | null {
    if (!orderbook.bids.length || !orderbook.asks.length) {
      return null;
    }
    
    return {
      bid: orderbook.bids[0].price,
      ask: orderbook.asks[0].price,
    };
  }
}
