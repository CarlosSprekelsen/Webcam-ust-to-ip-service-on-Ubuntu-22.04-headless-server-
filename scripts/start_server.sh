#!/bin/bash
# Start/Stop script for WebSocket JSON-RPC Server

set -e

VENV_PATH="/opt/webcam-env"
SERVER_DIR="${VENV_PATH}/webcam_ip"
PYTHON_EXEC="${VENV_PATH}/bin/python3"
LOG_DIR="${VENV_PATH}/logs"
PID_FILE="${VENV_PATH}/server.pid"
SERVER_MODULE="webcam_ip.server.websocket_server"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status()   { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning()  { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()    { echo -e "${RED}[ERROR]${NC} $1"; }

is_server_running() {
    [[ -f "$PID_FILE" ]] && kill -0 $(cat "$PID_FILE") 2>/dev/null
}

start_server() {
    print_status "Starting WebSocket JSON-RPC Server..."
    if is_server_running; then
        print_warning "Server is already running (PID: $(cat $PID_FILE))"
        exit 1
    fi
    if [[ ! -d "$VENV_PATH" ]]; then
        print_error "Virtual environment not found at $VENV_PATH"; exit 1; fi
    if [[ ! -f "$PYTHON_EXEC" ]]; then
        print_error "Python executable not found at $PYTHON_EXEC"; exit 1; fi
    if [[ ! -d "$LOG_DIR" ]]; then
        mkdir -p "$LOG_DIR"
        chmod 775 "$LOG_DIR"
    fi
    # Start as www-data (adjust as needed for your setup)
    nohup sudo -u www-data "$PYTHON_EXEC" -m "$SERVER_MODULE" \
        > "$LOG_DIR/server.out" 2> "$LOG_DIR/server.err" &
    echo $! > "$PID_FILE"
    print_status "Server started (PID: $(cat $PID_FILE))"
}

stop_server() {
    print_status "Stopping WebSocket JSON-RPC Server..."
    if ! is_server_running; then
        print_warning "Server is not running"
        rm -f "$PID_FILE"
        exit 0
    fi
    PID=$(cat "$PID_FILE")
    kill -TERM "$PID"
    timeout=10; count=0
    while is_server_running && [[ $count -lt $timeout ]]; do
        sleep 1
        ((count++))
        print_status "Waiting for graceful shutdown... ($count/$timeout)"
    done
    if is_server_running; then
        print_warning "Server did not shutdown gracefully, sending SIGKILL"
        kill -KILL "$PID"
    fi
    rm -f "$PID_FILE"
    print_status "Server stopped"
}

check_status() {
    if is_server_running; then
        print_status "Server is running (PID: $(cat $PID_FILE))"
        if ss -tlnp 2>/dev/null | grep -q ":8002"; then
            print_status "Server is listening on port 8002"
        else
            print_warning "Server running but port 8002 is not listening"
        fi
        [ -f "$LOG_DIR/server.log" ] && { print_status "Recent log entries:"; tail -n 5 "$LOG_DIR/server.log"; }
    else
        print_status "Server is not running"
    fi
}

restart_server() {
    print_status "Restarting WebSocket JSON-RPC Server..."
    stop_server
    sleep 2
    start_server
}

run_tests() {
    print_status "Running server tests..."
    TEST_CLIENT="$SERVER_DIR/test_client.py"
    if [[ ! -f "$TEST_CLIENT" ]]; then
        print_error "Test client not found at $TEST_CLIENT"; exit 1; fi
    sudo -u www-data "$PYTHON_EXEC" "$TEST_CLIENT" "$@"
}

show_usage() {
    echo "Usage: $0 {start|stop|restart|status|test|help}"
    echo "  start    - Start the WebSocket JSON-RPC server"
    echo "  stop     - Stop the WebSocket JSON-RPC server"
    echo "  restart  - Restart the server"
    echo "  status   - Show server status"
    echo "  test     - Run test_client.py"
    echo "  help     - Show this help message"
}

case "${1:-}" in
    start)   start_server ;;
    stop)    stop_server ;;
    restart) restart_server ;;
    status)  check_status ;;
    test)    shift; run_tests "$@" ;;
    help|--help|-h) show_usage ;;
    *) print_error "Invalid command: ${1:-}"; echo ""; show_usage; exit 1 ;;
esac
