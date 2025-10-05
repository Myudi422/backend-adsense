#!/usr/bin/env python3
"""
Test domain earnings endpoint
"""

import requests
import json

def test_domain_earnings():
    base_url = "http://localhost:8000"
    account_id = "pub-1777593071761494"
    
    print("🔍 Testing Domain Earnings Endpoint...")
    print("=" * 50)
    
    # Test 1: All domains
    try:
        response = requests.get(f"{base_url}/api/domain-earnings/{account_id}")
        if response.status_code == 200:
            data = response.json()
            print("✅ All Domains:")
            print(f"Total Domains: {data['summary']['total_domains']}")
            print(f"Total Earnings: ${data['summary']['total_earnings']} USD")
            print(f"Total Earnings: Rp {data['summary']['total_earnings_idr']}")
            print(f"Total Clicks: {data['summary']['total_clicks']:,}")
            print(f"Total Impressions: {data['summary']['total_impressions']:,}")
            print()
            
            print("📊 Breakdown by Domain:")
            for i, domain in enumerate(data['domains'][:5]):  # Top 5
                print(f"{i+1}. {domain['domain']}")
                print(f"   Earnings: Rp {domain['earnings_idr']} (${domain['earnings']:.6f})")
                print(f"   Traffic: {domain['clicks']} clicks, {domain['impressions']} impressions")
                print()
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("-" * 50)
    
    # Test 2: Filter untuk perpustakaan.id saja
    try:
        response = requests.get(f"{base_url}/api/domain-earnings/{account_id}?domain=perpustakaan.id")
        if response.status_code == 200:
            data = response.json()
            print("✅ Filter 'perpustakaan.id':")
            print(f"Matched Domains: {data['summary']['total_domains']}")
            print(f"Total Earnings: Rp {data['summary']['total_earnings_idr']}")
            print()
            
            for domain in data['domains']:
                print(f"• {domain['domain']}: Rp {domain['earnings_idr']}")
        else:
            print(f"❌ Filter Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Filter Error: {e}")

if __name__ == "__main__":
    test_domain_earnings()