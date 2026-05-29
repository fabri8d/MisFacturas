#!/bin/bash
# deploy.sh — Construye imágenes y las sube a Docker Hub.
# Uso:
#   ./deploy.sh                        # push como "latest"
#   ./deploy.sh fabribiondi2002 v1.0.0  # push con tag de versión
set -e

DOCKERHUB_USER=${1:-"fabribiondi2002"}
TAG=${2:-"latest"}

echo "▶ Building backend..."
docker build \
  --platform linux/amd64 \
  -t "$DOCKERHUB_USER/misfacturas-backend:$TAG" \
  ./backend

echo "▶ Building frontend..."
docker build \
  --platform linux/amd64 \
  -t "$DOCKERHUB_USER/misfacturas-frontend:$TAG" \
  ./frontend

echo "▶ Pushing to Docker Hub..."
docker push "$DOCKERHUB_USER/misfacturas-backend:$TAG"
docker push "$DOCKERHUB_USER/misfacturas-frontend:$TAG"

echo ""
echo "✓ Done. On the VPS run:"
echo "  cd ~/infra/misfacturas && docker compose pull && docker compose up -d"
