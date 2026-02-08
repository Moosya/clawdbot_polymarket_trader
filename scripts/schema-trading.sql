-- Trading Signals & Paper Positions Schema
-- Extends trades.db with auto-trading functionality

-- Store detected trading signals
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL, -- whale_cluster, smart_money_divergence, momentum_reversal
  confidence INTEGER NOT NULL,
  market_slug TEXT NOT NULL,
  market_question TEXT NOT NULL,
  outcome TEXT NOT NULL,
  direction TEXT NOT NULL, -- BUY or SELL
  price REAL NOT NULL,
  details TEXT, -- JSON with signal-specific data
  timestamp INTEGER NOT NULL,
  position_opened INTEGER DEFAULT 0, -- 1 if we traded on this signal
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_confidence ON signals(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(type);
CREATE INDEX IF NOT EXISTS idx_signals_market ON signals(market_slug);

-- Store paper trading positions
CREATE TABLE IF NOT EXISTS paper_positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id INTEGER, -- FK to signals table
  market_slug TEXT NOT NULL,
  market_question TEXT NOT NULL,
  outcome TEXT NOT NULL,
  direction TEXT NOT NULL, -- BUY or SELL
  entry_price REAL NOT NULL,
  entry_time INTEGER NOT NULL,
  size REAL NOT NULL, -- Position size in dollars
  confidence INTEGER, -- Signal confidence when opened
  status TEXT DEFAULT 'open', -- open or closed
  exit_price REAL,
  exit_time INTEGER,
  pnl REAL, -- Profit/loss in dollars
  roi REAL, -- Return on investment (percentage)
  close_reason TEXT, -- manual, exit_signal, expired, etc.
  notes TEXT, -- Trading reasoning/strategy notes
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (signal_id) REFERENCES signals(id)
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON paper_positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_market ON paper_positions(market_slug);
CREATE INDEX IF NOT EXISTS idx_positions_entry_time ON paper_positions(entry_time DESC);

-- Store portfolio stats snapshot (for historical tracking)
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  total_value REAL NOT NULL, -- Current portfolio value
  realized_pnl REAL, -- Closed positions P&L
  unrealized_pnl REAL, -- Open positions P&L
  total_trades INTEGER,
  open_positions INTEGER,
  win_rate REAL,
  roi REAL, -- Overall return
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON portfolio_snapshots(timestamp DESC);
