#!/usr/bin/env python3
"""
Security Hardening Module
Implements security features including rate limiting, security logging, and access control auditing
"""

import time
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import wraps
from flask import request, current_app, g
from flask_login import current_user

class RateLimiter:
    """Rate limiter for API endpoints."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self._requests = {}
        self._default_limit = 100  # requests per window
        self._default_window = 3600  # 1 hour window
    
    def _get_client_ip(self) -> str:
        """Get client IP address."""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0]
        return request.remote_addr
    
    def _get_user_id(self) -> str:
        """Get user ID for rate limiting."""
        if current_user.is_authenticated:
            return f"user_{current_user.id}"
        return f"ip_{self._get_client_ip()}"
    
    def is_allowed(self, key: str, limit: int = None, window: int = None) -> bool:
        """Check if request is allowed."""
        limit = limit or self._default_limit
        window = window or self._default_window
        now = time.time()
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Remove old requests outside the window
        self._requests[key] = [req_time for req_time in self._requests[key] 
                             if now - req_time < window]
        
        # Check if limit exceeded
        if len(self._requests[key]) >= limit:
            return False
        
        # Add current request
        self._requests[key].append(now)
        return True
    
    def get_remaining_requests(self, key: str, limit: int = None, window: int = None) -> int:
        """Get remaining requests for a key."""
        limit = limit or self._default_limit
        window = window or self._default_window
        now = time.time()
        
        if key not in self._requests:
            return limit
        
        # Remove old requests outside the window
        self._requests[key] = [req_time for req_time in self._requests[key] 
                             if now - req_time < window]
        
        return max(0, limit - len(self._requests[key]))

# Global rate limiter instance
rate_limiter = RateLimiter()

class SecurityLogger:
    """Security logging system."""
    
    def __init__(self, log_file: str = "security.log"):
        """Initialize security logger."""
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
    
    def log_access_attempt(self, user_id: Optional[int], endpoint: str, 
                          success: bool, ip_address: str, details: str = ""):
        """Log access attempt."""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'endpoint': endpoint,
            'success': success,
            'ip_address': ip_address,
            'user_agent': request.headers.get('User-Agent', ''),
            'details': details
        }
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, f"Access attempt: {json.dumps(log_data)}")
    
    def log_security_event(self, event_type: str, user_id: Optional[int], 
                          details: Dict[str, Any]):
        """Log security event."""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': request.remote_addr,
            'details': details
        }
        
        self.logger.warning(f"Security event: {json.dumps(log_data)}")
    
    def log_rate_limit_exceeded(self, user_id: str, endpoint: str):
        """Log rate limit exceeded."""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'endpoint': endpoint,
            'ip_address': request.remote_addr
        }
        
        self.logger.warning(f"Rate limit exceeded: {json.dumps(log_data)}")

# Global security logger instance
security_logger = SecurityLogger()

class AccessControlAuditor:
    """Access control auditing system."""
    
    def __init__(self):
        """Initialize access control auditor."""
        self._access_log = []
        self._suspicious_patterns = []
    
    def log_access(self, user_id: Optional[int], resource: str, 
                   action: str, success: bool, details: Dict[str, Any] = None):
        """Log access control event."""
        access_event = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'success': success,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'details': details or {}
        }
        
        self._access_log.append(access_event)
        
        # Check for suspicious patterns
        self._check_suspicious_patterns(access_event)
        
        # Log to security logger
        if not success:
            security_logger.log_security_event(
                'access_denied', user_id, access_event
            )
    
    def _check_suspicious_patterns(self, access_event: Dict[str, Any]):
        """Check for suspicious access patterns."""
        user_id = access_event['user_id']
        resource = access_event['resource']
        success = access_event['success']
        
        # Check for multiple failed attempts
        recent_failures = [
            event for event in self._access_log[-10:]
            if event['user_id'] == user_id and 
               event['resource'] == resource and 
               not event['success']
        ]
        
        if len(recent_failures) >= 3:
            security_logger.log_security_event(
                'multiple_failures', user_id, {
                    'resource': resource,
                    'failure_count': len(recent_failures)
                }
            )
    
    def get_access_summary(self, user_id: Optional[int] = None, 
                          time_window: int = 3600) -> Dict[str, Any]:
        """Get access summary for monitoring."""
        now = datetime.now()
        window_start = now - timedelta(seconds=time_window)
        
        recent_events = [
            event for event in self._access_log
            if datetime.fromisoformat(event['timestamp']) >= window_start
        ]
        
        if user_id:
            recent_events = [
                event for event in recent_events
                if event['user_id'] == user_id
            ]
        
        successful_access = len([e for e in recent_events if e['success']])
        failed_access = len([e for e in recent_events if not e['success']])
        
        return {
            'total_events': len(recent_events),
            'successful_access': successful_access,
            'failed_access': failed_access,
            'success_rate': (successful_access / len(recent_events) * 100) if recent_events else 0,
            'time_window': time_window
        }

# Global access control auditor instance
access_auditor = AccessControlAuditor()

def rate_limit(limit: int = 100, window: int = 3600):
    """Decorator for rate limiting endpoints."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get rate limit key
            if current_user.is_authenticated:
                key = f"user_{current_user.id}_{func.__name__}"
            else:
                key = f"ip_{request.remote_addr}_{func.__name__}"
            
            # Check rate limit
            if not rate_limiter.is_allowed(key, limit, window):
                security_logger.log_rate_limit_exceeded(
                    current_user.id if current_user.is_authenticated else 'anonymous',
                    request.endpoint
                )
                return {'error': 'Rate limit exceeded'}, 429
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def audit_access(resource: str, action: str):
    """Decorator for auditing access."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = current_user.id if current_user.is_authenticated else None
            
            try:
                result = func(*args, **kwargs)
                # Log successful access
                access_auditor.log_access(
                    user_id, resource, action, True,
                    {'endpoint': request.endpoint}
                )
                return result
            except Exception as e:
                # Log failed access
                access_auditor.log_access(
                    user_id, resource, action, False,
                    {'endpoint': request.endpoint, 'error': str(e)}
                )
                raise
        return wrapper
    return decorator

def validate_input_sanitization(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize input data."""
    sanitized_data = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Basic XSS prevention
            sanitized_value = value.replace('<script>', '').replace('</script>', '')
            sanitized_value = sanitized_value.replace('javascript:', '')
            sanitized_data[key] = sanitized_value
        elif isinstance(value, (int, float, bool)):
            sanitized_data[key] = value
        elif isinstance(value, list):
            sanitized_data[key] = [validate_input_sanitization(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            sanitized_data[key] = validate_input_sanitization(value)
        else:
            # Skip unsupported types
            continue
    
    return sanitized_data

def validate_csrf_token():
    """Validate CSRF token for POST requests."""
    if request.method == 'POST':
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not token or not current_app.csrf.validate_token(token):
            security_logger.log_security_event(
                'csrf_violation',
                current_user.id if current_user.is_authenticated else None,
                {'endpoint': request.endpoint}
            )
            return False
    return True

def check_permission_escalation(user_id: int, requested_permission: str) -> bool:
    """Check for permission escalation attempts."""
    # This would integrate with your permission system
    # For now, we'll log the check
    security_logger.log_security_event(
        'permission_check',
        user_id,
        {'requested_permission': requested_permission}
    )
    return True

def monitor_suspicious_activity():
    """Monitor for suspicious activity patterns."""
    # Check for rapid successive requests
    recent_requests = getattr(g, 'recent_requests', [])
    current_time = time.time()
    
    # Remove old requests (older than 1 minute)
    recent_requests = [req for req in recent_requests if current_time - req < 60]
    
    # Add current request
    recent_requests.append(current_time)
    g.recent_requests = recent_requests
    
    # Alert if too many requests in short time
    if len(recent_requests) > 50:  # More than 50 requests per minute
        security_logger.log_security_event(
            'suspicious_activity',
            current_user.id if current_user.is_authenticated else None,
            {'request_count': len(recent_requests), 'time_window': 60}
        )

def get_security_stats() -> Dict[str, Any]:
    """Get security statistics for monitoring."""
    return {
        'rate_limiter_stats': {
            'total_keys': len(rate_limiter._requests),
            'active_requests': sum(len(requests) for requests in rate_limiter._requests.values())
        },
        'access_auditor_stats': access_auditor.get_access_summary(),
        'security_log_stats': {
            'timestamp': datetime.now().isoformat()
        }
    }

def security_performance_test():
    """Test security features performance."""
    print("🧪 Testing Security Features...")
    
    # Test rate limiter
    test_key = "test_user_api"
    assert rate_limiter.is_allowed(test_key, 5, 60)  # 5 requests per minute
    assert rate_limiter.get_remaining_requests(test_key, 5, 60) == 4
    
    # Test input sanitization
    test_data = {
        'name': 'John<script>alert("xss")</script>',
        'email': 'john@example.com',
        'age': 25
    }
    sanitized = validate_input_sanitization(test_data)
    assert '<script>' not in sanitized['name']
    assert sanitized['age'] == 25
    
    # Test access auditor
    access_auditor.log_access(1, 'test_resource', 'read', True)
    summary = access_auditor.get_access_summary(user_id=1, time_window=3600)
    assert summary['successful_access'] >= 1
    
    print("✅ Security features test passed!")
    return True

if __name__ == "__main__":
    security_performance_test() 