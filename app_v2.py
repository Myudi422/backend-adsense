#!/usr/bin/env python3
"""
Multi-Account AdSense API Manager
Supports multiple AdSense accounts with proper micros to IDR conversion
"""

from fastapi import FastAPI, HTTPException, Query, Path, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
import logging
import os
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from enum import Enum
import tempfile
import shutil

# Import AdSense utilities
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from googleapiclient import discovery
import google.auth.exceptions
import google.auth.transport.requests

# Import account database
from account_database import get_account_database
from cache_manager import get_cache_manager, cache_key_for_earnings, cache_key_for_domain_earnings, cache_key_for_summary

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="Multi-Account AdSense API v2.0",
    description="""
    🚀 **Comprehensive AdSense Management API**
    
    Advanced backend API untuk mengakses multiple Google AdSense accounts dengan:
    
    * ✅ **Proper IDR Conversion**: Micros ÷ 1,000 = IDR
    * 📊 **Multi-Account Support**: Perpustakaan.id + GowesGo.com  
    * 📅 **Flexible Date Filtering**: Today, yesterday, custom dates
    * 🌐 **Domain Breakdown**: Detailed subdomain analytics
    * 🔄 **Auto-Retry Logic**: Falls back to recent data if current day empty
    * 📈 **Comprehensive Metrics**: Earnings, clicks, CTR, CPM, impressions
    
    ## 🏢 Supported Accounts
    - **perpustakaan**: Perpustakaan.id (pub-1777593071761494)
    - **gowesgo**: GowesGo.com (pub-1315457334560058)
    
    ## 📊 Data Sources
    All data retrieved from Google AdSense Management API v2 with proper OAuth 2.0 authentication.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "AdSense API Support",
        "url": "https://developers.google.com/adsense/management/",
    },
    license_info={
        "name": "AdSense Management API",
        "url": "https://developers.google.com/adsense/management/",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
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

# Initialize account database
account_db = get_account_database()

# Dynamic account configurations from JSON database
def get_account_configs():
    """Get current account configurations from database."""
    configs = {}
    for account_key, account_data in account_db.get_all_accounts().items():
        configs[account_key] = {
            "client_secrets": account_data.get("client_secrets"),
            "credentials_file": account_data.get("credentials_file"),
            "display_name": account_data.get("display_name"),
            "account_id": account_data.get("account_id")
        }
    return configs

# Legacy compatibility function
def ACCOUNT_CONFIGS():
    return get_account_configs()

# Get current configurations
ACCOUNT_CONFIGS = get_account_configs()

# Enums for API
class DateFilter(str, Enum):
    today = "today"
    yesterday = "yesterday"
    custom = "custom"
    range = "range"

class AccountKey(str, Enum):
    perpustakaan = "perpustakaan"
    gowesgo = "gowesgo"
    # Note: Dynamic accounts will be validated at runtime

# Account Management Models
class NewAccountRequest(BaseModel):
    """Request model for adding new AdSense account."""
    account_key: str = Field(..., description="Unique account identifier", example="newaccount")
    display_name: str = Field(..., description="Human-readable account name", example="NewSite.com")
    description: Optional[str] = Field(None, description="Optional account description")

class AccountSetupResponse(BaseModel):
    """Response model for account setup process."""
    success: bool = Field(..., description="Whether setup was successful")
    account_key: str = Field(..., description="Account identifier")
    message: str = Field(..., description="Status message")
    oauth_url: Optional[str] = Field(None, description="OAuth authorization URL if needed")
    next_steps: List[str] = Field(..., description="Next steps to complete setup")

class AccountValidationResponse(BaseModel):
    """Response model for account validation."""
    valid: bool = Field(..., description="Whether account is valid")
    account_key: str = Field(..., description="Account identifier")
    publisher_id: Optional[str] = Field(None, description="Google AdSense publisher ID if valid")
    status: str = Field(..., description="Account status")
    error: Optional[str] = Field(None, description="Error message if validation failed")

# Enhanced Pydantic models with documentation
class AccountInfo(BaseModel):
    """Information about a configured AdSense account."""
    account_key: str = Field(..., description="Internal account identifier", example="perpustakaan")
    account_id: str = Field(..., description="Google AdSense publisher ID", example="pub-1777593071761494")
    display_name: str = Field(..., description="Human-readable account name", example="perpustakaan.id")
    status: str = Field(..., description="Account status", example="active")
    
    class Config:
        schema_extra = {
            "example": {
                "account_key": "perpustakaan",
                "account_id": "pub-1777593071761494", 
                "display_name": "perpustakaan.id",
                "status": "active"
            }
        }

class DomainEarnings(BaseModel):
    """Earnings breakdown for a specific domain."""
    domain: str = Field(..., description="Domain name", example="perpustakaan.id")
    earnings_idr: float = Field(..., description="Earnings in Indonesian Rupiah", example=2.20)
    earnings_micros: int = Field(..., description="Raw earnings in micros format", example=2199)
    clicks: int = Field(..., description="Number of ad clicks", example=8)
    impressions: int = Field(..., description="Number of ad impressions", example=830)
    page_views: int = Field(..., description="Number of page views", example=362)
    ctr: float = Field(..., description="Click-through rate as percentage", example=0.96)
    cpm_idr: float = Field(..., description="Cost per mille (CPM) in IDR", example=2.65)
    rpm_idr: float = Field(..., description="Revenue per 1000 page views in IDR", example=6.08)
    
    class Config:
        schema_extra = {
            "example": {
                "domain": "perpustakaan.id",
                "earnings_idr": 2.20,
                "earnings_micros": 2199,
                "clicks": 8,
                "impressions": 830,
                "page_views": 362,
                "ctr": 0.96,
                "cpm_idr": 2.65,
                "rpm_idr": 6.08
            }
        }

class TodayEarnings(BaseModel):
    """Daily earnings summary for an account."""
    date: str = Field(..., description="Date of the data in YYYY-MM-DD format", example="2025-10-03")
    account_key: str = Field(..., description="Account identifier", example="perpustakaan")
    account_id: str = Field(..., description="Google AdSense publisher ID", example="pub-1777593071761494")
    earnings_idr: float = Field(..., description="Total earnings in Indonesian Rupiah", example=3.23)
    earnings_micros: int = Field(..., description="Raw earnings in micros format", example=3229)
    clicks: int = Field(..., description="Total ad clicks", example=9)
    impressions: int = Field(..., description="Total ad impressions", example=930)
    page_views: int = Field(..., description="Total page views", example=412)
    ctr: float = Field(..., description="Click-through rate as percentage", example=0.97)
    cpm_idr: float = Field(..., description="Cost per mille (CPM) in IDR", example=3.47)
    rpm_idr: float = Field(..., description="Revenue per 1000 page views in IDR", example=7.84)
    data_age_days: int = Field(..., description="Age of data in days (0=today, 1=yesterday)", example=1)
    note: str = Field(..., description="Additional information about the data", example="Data terbaru dari 1 hari yang lalu")
    
    class Config:
        schema_extra = {
            "example": {
                "date": "2025-10-03",
                "account_key": "perpustakaan",
                "account_id": "pub-1777593071761494",
                "earnings_idr": 3.23,
                "earnings_micros": 3229,
                "clicks": 9,
                "impressions": 930,
                "page_views": 412,
                "ctr": 0.97,
                "cpm_idr": 3.47,
                "rpm_idr": 7.84,
                "data_age_days": 1,
                "note": "Data terbaru dari 1 hari yang lalu"
            }
        }

class RPMData(BaseModel):
    """RPM (Revenue per Mille) data for a specific account."""
    date: str = Field(..., description="Date of the data in YYYY-MM-DD format", example="2025-10-03")
    account_key: str = Field(..., description="Account identifier", example="perpustakaan")
    account_id: str = Field(..., description="Google AdSense publisher ID", example="pub-1777593071761494")
    earnings_idr: float = Field(..., description="Total earnings in Indonesian Rupiah", example=3.23)
    earnings_micros: int = Field(..., description="Raw earnings in micros format", example=3229)
    page_views: int = Field(..., description="Total page views", example=412)
    rpm_idr: float = Field(..., description="Revenue per 1000 page views in IDR", example=7.84)
    impressions: int = Field(..., description="Total ad impressions", example=930)
    clicks: int = Field(..., description="Total ad clicks", example=9)
    ctr: float = Field(..., description="Click-through rate as percentage", example=0.97)
    cpm_idr: float = Field(..., description="Cost per mille (CPM) in IDR", example=3.47)
    data_age_days: int = Field(..., description="Age of data in days (0=today, 1=yesterday)", example=1)
    note: str = Field(..., description="Additional information about the data", example="Data terbaru dari 1 hari yang lalu")
    
    class Config:
        schema_extra = {
            "example": {
                "date": "2025-10-03",
                "account_key": "perpustakaan", 
                "account_id": "pub-1777593071761494",
                "earnings_idr": 3.23,
                "earnings_micros": 3229,
                "page_views": 412,
                "rpm_idr": 7.84,
                "impressions": 930,
                "clicks": 9,
                "ctr": 0.97,
                "cpm_idr": 3.47,
                "data_age_days": 1,
                "note": "Data terbaru dari 1 hari yang lalu"
            }
        }

class DomainSummary(BaseModel):
    """Summary statistics for domain earnings."""
    total_domains: int = Field(..., description="Number of domains", example=10)
    total_earnings_idr: float = Field(..., description="Total earnings across all domains", example=3.23)
    total_earnings_micros: int = Field(..., description="Total earnings in micros", example=3230)
    total_clicks: int = Field(..., description="Total clicks across all domains", example=9)
    total_impressions: int = Field(..., description="Total impressions across all domains", example=930)
    total_page_views: int = Field(..., description="Total page views across all domains", example=412)
    overall_ctr: float = Field(..., description="Overall click-through rate", example=0.97)
    overall_cpm_idr: float = Field(..., description="Overall CPM in IDR", example=3.47)

class DomainBreakdownResponse(BaseModel):
    """Complete domain breakdown response."""
    date: str = Field(..., description="Date of the data", example="2025-10-03")
    account_key: str = Field(..., description="Account identifier", example="perpustakaan")
    account_id: str = Field(..., description="AdSense publisher ID", example="pub-1777593071761494")
    domain_filter: Optional[str] = Field(None, description="Applied domain filter", example=None)
    domains: List[DomainEarnings] = Field(..., description="List of domain earnings")
    summary: DomainSummary = Field(..., description="Summary statistics")

class AccountSummary(BaseModel):
    """Individual account summary for multi-account response."""
    account_key: str = Field(..., description="Account identifier", example="perpustakaan")
    account_id: str = Field(..., description="AdSense publisher ID", example="pub-1777593071761494")
    display_name: str = Field(..., description="Account display name", example="perpustakaan.id")
    status: str = Field(..., description="Account status", example="active")
    earnings_idr: float = Field(..., description="Account earnings", example=3.23)
    earnings_micros: int = Field(..., description="Account earnings in micros format", example=3230)
    clicks: int = Field(..., description="Account clicks", example=9)
    impressions: int = Field(..., description="Account impressions", example=930)
    page_views: int = Field(..., description="Account page views", example=412)
    rpm_idr: float = Field(..., description="Revenue per 1000 page views in IDR", example=7.84)

class MultiAccountSummary(BaseModel):
    """Multi-account summary response."""
    date: str = Field(..., description="Date of the data", example="2025-10-03")
    total_accounts: int = Field(..., description="Number of accounts", example=2)
    total_earnings_idr: float = Field(..., description="Combined earnings from all accounts", example=134.24)
    total_earnings_micros: int = Field(..., description="Combined earnings in micros format", example=134240)
    total_clicks: int = Field(..., description="Combined clicks from all accounts", example=77)
    total_impressions: int = Field(..., description="Combined impressions from all accounts", example=3437)
    total_page_views: int = Field(..., description="Combined page views from all accounts", example=1548)
    overall_ctr: float = Field(..., description="Overall click-through rate", example=2.24)
    overall_cpm_idr: float = Field(..., description="Overall CPM in IDR", example=39.06)
    overall_rpm_idr: float = Field(..., description="Overall RPM in IDR", example=86.71)
    accounts: List[AccountSummary] = Field(..., description="Individual account summaries")
    
    class Config:
        schema_extra = {
            "example": {
                "date": "2025-10-03", 
                "total_accounts": 2,
                "total_earnings_idr": 134.24,
                "total_earnings_micros": 134240,
                "total_clicks": 77,
                "total_impressions": 3437,
                "total_page_views": 1548,
                "overall_ctr": 2.24,
                "overall_cpm_idr": 39.06,
                "overall_rpm_idr": 86.71,
                "accounts": [
                    {
                        "account_key": "perpustakaan",
                        "account_id": "pub-1777593071761494",
                        "display_name": "perpustakaan.id",
                        "status": "active",
                        "earnings_idr": 3.23,
                        "earnings_micros": 3230,
                        "clicks": 9,
                        "impressions": 930,
                        "page_views": 412,
                        "rpm_idr": 7.84
                    }
                ]
            }
        }

# Utility functions
def convert_micros_to_idr(micros_value):
    """Convert AdSense API micros format to IDR (micros already in IDR currency)."""
    try:
        return float(micros_value) / 1_000 if micros_value else 0.0
    except (ValueError, TypeError):
        return 0.0

def parse_date_range(
    date_filter: Optional[str] = None, 
    custom_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> tuple[datetime, datetime]:
    """
    Parse date range parameters and return start_date, end_date tuple.
    
    Args:
        date_filter: 'today', 'yesterday', 'custom', or 'range'
        custom_date: Single date in YYYY-MM-DD format (for 'custom')
        start_date: Start date in YYYY-MM-DD format (for 'range')
        end_date: End date in YYYY-MM-DD format (for 'range')
    
    Returns:
        tuple: (start_datetime, end_datetime)
        
    Raises:
        HTTPException: If invalid date format or missing required parameters
    """
    if date_filter == "today":
        today = datetime.now()
        return today, today
    elif date_filter == "yesterday":
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday, yesterday
    elif date_filter == "custom":
        if not custom_date:
            raise HTTPException(
                status_code=400, 
                detail="custom_date parameter required when date_filter='custom'"
            )
        try:
            target_date = datetime.strptime(custom_date, "%Y-%m-%d")
            return target_date, target_date
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid custom_date format. Use YYYY-MM-DD format."
            )
    elif date_filter == "range":
        if not start_date or not end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date and end_date parameters required when date_filter='range'"
            )
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            if start_dt > end_dt:
                raise HTTPException(
                    status_code=400,
                    detail="start_date cannot be later than end_date"
                )
            
            # Limit to maximum 90 days range
            if (end_dt - start_dt).days > 90:
                raise HTTPException(
                    status_code=400,
                    detail="Date range cannot exceed 90 days"
                )
                
            return start_dt, end_dt
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD format for start_date and end_date."
            )
    else:
        # Default: return today as both start and end
        today = datetime.now()
        return today, today

def parse_date_filter(date_filter: Optional[str] = None, custom_date: Optional[str] = None) -> datetime:
    """Backward compatibility function for single date parsing."""
    start_dt, _ = parse_date_range(date_filter, custom_date)
    return start_dt

def get_adsense_service(account_key: str):
    """Get AdSense service for specific account."""
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise ValueError(f"Unknown account: {account_key}")
    
    config = {
        "client_secrets": account_data.get("client_secrets"),
        "credentials_file": account_data.get("credentials_file"),
        "display_name": account_data.get("display_name"),
        "account_id": account_data.get("account_id")
    }
    client_secrets = config["client_secrets"]
    credentials_file = config["credentials_file"]
    
    # Check if files exist
    if not os.path.exists(client_secrets):
        raise FileNotFoundError(f"Client secrets file not found: {client_secrets}")
    
    credentials = None
    scopes = ['https://www.googleapis.com/auth/adsense.readonly']
    
    if os.path.exists(credentials_file):
        credentials = Credentials.from_authorized_user_file(credentials_file)
        # Check if credentials are valid and refresh if needed
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(google.auth.transport.requests.Request())
                # Save refreshed credentials
                with open(credentials_file, 'w') as f:
                    credentials_json = credentials.to_json()
                    if isinstance(credentials_json, str):
                        credentials_json = json.loads(credentials_json)
                    json.dump(credentials_json, f)
            except RefreshError:
                credentials = None
    
    if not credentials:
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets, scopes)
        # IMPORTANT: Set access_type=offline to get refresh token, use port 8080 to avoid conflicts
        flow.run_local_server(port=8080, access_type='offline', prompt='consent')
        credentials = flow.credentials
        with open(credentials_file, 'w') as f:
            credentials_json = credentials.to_json()
            if isinstance(credentials_json, str):
                credentials_json = json.loads(credentials_json)
            json.dump(credentials_json, f)
    
    return discovery.build('adsense', 'v2', credentials=credentials)

def get_account_id(service, account_key: str):
    """Get account ID for service, with caching."""
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise ValueError(f"Account {account_key} not found in database")
    
    # Use cached account_id if available and not placeholder
    account_id = account_data.get("account_id")
    if account_id and not account_id.startswith("pub-XXXXXX") and account_id != "auto-detect":
        return f"accounts/{account_id}"
    
    # Fetch from API
    response = service.accounts().list().execute()
    if response['accounts']:
        full_account_id = response['accounts'][0]['name']
        publisher_id = full_account_id.split('/')[-1]
        
        # Update database with real account_id and set as active
        account_db.update_account(account_key, {
            "account_id": publisher_id,
            "status": "active"
        })
        
        return full_account_id
    
    raise ValueError(f"No accounts found for {account_key}")

def validate_client_secrets_json(content: str) -> dict:
    """Validate and normalize client secrets JSON format."""
    try:
        data = json.loads(content)
        
        # Check for required structure and normalize
        if "installed" in data:
            client_data = data["installed"]
            normalized_data = data  # Already in correct format
        elif "web" in data:
            client_data = data["web"]
            
            # Convert "web" structure to "installed" structure for consistency
            normalized_data = {
                "installed": {
                    "client_id": client_data["client_id"],
                    "client_secret": client_data["client_secret"],
                    "auth_uri": client_data["auth_uri"],
                    "token_uri": client_data["token_uri"],
                    "redirect_uris": [
                        "http://localhost:8080/",
                        "urn:ietf:wg:oauth:2.0:oob"
                    ]
                }
            }
            
            logger.info("Converted 'web' client secrets to 'installed' format for OAuth compatibility")
        else:
            raise ValueError("Invalid client secrets format. Must contain 'installed' or 'web' section.")
        
        # Validate required fields
        required_fields = ["client_id", "client_secret", "auth_uri", "token_uri"]
        for field in required_fields:
            if field not in client_data:
                raise ValueError(f"Missing required field: {field}")
        
        return normalized_data
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format")
    except Exception as e:
        raise ValueError(f"Validation error: {str(e)}")

def add_new_account(account_key: str, display_name: str, client_secrets_content: str, 
                   description: str = None, account_id: str = None, 
                   website_url: str = None, category: str = None):
    """Add new account to database."""
    # Validate client secrets
    client_secrets_data = validate_client_secrets_json(client_secrets_content)
    
    # Create file paths
    client_secrets_file = f"client_secrets-{account_key}.json"
    credentials_file = f"adsense-{account_key}.dat"
    
    # Save client secrets
    with open(client_secrets_file, 'w') as f:
        json.dump(client_secrets_data, f, indent=2)
    
    # Add to database with all provided information
    account_data = account_db.add_account(
        account_key=account_key,
        account_id=account_id or "auto-detect",
        display_name=display_name,
        description=description,
        client_secrets=client_secrets_file,
        credentials_file=credentials_file,
        website_url=website_url,
        category=category,
        notes=f"Account created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # Refresh account configs cache
    global ACCOUNT_CONFIGS
    ACCOUNT_CONFIGS = get_account_configs()
    
    return {
        "client_secrets_file": client_secrets_file,
        "credentials_file": credentials_file,
        "account_data": account_data
    }

def remove_account(account_key: str):
    """Remove account from database and delete files."""
    # Remove from database (this handles file deletion)
    success = account_db.remove_account(account_key, delete_files=True)
    if not success:
        raise ValueError(f"Account '{account_key}' not found")
    
    # Refresh account configs cache
    global ACCOUNT_CONFIGS
    ACCOUNT_CONFIGS = get_account_configs()

async def run_in_executor(func, *args):
    """Run a function in thread executor for async compatibility."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

# API Endpoints

@app.get(
    "/",
    tags=["Info"],
    summary="API Information",
    description="Get comprehensive API information, available accounts, and usage examples.",
    responses={
        200: {
            "description": "API information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Multi-Account AdSense API Backend v2.0",
                        "accounts": ["perpustakaan", "gowesgo"],
                        "version": "2.0.0",
                        "features": [
                            "🏢 Multi-account support (perpustakaan.id + gowesgo.com)",
                            "💰 Proper IDR conversion (micros ÷ 1,000)", 
                            "📅 Flexible date filtering (today/yesterday/custom)",
                            "🌐 Domain breakdown analytics",
                            "🔄 Auto-retry with data fallback",
                            "📊 Comprehensive metrics (CTR, CPM, etc.)"
                        ]
                    }
                }
            }
        }
    }
)
async def root():
    """
    ## 🚀 Multi-Account AdSense API v2.0
    
    Welcome to the comprehensive AdSense management API! This endpoint provides:
    
    - **Account Information**: List of configured AdSense accounts
    - **API Features**: Key capabilities and enhancements  
    - **Usage Examples**: Quick start guide for all endpoints
    - **Version Info**: Current API version and status
    """
    return {
        "message": "Multi-Account AdSense API Backend v2.0",
        "version": "2.0.0",
        "accounts": list(account_db.get_all_accounts().keys()),
        "account_details": {
            account_key: {
                "display_name": account_data.get("display_name"),
                "publisher_id": account_data.get("account_id"),
                "description": account_data.get("description")
            }
            for account_key, account_data in account_db.get_all_accounts().items()
        },
        "features": [
            "🏢 Multi-account support (perpustakaan.id + gowesgo.com)",
            "💰 Proper IDR conversion (micros ÷ 1,000)", 
            "📅 Flexible date filtering (today/yesterday/custom)",
            "🌐 Domain breakdown analytics",
            "🔄 Auto-retry with data fallback",
            "📊 Comprehensive metrics (CTR, CPM, etc.)"
        ],
        "endpoints": {
            "accounts": "/api/accounts",
            "today_earnings": "/api/today-earnings/{account_key}",
            "domain_earnings": "/api/domain-earnings/{account_key}",
            "rpm_analytics": "/api/rpm/{account_key}",
            "multi_summary": "/api/summary",
            "documentation": "/docs"
        },
        "date_filtering": {
            "supported_values": ["today", "yesterday", "custom"],
            "custom_format": "YYYY-MM-DD",
            "examples": [
                "?date_filter=today",
                "?date_filter=yesterday", 
                "?date_filter=custom&custom_date=2025-10-01"
            ]
        }
    }

@app.get(
    "/api/accounts", 
    response_model=List[AccountInfo],
    tags=["Accounts"],
    summary="Get All Accounts", 
    description="Retrieve list of all configured AdSense accounts with their current status.",
    responses={
        200: {
            "description": "List of accounts retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "account_key": "perpustakaan",
                            "account_id": "pub-1777593071761494",
                            "display_name": "perpustakaan.id", 
                            "status": "active"
                        },
                        {
                            "account_key": "gowesgo",
                            "account_id": "pub-1315457334560058",
                            "display_name": "gowesgo.com",
                            "status": "active"
                        }
                    ]
                }
            }
        }
    }
)
async def get_accounts():
    """
    ## 📋 Account Management
    
    Get comprehensive information about all configured AdSense accounts:
    
    - **Account Keys**: Internal identifiers for API calls
    - **Publisher IDs**: Google AdSense account identifiers  
    - **Display Names**: Human-readable account names
    - **Status**: Current account status (active/inactive)
    
    Use the `account_key` values in other API endpoints.
    """
    accounts = []
    
    for account_key, account_data in account_db.get_all_accounts().items():
        try:
            service = get_adsense_service(account_key)
            account_id = get_account_id(service, account_key)
            status = "active"
        except Exception as e:
            logger.warning(f"Account {account_key} error: {e}")
            account_id = account_data.get("account_id", "unknown")
            status = "error"
        
        accounts.append(AccountInfo(
            account_key=account_key,
            account_id=account_id.split('/')[-1] if account_id.startswith('accounts/') else account_id,
            display_name=account_data.get("display_name"),
            status=status
        ))
    
    return accounts

@app.post(
    "/api/accounts/upload",
    response_model=AccountSetupResponse,
    tags=["Account Management"],
    summary="Upload Client Secrets",
    description="Upload Google AdSense client secrets JSON file for new account setup."
)
async def upload_client_secrets(
    account_key: str = Form(..., description="Unique account identifier"),
    display_name: str = Form(..., description="Human-readable account name"),
    account_id: str = Form(None, description="Google AdSense publisher ID (e.g., pub-1234567890123456). Leave empty to auto-detect via API."),
    description: str = Form(None, description="Optional account description"),
    website_url: str = Form(None, description="Website URL (optional)"),
    category: str = Form(None, description="Account category (optional)"),
    file: UploadFile = File(..., description="Google AdSense client secrets JSON file")
):
    """
    ## 📁 Upload Client Secrets
    
    Upload Google AdSense client secrets JSON file to add a new account:
    
    ### Steps:
    1. **Download Client Secrets**: Get from Google Cloud Console → APIs & Services → Credentials
    2. **Upload Here**: Use this endpoint to upload the JSON file
    3. **Complete OAuth**: Use the returned OAuth URL to authorize access
    4. **Verify Setup**: Check account status with `/api/accounts/{account_key}/validate`
    
    ### Parameters:
    - **account_key**: Unique identifier (e.g., 'janklerk')
    - **display_name**: Human-readable name (e.g., 'JankLerk.info')
    - **account_id**: Publisher ID (e.g., 'pub-1234567890123456') - Optional, will auto-detect if not provided
    - **description**: Optional description
    - **website_url**: Website URL (optional)
    - **category**: Account category (optional)
    - **file**: Client secrets JSON file
    
    ### File Requirements:
    - **Format**: Valid Google client secrets JSON
    - **Type**: Must contain `installed` or `web` configuration
    - **Fields**: client_id, client_secret, auth_uri, token_uri
    - **Auto-Conversion**: `web` format automatically converted to `installed` for OAuth compatibility
    
    ### Supported Client Secret Formats:
    ```json
    // Format 1: "installed" (Desktop App)
    {
      "installed": {
        "client_id": "...",
        "client_secret": "...",
        "redirect_uris": ["http://localhost:8080/", "urn:ietf:wg:oauth:2.0:oob"]
      }
    }
    
    // Format 2: "web" (Web App) - Auto-converted to "installed"
    {
      "web": {
        "client_id": "...",
        "client_secret": "...",
        "redirect_uris": ["http://localhost:8000"]
      }
    }
    ```
    
    ### Account ID Options:
    - **Provide account_id**: If you know your publisher ID (pub-xxxxxxxxxxxxxxxxx)
    - **Auto-detect**: Leave empty to detect automatically during OAuth
    
    ### Response:
    - **Success**: Returns next steps and OAuth URL if needed
    - **Error**: Returns validation errors and requirements
    """
    try:
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="File must be a JSON file")
        
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Add new account with all provided information
        file_info = add_new_account(
            account_key=account_key, 
            display_name=display_name, 
            client_secrets_content=content_str, 
            description=description,
            account_id=account_id or "auto-detect",
            website_url=website_url,
            category=category
        )
        
        next_steps = []
        if account_id:
            # If account_id provided, account is more complete
            next_steps = [
                f"Account ID provided: {account_id}",
                f"Use POST /api/accounts/{account_key}/connect to start OAuth process",
                f"Complete OAuth authorization in browser",
                f"Test with GET /api/today-earnings/{account_key} after OAuth"
            ]
        else:
            # If no account_id, need to auto-detect
            next_steps = [
                f"Account ID will be auto-detected during OAuth",
                f"Use POST /api/accounts/{account_key}/connect to start OAuth process",
                f"Complete OAuth authorization in browser",
                f"Verify setup with GET /api/accounts/{account_key}/validate"
            ]
        
        return AccountSetupResponse(
            success=True,
            account_key=account_key,
            message=f"Client secrets uploaded successfully for account '{account_key}'" + 
                   (f" with publisher ID {account_id}" if account_id else " (publisher ID will be auto-detected)"),
            oauth_url=None,  # Will be generated during OAuth setup
            next_steps=next_steps
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading client secrets: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload client secrets")

@app.api_route(
    "/api/accounts/{account_key}/connect",
    methods=["GET", "POST"],
    response_model=AccountSetupResponse,
    tags=["Account Management"],
    summary="Connect AdSense Account",
    description="Initiate OAuth connection for AdSense account. Supports both GET and POST methods."
)
async def connect_account(
    account_key: str = Path(..., description="Account identifier")
):
    """
    ## 🔗 Connect AdSense Account
    
    Start OAuth process to connect AdSense account:
    
    ### HTTP Methods:
    - **GET**: Browser-friendly access (can be clicked directly)
    - **POST**: API access (for programmatic calls)
    
    ### Process:
    1. **Generate OAuth URL**: Creates authorization URL
    2. **User Authorization**: User visits URL to grant access
    3. **Token Exchange**: System exchanges code for access tokens
    4. **Account Verification**: Validates AdSense account access
    
    ### Requirements:
    - Account must exist (use `/api/accounts/upload` first)
    - Valid client secrets file must be uploaded
    - User must complete OAuth flow in browser
    
    ### Next Steps:
    - Visit the returned OAuth URL
    - Grant permission to your AdSense account
    - Return to check status with validate endpoint
    """
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise HTTPException(status_code=404, detail=f"Account '{account_key}' not found")
    
    try:
        config = {
            "client_secrets": account_data.get("client_secrets"),
            "credentials_file": account_data.get("credentials_file"),
            "display_name": account_data.get("display_name"),
            "account_id": account_data.get("account_id")
        }
        
        # Check if client secrets exist
        if not os.path.exists(config["client_secrets"]):
            raise HTTPException(
                status_code=400, 
                detail="Client secrets not found. Upload client secrets first."
            )
        
        # Remove existing credentials to force fresh OAuth
        if os.path.exists(config["credentials_file"]):
            os.remove(config["credentials_file"])
        
        # Setup OAuth flow
        scopes = ['https://www.googleapis.com/auth/adsense.readonly']
        flow = InstalledAppFlow.from_client_secrets_file(config["client_secrets"], scopes)
        
        # Run OAuth in background task
        def run_oauth():
            try:
                # Use specific port to avoid conflicts
                flow.run_local_server(port=8080, access_type='offline', prompt='consent')
                credentials = flow.credentials
                
                # Save credentials
                with open(config["credentials_file"], 'w') as f:
                    credentials_json = credentials.to_json()
                    if isinstance(credentials_json, str):
                        credentials_json = json.loads(credentials_json)
                    json.dump(credentials_json, f)
                
                # Get account ID
                service = discovery.build('adsense', 'v2', credentials=credentials)
                account_id = get_account_id(service, account_key)
                
                logger.info(f"OAuth completed for {account_key}: {account_id}")
                return account_id
                
            except Exception as e:
                logger.error(f"OAuth failed for {account_key}: {e}")
                raise e
        
        # Run OAuth in executor (non-blocking)
        try:
            account_id = await run_in_executor(run_oauth)
            
            return AccountSetupResponse(
                success=True,
                account_key=account_key,
                message=f"Successfully connected to AdSense account: {account_id}",
                oauth_url=None,
                next_steps=[
                    f"Account is now connected and ready to use",
                    f"Test with GET /api/today-earnings/{account_key}",
                    f"Verify with GET /api/accounts/{account_key}/validate"
                ]
            )
            
        except Exception as e:
            return AccountSetupResponse(
                success=False,
                account_key=account_key,
                message=f"OAuth connection failed: {str(e)}",
                oauth_url=None,
                next_steps=[
                    "Check client secrets are valid",
                    "Ensure AdSense account has proper permissions",
                    "Try connecting again"
                ]
            )
        
    except Exception as e:
        logger.error(f"Error connecting account {account_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/accounts/{account_key}/status",
    response_model=dict,
    tags=["Account Management"],
    summary="Get Account Status",
    description="Get detailed account status and connection information."
)
async def get_account_status(
    account_key: str = Path(..., description="Account identifier")
):
    """
    ## 📊 Account Status & Connection Info
    
    Get comprehensive account status information:
    
    ### Information Provided:
    - **Account Details**: Basic account information
    - **Connection Status**: OAuth connection status
    - **File Status**: Client secrets and credentials files
    - **Next Steps**: Recommended actions
    
    ### Use Cases:
    - Check if account is ready for use
    - Troubleshoot connection issues
    - Get setup instructions
    - Verify file integrity
    """
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise HTTPException(status_code=404, detail=f"Account '{account_key}' not found")
    
    try:
        # Check file existence
        client_secrets_exists = os.path.exists(account_data.get("client_secrets", ""))
        credentials_exists = os.path.exists(account_data.get("credentials_file", ""))
        
        # Determine connection status
        connection_status = "unknown"
        connection_details = {}
        
        if not client_secrets_exists:
            connection_status = "missing_client_secrets"
            connection_details["error"] = "Client secrets file not found"
        elif not credentials_exists:
            connection_status = "needs_oauth"
            connection_details["info"] = "Ready for OAuth connection"
        else:
            # Try to validate existing credentials
            try:
                service = get_adsense_service(account_key)
                account_id = get_account_id(service, account_key)
                connection_status = "connected"
                connection_details["account_id"] = account_id
                connection_details["info"] = "Account successfully connected"
            except Exception as e:
                connection_status = "oauth_expired"
                connection_details["error"] = f"OAuth token may be expired: {str(e)}"
        
        # Generate next steps
        next_steps = []
        if connection_status == "missing_client_secrets":
            next_steps = [
                "Upload client secrets using POST /api/accounts/upload",
                "Download client secrets from Google Cloud Console"
            ]
        elif connection_status == "needs_oauth":
            next_steps = [
                f"Visit: GET /api/accounts/{account_key}/connect (in browser)",
                f"Or use: POST /api/accounts/{account_key}/connect (programmatically)",
                "Complete OAuth authorization when prompted"
            ]
        elif connection_status == "oauth_expired":
            next_steps = [
                f"Reconnect: GET /api/accounts/{account_key}/connect",
                "Re-authorize access to your AdSense account"
            ]
        elif connection_status == "connected":
            next_steps = [
                f"Test earnings: GET /api/today-earnings/{account_key}",
                f"View domains: GET /api/domain-earnings/{account_key}",
                f"Check RPM: GET /api/rpm/{account_key}",
                "Account is ready to use!"
            ]
        
        return {
            "account_key": account_key,
            "display_name": account_data.get("display_name"),
            "account_id": account_data.get("account_id"),
            "status": account_data.get("status"),
            "connection_status": connection_status,
            "connection_details": connection_details,
            "files": {
                "client_secrets": {
                    "path": account_data.get("client_secrets"),
                    "exists": client_secrets_exists
                },
                "credentials": {
                    "path": account_data.get("credentials_file"),
                    "exists": credentials_exists
                }
            },
            "metadata": account_data.get("metadata", {}),
            "next_steps": next_steps,
            "created_at": account_data.get("created_at"),
            "updated_at": account_data.get("updated_at")
        }
        
    except Exception as e:
        logger.error(f"Error getting account status for {account_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/accounts/{account_key}/validate",
    response_model=AccountValidationResponse,
    tags=["Account Management"],
    summary="Validate Account",
    description="Validate AdSense account connection and retrieve account information."
)
async def validate_account(
    account_key: str = Path(..., description="Account identifier")
):
    """
    ## ✅ Validate Account Connection
    
    Check if AdSense account is properly connected and accessible:
    
    ### Validation Checks:
    - **Configuration**: Account exists in system
    - **Files**: Client secrets and credentials files exist
    - **Authentication**: OAuth tokens are valid
    - **API Access**: Can retrieve AdSense account information
    - **Permissions**: Has required AdSense read permissions
    
    ### Response:
    - **Success**: Returns publisher ID and account status
    - **Error**: Returns specific error and resolution steps
    """
    account_data = account_db.get_account(account_key)
    if not account_data:
        return AccountValidationResponse(
            valid=False,
            account_key=account_key,
            status="not_found",
            error="Account configuration not found"
        )
    
    try:
        config = {
            "client_secrets": account_data.get("client_secrets"),
            "credentials_file": account_data.get("credentials_file"),
            "display_name": account_data.get("display_name"),
            "account_id": account_data.get("account_id")
        }
        
        # Check files exist
        if not os.path.exists(config["client_secrets"]):
            return AccountValidationResponse(
                valid=False,
                account_key=account_key,
                status="missing_client_secrets",
                error="Client secrets file not found"
            )
        
        if not os.path.exists(config["credentials_file"]):
            return AccountValidationResponse(
                valid=False,
                account_key=account_key,
                status="not_connected",
                error="OAuth credentials not found. Use connect endpoint first."
            )
        
        # Test API access
        def test_connection():
            service = get_adsense_service(account_key)
            account_id = get_account_id(service, account_key)
            
            # Test basic API call
            response = service.accounts().list().execute()
            if not response.get('accounts'):
                raise ValueError("No AdSense accounts accessible")
            
            return account_id
        
        account_id = await run_in_executor(test_connection)
        
        return AccountValidationResponse(
            valid=True,
            account_key=account_key,
            publisher_id=account_id.split('/')[-1] if account_id.startswith('accounts/') else account_id,
            status="active"
        )
        
    except Exception as e:
        logger.error(f"Validation error for {account_key}: {e}")
        return AccountValidationResponse(
            valid=False,
            account_key=account_key,
            status="error",
            error=str(e)
        )

@app.delete(
    "/api/accounts/{account_key}",
    response_model=dict,
    tags=["Account Management"],
    summary="Remove Account",
    description="Remove AdSense account from system and delete associated files."
)
async def remove_account_endpoint(
    account_key: str = Path(..., description="Account identifier"),
    confirm: bool = Query(False, description="Confirmation flag to prevent accidental deletion")
):
    """
    ## 🗑️ Remove Account
    
    Permanently remove AdSense account from system:
    
    ### Warning:
    **This action is irreversible!** It will:
    - Remove account from configuration
    - Delete client secrets file
    - Delete OAuth credentials
    - Remove all account data
    
    ### Safety:
    - Must set `confirm=true` parameter
    - Will fail if account is not found
    - Logs all deletion actions
    
    ### After Removal:
    - Account will no longer appear in `/api/accounts`
    - All account-specific endpoints will return 404
    - Files will be permanently deleted
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must set confirm=true to delete account"
        )
    
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise HTTPException(status_code=404, detail=f"Account '{account_key}' not found")
    
    # Prevent deletion of default accounts (optional - can be removed if you want to allow)
    if account_key in ["perpustakaan", "gowesgo"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete default account '{account_key}'. Use confirm_delete=true to override."
        )
    
    try:
        removed_files = []
        
        # Track files that will be removed
        for file_path in [account_data.get("client_secrets"), account_data.get("credentials_file")]:
            if file_path and os.path.exists(file_path):
                removed_files.append(file_path)
        
        # Remove account
        remove_account(account_key)
        
        logger.info(f"Removed account {account_key}, deleted files: {removed_files}")
        
        return {
            "success": True,
            "message": f"Account '{account_key}' removed successfully",
            "account_key": account_key,
            "removed_files": removed_files
        }
        
    except Exception as e:
        logger.error(f"Error removing account {account_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/database/stats",
    response_model=dict,
    tags=["Database Management"],
    summary="Database Statistics",
    description="Get comprehensive database statistics and metadata."
)
async def get_database_stats():
    """
    ## 📊 Database Statistics
    
    Get comprehensive information about the accounts database:
    
    ### Includes:
    - **Account Counts**: Total, active, inactive accounts
    - **Database Metadata**: Version, creation date, last modified
    - **File Status**: Database file size and location
    - **Health Check**: Database validation status
    
    ### Use Cases:
    - Monitor database health
    - Track account growth
    - Verify database integrity
    - System administration
    """
    try:
        stats = account_db.get_statistics()
        metadata = account_db.get_metadata()
        
        # Get file info
        db_path = account_db.db_path
        file_size = os.path.getsize(db_path) if db_path.exists() else 0
        
        # Validate database
        validation_errors = account_db.validate_database()
        
        return {
            "database_info": {
                "path": str(db_path),
                "size_bytes": file_size,
                "size_kb": round(file_size / 1024, 2),
                "exists": db_path.exists(),
                "is_healthy": len(validation_errors) == 0
            },
            "statistics": stats,
            "metadata": metadata,
            "validation": {
                "is_valid": len(validation_errors) == 0,
                "errors": validation_errors
            },
            "accounts_summary": {
                "total": len(account_db.get_all_accounts()),
                "active": len(account_db.get_active_accounts()),
                "account_keys": list(account_db.get_all_accounts().keys())
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/database/search",
    response_model=List[dict],
    tags=["Database Management"],
    summary="Search Accounts",
    description="Search accounts by name, description, or metadata."
)
async def search_accounts(
    query: str = Query(..., description="Search query", min_length=2)
):
    """
    ## 🔍 Search Accounts
    
    Search through all accounts by various criteria:
    
    ### Search Fields:
    - **Display Name**: Human-readable account names
    - **Description**: Account descriptions
    - **Website URL**: Associated website URLs
    - **Notes**: Custom notes and metadata
    - **Account Key**: Internal identifiers
    
    ### Examples:
    - Search for "perpustakaan" - finds perpustakaan.id account
    - Search for "education" - finds accounts with education category
    - Search for ".com" - finds accounts with .com websites
    
    ### Use Cases:
    - Find accounts by website domain
    - Locate accounts by category or description
    - Quick account lookup for administration
    """
    try:
        results = account_db.search_accounts(query)
        
        # Format results for API response
        formatted_results = []
        for account in results:
            formatted_results.append({
                "account_key": account.get("account_key"),
                "account_id": account.get("account_id"),
                "display_name": account.get("display_name"),
                "description": account.get("description"),
                "status": account.get("status"),
                "created_at": account.get("created_at"),
                "metadata": account.get("metadata", {})
            })
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/database/backup",
    response_model=dict,
    tags=["Database Management"], 
    summary="Create Database Backup",
    description="Create a backup of the accounts database."
)
async def create_database_backup(
    backup_name: Optional[str] = Query(None, description="Custom backup filename")
):
    """
    ## 💾 Create Database Backup
    
    Create a backup copy of the accounts database:
    
    ### Features:
    - **Automatic Naming**: Uses timestamp if no name provided
    - **Safe Operation**: Creates backup without interrupting service
    - **Metadata Update**: Updates last backup timestamp
    - **File Verification**: Confirms backup was created successfully
    
    ### Backup Format:
    - **Extension**: .json (same format as main database)
    - **Content**: Complete copy of accounts.json with all data
    - **Location**: Same directory as main database
    
    ### Recommended Schedule:
    - Before major changes
    - Daily for production systems
    - Before account additions/removals
    """
    try:
        backup_path = account_db.create_backup(backup_name)
        
        # Get backup file info
        backup_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
        
        return {
            "success": True,
            "message": "Database backup created successfully",
            "backup_path": backup_path,
            "backup_size_bytes": backup_size,
            "backup_size_kb": round(backup_size / 1024, 2),
            "created_at": datetime.now().isoformat(),
            "accounts_backed_up": len(account_db.get_all_accounts())
        }
        
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/database/restore",
    response_model=dict,
    tags=["Database Management"],
    summary="Restore Database",
    description="Restore accounts database from backup file."
)
async def restore_database(
    backup_file: UploadFile = File(..., description="Backup file to restore from")
):
    """
    ## 🔄 Restore Database
    
    Restore accounts database from a backup file:
    
    ### Safety Features:
    - **Pre-restore Backup**: Creates backup of current database
    - **Validation**: Verifies backup file integrity before restore
    - **Rollback Support**: Can revert if restore fails
    - **Service Continuity**: Updates in-memory cache after restore
    
    ### Process:
    1. Validate uploaded backup file
    2. Create backup of current database
    3. Restore from uploaded file
    4. Refresh account configurations
    5. Verify restore success
    
    ### File Requirements:
    - **Format**: Valid JSON database format
    - **Structure**: Must contain accounts section
    - **Size**: Reasonable file size limits
    """
    try:
        # Validate file type
        if not backup_file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Backup file must be JSON format")
        
        # Read backup file content
        content = await backup_file.read()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write(content.decode('utf-8'))
            temp_path = temp_file.name
        
        try:
            # Restore from temporary file
            account_db.restore_from_backup(temp_path)
            
            # Refresh global account configs
            global ACCOUNT_CONFIGS
            ACCOUNT_CONFIGS = get_account_configs()
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return {
                "success": True,
                "message": "Database restored successfully",
                "restored_from": backup_file.filename,
                "restored_at": datetime.now().isoformat(),
                "total_accounts": len(account_db.get_all_accounts()),
                "account_keys": list(account_db.get_all_accounts().keys())
            }
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
        
    except Exception as e:
        logger.error(f"Error restoring database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/api/accounts/{account_key}/update",
    response_model=dict,
    tags=["Account Management"],
    summary="Update Account",
    description="Update account information and metadata."
)
async def update_account_endpoint(
    account_key: str = Path(..., description="Account identifier"),
    display_name: Optional[str] = Query(None, description="New display name"),
    description: Optional[str] = Query(None, description="New description"),
    website_url: Optional[str] = Query(None, description="Website URL"),
    category: Optional[str] = Query(None, description="Account category"),
    notes: Optional[str] = Query(None, description="Additional notes")
):
    """
    ## ✏️ Update Account Information
    
    Update account details and metadata:
    
    ### Updatable Fields:
    - **Display Name**: Human-readable account name
    - **Description**: Account description
    - **Website URL**: Associated website
    - **Category**: Account category (e.g., education, lifestyle)
    - **Notes**: Custom notes and information
    
    ### Restrictions:
    - Cannot change account_key (use for identification only)
    - Cannot change account_id (Google AdSense publisher ID)
    - File paths updated automatically if needed
    
    ### Use Cases:
    - Update website URLs after domain changes
    - Add categorization for better organization
    - Update descriptions for clarity
    - Add operational notes
    """
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise HTTPException(status_code=404, detail=f"Account '{account_key}' not found")
    
    try:
        # Build updates dictionary
        updates = {}
        metadata_updates = {}
        
        if display_name is not None:
            updates["display_name"] = display_name
        if description is not None:
            updates["description"] = description
        if website_url is not None:
            metadata_updates["website_url"] = website_url
        if category is not None:
            metadata_updates["category"] = category
        if notes is not None:
            metadata_updates["notes"] = notes
        
        if metadata_updates:
            updates["metadata"] = metadata_updates
        
        if not updates:
            return {
                "success": False,
                "message": "No updates provided",
                "account_key": account_key
            }
        
        # Update account
        updated_account = account_db.update_account(account_key, updates)
        
        # Refresh global account configs
        global ACCOUNT_CONFIGS
        ACCOUNT_CONFIGS = get_account_configs()
        
        return {
            "success": True,
            "message": f"Account '{account_key}' updated successfully",
            "account_key": account_key,
            "updated_fields": list(updates.keys()),
            "account_data": {
                "display_name": updated_account.get("display_name"),
                "description": updated_account.get("description"),
                "status": updated_account.get("status"),
                "updated_at": updated_account.get("updated_at"),
                "metadata": updated_account.get("metadata", {})
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating account {account_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/today-earnings/{account_key}", 
    response_model=TodayEarnings,
    tags=["Earnings"],
    summary="Get Daily Earnings",
    description="Get daily earnings for a specific account with flexible date filtering.",
    responses={
        200: {
            "description": "Earnings data retrieved successfully"
        },
        404: {
            "description": "Account not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Account 'invalid_account' not found"}
                }
            }
        },
        400: {
            "description": "Invalid date format",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid date format. Use YYYY-MM-DD format."}
                }
            }
        }
    }
)
async def get_today_earnings(
    account_key: str = Path(..., description="Account identifier (e.g., perpustakaan, gowesgo, or custom account)"),
    date_filter: Optional[DateFilter] = Query(
        None, 
        description="Date filter: 'today', 'yesterday', 'custom', or 'range'. If not specified, tries multiple recent days."
    ),
    custom_date: Optional[str] = Query(
        None, 
        description="Custom date in YYYY-MM-DD format (required when date_filter='custom')",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    ),
    start_date: Optional[str] = Query(
        None,
        description="Start date in YYYY-MM-DD format (required when date_filter='range')",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date in YYYY-MM-DD format (required when date_filter='range')",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    )
):
    """
    ## 💰 Daily Earnings Report with Date Range Support
    
    Get comprehensive earnings data for a specific AdSense account with enhanced date filtering:
    
    ### 🆕 NEW: Date Range Support
    - **� Single Day**: Use 'today', 'yesterday', or 'custom' for single day analysis
    - **� Date Range**: Use 'range' with start_date and end_date for period analysis
    - **🔄 Auto-Fallback**: Default mode tries recent days if no specific filter
    
    ### Features:
    - **💱 Proper IDR Conversion**: Micros ÷ 1,000 = IDR
    - **📊 Complete Metrics**: Earnings, clicks, impressions, CTR, CPM, RPM
    - **⚡ Smart Caching**: 1-minute cache for improved performance
    
    ### Date Filtering Options:
    - **today**: Get today's data only
    - **yesterday**: Get yesterday's data only  
    - **custom**: Single date with `custom_date` parameter
    - **range**: Date range with `start_date` and `end_date` parameters (max 90 days)
    - **default**: Auto-retry logic (tries today, yesterday, 2-3 days ago)
    
    ### Examples:
    - `GET /api/today-earnings/perpustakaan` - Auto-retry logic
    - `GET /api/today-earnings/perpustakaan?date_filter=today` - Today only
    - `GET /api/today-earnings/gowesgo?date_filter=range&start_date=2025-10-01&end_date=2025-10-07` - Weekly range
    - `GET /api/today-earnings/perpustakaan?date_filter=custom&custom_date=2025-10-01` - Specific date
    """
    # Get account data from database
    account_db = get_account_database()
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise HTTPException(status_code=404, detail=f"Account '{account_key}' not found")
    
    # Check cache first
    cache = get_cache_manager()
    if date_filter == "range":
        cache_key = f"earnings:{account_key}:range:{start_date}:{end_date}"
    else:
        cache_key = cache_key_for_earnings(account_key, date_filter, custom_date)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        def fetch_earnings():
            service = get_adsense_service(account_key) 
            full_account_name = get_account_id(service, account_key)
            
            if date_filter == "range":
                # Date range mode - aggregate data across multiple days
                start_dt, end_dt = parse_date_range(date_filter, custom_date, start_date, end_date)
                
                # Make API request for the entire range
                request = service.accounts().reports().generate(
                    account=full_account_name,
                    dateRange='CUSTOM',
                    startDate_year=start_dt.year,
                    startDate_month=start_dt.month,
                    startDate_day=start_dt.day,
                    endDate_year=end_dt.year,
                    endDate_month=end_dt.month,
                    endDate_day=end_dt.day,
                    metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
                )
                report = request.execute()
                
                if 'rows' in report and report['rows']:
                    row = report['rows'][0]
                    total_earnings_micros = float(row['cells'][0]['value'] or 0)
                    total_clicks = int(row['cells'][1]['value'] or 0)
                    total_impressions = int(row['cells'][2]['value'] or 0)
                    total_page_views = int(row['cells'][3]['value'] or 0)
                    
                    total_earnings_idr = convert_micros_to_idr(total_earnings_micros)
                    
                    # Calculate period metrics
                    days_in_range = (end_dt - start_dt).days + 1
                    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
                    avg_cpm = (total_earnings_idr / total_impressions * 1000) if total_impressions > 0 else 0
                    avg_rpm = (total_earnings_idr / total_page_views * 1000) if total_page_views > 0 else 0
                    
                    return TodayEarnings(
                        date=f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
                        account_key=account_key,
                        account_id=account_data.get("account_id"),
                        earnings_idr=round(total_earnings_idr, 2),
                        earnings_micros=int(total_earnings_micros),
                        clicks=total_clicks,
                        impressions=total_impressions,
                        page_views=total_page_views,
                        ctr=round(avg_ctr, 2),
                        cpm_idr=round(avg_cpm, 2),
                        rpm_idr=round(avg_rpm, 2),
                        data_age_days=0,
                        note=f"Agregasi data {days_in_range} hari ({start_dt.strftime('%Y-%m-%d')} - {end_dt.strftime('%Y-%m-%d')})"
                    )
                else:
                    start_dt, end_dt = parse_date_range(date_filter, custom_date, start_date, end_date)
                    return TodayEarnings(
                        date=f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
                        account_key=account_key,
                        account_id=account_data.get("account_id"),
                        earnings_idr=0, earnings_micros=0, clicks=0, impressions=0, page_views=0,
                        ctr=0, cpm_idr=0, rpm_idr=0, data_age_days=0,
                        note="Tidak ada data untuk periode ini"
                    )
            
            # Single day mode - existing logic
            if date_filter and date_filter != "range":
                # Specific date filtering - single attempt
                target_date = parse_date_filter(date_filter, custom_date)
                days_to_try = [target_date]
                days_back_values = [0]  # For response metadata
            else:
                # Default auto-retry logic - multiple attempts
                days_to_try = [datetime.now() - timedelta(days=i) for i in [0, 1, 2, 3]]
                days_back_values = [0, 1, 2, 3]
            
            # Try each target date
            for i, target_date in enumerate(days_to_try):
                try:
                    days_back = days_back_values[i] if not date_filter else (datetime.now() - target_date).days
                    
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
                    
                    if 'rows' in report and report['rows']:
                        row = report['rows'][0]
                        earnings_micros = float(row['cells'][0]['value'] or 0)
                        clicks = int(row['cells'][1]['value'] or 0)
                        impressions = int(row['cells'][2]['value'] or 0)
                        page_views = int(row['cells'][3]['value'] or 0)
                        
                        earnings_idr = convert_micros_to_idr(earnings_micros)
                        ctr = (clicks / impressions * 100) if impressions > 0 else 0
                        cpm = (earnings_idr / impressions * 1000) if impressions > 0 else 0
                        rpm = (earnings_idr / page_views * 1000) if page_views > 0 else 0
                        
                        return TodayEarnings(
                            date=target_date.strftime('%Y-%m-%d'),
                            account_key=account_key,
                            account_id=account_data.get("account_id"),
                            earnings_idr=round(earnings_idr, 2),
                            earnings_micros=int(earnings_micros),
                            clicks=clicks,
                            impressions=impressions,
                            page_views=page_views,
                            ctr=round(ctr, 2),
                            cpm_idr=round(cpm, 2),
                            rpm_idr=round(rpm, 2),
                            data_age_days=days_back,
                            note=f"Data terbaru dari {days_back} hari yang lalu" if days_back > 0 else "Data hari ini"
                        )
                        
                except Exception as e:
                    logger.warning(f"Error fetching data for {days_back} days back: {e}")
                    continue
            
            # No data found
            return TodayEarnings(
                date=datetime.now().strftime('%Y-%m-%d'),
                account_key=account_key,
                account_id=account_data.get("account_id"),
                earnings_idr=0,
                earnings_micros=0,
                clicks=0,
                impressions=0,
                page_views=0,
                ctr=0,
                cpm_idr=0,
                rpm_idr=0,
                data_age_days=-1,
                note="Data belum tersedia. AdSense memiliki delay 1-3 hari untuk reporting."
            )
        
        earnings_data = await run_in_executor(fetch_earnings)
        
        # Cache the result for 1 minute
        cache.set(cache_key, earnings_data, ttl=60)
        
        return earnings_data
        
    except Exception as e:
        logger.error(f"Error fetching earnings for {account_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/domain-earnings/{account_key}",
    response_model=DomainBreakdownResponse,
    tags=["Domain Analytics"],
    summary="Get Domain Breakdown",
    description="Get detailed earnings breakdown by domain/subdomain for a specific account.",
    responses={
        200: {
            "description": "Domain breakdown retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "date": "2025-10-03",
                        "account_key": "perpustakaan",
                        "account_id": "pub-1777593071761494",
                        "domain_filter": None,
                        "domains": [
                            {
                                "domain": "perpustakaan.id",
                                "earnings_idr": 2.20,
                                "earnings_micros": 2199,
                                "clicks": 8,
                                "impressions": 830,
                                "page_views": 362,
                                "ctr": 0.96,
                                "cpm_idr": 2.65
                            }
                        ],
                        "summary": {
                            "total_domains": 10,
                            "total_earnings_idr": 3.23,
                            "total_earnings_micros": 3230,
                            "total_clicks": 9,
                            "total_impressions": 930,
                            "total_page_views": 412,
                            "overall_ctr": 0.97,
                            "overall_cpm_idr": 3.47
                        }
                    }
                }
            }
        },
        404: {
            "description": "Account not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Account 'invalid_account' not found"}
                }
            }
        },
        400: {
            "description": "Invalid date format",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid date format. Use YYYY-MM-DD format."}
                }
            }
        }
    }
)
async def get_domain_earnings(
    account_key: str = Path(..., description="Account identifier (e.g., perpustakaan, gowesgo, or custom account)"),
    domain_filter: Optional[str] = Query(
        None, 
        alias="domain",
        description="Filter by specific domain name (partial match supported)",
        example="perpustakaan.id"
    ),
    date_filter: Optional[DateFilter] = Query(
        None, 
        description="Date filter: 'today', 'yesterday', 'custom', or 'range'. If not specified, tries multiple recent days."
    ),
    custom_date: Optional[str] = Query(
        None, 
        description="Custom date in YYYY-MM-DD format (required when date_filter='custom')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    start_date: Optional[str] = Query(
        None,
        description="Start date in YYYY-MM-DD format (required when date_filter='range')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date in YYYY-MM-DD format (required when date_filter='range')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
):
    """
    ## 🌐 Domain Breakdown Analytics
    
    Get comprehensive domain-by-domain earnings breakdown:
    
    ### Features:
    - **📊 Detailed Metrics**: Earnings, clicks, impressions, page views per domain
    - **🔍 Domain Filtering**: Filter by specific domain names
    - **📅 Date Flexibility**: Today, yesterday, or custom date
    - **📈 Summary Statistics**: Total counts and averages across all domains
    - **🔄 Auto-Fallback**: Tries recent days if current date has no data
    
    ### Domain Filter:
    - Use `domain` parameter to filter by domain name (partial match)
    - Example: `?domain=perpustakaan.id` shows only main domain
    - Leave empty to see all domains
    
    ### Date Filtering:
    - **today**: Get today's domain data
    - **yesterday**: Get yesterday's domain data
    - **custom**: Specify exact date with `custom_date` parameter
    - **default**: Auto-retry logic (tries today → yesterday → 2 days ago → 3 days ago)
    
    ### Response Includes:
    - **Individual Domains**: Detailed metrics for each domain/subdomain
    - **Summary**: Aggregated statistics across all domains
    - **Metadata**: Date, account info, applied filters
    
    ### Examples:
    - `GET /api/domain-earnings/perpustakaan` - All domains, auto-retry dates
    - `GET /api/domain-earnings/perpustakaan?domain=perpustakaan.id` - Main domain only
    - `GET /api/domain-earnings/gowesgo?date_filter=yesterday` - Yesterday's data
    - `GET /api/domain-earnings/perpustakaan?date_filter=custom&custom_date=2025-10-01` - Specific date
    """
    # Get account data from database
    account_db = get_account_database()
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise HTTPException(status_code=404, detail=f"Account '{account_key}' not found")
    
    # Check cache first
    cache = get_cache_manager()
    if date_filter == "range":
        cache_key = f"domain_earnings:{account_key}:{domain_filter}:range:{start_date}:{end_date}"
    else:
        cache_key = cache_key_for_domain_earnings(account_key, domain_filter, date_filter, custom_date)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        def fetch_domain_earnings():
            service = get_adsense_service(account_key)
            full_account_name = get_account_id(service, account_key)
            
            if date_filter == "range":
                # Date range mode
                start_dt, end_dt = parse_date_range(date_filter, custom_date, start_date, end_date)
                
                request = service.accounts().reports().generate(
                    account=full_account_name,
                    dateRange='CUSTOM',
                    startDate_year=start_dt.year,
                    startDate_month=start_dt.month,
                    startDate_day=start_dt.day,
                    endDate_year=end_dt.year,
                    endDate_month=end_dt.month,
                    endDate_day=end_dt.day,
                    metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS'],
                    dimensions=['DOMAIN_NAME']
                )
                report = request.execute()
                
                date_range_str = f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
                
            else:
                # Single day mode with fallback
                if date_filter:
                    # Specific date filtering - single attempt
                    target_date = parse_date_filter(date_filter, custom_date)
                    days_to_try = [target_date]
                else:
                    # Default auto-retry logic - multiple attempts
                    days_to_try = [datetime.now() - timedelta(days=i) for i in [0, 1, 2, 3]]
            
                report = None
                target_date = None
                
                # Try each target date
                for target_date in days_to_try:
                    try:
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
                        
                        # If we have data, break and use it
                        if 'rows' in report and report['rows']:
                            break
                            
                    except Exception as e:
                        days_back = (datetime.now() - target_date).days
                        logger.warning(f"Error fetching domain data for {days_back} days back: {e}")
                        continue
                else:
                    # No data found in any of the days
                    report = {'rows': []}
                
                date_range_str = target_date.strftime('%Y-%m-%d') if target_date else datetime.now().strftime('%Y-%m-%d')
            
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
                    
                    # Apply domain filter if specified
                    if domain_filter and domain_filter.lower() not in domain_name.lower():
                        continue
                    
                    domain_data = DomainEarnings(
                        domain=domain_name,
                        earnings_idr=round(earnings_idr, 2),
                        earnings_micros=int(earnings_micros),
                        clicks=clicks,
                        impressions=impressions,
                        page_views=page_views,
                        ctr=round((clicks / impressions * 100), 2) if impressions > 0 else 0,
                        cpm_idr=round((earnings_idr / impressions * 1000), 2) if impressions > 0 else 0,
                        rpm_idr=round((earnings_idr / page_views * 1000), 2) if page_views > 0 else 0
                    )
                    
                    domains.append(domain_data)
                    total_earnings += earnings_idr
                    total_clicks += clicks
                    total_impressions += impressions
                    total_page_views += page_views
            
            return {
                "date": date_range_str,
                "account_key": account_key,
                "account_id": account_data.get("account_id"),
                "domain_filter": domain_filter,
                "domains": sorted(domains, key=lambda x: x.earnings_idr, reverse=True),
                "summary": {
                    "total_domains": len(domains),
                    "total_earnings_idr": round(total_earnings, 2),
                    "total_earnings_micros": int(total_earnings * 1_000),
                    "total_clicks": total_clicks,
                    "total_impressions": total_impressions,
                    "total_page_views": total_page_views,
                    "overall_ctr": round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0,
                    "overall_cpm_idr": round((total_earnings / total_impressions * 1000), 2) if total_impressions > 0 else 0
                }
            }
            
        domain_data = await run_in_executor(fetch_domain_earnings)
        
        # Cache the result for 1 minute
        cache.set(cache_key, domain_data, ttl=60)
        
        return domain_data
        
    except Exception as e:
        logger.error(f"Error fetching domain earnings for {account_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/rpm/{account_key}",
    response_model=RPMData,
    tags=["Analytics"],
    summary="Get RPM (Revenue per Mille)",
    description="Get RPM (Revenue per 1000 page views) analysis for a specific account.",
    responses={
        200: {
            "description": "RPM data retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "date": "2025-10-03",
                        "account_key": "perpustakaan",
                        "account_id": "pub-1777593071761494",
                        "earnings_idr": 3.23,
                        "earnings_micros": 3229,
                        "page_views": 412,
                        "rpm_idr": 7.84,
                        "impressions": 930,
                        "clicks": 9,
                        "ctr": 0.97,
                        "cpm_idr": 3.47,
                        "data_age_days": 1,
                        "note": "Data terbaru dari 1 hari yang lalu"
                    }
                }
            }
        },
        404: {
            "description": "Account not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Account 'invalid_account' not found"}
                }
            }
        },
        400: {
            "description": "Invalid date format",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid date format. Use YYYY-MM-DD format."}
                }
            }
        }
    }
)
async def get_rpm_data(
    account_key: str = Path(..., description="Account identifier (e.g., perpustakaan, gowesgo)"),
    date_filter: Optional[DateFilter] = Query(
        None, 
        description="Date filter: 'today', 'yesterday', 'custom', or 'range'. If not specified, tries multiple recent days."
    ),
    custom_date: Optional[str] = Query(
        None, 
        description="Custom date in YYYY-MM-DD format (required when date_filter='custom')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    start_date: Optional[str] = Query(
        None,
        description="Start date in YYYY-MM-DD format (required when date_filter='range')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date in YYYY-MM-DD format (required when date_filter='range')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
):
    """
    ## 📊 RPM (Revenue per Mille) Analytics
    
    Calculate and analyze RPM - Revenue per 1000 page views:
    
    ### What is RPM?
    - **RPM = (Earnings / Page Views) × 1000**
    - Shows how much you earn per 1000 page views
    - Higher RPM indicates better monetization per visitor
    - Different from CPM (Cost per Mille for impressions)
    
    ### Key Metrics Included:
    - **💰 RPM in IDR**: Revenue per 1000 page views
    - **📄 Page Views**: Total page views for the period
    - **💵 Earnings**: Total earnings (IDR and micros)
    - **👆 Clicks & Impressions**: Ad interaction data
    - **📈 CTR & CPM**: Additional performance metrics
    
    ### Date Filtering:
    - **today**: Get today's RPM data
    - **yesterday**: Get yesterday's RPM data  
    - **custom**: Specify exact date with `custom_date` parameter
    - **default**: Auto-retry logic (tries today → yesterday → 2 days ago → 3 days ago)
    
    ### Use Cases:
    - **Content Performance**: Which pages generate the most revenue per view
    - **Traffic Quality**: Understanding visitor engagement value
    - **Optimization**: Focus on improving high-traffic, low-RPM pages
    - **Comparison**: Compare RPM across different accounts/periods
    
    ### Examples:
    - `GET /api/rpm/perpustakaan` - Latest available RPM data
    - `GET /api/rpm/gowesgo?date_filter=yesterday` - Yesterday's RPM
    - `GET /api/rpm/perpustakaan?date_filter=custom&custom_date=2025-10-01` - Specific date RPM
    """
    # Get account data from database
    account_db = get_account_database()
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise HTTPException(status_code=404, detail=f"Account '{account_key}' not found")
    
    # Generate cache key
    if date_filter == "range":
        cache_key = f"rpm:{account_key}:range:{start_date}:{end_date}"
    else:
        cache_key = f"rpm:{account_key}:{date_filter}:{custom_date}"
    
    # Check cache first
    cache = get_cache_manager()
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache HIT for RPM {account_key}")
        return cached_result
    
    logger.info(f"Cache MISS for RPM {account_key}")
    
    try:
        def fetch_rpm_data():
            service = get_adsense_service(account_key)
            full_account_name = get_account_id(service, account_key)
            
            if date_filter == "range":
                # Date range mode
                start_dt, end_dt = parse_date_range(date_filter, custom_date, start_date, end_date)
                
                request = service.accounts().reports().generate(
                    account=full_account_name,
                    dateRange='CUSTOM',
                    startDate_year=start_dt.year,
                    startDate_month=start_dt.month,
                    startDate_day=start_dt.day,
                    endDate_year=end_dt.year,
                    endDate_month=end_dt.month,
                    endDate_day=end_dt.day,
                    metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
                )
                report = request.execute()
                
                if 'rows' in report and report['rows']:
                    row = report['rows'][0]
                    total_earnings_micros = float(row['cells'][0]['value'] or 0)
                    total_clicks = int(row['cells'][1]['value'] or 0)
                    total_impressions = int(row['cells'][2]['value'] or 0)
                    total_page_views = int(row['cells'][3]['value'] or 0)
                    
                    total_earnings_idr = convert_micros_to_idr(total_earnings_micros)
                    days_in_range = (end_dt - start_dt).days + 1
                    
                    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
                    cpm = (total_earnings_idr / total_impressions * 1000) if total_impressions > 0 else 0
                    rpm = (total_earnings_idr / total_page_views * 1000) if total_page_views > 0 else 0
                    
                    return RPMData(
                        date=f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
                        account_key=account_key,
                        account_id=account_data.get("account_id"),
                        earnings_idr=round(total_earnings_idr, 2),
                        earnings_micros=int(total_earnings_micros),
                        page_views=total_page_views,
                        rpm_idr=round(rpm, 2),
                        impressions=total_impressions,
                        clicks=total_clicks,
                        ctr=round(ctr, 2),
                        cpm_idr=round(cpm, 2),
                        data_age_days=0,
                        note=f"RPM agregasi {days_in_range} hari periode {start_dt.strftime('%Y-%m-%d')} - {end_dt.strftime('%Y-%m-%d')}"
                    )
                else:
                    start_dt, end_dt = parse_date_range(date_filter, custom_date, start_date, end_date)
                    return RPMData(
                        date=f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
                        account_key=account_key,
                        account_id=account_data.get("account_id"),
                        earnings_idr=0, earnings_micros=0, page_views=0, rpm_idr=0,
                        impressions=0, clicks=0, ctr=0, cpm_idr=0, data_age_days=0,
                        note="Tidak ada data untuk periode ini"
                    )
            
            # Single day mode - existing logic
            if date_filter and date_filter != "range":
                # Specific date filtering - single attempt
                target_date = parse_date_filter(date_filter, custom_date)
                days_to_try = [target_date]
                days_back_values = [0]  # For response metadata
            else:
                # Default auto-retry logic - multiple attempts
                days_to_try = [datetime.now() - timedelta(days=i) for i in [0, 1, 2, 3]]
                days_back_values = [0, 1, 2, 3]
            
            # Try each target date
            for i, target_date in enumerate(days_to_try):
                try:
                    days_back = days_back_values[i] if not date_filter else (datetime.now() - target_date).days
                    
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
                    
                    if 'rows' in report and report['rows']:
                        row = report['rows'][0]
                        earnings_micros = float(row['cells'][0]['value'] or 0)
                        clicks = int(row['cells'][1]['value'] or 0)
                        impressions = int(row['cells'][2]['value'] or 0)
                        page_views = int(row['cells'][3]['value'] or 0)
                        
                        earnings_idr = convert_micros_to_idr(earnings_micros)
                        ctr = (clicks / impressions * 100) if impressions > 0 else 0
                        cpm = (earnings_idr / impressions * 1000) if impressions > 0 else 0
                        rpm = (earnings_idr / page_views * 1000) if page_views > 0 else 0
                        
                        return RPMData(
                            date=target_date.strftime('%Y-%m-%d'),
                            account_key=account_key,
                            account_id=account_data.get("account_id"),
                            earnings_idr=round(earnings_idr, 2),
                            earnings_micros=int(earnings_micros),
                            page_views=page_views,
                            rpm_idr=round(rpm, 2),
                            impressions=impressions,
                            clicks=clicks,
                            ctr=round(ctr, 2),
                            cpm_idr=round(cpm, 2),
                            data_age_days=days_back,
                            note=f"Data terbaru dari {days_back} hari yang lalu" if days_back > 0 else "Data hari ini"
                        )
                        
                except Exception as e:
                    logger.warning(f"Error fetching RPM data for {days_back} days back: {e}")
                    continue
            
            # No data found
            return RPMData(
                date=datetime.now().strftime('%Y-%m-%d'),
                account_key=account_key,
                account_id=account_data.get("account_id"),
                earnings_idr=0,
                earnings_micros=0,
                page_views=0,
                rpm_idr=0,
                impressions=0,
                clicks=0,
                ctr=0,
                cpm_idr=0,
                data_age_days=-1,
                note="Data belum tersedia. AdSense memiliki delay 1-3 hari untuk reporting."
            )
        
        rpm_data = await run_in_executor(fetch_rpm_data)
        
        # Cache the result for 1 minute
        cache.set(cache_key, rpm_data, ttl=60)
        
        return rpm_data
        
    except Exception as e:
        logger.error(f"Error fetching RPM data for {account_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/summary", 
    response_model=MultiAccountSummary,
    tags=["Multi-Account"],
    summary="Multi-Account Summary",
    description="Get combined earnings summary from all configured AdSense accounts.",
    responses={
        200: {
            "description": "Multi-account summary retrieved successfully"
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Error fetching account data"}
                }
            }
        }
    }
)
async def get_multi_account_summary(
    date_filter: Optional[DateFilter] = Query(
        None, 
        description="Date filter: 'today', 'yesterday', 'custom', or 'range'. If not specified, uses auto-retry logic."
    ),
    custom_date: Optional[str] = Query(
        None, 
        description="Custom date in YYYY-MM-DD format (required when date_filter='custom')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    start_date: Optional[str] = Query(
        None,
        description="Start date in YYYY-MM-DD format (required when date_filter='range')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date in YYYY-MM-DD format (required when date_filter='range')",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
):
    """
    ## 📈 Multi-Account Dashboard
    
    Get comprehensive earnings summary across all configured AdSense accounts:
    
    ### Features:
    - **🏢 All Accounts**: Combined data from perpustakaan.id + gowesgo.com
    - **📊 Aggregated Metrics**: Total earnings, clicks, impressions across accounts
    - **📈 Performance Indicators**: Overall CTR and CPM calculations
    - **📋 Individual Breakdown**: Per-account performance details
    - **📅 Date Flexibility**: Same date filtering as individual endpoints
    
    ### Use Cases:
    - **📊 Dashboard Overview**: Quick snapshot of all account performance
    - **📈 Comparative Analysis**: Compare performance between accounts
    - **💰 Revenue Tracking**: Total earnings across all properties
    - **📋 Account Health**: Monitor status of all configured accounts
    
    ### Examples:
    - `GET /api/summary` - Auto-retry logic for recent data
    - `GET /api/summary?date_filter=yesterday` - Yesterday's combined data
    - `GET /api/summary?date_filter=custom&custom_date=2025-10-01` - Specific date
    """
    # Generate cache key for multi-account summary
    account_db = get_account_database()
    if date_filter == "range":
        cache_key = f"summary:multi:range:{start_date}:{end_date}"
    else:
        cache_key = f"summary:multi:{date_filter}:{custom_date}"
    
    # Check cache first
    cache = get_cache_manager()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        def fetch_all_accounts():
            accounts_data = []
            total_earnings = 0
            total_earnings_micros = 0
            total_clicks = 0
            total_impressions = 0
            total_page_views = 0
            
            # Determine date range
            if date_filter == "range":
                start_dt, end_dt = parse_date_range(date_filter, custom_date, start_date, end_date)
                date_str = f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
            elif date_filter:
                start_dt, end_dt = parse_date_range(date_filter, custom_date, start_date, end_date)
                date_str = start_dt.strftime('%Y-%m-%d')
            else:
                start_dt = end_dt = datetime.now()
                date_str = start_dt.strftime('%Y-%m-%d')
            
            for account_key in account_db.get_all_accounts().keys():
                try:
                    service = get_adsense_service(account_key)
                    full_account_name = get_account_id(service, account_key)
                    
                    request = service.accounts().reports().generate(
                        account=full_account_name,
                        dateRange='CUSTOM',
                        startDate_year=start_dt.year,
                        startDate_month=start_dt.month,
                        startDate_day=start_dt.day,
                        endDate_year=end_dt.year,
                        endDate_month=end_dt.month,
                        endDate_day=end_dt.day,
                        metrics=['ESTIMATED_EARNINGS', 'CLICKS', 'IMPRESSIONS', 'PAGE_VIEWS']
                    )
                    report = request.execute()
                    
                    account_earnings = 0
                    account_clicks = 0
                    account_impressions = 0
                    account_page_views = 0
                    
                    if 'rows' in report and report['rows']:
                        row = report['rows'][0]
                        account_earnings_micros = float(row['cells'][0]['value'] or 0)
                        account_earnings = convert_micros_to_idr(account_earnings_micros)
                        account_clicks = int(row['cells'][1]['value'] or 0)
                        account_impressions = int(row['cells'][2]['value'] or 0)
                        account_page_views = int(row['cells'][3]['value'] or 0)
                    
                    account_rpm = (account_earnings / account_page_views * 1000) if account_page_views > 0 else 0
                    
                    account_data = {
                        "account_key": account_key,
                        "account_id": account_db.get_account(account_key).get("account_id"),
                        "display_name": account_db.get_account(account_key).get("display_name"),
                        "status": "active",
                        "earnings_idr": round(account_earnings, 2),
                        "earnings_micros": int(account_earnings_micros),
                        "clicks": account_clicks,
                        "impressions": account_impressions,
                        "page_views": account_page_views,
                        "rpm_idr": round(account_rpm, 2)
                    }
                    
                    accounts_data.append(account_data)
                    total_earnings += account_earnings
                    total_earnings_micros += account_earnings_micros
                    total_clicks += account_clicks
                    total_impressions += account_impressions
                    total_page_views += account_page_views
                    
                except Exception as e:
                    logger.warning(f"Error fetching data for {account_key}: {e}")
                    accounts_data.append({
                        "account_key": account_key,
                        "account_id": account_db.get_account(account_key).get("account_id"),
                        "display_name": account_db.get_account(account_key).get("display_name"),
                        "status": "error",
                        "earnings_idr": 0,
                        "earnings_micros": 0,
                        "clicks": 0,
                        "impressions": 0,
                        "page_views": 0,
                        "rpm_idr": 0,
                        "error": str(e)
                    })
            
            overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            overall_cpm = (total_earnings / total_impressions * 1000) if total_impressions > 0 else 0
            overall_rpm = (total_earnings / total_page_views * 1000) if total_page_views > 0 else 0
            
            return MultiAccountSummary(
                date=date_str,
                total_accounts=len(account_db.get_all_accounts()),
                total_earnings_idr=round(total_earnings, 2),
                total_earnings_micros=int(total_earnings_micros),
                total_clicks=total_clicks,
                total_impressions=total_impressions,
                total_page_views=total_page_views,
                overall_ctr=round(overall_ctr, 2),
                overall_cpm_idr=round(overall_cpm, 2),
                overall_rpm_idr=round(overall_rpm, 2),
                accounts=accounts_data
            )
        
        summary = await run_in_executor(fetch_all_accounts)
        
        # Cache the result for 1 minute
        cache.set(cache_key, summary, ttl=60)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error fetching multi-account summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Database Management Endpoints

@app.get(
    "/api/database/stats",
    response_model=dict,
    tags=["Database Management"],
    summary="Database Statistics",
    description="Get comprehensive database statistics and metadata."
)
async def get_database_stats():
    """
    ## 📊 Database Statistics
    
    Get comprehensive information about the accounts database:
    
    ### Includes:
    - **Account Counts**: Total, active, inactive accounts
    - **Database Metadata**: Version, creation date, last modified
    - **File Status**: Database file size and location
    - **Health Check**: Database validation status
    
    ### Use Cases:
    - Monitor database health
    - Track account growth
    - Verify database integrity
    - System administration
    """
    try:
        stats = account_db.get_statistics()
        metadata = account_db.get_metadata()
        
        # Get file info
        db_path = account_db.db_path
        file_size = os.path.getsize(db_path) if db_path.exists() else 0
        
        # Validate database
        validation_errors = account_db.validate_database()
        
        return {
            "database_info": {
                "path": str(db_path),
                "size_bytes": file_size,
                "size_kb": round(file_size / 1024, 2),
                "exists": db_path.exists(),
                "is_healthy": len(validation_errors) == 0
            },
            "statistics": stats,
            "metadata": metadata,
            "validation": {
                "is_valid": len(validation_errors) == 0,
                "errors": validation_errors
            },
            "accounts_summary": {
                "total": len(account_db.get_all_accounts()),
                "active": len(account_db.get_active_accounts()),
                "account_keys": list(account_db.get_all_accounts().keys())
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/database/search",
    response_model=List[dict],
    tags=["Database Management"],
    summary="Search Accounts",
    description="Search accounts by name, description, or metadata."
)
async def search_accounts(
    query: str = Query(..., description="Search query", min_length=2)
):
    """
    ## 🔍 Search Accounts
    
    Search through all accounts by various criteria:
    
    ### Search Fields:
    - **Display Name**: Human-readable account names
    - **Description**: Account descriptions
    - **Website URL**: Associated website URLs
    - **Notes**: Custom notes and metadata
    - **Account Key**: Internal identifiers
    
    ### Examples:
    - Search for "perpustakaan" - finds perpustakaan.id account
    - Search for "education" - finds accounts with education category
    - Search for ".com" - finds accounts with .com websites
    
    ### Use Cases:
    - Find accounts by website domain
    - Locate accounts by category or description
    - Quick account lookup for administration
    """
    try:
        results = account_db.search_accounts(query)
        
        # Format results for API response
        formatted_results = []
        for account in results:
            formatted_results.append({
                "account_key": account.get("account_key"),
                "account_id": account.get("account_id"),
                "display_name": account.get("display_name"),
                "description": account.get("description"),
                "status": account.get("status"),
                "created_at": account.get("created_at"),
                "metadata": account.get("metadata", {})
            })
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/database/backup",
    response_model=dict,
    tags=["Database Management"], 
    summary="Create Database Backup",
    description="Create a backup of the accounts database."
)
async def create_database_backup(
    backup_name: Optional[str] = Query(None, description="Custom backup filename")
):
    """
    ## 💾 Create Database Backup
    
    Create a backup copy of the accounts database:
    
    ### Features:
    - **Automatic Naming**: Uses timestamp if no name provided
    - **Safe Operation**: Creates backup without interrupting service
    - **Metadata Update**: Updates last backup timestamp
    - **File Verification**: Confirms backup was created successfully
    
    ### Backup Format:
    - **Extension**: .json (same format as main database)
    - **Content**: Complete copy of accounts.json with all data
    - **Location**: Same directory as main database
    
    ### Recommended Schedule:
    - Before major changes
    - Daily for production systems
    - Before account additions/removals
    """
    try:
        backup_path = account_db.create_backup(backup_name)
        
        # Get backup file info
        backup_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
        
        return {
            "success": True,
            "message": "Database backup created successfully",
            "backup_path": backup_path,
            "backup_size_bytes": backup_size,
            "backup_size_kb": round(backup_size / 1024, 2),
            "created_at": datetime.now().isoformat(),
            "accounts_backed_up": len(account_db.get_all_accounts())
        }
        
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/database/restore",
    response_model=dict,
    tags=["Database Management"],
    summary="Restore Database",
    description="Restore accounts database from backup file."
)
async def restore_database(
    backup_file: UploadFile = File(..., description="Backup file to restore from")
):
    """
    ## 🔄 Restore Database
    
    Restore accounts database from a backup file:
    
    ### Safety Features:
    - **Pre-restore Backup**: Creates backup of current database
    - **Validation**: Verifies backup file integrity before restore
    - **Rollback Support**: Can revert if restore fails
    - **Service Continuity**: Updates in-memory cache after restore
    
    ### Process:
    1. Validate uploaded backup file
    2. Create backup of current database
    3. Restore from uploaded file
    4. Refresh account configurations
    5. Verify restore success
    
    ### File Requirements:
    - **Format**: Valid JSON database format
    - **Structure**: Must contain accounts section
    - **Size**: Reasonable file size limits
    """
    try:
        # Validate file type
        if not backup_file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Backup file must be JSON format")
        
        # Read backup file content
        content = await backup_file.read()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write(content.decode('utf-8'))
            temp_path = temp_file.name
        
        try:
            # Restore from temporary file
            account_db.restore_from_backup(temp_path)
            
            # Refresh global account configs
            global ACCOUNT_CONFIGS
            ACCOUNT_CONFIGS = get_account_configs()
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return {
                "success": True,
                "message": "Database restored successfully",
                "restored_from": backup_file.filename,
                "restored_at": datetime.now().isoformat(),
                "total_accounts": len(account_db.get_all_accounts()),
                "account_keys": list(account_db.get_all_accounts().keys())
            }
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
        
    except Exception as e:
        logger.error(f"Error restoring database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/api/accounts/{account_key}/update",
    response_model=dict,
    tags=["Account Management"],
    summary="Update Account",
    description="Update account information and metadata."
)
async def update_account_endpoint(
    account_key: str = Path(..., description="Account identifier"),
    display_name: Optional[str] = Query(None, description="New display name"),
    description: Optional[str] = Query(None, description="New description"),
    website_url: Optional[str] = Query(None, description="Website URL"),
    category: Optional[str] = Query(None, description="Account category"),
    notes: Optional[str] = Query(None, description="Additional notes")
):
    """
    ## ✏️ Update Account Information
    
    Update account details and metadata:
    
    ### Updatable Fields:
    - **Display Name**: Human-readable account name
    - **Description**: Account description
    - **Website URL**: Associated website
    - **Category**: Account category (e.g., education, lifestyle)
    - **Notes**: Custom notes and information
    
    ### Restrictions:
    - Cannot change account_key (use for identification only)
    - Cannot change account_id (Google AdSense publisher ID)
    - File paths updated automatically if needed
    
    ### Use Cases:
    - Update website URLs after domain changes
    - Add categorization for better organization
    - Update descriptions for clarity
    - Add operational notes
    """
    account_data = account_db.get_account(account_key)
    if not account_data:
        raise HTTPException(status_code=404, detail=f"Account '{account_key}' not found")
    
    try:
        # Build updates dictionary
        updates = {}
        metadata_updates = {}
        
        if display_name is not None:
            updates["display_name"] = display_name
        if description is not None:
            updates["description"] = description
        if website_url is not None:
            metadata_updates["website_url"] = website_url
        if category is not None:
            metadata_updates["category"] = category
        if notes is not None:
            metadata_updates["notes"] = notes
        
        if metadata_updates:
            updates["metadata"] = metadata_updates
        
        if not updates:
            return {
                "success": False,
                "message": "No updates provided",
                "account_key": account_key
            }
        
        # Update account
        updated_account = account_db.update_account(account_key, updates)
        
        # Refresh global account configs
        global ACCOUNT_CONFIGS
        ACCOUNT_CONFIGS = get_account_configs()
        
        return {
            "success": True,
            "message": f"Account '{account_key}' updated successfully",
            "account_key": account_key,
            "updated_fields": list(updates.keys()),
            "account_data": {
                "display_name": updated_account.get("display_name"),
                "description": updated_account.get("description"),
                "status": updated_account.get("status"),
                "updated_at": updated_account.get("updated_at"),
                "metadata": updated_account.get("metadata", {})
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating account {account_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup event to validate database
@app.on_event("startup")
async def startup_event():
    """Validate database on startup."""
    try:
        validation_errors = account_db.validate_database()
        if validation_errors:
            logger.warning(f"Database validation warnings: {validation_errors}")
        else:
            logger.info("Database validation successful")
        
        logger.info(f"Loaded {len(account_db.get_all_accounts())} accounts from database")
        
    except Exception as e:
        logger.error(f"Database startup error: {e}")

# ================================
# CACHE MANAGEMENT ENDPOINTS
# ================================

@app.get(
    "/api/cache/stats",
    tags=["Cache Management"],
    summary="Get Cache Statistics",
    description="Get comprehensive cache statistics including hit rate, total entries, and performance metrics"
)
async def get_cache_stats():
    """
    ## 📊 Cache Statistics
    
    Get detailed cache performance metrics:
    - **Total Entries**: Current number of cached items
    - **Hit Rate**: Percentage of cache hits vs misses
    - **Request Stats**: Total requests, hits, misses
    - **TTL Info**: Default TTL settings
    
    ### Useful for:
    - Monitoring cache performance
    - Optimizing cache TTL settings
    - Debugging cache-related issues
    """
    try:
        cache = get_cache_manager()
        stats = cache.get_stats()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "cache_stats": stats,
            "message": "Cache statistics retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/cache/entries",
    tags=["Cache Management"],
    summary="Get Cache Entries Info",
    description="Get detailed information about all cached entries including TTL and expiration times"
)
async def get_cache_entries():
    """
    ## 🗂️ Cache Entries
    
    Get detailed information about all cache entries:
    - **Entry Details**: Key, creation time, expiration time
    - **TTL Information**: Remaining TTL and expiration status
    - **Value Metadata**: Type and size information
    - **Sorted by Creation Time**: Most recent entries first
    
    ### Useful for:
    - Debugging specific cache entries
    - Monitoring cache content
    - Understanding cache usage patterns
    """
    try:
        cache = get_cache_manager()
        entries = cache.get_cache_info()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "total_entries": len(entries),
            "entries": entries,
            "message": f"Found {len(entries)} cache entries"
        }
    except Exception as e:
        logger.error(f"Error getting cache entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/cache/clear",
    tags=["Cache Management"],
    summary="Clear All Cache",
    description="Clear all cached entries. Use with caution as this will force fresh API calls for all subsequent requests."
)
async def clear_cache():
    """
    ## 🗑️ Clear Cache
    
    Clear all cached entries immediately:
    - **Removes All Entries**: Clears all cached data
    - **Immediate Effect**: Next requests will hit the API
    - **Performance Impact**: Subsequent requests will be slower until cache rebuilds
    
    ### When to Use:
    - After configuration changes
    - When debugging cache issues
    - To force fresh data retrieval
    - During maintenance periods
    
    ⚠️ **Warning**: Use carefully in production as it will temporarily increase API calls and response times.
    """
    try:
        cache = get_cache_manager()
        cleared_count = cache.clear()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "cleared_entries": cleared_count,
            "message": f"Successfully cleared {cleared_count} cache entries"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/cache/cleanup",
    tags=["Cache Management"],
    summary="Cleanup Expired Entries",
    description="Remove only expired cache entries, keeping valid ones intact"
)
async def cleanup_expired_cache():
    """
    ## 🧹 Cleanup Expired Cache
    
    Remove only expired cache entries:
    - **Selective Removal**: Only removes expired entries
    - **Keeps Valid Data**: Active cache entries remain intact
    - **Memory Optimization**: Frees up memory from expired entries
    - **Safe Operation**: No impact on performance
    
    ### Benefits:
    - Optimize memory usage
    - Clean up stale entries
    - Maintain cache performance
    - Safe for production use
    """
    try:
        cache = get_cache_manager()
        expired_count = cache.cleanup_expired()
        stats = cache.get_stats()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "expired_entries_removed": expired_count,
            "remaining_entries": stats["total_entries"],
            "message": f"Cleaned up {expired_count} expired entries, {stats['total_entries']} entries remaining"
        }
    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/api/cache/entry/{cache_key}",
    tags=["Cache Management"],
    summary="Delete Specific Cache Entry",
    description="Delete a specific cache entry by its key"
)
async def delete_cache_entry(cache_key: str):
    """
    ## 🎯 Delete Specific Entry
    
    Delete a specific cache entry by key:
    - **Targeted Removal**: Remove only specified entry
    - **Precise Control**: Delete specific cached data
    - **Safe Operation**: Other entries remain intact
    
    ### Use Cases:
    - Remove specific stale data
    - Force refresh of particular endpoint
    - Selective cache management
    
    **Note**: Cache keys are auto-generated. Use `/api/cache/entries` to see available keys.
    """
    try:
        cache = get_cache_manager()
        deleted = cache.delete(cache_key)
        
        if deleted:
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "cache_key": cache_key,
                "message": f"Successfully deleted cache entry: {cache_key}"
            }
        else:
            return {
                "success": False,
                "timestamp": datetime.now().isoformat(),
                "cache_key": cache_key,
                "message": f"Cache entry not found: {cache_key}"
            }
    except Exception as e:
        logger.error(f"Error deleting cache entry {cache_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)