#!/usr/bin/env python3
"""
Test client for WebSocket JSON-RPC Server
Tests the ping method and measures response time
"""

import asyncio
import json
import time
import logging
import sys

import websockets


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Server connection details
SERVER_URI = "ws://localhost:8002/ws"


class WebSocketJSONRPCClient:
    """Test client for WebSocket JSON-RPC server"""
    
    def __init__(self, uri: str = SERVER_URI):
        self.uri = uri
        self.websocket = None
    
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            logger.info(f"Connecting to {self.uri}")
            self.websocket = await websockets.connect(self.uri)
            logger.info("Connected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("Disconnected")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    async def send_jsonrpc_request(self, method: str, params=None, request_id=1):
        """Send a JSON-RPC 2.0 request and return the response"""
        if not self.websocket:
            raise Exception("Not connected to server")
        
        # Build JSON-RPC 2.0 request
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        
        if params is not None:
            request["params"] = params
        
        # Send request
        request_json = json.dumps(request)
        logger.info(f"Sending: {request_json}")
        
        start_time = time.time()
        await self.websocket.send(request_json)
        
        # Wait for response
        response_json = await self.websocket.recv()
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        logger.info(f"Received: {response_json}")
        logger.info(f"Response time: {response_time_ms:.2f} ms")
        
        # Parse response
        try:
            response = json.loads(response_json)
            return response, response_time_ms
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {e}")
            return None, response_time_ms
    
    async def test_ping(self):
        """Test the ping method"""
        logger.info("Testing ping method...")
        
        try:
            response, response_time = await self.send_jsonrpc_request("ping")
            
            if not response:
                logger.error("Failed to parse response")
                return False
            
            # Validate response
            if response.get("jsonrpc") != "2.0":
                logger.error(f"Invalid jsonrpc version: {response.get('jsonrpc')}")
                return False
            
            if response.get("id") != 1:
                logger.error(f"Invalid id: {response.get('id')}")
                return False
            
            if "error" in response:
                logger.error(f"Server returned error: {response['error']}")
                return False
            
            if response.get("result") != "pong":
                logger.error(f"Unexpected result: {response.get('result')}")
                return False
            
            logger.info(f"✅ Ping test passed! Response: '{response['result']}' in {response_time:.2f} ms")
            
            # Check if response time is within acceptable limit (50ms as per requirements)
            if response_time > 50:
                logger.warning(f"⚠️  Response time ({response_time:.2f} ms) exceeds 50ms threshold")
            else:
                logger.info(f"✅ Response time ({response_time:.2f} ms) is within 50ms threshold")
            
            return True
            
        except Exception as e:
            logger.error(f"Ping test failed: {e}")
            return False
    
    async def test_invalid_method(self):
        """Test calling a non-existent method"""
        logger.info("Testing invalid method...")
        
        try:
            response, response_time = await self.send_jsonrpc_request("invalid_method", request_id=2)
            
            if not response:
                logger.error("Failed to parse response")
                return False
            
            # Should return method not found error
            if "error" not in response:
                logger.error("Expected error response for invalid method")
                return False
            
            error = response["error"]
            if error.get("code") != -32601:
                logger.error(f"Expected error code -32601, got {error.get('code')}")
                return False
            
            logger.info(f"✅ Invalid method test passed! Got expected error: {error}")
            return True
            
        except Exception as e:
            logger.error(f"Invalid method test failed: {e}")
            return False
    
    async def test_malformed_json(self):
        """Test sending malformed JSON"""
        logger.info("Testing malformed JSON...")
        
        if not self.websocket:
            raise Exception("Not connected to server")
        
        try:
            # Send invalid JSON
            malformed_json = '{"jsonrpc":"2.0","method":"ping","id":3'  # Missing closing brace
            logger.info(f"Sending malformed JSON: {malformed_json}")
            
            start_time = time.time()
            await self.websocket.send(malformed_json)
            
            # Wait for response
            response_json = await self.websocket.recv()
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            logger.info(f"Received: {response_json}")
            
            # Parse response
            response = json.loads(response_json)
            
            # Should return parse error
            if "error" not in response:
                logger.error("Expected error response for malformed JSON")
                return False
            
            error = response["error"]
            if error.get("code") != -32700:
                logger.error(f"Expected error code -32700, got {error.get('code')}")
                return False
            
            logger.info(f"✅ Malformed JSON test passed! Got expected parse error: {error}")
            return True
            
        except Exception as e:
            logger.error(f"Malformed JSON test failed: {e}")
            return False


async def run_tests():
    """Run all tests"""
    client = WebSocketJSONRPCClient()
    
    # Connect to server
    if not await client.connect():
        logger.error("Failed to connect to server. Make sure the server is running.")
        return False
    
    try:
        # Run tests
        tests = [
            ("Ping Test", client.test_ping),
            ("Invalid Method Test", client.test_invalid_method),
            ("Malformed JSON Test", client.test_malformed_json),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                if await test_func():
                    passed_tests += 1
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    logger.error(f"❌ {test_name} FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name} FAILED with exception: {e}")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info(f"TEST SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed!")
            return True
        else:
            logger.error(f"❌ {total_tests - passed_tests} test(s) failed")
            return False
    
    finally:
        await client.disconnect()


async def simple_ping_test():
    """Simple ping test for quick verification"""
    client = WebSocketJSONRPCClient()
    
    if not await client.connect():
        logger.error("Failed to connect to server")
        return False
    
    try:
        success = await client.test_ping()
        return success
    finally:
        await client.disconnect()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        # Run simple ping test only
        success = asyncio.run(simple_ping_test())
        sys.exit(0 if success else 1)
    else:
        # Run full test suite
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)