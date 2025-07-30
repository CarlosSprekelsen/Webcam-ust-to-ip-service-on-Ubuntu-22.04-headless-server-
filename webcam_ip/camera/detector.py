"""
Camera Capability Detection

Handles detection of camera capabilities using v4l2-ctl with robust parsing.
Provides fallback mechanisms and comprehensive error handling.
"""

import os
import re
import subprocess
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from .models import CameraCapabilities

logger = logging.getLogger(__name__)

@dataclass
class DetectionConfig:
    """Configuration for camera detection"""
    v4l2_timeout: float = 2.0
    max_retries: int = 2
    retry_delay: float = 0.5
    fallback_resolution: str = "640x480"
    fallback_fps: int = 30
    fallback_formats: List[str] = None
    
    def __post_init__(self):
        if self.fallback_formats is None:
            self.fallback_formats = ["YUYV"]

class CameraCapabilityDetector:
    """
    Handles camera capability detection using v4l2-ctl with improved parsing
    
    Features:
    - Robust v4l2-ctl output parsing
    - Multiple detection strategies
    - Fallback mechanisms for unreliable devices
    - Comprehensive error handling
    - Caching for performance
    """
    
    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()
        self._capability_cache: Dict[str, CameraCapabilities] = {}
        self._cache_timeout = 30.0  # Cache for 30 seconds
        self._last_cache_time: Dict[str, float] = {}
    
    def detect_capabilities(self, device: str) -> Optional[CameraCapabilities]:
        """
        Detect camera capabilities for a given device
        
        Args:
            device: Device path (e.g., "/dev/video0")
            
        Returns:
            CameraCapabilities object or None if detection fails
        """
        if not self._is_valid_device(device):
            logger.warning(f"Invalid device path: {device}")
            return None
        
        # Check cache first
        cached_caps = self._get_cached_capabilities(device)
        if cached_caps:
            logger.debug(f"Using cached capabilities for {device}")
            return cached_caps
        
        logger.info(f"Detecting capabilities for {device}")
        
        try:
            # Primary detection method
            capabilities = self._detect_with_v4l2_list_formats(device)
            if capabilities:
                self._cache_capabilities(device, capabilities)
                return capabilities
            
            # Fallback detection method
            logger.warning(f"Primary detection failed for {device}, trying fallback")
            capabilities = self._detect_with_v4l2_get_fmt(device)
            if capabilities:
                self._cache_capabilities(device, capabilities)
                return capabilities
            
            # Final fallback - basic device check
            if self._device_responds(device):
                logger.warning(f"Using fallback capabilities for {device}")
                capabilities = CameraCapabilities(
                    resolution=self.config.fallback_resolution,
                    fps=self.config.fallback_fps,
                    formats=self.config.fallback_formats.copy()
                )
                self._cache_capabilities(device, capabilities)
                return capabilities
            
            logger.error(f"All detection methods failed for {device}")
            return None
            
        except Exception as e:
            logger.error(f"Exception during capability detection for {device}: {e}")
            return None
    
    def _detect_with_v4l2_list_formats(self, device: str) -> Optional[CameraCapabilities]:
        """Primary detection method using v4l2-ctl --list-formats-ext"""
        try:
            cmd = ["v4l2-ctl", "--device", device, "--list-formats-ext"]
            result = self._run_v4l2_command(cmd)
            
            if not result:
                return None
            
            return self._parse_list_formats_output(result.stdout)
            
        except Exception as e:
            logger.debug(f"v4l2-ctl list-formats failed for {device}: {e}")
            return None
    
    def _detect_with_v4l2_get_fmt(self, device: str) -> Optional[CameraCapabilities]:
        """Fallback detection method using v4l2-ctl --get-fmt-video"""
        try:
            cmd = ["v4l2-ctl", "--device", device, "--get-fmt-video"]
            result = self._run_v4l2_command(cmd)
            
            if not result:
                return None
            
            return self._parse_get_fmt_output(result.stdout)
            
        except Exception as e:
            logger.debug(f"v4l2-ctl get-fmt failed for {device}: {e}")
            return None
    
    def _run_v4l2_command(self, cmd: List[str]) -> Optional[subprocess.CompletedProcess]:
        """Run v4l2-ctl command with retries and error handling"""
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Running command (attempt {attempt + 1}): {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.v4l2_timeout,
                    check=False  # Don't raise on non-zero exit
                )
                
                if result.returncode == 0:
                    return result
                
                logger.debug(f"Command failed with exit code {result.returncode}: {result.stderr}")
                
                # Retry on certain errors
                if attempt < self.config.max_retries - 1:
                    import time
                    time.sleep(self.config.retry_delay)
                
            except subprocess.TimeoutExpired:
                logger.warning(f"Command timeout after {self.config.v4l2_timeout}s: {' '.join(cmd)}")
            except FileNotFoundError:
                logger.error("v4l2-ctl command not found - please install v4l-utils")
                break
            except Exception as e:
                logger.error(f"Unexpected error running v4l2-ctl: {e}")
                break
        
        return None
    
    def _parse_list_formats_output(self, output: str) -> Optional[CameraCapabilities]:
        """Parse v4l2-ctl --list-formats-ext output with robust regex patterns"""
        try:
            formats = []
            best_resolution = self.config.fallback_resolution
            best_fps = self.config.fallback_fps
            
            lines = output.split('\n')
            current_format = None
            
            # Improved regex patterns
            format_pattern = re.compile(r'\[(\d+)\]:\s*\'(\w+)\'\s*\(([^)]+)\)')
            size_pattern = re.compile(r'Size:\s*Discrete\s*(\d+x\d+)')
            fps_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*fps')
            interval_pattern = re.compile(r'Interval:\s*Discrete\s*[\d.]+s\s*\(([^)]+)\)')
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Check for format line
                format_match = format_pattern.search(line)
                if format_match:
                    current_format = format_match.group(2)  # e.g., "YUYV"
                    if current_format not in formats:
                        formats.append(current_format)
                    logger.debug(f"Found format: {current_format}")
                    continue
                
                # Check for size line
                size_match = size_pattern.search(line)
                if size_match and current_format:
                    resolution = size_match.group(1)
                    logger.debug(f"Found resolution: {resolution} for format {current_format}")
                    
                    # Look ahead for frame rate information
                    fps_found = self._find_fps_for_resolution(lines, i, resolution)
                    if fps_found:
                        # Prefer higher resolution or higher fps
                        if self._is_better_resolution(resolution, best_resolution, fps_found, best_fps):
                            best_resolution = resolution
                            best_fps = fps_found
                            logger.debug(f"Updated best: {resolution} @ {fps_found}fps")
            
            if not formats:
                logger.warning("No formats found in v4l2-ctl output")
                return None
            
            capabilities = CameraCapabilities(
                resolution=best_resolution,
                fps=best_fps,
                formats=formats
            )
            
            logger.info(f"Detected capabilities: {capabilities.resolution} @ {capabilities.fps}fps, formats: {capabilities.formats}")
            return capabilities
            
        except Exception as e:
            logger.error(f"Error parsing list-formats output: {e}")
            return None
    
    def _find_fps_for_resolution(self, lines: List[str], start_index: int, resolution: str) -> int:
        """Find FPS information for a specific resolution"""
        fps_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*fps')
        
        # Look in the next 10 lines for FPS information
        for i in range(start_index + 1, min(start_index + 11, len(lines))):
            line = lines[i].strip()
            
            # Stop if we hit another resolution or format
            if 'Size:' in line or 'fps' not in line.lower():
                if 'Interval:' not in line and 'fps' not in line:
                    break
            
            fps_match = fps_pattern.search(line)
            if fps_match:
                try:
                    fps = int(float(fps_match.group(1)))
                    logger.debug(f"Found FPS {fps} for resolution {resolution}")
                    return fps
                except ValueError:
                    continue
        
        return self.config.fallback_fps
    
    def _parse_get_fmt_output(self, output: str) -> Optional[CameraCapabilities]:
        """Parse v4l2-ctl --get-fmt-video output"""
        try:
            width_pattern = re.compile(r'Width/Height\s*:\s*(\d+)/(\d+)')
            pixelformat_pattern = re.compile(r'Pixel Format\s*:\s*\'(\w+)\'')
            
            width, height = 640, 480  # defaults
            pixel_format = "YUYV"  # default
            
            for line in output.split('\n'):
                line = line.strip()
                
                # Extract width/height
                width_match = width_pattern.search(line)
                if width_match:
                    width = int(width_match.group(1))
                    height = int(width_match.group(2))
                
                # Extract pixel format
                format_match = pixelformat_pattern.search(line)
                if format_match:
                    pixel_format = format_match.group(1)
            
            resolution = f"{width}x{height}"
            
            capabilities = CameraCapabilities(
                resolution=resolution,
                fps=self.config.fallback_fps,  # Can't determine FPS from get-fmt
                formats=[pixel_format]
            )
            
            logger.info(f"Detected from get-fmt: {resolution}, format: {pixel_format}")
            return capabilities
            
        except Exception as e:
            logger.error(f"Error parsing get-fmt output: {e}")
            return None
    
    def _is_better_resolution(self, new_res: str, current_res: str, new_fps: int, current_fps: int) -> bool:
        """Determine if new resolution/fps combo is better than current"""
        try:
            new_w, new_h = map(int, new_res.split('x'))
            cur_w, cur_h = map(int, current_res.split('x'))
            
            new_pixels = new_w * new_h
            cur_pixels = cur_w * cur_h
            
            # Prefer higher resolution, but not at the cost of very low FPS
            if new_pixels > cur_pixels and new_fps >= 15:
                return True
            
            # If same resolution, prefer higher FPS
            if new_pixels == cur_pixels and new_fps > current_fps:
                return True
            
            # Prefer common resolutions
            common_resolutions = ["1920x1080", "1280x720", "640x480"]
            if new_res in common_resolutions and current_res not in common_resolutions:
                return True
            
            return False
            
        except ValueError:
            return False
    
    def _device_responds(self, device: str) -> bool:
        """Check if device responds to basic v4l2-ctl query"""
        try:
            cmd = ["v4l2-ctl", "--device", device, "--info"]
            result = self._run_v4l2_command(cmd)
            return result is not None and result.returncode == 0
        except Exception:
            return False
    
    def _is_valid_device(self, device: str) -> bool:
        """Validate device path and existence"""
        if not device or not device.startswith('/dev/video'):
            return False
        
        return os.path.exists(device) and os.access(device, os.R_OK)
    
    def _get_cached_capabilities(self, device: str) -> Optional[CameraCapabilities]:
        """Get cached capabilities if still valid"""
        if device not in self._capability_cache:
            return None
        
        # Check if cache is still valid
        import time
        cache_time = self._last_cache_time.get(device, 0)
        if time.time() - cache_time > self._cache_timeout:
            self._invalidate_cache(device)
            return None
        
        return self._capability_cache[device]
    
    def _cache_capabilities(self, device: str, capabilities: CameraCapabilities):
        """Cache capabilities for a device"""
        import time
        self._capability_cache[device] = capabilities
        self._last_cache_time[device] = time.time()
        logger.debug(f"Cached capabilities for {device}")
    
    def _invalidate_cache(self, device: str):
        """Invalidate cache for a device"""
        self._capability_cache.pop(device, None)
        self._last_cache_time.pop(device, None)
        logger.debug(f"Invalidated cache for {device}")
    
    def clear_cache(self):
        """Clear all cached capabilities"""
        self._capability_cache.clear()
        self._last_cache_time.clear()
        logger.info("Cleared capability cache")
    
    def get_supported_devices(self, device_range: range = range(10)) -> List[str]:
        """
        Get list of supported video devices
        
        Args:
            device_range: Range of device numbers to check (default 0-9)
            
        Returns:
            List of device paths that exist and respond
        """
        supported = []
        
        for i in device_range:
            device = f"/dev/video{i}"
            
            if self._is_valid_device(device):
                # Quick check if device responds
                if self._device_responds(device):
                    supported.append(device)
                    logger.debug(f"Device {device} is supported")
                else:
                    logger.debug(f"Device {device} exists but doesn't respond")
            else:
                logger.debug(f"Device {device} not found or not accessible")
        
        logger.info(f"Found {len(supported)} supported devices: {supported}")
        return supported
    
    def detect_all_capabilities(self, device_range: range = range(10)) -> Dict[str, CameraCapabilities]:
        """
        Detect capabilities for all available devices
        
        Args:
            device_range: Range of device numbers to check
            
        Returns:
            Dictionary mapping device paths to capabilities
        """
        all_capabilities = {}
        supported_devices = self.get_supported_devices(device_range)
        
        for device in supported_devices:
            capabilities = self.detect_capabilities(device)
            if capabilities:
                all_capabilities[device] = capabilities
        
        logger.info(f"Detected capabilities for {len(all_capabilities)} devices")
        return all_capabilities

# Global detector instance with default configuration
default_detector = CameraCapabilityDetector()

# Convenience functions for backward compatibility
def detect_camera_capabilities(device: str) -> Optional[CameraCapabilities]:
    """Convenience function to detect capabilities for a single device"""
    return default_detector.detect_capabilities(device)

def get_supported_cameras(device_range: range = range(10)) -> List[str]:
    """Convenience function to get supported camera devices"""
    return default_detector.get_supported_devices(device_range)

def detect_all_cameras(device_range: range = range(10)) -> Dict[str, CameraCapabilities]:
    """Convenience function to detect all camera capabilities"""
    return default_detector.detect_all_capabilities(device_range)