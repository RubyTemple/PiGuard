#!/bin/bash
set -e

echo "Installing PiGuard-Hybrid..."

# Ensure pip/flask is installed
if ! python3 -c "import flask" &> /dev/null; then
    echo "Flask is required. Attempting to install via apt/pip..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y python3-flask || true
    fi
    # Fallback to pip if apt-get failed or wasn't available
    if ! python3 -c "import flask" &> /dev/null; then
        if command -v pip3 &> /dev/null; then
            pip3 install flask || true
        fi
    fi
fi

# Create opt directory
mkdir -p /opt/piguard
cp -r daemon /opt/piguard/

# Create config directory
mkdir -p /etc/piguard
if [ ! -f /etc/piguard/config.json ]; then
    cp config/config.json /etc/piguard/config.json
    echo "Default config installed to /etc/piguard/config.json"
else
    echo "Config already exists at /etc/piguard/config.json. Skipping config overwrite."
fi

# Install systemd service
cp systemd/piguard.service /etc/systemd/system/
chmod 644 /etc/systemd/system/piguard.service

# Reload and enable
systemctl daemon-reload
systemctl enable piguard.service
systemctl restart piguard.service

echo "PiGuard successfully installed and started."
echo "Check status with: systemctl status piguard"
