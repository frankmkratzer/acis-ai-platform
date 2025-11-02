# Database Backup & Restore Guide

Automated backup solution for the ACIS AI Platform database.

## Features

- Automated daily backups
- Compression (gzip)
- Configurable retention (default 30 days)
- Optional S3 upload
- Pre-restore backup creation
- Verification and logging
- Kubernetes CronJob support

## Local/VM Deployment

### Setup

```bash
# Make scripts executable
chmod +x scripts/backup/backup_database.sh
chmod +x scripts/backup/restore_database.sh

# Create backup directory
sudo mkdir -p /var/backups/acis-ai
sudo chown $USER:$USER /var/backups/acis-ai
```

### Manual Backup

```bash
# Basic backup (defaults to production)
./scripts/backup/backup_database.sh

# Backup specific environment
./scripts/backup/backup_database.sh development
./scripts/backup/backup_database.sh staging
./scripts/backup/backup_database.sh production
```

### Environment Variables

```bash
# Database connection
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=acis-ai
export DB_USER=postgres
export PGPASSWORD=your_password

# Backup configuration
export BACKUP_DIR=/var/backups/acis-ai
export RETENTION_DAYS=30

# Optional: S3 upload
export S3_BUCKET=my-backup-bucket
export S3_PREFIX=backups/database
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Optional: Webhook notification
export WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Automated Backups with Cron

Add to crontab (`crontab -e`):

```cron
# Daily backup at 2 AM
0 2 * * * /home/user/acis-ai-platform/scripts/backup/backup_database.sh production

# Weekly backup on Sunday at 3 AM
0 3 * * 0 /home/user/acis-ai-platform/scripts/backup/backup_database.sh production
```

## Database Restore

### List Available Backups

```bash
ls -lh /var/backups/acis-ai/
```

### Restore from Backup

```bash
# Restore from local backup
./scripts/backup/restore_database.sh /var/backups/acis-ai/acis-ai-production-20250102_020000.sql.gz

# Restore from S3
aws s3 cp s3://my-bucket/backups/database/acis-ai-production-20250102_020000.sql.gz /tmp/
./scripts/backup/restore_database.sh /tmp/acis-ai-production-20250102_020000.sql.gz
```

**Important**:
- The restore script will create a pre-restore backup first
- You must confirm before the restore proceeds
- The database will be completely replaced

## Kubernetes Deployment

### Deploy Backup CronJob

```bash
# Create the CronJob
kubectl apply -f k8s/base/backup-cronjob.yaml

# Verify CronJob is created
kubectl get cronjob -n acis-ai

# Check backup jobs
kubectl get jobs -n acis-ai

# View logs from latest backup
kubectl logs -n acis-ai job/postgres-backup-<timestamp>
```

### Manual Backup Trigger

```bash
# Create a one-time job from the CronJob
kubectl create job -n acis-ai --from=cronjob/postgres-backup manual-backup-$(date +%s)

# Watch the job
kubectl get jobs -n acis-ai -w

# Check logs
kubectl logs -n acis-ai job/manual-backup-<timestamp> -f
```

### Restore in Kubernetes

```bash
# Download backup from pod
kubectl cp acis-ai/postgres-backup-<pod>:/backup/acis-ai-20250102_020000.sql.gz ./backup.sql.gz

# Or download from S3
aws s3 cp s3://my-bucket/backups/database/acis-ai-20250102_020000.sql.gz ./backup.sql.gz

# Restore to database pod
gunzip -c backup.sql.gz | kubectl exec -i -n acis-ai postgres-0 -- psql -U postgres -d acis-ai
```

## S3 Configuration

### Setup AWS Credentials

**For local/VM:**
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure credentials
aws configure
```

**For Kubernetes:**
```bash
# Create AWS secrets
kubectl create secret generic aws-secrets \
  --from-literal=access-key-id=YOUR_ACCESS_KEY \
  --from-literal=secret-access-key=YOUR_SECRET_KEY \
  -n acis-ai

# Update CronJob to use S3
kubectl edit cronjob postgres-backup -n acis-ai
# Set S3_BUCKET environment variable
```

### S3 Bucket Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name/backups/*",
        "arn:aws:s3:::your-bucket-name"
      ]
    }
  ]
}
```

### S3 Lifecycle Policy

Configure automatic deletion of old backups:

```json
{
  "Rules": [
    {
      "Id": "Delete old backups",
      "Status": "Enabled",
      "Prefix": "backups/database/",
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
```

## Backup Verification

### Check Backup Integrity

```bash
# Verify gzip file
gunzip -t /var/backups/acis-ai/acis-ai-production-20250102_020000.sql.gz

# Check backup contents
gunzip -c /var/backups/acis-ai/acis-ai-production-20250102_020000.sql.gz | head -100

# Count tables in backup
gunzip -c backup.sql.gz | grep -c "CREATE TABLE"

# Check backup size
du -h /var/backups/acis-ai/acis-ai-production-20250102_020000.sql.gz
```

### Test Restore (to separate database)

```bash
# Create test database
psql -U postgres -c "CREATE DATABASE acis_ai_test;"

# Restore to test database
gunzip -c backup.sql.gz | psql -U postgres -d acis_ai_test

# Verify tables
psql -U postgres -d acis_ai_test -c "\dt"

# Drop test database when done
psql -U postgres -c "DROP DATABASE acis_ai_test;"
```

## Monitoring & Alerts

### Backup Logs

```bash
# Local backups
tail -f /var/backups/acis-ai/backup.log

# Kubernetes backups
kubectl logs -n acis-ai cronjob/postgres-backup
```

### Slack Notifications

Configure webhook in backup script:

```bash
export WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Prometheus Alerts

Add to `monitoring/prometheus/alerts/alerts.yml`:

```yaml
- alert: BackupFailed
  expr: time() - backup_last_success_timestamp > 86400
  for: 1h
  labels:
    severity: critical
  annotations:
    summary: "Database backup has not succeeded in 24 hours"
```

## Best Practices

1. **Test Restores Regularly**
   - Restore to a test environment monthly
   - Verify all critical data is present

2. **Multiple Retention Tiers**
   - Daily backups: 30 days
   - Weekly backups: 90 days
   - Monthly backups: 1 year

3. **Offsite Backups**
   - Always upload to S3 or similar cloud storage
   - Keep backups in different AWS region

4. **Encryption**
   - Enable S3 bucket encryption
   - Consider encrypting backups before upload:
     ```bash
     pg_dump ... | gzip | gpg --encrypt --recipient admin@acis-ai.com > backup.sql.gz.gpg
     ```

5. **Monitoring**
   - Set up alerts for failed backups
   - Monitor backup size trends
   - Verify backups complete within time window

6. **Documentation**
   - Document restore procedures
   - Maintain runbook for disaster recovery
   - Test restore process regularly

## Troubleshooting

### Backup Taking Too Long

```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('acis-ai'));

-- Check largest tables
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

Consider:
- Using parallel dump: `pg_dump -j 4`
- Excluding large tables: `pg_dump --exclude-table=large_table`
- Incremental backups for very large databases

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up old backups
find /var/backups/acis-ai -name "*.sql.gz" -mtime +30 -delete

# Compress existing uncompressed backups
find /var/backups/acis-ai -name "*.sql" -exec gzip {} \;
```

### Restore Fails with Errors

```bash
# Restore with verbose error messages
gunzip -c backup.sql.gz | psql -U postgres -d acis-ai -v ON_ERROR_STOP=1 2>&1 | tee restore.log

# Skip errors and continue
gunzip -c backup.sql.gz | psql -U postgres -d acis-ai
```

## Security Considerations

1. **Credentials**
   - Never commit credentials to version control
   - Use environment variables or secrets management
   - Rotate backup credentials regularly

2. **Access Control**
   - Limit access to backup files (chmod 600)
   - Use IAM roles in Kubernetes
   - Enable MFA for S3 bucket access

3. **Encryption**
   - Enable encryption at rest for S3
   - Consider encrypting backups before upload
   - Use TLS for database connections

4. **Audit**
   - Log all backup and restore operations
   - Monitor access to backup files
   - Regular security audits

## Disaster Recovery

### Complete System Restore

1. **Provision New Infrastructure**
   ```bash
   # Deploy Kubernetes cluster
   # Deploy database
   kubectl apply -f k8s/base/postgres-statefulset.yaml
   ```

2. **Restore Latest Backup**
   ```bash
   # Download from S3
   aws s3 cp s3://bucket/backups/database/latest.sql.gz ./

   # Restore
   ./scripts/backup/restore_database.sh latest.sql.gz
   ```

3. **Verify Application**
   ```bash
   # Deploy application
   helm install acis-ai ./helm/acis-ai

   # Verify
   kubectl get pods -n acis-ai
   ```

4. **Test Critical Functions**
   - User login
   - Portfolio retrieval
   - ML predictions
   - Trade execution

## Support

For backup/restore issues:
- Check logs: `/var/backups/acis-ai/backup.log`
- GitHub Issues: https://github.com/frankmkratzer/acis-ai-platform/issues
- Documentation: [DEPLOYMENT_GUIDE.md](../../DEPLOYMENT_GUIDE.md)
