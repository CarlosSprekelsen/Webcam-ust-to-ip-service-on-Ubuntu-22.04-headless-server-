#!/usr/bin/env python3
"""
Logging Configuration Validation Test
Tests the logging system functionality
"""

import tempfile
import os
from pathlib import Path

def test_log_config():
    """Test LogConfig creation and validation"""
    print("🔍 Testing LogConfig...")
    
    try:
        from webcam_ip.utils.logging import LogConfig
        
        # Test basic config
        config = LogConfig(
            level="INFO",
            console_enabled=True,
            file_enabled=False,
            json_format=False
        )
        
        assert config.log_level == 20, f"Expected log level 20 (INFO), got {config.log_level}"  # INFO = 20
        assert config.console_enabled == True, "Console should be enabled"
        assert config.file_enabled == False, "File logging should be disabled"
        
        # Test file size parsing
        config_with_size = LogConfig(max_file_size="50MB")
        expected_bytes = 50 * 1024 * 1024
        assert config_with_size.max_file_size_bytes == expected_bytes, f"Expected {expected_bytes} bytes, got {config_with_size.max_file_size_bytes}"
        
        print("✅ LogConfig working correctly")
        return True
        
    except Exception as e:
        print(f"❌ LogConfig test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_logging_setup():
    """Test logging setup and file creation"""
    print("🔍 Testing logging setup...")
    
    try:
        from webcam_ip.utils.logging import LogConfig, setup_logging, get_logger
        
        # Create temporary directory for logs
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LogConfig(
                level="INFO",
                log_dir=Path(temp_dir),
                console_enabled=False,  # Disable console for clean test output
                file_enabled=True,
                json_format=False
            )
            
            # Setup logging
            loggers = setup_logging(config)
            assert isinstance(loggers, dict), "setup_logging should return dict of loggers"
            
            # Get a logger and test it
            logger = get_logger("test_logger")
            logger.info("Test log message")
            
            # Check log file was created
            log_file = Path(temp_dir) / "server.log"
            assert log_file.exists(), f"Log file should be created at {log_file}"
            
            # Check log file has content
            log_content = log_file.read_text()
            assert "Test log message" in log_content, "Log message should be in file"
            
            print("✅ Logging setup working correctly")
            return True
            
    except Exception as e:
        print(f"❌ Logging setup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_structured_logging():
    """Test structured logging functionality"""
    print("🔍 Testing structured logging...")
    
    try:
        from webcam_ip.utils.logging import LogConfig, setup_logging, get_logger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LogConfig(
                level="INFO",
                log_dir=Path(temp_dir),
                console_enabled=False,
                file_enabled=True,
                json_format=True  # Enable JSON format
            )
            
            setup_logging(config)
            
            # Test structured logger
            logger = get_logger("test_structured", structured=True)
            logger.set_context(component="test", request_id="req-123")
            logger.info("Structured log message", user_id=456, action="test")
            
            # Check JSON log file
            log_file = Path(temp_dir) / "server.log"
            assert log_file.exists(), "JSON log file should be created"
            
            log_content = log_file.read_text()
            assert "request_id" in log_content, "Request ID should be in JSON log"
            assert "user_id" in log_content, "User ID should be in JSON log"
            
            print("✅ Structured logging working correctly")
            return True
            
    except Exception as e:
        print(f"❌ Structured logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_json_formatter():
    """Test JSON formatter"""
    print("🔍 Testing JSON formatter...")
    
    try:
        from webcam_ip.utils.logging import JsonFormatter
        import logging
        import json
        
        # Create formatter
        formatter = JsonFormatter()
        
        # Create log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format record
        formatted = formatter.format(record)
        
        # Parse as JSON
        log_data = json.loads(formatted)
        
        # Verify structure
        required_fields = ["timestamp", "level", "logger", "message", "module", "function", "line"]
        for field in required_fields:
            assert field in log_data, f"Missing field {field} in JSON log"
        
        assert log_data["level"] == "INFO", f"Expected level INFO, got {log_data['level']}"
        assert log_data["message"] == "Test message", f"Expected 'Test message', got {log_data['message']}"
        
        print("✅ JSON formatter working correctly")
        return True
        
    except Exception as e:
        print(f"❌ JSON formatter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 50)
    print("🔍 LOGGING VALIDATION TEST")
    print("=" * 50)
    
    tests = [
        test_log_config,
        test_logging_setup,
        test_structured_logging,
        test_json_formatter
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    if passed == len(tests):
        print("🎉 ALL LOGGING TESTS PASSED!")
    else:
        print(f"⚠️  {len(tests) - passed} tests failed")
    print("=" * 50)

if __name__ == "__main__":
    main()