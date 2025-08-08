#!/usr/bin/env python3
"""
Simple test for Vercel deployment
"""

from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "EA CRM Test - Working! ✅"

@app.route('/login')
def login():
    return "Login page - Working! ✅"

@app.route('/test')
def test():
    return "Test route - Working! ✅"

@app.route('/health')
def health():
    return "Health check: OK ✅"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) 