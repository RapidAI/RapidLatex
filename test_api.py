#!/usr/bin/env python
"""
Test script for MathTranslate API
"""

import requests
import json
import time
import os

# API Configuration
BASE_URL = "http://localhost:5000/api"

def test_health_check():
    """Test health check endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_get_engines():
    """Test getting available engines"""
    print("\nTesting engines endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/engines")
        if response.status_code == 200:
            data = response.json()
            engines = [engine['id'] for engine in data['engines']]
            print(f"✅ Available engines: {', '.join(engines)}")
            return True
        else:
            print(f"❌ Engines endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Engines endpoint error: {e}")
        return False

def test_file_upload():
    """Test file upload"""
    print("\nTesting file upload...")

    # Create a test LaTeX file
    test_content = r"""
\documentclass{article}
\usepackage{amsmath}

\begin{document}

\section{Test Document}

This is a test document for the MathTranslate API.

Mathematical formula: $E = mc^2$

\end{document}
"""

    test_file = "test_api_document.tex"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    try:
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/upload", files=files)

        if response.status_code == 200:
            data = response.json()
            task_id = data['task_id']
            print(f"✅ File uploaded successfully. Task ID: {task_id}")
            return task_id
        else:
            print(f"❌ File upload failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ File upload error: {e}")
        return None

    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

def test_start_translation(task_id):
    """Test starting translation"""
    print(f"\nTesting translation start for task {task_id}...")

    data = {
        'engine': 'openai',
        'language_from': 'en',
        'language_to': 'zh-CN',
        'compile': False,  # Skip compilation for faster testing
        'nocache': True
    }

    try:
        response = requests.post(f"{BASE_URL}/translate/{task_id}", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Translation started successfully")
            print(f"   Engine: {result['options']['engine']}")
            print(f"   Languages: {result['options']['language_from']} -> {result['options']['language_to']}")
            return True
        else:
            print(f"❌ Translation start failed: {response.status_code}")
            print(f"   Error: {response.json()}")
            return False

    except Exception as e:
        print(f"❌ Translation start error: {e}")
        return False

def test_check_status(task_id):
    """Test checking task status"""
    print(f"\nTesting status check for task {task_id}...")

    try:
        response = requests.get(f"{BASE_URL}/status/{task_id}")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Status retrieved successfully")
            print(f"   Status: {status['status']}")
            print(f"   Progress: {status['progress']}%")
            print(f"   Message: {status['message']}")
            return status
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Status check error: {e}")
        return None

def test_wait_for_completion(task_id, timeout=300):
    """Wait for task completion"""
    print(f"\nWaiting for task {task_id} completion (timeout: {timeout}s)...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BASE_URL}/status/{task_id}")
            if response.status_code == 200:
                status = response.json()
                print(f"   Status: {status['status']} | Progress: {status['progress']}% | Message: {status['message']}")

                if status['status'] in ['completed', 'failed']:
                    print(f"✅ Task finished with status: {status['status']}")
                    return status

            time.sleep(5)
        except Exception as e:
            print(f"❌ Status check error during wait: {e}")
            break

    print(f"⏰ Timeout waiting for task completion")
    return None

def test_list_tasks():
    """Test listing all tasks"""
    print("\nTesting tasks list...")

    try:
        response = requests.get(f"{BASE_URL}/tasks")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved {data['total']} tasks")
            for task in data['tasks'][:3]:  # Show first 3 tasks
                print(f"   Task {task['id'][:8]}...: {task['status']} ({task['progress']}%)")
            return True
        else:
            print(f"❌ Tasks list failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Tasks list error: {e}")
        return False

def test_arxiv_translation():
    """Test ArXiv paper translation (simplified)"""
    print("\nTesting ArXiv translation...")

    # Use a small, well-known paper for testing
    arxiv_id = "cs.LO/0611105"  # A small logic paper

    data = {
        'engine': 'google',  # Use free engine for testing
        'language_from': 'en',
        'language_to': 'zh-CN',
        'compile': False,
        'nocache': True
    }

    try:
        response = requests.post(f"{BASE_URL}/arxiv/{arxiv_id}", json=data)
        if response.status_code == 200:
            result = response.json()
            task_id = result['task_id']
            print(f"✅ ArXiv translation started. Task ID: {task_id}")
            print(f"   ArXiv ID: {result['arxiv_id']}")
            return task_id
        else:
            print(f"❌ ArXiv translation failed: {response.status_code}")
            print(f"   This might be due to network issues or invalid ArXiv ID")
            return None

    except Exception as e:
        print(f"❌ ArXiv translation error: {e}")
        return None

def run_api_tests():
    """Run all API tests"""
    print("🚀 Starting MathTranslate API Tests")
    print("=" * 50)

    # Test basic functionality
    if not test_health_check():
        print("❌ API server is not running. Please start it with: python api_app.py")
        return False

    test_get_engines()

    # Test file upload and translation
    task_id = test_file_upload()
    if task_id:
        if test_start_translation(task_id):
            final_status = test_wait_for_completion(task_id, timeout=120)  # 2 minute timeout
            if final_status and final_status['status'] == 'completed':
                print("✅ File translation test completed successfully")
            elif final_status and final_status['status'] == 'failed':
                print(f"❌ File translation failed: {final_status['message']}")

    # Test task listing
    test_list_tasks()

    # Test ArXiv translation (optional)
    print("\n" + "=" * 50)
    print("📝 Note: ArXiv translation test requires internet connection")
    arxiv_task = test_arxiv_translation()
    if arxiv_task:
        # Just check status briefly, don't wait for completion
        time.sleep(10)
        status = test_check_status(arxiv_task)

    print("\n" + "=" * 50)
    print("🎉 API tests completed!")
    print("\nTo use the API:")
    print("1. Start the server: python api_app.py")
    print("2. Upload files via POST /api/upload")
    print("3. Start translation via POST /api/translate/<task_id>")
    print("4. Check status via GET /api/status/<task_id>")
    print("5. Download results via GET /api/download/<task_id>/<filename>")
    print("\nSee API_DOCUMENTATION.md for detailed usage instructions.")

    return True

if __name__ == "__main__":
    try:
        run_api_tests()
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()