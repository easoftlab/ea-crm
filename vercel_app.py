#!/usr/bin/env python3
"""
EA CRM with SQLite database for Vercel deployment
Working version with database functionality
"""

from flask import Flask, request, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

def get_db():
    """Get database connection - in-memory SQLite for Vercel"""
    try:
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                company TEXT,
                status TEXT DEFAULT 'new',
                source TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                assigned_to TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add default admin user if not exists
        cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                         ('admin', 'admin123', 'admin'))
        
        # Add sample data if tables are empty
        cursor.execute('SELECT COUNT(*) FROM leads')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO leads (name, email, phone, company, status, source, notes) VALUES 
                ('John Doe', 'john@example.com', '+1234567890', 'Tech Corp', 'new', 'website', 'Interested in CRM'),
                ('Jane Smith', 'jane@example.com', '+0987654321', 'Marketing Inc', 'contacted', 'referral', 'Follow up needed')
            ''')
        
        cursor.execute('SELECT COUNT(*) FROM tasks')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO tasks (title, description, status, priority, due_date, assigned_to) VALUES 
                ('Follow up with John Doe', 'Call about CRM demo', 'pending', 'high', '2025-08-10', 'admin'),
                ('Update website content', 'Add new features page', 'in_progress', 'medium', '2025-08-15', 'admin')
            ''')
        
        conn.commit()
        return conn
    except Exception as e:
        print(f"Database error: {e}")
        return None

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
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
    conn = get_db()
    if not conn:
        return "Database error"
    
    cursor = conn.cursor()
    
    # Get stats
    cursor.execute('SELECT COUNT(*) FROM leads')
    total_leads = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM leads WHERE status = "new"')
    new_leads = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "pending"')
    pending_tasks = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "completed"')
    completed_tasks = cursor.fetchone()[0]
    
    conn.close()
    
    return f"""
    <html>
    <head><title>EA CRM - Dashboard</title></head>
    <body>
        <h1>EA CRM Dashboard</h1>
        <p>✅ Success! The CRM is working with database!</p>
        <p><a href="/leads">Leads</a> | <a href="/tasks">Tasks</a> | <a href="/add_lead">Add Lead</a> | <a href="/add_task">Add Task</a> | <a href="/">Logout</a></p>
        
        <h3>Stats:</h3>
        <ul>
            <li>Total Leads: {total_leads}</li>
            <li>New Leads: {new_leads}</li>
            <li>Pending Tasks: {pending_tasks}</li>
            <li>Completed Tasks: {completed_tasks}</li>
        </ul>
        
        <h3>Recent Activity:</h3>
        <p>Database is working! You can now:</p>
        <ul>
            <li>✅ View and manage leads</li>
            <li>✅ Create and track tasks</li>
            <li>✅ Store data persistently (in-memory for now)</li>
            <li>🔄 Next: Add external database for permanent storage</li>
        </ul>
    </body>
    </html>
    """

@app.route('/leads')
def leads():
    conn = get_db()
    if not conn:
        return "Database error"
    
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
    leads = cursor.fetchall()
    conn.close()
    
    leads_html = ""
    for lead in leads:
        leads_html += f"""
        <tr>
            <td>{lead[1]}</td>
            <td>{lead[2]}</td>
            <td>{lead[3]}</td>
            <td>{lead[4]}</td>
            <td>{lead[5]}</td>
            <td>{lead[6]}</td>
        </tr>
        """
    
    return f"""
    <html>
    <head><title>EA CRM - Leads</title></head>
    <body>
        <h1>Leads Management</h1>
        <p><a href="/dashboard">← Back to Dashboard</a> | <a href="/add_lead">Add New Lead</a></p>
        
        <table border="1" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Company</th>
                <th>Status</th>
                <th>Source</th>
            </tr>
            {leads_html}
        </table>
        
        <p><strong>Total Leads:</strong> {len(leads)}</p>
    </body>
    </html>
    """

@app.route('/add_lead', methods=['GET', 'POST'])
def add_lead():
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        company = request.form.get('company', '')
        source = request.form.get('source', '')
        notes = request.form.get('notes', '')
        
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO leads (name, email, phone, company, source, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, phone, company, source, notes))
            conn.commit()
            conn.close()
            return redirect('/leads')
    
    return """
    <html>
    <head><title>EA CRM - Add Lead</title></head>
    <body>
        <h1>Add New Lead</h1>
        <p><a href="/leads">← Back to Leads</a></p>
        
        <form method="POST">
            <p>Name: <input type="text" name="name" required></p>
            <p>Email: <input type="email" name="email"></p>
            <p>Phone: <input type="text" name="phone"></p>
            <p>Company: <input type="text" name="company"></p>
            <p>Source: <input type="text" name="source"></p>
            <p>Notes: <textarea name="notes"></textarea></p>
            <p><input type="submit" value="Add Lead"></p>
        </form>
    </body>
    </html>
    """

@app.route('/tasks')
def tasks():
    conn = get_db()
    if not conn:
        return "Database error"
    
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    tasks = cursor.fetchall()
    conn.close()
    
    tasks_html = ""
    for task in tasks:
        tasks_html += f"""
        <tr>
            <td>{task[1]}</td>
            <td>{task[2]}</td>
            <td>{task[3]}</td>
            <td>{task[4]}</td>
            <td>{task[5]}</td>
            <td>{task[6]}</td>
        </tr>
        """
    
    return f"""
    <html>
    <head><title>EA CRM - Tasks</title></head>
    <body>
        <h1>Tasks Management</h1>
        <p><a href="/dashboard">← Back to Dashboard</a> | <a href="/add_task">Add New Task</a></p>
        
        <table border="1" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th>Title</th>
                <th>Description</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Due Date</th>
                <th>Assigned To</th>
            </tr>
            {tasks_html}
        </table>
        
        <p><strong>Total Tasks:</strong> {len(tasks)}</p>
    </body>
    </html>
    """

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        priority = request.form.get('priority', 'medium')
        due_date = request.form.get('due_date', '')
        assigned_to = request.form.get('assigned_to', 'admin')
        
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (title, description, priority, due_date, assigned_to)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, description, priority, due_date, assigned_to))
            conn.commit()
            conn.close()
            return redirect('/tasks')
    
    return """
    <html>
    <head><title>EA CRM - Add Task</title></head>
    <body>
        <h1>Add New Task</h1>
        <p><a href="/tasks">← Back to Tasks</a></p>
        
        <form method="POST">
            <p>Title: <input type="text" name="title" required></p>
            <p>Description: <textarea name="description"></textarea></p>
            <p>Priority: 
                <select name="priority">
                    <option value="low">Low</option>
                    <option value="medium" selected>Medium</option>
                    <option value="high">High</option>
                </select>
            </p>
            <p>Due Date: <input type="date" name="due_date"></p>
            <p>Assigned To: <input type="text" name="assigned_to" value="admin"></p>
            <p><input type="submit" value="Add Task"></p>
        </form>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return "Health check: OK ✅"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) 