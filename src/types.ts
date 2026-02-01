// Core types for Polymarket trading bot

export interface Market {
  id?: string; // Some markets don't have id field
  condition_id?: string;
  question_id?: string;
  question: string;
  description?: string;
  end_date_iso?: string;
  game_start_time?: string;
  active: boolean;
  closed: boolean;
  archived?: boolean;
  accepting_orders: boolean;
  accepting_order_timestamp?: string | null;
  minimum_order_size?: number;
  minimum_tick_size?: number;
  enable_order_book?: boolean;
  market_slug?: string;
  fpmm?: string;
  tokens?: Token[];
  tags?: string[];
  icon?: string;
  image?: string;
  is_50_50_outcome?: boolean;
  neg_risk?: boolean;
  rewards?: {
    rates: any;
    min_size: number;
    max_spread: number;
  };
}

export interface Token {
  token_id: string;
  outcome: string; // Can be "Yes"/"No" or team names, etc.
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
