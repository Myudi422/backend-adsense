"""
Vercel Environment Configuration Helper
Membantu setup OAuth credentials dari environment variables
"""

import os
import json
import tempfile
from typing import Dict, Any

def get_client_secrets_from_env(account_name: str) -> Dict[str, Any]:
    """
    Generate client_secrets dictionary dari environment variables
    
    Args:
        account_name: Nama account (gowesgo, janklerk, perpus, dll)
    
    Returns:
        Dictionary format client_secrets
    """
    # Try environment variable format
    env_var = f"{account_name.upper()}_CLIENT_SECRETS"
    secrets_json = os.getenv(env_var)
    
    if secrets_json:
        try:
            return json.loads(secrets_json)
        except json.JSONDecodeError:
            pass
    
    # Fallback to individual environment variables
    client_id = os.getenv(f"{account_name.upper()}_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv(f"{account_name.upper()}_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")
    
    if client_id and client_secret:
        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
            }
        }
    
    return None

def create_temp_client_secrets_file(account_name: str) -> str:
    """
    Buat temporary file untuk client_secrets dari environment variables
    
    Returns:
        Path ke temporary file, atau None jika gagal
    """
    secrets = get_client_secrets_from_env(account_name)
    
    if not secrets:
        raise ValueError(f"No client secrets found for account: {account_name}")
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', 
        suffix=f'_client_secrets_{account_name}.json',
        delete=False
    )
    
    json.dump(secrets, temp_file, indent=2)
    temp_file.close()
    
    return temp_file.name

def get_oauth_config() -> Dict[str, str]:
    """Get OAuth configuration dari environment variables"""
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080"),
        "scope": "https://www.googleapis.com/auth/adsense.readonly"
    }

def is_production() -> bool:
    """Check apakah running di production (Vercel)"""
    return os.getenv("VERCEL_ENV") == "production" or os.getenv("PRODUCTION_MODE") == "true"

# Available accounts configuration
AVAILABLE_ACCOUNTS = {
    "gowesgo": {
        "name": "GowesGo.com",
        "description": "Main AdSense account for GowesGo website"
    },
    "janklerk": {
        "name": "JankLerk",
        "description": "Secondary AdSense account"
    },
    "perpus": {
        "name": "Perpustakaan.id",
        "description": "Library website AdSense account"
    }
}