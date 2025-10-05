#!/usr/bin/env python3
"""
AdSense Account Database Manager
Manages AdSense accounts configuration in JSON format
"""

import json
import os
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class AccountDatabase:
    """
    Manages AdSense accounts in JSON database format.
    Provides CRUD operations, validation, and backup functionality.
    """
    
    def __init__(self, db_path: str = "accounts.json"):
        """
        Initialize the account database.
        
        Args:
            db_path: Path to the JSON database file
        """
        self.db_path = Path(db_path)
        self._data = {}
        self._load_database()
    
    def _load_database(self):
        """Load database from JSON file."""
        try:
            if self.db_path.exists():
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                logger.info(f"Loaded {len(self.get_all_accounts())} accounts from database")
            else:
                # Create default database structure
                self._data = self._create_empty_database()
                self._save_database()
                logger.info("Created new accounts database")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            self._data = self._create_empty_database()
    
    def _create_empty_database(self) -> Dict[str, Any]:
        """Create empty database structure."""
        return {
            "_metadata": {
                "version": "1.0.0",
                "created": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
                "description": "AdSense Accounts Database",
                "schema_version": "1.0"
            },
            "_schema": {
                "account_structure": {
                    "account_key": "string (unique identifier)",
                    "account_id": "string (Google AdSense publisher ID)",
                    "display_name": "string (human readable name)",
                    "description": "string (optional description)",
                    "client_secrets": "string (path to client secrets file)",
                    "credentials_file": "string (path to OAuth credentials file)",
                    "status": "string (active/inactive/error)",
                    "created_at": "string (ISO timestamp)",
                    "updated_at": "string (ISO timestamp)",
                    "metadata": {
                        "website_url": "string (optional)",
                        "category": "string (optional)",
                        "notes": "string (optional)"
                    }
                }
            },
            "accounts": {},
            "_statistics": {
                "total_accounts": 0,
                "active_accounts": 0,
                "inactive_accounts": 0,
                "last_backup": None
            }
        }
    
    def _save_database(self):
        """Save database to JSON file."""
        try:
            # Update metadata
            self._data["_metadata"]["last_modified"] = datetime.now().isoformat()
            
            # Update statistics
            accounts = self._data.get("accounts", {})
            self._data["_statistics"] = {
                "total_accounts": len(accounts),
                "active_accounts": len([a for a in accounts.values() if a.get("status") == "active"]),
                "inactive_accounts": len([a for a in accounts.values() if a.get("status") != "active"]),
                "last_backup": self._data["_statistics"].get("last_backup")
            }
            
            # Create backup before saving
            if self.db_path.exists():
                backup_path = f"{self.db_path}.bak"
                shutil.copy2(self.db_path, backup_path)
            
            # Save with pretty formatting
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            
            logger.info("Database saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            raise
    
    def get_all_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Get all accounts from database."""
        return self._data.get("accounts", {})
    
    def get_account(self, account_key: str) -> Optional[Dict[str, Any]]:
        """
        Get specific account by key.
        
        Args:
            account_key: Account identifier
            
        Returns:
            Account data or None if not found
        """
        return self._data.get("accounts", {}).get(account_key)
    
    def account_exists(self, account_key: str) -> bool:
        """Check if account exists."""
        return account_key in self._data.get("accounts", {})
    
    def add_account(self, 
                   account_key: str,
                   account_id: str,
                   display_name: str,
                   description: str = None,
                   client_secrets: str = None,
                   credentials_file: str = None,
                   website_url: str = None,
                   category: str = None,
                   notes: str = None) -> Dict[str, Any]:
        """
        Add new account to database.
        
        Args:
            account_key: Unique account identifier
            account_id: Google AdSense publisher ID
            display_name: Human readable name
            description: Optional description
            client_secrets: Path to client secrets file
            credentials_file: Path to OAuth credentials file
            website_url: Optional website URL
            category: Optional category
            notes: Optional notes
            
        Returns:
            Created account data
            
        Raises:
            ValueError: If account already exists or invalid data
        """
        if self.account_exists(account_key):
            raise ValueError(f"Account '{account_key}' already exists")
        
        if not account_key.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Account key must contain only letters, numbers, underscores, and hyphens")
        
        # Generate file paths if not provided
        if not client_secrets:
            client_secrets = f"client_secrets-{account_key}.json"
        if not credentials_file:
            credentials_file = f"adsense-{account_key}.dat"
        
        # Create account data
        account_data = {
            "account_key": account_key,
            "account_id": account_id,
            "display_name": display_name,
            "description": description or f"AdSense account for {display_name}",
            "client_secrets": client_secrets,
            "credentials_file": credentials_file,
            "status": "inactive",  # Start as inactive until OAuth completed
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {
                "website_url": website_url,
                "category": category,
                "notes": notes
            }
        }
        
        # Add to database
        if "accounts" not in self._data:
            self._data["accounts"] = {}
        
        self._data["accounts"][account_key] = account_data
        self._save_database()
        
        logger.info(f"Added new account: {account_key}")
        return account_data
    
    def update_account(self, account_key: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing account.
        
        Args:
            account_key: Account identifier
            updates: Dictionary of fields to update
            
        Returns:
            Updated account data
            
        Raises:
            ValueError: If account not found
        """
        if not self.account_exists(account_key):
            raise ValueError(f"Account '{account_key}' not found")
        
        account = self._data["accounts"][account_key]
        
        # Update allowed fields
        allowed_fields = [
            "account_id", "display_name", "description", "status",
            "client_secrets", "credentials_file"
        ]
        
        for field, value in updates.items():
            if field in allowed_fields:
                account[field] = value
            elif field == "metadata":
                if "metadata" not in account:
                    account["metadata"] = {}
                account["metadata"].update(value)
        
        account["updated_at"] = datetime.now().isoformat()
        self._save_database()
        
        logger.info(f"Updated account: {account_key}")
        return account
    
    def remove_account(self, account_key: str, delete_files: bool = True) -> bool:
        """
        Remove account from database.
        
        Args:
            account_key: Account identifier
            delete_files: Whether to delete associated files
            
        Returns:
            True if removed, False if not found
        """
        if not self.account_exists(account_key):
            return False
        
        account = self._data["accounts"][account_key]
        
        # Delete associated files if requested
        if delete_files:
            for file_path in [account.get("client_secrets"), account.get("credentials_file")]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete file {file_path}: {e}")
        
        # Remove from database
        del self._data["accounts"][account_key]
        self._save_database()
        
        logger.info(f"Removed account: {account_key}")
        return True
    
    def get_account_list(self) -> List[Dict[str, Any]]:
        """Get list of all accounts with basic info."""
        accounts = []
        for account_key, account_data in self.get_all_accounts().items():
            accounts.append({
                "account_key": account_key,
                "account_id": account_data.get("account_id"),
                "display_name": account_data.get("display_name"),
                "status": account_data.get("status"),
                "created_at": account_data.get("created_at"),
                "website_url": account_data.get("metadata", {}).get("website_url")
            })
        return accounts
    
    def get_active_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Get only active accounts."""
        return {
            key: account for key, account in self.get_all_accounts().items()
            if account.get("status") == "active"
        }
    
    def search_accounts(self, query: str) -> List[Dict[str, Any]]:
        """
        Search accounts by display name, description, or metadata.
        
        Args:
            query: Search query
            
        Returns:
            List of matching accounts
        """
        query_lower = query.lower()
        results = []
        
        for account_key, account_data in self.get_all_accounts().items():
            # Search in various fields
            search_fields = [
                account_data.get("display_name", ""),
                account_data.get("description", ""),
                account_data.get("metadata", {}).get("website_url", ""),
                account_data.get("metadata", {}).get("notes", ""),
                account_key
            ]
            
            if any(query_lower in str(field).lower() for field in search_fields):
                results.append(account_data)
        
        return results
    
    def create_backup(self, backup_path: Optional[str] = None) -> str:
        """
        Create backup of database.
        
        Args:
            backup_path: Optional custom backup path
            
        Returns:
            Path to backup file
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"accounts_backup_{timestamp}.json"
        
        shutil.copy2(self.db_path, backup_path)
        
        # Update statistics
        self._data["_statistics"]["last_backup"] = datetime.now().isoformat()
        self._save_database()
        
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def restore_from_backup(self, backup_path: str):
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            
        Raises:
            FileNotFoundError: If backup file not found
            ValueError: If backup file is invalid
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        try:
            # Validate backup file
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Basic validation
            if "accounts" not in backup_data:
                raise ValueError("Invalid backup file: missing accounts section")
            
            # Create current backup before restore
            current_backup = self.create_backup(f"{self.db_path}.before_restore")
            
            # Restore data
            self._data = backup_data
            self._save_database()
            
            logger.info(f"Restored database from backup: {backup_path}")
            logger.info(f"Previous version backed up to: {current_backup}")
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self._data.get("_statistics", {})
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get database metadata."""
        return self._data.get("_metadata", {})
    
    def validate_database(self) -> List[str]:
        """
        Validate database integrity.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Check structure
            required_sections = ["_metadata", "accounts", "_statistics"]
            for section in required_sections:
                if section not in self._data:
                    errors.append(f"Missing section: {section}")
            
            # Check accounts
            accounts = self._data.get("accounts", {})
            for account_key, account_data in accounts.items():
                if not isinstance(account_data, dict):
                    errors.append(f"Account {account_key}: invalid data type")
                    continue
                
                # Check required fields
                required_fields = ["account_key", "display_name", "status"]
                for field in required_fields:
                    if field not in account_data:
                        errors.append(f"Account {account_key}: missing field {field}")
                
                # Check file existence
                client_secrets = account_data.get("client_secrets")
                if client_secrets and not os.path.exists(client_secrets):
                    errors.append(f"Account {account_key}: client secrets file not found: {client_secrets}")
            
        except Exception as e:
            errors.append(f"Database validation error: {e}")
        
        return errors

# Global database instance
db = AccountDatabase()

def get_account_database() -> AccountDatabase:
    """Get the global account database instance."""
    return db