"""
WebSocket JSON-RPC Server with Camera Monitoring

A modular, production-ready WebSocket server that provides JSON-RPC 2.0 API
with real-time USB camera monitoring capabilities.

Features:
- WebSocket server with JSON-RPC 2.0 support
- Real-time USB camera connect/disconnect detection
- Structured logging with JSON output support
- Graceful shutdown with proper cleanup
- Event-driven camera monitoring (Linux with pyudev)
- Comprehensive error handling and recovery
"""

__version__ = "1.0.0"
__author__ = "Camera Service Team"

# Make key components available at package level
try:
    from .server import WebSocketJSONRPCServer, create_server
    from .camera import CameraMonitor, CameraInfo, CameraStatus, create_camera_monitor
    from .utils import setup_logging, GracefulShutdown, LogConfig
except ImportError as e:
    # Handle import errors gracefully during development
    import warnings
    warnings.warn(f"Some modules could not be imported: {e}", ImportWarning)
    
    # Define minimal interface for debugging
    WebSocketJSONRPCServer = None
    create_server = None
    CameraMonitor = None
    CameraInfo = None
    CameraStatus = None
    create_camera_monitor = None
    setup_logging = None
    GracefulShutdown = None
    LogConfig = None

__all__ = [
    # Server components
    "WebSocketJSONRPCServer",
    "create_server",
    
    # Camera components
    "CameraMonitor", 
    "CameraInfo", 
    "CameraStatus",
    "create_camera_monitor",
    
    # Utility components
    "setup_logging",
    "GracefulShutdown",
    "LogConfig",
    
    # Package metadata
    "__version__",
    "__author__"
]

# Package-level configuration
def get_package_info():
    """Get package information for debugging"""
    return {
        "name": "webcam_ip",
        "version": __version__,
        "author": __author__,
        "components": {
            "server": WebSocketJSONRPCServer is not None,
            "camera": CameraMonitor is not None,
            "utils": setup_logging is not None
        }
    }

# Optional: Add package-level logging
def configure_package_logging(level="INFO"):
    """Configure logging for the entire package"""
    if setup_logging is not None:
        from .utils.logging import LogConfig
        config = LogConfig(level=level, console_enabled=True, file_enabled=False)
        return setup_logging(config)
    else:
        import logging
        logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
        return {"webcam_ip": logging.getLogger("webcam_ip")}

# Development helper
def run_validation():
    """Run package validation tests (development helper)"""
    try:
        print("🔍 Running package validation...")
        
        # Test imports
        success = True
        components = [
            ("server", WebSocketJSONRPCServer),
            ("camera", CameraMonitor),
            ("utils", setup_logging)
        ]
        
        for name, component in components:
            if component is not None:
                print(f"✅ {name} module OK")
            else:
                print(f"❌ {name} module failed to import")
                success = False
        
        if success:
            print("🎉 Package validation passed!")
        else:
            print("⚠️  Some components failed to import")
        
        return success
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False