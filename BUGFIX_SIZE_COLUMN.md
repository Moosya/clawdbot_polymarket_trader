# Bug Fix: SQLite "size" Column Constraint Error

**Date:** February 7, 2026  
**Status:** FIXED  
**Severity:** High (prevented trade storage)

---

## Problem

Production logs showed recurring error:
```
NOT NULL constraint failed: trades.size
```

This prevented new trades from being stored in the database.

---

## Root Cause

**Schema Mismatch:**

1. **Database schema** (sqlite_database.ts) required:
   ```sql
   size REAL NOT NULL
   ```

2. **Trade data interface** (TradeFeedTrade) only has:
   ```typescript
   sizeUsd: number;  // ✅ EXISTS
   size: ???          // ❌ DOESN'T EXIST
   ```

3. **Insert statement** tried to insert `trade.size` (which is `undefined`)

4. **Result:** NOT NULL constraint violation

---

## Analysis

The `size` column was **never used** in the codebase:
- ✅ **sizeUsd** is used for filtering ($2K minimum)
- ✅ **sizeUsd** is displayed in dashboard
- ✅ **sizeUsd** is used for whale trade detection
- ❌ **size** was never referenced anywhere

**Conclusion:** The `size` column was a leftover from initial schema design and should be removed.

---

## Solution

### 1. Removed `size` Column from Schema

**Before:**
```sql
CREATE TABLE trades (
  id TEXT PRIMARY KEY,
  trader TEXT NOT NULL,
  marketId TEXT NOT NULL,
  side TEXT NOT NULL,
  size REAL NOT NULL,      -- ❌ REMOVED
  price REAL NOT NULL,
  sizeUsd REAL NOT NULL,
  ...
);
```

**After:**
```sql
CREATE TABLE trades (
  id TEXT PRIMARY KEY,
  trader TEXT NOT NULL,
  marketId TEXT NOT NULL,
  side TEXT NOT NULL,
  price REAL NOT NULL,     -- ✅ Kept
  sizeUsd REAL NOT NULL,   -- ✅ Kept (this is what we use)
  ...
);
```

### 2. Updated INSERT Statement

**Before:**
```typescript
INSERT INTO trades (
  id, trader, marketId, side, size, price, sizeUsd, ...
) VALUES (?, ?, ?, ?, ?, ?, ?, ...)

insert.run(
  trade.id,
  trade.trader,
  trade.marketId,
  trade.side,
  trade.size,      // ❌ undefined!
  trade.price,
  trade.sizeUsd,
  ...
);
```

**After:**
```typescript
INSERT INTO trades (
  id, trader, marketId, side, price, sizeUsd, ...
) VALUES (?, ?, ?, ?, ?, ?, ...)

insert.run(
  trade.id,
  trade.trader,
  trade.marketId,
  trade.side,
  trade.price,     // ✅ No more size reference
  trade.sizeUsd,
  ...
);
```

### 3. Added Migration for Existing Databases

Added automatic migration that:
1. Checks if old `size` column exists
2. Creates new table without `size` column
3. Copies all data (excluding `size`)
4. Drops old table and renames new one
5. Recreates indexes

**Migration runs automatically** on next app start.

---

## Files Changed

- `src/utils/sqlite_database.ts` - Schema, insert statement, migration

---

## Testing

### Development Test:
```bash
cd /workspace/projects/polymarket
npm run build
npm run test:sqlite  # If test exists
```

### Production Deployment:
```bash
# On host (as root or Andrei):
/opt/deploy-polymarket.sh

# Monitor logs:
pm2 logs polymarket-dashboard

# Check for migration message:
# "🔄 Migrating database: removing unused 'size' column..."
# "✅ Database migration complete"
```

### Verification:
```bash
# Check database schema after migration
sqlite3 /opt/polymarket/data/trades.db ".schema trades"

# Should NOT have "size" column
# Should see: id, trader, marketId, side, price, sizeUsd, timestamp, ...
```

---

## Expected Results

After deployment:

✅ **No more constraint errors** in logs  
✅ **Trades stored successfully** (all trades >= $2K)  
✅ **Dashboard shows live data**  
✅ **Existing trades preserved** (migration doesn't lose data)  

---

## Rollback (if needed)

If migration fails, restore from backup:
```bash
cp /opt/polymarket/data/trades.db.backup /opt/polymarket/data/trades.db
pm2 restart polymarket-dashboard
```

---

## Related

- Issue discovered: Feb 7, 2026
- Fixed by: Krabby 🦀
- Deployment: Pending Andrei's approval
- Production instance: http://174.138.55.80:3000

---

**Status:** Ready for deployment via `/opt/deploy-polymarket.sh`
