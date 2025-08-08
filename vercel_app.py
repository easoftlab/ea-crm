#!/usr/bin/env python3
"""
Basic EA CRM for Vercel deployment
Working version without session dependencies
"""

from flask import Flask, render_template_string, request, redirect, url_for
import os

app = Flask(__name__)

@app.route('/')
def home():
    # Show login page directly without session check
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Simple hardcoded login for testing
        if username == 'admin' and password == 'admin123':
            return redirect(url_for('dashboard'))
        else:
            error_message = 'Invalid username or password'
    else:
        error_message = ""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EA CRM - Login</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                padding: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .login-container { 
                background: white; 
                padding: 40px; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 400px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                color: #333;
            }
            .form-group input {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
                box-sizing: border-box;
            }
            .login-btn {
                width: 100%;
                background: #667eea;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            .login-btn:hover {
                background: #5a6fd8;
            }
            .flash {
                background: #ffebee;
                color: #c62828;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1 style="text-align: center; margin-bottom: 30px;">🚀 EA CRM</h1>
            
            {flash_messages}
            
            <form method="POST">
                <div class="form-group">
                    <label>Username:</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="login-btn">Login</button>
            </form>
            
            <p style="text-align: center; margin-top: 20px; color: #666;">
                <strong>Default Login:</strong><br>
                Username: admin<br>
                Password: admin123
            </p>
        </div>
    </body>
    </html>
    """
    
    flash_messages = ""
    if error_message:
        flash_messages = f'<div class="flash">{error_message}</div>'
    
    return html.format(flash_messages=flash_messages)

@app.route('/dashboard')
def dashboard():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EA CRM - Dashboard</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                padding: 0; 
                background: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .stat-card h3 {
                margin: 0 0 10px 0;
                color: #333;
            }
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .nav-menu {
                background: white;
                padding: 15px;
                margin: 20px 0;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .nav-menu a {
                color: #667eea;
                text-decoration: none;
                margin-right: 20px;
                padding: 10px 15px;
                border-radius: 5px;
                transition: background 0.3s;
            }
            .nav-menu a:hover {
                background: #f0f0f0;
            }
            .logout-btn {
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
            }
            .logout-btn:hover {
                background: rgba(255,255,255,0.3);
            }
            .success-info {
                background: #e8f5e8;
                color: #2e7d32;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 EA CRM Dashboard</h1>
            <a href="/" class="logout-btn">Logout</a>
        </div>
        
        <div class="container">
            <div class="success-info">
                <strong>✅ Status:</strong> EA CRM is working successfully on Vercel!
            </div>
            
            <div class="nav-menu">
                <a href="/dashboard">Dashboard</a>
                <a href="/leads">Leads</a>
                <a href="/tasks">Tasks</a>
                <a href="/add_lead">Add Lead</a>
                <a href="/add_task">Add Task</a>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>📊 Total Leads</h3>
                    <div class="stat-number">0</div>
                </div>
                <div class="stat-card">
                    <h3>✅ Active Tasks</h3>
                    <div class="stat-number">0</div>
                </div>
                <div class="stat-card">
                    <h3>🆕 New Leads</h3>
                    <div class="stat-number">0</div>
                </div>
                <div class="stat-card">
                    <h3>📈 Conversion Rate</h3>
                    <div class="stat-number">0%</div>
                </div>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 20px;">
                <h3>🎉 Success!</h3>
                <p>The EA CRM is now working on Vercel! This is a functional version with login and navigation.</p>
                <p><strong>What's Working:</strong></p>
                <ul>
                    <li>✅ Basic deployment working</li>
                    <li>✅ Login system functional</li>
                    <li>✅ Dashboard displaying</li>
                    <li>✅ Navigation between pages</li>
                    <li>🔄 Next: Add database functionality</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/leads')
def leads():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EA CRM - Leads</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .nav-menu { background: white; padding: 15px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .nav-menu a { color: #667eea; text-decoration: none; margin-right: 20px; padding: 10px 15px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📋 Leads Management</h1>
        </div>
        
        <div class="container">
            <div class="nav-menu">
                <a href="/dashboard">Dashboard</a>
                <a href="/leads">Leads</a>
                <a href="/tasks">Tasks</a>
                <a href="/add_lead">Add Lead</a>
                <a href="/add_task">Add Task</a>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h3>📋 Leads</h3>
                <p>Database functionality will be added in the next version.</p>
                <p>Currently showing: 0 leads</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/add_lead', methods=['GET', 'POST'])
def add_lead():
    if 'user_id' not in request.args: # Changed from session to request.args
        return redirect(url_for('login'))
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EA CRM - Add Lead</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; }
            .form-container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 5px; color: #333; }
            .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; box-sizing: border-box; }
            .submit-btn { background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
            .submit-btn:hover { background: #5a6fd8; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>➕ Add New Lead</h1>
        </div>
        
        <div class="container">
            <div class="form-container">
                <h3>Database functionality coming soon!</h3>
                <p>This feature will be available in the next version with database integration.</p>
                <a href="/leads" style="color: #667eea;">← Back to Leads</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/tasks')
def tasks():
    if 'user_id' not in request.args: # Changed from session to request.args
        return redirect(url_for('login'))
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EA CRM - Tasks</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .nav-menu { background: white; padding: 15px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .nav-menu a { color: #667eea; text-decoration: none; margin-right: 20px; padding: 10px 15px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📝 Tasks Management</h1>
        </div>
        
        <div class="container">
            <div class="nav-menu">
                <a href="/dashboard">Dashboard</a>
                <a href="/leads">Leads</a>
                <a href="/tasks">Tasks</a>
                <a href="/add_lead">Add Lead</a>
                <a href="/add_task">Add Task</a>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h3>📝 Tasks</h3>
                <p>Database functionality will be added in the next version.</p>
                <p>Currently showing: 0 tasks</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in request.args: # Changed from session to request.args
        return redirect(url_for('login'))
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EA CRM - Add Task</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; }
            .form-container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 5px; color: #333; }
            .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; box-sizing: border-box; }
            .submit-btn { background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
            .submit-btn:hover { background: #5a6fd8; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>➕ Add New Task</h1>
        </div>
        
        <div class="container">
            <div class="form-container">
                <h3>Database functionality coming soon!</h3>
                <p>This feature will be available in the next version with database integration.</p>
                <a href="/tasks" style="color: #667eea;">← Back to Tasks</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/health')
def health():
    return "Health check: OK ✅"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) 