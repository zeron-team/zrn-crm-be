#!/bin/bash
# =============================================================================
# ZeRoN 360° — Automated Backup Script
# Backs up PostgreSQL + Redis + ARCA certificates
# Retention: 7 daily, 4 weekly
# Usage: Add to cron: 0 3 * * * /home/ubuntu/zrn-crm/backend/scripts/backup.sh
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="/home/ubuntu/backups/zeron-crm"
DB_NAME="zeron_crm"
DB_USER="zeron_user"
DB_PASS="zeron_password"
ARCA_CERTS_DIR="/home/ubuntu/zrn-crm/backend/arca/certs"
UPLOADS_DIR="/home/ubuntu/zrn-crm/backend/uploads"
DATE=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday
LOG_FILE="$BACKUP_DIR/backup.log"

# Create backup directory
mkdir -p "$BACKUP_DIR/daily"
mkdir -p "$BACKUP_DIR/weekly"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================="
log "Starting ZeRoN 360° backup — $DATE"
log "========================================="

# ── PostgreSQL Backup ──
DAILY_BACKUP="$BACKUP_DIR/daily/pg_${DB_NAME}_${DATE}.sql.gz"
log "📦 PostgreSQL backup..."
if docker exec zeron_crm_db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$DAILY_BACKUP"; then
    SIZE=$(du -sh "$DAILY_BACKUP" | cut -f1)
    log "   ✅ PostgreSQL: $DAILY_BACKUP ($SIZE)"
else
    log "   ❌ PostgreSQL backup FAILED"
fi

# ── Redis Backup ──
REDIS_BACKUP="$BACKUP_DIR/daily/redis_${DATE}.rdb"
log "📦 Redis backup..."
if redis-cli BGSAVE > /dev/null 2>&1; then
    sleep 2
    REDIS_RDB="/var/lib/redis/dump.rdb"
    if [ -f "$REDIS_RDB" ]; then
        cp "$REDIS_RDB" "$REDIS_BACKUP"
        SIZE=$(du -sh "$REDIS_BACKUP" | cut -f1)
        log "   ✅ Redis: $REDIS_BACKUP ($SIZE)"
    else
        log "   ⚠️ Redis dump.rdb not found at $REDIS_RDB"
    fi
else
    log "   ⚠️ Redis BGSAVE failed (may not be critical)"
fi

# ── ARCA Certificates Backup ──
CERTS_BACKUP="$BACKUP_DIR/daily/arca_certs_${DATE}.tar.gz"
log "📦 ARCA certificates backup..."
if [ -d "$ARCA_CERTS_DIR" ]; then
    tar -czf "$CERTS_BACKUP" -C "$(dirname "$ARCA_CERTS_DIR")" "$(basename "$ARCA_CERTS_DIR")" 2>/dev/null
    SIZE=$(du -sh "$CERTS_BACKUP" | cut -f1)
    log "   ✅ ARCA certs: $CERTS_BACKUP ($SIZE)"
else
    log "   ⚠️ ARCA certs directory not found"
fi

# ── Uploads Backup (invoices PDFs) ──
UPLOADS_BACKUP="$BACKUP_DIR/daily/uploads_${DATE}.tar.gz"
log "📦 Uploads backup..."
if [ -d "$UPLOADS_DIR" ]; then
    tar -czf "$UPLOADS_BACKUP" -C "$(dirname "$UPLOADS_DIR")" "$(basename "$UPLOADS_DIR")" 2>/dev/null
    SIZE=$(du -sh "$UPLOADS_BACKUP" | cut -f1)
    log "   ✅ Uploads: $UPLOADS_BACKUP ($SIZE)"
fi

# ── Weekly Backup (Sundays) ──
if [ "$DAY_OF_WEEK" -eq 7 ]; then
    log "📦 Creating weekly backup (Sunday)..."
    WEEKLY_BACKUP="$BACKUP_DIR/weekly/full_${DATE}.tar.gz"
    tar -czf "$WEEKLY_BACKUP" "$BACKUP_DIR/daily"/pg_*_${DATE}* "$BACKUP_DIR/daily"/arca_*_${DATE}* "$BACKUP_DIR/daily"/uploads_*_${DATE}* 2>/dev/null || true
    SIZE=$(du -sh "$WEEKLY_BACKUP" | cut -f1)
    log "   ✅ Weekly: $WEEKLY_BACKUP ($SIZE)"
fi

# ── Rotation ──
log "🔄 Cleaning old backups..."

# Keep only 7 daily backups
DAILY_COUNT=$(ls -1 "$BACKUP_DIR/daily"/pg_*.sql.gz 2>/dev/null | wc -l)
if [ "$DAILY_COUNT" -gt 7 ]; then
    ls -1t "$BACKUP_DIR/daily"/pg_*.sql.gz | tail -n +8 | while read f; do
        BASENAME=$(basename "$f" .sql.gz | sed 's/pg_zeron_crm_//')
        rm -f "$BACKUP_DIR/daily"/pg_*"$BASENAME"* "$BACKUP_DIR/daily"/redis_*"$BASENAME"* \
              "$BACKUP_DIR/daily"/arca_*"$BASENAME"* "$BACKUP_DIR/daily"/uploads_*"$BASENAME"* 2>/dev/null
        log "   🗑️ Removed daily backup: $BASENAME"
    done
fi

# Keep only 4 weekly backups
WEEKLY_COUNT=$(ls -1 "$BACKUP_DIR/weekly"/full_*.tar.gz 2>/dev/null | wc -l)
if [ "$WEEKLY_COUNT" -gt 4 ]; then
    ls -1t "$BACKUP_DIR/weekly"/full_*.tar.gz | tail -n +5 | while read f; do
        rm -f "$f"
        log "   🗑️ Removed weekly: $(basename "$f")"
    done
fi

log "✅ Backup complete!"
log ""
