#!/usr/bin/env bash
set -euo pipefail

VPS_USER="bart"
VPS_HOST="caraser.org"
VPS_PATH="/home/bart/caraser"
LOCAL_BACKUP_DIR="${HOME}/backup/caraser"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${VPS_PATH}/backups/${TIMESTAMP}"

echo "Creating backup ${TIMESTAMP} on ${VPS_HOST}..."

ssh "${VPS_USER}@${VPS_HOST}" bash <<EOF
  set -euo pipefail
  mkdir -p "${BACKUP_DIR}"

  echo "Backing up PostgreSQL..."
  docker compose -f "${VPS_PATH}/docker-compose.prod.yml" exec -T db \
    pg_dump -U caraser caraser | gzip > "${BACKUP_DIR}/db.sql.gz"

  echo "Backing up media files..."
  tar -czf "${BACKUP_DIR}/media.tar.gz" -C "${VPS_PATH}" media

  echo "Removing backups older than 30 days..."
  find "${VPS_PATH}/backups" -maxdepth 1 -mindepth 1 -type d -mtime +30 \
    -exec rm -rf {} +

  echo "Backup complete: ${BACKUP_DIR}"
  du -sh "${BACKUP_DIR}"/*
EOF

echo "Syncing backup to local ${LOCAL_BACKUP_DIR}..."
mkdir -p "${LOCAL_BACKUP_DIR}"
rsync -av --progress \
  "${VPS_USER}@${VPS_HOST}:${BACKUP_DIR}/" \
  "${LOCAL_BACKUP_DIR}/${TIMESTAMP}/"

echo "Local backup saved to ${LOCAL_BACKUP_DIR}/${TIMESTAMP}/"
du -sh "${LOCAL_BACKUP_DIR}/${TIMESTAMP}/"*
