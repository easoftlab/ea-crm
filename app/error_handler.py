#!/usr/bin/env python3
"""
Error Handling System
Comprehensive error handling with user-friendly messages, logging, and fallback mechanisms
"""

import logging
import traceback
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from functools import wraps
from flask import request, current_app, jsonify, render_template
from flask_login import current_user

class ErrorHandler:
    """Centralized error handling system."""
    
    def __init__(self, app=None):
        """Initialize error handler."""
        self.app = app
        self.logger = logging.getLogger('error_handler')
        self.error_templates = {}
        self.fallback_handlers = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize error handler with Flask app."""
        self.app = app
        
        # Configure logging
        self.logger.setLevel(logging.ERROR)
        
        # Create file handler
        handler = logging.FileHandler('error.log')
        handler.setLevel(logging.ERROR)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
        
        # Register error handlers
        self._register_error_handlers()
    
    def _register_error_handlers(self):
        """Register error handlers with Flask app."""
        
        @self.app.errorhandler(400)
        def bad_request(error):
            return self.handle_error(400, "Bad Request", error)
        
        @self.app.errorhandler(401)
        def unauthorized(error):
            return self.handle_error(401, "Unauthorized", error)
        
        @self.app.errorhandler(403)
        def forbidden(error):
            return self.handle_error(403, "Forbidden", error)
        
        @self.app.errorhandler(404)
        def not_found(error):
            return self.handle_error(404, "Not Found", error)
        
        @self.app.errorhandler(429)
        def too_many_requests(error):
            return self.handle_error(429, "Too Many Requests", error)
        
        @self.app.errorhandler(500)
        def internal_server_error(error):
            return self.handle_error(500, "Internal Server Error", error)
        
        @self.app.errorhandler(Exception)
        def handle_exception(error):
            return self.handle_error(500, "Internal Server Error", error)
    
    def handle_error(self, status_code: int, message: str, error: Exception = None) -> tuple:
        """Handle errors with appropriate response format."""
        
        # Log the error
        self.log_error(status_code, message, error)
        
        # Determine response format
        if request.is_xhr or request.path.startswith('/api/'):
            # API request - return JSON
            return self._handle_api_error(status_code, message, error)
        else:
            # Web request - return HTML
            return self._handle_web_error(status_code, message, error)
    
    def _handle_api_error(self, status_code: int, message: str, error: Exception = None) -> tuple:
        """Handle API errors with JSON response."""
        error_data = {
            'error': {
                'code': status_code,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'path': request.path,
                'method': request.method
            }
        }
        
        # Add debug information in development
        if current_app.debug and error:
            error_data['error']['debug'] = {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        
        return jsonify(error_data), status_code
    
    def _handle_web_error(self, status_code: int, message: str, error: Exception = None) -> tuple:
        """Handle web errors with HTML response."""
        
        # Try to render custom error template
        template_name = f"errors/{status_code}.html"
        
        try:
            return render_template(template_name, 
                                error_code=status_code,
                                error_message=message,
                                error=error), status_code
        except:
            # Fallback to generic error template
            return render_template("errors/generic.html",
                                error_code=status_code,
                                error_message=message), status_code
    
    def log_error(self, status_code: int, message: str, error: Exception = None):
        """Log error with context information."""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'status_code': status_code,
            'message': message,
            'path': request.path,
            'method': request.method,
            'user_agent': request.headers.get('User-Agent', ''),
            'ip_address': request.remote_addr,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'referrer': request.headers.get('Referer', '')
        }
        
        if error:
            log_data['error_type'] = type(error).__name__
            log_data['error_message'] = str(error)
            log_data['traceback'] = traceback.format_exc()
        
        self.logger.error(f"Error occurred: {json.dumps(log_data)}")
    
    def add_fallback_handler(self, error_type: type, handler: Callable):
        """Add fallback handler for specific error types."""
        self.fallback_handlers[error_type] = handler
    
    def get_error_stats(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        # This would typically query a database or log file
        # For now, return basic stats
        return {
            'total_errors': 0,
            'error_types': {},
            'most_common_errors': [],
            'time_window': time_window,
            'timestamp': datetime.now().isoformat()
        }

# Global error handler instance
error_handler = ErrorHandler()

def handle_errors(func: Callable) -> Callable:
    """Decorator to handle errors in functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the error
            error_handler.log_error(500, str(e), e)
            
            # Return appropriate error response
            if request.is_xhr or request.path.startswith('/api/'):
                return jsonify({
                    'error': {
                        'code': 500,
                        'message': 'Internal Server Error',
                        'timestamp': datetime.now().isoformat()
                    }
                }), 500
            else:
                return render_template("errors/generic.html",
                                    error_code=500,
                                    error_message="Internal Server Error"), 500
    
    return wrapper

def validate_data(data: Dict[str, Any], required_fields: list = None, 
                 optional_fields: list = None) -> tuple[bool, str]:
    """Validate data and return validation result."""
    if required_fields:
        for field in required_fields:
            if field not in data or data[field] is None:
                return False, f"Missing required field: {field}"
    
    if optional_fields:
        for field in data:
            if field not in optional_fields and field not in (required_fields or []):
                return False, f"Unexpected field: {field}"
    
    return True, ""

def safe_execute(func: Callable, *args, **kwargs) -> tuple[Any, Optional[str]]:
    """Safely execute a function and return result with error message."""
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        error_handler.log_error(500, str(e), e)
        return None, str(e)

class DatabaseErrorHandler:
    """Database-specific error handling."""
    
    @staticmethod
    def handle_connection_error(error: Exception) -> tuple:
        """Handle database connection errors."""
        error_handler.log_error(500, "Database connection failed", error)
        
        return jsonify({
            'error': {
                'code': 500,
                'message': 'Database connection failed',
                'timestamp': datetime.now().isoformat()
            }
        }), 500
    
    @staticmethod
    def handle_query_error(error: Exception) -> tuple:
        """Handle database query errors."""
        error_handler.log_error(500, "Database query failed", error)
        
        return jsonify({
            'error': {
                'code': 500,
                'message': 'Database query failed',
                'timestamp': datetime.now().isoformat()
            }
        }), 500
    
    @staticmethod
    def handle_constraint_error(error: Exception) -> tuple:
        """Handle database constraint errors."""
        error_handler.log_error(400, "Data validation failed", error)
        
        return jsonify({
            'error': {
                'code': 400,
                'message': 'Data validation failed',
                'timestamp': datetime.now().isoformat()
            }
        }), 400

class ValidationErrorHandler:
    """Validation-specific error handling."""
    
    @staticmethod
    def handle_validation_error(field: str, message: str) -> tuple:
        """Handle validation errors."""
        error_handler.log_error(400, f"Validation error: {field} - {message}")
        
        return jsonify({
            'error': {
                'code': 400,
                'message': 'Validation failed',
                'details': {
                    'field': field,
                    'message': message
                },
                'timestamp': datetime.now().isoformat()
            }
        }), 400
    
    @staticmethod
    def handle_missing_field(field: str) -> tuple:
        """Handle missing field errors."""
        return ValidationErrorHandler.handle_validation_error(
            field, "This field is required"
        )
    
    @staticmethod
    def handle_invalid_format(field: str, expected_format: str) -> tuple:
        """Handle invalid format errors."""
        return ValidationErrorHandler.handle_validation_error(
            field, f"Invalid format. Expected: {expected_format}"
        )

class PermissionErrorHandler:
    """Permission-specific error handling."""
    
    @staticmethod
    def handle_insufficient_permissions(required_permission: str) -> tuple:
        """Handle insufficient permissions error."""
        error_handler.log_error(403, f"Insufficient permissions: {required_permission}")
        
        return jsonify({
            'error': {
                'code': 403,
                'message': 'Insufficient permissions',
                'details': {
                    'required_permission': required_permission
                },
                'timestamp': datetime.now().isoformat()
            }
        }), 403
    
    @staticmethod
    def handle_unauthorized_access(resource: str) -> tuple:
        """Handle unauthorized access error."""
        error_handler.log_error(401, f"Unauthorized access to: {resource}")
        
        return jsonify({
            'error': {
                'code': 401,
                'message': 'Unauthorized access',
                'details': {
                    'resource': resource
                },
                'timestamp': datetime.now().isoformat()
            }
        }), 401

def create_error_templates():
    """Create error template files."""
    
    # Generic error template
    generic_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error {{ error_code }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card shadow">
                    <div class="card-body text-center">
                        <h1 class="display-1 text-danger">{{ error_code }}</h1>
                        <h2 class="mb-4">{{ error_message }}</h2>
                        <p class="text-muted mb-4">
                            Sorry, something went wrong. Please try again later.
                        </p>
                        <a href="/" class="btn btn-primary">Go Home</a>
                        <a href="javascript:history.back()" class="btn btn-secondary">Go Back</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    # 404 error template
    not_found_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Not Found</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card shadow">
                    <div class="card-body text-center">
                        <h1 class="display-1 text-warning">404</h1>
                        <h2 class="mb-4">Page Not Found</h2>
                        <p class="text-muted mb-4">
                            The page you're looking for doesn't exist.
                        </p>
                        <a href="/" class="btn btn-primary">Go Home</a>
                        <a href="javascript:history.back()" class="btn btn-secondary">Go Back</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    # Create templates directory
    import os
    templates_dir = "app/templates/errors"
    os.makedirs(templates_dir, exist_ok=True)
    
    # Write template files
    with open(f"{templates_dir}/generic.html", "w") as f:
        f.write(generic_template)
    
    with open(f"{templates_dir}/404.html", "w") as f:
        f.write(not_found_template)
    
    print("✅ Error templates created successfully!")

def error_handling_performance_test():
    """Test error handling performance."""
    print("🧪 Testing Error Handling...")
    
    # Test safe_execute
    def test_function(x, y):
        return x + y
    
    result, error = safe_execute(test_function, 5, 3)
    assert result == 8
    assert error is None
    
    # Test error case
    def error_function():
        raise ValueError("Test error")
    
    result, error = safe_execute(error_function)
    assert result is None
    assert error is not None
    
    # Test validation
    data = {'name': 'John', 'email': 'john@example.com'}
    valid, message = validate_data(data, ['name', 'email'])
    assert valid
    assert message == ""
    
    # Test missing field
    data = {'name': 'John'}
    valid, message = validate_data(data, ['name', 'email'])
    assert not valid
    assert "email" in message
    
    print("✅ Error handling test passed!")
    return True

if __name__ == "__main__":
    create_error_templates()
    error_handling_performance_test() 