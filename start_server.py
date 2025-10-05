#!/usr/bin/env python3
"""
Start script untuk AdSense API Backend
Menyediakan berbagai cara untuk menjalankan aplikasi
"""

import os
import sys
import argparse
import subprocess

def install_requirements():
    """Install dependencies dari requirements.txt"""
    print("Installing requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

def run_development():
    """Jalankan server dalam mode development dengan uvicorn"""
    print("Starting development server with uvicorn...")
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "app:app", 
        "--host", "0.0.0.0", 
        "--port", "8000", 
        "--reload",
        "--log-level", "info"
    ])

def run_production():
    """Jalankan server dalam mode production dengan gunicorn"""
    print("Starting production server with gunicorn...")
    subprocess.run([
        sys.executable, "-m", "gunicorn", 
        "--config", "gunicorn_config.py",
        "app:app"
    ])

def run_unicorn_style():
    """Jalankan server dengan konfigurasi Unicorn-style"""
    print("Starting server with Unicorn-compatible configuration...")
    subprocess.run([
        sys.executable, "-m", "gunicorn",
        "--bind", "0.0.0.0:8000",
        "--workers", "4",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--timeout", "30",
        "--keepalive", "2",
        "--max-requests", "1000",
        "--preload",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "app:app"
    ])

def main():
    parser = argparse.ArgumentParser(description='AdSense API Backend Starter')
    parser.add_argument('--mode', choices=['dev', 'prod', 'unicorn'], default='dev',
                       help='Mode untuk menjalankan server (default: dev)')
    parser.add_argument('--install', action='store_true',
                       help='Install requirements sebelum menjalankan')
    
    args = parser.parse_args()
    
    if args.install:
        install_requirements()
    
    if args.mode == 'dev':
        run_development()
    elif args.mode == 'prod':
        run_production()
    elif args.mode == 'unicorn':
        run_unicorn_style()

if __name__ == "__main__":
    main()