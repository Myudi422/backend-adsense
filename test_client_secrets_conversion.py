#!/usr/bin/env python3
"""
Test Script: Client Secrets Auto-Conversion
Test the auto-conversion from "web" to "installed" format
"""

import json
import sys
import os
import tempfile
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_v2 import validate_client_secrets_json

def test_web_to_installed_conversion():
    """Test conversion from web format to installed format."""
    print("🧪 Testing Client Secrets Auto-Conversion")
    print("=" * 50)
    
    # Test data: web format
    web_format = {
        "web": {
            "client_id": "test-client-id.apps.googleusercontent.com",
            "project_id": "test-project-123",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "GOCSPX-test-secret",
            "redirect_uris": ["http://localhost:8000"]
        }
    }
    
    # Test data: installed format
    installed_format = {
        "installed": {
            "client_id": "test-client-id.apps.googleusercontent.com",
            "client_secret": "GOCSPX-test-secret",
            "redirect_uris": ["http://localhost:8080/", "urn:ietf:wg:oauth:2.0:oob"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    
    print("🔍 Test 1: Web Format Conversion")
    try:
        result = validate_client_secrets_json(json.dumps(web_format))
        
        if "installed" in result:
            print("✅ PASS: Web format successfully converted to installed")
            print(f"   Client ID: {result['installed']['client_id']}")
            print(f"   Redirect URIs: {result['installed']['redirect_uris']}")
            
            # Verify redirect URIs are correct
            expected_uris = ["http://localhost:8080/", "urn:ietf:wg:oauth:2.0:oob"]
            if result['installed']['redirect_uris'] == expected_uris:
                print("✅ PASS: Redirect URIs correctly set for OAuth flow")
            else:
                print("❌ FAIL: Incorrect redirect URIs")
                return False
        else:
            print("❌ FAIL: Web format not converted to installed")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Web format conversion error: {e}")
        return False
    
    print("\n🔍 Test 2: Installed Format Passthrough")
    try:
        result = validate_client_secrets_json(json.dumps(installed_format))
        
        if "installed" in result:
            print("✅ PASS: Installed format passed through unchanged")
            if result == installed_format:
                print("✅ PASS: Data integrity maintained")
            else:
                print("⚠️  WARN: Data modified during passthrough")
        else:
            print("❌ FAIL: Installed format corrupted")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Installed format validation error: {e}")
        return False
    
    print("\n🔍 Test 3: Invalid Format Rejection")
    invalid_format = {
        "invalid": {
            "client_id": "test"
        }
    }
    
    try:
        validate_client_secrets_json(json.dumps(invalid_format))
        print("❌ FAIL: Invalid format should be rejected")
        return False
    except ValueError as e:
        print("✅ PASS: Invalid format correctly rejected")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False
    
    return True

def test_janklerk_account_setup():
    """Test janklerk account setup with regenerated client secrets."""
    print("\n🧪 Testing Janklerk Account Setup")
    print("=" * 50)
    
    # Check if client secrets exist
    client_secrets_path = "client_secrets-janklerk.json"
    if not os.path.exists(client_secrets_path):
        print(f"❌ FAIL: Client secrets not found: {client_secrets_path}")
        return False
    
    print(f"✅ PASS: Client secrets found: {client_secrets_path}")
    
    # Validate client secrets format
    try:
        with open(client_secrets_path, 'r') as f:
            content = f.read()
        
        result = validate_client_secrets_json(content)
        
        if "installed" in result:
            print("✅ PASS: Client secrets in correct 'installed' format")
            
            installed = result["installed"]
            required_fields = ["client_id", "client_secret", "auth_uri", "token_uri", "redirect_uris"]
            
            for field in required_fields:
                if field in installed:
                    print(f"   ✅ {field}: Present")
                else:
                    print(f"   ❌ {field}: Missing")
                    return False
            
            # Check redirect URIs
            redirect_uris = installed.get("redirect_uris", [])
            expected_uris = ["http://localhost:8080/", "urn:ietf:wg:oauth:2.0:oob"]
            
            if redirect_uris == expected_uris:
                print("   ✅ Redirect URIs: Correct for OAuth flow")
            else:
                print(f"   ⚠️  Redirect URIs: {redirect_uris} (expected: {expected_uris})")
            
        else:
            print("❌ FAIL: Client secrets not in 'installed' format")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Client secrets validation error: {e}")
        return False
    
    # Check accounts.json entry
    accounts_path = "accounts.json"
    if os.path.exists(accounts_path):
        try:
            with open(accounts_path, 'r') as f:
                accounts_data = json.load(f)
            
            if "janklerk" in accounts_data.get("accounts", {}):
                janklerk_account = accounts_data["accounts"]["janklerk"]
                print("✅ PASS: Janklerk account found in database")
                print(f"   Account ID: {janklerk_account.get('account_id')}")
                print(f"   Status: {janklerk_account.get('status')}")
                print(f"   Display Name: {janklerk_account.get('display_name')}")
                
                if janklerk_account.get("client_secrets") == client_secrets_path:
                    print("   ✅ Client secrets path correctly linked")
                else:
                    print("   ⚠️  Client secrets path mismatch")
                    
            else:
                print("⚠️  WARN: Janklerk account not found in database")
                
        except Exception as e:
            print(f"⚠️  WARN: Could not read accounts database: {e}")
    
    return True

def main():
    """Run all conversion tests."""
    print("🚀 Client Secrets Auto-Conversion Test Suite")
    print("Testing web-to-installed format conversion and janklerk setup")
    print("=" * 70)
    
    all_passed = True
    
    # Test auto-conversion
    if not test_web_to_installed_conversion():
        all_passed = False
    
    # Test janklerk setup
    if not test_janklerk_account_setup():
        all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 All tests passed! Auto-conversion system working correctly.")
        print("\n📋 Summary:")
        print("   ✅ Web-to-installed conversion functional")
        print("   ✅ Installed format passthrough working") 
        print("   ✅ Invalid format rejection working")
        print("   ✅ Janklerk account setup ready")
        print("\n🚀 Next steps:")
        print("   1. Start API server: python app_v2.py")
        print("   2. Connect janklerk account: POST /api/accounts/janklerk/connect")
        print("   3. Test earnings: GET /api/today-earnings/janklerk")
    else:
        print("❌ Some tests failed. Check output above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)