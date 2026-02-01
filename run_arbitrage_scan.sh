#!/bin/bash
# Quick script to run the live arbitrage scanner

echo "🦀 Polymarket Live Arbitrage Scanner"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found!"
    echo "Create .env with your Polymarket credentials:"
    echo ""
    echo "POLYMARKET_PRIVATE_KEY=0x..."
    echo "POLYMARKET_CHAIN_ID=137"
    echo ""
    exit 1
fi

# Run TypeScript directly with ts-node
npx ts-node src/test_live_arbitrage.ts
