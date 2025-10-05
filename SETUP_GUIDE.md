# 🚀 AdSense API Backend - Setup Guide

## ⚠️ Prerequisites

Sebelum menjalankan backend AdSense API, pastikan Python sudah terinstall di sistem Anda.

### 1. Install Python

#### Opsi A: Microsoft Store (Recommended untuk Windows)
1. Buka Microsoft Store
2. Search "Python 3.11" atau "Python 3.12"
3. Click "Get" atau "Install"

#### Opsi B: Download dari python.org
1. Kunjungi https://python.org/downloads/
2. Download Python 3.8+ (recommended: 3.11 atau 3.12)
3. Jalankan installer dengan centang "Add Python to PATH"

#### Opsi C: Using Chocolatey (Windows Package Manager)
```powershell
# Install Chocolatey dulu jika belum ada
# Kemudian install Python
choco install python
```

### 2. Verifikasi Installation
Buka Command Prompt atau PowerShell, lalu test:
```bash
python --version
# atau
python3 --version
# atau
py --version
```

## 🔧 Setup Backend

### 1. Install Dependencies
```bash
# Menggunakan setup script (recommended)
powershell -ExecutionPolicy Bypass -File setup.ps1

# Atau manual
pip install -r requirements.txt
```

### 2. Konfigurasi Credentials
File `akun/adsense-perpus.json` sudah berisi credentials yang valid. Pastikan format seperti ini:
```json
{
  "web": {
    "client_id": "your_client_id.apps.googleusercontent.com",
    "project_id": "your_project_id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "your_client_secret"
  }
}
```

## 🚀 Menjalankan Server

### Development Mode (Recommended untuk testing)
```bash
python start_server.py --mode dev
```
- Auto-reload saat file berubah
- Detailed logging
- Swagger UI di http://localhost:8000/docs

### Production Mode (Gunicorn)
```bash
python start_server.py --mode prod
```
- Multiple workers
- Optimized untuk production
- Load balancing

### Unicorn-Compatible Mode
```bash
python start_server.py --mode unicorn
```
- Konfigurasi khusus kompatibel dengan Unicorn
- Production-ready dengan custom settings

### Install dan Run sekaligus
```bash
python start_server.py --install --mode dev
```

## 📡 API Endpoints

Server akan berjalan di `http://localhost:8000`

### Core Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - Swagger documentation
- `GET /redoc` - ReDoc documentation

### AdSense Data Endpoints
- `GET /api/accounts` - List semua accounts
- `GET /api/ad-units/{account_id}` - Ad units untuk account
- `GET /api/reports/{account_id}` - Generate reports
- `GET /api/summary` - Dashboard summary (⭐ MAIN FEATURE)

## 🎯 Testing API

### 1. Cek Server Status
```bash
curl http://localhost:8000/health
```

### 2. Lihat Summary Dashboard
```bash
curl http://localhost:8000/api/summary
```

### 3. Browser Testing
Buka browser dan kunjungi:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/api/summary (JSON response)

## 📊 Summary Dashboard Features

Endpoint `/api/summary` memberikan overview lengkap:

```json
{
  "accounts_count": 1,
  "ad_units_count": 5,
  "total_earnings": 125.50,
  "total_clicks": 1250,
  "total_impressions": 45000,
  "accounts": [...],
  "recent_earnings": {
    "period": "last_7_days",
    "earnings": 125.50,
    "clicks": 1250,
    "impressions": 45000,
    "ctr": 2.78,
    "cpm": 2.79
  }
}
```

## 🔐 Authentication Flow

Pada first run, aplikasi akan:
1. Membuka browser untuk Google OAuth2
2. Minta permission untuk akses AdSense
3. Simpan token di file `adsense.dat`
4. Token akan di-refresh otomatis

## 🐛 Troubleshooting

### Python tidak ditemukan
```bash
# Windows - Install dari Microsoft Store atau python.org
# Pastikan "Add to PATH" dicentang saat install
```

### Port sudah digunakan
```bash
# Ganti port
set PORT=8080
python start_server.py --mode dev
```

### Authentication Error
```bash
# Hapus file token dan authenticate ulang
del adsense.dat
python start_server.py --mode dev
```

### Memory Issues
```bash
# Kurangi workers di gunicorn_config.py
# Edit: workers = 2
```

## 📈 Production Deployment

### 1. Using Systemd (Linux)
```ini
[Unit]
Description=AdSense API Backend
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 start_server.py --mode prod
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Using PM2 (Node.js Process Manager)
```bash
pm2 start "python start_server.py --mode prod" --name adsense-api
```

### 3. Using Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "start_server.py", "--mode", "unicorn"]
```

## 🔧 Configuration

### Environment Variables
```bash
# Optional environment variables
set PORT=8000              # Server port
set HOST=0.0.0.0           # Bind host
set WORKERS=4              # Gunicorn workers
set RELOAD=true            # Development reload
```

### Gunicorn Settings
Edit `gunicorn_config.py` untuk custom configuration:
- Workers count
- Timeout settings  
- Memory limits
- SSL configuration

## 📚 Development

### Adding New Endpoints
1. Edit `app.py`
2. Add Pydantic models
3. Implement async functions
4. Test dengan development server

### Custom AdSense Queries
Gunakan existing utilities di `adsense_util.py` untuk:
- Custom authentication
- Account management
- API service creation

## 🎉 Success!

Jika semua setup berhasil, Anda akan memiliki:
- ✅ REST API untuk AdSense data
- ✅ Summary dashboard dengan metrics
- ✅ Swagger documentation
- ✅ Production-ready server
- ✅ Unicorn-compatible deployment

Server siap digunakan untuk frontend integration atau API testing! 🚀