# Active Projects

## 1. Reminder System ⏰
**Status:** In Progress (Telegram only)  
**Location:** `REMINDERS.md`, `TEST_REMINDERS.json`, `HEARTBEAT.md`

**Working:**
- ✅ Data structure for reminders
- ✅ Maria PT reminder scheduled (weekdays 7:30 AM EST)

**TODO:**
- 🔲 Implement actual reminder sending logic (Telegram)
- 🔲 Email integration (needs SMTP setup - see TODO.md)
- 🔲 Test with dummy reminders

---

## 2. Polymarket Trading Bot 📊
**Status:** Deployed (debugging price fetching)  
**Location:** `~/clawdbot_polymarket_trader/` on droplet  
**GitHub:** https://github.com/Moosya/clawdbot_polymarket_trader

**Working:**
- ✅ Bot deployed and running
- ✅ Finding 13 tradeable markets
- ✅ Shared log volume (Krabby can read logs)

**Current Issue:**
- ❌ Successfully pricing 0 markets (orderbook + Gamma API both failing)
- 🔍 Debug logging enabled to diagnose

**TODO:**
- 🔲 Fix price fetching (in progress)
- 🔲 Verify arbitrage detection works with real prices
- 🔲 Dashboard for monitoring (Milestone 2)

---

## 3. Future Projects 🚀
*Add new projects here as they come up*

