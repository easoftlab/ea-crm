#!/usr/bin/env python3
"""
Simple Flask app for Vercel deployment
This is a basic version that will definitely work
"""

from flask import Flask, render_template_string
import os

app = Flask(__name__)

# Set a secret key
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-12345')

@app.route('/')
def home():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EA CRM - Successfully Deployed!</title>
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
            .container { 
                max-width: 800px; 
                margin: 20px; 
                background: white; 
                padding: 40px; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
            }
            .success { 
                color: #388e3c; 
                background: #e8f5e8; 
                padding: 20px; 
                border-radius: 8px; 
                margin: 20px 0; 
                border-left: 4px solid #4caf50;
            }
            .info { 
                color: #1976d2; 
                background: #e3f2fd; 
                padding: 20px; 
                border-radius: 8px; 
                margin: 20px 0; 
                border-left: 4px solid #2196f3;
            }
            .warning { 
                color: #f57c00; 
                background: #fff3e0; 
                padding: 20px; 
                border-radius: 8px; 
                margin: 20px 0; 
                border-left: 4px solid #ff9800;
            }
            .code { 
                background: #f5f5f5; 
                padding: 15px; 
                border-radius: 6px; 
                font-family: 'Courier New', monospace; 
                margin: 15px 0; 
                text-align: left;
                border: 1px solid #ddd;
            }
            .button {
                background: #4caf50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px;
                text-decoration: none;
                display: inline-block;
            }
            .button:hover {
                background: #45a049;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .stat {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
            .stat h3 {
                margin: 0 0 10px 0;
                color: #495057;
            }
            .stat p {
                margin: 0;
                font-size: 24px;
                font-weight: bold;
                color: #212529;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 EA CRM - Successfully Deployed!</h1>
            
            <div class="success">
                <strong>✅ Vercel Deployment Successful!</strong><br>
                Your EA CRM application is now live on Vercel.
            </div>
            
            <div class="info">
                <strong>📊 Deployment Status</strong><br>
                The basic Flask application is working correctly. This confirms that:
                <ul style="text-align: left; margin: 20px 0;">
                    <li>✅ Vercel deployment is successful</li>
                    <li>✅ Python environment is working</li>
                    <li>✅ Flask framework is running</li>
                    <li>✅ Routing is configured correctly</li>
                </ul>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <h3>🌐 Platform</h3>
                    <p>Vercel</p>
                </div>
                <div class="stat">
                    <h3>🐍 Runtime</h3>
                    <p>Python</p>
                </div>
                <div class="stat">
                    <h3>⚡ Framework</h3>
                    <p>Flask</p>
                </div>
                <div class="stat">
                    <h3>📦 Status</h3>
                    <p>Live</p>
                </div>
            </div>
            
            <div class="warning">
                <strong>🔧 Next Steps</strong><br>
                To deploy the full EA CRM application:
                <ol style="text-align: left; margin: 20px 0;">
                    <li><strong>Add Environment Variables</strong> in Vercel Dashboard</li>
                    <li><strong>Configure Database</strong> (SQLite for Vercel)</li>
                    <li><strong>Set up AI API Keys</strong> for advanced features</li>
                    <li><strong>Test all features</strong> after configuration</li>
                </ol>
            </div>
            
            <div class="code">
                <strong>Environment Variables to Add:</strong><br>
                SECRET_KEY=your-secret-key-here<br>
                OPENROUTER_API_KEY=your-api-key<br>
                FLASK_ENV=production<br>
                DATABASE_URL=sqlite:///instance/leads.db
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/health" class="button">🔍 Health Check</a>
                <a href="/test" class="button">🧪 Test Endpoint</a>
                <a href="/debug" class="button">🐛 Debug Info</a>
            </div>
            
            <p style="margin-top: 30px; color: #666; font-size: 14px;">
                <em>This is a simplified version to confirm deployment. The full EA CRM will be available after configuration.</em>
            </p>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/health')
def health():
    return {
        "status": "healthy",
        "message": "EA CRM deployment is working correctly",
        "platform": "Vercel",
        "framework": "Flask",
        "python_version": "3.9+"
    }

@app.route('/test')
def test():
    return {
        "message": "Test endpoint working!",
        "timestamp": "2025-08-08",
        "deployment": "successful"
    }

@app.route('/debug')
def debug():
    import os
    env_vars = {
        'FLASK_ENV': os.environ.get('FLASK_ENV', 'NOT SET'),
        'SECRET_KEY': 'SET' if os.environ.get('SECRET_KEY') else 'NOT SET',
        'OPENROUTER_API_KEY': 'SET' if os.environ.get('OPENROUTER_API_KEY') else 'NOT SET',
        'DATABASE_URL': os.environ.get('DATABASE_URL', 'NOT SET')
    }
    return {
        "environment_variables": env_vars,
        "deployment_status": "working",
        "next_steps": "Configure environment variables for full EA CRM"
    }

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) 