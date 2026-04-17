#!/bin/bash
set -euo pipefail

PROJECT_DIR="/opt/tg_bot"
VENV="$PROJECT_DIR/venv"
REPO_URL="${REPO_URL:-https://github.com/your_user/your_repo.git}"

echo "==> Updating source..."
cd "$PROJECT_DIR"
git pull origin main

echo "==> Installing dependencies..."
"$VENV/bin/pip" install --no-cache-dir -r requirements.txt

echo "==> Installing Playwright browsers..."
"$VENV/bin/playwright" install chromium
"$VENV/bin/playwright" install-deps chromium

echo "==> Restarting services..."
systemctl restart tg_bot
systemctl restart tg_bot_worker

echo "==> Service status:"
systemctl status tg_bot --no-pager
systemctl status tg_bot_worker --no-pager

echo "==> Deploy complete."
