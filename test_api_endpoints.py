#!/usr/bin/env python3
"""
Comprehensive test untuk memverifikasi semua perbaikan API
"""

import requests
import json
from datetime import datetime, timedelta

def test_api_endpoints():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing AdSense API Endpoints...")
    print("=" * 50)
    
    # Test 1: Root endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Root endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()['message']}")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
    
    print()
    
    # Test 2: Summary endpoint (main issue area)
    try:
        response = requests.get(f"{base_url}/api/summary")
        print(f"📊 Summary endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Accounts: {data.get('accounts_count', 0)}")
            print(f"   Ad Units: {data.get('ad_units_count', 0)}")
            print(f"   Total Earnings: ${data.get('total_earnings', 0):.2f}")
            print(f"   Total Clicks: {data.get('total_clicks', 0):,}")
            print(f"   Total Impressions: {data.get('total_impressions', 0):,}")
            
            # Check if earnings make sense (should be reasonable, not millions)
            earnings = data.get('total_earnings', 0)
            if earnings > 10000:
                print(f"   ⚠️  WARNING: Earnings seem too high - might be micros conversion issue")
            elif earnings == 0:
                print(f"   ⚠️  WARNING: Zero earnings - check data or time period")
            else:
                print(f"   ✅ Earnings look reasonable")
                
            if 'recent_earnings' in data:
                recent = data['recent_earnings']
                print(f"   Recent CTR: {recent.get('ctr', 0):.2f}%")
                print(f"   Recent CPM: ${recent.get('cpm', 0):.2f}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Summary endpoint failed: {e}")
    
    print()
    
    # Test 3: Today earnings for specific account
    account_id = "pub-1777593071761494"  # From your test
    try:
        response = requests.get(f"{base_url}/api/today-earnings/{account_id}")
        print(f"📈 Today earnings endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Date: {data.get('date', 'N/A')}")
            print(f"   Earnings: ${data.get('earnings', 0):.2f}")
            print(f"   Clicks: {data.get('clicks', 0):,}")
            print(f"   Impressions: {data.get('impressions', 0):,}")
            print(f"   CTR: {data.get('ctr', 0):.2f}%")
            print(f"   CPM: ${data.get('cpm', 0):.2f}")
            print(f"   Data age: {data.get('data_age_days', 0)} days")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Today earnings endpoint failed: {e}")
    
    print()
    
    # Test 4: Custom report
    try:
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        response = requests.get(f"{base_url}/api/report/{account_id}", params={
            'start_date': start_date,
            'end_date': end_date,
            'metrics': 'ESTIMATED_EARNINGS,CLICKS,IMPRESSIONS'
        })
        print(f"📋 Custom report endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Account: {data.get('account_id', 'N/A')}")
            print(f"   Period: {data.get('start_date')} to {data.get('end_date')}")
            print(f"   Metrics: {data.get('metrics', [])}")
            
            if 'data' in data and 'rows' in data['data']:
                rows = data['data']['rows']
                print(f"   Rows returned: {len(rows)}")
                
                if rows:
                    # Check first row to see if conversion worked
                    first_row = rows[0]
                    if 'cells' in first_row and len(first_row['cells']) > 1:
                        earnings_value = first_row['cells'][1]['value']
                        try:
                            earnings_float = float(earnings_value)
                            if earnings_float > 1000:
                                print(f"   ⚠️  First row earnings: {earnings_float} (might need micros conversion)")
                            else:
                                print(f"   ✅ First row earnings: ${earnings_float:.2f} (converted properly)")
                        except:
                            print(f"   ✅ First row earnings: {earnings_value} (string format)")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Custom report endpoint failed: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")

if __name__ == '__main__':
    test_api_endpoints()