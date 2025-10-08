# 🚀 Deployment Guide: AdSense Backend ke Vercel

Panduan lengkap untuk mendeploy AdSense Backend Python ke Vercel.

## 📋 Prerequisites

1. **Akun Vercel**: [Daftar di vercel.com](https://vercel.com)
2. **Vercel CLI**: Install dengan `npm i -g vercel`
3. **Git Repository**: Push code ke GitHub/GitLab/Bitbucket

## 🔧 Persiapan Project

### 1. File Konfigurasi yang Sudah Dibuat

✅ `vercel.json` - Konfigurasi utama Vercel  
✅ `api/index.py` - Entry point untuk serverless function  
✅ `.env.example` - Template environment variables  
✅ `.vercelignore` - File yang diabaikan saat deploy  
✅ `requirements.txt` - Dependencies yang sudah disesuaikan untuk Vercel  

### 2. Struktur Project untuk Vercel

```
backend/
├── api/
│   └── index.py           # Entry point Vercel
├── vercel.json           # Konfigurasi Vercel
├── requirements.txt      # Python dependencies
├── .env.example         # Template environment variables
├── .vercelignore        # Files to ignore
├── app_v2.py           # Main FastAPI application
├── app.py              # Fallback FastAPI application
├── account_database.py  # Database utilities
├── cache_manager.py     # Cache utilities
├── adsense_util.py     # AdSense utilities
└── client_secrets-*.json # Google OAuth secrets
```

## 🌐 Deployment Steps

### Method 1: Deployment via Vercel Dashboard (Recommended)

1. **Connect Repository**
   - Buka [Vercel Dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import repository dari GitHub/GitLab/Bitbucket

2. **Configure Project**
   - Framework Preset: `Other`
   - Root Directory: `backend/` (jika repo memiliki multiple folders)
   - Build Command: (kosongkan)
   - Output Directory: (kosongkan)
   - Install Command: `pip install -r requirements.txt`

3. **Set Environment Variables**
   ```bash
   # Buka Project Settings > Environment Variables
   # Tambahkan variables berikut:
   
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret  
   GOOGLE_REDIRECT_URI=https://your-vercel-app.vercel.app
   DEFAULT_ADSENSE_ACCOUNT=gowesgo
   DATABASE_PATH=/tmp/accounts.json
   CACHE_TTL=3600
   ENABLE_CACHE=true
   LOG_LEVEL=INFO
   PRODUCTION_MODE=true
   ```

4. **Deploy**
   - Click "Deploy"
   - Tunggu proses build selesai

### Method 2: Deployment via Vercel CLI

1. **Login ke Vercel**
   ```bash
   vercel login
   ```

2. **Deploy dari Local**
   ```bash
   cd backend
   vercel --prod
   ```

3. **Set Environment Variables via CLI**
   ```bash
   vercel env add GOOGLE_CLIENT_ID production
   vercel env add GOOGLE_CLIENT_SECRET production
   # ... tambahkan semua environment variables
   ```

## 🔐 Environment Variables Setup

### 1. Google OAuth Credentials

Dapatkan dari [Google Cloud Console](https://console.cloud.google.com):

1. Buka Google Cloud Console
2. Pilih project atau buat baru
3. Enable AdSense Management API
4. Buat OAuth 2.0 Client ID
5. Tambahkan redirect URI: `https://your-vercel-app.vercel.app`
6. Download client secrets atau copy Client ID & Secret

### 2. Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | OAuth Client ID | `123456789-abc.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret | `GOCSPX-abcdefghijklmnop` |
| `GOOGLE_REDIRECT_URI` | OAuth Redirect URI | `https://your-app.vercel.app` |
| `DEFAULT_ADSENSE_ACCOUNT` | Default account | `gowesgo` |
| `DATABASE_PATH` | JSON database path | `/tmp/accounts.json` |

### 3. File Secrets (Client Secrets JSON)

Untuk file `client_secrets-*.json`, Anda memiliki 2 opsi:

**Option A: Environment Variables** (Recommended)
```bash
# Convert JSON file ke environment variable
GOWESGO_CLIENT_SECRETS='{"installed":{"client_id":"...","client_secret":"..."}}'
JANKLERK_CLIENT_SECRETS='{"installed":{"client_id":"...","client_secret":"..."}}'
```

**Option B: Runtime Download**
Upload file ke cloud storage (Google Drive, Dropbox) dan download saat runtime.

## 🧪 Testing Deployment

### 1. Check Health Endpoint
```bash
curl https://your-vercel-app.vercel.app/health
```

### 2. Check API Documentation
```
https://your-vercel-app.vercel.app/docs
```

### 3. Test AdSense Endpoints
```bash
# Get accounts
curl https://your-vercel-app.vercel.app/api/v2/accounts

# Get earnings
curl "https://your-vercel-app.vercel.app/api/v2/earnings/gowesgo?date_filter=today"
```

## 🚨 Common Issues & Solutions

### 1. Import Errors
**Problem**: `ModuleNotFoundError: No module named 'xxx'`
**Solution**: 
- Pastikan semua dependencies ada di `requirements.txt`
- Check Python path di `api/index.py`

### 2. File Not Found Errors
**Problem**: `FileNotFoundError: client_secrets-xxx.json`
**Solution**:
- Convert JSON files ke environment variables
- Atau upload ke cloud storage dan download saat runtime

### 3. OAuth Redirect Errors
**Problem**: `redirect_uri_mismatch`
**Solution**:
- Update redirect URI di Google Cloud Console
- Set `GOOGLE_REDIRECT_URI` environment variable dengan URL Vercel yang benar

### 4. Cold Start Timeout
**Problem**: Function timeout setelah 10 detik
**Solution**:
- Increase `maxDuration` di `vercel.json` (max 30s untuk hobby plan)
- Optimize code untuk mengurangi startup time
- Implement caching yang lebih efektif

### 5. Database Issues
**Problem**: Data tidak persisten antara requests
**Solution**:
- Gunakan external database (PostgreSQL, MongoDB)
- Atau gunakan Vercel KV untuk storage sederhana

## 📊 Monitoring & Logging

### 1. Vercel Dashboard
- View function invocations
- Check error logs
- Monitor performance

### 2. Custom Logging
```python
import logging
logger = logging.getLogger(__name__)

# Logs akan muncul di Vercel function logs
logger.info("Custom log message")
```

## 🔄 Continuous Deployment

Setelah setup awal, setiap push ke branch `main` akan otomatis trigger deployment baru.

### Git Workflow
```bash
git add .
git commit -m "Update backend features"
git push origin main
# Vercel akan otomatis deploy
```

## 📞 Support

Jika ada issues:
1. Check Vercel function logs
2. Test locally dengan `vercel dev`
3. Review environment variables
4. Check Google Cloud Console untuk OAuth issues

## 🎯 Next Steps

1. **Custom Domain**: Setup custom domain di Vercel
2. **SSL Certificate**: Otomatis disediakan Vercel
3. **Edge Functions**: Untuk performance yang lebih baik
4. **Database Integration**: Connect ke external database untuk persistensi
5. **Monitoring**: Setup APM untuk monitoring yang lebih advanced

---

*Happy Deploying! 🚀*