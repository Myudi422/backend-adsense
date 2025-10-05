# Multi-Account AdSense API v2.0

## 🎯 Overview

Sistem API yang diperbaiki untuk manage multiple AdSense accounts dengan proper micros to IDR conversion. Mendukung perpustakaan.id, gowesgo.com, dan account lainnya.

## ✅ Fixed Issues dari v1.0

1. **Micros Conversion**: Sekarang benar `micros/1000 = IDR` (bukan USD)
2. **Data Mapping**: Fixed array access `row['cells'][0]['value']`
3. **API Parameters**: Updated ke format AdSense API v2 yang benar
4. **Multi-Account**: Support multiple accounts dengan credentials terpisah
5. **Rounding**: Preserve decimal places untuk nilai kecil

## 🚀 Quick Start

### 1. Setup Accounts
```bash
# List configured accounts
python account_manager.py list

# Setup OAuth untuk account tertentu  
python account_manager.py setup perpustakaan
python account_manager.py setup gowesgo

# Test API access
python account_manager.py test perpustakaan
```

### 2. Start API Server
```bash
# Start server
python app_v2.py

# Or with uvicorn
python -m uvicorn app_v2:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test API Endpoints
```bash
# Test all endpoints
python test_multi_account.py
```

## 📋 Account Configuration

### Current Accounts
- **perpustakaan**: Perpustakaan.id (pub-1777593071761494)
- **gowesgo**: GowesGo.com (auto-detect)

### File Structure
```
client_secrets.json           # Perpustakaan OAuth config
adsense.dat                  # Perpustakaan credentials
client_secrets-gowesgo.json  # GowesGo OAuth config  
adsense-gowesgo.dat         # GowesGo credentials
```

## 🌐 API Endpoints

### Base URL: `http://localhost:8000`

### 1. Root Info
```
GET /
```
Returns API info and available accounts.

### 2. List Accounts
```
GET /api/accounts
```
Returns all configured accounts with status.

### 3. Today's Earnings
```
GET /api/today-earnings/{account_key}
```
Get today's earnings for specific account.

**Example Response:**
```json
{
  "date": "2025-10-03",
  "account_key": "perpustakaan", 
  "account_id": "pub-1777593071761494",
  "earnings_idr": 3.17,
  "earnings_micros": 3169,
  "clicks": 9,
  "impressions": 896,
  "page_views": 393,
  "ctr": 1.00,
  "cpm_idr": 3.54,
  "data_age_days": 0,
  "note": "Data hari ini"
}
```

### 4. Domain Breakdown
```
GET /api/domain-earnings/{account_key}
GET /api/domain-earnings/{account_key}?domain=perpustakaan.id
```
Get earnings breakdown by domain/subdomain.

### 5. Multi-Account Summary
```
GET /api/summary
```
Get combined summary from all accounts.

## 🔧 Adding New Accounts

### Method 1: Using Account Manager
```bash
python account_manager.py add newsite "New Site Name" client_secrets-newsite.json
```

### Method 2: Manual Configuration

1. **Create OAuth Config**: Get `client_secrets-{name}.json` from Google Cloud Console

2. **Add to ACCOUNT_CONFIGS** in `app_v2.py`:
```python
"newsite": {
    "client_secrets": "client_secrets-newsite.json",
    "credentials_file": "adsense-newsite.dat", 
    "display_name": "New Site Name",
    "account_id": "auto-detect"
}
```

3. **Setup OAuth**:
```bash
python account_manager.py setup newsite
```

## 💡 Usage Examples

### Python Client
```python
import requests

# Get perpustakaan earnings
response = requests.get("http://localhost:8000/api/today-earnings/perpustakaan")
data = response.json()
print(f"Earnings: Rp {data['earnings_idr']:.2f}")

# Get domain breakdown
response = requests.get("http://localhost:8000/api/domain-earnings/perpustakaan")
domains = response.json()
for domain in domains['domains']:
    print(f"{domain['domain']}: Rp {domain['earnings_idr']:.2f}")
```

### JavaScript/Frontend
```javascript
// Get today's earnings
fetch('http://localhost:8000/api/today-earnings/perpustakaan')
  .then(response => response.json())
  .then(data => {
    console.log(`Earnings: Rp ${data.earnings_idr}`);
    console.log(`Clicks: ${data.clicks}`);
  });

// Get multi-account summary  
fetch('http://localhost:8000/api/summary')
  .then(response => response.json())
  .then(data => {
    console.log(`Total: Rp ${data.total_earnings_idr}`);
    data.accounts.forEach(account => {
      console.log(`${account.display_name}: Rp ${account.earnings_idr}`);
    });
  });
```

## 🎯 Key Features

- ✅ **Proper IDR Conversion**: `micros/1000 = IDR`
- ✅ **Multi-Account Support**: Manage multiple AdSense accounts
- ✅ **Domain Breakdown**: See earnings per domain/subdomain  
- ✅ **Fallback Logic**: Try multiple days if today's data unavailable
- ✅ **Error Handling**: Graceful handling of API errors
- ✅ **Easy Management**: Account manager tools
- ✅ **Auto-Detection**: Automatic account ID detection
- ✅ **CORS Support**: Ready for frontend integration

## 🔍 Troubleshooting

### Common Issues

1. **"Account not found"**
   - Run `python account_manager.py list` to check status
   - Setup OAuth: `python account_manager.py setup {account_key}`

2. **"Authentication failed"**
   - Delete credentials file: `adsense-{account}.dat`
   - Re-setup: `python account_manager.py setup {account_key}`

3. **"0 earnings"**
   - AdSense has 1-3 day reporting delay
   - Check `data_age_days` in response
   - Verify ads are properly setup

4. **"Connection refused"**
   - Start server: `python app_v2.py`
   - Check port 8000 is available

### Logs & Debugging
```bash
# Check server logs
python app_v2.py

# Test specific account
python account_manager.py test perpustakaan

# Validate setup
python test_multi_account.py setup
```

## 📈 Performance Notes

- Each account requires separate API calls
- Credentials are cached after first authentication
- Use domain filtering to reduce response size
- Consider rate limiting for production use

## 🔐 Security Notes

- Keep `client_secrets-*.json` files secure
- Credentials files contain access tokens
- Use HTTPS in production
- Consider OAuth token refresh handling

---

**Status: ✅ Production Ready**  
**Version: 2.0.0**  
**Last Updated: October 2025**