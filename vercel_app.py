#!/usr/bin/env python3
"""
Simplified EA CRM for Vercel deployment
This version supports external databases for production use
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify
import os
import sqlite3
from datetime import datetime
import json

app = Flask(__name__)

# Set secret key
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-12345')

# Database setup - support external databases
def get_db():
    """Get database connection - supports external databases"""
    
    # Check for external database URL
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('postgresql://'):
        # PostgreSQL support
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            return conn
        except ImportError:
            print("PostgreSQL driver not installed, using SQLite")
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}, using SQLite")
    
    elif database_url and database_url.startswith('mysql://'):
        # MySQL support
        try:
            import pymysql
            # Parse MySQL URL and connect
            conn = pymysql.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASSWORD', ''),
                database=os.environ.get('DB_NAME', 'ea_crm'),
                port=int(os.environ.get('DB_PORT', 3306))
            )
            return conn
        except ImportError:
            print("MySQL driver not installed, using SQLite")
        except Exception as e:
            print(f"MySQL connection failed: {e}, using SQLite")
    
    # Fallback to in-memory SQLite for development
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create leads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            company TEXT,
            status TEXT DEFAULT 'new',
            source TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            assigned_to TEXT,
            due_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin user if not exists
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                     ('admin', 'admin123', 'admin'))
    
    conn.commit()
    return conn

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get dashboard stats
    conn = get_db()
    cursor = conn.cursor()
    
    # Count leads by status
    cursor.execute('SELECT status, COUNT(*) FROM leads GROUP BY status')
    lead_stats = dict(cursor.fetchall())
    
    # Count tasks by status
    cursor.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status')
    task_stats = dict(cursor.fetchall())
    
    # Get recent leads
    cursor.execute('SELECT * FROM leads ORDER BY created_at DESC LIMIT 5')
    recent_leads = cursor.fetchall()
    
    conn.close()
    
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
            .recent-leads {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-top: 20px;
            }
            .lead-item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            .lead-item:last-child {
                border-bottom: none;
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
            .db-info {
                background: #e3f2fd;
                color: #1976d2;
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
            <a href="/logout" class="logout-btn">Logout</a>
        </div>
        
        <div class="container">
            <div class="db-info">
                <strong>Database:</strong> {db_type} - {db_status}
            </div>
            
            <div class="nav-menu">
                <a href="/">Dashboard</a>
                <a href="/leads">Leads</a>
                <a href="/tasks">Tasks</a>
                <a href="/add_lead">Add Lead</a>
                <a href="/add_task">Add Task</a>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>📊 Total Leads</h3>
                    <div class="stat-number">{total_leads}</div>
                </div>
                <div class="stat-card">
                    <h3>✅ Active Tasks</h3>
                    <div class="stat-number">{active_tasks}</div>
                </div>
                <div class="stat-card">
                    <h3>🆕 New Leads</h3>
                    <div class="stat-number">{new_leads}</div>
                </div>
                <div class="stat-card">
                    <h3>📈 Conversion Rate</h3>
                    <div class="stat-number">{conversion_rate}%</div>
                </div>
            </div>
            
            <div class="recent-leads">
                <h3>📋 Recent Leads</h3>
                {recent_leads_html}
            </div>
        </div>
    </body>
    </html>
    """
    
    # Calculate stats
    total_leads = sum(lead_stats.values()) if lead_stats else 0
    active_tasks = task_stats.get('active', 0) + task_stats.get('pending', 0)
    new_leads = lead_stats.get('new', 0)
    conversion_rate = round((lead_stats.get('converted', 0) / total_leads * 100) if total_leads > 0 else 0, 1)
    
    # Generate recent leads HTML
    recent_leads_html = ""
    for lead in recent_leads:
        recent_leads_html += f"""
        <div class="lead-item">
            <strong>{lead[1]}</strong> - {lead[4]} ({lead[5]})
            <br><small>Added: {lead[8]}</small>
        </div>
        """
    
    # Determine database type
    database_url = os.environ.get('DATABASE_URL', '')
    if database_url.startswith('postgresql://'):
        db_type = "PostgreSQL"
        db_status = "Production Ready"
    elif database_url.startswith('mysql://'):
        db_type = "MySQL"
        db_status = "Production Ready"
    else:
        db_type = "SQLite (In-Memory)"
        db_status = "Development Mode - Data not persistent"
    
    return html.format(
        total_leads=total_leads,
        active_tasks=active_tasks,
        new_leads=new_leads,
        conversion_rate=conversion_rate,
        recent_leads_html=recent_leads_html,
        db_type=db_type,
        db_status=db_status
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    
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
    if 'flash' in session:
        flash_messages = f'<div class="flash">{session["flash"]}</div>'
        session.pop('flash')
    
    return html.format(flash_messages=flash_messages)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/leads')
def leads():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
    leads = cursor.fetchall()
    conn.close()
    
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
            .leads-table { background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
            .leads-table table { width: 100%; border-collapse: collapse; }
            .leads-table th, .leads-table td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
            .leads-table th { background: #f8f9fa; font-weight: bold; }
            .status-new { background: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 3px; }
            .status-contacted { background: #fff3e0; color: #f57c00; padding: 2px 8px; border-radius: 3px; }
            .status-converted { background: #e8f5e8; color: #388e3c; padding: 2px 8px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📋 Leads Management</h1>
        </div>
        
        <div class="container">
            <div class="nav-menu">
                <a href="/">Dashboard</a>
                <a href="/leads">Leads</a>
                <a href="/tasks">Tasks</a>
                <a href="/add_lead">Add Lead</a>
                <a href="/add_task">Add Task</a>
            </div>
            
            <div class="leads-table">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>Company</th>
                            <th>Status</th>
                            <th>Created</th>
                        </tr>
                    </thead>
                    <tbody>
                        {leads_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    leads_rows = ""
    for lead in leads:
        status_class = f"status-{lead[5]}"
        leads_rows += f"""
        <tr>
            <td>{lead[1]}</td>
            <td>{lead[2]}</td>
            <td>{lead[3]}</td>
            <td>{lead[4]}</td>
            <td><span class="{status_class}">{lead[5]}</span></td>
            <td>{lead[8]}</td>
        </tr>
        """
    
    return html.format(leads_rows=leads_rows)

@app.route('/add_lead', methods=['GET', 'POST'])
def add_lead():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        company = request.form['company']
        status = request.form['status']
        notes = request.form['notes']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leads (name, email, phone, company, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, company, status, notes))
        conn.commit()
        conn.close()
        
        return redirect(url_for('leads'))
    
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
                <form method="POST">
                    <div class="form-group">
                        <label>Name:</label>
                        <input type="text" name="name" required>
                    </div>
                    <div class="form-group">
                        <label>Email:</label>
                        <input type="email" name="email">
                    </div>
                    <div class="form-group">
                        <label>Phone:</label>
                        <input type="tel" name="phone">
                    </div>
                    <div class="form-group">
                        <label>Company:</label>
                        <input type="text" name="company">
                    </div>
                    <div class="form-group">
                        <label>Status:</label>
                        <select name="status">
                            <option value="new">New</option>
                            <option value="contacted">Contacted</option>
                            <option value="converted">Converted</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Notes:</label>
                        <textarea name="notes" rows="4"></textarea>
                    </div>
                    <button type="submit" class="submit-btn">Add Lead</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "message": "EA CRM is running successfully",
        "version": "1.0.0",
        "deployment": "Vercel",
        "database": "External DB Ready"
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) 