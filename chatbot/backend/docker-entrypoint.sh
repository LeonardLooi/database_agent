#!/bin/sh
set -e

# Fix /app/data ownership at every startup.
# Handles pre-existing named volumes that were initialized as root before the
# non-root user was introduced. Only the directory itself is chowned — not its
# contents — so existing SQLite files are untouched.
chown appuser:appgroup /app/data

# Snapshot all SQLite databases before running migrations so the previous state
# is recoverable if alembic upgrade head fails or introduces a regression.
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
for db in /app/data/*.db; do
    [ -f "$db" ] || continue
    backup="${db}.backup.${TIMESTAMP}"
    cp "$db" "$backup"
    chown appuser:appgroup "$backup"
    echo "Backup created: $backup"
done

# Retain only the 5 most recent backups per database — remove older ones.
# tail -n +6 skips the 5 newest (ls -t = newest first), xargs -r skips if empty.
for db in /app/data/*.db; do
    [ -f "$db" ] || continue
    base=$(basename "$db")
    ls -t "/app/data/${base}.backup."* 2>/dev/null | tail -n +6 | xargs -r rm --
done

# Run migrations as appuser — failure exits here before the app starts.
gosu appuser alembic upgrade head

exec gosu appuser "$@"
