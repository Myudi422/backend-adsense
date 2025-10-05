#!/usr/bin/env python3
"""
Account Management Test Script
Test upload, connect, and manage AdSense accounts
"""

import requests
import json
import os
from datetime import datetime

def test_account_management():
    base_url = "http://localhost:8000"
    
    print("🔧 AdSense Account Management Test")
    print("=" * 50)
    
    # Test 1: List current accounts
    print("1️⃣ Current Accounts:")
    try:
        response = requests.get(f"{base_url}/api/accounts")
        if response.status_code == 200:
            accounts = response.json()
            for account in accounts:
                status_icon = "✅" if account['status'] == 'active' else "❌"
                print(f"   {status_icon} {account['display_name']} ({account['account_key']})")
                print(f"      Publisher ID: {account['account_id']}")
            print()
        else:
            print(f"   ❌ Failed to get accounts: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Upload new account (simulation)
    print("2️⃣ Account Upload Simulation:")
    print("   📁 To upload new account:")
    print("   POST /api/accounts/upload")
    print("   Form data:")
    print("     - account_key: 'newsite'")
    print("     - display_name: 'NewSite.com'") 
    print("     - description: 'My new website AdSense account'")
    print("     - file: client_secrets.json")
    print()
    
    # Test 3: Validate existing accounts
    print("3️⃣ Account Validation:")
    for account_key in ["perpustakaan", "gowesgo"]:
        try:
            response = requests.get(f"{base_url}/api/accounts/{account_key}/validate")
            if response.status_code == 200:
                data = response.json()
                status_icon = "✅" if data['valid'] else "❌"
                print(f"   {status_icon} {account_key.upper()}:")
                print(f"      Valid: {data['valid']}")
                print(f"      Status: {data['status']}")
                if data.get('publisher_id'):
                    print(f"      Publisher ID: {data['publisher_id']}")
                if data.get('error'):
                    print(f"      Error: {data['error']}")
                print()
            else:
                print(f"   ❌ {account_key}: Validation failed ({response.status_code})")
        except Exception as e:
            print(f"   ❌ {account_key}: Error - {e}")
    
    # Test 4: API Documentation
    print("4️⃣ Account Management Endpoints:")
    endpoints = [
        ("POST /api/accounts/upload", "Upload client secrets JSON"),
        ("POST /api/accounts/{account_key}/connect", "Connect AdSense account via OAuth"),
        ("GET /api/accounts/{account_key}/validate", "Validate account connection"),
        ("DELETE /api/accounts/{account_key}?confirm=true", "Remove account (irreversible)")
    ]
    
    for endpoint, description in endpoints:
        print(f"   📋 {endpoint}")
        print(f"      {description}")
        print()
    
    print("5️⃣ Usage Example - Adding New Account:")
    print("""
   Step 1: Get Client Secrets
   - Go to Google Cloud Console
   - Navigate to APIs & Services → Credentials  
   - Create OAuth 2.0 Client ID (Desktop Application)
   - Download client_secrets.json
   
   Step 2: Upload to API
   curl -X POST "http://localhost:8000/api/accounts/upload" \\
        -F "account_key=mysite" \\
        -F "display_name=MySite.com" \\
        -F "description=My website AdSense" \\
        -F "file=@client_secrets.json"
   
   Step 3: Connect Account
   curl -X POST "http://localhost:8000/api/accounts/mysite/connect"
   
   Step 4: Validate Setup
   curl "http://localhost:8000/api/accounts/mysite/validate"
   
   Step 5: Use Account
   curl "http://localhost:8000/api/today-earnings/mysite"
   """)
    
    print("🎯 Account Management Test Complete!")
    print("\n📋 Available Operations:")
    print("   ✅ List all accounts: GET /api/accounts")
    print("   📁 Upload client secrets: POST /api/accounts/upload")
    print("   🔗 Connect OAuth: POST /api/accounts/{account_key}/connect")
    print("   ✅ Validate setup: GET /api/accounts/{account_key}/validate")
    print("   🗑️ Remove account: DELETE /api/accounts/{account_key}?confirm=true")

def create_sample_client_secrets():
    """Create sample client secrets file for testing."""
    sample_secrets = {
        "installed": {
            "client_id": "123456789-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com",
            "project_id": "my-adsense-project",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "GOCSPX-sample_client_secret_here",
            "redirect_uris": ["http://localhost:8080/", "urn:ietf:wg:oauth:2.0:oob"]
        }
    }
    
    with open("sample_client_secrets.json", "w") as f:
        json.dump(sample_secrets, f, indent=2)
    
    print("📄 Created sample_client_secrets.json for testing")
    print("   ⚠️  Replace with real credentials for actual use")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        create_sample_client_secrets()
    else:
        test_account_management()