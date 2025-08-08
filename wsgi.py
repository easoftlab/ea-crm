#!/usr/bin/env python3
"""
WSGI entry point for EA CRM application
This file is used by web servers to run the Flask application
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

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
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        return f"Error: {str(e)}", 500 