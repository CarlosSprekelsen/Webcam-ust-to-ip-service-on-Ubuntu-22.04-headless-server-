import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ServerConfig:
    host: str = "0.0.0.0" 
    port: int = 8002
    websocket_path: str = "/ws"

@dataclass  
class CameraConfig:
    poll_interval: float = 0.1
    detection_timeout: float = 2.0
    devices_range: range = range(10)  # /dev/video0-9

@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_dir: Path = Path("/opt/webcam-env/logs")
    file_enabled: bool = True

def load_config() -> tuple[ServerConfig, CameraConfig, LoggingConfig]:
    """Load configuration from environment variables and config files"""
    return (
        ServerConfig(
            host=os.getenv("WEBSOCKET_HOST", "0.0.0.0"),
            port=int(os.getenv("WEBSOCKET_PORT", "8002")),
        ),
        CameraConfig(
            poll_interval=float(os.getenv("CAMERA_POLL_INTERVAL", "0.1")),
        ),
        LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=Path(os.getenv("LOG_DIR", "/opt/webcam-env/logs")),
        )
    )