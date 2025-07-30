"""
Camera Data Models

Defines data structures for camera information, capabilities, and status.
These models provide a clean interface between camera detection,
monitoring, and the JSON-RPC API.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class CameraStatus(Enum):
    """Camera connection status"""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

@dataclass
class CameraCapabilities:
    """
    Camera capability information detected from v4l2-ctl
    
    Attributes:
        resolution: Camera resolution (e.g., "640x480")
        fps: Frames per second
        formats: Supported pixel formats (e.g., ["YUYV", "MJPG"])
        controls: Available camera controls
    """
    resolution: str = "640x480"
    fps: int = 30
    formats: List[str] = field(default_factory=list)
    controls: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate capabilities after initialization"""
        if not self.resolution or 'x' not in self.resolution:
            self.resolution = "640x480"
        
        if self.fps <= 0:
            self.fps = 30
        
        if not self.formats:
            self.formats = ["YUYV"]
    
    @property
    def width(self) -> int:
        """Get width from resolution string"""
        try:
            return int(self.resolution.split('x')[0])
        except (ValueError, IndexError):
            return 640
    
    @property
    def height(self) -> int:
        """Get height from resolution string"""
        try:
            return int(self.resolution.split('x')[1])
        except (ValueError, IndexError):
            return 480
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "resolution": self.resolution,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "formats": self.formats,
            "controls": self.controls
        }

@dataclass
class CameraInfo:
    """
    Complete camera information container
    
    Attributes:
        device: Device path (e.g., "/dev/video0")
        status: Connection status
        capabilities: Camera capabilities (when connected)
        connected_at: Timestamp when camera was connected
        disconnected_at: Timestamp when camera was disconnected
        last_seen: Last time camera was detected
        error_message: Error message if status is ERROR
        metadata: Additional metadata
    """
    device: str
    status: CameraStatus = CameraStatus.UNKNOWN
    capabilities: Optional[CameraCapabilities] = None
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize timestamps and validate device path"""
        if not self.device.startswith('/dev/video'):
            raise ValueError(f"Invalid device path: {self.device}")
        
        if self.last_seen is None:
            self.last_seen = datetime.now()
    
    @property
    def connected(self) -> bool:
        """Check if camera is currently connected"""
        return self.status == CameraStatus.CONNECTED
    
    @property
    def device_number(self) -> int:
        """Extract device number from device path"""
        try:
            return int(self.device.replace('/dev/video', ''))
        except ValueError:
            return 0
    
    @property
    def uptime_seconds(self) -> Optional[float]:
        """Get uptime in seconds if connected"""
        if self.connected and self.connected_at:
            return (datetime.now() - self.connected_at).total_seconds()
        return None
    
    @property
    def resolution(self) -> str:
        """Get resolution string (convenience property)"""
        if self.capabilities:
            return self.capabilities.resolution
        return "Unknown"
    
    @property
    def fps(self) -> int:
        """Get FPS (convenience property)"""
        if self.capabilities:
            return self.capabilities.fps
        return 0
    
    def mark_connected(self, capabilities: Optional[CameraCapabilities] = None):
        """Mark camera as connected with optional capabilities"""
        self.status = CameraStatus.CONNECTED
        self.connected_at = datetime.now()
        self.last_seen = datetime.now()
        self.disconnected_at = None
        self.error_message = None
        
        if capabilities:
            self.capabilities = capabilities
    
    def mark_disconnected(self):
        """Mark camera as disconnected"""
        self.status = CameraStatus.DISCONNECTED
        self.disconnected_at = datetime.now()
        self.last_seen = datetime.now()
        # Keep capabilities for reference
    
    def mark_error(self, error_message: str):
        """Mark camera as having an error"""
        self.status = CameraStatus.ERROR
        self.error_message = error_message
        self.last_seen = datetime.now()
    
    def update_last_seen(self):
        """Update the last seen timestamp"""
        self.last_seen = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON-RPC notifications and responses
        
        This is the format sent to WebSocket clients
        """
        data = {
            "device": self.device,
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
        
        # Add connection-specific data
        if self.status == CameraStatus.CONNECTED:
            if self.capabilities:
                data.update({
                    "resolution": self.capabilities.resolution,
                    "fps": self.capabilities.fps,
                    "formats": self.capabilities.formats,
                })
            
            if self.connected_at:
                data["connected_at"] = self.connected_at.isoformat()
                data["uptime_seconds"] = self.uptime_seconds
        
        elif self.status == CameraStatus.DISCONNECTED:
            if self.disconnected_at:
                data["disconnected_at"] = self.disconnected_at.isoformat()
        
        elif self.status == CameraStatus.ERROR:
            if self.error_message:
                data["error_message"] = self.error_message
        
        # Add metadata if present
        if self.metadata:
            data["metadata"] = self.metadata
        
        return data
    
    def to_detailed_dict(self) -> Dict[str, Any]:
        """
        Convert to detailed dictionary with all information
        
        Used for administrative APIs and debugging
        """
        data = self.to_dict()
        
        # Add detailed capabilities
        if self.capabilities:
            data["capabilities"] = self.capabilities.to_dict()
        
        # Add all timestamps
        data.update({
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
            "device_number": self.device_number,
        })
        
        return data

@dataclass
class CameraEvent:
    """
    Camera event for monitoring and logging
    
    Represents a camera state change event
    """
    device: str
    event_type: str  # "connected", "disconnected", "error", "capability_change"
    timestamp: datetime = field(default_factory=datetime.now)
    old_status: Optional[CameraStatus] = None
    new_status: Optional[CameraStatus] = None
    capabilities: Optional[CameraCapabilities] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and notifications"""
        data = {
            "device": self.device,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
        }
        
        if self.old_status:
            data["old_status"] = self.old_status.value
        
        if self.new_status:
            data["new_status"] = self.new_status.value
        
        if self.capabilities:
            data["capabilities"] = self.capabilities.to_dict()
        
        if self.error_message:
            data["error_message"] = self.error_message
        
        if self.metadata:
            data["metadata"] = self.metadata
        
        return data

class CameraRegistry:
    """
    Registry for managing multiple camera instances
    
    Provides a centralized way to track and manage cameras
    """
    
    def __init__(self):
        self._cameras: Dict[str, CameraInfo] = {}
        self._events: List[CameraEvent] = []
        self._max_events = 1000  # Keep last 1000 events
    
    def get_camera(self, device: str) -> Optional[CameraInfo]:
        """Get camera by device path"""
        return self._cameras.get(device)
    
    def add_camera(self, camera_info: CameraInfo):
        """Add or update camera information"""
        old_camera = self._cameras.get(camera_info.device)
        self._cameras[camera_info.device] = camera_info
        
        # Record event if status changed
        if old_camera and old_camera.status != camera_info.status:
            event = CameraEvent(
                device=camera_info.device,
                event_type="status_change",
                old_status=old_camera.status,
                new_status=camera_info.status,
                capabilities=camera_info.capabilities
            )
            self._add_event(event)
    
    def remove_camera(self, device: str) -> bool:
        """Remove camera from registry"""
        if device in self._cameras:
            camera = self._cameras[device]
            camera.mark_disconnected()
            
            event = CameraEvent(
                device=device,
                event_type="removed",
                old_status=CameraStatus.CONNECTED,
                new_status=CameraStatus.DISCONNECTED
            )
            self._add_event(event)
            
            del self._cameras[device]
            return True
        return False
    
    def get_all_cameras(self) -> Dict[str, CameraInfo]:
        """Get all cameras"""
        return self._cameras.copy()
    
    def get_connected_cameras(self) -> Dict[str, CameraInfo]:
        """Get only connected cameras"""
        return {
            device: camera for device, camera in self._cameras.items()
            if camera.status == CameraStatus.CONNECTED
        }
    
    def get_camera_count(self) -> Dict[str, int]:
        """Get camera count by status"""
        counts = {status.value: 0 for status in CameraStatus}
        
        for camera in self._cameras.values():
            counts[camera.status.value] += 1
        
        return counts
    
    def _add_event(self, event: CameraEvent):
        """Add event to history"""
        self._events.append(event)
        
        # Trim events if too many
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
    
    def get_recent_events(self, limit: int = 100) -> List[CameraEvent]:
        """Get recent events"""
        return self._events[-limit:]
    
    def clear_events(self):
        """Clear event history"""
        self._events.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary"""
        return {
            "cameras": {device: camera.to_dict() 
                       for device, camera in self._cameras.items()},
            "counts": self.get_camera_count(),
            "total": len(self._cameras),
            "recent_events": [event.to_dict() for event in self.get_recent_events(10)]
        }

# Global camera registry instance
camera_registry = CameraRegistry()