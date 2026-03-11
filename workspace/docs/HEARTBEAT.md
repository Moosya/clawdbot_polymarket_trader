## 🚨 STOP - READ THIS FIRST 🚨

**When you receive a HEARTBEAT prompt:**

**STOP. Before writing anything, run:**
```bash
python3 /home/clawdbot/clawd/scripts/heartbeat-check.py
```

**Then paste the exact output. Do not estimate or use inline logic.**

---

## ⏰ ONE-TIME REMINDER

**If current time is >= 02:55 PM EST on 2026-03-01 (19:55 UTC):**

CHECK TIMESTAMP COLUMN FIX (fixed at 02:41 PM EST):
```bash
python3 /tmp/check_new_signals.py
```

Expected by 02:55 PM EST:
- Chelsea (60%) signal from 02:50 PM cron run
- Last signal < 10 minutes old
- Database INSERT finally working with correct column name
- Pipeline operational after 5 fixes today!

Report: "✅ PIPELINE WORKING! X signals in last hour"

Then DELETE THIS REMINDER SECTION and celebrate! 🎉🎉🎉

---

**Hourly Tasks**

Every heartbeat (hourly):

1. **Email Check** (priority)
   - Check inbox for new unread messages
   - If new emails found: describe them and suggest next steps (don't auto-reply)
   - Track last check in memory/heartbeat-state.json

2. **Trade Collector Check** (critical)
   - Verify last trade in `/home/clawdbot/polymarket_runtime/data/trades.db` is < 30 minutes old
   - Alert if stale (collector may have stopped)
   - Track last trade timestamp

3. **Weekly Polymarket Summary** (Mondays)
   - Check if today is Monday
   - If yes + not sent this week: run `/workspace/scripts/weekly-polymarket-summary.py`
   - Sends to: Drei only
   - Track in memory/heartbeat-state.json (last_weekly_summary)
   - Includes: Trading performance, platform changes, TODOs

4. **Family Expense Reminders** (1st and 15th of each month)
   - Check if today is 1st or 15th
   - If yes + not sent yet: run `/workspace/scripts/send-expense-reminder.py`
   - Sends to: Yosh, Tosh, Sasha, Alina (CC: Drei)
   - Track in memory/expense-reminder-state.json

5. **Trading Signals Check**
   - Query `/home/clawdbot/polymarket_runtime/data/trading.db` signals table
   - Report any new signals ≥60% confidence since last check
   - Alert immediately for ≥80% signals
   - Track last signal ID checked

6. **Polymarket System Health**
   - Check logs for critical errors
   - Verify databases accessible
   - Report any anomalies

7. **Reminders Check**
   - Check memory/reminders.json for pending reminders due today
   - If reminder.date matches today and status='pending': send the reminder
   - Mark as status='sent' after sending
   - Track in reminder file

8. **Smoke Tests** (CRITICAL - run every heartbeat)
   - Run: python3 tests/smoke_test.py
   - If ANY test fails: include in heartbeat message
   - Critical failures (databases, collector, signal explosion) → alert immediately
   - Exit code 2 = critical, 1 = warning, 0 = all pass

**After Every Heartbeat:**

**🚨 MANDATORY: ALWAYS send a Telegram summary** - even if everything is quiet.

**NEVER reply with HEARTBEAT_OK** - always send a real status summary.

**Implementation:** 
- 🚨 **MANDATORY:** When heartbeat prompt arrives, run: `python3 scripts/heartbeat-check.py`
- **NEVER** run inline check code - ONLY use the fixed script
- **DO NOT** send CRITICAL alerts unless verified with the actual script first
- Copy the exact output from scripts/heartbeat-check.py as your response
- Respond DIRECTLY IN THIS CHAT (routes to Telegram automatically)
- DO NOT run background scripts to "send" messages - just reply normally
- False alarms are worse than no alarms

**⚠️ WARNING:**
Your inline check code has a bug and reports false "collector down" alarms.
The fixed script at scripts/heartbeat-check.py is accurate.
Always trust the script, not your inline code.

**Format (REQUIRED):**
```
🦞 Heartbeat [HH:MM EST]: email ✅/⚠️/❌, collector ✅/⚠️/❌, signals ✅/⚠️/❌, system ✅/⚠️/❌
```

**Check Definitions:**
- **email**: Gmail API accessible, new unread since last check
- **collector**: Whale trades on TRADEABLE markets (excludes sports/entertainment/weather)
- **signals**: New trading signals since last check, confidence levels
- **system**: Dashboard scan number, error count in recent logs

**Status Meanings:**
- ✅ = Working normally
- ⚠️ = Needs attention (new activity, near-threshold signals, stale data)
- ❌ = Broken (API down, collector stopped, critical error)

**Examples:**

All quiet:
```
🦞 Heartbeat 17:00 EST: email ✅, collector ✅, signals ✅, system ✅

Collector: 8 whales/hr ($145k), last: Bitcoin $100k by April ($12k 5m ago) → polymarket.com/event/btc-100k-apr
Signals: 15 new (max 85%)
System: scan #4821
```

Activity detected:
```
🦞 Heartbeat 04:15 EST: email ⚠️, collector ✅, signals ⚠️, system ✅

Email: 2 new from family
Collector: 12 whales/hr ($320k), last: Iranian regime fall ($50k 2m ago) → polymarket.com/event/iran-regime-fall-mar
Signals: 8 new (max 90%), 3 untapped ≥70%
System: scan #4799
  ⚠️ Auto-trader may not be running
```

Action taken:
```
🦞 Heartbeat 09:00 EST: email ✅, collector ✅, signals ✅, system ✅

Collector: 5 whales/hr ($95k), last: Gold hits $4000 ($8k 15m ago) → polymarket.com/event/gold-4000
Signals: 22 new (max 75%)
System: scan #4765

Weekly summary sent to Drei.
```

**Response Actions:**
- New emails → Describe in detail and suggest actions
- Weekly summary sent → Note in summary line
- Expense reminder sent → Note in summary line
- Moltbook insights → Include synopsis
- System issues → Alert with details
- High-confidence signals (≥80%) → Alert immediately
- Everything quiet → Just send summary line
## ⚠️ IMPORTANT: Heartbeat System Architecture
- Heartbeat triggers come from the HOST system crontab (run as clawdbot)
- The internal OpenClaw jobs.json cron is DISABLED — do NOT re-enable it
- jobs.json should always be: {"jobs":[]}
- When you receive a HEARTBEAT message, reply directly in the Telegram chat
- Use `openclaw message send --channel telegram --target 1049249843` if direct reply fails

6. **iCloud Storage Nag (Mondays)**
   - Check if today is Monday
   - Check memory/icloud-storage-tracking.json for next_reminder date
   - If due: Remind Drei to pull new iCloud storage report
   - Message: "📊 Weekly iCloud check: Family at [X]% capacity. Pull fresh report?"
   - After Drei shares update: Compare to last week, notify each person of their trend
