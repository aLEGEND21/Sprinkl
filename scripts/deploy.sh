#!/bin/bash
set -e

# Change to project root (one directory up from scripts/)
cd "$(dirname "$0")/.."

echo "🚀 Pulling latest changes from GitHub..."
git pull origin master

echo "🐳 Building and starting Docker Compose services..."
docker compose -f compose.yml -f compose.prod.yml up -d --build

echo "✅ Deployment complete!"