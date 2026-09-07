#!/usr/bin/env bash
set -e

BACKUP_DIR="${1:-./backups}"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

if [ -f "backend/ai_gateway.db" ]; then
    echo "Backing up SQLite database..."
    cp backend/ai_gateway.db "$BACKUP_DIR/ai_gateway_${TIMESTAMP}.sqlite"
    echo "Saved to $BACKUP_DIR/ai_gateway_${TIMESTAMP}.sqlite"
else
    echo "Backing up PostgreSQL database..."
    docker exec -t ai_gateway_postgres pg_dump -U gateway_user ai_gateway > "$BACKUP_DIR/postgres_dump_${TIMESTAMP}.sql"
    echo "Saved to $BACKUP_DIR/postgres_dump_${TIMESTAMP}.sql"
fi
