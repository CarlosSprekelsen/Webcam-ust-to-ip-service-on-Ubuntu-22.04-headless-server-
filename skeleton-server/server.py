#!/usr/bin/env python3
"""
Skeleton WebSocket + JSON-RPC 2.0 Server
Main server implementation for camera service APIs
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import uvloop
import websockets
from jsonrpcserver import method, Result, Success, Error, InvalidRequest
from websockets.server import WebSocketServerProtocol


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/opt/webcam-env/logs/server.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)

# Server configuration
HOST = "0.0.0.0"
PORT = 8002
PATH = "/ws"

# Connected clients tracking
connected_clients = set()


@method
def ping() -> Success:
    """
    Simple ping method that returns 'pong'
    This serves as a health check and connectivity test
    """
    logger.info("Ping method called")
    return Success("pong")


class WebSocketJSONRPCServer:
    """WebSocket server with JSON-RPC 2.0 support"""
    
    def __init__(self, host: str = HOST, port: int = PORT, path: str = PATH):
        self.host = host
        self.port = port
        self.path = path
        self.server = None
        self.running = False
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle individual WebSocket client connections"""
        client_address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        # Add client to connected set
        connected_clients.add(websocket)
        logger.info(f"Client connected: {client_address} (Total clients: {len(connected_clients)})")
        
        try:
            async for message in websocket:
                await self.process_message(websocket, message, client_address)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_address} disconnected gracefully")
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            # Remove client from connected set
            connected_clients.discard(websocket)
            logger.info(f"Client disconnected: {client_address} (Total clients: {len(connected_clients)})")
    
    async def process_message(self, websocket: WebSocketServerProtocol, message: str, client_address: str):
        """Process incoming JSON-RPC messages"""
        try:
            # Log incoming message
            logger.info(f"Received from {client_address}: {message}")
            
            # Parse JSON-RPC request
            try:
                request_data = json.loads(message)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {client_address}: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None
                }
                await self.send_response(websocket, error_response, client_address)
                return
            
            # Handle JSON-RPC request
            response = await self.handle_jsonrpc_request(request_data)
            
            if response:
                await self.send_response(websocket, response, client_address)
                
        except Exception as e:
            logger.error(f"Error processing message from {client_address}: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Internal error"},
                "id": None
            }
            await self.send_response(websocket, error_response, client_address)
    
    async def handle_jsonrpc_request(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle JSON-RPC 2.0 request and return response"""
        try:
            # Validate JSON-RPC 2.0 format
            if not isinstance(request_data, dict):
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request"},
                    "id": None
                }
            
            jsonrpc_version = request_data.get("jsonrpc")
            method_name = request_data.get("method")
            request_id = request_data.get("id")
            params = request_data.get("params", [])
            
            # Validate required fields
            if jsonrpc_version != "2.0":
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request - jsonrpc must be '2.0'"},
                    "id": request_id
                }
            
            if not method_name or not isinstance(method_name, str):
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request - missing or invalid method"},
                    "id": request_id
                }
            
            # Handle the method
            if method_name == "ping":
                result = ping()
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
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method_name}"},
                    "id": request_id
                }
                
        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Internal error"},
                "id": request_data.get("id") if isinstance(request_data, dict) else None
            }
    
    async def send_response(self, websocket: WebSocketServerProtocol, response: Dict[str, Any], client_address: str):
        """Send JSON-RPC response to client"""
        try:
            response_json = json.dumps(response)
            logger.info(f"Sending to {client_address}: {response_json}")
            await websocket.send(response_json)
        except Exception as e:
            logger.error(f"Error sending response to {client_address}: {e}")
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket JSON-RPC server on {self.host}:{self.port}{self.path}")
        
        # Create logs directory if it doesn't exist
        import os
        os.makedirs('/opt/webcam-env/logs', exist_ok=True)
        
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                path=self.path,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            self.running = True
            logger.info(f"Server started successfully at ws://{self.host}:{self.port}{self.path}")
            
            # Keep the server running
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server and self.running:
            logger.info("Stopping server...")
            self.server.close()
            await self.server.wait_closed()
            self.running = False
            logger.info("Server stopped")


async def main():
    """Main function to run the server"""
    # Use uvloop for better performance
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    server = WebSocketJSONRPCServer()
    
    # Handle graceful shutdown
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(server.stop_server())
    
    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())