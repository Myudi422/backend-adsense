#!/usr/bin/env python3
"""
Simple test to verify today-earnings endpoint is working correctly
"""

import requests
import json
import time

def test_today_earnings():
    url = "http://localhost:8000/api/today-earnings/pub-1777593071761494"
    
    print("Testing today-earnings endpoint...")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS! Response:")
            print(json.dumps(data, indent=2))
            
            # Analyze the result
            earnings = data.get('earnings', 0)
            clicks = data.get('clicks', 0)
            impressions = data.get('impressions', 0)
            
            print(f"\n📊 Analysis:")
            print(f"Earnings: ${earnings} USD")
            print(f"Clicks: {clicks:,}")
            print(f"Impressions: {impressions:,}")
            
            if earnings > 0:
                print("✅ Earnings conversion working correctly!")
                # Convert back to see original micros value
                original_micros = earnings * 1_000_000
                print(f"Original micros value: {original_micros:,.0f}")
            else:
                print("⚠️  Earnings still 0 - may be no data today")
                
        else:
            print(f"❌ HTTP {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server not running?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_today_earnings()