#!/usr/bin/env python3
"""
Import Validation Test
Tests that all modules can be imported correctly after refactoring
"""

def test_basic_imports():
    """Test basic module imports"""
    print("🔍 Testing basic imports...")
    
    try:
        from webcam_ip.server import WebSocketJSONRPCServer, JSONRPCHandler
        print('✅ Server module imports OK')
    except Exception as e:
        print(f'❌ Server module import failed: {e}')
        return False
    
    try:
        from webcam_ip.camera import CameraMonitor, CameraInfo, CameraStatus
        print('✅ Camera module imports OK')
    except Exception as e:
        print(f'❌ Camera module import failed: {e}')
        return False
    
    try:
        from webcam_ip.utils import setup_logging, GracefulShutdown
        print('✅ Utils module imports OK')
    except Exception as e:
        print(f'❌ Utils module import failed: {e}')
        return False
    
    try:
        import webcam_ip
        print(f'✅ Main package import OK - version: {webcam_ip.__version__}')
    except Exception as e:
        print(f'❌ Main package import failed: {e}')
        return False
    
    return True

def test_cross_module_imports():
    """Test internal cross-module imports"""
    print("🔍 Testing cross-module imports...")
    
    try:
        from webcam_ip.server.methods import ping, get_server_info
        from webcam_ip.camera.models import CameraCapabilities
        from webcam_ip.utils.logging import LogConfig
        print('✅ Cross-module imports OK')
        return True
    except Exception as e:
        print(f'❌ Cross-module imports failed: {e}')
        return False

def test_dependencies():
    """Test required dependencies are available"""
    print("🔍 Testing Python dependencies...")
    
    required_modules = [
        'websockets',
        'psutil', 
        'asyncio',
        'json',
        'logging',
        'threading',
        'subprocess',
        'dataclasses',
        'typing',
        'pathlib',
        'enum'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f'✅ {module}')
        except ImportError:
            missing.append(module)
            print(f'❌ {module} - MISSING')
    
    if missing:
        print(f'\n🚨 Missing dependencies: {missing}')
        print('Install with: pip install ' + ' '.join([m for m in missing if m not in ['asyncio', 'json', 'logging', 'threading', 'subprocess', 'dataclasses', 'typing', 'pathlib', 'enum']]))
        return False
    else:
        print('\n✅ All Python dependencies satisfied')
        return True

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 IMPORT VALIDATION TEST")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_cross_module_imports,
        test_dependencies
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    if passed == len(tests):
        print("🎉 ALL IMPORT TESTS PASSED!")
    else:
        print(f"⚠️  {len(tests) - passed} tests failed")
    print("=" * 50)