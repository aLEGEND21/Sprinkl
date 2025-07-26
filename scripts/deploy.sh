#!/bin/bash
set -e

# Change to project root (one directory up from scripts/)
cd "$(dirname "$0")/.."

echo "🚀 Pulling latest changes from GitHub..."
if ! git pull origin master; then
    echo "❌ Failed to pull latest changes from GitHub"
    exit 1
fi

echo "🐳 Building and starting Docker Compose services..."
if ! docker compose -f compose.yml -f compose.prod.yml up -d --build; then
    echo "❌ Failed to build and start Docker Compose services"
    exit 1
fi

echo "✅ Deployment complete!"