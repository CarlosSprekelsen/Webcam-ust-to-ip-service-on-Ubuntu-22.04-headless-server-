#!/usr/bin/env python3
"""
Full Integration Validation Test
Tests that all components work together correctly
"""

import asyncio
import tempfile
from pathlib import Path

async def test_server_creation():
    """Test that server can be created with all components"""
    print("🔍 Testing server creation...")
    
    try:
        from webcam_ip.server import WebSocketJSONRPCServer, create_server
        from webcam_ip.server.jsonrpc_handler import JSONRPCHandler
        from webcam_ip.server.methods import register_all_methods
        
        # Test server creation
        server = WebSocketJSONRPCServer()
        assert server.host == "0.0.0.0", f"Expected host 0.0.0.0, got {server.host}"
        assert server.port == 8002, f"Expected port 8002, got {server.port}"
        assert server.websocket_path == "/ws", f"Expected path /ws, got {server.websocket_path}"
        
        # Test that RPC handler is properly initialized
        assert server.rpc_handler is not None, "RPC handler should be initialized"
        methods = server.rpc_handler.get_method_list()
        assert len(methods) > 0, "Methods should be registered"
        assert "ping" in methods, "Ping method should be registered"
        
        # Test factory function
        server2 = create_server(host="127.0.0.1", port=8003)
        assert server2.host == "127.0.0.1", "Factory should set custom host"
        assert server2.port == 8003, "Factory should set custom port"
        
        print("✅ Server creation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Server creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_camera_monitor_creation():
    """Test camera monitor creation (without starting)"""
    print("🔍 Testing camera monitor creation...")
    
    try:
        from webcam_ip.camera import create_camera_monitor, MonitorConfig, CameraMonitor
        
        # Dummy callback
        async def dummy_callback(data):
            pass
        
        # Test monitor creation
        loop = asyncio.get_event_loop()
        config = MonitorConfig(
            poll_interval=1.0,
            detection_timeout=3.0,
            enable_capability_detection=False  # Disable for testing
        )
        
        monitor = create_camera_monitor(
            callback=dummy_callback,
            loop=loop,
            use_event_driven=False,  # Use polling for testing
            config=config
        )
        
        assert isinstance(monitor, CameraMonitor), f"Expected CameraMonitor, got {type(monitor)}"
        assert monitor.config.poll_interval == 1.0, f"Expected poll interval 1.0, got {monitor.config.poll_interval}"
        assert monitor.monitoring == False, "Monitor should not be started yet"
        
        print("✅ Camera monitor creation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Camera monitor creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_utils_integration():
    """Test utils components integration"""
    print("🔍 Testing utils integration...")
    
    try:
        from webcam_ip.utils import setup_logging, LogConfig, GracefulShutdown
        
        # Test logging setup
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LogConfig(
                level="INFO",
                log_dir=Path(temp_dir),
                console_enabled=False,
                file_enabled=True
            )
            
            loggers = setup_logging(config)
            assert len(loggers) > 0, "Loggers should be created"
        
        # Test graceful shutdown creation (don't actually use it)
        shutdown = GracefulShutdown(timeout=10.0, setup_signals=False)
        assert shutdown.signal_handler.timeout == 10.0, "Timeout should be set correctly"
        
        print("✅ Utils integration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Utils integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_cross_component_integration():
    """Test integration between different components"""
    print("🔍 Testing cross-component integration...")
    
    try:
        from webcam_ip.server import WebSocketJSONRPCServer
        from webcam_ip.camera import create_camera_monitor, MonitorConfig
        from webcam_ip.utils import setup_logging, LogConfig
        
        # Setup logging
        with tempfile.TemporaryDirectory() as temp_dir:
            log_config = LogConfig(
                level="INFO",
                log_dir=Path(temp_dir),
                console_enabled=False,
                file_enabled=True
            )
            setup_logging(log_config)
            
            # Create server
            server = WebSocketJSONRPCServer()
            
            # Create camera monitor with server callback
            loop = asyncio.get_event_loop()
            monitor_config = MonitorConfig(
                poll_interval=1.0,
                enable_capability_detection=False
            )
            
            monitor = create_camera_monitor(
                callback=server.broadcast_camera_status,  # Integration point!
                loop=loop,
                use_event_driven=False,
                config=monitor_config
            )
            
            # Set monitor on server (dependency injection)
            server.set_camera_monitor(monitor)
            assert server.camera_monitor is not None, "Camera monitor should be set on server"
            
            print("✅ Cross-component integration working correctly")
            return True
            
    except Exception as e:
        print(f"❌ Cross-component integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_complete_system():
    """Test complete system configuration"""
    print("🔍 Testing complete system...")
    
    try:
        # Import everything needed for a complete system
        from webcam_ip.server import WebSocketJSONRPCServer
        from webcam_ip.camera import create_camera_monitor, MonitorConfig
        from webcam_ip.utils import setup_logging, LogConfig, GracefulShutdown
        from webcam_ip.camera.models import CameraInfo, CameraStatus
        from webcam_ip.server.methods import ping
        
        # This simulates a complete application setup
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Setup logging
            log_config = LogConfig(log_dir=Path(temp_dir), console_enabled=False)
            setup_logging(log_config)
            
            # 2. Create server
            server = WebSocketJSONRPCServer()
            
            # 3. Create camera monitor
            loop = asyncio.get_event_loop()
            monitor = create_camera_monitor(
                callback=server.broadcast_camera_status,
                loop=loop,
                config=MonitorConfig(enable_capability_detection=False)
            )
            
            # 4. Setup graceful shutdown (without signals)
            shutdown = GracefulShutdown(setup_signals=False)
            
            # 5. Create some test data
            camera = CameraInfo("/dev/video0")
            camera.mark_connected()
            
            # 6. Test method call
            result = await ping()
            assert result == "pong", f"Expected 'pong', got {result}"
            
            print("✅ Complete system configuration working correctly")
            return True
            
    except Exception as e:
        print(f"❌ Complete system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=" * 60)
    print("🔍 FULL INTEGRATION VALIDATION TEST")
    print("=" * 60)
    
    tests = [
        test_server_creation,
        test_camera_monitor_creation,
        test_utils_integration,
        test_cross_component_integration,
        test_complete_system
    ]
    
    passed = 0
    for test in tests:
        if await test():
            passed += 1
        print()
    
    print("=" * 60)
    if passed == len(tests):
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("🚀 Your refactored system is ready!")
    else:
        print(f"⚠️  {len(tests) - passed} tests failed")
        print("🔧 Please fix the failing tests before proceeding")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())