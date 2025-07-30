"""
JSON-RPC 2.0 Handler

Provides a clean, efficient JSON-RPC 2.0 implementation without external dependencies.
Handles method registration, request processing, and error management.
"""

import json
import logging
import inspect
import asyncio
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class JSONRPCError:
    """Standard JSON-RPC 2.0 error codes and messages"""
    PARSE_ERROR = (-32700, "Parse error")
    INVALID_REQUEST = (-32600, "Invalid Request") 
    METHOD_NOT_FOUND = (-32601, "Method not found")
    INVALID_PARAMS = (-32602, "Invalid params")
    INTERNAL_ERROR = (-32603, "Internal error")

class JSONRPCHandler:
    """
    Streamlined JSON-RPC 2.0 handler without external dependencies
    
    Features:
    - Method registration via decorator or direct registration
    - Support for both sync and async methods
    - Proper error handling with standard error codes
    - Notification support (methods without id)
    - Batch request support
    - Request/response logging
    """
    
    def __init__(self):
        self.methods: Dict[str, Callable] = {}
        self._request_id_counter = 0
    
    def register_method(self, name: str, func: Callable):
        """Register a method for JSON-RPC calls"""
        self.methods[name] = func
        logger.debug(f"Registered JSON-RPC method: {name}")
    
    def method(self, name: Optional[str] = None):
        """Decorator to register methods"""
        def decorator(func: Callable):
            method_name = name or func.__name__
            self.register_method(method_name, func)
            return func
        return decorator
    
    async def handle_request(self, message: str) -> Optional[str]:
        """
        Handle a JSON-RPC request and return response as string
        
        Args:
            message: JSON-RPC request string
            
        Returns:
            JSON-RPC response string, or None for notifications
        """
        logger.debug(f"Handling JSON-RPC request: {message}")
        
        try:
            request = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return self._create_error_response(None, *JSONRPCError.PARSE_ERROR)
        
        # Handle batch requests (list of requests)
        if isinstance(request, list):
            if not request:  # Empty array
                return self._create_error_response(None, *JSONRPCError.INVALID_REQUEST)
            
            responses = []
            for req in request:
                response = await self._handle_single_request(req)
                if response:  # Don't include responses for notifications
                    responses.append(response)
            
            # Return batch response or None if all were notifications
            return json.dumps(responses) if responses else None
        
        # Handle single request
        response = await self._handle_single_request(request)
        return json.dumps(response) if response else None
    
    async def _handle_single_request(self, request: Any) -> Optional[Dict]:
        """Handle a single JSON-RPC request"""
        # Validate request format
        if not isinstance(request, dict):
            return self._create_error_response(None, *JSONRPCError.INVALID_REQUEST)
        
        jsonrpc = request.get("jsonrpc")
        method_name = request.get("method") 
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Validate JSON-RPC 2.0 format
        if jsonrpc != "2.0":
            return self._create_error_response(request_id, *JSONRPCError.INVALID_REQUEST)
        
        if not isinstance(method_name, str):
            return self._create_error_response(request_id, *JSONRPCError.INVALID_REQUEST)
        
        # Check if it's a notification (no id field)
        is_notification = "id" not in request
        
        logger.debug(f"Processing method: {method_name}, params: {params}, notification: {is_notification}")
        
        # Find and call method
        if method_name not in self.methods:
            logger.warning(f"Method not found: {method_name}")
            if is_notification:
                return None  # Don't respond to notification errors
            return self._create_error_response(request_id, *JSONRPCError.METHOD_NOT_FOUND)
        
        try:
            method = self.methods[method_name]
            
            # Call method with appropriate parameters
            result = await self._call_method_with_params(method, params)
            
            # Don't respond to notifications
            if is_notification:
                logger.debug(f"Notification {method_name} processed successfully")
                return None
            
            logger.debug(f"Method {method_name} returned: {result}")
            return self._create_success_response(request_id, result)
            
        except TypeError as e:
            # Invalid parameters
            logger.error(f"Invalid parameters for {method_name}: {e}")
            if is_notification:
                return None
            return self._create_error_response(request_id, *JSONRPCError.INVALID_PARAMS)
            
        except Exception as e:
            # Internal error
            logger.error(f"Error calling {method_name}: {e}", exc_info=True)
            if is_notification:
                return None
            return self._create_error_response(request_id, *JSONRPCError.INTERNAL_ERROR)
    
    async def _call_method_with_params(self, method: Callable, params: Any):
        """Call a method with proper parameter handling"""
        try:
            # Handle different parameter formats
            if isinstance(params, dict):
                # Named parameters
                result = await self._call_method(method, **params)
            elif isinstance(params, list):
                # Positional parameters
                result = await self._call_method(method, *params)
            elif params is None:
                # No parameters
                result = await self._call_method(method)
            else:
                # Invalid parameter format
                raise TypeError(f"Invalid parameter type: {type(params)}")
            
            return result
            
        except TypeError as e:
            # Re-raise parameter errors
            raise
        except Exception as e:
            # Wrap other exceptions as internal errors
            raise RuntimeError(f"Method execution failed: {e}") from e
    
    async def _call_method(self, method: Callable, *args, **kwargs):
        """Call a method, handling both sync and async functions"""
        if inspect.iscoroutinefunction(method):
            return await method(*args, **kwargs)
        else:
            # Run sync function in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: method(*args, **kwargs))
    
    def create_notification(self, method: str, params: Any = None) -> str:
        """Create a JSON-RPC notification (no response expected)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            notification["params"] = params
        
        return json.dumps(notification)
    
    def create_request(self, method: str, params: Any = None, request_id: Optional[int] = None) -> str:
        """Create a JSON-RPC request"""
        if request_id is None:
            self._request_id_counter += 1
            request_id = self._request_id_counter
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        if params is not None:
            request["params"] = params
        
        return json.dumps(request)
    
    @staticmethod
    def _create_success_response(request_id: Any, result: Any) -> Dict:
        """Create a successful JSON-RPC response"""
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
    
    @staticmethod  
    def _create_error_response(request_id: Any, code: int, message: str) -> str:
        """Create a JSON-RPC error response as JSON string"""
        error_response = {
            "jsonrpc": "2.0", 
            "error": {"code": code, "message": message},
            "id": request_id
        }
        return json.dumps(error_response)
    
    def get_method_list(self) -> list:
        """Get list of registered methods"""
        return list(self.methods.keys())
    
    def has_method(self, method_name: str) -> bool:
        """Check if a method is registered"""
        return method_name in self.methods
    
    def unregister_method(self, method_name: str) -> bool:
        """Unregister a method"""
        if method_name in self.methods:
            del self.methods[method_name]
            logger.debug(f"Unregistered JSON-RPC method: {method_name}")
            return True
        return False