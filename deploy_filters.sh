#!/bin/bash
set -e

echo "🚀 Deploying Polymarket Filter Improvements"
echo "==========================================="

# Navigate to workspace
cd /workspace

echo ""
echo "📦 Step 1: Backing up files..."
cp src/strategies/volume_spike_detector.ts src/strategies/volume_spike_detector.ts.bak
cp src/strategies/arbitrage_detector.ts src/strategies/arbitrage_detector.ts.bak
cp src/web/server.ts src/web/server.ts.bak
echo "✅ Backups created with .bak extension"

echo ""
echo "📝 Step 2: Reading current files for patching..."

# We'll need to patch the arbitrage_detector and server.ts files
# For now, let's just show what needs to be done

echo ""
echo "⚠️  Manual steps needed:"
echo ""
echo "1. Update arbitrage_detector.ts:"
echo "   Add after active/closed check in checkMarket():"
echo "   ----------------------------------------"
cat << 'EOF'
    // NEW: Add liquidity filter
    const liquidity = parseFloat(market.liquidity) || 0;
    if (liquidity < 50000) {
      return null;
    }

    // NEW: Add volume filter
    const volume24hr = parseFloat(market.volume24hr) || 0;
    if (volume24hr < 5000) {
      return null;
    }
EOF

echo ""
echo "2. Update server.ts:"
echo "   Replace volumeDetector initialization (around line 47):"
echo "   ----------------------------------------"
cat << 'EOF'
// OLD: const volumeDetector = new VolumeSpikeDetector(2.0);
// NEW:
const volumeDetector = new VolumeSpikeDetector(
  2.0,      // minSpikeMultiplier
  10000,    // minAvgVolume
  50000,    // minLiquidity
  5000,     // min24hrVolume
  false     // excludeSports
);
EOF

echo ""
echo "   And update scanAllSignals():"
echo "   ----------------------------------------"
cat << 'EOF'
// OLD:
// const spikes = await volumeDetector.scanForSpikes();
// latestData.volumeSpikes = spikes;

// NEW:
const volumeResult = await volumeDetector.scanForSpikes();
latestData.volumeSpikes = volumeResult.spikes;
console.log(volumeDetector.formatFilterStats(volumeResult.stats));
EOF

echo ""
echo "==========================================="
echo "✅ Backup complete. Ready for manual edits."
