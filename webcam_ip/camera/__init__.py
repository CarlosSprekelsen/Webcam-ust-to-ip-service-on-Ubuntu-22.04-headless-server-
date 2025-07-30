"""
Camera Module

Provides camera monitoring, detection, and management functionality.
This module handles USB camera connect/disconnect events and capability detection.
"""

from .models import (
    CameraInfo,
    CameraCapabilities, 
    CameraStatus,
    CameraEvent,
    CameraRegistry,
    camera_registry
)

from .detector import (
    CameraCapabilityDetector,
    DetectionConfig,
    detect_camera_capabilities,
    get_supported_cameras,
    detect_all_cameras,
    default_detector
)

from .monitor import (
    CameraMonitor,
    EventDrivenCameraMonitor,
    MonitorConfig,
    create_camera_monitor,
    get_current_cameras,
    get_camera_status_by_device
)

__version__ = "1.0.0"
__all__ = [
    # Models
    "CameraInfo",
    "CameraCapabilities", 
    "CameraStatus",
    "CameraEvent",
    "CameraRegistry",
    "camera_registry",
    
    # Detection
    "CameraCapabilityDetector",
    "DetectionConfig", 
    "detect_camera_capabilities",
    "get_supported_cameras",
    "detect_all_cameras",
    "default_detector",
    
    # Monitoring
    "CameraMonitor",
    "EventDrivenCameraMonitor",
    "MonitorConfig",
    "create_camera_monitor",
    "get_current_cameras",
    "get_camera_status_by_device"
]