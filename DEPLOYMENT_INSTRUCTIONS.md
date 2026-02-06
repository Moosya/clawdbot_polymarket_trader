# Polymarket Filter Deployment Instructions

## Quick Start - Run These Commands on root@174.138.55.80

```bash
# 1. SSH to the server
ssh root@174.138.55.80

# 2. Navigate to workspace
cd /workspace

# 3. Create backups
cp src/strategies/volume_spike_detector.ts src/strategies/volume_spike_detector.ts.bak
cp src/strategies/arbitrage_detector.ts src/strategies/arbitrage_detector.ts.bak
cp src/web/server.ts src/web/server.ts.bak

# 4. Apply arbitrage_detector.ts patch
# Add these lines after the "if (!market.active || market.closed)" check in checkMarket():
```

Then edit each file as follows:

## File 1: src/strategies/arbitrage_detector.ts

Find the line with:
```typescript
if (!market.active || market.closed) {
  return null;
}
```

Add immediately after it:
```typescript
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
```

## File 2: src/web/server.ts

### Change 1: Update volumeDetector initialization (around line 47)

Replace:
```typescript
const volumeDetector = new VolumeSpikeDetector(2.0);
```

With:
```typescript
const volumeDetector = new VolumeSpikeDetector(
  2.0,      // minSpikeMultiplier
  10000,    // minAvgVolume
  50000,    // minLiquidity
  5000,     // min24hrVolume
  false     // excludeSports
);
```

### Change 2: Update scanAllSignals() method

Replace:
```typescript
const spikes = await volumeDetector.scanForSpikes();
latestData.volumeSpikes = spikes;
```

With:
```typescript
const volumeResult = await volumeDetector.scanForSpikes();
latestData.volumeSpikes = volumeResult.spikes;
console.log(volumeDetector.formatFilterStats(volumeResult.stats));
```

## Final Steps

```bash
# 5. Build
npm run build

# 6. Restart
pm2 restart polymarket-web

# 7. Check logs for filter stats
pm2 logs polymarket-web --lines 50
```

Look for output like:
```
📊 Filter Stats:
   Total: 500
   ├─ 24hr vol: 120
   ├─ Avg vol: 180
   ├─ Liquidity: 95
   ├─ Sports: 0
   └─ ✅ Passed: 105
```
