"""
Logging Configuration

Provides structured logging with JSON output, file rotation, and ELK stack compatibility.
Supports both development-friendly and production-ready logging formats.
"""

import json
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field

@dataclass
class LogConfig:
    """Configuration for logging setup"""
    level: str = "INFO"
    log_dir: Path = Path("/opt/webcam-env/logs")
    console_enabled: bool = True
    file_enabled: bool = True
    json_format: bool = False
    max_file_size: str = "10MB"
    backup_count: int = 5
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    json_format_string: str = None
    
    def __post_init__(self):
        """Initialize derived values"""
        # Convert string level to logging constant
        self.log_level = getattr(logging, self.level.upper(), logging.INFO)
        
        # Convert max_file_size string to bytes
        self.max_file_size_bytes = self._parse_file_size(self.max_file_size)
        
        # Ensure log directory exists
        self.log_dir = Path(self.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set default JSON format if not provided
        if self.json_format_string is None:
            self.json_format_string = self.format_string
    
    def _parse_file_size(self, size_str: str) -> int:
        """Parse file size string like '10MB' to bytes"""
        size_str = size_str.upper().strip()
        
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }
        
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    return int(float(size_str[:-len(suffix)]) * multiplier)
                except ValueError:
                    break
        
        # Default to 10MB if parsing fails
        return 10 * 1024 * 1024

class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging
    
    Produces JSON log entries suitable for ELK stack, Fluentd, or other log aggregators.
    """
    
    def __init__(self, format_string: str = None):
        super().__init__()
        self.format_string = format_string or "%(message)s"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
            "thread_name": record.threadName
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message', 'exc_info',
                'exc_text', 'stack_info', 'getMessage'
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        # Add application context if available
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        
        if hasattr(record, 'component'):
            log_entry["component"] = record.component
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)

class StructuredLogger:
    """
    Wrapper for Python logger with structured logging capabilities
    
    Provides convenient methods for adding context and structured data to log entries.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Set persistent context for all log messages"""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear persistent context"""
        self._context.clear()
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log with combined context and kwargs"""
        combined_context = {**self._context, **kwargs}
        
        # Create LogRecord with extra context
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, message, (), None, 
            extra=combined_context
        )
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback and context"""
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, **kwargs)

class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output
    
    Adds colors to log levels for better readability during development.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with colors if supported"""
        # Check if colors should be used
        if not self._should_use_colors():
            return super().format(record)
        
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        
        # Temporarily modify the record
        original_levelname = record.levelname
        record.levelname = f"{level_color}{record.levelname}{reset_color}"
        
        try:
            return super().format(record)
        finally:
            # Restore original level name
            record.levelname = original_levelname
    
    def _should_use_colors(self) -> bool:
        """Check if colors should be used"""
        # Don't use colors if NO_COLOR environment variable is set
        if os.environ.get('NO_COLOR'):
            return False
        
        # Use colors if FORCE_COLOR is set
        if os.environ.get('FORCE_COLOR'):
            return True
        
        # Use colors if stderr is a TTY
        return hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()

def setup_logging(config: LogConfig) -> Dict[str, logging.Logger]:
    """
    Set up logging with the provided configuration
    
    Args:
        config: LogConfig instance with logging settings
        
    Returns:
        Dictionary of configured loggers by name
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger level
    root_logger.setLevel(config.log_level)
    
    loggers = {}
    
    # Console handler
    if config.console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(config.log_level)
        
        if config.json_format:
            console_formatter = JsonFormatter(config.json_format_string)
        else:
            console_formatter = ColoredFormatter(config.format_string)
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if config.file_enabled:
        try:
            log_file = config.log_dir / "server.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=config.max_file_size_bytes,
                backupCount=config.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(config.log_level)
            
            if config.json_format:
                file_formatter = JsonFormatter(config.json_format_string)
            else:
                file_formatter = logging.Formatter(config.format_string)
            
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)
    
    # Create specific loggers for modules
    module_names = [
        'webcam_ip',
        'webcam_ip.server',
        'webcam_ip.camera', 
        'webcam_ip.utils',
        'websockets',
        'asyncio'
    ]
    
    for module_name in module_names:
        logger = logging.getLogger(module_name)
        logger.setLevel(config.log_level)
        loggers[module_name] = logger
    
    # Log successful setup
    setup_logger = logging.getLogger('webcam_ip.utils.logging')
    setup_logger.info(f"Logging configured - Level: {config.level}, "
                     f"Console: {config.console_enabled}, File: {config.file_enabled}, "
                     f"JSON: {config.json_format}")
    
    return loggers

def get_logger(name: str, structured: bool = False) -> Union[logging.Logger, StructuredLogger]:
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__)
        structured: Whether to return a StructuredLogger wrapper
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    if structured:
        return StructuredLogger(logger)
    
    return logger

def configure_uvicorn_logging(config: LogConfig):
    """
    Configure uvicorn logging to match our logging setup
    
    Args:
        config: LogConfig instance
    """
    # Configure uvicorn access logger
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(config.log_level)
    
    # Configure uvicorn error logger  
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.setLevel(config.log_level)
    
    # Prevent double logging
    uvicorn_access.propagate = False
    uvicorn_error.propagate = False

def setup_development_logging(level: str = "DEBUG") -> Dict[str, logging.Logger]:
    """
    Quick setup for development logging with console output and colors
    
    Args:
        level: Log level string
        
    Returns:
        Dictionary of configured loggers
    """
    config = LogConfig(
        level=level,
        console_enabled=True,
        file_enabled=False,
        json_format=False
    )
    
    return setup_logging(config)

def setup_production_logging(log_dir: Union[str, Path] = "/opt/webcam-env/logs",
                           level: str = "INFO",
                           json_format: bool = True) -> Dict[str, logging.Logger]:
    """
    Quick setup for production logging with JSON format and file rotation
    
    Args:
        log_dir: Directory for log files
        level: Log level string  
        json_format: Whether to use JSON format
        
    Returns:
        Dictionary of configured loggers
    """
    config = LogConfig(
        level=level,
        log_dir=Path(log_dir),
        console_enabled=True,
        file_enabled=True,
        json_format=json_format,
        max_file_size="50MB",
        backup_count=10
    )
    
    return setup_logging(config)

# Convenience function for quick logger setup
def quick_setup(level: str = "INFO", 
                json_format: bool = False,
                file_enabled: bool = True) -> logging.Logger:
    """
    Quick logging setup for simple use cases
    
    Args:
        level: Log level
        json_format: Use JSON format
        file_enabled: Enable file logging
        
    Returns:
        Main logger
    """
    config = LogConfig(
        level=level,
        json_format=json_format,
        file_enabled=file_enabled
    )
    
    loggers = setup_logging(config)
    return loggers.get('webcam_ip', logging.getLogger('webcam_ip'))

# Context manager for temporary log level
class LogLevel:
    """Context manager for temporarily changing log level"""
    
    def __init__(self, logger: logging.Logger, level: Union[str, int]):
        self.logger = logger
        self.new_level = getattr(logging, level.upper(), level) if isinstance(level, str) else level
        self.old_level = None
    
    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_level is not None:
            self.logger.setLevel(self.old_level)