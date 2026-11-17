# PostgreSQL 17 Dump/Restore Cross-Architecture

## The \restrict Issue

pg_dump from PostgreSQL 17 adds `\restrict <token>` and `\unrestrict <token>` metadata commands in the dump. These are security features that restrict backslash meta-commands during restore.

### Symptom

```
psql:/tmp/dump.sql:1: error: backslash commands are restricted; only \unrestrict is allowed
ERROR:  syntax error at or near "if"
LINE 1: if so, read its findings and decide with the user whether to...
```

### Root Cause

The `\restrict` command at the top of the dump blocks all backslash commands (including `\unrestrict` at the bottom). When piping via stdin (`psql -d db < dump.sql`), psql processes these but may hit restrictions. Using `psql -f dump.sql` works correctly.

### Fix

Three reliable approaches:

**Approach A (easiest) — Drop/recreate DB, import via `psql -f`:**

```bash
# Stop services connected to DB first
docker compose stop <api-service>

# Drop and recreate
docker exec <postgres> psql -U <user> -d postgres \
  -c "DROP DATABASE IF EXISTS <db>;"
docker exec <postgres> psql -U <user> -d postgres \
  -c "CREATE DATABASE <db>;"

# Copy dump into container
docker cp /path/to/dump.sql <postgres>:/tmp/dump.sql

# Import via -f (NOT stdin pipe)
docker exec <postgres> psql -U <user> -d <db> -f /tmp/dump.sql
```

The `\restrict` errors appear but are non-fatal — all INSERT/COPY/ALTER statements execute.

**Approach B — Strip restrict commands:**

```bash
# Remove the \restrict and \unrestrict lines
grep -v '^\\\\restrict\|^\\\\unrestrict' dump.sql > dump-clean.sql
psql -U <user> -d <db> < dump-clean.sql
```

**Approach C — Use pg_restore (custom format):**

```bash
pg_dump -Fc --no-owner --no-acl -f dump.dump
pg_restore -U <user> -d <db> --no-owner --no-acl dump.dump
```

## Table count verification

```sql
SELECT schemaname, tablename, n_live_tup 
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC;
```

Or simpler:

```sql
SELECT count(*) FROM memories;
-- Should match source count
```
