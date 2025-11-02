#!/bin/bash
# Automated PostgreSQL database backup script
# Usage: ./backup_database.sh [environment]

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/acis-ai}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
ENVIRONMENT="${1:-production}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="acis-ai-${ENVIRONMENT}-${TIMESTAMP}.sql.gz"

# Database connection
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-acis-ai}"
DB_USER="${DB_USER:-postgres}"

# S3 configuration (optional)
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-backups/database}"

# Logging
LOG_FILE="${BACKUP_DIR}/backup.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
    exit 1
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "Starting database backup for environment: $ENVIRONMENT"

# Check if database is accessible
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    error "Database is not accessible at ${DB_HOST}:${DB_PORT}"
fi

# Create backup
log "Creating backup: $BACKUP_FILE"
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-acl --clean --if-exists \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"; then
    log "Backup created successfully: ${BACKUP_DIR}/${BACKUP_FILE}"
else
    error "Failed to create backup"
fi

# Verify backup
BACKUP_SIZE=$(stat -f%z "${BACKUP_DIR}/${BACKUP_FILE}" 2>/dev/null || stat -c%s "${BACKUP_DIR}/${BACKUP_FILE}")
if [ "$BACKUP_SIZE" -lt 1000 ]; then
    error "Backup file is suspiciously small: ${BACKUP_SIZE} bytes"
fi
log "Backup size: $(numfmt --to=iec-i --suffix=B $BACKUP_SIZE 2>/dev/null || echo ${BACKUP_SIZE} bytes)"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    log "Uploading backup to S3: s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}"
    if command -v aws &> /dev/null; then
        if aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}"; then
            log "Backup uploaded to S3 successfully"
        else
            error "Failed to upload backup to S3"
        fi
    else
        log "WARNING: AWS CLI not installed, skipping S3 upload"
    fi
fi

# Cleanup old local backups
log "Cleaning up backups older than ${RETENTION_DAYS} days"
find "$BACKUP_DIR" -name "acis-ai-${ENVIRONMENT}-*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
OLD_COUNT=$(find "$BACKUP_DIR" -name "acis-ai-${ENVIRONMENT}-*.sql.gz" -type f | wc -l)
log "Retained $OLD_COUNT backup(s)"

# Cleanup old S3 backups if configured
if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
    log "Cleaning up S3 backups older than ${RETENTION_DAYS} days"
    CUTOFF_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)
    aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | while read -r line; do
        FILE_DATE=$(echo "$line" | awk '{print $1}')
        FILE_NAME=$(echo "$line" | awk '{print $4}')
        if [[ "$FILE_NAME" =~ ^acis-ai-${ENVIRONMENT}- ]]; then
            if [[ "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
                log "Deleting old S3 backup: $FILE_NAME"
                aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${FILE_NAME}"
            fi
        fi
    done
fi

log "Backup completed successfully"

# Send notification (optional)
if [ -n "$WEBHOOK_URL" ]; then
    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"Database backup completed: ${BACKUP_FILE}\"}" \
        > /dev/null 2>&1 || true
fi

exit 0
