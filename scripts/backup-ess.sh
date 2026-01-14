#!/bin/bash
#
# ESS Daily Backup Script
#
# Backs up Neo4j, Qdrant, and Redis data to local backup directory.
# Rotates backups older than 7 days.
#
# Usage: ./backup-ess.sh [--force]
# Cron:  0 3 * * * /home/devuser/scripts/backup-ess.sh >> /home/devuser/logs/backup.log 2>&1
#

set -euo pipefail

# Configuration
BACKUP_ROOT="${BACKUP_ROOT:-/home/devuser/backups/ess}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$DATE_STAMP"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# Container names (match docker-compose.prod.yml)
NEO4J_CONTAINER="ess-neo4j"
QDRANT_CONTAINER="ess-qdrant"
REDIS_CONTAINER="ess-redis"

# Qdrant API (for snapshots)
QDRANT_URL="${QDRANT_URL:-http://localhost:6335}"
QDRANT_COLLECTION="${QDRANT_COLLECTION:-ess_rad_engineer_v2}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "$LOG_PREFIX ${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "$LOG_PREFIX ${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "$LOG_PREFIX ${RED}[ERROR]${NC} $1"
}

check_container() {
    local container=$1
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        return 1
    fi
    return 0
}

# Check if running as a user with docker access
if ! docker ps &>/dev/null; then
    log_error "Cannot access Docker. Run with a user that has docker permissions."
    exit 1
fi

# Create backup directory
log_info "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Track success/failure
BACKUP_SUCCESS=true
ERRORS=()

# =============================================================================
# NEO4J BACKUP
# =============================================================================

log_info "Starting Neo4j backup..."

if check_container "$NEO4J_CONTAINER"; then
    NEO4J_BACKUP_FILE="$BACKUP_DIR/neo4j-data.tar.gz"

    # Stop writes temporarily (optional, for consistency)
    # docker exec $NEO4J_CONTAINER neo4j-admin database backup neo4j --to=/data/backup

    # Alternative: Just copy the data directory
    # This requires the container to have the data volume mounted
    if docker exec "$NEO4J_CONTAINER" ls /data &>/dev/null; then
        log_info "Creating Neo4j data archive..."
        docker exec "$NEO4J_CONTAINER" tar czf /tmp/neo4j-backup.tar.gz -C /data . 2>/dev/null || true
        docker cp "$NEO4J_CONTAINER:/tmp/neo4j-backup.tar.gz" "$NEO4J_BACKUP_FILE" || {
            log_warn "Neo4j backup via tar failed, trying alternate method..."
            # Alternative: Copy data directory directly
            docker cp "$NEO4J_CONTAINER:/data" "$BACKUP_DIR/neo4j-data" 2>/dev/null && \
            tar czf "$NEO4J_BACKUP_FILE" -C "$BACKUP_DIR" neo4j-data && \
            rm -rf "$BACKUP_DIR/neo4j-data" || {
                log_error "Neo4j backup failed"
                BACKUP_SUCCESS=false
                ERRORS+=("Neo4j backup failed")
            }
        }
        docker exec "$NEO4J_CONTAINER" rm -f /tmp/neo4j-backup.tar.gz 2>/dev/null || true

        if [ -f "$NEO4J_BACKUP_FILE" ]; then
            SIZE=$(du -h "$NEO4J_BACKUP_FILE" | cut -f1)
            log_info "Neo4j backup complete: $NEO4J_BACKUP_FILE ($SIZE)"
        fi
    else
        log_warn "Neo4j data directory not accessible"
        ERRORS+=("Neo4j data directory not accessible")
    fi
else
    log_warn "Neo4j container not running, skipping backup"
    ERRORS+=("Neo4j container not running")
fi

# =============================================================================
# QDRANT BACKUP (via API snapshot)
# =============================================================================

log_info "Starting Qdrant backup..."

if check_container "$QDRANT_CONTAINER"; then
    QDRANT_SNAPSHOT_DIR="$BACKUP_DIR/qdrant-snapshots"
    mkdir -p "$QDRANT_SNAPSHOT_DIR"

    # Create snapshot via API
    log_info "Creating Qdrant snapshot for collection: $QDRANT_COLLECTION"
    SNAPSHOT_RESPONSE=$(curl -s -X POST "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots" 2>/dev/null || echo '{"error": "failed"}')

    if echo "$SNAPSHOT_RESPONSE" | grep -q '"result"'; then
        SNAPSHOT_NAME=$(echo "$SNAPSHOT_RESPONSE" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        log_info "Snapshot created: $SNAPSHOT_NAME"

        # Download snapshot
        if [ -n "$SNAPSHOT_NAME" ]; then
            curl -s "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots/$SNAPSHOT_NAME" \
                -o "$QDRANT_SNAPSHOT_DIR/$SNAPSHOT_NAME" 2>/dev/null || {
                log_warn "Failed to download Qdrant snapshot"
                ERRORS+=("Failed to download Qdrant snapshot")
            }

            if [ -f "$QDRANT_SNAPSHOT_DIR/$SNAPSHOT_NAME" ]; then
                SIZE=$(du -h "$QDRANT_SNAPSHOT_DIR/$SNAPSHOT_NAME" | cut -f1)
                log_info "Qdrant backup complete: $QDRANT_SNAPSHOT_DIR/$SNAPSHOT_NAME ($SIZE)"
            fi
        fi
    else
        log_warn "Qdrant snapshot creation failed: $SNAPSHOT_RESPONSE"

        # Alternative: Copy storage directory
        log_info "Trying alternative backup via volume copy..."
        if docker exec "$QDRANT_CONTAINER" ls /qdrant/storage &>/dev/null; then
            docker cp "$QDRANT_CONTAINER:/qdrant/storage" "$QDRANT_SNAPSHOT_DIR/storage" 2>/dev/null && \
            tar czf "$BACKUP_DIR/qdrant-storage.tar.gz" -C "$QDRANT_SNAPSHOT_DIR" storage && \
            rm -rf "$QDRANT_SNAPSHOT_DIR/storage" || {
                log_error "Qdrant backup failed"
                BACKUP_SUCCESS=false
                ERRORS+=("Qdrant backup failed")
            }
        fi
    fi
else
    log_warn "Qdrant container not running, skipping backup"
    ERRORS+=("Qdrant container not running")
fi

# =============================================================================
# REDIS BACKUP
# =============================================================================

log_info "Starting Redis backup..."

if check_container "$REDIS_CONTAINER"; then
    REDIS_BACKUP_FILE="$BACKUP_DIR/redis-dump.rdb"

    # Trigger BGSAVE
    log_info "Triggering Redis BGSAVE..."
    docker exec "$REDIS_CONTAINER" redis-cli BGSAVE 2>/dev/null || true

    # Wait for BGSAVE to complete (max 30 seconds)
    for i in {1..30}; do
        LASTSAVE=$(docker exec "$REDIS_CONTAINER" redis-cli LASTSAVE 2>/dev/null || echo "0")
        sleep 1
        NEWSAVE=$(docker exec "$REDIS_CONTAINER" redis-cli LASTSAVE 2>/dev/null || echo "0")
        if [ "$NEWSAVE" != "$LASTSAVE" ] || [ "$i" -eq 1 ]; then
            break
        fi
    done

    # Copy dump.rdb
    docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$REDIS_BACKUP_FILE" 2>/dev/null || {
        log_warn "Redis dump.rdb not found at /data/dump.rdb"
        # Try alternate location
        docker cp "$REDIS_CONTAINER:/var/lib/redis/dump.rdb" "$REDIS_BACKUP_FILE" 2>/dev/null || {
            log_error "Redis backup failed"
            BACKUP_SUCCESS=false
            ERRORS+=("Redis backup failed")
        }
    }

    if [ -f "$REDIS_BACKUP_FILE" ]; then
        SIZE=$(du -h "$REDIS_BACKUP_FILE" | cut -f1)
        log_info "Redis backup complete: $REDIS_BACKUP_FILE ($SIZE)"
    fi
else
    log_warn "Redis container not running, skipping backup"
    ERRORS+=("Redis container not running")
fi

# =============================================================================
# BACKUP METADATA
# =============================================================================

# Write backup metadata
cat > "$BACKUP_DIR/backup-info.json" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "date_stamp": "$DATE_STAMP",
  "hostname": "$(hostname)",
  "backup_root": "$BACKUP_ROOT",
  "retention_days": $RETENTION_DAYS,
  "containers": {
    "neo4j": "$(check_container $NEO4J_CONTAINER && echo 'running' || echo 'not running')",
    "qdrant": "$(check_container $QDRANT_CONTAINER && echo 'running' || echo 'not running')",
    "redis": "$(check_container $REDIS_CONTAINER && echo 'running' || echo 'not running')"
  },
  "success": $BACKUP_SUCCESS,
  "errors": $(printf '%s\n' "${ERRORS[@]:-}" | jq -R -s -c 'split("\n") | map(select(length > 0))')
}
EOF

# =============================================================================
# ROTATION (Delete old backups)
# =============================================================================

log_info "Rotating old backups (keeping $RETENTION_DAYS days)..."
DELETED_COUNT=0

if [ -d "$BACKUP_ROOT" ]; then
    while IFS= read -r old_backup; do
        if [ -d "$old_backup" ]; then
            rm -rf "$old_backup"
            DELETED_COUNT=$((DELETED_COUNT + 1))
            log_info "Deleted old backup: $old_backup"
        fi
    done < <(find "$BACKUP_ROOT" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -not -path "$BACKUP_ROOT")
fi

log_info "Rotation complete. Deleted $DELETED_COUNT old backups."

# =============================================================================
# SUMMARY
# =============================================================================

TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)

echo ""
echo "=============================================="
echo "BACKUP SUMMARY"
echo "=============================================="
echo "Backup Directory: $BACKUP_DIR"
echo "Total Size: $TOTAL_SIZE"
echo "Status: $($BACKUP_SUCCESS && echo 'SUCCESS' || echo 'PARTIAL/FAILED')"

if [ ${#ERRORS[@]} -gt 0 ]; then
    echo ""
    echo "Warnings/Errors:"
    for err in "${ERRORS[@]}"; do
        echo "  - $err"
    done
fi

echo ""
echo "Files:"
ls -lh "$BACKUP_DIR"
echo "=============================================="

if $BACKUP_SUCCESS; then
    exit 0
else
    exit 1
fi
