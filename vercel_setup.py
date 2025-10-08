#!/usr/bin/env python3
"""
Vercel Deployment Setup Script
Script untuk mempersiapkan deployment ke Vercel
"""

import os
import json
import sys
from typing import Dict, Any

def check_requirements():
    """Check apakah semua file yang dibutuhkan sudah ada"""
    required_files = [
        "vercel.json",
        "api/index.py", 
        "requirements.txt",
        ".env.example",
        ".vercelignore"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required files present")
    return True

def validate_vercel_json():
    """Validate vercel.json configuration"""
    try:
        with open("vercel.json", "r") as f:
            config = json.load(f)
        
        required_keys = ["version", "builds", "routes"]
        for key in required_keys:
            if key not in config:
                print(f"❌ Missing key '{key}' in vercel.json")
                return False
        
        print("✅ vercel.json is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating vercel.json: {e}")
        return False

def check_dependencies():
    """Check dependencies di requirements.txt"""
    required_deps = [
        "fastapi",
        "google-api-python-client", 
        "google-auth-oauthlib",
        "google-auth"
    ]
    
    try:
        with open("requirements.txt", "r") as f:
            deps = f.read().lower()
        
        missing_deps = []
        for dep in required_deps:
            if dep not in deps:
                missing_deps.append(dep)
        
        if missing_deps:
            print("❌ Missing dependencies:")
            for dep in missing_deps:
                print(f"   - {dep}")
            return False
        
        print("✅ All required dependencies present")
        return True
        
    except Exception as e:
        print(f"❌ Error checking dependencies: {e}")
        return False

def show_env_variables():
    """Show environment variables yang perlu di-set di Vercel"""
    env_vars = [
        ("GOOGLE_CLIENT_ID", "OAuth Client ID dari Google Cloud Console", True),
        ("GOOGLE_CLIENT_SECRET", "OAuth Client Secret dari Google Cloud Console", True),
        ("GOOGLE_REDIRECT_URI", "https://your-vercel-app.vercel.app", False),
        ("DEFAULT_ADSENSE_ACCOUNT", "gowesgo", False),
        ("DATABASE_PATH", "/tmp/accounts.json", False),
        ("CACHE_TTL", "3600", False),
        ("ENABLE_CACHE", "true", False),
        ("LOG_LEVEL", "INFO", False),
        ("PRODUCTION_MODE", "true", False)
    ]
    
    print("\n📋 Environment Variables untuk Vercel Dashboard:")
    print("=" * 60)
    
    for var_name, description, required in env_vars:
        status = "REQUIRED" if required else "OPTIONAL"
        print(f"🔧 {var_name}")
        print(f"   Description: {description}")
        print(f"   Status: {status}")
        print()

def show_deployment_steps():
    """Show step-by-step deployment instructions"""
    print("\n🚀 Vercel Deployment Steps:")
    print("=" * 40)
    
    steps = [
        "1. Push code ke GitHub/GitLab/Bitbucket repository",
        "2. Buka Vercel Dashboard (https://vercel.com/dashboard)",
        "3. Click 'New Project' dan import repository",
        "4. Set Framework Preset ke 'Other'",
        "5. Set Root Directory ke 'backend/' (jika diperlukan)",
        "6. Kosongkan Build Command dan Output Directory", 
        "7. Set Install Command ke 'pip install -r requirements.txt'",
        "8. Tambahkan Environment Variables (lihat list di atas)",
        "9. Click 'Deploy' dan tunggu proses selesai",
        "10. Test deployment dengan mengakses /docs endpoint"
    ]
    
    for step in steps:
        print(f"   {step}")

def main():
    """Main setup function"""
    print("🔧 AdSense Backend - Vercel Deployment Checker")
    print("=" * 50)
    
    # Check semua requirements
    all_good = True
    
    all_good &= check_requirements()
    all_good &= validate_vercel_json()  
    all_good &= check_dependencies()
    
    if all_good:
        print("\n🎉 Setup completed successfully!")
        print("Your project is ready for Vercel deployment.")
        
        show_env_variables()
        show_deployment_steps()
        
        print("\n📚 For detailed instructions, read:")
        print("   - VERCEL_DEPLOYMENT_GUIDE.md")
        
    else:
        print("\n❌ Setup incomplete!")
        print("Please fix the issues above before deploying.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())