#!/usr/bin/env python3
"""
Test Script: JSON Database System
Tests the new AdSense accounts JSON database system
"""

import asyncio
import json
import sys
import os
from datetime import datetime
import tempfile
import shutil

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from account_database import AccountDatabase
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseTester:
    """Test class for account database functionality."""
    
    def __init__(self):
        """Initialize test database."""
        # Use test database file
        self.test_db_path = "test_accounts.json"
        self.db = AccountDatabase(self.test_db_path)
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {"test": test_name, "success": success, "message": message}
        self.test_results.append(result)
        print(f"{status} {test_name}: {message}")
        if not success:
            logger.error(f"Test failed: {test_name} - {message}")
    
    def test_database_creation(self):
        """Test database creation and initialization."""
        print("\n🧪 Testing Database Creation")
        print("-" * 40)
        
        try:
            # Check if database file was created
            db_exists = os.path.exists(self.test_db_path)
            self.log_test(
                "Database File Creation",
                db_exists,
                f"Database file {'exists' if db_exists else 'missing'}: {self.test_db_path}"
            )
            
            # Check database structure
            metadata = self.db.get_metadata()
            self.log_test(
                "Metadata Structure",
                bool(metadata and 'version' in metadata),
                f"Metadata version: {metadata.get('version', 'missing')}"
            )
            
            # Check statistics
            stats = self.db.get_statistics()
            self.log_test(
                "Statistics Structure",
                bool(stats and 'total_accounts' in stats),
                f"Total accounts: {stats.get('total_accounts', 'missing')}"
            )
            
        except Exception as e:
            self.log_test("Database Creation", False, str(e))
    
    def test_account_management(self):
        """Test account CRUD operations."""
        print("\n🧪 Testing Account Management")
        print("-" * 40)
        
        test_account = {
            "account_key": "test_account",
            "account_id": "pub-1234567890123456",
            "display_name": "Test Account",
            "description": "Test account for database validation",
            "website_url": "https://test.example.com",
            "category": "test",
            "notes": "This is a test account"
        }
        
        try:
            # Test account creation
            account_data = self.db.add_account(**test_account)
            self.log_test(
                "Account Creation",
                bool(account_data and account_data.get('account_key') == test_account['account_key']),
                f"Created account: {test_account['account_key']}"
            )
            
            # Test account retrieval
            retrieved_account = self.db.get_account(test_account['account_key'])
            self.log_test(
                "Account Retrieval",
                bool(retrieved_account and retrieved_account.get('display_name') == test_account['display_name']),
                f"Retrieved account: {retrieved_account.get('display_name') if retrieved_account else 'None'}"
            )
            
            # Test account update
            updates = {
                "display_name": "Updated Test Account",
                "metadata": {"notes": "Updated notes"}
            }
            updated_account = self.db.update_account(test_account['account_key'], updates)
            self.log_test(
                "Account Update",
                updated_account.get('display_name') == "Updated Test Account",
                f"Updated display name: {updated_account.get('display_name')}"
            )
            
            # Test account existence check
            exists = self.db.account_exists(test_account['account_key'])
            self.log_test(
                "Account Existence Check",
                exists,
                f"Account exists: {exists}"
            )
            
            # Test account listing
            all_accounts = self.db.get_all_accounts()
            self.log_test(
                "Account Listing",
                test_account['account_key'] in all_accounts,
                f"Found {len(all_accounts)} accounts"
            )
            
        except Exception as e:
            self.log_test("Account Management", False, str(e))
    
    def test_search_functionality(self):
        """Test account search functionality."""
        print("\n🧪 Testing Search Functionality")
        print("-" * 40)
        
        try:
            # Add multiple test accounts for search testing
            test_accounts = [
                {
                    "account_key": "search_test_1",
                    "account_id": "pub-1111111111111111",
                    "display_name": "Education Site",
                    "description": "Educational content website",
                    "category": "education"
                },
                {
                    "account_key": "search_test_2", 
                    "account_id": "pub-2222222222222222",
                    "display_name": "Gaming Blog",
                    "description": "Gaming and entertainment blog",
                    "category": "entertainment"
                }
            ]
            
            # Add test accounts
            for account in test_accounts:
                self.db.add_account(**account)
            
            # Test search by display name
            search_results = self.db.search_accounts("Education")
            self.log_test(
                "Search by Display Name",
                len(search_results) > 0 and any(acc.get('display_name') == 'Education Site' for acc in search_results),
                f"Found {len(search_results)} results for 'Education'"
            )
            
            # Test search by category
            search_results = self.db.search_accounts("gaming")
            self.log_test(
                "Search by Category",
                len(search_results) > 0,
                f"Found {len(search_results)} results for 'gaming'"
            )
            
            # Test search by account key
            search_results = self.db.search_accounts("search_test")
            self.log_test(
                "Search by Account Key",
                len(search_results) >= 2,
                f"Found {len(search_results)} results for 'search_test'"
            )
            
        except Exception as e:
            self.log_test("Search Functionality", False, str(e))
    
    def test_backup_restore(self):
        """Test backup and restore functionality."""
        print("\n🧪 Testing Backup & Restore")
        print("-" * 40)
        
        try:
            # Create backup
            backup_path = self.db.create_backup("test_backup.json")
            backup_exists = os.path.exists(backup_path)
            self.log_test(
                "Backup Creation",
                backup_exists,
                f"Backup created: {backup_path if backup_exists else 'Failed'}"
            )
            
            if backup_exists:
                # Verify backup content
                with open(backup_path, 'r') as f:
                    backup_data = json.load(f)
                
                has_accounts = 'accounts' in backup_data
                self.log_test(
                    "Backup Content Validation",
                    has_accounts,
                    f"Backup contains accounts section: {has_accounts}"
                )
                
                # Test restore functionality
                original_accounts = self.db.get_all_accounts()
                
                # Create a modified database state
                self.db.add_account(
                    account_key="temp_account",
                    account_id="pub-9999999999999999",
                    display_name="Temporary Account",
                    description="Temporary account for restore testing"
                )
                
                # Restore from backup
                self.db.restore_from_backup(backup_path)
                
                # Check if restore worked
                restored_accounts = self.db.get_all_accounts()
                temp_account_exists = self.db.account_exists("temp_account")
                
                self.log_test(
                    "Database Restore",
                    not temp_account_exists,
                    f"Temporary account removed after restore: {not temp_account_exists}"
                )
                
                # Clean up backup file
                os.remove(backup_path)
            
        except Exception as e:
            self.log_test("Backup & Restore", False, str(e))
    
    def test_validation(self):
        """Test database validation."""
        print("\n🧪 Testing Database Validation")
        print("-" * 40)
        
        try:
            # Run validation
            validation_errors = self.db.validate_database()
            
            self.log_test(
                "Database Validation",
                len(validation_errors) == 0,
                f"Validation errors: {len(validation_errors)}"
            )
            
            if validation_errors:
                for error in validation_errors[:3]:  # Show first 3 errors
                    print(f"   • {error}")
                if len(validation_errors) > 3:
                    print(f"   • ... and {len(validation_errors) - 3} more errors")
            
        except Exception as e:
            self.log_test("Database Validation", False, str(e))
    
    def test_statistics(self):
        """Test statistics functionality."""
        print("\n🧪 Testing Statistics")
        print("-" * 40)
        
        try:
            # Get statistics
            stats = self.db.get_statistics()
            
            self.log_test(
                "Statistics Retrieval",
                bool(stats and isinstance(stats.get('total_accounts'), int)),
                f"Total accounts: {stats.get('total_accounts', 'N/A')}"
            )
            
            # Check active accounts
            active_accounts = self.db.get_active_accounts()
            self.log_test(
                "Active Accounts Filter",
                isinstance(active_accounts, dict),
                f"Active accounts: {len(active_accounts)}"
            )
            
            # Get account list
            account_list = self.db.get_account_list()
            self.log_test(
                "Account List",
                isinstance(account_list, list),
                f"Account list entries: {len(account_list)}"
            )
            
        except Exception as e:
            self.log_test("Statistics", False, str(e))
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        print("\n🧪 Testing Edge Cases")
        print("-" * 40)
        
        try:
            # Test duplicate account creation
            try:
                self.db.add_account(
                    account_key="test_account",  # Already exists
                    account_id="pub-1234567890123456",
                    display_name="Duplicate Test",
                    description="Should fail"
                )
                self.log_test("Duplicate Account Prevention", False, "Duplicate account was allowed")
            except ValueError:
                self.log_test("Duplicate Account Prevention", True, "Duplicate account correctly rejected")
            
            # Test invalid account key
            try:
                self.db.add_account(
                    account_key="invalid!@#$%",
                    account_id="pub-1234567890123456",
                    display_name="Invalid Key Test",
                    description="Should fail"
                )
                self.log_test("Invalid Account Key Prevention", False, "Invalid account key was allowed")
            except ValueError:
                self.log_test("Invalid Account Key Prevention", True, "Invalid account key correctly rejected")
            
            # Test non-existent account operations
            non_existent = self.db.get_account("non_existent_account")
            self.log_test(
                "Non-existent Account Handling",
                non_existent is None,
                f"Non-existent account returned: {type(non_existent).__name__}"
            )
            
            # Test account removal
            removal_success = self.db.remove_account("test_account", delete_files=False)
            self.log_test(
                "Account Removal",
                removal_success,
                f"Account removal success: {removal_success}"
            )
            
            # Verify account was removed
            removed_account = self.db.get_account("test_account")
            self.log_test(
                "Account Removal Verification",
                removed_account is None,
                f"Account still exists after removal: {removed_account is not None}"
            )
            
        except Exception as e:
            self.log_test("Edge Cases", False, str(e))
    
    def cleanup(self):
        """Clean up test database and files."""
        print("\n🧹 Cleaning up test files...")
        
        try:
            # Remove test database
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
                print(f"   ✅ Removed test database: {self.test_db_path}")
            
            # Remove backup files
            backup_files = [f for f in os.listdir('.') if f.startswith('test_backup') and f.endswith('.json')]
            for backup_file in backup_files:
                os.remove(backup_file)
                print(f"   ✅ Removed backup file: {backup_file}")
                
        except Exception as e:
            print(f"   ⚠️  Cleanup warning: {e}")
    
    def run_all_tests(self):
        """Run all database tests."""
        print("🚀 AdSense JSON Database System Test Suite")
        print("=" * 60)
        
        # Run test suites
        self.test_database_creation()
        self.test_account_management()
        self.test_search_functionality()
        self.test_backup_restore()
        self.test_validation()
        self.test_statistics()
        self.test_edge_cases()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("-" * 30)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   • {result['test']}: {result['message']}")
        
        print(f"\n{'🎉 All tests passed!' if failed_tests == 0 else '⚠️  Some tests failed. Check logs above.'}")
        
        # Cleanup
        self.cleanup()
        
        return failed_tests == 0

def main():
    """Run database tests."""
    try:
        tester = DatabaseTester()
        success = tester.run_all_tests()
        
        if success:
            print("\n✅ Database system is ready for production!")
            sys.exit(0)
        else:
            print("\n❌ Database system has issues. Please fix before using.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        logger.error(f"Test suite error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()