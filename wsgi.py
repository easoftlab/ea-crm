#!/usr/bin/env python3
"""
WSGI entry point for EA CRM application
This file is used by web servers to run the Flask application
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask application
from app import create_app

# Create the application instance
app = create_app()

# For direct execution
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False) 