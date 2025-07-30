#!/bin/bash
# Installation script for WebSocket JSON-RPC Server with Camera Monitoring

set -e

# Configuration
VENV_PATH="/opt/webcam-env"
SERVER_DIR="${VENV_PATH}/skeleton-server"
SERVICE_NAME="websocket-jsonrpc"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_title() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_title "Checking Prerequisites"
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found at $VENV_PATH"
        print_error "Please create the virtual environment first:"
        print_error "  sudo python3 -m venv $VENV_PATH"
        exit 1
    fi
    
    print_status "Virtual environment found at $VENV_PATH"
    
    # Check if Python executable exists
    if [ ! -f "$VENV_PATH/bin/python3" ]; then
        print_error "Python executable not found at $VENV_PATH/bin/python3"
        exit 1
    fi
    
    print_status "Python executable found"
    
    # Check if pip is available
    if ! "$VENV_PATH/bin/python3" -m pip --version > /dev/null 2>&1; then
        print_error "pip not available in virtual environment"
        exit 1
    fi
    
    print_status "pip is available"
}

# Function to install system dependencies
install_system_dependencies() {
    print_title "Installing System Dependencies"
    
    # Update package list
    print_status "Updating package list..."
    apt-get update
    
    # Install v4l-utils for camera capability detection
    print_status "Installing v4l-utils..."
    apt-get install -y v4l-utils
    
    # Verify v4l2-ctl is available
    if command -v v4l2-ctl > /dev/null 2>&1; then
        print_status "v4l2-ctl installed successfully"
        print_status "v4l2-ctl version: $(v4l2-ctl --version | head -n1)"
    else
        print_error "v4l2-ctl installation failed"
        exit 1
    fi
    
    # Install other useful camera tools
    print_status "Installing additional camera tools..."
    apt-get install -y uvcdynctrl guvcview || print_warning "Some additional tools may not be available"
    
    print_status "System dependencies installed successfully"
}

# Function to check camera permissions
setup_camera_permissions() {
    print_title "Setting Up Camera Permissions"
    
    # Add www-data user to video group for camera access
    usermod -a -G video www-data
    print_status "Added www-data user to video group"
    
    # Check if any video devices exist
    if ls /dev/video* > /dev/null 2>&1; then
        print_status "Video devices found:"
        ls -la /dev/video* | while read line; do
            print_status "  $line"
        done
        
        # Test v4l2-ctl access
        for device in /dev/video*; do
            if [ -c "$device" ]; then
                if sudo -u www-data v4l2-ctl --device="$device" --list-formats > /dev/null 2>&1; then
                    print_status "www-data can access $device"
                else
                    print_warning "www-data cannot access $device"
                fi
            fi
        done
    else
        print_warning "No video devices found - this is normal if no cameras are connected"
        print_status "The server will still start and monitor for camera connections"
    fi
}

# Function to create project structure
create_project_structure() {
    print_title "Creating Project Structure"
    
    # Create server directory
    mkdir -p "$SERVER_DIR"
    print_status "Created server directory: $SERVER_DIR"
    
    # Create logs directory
    mkdir -p "$VENV_PATH/logs"
    print_status "Created logs directory: $VENV_PATH/logs"
    
    # Set proper ownership
    chown -R www-data:www-data "$VENV_PATH"
    print_status "Set ownership to www-data:www-data"
    
    # Set proper permissions
    chmod -R 755 "$VENV_PATH"
    chmod -R 775 "$VENV_PATH/logs"
    print_status "Set proper permissions"
}

# Function to install Python dependencies
install_dependencies() {
    print_title "Installing Python Dependencies"
    
    # Check if requirements.txt exists
    if [ ! -f "$SERVER_DIR/requirements.txt" ]; then
        print_error "requirements.txt not found at $SERVER_DIR/requirements.txt"
        print_error "Please ensure all project files are in place"
        exit 1
    fi
    
    # Install dependencies
    print_status "Installing dependencies from requirements.txt"
    sudo -u www-data "$VENV_PATH/bin/python3" -m pip install -r "$SERVER_DIR/requirements.txt"
    
    print_status "Dependencies installed successfully"
}

# Function to install systemd service
install_systemd_service() {
    print_title "Installing Systemd Service"
    
    # Check if service file exists
    if [ ! -f "$SERVER_DIR/websocket-jsonrpc.service" ]; then
        print_warning "Service file not found at $SERVER_DIR/websocket-jsonrpc.service"
        print_warning "Skipping systemd service installation"
        return
    fi
    
    # Copy service file
    cp "$SERVER_DIR/websocket-jsonrpc.service" "/etc/systemd/system/"
    print_status "Copied service file to /etc/systemd/system/"
    
    # Reload systemd
    systemctl daemon-reload
    print_status "Reloaded systemd daemon"
    
    # Enable service
    systemctl enable "$SERVICE_NAME"
    print_status "Enabled $SERVICE_NAME service"
    
    print_status "Service installation complete"
    print_status "Use 'sudo systemctl start $SERVICE_NAME' to start the service"
}

# Function to make scripts executable
make_scripts_executable() {
    print_title "Making Scripts Executable"
    
    local scripts=("start_server.sh" "test_client.py" "server.py")
    
    for script in "${scripts[@]}"; do
        if [ -f "$SERVER_DIR/$script" ]; then
            chmod +x "$SERVER_DIR/$script"
            print_status "Made $script executable"
        else
            print_warning "$script not found, skipping"
        fi
    done
}

# Function to test camera functionality
test_camera_functionality() {
    print_title "Testing Camera Functionality"
    
    # Test v4l2-ctl as www-data user
    print_status "Testing v4l2-ctl access..."
    if sudo -u www-data v4l2-ctl --list-devices > /dev/null 2>&1; then
        print_status "v4l2-ctl works for www-data user"
    else
        print_warning "v4l2-ctl may not work properly for www-data user"
    fi
    
    # List available cameras
    print_status "Scanning for cameras..."
    if ls /dev/video* > /dev/null 2>&1; then
        for device in /dev/video*; do
            if [ -c "$device" ]; then
                print_status "Found camera device: $device"
                
                # Try to get device info
                if sudo -u www-data v4l2-ctl --device="$device" --info > /