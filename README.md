# WebSocket JSON-RPC 2.0 Server with Camera Monitoring

A Python service that provides a WebSocket endpoint with JSON-RPC 2.0 protocol support and real-time USB camera status monitoring. This server automatically detects when USB webcams are connected or disconnected and broadcasts notifications to all connected clients.

## Features

- **WebSocket Server**: Listens on `ws://0.0.0.0:8002/ws`
- **JSON-RPC 2.0 Compliance**: Full support for JSON-RPC 2.0 specification
- **Real-time Camera Monitoring**: Detects USB webcam connect/disconnect events within 200ms
- **Camera Status Notifications**: Broadcasts camera status updates to all connected clients
- **Camera Capability Detection**: Automatically detects resolution and FPS for connected cameras
- **Ping Method**: Simple health check method that returns "pong"
- **Comprehensive Logging**: Logs all connections, disconnections, and camera status changes
- **High Performance**: Uses uvloop for optimized event loop performance
- **Graceful Shutdown**: Handles SIGTERM and SIGINT signals properly

## Prerequisites

- Ubuntu 22.04 server (updated and upgraded)
- Python 3.10+ virtual environment at `/opt/webcam-env`
- Virtual environment activated
- **System package**: `v4l-utils` for camera capability detection

## Installation

1. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install v4l-utils
   ```

2. **Navigate to the project directory:**
   ```bash
   cd /opt/webcam-env
   mkdir -p webcam_ip
   cd webcam_ip
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create logs directory:**
   ```bash
   mkdir -p /opt/webcam-env/logs
   ```

## Usage

### Starting the Server

**Method 1: Direct execution**
```bash
python3 server.py
```

**Method 2: As a module**
```bash
python3 -m server
```

**Method 3: Using the start script**
```bash
./start_server.sh start
```

The server will start and listen on `ws://0.0.0.0:8002/ws`.

### Expected Output
```
2025-07-30 10:00:00,000 - __main__ - INFO - Starting WebSocket JSON-RPC server on 0.0.0.0:8002/ws
2025-07-30 10:00:00,001 - __main__ - INFO - Camera monitoring started
2025-07-30 10:00:00,100 - __main__ - INFO - Initial camera status: /dev/video0 - CONNECTED
2025-07-30 10:00:00,101 - __main__ - INFO - Server started successfully at ws://0.0.0.0:8002/ws
```

### Stopping the Server
- Press `Ctrl+C` for graceful shutdown
- Send `SIGTERM` signal: `kill -TERM <pid>`
- Use start script: `./start_server.sh stop`

## Camera Monitoring

### Automatic Notifications

The server automatically monitors USB camera devices and sends JSON-RPC notifications when cameras are connected or disconnected:

#### Camera Connected Notification
```json
{
  "jsonrpc": "2.0",
  "method": "camera_status_update",
  "params": {
    "status": "CONNECTED",
    "device": "/dev/video0",
    "resolution": "640x480",
    "fps": 30
  }
}
```

#### Camera Disconnected Notification
```json
{
  "jsonrpc": "2.0",
  "method": "camera_status_update",
  "params": {
    "status": "DISCONNECTED",
    "device": "/dev/video0"
  }
}
```

### Features

- **Initial Status**: Server sends camera status on startup
- **Real-time Detection**: Detects changes within 200ms
- **Automatic Capability Detection**: Resolution and FPS are detected automatically
- **Multiple Camera Support**: Monitors `/dev/video0` through `/dev/video9`
- **Broadcast to All Clients**: Notifications sent to all connected WebSocket clients

## Testing

### Quick Tests

**Simple ping test:**
```bash
python3 test_client.py --simple
```

**Camera monitoring demo:**
```bash
python3 test_client.py --monitor --duration 30
```

### Full Test Suite
```bash
python3 test_client.py
```

The test suite includes:
- **Ping Test**: Verifies the ping method returns "pong"
- **Invalid Method Test**: Tests error handling for non-existent methods
- **Malformed JSON Test**: Tests error handling for invalid JSON
- **Camera Notification Test**: Monitors camera status changes

### Expected Test Output
```
✅ Ping test passed! Response: 'pong' in 12.34 ms
✅ Response time (12.34 ms) is within 50ms threshold
✅ Invalid method test passed! Got expected error: {'code': -32601, 'message': 'Method not found: invalid_method'}
✅ Malformed JSON test passed! Got expected parse error: {'code': -32700, 'message': 'Parse error'}
📷 Testing camera status notifications for 15 seconds...
💡 Plug/unplug a USB camera during this test to verify notifications
📷 Camera Status Update: /dev/video0 -> CONNECTED
   Resolution: 640x480, FPS: 30
✅ Camera notification test passed! Received 1 notifications

🎉 All tests passed!
```

### Manual Camera Testing

1. **Start the server:**
   ```bash
   python3 server.py
   ```

2. **In another terminal, run the monitoring demo:**
   ```bash
   python3 test_client.py --monitor --duration 60
   ```

3. **Physically plug/unplug a USB webcam** and observe real-time notifications

## Manual Testing with WebSocket Client

You can also test manually using any WebSocket client:

### JSON-RPC 2.0 Ping Request
```json
{
  "jsonrpc": "2.0",
  "method": "ping",
  "id": 1
}
```

### Expected Response
```json
{
  "jsonrpc": "2.0",
  "result": "pong",
  "id": 1
}
```

### Camera Status Notifications
When you connect to the WebSocket, you'll automatically receive camera status notifications as JSON-RPC notifications (no `id` field since they're notifications, not responses).

## API Documentation

### Supported Methods

#### `ping`
- **Description**: Health check method
- **Parameters**: None
- **Returns**: `"pong"`
- **Example**:
  ```json
  Request:  {"jsonrpc": "2.0", "method": "ping", "id": 1}
  Response: {"jsonrpc": "2.0", "result": "pong", "id": 1}
  ```

### Notifications

#### `camera_status_update`
- **Description**: Automatic notification sent when camera status changes
- **Type**: JSON-RPC 2.0 Notification (no response expected)
- **Parameters**:
  - `status`: `"CONNECTED"` or `"DISCONNECTED"`
  - `device`: Device path (e.g., `"/dev/video0"`)
  - `resolution`: Camera resolution (only when CONNECTED, e.g., `"640x480"`)
  - `fps`: Camera frame rate (only when CONNECTED, e.g., `30`)

### Error Codes

The server implements standard JSON-RPC 2.0 error codes:

- **-32700**: Parse error (Invalid JSON)
- **-32600**: Invalid Request (Missing required fields)
- **-32601**: Method not found
- **-32603**: Internal error

## Logging

### Log Levels
- **INFO**: Connection events, method calls, camera status changes, request/response logging
- **ERROR**: Error conditions, exceptions
- **DEBUG**: Detailed debugging information (when enabled)

### Log Locations
- **Console**: Standard output
- **File**: `/opt/webcam-env/logs/server.log`

### Sample Log Entries
```
2025-07-30 10:01:00,000 - __main__ - INFO - Client connected: 127.0.0.1:54321 (Total clients: 1)
2025-07-30 10:01:00,001 - __main__ - INFO - Camera connected: /dev/video0 - 640x480 @ 30fps
2025-07-30 10:01:00,002 - __main__ - INFO - Broadcasting camera status to 1 clients: {"jsonrpc":"2.0","method":"camera_status_update","params":{"status":"CONNECTED","device":"/dev/video0","resolution":"640x480","fps":30}}
2025-07-30 10:01:00,003 - __main__ - INFO - Received from 127.0.0.1:54321: {"jsonrpc":"2.0","method":"ping","id":1}
2025-07-30 10:01:00,004 - __main__ - INFO - Ping method called
2025-07-30 10:01:00,005 - __main__ - INFO - Sending to 127.0.0.1:54321: {"jsonrpc":"2.0","result":"pong","id":1}
2025-07-30 10:01:10,000 - __main__ - INFO - Camera disconnected: /dev/video0
2025-07-30 10:01:15,000 - __main__ - INFO - Client disconnected: 127.0.0.1:54321 (Total clients: 0)
```

## Project Structure

```
webcam-service/
├── webcam_ip/                    # Main package
│   ├── __init__.py
│   ├── __main__.py              # Entry point: python -m webcam_ip
│   ├── config.py                # Configuration management
│   ├── server/
│   │   ├── __init__.py
│   │   ├── websocket_server.py  # WebSocket connection handling
│   │   ├── jsonrpc_handler.py   # JSON-RPC request/response logic
│   │   └── methods.py           # RPC method implementations
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── monitor.py           # Camera monitoring logic
│   │   ├── detector.py          # Camera capability detection
│   │   └── models.py            # CameraInfo and related models
│   └── utils/
│       ├── __init__.py
│       ├── logging.py           # Logging configuration
│       └── signals.py           # Signal handling
├── tests/
│   ├── __init__.py
│   ├── test_camera_monitor.py
│   ├── test_jsonrpc.py
│   └── conftest.py              # pytest configuration
├── config/
│   ├── config.yaml              # Default configuration
│   └── logging.yaml             # Logging configuration
├── scripts/
│   ├── install.sh
│   └── start_server.sh
├── systemd/
│   └── webcam-service.service
├── setup.py
├── requirements.txt
└── README.md
```

## Architecture

### Server Components
- **WebSocketJSONRPCServer**: Main server class handling WebSocket connections
- **CameraMonitor**: Real-time USB camera monitoring with threading
- **CameraInfo**: Data structure for camera information
- **JSON-RPC Handler**: Processes JSON-RPC 2.0 requests and responses
- **Method Registry**: Currently supports the `ping` method
- **Connection Manager**: Tracks connected clients and broadcasts notifications
- **Logger**: Comprehensive logging system

### Camera Monitoring Features
- **Real-time Detection**: Polls camera devices every 100ms for sub-200ms response
- **Capability Detection**: Uses `v4l2-ctl` to detect resolution and FPS
- **Multiple Device Support**: Monitors `/dev/video0` through `/dev/video9`
- **Thread Safety**: Uses threading locks for safe concurrent access
- **Initial Status**: Sends status on startup
- **Graceful Cleanup**: Proper thread cleanup on shutdown

### Performance Features
- **uvloop**: High-performance event loop for better throughput
- **Async/Await**: Non-blocking I/O operations
- **Connection Pooling**: Efficient client connection management
- **Graceful Shutdown**: Proper cleanup of resources
- **Fast Polling**: 100ms camera polling for responsive detection

## System Requirements

### Hardware
- USB webcam(s) compatible with Video4Linux2 (V4L2)
- Sufficient USB bandwidth for multiple cameras

### Software
- **Python 3.10+**
- **v4l-utils** package (`sudo apt-get install v4l-utils`)
- Virtual environment with required Python packages

### Performance
- **Camera Detection**: Sub-200ms response time for USB events
- **Ping Response**: Typically < 5ms for ping requests
- **Throughput**: Supports 1000+ concurrent WebSocket connections
- **Memory Usage**: ~15MB base memory footprint + camera monitoring overhead

## Troubleshooting

### Common Issues

1. **Port 8002 already in use**
   ```bash
   sudo lsof -i :8002
   sudo kill -9 <pid>
   ```

2. **Permission denied for camera devices**
   ```bash
   sudo usermod -a -G video $USER
   # Log out and back in
   ```

3. **v4l2-ctl command not found**
   ```bash
   sudo apt-get install v4l-utils
   ```

4. **Camera not detected**
   ```bash
   # Check if camera is recognized by system
   lsusb | grep -i camera
   ls -la /dev/video*
   v4l2-ctl --list-devices
   ```

5. **No camera notifications received**
   - Ensure camera supports V4L2 (`v4l2-ctl --list-devices`)
   - Check camera permissions (`ls -la /dev/video*`)
   - Verify camera works with other applications
   - Check server logs for errors

6. **Permission denied for logs directory**
   ```bash
   sudo mkdir -p /opt/webcam-env/logs
   sudo chown $USER:$USER /opt/webcam-env/logs
   ```

### Debug Mode
To enable debug logging, modify the logging level in `server.py`:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

### Camera Debugging
```bash
# List all video devices
v4l2-ctl --list-devices

# Check device capabilities
v4l2-ctl --device=/dev/video0 --list-formats-ext

# Test camera with simple capture
ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test.jpg
```

## Security Considerations

- Server binds to `0.0.0.0` for development; consider restricting to specific interfaces in production
- No authentication implemented in skeleton version
- Consider adding rate limiting for production deployment
- WebSocket connections are not encrypted (consider WSS for production)
- Camera access requires appropriate permissions

## Future Enhancements

This server can be extended with:
- Camera control methods (resolution change, capture, etc.)
- Authentication and authorization
- Rate limiting
- SSL/TLS support (WSS)
- Configuration file support
- Health check endpoints
- Metrics and monitoring integration
- Support for other camera types (IP cameras, etc.)
- Camera streaming capabilities

## Contributing

1. Follow PEP 8 style guidelines
2. Add comprehensive logging for new methods
3. Include tests for new functionality
4. Update documentation for API changes
5. Test camera functionality with real hardware

## License

This project is part of the camera service infrastructure.

## TODO (as of 2025-07-31)

### 1. Media Capture Functionality

- [ ] **Implement JSON-RPC media methods:**
    - [ ] `take_snapshot`: Capture a frame from the active camera and save to disk.
    - [ ] `start_recording`: Begin video recording to file.
    - [ ] `stop_recording`: Stop the current recording operation.
    - [ ] `schedule_snapshots`: Capture periodic snapshots as scheduled.
    - [ ] `schedule_recording`: Start/stop recording based on scheduled times.
- [ ] Integrate with `ffmpeg` or GStreamer (via subprocess) for snapshot and recording.
- [ ] Store resulting files in the configured media output directory (e.g., `/opt/media/`).
- [ ] Generate and store a metadata `.json` file for each snapshot/recording (timestamp, resolution, FPS, etc.).

### 2. API Validation & Robustness

- [ ] Add parameter schema validation for all JSON-RPC methods (using Pydantic or manual validation).
- [ ] Surface critical hardware errors as health notifications or status endpoints (not just in logs).
- [ ] Ensure all persistent/hard failures are logged and surfaced to clients as needed.

### 3. Testing

- [ ] Expand `test_client.py` to cover all implemented API methods (including media and error cases).
- [ ] Add/complete pytest suite:
    - [ ] Add or expand tests for camera signal handling and graceful shutdown.
    - [ ] Include `test_client.py` in the ordered suite (`run_all_validation.py`).
- [ ] Integrate all tests into a CI pipeline (e.g., GitHub Actions, GitLab CI).

### 4. Configuration & Deployment

- [ ] Fully document the structure and schema of `config/config.yaml` (and/or `config.json`).
- [ ] Create `docs/03.Configuration.md`:
    - [ ] List all supported environment variables, defaults, and their mapping to config files.
    - [ ] Explain how to override configuration via env vars or custom config files.
- [ ] Ensure all configuration and log directory permission errors are gracefully handled (fallback to console logging if file logging fails).
- [ ] Create or expand `docs/04.Deployment.md`:
    - [ ] Document deployment, systemd service setup, startup scripts, and permission setup.

### 6. Documentation
- [ ] Update README to include:
  - [ ] New snapshot/recording API methods and example usage (refer to docs-API.md).
  - [ ] Environment variables table (host, port, poll interval, log settings).
  - [ ] Quickstart “clone → install → test → run” commands.
- [ ] - Create a `docs/` folder with:
  - [ ] - `05.Validation.md` updated to list all test files (`validate_config.py`, `test_imports.py`, `test_jsonrpc.py`, `test_camera_models.py`, `test_logging.py`, `test_signals.py`, `test_client.py`, `test_integration.py`) in the proper order.
  - [ ] - `06.ClientDemo.md` (or include in README) with a minimal `client_demo.py` example and usage instructions.
- [ ] Align README.md with implemented features based on actual code.
- [ ] Simplify README.md  and refer to complete docs under docs folder

### 6. Additional Enhancements (Future)

- [ ] Add authentication and authorization for client connections.
- [ ] Add support for WSS (WebSocket Secure) and TLS configuration.
- [ ] Implement camera control methods (resolution/focus/zoom, if hardware supports).
- [ ] Add metrics and health endpoints for monitoring/observability (Prometheus, etc.).
- [ ] Support for additional camera types (e.g., IP cameras, MJPEG streams).

---

**Legend:**  
- `[ ]` = Not started  
- `[x]` = Completed (mark as you progress)

--- OLDER TODO, to merge or update if already done.

## API Validation & Error Handling
- Add parameter schema validation for all JSON-RPC methods (e.g. using `pydantic` or manual checks).
- Surface critical hardware errors as server health metrics or notifications.
- Ensure JSON-RPC handler catches and logs all exceptions without masking persistent failures.

## Testing
- Add CI pipeline step to run tests automatically.

## Configuration & Deployment
- Support external configuration file (e.g. `config.json`) in addition to environment variables.
- Handle log-directory permission errors gracefully (fallback to console only).
- Add systemd service file and startup script to repository.

## Packaging & Code Quality
- Remove or consolidate redundant `__init__.py` imports to avoid circular dependencies.
- Refine module structure to minimize relative imports and improve clarity.
- Lint and format codebase (e.g. `flake8`, `black`).

## Device Enumeration
- Extend device discovery beyond `/dev/video0-9`:
  - Automatically detect all V4L2 devices (`v4l2-ctl --list-devices`).
  - Ignore non-camera video devices.

## Logging & Observability
- Leverage `StructuredLogger` consistently across modules.
- Expose server health and metrics via a JSON-RPC or HTTP endpoint (e.g. Prometheus).
