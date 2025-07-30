#!/bin/bash
# Installation script for WebSocket JSON-RPC Server

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

# Function to run initial tests
run_initial_tests() {
    print_title "Running Initial Tests"
    
    print_status "Starting server in background for testing..."
    
    # Start server in background
    sudo -u www-data "$VENV_PATH/bin/python3" "$SERVER_DIR/server.py" &
    local server_pid=$!
    
    # Wait a moment for server to start
    sleep 3
    
    # Check if server is still running
    if ! kill -0 $server_pid 2>/dev/null; then
        print_error "Server failed to start"
        return 1
    fi
    
    print_status "Server started (PID: $server_pid)"
    
    # Run simple test
    if sudo -u www-data "$VENV_PATH/bin/python3" "$SERVER_DIR/test_client.py" --simple; then
        print_status "Initial test passed!"
    else
        print_error "Initial test failed"
    fi
    
    # Stop the server
    print_status "Stopping test server..."
    kill -TERM $server_pid
    wait $server_pid 2>/dev/null || true
    
    print_status "Test server stopped"
}

# Function to show completion message
show_completion_message() {
    print_title "Installation Complete"
    
    echo -e "${GREEN}WebSocket JSON-RPC Server has been installed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start the server:"
    echo "     sudo systemctl start $SERVICE_NAME"
    echo ""
    echo "  2. Check server status:"
    echo "     sudo systemctl status $SERVICE_NAME"
    echo ""
    echo "  3. Run tests:"
    echo "     cd $SERVER_DIR"
    echo "     sudo -u www-data $VENV_PATH/bin/python3 test_client.py"
    echo ""
    echo "  4. Use the start script:"
    echo "     sudo $SERVER_DIR/start_server.sh start"
    echo ""
    echo "Server will be available at: ws://localhost:8002/ws"
    echo "Logs location: $VENV_PATH/logs/server.log"
    echo ""
    echo "For more information, see: $SERVER_DIR/README.md"
}

# Function to cleanup on error
cleanup_on_error() {
    print_error "Installation failed. Cleaning up..."
    
    # Stop and disable service if it was created
    if systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        systemctl disable "$SERVICE_NAME" >/dev/null 2>&1 || true
    fi
    
    if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        systemctl daemon-reload
    fi
    
    print_error "Cleanup complete"
    exit 1
}

# Main installation function
main() {
    print_title "WebSocket JSON-RPC Server Installation"
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Run installation steps
    check_root
    check_prerequisites
    create_project_structure
    install_dependencies
    make_scripts_executable
    install_systemd_service
    run_initial_tests
    show_completion_message
    
    print_status "Installation completed successfully!"
}

# Run main function
main "$@"
