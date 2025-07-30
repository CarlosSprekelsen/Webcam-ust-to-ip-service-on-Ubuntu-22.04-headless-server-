"""
Utility Module

Provides common utilities for logging, signal handling, and other infrastructure needs.
These utilities are used across the camera and server modules.
"""

from .logging import (
    setup_logging,
    get_logger,
    JsonFormatter,
    StructuredLogger,
    LogConfig,
    configure_uvicorn_logging
)

from .signals import (
    SignalHandler,
    GracefulShutdown,
    setup_signal_handlers,
    cleanup_on_exit
)

__version__ = "1.0.0"
__all__ = [
    # Logging
    "setup_logging",
    "get_logger", 
    "JsonFormatter",
    "StructuredLogger",
    "LogConfig",
    "configure_uvicorn_logging",
    
    # Signal handling
    "SignalHandler",
    "GracefulShutdown",
    "setup_signal_handlers", 
    "cleanup_on_exit"
]