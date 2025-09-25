#!/usr/bin/env python3
"""
Backend Smoke Test for Geo-Strategist API
Tests basic health endpoints that don't require external services.
"""

import requests
import json
import sys
from typing import Dict, Any

# Backend URL - using the default from config since no .env file exists
BACKEND_URL = "http://localhost:8001"

def test_health_endpoint() -> Dict[str, Any]:
    """Test GET /api/v1/health endpoint"""
    print("Testing GET /api/v1/health...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/health", timeout=10)
        
        result = {
            "endpoint": "/api/v1/health",
            "status_code": response.status_code,
            "success": False,
            "response_data": None,
            "error": None
        }
        
        if response.status_code == 200:
            try:
                data = response.json()
                result["response_data"] = data
                
                # Check if response matches expected format
                if isinstance(data, dict) and data.get("status") == "ok":
                    result["success"] = True
                    print(f"✅ Health endpoint working: {data}")
                else:
                    result["error"] = f"Unexpected response format: {data}"
                    print(f"❌ Health endpoint returned unexpected format: {data}")
            except json.JSONDecodeError as e:
                result["error"] = f"Invalid JSON response: {e}"
                print(f"❌ Health endpoint returned invalid JSON: {e}")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Health endpoint failed with status {response.status_code}: {response.text}")
            
        return result
        
    except requests.exceptions.RequestException as e:
        result = {
            "endpoint": "/api/v1/health",
            "status_code": None,
            "success": False,
            "response_data": None,
            "error": f"Request failed: {e}"
        }
        print(f"❌ Health endpoint request failed: {e}")
        return result

def test_health_details_endpoint() -> Dict[str, Any]:
    """Test GET /api/v1/config/health/details endpoint"""
    print("\nTesting GET /api/v1/config/health/details...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/config/health/details", timeout=10)
        
        result = {
            "endpoint": "/api/v1/config/health/details",
            "status_code": response.status_code,
            "success": False,
            "response_data": None,
            "error": None
        }
        
        if response.status_code == 200:
            try:
                data = response.json()
                result["response_data"] = data
                
                # Check if response has expected structure
                if isinstance(data, dict) and "backend" in data:
                    backend_info = data.get("backend", {})
                    if isinstance(backend_info, dict) and backend_info.get("ok") is True:
                        result["success"] = True
                        print(f"✅ Health details endpoint working")
                        print(f"   Backend status: {backend_info}")
                        
                        # Check Ollama and Chroma status (should not depend on them being available)
                        ollama_info = data.get("ollama", {})
                        chroma_info = data.get("chroma", {})
                        print(f"   Ollama reachable: {ollama_info.get('reachable', 'unknown')}")
                        print(f"   Chroma reachable: {chroma_info.get('reachable', 'unknown')}")
                    else:
                        result["error"] = f"Backend not marked as ok: {backend_info}"
                        print(f"❌ Backend not marked as ok: {backend_info}")
                else:
                    result["error"] = f"Missing 'backend' key in response: {data}"
                    print(f"❌ Missing 'backend' key in response: {data}")
                    
            except json.JSONDecodeError as e:
                result["error"] = f"Invalid JSON response: {e}"
                print(f"❌ Health details endpoint returned invalid JSON: {e}")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Health details endpoint failed with status {response.status_code}: {response.text}")
            
        return result
        
    except requests.exceptions.RequestException as e:
        result = {
            "endpoint": "/api/v1/config/health/details",
            "status_code": None,
            "success": False,
            "response_data": None,
            "error": f"Request failed: {e}"
        }
        print(f"❌ Health details endpoint request failed: {e}")
        return result

def test_root_endpoint() -> Dict[str, Any]:
    """Test GET / endpoint (non-critical)"""
    print("\nTesting GET / (root endpoint)...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=10)
        
        result = {
            "endpoint": "/",
            "status_code": response.status_code,
            "success": False,
            "response_data": None,
            "error": None
        }
        
        if response.status_code == 200:
            content = response.text
            result["response_data"] = f"HTML content ({len(content)} chars)"
            
            # Check if it's HTML with expected links
            if "html" in content.lower() and "api" in content.lower():
                result["success"] = True
                print(f"✅ Root endpoint working - returned HTML page with API links")
            else:
                result["error"] = "Response doesn't appear to be HTML with API links"
                print(f"❌ Root endpoint returned unexpected content")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Root endpoint failed with status {response.status_code}: {response.text}")
            
        return result
        
    except requests.exceptions.RequestException as e:
        result = {
            "endpoint": "/",
            "status_code": None,
            "success": False,
            "response_data": None,
            "error": f"Request failed: {e}"
        }
        print(f"❌ Root endpoint request failed: {e}")
        return result

def main():
    """Run all backend smoke tests"""
    print("=" * 60)
    print("BACKEND SMOKE TEST - Geo-Strategist API")
    print("=" * 60)
    print(f"Testing backend at: {BACKEND_URL}")
    print()
    
    # Run tests
    results = []
    results.append(test_health_endpoint())
    results.append(test_health_details_endpoint())
    results.append(test_root_endpoint())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} {result['endpoint']}")
        if not result["success"] and result["error"]:
            print(f"     Error: {result['error']}")
        
        if result["success"]:
            passed += 1
        else:
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    # Return appropriate exit code
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)