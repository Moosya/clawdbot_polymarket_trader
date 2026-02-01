# TODO List

## High Priority 🔥

### Reminders
- [ ] **Implement Telegram reminder sending** (check TEST_REMINDERS.json during heartbeat)
- [ ] Test with 3 dummy reminders
- [ ] Verify Maria PT reminder works (next weekday 7:30 AM EST)

### Polymarket Trader
- [ ] **Debug price fetching** (check logs, see why orderbook/Gamma APIs fail)
- [ ] Fix price sources or find alternative
- [ ] Verify arbitrage detection with real data

---

## Medium Priority 📋

### Reminders
- [ ] Email integration (SMTP gateway needed)
  - Research: SendGrid vs AWS SES vs mailgun
  - Get API key / credentials
  - Implement email sending
  - Test email delivery

### Polymarket Trader
- [ ] Build web dashboard (Milestone 2)
  - Live scan results
  - Opportunity history
  - Market stats
  - P&L tracking when we add execution

---

## Low Priority / Nice to Have 💡

### General
- [ ] Enable elevated access for Krabby (faster iteration)
- [ ] Better error handling across all projects
- [ ] Automated tests

### Polymarket Trader
- [ ] Trade execution (paper → real when proven)
- [ ] Multiple strategies (market making, momentum)
- [ ] Risk management
- [ ] Position tracking

---

## Completed ✅
- ✅ Set up shared log volume (Polymarket bot → Krabby sandbox)
- ✅ Fix OpenClaw config dashboard (symlink workaround)
- ✅ Set update channel to "stable"
- ✅ Create project structure (PROJECTS.md, TODO.md)

