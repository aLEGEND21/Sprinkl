#!/bin/bash
set -e

# Change to project root (one directory up from scripts/)
cd "$(dirname "$0")/.."

echo "⏪ Rolling back to previous commit..."

# Get the previous commit hash
PREV_COMMIT=$(git rev-parse HEAD@{1})

if [ -z "$PREV_COMMIT" ]; then
    echo "❌ Could not determine previous commit hash"
    exit 1
fi

echo "🔙 Checking out previous commit: $PREV_COMMIT"
if ! git checkout $PREV_COMMIT; then
    echo "❌ Failed to checkout previous commit"
    exit 1
fi

echo "🐳 Rebuilding and restarting Docker Compose services..."
if ! docker compose -f compose.yml -f compose.prod.yml up -d --build; then
    echo "❌ Failed to rebuild and restart Docker Compose services during rollback"
    exit 1
fi

# Wait a moment for services to start and check their status
echo "🔍 Checking service status after rollback..."
sleep 10

# Check if all containers are running
if ! docker compose -f compose.yml -f compose.prod.yml ps | grep -q "Up"; then
    echo "❌ Some services failed to start properly after rollback"
    exit 1
fi

echo "✅ Rollback complete!"