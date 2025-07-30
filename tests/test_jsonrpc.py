#!/usr/bin/env python3
"""
JSON-RPC Handler Validation Test
Tests the core JSON-RPC functionality
"""

import asyncio
import json

async def test_jsonrpc_basic():
    """Test basic JSON-RPC handler functionality"""
    print("🔍 Testing JSON-RPC Handler...")
    
    try:
        from webcam_ip.server.jsonrpc_handler import JSONRPCHandler
        
        handler = JSONRPCHandler()
        
        # Register test method
        @handler.method()
        def test_ping():
            return "pong"
        
        # Test valid request
        request = '{"jsonrpc":"2.0","method":"test_ping","id":1}'
        response = await handler.handle_request(request)
        response_data = json.loads(response)
        
        if response_data.get("result") == "pong" and response_data.get("id") == 1:
            print("✅ Basic JSON-RPC request/response working")
        else:
            print(f"❌ JSON-RPC response incorrect: {response}")
            return False
        
        # Test notification (no response expected)
        notification = '{"jsonrpc":"2.0","method":"test_ping"}'
        response = await handler.handle_request(notification)
        
        if response is None:
            print("✅ JSON-RPC notifications working")
        else:
            print(f"❌ Notification should return None, got: {response}")
            return False
        
        # Test error handling
        error_request = '{"jsonrpc":"2.0","method":"nonexistent","id":2}'
        response = await handler.handle_request(error_request)
        response_data = json.loads(response)
        
        if "error" in response_data and response_data["error"]["code"] == -32601:
            print("✅ Error handling working")
        else:
            print(f"❌ Error handling failed: {response}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ JSON-RPC handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_method_registration():
    """Test method registration system"""
    print("🔍 Testing method registration...")
    
    try:
        from webcam_ip.server.jsonrpc_handler import JSONRPCHandler
        from webcam_ip.server.methods import register_all_methods
        
        handler = JSONRPCHandler()
        register_all_methods(handler)
        
        methods = handler.get_method_list()
        expected_methods = ["ping", "get_server_info", "get_camera_list", "echo", "get_supported_methods"]
        
        missing_methods = []
        for method in expected_methods:
            if method not in methods:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing methods: {missing_methods}")
            return False
        
        print(f"✅ All expected methods registered: {methods}")
        
        # Test ping method specifically
        request = '{"jsonrpc":"2.0","method":"ping","id":1}'
        response = await handler.handle_request(request)
        response_data = json.loads(response)
        
        if response_data.get("result") == "pong":
            print("✅ Ping method working correctly")
            return True
        else:
            print(f"❌ Ping method failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Method registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=" * 50)
    print("🔍 JSON-RPC VALIDATION TEST")
    print("=" * 50)
    
    tests = [
        test_jsonrpc_basic,
        test_method_registration
    ]
    
    passed = 0
    for test in tests:
        if await test():
            passed += 1
        print()
    
    print("=" * 50)
    if passed == len(tests):
        print("🎉 ALL JSON-RPC TESTS PASSED!")
    else:
        print(f"⚠️  {len(tests) - passed} tests failed")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())