# test_logging.py
import logging
import json
from pathlib import Path
from webcam_ip.utils import setup_logging, LogConfig, get_logger

def test_basic_logging():
    """Test basic logging setup"""
    print("🔍 Testing basic logging...")
    
    # Development logging
    config = LogConfig(
        level="DEBUG",
        console_enabled=True,
        file_enabled=False,
        json_format=False
    )
    
    loggers = setup_logging(config)
    logger = get_logger(__name__)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message") 
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    print("✅ Basic logging test completed")

def test_json_logging():
    """Test JSON structured logging"""
    print("🔍 Testing JSON logging...")
    
    config = LogConfig(
        level="INFO",
        console_enabled=True,
        file_enabled=True,
        json_format=True,
        log_dir=Path("./test_logs")
    )
    
    loggers = setup_logging(config)
    logger = get_logger(__name__, structured=True)
    
    # Test structured logging
    logger.info("User login", user_id=123, ip_address="192.168.1.1")
    logger.error("Database error", error_code="DB001", query="SELECT * FROM users")
    
    # Test with context
    logger.set_context(component="authentication", request_id="req-123")
    logger.info("Authentication successful")
    logger.warning("Rate limit exceeded", attempts=5)
    
    print("✅ JSON logging test completed")
    print("📁 Check ./test_logs/server.log for JSON output")

def test_exception_logging():
    """Test exception logging with traceback"""
    print("🔍 Testing exception logging...")
    
    logger = get_logger(__name__, structured=True)
    
    try:
        1 / 0  # Trigger exception
    except Exception:
        logger.exception("Division by zero error", operation="divide", values=[1, 0])
    
    print("✅ Exception logging test completed")

if __name__ == "__main__":
    test_basic_logging()
    print()
    test_json_logging() 
    print()
    test_exception_logging()