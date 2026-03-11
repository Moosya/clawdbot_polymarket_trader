# Path Usage Guide

## CRITICAL: Always use relative paths, never absolute paths

❌ WRONG (causes "path escapes sandbox" errors):
- /workspace/polymarket_runtime/data/
- /workspace/projects/mission-control/logs/
- /workspace/memory/2026-02-11.md

✅ CORRECT (relative to workspace root):
- polymarket_runtime/data/
- projects/mission-control/logs/
- memory/2026-02-11.md

## Available Paths (use relative)
- `memory/` - Memory files and daily logs
- `scripts/` - All automation scripts
- `polymarket_runtime/data/` - Trading database
- `polymarket_runtime/logs/` - Trading logs
- `projects/mission-control/` - Mission control dashboard
- `signals/` - Signal aggregation results

## Git Repositories
The workspace itself is NOT a git repo. Individual projects are:
- `projects/mission-control/` (has .git)
- `polymarket_runtime/` might have .git
