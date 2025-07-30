"""
JSON-RPC Method Implementations

Contains all the RPC methods that can be called by clients.
Methods should be simple, focused, and well-documented.
"""

import time
import logging
import platform
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Core Methods
# ============================================================================

async def ping() -> str:
    """
    Health check method that returns 'pong'
    
    This is the most basic method for testing connectivity and server responsiveness.
    
    Returns:
        str: Always returns "pong"
    
    Example:
        Request:  {"jsonrpc": "2.0", "method": "ping", "id": 1}
        Response: {"jsonrpc": "2.0", "result": "pong", "id": 1}
    """
    logger.info("Ping method called")
    return "pong"

async def get_server_info() -> Dict[str, Any]:
    """
    Get comprehensive server information
    
    Returns detailed information about the server including version,
    uptime, system resources, and configuration.
    
    Returns:
        Dict containing server information
    
    Example:
        Request:  {"jsonrpc": "2.0", "method": "get_server_info", "id": 2}
        Response: {"jsonrpc": "2.0", "result": {...}, "id": 2}
    """
    logger.info("Server info requested")
    
    # Get system information
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
    except Exception as e:
        logger.warning(f"Could not get system info: {e}")
        cpu_percent = 0
        memory = None
        disk = None
    
    server_info = {
        "server": {
            "name": "WebSocket JSON-RPC Camera Server",
            "version": "1.0.0",
            "uptime_seconds": time.time() - getattr(get_server_info, '_start_time', time.time()),
            "started_at": getattr(get_server_info, '_started_at', datetime.now().isoformat()),
        },
        "system": {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
        },
        "resources": {
            "cpu_percent": cpu_percent,
            "memory_total_mb": round(memory.total / 1024 / 1024, 2) if memory else None,
            "memory_used_mb": round(memory.used / 1024 / 1024, 2) if memory else None,
            "memory_percent": memory.percent if memory else None,
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2) if disk else None,
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2) if disk else None,
            "disk_percent": round((disk.used / disk.total) * 100, 2) if disk else None,
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return server_info

# Initialize server start time
get_server_info._start_time = time.time()
get_server_info._started_at = datetime.now().isoformat()

# ============================================================================
# Camera Methods  
# ============================================================================

async def get_camera_list() -> Dict[str, Any]:
    """
    Get list of currently connected cameras
    
    Returns information about all detected cameras including their
    capabilities and current status.
    
    Returns:
        Dict containing camera list and metadata
    
    Example:
        Request:  {"jsonrpc": "2.0", "method": "get_camera_list", "id": 3}
        Response: {"jsonrpc": "2.0", "result": {"cameras": [...], "total": 2}, "id": 3}
    """
    logger.info("Camera list requested")
    
    # This will be populated by the camera monitor
    # For now, return a placeholder response
    from ..camera.monitor import get_current_cameras
    
    try:
        cameras = await get_current_cameras()
        
        camera_list = []
        for device, info in cameras.items():
            camera_list.append({
                "device": device,
                "status": "CONNECTED" if info.connected else "DISCONNECTED",
                "resolution": info.resolution if info.connected else None,
                "fps": info.fps if info.connected else None,
                "capabilities": info.capabilities if hasattr(info, 'capabilities') else None
            })
        
        return {
            "cameras": camera_list,
            "total": len(camera_list),
            "connected": len([c for c in camera_list if c["status"] == "CONNECTED"]),
            "timestamp": datetime.now().isoformat()
        }
        
    except ImportError:
        # Camera monitor not available yet, return empty list
        logger.warning("Camera monitor not available, returning empty camera list")
        return {
            "cameras": [],
            "total": 0,
            "connected": 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting camera list: {e}")
        raise RuntimeError(f"Failed to get camera list: {e}")

async def get_camera_status(device: str) -> Dict[str, Any]:
    """
    Get detailed status for a specific camera device
    
    Args:
        device: Camera device path (e.g., "/dev/video0")
    
    Returns:
        Dict containing detailed camera status
    
    Example:
        Request:  {"jsonrpc": "2.0", "method": "get_camera_status", "params": {"device": "/dev/video0"}, "id": 4}
        Response: {"jsonrpc": "2.0", "result": {...}, "id": 4}
    """
    logger.info(f"Camera status requested for device: {device}")
    
    if not device or not device.startswith('/dev/video'):
        raise ValueError(f"Invalid device path: {device}")
    
    # This will be implemented with the camera monitor
    try:
        from ..camera.monitor import get_camera_status_by_device
        status = await get_camera_status_by_device(device)
        return status
    except ImportError:
        # Camera monitor not available yet
        return {
            "device": device,
            "status": "UNKNOWN",
            "message": "Camera monitoring not available",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting camera status for {device}: {e}")
        raise RuntimeError(f"Failed to get camera status: {e}")

# ============================================================================
# Utility Methods
# ============================================================================

async def echo(message: str) -> str:
    """
    Echo back the provided message
    
    Useful for testing parameter passing and connectivity.
    
    Args:
        message: Message to echo back
    
    Returns:
        str: The same message that was sent
    
    Example:
        Request:  {"jsonrpc": "2.0", "method": "echo", "params": {"message": "hello"}, "id": 5}
        Response: {"jsonrpc": "2.0", "result": "hello", "id": 5}
    """
    logger.debug(f"Echo method called with message: {message}")
    return message

async def get_supported_methods() -> List[str]:
    """
    Get list of all supported RPC methods
    
    Returns:
        List of method names that can be called
    
    Example:
        Request:  {"jsonrpc": "2.0", "method": "get_supported_methods", "id": 6}
        Response: {"jsonrpc": "2.0", "result": ["ping", "echo", ...], "id": 6}
    """
    logger.info("Supported methods list requested")
    
    # This will be populated by the JSON-RPC handler
    methods = [
        "ping",
        "get_server_info", 
        "get_camera_list",
        "get_camera_status",
        "echo",
        "get_supported_methods"
    ]
    
    return methods

# ============================================================================
# Method Registration Helper
# ============================================================================

def register_all_methods(rpc_handler):
    """
    Register all methods with the JSON-RPC handler
    
    Args:
        rpc_handler: JSONRPCHandler instance to register methods with
    """
    methods_to_register = [
        ("ping", ping),
        ("get_server_info", get_server_info),
        ("get_camera_list", get_camera_list),
        ("get_camera_status", get_camera_status),
        ("echo", echo),
        ("get_supported_methods", get_supported_methods),
    ]
    
    for method_name, method_func in methods_to_register:
        rpc_handler.register_method(method_name, method_func)
        logger.debug(f"Registered method: {method_name}")
    
    logger.info(f"Registered {len(methods_to_register)} JSON-RPC methods")

# ============================================================================  
# Method Metadata (for documentation/introspection)
# ============================================================================

METHOD_METADATA = {
    "ping": {
        "description": "Health check method that returns 'pong'",
        "parameters": {},
        "returns": "string",
        "example_request": {"jsonrpc": "2.0", "method": "ping", "id": 1},
        "example_response": {"jsonrpc": "2.0", "result": "pong", "id": 1}
    },
    "get_server_info": {
        "description": "Get comprehensive server information",
        "parameters": {},
        "returns": "object",
        "example_request": {"jsonrpc": "2.0", "method": "get_server_info", "id": 2}
    },
    "get_camera_list": {
        "description": "Get list of currently connected cameras",
        "parameters": {},
        "returns": "object",
        "example_request": {"jsonrpc": "2.0", "method": "get_camera_list", "id": 3}
    },
    "get_camera_status": {
        "description": "Get detailed status for a specific camera device",
        "parameters": {
            "device": {"type": "string", "description": "Camera device path (e.g., '/dev/video0')", "required": True}
        },
        "returns": "object",
        "example_request": {"jsonrpc": "2.0", "method": "get_camera_status", "params": {"device": "/dev/video0"}, "id": 4}
    },
    "echo": {
        "description": "Echo back the provided message",
        "parameters": {
            "message": {"type": "string", "description": "Message to echo back", "required": True}
        },
        "returns": "string",
        "example_request": {"jsonrpc": "2.0", "method": "echo", "params": {"message": "hello"}, "id": 5}
    },
    "get_supported_methods": {
        "description": "Get list of all supported RPC methods",
        "parameters": {},
        "returns": "array",
        "example_request": {"jsonrpc": "2.0", "method": "get_supported_methods", "id": 6}
    }
}