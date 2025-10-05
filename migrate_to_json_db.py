#!/usr/bin/env python3
"""
Migration Script: Hardcoded Config to JSON Database
Migrates existing AdSense accounts from hardcoded configuration to JSON database format
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from account_database import AccountDatabase
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_existing_accounts():
    """
    Migrate existing hardcoded account configurations to JSON database.
    """
    print("🔄 AdSense Account Migration Tool")
    print("=" * 50)
    
    # Initialize database
    db = AccountDatabase()
    
    # Define existing accounts (from previous hardcoded config)
    existing_accounts = {
        "perpustakaan": {
            "client_secrets": "client_secrets.json",
            "credentials_file": "adsense.dat",
            "display_name": "perpustakaan.id",
            "account_id": "pub-1777593071761494",
            "description": "Perpustakaan.id AdSense account - Main educational website",
            "metadata": {
                "website_url": "https://perpustakaan.id",
                "category": "education",
                "notes": "Primary account with library content"
            }
        },
        "gowesgo": {
            "client_secrets": "client_secrets-gowesgo.json",
            "credentials_file": "adsense-gowesgo.dat",
            "display_name": "gowesgo.com",
            "account_id": "pub-1315457334560058",
            "description": "GowesGo.com AdSense account - Cycling community website",
            "metadata": {
                "website_url": "https://gowesgo.com",
                "category": "lifestyle",
                "notes": "Cycling and outdoor activities content"
            }
        }
    }
    
    migration_summary = {
        "migrated": [],
        "skipped": [],
        "errors": [],
        "files_found": [],
        "files_missing": []
    }
    
    print(f"📋 Found {len(existing_accounts)} accounts to migrate:")
    for account_key in existing_accounts.keys():
        print(f"   • {account_key}")
    print()
    
    # Check if accounts already exist in database
    existing_db_accounts = db.get_all_accounts()
    if existing_db_accounts:
        print(f"⚠️  Database already contains {len(existing_db_accounts)} accounts:")
        for account_key in existing_db_accounts.keys():
            print(f"   • {account_key}")
        
        response = input("\nDo you want to overwrite existing accounts? (y/N): ").lower()
        if response != 'y':
            print("❌ Migration cancelled by user.")
            return migration_summary
        print()
    
    # Migrate each account
    for account_key, config in existing_accounts.items():
        print(f"🔄 Migrating account: {account_key}")
        
        try:
            # Check if files exist
            client_secrets_file = config["client_secrets"]
            credentials_file = config["credentials_file"]
            
            if os.path.exists(client_secrets_file):
                migration_summary["files_found"].append(client_secrets_file)
                print(f"   ✅ Found client secrets: {client_secrets_file}")
            else:
                migration_summary["files_missing"].append(client_secrets_file)
                print(f"   ⚠️  Missing client secrets: {client_secrets_file}")
            
            if os.path.exists(credentials_file):
                migration_summary["files_found"].append(credentials_file)
                print(f"   ✅ Found credentials: {credentials_file}")
            else:
                migration_summary["files_missing"].append(credentials_file)
                print(f"   ⚠️  Missing credentials: {credentials_file}")
            
            # Check if account already exists
            if db.account_exists(account_key):
                print(f"   🔄 Updating existing account: {account_key}")
                
                # Update existing account
                updates = {
                    "account_id": config["account_id"],
                    "display_name": config["display_name"],
                    "description": config["description"],
                    "client_secrets": config["client_secrets"],
                    "credentials_file": config["credentials_file"],
                    "status": "active" if os.path.exists(credentials_file) else "inactive",
                    "metadata": config["metadata"]
                }
                
                db.update_account(account_key, updates)
                migration_summary["migrated"].append(f"{account_key} (updated)")
                
            else:
                print(f"   ➕ Adding new account: {account_key}")
                
                # Add new account
                db.add_account(
                    account_key=account_key,
                    account_id=config["account_id"],
                    display_name=config["display_name"],
                    description=config["description"],
                    client_secrets=config["client_secrets"],
                    credentials_file=config["credentials_file"],
                    website_url=config["metadata"]["website_url"],
                    category=config["metadata"]["category"],
                    notes=config["metadata"]["notes"]
                )
                
                # Update status based on credentials file
                if os.path.exists(credentials_file):
                    db.update_account(account_key, {"status": "active"})
                
                migration_summary["migrated"].append(f"{account_key} (new)")
            
            print(f"   ✅ Successfully migrated: {account_key}")
            
        except Exception as e:
            error_msg = f"Error migrating {account_key}: {str(e)}"
            migration_summary["errors"].append(error_msg)
            print(f"   ❌ {error_msg}")
            logger.error(error_msg)
    
    print("\n" + "=" * 50)
    print("📊 Migration Summary:")
    print(f"   ✅ Migrated: {len(migration_summary['migrated'])} accounts")
    for account in migration_summary['migrated']:
        print(f"      • {account}")
    
    if migration_summary['errors']:
        print(f"   ❌ Errors: {len(migration_summary['errors'])}")
        for error in migration_summary['errors']:
            print(f"      • {error}")
    
    print(f"   📁 Files found: {len(migration_summary['files_found'])}")
    print(f"   📁 Files missing: {len(migration_summary['files_missing'])}")
    
    if migration_summary['files_missing']:
        print("\n⚠️  Missing files:")
        for file in migration_summary['files_missing']:
            print(f"      • {file}")
        print("\n💡 Note: Accounts with missing files will be marked as 'inactive'")
        print("   Use the OAuth connection endpoints to re-authenticate these accounts.")
    
    # Validate final database
    print(f"\n🔍 Validating database...")
    validation_errors = db.validate_database()
    if validation_errors:
        print(f"   ⚠️  Validation warnings: {len(validation_errors)}")
        for error in validation_errors:
            print(f"      • {error}")
    else:
        print("   ✅ Database validation successful")
    
    # Show final account count
    final_accounts = db.get_all_accounts()
    print(f"\n📈 Final database status:")
    print(f"   • Total accounts: {len(final_accounts)}")
    print(f"   • Active accounts: {len(db.get_active_accounts())}")
    
    print(f"\n🎉 Migration completed! Database saved to: {db.db_path}")
    
    return migration_summary

def create_backup_of_old_system():
    """Create backup of old hardcoded system files."""
    print("💾 Creating backup of current system...")
    
    backup_dir = Path(f"backup_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(exist_ok=True)
    
    files_to_backup = [
        "app_v2.py.bak",  # If exists
        "client_secrets.json",
        "client_secrets-gowesgo.json", 
        "adsense.dat",
        "adsense-gowesgo.dat"
    ]
    
    backed_up = []
    for file_name in files_to_backup:
        if os.path.exists(file_name):
            import shutil
            backup_path = backup_dir / file_name
            shutil.copy2(file_name, backup_path)
            backed_up.append(file_name)
            print(f"   ✅ Backed up: {file_name}")
    
    if backed_up:
        print(f"   📁 Backup created in: {backup_dir}")
        return str(backup_dir)
    else:
        print("   ℹ️  No files to backup")
        backup_dir.rmdir()  # Remove empty directory
        return None

def main():
    """Main migration function."""
    print("AdSense Account Migration Tool")
    print("Migrating from hardcoded configuration to JSON database")
    print("=" * 60)
    
    try:
        # Create backup first
        backup_dir = create_backup_of_old_system()
        if backup_dir:
            print(f"✅ Backup created: {backup_dir}\n")
        
        # Run migration
        summary = migrate_existing_accounts()
        
        print("\n" + "=" * 60)
        print("🚀 Next Steps:")
        print("1. Test the new API endpoints:")
        print("   • GET /api/accounts - View all accounts")
        print("   • GET /api/database/stats - Database statistics")
        print("   • GET /api/today-earnings/perpustakaan - Test earnings")
        print("\n2. Add new accounts using:")
        print("   • POST /api/accounts/upload - Upload client secrets")
        print("   • POST /api/accounts/{key}/connect - Connect OAuth")
        print("\n3. Manage database:")
        print("   • POST /api/database/backup - Create backups")
        print("   • GET /api/database/search?query=... - Search accounts")
        print("\n4. Documentation:")
        print("   • Visit http://localhost:8000/docs for full API docs")
        
        if summary['errors']:
            print(f"\n⚠️  Please resolve {len(summary['errors'])} errors before production use.")
            sys.exit(1)
        else:
            print("\n✅ Migration completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()