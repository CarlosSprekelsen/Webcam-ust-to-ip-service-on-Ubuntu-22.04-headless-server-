# test_production_config.py
from pathlib import Path
from webcam_ip.utils import setup_production_logging, LogConfig

def test_production_logging():
    """Test production logging configuration"""
    print("🔍 Testing production logging setup...")
    
    # Production config
    loggers = setup_production_logging(
        log_dir="/tmp/webcam_logs",
        level="INFO", 
        json_format=True
    )
    
    # Test various loggers
    server_logger = loggers['webcam_ip.server']
    camera_logger = loggers['webcam_ip.camera']
    
    server_logger.info("Server started on port 8002")
    camera_logger.info("Camera monitoring enabled")
    
    print("✅ Production logging test completed")
    print("📁 Check /tmp/webcam_logs/server.log for JSON logs")

def test_custom_config():
    """Test custom logging configuration"""
    print("🔍 Testing custom logging configuration...")
    
    config = LogConfig(
        level="DEBUG",
        log_dir=Path("./custom_logs"),
        console_enabled=True,
        file_enabled=True,
        json_format=True,
        max_file_size="5MB",
        backup_count=3
    )
    
    from webcam_ip.utils import setup_logging
    loggers = setup_logging(config)
    
    logger = loggers['webcam_ip']
    logger.info("Custom configuration test")
    
    print("✅ Custom configuration test completed")

if __name__ == "__main__":
    test_production_logging()
    print()
    test_custom_config()