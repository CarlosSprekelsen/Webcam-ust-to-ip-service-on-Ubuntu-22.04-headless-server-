"""
WebSocket JSON-RPC Server Module

This module provides a WebSocket server with JSON-RPC 2.0 support
and real-time USB camera monitoring capabilities.
"""

from .websocket_server import WebSocketJSONRPCServer
from .jsonrpc_handler import JSONRPCHandler, JSONRPCError
from .methods import ping, get_server_info

__version__ = "1.0.0"
__all__ = [
    "WebSocketJSONRPCServer",
    "JSONRPCHandler", 
    "JSONRPCError",
    "ping",
    "get_server_info"
]
