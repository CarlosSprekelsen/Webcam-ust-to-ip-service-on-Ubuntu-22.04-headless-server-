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
import subprocess
import uuid
from pathlib import Path
import asyncio
import json

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

async def capture_snapshot(device: str, format: str = "jpeg") -> Dict[str, Any]:
    """
    Capture a snapshot from the specified camera device.

    Args:
        device: Camera device path (e.g., "/dev/video0")
        format: Image format (default: "jpeg")

    Returns:
        Dict containing snapshot metadata

    Example:
        Request:  {"jsonrpc": "2.0", "method": "capture_snapshot", "params": {"device": "/dev/video0"}, "id": 7}
        Response: {"jsonrpc": "2.0", "result": {...}, "id": 7}
    """
    logger.info(f"Snapshot capture requested for device: {device} in format: {format}")

    if not device or not device.startswith('/dev/video'):
        raise ValueError(f"Invalid device path: {device}")

    snapshot_id = str(uuid.uuid4())
    filename = f"{snapshot_id}.{format}"
    media_dir = Path("/opt/webcam-env/media")
    media_dir.mkdir(parents=True, exist_ok=True)
    filepath = media_dir / filename

    cmd = [
        "ffmpeg", "-f", "v4l2", "-i", device,
        "-frames:v", "1", "-y", str(filepath)
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(f"ffmpeg error: {stderr.decode().strip()}")
            raise RuntimeError(f"Snapshot capture failed: {stderr.decode().strip()}")
    except Exception as e:
        logger.error(f"Error capturing snapshot: {e}")
        raise RuntimeError(f"Failed to capture snapshot: {e}")

    return {
        "snapshot_id": snapshot_id,
        "filename": filename,
        "device": device,
        "timestamp": datetime.now().isoformat()
    }

GST_RECORDING_PROCESS = {"proc": None, "filename": None, "start_time": None}

async def start_recording(device: str, filename: str, resolution: str = "640x480", duration: Optional[int] = None) -> dict:
    """
    Start recording video from the device using GStreamer and save as MP4.

    Args:
        device: Camera device path (e.g., "/dev/video0")
        filename: Output filename (e.g., "/opt/webcam-env/media/recording.mp4")
        resolution: Video resolution (default: "640x480")
        duration: Optional duration in seconds

    Returns:
        Dict containing recording metadata
    """
    logger.info(f"Start recording requested for device: {device} to file: {filename} at resolution: {resolution}, duration: {duration}")

    if not device or not filename:
        return {"error": "device and filename are required"}
    if GST_RECORDING_PROCESS["proc"]:
        return {"error": "A recording is already in progress"}
    try:
        width, height = map(int, resolution.split("x"))
    except Exception:
        return {"error": "Invalid resolution format. Use 'WIDTHxHEIGHT'."}

    cmd = [
        "gst-launch-1.0",
        "v4l2src", f"device={device}",
        "!", f"video/x-raw,width={width},height={height}",
        "!", "x264enc",
        "!", "mp4mux",
        "!", "filesink", f"location={filename}"
    ]
    if duration:
        # Use 'timeout' to limit duration if available (Linux)
        cmd = ["timeout", str(duration)] + cmd

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        GST_RECORDING_PROCESS["proc"] = proc
        GST_RECORDING_PROCESS["filename"] = filename
        GST_RECORDING_PROCESS["start_time"] = datetime.now().isoformat()
        return {
            "filename": filename,
            "device": device,
            "resolution": resolution,
            "started_at": GST_RECORDING_PROCESS["start_time"],
            "duration": duration
        }
    except Exception as e:
        logger.error(f"start_recording error: {e}")
        return {"error": str(e)}

async def stop_recording() -> dict:
    """
    Stop any running GStreamer process started by start_recording.
    """
    proc = GST_RECORDING_PROCESS.get("proc")
    filename = GST_RECORDING_PROCESS.get("filename")
    start_time = GST_RECORDING_PROCESS.get("start_time")
    if not proc:
        return {"error": "No recording in progress"}
    try:
        proc.terminate()
        await proc.wait()
        GST_RECORDING_PROCESS["proc"] = None
        stop_time = datetime.now().isoformat()
        # Optionally write metadata
        meta = {
            "filename": filename,
            "started_at": start_time,
            "stopped_at": stop_time
        }
        if filename:
            meta_path = filename + ".json"
            with open(meta_path, "w") as f:
                json.dump(meta, f)
        return {"status": "stopped", **meta}
    except Exception as e:
        logger.error(f"stop_recording error: {e}")
        return {"error": str(e)}

async def schedule_recording(device: str, start_time: str, duration: int, format: str = "mp4") -> Dict[str, Any]:
    """
    Schedule a recording at a future time.

    Args:
        device: Camera device path (e.g., "/dev/video0")
        start_time: ISO8601 string for when to start recording
        duration: Duration in seconds
        format: Video format (default: "mp4")

    Returns:
        Dict containing schedule metadata
    """
    logger.info(f"Schedule recording requested for device: {device} at {start_time} for {duration}s in format: {format}")

    try:
        start_dt = datetime.fromisoformat(start_time)
    except Exception as e:
        raise ValueError(f"Invalid start_time format: {e}")

    now = datetime.now()
    delay = (start_dt - now).total_seconds()
    if delay < 0:
        raise ValueError("start_time must be in the future")

    async def delayed_record():
        await asyncio.sleep(delay)
        await start_recording(device, format=format, duration=duration)

    asyncio.create_task(delayed_record())

    return {
        "device": device,
        "scheduled_for": start_time,
        "duration": duration,
        "format": format,
        "status": "scheduled"
    }

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
        "capture_snapshot",
        "start_recording",
        "stop_recording",
        "schedule_recording",
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
        ("capture_snapshot", capture_snapshot),
        ("start_recording", start_recording),
        ("stop_recording", stop_recording),
        ("schedule_recording", schedule_recording),
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
    "capture_snapshot": {
        "description": "Capture a snapshot from the specified camera device",
        "parameters": {
            "device": {"type": "string", "description": "Camera device path (e.g., '/dev/video0')", "required": True},
            "format": {"type": "string", "description": "Image format (e.g., 'jpeg')", "required": False}
        },
        "returns": "object",
        "example_request": {"jsonrpc": "2.0", "method": "capture_snapshot", "params": {"device": "/dev/video0"}, "id": 7}
    },
    "start_recording": {
        "description": "Start recording video from the specified camera device",
        "parameters": {
            "device": {"type": "string", "description": "Camera device path (e.g., '/dev/video0')", "required": True},
            "format": {"type": "string", "description": "Video format (e.g., 'mp4')", "required": False},
            "duration": {"type": "integer", "description": "Duration in seconds", "required": False}
        },
        "returns": "object",
        "example_request": {"jsonrpc": "2.0", "method": "start_recording", "params": {"device": "/dev/video0"}, "id": 8}
    },
    "stop_recording": {
        "description": "Stop a running recording by its ID",
        "parameters": {
            "recording_id": {"type": "string", "description": "The ID of the recording to stop", "required": True}
        },
        "returns": "object",
        "example_request": {"jsonrpc": "2.0", "method": "stop_recording", "params": {"recording_id": "uuid"}, "id": 9}
    },
    "schedule_recording": {
        "description": "Schedule a recording at a future time",
        "parameters": {
            "device": {"type": "string", "description": "Camera device path (e.g., '/dev/video0')", "required": True},
            "start_time": {"type": "string", "description": "ISO8601 string for when to start recording", "required": True},
            "duration": {"type": "integer", "description": "Duration in seconds", "required": True},
            "format": {"type": "string", "description": "Video format (e.g., 'mp4')", "required": False}
        },
        "returns": "object",
        "example_request": {
            "jsonrpc": "2.0",
            "method": "schedule_recording",
            "params": {
                "device": "/dev/video0",
                "start_time": "2025-07-30T15:00:00",
                "duration": 60
            },
            "id": 10
        }
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