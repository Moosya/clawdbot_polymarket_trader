// Core types for Polymarket trading bot

export interface Market {
  id: string;
  question: string;
  end_date_iso: string;
  active: boolean;
  closed: boolean;
  tokens?: Token[];
}

export interface Token {
  token_id: string;
  outcome: string; // "Yes" or "No"
  price?: number;
  winner?: boolean;
}

export interface OrderBook {
  market_id: string;
  asset_id: string;
  bids: Order[];
  asks: Order[];
  timestamp: number;
}

export interface Order {
  price: number;
  size: number;
}

export interface ArbitrageOpportunity {
  market_id: string;
  question: string;
  yes_price: number;
  no_price: number;
  combined_price: number;
  profit_per_share: number;
  profit_percent: number;
  timestamp: number;
}

export interface Trade {
  id: string;
  market_id: string;
  strategy: 'arbitrage' | 'market_making' | 'momentum';
  side: 'yes' | 'no' | 'both';
  entry_price: number;
  shares: number;
  timestamp: number;
  exit_price?: number;
  exit_timestamp?: number;
  profit?: number;
  status: 'open' | 'closed';
}

export interface Portfolio {
  balance: number;
  positions: Position[];
  total_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
}

export interface Position {
  market_id: string;
  yes_shares: number;
  no_shares: number;
  yes_avg_price: number;
  no_avg_price: number;
  current_yes_price: number;
  current_no_price: number;
  unrealized_pnl: number;
}
