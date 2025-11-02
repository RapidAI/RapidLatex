#!/usr/bin/env python
"""
MathTranslate API Server Launcher
Convenient script to start the API server with proper configuration
"""

import os
import sys
import argparse
import subprocess

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['flask', 'flask_cors']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Please install them with: pip install -r api_requirements.txt")
        return False

    return True

def check_config():
    """Check if config file exists and is properly formatted"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        print(f"❌ Config file '{config_file}' not found")
        print("Please create a config.json file with your translation engine settings")
        return False

    try:
        import json
        with open(config_file, 'r') as f:
            json.load(f)
        print(f"✅ Config file '{config_file}' is valid")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Config file '{config_file}' is not valid JSON: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'api_output', 'input']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Directory '{directory}' ready")

def start_server(host='0.0.0.0', port=5000, debug=False):
    """Start the API server"""
    print(f"🚀 Starting MathTranslate API Server...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")
    print(f"   PID: {os.getpid()}")
    print()

    # Set environment variables
    env = os.environ.copy()
    env['FLASK_ENV'] = 'development' if debug else 'production'

    # Start the server
    try:
        from api_app import app
        app.run(host=host, port=port, debug=debug)
    except ImportError as e:
        print(f"❌ Failed to import API app: {e}")
        print("Make sure api_app.py is in the same directory")
        return False
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Start MathTranslate API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--check-only', action='store_true', help='Only check dependencies and config, don\'t start server')

    args = parser.parse_args()

    print("🔍 MathTranslate API Server Setup Check")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Check config
    if not check_config():
        sys.exit(1)

    # Create directories
    create_directories()

    if args.check_only:
        print("\n✅ All checks passed! Ready to start the server.")
        return

    print("\n" + "=" * 50)
    print("🌐 Server Information:")
    print(f"   Local URL: http://localhost:{args.port}")
    print(f"   Network URL: http://{args.host}:{args.port}")
    print()
    print("📚 API Endpoints:")
    print("   GET  /api/health - Health check")
    print("   GET  /api/engines - List translation engines")
    print("   POST /api/upload - Upload file")
    print("   POST /api/arxiv/<id> - Translate ArXiv paper")
    print("   POST /api/translate/<task_id> - Start translation")
    print("   GET  /api/status/<task_id> - Get task status")
    print("   GET  /api/download/<task_id>/<filename> - Download file")
    print("   GET  /api/tasks - List all tasks")
    print("   DELETE /api/tasks/<task_id> - Delete task")
    print()
    print("🛠️  Usage Examples:")
    print(f"   curl http://localhost:{args.port}/api/health")
    print(f"   curl -X POST -F 'file=@document.tex' http://localhost:{args.port}/api/upload")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)

    # Start the server
    start_server(args.host, args.port, args.debug)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)