"""
Camera Monitoring Logic

Provides real-time monitoring of USB camera connect/disconnect events.
Fixes the threading + asyncio integration issues and provides both
polling and event-driven monitoring options.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Callable, Optional, List, Set, Any
from dataclasses import dataclass

from .models import CameraInfo, CameraStatus, CameraCapabilities, CameraEvent, camera_registry
from .detector import CameraCapabilityDetector, DetectionConfig

logger = logging.getLogger(__name__)

@dataclass
class MonitorConfig:
    """Configuration for camera monitoring"""
    poll_interval: float = 0.1  # 100ms for sub-200ms response
    device_range: range = None
    detection_timeout: float = 2.0
    max_detection_retries: int = 2
    enable_capability_detection: bool = True
    capability_cache_timeout: float = 30.0
    
    def __post_init__(self):
        if self.device_range is None:
            self.device_range = range(10)  # /dev/video0 to /dev/video9

class CameraMonitor:
    """
    Camera monitoring with proper async/thread integration
    
    Features:
    - Fixed threading + asyncio integration
    - Real-time camera connect/disconnect detection
    - Automatic capability detection
    - Event-driven callbacks
    - Comprehensive error handling
    - Performance optimizations
    """
    
    def __init__(self, 
                 callback: Callable[[Dict[str, Any]], None],
                 loop: asyncio.AbstractEventLoop,
                 config: Optional[MonitorConfig] = None):
        """
        Initialize camera monitor
        
        Args:
            callback: Async callback function for camera events
            loop: Event loop for scheduling callbacks (FIXES the threading issue!)
            config: Monitor configuration
        """
        self.callback = callback
        self.loop = loop  # Store the main event loop - THIS FIXES THE BUG!
        self.config = config or MonitorConfig()
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Camera state tracking
        self.known_cameras: Dict[str, CameraInfo] = {}
        self.lock = threading.Lock()
        
        # Detection components
        detection_config = DetectionConfig(
            v4l2_timeout=self.config.detection_timeout,
            max_retries=self.config.max_detection_retries
        )
        self.detector = CameraCapabilityDetector(detection_config)
        
        # Statistics
        self.stats = {
            "monitoring_started": None,
            "total_events": 0,
            "connect_events": 0,
            "disconnect_events": 0,
            "error_events": 0,
            "detection_failures": 0,
        }
        
        logger.info(f"Camera monitor initialized with config: {self.config}")
    
    def start_monitoring(self):
        """Start camera monitoring in a separate thread"""
        if self.monitoring:
            logger.warning("Camera monitoring already started")
            return
        
        self.monitoring = True
        self.stats["monitoring_started"] = datetime.now()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="CameraMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("Camera monitoring started")
        
        # Send initial camera status using proper async scheduling
        self.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._send_initial_status())
        )
    
    def stop_monitoring(self):
        """Stop camera monitoring gracefully"""
        if not self.monitoring:
            return
        
        logger.info("Stopping camera monitoring...")
        self.monitoring = False
        
        # Wait for monitor thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
            if self.monitor_thread.is_alive():
                logger.warning("Monitor thread did not stop gracefully")
        
        # Log final statistics
        duration = datetime.now() - self.stats["monitoring_started"]
        logger.info(f"Camera monitoring stopped after {duration.total_seconds():.1f}s")
        logger.info(f"Final stats: {self.stats}")
    
    def _monitor_loop(self):
        """Main monitoring loop running in separate thread"""
        logger.info("Camera monitoring loop started")
        
        while self.monitoring:
            try:
                # Detect current cameras
                current_cameras = self._detect_current_cameras()
                
                # Process changes with thread-safe locking
                with self.lock:
                    self._process_camera_changes(current_cameras)
                
                # Sleep for poll interval
                time.sleep(self.config.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in camera monitoring loop: {e}", exc_info=True)
                self.stats["error_events"] += 1
                # Continue monitoring after error with longer delay
                time.sleep(1.0)
        
        logger.info("Camera monitoring loop stopped")
    
    def _detect_current_cameras(self) -> Dict[str, CameraInfo]:
        """Detect currently connected cameras"""
        current_cameras = {}
        
        try:
            # Get supported devices from detector
            supported_devices = self.detector.get_supported_devices(self.config.device_range)
            
            for device in supported_devices:
                try:
                    camera_info = self._create_camera_info(device)
                    if camera_info:
                        current_cameras[device] = camera_info
                        logger.debug(f"Detected camera: {device}")
                    
                except Exception as e:
                    logger.error(f"Error detecting camera {device}: {e}")
                    self.stats["detection_failures"] += 1
            
        except Exception as e:
            logger.error(f"Error during camera detection: {e}")
            self.stats["detection_failures"] += 1
        
        return current_cameras
    
    def _create_camera_info(self, device: str) -> Optional[CameraInfo]:
        """Create CameraInfo for a device"""
        try:
            camera_info = CameraInfo(device=device, status=CameraStatus.CONNECTED)
            
            # Detect capabilities if enabled
            if self.config.enable_capability_detection:
                capabilities = self.detector.detect_capabilities(device)
                if capabilities:
                    camera_info.capabilities = capabilities
                    logger.debug(f"Detected capabilities for {device}: {capabilities.resolution} @ {capabilities.fps}fps")
                else:
                    logger.warning(f"Could not detect capabilities for {device}")
            
            camera_info.mark_connected(camera_info.capabilities)
            return camera_info
            
        except Exception as e:
            logger.error(f"Error creating camera info for {device}: {e}")
            return None
    
    def _process_camera_changes(self, current_cameras: Dict[str, CameraInfo]):
        """Process camera connect/disconnect events"""
        
        # Find newly connected cameras
        for device, camera_info in current_cameras.items():
            if device not in self.known_cameras:
                # New camera connected
                self.known_cameras[device] = camera_info
                self._schedule_camera_event(camera_info, "connected")
        
        # Find disconnected cameras
        disconnected_devices = []
        for device in list(self.known_cameras.keys()):
            if device not in current_cameras:
                # Camera disconnected
                camera_info = self.known_cameras[device]
                camera_info.mark_disconnected()
                self._schedule_camera_event(camera_info, "disconnected")
                disconnected_devices.append(device)
        
        # Remove disconnected cameras after processing
        for device in disconnected_devices:
            del self.known_cameras[device]
    
    def _schedule_camera_event(self, camera_info: CameraInfo, event_type: str):
        """Schedule camera event callback using proper async integration"""
        try:
            # Update statistics
            self.stats["total_events"] += 1
            if event_type == "connected":
                self.stats["connect_events"] += 1
                logger.info(f"Camera connected: {camera_info.device} - {camera_info.resolution} @ {camera_info.fps}fps")
            elif event_type == "disconnected":
                self.stats["disconnect_events"] += 1
                logger.info(f"Camera disconnected: {camera_info.device}")
            
            # Create event data
            event_data = camera_info.to_dict()
            
            # Schedule callback in main event loop using call_soon_threadsafe
            # THIS FIXES THE THREADING + ASYNCIO BUG!
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._execute_callback(event_data))
            )
            
        except Exception as e:
            logger.error(f"Error scheduling camera event: {e}")
            self.stats["error_events"] += 1
    
    async def _execute_callback(self, event_data: Dict[str, Any]):
        """Execute the camera event callback"""
        try:
            await self.callback(event_data)
        except Exception as e:
            logger.error(f"Error in camera event callback: {e}")
            self.stats["error_events"] += 1
    
    async def _send_initial_status(self):
        """Send initial camera status on startup"""
        # Small delay to ensure everything is initialized
        await asyncio.sleep(0.1)
        
        try:
            # Detect initial cameras
            current_cameras = self._detect_current_cameras()
            
            with self.lock:
                if current_cameras:
                    # Send status for each detected camera
                    for device, camera_info in current_cameras.items():
                        self.known_cameras[device] = camera_info
                        logger.info(f"Initial camera status: {device} - CONNECTED")
                        await self.callback(camera_info.to_dict())
                else:
                    # Send disconnected status for video0 if no cameras found
                    camera_info = CameraInfo("/dev/video0", status=CameraStatus.DISCONNECTED)
                    camera_info.mark_disconnected()
                    self.known_cameras["/dev/video0"] = camera_info
                    logger.info("Initial camera status: /dev/video0 - DISCONNECTED")
                    await self.callback(camera_info.to_dict())
        
        except Exception as e:
            logger.error(f"Error sending initial camera status: {e}")
    
    def get_current_cameras(self) -> Dict[str, CameraInfo]:
        """Get current camera status (thread-safe)"""
        with self.lock:
            return {device: CameraInfo(
                device=info.device,
                status=info.status,
                capabilities=info.capabilities,
                connected_at=info.connected_at,
                disconnected_at=info.disconnected_at,
                last_seen=info.last_seen,
                error_message=info.error_message,
                metadata=info.metadata.copy()
            ) for device, info in self.known_cameras.items()}
    
    def get_camera_by_device(self, device: str) -> Optional[CameraInfo]:
        """Get specific camera info by device path"""
        with self.lock:
            camera_info = self.known_cameras.get(device)
            if camera_info:
                # Return a copy to avoid thread safety issues
                return CameraInfo(
                    device=camera_info.device,
                    status=camera_info.status,
                    capabilities=camera_info.capabilities,
                    connected_at=camera_info.connected_at,
                    disconnected_at=camera_info.disconnected_at,
                    last_seen=camera_info.last_seen,
                    error_message=camera_info.error_message,
                    metadata=camera_info.metadata.copy()
                )
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        stats = self.stats.copy()
        
        if stats["monitoring_started"]:
            uptime = datetime.now() - stats["monitoring_started"]
            stats["uptime_seconds"] = uptime.total_seconds()
        
        with self.lock:
            stats["current_cameras"] = len(self.known_cameras)
            stats["connected_cameras"] = len([
                c for c in self.known_cameras.values() 
                if c.status == CameraStatus.CONNECTED
            ])
        
        return stats
    
    def refresh_capabilities(self, device: Optional[str] = None):
        """Refresh camera capabilities (clears cache and re-detects)"""
        if device:
            logger.info(f"Refreshing capabilities for {device}")
            self.detector._invalidate_cache(device)
        else:
            logger.info("Refreshing all camera capabilities")
            self.detector.clear_cache()

class EventDrivenCameraMonitor(CameraMonitor):
    """
    Event-driven camera monitor using pyudev (Linux only)
    
    Provides instant response to device changes without polling overhead.
    Falls back to polling if pyudev is not available.
    """
    
    def __init__(self, callback: Callable, loop: asyncio.AbstractEventLoop, 
                 config: Optional[MonitorConfig] = None):
        super().__init__(callback, loop, config)
        
        # Try to import pyudev
        try:
            import pyudev
            self.pyudev = pyudev
            self.context = pyudev.Context()
            self.monitor = pyudev.Monitor.from_netlink(self.context)
            self.monitor.filter_by(subsystem='video4linux')
            self.event_driven = True
            logger.info("Event-driven monitoring enabled (pyudev available)")
        except ImportError:
            self.pyudev = None
            self.event_driven = False
            logger.warning("pyudev not available, falling back to polling")
    
    def _monitor_loop(self):
        """Event-driven monitoring loop"""
        if not self.event_driven:
            # Fall back to polling
            super()._monitor_loop()
            return
        
        logger.info("Event-driven camera monitoring loop started")
        
        try:
            # Send initial status
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._detect_and_process_initial_cameras())
            )
            
            # Start monitoring events
            self.monitor.start()
            
            while self.monitoring:
                # Poll for device events with timeout
                device = self.monitor.poll(timeout=1.0)
                
                if device is None:
                    continue  # Timeout, check if still monitoring
                
                action = device.action
                device_path = device.device_node
                
                if not device_path or not device_path.startswith('/dev/video'):
                    continue
                
                logger.debug(f"Device event: {action} {device_path}")
                
                if action == 'add':
                    self._handle_device_added(device_path)
                elif action == 'remove':
                    self._handle_device_removed(device_path)
                    
        except Exception as e:
            logger.error(f"Error in event-driven monitoring loop: {e}")
        finally:
            if hasattr(self, 'monitor'):
                self.monitor.remove_filter()
        
        logger.info("Event-driven camera monitoring loop stopped")
    
    def _handle_device_added(self, device_path: str):
        """Handle camera device addition"""
        # Small delay to allow device to initialize  
        time.sleep(0.1)
        
        try:
            camera_info = self._create_camera_info(device_path)
            if camera_info:
                with self.lock:
                    self.known_cameras[device_path] = camera_info
                    self._schedule_camera_event(camera_info, "connected")
        except Exception as e:
            logger.error(f"Error handling device addition {device_path}: {e}")
    
    def _handle_device_removed(self, device_path: str):
        """Handle camera device removal"""
        try:
            with self.lock:
                if device_path in self.known_cameras:
                    camera_info = self.known_cameras[device_path]
                    camera_info.mark_disconnected()
                    self._schedule_camera_event(camera_info, "disconnected")
                    del self.known_cameras[device_path]
        except Exception as e:
            logger.error(f"Error handling device removal {device_path}: {e}")
    
    async def _detect_and_process_initial_cameras(self):
        """Detect and process initial cameras for event-driven monitoring"""
        await asyncio.sleep(0.1)  # Small delay
        
        try:
            current_cameras = self._detect_current_cameras()
            
            with self.lock:
                for device, camera_info in current_cameras.items():
                    self.known_cameras[device] = camera_info
                    logger.info(f"Initial camera status: {device} - CONNECTED")
                    await self.callback(camera_info.to_dict())
                
                # If no cameras found, send default disconnected status
                if not current_cameras:
                    camera_info = CameraInfo("/dev/video0", status=CameraStatus.DISCONNECTED)
                    camera_info.mark_disconnected()
                    self.known_cameras["/dev/video0"] = camera_info
                    logger.info("Initial camera status: /dev/video0 - DISCONNECTED")
                    await self.callback(camera_info.to_dict())
        
        except Exception as e:
            logger.error(f"Error detecting initial cameras: {e}")

# Convenience functions for integration with existing code
async def get_current_cameras() -> Dict[str, CameraInfo]:
    """Get current cameras from global registry"""
    return camera_registry.get_all_cameras()

async def get_camera_status_by_device(device: str) -> Dict[str, Any]:
    """Get camera status for a specific device"""
    camera_info = camera_registry.get_camera(device)
    if camera_info:
        return camera_info.to_detailed_dict()
    else:
        return {
            "device": device,
            "status": "UNKNOWN",
            "message": "Device not found in registry",
            "timestamp": datetime.now().isoformat()
        }

def create_camera_monitor(callback: Callable, loop: asyncio.AbstractEventLoop, 
                         use_event_driven: bool = True, 
                         config: Optional[MonitorConfig] = None) -> CameraMonitor:
    """
    Factory function to create appropriate camera monitor
    
    Args:
        callback: Async callback for camera events
        loop: Event loop for callback scheduling
        use_event_driven: Try to use event-driven monitoring
        config: Monitor configuration
        
    Returns:
        CameraMonitor instance (event-driven or polling)
    """
    if use_event_driven:
        try:
            return EventDrivenCameraMonitor(callback, loop, config)
        except Exception as e:
            logger.warning(f"Failed to create event-driven monitor: {e}")
    
    return CameraMonitor(callback, loop, config)