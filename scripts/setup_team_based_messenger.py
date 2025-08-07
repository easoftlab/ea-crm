#!/usr/bin/env python3
"""
Setup Team-Based Messenger Script
This script creates teams and assigns users to them for team-based messenger access.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Role, Team, UserTeam
from werkzeug.security import generate_password_hash

app = create_app()

def create_teams():
    """Create the teams for the organization."""
    
    with app.app_context():
        print("Creating teams...")
        
        # Create teams
        teams_data = [
            {
                'name': 'Marketing Team',
                'description': 'Lead generation and calling team',
                'manager_username': 'marketing_manager'
            },
            {
                'name': 'Production Team', 
                'description': 'Production and development team',
                'manager_username': 'production_manager'
            },
            {
                'name': 'Admin Team',
                'description': 'System administrators and managers',
                'manager_username': 'admin'
            }
        ]
        
        # Create teams
        for team_data in teams_data:
            team = Team.query.filter_by(name=team_data['name']).first()
            if not team:
                team = Team(
                    name=team_data['name'],
                    description=team_data['description']
                )
                db.session.add(team)
                print(f"Created team: {team_data['name']}")
        
        db.session.commit()
        print("Teams created successfully!")

def create_team_managers():
    """Create team manager users."""
    
    with app.app_context():
        print("Creating team managers...")
        
        # Create Marketing Manager
        marketing_manager = User.query.filter_by(username='marketing_manager').first()
        if not marketing_manager:
            marketing_manager = User(
                username='marketing_manager',
                email='marketing.manager@example.com',
                first_name='Marketing',
                last_name='Manager',
                role_id=Role.query.filter_by(name='Messenger Moderator').first().id,
                is_active=True,
                is_approved=True
            )
            marketing_manager.set_password('manager123')
            db.session.add(marketing_manager)
            print("Created Marketing Manager user")
        
        # Create Production Manager
        production_manager = User.query.filter_by(username='production_manager').first()
        if not production_manager:
            production_manager = User(
                username='production_manager',
                email='production.manager@example.com',
                first_name='Production',
                last_name='Manager',
                role_id=Role.query.filter_by(name='Messenger Moderator').first().id,
                is_active=True,
                is_approved=True
            )
            production_manager.set_password('manager123')
            db.session.add(production_manager)
            print("Created Production Manager user")
        
        db.session.commit()
        print("Team managers created!")

def assign_users_to_teams():
    """Assign users to their respective teams."""
    
    with app.app_context():
        print("Assigning users to teams...")
        
        # Get teams
        marketing_team = Team.query.filter_by(name='Marketing Team').first()
        production_team = Team.query.filter_by(name='Production Team').first()
        admin_team = Team.query.filter_by(name='Admin Team').first()
        
        if not marketing_team or not production_team or not admin_team:
            print("ERROR: Teams not found! Please run create_teams() first.")
            return
        
        # Assign users to teams
        team_assignments = [
            # Marketing Team
            ('leadgen', marketing_team.id, 'member'),
            ('caller', marketing_team.id, 'member'),
            ('test_caller', marketing_team.id, 'member'),
            ('yeasin.ea', marketing_team.id, 'member'),
            ('marketing_manager', marketing_team.id, 'manager'),
            
            # Production Team
            ('production_user', production_team.id, 'member'),
            ('production_manager', production_team.id, 'manager'),
            
            # Admin Team
            ('emon', admin_team.id, 'manager'),
            ('admin', admin_team.id, 'manager'),
            ('test_admin', admin_team.id, 'manager'),
            ('lead_generator', admin_team.id, 'manager'),
            ('messenger_admin', admin_team.id, 'manager'),
            ('messenger_mod', admin_team.id, 'member'),
            ('messenger_user', admin_team.id, 'member'),
            ('messenger_readonly', admin_team.id, 'member'),
        ]
        
        for username, team_id, role in team_assignments:
            user = User.query.filter_by(username=username).first()
            if user:
                # Check if user is already assigned to this team
                existing = UserTeam.query.filter_by(user_id=user.id, team_id=team_id).first()
                if not existing:
                    user_team = UserTeam(
                        user_id=user.id,
                        team_id=team_id,
                        role=role
                    )
                    db.session.add(user_team)
                    print(f"Assigned {username} to team {team_id} as {role}")
                else:
                    print(f"User {username} already assigned to team {team_id}")
            else:
                print(f"WARNING: User {username} not found!")
        
        db.session.commit()
        print("Team assignments completed!")

def update_team_managers():
    """Update team manager references."""
    
    with app.app_context():
        print("Updating team managers...")
        
        # Update Marketing Team manager
        marketing_team = Team.query.filter_by(name='Marketing Team').first()
        marketing_manager = User.query.filter_by(username='marketing_manager').first()
        if marketing_team and marketing_manager:
            marketing_team.manager_id = marketing_manager.id
            print("Updated Marketing Team manager")
        
        # Update Production Team manager
        production_team = Team.query.filter_by(name='Production Team').first()
        production_manager = User.query.filter_by(username='production_manager').first()
        if production_team and production_manager:
            production_team.manager_id = production_manager.id
            print("Updated Production Team manager")
        
        # Update Admin Team manager
        admin_team = Team.query.filter_by(name='Admin Team').first()
        admin_user = User.query.filter_by(username='admin').first()
        if admin_team and admin_user:
            admin_team.manager_id = admin_user.id
            print("Updated Admin Team manager")
        
        db.session.commit()
        print("Team managers updated!")

def show_team_summary():
    """Show a summary of all teams and their members."""
    
    with app.app_context():
        print("\n" + "="*80)
        print("TEAM SUMMARY")
        print("="*80)
        
        teams = Team.query.all()
        
        for team in teams:
            print(f"\n📋 Team: {team.name}")
            print(f"   Description: {team.description}")
            print(f"   Manager: {team.manager.get_full_name() if team.manager else 'None'}")
            print(f"   Member Count: {team.get_member_count()}")
            
            # Show members
            active_members = [m for m in team.members if m.is_active]
            if active_members:
                print("   Members:")
                for member in active_members:
                    role_icon = "👑" if member.role == 'manager' else "👤"
                    print(f"     {role_icon} {member.user.get_full_name()} ({member.user.username}) - {member.role}")
            else:
                print("   No active members")
        
        print("\n" + "="*80)

def run_setup():
    """Run the complete team-based messenger setup."""
    
    print("Setting up Team-Based Messenger System...")
    print("="*60)
    
    # Step 1: Create teams
    print("\n1. Creating teams...")
    create_teams()
    
    # Step 2: Create team managers
    print("\n2. Creating team managers...")
    create_team_managers()
    
    # Step 3: Assign users to teams
    print("\n3. Assigning users to teams...")
    assign_users_to_teams()
    
    # Step 4: Update team managers
    print("\n4. Updating team managers...")
    update_team_managers()
    
    # Step 5: Show summary
    print("\n5. Team summary...")
    show_team_summary()
    
    print("\n" + "="*60)
    print("Team-Based Messenger Setup Complete!")
    print("="*60)
    
    print("\nNext steps:")
    print("1. Run the migration: flask db upgrade")
    print("2. Update the messenger routes in app/production.py")
    print("3. Update the frontend JavaScript files")
    print("4. Test the team-based access")

if __name__ == '__main__':
    run_setup() 