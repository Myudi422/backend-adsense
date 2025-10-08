"""
Vercel Entry Point for AdSense Backend
Entry point untuk deployment ke Vercel dengan proper error handling
"""

import os
import sys
import logging

# Setup logging untuk Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tambahkan root directory ke Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)

# Set environment untuk Vercel
os.environ.setdefault("PRODUCTION_MODE", "true")
if not os.getenv("VERCEL_ENV"):
    os.environ["VERCEL_ENV"] = "production"

try:
    # Import Vercel configuration helper
    from vercel_config import is_production, get_oauth_config
    
    # Log environment info
    logger.info(f"Running in production: {is_production()}")
    logger.info(f"Python path: {sys.path[:3]}...")  # Log first 3 paths
    
    # Import aplikasi FastAPI
    try:
        # Prioritaskan app_v2.py karena lebih lengkap
        from app_v2 import app
        logger.info("Successfully loaded app_v2")
    except ImportError as e:
        logger.warning(f"Failed to load app_v2: {e}")
        try:
            # Fallback ke app.py
            from app import app
            logger.info("Successfully loaded app.py as fallback")
        except ImportError as e2:
            logger.error(f"Failed to load both app_v2 and app: {e2}")
            raise
    
    # Export untuk Vercel
    handler = app
    
    # Untuk kompatibilitas dengan ASGI
    def application(scope, receive, send):
        return app(scope, receive, send)
    
    # Health check endpoint khusus untuk Vercel
    @app.get("/vercel-health")
    async def vercel_health():
        return {
            "status": "ok",
            "environment": "vercel",
            "production": is_production(),
            "timestamp": os.getenv("VERCEL_DEPLOYMENT_ID", "local")
        }
    
    logger.info("Vercel entry point setup completed successfully")

except Exception as e:
    logger.error(f"Critical error in Vercel entry point: {e}")
    
    # Create minimal fallback app
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI(title="AdSense Backend - Error State")
    
    @app.get("/")
    async def error_handler():
        return JSONResponse(
            status_code=500,
            content={
                "error": "Application failed to initialize",
                "message": str(e),
                "status": "error"
            }
        )
    
    handler = app