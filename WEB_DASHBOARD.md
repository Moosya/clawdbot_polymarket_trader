# Web Dashboard

Simple web interface to view live trading signals.

## Quick Start

```bash
npm install
npm run web
```

Then open: **http://localhost:3000**

## Features

✅ **Real-time Monitoring**
- Arbitrage opportunities (YES + NO < $1.00)
- Volume spikes (2x+ above average)
- New markets (last 24 hours)

✅ **Auto-refresh**
- Scans markets every 2 minutes
- Web UI updates every 30 seconds
- No manual refresh needed

✅ **Clean Interface**
- Dark theme
- Color-coded signals
- Mobile-responsive

## Production Deployment

### Option 1: Simple Background Process

```bash
npm run build
nohup node dist/web/server.js > web.log 2>&1 &
```

### Option 2: PM2 (Recommended)

```bash
npm install -g pm2
pm2 start dist/web/server.js --name polymarket-dashboard
pm2 save
pm2 startup  # Enable auto-start on reboot
```

**Auto-restart on git pull:**
```bash
pm2 start ecosystem.config.js
```

Create `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [{
    name: 'polymarket-dashboard',
    script: 'dist/web/server.js',
    watch: ['dist'],
    ignore_watch: ['node_modules', 'logs'],
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    }
  }]
};
```

Then after git pull:
```bash
npm run build  # Rebuild TypeScript
pm2 reload polymarket-dashboard  # Auto-restart
```

### Option 3: Docker

```bash
docker build -t polymarket-dashboard .
docker run -d -p 3000:3000 --name dashboard polymarket-dashboard
```

## Environment Variables

```env
# Optional - for arbitrage detection
CLOB_API_KEY=your_key
CLOB_API_SECRET=your_secret
CLOB_API_PASSPHRASE=your_passphrase

# Server config
PORT=3000
```

## Architecture

- **Frontend:** Vanilla HTML/CSS/JS (no framework bloat)
- **Backend:** Express + TypeScript
- **Data:** Fetches from Polymarket Gamma API
- **State:** In-memory cache (rebuilds on restart)
- **Persistence:** Volume history & known markets saved to JSON files

## URL Endpoints

- `GET /` - Main dashboard
- `GET /api/signals` - JSON API for current signals

## Auto-restart on Code Changes

### Development (nodemon)

```bash
npm install -g nodemon
nodemon --watch src --exec "ts-node src/web/server.ts"
```

### Production (PM2 with watch)

```bash
pm2 start dist/web/server.js --name dashboard --watch dist
```

After `git pull`:
1. `npm run build` - Recompile
2. PM2 detects `dist/` changes and auto-restarts

## Notes

- First run won't show volume spikes (needs history)
- New markets monitor will show all current markets as "new" on first run
- Data persists in `volume_history.json` and `known_markets.json`
