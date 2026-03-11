# OpenClaw System Architecture

**Last Updated:** 2026-02-20

---

## 🔍 Debugging & Logs

### Gateway Logs
**Location:** `/home/clawdbot/openclaw-gateway.log`

**Use for:**
- Diagnosing heartbeat failures
- Checking tool execution errors
- Understanding why automated tasks didn't run
- Debugging email check failures

**How to check:**
```bash
# Tail live logs
tail -f /home/clawdbot/openclaw-gateway.log

# Search for heartbeat activity
grep -i heartbeat /home/clawdbot/openclaw-gateway.log | tail -20

# Search for specific errors
grep -i "error\|failed" /home/clawdbot/openclaw-gateway.log | tail -20

# Check last 100 lines
tail -100 /home/clawdbot/openclaw-gateway.log
```

**What to look for when email checks fail:**
- Was heartbeat poll sent?
- Did agent wake up and read HEARTBEAT.md?
- Were there any errors executing email check script?
- Did Gmail API timeout or fail?

---

## 📂 File System Structure

### Workspace Symlink
**Important:** `/workspace` is symlinked to the clawd directory

This means:
- ✅ `/workspace/scripts/` → Works from both sandbox and production
- ✅ `/workspace/.credentials/` → Works from both sandbox and production
- ✅ `/workspace/memory/` → Shared state files
- ✅ Scripts using `/workspace/` paths will work correctly on production

**Implications:**
- Scripts written with `/workspace/` paths are portable
- No need for environment-specific path detection for these directories
- Credentials and memory are in the same place everywhere

---

## 🏗️ Environment Layers

### Production (Host)
- **Location:** `/opt/polymarket/` (git repo)
- **Gateway:** Running as service, sends heartbeats
- **Logs:** `/home/clawdbot/openclaw-gateway.log`
- **Databases:** `/opt/polymarket/data/*.db`
- **Workspace:** `/home/clawdbot/clawd/` (symlinked to `/workspace`)

### Sandbox (Docker)
- **Purpose:** Isolated execution environment for agent
- **View:** Can see `/workspace/` but not underlying symlink
- **Limits:** Cannot access host filesystem directly
- **Logs:** Gateway logs not accessible from sandbox

### Development (Git Repo)
- **Location:** `/workspace/projects/polymarket/`
- **Purpose:** Code development, commits, pushes
- **Workflow:** Edit here → commit → push → deploy.sh on production

---

## 🔄 Heartbeat System

### How It Works

1. **Gateway polls** main agent every 30-60 minutes
2. **Agent reads** `HEARTBEAT.md` for task checklist
3. **Agent executes** tasks (email check, expense reminders, etc.)
4. **Agent responds** with status or HEARTBEAT_OK

### Heartbeat Checklist (from HEARTBEAT.md)

1. **Email Check** (hourly)
2. **Weekly Polymarket Summary** (Mondays)
3. **Family Expense Reminders** (1st & 15th)
4. **Moltbook Trading Insights** (every 2 hours)
5. **Polymarket System Health** (every 3-4 hours)

### Why Heartbeats Fail

**Common causes:**
- Gateway service not running
- Agent crashed or hung
- Network issues (can't reach APIs)
- Script errors (check gateway logs)
- State file corruption

**How to diagnose:**
```bash
# 1. Check if gateway is running
ps aux | grep openclaw-gateway

# 2. Check recent heartbeat activity
grep heartbeat /home/clawdbot/openclaw-gateway.log | tail -20

# 3. Check for errors in last hour
tail -100 /home/clawdbot/openclaw-gateway.log | grep -i error

# 4. Verify agent can execute tasks
cd /workspace && python3 scripts/check-moltbook-insights.py
```

---

## 🚨 Known Issue: Alek Email Failure (2026-02-20)

### What Happened
- Alek sent email at 11:29 AM EST
- Email was marked as read but **never responded to**
- Response finally sent at ~7:24 PM EST (8 hours late)

### Root Cause
- Heartbeat checks were not executing
- Agent (sandbox) was not receiving heartbeat polls
- Production agent may not have been properly configured to execute HEARTBEAT.md tasks

### Prevention
- Check `/home/clawdbot/openclaw-gateway.log` regularly
- Verify heartbeat polls are happening
- Test email check manually: `python3 /workspace/scripts/check-emails.py`
- Consider backup cron job for critical checks

---

## 📊 Database Locations

### Production
- **Trading DB:** `/opt/polymarket/data/trading.db`
- **Trades DB:** `/opt/polymarket/data/trades.db`

### Sandbox/Workspace
- **Trading DB:** `/workspace/polymarket_runtime/data/trading.db`
- **Trades DB:** `/workspace/polymarket_runtime/data/trades.db`

**Note:** Production databases are the source of truth. Scripts should auto-detect which to use based on file existence.

---

## 🔐 Credentials

**Location:** `/workspace/.credentials/`

Files:
- `gmail-token.pickle` - Gmail OAuth token (expires, needs periodic reauth)
- `gmail-credentials.json` - Gmail OAuth client ID (permanent)
- `gmail-app-password.txt` - App password (backup, not used)

**Reauth procedure when token expires:**
```bash
# SSH with port forwarding
ssh -L 8080:localhost:8080 clawdbot@[server]

# Run reauth
python3 /workspace/reauth-gmail.py

# Follow browser prompt at localhost:8080
```

---

## 📝 State Files

### Heartbeat State
**File:** `/workspace/memory/heartbeat-state.json`

**Tracks:**
- `last_weekly_summary` - When weekly Polymarket summary was last sent
- `last_moltbook_check` - Last Moltbook scan timestamp
- Other periodic task timestamps

### Expense Reminder State
**File:** `/workspace/memory/expense-reminder-state.json`

**Tracks:**
- `last_sent` - Date of last reminder (YYYY-MM-DD)
- `last_sent_timestamp` - Full ISO timestamp

**Purpose:** Prevent duplicate reminders on same day

---

## 🛠️ Troubleshooting Checklist

When something doesn't work:

1. **Check gateway logs first**
   ```bash
   tail -50 /home/clawdbot/openclaw-gateway.log
   ```

2. **Verify service is running**
   ```bash
   systemctl status openclaw-gateway  # or ps aux | grep openclaw
   ```

3. **Test the specific task manually**
   ```bash
   cd /workspace
   python3 scripts/[script-name].py
   ```

4. **Check for credential issues**
   ```bash
   ls -la /workspace/.credentials/
   # Is gmail-token.pickle recent? (< 7 days old)
   ```

5. **Review state files**
   ```bash
   cat /workspace/memory/heartbeat-state.json
   cat /workspace/memory/expense-reminder-state.json
   ```

6. **Check database accessibility**
   ```bash
   python3 -c "import sqlite3; conn = sqlite3.connect('/opt/polymarket/data/trading.db'); print('OK')"
   ```

---

## 📚 Key Documentation Files

- `HEARTBEAT.md` - What to check every heartbeat
- `AGENTS.md` - Agent behavior and conventions
- `SOUL.md` - Personality and tone
- `MEMORY.md` - Long-term curated memory
- `CURRENT_ISSUES.md` - Active issues and fixes
- `TRADING_PRIVACY.md` - What NEVER to share publicly
- `SYSTEM_ARCHITECTURE.md` - This file

---

## 🔄 Deployment Workflow

1. **Edit code:** `/workspace/projects/polymarket/`
2. **Test locally:** Run scripts manually
3. **Commit:** `git add && git commit`
4. **Push:** `git push origin master`
5. **Deploy:** On production: `cd /opt/polymarket && ./deploy.sh`
6. **Verify:** Check logs, test manually

---

**Remember:** When in doubt, check `/home/clawdbot/openclaw-gateway.log` first!
