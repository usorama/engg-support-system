#!/bin/bash
#
# ESS Database Backup Script
# Backs up Neo4j, Qdrant, and Redis data
#
# Usage: ./backup-databases.sh [backup_dir]
# Requires: docker compose running
#

set -euo pipefail

# Configuration
BACKUP_DIR="${1:-/tmp/ess-backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${DATE}"
RETENTION_DAYS=7

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create backup directory
mkdir -p "${BACKUP_PATH}"
log_info "Backup directory: ${BACKUP_PATH}"

# ============================================================================
# NEO4J BACKUP
# ============================================================================
backup_neo4j() {
    log_info "Backing up Neo4j..."

    # Create dump using neo4j-admin
    docker exec ess-neo4j neo4j-admin database dump neo4j \
        --to-path=/backups \
        --overwrite-destination=true 2>/dev/null || {
        log_warn "Neo4j admin backup failed, trying volume copy..."

        # Fallback: Copy data volume directly
        docker run --rm \
            -v ess_neo4j_data:/data:ro \
            -v "${BACKUP_PATH}:/backup" \
            alpine tar czf /backup/neo4j_data.tar.gz -C /data .
    }

    # Copy dump from container if admin succeeded
    if docker exec ess-neo4j test -f /backups/neo4j.dump 2>/dev/null; then
        docker cp ess-neo4j:/backups/neo4j.dump "${BACKUP_PATH}/neo4j.dump"
        log_info "Neo4j backup: ${BACKUP_PATH}/neo4j.dump"
    else
        log_info "Neo4j backup: ${BACKUP_PATH}/neo4j_data.tar.gz"
    fi
}

# ============================================================================
# QDRANT BACKUP
# ============================================================================
backup_qdrant() {
    log_info "Backing up Qdrant..."

    # Qdrant snapshot via API
    QDRANT_URL="http://localhost:6333"

    # Create snapshot for all collections
    COLLECTIONS=$(curl -s "${QDRANT_URL}/collections" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)

    if [ -n "$COLLECTIONS" ]; then
        for collection in $COLLECTIONS; do
            log_info "  Creating snapshot for collection: $collection"
            SNAPSHOT=$(curl -s -X POST "${QDRANT_URL}/collections/${collection}/snapshots" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)

            if [ -n "$SNAPSHOT" ]; then
                # Download snapshot
                curl -s "${QDRANT_URL}/collections/${collection}/snapshots/${SNAPSHOT}" \
                    -o "${BACKUP_PATH}/qdrant_${collection}_${SNAPSHOT}.snapshot"
                log_info "    Saved: qdrant_${collection}_${SNAPSHOT}.snapshot"
            fi
        done
    else
        # Fallback: Copy storage volume
        log_warn "No collections found, copying volume..."
        docker run --rm \
            -v ess_qdrant_data:/data:ro \
            -v "${BACKUP_PATH}:/backup" \
            alpine tar czf /backup/qdrant_storage.tar.gz -C /data .
        log_info "Qdrant backup: ${BACKUP_PATH}/qdrant_storage.tar.gz"
    fi
}

# ============================================================================
# REDIS BACKUP
# ============================================================================
backup_redis() {
    log_info "Backing up Redis..."

    # Trigger BGSAVE
    docker exec ess-redis redis-cli BGSAVE || true
    sleep 2

    # Copy RDB file
    docker cp ess-redis:/data/dump.rdb "${BACKUP_PATH}/redis_dump.rdb" 2>/dev/null || {
        # Fallback: Copy volume
        log_warn "RDB copy failed, copying volume..."
        docker run --rm \
            -v ess_redis_data:/data:ro \
            -v "${BACKUP_PATH}:/backup" \
            alpine tar czf /backup/redis_data.tar.gz -C /data .
    }

    log_info "Redis backup: ${BACKUP_PATH}/redis_dump.rdb or redis_data.tar.gz"
}

# ============================================================================
# CLEANUP OLD BACKUPS
# ============================================================================
cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

    find "${BACKUP_DIR}" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true

    # Show remaining backups
    BACKUP_COUNT=$(find "${BACKUP_DIR}" -maxdepth 1 -type d | wc -l)
    log_info "Remaining backups: $((BACKUP_COUNT - 1))"
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    log_info "Starting ESS database backup..."
    log_info "Timestamp: ${DATE}"

    # Run backups
    backup_neo4j
    backup_qdrant
    backup_redis

    # Create manifest
    cat > "${BACKUP_PATH}/manifest.json" << EOF
{
    "timestamp": "${DATE}",
    "created_at": "$(date -Iseconds)",
    "retention_days": ${RETENTION_DAYS},
    "contents": $(ls -1 "${BACKUP_PATH}" | grep -v manifest.json | jq -R -s -c 'split("\n") | map(select(. != ""))')
}
EOF

    # Calculate total size
    TOTAL_SIZE=$(du -sh "${BACKUP_PATH}" | cut -f1)
    log_info "Backup complete! Total size: ${TOTAL_SIZE}"

    # Cleanup
    cleanup_old_backups

    log_info "Backup path: ${BACKUP_PATH}"
}

# Run main function
main "$@"
