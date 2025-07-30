#!/usr/bin/env python3
"""
WebSocket JSON-RPC 2.0 Server with USB Camera Monitoring
Enhanced version that monitors USB webcam connect/disconnect events
and emits real-time status notifications to connected clients.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import websockets
from jsonrpcserver import method, Success, Result
import uvloop

# Configure logging
LOG_DIR = Path("/opt/webcam-env/logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "server.log", mode='a')
    ]
)

logger = logging.getLogger(__name__)

class CameraInfo:
    """Container for camera information"""
    def __init__(self, device: str, connected: bool = False, 
                 resolution: str = "", fps: int = 0):
        self.device = device
        self.connected = connected
        self.resolution = resolution
        self.fps = fps
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON-RPC notification"""
        data = {
            "status": "CONNECTED" if self.connected else "DISCONNECTED",
            "device": self.device
        }
        if self.connected:
            data["resolution"] = self.resolution
            data["fps"] = self.fps
        return data

class CameraMonitor:
    """Monitors USB camera connect/disconnect events"""
    
    def __init__(self, callback):
        self.callback = callback
        self.monitoring = False
        self.monitor_thread = None
        self.known_cameras: Dict[str, CameraInfo] = {}
        self.lock = threading.Lock()
    
    def start_monitoring(self):
        """Start camera monitoring in a separate thread"""
        if self.monitoring:
            logger.warning("Camera monitoring already started")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Camera monitoring started")
        
        # Send initial status
        asyncio.create_task(self._send_initial_status())
    
    def stop_monitoring(self):
        """Stop camera monitoring"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        logger.info("Camera monitoring stopped")
    
    async def _send_initial_status(self):
        """Send initial camera status on startup"""
        # Small delay to ensure WebSocket connections are established
        await asyncio.sleep(0.1)
        
        current_cameras = self._detect_cameras()
        
        with self.lock:
            if current_cameras:
                for device, camera_info in current_cameras.items():
                    self.known_cameras[device] = camera_info
                    logger.info(f"Initial camera status: {device} - CONNECTED")
                    asyncio.create_task(self.callback(camera_info.to_dict()))
            else:
                # Send disconnected status for /dev/video0 if no cameras found
                camera_info = CameraInfo("/dev/video0", connected=False)
                self.known_cameras["/dev/video0"] = camera_info
                logger.info("Initial camera status: /dev/video0 - DISCONNECTED")
                asyncio.create_task(self.callback(camera_info.to_dict()))
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Camera monitoring loop started")
        
        while self.monitoring:
            try:
                current_cameras = self._detect_cameras()
                
                with self.lock:
                    # Check for newly connected cameras
                    for device, camera_info in current_cameras.items():
                        if device not in self.known_cameras:
                            self.known_cameras[device] = camera_info
                            logger.info(f"Camera connected: {device} - {camera_info.resolution} @ {camera_info.fps}fps")
                            asyncio.run_coroutine_threadsafe(
                                self.callback(camera_info.to_dict()),
                                asyncio.get_event_loop()
                            )
                    
                    # Check for disconnected cameras
                    for device in list(self.known_cameras.keys()):
                        if device not in current_cameras:
                            if self.known_cameras[device].connected:
                                # Mark as disconnected
                                self.known_cameras[device].connected = False
                                logger.info(f"Camera disconnected: {device}")
                                asyncio.run_coroutine_threadsafe(
                                    self.callback(self.known_cameras[device].to_dict()),
                                    asyncio.get_event_loop()
                                )
                
                # Poll every 100ms for sub-200ms response time
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in camera monitoring loop: {e}")
                time.sleep(1.0)
    
    def _detect_cameras(self) -> Dict[str, CameraInfo]:
        """Detect currently connected cameras"""
        cameras = {}
        
        # Check for video devices
        for i in range(10):  # Check /dev/video0 through /dev/video9
            device = f"/dev/video{i}"
            if os.path.exists(device):
                try:
                    # Get camera capabilities
                    resolution, fps = self._get_camera_capabilities(device)
                    if resolution and fps:
                        cameras[device] = CameraInfo(device, True, resolution, fps)
                except Exception as e:
                    logger.debug(f"Failed to get capabilities for {device}: {e}")
        
        return cameras
    
    def _get_camera_capabilities(self, device: str) -> tuple[str, int]:
        """Get camera resolution and FPS using v4l2-ctl"""
        try:
            # Get supported formats
            cmd = ["v4l2-ctl", "--device", device, "--list-formats-ext"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
            if result.returncode != 0:
                return "", 0
            
            # Parse output to find default resolution and fps
            lines = result.stdout.split('\n')
            resolution = ""
            fps = 0
            
            for i, line in enumerate(lines):
                if 'YUYV' in line or 'MJPG' in line:
                    # Look for size information in following lines
                    for j in range(i + 1, min(i + 10, len(lines))):
                        size_line = lines[j].strip()
                        if 'Size:' in size_line and 'x' in size_line:
                            # Extract resolution (e.g., "Size: Discrete 640x480")
                            parts = size_line.split()
                            for part in parts:
                                if 'x' in part and part.replace('x', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '') == '':
                                    resolution = part
                                    break
                            
                            # Look for frame rate in next few lines
                            for k in range(j + 1, min(j + 5, len(lines))):
                                fps_line = lines[k].strip()
                                if 'fps' in fps_line:
                                    # Extract FPS (e.g., "Interval: Discrete 0.033s (30.000 fps)")
                                    import re
                                    fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', fps_line)
                                    if fps_match:
                                        fps = int(float(fps_match.group(1)))
                                        break
                            
                            if resolution and fps:
                                return resolution, fps
            
            # Fallback: try to get current format
            cmd = ["v4l2-ctl", "--device", device, "--get-fmt-video"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Width/Height' in line:
                        # Extract width/height (e.g., "Width/Height      : 640/480")
                        parts = line.split(':')
                        if len(parts) > 1:
                            dims = parts[1].strip().split('/')
                            if len(dims) == 2:
                                try:
                                    width = int(dims[0])
                                    height = int(dims[1])
                                    resolution = f"{width}x{height}"
                                except ValueError:
                                    pass
                
                # Default FPS if not found
                if resolution and fps == 0:
                    fps = 30
            
            return resolution or "640x480", fps or 30
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"v4l2-ctl failed for {device}: {e}")
            return "640x480", 30  # Default fallback

class WebSocketJSONRPCServer:
    """Enhanced WebSocket JSON-RPC server with camera monitoring"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8002):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.camera_monitor = CameraMonitor(self.broadcast_camera_status)
        self.server = None
        self._shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket JSON-RPC server on {self.host}:{self.port}/ws")
        
        # Install signal handlers
        if sys.platform != 'win32':
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self._signal_handler)
        
        # Start camera monitoring
        self.camera_monitor.start_monitoring()
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            subprotocols=["echo-protocol"]
        )
        
        logger.info(f"Server started successfully at ws://{self.host}:{self.port}/ws")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
    
    def _signal_handler(self):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()
    
    async def stop(self):
        """Stop the server gracefully"""
        logger.info("Stopping WebSocket JSON-RPC server")
        
        # Stop camera monitoring
        self.camera_monitor.stop_monitoring()
        
        # Close all client connections
        if self.clients:
            logger.info(f"Closing {len(self.clients)} client connections")
            await asyncio.gather(
                *[client.close() for client in self.clients.copy()],
                return_exceptions=True
            )
        
        # Stop WebSocket server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("Server stopped")
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        # Add client to set
        self.clients.add(websocket)
        logger.info(f"Client connected: {client_addr} (Total clients: {len(self.clients)})")
        
        try:
            async for message in websocket:
                try:
                    logger.info(f"Received from {client_addr}: {message}")
                    
                    # Handle JSON-RPC request
                    response = await self.handle_jsonrpc_request(message)
                    
                    if response:
                        response_str = json.dumps(response)
                        await websocket.send(response_str)
                        logger.info(f"Sending to {client_addr}: {response_str}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error from {client_addr}: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None
                    }
                    await websocket.send(json.dumps(error_response))
                
                except Exception as e:
                    logger.error(f"Error handling message from {client_addr}: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": "Internal error"},
                        "id": None
                    }
                    await websocket.send(json.dumps(error_response))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client connection closed: {client_addr}")
        except Exception as e:
            logger.error(f"Error in client handler for {client_addr}: {e}")
        finally:
            # Remove client from set
            self.clients.discard(websocket)
            logger.info(f"Client disconnected: {client_addr} (Total clients: {len(self.clients)})")
    
    async def handle_jsonrpc_request(self, message: str) -> Optional[Dict]:
        """Handle JSON-RPC 2.0 requests"""
        try:
            request = json.loads(message)
            
            # Validate JSON-RPC 2.0 format
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request"},
                    "id": request.get("id") if isinstance(request, dict) else None
                }
            
            method_name = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            # Handle methods
            if method_name == "ping":
                result = ping()
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method_name}"},
                    "id": request_id
                }
            
            # Return successful response
            if isinstance(result, Success):
                return {
                    "jsonrpc": "2.0",
                    "result": result.result,
                    "id": request_id
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": "Internal error"},
                    "id": request_id
                }
        
        except json.JSONDecodeError:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }
        except Exception as e:
            logger.error(f"Error processing JSON-RPC request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Internal error"},
                "id": None
            }
    
    async def broadcast_camera_status(self, status_data: Dict):
        """Broadcast camera status notification to all connected clients"""
        if not self.clients:
            logger.debug("No clients connected, skipping camera status broadcast")
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": "camera_status_update",
            "params": status_data
        }
        
        notification_str = json.dumps(notification)
        logger.info(f"Broadcasting camera status to {len(self.clients)} clients: {notification_str}")
        
        # Send to all connected clients
        disconnected_clients = []
        for client in self.clients.copy():
            try:
                await client.send(notification_str)
            except Exception as e:
                logger.warning(f"Failed to send camera status to client: {e}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)

# JSON-RPC Methods
@method
def ping() -> Success:
    """Health check method that returns 'pong'"""
    logger.info("Ping method called")
    return Success("pong")

async def main():
    """Main function to run the server"""
    try:
        # Use uvloop for better performance on Linux
        if sys.platform != 'win32':
            uvloop.install()
        
        # Create and start server
        server = WebSocketJSONRPCServer()
        await server.start()
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        # Ensure cleanup
        if 'server' in locals():
            await server.stop()

if __name__ == "__main__":
    asyncio.run(main())