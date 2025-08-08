#!/usr/bin/env python3
"""
Absolute simplest test for Vercel deployment
"""

from flask import Flask, render_template_string
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello World! EA CRM is working! ✅"

@app.route('/test')
def test():
    return "Test route is working! ✅"

@app.route('/health')
def health():
    return "Health check: OK ✅"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) 