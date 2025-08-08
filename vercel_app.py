#!/usr/bin/env python3
"""
Ultra-simple EA CRM for Vercel deployment
Plain text version to isolate issues
"""

from flask import Flask, request, redirect
import os

app = Flask(__name__)

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username == 'admin' and password == 'admin123':
            return redirect('/dashboard')
        else:
            return """
            <html>
            <head><title>EA CRM - Login</title></head>
            <body>
                <h1>EA CRM Login</h1>
                <p style="color: red;">Invalid username or password</p>
                <form method="POST">
                    <p>Username: <input type="text" name="username" required></p>
                    <p>Password: <input type="password" name="password" required></p>
                    <p><input type="submit" value="Login"></p>
                </form>
                <p><strong>Default:</strong> admin / admin123</p>
            </body>
            </html>
            """
    
    return """
    <html>
    <head><title>EA CRM - Login</title></head>
    <body>
        <h1>EA CRM Login</h1>
        <form method="POST">
            <p>Username: <input type="text" name="username" required></p>
            <p>Password: <input type="password" name="password" required></p>
            <p><input type="submit" value="Login"></p>
        </form>
        <p><strong>Default:</strong> admin / admin123</p>
    </body>
    </html>
    """

@app.route('/dashboard')
def dashboard():
    return """
    <html>
    <head><title>EA CRM - Dashboard</title></head>
    <body>
        <h1>EA CRM Dashboard</h1>
        <p>✅ Success! The CRM is working on Vercel!</p>
        <p><a href="/leads">Leads</a> | <a href="/tasks">Tasks</a> | <a href="/">Logout</a></p>
        <h3>Stats:</h3>
        <ul>
            <li>Total Leads: 0</li>
            <li>Active Tasks: 0</li>
            <li>New Leads: 0</li>
        </ul>
    </body>
    </html>
    """

@app.route('/leads')
def leads():
    return """
    <html>
    <head><title>EA CRM - Leads</title></head>
    <body>
        <h1>Leads Management</h1>
        <p><a href="/dashboard">← Back to Dashboard</a></p>
        <p>Database functionality coming soon!</p>
        <p>Currently showing: 0 leads</p>
    </body>
    </html>
    """

@app.route('/tasks')
def tasks():
    return """
    <html>
    <head><title>EA CRM - Tasks</title></head>
    <body>
        <h1>Tasks Management</h1>
        <p><a href="/dashboard">← Back to Dashboard</a></p>
        <p>Database functionality coming soon!</p>
        <p>Currently showing: 0 tasks</p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return "Health check: OK ✅"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) 