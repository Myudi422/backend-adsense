"""
Cache Manager for AdSense API responses
Provides in-memory caching with TTL (Time To Live) to reduce API calls
"""

import time
import json
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import threading


class CacheManager:
    """
    Simple in-memory cache with TTL support
    Thread-safe implementation for concurrent access
    """
    
    def __init__(self, default_ttl: int = 60):
        """
        Initialize cache manager
        
        Args:
            default_ttl: Default time to live in seconds (default: 60 seconds)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "total_requests": 0
        }
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a unique cache key based on prefix and parameters
        
        Args:
            prefix: Cache key prefix (e.g., 'today_earnings', 'domain_earnings')
            **kwargs: Parameters to include in the key
            
        Returns:
            str: Unique cache key
        """
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        
        # Create hash for long parameter strings
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"{prefix}:{params_hash}:{params_str}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if expired/not found
        """
        with self._lock:
            self._stats["total_requests"] += 1
            
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            cache_entry = self._cache[key]
            
            # Check if expired
            if time.time() > cache_entry["expires_at"]:
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            
            self._stats["hits"] += 1
            return cache_entry["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        with self._lock:
            self._cache[key] = {
                "value": value,
                "created_at": time.time(),
                "expires_at": time.time() + ttl,
                "ttl": ttl
            }
            self._stats["sets"] += 1
    
    def delete(self, key: str) -> bool:
        """
        Delete specific key from cache
        
        Args:
            key: Cache key to delete
            
        Returns:
            bool: True if key existed and was deleted
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
                return True
            return False
    
    def clear(self) -> int:
        """
        Clear all cache entries
        
        Returns:
            int: Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache
        
        Returns:
            int: Number of expired entries removed
        """
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if current_time > entry["expires_at"]:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict with cache statistics
        """
        with self._lock:
            hit_rate = (self._stats["hits"] / self._stats["total_requests"] * 100) if self._stats["total_requests"] > 0 else 0
            
            return {
                "total_entries": len(self._cache),
                "total_requests": self._stats["total_requests"],
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate_percent": round(hit_rate, 2),
                "sets": self._stats["sets"],
                "deletes": self._stats["deletes"],
                "default_ttl_seconds": self.default_ttl
            }
    
    def get_cache_info(self) -> List[Dict[str, Any]]:
        """
        Get detailed info about all cache entries
        
        Returns:
            List of cache entry information
        """
        current_time = time.time()
        cache_info = []
        
        with self._lock:
            for key, entry in self._cache.items():
                remaining_ttl = max(0, entry["expires_at"] - current_time)
                cache_info.append({
                    "key": key,
                    "created_at": datetime.fromtimestamp(entry["created_at"]).isoformat(),
                    "expires_at": datetime.fromtimestamp(entry["expires_at"]).isoformat(),
                    "ttl_seconds": entry["ttl"],
                    "remaining_ttl_seconds": round(remaining_ttl, 1),
                    "is_expired": remaining_ttl <= 0,
                    "value_type": type(entry["value"]).__name__,
                    "value_size_bytes": len(str(entry["value"]))
                })
        
        return sorted(cache_info, key=lambda x: x["created_at"], reverse=True)


# Global cache manager instance
cache_manager = CacheManager(default_ttl=60)  # 1 minute default TTL


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    return cache_manager


def cache_key_for_earnings(account_key: str, date_filter: Optional[str] = None, custom_date: Optional[str] = None) -> str:
    """
    Generate cache key for earnings data
    
    Args:
        account_key: Account identifier
        date_filter: Date filter type
        custom_date: Custom date if applicable
        
    Returns:
        str: Cache key for earnings data
    """
    return cache_manager._generate_cache_key(
        "today_earnings",
        account_key=account_key,
        date_filter=date_filter,
        custom_date=custom_date
    )


def cache_key_for_domain_earnings(account_key: str, domain_filter: Optional[str] = None, 
                                date_filter: Optional[str] = None, custom_date: Optional[str] = None) -> str:
    """
    Generate cache key for domain earnings data
    
    Args:
        account_key: Account identifier
        domain_filter: Domain filter
        date_filter: Date filter type
        custom_date: Custom date if applicable
        
    Returns:
        str: Cache key for domain earnings data
    """
    return cache_manager._generate_cache_key(
        "domain_earnings",
        account_key=account_key,
        domain_filter=domain_filter,
        date_filter=date_filter,
        custom_date=custom_date
    )


def cache_key_for_summary() -> str:
    """Generate cache key for multi-account summary"""
    return cache_manager._generate_cache_key("multi_account_summary")


# Cache decorator for functions
def cached(ttl: int = 60, key_prefix: str = "default"):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = cache_manager._generate_cache_key(
                f"{key_prefix}:{func.__name__}",
                args=str(args),
                kwargs=kwargs
            )
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the cache manager
    print("Testing Cache Manager...")
    
    # Test basic operations
    cache = CacheManager(default_ttl=2)  # 2 seconds for testing
    
    # Set and get
    cache.set("test_key", {"data": "test_value"})
    result = cache.get("test_key")
    print(f"Cache get result: {result}")
    
    # Test cache key generation
    key1 = cache._generate_cache_key("earnings", account="test", date="2025-10-04")
    key2 = cache._generate_cache_key("earnings", date="2025-10-04", account="test")  # Same params, different order
    print(f"Key consistency: {key1 == key2}")
    
    # Test TTL expiration
    print("Waiting for TTL expiration...")
    time.sleep(3)
    expired_result = cache.get("test_key")
    print(f"After TTL expiration: {expired_result}")
    
    # Test statistics
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")
    
    print("Cache Manager test completed!")