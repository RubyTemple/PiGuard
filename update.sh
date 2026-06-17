#!/bin/bash
set -e

echo "Updating PiGuard-Hybrid..."

# Pull latest changes if this is a git repository
if [ -d ".git" ]; then
    echo "Fetching latest updates from git..."
    git pull || echo "Warning: git pull failed or no remote configured."
fi

echo "Stopping PiGuard service..."
systemctl stop piguard.service || true

echo "Updating daemon files..."
cp -r daemon/* /opt/piguard/

echo "Restarting PiGuard service..."
systemctl daemon-reload
systemctl start piguard.service

echo "PiGuard successfully updated and restarted."
echo "Check status with: systemctl status piguard"
