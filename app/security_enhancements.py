#!/usr/bin/env python3
"""
Enhanced Security Features
Provides advanced security features including rate limiting, audit logging, and advanced authentication
"""

import os
import sqlite3
import hashlib
import secrets
import time
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, session, g, abort, jsonify
import jwt
from cryptography.fernet import Fernet
import bcrypt

class SecurityEnhancements:
    """Enhanced security features for the application."""
    
    def __init__(self, app=None, db_path='instance/leads.db'):
        self.db_path = db_path
        self.rate_limit_store = {}
        self.audit_log_enabled = True
        self.max_login_attempts = 5
        self.lockout_duration = 900  # 15 minutes
        self.session_timeout = 3600  # 1 hour
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security features with Flask app."""
        self.app = app
        
        # Setup database tables
        self.setup_security_tables()
        
        # Register before_request handler
        app.before_request(self.before_request)
        
        # Register after_request handler
        app.after_request(self.after_request)
        
        # Setup session configuration
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    def setup_security_tables(self):
        """Setup security-related database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT,
                resource TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                details TEXT
            )
        """)
        
        # Failed login attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_logins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                ip_address TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT
            )
        """)
        
        # Rate limiting table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT,
                endpoint TEXT,
                count INTEGER DEFAULT 1,
                first_request DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_request DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Security events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                severity TEXT,
                description TEXT,
                ip_address TEXT,
                user_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE
            )
        """)
        
        # API keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                key_hash TEXT,
                name TEXT,
                permissions TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used DATETIME,
                active BOOLEAN DEFAULT TRUE
            )
        """)
        
        conn.commit()
        conn.close()
    
    def before_request(self):
        """Security checks before each request."""
        # Check session timeout
        if 'user_id' in session:
            if 'last_activity' in session:
                last_activity = datetime.fromisoformat(session['last_activity'])
                if datetime.now() - last_activity > timedelta(seconds=self.session_timeout):
                    self.logout_user()
                    return jsonify({'error': 'Session expired'}), 401
            
            session['last_activity'] = datetime.now().isoformat()
        
        # Rate limiting
        if not self.check_rate_limit():
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Check for suspicious activity
        self.detect_suspicious_activity()
    
    def after_request(self, response):
        """Security actions after each request."""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        
        # Log audit trail
        if self.audit_log_enabled:
            self.log_audit_trail(response)
        
        return response
    
    def rate_limit(self, max_requests=100, window=3600):
        """Rate limiting decorator."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                identifier = self.get_rate_limit_identifier()
                if not self.check_rate_limit_for_endpoint(identifier, request.endpoint, max_requests, window):
                    return jsonify({'error': 'Rate limit exceeded'}), 429
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def get_rate_limit_identifier(self):
        """Get identifier for rate limiting."""
        if 'user_id' in session:
            return f"user_{session['user_id']}"
        return f"ip_{request.remote_addr}"
    
    def check_rate_limit_for_endpoint(self, identifier, endpoint, max_requests, window):
        """Check rate limit for specific endpoint."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clean old entries
        cutoff_time = datetime.now() - timedelta(seconds=window)
        cursor.execute("""
            DELETE FROM rate_limits 
            WHERE last_request < ?
        """, (cutoff_time,))
        
        # Check current rate
        cursor.execute("""
            SELECT count, first_request 
            FROM rate_limits 
            WHERE identifier = ? AND endpoint = ?
        """, (identifier, endpoint))
        
        result = cursor.fetchone()
        
        if result:
            count, first_request = result
            if count >= max_requests:
                conn.close()
                return False
            
            # Update count
            cursor.execute("""
                UPDATE rate_limits 
                SET count = count + 1, last_request = ? 
                WHERE identifier = ? AND endpoint = ?
            """, (datetime.now(), identifier, endpoint))
        else:
            # Create new entry
            cursor.execute("""
                INSERT INTO rate_limits (identifier, endpoint, count, first_request, last_request)
                VALUES (?, ?, 1, ?, ?)
            """, (identifier, endpoint, datetime.now(), datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    
    def check_rate_limit(self):
        """Check general rate limiting."""
        return self.check_rate_limit_for_endpoint(
            self.get_rate_limit_identifier(),
            request.endpoint,
            1000,  # 1000 requests per hour
            3600
        )
    
    def detect_suspicious_activity(self):
        """Detect and log suspicious activity."""
        suspicious_patterns = [
            'script', 'javascript:', 'vbscript:', 'onload=', 'onerror=',
            'union select', 'drop table', 'insert into', 'delete from',
            'exec(', 'eval(', 'document.cookie'
        ]
        
        # Check request parameters
        for key, value in request.values.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for pattern in suspicious_patterns:
                    if pattern in value_lower:
                        self.log_security_event(
                            'SUSPICIOUS_INPUT',
                            'HIGH',
                            f'Suspicious input detected in parameter {key}: {value[:100]}',
                            request.remote_addr,
                            session.get('user_id')
                        )
                        return False
        
        # Check for unusual request patterns
        if request.method == 'POST' and not request.is_json:
            content_type = request.headers.get('Content-Type', '')
            if 'application/x-www-form-urlencoded' not in content_type:
                self.log_security_event(
                    'UNUSUAL_REQUEST',
                    'MEDIUM',
                    f'Unusual content type: {content_type}',
                    request.remote_addr,
                    session.get('user_id')
                )
        
        return True
    
    def log_security_event(self, event_type, severity, description, ip_address, user_id=None):
        """Log security events."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO security_events (event_type, severity, description, ip_address, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, severity, description, ip_address, user_id))
        
        conn.commit()
        conn.close()
    
    def log_audit_trail(self, response):
        """Log audit trail for requests."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        user_id = session.get('user_id')
        username = session.get('username', 'anonymous')
        
        cursor.execute("""
            INSERT INTO audit_log (user_id, username, action, resource, ip_address, user_agent, success, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            username,
            request.method,
            request.path,
            request.remote_addr,
            request.headers.get('User-Agent', ''),
            response.status_code < 400,
            f'Status: {response.status_code}, Size: {len(response.get_data())}'
        ))
        
        conn.commit()
        conn.close()
    
    def check_login_attempts(self, username, ip_address):
        """Check if user is locked out due to failed login attempts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clean old failed attempts
        cutoff_time = datetime.now() - timedelta(seconds=self.lockout_duration)
        cursor.execute("""
            DELETE FROM failed_logins 
            WHERE timestamp < ?
        """, (cutoff_time,))
        
        # Count recent failed attempts
        cursor.execute("""
            SELECT COUNT(*) FROM failed_logins 
            WHERE username = ? AND ip_address = ?
        """, (username, ip_address))
        
        failed_count = cursor.fetchone()[0]
        conn.close()
        
        return failed_count < self.max_login_attempts
    
    def record_failed_login(self, username, ip_address):
        """Record a failed login attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO failed_logins (username, ip_address, user_agent)
            VALUES (?, ?, ?)
        """, (username, ip_address, request.headers.get('User-Agent', '')))
        
        conn.commit()
        conn.close()
        
        # Log security event
        self.log_security_event(
            'FAILED_LOGIN',
            'MEDIUM',
            f'Failed login attempt for user: {username}',
            ip_address
        )
    
    def clear_failed_logins(self, username, ip_address):
        """Clear failed login attempts for successful login."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM failed_logins 
            WHERE username = ? AND ip_address = ?
        """, (username, ip_address))
        
        conn.commit()
        conn.close()
    
    def generate_api_key(self, user_id, name, permissions=None):
        """Generate API key for user."""
        if permissions is None:
            permissions = ['read']
        
        # Generate random key
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_keys (user_id, key_hash, name, permissions)
            VALUES (?, ?, ?, ?)
        """, (user_id, key_hash, name, ','.join(permissions)))
        
        conn.commit()
        conn.close()
        
        return api_key
    
    def validate_api_key(self, api_key):
        """Validate API key and return user info."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, permissions, active 
            FROM api_keys 
            WHERE key_hash = ?
        """, (key_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[2]:  # active
            return {
                'user_id': result[0],
                'permissions': result[1].split(',') if result[1] else []
            }
        
        return None
    
    def require_api_key(self, required_permissions=None):
        """Decorator to require valid API key."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                api_key = request.headers.get('X-API-Key')
                if not api_key:
                    return jsonify({'error': 'API key required'}), 401
                
                key_info = self.validate_api_key(api_key)
                if not key_info:
                    return jsonify({'error': 'Invalid API key'}), 401
                
                if required_permissions:
                    user_permissions = set(key_info['permissions'])
                    required_permissions_set = set(required_permissions)
                    if not required_permissions_set.issubset(user_permissions):
                        return jsonify({'error': 'Insufficient permissions'}), 403
                
                g.api_user_id = key_info['user_id']
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive data."""
        if isinstance(data, str):
            data = data.encode()
        return self.cipher.encrypt(data)
    
    def decrypt_sensitive_data(self, encrypted_data):
        """Decrypt sensitive data."""
        decrypted = self.cipher.decrypt(encrypted_data)
        try:
            return decrypted.decode()
        except UnicodeDecodeError:
            return decrypted
    
    def hash_password(self, password):
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)
    
    def verify_password(self, password, hashed):
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    def generate_jwt_token(self, user_id, username, role):
        """Generate JWT token for user."""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.now(timezone.utc) + timedelta(hours=24),
            'iat': datetime.now(timezone.utc)
        }
        
        # In production, use a secure secret key
        secret_key = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token):
        """Verify JWT token and return payload."""
        try:
            secret_key = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def logout_user(self):
        """Logout user and clear session."""
        if 'user_id' in session:
            self.log_security_event(
                'USER_LOGOUT',
                'LOW',
                f'User {session.get("username")} logged out',
                request.remote_addr,
                session.get('user_id')
            )
        
        session.clear()
    
    def get_security_report(self):
        """Generate security report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent security events
        cursor.execute("""
            SELECT event_type, severity, description, timestamp 
            FROM security_events 
            WHERE timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC
        """)
        
        recent_events = cursor.fetchall()
        
        # Get failed login attempts
        cursor.execute("""
            SELECT username, ip_address, COUNT(*) as attempts
            FROM failed_logins 
            WHERE timestamp > datetime('now', '-1 hour')
            GROUP BY username, ip_address
            HAVING attempts >= 3
        """)
        
        suspicious_logins = cursor.fetchall()
        
        # Get rate limit violations
        cursor.execute("""
            SELECT identifier, endpoint, COUNT(*) as violations
            FROM rate_limits 
            WHERE last_request > datetime('now', '-1 hour')
            GROUP BY identifier, endpoint
            HAVING violations > 100
        """)
        
        rate_violations = cursor.fetchall()
        
        conn.close()
        
        return {
            'recent_events': recent_events,
            'suspicious_logins': suspicious_logins,
            'rate_violations': rate_violations,
            'total_events_24h': len(recent_events),
            'high_severity_events': len([e for e in recent_events if e[1] == 'HIGH'])
        }

# Example usage
if __name__ == "__main__":
    # Initialize security enhancements
    security = SecurityEnhancements()
    
    # Generate API key
    api_key = security.generate_api_key(1, 'Test API Key', ['read', 'write'])
    print(f"Generated API key: {api_key}")
    
    # Hash password
    password_hash = security.hash_password('my_password')
    print(f"Password hash: {password_hash}")
    
    # Verify password
    is_valid = security.verify_password('my_password', password_hash)
    print(f"Password valid: {is_valid}")
    
    # Generate JWT token
    token = security.generate_jwt_token(1, 'testuser', 'marketing_manager')
    print(f"JWT token: {token}")
    
    # Verify JWT token
    payload = security.verify_jwt_token(token)
    print(f"JWT payload: {payload}")
    
    print("Security enhancements initialized successfully!") 