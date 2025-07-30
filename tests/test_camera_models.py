#!/usr/bin/env python3
"""
Camera Models Validation Test
Tests the camera data models and their functionality
"""

def test_camera_capabilities():
    """Test CameraCapabilities model"""
    print("🔍 Testing CameraCapabilities...")
    
    try:
        from webcam_ip.camera.models import CameraCapabilities
        
        # Test basic creation
        caps = CameraCapabilities(
            resolution="1920x1080", 
            fps=30, 
            formats=["YUYV", "MJPG"]
        )
        
        # Test properties
        assert caps.width == 1920, f"Expected width 1920, got {caps.width}"
        assert caps.height == 1080, f"Expected height 1080, got {caps.height}"
        assert caps.fps == 30, f"Expected fps 30, got {caps.fps}"
        assert "YUYV" in caps.formats, f"Expected YUYV in formats, got {caps.formats}"
        
        # Test serialization
        caps_dict = caps.to_dict()
        required_keys = ["resolution", "width", "height", "fps", "formats"]
        for key in required_keys:
            assert key in caps_dict, f"Missing key {key} in serialized data"
        
        print("✅ CameraCapabilities working correctly")
        return True
        
    except Exception as e:
        print(f"❌ CameraCapabilities test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_camera_info():
    """Test CameraInfo model"""
    print("🔍 Testing CameraInfo...")
    
    try:
        from webcam_ip.camera.models import CameraInfo, CameraCapabilities, CameraStatus
        
        # Test basic creation
        camera = CameraInfo("/dev/video0")
        assert camera.device == "/dev/video0", f"Expected device /dev/video0, got {camera.device}"
        assert camera.device_number == 0, f"Expected device number 0, got {camera.device_number}"
        
        # Test status transitions
        caps = CameraCapabilities(resolution="640x480", fps=30)
        camera.mark_connected(caps)
        
        assert camera.connected == True, "Camera should be connected"
        assert camera.status == CameraStatus.CONNECTED, f"Expected CONNECTED status, got {camera.status}"
        assert camera.capabilities is not None, "Capabilities should be set"
        assert camera.connected_at is not None, "Connected timestamp should be set"
        
        # Test serialization when connected
        camera_dict = camera.to_dict()
        required_keys = ["device", "status", "resolution", "fps"]
        for key in required_keys:
            assert key in camera_dict, f"Missing key {key} in connected camera dict"
        
        assert camera_dict["status"] == "CONNECTED", f"Expected CONNECTED status in dict, got {camera_dict['status']}"
        
        # Test disconnection
        camera.mark_disconnected()
        assert camera.connected == False, "Camera should be disconnected"
        assert camera.status == CameraStatus.DISCONNECTED, f"Expected DISCONNECTED status, got {camera.status}"
        assert camera.disconnected_at is not None, "Disconnected timestamp should be set"
        
        # Test error state
        camera.mark_error("Test error")
        assert camera.status == CameraStatus.ERROR, f"Expected ERROR status, got {camera.status}"
        assert camera.error_message == "Test error", f"Expected error message 'Test error', got {camera.error_message}"
        
        print("✅ CameraInfo working correctly")
        return True
        
    except Exception as e:
        print(f"❌ CameraInfo test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_camera_registry():
    """Test CameraRegistry functionality"""
    print("🔍 Testing CameraRegistry...")
    
    try:
        from webcam_ip.camera.models import CameraInfo, CameraRegistry, CameraStatus
        
        registry = CameraRegistry()
        
        # Test adding cameras
        camera1 = CameraInfo("/dev/video0")
        camera1.mark_connected()
        registry.add_camera(camera1)
        
        camera2 = CameraInfo("/dev/video1")
        camera2.mark_disconnected()
        registry.add_camera(camera2)
        
        # Test retrieval
        all_cameras = registry.get_all_cameras()
        assert len(all_cameras) == 2, f"Expected 2 cameras, got {len(all_cameras)}"
        
        connected_cameras = registry.get_connected_cameras()
        assert len(connected_cameras) == 1, f"Expected 1 connected camera, got {len(connected_cameras)}"
        
        # Test counts
        counts = registry.get_camera_count()
        assert counts["CONNECTED"] == 1, f"Expected 1 connected, got {counts['CONNECTED']}"
        assert counts["DISCONNECTED"] == 1, f"Expected 1 disconnected, got {counts['DISCONNECTED']}"
        
        # Test removal
        removed = registry.remove_camera("/dev/video0")
        assert removed == True, "Camera removal should return True"
        
        remaining = registry.get_all_cameras()
        assert len(remaining) == 1, f"Expected 1 camera after removal, got {len(remaining)}"
        
        print("✅ CameraRegistry working correctly")
        return True
        
    except Exception as e:
        print(f"❌ CameraRegistry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_camera_status_enum():
    """Test CameraStatus enum values"""
    print("🔍 Testing CameraStatus Enum...")
    try:
        from webcam_ip.camera.models import CameraStatus
        assert CameraStatus.CONNECTED.value == "CONNECTED"
        assert CameraStatus.DISCONNECTED.value == "DISCONNECTED"
        assert CameraStatus.ERROR.value == "ERROR"
        assert CameraStatus.UNKNOWN.value == "UNKNOWN"
        print("✅ CameraStatus Enum working correctly")
        return True
    except Exception as e:
        print(f"❌ CameraStatus Enum test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_camera_event():
    """Test CameraEvent dataclass"""
    print("🔍 Testing CameraEvent...")
    try:
        from webcam_ip.camera.models import CameraEvent, CameraStatus, CameraCapabilities
        event = CameraEvent(
            device="/dev/video0",
            event_type="connected",
            old_status=CameraStatus.DISCONNECTED,
            new_status=CameraStatus.CONNECTED,
            capabilities=CameraCapabilities(resolution="1280x720", fps=25, formats=["YUYV"]),
            error_message=None,
            metadata={"note": "Test event"}
        )
        event_dict = event.to_dict()
        assert event_dict["device"] == "/dev/video0"
        assert event_dict["event_type"] == "connected"
        assert event_dict["old_status"] == "DISCONNECTED"
        assert event_dict["new_status"] == "CONNECTED"
        assert "capabilities" in event_dict
        assert event_dict["metadata"]["note"] == "Test event"
        print("✅ CameraEvent working correctly")
        return True
    except Exception as e:
        print(f"❌ CameraEvent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 50)
    print("🔍 CAMERA MODELS VALIDATION TEST")
    print("=" * 50)
    
    tests = [
        test_camera_capabilities,
        test_camera_info,
        test_camera_registry,
        test_camera_status_enum,   
        test_camera_event          
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    if passed == len(tests):
        print("🎉 ALL CAMERA MODEL TESTS PASSED!")
    else:
        print(f"⚠️  {len(tests) - passed} tests failed")
    print("=" * 50)

if __name__ == "__main__":
    main()