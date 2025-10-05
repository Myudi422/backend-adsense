#!/usr/bin/env python3
"""
Quick API Test Script
Test the new JSON database API endpoints
"""

import requests
import json
import time
import sys
from threading import Thread
import subprocess
import os

def start_server():
    """Start API server in background."""
    try:
        # Start server process
        cmd = [sys.executable, "app_v2.py"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        time.sleep(3)
        
        return process
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def test_api_endpoints():
    """Test various API endpoints."""
    base_url = "http://localhost:8001"
    
    print("🧪 Testing AdSense JSON Database API")
    print("=" * 50)
    
    tests = [
        {
            "name": "Root Endpoint",
            "url": f"{base_url}/",
            "method": "GET"
        },
        {
            "name": "Get All Accounts",
            "url": f"{base_url}/api/accounts", 
            "method": "GET"
        },
        {
            "name": "Database Statistics",
            "url": f"{base_url}/api/database/stats",
            "method": "GET"
        },
        {
            "name": "Search Accounts",
            "url": f"{base_url}/api/database/search?query=perpustakaan",
            "method": "GET"
        },
        {
            "name": "Multi-Account Summary",
            "url": f"{base_url}/api/summary",
            "method": "GET"
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"\n🔍 Testing: {test['name']}")
        print(f"   URL: {test['url']}")
        
        try:
            response = requests.get(test['url'], timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS (Status: {response.status_code})")
                
                # Show relevant data
                if 'accounts' in data and isinstance(data['accounts'], list):
                    print(f"   📊 Found {len(data['accounts'])} accounts")
                elif 'total_accounts' in data:
                    print(f"   📊 Total accounts: {data['total_accounts']}")
                elif 'database_info' in data:
                    print(f"   📊 Database size: {data['database_info'].get('size_kb', 0)} KB")
                
                results.append({"test": test['name'], "success": True, "status": response.status_code})
            else:
                print(f"   ❌ FAILED (Status: {response.status_code})")
                print(f"   Error: {response.text[:200]}...")
                results.append({"test": test['name'], "success": False, "status": response.status_code})
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ CONNECTION ERROR - Server not running on port 8001")
            results.append({"test": test['name'], "success": False, "error": "connection_error"})
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({"test": test['name'], "success": False, "error": str(e)})
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    
    passed = len([r for r in results if r.get('success', False)])
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All API endpoints working correctly!")
        print("\n🌐 Access your API documentation at:")
        print("   http://localhost:8001/docs (Swagger UI)")
        print("   http://localhost:8001/redoc (ReDoc)")
    else:
        print(f"\n⚠️  {total - passed} endpoints failed. Check server logs.")
    
    return passed == total

def main():
    """Main test function."""
    print("🚀 AdSense JSON Database API Test")
    print("Starting server and testing endpoints...")
    
    # Check if accounts.json exists
    if not os.path.exists("accounts.json"):
        print("❌ accounts.json not found. Run migrate_to_json_db.py first.")
        return False
    
    print("✅ Found accounts.json database")
    
    # Test directly without starting server (assume it's running)
    success = test_api_endpoints()
    
    if success:
        print("\n✅ JSON Database API is working perfectly!")
        print("\n📖 Key Features Available:")
        print("   • Dynamic account management")
        print("   • JSON database with backup/restore")
        print("   • Search and filtering")
        print("   • Complete API documentation")
        print("   • Multi-account earnings tracking")
        
        return True
    else:
        print("\n❌ Some API endpoints failed. Check server status.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)