"""
Django cache utilities and configuration.

Provides:
- Cache key generators and utilities
- Cache decorators for views and functions
- Cache invalidation patterns
- Performance monitoring for cache operations
"""

import hashlib
import time
from functools import wraps
from typing import Any, Callable, Optional, Union, Dict, List
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
import logging
import json

logger = logging.getLogger(__name__)


class CacheKeyGenerator:
    """Utility class for generating consistent cache keys."""
    
    @staticmethod
    def user_key(user_id: int, suffix: str = "") -> str:
        """Generate user-specific cache key."""
        key = f"user:{user_id}"
        if suffix:
            key += f":{suffix}"
        return key
    
    @staticmethod
    def notebook_key(notebook_id: str, suffix: str = "") -> str:
        """Generate notebook-specific cache key."""
        key = f"notebook:{notebook_id}"
        if suffix:
            key += f":{suffix}"
        return key
    
    @staticmethod
    def file_key(file_id: str, suffix: str = "") -> str:
        """Generate file-specific cache key."""
        key = f"file:{file_id}"
        if suffix:
            key += f":{suffix}"
        return key
    
    @staticmethod
    def query_key(model_name: str, query_params: Dict) -> str:
        """Generate cache key for database queries."""
        # Create hash of query parameters for consistency
        params_str = json.dumps(query_params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:12]
        return f"query:{model_name}:{params_hash}"
    
    @staticmethod
    def api_key(request: HttpRequest, view_name: str) -> str:
        """Generate cache key for API responses."""
        user_id = request.user.id if request.user.is_authenticated else 'anon'
        query_hash = hashlib.md5(request.GET.urlencode().encode()).hexdigest()[:8]
        return f"api:{view_name}:user:{user_id}:query:{query_hash}"


class CacheManager:
    """Manager for cache operations with monitoring and invalidation."""
    
    def __init__(self):
        self.default_timeout = getattr(settings, 'CACHE_DEFAULT_TIMEOUT', 300)  # 5 minutes
        self.long_timeout = getattr(settings, 'CACHE_LONG_TIMEOUT', 3600)  # 1 hour
        self.short_timeout = getattr(settings, 'CACHE_SHORT_TIMEOUT', 60)   # 1 minute
    
    def get(self, key: str, default=None, timeout: Optional[int] = None) -> Any:
        """Get value from cache with monitoring."""
        start_time = time.time()
        
        try:
            value = cache.get(key, default)
            hit = value is not default
            
            response_time = (time.time() - start_time) * 1000
            
            # Log cache performance
            if response_time > 50:  # Log slow cache operations
                logger.warning(f"Slow cache GET: {key} took {response_time:.2f}ms")
            
            # Log cache metrics
            self._log_cache_operation('get', key, hit, response_time)
            
            return value
            
        except Exception as e:
            logger.exception(f"Cache GET failed for key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set value in cache with monitoring."""
        if timeout is None:
            timeout = self.default_timeout
        
        start_time = time.time()
        
        try:
            result = cache.set(key, value, timeout)
            response_time = (time.time() - start_time) * 1000
            
            # Log slow cache operations
            if response_time > 100:
                logger.warning(f"Slow cache SET: {key} took {response_time:.2f}ms")
            
            # Log cache metrics
            self._log_cache_operation('set', key, result, response_time)
            
            return result
            
        except Exception as e:
            logger.exception(f"Cache SET failed for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            result = cache.delete(key)
            logger.debug(f"Cache DELETE: {key} (success: {result})")
            return result
        except Exception as e:
            logger.exception(f"Cache DELETE failed for key {key}: {e}")
            return False
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        start_time = time.time()
        
        try:
            values = cache.get_many(keys)
            response_time = (time.time() - start_time) * 1000
            
            hit_count = len(values)
            hit_rate = hit_count / len(keys) * 100 if keys else 0
            
            logger.debug(
                f"Cache GET_MANY: {len(keys)} keys, {hit_count} hits "
                f"({hit_rate:.1f}% hit rate) in {response_time:.2f}ms"
            )
            
            return values
            
        except Exception as e:
            logger.exception(f"Cache GET_MANY failed: {e}")
            return {}
    
    def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """Set multiple values in cache."""
        if timeout is None:
            timeout = self.default_timeout
        
        start_time = time.time()
        
        try:
            result = cache.set_many(data, timeout)
            response_time = (time.time() - start_time) * 1000
            
            logger.debug(
                f"Cache SET_MANY: {len(data)} keys set in {response_time:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Cache SET_MANY failed: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching a pattern."""
        try:
            # This is a simplified version - Redis-specific implementations
            # would use SCAN with pattern matching
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(pattern)
                logger.info(f"Invalidated cache pattern: {pattern}")
            else:
                logger.warning(f"Pattern invalidation not supported for cache backend")
                
        except Exception as e:
            logger.exception(f"Cache pattern invalidation failed for {pattern}: {e}")
    
    def _log_cache_operation(self, operation: str, key: str, success: bool, response_time: float):
        """Log cache operation metrics."""
        # This could be enhanced to send metrics to monitoring systems
        if response_time > 100 or not success:
            logger.info(
                f"Cache {operation.upper()}: key={key}, success={success}, "
                f"time={response_time:.2f}ms"
            )


# Global cache manager instance
cache_manager = CacheManager()


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    key = ":".join(key_parts)
    return hashlib.md5(key.encode()).hexdigest()[:32]


def cached_function(timeout: Optional[int] = None, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            func_name = f"{func.__module__}.{func.__name__}"
            key_parts = [key_prefix, func_name] if key_prefix else [func_name]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            
            cache_key = ":".join(key_parts)
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()[:32]
            
            # Try to get from cache
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # Execute function
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            # Cache result
            cache_timeout = timeout or cache_manager.default_timeout
            cache_manager.set(cache_key, result, cache_timeout)
            
            logger.debug(
                f"Function cached: {func_name} executed in {execution_time:.2f}ms, "
                f"cached for {cache_timeout}s"
            )
            
            return result
        
        # Add cache invalidation method
        def invalidate(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            key_parts = [key_prefix, func_name] if key_prefix else [func_name]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            
            cache_key = ":".join(key_parts)
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()[:32]
            
            cache_manager.delete(cache_key)
        
        wrapper.invalidate = invalidate
        return wrapper
    
    return decorator


def cached_queryset(timeout: Optional[int] = None, key_prefix: str = "queryset"):
    """Decorator to cache Django QuerySet results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function and arguments
            func_name = f"{func.__module__}.{func.__name__}"
            key = CacheKeyGenerator.query_key(func_name, {
                'args': args,
                'kwargs': kwargs
            })
            
            if key_prefix:
                key = f"{key_prefix}:{key}"
            
            # Try to get from cache
            cached_result = cache_manager.get(key)
            if cached_result is not None:
                logger.debug(f"QuerySet cache hit: {key}")
                return cached_result
            
            # Execute function
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            # Convert QuerySet to list for caching
            if hasattr(result, '__iter__') and hasattr(result, 'model'):
                cached_data = list(result)
            else:
                cached_data = result
            
            # Cache result
            cache_timeout = timeout or cache_manager.default_timeout
            cache_manager.set(key, cached_data, cache_timeout)
            
            logger.debug(
                f"QuerySet cached: {func_name} executed in {execution_time:.2f}ms, "
                f"cached {len(cached_data) if isinstance(cached_data, list) else 1} items"
            )
            
            return result
        
        return wrapper
    
    return decorator


class CacheInvalidator:
    """Utility for cache invalidation patterns."""
    
    @staticmethod
    def invalidate_user_caches(user_id: int):
        """Invalidate all caches for a specific user."""
        patterns = [
            f"user:{user_id}:*",
            f"*:user:{user_id}:*",
            f"api:*:user:{user_id}:*"
        ]
        
        for pattern in patterns:
            cache_manager.invalidate_pattern(pattern)
        
        logger.info(f"Invalidated user caches for user {user_id}")
    
    @staticmethod
    def invalidate_notebook_caches(notebook_id: str):
        """Invalidate all caches for a specific notebook."""
        patterns = [
            f"notebook:{notebook_id}:*",
            f"*:notebook:{notebook_id}:*"
        ]
        
        for pattern in patterns:
            cache_manager.invalidate_pattern(pattern)
        
        logger.info(f"Invalidated notebook caches for notebook {notebook_id}")
    
    @staticmethod
    def invalidate_model_caches(model_name: str):
        """Invalidate all caches for a specific model."""
        patterns = [
            f"query:{model_name}:*",
            f"queryset:{model_name}:*"
        ]
        
        for pattern in patterns:
            cache_manager.invalidate_pattern(pattern)
        
        logger.info(f"Invalidated model caches for {model_name}")


def warm_cache():
    """Warm up frequently accessed cache entries."""
    logger.info("Starting cache warm-up process...")
    
    try:
        # Warm up common queries
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Cache active user count
        active_users = User.objects.filter(is_active=True).count()
        cache_manager.set("stats:active_users", active_users, timeout=3600)
        
        # Cache system statistics
        from notebooks.models import Notebook, KnowledgeBaseItem
        
        notebook_count = Notebook.objects.count()
        file_count = KnowledgeBaseItem.objects.count()
        
        cache_manager.set("stats:notebook_count", notebook_count, timeout=3600)
        cache_manager.set("stats:file_count", file_count, timeout=3600)
        
        logger.info("Cache warm-up completed successfully")
        
    except Exception as e:
        logger.exception(f"Cache warm-up failed: {e}")


# Cache configuration for different environments
CACHE_CONFIGS = {
    'development': {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'TIMEOUT': 300,
            'OPTIONS': {
                'MAX_ENTRIES': 1000,
                'CULL_FREQUENCY': 3,
            }
        }
    },
    'production': {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://localhost:6379/1',
            'TIMEOUT': 300,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 50,
                    'health_check_interval': 30,
                },
                'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            },
            'KEY_PREFIX': 'deepsight',
            'VERSION': 1,
        }
    }
}