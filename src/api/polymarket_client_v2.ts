import { ClobClient, Side } from '@polymarket/clob-client';
import { ethers } from 'ethers';
import { Market, OrderBook } from '../types';

/**
 * Polymarket Client using official @polymarket/clob-client SDK
 * Replaces custom axios implementation with battle-tested official client
 */
export class PolymarketClientV2 {
  private client: ClobClient;
  private chainId: number = 137; // Polygon mainnet

  constructor(privateKey: string, chainId: number = 137) {
    this.chainId = chainId;

    // Initialize the official CLOB client
    this.client = new ClobClient(
      privateKey,
      chainId,
      // Optional: customize host URLs
      // chainId === 137 ? 'https://clob.polymarket.com' : 'https://clob-staging.polymarket.com'
    );
  }

  /**
   * Fetch all active markets
   */
  async getMarkets(): Promise<Market[]> {
    try {
      // Get markets from the official client (returns PaginationPayload)
      const response = await this.client.getMarkets();
      const markets = (response as any).data || response;
      
      // Transform to our Market interface
      return markets.map((m: any) => ({
        id: m.condition_id || m.id,
        question: m.question,
        end_date_iso: m.end_date_iso,
        active: m.active !== false,
        closed: m.closed === true,
        tokens: m.tokens?.map((t: any) => ({
          token_id: t.token_id,
          outcome: t.outcome,
          price: t.price,
          winner: t.winner,
        })),
      }));
    } catch (error) {
      console.error('Error fetching markets:', error);
      throw error;
    }
  }

  /**
   * Get orderbook for a specific token
   */
  async getOrderBook(tokenId: string): Promise<OrderBook> {
    try {
      const book = await this.client.getOrderBook(tokenId);
      
      return {
        market_id: book.market || tokenId,
        asset_id: tokenId,
        bids: book.bids?.map((b: any) => ({
          price: parseFloat(b.price),
          size: parseFloat(b.size),
        })) || [],
        asks: book.asks?.map((a: any) => ({
          price: parseFloat(a.price),
          size: parseFloat(a.size),
        })) || [],
        timestamp: Date.now(),
      };
    } catch (error) {
      console.error(`Error fetching orderbook for ${tokenId}:`, error);
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
   * Get mid price for a token (average of best bid/ask)
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
   * Create and sign an order (for future live trading)
   * Currently just a placeholder - we're in paper trading mode
   */
  async createOrder(params: {
    tokenId: string;
    price: number;
    size: number;
    side: 'BUY' | 'SELL';
  }): Promise<any> {
    try {
      // Convert string to Side enum
      const side = params.side === 'BUY' ? Side.BUY : Side.SELL;
      
      // Use official client's order creation
      const order = await this.client.createOrder({
        tokenID: params.tokenId,
        price: params.price,
        size: params.size,
        side: side,
        // Additional params will be needed for real orders
      });

      console.log('📝 Order created (PAPER TRADING - NOT EXECUTED):', order);
      return order;
    } catch (error) {
      console.error('Error creating order:', error);
      throw error;
    }
  }

  /**
   * Get server time (useful for sync checks)
   */
  async getServerTime(): Promise<number> {
    try {
      const time = await this.client.getServerTime();
      return time;
    } catch (error) {
      console.error('Error getting server time:', error);
      return Date.now();
    }
  }
}

/**
 * Helper function to create client from environment variables
 */
export function createPolymarketClient(): PolymarketClientV2 {
  const privateKey = process.env.POLYMARKET_PRIVATE_KEY;
  
  if (!privateKey) {
    throw new Error('POLYMARKET_PRIVATE_KEY not found in environment');
  }

  const chainId = process.env.POLYMARKET_CHAIN_ID 
    ? parseInt(process.env.POLYMARKET_CHAIN_ID) 
    : 137; // Default to Polygon mainnet

  return new PolymarketClientV2(privateKey, chainId);
}
