#!/usr/bin/env python3
"""
Test script untuk mengambil data reporting terbaru
dengan date range yang valid (setelah 2022-10-01)
"""

import adsense_util
import sys
from datetime import datetime, timedelta
from googleapiclient import discovery
import google.auth.exceptions

def main():
    try:
        # Authenticate
        
        credentials = adsense_util.get_adsense_credentials()
        service = discovery.build('adsense', 'v2', credentials=credentials)
        
        # Get account
        account_id = adsense_util.get_account_id(service)
        print(f"Using account: {account_id}")
        
        # Set date range untuk 30 hari terakhir
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"Requesting data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Generate report dengan data terbaru
        result = service.accounts().reports().generate(
            account=account_id,
            dateRange='CUSTOM',
            startDate_year=start_date.year,
            startDate_month=start_date.month, 
            startDate_day=start_date.day,
            endDate_year=end_date.year,
            endDate_month=end_date.month,
            endDate_day=end_date.day,
            metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS'],
            dimensions=['DATE']
        ).execute()
        
        print("\n=== REPORT RESULTS ===")
        print(f"Headers: {[h['name'] for h in result.get('headers', [])]}")
        
        if 'rows' in result and result['rows']:
            print(f"Total rows: {len(result['rows'])}")
            print("\nFirst 5 rows:")
            for i, row in enumerate(result['rows'][:5]):
                print(f"Row {i+1}: {row}")
                
            # Calculate totals
            total_earnings = sum(float(row['cells'][1]['value'] or 0) for row in result['rows'])
            total_clicks = sum(int(row['cells'][2]['value'] or 0) for row in result['rows'])
            total_impressions = sum(int(row['cells'][3]['value'] or 0) for row in result['rows'])
            total_pageviews = sum(int(row['cells'][4]['value'] or 0) for row in result['rows']) if len(result['rows'][0]['cells']) > 4 else 0
            
            print(f"\n=== SUMMARY ===")
            print(f"Total Earnings: ${total_earnings:.2f}")
            print(f"Total Clicks: {total_clicks:,}")
            print(f"Total Impressions: {total_impressions:,}")
            print(f"Total Page Views: {total_pageviews:,}")
            print(f"CTR: {(total_clicks/total_impressions*100):.2f}%" if total_impressions > 0 else "CTR: 0%")
            print(f"CPM: ${(total_earnings/total_impressions*1000):.2f}" if total_impressions > 0 else "CPM: $0.00")
        else:
            print("No data found in the report!")
            print("This could mean:")
            print("1. No ad revenue generated in the time period")
            print("2. Ads not properly setup or approved")
            print("3. Site has no traffic")
            print("4. AdSense account needs time to process data")
        
        # Test sites endpoint
        print(f"\n=== TESTING SITES ===")
        try:
            sites_result = service.accounts().sites().list(parent=account_id).execute()
            if 'sites' in sites_result:
                print(f"Found {len(sites_result['sites'])} sites:")
                for site in sites_result['sites']:
                    print(f"  - {site.get('domain', 'N/A')} ({site.get('state', 'Unknown state')})")
            else:
                print("No sites found!")
        except Exception as e:
            print(f"Error fetching sites: {e}")
        
        # Test ad clients
        print(f"\n=== TESTING AD CLIENTS ===")
        try:
            adclients_result = service.accounts().adclients().list(parent=account_id).execute()
            if 'adClients' in adclients_result:
                print(f"Found {len(adclients_result['adClients'])} ad clients:")
                for client in adclients_result['adClients']:
                    supports_reporting = "Yes" if client.get('reportingDimensionId') else "No"
                    print(f"  - {client.get('productCode', 'N/A')} (ID: {client.get('name', 'N/A').split('/')[-1]}, Reporting: {supports_reporting})")
            else:
                print("No ad clients found!")
        except Exception as e:
            print(f"Error fetching ad clients: {e}")
        
    except google.auth.exceptions.RefreshError:
        print('Authentication failed. Please delete adsense.dat and re-authenticate.')
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()