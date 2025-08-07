#!/usr/bin/env python3
"""
Deployment script for EA CRM application
Handles database migrations and application setup
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
        logging.FileHandler('deploy.log'),
        logging.StreamHandler()
    ]
)

class Deployer:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.instance_dir = os.path.join(self.base_dir, 'instance')
        self.migrations_dir = os.path.join(self.base_dir, 'migrations')
        
    def backup_database(self):
        """Backup existing database before migration"""
        try:
            if os.path.exists(os.path.join(self.instance_dir, 'leads.db')):
                backup_name = f"leads_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                backup_path = os.path.join(self.instance_dir, backup_name)
                shutil.copy2(
                    os.path.join(self.instance_dir, 'leads.db'),
                    backup_path
                )
                logging.info(f"Database backed up to: {backup_path}")
                return backup_path
        except Exception as e:
            logging.error(f"Failed to backup database: {e}")
            return None
    
    def run_migrations(self):
        """Run database migrations"""
        try:
            # Ensure migrations directory exists
            if not os.path.exists(self.migrations_dir):
                logging.warning("Migrations directory not found")
                return False
            
            # Get all migration files
            migration_files = []
            for file in os.listdir(self.migrations_dir):
                if file.endswith('.py') and file != '__init__.py':
                    migration_files.append(file)
            
            migration_files.sort()  # Sort to ensure proper order
            
            logging.info(f"Found {len(migration_files)} migration files")
            
            # Run each migration
            for migration_file in migration_files:
                migration_path = os.path.join(self.migrations_dir, migration_file)
                logging.info(f"Running migration: {migration_file}")
                
                try:
                    # Import and run migration
                    sys.path.insert(0, self.migrations_dir)
                    module_name = migration_file[:-3]  # Remove .py
                    migration_module = __import__(module_name)
                    
                    if hasattr(migration_module, 'upgrade'):
                        migration_module.upgrade()
                        logging.info(f"Successfully ran migration: {migration_file}")
                    else:
                        logging.warning(f"Migration {migration_file} has no upgrade function")
                        
                except Exception as e:
                    logging.error(f"Failed to run migration {migration_file}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to run migrations: {e}")
            return False
    
    def setup_environment(self):
        """Setup environment variables and configuration"""
        try:
            # Create instance directory if it doesn't exist
            os.makedirs(self.instance_dir, exist_ok=True)
            
            # Set environment variables for production
            os.environ['FLASK_ENV'] = 'production'
            os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
            
            logging.info("Environment setup completed")
            return True
            
        except Exception as e:
            logging.error(f"Failed to setup environment: {e}")
            return False
    
    def install_dependencies(self):
        """Install Python dependencies"""
        try:
            requirements_file = os.path.join(self.base_dir, 'requirements.txt')
            if os.path.exists(requirements_file):
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', requirements_file
                ], check=True)
                logging.info("Dependencies installed successfully")
                return True
            else:
                logging.warning("requirements.txt not found")
                return False
                
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install dependencies: {e}")
            return False
    
    def test_application(self):
        """Test if the application can start"""
        try:
            # Import the application
            sys.path.insert(0, self.base_dir)
            from app import create_app
            
            app = create_app()
            with app.app_context():
                # Test database connection
                from app import db
                db.engine.execute('SELECT 1')
                logging.info("Application test passed")
                return True
                
        except Exception as e:
            logging.error(f"Application test failed: {e}")
            return False
    
    def deploy(self):
        """Main deployment process"""
        logging.info("Starting deployment process...")
        
        # Step 1: Setup environment
        if not self.setup_environment():
            logging.error("Environment setup failed")
            return False
        
        # Step 2: Backup database
        backup_path = self.backup_database()
        
        # Step 3: Install dependencies
        if not self.install_dependencies():
            logging.error("Dependency installation failed")
            return False
        
        # Step 4: Run migrations
        if not self.run_migrations():
            logging.error("Database migrations failed")
            return False
        
        # Step 5: Test application
        if not self.test_application():
            logging.error("Application test failed")
            return False
        
        logging.info("Deployment completed successfully!")
        return True

def main():
    """Main entry point"""
    deployer = Deployer()
    success = deployer.deploy()
    
    if success:
        print("✅ Deployment completed successfully!")
        sys.exit(0)
    else:
        print("❌ Deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 