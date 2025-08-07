from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from . import db
from .forms import LoginForm, RegistrationForm, UserProfileForm, ComprehensiveUserProfileForm, ChangePasswordForm, UserManagementForm
from .models import User, Role, ProfileChangeRequest
from .activity_logger import log_user_login, log_user_logout
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime, timezone

auth = Blueprint('auth', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('admin'):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission):
                flash(f'Access denied. {permission.replace("_", " ").title()} permission required.', 'error')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# New permission decorators for manager roles
def marketing_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user has marketing manager permissions
        required_permissions = [
            'manage_marketing_team',
            'view_marketing_reports',
            'manage_leads',
            'view_projections',
            'manage_calls'
        ]
        
        has_permission = any(current_user.has_permission(perm) for perm in required_permissions)
        if not has_permission:
            flash('Access denied. Marketing manager privileges required.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def productions_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user has productions manager permissions
        required_permissions = [
            'manage_productions_team',
            'view_productions_reports',
            'manage_tasks',
            'upload_files',
            'access_lan_server'
        ]
        
        has_permission = any(current_user.has_permission(perm) for perm in required_permissions)
        if not has_permission:
            flash('Access denied. Productions manager privileges required.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def team_manager_required(team_id=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))
            
            # Get team_id from kwargs or function parameter
            target_team_id = team_id or kwargs.get('team_id')
            
            if target_team_id:
                # Check if user is manager of the specific team
                from .models import UserTeam
                user_team = UserTeam.query.filter_by(
                    user_id=current_user.id,
                    team_id=target_team_id,
                    role='manager'
                ).first()
                
                if not user_team:
                    flash('Access denied. Team manager privileges required.', 'error')
                    return redirect(url_for('auth.login'))
            else:
                # Check if user is manager of any team
                from .models import UserTeam
                user_teams = UserTeam.query.filter_by(
                    user_id=current_user.id,
                    role='manager'
                ).all()
                
                if not user_teams:
                    flash('Access denied. Team manager privileges required.', 'error')
                    return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def team_member_required(team_id=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))
            
            # Get team_id from kwargs or function parameter
            target_team_id = team_id or kwargs.get('team_id')
            
            if target_team_id:
                # Check if user is member of the specific team
                from .models import UserTeam
                user_team = UserTeam.query.filter_by(
                    user_id=current_user.id,
                    team_id=target_team_id
                ).first()
                
                if not user_team:
                    flash('Access denied. Team member privileges required.', 'error')
                    return redirect(url_for('auth.login'))
            else:
                # Check if user is member of any team
                from .models import UserTeam
                user_teams = UserTeam.query.filter_by(
                    user_id=current_user.id
                ).all()
                
                if not user_teams:
                    flash('Access denied. Team member privileges required.', 'error')
                    return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Permission validation functions
def validate_marketing_permissions(user):
    """Validate if user has marketing manager permissions."""
    required_permissions = [
        'manage_marketing_team',
        'view_marketing_reports',
        'manage_leads',
        'view_projections',
        'manage_calls'
    ]
    return any(user.has_permission(perm) for perm in required_permissions)

def validate_productions_permissions(user):
    """Validate if user has productions manager permissions."""
    required_permissions = [
        'manage_productions_team',
        'view_productions_reports',
        'manage_tasks',
        'upload_files',
        'access_lan_server'
    ]
    return any(user.has_permission(perm) for perm in required_permissions)

def validate_team_access(user, team_id):
    """Validate if user has access to a specific team."""
    from .models import UserTeam
    user_team = UserTeam.query.filter_by(
        user_id=user.id,
        team_id=team_id
    ).first()
    return user_team is not None

def validate_team_manager_access(user, team_id):
    """Validate if user is manager of a specific team."""
    from .models import UserTeam
    user_team = UserTeam.query.filter_by(
        user_id=user.id,
        team_id=team_id,
        role='manager'
    ).first()
    return user_team is not None

@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Initialize session to ensure CSRF token is generated
    if 'csrf_token' not in session:
        session.permanent = True
    
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_approved:
                flash('Your account is pending approval. Please contact an administrator.', 'warning')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log login activity
            log_user_login(user.id)
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth.route('/logout')
def logout():
    # Log logout activity before logging out
    if current_user.is_authenticated:
        log_user_logout(current_user.id)
    
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Initialize session to ensure CSRF token is generated
    if 'csrf_token' not in session:
        session.permanent = True
    
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html', title='Register', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html', title='Register', form=form)
        
        # Find or create the selected role
        selected_role_name = form.role.data
        role = Role.query.filter_by(name=selected_role_name).first()
        
        # If role doesn't exist, create it with appropriate permissions
        if not role:
            role = Role(name=selected_role_name, description=f'Role for {selected_role_name}')
            
            # Set permissions based on role
            if selected_role_name == 'Admin':
                role.permissions = 'admin,manage_users,manage_roles,view_reports,manage_leads,add_leads,manage_tasks,view_tasks,upload_files,access_lan_server,view_client_info,manage_scraper,messenger_send,messenger_read,messenger_moderate,messenger_admin,manage_marketing_team,manage_productions_team'
            elif selected_role_name == 'Marketing Manager':
                role.permissions = 'manage_marketing_team,view_reports,manage_leads,add_leads,view_tasks,messenger_send,messenger_read'
            elif selected_role_name == 'Productions Manager':
                role.permissions = 'manage_productions_team,view_reports,manage_tasks,view_tasks,upload_files,access_lan_server,messenger_send,messenger_read'
            elif selected_role_name == 'HR':
                role.permissions = 'manage_users,view_reports,view_tasks,messenger_send,messenger_read'
            elif selected_role_name == 'Caller':
                role.permissions = 'add_leads,view_tasks,messenger_send,messenger_read'
            elif selected_role_name == 'Lead Generator':
                role.permissions = 'add_leads,view_tasks,messenger_send,messenger_read'
            elif selected_role_name == 'Production':
                role.permissions = 'view_tasks,upload_files,messenger_send,messenger_read'
            else:
                # Default permissions for unknown roles
                role.permissions = 'view_tasks,messenger_send,messenger_read'
            
            db.session.add(role)
            db.session.flush()  # Get the role ID
        
        # Create new user (not approved by default)
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role_id=role.id
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.flush()  # Get the user ID
        
        # Automatically add user to appropriate team based on role
        from .models import Team, UserTeam
        
        role_team_mappings = {
            'Caller': 'Marketing Team',
            'Lead Generator': 'Marketing Team',
            'Marketing Manager': 'Marketing Team',
            'Production': 'Productions Team',
            'Productions Manager': 'Productions Team',
            'Admin': 'Admin Team',
            'HR': 'Admin Team'
        }
        
        if selected_role_name in role_team_mappings:
            team_name = role_team_mappings[selected_role_name]
            team = Team.query.filter_by(name=team_name).first()
            
            if team:
                # Determine team role
                team_role = 'manager' if selected_role_name in ['Marketing Manager', 'Productions Manager', 'Admin'] else 'member'
                
                # Add user to team
                user_team = UserTeam(
                    user_id=user.id,
                    team_id=team.id,
                    role=team_role,
                    is_active=True
                )
                db.session.add(user_team)
                print(f"Automatically added {user.username} to {team_name} as {team_role}")
        
        db.session.commit()
        
        flash('Registration successful! Your account is pending approval.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    from .models import ProfileChangeRequest
    from datetime import datetime, timezone
    
    # Initialize session to ensure CSRF token is generated
    if 'csrf_token' not in session:
        session.permanent = True
    
    form = ComprehensiveUserProfileForm()
    
    if form.validate_on_submit():
        changes_made = []
        
        # Handle profile image upload
        if form.profile_image.data:
            file = form.profile_image.data
            if file.filename:
                # Generate unique filename
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                
                # Save file
                upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
                os.makedirs(upload_path, exist_ok=True)
                file_path = os.path.join(upload_path, unique_filename)
                file.save(file_path)
                
                # Update user profile image
                current_user.profile_image = unique_filename
                changes_made.append('profile_image')
        
        # Check for username change (requires approval)
        if form.username.data != current_user.username:
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Username is already taken', 'error')
                return redirect(url_for('auth.profile'))
            
            change_request = ProfileChangeRequest(
                user_id=current_user.id,
                request_type='username',
                old_value=current_user.username,
                new_value=form.username.data,
                status='pending'
            )
            db.session.add(change_request)
            changes_made.append('username')
        
        # Check for email change (requires approval)
        if form.email.data != current_user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Email is already taken', 'error')
                return redirect(url_for('auth.profile'))
            
            change_request = ProfileChangeRequest(
                user_id=current_user.id,
                request_type='email',
                old_value=current_user.email,
                new_value=form.email.data,
                status='pending'
            )
            db.session.add(change_request)
            changes_made.append('email')
        
        # Apply immediate changes for other fields
        if form.first_name.data != current_user.first_name:
            current_user.first_name = form.first_name.data
            changes_made.append('first_name')
        
        if form.last_name.data != current_user.last_name:
            current_user.last_name = form.last_name.data
            changes_made.append('last_name')
        
        # Update personal information
        if form.date_of_birth.data != current_user.date_of_birth:
            current_user.date_of_birth = form.date_of_birth.data
            changes_made.append('date_of_birth')
        
        if form.nid_number.data != current_user.nid_number:
            current_user.nid_number = form.nid_number.data
            changes_made.append('nid_number')
        
        if form.phone_number.data != current_user.phone_number:
            current_user.phone_number = form.phone_number.data
            changes_made.append('phone_number')
        
        if form.emergency_phone.data != current_user.emergency_phone:
            current_user.emergency_phone = form.emergency_phone.data
            changes_made.append('emergency_phone')
        
        if form.current_address.data != current_user.current_address:
            current_user.current_address = form.current_address.data
            changes_made.append('current_address')
        
        if form.permanent_address.data != current_user.permanent_address:
            current_user.permanent_address = form.permanent_address.data
            changes_made.append('permanent_address')
        
        if form.city.data != current_user.city:
            current_user.city = form.city.data
            changes_made.append('city')
        
        if form.state_province.data != current_user.state_province:
            current_user.state_province = form.state_province.data
            changes_made.append('state_province')
        
        if form.postal_code.data != current_user.postal_code:
            current_user.postal_code = form.postal_code.data
            changes_made.append('postal_code')
        
        if form.country.data != current_user.country:
            current_user.country = form.country.data
            changes_made.append('country')
        
        if form.father_name.data != current_user.father_name:
            current_user.father_name = form.father_name.data
            changes_made.append('father_name')
        
        if form.mother_name.data != current_user.mother_name:
            current_user.mother_name = form.mother_name.data
            changes_made.append('mother_name')
        
        if form.blood_group.data != current_user.blood_group:
            current_user.blood_group = form.blood_group.data
            changes_made.append('blood_group')
        
        if form.marital_status.data != current_user.marital_status:
            current_user.marital_status = form.marital_status.data
            changes_made.append('marital_status')
        
        if form.emergency_contact_name.data != current_user.emergency_contact_name:
            current_user.emergency_contact_name = form.emergency_contact_name.data
            changes_made.append('emergency_contact_name')
        
        if form.emergency_contact_relationship.data != current_user.emergency_contact_relationship:
            current_user.emergency_contact_relationship = form.emergency_contact_relationship.data
            changes_made.append('emergency_contact_relationship')
        
        db.session.commit()
        
        if changes_made:
            if 'username' in changes_made or 'email' in changes_made:
                flash('Profile updated! Username/email changes submitted for admin approval.', 'success')
            else:
                flash('Profile updated successfully!', 'success')
        else:
            flash('No changes were made.', 'info')
        
        return redirect(url_for('auth.profile'))
    
    elif request.method == 'GET':
        # Populate form with current user data
        form.username.data = current_user.username
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.date_of_birth.data = current_user.date_of_birth
        form.nid_number.data = current_user.nid_number
        form.phone_number.data = current_user.phone_number
        form.emergency_phone.data = current_user.emergency_phone
        form.current_address.data = current_user.current_address
        form.permanent_address.data = current_user.permanent_address
        form.city.data = current_user.city
        form.state_province.data = current_user.state_province
        form.postal_code.data = current_user.postal_code
        form.country.data = current_user.country
        form.father_name.data = current_user.father_name
        form.mother_name.data = current_user.mother_name
        form.blood_group.data = current_user.blood_group
        form.marital_status.data = current_user.marital_status
        form.emergency_contact_name.data = current_user.emergency_contact_name
        form.emergency_contact_relationship.data = current_user.emergency_contact_relationship
    
    # Get pending change requests
    pending_requests = ProfileChangeRequest.query.filter_by(
        user_id=current_user.id, 
        status='pending'
    ).all()
    
    return render_template('auth/comprehensive_profile.html', title='Profile', form=form, pending_requests=pending_requests)



@auth.route('/admin/profile-changes')
@admin_required
def admin_profile_changes():
    from .models import ProfileChangeRequest
    
    pending_changes = ProfileChangeRequest.query.filter_by(status='pending').order_by(ProfileChangeRequest.created_at.desc()).all()
    return render_template('auth/admin_profile_changes.html', title='Profile Change Requests', changes=pending_changes)

@auth.route('/admin/profile-changes/<int:change_id>/approve', methods=['POST'])
@admin_required
def admin_approve_profile_change(change_id):
    from .models import ProfileChangeRequest
    
    change_request = ProfileChangeRequest.query.get_or_404(change_id)
    
    if change_request.status != 'pending':
        flash('This change request has already been processed', 'error')
        return redirect(url_for('auth.admin_profile_changes'))
    
    # Apply the change
    user = User.query.get(change_request.user_id)
    if change_request.request_type == 'username':
        user.username = change_request.new_value
    elif change_request.request_type == 'email':
        user.email = change_request.new_value
    elif change_request.request_type == 'password':
        user.set_password(change_request.new_value)
    
    # Mark as approved
    change_request.status = 'approved'
    change_request.approved_by = current_user.id
    change_request.approved_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    flash(f'Profile change for {user.username} has been approved!', 'success')
    return redirect(url_for('auth.admin_profile_changes'))

@auth.route('/admin/profile-changes/<int:change_id>/reject', methods=['POST'])
@admin_required
def admin_reject_profile_change(change_id):
    from .models import ProfileChangeRequest
    
    change_request = ProfileChangeRequest.query.get_or_404(change_id)
    
    if change_request.status != 'pending':
        flash('This change request has already been processed', 'error')
        return redirect(url_for('auth.admin_profile_changes'))
    
    # Mark as rejected
    change_request.status = 'rejected'
    change_request.approved_by = current_user.id
    change_request.approved_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    flash(f'Profile change request has been rejected.', 'success')
    return redirect(url_for('auth.admin_profile_changes'))

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    from .models import ProfileChangeRequest
    
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('auth.change_password'))
        
        # Create change request for password
        change_request = ProfileChangeRequest(
            user_id=current_user.id,
            request_type='password',
            old_value='***',  # Don't store actual password
            new_value=form.new_password.data,
            status='pending'
        )
        db.session.add(change_request)
        db.session.commit()
        
        flash('Password change request submitted for admin approval. You will be notified when approved.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', title='Change Password', form=form)

@auth.route('/admin/users/<int:user_id>/view-profile')
@admin_required
def admin_view_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('auth/admin_view_user_profile.html', title=f'User Profile - {user.username}', user=user)

@auth.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('auth/admin_users.html', title='User Management', users=users)

@auth.route('/admin/users/pending')
@admin_required
def admin_pending_users():
    pending_users = User.query.filter_by(is_approved=False).all()
    return render_template('auth/admin_pending_users.html', title='Pending User Approvals', users=pending_users)

@auth.route('/admin/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def admin_approve_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.is_approved:
        flash('User is already approved', 'info')
        return redirect(url_for('auth.admin_pending_users'))
    
    user.is_approved = True
    user.approved_by = current_user.id
    user.approved_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    flash(f'User "{user.username}" has been approved successfully!', 'success')
    return redirect(url_for('auth.admin_pending_users'))

@auth.route('/admin/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def admin_reject_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.is_approved:
        flash('User is already approved', 'info')
        return redirect(url_for('auth.admin_pending_users'))
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User "{user.username}" has been rejected and removed.', 'success')
    return redirect(url_for('auth.admin_pending_users'))

@auth.route('/admin/users/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserManagementForm()
    
    # Populate role choices
    roles = Role.query.all()
    form.role_id.choices = [(role.id, role.name) for role in roles]
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role_id = form.role_id.data
        user.is_active = form.is_active.data
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('auth.admin_users'))
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.role_id.data = user.role_id
        form.is_active.data = user.is_active
    
    return render_template('auth/admin_edit_user.html', title='Edit User', form=form, user=user)

@auth.route('/admin/roles')
@admin_required
def admin_roles():
    roles = Role.query.all()
    return render_template('auth/admin_roles.html', title='Role Management', roles=roles)

@auth.route('/admin/roles/create', methods=['GET', 'POST'])
@admin_required
def admin_create_role():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        permissions = request.form.getlist('permissions')
        
        if not name:
            flash('Role name is required', 'error')
            return redirect(url_for('auth.admin_create_role'))
        
        if Role.query.filter_by(name=name).first():
            flash('Role name already exists', 'error')
            return redirect(url_for('auth.admin_create_role'))
        
        # Convert permissions list to comma-separated string
        permissions_str = ','.join(permissions) if permissions else ''
        
        new_role = Role(
            name=name,
            description=description,
            permissions=permissions_str
        )
        
        db.session.add(new_role)
        db.session.commit()
        
        flash('Role created successfully!', 'success')
        return redirect(url_for('auth.admin_roles'))
    
    # Available permissions for selection
    available_permissions = [
        'admin', 'manage_users', 'manage_roles', 'view_reports', 
        'manage_leads', 'add_leads', 'manage_tasks', 'view_tasks', 'upload_files', 
        'access_lan_server', 'view_client_info', 'manage_scraper',
        'messenger_send', 'messenger_read', 'messenger_moderate', 'messenger_admin',
        'manage_marketing_team', 'manage_productions_team'
    ]
    
    return render_template('auth/admin_create_role.html', 
                         title='Create Role', 
                         available_permissions=available_permissions)

@auth.route('/admin/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    
    # Prevent editing system roles (Admin)
    if role.name == 'Admin':
        flash('System roles cannot be edited', 'error')
        return redirect(url_for('auth.admin_roles'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        permissions = request.form.getlist('permissions')
        
        if not name:
            flash('Role name is required', 'error')
            return redirect(url_for('auth.admin_edit_role', role_id=role_id))
        
        # Check if name already exists (excluding current role)
        existing_role = Role.query.filter_by(name=name).first()
        if existing_role and existing_role.id != role_id:
            flash('Role name already exists', 'error')
            return redirect(url_for('auth.admin_edit_role', role_id=role_id))
        
        # Convert permissions list to comma-separated string
        permissions_str = ','.join(permissions) if permissions else ''
        
        role.name = name
        role.description = description
        role.permissions = permissions_str
        
        db.session.commit()
        
        flash('Role updated successfully!', 'success')
        return redirect(url_for('auth.admin_roles'))
    
    # Available permissions for selection
    available_permissions = [
        'admin', 'manage_users', 'manage_roles', 'view_reports', 
        'manage_leads', 'add_leads', 'manage_tasks', 'view_tasks', 'upload_files', 
        'access_lan_server', 'view_client_info', 'manage_scraper',
        'messenger_send', 'messenger_read', 'messenger_moderate', 'messenger_admin',
        'manage_marketing_team', 'manage_productions_team'
    ]
    
    # Get current permissions as list
    current_permissions = role.permissions.split(',') if role.permissions else []
    
    return render_template('auth/admin_edit_role.html', 
                         title='Edit Role', 
                         role=role,
                         available_permissions=available_permissions,
                         current_permissions=current_permissions)

@auth.route('/admin/roles/<int:role_id>/delete', methods=['POST'])
@admin_required
def admin_delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    
    # Prevent deleting system roles (Admin)
    if role.name == 'Admin':
        flash('System roles cannot be deleted', 'error')
        return redirect(url_for('auth.admin_roles'))
    
    # Check if role has users
    if role.users:
        flash(f'Cannot delete role "{role.name}" - it has {len(role.users)} user(s) assigned', 'error')
        return redirect(url_for('auth.admin_roles'))
    
    db.session.delete(role)
    db.session.commit()
    
    flash(f'Role "{role.name}" deleted successfully!', 'success')
    return redirect(url_for('auth.admin_roles'))

@auth.route('/admin/roles/<int:role_id>/assign', methods=['GET', 'POST'])
@admin_required
def admin_assign_role(role_id):
    role = Role.query.get_or_404(role_id)
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')  # 'assign' or 'remove'
        
        user = User.query.get_or_404(user_id)
        
        if action == 'assign':
            user.role_id = role_id
            flash(f'User "{user.username}" assigned to role "{role.name}"', 'success')
        elif action == 'remove':
            # Don't allow removing the last admin
            if role.name == 'Admin' and len(role.users) == 1:
                flash('Cannot remove the last admin user', 'error')
                return redirect(url_for('auth.admin_assign_role', role_id=role_id))
            
            # Assign to default User role
            default_role = Role.query.filter_by(name='User').first()
            if default_role:
                user.role_id = default_role.id
                flash(f'User "{user.username}" removed from role "{role.name}"', 'success')
            else:
                flash('Default User role not found', 'error')
                return redirect(url_for('auth.admin_assign_role', role_id=role_id))
        
        db.session.commit()
        return redirect(url_for('auth.admin_assign_role', role_id=role_id))
    
    # Get all users and their current roles
    all_users = User.query.all()
    users_with_role = [user for user in all_users if user.role_id == role_id]
    users_without_role = [user for user in all_users if user.role_id != role_id]
    
    return render_template('auth/admin_assign_role.html', 
                         title=f'Assign Role: {role.name}',
                         role=role,
                         users_with_role=users_with_role,
                         users_without_role=users_without_role) 