#!/usr/bin/env node
/**
 * Test Volume Spike Detector
 * 
 * Run this to build initial volume history and see current spikes
 */

import { VolumeSpikeDetector } from './strategies/volume_spike_detector';

async function main() {
  console.log('🦀 Volume Spike Detector - Test Run\n');
  console.log('=' .repeat(70));

  // Initialize detector (2x spike threshold)
  const detector = new VolumeSpikeDetector(2.0);

  console.log(detector.getSummary());
  console.log('\n🔍 Scanning markets for volume spikes...\n');

  try {
    const spikes = await detector.scanForSpikes();

    if (spikes.length === 0) {
      console.log('✅ No volume spikes detected (this is normal on first run)');
      console.log('   Run this script a few more times over the next hours/days');
      console.log('   to build up volume history and detect spikes.\n');
    } else {
      console.log(`🔥 Found ${spikes.length} volume spikes!\n`);

      spikes.forEach(spike => {
        console.log(detector.formatSpike(spike));
      });
    }

    console.log(detector.getSummary());

    console.log('\n💡 NEXT STEPS:');
    console.log('   1. Run this script every few hours to build history');
    console.log('   2. Or integrate into main bot loop');
    console.log('   3. Volume spikes often precede price movements');
    console.log('   4. Combine with arbitrage detector for best signals\n');

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

main();
