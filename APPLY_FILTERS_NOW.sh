#!/bin/bash
# Run this on your server to apply filter improvements

set -e

echo "🦀 Applying Polymarket filter improvements..."
echo ""

# cd to your repo
cd /root/clawdbot_polymarket_trader

# Backup
echo "📦 Backing up..."
cp src/strategies/volume_spike_detector.ts src/strategies/volume_spike_detector.ts.bak
cp src/web/server.ts src/web/server.ts.bak

# Download the updated file from this workspace
# (You'll need to copy volume_spike_detector_UPDATED.ts content manually)
echo "⚠️  Copy the updated volume_spike_detector_UPDATED.ts content to:"
echo "    src/strategies/volume_spike_detector.ts"
echo ""

# Update server.ts - just 2 quick changes
echo "📝 Update src/web/server.ts manually:"
echo ""
echo "1. Line ~47 - Change:"
echo "   FROM: const volumeDetector = new VolumeSpikeDetector(2.0);"
echo "   TO:   const volumeDetector = new VolumeSpikeDetector(2.0, 10000, 50000, 5000, false);"
echo ""
echo "2. Line ~920 - Change:"
echo "   FROM: const spikes = await volumeDetector.scanForSpikes();"
echo "         latestData.volumeSpikes = spikes;"
echo "   TO:   const volumeResult = await volumeDetector.scanForSpikes();"
echo "         latestData.volumeSpikes = volumeResult.spikes;"
echo "         console.log(volumeDetector.formatFilterStats(volumeResult.stats));"
echo ""

read -p "Press Enter after making the changes..."

# Build
echo ""
echo "🔧 Building..."
npm run build

# Commit
echo ""
echo "📝 Committing..."
git add src/strategies/volume_spike_detector.ts src/web/server.ts
git commit -m "Add liquidity and volume filters to prevent illiquid market alerts

- Min avg volume filter: \$10K (prevents \$200 avg volume markets)
- Min liquidity filter: \$50K (ensures market depth)
- Min 24hr volume: \$5K (raised from \$1K)
- Sports market detection (optional filter, currently disabled)
- Filter statistics tracking

Fixes: Volume spikes on illiquid markets where any trade would
move the entire market (e.g., \$1K trade on \$200 avg volume = 5x weekly volume)"

# Push
echo ""
echo "🚀 Pushing to GitHub..."
git push origin main

# Restart
echo ""
echo "♻️  Restarting app..."
pm2 restart polymarket-web

echo ""
echo "✅ Done! Monitor logs:"
echo "   pm2 logs polymarket-web"
echo ""
echo "You should see filter stats showing:"
echo "   Total: ~2000, Passed: ~50-150"
