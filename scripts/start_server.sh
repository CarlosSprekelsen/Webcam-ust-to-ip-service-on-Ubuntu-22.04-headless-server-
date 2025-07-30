#!/bin/bash
# Start script for WebSocket JSON-RPC Server

set -e

# Configuration
VENV_PATH="/opt/webcam-env"
SERVER_DIR="${VENV_PATH}/webcam_ip"
PYTHON_EXEC="${VENV_PATH}/bin/python3"
SERVER_SCRIPT="-m webcam_ip.server.websocket_server"
LOG_DIR="${VENV_PATH}/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if server is running
is_server_running() {
    if pgrep -f "python.*server.py" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to get server PID
get_server_pid() {
    pgrep -f "python.*server.py"
}

# Function to start the server
start_server() {
    print_status "Starting WebSocket JSON-RPC Server..."
    
    # Check if server is already running
    if is_server_running; then
        print_warning "Server is already running (PID: $(get_server_pid))"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found at $VENV_PATH"
        exit 1
    fi
    
    # Check if Python executable exists
    if [ ! -f "$PYTHON_EXEC" ]; then
        print_error "Python executable not found at $PYTHON_EXEC"
        exit 1
    fi
    
    # Check if server directory exists
    if [ ! -d "$SERVER_DIR" ]; then
        print_error "Server directory not found at $SERVER_DIR"
        exit 1
    fi
    
    # Check if server script exists
    if [ ! -f "$SERVER_DIR/$SERVER_SCRIPT" ]; then
        print_error "Server script not found at $SERVER_DIR/$SERVER_SCRIPT"
        exit 1
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p "$LOG_DIR"
    
    # Change to server directory
    cd "$SERVER_DIR"
    
    # Start the server
    print_status "Executing: $PYTHON_EXEC $SERVER_SCRIPT"
    exec "$PYTHON_EXEC" "$SERVER_SCRIPT"
}

# Function to stop the server
stop_server() {
    print_status "Stopping WebSocket JSON-RPC Server..."
    
    if ! is_server_running; then
        print_warning "Server is not running"
        exit 1
    fi
    
    local pid=$(get_server_pid)
    print_status "Sending SIGTERM to process $pid"
    kill -TERM "$pid"
    
    # Wait for graceful shutdown
    local timeout=10
    local count=0
    while is_server_running && [ $count -lt $timeout ]; do
        sleep 1
        ((count++))
        print_status "Waiting for graceful shutdown... ($count/$timeout)"
    done
    
    if is_server_running; then
        print_warning "Server did not shutdown gracefully, sending SIGKILL"
        kill -KILL "$pid"
    fi
    
    print_status "Server stopped"
}

# Function to check server status
check_status() {
    if is_server_running; then
        local pid=$(get_server_pid)
        print_status "Server is running (PID: $pid)"
        
        # Check if port 8002 is listening
        if netstat -tlnp 2>/dev/null | grep -q ":8002.*LISTEN"; then
            print_status "Server is listening on port 8002"
        else
            print_warning "Server process found but port 8002 is not listening"
        fi
        
        # Show recent log entries
        if [ -f "$LOG_DIR/server.log" ]; then
            print_status "Recent log entries:"
            tail -n 5 "$LOG_DIR/server.log"
        fi
    else
        print_status "Server is not running"
    fi
}

# Function to restart the server
restart_server() {
    print_status "Restarting WebSocket JSON-RPC Server..."
    
    if is_server_running; then
        stop_server
        sleep 2
    fi
    
    start_server
}

# Function to run tests
run_tests() {
    print_status "Running server tests..."
    
    # Check if test client exists
    if [ ! -f "$SERVER_DIR/test_client.py" ]; then
        print_error "Test client not found at $SERVER_DIR/test_client.py"
        exit 1
    fi
    
    # Change to server directory
    cd "$SERVER_DIR"
    
    # Run tests
    "$PYTHON_EXEC" test_client.py "$@"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {start|stop|restart|status|test|help}"
    echo ""
    echo "Commands:"
    echo "  start    - Start the WebSocket JSON-RPC server"
    echo "  stop     - Stop the WebSocket JSON-RPC server"
    echo "  restart  - Restart the WebSocket JSON-RPC server"
    echo "  status   - Check server status"
    echo "  test     - Run server tests"
    echo "  help     - Show this help message"
    echo ""
    echo "Test options:"
    echo "  $0 test --simple    - Run simple ping test only"
    echo "  $0 test             - Run full test suite"
}

# Main script logic
case "${1:-}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        check_status
        ;;
    test)
        shift # Remove 'test' from arguments
        run_tests "$@"
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Invalid command: ${1:-}"
        echo ""
        show_usage
        exit 1
        ;;
esac
