#!/usr/bin/env python3
"""
Post-Deployment Setup Script for EA CRM
This script runs on the server after deployment to set up the application
"""

import os
import sys
import subprocess
import sqlite3
import shutil
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('post_deploy.log'),
        logging.StreamHandler()
    ]
)

class PostDeploySetup:
    def __init__(self):
        self.base_dir = os.getcwd()
        self.instance_dir = os.path.join(self.base_dir, 'instance')
        self.scripts_dir = os.path.join(self.base_dir, 'scripts')
        
    def setup_directories(self):
        """Create necessary directories"""
        try:
            directories = [
                self.instance_dir,
                os.path.join(self.base_dir, 'logs'),
                os.path.join(self.base_dir, 'backups'),
                os.path.join(self.base_dir, 'app', 'static', 'uploads'),
                os.path.join(self.base_dir, 'app', 'static', 'uploads', 'profiles'),
                os.path.join(self.base_dir, 'app', 'static', 'uploads', 'chat'),
                os.path.join(self.base_dir, 'app', 'static', 'uploads', 'chat', 'media')
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                logging.info(f"Created directory: {directory}")
            
            return True
        except Exception as e:
            logging.error(f"Failed to create directories: {e}")
            return False
    
    def setup_environment(self):
        """Setup environment variables"""
        try:
            # Create .env file if it doesn't exist
            env_file = os.path.join(self.base_dir, '.env')
            if not os.path.exists(env_file):
                import secrets
                secret_key = secrets.token_hex(32)
                
                env_content = f"""# EA CRM Environment Configuration
SECRET_KEY={secret_key}
FLASK_ENV=production
FLASK_APP=wsgi.py
DATABASE_URL=sqlite:///instance/leads.db
REDIS_URL=redis://localhost:6379/0
"""
                
                with open(env_file, 'w') as f:
                    f.write(env_content)
                
                logging.info("Created .env file with production settings")
            
            return True
        except Exception as e:
            logging.error(f"Failed to setup environment: {e}")
            return False
    
    def setup_database(self):
        """Initialize database and create tables"""
        try:
            # Import app and create database
            sys.path.insert(0, self.base_dir)
            from app import create_app, db
            from app.models import User, Role
            
            app = create_app()
            
            with app.app_context():
                # Create all tables
                db.create_all()
                logging.info("Database tables created successfully")
                
                # Check if admin user exists
                admin_user = User.query.filter_by(username='admin').first()
                if not admin_user:
                    # Create admin user
                    admin_user = User(
                        username='admin',
                        email='admin@example.com',
                        role_id=1  # Assuming admin role ID is 1
                    )
                    admin_user.set_password('admin123')
                    db.session.add(admin_user)
                    db.session.commit()
                    logging.info("Created admin user: admin/admin123")
                
                # Check if roles exist
                roles = Role.query.all()
                if not roles:
                    # Create default roles
                    default_roles = [
                        {'name': 'Admin', 'description': 'Full system administrator'},
                        {'name': 'Manager', 'description': 'Team manager'},
                        {'name': 'User', 'description': 'Standard user'},
                        {'name': 'Caller', 'description': 'Lead caller'}
                    ]
                    
                    for role_data in default_roles:
                        role = Role(**role_data)
                        db.session.add(role)
                    
                    db.session.commit()
                    logging.info("Created default roles")
            
            return True
        except Exception as e:
            logging.error(f"Failed to setup database: {e}")
            return False
    
    def setup_permissions(self):
        """Set proper file permissions"""
        try:
            # Set directory permissions
            subprocess.run(['chmod', '-R', '755', self.base_dir], check=True)
            
            # Set file permissions
            subprocess.run(['find', self.base_dir, '-type', 'f', '-exec', 'chmod', '644', '{}', ';'], check=True)
            
            # Set executable permissions for scripts
            subprocess.run(['chmod', '+x', os.path.join(self.scripts_dir, '*.py')], check=True)
            
            logging.info("File permissions set successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to set permissions: {e}")
            return False
    
    def test_application(self):
        """Test if the application can start"""
        try:
            # Test database connection
            db_path = os.path.join(self.instance_dir, 'leads.db')
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                logging.info(f"Database test successful. Found {len(tables)} tables")
            
            # Test Flask app import
            sys.path.insert(0, self.base_dir)
            from app import create_app
            app = create_app()
            logging.info("Flask application test successful")
            
            return True
        except Exception as e:
            logging.error(f"Application test failed: {e}")
            return False
    
    def create_deployment_marker(self):
        """Create a marker file to indicate successful deployment"""
        try:
            marker_file = os.path.join(self.base_dir, 'deployment_success.txt')
            with open(marker_file, 'w') as f:
                f.write(f"Deployment completed successfully at {datetime.now()}\n")
                f.write(f"Application is ready for use\n")
            
            logging.info("Deployment marker created")
            return True
        except Exception as e:
            logging.error(f"Failed to create deployment marker: {e}")
            return False
    
    def run_setup(self):
        """Run the complete post-deployment setup"""
        logging.info("Starting post-deployment setup...")
        
        steps = [
            ("Setting up directories", self.setup_directories),
            ("Setting up environment", self.setup_environment),
            ("Setting up database", self.setup_database),
            ("Setting up permissions", self.setup_permissions),
            ("Testing application", self.test_application),
            ("Creating deployment marker", self.create_deployment_marker)
        ]
        
        for step_name, step_func in steps:
            logging.info(f"Running: {step_name}")
            if not step_func():
                logging.error(f"Failed at step: {step_name}")
                return False
        
        logging.info("Post-deployment setup completed successfully!")
        return True

def main():
    """Main function to run the post-deployment setup"""
    setup = PostDeploySetup()
    
    if setup.run_setup():
        print("✅ Post-deployment setup completed successfully!")
        print("🚀 Your EA CRM application is now ready!")
        print("📊 Check the logs for any issues")
        return 0
    else:
        print("❌ Post-deployment setup failed!")
        print("📋 Check the logs for details")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 