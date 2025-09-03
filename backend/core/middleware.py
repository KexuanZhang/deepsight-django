"""
Custom Django middleware for enhanced functionality.

Provides middleware for:
- Request/response timing and logging
- API rate limiting and throttling
- Security headers and CORS handling
- Request ID tracking for debugging
- Performance monitoring and metrics
"""

import time
import uuid
import logging
from typing import Callable, Optional
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import json

logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    """
    Middleware to track request timing and add performance headers.
    
    Adds response headers:
    - X-Request-Time: Processing time in milliseconds
    - X-Request-ID: Unique request identifier
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Add headers
        response['X-Request-Time'] = f"{processing_time:.2f}ms"
        response['X-Request-ID'] = request_id
        
        # Log slow requests
        if processing_time > getattr(settings, 'SLOW_REQUEST_THRESHOLD_MS', 1000):
            logger.warning(
                f"Slow request detected: {request.method} {request.path} "
                f"took {processing_time:.2f}ms (ID: {request_id})"
            )
        
        return response


class RequestLoggingMiddleware:
    """
    Middleware for comprehensive request/response logging.
    
    Logs request details for debugging and monitoring purposes.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip logging for static files and health checks
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            request.path == '/health/'):
            return self.get_response(request)
        
        # Log request
        request_data = {
            'method': request.method,
            'path': request.path,
            'user_id': request.user.id if request.user.is_authenticated else None,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'request_id': getattr(request, 'request_id', 'unknown'),
            'timestamp': timezone.now().isoformat()
        }
        
        # Log request body for POST/PUT/PATCH (excluding sensitive data)
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.content_type == 'application/json':
                    body = json.loads(request.body.decode('utf-8'))
                    # Remove sensitive fields
                    sanitized_body = self._sanitize_data(body)
                    request_data['body'] = sanitized_body
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_data['body'] = '[Non-JSON content]'
        
        logger.info(f"Request: {json.dumps(request_data)}")
        
        # Process request
        response = self.get_response(request)
        
        # Log response
        response_data = {
            'request_id': getattr(request, 'request_id', 'unknown'),
            'status_code': response.status_code,
            'content_type': response.get('Content-Type', ''),
            'response_size': len(response.content) if hasattr(response, 'content') else 0
        }
        
        # Log response body for errors (sanitized)
        if response.status_code >= 400:
            try:
                if hasattr(response, 'content'):
                    response_content = json.loads(response.content.decode('utf-8'))
                    response_data['error_details'] = self._sanitize_data(response_content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                response_data['error_details'] = '[Non-JSON content]'
        
        logger.info(f"Response: {json.dumps(response_data)}")
        
        return response
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _sanitize_data(self, data: dict) -> dict:
        """Remove sensitive data from logging."""
        sensitive_fields = [
            'password', 'token', 'api_key', 'secret', 'credential',
            'authorization', 'cookie', 'session'
        ]
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(field in key.lower() for field in sensitive_fields):
                    sanitized[key] = '[REDACTED]'
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        
        return data


class RateLimitMiddleware:
    """
    Simple rate limiting middleware.
    
    Implements per-IP and per-user rate limiting with configurable limits.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.default_rate_limit = getattr(settings, 'DEFAULT_RATE_LIMIT', 1000)  # requests per hour
        self.rate_limit_period = 3600  # 1 hour in seconds
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip rate limiting for certain paths
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            request.path == '/health/'):
            return self.get_response(request)
        
        # Get rate limit key
        if request.user.is_authenticated:
            rate_key = f"rate_limit:user:{request.user.id}"
            rate_limit = getattr(settings, 'USER_RATE_LIMIT', self.default_rate_limit)
        else:
            ip = self._get_client_ip(request)
            rate_key = f"rate_limit:ip:{ip}"
            rate_limit = getattr(settings, 'ANONYMOUS_RATE_LIMIT', self.default_rate_limit // 10)
        
        # Check current count
        current_count = cache.get(rate_key, 0)
        
        if current_count >= rate_limit:
            logger.warning(f"Rate limit exceeded for {rate_key}: {current_count}/{rate_limit}")
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'limit': rate_limit,
                    'period': self.rate_limit_period,
                    'retry_after': self.rate_limit_period
                },
                status=429
            )
        
        # Increment count
        cache.set(rate_key, current_count + 1, self.rate_limit_period)
        
        # Process request
        response = self.get_response(request)
        
        # Add rate limit headers
        response['X-RateLimit-Limit'] = str(rate_limit)
        response['X-RateLimit-Remaining'] = str(max(0, rate_limit - current_count - 1))
        response['X-RateLimit-Reset'] = str(int(time.time()) + self.rate_limit_period)
        
        return response
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to responses.
    
    Adds recommended security headers for API security.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # CORS headers for API endpoints
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Origin'] = getattr(
                settings, 'CORS_ALLOW_ORIGIN', 'http://localhost:5173'
            )
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = (
                'Authorization, Content-Type, X-Requested-With, X-CSRFToken'
            )
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response


class HealthCheckMiddleware:
    """
    Middleware to handle health check endpoints efficiently.
    
    Provides quick health checks without full request processing.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Handle health check
        if request.path == '/health/' and request.method == 'GET':
            return self._health_check_response()
        
        # Handle readiness check
        if request.path == '/ready/' and request.method == 'GET':
            return self._readiness_check_response()
        
        return self.get_response(request)
    
    def _health_check_response(self) -> JsonResponse:
        """Quick health check response."""
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'deepsight-django'
        })
    
    def _readiness_check_response(self) -> JsonResponse:
        """Readiness check with basic dependency verification."""
        try:
            # Quick database check
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # Quick cache check
            cache_key = f"health_check_{int(time.time())}"
            cache.set(cache_key, 'test', 10)
            cache_test = cache.get(cache_key) == 'test'
            cache.delete(cache_key)
            
            if not cache_test:
                raise Exception("Cache check failed")
            
            return JsonResponse({
                'status': 'ready',
                'timestamp': timezone.now().isoformat(),
                'checks': {
                    'database': 'healthy',
                    'cache': 'healthy'
                }
            })
            
        except Exception as e:
            logger.exception(f"Readiness check failed: {e}")
            return JsonResponse({
                'status': 'not_ready',
                'timestamp': timezone.now().isoformat(),
                'error': str(e)
            }, status=503)


class APIVersionMiddleware:
    """
    Middleware to handle API versioning.
    
    Supports version detection via URL path and Accept header.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Detect API version
        api_version = self._detect_api_version(request)
        request.api_version = api_version
        
        response = self.get_response(request)
        
        # Add API version header
        if api_version:
            response['X-API-Version'] = api_version
        
        return response
    
    def _detect_api_version(self, request: HttpRequest) -> Optional[str]:
        """Detect API version from request."""
        # Check URL path
        if request.path.startswith('/api/v'):
            parts = request.path.split('/')
            if len(parts) >= 3 and parts[2].startswith('v'):
                return parts[2]  # e.g., 'v1', 'v2'
        
        # Check Accept header
        accept_header = request.META.get('HTTP_ACCEPT', '')
        if 'application/vnd.deepsight.' in accept_header:
            # Format: application/vnd.deepsight.v1+json
            try:
                version_part = accept_header.split('vnd.deepsight.')[1].split('+')[0]
                return version_part
            except (IndexError, AttributeError):
                pass
        
        return None