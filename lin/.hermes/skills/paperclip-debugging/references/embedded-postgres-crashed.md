### Embedded Postgres Crashed Mid-Run

The embedded PostgreSQL process can crash (OOM, signal, or internal failure) while the Paperclip server itself continues running. Symptoms:

```
Error: connect ECONNREFUSED 127.0.0.1:54329
```

repeated on every database query — issues, auth sessions, feedback exports, everything. The server health endpoint may still return but DB-dependent routes fail.

#### Diagnosis

1. **Check journal for persistent ECONNREFUSED:**
   ```bash
   journalctl --user -u paperclip.service --no-pager | grep "ECONNREFUSED.*54329"
   ```
   If this fills the log continuously, Postgres is dead.

2. **Verify nobody is listening on the Postgres port:**
   ```bash
   lsof -i :54329
   # → no output means Postgres is gone
   ss -tlnp | grep 54329
   ```

3. **Check the server's startup timeline in the journal:**
   ```bash
   journalctl --user -u paperclip.service --no-pager | grep -E "embedded|listening|port"
   ```
   If you see `Using embedded PostgreSQL` followed immediately by DB query failures, Postgres failed to start on that server instance.

4. **Check that the data directory is intact:**
   ```bash
   ls ~/.paperclip/instances/default/db/postmaster.pid
   ```
   Absence of `postmaster.pid` confirms Postgres exited (cleanly or crashed).

#### Fix

Simple restart brings embedded Postgres back:

```bash
systemctl --user restart paperclip.service
```

Wait ~20-30 seconds then verify:

```bash
lsof -i :54329
# → should show postgres PID listening
journalctl --user -u paperclip.service --no-pager -n 10 | grep "listening"
# → "Server listening on ..."
```

**Note:** Paperclip's dev-runner watch mode may auto-restart the server when code changes occur (e.g., during active development). When it does, the new server instance must re-initialize embedded Postgres. If that re-initialization fails, you get this same symptom. A full service restart always works.

**Data safety:** The PGlite/embedded Postgres data directory at `~/.paperclip/instances/default/db/` survives restarts. No migration or data loss occurs from a restart alone. Only delete the data directory (`rm -rf ~/.paperclip/instances/default/db`) if explicitly told to reset the database.
