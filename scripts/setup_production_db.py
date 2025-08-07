#!/usr/bin/env python3
"""
Production Database Setup Script for EA CRM
This script sets up the MySQL database for production deployment
"""

import os
import sys
import mysql.connector
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def setup_mysql_database():
    """Set up MySQL database for production"""
    
    print("🗄️ Setting up MySQL Database for Production...")
    
    # Database configuration
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_NAME = os.environ.get('DB_NAME', 'ea_crm_db')
    DB_USER = os.environ.get('DB_USER', 'ea_crm_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'your_password')
    
    print(f"Database: {DB_NAME}")
    print(f"User: {DB_USER}")
    print(f"Host: {DB_HOST}")
    
    try:
        # Connect to MySQL server
        print("\n📡 Connecting to MySQL server...")
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        print(f"📂 Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print("✅ Database created successfully!")
        
        # Use the database
        cursor.execute(f"USE {DB_NAME}")
        
        # Create tables using SQLAlchemy
        print("\n🏗️ Creating database tables...")
        
        # Add the app directory to Python path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        from app import create_app, db
        from app.models import User, Role, Lead, Call, Task, Projection
        
        app = create_app()
        
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ All tables created successfully!")
            
            # Create default roles
            print("\n👥 Creating default roles...")
            roles = [
                {'name': 'Admin', 'description': 'Full system administrator'},
                {'name': 'Manager', 'description': 'Team manager'},
                {'name': 'User', 'description': 'Standard user'},
                {'name': 'Caller', 'description': 'Lead caller'},
                {'name': 'Lead Generator', 'description': 'Lead generation specialist'},
                {'name': 'Marketing Manager', 'description': 'Marketing and campaigns'},
                {'name': 'Production Manager', 'description': 'Task and project management'}
            ]
            
            for role_data in roles:
                role = Role.query.filter_by(name=role_data['name']).first()
                if not role:
                    role = Role(**role_data)
                    db.session.add(role)
            
            db.session.commit()
            print("✅ Default roles created!")
            
            # Create admin user
            print("\n👤 Creating admin user...")
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_role = Role.query.filter_by(name='Admin').first()
                admin_user = User(
                    username='admin',
                    email='admin@eaincorp.com',
                    role_id=admin_role.id if admin_role else 1
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Admin user created: admin/admin123")
            else:
                print("✅ Admin user already exists")
        
        cursor.close()
        connection.close()
        
        print("\n🎉 Production database setup completed successfully!")
        print("📊 Your EA CRM is ready for production use!")
        
    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        print("\n💡 Make sure to:")
        print("1. Create MySQL database in Hostinger")
        print("2. Set correct database credentials")
        print("3. Install mysql-connector-python: pip install mysql-connector-python")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Check your database configuration")

def setup_sqlite_database():
    """Set up SQLite database for development/testing"""
    
    print("🗄️ Setting up SQLite Database...")
    
    try:
        # Add the app directory to Python path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        from app import create_app, db
        from app.models import User, Role, Lead, Call, Task, Projection
        
        app = create_app()
        
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ All tables created successfully!")
            
            # Create default roles
            print("\n👥 Creating default roles...")
            roles = [
                {'name': 'Admin', 'description': 'Full system administrator'},
                {'name': 'Manager', 'description': 'Team manager'},
                {'name': 'User', 'description': 'Standard user'},
                {'name': 'Caller', 'description': 'Lead caller'},
                {'name': 'Lead Generator', 'description': 'Lead generation specialist'},
                {'name': 'Marketing Manager', 'description': 'Marketing and campaigns'},
                {'name': 'Production Manager', 'description': 'Task and project management'}
            ]
            
            for role_data in roles:
                role = Role.query.filter_by(name=role_data['name']).first()
                if not role:
                    role = Role(**role_data)
                    db.session.add(role)
            
            db.session.commit()
            print("✅ Default roles created!")
            
            # Create admin user
            print("\n👤 Creating admin user...")
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_role = Role.query.filter_by(name='Admin').first()
                admin_user = User(
                    username='admin',
                    email='admin@eaincorp.com',
                    role_id=admin_role.id if admin_role else 1
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Admin user created: admin/admin123")
            else:
                print("✅ Admin user already exists")
        
        print("\n🎉 SQLite database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup EA CRM Database')
    parser.add_argument('--type', choices=['mysql', 'sqlite'], default='sqlite',
                       help='Database type to setup (default: sqlite)')
    
    args = parser.parse_args()
    
    if args.type == 'mysql':
        setup_mysql_database()
    else:
        setup_sqlite_database() 