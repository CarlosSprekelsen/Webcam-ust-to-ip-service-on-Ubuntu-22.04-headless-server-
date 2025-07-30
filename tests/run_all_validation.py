#!/usr/bin/env python3
"""
Master Validation Script
Runs all validation tests in the correct order
"""

import sys
import asyncio
import importlib.util
from pathlib import Path

def run_test_module(module_path, test_name):
    """Dynamically import and run a test module"""
    print(f"\n{'='*60}")
    print(f"🔍 Running {test_name}")
    print(f"{'='*60}")
    
    if not Path(module_path).exists():
        print(f"❌ Test file not found: {module_path}")
        return False
    
    try:
        # Import the module
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(module)
        
        # Run main function if it exists
        if hasattr(module, 'main'):
            if asyncio.iscoroutinefunction(module.main):
                result = asyncio.run(module.main())
            else:
                result = module.main()
            return True  # Assume success if no exception
        else:
            print("✅ Module imported successfully (no main function)")
            return True
            
    except SystemExit as e:
        # Handle sys.exit() calls
        return e.code == 0
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 COMPLETE SYSTEM VALIDATION")
    print("Testing refactored webcam_ip system")
    print(f"Python version: {sys.version}")
    print()
    
    # Define test order and descriptions
    tests = [
        ("validate_config.py", "Configuration Validation"),
        ("test_imports.py", "Import Tests"),
        ("test_jsonrpc.py", "JSON-RPC Handler Tests"),
        ("test_camera_models.py", "Camera Models Tests"),
        ("test_logging.py", "Logging System Tests"),
        ("test_integration.py", "Full Integration Tests"),
    ]
    
    # Track results
    results = []
    
    for test_file, test_name in tests:
        success = run_test_module(test_file, test_name)
        results.append((test_name, success))
        
        if not success:
            print(f"\n❌ {test_name} FAILED - Consider fixing before proceeding")
        else:
            print(f"\n✅ {test_name} PASSED")
    
    # Summary
    print(f"\n{'='*80}")
    print("📋 VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("🚀 Your refactored system is ready for deployment!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt") 
        print("2. Install system dependencies: sudo apt-get install v4l-utils")
        print("3. Test on your Linux server: python -m webcam_ip.server.websocket_server")
        return True
    else:
        print(f"\n⚠️  {total - passed} validations failed")
        print("🔧 Please fix the failing tests before deployment")
        print("\nCommon fixes:")
        print("- Copy missing module files from our artifacts")
        print("- Install missing dependencies: pip install websockets psutil")
        print("- Check file permissions and paths")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)