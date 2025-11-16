# Database Deduplication Analysis

**Date:** 2025-11-17
**Task:** Phase 2.1.1 - Анализ дублированных файлов

## Summary

**Total files analyzed:** 4
**Code duplication:** ~35% (3 duplicate files)
**Recommended action:** Keep File 1, delete Files 2-4, update imports

---

## File Comparison

### File 1: `shared/database.py` ✅ **KEEP - MOST CURRENT**

**Size:** 497 lines
**Status:** Production-ready with Phase 1 security fixes

**Features:**
- ✅ PostgreSQL + SQLite support with auto-detection via `DATABASE_URL`
- ✅ Timezone utilities import: `from shared.timezone_utils import utc_now_iso`
- ✅ Uses `utc_now_iso()` for timestamps (UTC storage)
- ✅ SQL injection protection with input validation (lines 238-239):
  ```python
  hours = int(hours)  # Validate
  limit = int(limit)  # Validate
  ```
- ✅ Proper exception handling with rollback + finally blocks
- ✅ Database connection cleanup in all methods
- ✅ Placeholder-based parameterized queries

**Last updated:** Phase 1 (2025-11-16)

---

### File 2: `shared/database_pg.py` ❌ **DELETE - OBSOLETE**

**Size:** 471 lines
**Status:** Old version without Phase 1 fixes

**Missing features:**
- ❌ No timezone_utils import
- ❌ Uses old `datetime.now().isoformat()` instead of `utc_now_iso()`
- ❌ SQL injection vulnerability in line 229-230:
  ```python
  WHERE timestamp >= NOW() - INTERVAL '%s hours' % hours
  ```
- ❌ No input validation
- ❌ Basic exception handling (no rollback, no finally)
- ❌ No connection cleanup in error cases

**Verdict:** Completely superseded by File 1. Safe to delete.

---

### File 3: `shared/database_sqlite_backup.py` ❌ **DELETE - BACKUP**

**Size:** 346 lines
**Status:** SQLite-only backup, outdated

**Issues:**
- ❌ SQLite ONLY (no PostgreSQL support)
- ❌ No timezone_utils import
- ❌ Uses `datetime.now().isoformat()`
- ❌ **MULTIPLE SQL INJECTION VULNERABILITIES:**
  - Line 147-148: `.format(hours)` in WHERE clause
  - Line 151: `f" AND source = '{source}'"`
  - Line 220: `f" AND alert_type = '{alert_type}'"`
  - Line 333-334: `.format(days)` in DELETE query
- ❌ No proper exception handling
- ❌ No connection cleanup

**Verdict:** Insecure backup file. Delete after migration.

---

### File 4: `miniapp/backend/shared/database.py` ❌ **DELETE - DUPLICATE**

**Size:** 346 lines
**Status:** Exact duplicate of File 3

**Issues:**
- Identical to File 3 (line-by-line match)
- All same vulnerabilities:
  - SQL injection in lines 147-148, 151, 220, 333-334
  - No timezone handling
  - No exception handling
  - No connection cleanup

**Verdict:** Remove entire `miniapp/backend/shared/` directory, use main `shared/database.py` instead.

---

## Functional Differences Table

| Feature | File 1 (KEEP) | File 2 | File 3 | File 4 |
|---------|---------------|--------|--------|--------|
| PostgreSQL Support | ✅ | ✅ | ❌ | ❌ |
| SQLite Support | ✅ | ✅ | ✅ | ✅ |
| Timezone Utils | ✅ `utc_now_iso()` | ❌ | ❌ | ❌ |
| SQL Injection Fix | ✅ | ❌ | ❌ | ❌ |
| Exception Handling | ✅ Full | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic |
| Connection Cleanup | ✅ | ❌ | ❌ | ❌ |
| Parameterized Queries | ✅ | ✅ | ⚠️ Mixed | ⚠️ Mixed |
| Lines of Code | 497 | 471 | 346 | 346 |

---

## Security Issues in Files 2-4

### SQL Injection Vulnerabilities

**File 2 (database_pg.py):**
```python
# Line 229-230 - Unsafe string interpolation
query = """
    WHERE timestamp >= NOW() - INTERVAL '%s hours'
""" % hours
```

**File 3 & 4 (database_sqlite_backup.py, miniapp):**
```python
# Line 147-148 - Unsafe .format()
query = """
    WHERE datetime(timestamp) >= datetime('now', '-{} hours')
""".format(hours)

# Line 151 - Direct f-string injection
query += f" AND source = '{source}'"

# Line 220 - Direct f-string injection
query += f" AND alert_type = '{alert_type}'"

# Line 333-334 - Unsafe .format()
cursor.execute("""
    WHERE datetime(created_at) < datetime('now', '-{} days')
""".format(days))
```

**Impact:** Allows SQL injection if user input is passed to `source`, `alert_type`, or if `hours`/`days`/`limit` are not integers.

---

## Migration Plan

### Step 1: Find all imports (Next task)
```bash
grep -r "from.*database" --include="*.py" | grep -v ".pyc"
grep -r "import.*database" --include="*.py" | grep -v ".pyc"
```

### Step 2: Update imports
Replace all:
- `from shared.database_pg import Database`
- `from miniapp.backend.shared.database import Database`

With:
- `from shared.database import Database`

### Step 3: Test locally with SQLite
```bash
python bot/main.py  # Should use SQLite
```

### Step 4: Test on Render with PostgreSQL
- Deploy to Render
- Verify `DATABASE_URL` detected
- Check logs for "Using PostgreSQL database"

### Step 5: Delete obsolete files
```bash
rm shared/database_pg.py
rm shared/database_sqlite_backup.py
rm -rf miniapp/backend/shared/
```

### Step 6: Update ROADMAP.md
Mark Phase 2.1.1 as completed ✅

---

## Risk Assessment

**Risk Level:** LOW
**Reason:** File 1 is already in production use by bot and price tracker

**Testing Required:**
- ✅ Bot commands (already tested in production)
- ✅ Price tracking (already tested in production)
- ⚠️ Miniapp backend (needs verification)

**Rollback Plan:**
Keep backup files in a separate `archive/` directory for 1 week before permanent deletion.

---

## Next Steps (Phase 2.1.2)

1. Search for all `database.py` imports across codebase
2. Create list of files to update
3. Update imports one by one
4. Test each component
5. Move old files to `archive/` directory
6. Final testing
7. Delete archive after 1 week

**Estimated time:** 30 minutes
