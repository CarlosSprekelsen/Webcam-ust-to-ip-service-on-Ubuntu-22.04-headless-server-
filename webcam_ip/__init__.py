"""
WebSocket JSON-RPC Server with Camera Monitoring
"""

__version__ = "1.0.0"
__author__ = "Camera Service Team"

# Make key components available at package level
from .server import WebSocketJSONRPCServer
from .camera import CameraMonitor, CameraInfo, CameraStatus
from .utils import setup_logging, GracefulShutdown

__all__ = [
    "WebSocketJSONRPCServer", 
    "CameraMonitor", 
    "CameraInfo", 
    "CameraStatus",
    "setup_logging",
    "GracefulShutdown"
]