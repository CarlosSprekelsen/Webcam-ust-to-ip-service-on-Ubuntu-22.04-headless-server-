"""
WebSocket JSON-RPC Server

Main WebSocket server that handles client connections, JSON-RPC requests,
and broadcasts camera status notifications to connected clients.
"""

import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Set, Dict, Any, Optional
from pathlib import Path

import websockets
import uvloop

from .jsonrpc_handler import JSONRPCHandler
from .methods import register_all_methods

logger = logging.getLogger(__name__)

class WebSocketJSONRPCServer:
    """
    Enhanced WebSocket JSON-RPC server with camera monitoring integration
    
    Features:
    - WebSocket server with JSON-RPC 2.0 support
    - Client connection management
    - Real-time camera status broadcasting
    - Graceful shutdown handling
    - Comprehensive logging
    - Performance optimizations with uvloop
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8002, websocket_path: str = "/ws"):
        self.host = host
        self.port = port
        self.websocket_path = websocket_path
        
        # Client management
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # JSON-RPC handler
        self.rpc_handler = JSONRPCHandler()
        register_all_methods(self.rpc_handler)
        
        # Server state
        self.server = None
        self.camera_monitor = None
        self._shutdown_event = asyncio.Event()
        self._start_time = time.time()
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "total_requests": 0,
            "total_notifications": 0,
            "start_time": datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket JSON-RPC server on {self.host}:{self.port}{self.websocket_path}")
        
        # Install signal handlers for graceful shutdown
        if sys.platform != 'win32':
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self._signal_handler)
        
        # Initialize camera monitoring (will be injected later)
        await self._initialize_camera_monitor()
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            subprotocols=["echo-protocol"],
            logger=logger,
            # Performance settings
            max_size=1024*1024,  # 1MB max message size
            max_queue=32,        # Max queued messages per client
            compression=None,    # Disable compression for speed
            ping_interval=20,    # Send ping every 20 seconds
            ping_timeout=10,     # Wait 10 seconds for pong
            close_timeout=10     # Wait 10 seconds for close
        )
        
        logger.info(f"Server started successfully at ws://{self.host}:{self.port}{self.websocket_path}")
        logger.info(f"Registered JSON-RPC methods: {self.rpc_handler.get_method_list()}")
        
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
        if self.camera_monitor:
            await self._stop_camera_monitor()
        
        # Close all client connections
        if self.clients:
            logger.info(f"Closing {len(self.clients)} client connections")
            close_tasks = []
            for client in self.clients.copy():
                try:
                    close_tasks.append(self._close_client_gracefully(client))
                except Exception as e:
                    logger.warning(f"Error initiating client close: {e}")
            
            # Wait for all clients to close
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Stop WebSocket server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Log final statistics
        uptime = time.time() - self._start_time
        logger.info(f"Server stopped after {uptime:.2f} seconds")
        logger.info(f"Final stats: {self.stats}")
    
    async def _close_client_gracefully(self, client: websockets.WebSocketServerProtocol):
        """Close a client connection gracefully"""
        try:
            await client.close(code=1001, reason="Server shutdown")
        except Exception as e:
            logger.debug(f"Error closing client: {e}")
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        # Validate path
        if path != self.websocket_path:
            logger.warning(f"Client {client_addr} connected to invalid path: {path}")
            await websocket.close(code=1008, reason="Invalid path")
            return
        
        # Add client to set
        self.clients.add(websocket)
        self.stats["total_connections"] += 1
        logger.info(f"Client connected: {client_addr} (Total clients: {len(self.clients)})")
        
        try:
            # Send welcome message with server info
            await self._send_welcome_message(websocket)
            
            # Handle messages
            async for message in websocket:
                await self._handle_client_message(websocket, client_addr, message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client connection closed normally: {client_addr}")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Client connection closed with error: {client_addr} - {e}")
        except Exception as e:
            logger.error(f"Error in client handler for {client_addr}: {e}", exc_info=True)
        finally:
            # Remove client from set
            self.clients.discard(websocket)
            logger.info(f"Client disconnected: {client_addr} (Total clients: {len(self.clients)})")
    
    async def _send_welcome_message(self, websocket):
        """Send welcome notification to newly connected client"""
        try:
            welcome_notification = self.rpc_handler.create_notification(
                "server_welcome",
                {
                    "server": "WebSocket JSON-RPC Camera Server",
                    "version": "1.0.0",
                    "timestamp": datetime.now().isoformat(),
                    "available_methods": self.rpc_handler.get_method_list()
                }
            )
            await websocket.send(welcome_notification)
            logger.debug(f"Sent welcome message to {websocket.remote_address}")
        except Exception as e:
            logger.warning(f"Failed to send welcome message: {e}")
    
    async def _handle_client_message(self, websocket, client_addr, message):
        """Handle individual client messages"""
        try:
            logger.debug(f"Received from {client_addr}: {message}")
            
            # Update statistics
            self.stats["total_requests"] += 1
            
            # Process JSON-RPC request
            start_time = time.time()
            response = await self.rpc_handler.handle_request(message)
            response_time = (time.time() - start_time) * 1000
            
            # Send response if not a notification
            if response:
                await websocket.send(response)
                logger.debug(f"Sent to {client_addr} ({response_time:.2f}ms): {response}")
            else:
                logger.debug(f"Processed notification from {client_addr} ({response_time:.2f}ms)")
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from {client_addr}: {e}")
            error_response = self.rpc_handler._create_error_response(
                None, -32700, "Parse error"
            )
            await websocket.send(error_response)
        
        except Exception as e:
            logger.error(f"Error handling message from {client_addr}: {e}", exc_info=True)
            error_response = self.rpc_handler._create_error_response(
                None, -32603, "Internal error"
            )
            await websocket.send(error_response)
    
    async def broadcast_camera_status(self, status_data: Dict[str, Any]):
        """
        Broadcast camera status notification to all connected clients
        
        Args:
            status_data: Camera status information to broadcast
        """
        if not self.clients:
            logger.debug("No clients connected, skipping camera status broadcast")
            return
        
        # Create notification
        notification = self.rpc_handler.create_notification(
            "camera_status_update",
            status_data
        )
        
        logger.info(f"Broadcasting camera status to {len(self.clients)} clients")
        logger.debug(f"Camera status data: {status_data}")
        
        # Send to all connected clients
        disconnected_clients = []
        successful_sends = 0
        
        for client in self.clients.copy():
            try:
                await client.send(notification)
                successful_sends += 1
            except websockets.exceptions.ConnectionClosed:
                logger.debug(f"Client disconnected during broadcast")
                disconnected_clients.append(client)
            except Exception as e:
                logger.warning(f"Failed to send camera status to client: {e}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)
        
        # Update statistics
        self.stats["total_notifications"] += successful_sends
        
        logger.debug(f"Camera status broadcast completed: {successful_sends} successful, {len(disconnected_clients)} failed")
    
    async def broadcast_notification(self, method: str, params: Any = None):
        """
        Broadcast a custom notification to all connected clients
        
        Args:
            method: Notification method name
            params: Notification parameters
        """
        if not self.clients:
            logger.debug(f"No clients connected, skipping broadcast of {method}")
            return
        
        notification = self.rpc_handler.create_notification(method, params)
        
        logger.info(f"Broadcasting {method} notification to {len(self.clients)} clients")
        
        # Send to all connected clients
        disconnected_clients = []
        successful_sends = 0
        
        for client in self.clients.copy():
            try:
                await client.send(notification)
                successful_sends += 1
            except Exception as e:
                logger.warning(f"Failed to send {method} notification to client: {e}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)
        
        self.stats["total_notifications"] += successful_sends
        logger.debug(f"Broadcast {method} completed: {successful_sends} successful")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        uptime = time.time() - self._start_time
        return {
            **self.stats,
            "current_connections": len(self.clients),
            "uptime_seconds": round(uptime, 2),
            "requests_per_second": round(self.stats["total_requests"] / max(uptime, 1), 2)
        }
    
    def set_camera_monitor(self, camera_monitor):
        """Set the camera monitor instance (dependency injection)"""
        self.camera_monitor = camera_monitor
        logger.info("Camera monitor attached to WebSocket server")
    
    async def _initialize_camera_monitor(self):
        """Initialize camera monitoring if available"""
        try:
            # This will be implemented when camera module is ready
            # For now, just log that we're ready for camera monitoring
            logger.info("WebSocket server ready for camera monitoring integration")
        except Exception as e:
            logger.error(f"Failed to initialize camera monitor: {e}")
    
    async def _stop_camera_monitor(self):
        """Stop camera monitoring gracefully"""
        try:
            if hasattr(self.camera_monitor, 'stop_monitoring'):
                self.camera_monitor.stop_monitoring()
                logger.info("Camera monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping camera monitor: {e}")

# ============================================================================
# Server Factory Function
# ============================================================================

def create_server(host: str = "0.0.0.0", port: int = 8002, 
                 websocket_path: str = "/ws", use_uvloop: bool = True) -> WebSocketJSONRPCServer:
    """
    Create and configure a WebSocket JSON-RPC server
    
    Args:
        host: Host to bind to
        port: Port to bind to  
        websocket_path: WebSocket endpoint path
        use_uvloop: Whether to use uvloop for performance (Linux only)
    
    Returns:
        Configured WebSocketJSONRPCServer instance
    """
    # Install uvloop for better performance on Linux
    if use_uvloop and sys.platform != 'win32':
        try:
            uvloop.install()
            logger.info("uvloop installed for improved performance")
        except ImportError:
            logger.warning("uvloop not available, using default event loop")
    
    server = WebSocketJSONRPCServer(host, port, websocket_path)
    logger.info(f"Created WebSocket server: {host}:{port}{websocket_path}")
    
    return server

# ============================================================================
# Main Server Entry Point  
# ============================================================================

async def main():
    """Main function to run the server standalone"""
    try:
        # Create and start server
        server = create_server()
        await server.start()
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        # Ensure cleanup
        if 'server' in locals():
            await server.stop()

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())