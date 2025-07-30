"""
WebSocket JSON-RPC Server with Camera Monitoring
"""

__version__ = "1.0.0"
__author__ = "Camera Service Team"

# Make key components available at package level
from .server import WebSocketJSONRPCServer, CameraMonitor
from .test_client import CameraTestClient

__all__ = ["WebSocketJSONRPCServer", "CameraMonitor", "CameraTestClient"]