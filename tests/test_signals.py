# test_signals.py
import asyncio
import time
import threading
from webcam_ip.utils import setup_signal_handlers, GracefulShutdown

def test_signal_setup():
    """Test signal handler setup"""
    print("🔍 Testing signal handler setup...")
    
    handler = setup_signal_handlers(timeout=10.0)
    
    # Add cleanup handlers
    def cleanup_resources():
        print("🧹 Cleaning up resources...")
    
    async def async_cleanup():
        print("🧹 Async cleanup starting...")
        await asyncio.sleep(0.5)  # Simulate cleanup work
        print("🧹 Async cleanup completed")
    
    handler.add_cleanup_handler(cleanup_resources)
    handler.add_cleanup_handler(async_cleanup, async_handler=True)
    
    print("✅ Signal handlers registered")
    print("💡 Press Ctrl+C to test graceful shutdown")
    
    return handler

async def test_graceful_shutdown():
    """Test graceful shutdown context manager"""
    print("🔍 Testing graceful shutdown...")
    
    async with GracefulShutdown(timeout=10.0) as shutdown:
        # Add cleanup handlers
        def cleanup_db():
            print("🗄️ Closing database connections...")
        
        async def cleanup_server():
            print("🖥️ Shutting down server...")
            await asyncio.sleep(0.3)
            print("🖥️ Server stopped")
        
        shutdown.add_cleanup_handler(cleanup_db)
        shutdown.add_cleanup_handler(cleanup_server, async_handler=True)
        
        print("⏳ Waiting for shutdown signal...")
        print("💡 Press Ctrl+C to trigger shutdown")
        
        # Wait for shutdown
        context = await shutdown.wait_for_shutdown()
        print(f"📨 Shutdown triggered: {context.reason.value}")

def test_manual_shutdown():
    """Test manual shutdown triggering"""
    print("🔍 Testing manual shutdown...")
    
    handler = setup_signal_handlers()
    
    def delayed_shutdown():
        """Trigger shutdown after 3 seconds"""
        time.sleep(3)
        print("⏰ Triggering manual shutdown...")
        handler.trigger_shutdown("MANUAL")
    
    # Start shutdown trigger in background
    shutdown_thread = threading.Thread(target=delayed_shutdown)
    shutdown_thread.start()
    
    # Wait for shutdown
    context = handler.wait_for_shutdown()
    print(f"📨 Manual shutdown completed: {context.reason.value}")

if __name__ == "__main__":
    print("Choose test:")
    print("1. Signal setup")
    print("2. Graceful shutdown (async)")
    print("3. Manual shutdown")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        handler = test_signal_setup()
        context = handler.wait_for_shutdown()
        print(f"Shutdown completed: {context.reason.value}")
    elif choice == "2":
        asyncio.run(test_graceful_shutdown())
    elif choice == "3":
        test_manual_shutdown()
    else:
        print("Invalid choice")