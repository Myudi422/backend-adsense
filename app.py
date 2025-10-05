#!/usr/bin/env python3
"""
AdSense API Backend Server
Menyediakan REST API untuk mengakses data AdSense dengan summary dashboard.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import sys
import os
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import AdSense utilities
import adsense_util
import google.auth.exceptions
from googleapiclient import discovery

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="AdSense API Backend",
    description="Backend API untuk mengakses data AdSense dengan summary dashboard",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool untuk async operations
executor = ThreadPoolExecutor(max_workers=4)

# Global service instance
_service = None

# Pydantic models
class Account(BaseModel):
    name: str
    displayName: str
    accountId: str
    premium: Optional[bool] = None
    timeZone: Optional[str] = None

class AdUnit(BaseModel):
    name: str
    displayName: str
    state: str
    contentAdsSettings: Optional[Dict[str, Any]] = None

class ReportData(BaseModel):
    dimensions: List[str]
    metrics: List[str]
    rows: List[List[str]]
    totalMatchedRows: Optional[int] = None

class Site(BaseModel):
    name: str
    displayName: str
    domain: str
    state: str
    autoAdsEnabled: Optional[bool] = None

class TodayEarnings(BaseModel):
    date: str
    account_id: str
    earnings: Optional[float] = None
    clicks: Optional[int] = None
    impressions: Optional[int] = None
    ctr: Optional[float] = None
    cpm: Optional[float] = None
    page_views: Optional[int] = None

class SummaryData(BaseModel):
    accounts_count: int
    ad_units_count: int
    total_earnings: Optional[float] = None
    total_clicks: Optional[int] = None
    total_impressions: Optional[int] = None
    accounts: List[Account]
    recent_earnings: Optional[Dict[str, Any]] = None

def convert_micros_to_dollars(micros_value):
    """Convert AdSense API micros format to dollars."""
    try:
        return float(micros_value) / 1_000_000 if micros_value else 0.0
    except (ValueError, TypeError):
        return 0.0

def convert_micros_to_idr(micros_value):
    """Convert AdSense API micros format to IDR (micros already in IDR currency)."""
    try:
        return float(micros_value) / 1_000 if micros_value else 0.0
    except (ValueError, TypeError):
        return 0.0

def convert_report_data(report):
    """Convert all earnings data in report from micros to dollars."""
    if 'rows' in report:
        for row in report['rows']:
            if isinstance(row, dict) and 'cells' in row:
                # Convert earnings columns based on header information
                if 'headers' in report:
                    for i, header in enumerate(report['headers']):
                        # Look for earnings-related metrics
                        if ('EARNINGS' in header.get('name', '').upper() or 
                            'REVENUE' in header.get('name', '').upper() or
                            'RPM' in header.get('name', '').upper() or
                            'CPC' in header.get('name', '').upper()):
                            if i < len(row['cells']):
                                try:
                                    original_value = float(row['cells'][i]['value'] or 0)
                                    # Convert micros to dollars
                                    row['cells'][i]['value'] = str(convert_micros_to_dollars(original_value))
                                except (ValueError, TypeError):
                                    pass
                else:
                    # Fallback: assume column 1 is earnings if no headers
                    if len(row['cells']) > 1:
                        try:
                            original_value = float(row['cells'][1]['value'] or 0)
                            row['cells'][1]['value'] = str(convert_micros_to_dollars(original_value))
                        except (ValueError, TypeError):
                            pass
    return report

def get_adsense_service():
    """Get or create AdSense service instance."""
    global _service
    if _service is None:
        credentials = adsense_util.get_adsense_credentials()
        _service = discovery.build('adsense', 'v2', credentials=credentials)
    return _service

async def run_in_executor(func, *args):
    """Run a function in thread executor for async compatibility."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting AdSense API Backend...")
    try:
        service = get_adsense_service()
        logger.info("AdSense service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AdSense service: {e}")

@app.get("/")
async def root():
    """Root endpoint dengan informasi API."""
    return {
        "message": "AdSense API Backend",
        "version": "1.0.0",
        "endpoints": {
            "accounts": "/api/accounts",
            "ad-units": "/api/ad-units/{account_id}",
            "reports": "/api/reports/{account_id}",
            "summary": "/api/summary",
            "today-earnings": "/api/today-earnings/{account_id}",
            "sites": "/api/sites/{account_id}",
            "earnings-by-site": "/api/earnings-by-site/{account_id}",
            "all-domains": "/api/all-domains/{account_id}",
            "subdomain-analysis": "/api/subdomain-analysis/{account_id}",
            "custom-channels": "/api/custom-channels/{account_id}",
            "subdomain-setup-guide": "/api/subdomain-setup-guide",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        service = get_adsense_service()
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/api/accounts", response_model=List[Account])
async def get_accounts():
    """Mendapatkan semua account AdSense."""
    try:
        service = get_adsense_service()
        
        def fetch_accounts():
            accounts = []
            request = service.accounts().list(pageSize=50)
            while request is not None:
                result = request.execute()
                if 'accounts' in result:
                    for account in result['accounts']:
                        accounts.append(Account(
                            name=account.get('name', ''),
                            displayName=account.get('displayName', ''),
                            accountId=account.get('name', '').split('/')[-1],
                            premium=account.get('premium'),
                            timeZone=account.get('timeZone', {}).get('id')
                        ))
                request = service.accounts().list_next(request, result)
            return accounts
        
        accounts = await run_in_executor(fetch_accounts)
        return accounts
        
    except google.auth.exceptions.RefreshError as e:
        raise HTTPException(status_code=401, detail="Authentication failed. Please re-authenticate.")
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ad-units/{account_id}", response_model=List[AdUnit])
async def get_ad_units(account_id: str):
    """Mendapatkan semua ad units untuk account tertentu."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_ad_units():
            ad_units = []
            request = service.accounts().adclients().adunits().list(
                parent=f"{full_account_name}/adclients/-",
                pageSize=50
            )
            while request is not None:
                result = request.execute()
                if 'adUnits' in result:
                    for ad_unit in result['adUnits']:
                        ad_units.append(AdUnit(
                            name=ad_unit.get('name', ''),
                            displayName=ad_unit.get('displayName', ''),
                            state=ad_unit.get('state', ''),
                            contentAdsSettings=ad_unit.get('contentAdsSettings')
                        ))
                request = service.accounts().adclients().adunits().list_next(request, result)
            return ad_units
        
        ad_units = await run_in_executor(fetch_ad_units)
        return ad_units
        
    except Exception as e:
        logger.error(f"Error fetching ad units: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/{account_id}")
async def get_reports(
    account_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    metrics: Optional[str] = "ESTIMATED_EARNINGS,CLICKS,IMPRESSIONS"
):
    """Generate report untuk account tertentu."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        # Default dates (last 30 days)
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        def generate_report():
            request = service.accounts().reports().generate(
                account=full_account_name,
                dateRange='CUSTOM',
                startDate_year=int(start_date.split('-')[0]),
                startDate_month=int(start_date.split('-')[1]),
                startDate_day=int(start_date.split('-')[2]),
                endDate_year=int(end_date.split('-')[0]),
                endDate_month=int(end_date.split('-')[1]),
                endDate_day=int(end_date.split('-')[2]),
                metrics=metrics.split(',')
            )
            return request.execute()
        
        report = await run_in_executor(generate_report)
        
        # Convert currency data from micros to dollars
        converted_report = convert_report_data(report)
        
        return {
            "account_id": account_id,
            "start_date": start_date,
            "end_date": end_date,
            "metrics": metrics.split(','),
            "data": converted_report
        }
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary", response_model=SummaryData)
async def get_summary():
    """Mendapatkan summary lengkap dari semua data AdSense."""
    try:
        service = get_adsense_service()
        
        def fetch_summary_data():
            # Get accounts
            accounts = []
            request = service.accounts().list(pageSize=50)
            while request is not None:
                result = request.execute()
                if 'accounts' in result:
                    for account in result['accounts']:
                        accounts.append(Account(
                            name=account.get('name', ''),
                            displayName=account.get('displayName', ''),
                            accountId=account.get('name', '').split('/')[-1],
                            premium=account.get('premium'),
                            timeZone=account.get('timeZone', {}).get('id')
                        ))
                request = service.accounts().list_next(request, result)
            
            # Count ad units for all accounts
            total_ad_units = 0
            total_earnings = 0.0
            total_clicks = 0
            total_impressions = 0
            
            for account in accounts:
                try:
                    # Count ad units
                    ad_units_request = service.accounts().adclients().adunits().list(
                        parent=f"{account.name}/adclients/-",
                        pageSize=1
                    )
                    ad_units_result = ad_units_request.execute()
                    if 'totalSize' in ad_units_result:
                        total_ad_units += int(ad_units_result['totalSize'])
                    
                    # Get recent earnings (last 7 days)
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    
                    report_request = service.accounts().reports().generate(
                        account=account.name,
                        dateRange='CUSTOM',
                        startDate_year=start_date.year,
                        startDate_month=start_date.month,
                        startDate_day=start_date.day,
                        endDate_year=end_date.year,
                        endDate_month=end_date.month,
                        endDate_day=end_date.day,
                        metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS']
                    )
                    report = report_request.execute()
                    
                    if 'rows' in report and report['rows']:
                        for row in report['rows']:
                            if 'cells' in row and len(row['cells']) >= 3:
                                # Correctly access cell values: [DATE, EARNINGS, CLICKS, IMPRESSIONS]
                                earnings_micros = float(row['cells'][1]['value'] or 0)
                                total_earnings += convert_micros_to_dollars(earnings_micros)
                                total_clicks += int(row['cells'][2]['value'] or 0)
                                total_impressions += int(row['cells'][3]['value'] or 0)
                                
                except Exception as e:
                    logger.warning(f"Error fetching data for account {account.accountId}: {e}")
                    continue
            
            return {
                "accounts_count": len(accounts),
                "ad_units_count": total_ad_units,
                "total_earnings": total_earnings,
                "total_clicks": total_clicks,
                "total_impressions": total_impressions,
                "accounts": accounts,
                "recent_earnings": {
                    "period": "last_7_days",
                    "earnings": total_earnings,
                    "clicks": total_clicks,
                    "impressions": total_impressions,
                    "ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                    "cpm": (total_earnings / total_impressions * 1000) if total_impressions > 0 else 0
                }
            }
        
        summary = await run_in_executor(fetch_summary_data)
        return SummaryData(**summary)
        
    except google.auth.exceptions.RefreshError as e:
        raise HTTPException(status_code=401, detail="Authentication failed. Please re-authenticate.")
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/today-earnings/{account_id}")
async def get_today_earnings(account_id: str):
    """Mendapatkan estimasi penghasilan dengan fallback ke data terbaru yang tersedia."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_recent_earnings():
            # Try multiple days to find the most recent data
            for days_back in [0, 1, 2, 3]:  # Today, yesterday, 2 days ago, 3 days ago
                try:
                    target_date = datetime.now() - timedelta(days=days_back)
                    date_str = target_date.strftime('%Y-%m-%d')
                    
                    request = service.accounts().reports().generate(
                        account=full_account_name,
                        dateRange='CUSTOM',
                        startDate_year=target_date.year,
                        startDate_month=target_date.month,
                        startDate_day=target_date.day,
                        endDate_year=target_date.year,
                        endDate_month=target_date.month,
                        endDate_day=target_date.day,
                        metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
                    )
                    report = request.execute()
                    
                    earnings = 0.0
                    clicks = 0
                    impressions = 0
                    page_views = 0
                    
                    if 'rows' in report and report['rows']:
                        logger.info(f"Found {len(report['rows'])} rows for {date_str}")
                        for row in report['rows']:
                            if 'cells' in row and len(row['cells']) >= 4:
                                # Fix: Without DATE dimension, EARNINGS=0, CLICKS=1, IMPRESSIONS=2, PAGE_VIEWS=3
                                earnings_micros = float(row['cells'][0]['value'] or 0)
                                earnings_idr = convert_micros_to_idr(earnings_micros)
                                logger.info(f"Row data - Micros: {earnings_micros}, IDR: Rp {earnings_idr:.2f}, Clicks: {row['cells'][1]['value']}")
                                earnings += earnings_idr
                                clicks += int(row['cells'][1]['value'] or 0)
                                impressions += int(row['cells'][2]['value'] or 0)
                                page_views += int(row['cells'][3]['value'] or 0)
                    
                    # If we found data, return it
                    if earnings > 0 or clicks > 0 or impressions > 0:
                        ctr = (clicks / impressions * 100) if impressions > 0 else 0
                        cpm = (earnings / impressions * 1000) if impressions > 0 else 0
                        
                        return {
                            "date": date_str,
                            "account_id": account_id,
                            "earnings_idr": round(earnings, 2),  # Direct IDR value
                            "earnings_micros": int(earnings * 1_000), # Original micros for reference
                            "earnings_usd": round(earnings / 15000, 6),  # Approximate USD conversion
                            "clicks": clicks,
                            "impressions": impressions,
                            "ctr": round(ctr, 2),
                            "cpm": round(cpm, 2),
                            "page_views": page_views,
                            "data_age_days": days_back,
                            "note": f"Data terbaru tersedia dari {days_back} hari yang lalu" if days_back > 0 else "Data hari ini"
                        }
                        
                except Exception as e:
                    logger.warning(f"Error fetching data for {days_back} days back: {e}")
                    continue
            
            # Return no data found
            return {
                "date": datetime.now().strftime('%Y-%m-%d'),
                "account_id": account_id,
                "earnings_idr": 0,
                "earnings_micros": 0,
                "earnings_usd": 0,
                "clicks": 0,
                "impressions": 0,
                "ctr": 0,
                "cpm": 0,
                "page_views": 0,
                "data_age_days": -2,
                "note": "Data belum tersedia. AdSense biasanya memiliki delay 1-3 hari untuk reporting.",
                "suggestions": [
                    "Cek lagi besok untuk data yang lebih akurat",
                    "Pastikan website memiliki traffic",
                    "Verifikasi ads sudah terpasang dengan benar"
                ]
            }
        
        earnings_data = await run_in_executor(fetch_recent_earnings)
        return earnings_data
        
    except Exception as e:
        logger.error(f"Error fetching earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/domain-earnings/{account_id}")
async def get_domain_earnings(account_id: str, domain: str = None):
    """Mendapatkan estimasi penghasilan dengan fallback ke data terbaru yang tersedia."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_recent_earnings():
            # Try multiple days to find the most recent data
            for days_back in [0, 1, 2, 3]:  # Today, yesterday, 2 days ago, 3 days ago
                try:
                    target_date = datetime.now() - timedelta(days=days_back)
                    date_str = target_date.strftime('%Y-%m-%d')
                    
                    request = service.accounts().reports().generate(
                        account=full_account_name,
                        dateRange='CUSTOM',
                        startDate_year=target_date.year,
                        startDate_month=target_date.month,
                        startDate_day=target_date.day,
                        endDate_year=target_date.year,
                        endDate_month=target_date.month,
                        endDate_day=target_date.day,
                        metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
                    )
                    report = request.execute()
                    
                    earnings = 0.0
                    clicks = 0
                    impressions = 0
                    page_views = 0
                    
                    if 'rows' in report and report['rows']:
                        logger.info(f"Found {len(report['rows'])} rows for {date_str}")
                        for row in report['rows']:
                            if 'cells' in row and len(row['cells']) >= 4:
                                # Fix: Without DATE dimension, EARNINGS=0, CLICKS=1, IMPRESSIONS=2, PAGE_VIEWS=3
                                earnings_micros = float(row['cells'][0]['value'] or 0)
                                earnings_idr = convert_micros_to_idr(earnings_micros)
                                logger.info(f"Row data - Micros: {earnings_micros}, IDR: Rp {earnings_idr:.2f}, Clicks: {row['cells'][1]['value']}")
                                earnings += earnings_idr
                                clicks += int(row['cells'][1]['value'] or 0)
                                impressions += int(row['cells'][2]['value'] or 0)
                                page_views += int(row['cells'][3]['value'] or 0)
                    
                    # If we found data, return it
                    if earnings > 0 or clicks > 0 or impressions > 0:
                        ctr = (clicks / impressions * 100) if impressions > 0 else 0
                        cpm = (earnings / impressions * 1000) if impressions > 0 else 0
                        
                        return {
                            "date": date_str,
                            "account_id": account_id,
                            "earnings_idr": round(earnings, 2),  # Direct IDR value
                            "earnings_micros": int(earnings * 1_000), # Original micros for reference
                            "earnings_usd": round(earnings / 15000, 6),  # Approximate USD conversion
                            "clicks": clicks,
                            "impressions": impressions,
                            "ctr": round(ctr, 2),
                            "cpm": round(cpm, 2),
                            "page_views": page_views,
                            "data_age_days": days_back,
                            "note": f"Data terbaru tersedia dari {days_back} hari yang lalu" if days_back > 0 else "Data hari ini"
                        }
                        
                except Exception as e:
                    logger.warning(f"Error fetching data for {days_back} days back: {e}")
                    continue
            
            # If no data found in last 4 days, try to get last 7 days summary
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                request = service.accounts().reports().generate(
                    account=full_account_name,
                    dateRange='CUSTOM',
                    startDate_year=start_date.year,
                    startDate_month=start_date.month,
                    startDate_day=start_date.day,
                    endDate_year=end_date.year,
                    endDate_month=end_date.month,
                    endDate_day=end_date.day,
                    metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
                )
                report = request.execute()
                
                earnings = clicks = impressions = page_views = 0
                if 'rows' in report and report['rows']:
                    for row in report['rows']:
                        if 'cells' in row and len(row['cells']) >= 4:
                            # Fix: Without DATE dimension, EARNINGS=0, CLICKS=1, IMPRESSIONS=2, PAGE_VIEWS=3
                            earnings_micros = float(row['cells'][0]['value'] or 0)
                            earnings += convert_micros_to_idr(earnings_micros)
                            clicks += int(row['cells'][1]['value'] or 0)
                            impressions += int(row['cells'][2]['value'] or 0)
                            page_views += int(row['cells'][3]['value'] or 0)
                
                # Calculate averages
                avg_earnings = earnings / 7
                avg_clicks = clicks // 7
                avg_impressions = impressions // 7
                avg_page_views = page_views // 7
                
                ctr = (avg_clicks / avg_impressions * 100) if avg_impressions > 0 else 0
                cpm = (avg_earnings / avg_impressions * 1000) if avg_impressions > 0 else 0
                
                return {
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "account_id": account_id,
                    "earnings_idr": round(avg_earnings, 2),  # Direct IDR value
                    "earnings_micros": int(avg_earnings * 1_000),
                    "earnings_usd": round(avg_earnings / 15000, 6),
                    "clicks": avg_clicks,
                    "impressions": avg_impressions,
                    "ctr": round(ctr, 2),
                    "cpm": round(cpm, 2),
                    "page_views": avg_page_views,
                    "data_age_days": -1,
                    "note": "Estimasi berdasarkan rata-rata 7 hari terakhir (data real-time belum tersedia)",
                    "total_last_7_days": {
                        "earnings": round(earnings, 2),
                        "clicks": clicks,
                        "impressions": impressions,
                        "page_views": page_views
                    }
                }
                
            except Exception as e:
                logger.warning(f"Error fetching 7-day summary: {e}")
                return {
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "account_id": account_id,
                    "earnings": 0.0,
                    "clicks": 0,
                    "impressions": 0,
                    "ctr": 0.0,
                    "cpm": 0.0,
                    "page_views": 0,
                    "data_age_days": -2,
                    "note": "Data belum tersedia. AdSense biasanya memiliki delay 1-3 hari untuk reporting.",
                    "suggestions": [
                        "Cek lagi besok untuk data yang lebih akurat",
                        "Pastikan website memiliki traffic",
                        "Verifikasi ads sudah terpasang dengan benar"
                    ]
                }
        
        earnings_data = await run_in_executor(fetch_recent_earnings)
        return earnings_data
        
    except Exception as e:
        logger.error(f"Error fetching earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/domain-earnings/{account_id}")
async def get_domain_earnings(account_id: str, domain: str = None):
    """Get earnings breakdown by domain/subdomain."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_domain_earnings():
            target_date = datetime.now()
            
            request = service.accounts().reports().generate(
                account=full_account_name,
                dateRange='CUSTOM',
                startDate_year=target_date.year,
                startDate_month=target_date.month,
                startDate_day=target_date.day,
                endDate_year=target_date.year,
                endDate_month=target_date.month,
                endDate_day=target_date.day,
                metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS'],
                dimensions=['DOMAIN_NAME']
            )
            report = request.execute()
            
            domains = []
            total_earnings = 0
            total_clicks = 0
            total_impressions = 0
            total_page_views = 0
            
            if 'rows' in report and report['rows']:
                for row in report['rows']:
                    domain_name = row['cells'][0]['value']
                    earnings_micros = float(row['cells'][1]['value'] or 0)
                    clicks = int(row['cells'][2]['value'] or 0)
                    impressions = int(row['cells'][3]['value'] or 0)
                    page_views = int(row['cells'][4]['value'] or 0)
                    
                    earnings_idr = convert_micros_to_idr(earnings_micros)
                    
                    domain_data = {
                        "domain": domain_name,
                        "earnings_idr": round(earnings_idr, 2),
                        "earnings_micros": int(earnings_micros),
                        "earnings_usd": round(earnings_idr / 15000, 6),
                        "clicks": clicks,
                        "impressions": impressions,
                        "page_views": page_views,
                        "ctr": round((clicks / impressions * 100), 2) if impressions > 0 else 0,
                        "cpm_idr": round((earnings_idr / impressions * 1000), 2) if impressions > 0 else 0
                    }
                    
                    # Filter by domain if specified
                    if domain is None or domain.lower() in domain_name.lower():
                        domains.append(domain_data)
                        total_earnings += earnings_idr
                        total_clicks += clicks
                        total_impressions += impressions
                        total_page_views += page_views
            
            return {
                "date": target_date.strftime('%Y-%m-%d'),
                "account_id": account_id,
                "filter_domain": domain,
                "domains": sorted(domains, key=lambda x: x['earnings'], reverse=True),
                "summary": {
                    "total_domains": len(domains),
                    "total_earnings_idr": round(total_earnings, 2),
                    "total_earnings_micros": int(total_earnings * 1_000),
                    "total_earnings_usd": round(total_earnings / 15000, 6),
                    "total_clicks": total_clicks,
                    "total_impressions": total_impressions,
                    "total_page_views": total_page_views,
                    "overall_ctr": round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0,
                    "overall_cpm_idr": round((total_earnings / total_impressions * 1000), 2) if total_impressions > 0 else 0
                }
            }
            
        domain_data = await run_in_executor(fetch_domain_earnings)
        return domain_data
        
    except Exception as e:
        logger.error(f"Error fetching domain earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sites/{account_id}", response_model=List[Site])
async def get_sites(account_id: str):
    """Mendapatkan semua sites/domains yang terdaftar di AdSense account."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_sites():
            sites = []
            try:
                request = service.accounts().sites().list(
                    parent=full_account_name,
                    pageSize=50
                )
                
                while request is not None:
                    result = request.execute()
                    if 'sites' in result:
                        for site in result['sites']:
                            sites.append(Site(
                                name=site.get('name', ''),
                                displayName=site.get('displayName', ''),
                                domain=site.get('domain', ''),
                                state=site.get('state', ''),
                                autoAdsEnabled=site.get('autoAdsEnabled')
                            ))
                    request = service.accounts().sites().list_next(request, result)
                
            except Exception as e:
                logger.warning(f"Error fetching sites: {e}")
                # If sites API fails, try to get from ad clients
                try:
                    request = service.accounts().adclients().list(
                        parent=full_account_name,
                        pageSize=50
                    )
                    result = request.execute()
                    if 'adClients' in result:
                        for client in result['adClients']:
                            sites.append(Site(
                                name=client.get('name', ''),
                                displayName=client.get('productCode', 'AdSense for Content'),
                                domain=client.get('name', '').split('/')[-1] if client.get('name') else '',
                                state=client.get('state', 'ACTIVE'),
                                autoAdsEnabled=None
                            ))
                except Exception as e2:
                    logger.warning(f"Error fetching ad clients: {e2}")
            
            return sites
        
        sites = await run_in_executor(fetch_sites)
        return sites
        
    except Exception as e:
        logger.error(f"Error fetching sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recent-earnings/{account_id}")
async def get_recent_earnings(account_id: str, days: Optional[int] = 7):
    """Mendapatkan penghasilan beberapa hari terakhir yang tersedia."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_recent_data():
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            try:
                request = service.accounts().reports().generate(
                    account=full_account_name,
                    dateRange_startDate_year=start_date.year,
                    dateRange_startDate_month=start_date.month,
                    dateRange_startDate_day=start_date.day,
                    dateRange_endDate_year=end_date.year,
                    dateRange_endDate_month=end_date.month,
                    dateRange_endDate_day=end_date.day,
                    metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS'],
                    dimensions=['DATE']
                )
                report = request.execute()
                
                daily_data = {}
                total_earnings = total_clicks = total_impressions = total_page_views = 0
                
                if 'rows' in report and report['rows']:
                    for row in report['rows']:
                        if len(row) >= 5:  # DATE + 4 metrics
                            date = row[0]
                            earnings = convert_micros_to_dollars(float(row[1] or 0))
                            clicks = int(row[2] or 0)
                            impressions = int(row[3] or 0)
                            page_views = int(row[4] or 0)
                            
                            daily_data[date] = {
                                "date": date,
                                "earnings": round(earnings, 2),
                                "clicks": clicks,
                                "impressions": impressions,
                                "page_views": page_views,
                                "ctr": round((clicks / impressions * 100) if impressions > 0 else 0, 2),
                                "cpm": round((earnings / impressions * 1000) if impressions > 0 else 0, 2)
                            }
                            
                            total_earnings += earnings
                            total_clicks += clicks
                            total_impressions += impressions
                            total_page_views += page_views
                
                # Fill missing dates with zeros
                daily_list = []
                current_date = start_date
                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    if date_str in daily_data:
                        daily_list.append(daily_data[date_str])
                    else:
                        daily_list.append({
                            "date": date_str,
                            "earnings": 0.0,
                            "clicks": 0,
                            "impressions": 0,
                            "page_views": 0,
                            "ctr": 0.0,
                            "cpm": 0.0
                        })
                    current_date += timedelta(days=1)
                
                return {
                    "account_id": account_id,
                    "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    "total_days": days,
                    "daily_data": daily_list,
                    "summary": {
                        "total_earnings": round(total_earnings, 2),
                        "total_clicks": total_clicks,
                        "total_impressions": total_impressions,
                        "total_page_views": total_page_views,
                        "average_daily_earnings": round(total_earnings / days, 2),
                        "overall_ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                        "overall_cpm": round((total_earnings / total_impressions * 1000) if total_impressions > 0 else 0, 2)
                    },
                    "note": "Data yang tersedia dalam periode ini"
                }
                
            except Exception as e:
                logger.error(f"Error fetching recent earnings: {e}")
                raise e
        
        result = await run_in_executor(fetch_recent_data)
        return result
        
    except Exception as e:
        logger.error(f"Error in recent earnings endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/earnings-trend/{account_id}")
async def get_earnings_trend(
    account_id: str,
    days: Optional[int] = 7
):
    """Mendapatkan trend penghasilan untuk beberapa hari terakhir."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_earnings_trend():
            trend_data = []
            end_date = datetime.now()
            
            for i in range(days):
                date = end_date - timedelta(days=i)
                try:
                    request = service.accounts().reports().generate(
                        account=full_account_name,
                        dateRange_startDate_year=date.year,
                        dateRange_startDate_month=date.month,
                        dateRange_startDate_day=date.day,
                        dateRange_endDate_year=date.year,
                        dateRange_endDate_month=date.month,
                        dateRange_endDate_day=date.day,
                        metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS'],
                        dimensions=['DATE']
                    )
                    report = request.execute()
                    
                    earnings = 0.0
                    clicks = 0
                    impressions = 0
                    
                    if 'rows' in report and report['rows']:
                        for row in report['rows']:
                            if len(row) >= 4:  # DATE + 3 metrics
                                earnings += convert_micros_to_dollars(float(row[1] or 0))
                                clicks += int(row[2] or 0)
                                impressions += int(row[3] or 0)
                    
                    trend_data.append({
                        "date": date.strftime('%Y-%m-%d'),
                        "earnings": round(earnings, 2),
                        "clicks": clicks,
                        "impressions": impressions
                    })
                    
                except Exception as e:
                    logger.warning(f"Error fetching data for {date.strftime('%Y-%m-%d')}: {e}")
                    trend_data.append({
                        "date": date.strftime('%Y-%m-%d'),
                        "earnings": 0.0,
                        "clicks": 0,
                        "impressions": 0
                    })
            
            return sorted(trend_data, key=lambda x: x['date'])
        
        trend = await run_in_executor(fetch_earnings_trend)
        
        return {
            "account_id": account_id,
            "period_days": days,
            "trend": trend,
            "total_earnings": sum(item["earnings"] for item in trend),
            "total_clicks": sum(item["clicks"] for item in trend),
            "total_impressions": sum(item["impressions"] for item in trend)
        }
        
    except Exception as e:
        logger.error(f"Error fetching earnings trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/earnings-by-site/{account_id}")
async def get_earnings_by_site(
    account_id: str, 
    days: Optional[int] = 7,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Mendapatkan breakdown earnings per site/domain."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        # Set date range
        if not end_date:
            end_date_obj = datetime.now()
            end_date = end_date_obj.strftime('%Y-%m-%d')
        else:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            
        if not start_date:
            start_date_obj = end_date_obj - timedelta(days=days)
            start_date = start_date_obj.strftime('%Y-%m-%d')
        else:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        
        def fetch_earnings_by_site():
            try:
                # Try to get earnings breakdown by HOSTED_AD_CLIENT_ID (which represents different sites)
                request = service.accounts().reports().generate(
                    account=full_account_name,
                    dateRange_startDate_year=start_date_obj.year,
                    dateRange_startDate_month=start_date_obj.month,
                    dateRange_startDate_day=start_date_obj.day,
                    dateRange_endDate_year=end_date_obj.year,
                    dateRange_endDate_month=end_date_obj.month,
                    dateRange_endDate_day=end_date_obj.day,
                    dimensions=['HOSTED_AD_CLIENT_ID'],
                    metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
                )
                report = request.execute()
                
                sites_data = []
                total_earnings = total_clicks = total_impressions = total_page_views = 0
                
                if 'rows' in report and report['rows']:
                    for row in report['rows']:
                        if len(row) >= 5:  # HOSTED_AD_CLIENT_ID + 4 metrics
                            site_id = row[0]
                            earnings = convert_micros_to_dollars(float(row[1] or 0))
                            clicks = int(row[2] or 0)
                            impressions = int(row[3] or 0)
                            page_views = int(row[4] or 0)
                            
                            ctr = (clicks / impressions * 100) if impressions > 0 else 0
                            cpm = (earnings / impressions * 1000) if impressions > 0 else 0
                            
                            sites_data.append({
                                "site_id": site_id,
                                "site_name": site_id.replace('ca-host-', '').replace('ca-', ''),  # Clean up site ID
                                "earnings": round(earnings, 2),
                                "clicks": clicks,
                                "impressions": impressions,
                                "page_views": page_views,
                                "ctr": round(ctr, 2),
                                "cpm": round(cpm, 2)
                            })
                            
                            total_earnings += earnings
                            total_clicks += clicks
                            total_impressions += impressions
                            total_page_views += page_views
                
                # If no data with HOSTED_AD_CLIENT_ID, try with AD_UNIT_NAME
                if not sites_data:
                    try:
                        request = service.accounts().reports().generate(
                            account=full_account_name,
                            dateRange_startDate_year=start_date_obj.year,
                            dateRange_startDate_month=start_date_obj.month,
                            dateRange_startDate_day=start_date_obj.day,
                            dateRange_endDate_year=end_date_obj.year,
                            dateRange_endDate_month=end_date_obj.month,
                            dateRange_endDate_day=end_date_obj.day,
                            dimensions=['AD_UNIT_NAME'],
                            metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS']
                        )
                        report = request.execute()
                        
                        if 'rows' in report and report['rows']:
                            for row in report['rows']:
                                if len(row) >= 4:
                                    ad_unit = row[0]
                                    earnings = convert_micros_to_dollars(float(row[1] or 0))
                                    clicks = int(row[2] or 0)
                                    impressions = int(row[3] or 0)
                                    
                                    ctr = (clicks / impressions * 100) if impressions > 0 else 0
                                    cpm = (earnings / impressions * 1000) if impressions > 0 else 0
                                    
                                    sites_data.append({
                                        "site_id": ad_unit,
                                        "site_name": ad_unit,
                                        "earnings": round(earnings, 2),
                                        "clicks": clicks,
                                        "impressions": impressions,
                                        "page_views": 0,  # Not available in this dimension
                                        "ctr": round(ctr, 2),
                                        "cpm": round(cpm, 2)
                                    })
                                    
                                    total_earnings += earnings
                                    total_clicks += clicks
                                    total_impressions += impressions
                    except Exception as e:
                        logger.warning(f"Error fetching by AD_UNIT_NAME: {e}")
                
                # Sort by earnings descending
                sites_data.sort(key=lambda x: x['earnings'], reverse=True)
                
                return {
                    "account_id": account_id,
                    "period": f"{start_date} to {end_date}",
                    "sites_count": len(sites_data),
                    "sites_data": sites_data,
                    "summary": {
                        "total_earnings": round(total_earnings, 2),
                        "total_clicks": total_clicks,
                        "total_impressions": total_impressions,
                        "total_page_views": total_page_views,
                        "overall_ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                        "overall_cpm": round((total_earnings / total_impressions * 1000) if total_impressions > 0 else 0, 2)
                    },
                    "note": "Breakdown earnings per site/domain berdasarkan data yang tersedia"
                }
                
            except Exception as e:
                logger.error(f"Error fetching earnings by site: {e}")
                # Return aggregate data if breakdown fails
                try:
                    request = service.accounts().reports().generate(
                        account=full_account_name,
                        dateRange_startDate_year=start_date_obj.year,
                        dateRange_startDate_month=start_date_obj.month,
                        dateRange_startDate_day=start_date_obj.day,
                        dateRange_endDate_year=end_date_obj.year,
                        dateRange_endDate_month=end_date_obj.month,
                        dateRange_endDate_day=end_date_obj.day,
                        metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
                    )
                    report = request.execute()
                    
                    total_earnings = total_clicks = total_impressions = total_page_views = 0
                    if 'rows' in report and report['rows']:
                        for row in report['rows']:
                            if len(row) >= 4:
                                total_earnings += convert_micros_to_dollars(float(row[0] or 0))
                                total_clicks += int(row[1] or 0)
                                total_impressions += int(row[2] or 0)
                                total_page_views += int(row[3] or 0)
                    
                    return {
                        "account_id": account_id,
                        "period": f"{start_date} to {end_date}",
                        "sites_count": 1,
                        "sites_data": [{
                            "site_id": "aggregate",
                            "site_name": "All Sites (Aggregate)",
                            "earnings": round(total_earnings, 2),
                            "clicks": total_clicks,
                            "impressions": total_impressions,
                            "page_views": total_page_views,
                            "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                            "cpm": round((total_earnings / total_impressions * 1000) if total_impressions > 0 else 0, 2)
                        }],
                        "summary": {
                            "total_earnings": round(total_earnings, 2),
                            "total_clicks": total_clicks,
                            "total_impressions": total_impressions,
                            "total_page_views": total_page_views,
                            "overall_ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                            "overall_cpm": round((total_earnings / total_impressions * 1000) if total_impressions > 0 else 0, 2)
                        },
                        "note": "Data breakdown per site tidak tersedia, menampilkan data aggregate. Ini normal untuk beberapa setup AdSense."
                    }
                except Exception as e2:
                    logger.error(f"Error fetching aggregate data: {e2}")
                    raise e2
        
        result = await run_in_executor(fetch_earnings_by_site)
        return result
        
    except Exception as e:
        logger.error(f"Error in earnings by site endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/all-domains/{account_id}")
async def get_all_domains(account_id: str):
    """Mendapatkan semua domain/subdomain yang terdaftar di AdSense dengan earnings terbaru."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_all_domains():
            domains_info = []
            
            try:
                # Get sites first
                sites_request = service.accounts().sites().list(
                    parent=full_account_name,
                    pageSize=50
                )
                
                sites_result = sites_request.execute()
                
                if 'sites' in sites_result:
                    for site in sites_result['sites']:
                        domain = site.get('domain', '')
                        
                        # Try to get recent earnings for this domain
                        try:
                            end_date = datetime.now()
                            start_date = end_date - timedelta(days=7)
                            
                            # Note: AdSense API doesn't support filtering by specific domain directly
                            # This is a limitation of the API structure
                            domains_info.append({
                                "domain": domain,
                                "display_name": site.get('displayName', domain),
                                "state": site.get('state', 'UNKNOWN'),
                                "auto_ads_enabled": site.get('autoAdsEnabled', False),
                                "site_id": site.get('name', ''),
                                "note": "Individual domain earnings require manual tracking or Google Analytics integration"
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error fetching earnings for domain {domain}: {e}")
                            domains_info.append({
                                "domain": domain,
                                "display_name": site.get('displayName', domain),
                                "state": site.get('state', 'UNKNOWN'),
                                "auto_ads_enabled": site.get('autoAdsEnabled', False),
                                "site_id": site.get('name', ''),
                                "earnings_last_7_days": 0,
                                "note": "Earnings data not available"
                            })
                
                # If no sites found, try to infer from ad clients
                if not domains_info:
                    try:
                        adclients_request = service.accounts().adclients().list(
                            parent=full_account_name
                        )
                        adclients_result = adclients_request.execute()
                        
                        if 'adClients' in adclients_result:
                            for client in adclients_result['adClients']:
                                domains_info.append({
                                    "domain": "Domain information not available via API",
                                    "display_name": client.get('productCode', 'AdSense Client'),
                                    "state": client.get('state', 'ACTIVE'),
                                    "auto_ads_enabled": None,
                                    "site_id": client.get('name', ''),
                                    "note": "Specific domain breakdown requires manual configuration"
                                })
                    except Exception as e:
                        logger.warning(f"Error fetching ad clients: {e}")
                
                return {
                    "account_id": account_id,
                    "domains_count": len(domains_info),
                    "domains": domains_info,
                    "api_limitation_note": "AdSense API memiliki keterbatasan dalam memberikan breakdown earnings per domain secara langsung. Untuk tracking yang lebih detail per subdomain, Anda perlu:",
                    "recommendations": [
                        "Gunakan Google Analytics 4 yang diintegrasikan dengan AdSense",
                        "Setup custom channels per domain di AdSense dashboard",
                        "Gunakan UTM parameters untuk tracking yang lebih detail",
                        "Implementasi tracking manual di level aplikasi"
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error fetching domains: {e}")
                return {
                    "account_id": account_id,
                    "domains_count": 0,
                    "domains": [],
                    "error_note": "Tidak dapat mengambil data domain. Ini mungkin karena keterbatasan API atau konfigurasi account.",
                    "alternative_solution": "Cek breakdown earnings menggunakan endpoint /api/earnings-by-site yang mungkin memberikan informasi lebih detail."
                }
        
        result = await run_in_executor(fetch_all_domains)
        return result
        
    except Exception as e:
        logger.error(f"Error in all domains endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/subdomain-analysis/{account_id}")
async def get_subdomain_analysis(account_id: str):
    """Analisis subdomain berdasarkan data yang tersedia dan memberikan rekomendasi setup."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def analyze_subdomains():
            analysis = {
                "account_id": account_id,
                "main_domain": "perpustakaan.id",  # From your data
                "detected_subdomains": [],
                "potential_subdomains": [
                    "www.perpustakaan.id",
                    "blog.perpustakaan.id", 
                    "api.perpustakaan.id",
                    "admin.perpustakaan.id",
                    "m.perpustakaan.id"
                ],
                "analysis_results": {},
                "recommendations": []
            }
            
            # Try to get ad units to infer potential subdomains
            try:
                adunits_request = service.accounts().adclients().adunits().list(
                    parent=f"{full_account_name}/adclients/-",
                    pageSize=50
                )
                
                adunits_result = adunits_request.execute()
                ad_units = []
                
                if 'adUnits' in adunits_result:
                    for unit in adunits_result['adUnits']:
                        ad_units.append({
                            "name": unit.get('displayName', ''),
                            "id": unit.get('name', ''),
                            "state": unit.get('state', ''),
                            "type": unit.get('contentAdsSettings', {}).get('type', 'UNKNOWN')
                        })
                
                analysis["ad_units_count"] = len(ad_units)
                analysis["ad_units"] = ad_units
                
                # Analyze patterns in ad unit names to detect potential subdomains
                detected_patterns = set()
                for unit in ad_units:
                    name = unit["name"].lower()
                    if "blog" in name:
                        detected_patterns.add("blog.perpustakaan.id")
                    if "api" in name:
                        detected_patterns.add("api.perpustakaan.id")
                    if "mobile" in name or "m." in name:
                        detected_patterns.add("m.perpustakaan.id")
                    if "admin" in name:
                        detected_patterns.add("admin.perpustakaan.id")
                
                analysis["detected_subdomains"] = list(detected_patterns)
                
            except Exception as e:
                logger.warning(f"Error analyzing ad units: {e}")
                analysis["ad_units_count"] = 0
                analysis["ad_units"] = []
            
            # Try to get custom channels
            try:
                channels_request = service.accounts().adclients().customchannels().list(
                    parent=f"{full_account_name}/adclients/-",
                    pageSize=50
                )
                channels_result = channels_request.execute()
                
                custom_channels = []
                if 'customChannels' in channels_result:
                    for channel in channels_result['customChannels']:
                        custom_channels.append({
                            "name": channel.get('displayName', ''),
                            "id": channel.get('name', ''),
                            "targeting_type": channel.get('targetingType', 'URL_TARGETING')
                        })
                
                analysis["custom_channels_count"] = len(custom_channels)
                analysis["custom_channels"] = custom_channels
                
            except Exception as e:
                logger.warning(f"Error fetching custom channels: {e}")
                analysis["custom_channels_count"] = 0
                analysis["custom_channels"] = []
            
            # Generate recommendations based on findings
            recommendations = [
                {
                    "priority": "HIGH",
                    "title": "Setup Custom Channels per Subdomain",
                    "description": "Buat custom channel terpisah untuk setiap subdomain di AdSense dashboard",
                    "steps": [
                        "Login ke AdSense dashboard",
                        "Buka Sites → Channels",
                        "Klik 'Add channel' → 'Custom channel'",
                        "Buat channel untuk setiap subdomain (blog, api, admin, dll)",
                        "Assign ad units ke channel yang sesuai"
                    ]
                },
                {
                    "priority": "MEDIUM", 
                    "title": "Implement URL-based Tracking",
                    "description": "Tambahkan parameter tracking di ad code untuk membedakan subdomain",
                    "technical_solution": "Gunakan data attributes atau URL parameters di ad code"
                },
                {
                    "priority": "HIGH",
                    "title": "Google Analytics 4 Integration",
                    "description": "Integrasikan GA4 dengan AdSense untuk tracking yang lebih detail",
                    "benefits": "Dapat melihat performance per page/subdomain di GA4"
                }
            ]
            
            analysis["recommendations"] = recommendations
            
            # Summary analysis
            analysis["analysis_results"] = {
                "has_multiple_subdomains": len(analysis["detected_subdomains"]) > 0,
                "tracking_setup_needed": analysis["custom_channels_count"] == 0,
                "estimated_subdomains": len(analysis["potential_subdomains"]),
                "current_tracking_level": "BASIC" if analysis["custom_channels_count"] == 0 else "ADVANCED"
            }
            
            return analysis
        
        result = await run_in_executor(analyze_subdomains)
        return result
        
    except Exception as e:
        logger.error(f"Error in subdomain analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/custom-channels/{account_id}")
async def get_custom_channels(account_id: str):
    """Mendapatkan semua custom channels dan earnings breakdown-nya."""
    try:
        service = get_adsense_service()
        full_account_name = f"accounts/{account_id}"
        
        def fetch_channels_data():
            channels_data = {
                "account_id": account_id,
                "channels": [],
                "earnings_by_channel": {},
                "setup_guide": {}
            }
            
            try:
                # Get all custom channels
                channels_request = service.accounts().adclients().customchannels().list(
                    parent=f"{full_account_name}/adclients/-",
                    pageSize=50
                )
                channels_result = channels_request.execute()
                
                if 'customChannels' in channels_result:
                    for channel in channels_result['customChannels']:
                        channel_info = {
                            "name": channel.get('displayName', ''),
                            "id": channel.get('name', ''),
                            "targeting_type": channel.get('targetingType', 'URL_TARGETING'),
                            "active": channel.get('active', True)
                        }
                        channels_data["channels"].append(channel_info)
                        
                        # Try to get earnings for this channel (last 7 days)
                        try:
                            end_date = datetime.now()
                            start_date = end_date - timedelta(days=7)
                            
                            earnings_request = service.accounts().reports().generate(
                                account=full_account_name,
                                dateRange_startDate_year=start_date.year,
                                dateRange_startDate_month=start_date.month,
                                dateRange_startDate_day=start_date.day,  
                                dateRange_endDate_year=end_date.year,
                                dateRange_endDate_month=end_date.month,
                                dateRange_endDate_day=end_date.day,
                                dimensions=['CUSTOM_CHANNEL_NAME'],
                                metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS'],
                                filters=[f'CUSTOM_CHANNEL_NAME=={channel.get("displayName", "")}']
                            )
                            earnings_result = earnings_request.execute()
                            
                            channel_earnings = {"earnings": 0, "clicks": 0, "impressions": 0}
                            if 'rows' in earnings_result and earnings_result['rows']:
                                for row in earnings_result['rows']:
                                    if len(row) >= 4:
                                        channel_earnings = {
                                            "earnings": convert_micros_to_dollars(float(row[1] or 0)),
                                            "clicks": int(row[2] or 0),
                                            "impressions": int(row[3] or 0)
                                        }
                            
                            channels_data["earnings_by_channel"][channel.get('displayName', '')] = channel_earnings
                            
                        except Exception as e:
                            logger.warning(f"Error fetching earnings for channel {channel.get('displayName', '')}: {e}")
                            channels_data["earnings_by_channel"][channel.get('displayName', '')] = {
                                "earnings": 0, "clicks": 0, "impressions": 0, "error": str(e)
                            }
                
                channels_data["channels_count"] = len(channels_data["channels"])
                
                # If no custom channels found, provide setup guide
                if len(channels_data["channels"]) == 0:
                    channels_data["setup_guide"] = {
                        "title": "Setup Custom Channels untuk Tracking Subdomain",
                        "steps": [
                            {
                                "step": 1,
                                "title": "Login ke AdSense Dashboard",
                                "url": "https://www.google.com/adsense/"
                            },
                            {
                                "step": 2, 
                                "title": "Buka Sites → Channels",
                                "description": "Navigate ke menu Sites, lalu pilih Channels"
                            },
                            {
                                "step": 3,
                                "title": "Add Custom Channel",
                                "description": "Klik 'Add channel' → 'Custom channel'"
                            },
                            {
                                "step": 4,
                                "title": "Create Channels per Subdomain",
                                "suggested_channels": [
                                    "Blog - blog.perpustakaan.id",
                                    "API - api.perpustakaan.id", 
                                    "Admin - admin.perpustakaan.id",
                                    "Mobile - m.perpustakaan.id",
                                    "Main - www.perpustakaan.id"
                                ]
                            },
                            {
                                "step": 5,
                                "title": "Setup URL Targeting",
                                "description": "Gunakan URL patterns untuk setiap channel, misal: blog.perpustakaan.id/*"
                            },
                            {
                                "step": 6,
                                "title": "Assign Ad Units",
                                "description": "Assign ad units yang ada ke channel yang sesuai"
                            }
                        ],
                        "expected_result": "Setelah setup, API ini akan menampilkan breakdown earnings per channel/subdomain"
                    }
                
                return channels_data
                
            except Exception as e:
                logger.error(f"Error fetching custom channels: {e}")
                return {
                    "account_id": account_id,
                    "channels_count": 0,
                    "channels": [],
                    "error": str(e),
                    "note": "Custom channels belum di-setup atau API tidak bisa mengaksesnya"
                }
        
        result = await run_in_executor(fetch_channels_data)
        return result
        
    except Exception as e:
        logger.error(f"Error in custom channels endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/subdomain-setup-guide")
async def get_subdomain_setup_guide():
    """Panduan lengkap untuk setup tracking subdomain di AdSense."""
    return {
        "title": "Panduan Setup Tracking Subdomain AdSense",
        "problem": "AdSense API v2 tidak mendukung breakdown earnings per subdomain secara otomatis",
        "limitations": {
            "api_limitations": [
                "AdSense API menganggap semua subdomain sebagai 1 domain utama",
                "Tidak ada filter bawaan untuk earnings per subdomain",
                "Data reporting hanya berdasarkan domain yang terdaftar di AdSense"
            ],
            "current_setup": "Saat ini hanya perpustakaan.id yang terdaftar di AdSense account"
        },
        "solutions": {
            "solution_1": {
                "name": "Custom Channels (Recommended)",
                "steps": [
                    "Login ke dashboard AdSense (adsense.google.com)",
                    "Navigasi ke Sites > Overview > Custom channels",
                    "Klik 'Create custom channel'",
                    "Buat channel untuk setiap subdomain:",
                    "  - blog.perpustakaan.id",
                    "  - api.perpustakaan.id", 
                    "  - admin.perpustakaan.id",
                    "Setup URL targeting untuk setiap channel",
                    "Tunggu 24-48 jam untuk data muncul"
                ],
                "benefits": [
                    "Tracking earnings per subdomain",
                    "Data tersedia via API",
                    "Historical reporting"
                ]
            },
            "solution_2": {
                "name": "Google Analytics 4 Integration",
                "steps": [
                    "Setup Google Analytics 4 untuk setiap subdomain",
                    "Link GA4 dengan AdSense account",
                    "Enable AdSense reporting in GA4",
                    "Use GA4 Reporting API untuk data detail"
                ],
                "benefits": [
                    "Detailed traffic analysis per subdomain",
                    "AdSense earnings breakdown",
                    "Advanced segmentation"
                ]
            },
            "solution_3": {
                "name": "Manual Tracking Implementation",
                "steps": [
                    "Implement UTM parameters di setiap subdomain",
                    "Setup Google Tag Manager per subdomain",
                    "Create custom dimensions dalam GA4",
                    "Build custom reporting dashboard"
                ],
                "benefits": [
                    "Complete control over tracking",
                    "Real-time data",
                    "Custom metrics"
                ]
            }
        },
        "quick_implementation": {
            "immediate_steps": [
                "1. Buat Custom Channels di AdSense dashboard",
                "2. Setup URL targeting per subdomain",
                "3. Tunggu 24-48 jam untuk data collection",
                "4. Test dengan endpoint /api/custom-channels/{account_id}"
            ],
            "alternative_endpoint": "/api/earnings-by-site/{account_id} - untuk melihat breakdown yang sudah tersedia"
        },
        "api_enhancement_needed": {
            "note": "Untuk tracking subdomain yang lebih baik, aplikasi ini perlu:",
            "enhancements": [
                "Integration dengan Google Analytics Reporting API",
                "Setup custom database untuk manual tracking",
                "Implementation of UTM parameter tracking",
                "Custom dashboard untuk breakdown per subdomain"
            ]
        },
        "contact_info": {
            "message": "Jika ingin implementasi tracking subdomain yang lebih advanced, perlu development tambahan untuk integrasi dengan Google Analytics API atau setup custom tracking system."
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )