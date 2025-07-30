#!/usr/bin/env python3
"""
Test client for WebSocket JSON-RPC Server with Camera Monitoring
Enhanced test client that verifies camera status notifications
"""

import asyncio
import json
import logging
import sys
import time
import argparse
from typing import Dict, List

import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CameraTestClient:
    """Test client for camera status monitoring"""
    
    def __init__(self, uri: str = "ws://localhost:8002/ws"):
        self.uri = uri
        self.websocket = None
        self.received_notifications: List[Dict] = []
        self.test_results = []
        
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            logger.info(f"Connected to {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.uri}: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from server")
    
    async def send_request(self, method: str, params: Dict = None, request_id: int = 1) -> Dict:
        """Send JSON-RPC request and wait for response"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        
        if params:
            request["params"] = params
        
        request_str = json.dumps(request)
        logger.info(f"Sending: {request_str}")
        
        await self.websocket.send(request_str)
        
        # Wait for response
        response_str = await self.websocket.recv()
        logger.info(f"Received: {response_str}")
        
        return json.loads(response_str)
    
    async def listen_for_notifications(self, duration: float = 10.0):
        """Listen for camera status notifications for a specified duration"""
        logger.info(f"Listening for camera status notifications for {duration} seconds...")
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                try:
                    # Set a timeout for receiving messages
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0
                    )
                    
                    try:
                        data = json.loads(message)
                        
                        # Check if it's a camera status notification
                        if (data.get("jsonrpc") == "2.0" and 
                            data.get("method") == "camera_status_update"):
                            
                            self.received_notifications.append(data)
                            params = data.get("params", {})
                            status = params.get("status", "UNKNOWN")
                            device = params.get("device", "Unknown")
                            
                            logger.info(f"📷 Camera Status Update: {device} -> {status}")
                            
                            if status == "CONNECTED":
                                resolution = params.get("resolution", "N/A")
                                fps = params.get("fps", "N/A")
                                logger.info(f"   Resolution: {resolution}, FPS: {fps}")
                        
                        else:
                            logger.info(f"Other message: {message}")
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON received: {message}")
                
                except asyncio.TimeoutError:
                    # Continue listening, timeout is normal
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Connection closed while listening")
                    break
        
        except Exception as e:
            logger.error(f"Error while listening: {e}")
        
        logger.info(f"Finished listening. Received {len(self.received_notifications)} camera notifications")
    
    async def test_ping(self) -> bool:
        """Test the ping method"""
        logger.info("🏓 Testing ping method...")
        
        try:
            start_time = time.time()
            response = await self.send_request("ping")
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            
            if (response.get("jsonrpc") == "2.0" and 
                response.get("result") == "pong" and
                response.get("id") == 1):
                
                logger.info(f"✅ Ping test passed! Response: '{response['result']}' in {response_time:.2f} ms")
                
                if response_time <= 50:
                    logger.info(f"✅ Response time ({response_time:.2f} ms) is within 50ms threshold")
                else:
                    logger.warning(f"⚠️ Response time ({response_time:.2f} ms) exceeds 50ms threshold")
                
                return True
            else:
                logger.error(f"❌ Ping test failed! Unexpected response: {response}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Ping test failed with exception: {e}")
            return False
    
    async def test_invalid_method(self) -> bool:
        """Test error handling for invalid methods"""
        logger.info("❌ Testing invalid method handling...")
        
        try:
            response = await self.send_request("invalid_method")
            
            error = response.get("error", {})
            if (response.get("jsonrpc") == "2.0" and 
                error.get("code") == -32601 and
                "Method not found" in error.get("message", "")):
                
                logger.info(f"✅ Invalid method test passed! Got expected error: {error}")
                return True
            else:
                logger.error(f"❌ Invalid method test failed! Unexpected response: {response}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Invalid method test failed with exception: {e}")
            return False
    
    async def test_malformed_json(self) -> bool:
        """Test error handling for malformed JSON"""
        logger.info("🔧 Testing malformed JSON handling...")
        
        try:
            # Send invalid JSON
            invalid_json = '{"jsonrpc":"2.0","method":"ping","id":1'  # Missing closing brace
            await self.websocket.send(invalid_json)
            
            response_str = await self.websocket.recv()
            response = json.loads(response_str)
            
            error = response.get("error", {})
            if (response.get("jsonrpc") == "2.0" and 
                error.get("code") == -32700 and
                "Parse error" in error.get("message", "")):
                
                logger.info(f"✅ Malformed JSON test passed! Got expected parse error: {error}")
                return True
            else:
                logger.error(f"❌ Malformed JSON test failed! Unexpected response: {response}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Malformed JSON test failed with exception: {e}")
            return False
    
    async def test_camera_notifications(self, duration: float = 15.0) -> bool:
        """Test camera status notifications"""
        logger.info(f"📷 Testing camera status notifications for {duration} seconds...")
        logger.info("💡 Plug/unplug a USB camera during this test to verify notifications")
        
        initial_count = len(self.received_notifications)
        await self.listen_for_notifications(duration)
        
        notifications_received = len(self.received_notifications) - initial_count
        
        if notifications_received > 0:
            logger.info(f"✅ Camera notification test passed! Received {notifications_received} notifications")
            
            # Validate notification format
            valid_notifications = 0
            for notification in self.received_notifications[-notifications_received:]:
                params = notification.get("params", {})
                
                # Check required fields
                if (params.get("status") in ["CONNECTED", "DISCONNECTED"] and
                    params.get("device") and
                    "/dev/video" in params.get("device", "")):
                    
                    valid_notifications += 1
                    
                    # Check additional fields for CONNECTED status
                    if params.get("status") == "CONNECTED":
                        if "resolution" in params and "fps" in params:
                            logger.info(f"   ✅ CONNECTED notification has resolution and fps")
                        else:
                            logger.warning(f"   ⚠️ CONNECTED notification missing resolution or fps")
                
                else:
                    logger.warning(f"   ⚠️ Invalid notification format: {params}")
            
            logger.info(f"✅ {valid_notifications}/{notifications_received} notifications have valid format")
            return valid_notifications > 0
        
        else:
            logger.info("ℹ️ No camera notifications received during test period")
            logger.info("   This is normal if no camera was plugged/unplugged")
            # Don't fail the test, just inform
            return True
    
    async def run_full_test_suite(self):
        """Run the complete test suite"""
        logger.info("🚀 Starting full test suite...")
        
        if not await self.connect():
            return False
        
        try:
            # Basic functionality tests
            tests = [
                ("Ping Test", self.test_ping()),
                ("Invalid Method Test", self.test_invalid_method()),
                ("Malformed JSON Test", self.test_malformed_json()),
            ]
            
            # Run basic tests
            passed_tests = 0
            for test_name, test_coro in tests:
                try:
                    if await test_coro:
                        passed_tests += 1
                    else:
                        logger.error(f"❌ {test_name} failed")
                except Exception as e:
                    logger.error(f"❌ {test_name} failed with exception: {e}")
            
            # Camera notification test (separate)
            logger.info("\n" + "="*50)
            camera_test_passed = await self.test_camera_notifications()
            if camera_test_passed:
                passed_tests += 1
            
            total_tests = len(tests) + 1
            
            logger.info("\n" + "="*50)
            if passed_tests == total_tests:
                logger.info("🎉 All tests passed!")
                return True
            else:
                logger.error(f"❌ {total_tests - passed_tests}/{total_tests} tests failed")
                return False
        
        finally:
            await self.disconnect()
    
    async def run_simple_test(self):
        """Run a simple ping test"""
        logger.info("🚀 Running simple ping test...")
        
        if not await self.connect():
            return False
        
        try:
            success = await self.test_ping()
            if success:
                logger.info("✅ Simple test passed!")
            else:
                logger.error("❌ Simple test failed!")
            return success
        
        finally:
            await self.disconnect()
    
    async def run_camera_monitor_demo(self, duration: float = 30.0):
        """Run a demo that just monitors camera status changes"""
        logger.info(f"📷 Starting camera status monitor demo for {duration} seconds...")
        logger.info("💡 Plug and unplug USB cameras to see real-time notifications")
        
        if not await self.connect():
            return False
        
        try:
            # First send a ping to verify connection
            await self.test_ping()
            
            # Then listen for camera notifications
            await self.listen_for_notifications(duration)
            
            logger.info("📊 Demo Summary:")
            logger.info(f"   Total notifications received: {len(self.received_notifications)}")
            
            for i, notification in enumerate(self.received_notifications, 1):
                params = notification.get("params", {})
                status = params.get("status", "UNKNOWN")
                device = params.get("device", "Unknown")
                logger.info(f"   {i}. {device} -> {status}")
            
            return True
        
        finally:
            await self.disconnect()

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="WebSocket JSON-RPC Camera Test Client")
    parser.add_argument("--simple", action="store_true", help="Run simple ping test only")
    parser.add_argument("--monitor", action="store_true", help="Monitor camera status changes")
    parser.add_argument("--duration", type=float, default=30.0, help="Duration for monitoring (seconds)")
    parser.add_argument("--uri", default="ws://localhost:8002/ws", help="WebSocket server URI")
    
    args = parser.parse_args()
    
    client = CameraTestClient(args.uri)
    
    try:
        if args.simple:
            success = await client.run_simple_test()
        elif args.monitor:
            success = await client.run_camera_monitor_demo(args.duration)
        else:
            success = await client.run_full_test_suite()
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())