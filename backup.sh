#!/usr/bin/env bash
set -euo pipefail

VPS_USER="bart"
VPS_HOST="caraser.org"
VPS_PATH="/home/bart/caraser"
LOCAL_BACKUP_DIR="${HOME}/backup/caraser"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${VPS_PATH}/backups/${TIMESTAMP}"

SSH="ssh ${VPS_USER}@${VPS_HOST}"

echo "==> [1/4] Creating backup directory ${BACKUP_DIR}..."
$SSH "mkdir -p '${BACKUP_DIR}'"

echo "==> [2/4] Backing up PostgreSQL..."
$SSH "docker compose -f '${VPS_PATH}/docker-compose.prod.yml' exec -T db \
  pg_dump -U caraser caraser 2>/dev/null | gzip > '${BACKUP_DIR}/db.sql.gz'"

echo "==> [3/4] Backing up media files..."
$SSH "docker compose -f '${VPS_PATH}/docker-compose.prod.yml' exec -T api \
  tar -czf - /app/media 2>/dev/null > '${BACKUP_DIR}/media.tar.gz'"

echo "==> [4/4] Removing backups older than 30 days..."
$SSH "find '${VPS_PATH}/backups' -maxdepth 1 -mindepth 1 -type d -mtime +30 -exec rm -rf {} +"

echo "==> Backup complete: ${BACKUP_DIR}"
$SSH "du -sh '${BACKUP_DIR}'/*"

echo "==> Syncing backup to local ${LOCAL_BACKUP_DIR}..."
mkdir -p "${LOCAL_BACKUP_DIR}"
rsync -av --progress \
  "${VPS_USER}@${VPS_HOST}:${BACKUP_DIR}/" \
  "${LOCAL_BACKUP_DIR}/${TIMESTAMP}/"

echo "==> Local backup saved to ${LOCAL_BACKUP_DIR}/${TIMESTAMP}/"
du -sh "${LOCAL_BACKUP_DIR}/${TIMESTAMP}/"*
