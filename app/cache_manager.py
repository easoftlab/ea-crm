#!/usr/bin/env python3
"""
Cache Manager for Dashboard Performance
Implements caching system for dashboard data to improve performance
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, Callable

class CacheManager:
    """Cache manager for dashboard performance optimization."""
    
    def __init__(self):
        """Initialize cache manager."""
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = {}
        self._default_ttl = 300  # 5 minutes default TTL
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key."""
        # Create a string representation of arguments
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        # Create hash of the key parts
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None
        
        # Check if cache has expired
        if key in self._cache_timestamps and key in self._cache_ttl:
            timestamp = self._cache_timestamps[key]
            ttl = self._cache_ttl[key]
            
            if time.time() - timestamp > ttl:
                # Cache expired, remove it
                self.delete(key)
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        try:
            self._cache[key] = value
            self._cache_timestamps[key] = time.time()
            self._cache_ttl[key] = ttl if ttl is not None else self._default_ttl
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if key in self._cache:
                del self._cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
            if key in self._cache_ttl:
                del self._cache_ttl[key]
            return True
        except Exception:
            return False
    
    def clear(self) -> bool:
        """Clear all cache."""
        try:
            self._cache.clear()
            self._cache_timestamps.clear()
            self._cache_ttl.clear()
            return True
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache and self.get(key) is not None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_keys = len(self._cache)
        expired_keys = 0
        
        for key in list(self._cache.keys()):
            if self.get(key) is None:
                expired_keys += 1
        
        return {
            'total_keys': total_keys,
            'expired_keys': expired_keys,
            'active_keys': total_keys - expired_keys,
            'cache_size': len(self._cache),
            'timestamp': datetime.now().isoformat()
        }
    
    def cache_function(self, prefix: str, ttl: int = None):
        """Decorator to cache function results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator

# Global cache instance
cache_manager = CacheManager()

class DashboardCache:
    """Dashboard-specific caching utilities."""
    
    @staticmethod
    def cache_team_data(team_id: int, ttl: int = 600):
        """Cache team data with 10-minute TTL."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"team_data_{team_id}"
                cached_result = cache_manager.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def cache_user_reports(user_id: int, report_type: str, ttl: int = 300):
        """Cache user reports with 5-minute TTL."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"user_reports_{user_id}_{report_type}"
                cached_result = cache_manager.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def cache_dashboard_metrics(team_id: int, metric_type: str, ttl: int = 180):
        """Cache dashboard metrics with 3-minute TTL."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"dashboard_metrics_{team_id}_{metric_type}"
                cached_result = cache_manager.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def invalidate_team_cache(team_id: int):
        """Invalidate all cache entries for a team."""
        keys_to_delete = []
        
        for key in cache_manager._cache.keys():
            if f"team_data_{team_id}" in key or f"dashboard_metrics_{team_id}" in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            cache_manager.delete(key)
    
    @staticmethod
    def invalidate_user_cache(user_id: int):
        """Invalidate all cache entries for a user."""
        keys_to_delete = []
        
        for key in cache_manager._cache.keys():
            if f"user_reports_{user_id}" in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            cache_manager.delete(key)

class ReportCache:
    """Report-specific caching utilities."""
    
    @staticmethod
    def cache_daily_reports(team_id: int, date: str, ttl: int = 600):
        """Cache daily reports with 10-minute TTL."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"daily_reports_{team_id}_{date}"
                cached_result = cache_manager.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def cache_weekly_reports(team_id: int, week_start: str, ttl: int = 1800):
        """Cache weekly reports with 30-minute TTL."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"weekly_reports_{team_id}_{week_start}"
                cached_result = cache_manager.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def cache_monthly_reports(team_id: int, month_year: str, ttl: int = 3600):
        """Cache monthly reports with 1-hour TTL."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"monthly_reports_{team_id}_{month_year}"
                cached_result = cache_manager.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def invalidate_report_cache(team_id: int, report_type: str = None):
        """Invalidate report cache for a team."""
        keys_to_delete = []
        
        for key in cache_manager._cache.keys():
            if report_type:
                if f"{report_type}_reports_{team_id}" in key:
                    keys_to_delete.append(key)
            else:
                if f"_reports_{team_id}" in key:
                    keys_to_delete.append(key)
        
        for key in keys_to_delete:
            cache_manager.delete(key)

class SecurityCache:
    """Security-related caching utilities."""
    
    @staticmethod
    def cache_user_permissions(user_id: int, ttl: int = 1800):
        """Cache user permissions with 30-minute TTL."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"user_permissions_{user_id}"
                cached_result = cache_manager.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def cache_team_access(user_id: int, team_id: int, ttl: int = 900):
        """Cache team access permissions with 15-minute TTL."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"team_access_{user_id}_{team_id}"
                cached_result = cache_manager.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def invalidate_security_cache(user_id: int):
        """Invalidate security cache for a user."""
        keys_to_delete = []
        
        for key in cache_manager._cache.keys():
            if f"user_permissions_{user_id}" in key or f"team_access_{user_id}" in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            cache_manager.delete(key)

def get_cache_stats():
    """Get cache statistics for monitoring."""
    return cache_manager.get_cache_stats()

def clear_all_cache():
    """Clear all cache (useful for testing)."""
    return cache_manager.clear()

def cache_performance_test():
    """Test cache performance."""
    print("🧪 Testing Cache Performance...")
    
    # Test basic operations
    cache_manager.set("test_key", "test_value", 60)
    assert cache_manager.get("test_key") == "test_value"
    assert cache_manager.exists("test_key")
    
    # Test cache expiration
    cache_manager.set("expire_key", "expire_value", 1)
    time.sleep(2)
    assert cache_manager.get("expire_key") is None
    
    # Test cache decorator
    @cache_manager.cache_function("test_func", 60)
    def test_function(x, y):
        return x + y
    
    # First call should cache
    result1 = test_function(5, 3)
    # Second call should use cache
    result2 = test_function(5, 3)
    assert result1 == result2 == 8
    
    print("✅ Cache performance test passed!")
    return True

if __name__ == "__main__":
    cache_performance_test() 