# Lessons Learned

## Log Visibility (2026-02-03)
**Problem**: Bot was writing logs to `./logs/console.log` which wasn't visible in Krabby's sandbox.

**Solution**: Modified `package.json` start script to pipe output to `polymarket_bot/logs/console.log` using `tee`.

**Lesson**: Always verify log paths are accessible from sandbox environment (`/workspace/polymarket_bot/logs/` is visible).

## Git Permissions (2026-02-01, 2026-02-03)
**Problem**: Container runs as root, but workspace is owned by UID 1000. Direct git operations fail with permission errors.

**Solution**: Clone repo to `/tmp` (writable by root), make changes there, commit and push.

**Lesson**: Git workflow must use `/tmp/clawdbot_polymarket_trader/` for commits, then user pulls into `/root/clawdbot_polymarket_trader/`.

## Signal Logging Design (2026-02-03)
**Problem**: Console logs are human-readable but hard to parse programmatically.

**Solution**: Created SignalLogger utility that writes JSON Lines format to `signals.jsonl`.

**Lesson**: Machine-readable logs (JSONL) separate from human-readable console output enables better analysis.

---

*Update this file after any correction from the user or when discovering a better pattern.*
