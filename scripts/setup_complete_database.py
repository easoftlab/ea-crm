#!/usr/bin/env python3
"""
Setup Complete Database Script
This script sets up the complete database with all tables including team support.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Role, Team, UserTeam
from werkzeug.security import generate_password_hash

app = create_app()

def setup_complete_database():
    """Set up the complete database with all tables."""
    
    with app.app_context():
        print("Setting up complete database...")
        print("="*50)
        
        # Step 1: Create all tables
        print("1. Creating all database tables...")
        db.create_all()
        print("✅ All tables created successfully!")
        
        # Step 2: Create roles
        print("\n2. Creating roles...")
        roles_data = [
            {
                'name': 'Admin',
                'description': 'Full system administrator with all permissions',
                'permissions': 'admin,add_leads,manage_leads,view_reports,manage_scraper,view_tasks,manage_tasks,upload_files,access_lan_server,messenger_admin,messenger_moderate,messenger_send,messenger_read'
            },
            {
                'name': 'Manager',
                'description': 'Team manager with lead management and reporting permissions',
                'permissions': 'view_reports,manage_leads,manage_scraper,admin,view_tasks,manage_tasks,upload_files,messenger_moderate,messenger_send,messenger_read'
            },
            {
                'name': 'User',
                'description': 'Standard user with basic lead management permissions',
                'permissions': 'add_leads,view_tasks,messenger_send,messenger_read'
            },
            {
                'name': 'Caller',
                'description': 'Caller with lead management permissions',
                'permissions': 'add_leads,view_tasks,messenger_send,messenger_read'
            },
            {
                'name': 'Messenger Admin',
                'description': 'Full messenger control',
                'permissions': 'messenger_admin,messenger_moderate,messenger_send,messenger_read'
            },
            {
                'name': 'Messenger Moderator',
                'description': 'Content moderation',
                'permissions': 'messenger_moderate,messenger_send,messenger_read'
            },
            {
                'name': 'Messenger User',
                'description': 'Standard messaging',
                'permissions': 'messenger_send,messenger_read'
            },
            {
                'name': 'Messenger Read-Only',
                'description': 'Read-only access',
                'permissions': 'messenger_read'
            }
        ]
        
        for role_data in roles_data:
            role = Role.query.filter_by(name=role_data['name']).first()
            if not role:
                role = Role(
                    name=role_data['name'],
                    description=role_data['description'],
                    permissions=role_data['permissions']
                )
                db.session.add(role)
                print(f"  Created role: {role_data['name']}")
            else:
                print(f"  Role already exists: {role_data['name']}")
        
        db.session.commit()
        print("✅ Roles created successfully!")
        
        # Step 3: Create teams
        print("\n3. Creating teams...")
        teams_data = [
            {
                'name': 'Marketing Team',
                'description': 'Lead generation and calling team'
            },
            {
                'name': 'Production Team',
                'description': 'Production and development team'
            },
            {
                'name': 'Admin Team',
                'description': 'System administrators and managers'
            }
        ]
        
        for team_data in teams_data:
            team = Team.query.filter_by(name=team_data['name']).first()
            if not team:
                team = Team(
                    name=team_data['name'],
                    description=team_data['description']
                )
                db.session.add(team)
                print(f"  Created team: {team_data['name']}")
            else:
                print(f"  Team already exists: {team_data['name']}")
        
        db.session.commit()
        print("✅ Teams created successfully!")
        
        # Step 4: Create users
        print("\n4. Creating users...")
        users_data = [
            {
                'username': 'emon',
                'email': 'emon@example.com',
                'first_name': 'Emranul',
                'last_name': 'Hassan',
                'role_name': 'Admin',
                'password': 'admin123'
            },
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'role_name': 'Admin',
                'password': 'admin123'
            },
            {
                'username': 'leadgen',
                'email': 'leadgen@example.com',
                'first_name': 'Lead',
                'last_name': 'Generator',
                'role_name': 'User',
                'password': 'user123'
            },
            {
                'username': 'caller',
                'email': 'caller@example.com',
                'first_name': 'Test',
                'last_name': 'Caller',
                'role_name': 'Caller',
                'password': 'user123'
            },
            {
                'username': 'production_user',
                'email': 'production@example.com',
                'first_name': 'Production',
                'last_name': 'User',
                'role_name': 'User',
                'password': 'user123'
            }
        ]
        
        for user_data in users_data:
            user = User.query.filter_by(username=user_data['username']).first()
            if not user:
                role = Role.query.filter_by(name=user_data['role_name']).first()
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    role_id=role.id if role else None,
                    is_active=True,
                    is_approved=True
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                print(f"  Created user: {user_data['username']}")
            else:
                print(f"  User already exists: {user_data['username']}")
        
        db.session.commit()
        print("✅ Users created successfully!")
        
        # Step 5: Assign users to teams
        print("\n5. Assigning users to teams...")
        team_assignments = [
            ('leadgen', 'Marketing Team', 'member'),
            ('caller', 'Marketing Team', 'member'),
            ('production_user', 'Production Team', 'member'),
            ('emon', 'Admin Team', 'manager'),
            ('admin', 'Admin Team', 'manager')
        ]
        
        for username, team_name, role in team_assignments:
            user = User.query.filter_by(username=username).first()
            team = Team.query.filter_by(name=team_name).first()
            
            if user and team:
                existing = UserTeam.query.filter_by(user_id=user.id, team_id=team.id).first()
                if not existing:
                    user_team = UserTeam(
                        user_id=user.id,
                        team_id=team.id,
                        role=role
                    )
                    db.session.add(user_team)
                    print(f"  Assigned {username} to {team_name} as {role}")
                else:
                    print(f"  {username} already assigned to {team_name}")
            else:
                print(f"  WARNING: User {username} or team {team_name} not found!")
        
        db.session.commit()
        print("✅ Team assignments completed!")
        
        print("\n" + "="*50)
        print("✅ Complete database setup finished!")
        print("\nDatabase Summary:")
        print(f"  - Roles: {Role.query.count()}")
        print(f"  - Teams: {Team.query.count()}")
        print(f"  - Users: {User.query.count()}")
        print(f"  - User-Team Assignments: {UserTeam.query.count()}")

if __name__ == '__main__':
    setup_complete_database() 