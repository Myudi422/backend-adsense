#!/usr/bin/env python3
"""
Test script dengan perbaikan konversi micros yang benar
"""

import adsense_util
import sys
from datetime import datetime, timedelta
from googleapiclient import discovery
import google.auth.exceptions

def convert_micros_to_dollars(micros_value):
    """Convert AdSense API micros format to dollars."""
    try:
        return float(micros_value) / 1_000_000 if micros_value else 0.0
    except (ValueError, TypeError):
        return 0.0

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
        
        print("\n=== REPORT RESULTS (FIXED) ===")
        print(f"Headers: {[h['name'] for h in result.get('headers', [])]}")
        
        if 'rows' in result and result['rows']:
            print(f"Total rows: {len(result['rows'])}")
            print("\nFirst 5 rows (dengan konversi micros):")
            
            for i, row in enumerate(result['rows'][:5]):
                # Konversi earnings dari micros ke dollars
                earnings_micros = float(row['cells'][1]['value'] or 0)
                earnings_dollars = convert_micros_to_dollars(earnings_micros)
                
                print(f"Row {i+1}:")
                print(f"  Date: {row['cells'][0]['value']}")
                print(f"  Earnings (raw micros): {earnings_micros:,.0f}")
                print(f"  Earnings (USD): ${earnings_dollars:.2f}")
                print(f"  Clicks: {row['cells'][2]['value']}")
                print(f"  Impressions: {row['cells'][3]['value']}")
                print(f"  Page Views: {row['cells'][4]['value']}")
                print()
                
            # Calculate totals dengan konversi yang benar
            total_earnings_micros = sum(float(row['cells'][1]['value'] or 0) for row in result['rows'])
            total_earnings_dollars = convert_micros_to_dollars(total_earnings_micros)
            total_clicks = sum(int(row['cells'][2]['value'] or 0) for row in result['rows'])
            total_impressions = sum(int(row['cells'][3]['value'] or 0) for row in result['rows'])
            total_pageviews = sum(int(row['cells'][4]['value'] or 0) for row in result['rows'])
            
            print(f"=== SUMMARY (CORRECTED) ===")
            print(f"Total Earnings (micros): {total_earnings_micros:,.0f}")
            print(f"Total Earnings (USD): ${total_earnings_dollars:.2f}")
            print(f"Total Clicks: {total_clicks:,}")
            print(f"Total Impressions: {total_impressions:,}")
            print(f"Total Page Views: {total_pageviews:,}")
            print(f"CTR: {(total_clicks/total_impressions*100):.2f}%" if total_impressions > 0 else "CTR: 0%")
            print(f"CPM: ${(total_earnings_dollars/total_impressions*1000):.2f}" if total_impressions > 0 else "CPM: $0.00")
            
            # Perbandingan dengan data yang salah
            print(f"\n=== PERBANDINGAN ===")
            print(f"❌ Tanpa konversi micros: ${total_earnings_micros:.2f} (SALAH)")
            print(f"✅ Dengan konversi micros: ${total_earnings_dollars:.2f} (BENAR)")
            
        else:
            print("No data found in the report!")
        
    except google.auth.exceptions.RefreshError:
        print('Authentication failed. Please delete adsense.dat and re-authenticate.')
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()