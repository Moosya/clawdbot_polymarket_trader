-- Add price tracking columns to paper_positions table
-- Run this migration to enable live P&L tracking

ALTER TABLE paper_positions ADD COLUMN current_price REAL;
ALTER TABLE paper_positions ADD COLUMN unrealized_pnl REAL;
ALTER TABLE paper_positions ADD COLUMN unrealized_roi REAL;

-- Add index for faster price updates
CREATE INDEX IF NOT EXISTS idx_positions_status_updated ON paper_positions(status, updated_at DESC);
