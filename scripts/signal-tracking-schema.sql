-- Signal Performance Tracking Schema
-- Tracks all signals, outcomes, and performance metrics

CREATE TABLE IF NOT EXISTS signal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Signal Identification
    signal_id TEXT UNIQUE NOT NULL,  -- unique ID for this signal instance
    signal_type TEXT NOT NULL,        -- whale_cluster, smart_money_divergence, momentum_reversal
    
    -- Market Details
    market_slug TEXT NOT NULL,
    market_name TEXT NOT NULL,
    market_end_date TEXT,
    
    -- Signal Details
    detected_at INTEGER NOT NULL,     -- unix timestamp
    confidence REAL NOT NULL,         -- 0-100
    recommendation TEXT NOT NULL,     -- BUY_YES, BUY_NO, SELL_YES, SELL_NO
    entry_price REAL NOT NULL,        -- recommended entry price
    
    -- Signal Reasoning (JSON)
    reasoning TEXT,                    -- JSON blob with signal-specific details
    
    -- Outcome Tracking
    outcome_known INTEGER DEFAULT 0,   -- 0=pending, 1=resolved
    outcome_checked_at INTEGER,        -- when we last checked the outcome
    market_result TEXT,                -- YES, NO, CANCELLED, etc.
    final_price REAL,                  -- final market price at resolution
    
    -- Performance Metrics
    signal_correct INTEGER,            -- 1=correct, 0=incorrect, NULL=unknown
    edge REAL,                         -- (final_price - entry_price) * direction
    
    -- Trading Status
    position_opened INTEGER DEFAULT 0, -- did we actually trade this?
    position_id INTEGER,               -- FK to positions table if traded
    actual_pnl REAL,                   -- realized P&L if we traded it
    
    -- Metadata
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_signal_type ON signal_history(signal_type);
CREATE INDEX IF NOT EXISTS idx_detected_at ON signal_history(detected_at);
CREATE INDEX IF NOT EXISTS idx_outcome_known ON signal_history(outcome_known);
CREATE INDEX IF NOT EXISTS idx_confidence ON signal_history(confidence);
CREATE INDEX IF NOT EXISTS idx_market_slug ON signal_history(market_slug);

-- View: Signal Performance Summary by Type
CREATE VIEW IF NOT EXISTS signal_performance_summary AS
SELECT 
    signal_type,
    COUNT(*) as total_signals,
    AVG(confidence) as avg_confidence,
    SUM(CASE WHEN outcome_known = 1 THEN 1 ELSE 0 END) as resolved_count,
    SUM(CASE WHEN signal_correct = 1 THEN 1 ELSE 0 END) as correct_count,
    CAST(SUM(CASE WHEN signal_correct = 1 THEN 1 ELSE 0 END) AS REAL) / 
        NULLIF(SUM(CASE WHEN outcome_known = 1 THEN 1 ELSE 0 END), 0) * 100 as accuracy_pct,
    AVG(CASE WHEN outcome_known = 1 THEN edge END) as avg_edge,
    SUM(CASE WHEN position_opened = 1 THEN 1 ELSE 0 END) as positions_opened,
    SUM(actual_pnl) as total_pnl
FROM signal_history
GROUP BY signal_type;

-- View: Recent Unresolved Signals
CREATE VIEW IF NOT EXISTS pending_signals AS
SELECT 
    signal_id,
    signal_type,
    market_name,
    confidence,
    recommendation,
    datetime(detected_at, 'unixepoch') as detected,
    market_end_date,
    position_opened
FROM signal_history
WHERE outcome_known = 0
ORDER BY detected_at DESC;

-- View: High Confidence Failures (for learning)
CREATE VIEW IF NOT EXISTS high_confidence_failures AS
SELECT 
    signal_type,
    market_name,
    confidence,
    recommendation,
    entry_price,
    final_price,
    reasoning,
    datetime(detected_at, 'unixepoch') as detected
FROM signal_history
WHERE outcome_known = 1 
    AND signal_correct = 0 
    AND confidence >= 80
ORDER BY confidence DESC;
