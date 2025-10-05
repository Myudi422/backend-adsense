#!/usr/bin/env python3
"""
Script untuk memperbaiki masalah konversi currency dari micros ke dollars
dan membuat endpoint yang tepat untuk handling data AdSense
"""

import adsense_util
from datetime import datetime, timedelta
from googleapiclient import discovery
import google.auth.exceptions

def convert_micros_to_dollars(micros_value):
    """Convert micros (AdSense API format) to dollars"""
    try:
        return float(micros_value) / 1_000_000 if micros_value else 0.0
    except (ValueError, TypeError):
        return 0.0

def test_corrected_data():
    try:
        # Authenticate
        credentials = adsense_util.get_adsense_credentials()
        service = discovery.build('adsense', 'v2', credentials=credentials)
        
        # Get account
        account_id = adsense_util.get_account_id(service)
        print(f"Account: {account_id}")
        
        # Get last 7 days data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"\n=== DATA TERKOREKSI (7 hari terakhir) ===")
        print(f"Periode: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Generate report
        result = service.accounts().reports().generate(
            account=account_id,
            dateRange='CUSTOM',
            startDate_year=start_date.year,
            startDate_month=start_date.month, 
            startDate_day=start_date.day,
            endDate_year=end_date.year,
            endDate_month=end_date.month,
            endDate_day=end_date.day,
            metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
        ).execute()
        
        if 'rows' in result and result['rows']:
            # Calculate corrected totals
            total_earnings_micros = sum(float(row['cells'][1]['value'] or 0) for row in result['rows'])
            total_earnings_dollars = convert_micros_to_dollars(total_earnings_micros)
            total_clicks = sum(int(row['cells'][2]['value'] or 0) for row in result['rows'])
            total_impressions = sum(int(row['cells'][3]['value'] or 0) for row in result['rows'])
            total_pageviews = sum(int(row['cells'][4]['value'] or 0) for row in result['rows'])
            
            print(f"\n📊 SUMMARY TERKOREKSI:")
            print(f"💰 Total Earnings: ${total_earnings_dollars:.2f} (bukan ${total_earnings_micros:,.2f})")
            print(f"🖱️  Total Clicks: {total_clicks:,}")
            print(f"👁️  Total Impressions: {total_impressions:,}")
            print(f"📄 Total Page Views: {total_pageviews:,}")
            print(f"📈 CTR: {(total_clicks/total_impressions*100):.2f}%" if total_impressions > 0 else "CTR: 0%")
            print(f"💸 CPM: ${(total_earnings_dollars/total_impressions*1000):.4f}" if total_impressions > 0 else "CPM: $0.00")
            
            print(f"\n📅 BREAKDOWN HARIAN:")
            for row in result['rows'][-5:]:  # Show last 5 days
                date = row['cells'][0]['value']
                earnings_micros = float(row['cells'][1]['value'] or 0)
                earnings_dollars = convert_micros_to_dollars(earnings_micros)
                clicks = int(row['cells'][2]['value'] or 0)
                impressions = int(row['cells'][3]['value'] or 0)
                
                print(f"  {date}: ${earnings_dollars:.2f} | {clicks} clicks | {impressions:,} impressions")
        
        # Analyze subdomain possibilities
        print(f"\n🌐 ANALISIS SUBDOMAIN:")
        print(f"Domain utama: perpustakaan.id")
        
        # Try to get more detailed breakdown using different dimensions
        try:
            # Try with AD_UNIT_NAME dimension
            unit_result = service.accounts().reports().generate(
                account=account_id,
                dateRange='LAST_7_DAYS',
                metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS'],
                dimensions=['AD_UNIT_NAME']
            ).execute()
            
            if 'rows' in unit_result and unit_result['rows']:
                print(f"\n📋 BREAKDOWN PER AD UNIT:")
                for row in unit_result['rows'][:10]:  # Show top 10
                    unit_name = row['cells'][0]['value']
                    earnings = convert_micros_to_dollars(float(row['cells'][1]['value'] or 0))
                    clicks = int(row['cells'][2]['value'] or 0)
                    print(f"  {unit_name}: ${earnings:.2f} | {clicks} clicks")
        except Exception as e:
            print(f"Cannot get ad unit breakdown: {e}")
        
        # Get custom channels if any
        try:
            channels_result = service.accounts().adclients().customchannels().list(
                parent=f"{account_id}/adclients/-"
            ).execute()
            
            if 'customChannels' in channels_result and channels_result['customChannels']:
                print(f"\n🎯 CUSTOM CHANNELS TERSEDIA:")
                for channel in channels_result['customChannels']:
                    print(f"  - {channel.get('displayName', 'Unnamed Channel')}")
            else:
                print(f"\n❌ TIDAK ADA CUSTOM CHANNELS")
                print(f"   Ini sebabnya subdomain tidak bisa dipisah!")
        except Exception as e:
            print(f"Cannot get custom channels: {e}")
        
        print(f"\n💡 REKOMENDASI UNTUK SUBDOMAIN TRACKING:")
        print(f"1. Buat Custom Channels di AdSense Dashboard untuk setiap subdomain")
        print(f"2. Setup manual tracking per halaman dengan JavaScript")
        print(f"3. Gunakan Google Analytics 4 untuk breakdown yang lebih detail")
        print(f"4. Implementasi UTM parameters untuk tracking")
        
    except Exception as e:
        print(f"Error: {e}")

def create_currency_fix_for_app():
    """Create a fix for the app.py currency conversion issue"""
    
    conversion_code = '''
def convert_micros_to_dollars(micros_value):
    """Convert AdSense API micros format to dollars"""
    try:
        return float(micros_value) / 1_000_000 if micros_value else 0.0
    except (ValueError, TypeError):
        return 0.0

def convert_report_data(report):
    """Convert all earnings data in report from micros to dollars"""
    if 'rows' in report:
        for row in report['rows']:
            if isinstance(row, dict) and 'cells' in row:
                # Find earnings columns (usually contain ESTIMATED_EARNINGS)
                for i, cell in enumerate(row['cells']):
                    # Check if this is an earnings column by looking at headers
                    if i == 1:  # Usually earnings is the second column
                        try:
                            original_value = float(cell['value'] or 0)
                            cell['value'] = str(convert_micros_to_dollars(original_value))
                        except (ValueError, TypeError):
                            pass
    return report
'''
    
    print("🔧 CURRENCY CONVERSION CODE:")
    print("Add this to your app.py file:")
    print(conversion_code)
    
    print("\n📝 THEN UPDATE YOUR REPORT ENDPOINTS:")
    print("Replace lines like:")
    print("  earnings += float(row[0] or 0)")
    print("With:")
    print("  earnings += convert_micros_to_dollars(float(row[0] or 0))")

if __name__ == '__main__':
    test_corrected_data()
    print("\n" + "="*50)
    create_currency_fix_for_app()