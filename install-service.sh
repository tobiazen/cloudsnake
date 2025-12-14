#!/bin/bash
# Cloudsnake Server Service Installation Script
# This script installs the cloudsnake server as a systemd service

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/cloudsnake.service"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_NAME="cloudsnake.service"

echo "============================================"
echo "Cloudsnake Server Service Installation"
echo "============================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Please run ./setup.sh first to create the virtual environment"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Detect the actual user who owns the cloudsnake directory
ACTUAL_USER=$(stat -c '%U' "$SCRIPT_DIR")
echo "Detected repository owner: $ACTUAL_USER"

# Create logs directory if it doesn't exist and set proper permissions
LOGS_DIR="$SCRIPT_DIR/logs"
if [ ! -d "$LOGS_DIR" ]; then
    echo "Creating logs directory..."
    mkdir -p "$LOGS_DIR"
fi

# Create empty log files with proper permissions
touch "$LOGS_DIR/cloudsnake-server.log"
touch "$LOGS_DIR/cloudsnake-server-errors.log"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$LOGS_DIR"
chmod 644 "$LOGS_DIR/cloudsnake-server.log"
chmod 644 "$LOGS_DIR/cloudsnake-server-errors.log"
echo "✓ Logs directory ready: $LOGS_DIR"

# Create a temporary service file with the correct user and paths
TEMP_SERVICE=$(mktemp)
sed "s/User=s0001311/User=$ACTUAL_USER/g" "$SERVICE_FILE" > "$TEMP_SERVICE"
sed -i "s|WorkingDirectory=/home/s0001311/dev/cloudsnake|WorkingDirectory=$SCRIPT_DIR|g" "$TEMP_SERVICE"
sed -i "s|ExecStart=/home/s0001311/dev/cloudsnake/venv|ExecStart=$SCRIPT_DIR/venv|g" "$TEMP_SERVICE"
sed -i "s|/home/s0001311/dev/cloudsnake/server.py|$SCRIPT_DIR/server.py|g" "$TEMP_SERVICE"
sed -i "s|StandardOutput=append:/home/s0001311/dev/cloudsnake/logs/|StandardOutput=append:$LOGS_DIR/|g" "$TEMP_SERVICE"
sed -i "s|StandardError=append:/home/s0001311/dev/cloudsnake/logs/|StandardError=append:$LOGS_DIR/|g" "$TEMP_SERVICE"

echo "Service will run as user: $ACTUAL_USER"
echo "Working directory: $SCRIPT_DIR"

# Stop existing service if running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Stopping existing cloudsnake service..."
    systemctl stop "$SERVICE_NAME"
fi

# Copy modified service file to systemd directory
echo "Installing service file..."
cp "$TEMP_SERVICE" "$SYSTEMD_DIR/$SERVICE_NAME"
rm "$TEMP_SERVICE"
echo "✓ Service file installed to $SYSTEMD_DIR/$SERVICE_NAME"

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

# Start the service
echo "Starting cloudsnake service..."
systemctl start "$SERVICE_NAME"

echo ""
echo "============================================"
echo "✓ Service installation complete!"
echo "============================================"
echo ""
echo "Service status:"
systemctl status "$SERVICE_NAME" --no-pager || true
echo ""
echo "Useful commands:"
echo "  Status:  sudo systemctl status cloudsnake"
echo "  Start:   sudo systemctl start cloudsnake"
echo "  Stop:    sudo systemctl stop cloudsnake"
echo "  Restart: sudo systemctl restart cloudsnake"
echo "  Logs:    sudo journalctl -u cloudsnake -f"
echo "  Disable: sudo systemctl disable cloudsnake"
echo ""
