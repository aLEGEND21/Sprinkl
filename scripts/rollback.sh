#!/bin/bash
set -e

# Change to project root (one directory up from scripts/)
cd "$(dirname "$0")/.."

echo "⏪ Rolling back to previous commit..."

# Get the previous commit hash
PREV_COMMIT=$(git rev-parse HEAD@{1})

echo "🔙 Checking out previous commit: $PREV_COMMIT"
git checkout $PREV_COMMIT

echo "🐳 Rebuilding and restarting Docker Compose services..."
docker compose -f compose.yml -f compose.prod.yml up -d --build

echo "✅ Rollback complete!"