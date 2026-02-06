#!/bin/bash
set -e

echo "🚀 Applying Polymarket Filter Improvements"
echo "==========================================="

cd /workspace

# Step 1: Backups
echo ""
echo "📦 Step 1: Creating backups..."
cp src/strategies/volume_spike_detector.ts src/strategies/volume_spike_detector.ts.bak
cp src/strategies/arbitrage_detector.ts src/strategies/arbitrage_detector.ts.bak
cp src/web/server.ts src/web/server.ts.bak
echo "✅ Backups created"

# Step 2: Update arbitrage_detector.ts
echo ""
echo "📝 Step 2: Updating arbitrage_detector.ts..."

# Find the line with "if (!market.active || market.closed)" and add filters after it
perl -i -pe 'BEGIN{undef $/;} s/(if \(!market\.active \|\| market\.closed\) \{\s+return null;\s+\})/\1\n\n    \/\/ NEW: Add liquidity filter\n    const liquidity = parseFloat(market.liquidity) || 0;\n    if (liquidity < 50000) {\n      return null;\n    }\n\n    \/\/ NEW: Add volume filter\n    const volume24hr = parseFloat(market.volume24hr) || 0;\n    if (volume24hr < 5000) {\n      return null;\n    }/gs' src/strategies/arbitrage_detector.ts

echo "✅ arbitrage_detector.ts updated"

# Step 3: Update server.ts
echo ""
echo "📝 Step 3: Updating server.ts..."

# Update volumeDetector initialization
perl -i -pe 's/const volumeDetector = new VolumeSpikeDetector\(2\.0\);/const volumeDetector = new VolumeSpikeDetector(\n  2.0,      \/\/ minSpikeMultiplier\n  10000,    \/\/ minAvgVolume\n  50000,    \/\/ minLiquidity\n  5000,     \/\/ min24hrVolume\n  false     \/\/ excludeSports\n);/g' src/web/server.ts

# Update scanForSpikes call
perl -i -pe 'BEGIN{undef $/;} s/const spikes = await volumeDetector\.scanForSpikes\(\);\s+latestData\.volumeSpikes = spikes;/const volumeResult = await volumeDetector.scanForSpikes();\n      latestData.volumeSpikes = volumeResult.spikes;\n      console.log(volumeDetector.formatFilterStats(volumeResult.stats));/gs' src/web/server.ts

echo "✅ server.ts updated"

# Step 4: Build
echo ""
echo "🔨 Step 4: Building..."
npm run build

echo ""
echo "✅ Build complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Run: pm2 restart polymarket-web"
echo "   2. Run: pm2 logs polymarket-web"
echo "   3. Look for filter stats in the logs"
echo ""
