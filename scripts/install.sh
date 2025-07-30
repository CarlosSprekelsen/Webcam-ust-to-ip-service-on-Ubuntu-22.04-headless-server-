#!/bin/bash
# Installation script for WebSocket JSON-RPC Server with Camera Monitoring

set -e

# === CONFIGURATION ===
VENV_PATH="/opt/webcam-env"
SERVER_DIR="${VENV_PATH}/webcam_ip"
LOG_DIR="${VENV_PATH}/logs"
SERVICE_NAME="websocket-jsonrpc"
SYSTEMD_UNIT_SRC="./systemd/websocket-jsonrpc.service"
SYSTEMD_UNIT_DST="/etc/systemd/system/websocket-jsonrpc.service"
PYTHON_VERSION="python3.10"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status()   { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning()  { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()    { echo -e "${RED}[ERROR]${NC} $1"; }
print_title()    { echo -e "\n${BLUE}=== $1 ===${NC}"; }

# Check root
if [[ "$EUID" -ne 0 ]]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

print_title "Installing System Dependencies"
apt-get update
apt-get install -y v4l-utils $PYTHON_VERSION $PYTHON_VERSION-venv || {
    print_error "Failed to install system dependencies"; exit 1; }
print_status "System dependencies installed"

print_title "Creating Virtual Environment"
if [[ ! -d "$VENV_PATH" ]]; then
    $PYTHON_VERSION -m venv "$VENV_PATH"
    print_status "Virtualenv created at $VENV_PATH"
else
    print_status "Virtualenv found at $VENV_PATH"
fi

print_title "Preparing Project Structure"
mkdir -p "$SERVER_DIR"
mkdir -p "$LOG_DIR"
chown -R www-data:www-data "$VENV_PATH"
chmod -R 755 "$VENV_PATH"
chmod -R 775 "$LOG_DIR"
print_status "Project structure and permissions set"

print_title "Activating Virtual Environment and Installing Python Dependencies"
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
REQ_FILE="$SERVER_DIR/requirements.txt"
if [[ ! -f "$REQ_FILE" ]]; then
    # Fallback: try project root
    REQ_ROOT="$(pwd)/requirements.txt"
    if [[ -f "$REQ_ROOT" ]]; then
        cp "$REQ_ROOT" "$REQ_FILE"
        print_status "Copied requirements.txt from project root"
    else
        print_error "requirements.txt not found in $SERVER_DIR or project root"
        exit 1
    fi
fi
pip install -r "$REQ_FILE"
print_status "Python dependencies installed"

print_title "Setting Camera Permissions"
usermod -a -G video www-data
print_status "Added www-data user to video group (re-login may be required for changes to take effect)"

print_title "(Optional) Installing Systemd Service"
if [[ -f "$SYSTEMD_UNIT_SRC" ]]; then
    cp "$SYSTEMD_UNIT_SRC" "$SYSTEMD_UNIT_DST"
    chmod 644 "$SYSTEMD_UNIT_DST"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    print_status "Systemd service installed and enabled. Use 'systemctl start $SERVICE_NAME' to start."
else
    print_warning "Systemd unit file $SYSTEMD_UNIT_SRC not found; skipping systemd setup."
fi

print_title "Final Steps"
print_status "To start the server in foreground: sudo -u www-data $VENV_PATH/bin/python3 -m webcam_ip.server.websocket_server"
print_status "Or use the start script: sudo ./start_server.sh start"
print_status "Or, if systemd enabled: sudo systemctl start $SERVICE_NAME"
print_status "Installation complete!"
