#!/usr/bin/env python3
"""
WSGI entry point for EA CRM application
This file is used by web servers to run the Flask application
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Set default environment variables for Vercel
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('SECRET_KEY', 'your-secret-key-here-12345')
os.environ.setdefault('DATABASE_URL', 'sqlite:///instance/leads.db')
os.environ.setdefault('OPENROUTER_API_KEY', '')

try:
    # Import the Flask application
    from app import create_app
    
    # Create the application instance
    app = create_app()
    
    # For Vercel deployment
    if __name__ == "__main__":
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
        
except Exception as e:
    # Create a simple error handler for debugging
    from flask import Flask, render_template_string
    
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        error_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>EA CRM - Setup Required</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .error { color: #d32f2f; background: #ffebee; padding: 15px; border-radius: 4px; margin: 20px 0; }
                .success { color: #388e3c; background: #e8f5e8; padding: 15px; border-radius: 4px; margin: 20px 0; }
                .code { background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 EA CRM - Deployment Status</h1>
                
                <div class="success">
                    <strong>✅ Deployment Successful!</strong><br>
                    Your EA CRM application has been deployed to Vercel successfully.
                </div>
                
                <div class="error">
                    <strong>⚠️ Setup Required</strong><br>
                    The application needs environment variables to be configured.
                </div>
                
                <h2>🔧 Next Steps:</h2>
                <ol>
                    <li><strong>Add Environment Variables</strong> in Vercel Dashboard:
                        <div class="code">
                            SECRET_KEY=your-secret-key-here<br>
                            OPENROUTER_API_KEY=your-api-key<br>
                            FLASK_ENV=production
                        </div>
                    </li>
                    <li><strong>Database Setup</strong> - The app will create SQLite database automatically</li>
                    <li><strong>Test Login</strong> - Use admin/admin123 after setup</li>
                </ol>
                
                <h2>🐛 Debug Information:</h2>
                <div class="code">
                    Error: {{ error }}
                </div>
                
                <p><em>This is a temporary page while the application is being configured.</em></p>
            </div>
        </body>
        </html>
        """
        return render_template_string(error_html, error=str(e))
    
    @app.route('/health')
    def health():
        return {"status": "ok", "message": "EA CRM is deployed but needs configuration"} 