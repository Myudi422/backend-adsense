#!/usr/bin/env python3
"""
AdSense Account Manager
Easy management untuk multiple AdSense accounts
"""

import json
import os
import sys
from datetime import datetime
from app_v2 import ACCOUNT_CONFIGS, get_adsense_service, get_account_id

class AdSenseAccountManager:
    def __init__(self):
        self.configs = ACCOUNT_CONFIGS
    
    def list_accounts(self):
        """List all configured accounts."""
        print("📋 Configured AdSense Accounts:")
        print("=" * 40)
        
        for key, config in self.configs.items():
            print(f"\n🏢 {key.upper()} ({config['display_name']})")
            print(f"   Client Secrets: {config['client_secrets']}")
            print(f"   Credentials: {config['credentials_file']}")
            print(f"   Account ID: {config['account_id']}")
            
            # Check file status
            client_exists = os.path.exists(config['client_secrets'])
            creds_exists = os.path.exists(config['credentials_file'])
            
            print(f"   Status:")
            print(f"     Client Secrets: {'✅' if client_exists else '❌'}")
            print(f"     Credentials: {'✅' if creds_exists else '❌'}")
            
            if creds_exists:
                try:
                    with open(config['credentials_file'], 'r') as f:
                        creds = json.load(f)
                        if creds.get('token') == 'placeholder':
                            print(f"     OAuth: ⚠️  Needs setup")
                        else:
                            expiry = creds.get('expiry', 'Unknown')
                            print(f"     OAuth: ✅ Valid until {expiry}")
                except:
                    print(f"     OAuth: ❌ Invalid format")
    
    def setup_account(self, account_key):
        """Setup OAuth for specific account."""
        if account_key not in self.configs:
            print(f"❌ Account '{account_key}' not found")
            return False
        
        config = self.configs[account_key]
        print(f"🔧 Setting up OAuth for {config['display_name']}...")
        
        try:
            # This will trigger OAuth flow if needed
            service = get_adsense_service(account_key)
            account_id = get_account_id(service, account_key)
            
            print(f"✅ OAuth setup successful!")
            print(f"   Account ID: {account_id}")
            
            # Update config with real account ID
            real_id = account_id.split('/')[-1]
            self.configs[account_key]['account_id'] = real_id
            
            return True
            
        except Exception as e:
            print(f"❌ OAuth setup failed: {e}")
            return False
    
    def test_account(self, account_key):
        """Test API access for specific account."""
        if account_key not in self.configs:
            print(f"❌ Account '{account_key}' not found")
            return False
        
        config = self.configs[account_key]
        print(f"🧪 Testing {config['display_name']} API access...")
        
        try:
            service = get_adsense_service(account_key)
            account_id = get_account_id(service, account_key)
            
            # Test basic API call
            accounts_response = service.accounts().list().execute()
            
            print(f"✅ API access successful!")
            print(f"   Account ID: {account_id}")
            print(f"   Accounts found: {len(accounts_response.get('accounts', []))}")
            
            # Test sites
            try:
                sites_response = service.accounts().sites().list(parent=account_id).execute()
                sites = sites_response.get('sites', [])
                print(f"   Sites: {len(sites)}")
                for site in sites[:3]:  # Show first 3
                    print(f"     - {site.get('domain', 'N/A')} ({site.get('state', 'Unknown')})")
            except Exception as e:
                print(f"   Sites: Error - {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False
    
    def add_account(self, account_key, display_name, client_secrets_file):
        """Add new account configuration."""
        if account_key in self.configs:
            print(f"❌ Account '{account_key}' already exists")
            return False
        
        if not os.path.exists(client_secrets_file):
            print(f"❌ Client secrets file not found: {client_secrets_file}")
            return False
        
        credentials_file = f"adsense-{account_key}.dat"
        
        new_config = {
            "client_secrets": client_secrets_file,
            "credentials_file": credentials_file,
            "display_name": display_name,
            "account_id": "auto-detect"
        }
        
        print(f"➕ Adding new account '{account_key}':")
        print(f"   Display Name: {display_name}")
        print(f"   Client Secrets: {client_secrets_file}")
        print(f"   Credentials: {credentials_file}")
        
        # Create placeholder credentials
        placeholder_creds = {
            "token": "placeholder",
            "refresh_token": "placeholder",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "auto-detect",
            "client_secret": "auto-detect",
            "scopes": ["https://www.googleapis.com/auth/adsense.readonly"],
            "universe_domain": "googleapis.com",
            "account": "",
            "expiry": "2025-01-01T00:00:00Z"
        }
        
        with open(credentials_file, 'w') as f:
            json.dump(placeholder_creds, f, indent=2)
        
        # Note: In production, you'd want to save this to a config file
        print(f"✅ Account configuration created!")
        print(f"📝 Next steps:")
        print(f"   1. Add this config to ACCOUNT_CONFIGS in app_v2.py:")
        print(f"   \"{account_key}\": {json.dumps(new_config, indent=2)}")
        print(f"   2. Run: python account_manager.py setup {account_key}")
        
        return True

def main():
    manager = AdSenseAccountManager()
    
    if len(sys.argv) < 2:
        print("🔧 AdSense Account Manager")
        print("=" * 30)
        print("Usage:")
        print("  python account_manager.py list")
        print("  python account_manager.py setup <account_key>")
        print("  python account_manager.py test <account_key>")
        print("  python account_manager.py add <account_key> <display_name> <client_secrets_file>")
        print()
        print("Examples:")
        print("  python account_manager.py list")
        print("  python account_manager.py setup gowesgo")
        print("  python account_manager.py test perpustakaan")
        print("  python account_manager.py add newsite \"New Site\" client_secrets-newsite.json")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        manager.list_accounts()
    
    elif command == "setup":
        if len(sys.argv) < 3:
            print("❌ Usage: python account_manager.py setup <account_key>")
            return
        account_key = sys.argv[2]
        manager.setup_account(account_key)
    
    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ Usage: python account_manager.py test <account_key>")
            return
        account_key = sys.argv[2]
        manager.test_account(account_key)
    
    elif command == "add":
        if len(sys.argv) < 5:
            print("❌ Usage: python account_manager.py add <account_key> <display_name> <client_secrets_file>")
            return
        account_key = sys.argv[2]
        display_name = sys.argv[3]
        client_secrets_file = sys.argv[4]
        manager.add_account(account_key, display_name, client_secrets_file)
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()