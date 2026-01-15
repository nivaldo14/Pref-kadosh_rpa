#!/bin/bash
set -e

echo "Running custom Vercel build script..."

# Install Python dependencies from requirements.txt
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers to /tmp directory
echo "Installing Playwright browsers..."
PLAYWRIGHT_BROWSERS_PATH=/tmp/.ms-playwright playwright install chromium

echo "Custom Vercel build script finished."
