#!/usr/bin/env python3
"""
Multi-Account AdSense Setup & Test Script
Setup dan test multiple AdSense accounts
"""

import requests
import json
import os
from datetime import datetime

def test_multi_account_api():
    base_url = "http://localhost:8000"
    
    print("🚀 Multi-Account AdSense API Test")
    print("=" * 50)
    
    # Test 1: Root endpoint
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print("✅ API Info:")
            print(f"   Version: {data['message']}")
            print(f"   Accounts: {', '.join(data['accounts'])}")
            print()
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("   Make sure server is running: python app_v2.py")
        return
    
    # Test 2: Get all accounts status
    try:
        response = requests.get(f"{base_url}/api/accounts")
        if response.status_code == 200:
            accounts = response.json()
            print("📋 Configured Accounts:")
            for account in accounts:
                status_icon = "✅" if account['status'] == 'active' else "❌"
                print(f"   {status_icon} {account['display_name']} ({account['account_key']})")
                print(f"      Account ID: {account['account_id']}")
                print(f"      Status: {account['status']}")
                print()
        else:
            print(f"❌ Accounts endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Accounts test error: {e}")
    
    # Test 3: Today earnings for each account
    print("💰 Today's Earnings:")
    for account_key in ["perpustakaan", "gowesgo"]:
        try:
            response = requests.get(f"{base_url}/api/today-earnings/{account_key}")
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 {account_key.upper()}:")
                print(f"      Earnings: Rp {data['earnings_idr']:.2f}")
                print(f"      Micros: {data['earnings_micros']:,}")
                print(f"      Clicks: {data['clicks']:,}")
                print(f"      Impressions: {data['impressions']:,}")
                print(f"      CTR: {data['ctr']}%")
                print(f"      Data age: {data['data_age_days']} days")
                print(f"      Note: {data['note']}")
                print()
            else:
                print(f"   ❌ {account_key}: {response.status_code}")
                if response.status_code == 404:
                    print(f"      Account not found or not configured")
                print()
        except Exception as e:
            print(f"   ❌ {account_key} error: {e}")
    
    # Test 4: Domain breakdown for both accounts
    for account_key, account_name in [("perpustakaan", "Perpustakaan"), ("gowesgo", "GowesGo")]:
        try:
            response = requests.get(f"{base_url}/api/domain-earnings/{account_key}")
            if response.status_code == 200:
                data = response.json()
                print(f"🌐 Domain Breakdown ({account_name}):")
                print(f"   Total domains: {data['summary']['total_domains']}")
                print(f"   Total earnings: Rp {data['summary']['total_earnings_idr']:.2f}")
                print()
                if data['domains']:
                    print("   Top domains:")
                    for i, domain in enumerate(data['domains'][:5]):
                        if domain['earnings_idr'] > 0:  # Only show domains with earnings
                            print(f"   {i+1}. {domain['domain']}")
                            print(f"      Earnings: Rp {domain['earnings_idr']:.2f}")
                            print(f"      Traffic: {domain['clicks']} clicks, {domain['impressions']:,} impressions")
                            print()
                else:
                    print("   No domain data available")
                print()
            else:
                print(f"❌ {account_name} domain breakdown failed: {response.status_code}")
        except Exception as e:
            print(f"❌ {account_name} domain breakdown error: {e}")
    
    # Test 5: Multi-account summary
    try:
        response = requests.get(f"{base_url}/api/summary")
        if response.status_code == 200:
            data = response.json()
            print("📈 Multi-Account Summary:")
            print(f"   Total accounts: {data['total_accounts']}")
            print(f"   Total earnings: Rp {data['total_earnings_idr']:.2f}")
            print(f"   Total clicks: {data['total_clicks']:,}")
            print(f"   Total impressions: {data['total_impressions']:,}")
            print()
            print("   Account breakdown:")
            for account in data['accounts']:
                status_icon = "✅" if account['status'] == 'active' else "❌"
                print(f"   {status_icon} {account['display_name']}: Rp {account['earnings_idr']:.2f}")
            print()
        else:
            print(f"❌ Summary failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Summary error: {e}")
    
    print("🎯 Test completed!")
    print("\nUsage Examples:")
    print(f"   All accounts: GET {base_url}/api/accounts")
    print(f"   Today earnings: GET {base_url}/api/today-earnings/perpustakaan")
    print(f"   Domain filter: GET {base_url}/api/domain-earnings/perpustakaan?domain=perpustakaan.id")
    print(f"   Multi summary: GET {base_url}/api/summary")

def setup_accounts():
    """Setup and validate account configurations."""
    print("🔧 Account Setup Validation")
    print("=" * 30)
    
    # Check required files
    required_files = {
        "perpustakaan": {
            "client_secrets.json": "Perpustakaan client secrets",
            "adsense.dat": "Perpustakaan credentials"
        },
        "gowesgo": {
            "client_secrets-gowesgo.json": "GowesGo client secrets", 
            "adsense-gowesgo.dat": "GowesGo credentials"
        }
    }
    
    for account, files in required_files.items():
        print(f"\n📋 {account.upper()} Account:")
        for filename, description in files.items():
            if os.path.exists(filename):
                print(f"   ✅ {description}: {filename}")
            else:
                print(f"   ❌ {description}: {filename} (MISSING)")
        
        # Check if credentials need refresh
        if account == "gowesgo" and os.path.exists("adsense-gowesgo.dat"):
            try:
                with open("adsense-gowesgo.dat", 'r') as f:
                    creds = json.load(f)
                    if creds.get("token") == "placeholder":
                        print(f"   ⚠️  GowesGo credentials need OAuth setup")
                        print(f"      Run: python -c \"from app_v2 import get_adsense_service; get_adsense_service('gowesgo')\"")
            except:
                pass

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_accounts()
    else:
        test_multi_account_api()