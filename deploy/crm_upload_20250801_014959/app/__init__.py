import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_login import LoginManager
import threading
from .scraper.scraper import LinkedInScraper
import subprocess
import time

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()

load_dotenv()

SCRAPER_EMAIL = os.getenv('LINKEDIN_EMAIL')
SCRAPER_PASSWORD = os.getenv('LINKEDIN_PASSWORD')

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

def start_scraper(app):
    def run_scraper():
        scraper = LinkedInScraper(app)
        scraper.scrape()
    t = threading.Thread(target=run_scraper, daemon=True)
    t.start()

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
    app.register_blueprint(routes.bp)
    app.register_blueprint(auth.auth, url_prefix='/auth')
    app.register_blueprint(production.production, url_prefix='/production')
    
    # Exempt specific API endpoints from CSRF protection
    csrf.exempt(app.view_functions.get('main.api_check_duplicates'))
    
    # Exempt all API endpoints from CSRF protection
    for endpoint in app.view_functions:
        if endpoint.startswith('main.api_'):
            csrf.exempt(app.view_functions.get(endpoint))
    
    import os
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        pass
        # start_scraper(app)  # Removed for manual control
        # start_auto_retrain()  # Temporarily disabled due to missing files
    return app 