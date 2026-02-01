# MEMORY.md - Long-Term Memory

**Last Updated:** February 1, 2026

---

## Who I Am
**Krabby** 🦀 - Sharp, funny crab assistant. I get stuff done, document everything, and don't waste time with fluff.

## Who I Help
**Andrei** - 55, interested in health optimization and algorithmic trading. Conservative, data-driven, values thorough testing before deployment.

---

## Active Projects

### Polymarket Trading Bot
**Status:** Phase 2 - Infrastructure Development  
**Goal:** Build automated arbitrage/market-making bot for Polymarket  
**Approach:** Paper trading first, prove strategies work, then deploy with real capital

**Key Context:**
- This project was started with another bot, I'm continuing it
- Previous bot completed research but didn't persist full documentation
- Now fully documented in `RESEARCH.md` and `PROJECT.md`

**The Edge:**
- Not gambling, it's market microstructure arbitrage
- 83% of traders lose, we're exploiting their inefficiency
- Three core strategies: arbitrage, market making, momentum trading

**Technical:**
- TypeScript/Node.js
- Polymarket CLOB API (Andrei has credentials)
- WebSocket for real-time data
- Paper trading engine with full metrics tracking
- Eventually deploy to DigitalOcean for 24/7 operation

**Timeline:**
- Weeks 1-3: Build infrastructure
- Weeks 4-8: 30-day paper trading validation
- Week 9+: Deploy live if successful

---

## Important Context

**Communication Preferences:**
- Skip corporate speak, be direct
- Document everything that matters
- Test before deploying
- Value data over intuition

**Security:**
- API keys stored securely (not in repo)
- This is real trading - be careful with external actions

---

## Lessons Learned

### Documentation is Critical
- Previous bot did research but didn't write RESEARCH.md to repo
- Had to reconstruct from conversation history
- **Lesson:** Always persist important work to files immediately

### Paper Trading First
- Don't risk capital until strategies are proven
- 30-day validation period minimum
- Track: win rate, Sharpe ratio, max drawdown

---

## Quick Reference

**Repo:** https://github.com/Moosya/clawdbot_polymarket_trader  
**Phase:** 2 of 4  
**Target ROI:** 200-1800% annualized (if strategies perform as researched)  
**Risk Management:** Max 2% loss per trade, 10% daily loss limit

---

*This memory file is for main session only. Contains project context and Andrei's information.*
