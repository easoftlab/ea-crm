import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from flask_socketio import SocketIO
import threading
import subprocess
import time

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
socketio = SocketIO()

load_dotenv()

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

def start_auto_retrain():
    def retrain_loop():
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        while True:
            try:
                print('[AutoRetrain] Running lead scoring retraining...')
                subprocess.run(['python', os.path.join(base_dir, 'tests', 'retrain_lead_scoring.py')])
                print('[AutoRetrain] Running intent detection retraining...')
                subprocess.run(['python', os.path.join(base_dir, 'tests', 'retrain_intent_detection.py')])
                print('[AutoRetrain] Running deduplication retraining...')
                subprocess.run(['python', os.path.join(base_dir, 'tests', 'retrain_deduplication.py')])
                print('[AutoRetrain] Running AI messaging retraining...')
                subprocess.run(['python', os.path.join(base_dir, 'tests', 'retrain_ai_messaging.py')])
                # Ensure retrain scripts are referenced from the correct absolute path
            except Exception as e:
                print(f'[AutoRetrain] Error: {e}')
            time.sleep(60 * 60 * 24)  # 24 hours
    t = threading.Thread(target=retrain_loop, daemon=True)
    t.start()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)  # Initialize login manager first
    csrf.init_app(app)  # Re-enable CSRF protection
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    # Ensure session is configured properly for CSRF
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_PATH'] = '/'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # Register blueprints
    from . import routes
    from . import auth
    from . import production
    from . import marketing
    from . import productions
    app.register_blueprint(routes.bp)
    app.register_blueprint(auth.auth, url_prefix='/auth')
    app.register_blueprint(production.production, url_prefix='/production')
    app.register_blueprint(marketing.marketing, url_prefix='/marketing')
    app.register_blueprint(productions.productions, url_prefix='/productions')
    
    # Import SocketIO events
    from . import socketio_events
    
    # Exempt specific API endpoints from CSRF protection
    csrf.exempt(app.view_functions.get('main.api_check_duplicates'))
    
    # Exempt all API endpoints from CSRF protection
    for endpoint in app.view_functions:
        if endpoint.startswith('main.api_') or endpoint.startswith('production.api_'):
            csrf.exempt(app.view_functions.get(endpoint))
    
    # Exempt AJAX endpoints from CSRF protection
    ajax_endpoints = [
        'main.ajax_search_leads',
        'main.ajax_search_converted',
        'main.update_lead',
        'main.delete_lead',
        'main.edit_lead',
        'main.get_lead'
    ]
    for endpoint in ajax_endpoints:
        if endpoint in app.view_functions:
            csrf.exempt(app.view_functions.get(endpoint))
    
    # Exempt auth endpoints from CSRF protection
    auth_endpoints = [
        'auth.login',
        'auth.register',
        'auth.logout'
    ]
    for endpoint in auth_endpoints:
        if endpoint in app.view_functions:
            csrf.exempt(app.view_functions.get(endpoint))
    
    # Temporarily disable CSRF for all endpoints to test
    print("⚠️  CSRF protection temporarily disabled for testing")
    # Disable CSRF for all endpoints by exempting them individually
    for endpoint in app.view_functions:
        try:
            csrf.exempt(app.view_functions.get(endpoint))
        except:
            pass  # Skip if endpoint doesn't exist
    
    # Exempt production API endpoints from CSRF protection
    production_api_endpoints = [
        'production.api_messenger_status',
        'production.api_messenger_online_users',
        'production.api_messenger_messages',
        'production.api_messenger_send_message',
        'production.api_messenger_react_to_message',
        'production.api_messenger_pin_message',
        'production.api_messenger_delete_message',
        'production.api_messenger_upload_file',
        'production.api_messenger_search',
        'production.api_messenger_pinned_messages',
        'production.api_messenger_typing'
    ]
    for endpoint in production_api_endpoints:
        if endpoint in app.view_functions:
            csrf.exempt(app.view_functions.get(endpoint))
    
    import os
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        pass
        # start_auto_retrain()  # Temporarily disabled due to missing files
    return app 