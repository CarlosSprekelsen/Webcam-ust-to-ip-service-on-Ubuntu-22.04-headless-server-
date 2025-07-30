#!/usr/bin/env python3
"""
Configuration Validation Script
Validates that configuration files are properly structured
"""

import os
from pathlib import Path

def validate_file_structure():
    """Validate that all required files exist"""
    print("🔍 Validating file structure...")
    
    required_files = {
        # Main package
        "webcam_ip/__init__.py": "Main package initialization",
        "webcam_ip/config.py": "Configuration module",
        
        # Server module
        "webcam_ip/server/__init__.py": "Server package initialization",
        "webcam_ip/server/websocket_server.py": "WebSocket server implementation",
        "webcam_ip/server/jsonrpc_handler.py": "JSON-RPC handler",
        "webcam_ip/server/methods.py": "RPC method implementations",
        
        # Camera module
        "webcam_ip/camera/__init__.py": "Camera package initialization",
        "webcam_ip/camera/models.py": "Camera data models",
        "webcam_ip/camera/detector.py": "Camera capability detection",
        "webcam_ip/camera/monitor.py": "Camera monitoring logic",
        
        # Utils module
        "webcam_ip/utils/__init__.py": "Utils package initialization",
        "webcam_ip/utils/logging.py": "Logging configuration",
        "webcam_ip/utils/signals.py": "Signal handling",
        
        # Configuration
        "config/config.yaml": "Main configuration file",
        ".env.example": "Environment variables example",
        
        # Dependencies
        "requirements.txt": "Python dependencies",
        "setup.py": "Package setup configuration",
    }
    
    missing_files = []
    empty_files = []
    
    for file_path, description in required_files.items():
        if not os.path.exists(file_path):
            missing_files.append((file_path, description))
        else:
            # Check if Python files are empty (should have content)
            if file_path.endswith('.py'):
                file_size = os.path.getsize(file_path)
                if file_size < 50:  # Less than 50 bytes is likely empty
                    empty_files.append((file_path, description))
    
    # Report results
    if missing_files:
        print("❌ Missing files:")
        for file_path, description in missing_files:
            print(f"   - {file_path} ({description})")
    
    if empty_files:
        print("⚠️  Possibly empty files:")
        for file_path, description in empty_files:
            file_size = os.path.getsize(file_path)
            print(f"   - {file_path} ({file_size} bytes) ({description})")
    
    if not missing_files and not empty_files:
        print("✅ All required files present and non-empty")
        return True
    else:
        print(f"❌ Found {len(missing_files)} missing and {len(empty_files)} possibly empty files")
        return False

def validate_config_yaml():
    """Validate YAML configuration file"""
    print("🔍 Validating config.yaml...")
    
    config_path = "config/config.yaml"
    
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        return False
    
    try:
        # Try to import yaml
        try:
            import yaml
        except ImportError:
            print("⚠️  PyYAML not available, skipping YAML validation")
            print("   Install with: pip install PyYAML")
            return True  # Not a failure, just skip
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate structure
        required_sections = ['server', 'camera', 'logging']
        missing_sections = []
        
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"❌ Missing configuration sections: {missing_sections}")
            return False
        
        # Validate server section
        server_config = config.get('server', {})
        if 'port' not in server_config:
            print("❌ Missing server.port in configuration")
            return False
        
        print("✅ Configuration file is valid")
        print(f"   - Server port: {server_config.get('port', 'not set')}")
        print(f"   - Log level: {config.get('logging', {}).get('level', 'not set')}")
        return True
        
    except Exception as e:
        print(f"❌ Configuration file invalid: {e}")
        return False

def validate_env_example():
    """Validate .env.example file"""
    print("🔍 Validating .env.example...")
    
    env_path = ".env.example"
    
    if not os.path.exists(env_path):
        print("⚠️  .env.example not found (optional)")
        return True
    
    try:
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Check for key environment variables
        expected_vars = [
            'WEBSOCKET_HOST',
            'WEBSOCKET_PORT', 
            'LOG_LEVEL',
            'LOG_DIR'
        ]
        
        missing_vars = []
        for var in expected_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing environment variables in .env.example: {missing_vars}")
        else:
            print("✅ .env.example contains expected variables")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading .env.example: {e}")
        return False

def validate_python_files():
    """Basic validation of Python files"""
    print("🔍 Validating Python file syntax...")
    
    python_files = []
    for root, dirs, files in os.walk("webcam_ip"):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    syntax_errors = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Try to compile the file
            compile(content, file_path, 'exec')
            
        except SyntaxError as e:
            syntax_errors.append((file_path, str(e)))
        except Exception as e:
            # Other errors (like encoding issues)
            syntax_errors.append((file_path, f"Error: {e}"))
    
    if syntax_errors:
        print("❌ Python syntax errors found:")
        for file_path, error in syntax_errors:
            print(f"   - {file_path}: {error}")
        return False
    else:
        print(f"✅ All {len(python_files)} Python files have valid syntax")
        return True

def main():
    print("=" * 60)
    print("🔍 CONFIGURATION VALIDATION")
    print("=" * 60)
    
    validators = [
        validate_file_structure,
        validate_config_yaml,
        validate_env_example,
        validate_python_files
    ]
    
    passed = 0
    for validator in validators:
        if validator():
            passed += 1
        print()
    
    print("=" * 60)
    if passed == len(validators):
        print("🎉 ALL CONFIGURATION VALIDATIONS PASSED!")
        print("🚀 Your system configuration is valid!")
    else:
        print(f"⚠️  {len(validators) - passed} validations failed")
        print("🔧 Please fix the configuration issues")
    print("=" * 60)

if __name__ == "__main__":
    main()