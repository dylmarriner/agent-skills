#!/bin/bash
# Backup All — Full stack backup script
# Part of backup-system skill

set -e

BACKUP_DIR="/home/rabuntu/backups/$(date +%Y%m%d-%H%M)"
mkdir -p "$BACKUP_DIR"
LOG="$BACKUP_DIR/backup-log.txt"

echo "==========================================" | tee -a "$LOG"
echo "  FULL BACKUP — $(date '+%Y-%m-%d %H:%M %Z')" | tee -a "$LOG"
echo "  Destination: $BACKUP_DIR" | tee -a "$LOG"
echo "==========================================" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# 1. Docker Volumes
echo "--- Docker Volumes ---" | tee -a "$LOG"
for vol in $(docker volume ls -q 2>/dev/null); do
  echo "  Backing up: $vol ..." | tee -a "$LOG"
  docker run --rm -v $vol:/source -v $BACKUP_DIR:/dest alpine \
    tar czf /dest/$vol.tar.gz -C /source . 2>>"$LOG" && \
    echo "    ✅ $vol ($(du -h $BACKUP_DIR/$vol.tar.gz | cut -f1))" | tee -a "$LOG" || \
    echo "    ❌ $vol failed" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"

# 2. Stack Config
echo "--- Stack Config (/srv/stack) ---" | tee -a "$LOG"
tar czf "$BACKUP_DIR/stack-config.tar.gz" -C / srv/stack 2>/dev/null && \
  echo "  ✅ Config backed up ($(du -h $BACKUP_DIR/stack-config.tar.gz | cut -f1))" | tee -a "$LOG" || \
  echo "  ❌ Config backup failed" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# 3. SSH Keys
echo "--- SSH Keys ---" | tee -a "$LOG"
tar czf "$BACKUP_DIR/ssh-keys.tar.gz" -C /home/rabuntu .ssh 2>/dev/null && \
  echo "  ✅ SSH keys backed up ($(du -h $BACKUP_DIR/ssh-keys.tar.gz | cut -f1))" | tee -a "$LOG" || \
  echo "  ❌ SSH keys backup failed" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# 4. PostgreSQL (Kubuntux)
echo "--- PostgreSQL (Kubuntux) ---" | tee -a "$LOG"
DB_BACKUP="$BACKUP_DIR/postgres.sql"
if ssh -o ConnectTimeout=5 root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net \
  "su - postgres -c 'pg_dumpall --clean'" > "$DB_BACKUP" 2>/dev/null; then
  gzip "$DB_BACKUP"
  echo "  ✅ PostgreSQL dumped ($(du -h ${DB_BACKUP}.gz | cut -f1))" | tee -a "$LOG"
else
  echo "  ⚠️ PostgreSQL backup skipped (kubuntux unreachable?)" | tee -a "$LOG"
  rm -f "$DB_BACKUP"
fi
echo "" | tee -a "$LOG"

# 5. Size Summary
echo "==========================================" | tee -a "$LOG"
echo "  BACKUP COMPLETE" | tee -a "$LOG"
echo "  Total size: $(du -sh $BACKUP_DIR | cut -f1)" | tee -a "$LOG"
echo "  Files:" | tee -a "$LOG"
ls -lh "$BACKUP_DIR"/*.tar.gz "$BACKUP_DIR"/*.gz 2>/dev/null | awk '{print "    " $5 " " $9}' | tee -a "$LOG"
echo "==========================================" | tee -a "$LOG"
