#!/usr/bin/env python3
"""
EA CRM with Supabase database for Vercel deployment
Production-ready version with external database
"""

from flask import Flask, request, redirect
import os
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)

def get_supabase():
    """Get Supabase client"""
    try:
        url = os.environ.get('SUPABASE_URL')
        key = os.environ.get('SUPABASE_ANON_KEY')
        
        if not url or not key:
            print("Supabase credentials not found, using fallback")
            return None
            
        supabase: Client = create_client(url, key)
        return supabase
    except Exception as e:
        print(f"Supabase connection error: {e}")
        return None

def get_db():
    """Get database connection - Supabase with SQLite fallback"""
    supabase = get_supabase()
    
    if supabase:
        try:
            # Test connection
            result = supabase.table('users').select('*').limit(1).execute()
            return supabase
        except Exception as e:
            print(f"Supabase test failed: {e}")
            return None
    
    # Fallback to in-memory SQLite
    try:
        import sqlite3
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
        
        db = get_db()
        if db:
            if isinstance(db, Client):  # Supabase
                try:
                    result = db.table('users').select('*').eq('username', username).eq('password', password).execute()
                    user = result.data[0] if result.data else None
                    
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
                except Exception as e:
                    print(f"Supabase login error: {e}")
                    return "Database error"
            else:  # SQLite
                cursor = db.cursor()
                cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
                user = cursor.fetchone()
                db.close()
                
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
    db = get_db()
    if not db:
        return "Database error"
    
    if isinstance(db, Client):  # Supabase
        try:
            # Get stats
            leads_result = db.table('leads').select('*').execute()
            total_leads = len(leads_result.data)
            
            new_leads_result = db.table('leads').select('*').eq('status', 'new').execute()
            new_leads = len(new_leads_result.data)
            
            tasks_result = db.table('tasks').select('*').eq('status', 'pending').execute()
            pending_tasks = len(tasks_result.data)
            
            completed_tasks_result = db.table('tasks').select('*').eq('status', 'completed').execute()
            completed_tasks = len(completed_tasks_result.data)
            
        except Exception as e:
            print(f"Supabase dashboard error: {e}")
            total_leads = new_leads = pending_tasks = completed_tasks = 0
    else:  # SQLite
        cursor = db.cursor()
        
        # Get stats
        cursor.execute('SELECT COUNT(*) FROM leads')
        total_leads = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM leads WHERE status = "new"')
        new_leads = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "pending"')
        pending_tasks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "completed"')
        completed_tasks = cursor.fetchone()[0]
        
        db.close()
    
    return f"""
    <html>
    <head><title>EA CRM - Dashboard</title></head>
    <body>
        <h1>EA CRM Dashboard</h1>
        <p>✅ Success! The CRM is working with {'Supabase' if isinstance(db, Client) else 'SQLite'} database!</p>
        <p><a href="/leads">Leads</a> | <a href="/tasks">Tasks</a> | <a href="/add_lead">Add Lead</a> | <a href="/add_task">Add Task</a> | <a href="/">Logout</a></p>
        
        <h3>Stats:</h3>
        <ul>
            <li>Total Leads: {total_leads}</li>
            <li>New Leads: {new_leads}</li>
            <li>Pending Tasks: {pending_tasks}</li>
            <li>Completed Tasks: {completed_tasks}</li>
        </ul>
        
        <h3>Database Status:</h3>
        <p>Currently using: {'Supabase (Production)' if isinstance(db, Client) else 'SQLite (Development)'}</p>
        <ul>
            <li>✅ View and manage leads</li>
            <li>✅ Create and track tasks</li>
            <li>✅ {'Permanent storage with Supabase' if isinstance(db, Client) else 'Temporary storage (in-memory)'}</li>
            <li>🔄 Next: Add more features</li>
        </ul>
    </body>
    </html>
    """

@app.route('/leads')
def leads():
    db = get_db()
    if not db:
        return "Database error"
    
    if isinstance(db, Client):  # Supabase
        try:
            result = db.table('leads').select('*').order('created_at', desc=True).execute()
            leads = result.data
        except Exception as e:
            print(f"Supabase leads error: {e}")
            leads = []
    else:  # SQLite
        cursor = db.cursor()
        cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
        leads = cursor.fetchall()
        db.close()
    
    leads_html = ""
    for lead in leads:
        if isinstance(db, Client):  # Supabase data structure
            leads_html += f"""
            <tr>
                <td>{lead.get('name', '')}</td>
                <td>{lead.get('email', '')}</td>
                <td>{lead.get('phone', '')}</td>
                <td>{lead.get('company', '')}</td>
                <td>{lead.get('status', '')}</td>
                <td>{lead.get('source', '')}</td>
            </tr>
            """
        else:  # SQLite data structure
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
        <p><strong>Database:</strong> {'Supabase' if isinstance(db, Client) else 'SQLite'}</p>
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
        
        db = get_db()
        if db:
            if isinstance(db, Client):  # Supabase
                try:
                    db.table('leads').insert({
                        'name': name,
                        'email': email,
                        'phone': phone,
                        'company': company,
                        'source': source,
                        'notes': notes
                    }).execute()
                    return redirect('/leads')
                except Exception as e:
                    print(f"Supabase add lead error: {e}")
                    return "Database error"
            else:  # SQLite
                cursor = db.cursor()
                cursor.execute('''
                    INSERT INTO leads (name, email, phone, company, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, email, phone, company, source, notes))
                db.commit()
                db.close()
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
    db = get_db()
    if not db:
        return "Database error"
    
    if isinstance(db, Client):  # Supabase
        try:
            result = db.table('tasks').select('*').order('created_at', desc=True).execute()
            tasks = result.data
        except Exception as e:
            print(f"Supabase tasks error: {e}")
            tasks = []
    else:  # SQLite
        cursor = db.cursor()
        cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        tasks = cursor.fetchall()
        db.close()
    
    tasks_html = ""
    for task in tasks:
        if isinstance(db, Client):  # Supabase data structure
            tasks_html += f"""
            <tr>
                <td>{task.get('title', '')}</td>
                <td>{task.get('description', '')}</td>
                <td>{task.get('status', '')}</td>
                <td>{task.get('priority', '')}</td>
                <td>{task.get('due_date', '')}</td>
                <td>{task.get('assigned_to', '')}</td>
            </tr>
            """
        else:  # SQLite data structure
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
        <p><strong>Database:</strong> {'Supabase' if isinstance(db, Client) else 'SQLite'}</p>
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
        
        db = get_db()
        if db:
            if isinstance(db, Client):  # Supabase
                try:
                    db.table('tasks').insert({
                        'title': title,
                        'description': description,
                        'priority': priority,
                        'due_date': due_date,
                        'assigned_to': assigned_to
                    }).execute()
                    return redirect('/tasks')
                except Exception as e:
                    print(f"Supabase add task error: {e}")
                    return "Database error"
            else:  # SQLite
                cursor = db.cursor()
                cursor.execute('''
                    INSERT INTO tasks (title, description, priority, due_date, assigned_to)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, description, priority, due_date, assigned_to))
                db.commit()
                db.close()
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