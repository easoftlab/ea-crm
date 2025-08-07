#!/usr/bin/env python3
"""
Initialize Authentication System for EA CRM
Creates default roles and admin user
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Role

def init_auth():
    app = create_app()
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Create default roles
        roles = {
            'admin': {
                'name': 'Admin',
                'description': 'Full system administrator with all permissions',
                'permissions': 'admin,manage_users,manage_roles,view_reports,manage_leads,manage_scraper'
            },
            'manager': {
                'name': 'Manager',
                'description': 'Team manager with lead management and reporting permissions',
                'permissions': 'view_reports,manage_leads,manage_scraper'
            },
            'user': {
                'name': 'User',
                'description': 'Standard user with basic lead management',
                'permissions': 'view_reports,manage_leads'
            },
            'viewer': {
                'name': 'Viewer',
                'description': 'Read-only access to leads and reports',
                'permissions': 'view_reports'
            }
        }
        
        # Create roles
        for role_key, role_data in roles.items():
            role = Role.query.filter_by(name=role_data['name']).first()
            if not role:
                role = Role(
                    name=role_data['name'],
                    description=role_data['description'],
                    permissions=role_data['permissions']
                )
                db.session.add(role)
                print(f"✅ Created role: {role_data['name']}")
            else:
                print(f"⚠️  Role already exists: {role_data['name']}")
        
        db.session.commit()
        
        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role:
                admin_user = User(
                    username='admin',
                    email='admin@eacrm.com',
                    first_name='System',
                    last_name='Administrator',
                    role_id=admin_role.id,
                    is_active=True
                )
                admin_user.set_password('admin123')  # Change this password!
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Created admin user:")
                print("   Username: admin")
                print("   Password: admin123")
                print("   ⚠️  IMPORTANT: Change this password immediately!")
            else:
                print("❌ Error: Admin role not found!")
        else:
            print("⚠️  Admin user already exists")
        
        print("\n🎉 Authentication system initialized successfully!")
        print("\n📋 Default Roles Created:")
        for role_key, role_data in roles.items():
            print(f"   • {role_data['name']}: {role_data['description']}")
        
        print("\n🔐 Default Admin Account:")
        print("   Username: admin")
        print("   Password: admin123")
        print("   ⚠️  Change this password immediately after first login!")

if __name__ == '__main__':
    init_auth() 