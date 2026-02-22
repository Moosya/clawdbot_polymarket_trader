-- Polymarket Trading Database Schema
-- Run this to initialize a fresh database

CREATE TABLE IF NOT EXISTS trades (
  id TEXT PRIMARY KEY,
  trader TEXT NOT NULL,
  marketId TEXT NOT NULL,
  side TEXT NOT NULL,
  price REAL NOT NULL,
  sizeUsd REAL NOT NULL,
  timestamp INTEGER NOT NULL,
  feeRateBps INTEGER,
  makerAddress TEXT,
  marketSlug TEXT,
  marketQuestion TEXT,
  marketCategory TEXT,
  outcome TEXT
);

CREATE INDEX IF NOT EXISTS idx_trader ON trades(trader);
CREATE INDEX IF NOT EXISTS idx_market ON trades(marketId);
CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trader_market ON trades(trader, marketId);
CREATE INDEX IF NOT EXISTS idx_size ON trades(sizeUsd DESC);
