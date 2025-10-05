#!/usr/bin/env python3
"""
Test script dengan konversi IDR langsung yang benar
"""

import requests
import json

def test_corrected_endpoints():
    base_url = "http://localhost:8000"
    account_id = "pub-1777593071761494"
    
    print("🧪 Testing Corrected IDR Conversion...")
    print("=" * 50)
    
    # Test today-earnings
    try:
        response = requests.get(f"{base_url}/api/today-earnings/{account_id}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Today Earnings (Fixed):")
            print(f"  Earnings: Rp {data.get('earnings_idr', 0):.2f}")
            print(f"  Micros: {data.get('earnings_micros', 0):,}")
            print(f"  USD: ${data.get('earnings_usd', 0):.6f}")
            print(f"  Clicks: {data.get('clicks', 0):,}")
            print(f"  Impressions: {data.get('impressions', 0):,}")
            print()
        else:
            print(f"❌ Today earnings failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test domain earnings
    try:
        response = requests.get(f"{base_url}/api/domain-earnings/{account_id}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Domain Earnings (Fixed):")
            print(f"  Total: Rp {data['summary']['total_earnings_idr']:.2f}")
            print(f"  Domains: {data['summary']['total_domains']}")
            print()
            
            print("📊 Top domains:")
            for i, domain in enumerate(data['domains'][:3]):
                print(f"  {i+1}. {domain['domain']}: Rp {domain['earnings_idr']:.2f}")
                
        else:
            print(f"❌ Domain earnings failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_corrected_endpoints()