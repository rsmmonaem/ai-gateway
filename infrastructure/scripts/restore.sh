#!/usr/bin/env bash
set -e

BACKUP_FILE="$1"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <path-to-backup-file>"
    exit 1
fi

if [[ "$BACKUP_FILE" == *.sqlite ]]; then
    echo "Restoring SQLite database..."
    cp "$BACKUP_FILE" backend/ai_gateway.db
    echo "Restoration complete."
elif [[ "$BACKUP_FILE" == *.sql ]]; then
    echo "Restoring PostgreSQL database..."
    docker exec -i ai_gateway_postgres psql -U gateway_user ai_gateway < "$BACKUP_FILE"
    echo "Restoration complete."
fi
