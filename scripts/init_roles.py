import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Role
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("Database tables created successfully!")
    
    # Create roles if they don't exist
    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role:
        admin_role = Role(
            name='Admin',
            description='Full system administrator with all permissions',
            permissions='admin,add_leads,manage_leads,view_reports,manage_scraper,view_tasks,manage_tasks,upload_files,access_lan_server,messenger_admin,messenger_moderate,messenger_send,messenger_read,manage_marketing_team,manage_productions_team,manage_roles,manage_users,view_client_info'
        )
        db.session.add(admin_role)
        print("Admin role created!")
    else:
        # Update admin role to ensure it has ALL permissions
        admin_role.permissions = 'admin,add_leads,manage_leads,view_reports,manage_scraper,view_tasks,manage_tasks,upload_files,access_lan_server,messenger_admin,messenger_moderate,messenger_send,messenger_read,manage_marketing_team,manage_productions_team,manage_roles,manage_users,view_client_info'
        print("Admin role updated with ALL permissions!")
    
    # Create Manager role
    manager_role = Role.query.filter_by(name='Manager').first()
    if not manager_role:
        manager_role = Role(
            name='Manager',
            description='Team manager with lead management, reporting, and messenger moderation permissions',
            permissions='add_leads,manage_leads,view_reports,admin,view_tasks,manage_tasks,upload_files,messenger_moderate,messenger_send,messenger_read,manage_marketing_team,manage_productions_team'
        )
        db.session.add(manager_role)
        print("Manager role created!")
    else:
        # Update manager role to ensure it has all manager permissions
        manager_role.permissions = 'add_leads,manage_leads,view_reports,admin,view_tasks,manage_tasks,upload_files,messenger_moderate,messenger_send,messenger_read,manage_marketing_team,manage_productions_team'
        print("Manager role updated with all manager permissions!")
    
    # Create Lead Generator role
    lead_generator_role = Role.query.filter_by(name='Lead Generator').first()
    if not lead_generator_role:
        lead_generator_role = Role(
            name='Lead Generator',
            description='Lead generator who can add leads and view personal metrics, but cannot manage existing leads',
            permissions='add_leads,view_tasks,messenger_send,messenger_read'
        )
        db.session.add(lead_generator_role)
        print("Lead Generator role created!")
    else:
        # Update lead generator role to ensure it has correct permissions
        if lead_generator_role.permissions is None or 'add_leads' not in lead_generator_role.permissions:
            lead_generator_role.permissions = 'add_leads,view_tasks,messenger_send,messenger_read'
            print("Lead Generator role updated with correct permissions!")
    
    # Create User role
    user_role = Role.query.filter_by(name='User').first()
    if not user_role:
        user_role = Role(
            name='User',
            description='Standard user with basic lead management and messenger access',
            permissions='add_leads,view_tasks,messenger_send,messenger_read'
        )
        db.session.add(user_role)
        print("User role created!")
    else:
        # Update user role to include messenger permissions
        if user_role.permissions is None or 'view_tasks' not in user_role.permissions:
            user_role.permissions = 'add_leads,view_tasks,messenger_send,messenger_read'
            print("User role updated with messenger permissions!")
    
    # Create Caller role
    caller_role = Role.query.filter_by(name='Caller').first()
    if not caller_role:
        caller_role = Role(
            name='Caller',
            description='Caller who can add leads, view main dashboard, edit leads, update status, followups, notes, and use messenger',
            permissions='add_leads,manage_leads,view_reports,view_tasks,messenger_send,messenger_read'
        )
        db.session.add(caller_role)
        print("Caller role created!")
    else:
        # Update caller role to include messenger permissions
        if caller_role.permissions is None or 'view_tasks' not in caller_role.permissions:
            caller_role.permissions = 'add_leads,manage_leads,view_reports,view_tasks,messenger_send,messenger_read'
            print("Caller role updated with messenger permissions!")
    
    # Create Marketing Manager role
    marketing_manager_role = Role.query.filter_by(name='Marketing Manager').first()
    if not marketing_manager_role:
        marketing_manager_role = Role(
            name='Marketing Manager',
            description='Marketing team manager with lead management, team management, and reporting permissions',
            permissions='add_leads,manage_leads,view_reports,manage_marketing_team,view_tasks,manage_tasks,messenger_send,messenger_read'
        )
        db.session.add(marketing_manager_role)
        print("Marketing Manager role created!")
    else:
        # Update marketing manager role to ensure it has correct permissions
        if marketing_manager_role.permissions is None or 'manage_marketing_team' not in marketing_manager_role.permissions:
            marketing_manager_role.permissions = 'add_leads,manage_leads,view_reports,manage_marketing_team,view_tasks,manage_tasks,messenger_send,messenger_read'
            print("Marketing Manager role updated with correct permissions!")
    
    # Create Productions Manager role
    productions_manager_role = Role.query.filter_by(name='Productions Manager').first()
    if not productions_manager_role:
        productions_manager_role = Role(
            name='Productions Manager',
            description='Productions team manager with task management and team oversight permissions',
            permissions='add_leads,manage_leads,view_reports,manage_productions_team,view_tasks,manage_tasks,messenger_send,messenger_read'
        )
        db.session.add(productions_manager_role)
        print("Productions Manager role created!")
    else:
        # Update productions manager role to ensure it has correct permissions
        if productions_manager_role.permissions is None or 'manage_productions_team' not in productions_manager_role.permissions:
            productions_manager_role.permissions = 'add_leads,manage_leads,view_reports,manage_productions_team,view_tasks,manage_tasks,messenger_send,messenger_read'
            print("Productions Manager role updated with correct permissions!")
    
    # Create new Messenger-specific roles
    
    # Messenger Admin role
    messenger_admin_role = Role.query.filter_by(name='Messenger Admin').first()
    if not messenger_admin_role:
        messenger_admin_role = Role(
            name='Messenger Admin',
            description='Messenger administrator with full control over chat groups, moderation, and user management',
            permissions='view_tasks,messenger_admin,messenger_moderate,messenger_send,messenger_read,manage_tasks'
        )
        db.session.add(messenger_admin_role)
        print("Messenger Admin role created!")
    
    # Messenger Moderator role
    messenger_moderator_role = Role.query.filter_by(name='Messenger Moderator').first()
    if not messenger_moderator_role:
        messenger_moderator_role = Role(
            name='Messenger Moderator',
            description='Messenger moderator who can manage groups, moderate content, and manage users',
            permissions='view_tasks,messenger_moderate,messenger_send,messenger_read'
        )
        db.session.add(messenger_moderator_role)
        print("Messenger Moderator role created!")
    
    # Messenger User role
    messenger_user_role = Role.query.filter_by(name='Messenger User').first()
    if not messenger_user_role:
        messenger_user_role = Role(
            name='Messenger User',
            description='Basic messenger user who can send and read messages',
            permissions='view_tasks,messenger_send,messenger_read'
        )
        db.session.add(messenger_user_role)
        print("Messenger User role created!")
    
    # Messenger Read-Only role
    messenger_readonly_role = Role.query.filter_by(name='Messenger Read-Only').first()
    if not messenger_readonly_role:
        messenger_readonly_role = Role(
            name='Messenger Read-Only',
            description='Read-only messenger user who can only view messages',
            permissions='view_tasks,messenger_read'
        )
        db.session.add(messenger_readonly_role)
        print("Messenger Read-Only role created!")
    
    # Commit changes
    db.session.commit()
    
    # Create admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            role_id=admin_role.id,
            is_active=True,
            is_approved=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        print("Admin user created with username: admin, password: admin123")
        db.session.commit()
    else:
        print("Admin user already exists!")
    
    print("\nRoles and permissions initialized successfully!")
    print("Available roles:")
    for role in Role.query.all():
        print(f"- {role.name}: {role.permissions}")
    
    print("\nMessenger Permission Levels:")
    print("- messenger_admin: Full messenger control (create groups, manage users, moderate)")
    print("- messenger_moderate: Moderate content and manage groups")
    print("- messenger_send: Send messages and upload files")
    print("- messenger_read: Read messages only") 