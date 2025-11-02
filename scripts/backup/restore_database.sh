#!/bin/bash
# Database restore script
# Usage: ./restore_database.sh <backup_file> [environment]

set -e

BACKUP_FILE="$1"
ENVIRONMENT="${2:-production}"

# Database connection
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-acis-ai}"
DB_USER="${DB_USER:-postgres}"

# Logging
LOG_FILE="/var/backups/acis-ai/restore.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
    exit 1
}

# Validation
if [ -z "$BACKUP_FILE" ]; then
    error "Usage: $0 <backup_file> [environment]"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

log "Starting database restore from: $BACKUP_FILE"
log "Environment: $ENVIRONMENT"
log "Target database: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Confirmation prompt
read -p "This will REPLACE the current database. Are you sure? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log "Restore cancelled by user"
    exit 0
fi

# Check if database is accessible
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    error "Database is not accessible at ${DB_HOST}:${DB_PORT}"
fi

# Create pre-restore backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PRE_RESTORE_BACKUP="/var/backups/acis-ai/pre-restore-${TIMESTAMP}.sql.gz"
log "Creating pre-restore backup: $PRE_RESTORE_BACKUP"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-acl | gzip > "$PRE_RESTORE_BACKUP" || \
    error "Failed to create pre-restore backup"

# Restore database
log "Restoring database..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 || error "Failed to restore database"
else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 -f "$BACKUP_FILE" || error "Failed to restore database"
fi

log "Database restored successfully"

# Verify restore
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'" | xargs)
log "Verified: $TABLE_COUNT tables restored"

# Run post-restore checks
log "Running post-restore checks..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Check for basic tables
SELECT 'Checking tables...' as status;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Verify critical tables have data
SELECT 'clients', COUNT(*) FROM clients;
SELECT 'daily_bars', COUNT(*) FROM daily_bars;
SELECT 'ml_training_features', COUNT(*) FROM ml_training_features;
EOF

log "Restore completed successfully"
log "Pre-restore backup saved at: $PRE_RESTORE_BACKUP"

exit 0
