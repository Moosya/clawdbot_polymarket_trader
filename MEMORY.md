# MEMORY.md - Long-Term Memory

**Last Updated:** February 6, 2026

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

**Recent Progress (Feb 1-4):**
- ✅ SQLite database migration (Feb 2) - Unlimited trade storage, $2K minimum filter
- ✅ Signal logging system (Feb 3) - JSON Lines format for analyzing strategy performance
- ✅ Workflow documentation (Feb 3) - Best practices for development
- 🔄 Twitter sentiment integration (Feb 1) - Built but needs testing
- 📋 Wallet/market drill-down pages (planned) - See DRILLDOWN_FEATURES.md

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

### Git Workflow (SOLVED - Feb 6, 2026) ✅

**THE ISSUE WAS:**
- Workspace `/workspace` is owned by UID 1000 (host clawdbot user)
- Container runs as root (UID 0)
- Git blocks operations due to ownership mismatch
- Container root filesystem is read-only, can't persist git config

**THE SOLUTION (WORKING NOW):**
GitHub token stored in `/workspace/.env` as `GITHUB_TOKEN`

**To push changes, use the helper script:**
```bash
bash /workspace/git-push-helper.sh "Your commit message"
```

**What the script does:**
1. Clones repo fresh into `/tmp` (owned by root, no permission issues)
2. Sets authenticated remote URL using token from .env
3. Copies all changed files from `/workspace` to `/tmp/repo`
4. Commits and pushes to GitHub

**Key files:**
- `/workspace/.env` - Contains `GITHUB_TOKEN=ghp_...` (gitignored, safe)
- `/workspace/git-push-helper.sh` - Automated push script
- `/workspace/CONTAINER_RESTART_PROCEDURES.md` - Full documentation

**This persists across container restarts because:**
- Token is in .env (mounted from host)
- Helper script is in workspace (mounted from host)
- Both survive container rebuilds

**NEVER commit the token to the repo - GitHub will block the push!**

### File Writing in Sandbox
- ✅ Use `write` tool for creating/editing files
- ❌ Shell redirects (`echo > file`) fail (permission issues)
- ✅ Read with `read` tool or `cat`
- Skills can be bootstrapped from /opt tools

---

## Quick Reference

**Repo:** https://github.com/Moosya/clawdbot_polymarket_trader  
**Phase:** 2 of 4  
**Target ROI:** 200-1800% annualized (if strategies perform as researched)  
**Risk Management:** Max 2% loss per trade, 10% daily loss limit

---

*This memory file is for main session only. Contains project context and Andrei's information.*
