# AdSense API Backend

Backend API untuk mengakses data Google AdSense dengan dashboard summary. Aplikasi ini menggunakan FastAPI dan dapat dijalankan dengan Gunicorn/Unicorn untuk production deployment.

## 🚀 Fitur

- **REST API** untuk mengakses data AdSense
- **Dashboard Summary** dengan metrics lengkap
- **Authentication** menggunakan OAuth2 Google
- **Async/Await** support untuk performa optimal
- **Production-ready** dengan Gunicorn/Unicorn
- **CORS enabled** untuk frontend integration
- **Swagger Documentation** tersedia di `/docs`

## 📋 Endpoints

### Core Endpoints
- `GET /` - Informasi API dan daftar endpoints
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

### AdSense Data Endpoints
- `GET /api/accounts` - Mendapatkan semua accounts
- `GET /api/ad-units/{account_id}` - Mendapatkan ad units untuk account tertentu
- `GET /api/reports/{account_id}` - Generate reports dengan parameter tanggal
- `GET /api/summary` - Dashboard summary lengkap
- `GET /api/today-earnings/{account_id}` - Estimasi penghasilan hari ini (dengan smart fallback)
- `GET /api/sites/{account_id}` - Semua sites/domains yang terdaftar
- `GET /api/earnings-by-site/{account_id}` - Breakdown earnings per site (jika tersedia)
- `GET /api/all-domains/{account_id}` - Semua domain dengan informasi detail
- `GET /api/recent-earnings/{account_id}?days=7` - Historical earnings beberapa hari terakhir
- `GET /api/subdomain-analysis/{account_id}` - Analisis subdomain dan rekomendasi setup
- `GET /api/custom-channels/{account_id}` - Custom channels dan earnings breakdown

## 🛠️ Setup & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Konfigurasi Credentials
Pastikan file `akun/adsense-perpus.json` berisi credentials Google OAuth2 yang valid.

### 3. Jalankan Server

#### Development Mode (dengan auto-reload):
```bash
python start_server.py --mode dev
```

#### Production Mode (dengan Gunicorn):
```bash
python start_server.py --mode prod
```

#### Unicorn-compatible Mode:
```bash
python start_server.py --mode unicorn
```

#### Install dan Jalankan sekaligus:
```bash
python start_server.py --install --mode dev
```

## 🎯 Cara Penggunaan

### 1. Cek Status Server
```bash
curl http://localhost:8000/health
```

### 2. Lihat Semua Accounts
```bash
curl http://localhost:8000/api/accounts
```

### 3. Lihat Summary Dashboard
```bash
curl http://localhost:8000/api/summary
```

### 4. Generate Report
```bash
curl "http://localhost:8000/api/reports/pub-1777593071761494?start_date=2024-01-01&end_date=2024-01-31&metrics=ESTIMATED_EARNINGS,CLICKS,IMPRESSIONS"
```

### 5. Cek Penghasilan Hari Ini
```bash
curl http://localhost:8000/api/today-earnings/pub-1777593071761494
```

### 6. Breakdown Earnings per Site/Domain
```bash
curl "http://localhost:8000/api/earnings-by-site/pub-1777593071761494?days=7"
```

### 7. Lihat Semua Domain
```bash
curl http://localhost:8000/api/all-domains/pub-1777593071761494
```

### 8. Analisis Subdomain & Setup Guide
```bash
curl http://localhost:8000/api/subdomain-analysis/pub-1777593071761494
```

### 9. Cek Custom Channels (untuk tracking per subdomain)
```bash
curl http://localhost:8000/api/custom-channels/pub-1777593071761494
```

## 📊 Response Examples

### Summary Dashboard Response:
```json
{
  "accounts_count": 1,
  "ad_units_count": 5,
  "total_earnings": 125.50,
  "total_clicks": 1250,
  "total_impressions": 45000,
  "accounts": [
    {
      "name": "accounts/pub-1234567890123456",
      "displayName": "My AdSense Account",
      "accountId": "pub-1234567890123456",
      "premium": false,
      "timeZone": "Asia/Jakarta"
    }
  ],
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

## 🔧 Configuration

### Gunicorn Configuration
Konfigurasi Gunicorn dapat diubah di `gunicorn_config.py`:
- Workers: 4 (default)
- Worker class: UvicornWorker
- Timeout: 30 seconds
- Max requests: 1000

### Environment Variables
Aplikasi akan menggunakan environment variables jika ada:
- `PORT` - Port untuk server (default: 8000)
- `HOST` - Host untuk bind (default: 0.0.0.0)
- `WORKERS` - Jumlah worker processes

## 🔐 Authentication

Aplikasi menggunakan Google OAuth2 untuk authentication dengan AdSense API. Pada first run, aplikasi akan membuka browser untuk authentication flow.

## 📈 Monitoring & Logging

- Access logs tersedia di stdout
- Error logs tersedia di stderr
- Health check endpoint: `/health`
- Metrics endpoint dalam summary: `/api/summary`

## 🌐 Subdomain Tracking Solutions

### Masalah: Hanya Domain Utama yang Terdeteksi
Jika API hanya menampilkan `perpustakaan.id` tanpa subdomain seperti `blog.perpustakaan.id`, ini normal karena keterbatasan AdSense API.

### Solusi 1: Setup Custom Channels (Recommended)
1. **Analisis Setup Saat Ini:**
   ```bash
   curl http://localhost:8000/api/subdomain-analysis/pub-1777593071761494
   ```

2. **Cek Custom Channels:**
   ```bash
   curl http://localhost:8000/api/custom-channels/pub-1777593071761494
   ```

3. **Setup Manual di AdSense Dashboard:**
   - Login ke [AdSense Dashboard](https://www.google.com/adsense/)
   - Buka **Sites → Channels**
   - Klik **Add channel → Custom channel**
   - Buat channel untuk setiap subdomain:
     - `Blog Channel` → Target: `blog.perpustakaan.id/*`
     - `API Channel` → Target: `api.perpustakaan.id/*`
     - `Admin Channel` → Target: `admin.perpustakaan.id/*`

### Solusi 2: Google Analytics 4 Integration
```bash
# Setelah GA4 terintegrasi, gunakan endpoint ini untuk cross-reference
curl http://localhost:8000/api/earnings-by-site/pub-1777593071761494?days=30
```

### Solusi 3: Manual URL Tracking
Implementasi tracking di level aplikasi dengan parameter custom di ad code.

## 🐛 Troubleshooting

### Authentication Error
```bash
# Re-authenticate jika terjadi error
rm adsense.dat
python start_server.py --mode dev
```

### Port Already in Use
```bash
# Ganti port jika 8000 sudah digunakan
PORT=8080 python start_server.py --mode dev
```

### Memory Issues
```bash
# Kurangi jumlah workers jika memory terbatas
python -m gunicorn --workers 2 --config gunicorn_config.py app:app
```

### Subdomain Not Showing in Breakdown
```bash
# Cek setup saat ini
curl http://localhost:8000/api/subdomain-analysis/pub-1777593071761494

# Lihat custom channels (jika sudah di-setup)
curl http://localhost:8000/api/custom-channels/pub-1777593071761494
```

## 📚 Development

### Project Structure
```
python/
├── app.py                 # Main FastAPI application
├── adsense_util.py       # AdSense utilities (modified)
├── start_server.py       # Server startup script
├── gunicorn_config.py    # Gunicorn configuration
├── requirements.txt      # Python dependencies
├── akun/
│   └── adsense-perpus.json   # OAuth2 credentials
└── [existing AdSense scripts...]
```

### Adding New Endpoints
1. Tambahkan endpoint di `app.py`
2. Buat Pydantic model jika diperlukan
3. Test dengan development server
4. Update dokumentasi

## 🚀 Deployment

### Docker (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "start_server.py", "--mode", "unicorn"]
```

### Systemd Service (Linux)
```ini
[Unit]
Description=AdSense API Backend
After=network.target

[Service]
Type=exec
User=your-user
Group=your-group
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 start_server.py --mode prod
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📄 License

Mengikuti lisensi dari Google AdSense API examples (Apache 2.0).