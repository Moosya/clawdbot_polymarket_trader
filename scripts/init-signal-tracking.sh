#!/bin/bash
# Initialize signal tracking database

# Detect base directory
if [ -d "/opt/polymarket" ]; then
    BASE_DIR="/opt/polymarket"
else
    BASE_DIR="/workspace"
fi

DB_PATH="$BASE_DIR/data/trading.db"
SCHEMA_FILE="$BASE_DIR/scripts/signal-tracking-schema.sql"

echo "🗄️  Initializing signal tracking database..."
echo "   Database: $DB_PATH"
echo "   Schema: $SCHEMA_FILE"
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found at $DB_PATH"
    echo "   Please create trading.db first"
    exit 1
fi

# Apply schema
sqlite3 "$DB_PATH" < "$SCHEMA_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Signal tracking tables created"
    echo ""
    echo "📊 Quick stats:"
    sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM signal_history" 2>/dev/null && \
        echo "   Signals logged: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM signal_history")" || \
        echo "   Signals logged: 0 (new table)"
    echo ""
    echo "Next steps:"
    echo "  1. Integrate log-signal.py into your signal detection"
    echo "  2. Run update-signal-outcomes.py periodically (daily cron)"
    echo "  3. Check performance with signal-performance-report.py"
else
    echo "❌ Failed to create tables"
    exit 1
fi
