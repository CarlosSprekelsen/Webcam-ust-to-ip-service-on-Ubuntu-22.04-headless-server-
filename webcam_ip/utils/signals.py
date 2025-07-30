"""
Signal Handling

Provides graceful shutdown and signal handling for the camera server.
Coordinates cleanup of resources, connections, and background tasks.
"""

import asyncio
import atexit
import logging
import signal
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import List, Callable, Any, Optional, Dict, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ShutdownReason(Enum):
    """Reasons for application shutdown"""
    SIGNAL_SIGTERM = "SIGTERM"
    SIGNAL_SIGINT = "SIGINT" 
    SIGNAL_SIGQUIT = "SIGQUIT"
    MANUAL = "MANUAL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"

@dataclass
class ShutdownContext:
    """Context information for shutdown process"""
    reason: ShutdownReason
    signal_number: Optional[int] = None
    start_time: float = field(default_factory=time.time)
    timeout: float = 30.0
    cleanup_handlers: List[Callable] = field(default_factory=list)
    async_cleanup_handlers: List[Callable] = field(default_factory=list)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since shutdown started"""
        return time.time() - self.start_time
    
    @property
    def remaining_time(self) -> float:
        """Get remaining time before timeout"""
        return max(0, self.timeout - self.elapsed_time)

class SignalHandler:
    """
    Handles system signals for graceful shutdown
    
    Features:
    - Cross-platform signal handling
    - Coordinated shutdown process
    - Resource cleanup management
    - Timeout handling
    - Integration with asyncio
    """
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.shutdown_event = asyncio.Event()
        self.shutdown_context: Optional[ShutdownContext] = None
        self.cleanup_handlers: List[Callable] = []
        self.async_cleanup_handlers: List[Callable] = []
        self._signal_handlers: Dict[int, Callable] = {}
        self._original_handlers: Dict[int, Any] = {}
        self._shutdown_in_progress = False
        self._lock = threading.Lock()
        
        logger.info(f"Signal handler initialized with {timeout}s timeout")
    
    def add_cleanup_handler(self, handler: Callable, async_handler: bool = False):
        """
        Add a cleanup handler to be called during shutdown
        
        Args:
            handler: Cleanup function to call
            async_handler: Whether handler is async
        """
        with self._lock:
            if async_handler:
                self.async_cleanup_handlers.append(handler)
                logger.debug(f"Added async cleanup handler: {handler.__name__}")
            else:
                self.cleanup_handlers.append(handler)
                logger.debug(f"Added sync cleanup handler: {handler.__name__}")
    
    def remove_cleanup_handler(self, handler: Callable):
        """Remove a cleanup handler"""
        with self._lock:
            if handler in self.cleanup_handlers:
                self.cleanup_handlers.remove(handler)
                logger.debug(f"Removed sync cleanup handler: {handler.__name__}")
            
            if handler in self.async_cleanup_handlers:
                self.async_cleanup_handlers.remove(handler)
                logger.debug(f"Removed async cleanup handler: {handler.__name__}")
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        if sys.platform == 'win32':
            # Windows signal handling
            signals_to_handle = [signal.SIGINT]
        else:
            # Unix signal handling
            signals_to_handle = [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]
        
        for sig in signals_to_handle:
            try:
                # Store original handler
                self._original_handlers[sig] = signal.signal(sig, self._signal_handler)
                self._signal_handlers[sig] = self._signal_handler
                logger.debug(f"Registered signal handler for {signal.Signals(sig).name}")
            except (OSError, ValueError) as e:
                logger.warning(f"Could not register handler for signal {sig}: {e}")
        
        # Register cleanup on normal exit
        atexit.register(self._atexit_handler)
        
        logger.info(f"Signal handlers registered for: {[signal.Signals(s).name for s in signals_to_handle]}")
    
    def restore_signal_handlers(self):
        """Restore original signal handlers"""
        for sig, original_handler in self._original_handlers.items():
            try:
                signal.signal(sig, original_handler)
                logger.debug(f"Restored original handler for {signal.Signals(sig).name}")
            except (OSError, ValueError) as e:
                logger.warning(f"Could not restore handler for signal {sig}: {e}")
        
        self._original_handlers.clear()
        self._signal_handlers.clear()
    
    def _signal_handler(self, sig: int, frame):
        """Handle received signals"""
        signal_name = signal.Signals(sig).name
        logger.info(f"Received signal {signal_name} ({sig})")
        
        # Determine shutdown reason
        reason_map = {
            signal.SIGTERM: ShutdownReason.SIGNAL_SIGTERM,
            signal.SIGINT: ShutdownReason.SIGNAL_SIGINT,
            signal.SIGQUIT: ShutdownReason.SIGNAL_SIGQUIT,
        }
        
        reason = reason_map.get(sig, ShutdownReason.SIGNAL_SIGTERM)
        
        # Trigger shutdown
        self.trigger_shutdown(reason, sig)
    
    def _atexit_handler(self):
        """Handle normal program exit"""
        if not self._shutdown_in_progress:
            logger.info("Normal program exit - running cleanup")
            self._run_sync_cleanup_handlers()
    
    def trigger_shutdown(self, reason: ShutdownReason, signal_number: Optional[int] = None):
        """
        Trigger graceful shutdown
        
        Args:
            reason: Reason for shutdown
            signal_number: Signal number if triggered by signal
        """
        with self._lock:
            if self._shutdown_in_progress:
                logger.warning(f"Shutdown already in progress, ignoring {reason}")
                return
            
            self._shutdown_in_progress = True
        
        logger.info(f"Initiating graceful shutdown: {reason.value}")
        
        # Create shutdown context
        self.shutdown_context = ShutdownContext(
            reason=reason,
            signal_number=signal_number,
            timeout=self.timeout,
            cleanup_handlers=self.cleanup_handlers.copy(),
            async_cleanup_handlers=self.async_cleanup_handlers.copy()
        )
        
        # Set shutdown event
        try:
            # Try to set the event in the current loop
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self.shutdown_event.set)
        except RuntimeError:
            # No running loop, set directly
            if not self.shutdown_event.is_set():
                # Create a new loop to set the event
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._set_shutdown_event())
                    loop.close()
                except Exception as e:
                    logger.error(f"Could not set shutdown event: {e}")
    
    async def _set_shutdown_event(self):
        """Set shutdown event in async context"""
        self.shutdown_event.set()
    
    async def wait_for_shutdown(self) -> ShutdownContext:
        """
        Wait for shutdown signal
        
        Returns:
            ShutdownContext with shutdown information
        """
        logger.debug("Waiting for shutdown signal...")
        await self.shutdown_event.wait()
        logger.info(f"Shutdown signal received: {self.shutdown_context.reason.value}")
        return self.shutdown_context
    
    async def run_async_cleanup(self):
        """Run all async cleanup handlers with timeout"""
        if not self.shutdown_context:
            return
        
        if not self.async_cleanup_handlers:
            logger.debug("No async cleanup handlers to run")
            return
        
        logger.info(f"Running {len(self.async_cleanup_handlers)} async cleanup handlers...")
        
        cleanup_tasks = []
        for handler in self.shutdown_context.async_cleanup_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    task = asyncio.create_task(handler())
                else:
                    # Wrap sync function in async
                    task = asyncio.create_task(self._run_sync_in_executor(handler))
                
                cleanup_tasks.append(task)
                logger.debug(f"Added cleanup task: {handler.__name__}")
                
            except Exception as e:
                logger.error(f"Error creating cleanup task for {handler.__name__}: {e}")
        
        if cleanup_tasks:
            try:
                # Wait for all cleanup tasks with timeout
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=self.shutdown_context.remaining_time
                )
                logger.info("All async cleanup handlers completed")
                
            except asyncio.TimeoutError:
                logger.warning(f"Async cleanup timed out after {self.shutdown_context.remaining_time:.1f}s")
                
                # Cancel remaining tasks
                for task in cleanup_tasks:
                    if not task.done():
                        task.cancel()
                        logger.debug(f"Cancelled cleanup task: {task}")
                
            except Exception as e:
                logger.error(f"Error during async cleanup: {e}")
    
    def run_sync_cleanup(self):
        """Run all sync cleanup handlers"""
        self._run_sync_cleanup_handlers()
    
    def _run_sync_cleanup_handlers(self):
        """Internal method to run sync cleanup handlers"""
        if not self.cleanup_handlers:
            logger.debug("No sync cleanup handlers to run")
            return
        
        logger.info(f"Running {len(self.cleanup_handlers)} sync cleanup handlers...")
        
        for handler in self.cleanup_handlers:
            try:
                handler()
                logger.debug(f"Completed cleanup handler: {handler.__name__}")
            except Exception as e:
                logger.error(f"Error in cleanup handler {handler.__name__}: {e}")
    
    async def _run_sync_in_executor(self, handler: Callable):
        """Run sync handler in thread executor"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, handler)
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested"""
        return self.shutdown_event.is_set()
    
    def get_shutdown_context(self) -> Optional[ShutdownContext]:
        """Get current shutdown context"""
        return self.shutdown_context

class GracefulShutdown:
    """
    Context manager for graceful shutdown handling
    
    Provides a clean interface for managing application lifecycle
    with proper resource cleanup.
    """
    
    def __init__(self, timeout: float = 30.0, setup_signals: bool = True):
        self.signal_handler = SignalHandler(timeout)
        self.setup_signals = setup_signals
        self._resources: Set[Any] = set()
    
    def __enter__(self):
        if self.setup_signals:
            self.signal_handler.setup_signal_handlers()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.setup_signals:
            self.signal_handler.restore_signal_handlers()
        
        # Run sync cleanup
        self.signal_handler.run_sync_cleanup()
    
    async def __aenter__(self):
        if self.setup_signals:
            self.signal_handler.setup_signal_handlers()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Run async cleanup first
        await self.signal_handler.run_async_cleanup()
        
        # Then sync cleanup
        self.signal_handler.run_sync_cleanup()
        
        if self.setup_signals:
            self.signal_handler.restore_signal_handlers()
    
    def add_cleanup_handler(self, handler: Callable, async_handler: bool = False):
        """Add cleanup handler"""
        self.signal_handler.add_cleanup_handler(handler, async_handler)
    
    def add_resource(self, resource: Any, cleanup_method: str = "close"):
        """
        Add resource for automatic cleanup
        
        Args:
            resource: Resource object
            cleanup_method: Method name to call for cleanup
        """
        self._resources.add(resource)
        
        def cleanup():
            try:
                if hasattr(resource, cleanup_method):
                    method = getattr(resource, cleanup_method)
                    if callable(method):
                        method()
                        logger.debug(f"Cleaned up resource: {resource}")
            except Exception as e:
                logger.error(f"Error cleaning up resource {resource}: {e}")
        
        self.add_cleanup_handler(cleanup)
    
    async def wait_for_shutdown(self) -> ShutdownContext:
        """Wait for shutdown signal"""
        return await self.signal_handler.wait_for_shutdown()
    
    def trigger_shutdown(self, reason: str = "manual"):
        """Manually trigger shutdown"""
        shutdown_reason = ShutdownReason.MANUAL
        self.signal_handler.trigger_shutdown(shutdown_reason)

# Global signal handler instance
_global_signal_handler: Optional[SignalHandler] = None

def setup_signal_handlers(timeout: float = 30.0) -> SignalHandler:
    """
    Set up global signal handlers
    
    Args:
        timeout: Shutdown timeout in seconds
        
    Returns:
        SignalHandler instance
    """
    global _global_signal_handler
    
    if _global_signal_handler is None:
        _global_signal_handler = SignalHandler(timeout)
        _global_signal_handler.setup_signal_handlers()
        logger.info("Global signal handlers set up")
    
    return _global_signal_handler

def get_signal_handler() -> Optional[SignalHandler]:
    """Get global signal handler"""
    return _global_signal_handler

def cleanup_on_exit(handler: Callable, async_handler: bool = False):
    """
    Decorator to register cleanup handler
    
    Args:
        handler: Function to call on shutdown
        async_handler: Whether handler is async
    """
    if _global_signal_handler:
        _global_signal_handler.add_cleanup_handler(handler, async_handler)
    else:
        logger.warning("No global signal handler - cleanup handler not registered")
    
    return handler

@asynccontextmanager
async def managed_shutdown(timeout: float = 30.0):
    """
    Async context manager for managed shutdown
    
    Args:
        timeout: Shutdown timeout in seconds
        
    Usage:
        async with managed_shutdown() as shutdown:
            await shutdown.wait_for_shutdown()
    """
    async with GracefulShutdown(timeout=timeout) as shutdown:
        yield shutdown

# Convenience functions
def wait_for_signal(timeout: float = 30.0) -> ShutdownContext:
    """
    Wait for shutdown signal (synchronous)
    
    Args:
        timeout: Shutdown timeout
        
    Returns:
        ShutdownContext
    """
    handler = setup_signal_handlers(timeout)
    
    # Block until signal received
    while not handler.is_shutdown_requested():
        time.sleep(0.1)
    
    return handler.get_shutdown_context()

def register_cleanup(func: Callable, async_cleanup: bool = False):
    """
    Register a cleanup function
    
    Args:
        func: Cleanup function
        async_cleanup: Whether function is async
    """
    handler = setup_signal_handlers()
    handler.add_cleanup_handler(func, async_cleanup)