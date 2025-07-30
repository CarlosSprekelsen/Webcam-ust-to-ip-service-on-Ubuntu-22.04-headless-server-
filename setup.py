#!/usr/bin/env python3
"""
Setup script for WebSocket JSON-RPC Camera Server
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    with open(os.path.join(os.path.dirname(__file__), 'skeleton-server', 'README.md'), 'r') as f:
        return f.read()

# Read requirements
def read_requirements():
    with open(os.path.join(os.path.dirname(__file__), 'skeleton-server', 'requirements.txt'), 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="websocket-jsonrpc-camera",
    version="1.0.0",
    description="WebSocket JSON-RPC Server with USB Camera Monitoring",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Camera Service Team",
    python_requires=">=3.10",
    packages=find_packages(),
    package_dir={"": "skeleton-server"},
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.1",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "camera-server=server:main",
            "camera-test=test_client:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)