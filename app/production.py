from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file, session
from sqlalchemy import func
from flask_login import login_required, current_user
from .auth import permission_required
from .models import db, ProductionTask, TaskAttachment, LANServerFile, DropboxUpload, User, ConvertedClient, ProductionActivity, ScreenRecording, ProductivityReport, ApplicationUsage, MouseKeyboardActivity, WebsiteVisit, BrowserActivity, DetailedApplicationUsage, ChatMessage, ChatMention, Notification, UserOnlineStatus, TaskAuditLog, DesktopActivity, TaskDependency, UserTask, Role, ChatReminder, ScheduledMessage, ChatGroup, ChatGroupMember, ChatGroupInvitation, ChatGroupReport, PinnedMessage, MessageAttachment, UserTeam, TaskComment, TaskSession, TaskSessionPause
from .ai_service import ai_service
from werkzeug.utils import secure_filename
from sqlalchemy import text
import os
import uuid
from datetime import datetime, timezone, timedelta, date, timedelta
import mimetypes
import io
import re
import json
from .ai_enhancements import ai_enhancer
from functools import wraps

production = Blueprint('production', __name__)

def production_role_required(f):
    """Decorator to require Production role or admin/productions manager permissions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        # Allow if user is Admin or Productions Manager
        if (current_user.has_permission('admin') or 
            current_user.has_permission('manage_productions_team')):
            return f(*args, **kwargs)
        
        # Allow if user has view_tasks permission AND is Production role
        if (current_user.has_permission('view_tasks') and 
            current_user.role and current_user.role.name == 'Production'):
            return f(*args, **kwargs)
        
        flash('Access denied. Production role required.', 'error')
        return redirect(url_for('auth.login'))
    
    return decorated_function

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', 'psd', 'ai', 'eps', 'svg'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_notification(user_id, notification_type, title, message, related_id=None):
    """Create a notification for a user."""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_id=related_id
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def log_task_audit(task_id, task_type, operation, user_id, field_name=None, old_value=None, new_value=None, description=None, request_data=None):
    """Log task audit information."""
    audit_log = TaskAuditLog(
        task_id=task_id,
        task_type=task_type,
        operation=operation,
        user_id=user_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        description=description,
        request_data=json.dumps(request_data) if request_data else None
    )
    db.session.add(audit_log)
    db.session.commit()

def update_user_online_status(user_id, is_online=True):
    """Update user's online status."""
    status = UserOnlineStatus.query.filter_by(user_id=user_id).first()
    if not status:
        status = UserOnlineStatus(user_id=user_id)
        db.session.add(status)
    
    status.is_online = is_online
    status.last_seen = datetime.now(timezone.utc)
    db.session.commit()

def extract_mentions(content):
    """Extract @mentions from message content."""
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, content)
    return mentions

@production.route('/dashboard')
@login_required
@production_role_required
def dashboard():
    """Production dashboard with comprehensive tracking and chat."""
    # Update user online status
    update_user_online_status(current_user.id, True)
    
    # Get assigned tasks
    assigned_tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).order_by(ProductionTask.created_at.desc()).all()
    
    # Get task statistics
    pending_count = ProductionTask.query.filter_by(assigned_to=current_user.id, status='pending').count()
    in_progress_count = ProductionTask.query.filter_by(assigned_to=current_user.id, status='in_progress').count()
    completed_count = ProductionTask.query.filter_by(assigned_to=current_user.id, status='completed').count()
    overdue_count = ProductionTask.query.filter(
        ProductionTask.assigned_to == current_user.id,
        ProductionTask.due_date < date.today(),
        ProductionTask.status.in_(['pending', 'in_progress'])
    ).count()
    
    # Get recent chat messages
    recent_messages = ChatMessage.query.filter_by(room='general').order_by(ChatMessage.created_at.desc()).limit(20).all()
    recent_messages.reverse()  # Show oldest first
    
    # Get online users
    online_users = UserOnlineStatus.query.filter_by(is_online=True).all()
    online_users_count = len(online_users)
    
    # Get unread notifications
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()
    
    # Get today's productivity data
    today = date.today()
    
    # Get today's application usage
    today_app_usage = ApplicationUsage.query.filter_by(
        user_id=current_user.id, 
        usage_date=today
    ).all()
    
    # Get today's detailed application usage
    today_detailed_apps = DetailedApplicationUsage.query.filter_by(
        user_id=current_user.id,
        usage_date=today
    ).all()
    
    # Get today's mouse/keyboard activity
    today_activity = MouseKeyboardActivity.query.filter_by(
        user_id=current_user.id,
        activity_date=today
    ).first()
    
    # Get today's productivity report
    today_report = ProductivityReport.query.filter_by(
        user_id=current_user.id,
        report_date=today
    ).first()
    
    # Get today's website visits
    today_website_visits = WebsiteVisit.query.filter_by(
        user_id=current_user.id,
        visit_date=today
    ).all()
    
    # Get today's browser activity
    today_browser_activity = BrowserActivity.query.filter_by(
        user_id=current_user.id,
        activity_date=today
    ).all()
    
    # Get recent production activities
    recent_activities = ProductionActivity.query.filter_by(
        user_id=current_user.id
    ).order_by(ProductionActivity.created_at.desc()).limit(10).all()
    
    # Calculate productivity metrics
    total_active_time = sum(app.active_time_seconds for app in today_app_usage) if today_app_usage else 0
    total_break_time = sum(app.idle_time_seconds for app in today_app_usage) if today_app_usage else 0
    
    # Calculate productivity score
    if total_active_time > 0:
        productivity_score = min(100, (total_active_time / (total_active_time + total_break_time)) * 100)
    else:
        productivity_score = 0
    
    # Get application usage percentages (Adobe Creative Suite)
    adobe_apps = ['Adobe Photoshop', 'Adobe Illustrator', 'Adobe InDesign', 'Adobe XD']
    adobe_usage = {}
    total_adobe_time = 0
    
    for app in today_app_usage:
        if app.application_name in adobe_apps:
            total_adobe_time += app.total_time_seconds
    
    for app in today_app_usage:
        if app.application_name in adobe_apps:
            if total_adobe_time > 0:
                percentage = (app.total_time_seconds / total_adobe_time) * 100
                adobe_usage[app.application_name] = round(percentage, 1)
            else:
                adobe_usage[app.application_name] = 0
    
    # Get detailed application usage by category
    app_categories = {}
    for app in today_detailed_apps:
        category = app.application_category
        if category not in app_categories:
            app_categories[category] = 0
        app_categories[category] += app.total_time_seconds
    
    # Get today's desktop activities
    today_desktop_activities = DesktopActivity.query.filter_by(
        user_id=current_user.id
    ).filter(
        db.func.date(DesktopActivity.timestamp) == today
    ).order_by(DesktopActivity.timestamp.desc()).limit(20).all()
    
    return render_template('production/dashboard.html',
                         assigned_tasks=assigned_tasks,
                         pending_count=pending_count,
                         in_progress_count=in_progress_count,
                         completed_count=completed_count,
                         overdue_count=overdue_count,
                         recent_messages=recent_messages,
                         online_users_count=online_users_count,
                         unread_notifications=unread_notifications,
                         today_app_usage=today_app_usage,
                         today_detailed_apps=today_detailed_apps,
                         today_activity=today_activity,
                         today_report=today_report,
                         today_website_visits=today_website_visits,
                         today_browser_activity=today_browser_activity,
                         recent_activities=recent_activities,
                         productivity_score=productivity_score,
                         adobe_usage=adobe_usage,
                         app_categories=app_categories,
                         today_desktop_activities=today_desktop_activities,
                         today=today)

@production.route('/tasks')
@login_required
@production_role_required
def tasks():
    """View all assigned tasks."""
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    
    query = ProductionTask.query.filter_by(assigned_to=current_user.id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    
    tasks = query.order_by(ProductionTask.created_at.desc()).all()
    
    # Add current date for template
    from datetime import datetime
    now = datetime.now()
    
    return render_template('production/tasks.html', tasks=tasks, now=now)

@production.route('/tasks/<int:task_id>')
@login_required
@production_role_required
def view_task(task_id):
    """View a specific task with all details."""
    from .models import TaskComment
    
    task = ProductionTask.query.get_or_404(task_id)
    
    # Get assigned user
    assigned_user = User.query.get(task.assigned_to) if task.assigned_to else None
    
    # Get task comments
    task_comments = TaskComment.query.filter_by(
        task_id=task_id,
        task_type='production_task'
    ).all()
    
    # Mask sensitive client information
    if task.client_name:
        task.client_name = task.client_name[:2] + '*' * (len(task.client_name) - 2)
    if task.client_contact:
        task.client_contact = task.client_contact[:2] + '*' * (len(task.client_contact) - 2)
    if task.client_phone:
        task.client_phone = task.client_phone[:2] + '*' * (len(task.client_phone) - 2)
    if task.client_email:
        email_parts = task.client_email.split('@')
        if len(email_parts) == 2:
            task.client_email = email_parts[0][:2] + '*' * (len(email_parts[0]) - 2) + '@' + email_parts[1]
    
    return render_template('production/view_task.html', 
                         task=task, 
                         assigned_user=assigned_user,
                         task_comments=task_comments)

@production.route('/gantt')
@login_required
@production_role_required
def gantt_view():
    """Gantt chart view for task dependencies."""
    return render_template('production/gantt.html')

@production.route('/kanban')
@login_required
@production_role_required
def kanban_view():
    """Kanban board view for personal task management."""
    return render_template('production/kanban.html')

@production.route('/chat')
@login_required
@production_role_required
def chat():
    """Team chat interface with enhanced features."""
    return render_template('production/chat.html')

@production.route('/messenger')
@login_required
@production_role_required
def messenger():
    """Full-screen messenger interface with advanced search features."""
    return render_template('production/messenger.html')

@production.route('/tasks/<int:task_id>/update', methods=['POST'])
@login_required
@permission_required('manage_tasks')
def update_task(task_id):
    """Update task status and progress."""
    task = ProductionTask.query.get_or_404(task_id)
    
    # Check if user is assigned to this task
    if task.assigned_to != current_user.id:
        flash('Access denied. You can only update your assigned tasks.', 'error')
        return redirect(url_for('production.tasks'))
    
    # Store old values for audit logging
    old_status = task.status
    old_description = task.description
    
    status = request.form.get('status')
    description = request.form.get('description')
    
    changes_logged = False
    
    if status and status in ['pending', 'in_progress', 'completed', 'cancelled']:
        if status != old_status:
            task.status = status
            if status == 'completed':
                task.completed_at = datetime.now(timezone.utc)
            
            # Log status change
            log_task_audit(
                task_id=task_id,
                task_type='production_task',
                operation='status_change',
                user_id=current_user.id,
                field_name='status',
                old_value=old_status,
                new_value=status,
                description=f"Production task status changed from '{old_status}' to '{status}'",
                request_data=request.form.to_dict()
            )
            changes_logged = True
    
    if description and description != old_description:
        task.description = description
        
        # Log description change
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='update',
            user_id=current_user.id,
            field_name='description',
            old_value=old_description,
            new_value=description,
            description="Production task description updated",
            request_data=request.form.to_dict()
        )
        changes_logged = True
    
    task.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    if changes_logged:
        flash('Task updated successfully!', 'success')
    else:
        flash('No changes made to task.', 'info')
    
    return redirect(url_for('production.view_task', task_id=task_id))

@production.route('/upload', methods=['GET', 'POST'])
@login_required
@permission_required('upload_files')
def upload_files():
    """Upload files to Dropbox or local storage."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        files = request.files.getlist('file')
        task_id = request.form.get('task_id')
        upload_type = request.form.get('upload_type', 'local')  # 'local', 'dropbox'
        
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
            
            if file and allowed_file(file.filename):
                # Generate unique filename
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                
                if upload_type == 'dropbox':
                    # Upload to Dropbox (placeholder - implement actual Dropbox API)
                    dropbox_upload = DropboxUpload(
                        filename=unique_filename,
                        dropbox_path=f"/production/{unique_filename}",
                        file_size=0,  # Will be updated after upload
                        file_type=mimetypes.guess_type(filename)[0],
                        uploaded_by=current_user.id,
                        upload_status='completed'  # Placeholder
                    )
                    db.session.add(dropbox_upload)
                    uploaded_files.append(dropbox_upload)
                else:
                    # Upload to local storage
                    upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'production')
                    os.makedirs(upload_path, exist_ok=True)
                    file_path = os.path.join(upload_path, unique_filename)
                    file.save(file_path)
                    
                    # Create attachment record
                    attachment = TaskAttachment(
                        filename=unique_filename,
                        original_filename=filename,
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        file_type=mimetypes.guess_type(filename)[0],
                        upload_source='local',
                        uploaded_by=current_user.id
                    )
                    
                    if task_id:
                        attachment.task_id = task_id
                    
                    db.session.add(attachment)
                    uploaded_files.append(attachment)
        
        db.session.commit()
        flash(f'{len(uploaded_files)} file(s) uploaded successfully!', 'success')
        return redirect(url_for('production.upload_files'))
    
    # Get user's recent uploads
    recent_uploads = TaskAttachment.query.filter_by(uploaded_by=current_user.id).order_by(TaskAttachment.uploaded_at.desc()).limit(10).all()
    
    return render_template('production/upload.html', recent_uploads=recent_uploads)

@production.route('/lan-server')
@login_required
@permission_required('access_lan_server')
def lan_server():
    """Access files from LAN server."""
    server_path = request.args.get('path', '/')  # Default to root
    search = request.args.get('search', '')
    
    # Simulate LAN server file listing (replace with actual implementation)
    # This is a placeholder - you'll need to implement actual LAN server access
    files = []
    
    # Example file structure (replace with actual LAN server scanning)
    if not search:
        files = [
            {'name': 'project_docs', 'type': 'folder', 'size': 0},
            {'name': 'design_files', 'type': 'folder', 'size': 0},
            {'name': 'client_assets', 'type': 'folder', 'size': 0},
            {'name': 'sample_document.pdf', 'type': 'file', 'size': 1024000},
            {'name': 'design_mockup.psd', 'type': 'file', 'size': 2048000},
        ]
    else:
        # Filter files based on search
        files = [
            {'name': f'{search}_result.pdf', 'type': 'file', 'size': 512000},
        ]
    
    return render_template('production/lan_server.html', files=files, current_path=server_path, search=search)

@production.route('/lan-server/download/<path:filepath>')
@login_required
@permission_required('access_lan_server')
def download_lan_file(filepath):
    """Download file from LAN server."""
    # This is a placeholder - implement actual LAN server file access
    # For now, we'll return a dummy file
    
    # Record access in database
    lan_file = LANServerFile(
        server_path='/',
        filename=os.path.basename(filepath),
        file_type=mimetypes.guess_type(filepath)[0],
        accessed_by=current_user.id,
        last_accessed=datetime.now(timezone.utc)
    )
    db.session.add(lan_file)
    db.session.commit()
    
    # Return dummy file (replace with actual LAN server file)
    dummy_content = f"This is a dummy file for {filepath}. Replace with actual LAN server implementation."
    return send_file(
        io.BytesIO(dummy_content.encode()),
        mimetype='text/plain',
        as_attachment=True,
        download_name=os.path.basename(filepath)
    )



@production.route('/api/tasks')
@login_required
@production_role_required
def api_tasks():
    """API endpoint for tasks data."""
    tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).all()
    
    tasks_data = []
    for task in tasks:
        # For Production team, mask sensitive client information
        if not current_user.has_permission('admin') and not current_user.has_permission('manage_leads'):
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'client_name': None,  # Hide client name from Production team
                'client_id': task.client_id,  # Show only Client ID for reference
                'client_contact': None,  # Hide contact info
                'client_phone': None,  # Hide phone info
                'client_email': None,  # Hide email info
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat()
            })
        else:
            # Managers and Admins see full information
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'client_name': task.client_name,
                'client_id': task.client_id,
                'client_contact': task.client_contact,
                'client_phone': task.client_phone,
                'client_email': task.client_email,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat()
            })
    
    return jsonify({'tasks': tasks_data})

@production.route('/api/upload-progress')
@login_required
@permission_required('upload_files')
def api_upload_progress():
    """API endpoint for upload progress tracking."""
    # Get recent uploads for the user
    recent_uploads = DropboxUpload.query.filter_by(uploaded_by=current_user.id).order_by(DropboxUpload.uploaded_at.desc()).limit(5).all()
    
    uploads_data = []
    for upload in recent_uploads:
        uploads_data.append({
            'id': upload.id,
            'filename': upload.filename,
            'status': upload.upload_status,
            'uploaded_at': upload.uploaded_at.isoformat(),
            'file_size_mb': upload.get_file_size_mb()
        })
    
    return jsonify({'uploads': uploads_data}) 

@production.route('/api/dashboard_data')
@login_required
@production_role_required
def api_dashboard_data():
    """Get real-time dashboard data for AJAX updates."""
    today = date.today()
    
    # Get task counts
    pending_count = ProductionTask.query.filter_by(assigned_to=current_user.id, status='pending').count()
    in_progress_count = ProductionTask.query.filter_by(assigned_to=current_user.id, status='in_progress').count()
    completed_count = ProductionTask.query.filter_by(assigned_to=current_user.id, status='completed').count()
    overdue_count = ProductionTask.query.filter(
        ProductionTask.assigned_to == current_user.id,
        ProductionTask.due_date < today,
        ProductionTask.status.in_(['pending', 'in_progress'])
    ).count()
    
    # Get online users count
    online_users_count = UserOnlineStatus.query.filter_by(is_online=True).count()
    
    # Get unread notifications count
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return jsonify({
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'online_users_count': online_users_count,
        'unread_notifications_count': unread_count
    })

# Chat API Endpoints
@production.route('/api/chat/messages')
@login_required
@production_role_required
def api_chat_messages():
    """Get chat messages."""
    room = request.args.get('room', 'general')
    last_id = request.args.get('last_id', 0)
    
    messages = ChatMessage.query.filter(
        ChatMessage.room == room,
        ChatMessage.id > int(last_id)
    ).order_by(ChatMessage.created_at.asc()).all()
    
    message_data = []
    for message in messages:
        # Get read receipts
        read_by = []
        for receipt in message.read_receipts:
            read_by.append({
                'user_id': receipt.read_by_id,
                'full_name': receipt.read_by.get_full_name(),
                'username': receipt.read_by.username,
                'read_at': receipt.read_at.isoformat()
            })
        
        message_data.append({
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_name': message.sender.get_full_name(),
            'content': message.content,
            'message_type': message.message_type,
            'file_url': message.file_url,
            'file_name': message.file_name,
            'file_size': message.file_size,
            'is_pinned': message.is_pinned,
            'created_at': message.created_at.isoformat(),
            'mentions': [mention.mentioned_user.username for mention in message.mentions],
            'read_by': read_by
        })
    
    return jsonify({'messages': message_data})

@production.route('/api/users/list')
@login_required
@production_role_required
def api_users_list():
    """Get list of users for mentions."""
    try:
        users = User.query.join(Role).filter(
            User.is_approved == True,
            Role.name != 'Admin'
        ).all()
        
        users_data = []
        for user in users:
                    users_data.append({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.role.name if user.role else 'Unknown',
            'profile_image': user.get_profile_image_url()
        })
        
        return jsonify({'users': users_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/chat/offline-sync', methods=['POST'])
@login_required
@production_role_required
def api_sync_offline_messages():
    """Sync offline messages when connection is restored."""
    data = request.get_json()
    messages = data.get('messages', [])
    
    synced_count = 0
    for message_data in messages:
        try:
            # Create the message
            message = ChatMessage(
                sender_id=current_user.id,
                content=message_data.get('content'),
                room=message_data.get('room', 'general')
            )
            db.session.add(message)
            db.session.commit()
            
            # Process mentions
            mentions = message_data.get('mentions', [])
            for username in mentions:
                user = User.query.filter_by(username=username).first()
                if user:
                    mention = ChatMention(
                        message_id=message.id,
                        mentioned_user_id=user.id
                    )
                    db.session.add(mention)
            
            db.session.commit()
            synced_count += 1
            
        except Exception as e:
            print(f"Error syncing message: {e}")
            continue
    
    return jsonify({
        'success': True,
        'synced_count': synced_count,
        'message': f'Synced {synced_count} offline messages'
    })

@production.route('/api/chat/send', methods=['POST'])
@login_required
@production_role_required
def api_send_message():
    """Send a chat message."""
    data = request.get_json()
    content = data.get('content', '').strip()
    room = data.get('room', 'general')
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
    
    # Create the message
    message = ChatMessage(
        sender_id=current_user.id,
        content=content,
        room=room
    )
    db.session.add(message)
    db.session.commit()
    
    # Extract and process mentions
    mentions = extract_mentions(content)
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user:
            mention = ChatMention(
                message_id=message.id,
                mentioned_user_id=user.id
            )
            db.session.add(mention)
            
            # Create notification for mentioned user
            if user.id != current_user.id:
                create_notification(
                    user_id=user.id,
                    notification_type='mention',
                    title=f'You were mentioned by {current_user.get_full_name()}',
                    message=f'{current_user.get_full_name()} mentioned you in a message: "{content[:50]}{"..." if len(content) > 50 else ""}"',
                    related_id=message.id
                )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': {
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_name': current_user.get_full_name(),
            'content': message.content,
            'message_type': message.message_type,
            'created_at': message.created_at.isoformat(),
            'mentions': mentions
        }
    })

@production.route('/api/chat/upload', methods=['POST'])
@login_required
@production_role_required
def api_upload_chat_file():
    """Upload a file for chat."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    
    # Save file
    upload_folder = os.path.join(current_app.static_folder, 'uploads', 'chat')
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    # Determine message type
    file_ext = filename.rsplit('.', 1)[1].lower()
    if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
        message_type = 'image'
    else:
        message_type = 'file'
    
    # Create message
    message = ChatMessage(
        sender_id=current_user.id,
        content=f'📎 {filename}',
        message_type=message_type,
        file_url=f'/static/uploads/chat/{unique_filename}',
        file_name=filename,
        file_size=os.path.getsize(file_path),
        room=request.form.get('room', 'general')
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': {
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_name': current_user.get_full_name(),
            'content': message.content,
            'message_type': message.message_type,
            'file_url': message.file_url,
            'file_name': message.file_name,
            'file_size': message.file_size,
            'created_at': message.created_at.isoformat()
        }
    })

# Message Action API Routes
@production.route('/api/chat/edit', methods=['POST'])
@login_required
@production_role_required
def api_edit_message():
    """Edit a chat message."""
    data = request.get_json()
    message_id = data.get('message_id')
    content = data.get('content')
    room = data.get('room', 'general')
    
    if not message_id or not content:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    try:
        message = ChatMessage.query.get(message_id)
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Check if user owns the message
        if message.sender_id != current_user.id:
            return jsonify({'success': False, 'error': 'You can only edit your own messages'}), 403
        
        # Update message
        old_content = message.content
        message.content = content
        message.is_edited = True
        message.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Create notification for message edit
        create_notification(
            current_user.id,
            'message_edit',
            'Message Edited',
            f'You edited a message in {room}',
            message.id
        )
        
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'sender_id': message.sender_id,
                'sender_name': message.sender_name,
                'content': message.content,
                'is_edited': message.is_edited,
                'updated_at': message.updated_at.isoformat() if message.updated_at else None,
                'created_at': message.created_at.isoformat(),
                'room': message.room
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error editing message: {str(e)}")
        return jsonify({'success': False, 'error': 'Edit failed'}), 500

@production.route('/api/chat/delete', methods=['POST'])
@login_required
@production_role_required
def api_delete_message():
    """Delete a chat message."""
    data = request.get_json()
    message_id = data.get('message_id')
    room = data.get('room', 'general')
    
    if not message_id:
        return jsonify({'success': False, 'error': 'Missing message ID'}), 400
    
    try:
        message = ChatMessage.query.get(message_id)
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Check if user owns the message
        if message.sender_id != current_user.id:
            return jsonify({'success': False, 'error': 'You can only delete your own messages'}), 403
        
        # Delete message
        db.session.delete(message)
        db.session.commit()
        
        # Create notification for message deletion
        create_notification(
            current_user.id,
            'message_delete',
            'Message Deleted',
            f'You deleted a message in {room}',
            message_id
        )
        
        return jsonify({'success': True, 'message_id': message_id})
        
    except Exception as e:
        current_app.logger.error(f"Error deleting message: {str(e)}")
        return jsonify({'success': False, 'error': 'Delete failed'}), 500

@production.route('/api/chat/pin', methods=['POST'])
@login_required
@production_role_required
def api_pin_message():
    """Pin a chat message."""
    data = request.get_json()
    message_id = data.get('message_id')
    room = data.get('room', 'general')
    
    if not message_id:
        return jsonify({'success': False, 'error': 'Missing message ID'}), 400
    
    try:
        message = ChatMessage.query.get(message_id)
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Toggle pin status
        message.is_pinned = not message.is_pinned
        db.session.commit()
        
        # Create notification for message pin
        action = 'pinned' if message.is_pinned else 'unpinned'
        create_notification(
            current_user.id,
            'message_pin',
            f'Message {action.title()}',
            f'You {action} a message in {room}',
            message.id
        )
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'is_pinned': message.is_pinned
        })
        
    except Exception as e:
        current_app.logger.error(f"Error pinning message: {str(e)}")
        return jsonify({'success': False, 'error': 'Pin failed'}), 500



# Notification API Endpoints
@production.route('/api/notifications')
@login_required
@production_role_required
def api_notifications():
    """Get user notifications."""
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    notification_data = []
    for notification in notifications:
        notification_data.append({
            'id': notification.id,
            'type': notification.type,
            'title': notification.title,
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'time_ago': notification.get_time_ago(),
            'icon': notification.get_icon(),
            'color': notification.get_color()
        })
    
    return jsonify({
        'notifications': notification_data
    })

@production.route('/api/notifications/mark-read', methods=['POST'])
@login_required
@production_role_required
def api_mark_notification_read():
    """Mark notification as read."""
    data = request.get_json()
    notification_id = data.get('notification_id')
    
    if notification_id:
        notification = Notification.query.get(notification_id)
        if notification and notification.user_id == current_user.id:
            notification.is_read = True
            db.session.commit()
            return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid notification ID'}), 400

@production.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
@production_role_required
def api_mark_all_notifications_read():
    """Mark all notifications as read."""
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    return jsonify({'success': True})

# Task Management API Endpoints
@production.route('/api/tasks/<int:task_id>/assign', methods=['POST'])
@login_required
@permission_required('manage_tasks')
def api_assign_task(task_id):
    """Assign a task to a user."""
    data = request.get_json()
    assigned_to = data.get('assigned_to')
    
    task = ProductionTask.query.get_or_404(task_id)
    
    if assigned_to:
        user = User.query.get(assigned_to)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        old_assignee = task.assigned_to
        task.assigned_to = assigned_to
        task.assigned_by = current_user.id
        db.session.commit()
        
        # Create notification for assigned user
        create_notification(
            user_id=assigned_to,
            notification_type='task_assigned',
            title='New Task Assigned',
            message=f'You have been assigned task: "{task.title}"',
            related_id=task.id
        )
        
        # Log the assignment
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='assign',
            user_id=current_user.id,
            field_name='assigned_to',
            old_value=str(old_assignee) if old_assignee else None,
            new_value=str(assigned_to),
            description=f'Task assigned to {user.get_full_name()}'
        )
        
        return jsonify({'success': True, 'message': f'Task assigned to {user.get_full_name()}'})
    
    return jsonify({'error': 'No user specified'}), 400

@production.route('/api/tasks/<int:task_id>/status', methods=['POST'])
@login_required
@permission_required('manage_tasks')
def api_update_task_status(task_id):
    """Update task status."""
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['pending', 'in_progress', 'completed', 'cancelled']:
        return jsonify({'error': 'Invalid status'}), 400
    
    task = ProductionTask.query.get_or_404(task_id)
    old_status = task.status
    task.status = new_status
    
    if new_status == 'completed':
        task.completed_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    # Create notification for task creator/assigner
    if task.assigned_by and task.assigned_by != current_user.id:
        create_notification(
            user_id=task.assigned_by,
            notification_type='task_completed' if new_status == 'completed' else 'task_status_change',
            title=f'Task Status Updated',
            message=f'Task "{task.title}" status changed to {new_status.replace("_", " ").title()}',
            related_id=task.id
        )
    
    # Log the status change
    log_task_audit(
        task_id=task_id,
        task_type='production_task',
        operation='status_change',
        user_id=current_user.id,
        field_name='status',
        old_value=old_status,
        new_value=new_status,
        description=f'Task status changed from {old_status} to {new_status}'
    )
    
    return jsonify({'success': True, 'message': f'Task status updated to {new_status}'})

# User Online Status API
@production.route('/api/users/online')
@login_required
@production_role_required
def api_online_users():
    """Get online users."""
    online_users = UserOnlineStatus.query.filter_by(is_online=True).all()
    
    user_data = []
    for status in online_users:
        user_data.append({
            'user_id': status.user_id,
            'username': status.user.username,
            'full_name': status.user.get_full_name(),
            'last_seen': status.last_seen.isoformat()
        })
    
    return jsonify({'online_users': user_data})

@production.route('/api/users/update-status', methods=['POST'])
@login_required
@production_role_required
def api_update_user_status():
    """Update user's online status."""
    try:
        data = request.get_json()
        if data is None:
            # Try form data if JSON is not available
            data = request.form.to_dict()
        
        is_online = data.get('is_online', True)
        if isinstance(is_online, str):
            is_online = is_online.lower() == 'true'
        
        update_user_online_status(current_user.id, is_online)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# AI-Powered Endpoints
@production.route('/api/ai/audit-analysis')
@login_required
@production_role_required
def api_audit_analysis():
    """Get AI-powered audit analysis for the current user."""
    try:
        # Get recent audit logs for the user
        recent_logs = TaskAuditLog.query.filter_by(user_id=current_user.id)\
            .order_by(TaskAuditLog.created_at.desc())\
            .limit(50).all()
        
        # Convert to dict format for AI analysis
        audit_logs = []
        for log in recent_logs:
            audit_logs.append({
                'id': log.id,
                'task_id': log.task_id,
                'task_type': log.task_type,
                'operation': log.operation,
                'field_name': log.field_name,
                'old_value': log.old_value,
                'new_value': log.new_value,
                'description': log.description,
                'created_at': log.created_at.isoformat()
            })
        
        # Get user statistics
        user_stats = {
            'total_tasks': ProductionTask.query.filter_by(assigned_to=current_user.id).count(),
            'completed_tasks': ProductionTask.query.filter_by(assigned_to=current_user.id, status='completed').count(),
            'pending_tasks': ProductionTask.query.filter_by(assigned_to=current_user.id, status='pending').count(),
            'in_progress_tasks': ProductionTask.query.filter_by(assigned_to=current_user.id, status='in_progress').count(),
            'total_active_time': ProductionActivity.query.filter_by(user_id=current_user.id).with_entities(db.func.sum(ProductionActivity.duration_seconds)).scalar() or 0
        }
        
        # Get AI analysis
        analysis = ai_service.analyze_audit_logs(audit_logs, user_stats)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'log_count': len(audit_logs)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/ai/suggest-assignee', methods=['POST'])
@login_required
@permission_required('manage_tasks')
def api_suggest_assignee():
    """Get AI-powered task assignment suggestions."""
    try:
        data = request.get_json()
        task_data = data.get('task', {})
        
        # Get available users (excluding current user if they're not a manager)
        if current_user.has_permission('manage_tasks'):
            available_users = User.query.filter(User.is_active == True).all()
        else:
            available_users = [current_user]
        
        # Convert users to dict format for AI analysis
        users_data = []
        for user in available_users:
            user_tasks = ProductionTask.query.filter_by(assigned_to=user.id, status='in_progress').count()
            completed_tasks = ProductionTask.query.filter_by(assigned_to=user.id, status='completed').count()
            
            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'role': user.role.name if user.role else 'Unknown',
                'current_task_count': user_tasks,
                'completed_task_count': completed_tasks,
                'is_active': user.is_active
            })
        
        # Get AI suggestion
        suggestion = ai_service.suggest_task_assignee(task_data, users_data)
        
        return jsonify({
            'success': True,
            'suggestion': suggestion,
            'available_users': users_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/ai/task-summary/<int:task_id>')
@login_required
@production_role_required
def api_task_summary(task_id):
    """Get AI-generated task summary."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Get related activities
        related_activities = TaskAuditLog.query.filter_by(task_id=task_id).all()
        
        # Convert to dict format
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'assigned_to': task.assigned_to,
            'created_at': task.created_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        }
        
        activities_data = []
        for activity in related_activities:
            activities_data.append({
                'operation': activity.operation,
                'field_name': activity.field_name,
                'old_value': activity.old_value,
                'new_value': activity.new_value,
                'description': activity.description,
                'created_at': activity.created_at.isoformat()
            })
        
        # Generate AI summary
        summary = ai_service.generate_task_summary(task_data, activities_data)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'task': task_data,
            'activities_count': len(activities_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/ai/productivity-analysis')
@login_required
@production_role_required
def api_productivity_analysis():
    """Get AI-powered productivity analysis for the current user."""
    try:
        # Get user activities from the last 7 days
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        activities = ProductionActivity.query.filter(
            ProductionActivity.user_id == current_user.id,
            ProductionActivity.created_at >= week_ago
        ).all()
        
        # Convert to dict format for AI analysis
        activities_data = []
        for activity in activities:
            activities_data.append({
                'id': activity.id,
                'activity_type': activity.activity_type,
                'application_name': activity.application_name,
                'duration_seconds': activity.duration_seconds,
                'mouse_clicks': activity.mouse_clicks,
                'keyboard_strokes': activity.keyboard_strokes,
                'productivity_score': activity.productivity_score,
                'session_start': activity.session_start.isoformat(),
                'session_end': activity.session_end.isoformat() if activity.session_end else None,
                'created_at': activity.created_at.isoformat()
            })
        
        # Get AI analysis
        analysis = ai_service.analyze_productivity_patterns(activities_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'activities_count': len(activities_data),
            'analysis_period': '7 days'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/ai/smart-search', methods=['POST'])
@login_required
@production_role_required
def api_smart_search():
    """AI-powered natural language search for tasks and activities."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Get all user's tasks
        user_tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).all()
        
        # Prepare task data for AI analysis
        tasks_data = []
        for task in user_tasks:
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'created_at': task.created_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            })
        
        # Use AI to interpret the query and find relevant tasks
        prompt = f"""
        Search query: "{query}"
        
        Available tasks:
        {json.dumps(tasks_data, indent=2)}
        
        Find tasks that match the search query. Consider:
        - Task title and description
        - Status, priority, and due dates
        - Time-based queries (e.g., "last week", "overdue")
        - Status-based queries (e.g., "pending", "completed")
        
        Return JSON with:
        - matching_task_ids: array of task IDs that match
        - reason: explanation of why these tasks match
        - confidence_score: number (0-100)
        """
        
        # For now, implement a simple keyword search as fallback
        matching_tasks = []
        query_lower = query.lower()
        
        for task in user_tasks:
            if (query_lower in task.title.lower() or 
                (task.description and query_lower in task.description.lower()) or
                query_lower in task.status.lower() or
                query_lower in task.priority.lower()):
                matching_tasks.append(task.id)
        
        return jsonify({
            'success': True,
            'matching_task_ids': matching_tasks,
            'reason': f'Found {len(matching_tasks)} tasks matching "{query}"',
            'confidence_score': 80.0,
            'query': query
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Task Dependency Management API Endpoints

@production.route('/api/tasks/<int:task_id>/dependencies', methods=['GET'])
@login_required
@production_role_required
def api_get_task_dependencies(task_id):
    """Get all dependencies for a specific task."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Get forward dependencies (tasks this task depends on)
        forward_deps = TaskDependency.query.filter_by(dependent_task_id=task_id).all()
        
        # Get backward dependencies (tasks that depend on this task)
        backward_deps = TaskDependency.query.filter_by(prerequisite_task_id=task_id).all()
        
        # Format dependencies for response
        forward_data = []
        for dep in forward_deps:
            prerequisite_task = ProductionTask.query.get(dep.prerequisite_task_id)
            if prerequisite_task:
                forward_data.append({
                    'id': dep.id,
                    'prerequisite_task_id': dep.prerequisite_task_id,
                    'prerequisite_task_title': prerequisite_task.title,
                    'prerequisite_task_status': prerequisite_task.status,
                    'dependency_type': dep.dependency_type,
                    'lag_hours': dep.lag_hours,
                    'created_at': dep.created_at.isoformat()
                })
        
        backward_data = []
        for dep in backward_deps:
            dependent_task = ProductionTask.query.get(dep.dependent_task_id)
            if dependent_task:
                backward_data.append({
                    'id': dep.id,
                    'dependent_task_id': dep.dependent_task_id,
                    'dependent_task_title': dependent_task.title,
                    'dependent_task_status': dependent_task.status,
                    'dependency_type': dep.dependency_type,
                    'lag_hours': dep.lag_hours,
                    'created_at': dep.created_at.isoformat()
                })
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'task_title': task.title,
            'forward_dependencies': forward_data,  # Tasks this task depends on
            'backward_dependencies': backward_data,  # Tasks that depend on this task
            'is_blocked': task.is_blocked(),
            'earliest_start_date': task.get_earliest_start_date().isoformat() if task.get_earliest_start_date() else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/tasks/<int:task_id>/dependencies', methods=['POST'])
@login_required
@permission_required('manage_tasks')
def api_add_task_dependency(task_id):
    """Add a dependency to a task."""
    try:
        data = request.get_json()
        prerequisite_task_id = data.get('prerequisite_task_id')
        dependency_type = data.get('dependency_type', 'finish_to_start')
        lag_hours = data.get('lag_hours', 0.0)
        
        if not prerequisite_task_id:
            return jsonify({'error': 'Prerequisite task ID is required'}), 400
        
        # Check if tasks exist
        task = ProductionTask.query.get_or_404(task_id)
        prerequisite_task = ProductionTask.query.get_or_404(prerequisite_task_id)
        
        # Prevent self-dependency
        if task_id == prerequisite_task_id:
            return jsonify({'error': 'Task cannot depend on itself'}), 400
        
        # Check for circular dependencies
        if would_create_circular_dependency(task_id, prerequisite_task_id):
            return jsonify({'error': 'Adding this dependency would create a circular dependency'}), 400
        
        # Create dependency
        dependency = TaskDependency(
            dependent_task_id=task_id,
            prerequisite_task_id=prerequisite_task_id,
            dependency_type=dependency_type,
            lag_hours=lag_hours,
            created_by=current_user.id
        )
        
        db.session.add(dependency)
        db.session.commit()
        
        # Log the audit
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='add_dependency',
            user_id=current_user.id,
            description=f'Added dependency on task {prerequisite_task_id} ({prerequisite_task.title})'
        )
        
        return jsonify({
            'success': True,
            'message': f'Dependency added successfully',
            'dependency_id': dependency.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@production.route('/api/tasks/dependencies/<int:dependency_id>', methods=['DELETE'])
@login_required
@permission_required('manage_tasks')
def api_remove_task_dependency(dependency_id):
    """Remove a task dependency."""
    try:
        dependency = TaskDependency.query.get_or_404(dependency_id)
        
        # Log before deletion
        task = ProductionTask.query.get(dependency.dependent_task_id)
        prerequisite_task = ProductionTask.query.get(dependency.prerequisite_task_id)
        
        db.session.delete(dependency)
        db.session.commit()
        
        # Log the audit
        log_task_audit(
            task_id=dependency.dependent_task_id,
            task_type='production_task',
            operation='remove_dependency',
            user_id=current_user.id,
            description=f'Removed dependency on task {dependency.prerequisite_task_id} ({prerequisite_task.title if prerequisite_task else "Unknown"})'
        )
        
        return jsonify({
            'success': True,
            'message': 'Dependency removed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@production.route('/api/tasks/gantt-data')
@login_required
@production_role_required
def api_gantt_data():
    """Get all tasks formatted for Gantt chart display."""
    try:
        # Get all tasks for the current user or all tasks if user is manager
        if current_user.has_permission('manage_tasks'):
            tasks = ProductionTask.query.all()
        else:
            tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).all()
        
        # Get all dependencies
        dependencies = TaskDependency.query.all()
        
        # Format tasks for Gantt chart
        gantt_tasks = []
        for task in tasks:
            gantt_task = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'assigned_to': task.assigned_to,
                'assigned_to_name': task.assignee.get_full_name() if task.assignee else 'Unassigned',
                'start_date': task.start_date.isoformat() if task.start_date else task.created_at.date().isoformat(),
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'estimated_duration_hours': task.estimated_duration_hours,
                'actual_duration_hours': task.actual_duration_hours,
                'project_id': task.project_id,
                'workflow_stage': task.workflow_stage,
                'is_blocked': task.is_blocked(),
                'earliest_start_date': task.get_earliest_start_date().isoformat() if task.get_earliest_start_date() else None
            }
            gantt_tasks.append(gantt_task)
        
        # Format dependencies for Gantt chart
        gantt_dependencies = []
        for dep in dependencies:
            gantt_dep = {
                'id': dep.id,
                'from': dep.prerequisite_task_id,
                'to': dep.dependent_task_id,
                'type': dep.dependency_type,
                'lag_hours': dep.lag_hours
            }
            gantt_dependencies.append(gantt_dep)
        
        return jsonify({
            'success': True,
            'tasks': gantt_tasks,
            'dependencies': gantt_dependencies
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def would_create_circular_dependency(task_id, prerequisite_task_id):
    """Check if adding a dependency would create a circular dependency."""
    # Simple check: if prerequisite_task_id depends on task_id (directly or indirectly)
    visited = set()
    
    def check_dependency_chain(current_task_id, target_task_id):
        if current_task_id == target_task_id:
            return True
        
        if current_task_id in visited:
            return False
        
        visited.add(current_task_id)
        
        # Get all tasks that current_task_id depends on
        dependencies = TaskDependency.query.filter_by(dependent_task_id=current_task_id).all()
        
        for dep in dependencies:
            if check_dependency_chain(dep.prerequisite_task_id, target_task_id):
                return True
        
        return False
    
    return check_dependency_chain(prerequisite_task_id, task_id)

# Kanban Board API Endpoints

@production.route('/api/kanban/columns')
@login_required
@production_role_required
def api_kanban_columns():
    """Get Kanban board columns configuration."""
    columns = [
        {
            'id': 'backlog',
            'title': 'Backlog',
            'color': 'secondary',
            'icon': 'fas fa-inbox',
            'description': 'Tasks waiting to be started'
        },
        {
            'id': 'todo',
            'title': 'To Do',
            'color': 'primary',
            'icon': 'fas fa-list',
            'description': 'Tasks ready to be worked on'
        },
        {
            'id': 'in_progress',
            'title': 'In Progress',
            'color': 'info',
            'icon': 'fas fa-play',
            'description': 'Tasks currently being worked on'
        },
        {
            'id': 'review',
            'title': 'Review',
            'color': 'warning',
            'icon': 'fas fa-search',
            'description': 'Tasks ready for review'
        },
        {
            'id': 'completed',
            'title': 'Completed',
            'color': 'success',
            'icon': 'fas fa-check',
            'description': 'Tasks that are finished'
        }
    ]
    
    return jsonify({
        'success': True,
        'columns': columns
    })

@production.route('/api/kanban/tasks')
@login_required
@production_role_required
def api_kanban_tasks():
    """Get tasks for Kanban board."""
    try:
        # Get user's tasks
        tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).all()
        
        # Group tasks by status
        kanban_tasks = {
            'backlog': [],
            'todo': [],
            'in_progress': [],
            'review': [],
            'completed': []
        }
        
        for task in tasks:
            task_data = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'priority': task.priority,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'created_at': task.created_at.isoformat(),
                'estimated_duration_hours': task.estimated_duration_hours,
                'actual_duration_hours': task.actual_duration_hours,
                'is_blocked': task.is_blocked(),
                'workflow_stage': task.workflow_stage,
                'client_name': task.client_name,
                'attachments_count': len(task.attachments)
            }
            
            # Map task status to Kanban columns
            if task.status == 'pending':
                if task.workflow_stage == 'planning':
                    kanban_tasks['backlog'].append(task_data)
                else:
                    kanban_tasks['todo'].append(task_data)
            elif task.status == 'in_progress':
                if task.workflow_stage == 'review':
                    kanban_tasks['review'].append(task_data)
                else:
                    kanban_tasks['in_progress'].append(task_data)
            elif task.status == 'completed':
                kanban_tasks['completed'].append(task_data)
            else:
                kanban_tasks['backlog'].append(task_data)
        
        return jsonify({
            'success': True,
            'tasks': kanban_tasks
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/kanban/move-task', methods=['POST'])
@login_required
@permission_required('manage_tasks')
def api_move_task():
    """Move a task to a different column."""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        new_status = data.get('new_status')
        new_workflow_stage = data.get('new_workflow_stage')
        
        if not task_id or not new_status:
            return jsonify({'error': 'Task ID and new status are required'}), 400
        
        task = ProductionTask.query.get_or_404(task_id)
        
        # Check if user can modify this task
        if task.assigned_to != current_user.id and not current_user.has_permission('manage_tasks'):
            return jsonify({'error': 'You can only modify your own tasks'}), 403
        
        # Store old values for audit
        old_status = task.status
        old_workflow_stage = task.workflow_stage
        
        # Update task
        task.status = new_status
        if new_workflow_stage:
            task.workflow_stage = new_workflow_stage
        
        # Set completion time if moving to completed
        if new_status == 'completed' and old_status != 'completed':
            task.completed_at = datetime.now(timezone.utc)
        
        # Set start time if moving to in_progress
        if new_status == 'in_progress' and old_status != 'in_progress':
            task.start_date = date.today()
        
        task.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log the audit
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='status_change',
            user_id=current_user.id,
            field_name='status',
            old_value=old_status,
            new_value=new_status,
            description=f"Task moved from '{old_status}' to '{new_status}' via Kanban board"
        )
        
        return jsonify({
            'success': True,
            'message': f'Task moved to {new_status}',
            'task_id': task_id,
            'new_status': new_status,
            'new_workflow_stage': new_workflow_stage
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@production.route('/api/kanban/quick-edit', methods=['POST'])
@login_required
@permission_required('manage_tasks')
def api_quick_edit_task():
    """Quick edit task details from Kanban board."""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        field = data.get('field')
        value = data.get('value')
        
        if not task_id or not field:
            return jsonify({'error': 'Task ID and field are required'}), 400
        
        task = ProductionTask.query.get_or_404(task_id)
        
        # Check if user can modify this task
        if task.assigned_to != current_user.id and not current_user.has_permission('manage_tasks'):
            return jsonify({'error': 'You can only modify your own tasks'}), 403
        
        # Store old value for audit
        old_value = getattr(task, field, None)
        
        # Update the field
        if hasattr(task, field):
            setattr(task, field, value)
            task.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log the audit
            log_task_audit(
                task_id=task_id,
                task_type='production_task',
                operation='update',
                user_id=current_user.id,
                field_name=field,
                old_value=str(old_value) if old_value else None,
                new_value=str(value),
                description=f"Task {field} updated via Kanban board"
            )
            
            return jsonify({
                'success': True,
                'message': f'Task {field} updated',
                'task_id': task_id,
                'field': field,
                'value': value
            })
        else:
            return jsonify({'error': f'Field {field} does not exist'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 

@production.route('/api/kanban/ai-analyze-task', methods=['POST'])
@login_required
@production_role_required
def ai_analyze_task():
    """AI-powered task analysis and suggestions"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({'success': False, 'error': 'Task ID required'})
        
        task = ProductionTask.query.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'})
        
        # Perform AI analysis
        ai_result = ai_enhancer.analyze_task_priority(
            task_title=task.title,
            task_description=task.description or "",
            due_date=task.due_date.isoformat() if task.due_date else None,
            client_name=task.client_name or ""
        )
        
        if ai_result['success']:
            # Update task with AI analysis
            task.ai_priority = ai_result['priority']
            task.ai_priority_reasoning = ai_result['reasoning']
            task.ai_risk_level = ai_result['risk_level']
            task.ai_estimated_hours = ai_result['estimated_hours']
            task.set_ai_suggested_tags(ai_result['suggested_tags'])
            task.ai_confidence = ai_result['ai_confidence']
            task.ai_last_analyzed = datetime.now(timezone.utc)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'ai_analysis': task.get_ai_analysis_summary()
            })
        else:
            return jsonify({'success': False, 'error': ai_result.get('error', 'AI analysis failed')})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@production.route('/api/kanban/ai-suggest-assignee', methods=['POST'])
@login_required
@production_role_required
def ai_suggest_assignee():
    """AI-powered task assignment suggestions"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({'success': False, 'error': 'Task ID required'})
        
        task = ProductionTask.query.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'})
        
        # Get available editors (users with editor role)
        editors = User.query.filter_by(role='editor').all()
        
        # Build editor profiles for AI analysis
        editor_profiles = []
        for editor in editors:
            # Get editor's current workload
            current_tasks = ProductionTask.query.filter_by(assigned_to=editor.id, status='in_progress').count()
            
            # Get editor's average completion time (simplified)
            completed_tasks = ProductionTask.query.filter_by(assigned_to=editor.id, status='completed').all()
            avg_completion_hours = 4.0  # Default
            if completed_tasks:
                total_hours = sum(task.actual_duration_hours or 4.0 for task in completed_tasks)
                avg_completion_hours = total_hours / len(completed_tasks)
            
            editor_profile = {
                'id': editor.id,
                'name': editor.username,
                'skills': ['image-editing', 'color-correction', 'retouching'],  # Default skills
                'current_tasks': current_tasks,
                'avg_completion_hours': avg_completion_hours,
                'specializations': ['product-photography', 'portrait-retouching']  # Default specializations
            }
            editor_profiles.append(editor_profile)
        
        # Prepare task data for AI analysis
        task_data = {
            'title': task.title,
            'description': task.description or "",
            'priority': task.priority,
            'estimated_hours': task.estimated_duration_hours or 2.0
        }
        
        # Get AI suggestion
        ai_result = ai_enhancer.suggest_task_assignee(task_data, editor_profiles)
        
        if ai_result['success']:
            return jsonify({
                'success': True,
                'suggested_editor_id': ai_result['suggested_editor_id'],
                'reasoning': ai_result['reasoning'],
                'confidence_score': ai_result['confidence_score'],
                'alternative_editors': ai_result['alternative_editors']
            })
        else:
            return jsonify({'success': False, 'error': ai_result.get('error', 'AI suggestion failed')})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@production.route('/api/kanban/ai-deadline-risk', methods=['POST'])
@login_required
@production_role_required
def ai_deadline_risk():
    """AI-powered deadline risk analysis"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({'success': False, 'error': 'Task ID required'})
        
        task = ProductionTask.query.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'})
        
        # Get editor performance data
        editor_performance = {
            'avg_completion_hours': 4.0,  # Default
            'current_tasks': 0,
            'on_time_rate': 0.8  # Default 80%
        }
        
        if task.assigned_to:
            editor = User.query.get(task.assigned_to)
            if editor:
                # Calculate editor performance
                editor_tasks = ProductionTask.query.filter_by(assigned_to=editor.id).all()
                completed_tasks = [t for t in editor_tasks if t.status == 'completed']
                current_tasks = [t for t in editor_tasks if t.status == 'in_progress']
                
                if completed_tasks:
                    total_hours = sum(t.actual_duration_hours or 4.0 for t in completed_tasks)
                    editor_performance['avg_completion_hours'] = total_hours / len(completed_tasks)
                
                editor_performance['current_tasks'] = len(current_tasks)
                
                # Calculate on-time rate (simplified)
                on_time_tasks = len([t for t in completed_tasks if not t.is_overdue()])
                if completed_tasks:
                    editor_performance['on_time_rate'] = on_time_tasks / len(completed_tasks)
        
        # Prepare task data
        task_data = {
            'title': task.title,
            'estimated_hours': task.estimated_duration_hours or 2.0,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'priority': task.priority,
            'status': task.status
        }
        
        # Get AI risk analysis
        ai_result = ai_enhancer.detect_deadline_risk(task_data, editor_performance)
        
        if ai_result['success']:
            # Update task with AI risk analysis
            task.ai_deadline_risk_level = ai_result['risk_level']
            task.ai_deadline_risk_probability = ai_result['delay_probability']
            db.session.commit()
            
            return jsonify({
                'success': True,
                'risk_level': ai_result['risk_level'],
                'delay_probability': ai_result['delay_probability'],
                'recommended_actions': ai_result['recommended_actions'],
                'alternative_solutions': ai_result['alternative_solutions']
            })
        else:
            return jsonify({'success': False, 'error': ai_result.get('error', 'AI risk analysis failed')})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@production.route('/api/kanban/ai-activity-summary', methods=['GET'])
@login_required
@production_role_required
def ai_activity_summary():
    """AI-powered activity summary for the Kanban board"""
    try:
        # Get all tasks for current user
        user_tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).all()
        
        # Organize tasks by status/column
        board_data = {
            'tasks': {
                'backlog': [],
                'todo': [],
                'in_progress': [],
                'review': [],
                'completed': []
            }
        }
        
        for task in user_tasks:
            # Map task status to column
            if task.status == 'pending':
                if task.workflow_stage == 'planning':
                    board_data['tasks']['backlog'].append({
                        'id': task.id,
                        'title': task.title,
                        'priority': task.priority,
                        'due_date': task.due_date.isoformat() if task.due_date else '',
                        'completed_at': task.completed_at.isoformat() if task.completed_at else ''
                    })
                else:
                    board_data['tasks']['todo'].append({
                        'id': task.id,
                        'title': task.title,
                        'priority': task.priority,
                        'due_date': task.due_date.isoformat() if task.due_date else ''
                    })
            elif task.status == 'in_progress':
                if task.workflow_stage == 'review':
                    board_data['tasks']['review'].append({
                        'id': task.id,
                        'title': task.title,
                        'priority': task.priority,
                        'due_date': task.due_date.isoformat() if task.due_date else ''
                    })
                else:
                    board_data['tasks']['in_progress'].append({
                        'id': task.id,
                        'title': task.title,
                        'priority': task.priority,
                        'due_date': task.due_date.isoformat() if task.due_date else ''
                    })
            elif task.status == 'completed':
                board_data['tasks']['completed'].append({
                    'id': task.id,
                    'title': task.title,
                    'priority': task.priority,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else ''
                })
        
        # Get AI activity summary
        ai_result = ai_enhancer.generate_activity_summary(board_data)
        
        if ai_result['success']:
            return jsonify({
                'success': True,
                'summary': ai_result['summary'],
                'insights': ai_result['insights'],
                'bottlenecks': ai_result['bottlenecks'],
                'recommendations': ai_result['recommendations'],
                'priority_actions': ai_result['priority_actions']
            })
        else:
            return jsonify({'success': False, 'error': ai_result.get('error', 'AI summary generation failed')})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}) 

# Media Handling Routes
@production.route('/media-gallery')
@login_required
@production_role_required
def media_gallery():
    """Media gallery page with tabs for different media types."""
    return render_template('production/media_gallery.html')

@production.route('/api/media/gallery')
@login_required
@production_role_required
def api_media_gallery():
    """Get media items for gallery view."""
    media_type = request.args.get('type', 'all')
    room = request.args.get('room', 'general')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    from .models import ChatMedia
    
    query = ChatMedia.query.join(ChatMessage).filter(ChatMessage.room == room)
    
    if media_type != 'all':
        query = query.filter(ChatMedia.media_type == media_type)
    
    # Get total count
    total_count = query.count()
    
    # Paginate results
    media_items = query.order_by(ChatMedia.uploaded_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    # Format response
    media_data = []
    for media in media_items:
        media_data.append({
            'id': media.id,
            'file_name': media.file_name,
            'original_filename': media.original_filename,
            'file_path': media.file_path,
            'file_size': media.get_file_size_mb(),
            'file_type': media.file_type,
            'media_type': media.media_type,
            'thumbnail_path': media.thumbnail_path,
            'duration': media.duration,
            'width': media.width,
            'height': media.height,
            'uploaded_by': media.uploader.get_full_name(),
            'uploaded_at': media.uploaded_at.isoformat(),
            'link_url': media.link_url,
            'link_title': media.link_title,
            'link_description': media.link_description,
            'link_image': media.link_image,
            'icon': media.get_media_icon(),
            'color': media.get_media_color()
        })
    
    return jsonify({
        'media_items': media_data,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    })

@production.route('/api/media/upload', methods=['POST'])
@login_required
@production_role_required
def api_media_upload():
    """Upload media files for chat."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large (max 50MB)'}), 400
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Determine media type
        file_ext = filename.rsplit('.', 1)[1].lower()
        media_type = 'document'
        if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
            media_type = 'image'
        elif file_ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
            media_type = 'video'
        elif file_ext in ['mp3', 'wav', 'ogg', 'aac', 'flac']:
            media_type = 'audio'
        
        # Create upload directory
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'chat', 'media')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Get file info
        file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        # Create media record
        from .models import ChatMedia, ChatMessage
        
        # Create a placeholder message for the media
        message = ChatMessage(
            sender_id=current_user.id,
            content=f"Shared {filename}",
            message_type='file',
            file_url=f'/static/uploads/chat/media/{unique_filename}',
            file_name=unique_filename,
            file_size=file_size,
            room='general'
        )
        db.session.add(message)
        db.session.flush()  # Get the message ID
        
        # Create media record
        media = ChatMedia(
            message_id=message.id,
            file_name=unique_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            media_type=media_type,
            uploaded_by=current_user.id
        )
        db.session.add(media)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'media_id': media.id,
            'message_id': message.id,
            'file_name': filename,
            'file_url': f'/static/uploads/chat/media/{unique_filename}',
            'media_type': media_type,
            'file_size': media.get_file_size_mb()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@production.route('/api/media/link-preview', methods=['POST'])
@login_required
@production_role_required
def api_link_preview():
    """Generate preview for shared links."""
    try:
        data = request.get_json()
        link_url = data.get('url')
        
        if not link_url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Basic link preview (in a real app, you'd use a service like OpenGraph)
        import re
        
        # Extract domain
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', link_url)
        domain = domain_match.group(1) if domain_match else 'Unknown'
        
        # Create placeholder preview
        preview_data = {
            'url': link_url,
            'title': f'Link from {domain}',
            'description': f'Shared link from {domain}',
            'image': None
        }
        
        return jsonify({
            'success': True,
            'preview': preview_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/media/download/<int:media_id>')
@login_required
@production_role_required
def api_media_download(media_id):
    """Download a media file."""
    from .models import ChatMedia
    
    media = ChatMedia.query.get_or_404(media_id)
    
    if not os.path.exists(media.file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(
        media.file_path,
        as_attachment=True,
        download_name=media.original_filename
    )

@production.route('/api/media/delete/<int:media_id>', methods=['DELETE'])
@login_required
@production_role_required
def api_media_delete(media_id):
    """Delete a media file."""
    from .models import ChatMedia
    
    media = ChatMedia.query.get_or_404(media_id)
    
    # Check permissions (only uploader or admin can delete)
    if media.uploaded_by != current_user.id and not current_user.has_permission('manage_tasks'):
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # Delete file from filesystem
        if os.path.exists(media.file_path):
            os.remove(media.file_path)
        
        # Delete thumbnail if exists
        if media.thumbnail_path and os.path.exists(media.thumbnail_path):
            os.remove(media.thumbnail_path)
        
        # Delete from database
        db.session.delete(media)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 

@production.route('/api/tasks/create-from-message', methods=['POST'])
@login_required
@production_role_required
def api_create_task_from_message():
    """Create a task from a chat message"""
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        title = data.get('title')
        description = data.get('description')
        task_type = data.get('task_type', 'chat_followup')
        priority = data.get('priority', 'medium')
        due_date_str = data.get('due_date')
        assigned_to = data.get('assigned_to', current_user.id)
        
        if not all([message_id, title]):
            return jsonify({'success': False, 'error': 'Message ID and title are required'}), 400
        
        # Get the original message
        message = ChatMessage.query.get(message_id)
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Create the task
        task = UserTask(
            user_id=assigned_to,
            assigned_by=current_user.id,
            title=title,
            description=description or f"Task created from chat message: {message.content[:100]}...",
            task_type=task_type,
            priority=priority,
            due_date=due_date
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Log task creation
        from app.routes import log_task_audit
        log_task_audit(
            task_id=task.id,
            task_type='user_task',
            operation='create',
            user_id=current_user.id,
            description=f"Task '{title}' created from chat message ID {message_id}",
            request_data=data
        )
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Task created successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/reminders/create-from-message', methods=['POST'])
@login_required
@production_role_required
def api_create_reminder_from_message():
    """Create a reminder from a chat message"""
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        title = data.get('title')
        description = data.get('description')
        reminder_time_str = data.get('reminder_time')
        
        if not all([message_id, title, reminder_time_str]):
            return jsonify({'success': False, 'error': 'Message ID, title, and reminder time are required'}), 400
        
        # Get the original message
        message = ChatMessage.query.get(message_id)
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Parse reminder time
        try:
            reminder_time = datetime.fromisoformat(reminder_time_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid reminder time format'}), 400
        
        # Create the reminder
        reminder = ChatReminder(
            message_id=message_id,
            user_id=current_user.id,
            title=title,
            description=description or f"Reminder from chat message: {message.content[:100]}...",
            reminder_time=reminder_time
        )
        
        db.session.add(reminder)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'reminder_id': reminder.id,
            'message': 'Reminder created successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/reminders/list')
@login_required
@production_role_required
def api_reminders_list():
    """Get user's reminders"""
    try:
        reminders = ChatReminder.query.filter_by(user_id=current_user.id).order_by(ChatReminder.reminder_time.asc()).all()
        
        reminders_data = []
        for reminder in reminders:
            reminders_data.append({
                'id': reminder.id,
                'title': reminder.title,
                'description': reminder.description,
                'reminder_time': reminder.reminder_time.isoformat(),
                'is_completed': reminder.is_completed,
                'completed_at': reminder.completed_at.isoformat() if reminder.completed_at else None,
                'status': reminder.get_status(),
                'message_content': reminder.message.content if reminder.message else '',
                'created_at': reminder.created_at.isoformat()
            })
        
        return jsonify({'reminders': reminders_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/reminders/<int:reminder_id>/complete', methods=['POST'])
@login_required
@production_role_required
def api_complete_reminder(reminder_id):
    """Mark a reminder as completed"""
    try:
        reminder = ChatReminder.query.get_or_404(reminder_id)
        
        # Check if user owns this reminder
        if reminder.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        reminder.mark_completed()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reminder marked as completed!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/reminders/<int:reminder_id>/delete', methods=['DELETE'])
@login_required
@production_role_required
def api_delete_reminder(reminder_id):
    """Delete a reminder"""
    try:
        reminder = ChatReminder.query.get_or_404(reminder_id)
        
        # Check if user owns this reminder
        if reminder.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        db.session.delete(reminder)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reminder deleted successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/messages/schedule', methods=['POST'])
@login_required
@production_role_required
def api_schedule_message():
    """Schedule a message to be sent later"""
    try:
        data = request.get_json()
        content = data.get('content')
        scheduled_time_str = data.get('scheduled_time')
        room = data.get('room', 'general')
        
        if not all([content, scheduled_time_str]):
            return jsonify({'success': False, 'error': 'Content and scheduled time are required'}), 400
        
        # Parse scheduled time
        try:
            scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid scheduled time format'}), 400
        
        # Check if scheduled time is in the future
        if scheduled_time <= datetime.now(timezone.utc):
            return jsonify({'success': False, 'error': 'Scheduled time must be in the future'}), 400
        
        # Create the scheduled message
        scheduled_message = ScheduledMessage(
            sender_id=current_user.id,
            room=room,
            content=content,
            scheduled_time=scheduled_time
        )
        
        db.session.add(scheduled_message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'scheduled_message_id': scheduled_message.id,
            'message': 'Message scheduled successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/messages/scheduled')
@login_required
@production_role_required
def api_scheduled_messages():
    """Get user's scheduled messages"""
    try:
        scheduled_messages = ScheduledMessage.query.filter_by(sender_id=current_user.id).order_by(ScheduledMessage.scheduled_time.asc()).all()
        
        messages_data = []
        for msg in scheduled_messages:
            messages_data.append({
                'id': msg.id,
                'content': msg.content,
                'room': msg.room,
                'scheduled_time': msg.scheduled_time.isoformat(),
                'is_sent': msg.is_sent,
                'sent_at': msg.sent_at.isoformat() if msg.sent_at else None,
                'status': msg.get_status(),
                'created_at': msg.created_at.isoformat()
            })
        
        return jsonify({'scheduled_messages': messages_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@production.route('/api/messages/scheduled/<int:message_id>/cancel', methods=['DELETE'])
@login_required
@production_role_required
def api_cancel_scheduled_message(message_id):
    """Cancel a scheduled message"""
    try:
        scheduled_message = ScheduledMessage.query.get_or_404(message_id)
        
        # Check if user owns this message
        if scheduled_message.sender_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Check if message is already sent
        if scheduled_message.is_sent:
            return jsonify({'success': False, 'error': 'Cannot cancel already sent message'}), 400
        
        db.session.delete(scheduled_message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Scheduled message cancelled successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Group Management API Endpoints
@production.route('/api/groups', methods=['GET'])
@login_required
@production_role_required
def api_groups_list():
    """Get list of chat groups user is member of or can join - team-based filtering."""
    try:
        # Get user's teams
        user_teams = current_user.get_teams()
        team_ids = [team.id for team in user_teams]
        
        # Get groups where user is a member (filtered by team)
        user_groups_query = ChatGroupMember.query.filter_by(
            user_id=current_user.id, 
            is_active=True
        ).join(ChatGroup)
        
        # Filter by user's teams if user has teams
        if team_ids:
            user_groups_query = user_groups_query.filter(ChatGroup.team_id.in_(team_ids))
        
        user_groups = user_groups_query.all()
        
        # Get public groups user is not member of (filtered by team)
        member_group_ids = [mg.group_id for mg in user_groups]
        public_groups_query = ChatGroup.query.filter(
            ChatGroup.is_public == True,
            ChatGroup.is_archived == False,
            ~ChatGroup.id.in_(member_group_ids)
        )
        
        # Filter public groups by user's teams if user has teams
        if team_ids:
            public_groups_query = public_groups_query.filter(ChatGroup.team_id.in_(team_ids))
        
        public_groups = public_groups_query.all()
        
        groups_data = []
        
        # Add user's groups
        for member in user_groups:
            group = member.group
            groups_data.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'avatar_url': group.avatar_url,
                'is_public': group.is_public,
                'is_archived': group.is_archived,
                'member_count': group.get_member_count(),
                'user_role': member.role,
                'user_permissions': member.permissions,
                'is_muted': member.is_muted,
                'joined_at': member.joined_at.isoformat(),
                'created_at': group.created_at.isoformat(),
                'created_by': {
                    'id': group.creator.id,
                    'name': group.creator.get_full_name()
                }
            })
        
        # Add public groups
        for group in public_groups:
            groups_data.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'avatar_url': group.avatar_url,
                'is_public': group.is_public,
                'is_archived': group.is_archived,
                'member_count': group.get_member_count(),
                'user_role': None,
                'user_permissions': None,
                'is_muted': False,
                'joined_at': None,
                'created_at': group.created_at.isoformat(),
                'created_by': {
                    'id': group.creator.id,
                    'name': group.creator.get_full_name()
                }
            })
        
        return jsonify({'groups': groups_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@production.route('/api/groups', methods=['POST'])
@login_required
@production_role_required
def api_create_group():
    """Create a new chat group with team-based access."""
    try:
        # Check if user has permission to create groups (managers only)
        if not current_user.role or current_user.role.name not in ['productions_manager', 'marketing_manager', 'admin']:
            return jsonify({'success': False, 'error': 'Only managers can create groups'}), 403
        
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        is_public = data.get('is_public', True)
        allow_guest_messages = data.get('allow_guest_messages', True)
        team_id = data.get('team_id')  # Get team_id from request
        member_ids = data.get('member_ids', [])  # Get selected member IDs
        
        if not name:
            return jsonify({'success': False, 'error': 'Group name is required'}), 400
        
        # Get user's teams for validation
        user_teams = current_user.get_teams()
        user_team_ids = [team.id for team in user_teams]
        
        # If team_id is provided, validate user has access to that team
        if team_id and team_id not in user_team_ids:
            return jsonify({'success': False, 'error': 'Access denied to this team'}), 403
        
        # If no team_id provided, use user's primary team
        if not team_id and user_team_ids:
            team_id = user_team_ids[0]  # Use first team as primary
        
        # Create the group with team information
        group = ChatGroup(
            name=name,
            description=description,
            is_public=is_public,
            allow_guest_messages=allow_guest_messages,
            created_by=current_user.id,
            team_id=team_id
        )
        db.session.add(group)
        db.session.flush()  # Get the group ID
        
        # Add creator as admin
        creator_member = ChatGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            role='admin',
            is_active=True
        )
        db.session.add(creator_member)
        
        # Add selected team members
        if member_ids:
            # Validate that all member_ids belong to the same team
            team_members = User.query.join(UserTeam).filter(
                UserTeam.team_id == team_id,
                User.id.in_(member_ids)
            ).all()
            
            for user in team_members:
                # Skip if user is already added (creator)
                if user.id == current_user.id:
                    continue
                    
                member = ChatGroupMember(
                    group_id=group.id,
                    user_id=user.id,
                    role='member',
                    is_active=True
                )
                db.session.add(member)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'group': {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'is_public': group.is_public,
                'allow_guest_messages': group.allow_guest_messages,
                'created_at': group.created_at.isoformat()
            },
            'message': 'Group created successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>', methods=['GET'])
@login_required
@production_role_required
def api_get_group(group_id):
    """Get detailed information about a specific group."""
    try:
        group = ChatGroup.query.get_or_404(group_id)
        
        # Check if user is member
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        # Get group members
        members_data = []
        for group_member in group.members:
            if group_member.is_active:
                members_data.append({
                    'id': group_member.user.id,
                    'name': group_member.user.get_full_name(),
                    'username': group_member.user.username,
                    'role': group_member.role,
                    'permissions': group_member.permissions,
                    'is_muted': group_member.is_muted,
                    'joined_at': group_member.joined_at.isoformat(),
                    'role_display': group_member.get_role_display_name(),
                    'role_color': group_member.get_role_color()
                })
        
        group_data = {
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'avatar_url': group.avatar_url,
            'is_public': group.is_public,
            'is_archived': group.is_archived,
            'allow_guest_messages': group.allow_guest_messages,
            'member_count': group.get_member_count(),
            'admin_count': group.get_admin_count(),
            'created_at': group.created_at.isoformat(),
            'created_by': {
                'id': group.creator.id,
                'name': group.creator.get_full_name()
            },
            'user_membership': {
                'is_member': member is not None,
                'role': member.role if member else None,
                'permissions': member.permissions if member else None,
                'is_muted': member.is_muted if member else False,
                'joined_at': member.joined_at.isoformat() if member else None
            },
            'members': members_data
        }
        
        return jsonify({'group': group_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>', methods=['PUT'])
@login_required
@production_role_required
def api_update_group(group_id):
    """Update group information (admin only)."""
    try:
        group = ChatGroup.query.get_or_404(group_id)
        
        # Check if user is admin
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not member or member.role != 'admin':
            return jsonify({'success': False, 'error': 'Only admins can update group information'}), 403
        
        data = request.get_json()
        
        if 'name' in data:
            group.name = data['name']
        if 'description' in data:
            group.description = data['description']
        if 'is_public' in data:
            group.is_public = data['is_public']
        if 'allow_guest_messages' in data:
            group.allow_guest_messages = data['allow_guest_messages']
        if 'is_archived' in data:
            group.is_archived = data['is_archived']
        
        group.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Group updated successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>/members', methods=['GET'])
@login_required
@production_role_required
def api_group_members(group_id):
    """Get group members."""
    try:
        group = ChatGroup.query.get_or_404(group_id)
        
        # Check if user is member or group is public
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not member and not group.is_public:
            return jsonify({'error': 'Access denied'}), 403
        
        members_data = []
        for group_member in group.members:
            if group_member.is_active:
                members_data.append({
                    'id': group_member.user.id,
                    'name': group_member.user.get_full_name(),
                    'username': group_member.user.username,
                    'role': group_member.role,
                    'permissions': group_member.permissions,
                    'is_muted': group_member.is_muted,
                    'joined_at': group_member.joined_at.isoformat(),
                    'role_display': group_member.get_role_display_name(),
                    'role_color': group_member.get_role_color()
                })
        
        return jsonify({'members': members_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>/members', methods=['POST'])
@login_required
@production_role_required
def api_add_group_member(group_id):
    """Add a member to the group (admin only)."""
    try:
        group = ChatGroup.query.get_or_404(group_id)
        
        # Check if user is admin
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not member or member.role != 'admin':
            return jsonify({'success': False, 'error': 'Only admins can add members'}), 403
        
        data = request.get_json()
        user_id = data.get('user_id')
        role = data.get('role', 'member')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Check if user is already a member
        existing_member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=user_id
        ).first()
        
        if existing_member:
            if existing_member.is_active:
                return jsonify({'success': False, 'error': 'User is already a member'}), 400
            else:
                # Reactivate member
                existing_member.is_active = True
                existing_member.role = role
                existing_member.left_at = None
                existing_member.joined_at = datetime.now(timezone.utc)
        else:
            # Create new member
            new_member = ChatGroupMember(
                group_id=group_id,
                user_id=user_id,
                role=role,
                invited_by=current_user.id,
                invitation_accepted_at=datetime.now(timezone.utc)
            )
            db.session.add(new_member)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User {user.get_full_name()} added to group successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>/members/<int:user_id>', methods=['PUT'])
@login_required
@production_role_required
def api_update_group_member(group_id, user_id):
    """Update member role or permissions (admin only)."""
    try:
        group = ChatGroup.query.get_or_404(group_id)
        
        # Check if user is admin
        admin_member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not admin_member or admin_member.role != 'admin':
            return jsonify({'success': False, 'error': 'Only admins can update members'}), 403
        
        # Get the member to update
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=user_id,
            is_active=True
        ).first()
        
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        
        data = request.get_json()
        
        if 'role' in data:
            member.role = data['role']
        if 'permissions' in data:
            member.permissions = data['permissions']
        if 'is_muted' in data:
            member.is_muted = data['is_muted']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Member updated successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
@production_role_required
def api_remove_group_member(group_id, user_id):
    """Remove a member from the group (admin only or self-removal)."""
    try:
        group = ChatGroup.query.get_or_404(group_id)
        
        # Get the member to remove
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=user_id,
            is_active=True
        ).first()
        
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        
        # Check permissions
        admin_member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        # Allow removal if user is admin or removing themselves
        if not (admin_member and admin_member.role == 'admin') and current_user.id != user_id:
            return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
        
        # Prevent removing the last admin
        if member.role == 'admin' and group.get_admin_count() <= 1:
            return jsonify({'success': False, 'error': 'Cannot remove the last admin'}), 400
        
        # Soft delete the member
        member.is_active = False
        member.left_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Member removed from group successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>/invitations', methods=['POST'])
@login_required
@production_role_required
def api_invite_to_group(group_id):
    """Invite a user to join the group (admin only)."""
    try:
        group = ChatGroup.query.get_or_404(group_id)
        
        # Check if user is admin
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not member or member.role != 'admin':
            return jsonify({'success': False, 'error': 'Only admins can send invitations'}), 403
        
        data = request.get_json()
        invited_user_id = data.get('user_id')
        role = data.get('role', 'member')
        message = data.get('message', '')
        
        if not invited_user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        # Check if user exists
        user = User.query.get(invited_user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Check if user is already a member
        existing_member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=invited_user_id,
            is_active=True
        ).first()
        
        if existing_member:
            return jsonify({'success': False, 'error': 'User is already a member'}), 400
        
        # Check if invitation already exists
        existing_invitation = ChatGroupInvitation.query.filter_by(
            group_id=group_id,
            invited_user_id=invited_user_id,
            status='pending'
        ).first()
        
        if existing_invitation:
            return jsonify({'success': False, 'error': 'Invitation already sent'}), 400
        
        # Create invitation
        invitation = ChatGroupInvitation(
            group_id=group_id,
            invited_user_id=invited_user_id,
            invited_by_id=current_user.id,
            role=role,
            message=message,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)  # 7 days expiry
        )
        db.session.add(invitation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Invitation sent to {user.get_full_name()} successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/invitations', methods=['GET'])
@login_required
@production_role_required
def api_user_invitations():
    """Get user's pending group invitations."""
    try:
        invitations = ChatGroupInvitation.query.filter_by(
            invited_user_id=current_user.id,
            status='pending'
        ).join(ChatGroup).all()
        
        invitations_data = []
        for invitation in invitations:
            if not invitation.is_expired():
                invitations_data.append({
                    'id': invitation.id,
                    'group': {
                        'id': invitation.group.id,
                        'name': invitation.group.name,
                        'description': invitation.group.description,
                        'avatar_url': invitation.group.avatar_url,
                        'member_count': invitation.group.get_member_count()
                    },
                    'role': invitation.role,
                    'message': invitation.message,
                    'expires_at': invitation.expires_at.isoformat() if invitation.expires_at else None,
                    'invited_by': {
                        'id': invitation.invited_by.id,
                        'name': invitation.invited_by.get_full_name()
                    },
                    'created_at': invitation.created_at.isoformat()
                })
        
        return jsonify({'invitations': invitations_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@production.route('/api/groups/invitations/<int:invitation_id>/accept', methods=['POST'])
@login_required
@production_role_required
def api_accept_invitation(invitation_id):
    """Accept a group invitation."""
    try:
        invitation = ChatGroupInvitation.query.get_or_404(invitation_id)
        
        # Check if invitation is for current user
        if invitation.invited_user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Check if invitation is still valid
        if invitation.status != 'pending' or invitation.is_expired():
            return jsonify({'success': False, 'error': 'Invitation is no longer valid'}), 400
        
        # Accept the invitation
        member = invitation.accept()
        if member:
            db.session.add(member)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully joined {invitation.group.name}!'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to accept invitation'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/invitations/<int:invitation_id>/decline', methods=['POST'])
@login_required
@production_role_required
def api_decline_invitation(invitation_id):
    """Decline a group invitation."""
    try:
        invitation = ChatGroupInvitation.query.get_or_404(invitation_id)
        
        # Check if invitation is for current user
        if invitation.invited_user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Check if invitation is still valid
        if invitation.status != 'pending':
            return jsonify({'success': False, 'error': 'Invitation is no longer valid'}), 400
        
        # Decline the invitation
        if invitation.decline():
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Invitation declined successfully!'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to decline invitation'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>/reports', methods=['POST'])
@login_required
@production_role_required
def api_report_group(group_id):
    """Report a group for moderation."""
    try:
        group = ChatGroup.query.get_or_404(group_id)
        
        data = request.get_json()
        report_type = data.get('report_type')
        description = data.get('description')
        evidence = data.get('evidence')
        
        if not report_type or not description:
            return jsonify({'success': False, 'error': 'Report type and description are required'}), 400
        
        # Create the report
        report = ChatGroupReport(
            group_id=group_id,
            reported_by_id=current_user.id,
            report_type=report_type,
            description=description,
            evidence=evidence
        )
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Report submitted successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/groups/<int:group_id>/mute', methods=['POST'])
@login_required
@production_role_required
def api_mute_group(group_id):
    """Mute/unmute group notifications for current user."""
    try:
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not member:
            return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403
        
        data = request.get_json()
        is_muted = data.get('is_muted', True)
        
        member.is_muted = is_muted
        db.session.commit()
        
        action = 'muted' if is_muted else 'unmuted'
        return jsonify({
            'success': True,
            'message': f'Group {action} successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# MESSENGER API ENDPOINTS
# ============================================================================

@production.route('/api/messenger/status', methods=['GET'])
@login_required
@production_role_required
def api_messenger_status():
    """Get current user's messenger status."""
    try:
        # Get or create user status
        status = UserOnlineStatus.query.filter_by(user_id=current_user.id).first()
        if not status:
            status = UserOnlineStatus(user_id=current_user.id, is_online=True)
            db.session.add(status)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'status': {
                'is_online': status.is_online,
                'last_seen': status.last_seen.isoformat() if status.last_seen else None,
                'status_message': None  # Not implemented in current model
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/users/online', methods=['GET'])
@login_required
@production_role_required
def api_messenger_online_users():
    """Get list of online users for messenger."""
    try:
        # Get online users with their details
        online_users = db.session.query(User, UserOnlineStatus).join(
            UserOnlineStatus, User.id == UserOnlineStatus.user_id
        ).filter(UserOnlineStatus.is_online == True).all()
        
        users_data = []
        for user, status in online_users:
            users_data.append({
                'id': user.id,
                'name': user.get_full_name(),
                'username': user.username,
                'avatar': user.profile_image if hasattr(user, 'profile_image') else None,
                'is_online': status.is_online,
                'last_seen': status.last_seen.isoformat() if status.last_seen else None,
                'status_message': None  # Not implemented in current model
            })
        
        return jsonify({
            'success': True,
            'users': users_data,
            'count': len(users_data)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/messages', methods=['GET'])
@login_required
@production_role_required
def api_messenger_messages():
    """Get messages for messenger with reactions and attachments - team-based filtering."""
    try:
        # Get user's teams
        user_teams = current_user.get_teams()
        team_ids = [team.id for team in user_teams]
        
        # Build query with team filtering
        query = db.session.query(ChatMessage, User).join(
            User, ChatMessage.sender_id == User.id
        ).filter(
            ChatMessage.is_deleted == False  # Only show non-deleted messages
        )
        
        # If user has teams, filter by team; otherwise show all (for admin users)
        if team_ids:
            query = query.filter(ChatMessage.team_id.in_(team_ids))
        
        # Get messages ordered by creation time
        messages = query.order_by(ChatMessage.created_at.asc()).limit(100).all()
        
        messages_data = []
        for message, sender in messages:
            # Get reactions for this message
            reactions = db.session.execute(text('''
                SELECT reaction_type, COUNT(*) as count, 
                       GROUP_CONCAT(user_id) as user_ids
                FROM message_reactions 
                WHERE message_id = :message_id 
                GROUP BY reaction_type
            '''), {'message_id': message.id}).fetchall()
            
            # Get attachments for this message
            attachments = db.session.execute(text('''
                SELECT id, file_name, file_path, file_size, file_type, mime_type
                FROM message_attachments 
                WHERE message_id = :message_id
            '''), {'message_id': message.id}).fetchall()
            
            # Check if message is pinned
            is_pinned = db.session.execute(text('''
                SELECT id FROM pinned_messages WHERE message_id = :message_id
            '''), {'message_id': message.id}).fetchone() is not None
            
            message_data = {
                'id': message.id,
                'content': message.content,
                'sender_id': message.sender_id,
                'sender_name': sender.get_full_name(),
                'sender_username': sender.username,
                'created_at': message.created_at.isoformat(),
                'updated_at': message.updated_at.isoformat() if message.updated_at else None,
                'is_edited': message.is_edited if hasattr(message, 'is_edited') else False,
                'is_own': message.sender_id == current_user.id,
                'is_pinned': is_pinned,
                'reactions': [
                    {
                        'type': reaction.reaction_type,
                        'count': reaction.count,
                        'user_ids': [int(uid) for uid in reaction.user_ids.split(',') if uid]
                    } for reaction in reactions
                ],
                'attachments': [
                    {
                        'id': att.id,
                        'file_name': att.file_name,
                        'file_path': att.file_path,
                        'file_size': att.file_size,
                        'file_type': att.file_type,
                        'mime_type': att.mime_type
                    } for att in attachments
                ]
            }
            messages_data.append(message_data)
        
        # Reverse to show oldest first
        messages_data.reverse()
        
        return jsonify({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/messages/send', methods=['POST'])
@login_required
@production_role_required
def api_messenger_send_message():
    """Send a new message in messenger with team-based access."""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        room = data.get('room', 'general')
        team_id = data.get('team_id')  # Get team_id from request
        group_id = data.get('group_id')  # Get group_id from request
        
        if not content:
            return jsonify({'success': False, 'error': 'Message content is required'}), 400
        
        # If group_id is provided, validate user is member of the group
        if group_id:
            member = ChatGroupMember.query.filter_by(
                group_id=group_id, 
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not member:
                return jsonify({'success': False, 'error': 'Access denied to this group'}), 403
        
        # Get user's teams for validation
        user_teams = current_user.get_teams()
        user_team_ids = [team.id for team in user_teams]
        
        # If team_id is provided, validate user has access to that team
        if team_id and team_id not in user_team_ids:
            return jsonify({'success': False, 'error': 'Access denied to this team'}), 403
        
        # If no team_id provided, use user's primary team
        if not team_id and user_team_ids:
            team_id = user_team_ids[0]  # Use first team as primary
        
        # Create the message with team and group information
        message = ChatMessage(
            sender_id=current_user.id,
            content=content,
            room=room,
            message_type='text',
            is_deleted=False,
            is_edited=False,
            team_id=team_id,
            group_id=group_id
        )
        db.session.add(message)
        db.session.flush()  # Get the ID before commit
        
        # Extract and process mentions
        mentions = extract_mentions(content)
        for username in mentions:
            user = User.query.filter_by(username=username).first()
            if user:
                mention = ChatMention(
                    message_id=message.id,
                    mentioned_user_id=user.id
                )
                db.session.add(mention)
                
                # Create notification for mentioned user
                if user.id != current_user.id:
                    create_notification(
                        user_id=user.id,
                        notification_type='mention',
                        title=f'You were mentioned by {current_user.get_full_name()}',
                        message=f'{current_user.get_full_name()} mentioned you in a message: "{content[:50]}{"..." if len(content) > 50 else ""}"',
                        related_id=message.id
                    )
        
        # Ensure the message is properly saved
        db.session.commit()
        
        # Verify the message was saved
        db.session.refresh(message)
        
        # Get sender info
        sender = User.query.get(current_user.id)
        
        message_data = {
            'id': message.id,
            'content': message.content,
            'sender_id': message.sender_id,
            'sender_name': sender.get_full_name(),
            'sender_username': sender.username,
            'created_at': message.created_at.isoformat(),
            'is_own': True,
            'reactions': [],
            'attachments': []
        }
        
        return jsonify({
            'success': True,
            'message': message_data
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/messages/<int:message_id>/react', methods=['POST'])
@login_required
@production_role_required
def api_messenger_react_to_message(message_id):
    """Add or remove reaction to a message."""
    try:
        data = request.get_json()
        reaction_type = data.get('reaction_type')
        action = data.get('action', 'add')  # 'add' or 'remove'
        
        if not reaction_type:
            return jsonify({'success': False, 'error': 'Reaction type is required'}), 400
        
        if action == 'add':
            # Add reaction (allow multiple reactions per user)
            db.session.execute(text('''
                INSERT INTO message_reactions (message_id, user_id, reaction_type)
                VALUES (:message_id, :user_id, :reaction_type)
            '''), {'message_id': message_id, 'user_id': current_user.id, 'reaction_type': reaction_type})
        else:
            # Remove reaction
            db.session.execute(text('''
                DELETE FROM message_reactions 
                WHERE message_id = :message_id AND user_id = :user_id AND reaction_type = :reaction_type
                LIMIT 1
            '''), {'message_id': message_id, 'user_id': current_user.id, 'reaction_type': reaction_type})
        
        db.session.commit()
        
        # Get updated reaction counts
        reactions = db.session.execute(text('''
            SELECT reaction_type, COUNT(*) as count, 
                   GROUP_CONCAT(user_id) as user_ids
            FROM message_reactions 
            WHERE message_id = :message_id 
            GROUP BY reaction_type
        '''), {'message_id': message_id}).fetchall()
        
        return jsonify({
            'success': True,
            'reactions': [
                {
                    'type': reaction.reaction_type,
                    'count': reaction.count,
                    'user_ids': [int(uid) for uid in reaction.user_ids.split(',') if uid]
                } for reaction in reactions
            ]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/messages/<int:message_id>/pin', methods=['POST'])
@login_required
@production_role_required
def api_messenger_pin_message(message_id):
    """Pin or unpin a message."""
    try:
        data = request.get_json()
        action = data.get('action', 'pin')  # 'pin' or 'unpin'
        
        if action == 'pin':
            # Pin the message
            db.session.execute(text('''
                INSERT OR IGNORE INTO pinned_messages (message_id, pinned_by)
                VALUES (:message_id, :pinned_by)
            '''), {'message_id': message_id, 'pinned_by': current_user.id})
        else:
            # Unpin the message
            db.session.execute(text('''
                DELETE FROM pinned_messages WHERE message_id = :message_id
            '''), {'message_id': message_id})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Message {action}ed successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/messages/<int:message_id>/edit', methods=['POST'])
@login_required
@production_role_required
def api_messenger_edit_message(message_id):
    """Edit a message (only own messages)."""
    try:
        data = request.get_json()
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return jsonify({'success': False, 'error': 'Message content is required'}), 400
        
        message = ChatMessage.query.get_or_404(message_id)
        
        # Check if user can edit this message
        if message.sender_id != current_user.id:
            return jsonify({'success': False, 'error': 'You can only edit your own messages'}), 403
        
        # Update the message
        message.content = new_content
        message.updated_at = datetime.now(timezone.utc)
        message.is_edited = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'updated_at': message.updated_at.isoformat() if message.updated_at else None,
                'is_edited': message.is_edited
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/messenger/messages/<int:message_id>/delete', methods=['DELETE'])
@login_required
@production_role_required
def api_messenger_delete_message(message_id):
    """Delete a message (only own messages)."""
    try:
        message = ChatMessage.query.get_or_404(message_id)
        
        # Check if user can delete this message
        if message.sender_id != current_user.id:
            return jsonify({'success': False, 'error': 'You can only delete your own messages'}), 403
        
        # Check if message is already deleted
        if message.is_deleted:
            return jsonify({'success': False, 'error': 'Message is already deleted'}), 400
        
        # Soft delete the message
        message.soft_delete(current_user.id)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Message deleted successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting message {message_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/files/upload', methods=['POST'])
@login_required
@production_role_required
def api_messenger_upload_file():
    """Upload a file for messenger."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': 'File too large'}), 400
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'messenger')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Get file info
        file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
        mime_type = file.content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        # Create attachment record
        attachment_data = {
            'file_name': filename,
            'file_path': f'/static/uploads/messenger/{unique_filename}',
            'file_size': file_size,
            'file_type': file_type,
            'mime_type': mime_type
        }
        
        return jsonify({
            'success': True,
            'attachment': attachment_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/search', methods=['GET'])
@login_required
@production_role_required
def api_messenger_search():
    """Search messages in messenger."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'success': False, 'error': 'Search query is required'}), 400
        
        # Search messages
        messages = db.session.query(ChatMessage, User).join(
            User, ChatMessage.sender_id == User.id
        ).filter(
            ChatMessage.room == 'general',
            ChatMessage.content.ilike(f'%{query}%')
        ).order_by(ChatMessage.created_at.desc()).limit(20).all()
        
        results = []
        for message, sender in messages:
            results.append({
                'id': message.id,
                'content': message.content,
                'sender_name': sender.get_full_name(),
                'created_at': message.created_at.isoformat(),
                'highlighted_content': message.content.replace(query, f'<mark>{query}</mark>')
            })
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/pinned-messages', methods=['GET'])
@login_required
@production_role_required
def api_messenger_pinned_messages():
    """Get pinned messages for messenger."""
    try:
        pinned_messages = db.session.execute(text('''
            SELECT pm.message_id, pm.pinned_at, pm.pinned_by,
                   cm.content, cm.created_at,
                   u.first_name, u.last_name, u.username
            FROM pinned_messages pm
            JOIN chat_messages cm ON pm.message_id = cm.id
            JOIN users u ON cm.sender_id = u.id
            ORDER BY pm.pinned_at DESC
        ''')).fetchall()
        
        messages_data = []
        for row in pinned_messages:
            messages_data.append({
                'message_id': row.message_id,
                'content': row.content,
                'sender_name': f"{row.first_name} {row.last_name}".strip(),
                'sender_username': row.username,
                'created_at': row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
                'pinned_at': row.pinned_at.isoformat() if hasattr(row.pinned_at, 'isoformat') else str(row.pinned_at),
                'pinned_by': row.pinned_by
            })
        
        return jsonify({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production.route('/api/messenger/users/mention', methods=['GET'])
@login_required
@production_role_required
def api_messenger_mention_users():
    """Get users for mention dropdown."""
    try:
        query = request.args.get('q', '').strip()
        
        # Get all active users
        users = User.query.filter(
            User.is_active == True,
            User.id != current_user.id  # Exclude current user
        ).all()
        
        users_data = []
        for user in users:
            # Filter by query if provided
            if query:
                if query.lower() not in user.get_full_name().lower() and query.lower() not in user.username.lower():
                    continue
            
            users_data.append({
                'id': user.id,
                'name': user.get_full_name(),
                'username': user.username,
                'avatar': user.get_avatar_url() if hasattr(user, 'get_avatar_url') else None
            })
        
        return jsonify({
            'success': True,
            'users': users_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/messenger/typing', methods=['POST'])
@login_required
@production_role_required
def api_messenger_typing():
    """Handle typing indicators."""
    try:
        data = request.get_json()
        is_typing = data.get('is_typing', True)
        room = data.get('room', 'general')
        
        # This would typically emit a SocketIO event
        # For now, we'll just return success
        return jsonify({
            'success': True,
            'is_typing': is_typing,
            'user': current_user.get_full_name()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/messenger/teams', methods=['GET'])
@login_required
@production_role_required
def api_messenger_teams():
    """Get user's teams for messenger interface."""
    try:
        user_teams = current_user.get_teams()
        teams_data = []
        
        for team in user_teams:
            # Get user's role in this team
            user_team = UserTeam.query.filter_by(
                user_id=current_user.id,
                team_id=team.id,
                is_active=True
            ).first()
            
            teams_data.append({
                'id': team.id,
                'name': team.name,
                'description': team.description,
                'is_manager': user_team.role == 'manager' if user_team else False,
                'role': user_team.role if user_team else 'member'
            })
        
        return jsonify({
            'success': True,
            'teams': teams_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/messenger/current-user', methods=['GET'])
@login_required
@production_role_required
def api_messenger_current_user():
    """Get current user information for messenger."""
    try:
        user_data = {
            'id': current_user.id,
            'username': current_user.username,
            'full_name': current_user.get_full_name(),
            'email': current_user.email,
            'avatar_url': current_user.avatar_url if hasattr(current_user, 'avatar_url') else None,
            'role': current_user.role.name if current_user.role else None,
            'permissions': current_user.role.permissions if current_user.role else ''
        }
        
        return jsonify({
            'success': True,
            'user': user_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/groups/<int:group_id>/messages', methods=['GET'])
@login_required
@production_role_required
def api_group_messages(group_id):
    """Get messages for a specific group with reactions and attachments."""
    try:
        # Check if user is member of this group
        member = ChatGroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not member:
            return jsonify({'success': False, 'error': 'Access denied to this group'}), 403
        
        # Get group messages
        query = db.session.query(ChatMessage, User).join(
            User, ChatMessage.sender_id == User.id
        ).filter(
            ChatMessage.group_id == group_id,
            ChatMessage.is_deleted == False
        )
        
        # Get messages ordered by creation time
        messages = query.order_by(ChatMessage.created_at.asc()).limit(100).all()
        
        messages_data = []
        for message, sender in messages:
            # Get reactions for this message
            reactions = db.session.execute(text('''
                SELECT reaction_type, COUNT(*) as count, 
                       GROUP_CONCAT(user_id) as user_ids
                FROM message_reactions 
                WHERE message_id = :message_id 
                GROUP BY reaction_type
            '''), {'message_id': message.id}).fetchall()
            
            # Get attachments for this message
            attachments = db.session.execute(text('''
                SELECT id, file_name, file_path, file_size, file_type, mime_type
                FROM message_attachments 
                WHERE message_id = :message_id
            '''), {'message_id': message.id}).fetchall()
            
            # Check if message is pinned
            is_pinned = db.session.execute(text('''
                SELECT id FROM pinned_messages WHERE message_id = :message_id
            '''), {'message_id': message.id}).fetchone() is not None
            
            message_data = {
                'id': message.id,
                'content': message.content,
                'sender_id': message.sender_id,
                'sender_name': sender.get_full_name(),
                'sender_username': sender.username,
                'created_at': message.created_at.isoformat(),
                'updated_at': message.updated_at.isoformat() if message.updated_at else None,
                'is_edited': message.is_edited if hasattr(message, 'is_edited') else False,
                'is_own': message.sender_id == current_user.id,
                'is_pinned': is_pinned,
                'reactions': [
                    {
                        'type': reaction.reaction_type,
                        'count': reaction.count,
                        'user_ids': [int(uid) for uid in reaction.user_ids.split(',') if uid]
                    } for reaction in reactions
                ],
                'attachments': [
                    {
                        'id': att.id,
                        'file_name': att.file_name,
                        'file_path': att.file_path,
                        'file_size': att.file_size,
                        'file_type': att.file_type,
                        'mime_type': att.mime_type
                    } for att in attachments
                ]
            }
            messages_data.append(message_data)
        
        # Reverse to show oldest first
        messages_data.reverse()
        
        return jsonify({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/groups/<int:group_id>/delete', methods=['DELETE'])
@login_required
@production_role_required
def api_delete_group(group_id):
    """Soft delete a group (only managers can delete groups)."""
    try:
        # Check if user has permission to delete groups (managers only)
        if not current_user.role or current_user.role.name not in ['productions_manager', 'marketing_manager', 'admin']:
            return jsonify({'success': False, 'error': 'Only managers can delete groups'}), 403
        
        group = ChatGroup.query.get_or_404(group_id)
        
        # Check if user is admin of the group or has manager role
        is_group_admin = ChatGroupMember.query.filter_by(
            group_id=group_id,
            user_id=current_user.id,
            role='admin',
            is_active=True
        ).first()
        
        if not is_group_admin and current_user.role.name not in ['productions_manager', 'marketing_manager', 'admin']:
            return jsonify({'success': False, 'error': 'Access denied to delete this group'}), 403
        
        # Soft delete the group
        group.is_deleted = True
        group.deleted_at = datetime.now(timezone.utc)
        group.deleted_by = current_user.id
        
        # Also deactivate all group members
        ChatGroupMember.query.filter_by(group_id=group_id).update({
            'is_active': False,
            'left_at': datetime.now(timezone.utc)
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Group deleted successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/teams/<int:team_id>/members', methods=['GET'])
@login_required
@production_role_required
def api_team_members(team_id):
    """Get team members for group creation."""
    try:
        # Check if user has access to this team
        user_teams = current_user.get_teams()
        user_team_ids = [team.id for team in user_teams]
        
        if team_id not in user_team_ids:
            return jsonify({'success': False, 'error': 'Access denied to this team'}), 403
        
        # Get team members
        team_members = User.query.join(UserTeam).filter(
            UserTeam.team_id == team_id,
            User.is_active == True
        ).all()
        
        members_data = []
        for member in team_members:
            members_data.append({
                'id': member.id,
                'name': member.get_full_name(),
                'username': member.username,
                'email': member.email,
                'role': member.role.name if member.role else 'No Role',
                'is_online': member.is_online
            })
        
        return jsonify({
            'success': True,
            'members': members_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@production.route('/api/tasks/<int:task_id>/comments', methods=['GET'])
@login_required
@production_role_required
def api_get_task_comments(task_id):
    """Get all comments for a task."""
    from .models import TaskComment
    
    task = ProductionTask.query.get_or_404(task_id)
    
    # Check if user has permission to view this task
    if task.assigned_to and task.assigned_to != current_user.id and not current_user.has_permission('manage_productions_team'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Get comments for this task
    comments = TaskComment.query.filter_by(
        task_id=task_id,
        task_type='production_task',
        parent_comment_id=None  # Only top-level comments
    ).order_by(TaskComment.created_at.asc()).all()
    
    # Format comments for frontend
    formatted_comments = []
    for comment in comments:
        comment_data = {
            'id': comment.id,
            'content': comment.get_display_content(),
            'user_id': comment.user_id,
            'user_name': comment.user.get_full_name(),
            'created_at': comment.created_at.isoformat(),
            'is_edited': comment.is_edited,
            'is_deleted': comment.is_deleted,
            'can_edit': comment.can_edit(current_user.id),
            'can_delete': comment.can_delete(current_user.id),
            'replies': []
        }
        
        # Get replies for this comment
        replies = TaskComment.query.filter_by(
            parent_comment_id=comment.id
        ).order_by(TaskComment.created_at.asc()).all()
        
        for reply in replies:
            reply_data = {
                'id': reply.id,
                'content': reply.get_display_content(),
                'user_id': reply.user_id,
                'user_name': reply.user.get_full_name(),
                'created_at': reply.created_at.isoformat(),
                'is_edited': reply.is_edited,
                'is_deleted': reply.is_deleted,
                'can_edit': reply.can_edit(current_user.id),
                'can_delete': reply.can_delete(current_user.id)
            }
            comment_data['replies'].append(reply_data)
        
        formatted_comments.append(comment_data)
    
    return jsonify({
        'success': True,
        'comments': formatted_comments
    })

@production.route('/api/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
@production_role_required
def api_add_task_comment(task_id):
    """Add a comment to a task."""
    from .models import TaskComment
    
    task = ProductionTask.query.get_or_404(task_id)
    
    # Check if user has permission to comment on this task
    if task.assigned_to and task.assigned_to != current_user.id and not current_user.has_permission('manage_productions_team'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    content = data.get('content', '').strip()
    parent_comment_id = data.get('parent_comment_id')  # For replies
    
    if not content:
        return jsonify({'success': False, 'message': 'Comment content is required'}), 400
    
    try:
        # Create the comment
        comment = TaskComment(
            task_id=task_id,
            task_type='production_task',
            content=content,
            user_id=current_user.id,
            parent_comment_id=parent_comment_id
        )
        
        db.session.add(comment)
        db.session.commit()
        
        # Log the comment
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='comment',
            user_id=current_user.id,
            description=f"Added comment: {content[:50]}...",
            request_data=request.get_json()
        )
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user_id': comment.user_id,
                'user_name': comment.user.get_full_name(),
                'created_at': comment.created_at.isoformat(),
                'is_edited': False,
                'is_deleted': False,
                'can_edit': True,
                'can_delete': True,
                'replies': []
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/tasks/comments/<int:comment_id>', methods=['PUT'])
@login_required
@production_role_required
def api_edit_task_comment(comment_id):
    """Edit a task comment."""
    from .models import TaskComment
    
    comment = TaskComment.query.get_or_404(comment_id)
    
    # Check if user can edit this comment
    if not comment.can_edit(current_user.id):
        return jsonify({'success': False, 'message': 'Cannot edit this comment'}), 403
    
    data = request.get_json()
    new_content = data.get('content', '').strip()
    
    if not new_content:
        return jsonify({'success': False, 'message': 'Comment content is required'}), 400
    
    try:
        # Store original content for audit
        if not comment.original_content:
            comment.original_content = comment.content
        
        comment.content = new_content
        comment.is_edited = True
        comment.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'is_edited': True
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/tasks/comments/<int:comment_id>', methods=['DELETE'])
@login_required
@production_role_required
def api_delete_task_comment(comment_id):
    """Delete a task comment."""
    from .models import TaskComment
    
    comment = TaskComment.query.get_or_404(comment_id)
    
    # Check if user can delete this comment
    if not comment.can_delete(current_user.id):
        return jsonify({'success': False, 'message': 'Cannot delete this comment'}), 403
    
    try:
        comment.is_deleted = True
        comment.deleted_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/tasks/<int:task_id>/session/start', methods=['POST'])
@login_required
@production_role_required
def api_start_task_session(task_id):
    """Start a new task session for timing."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Check if user is assigned to this task
        if task.assigned_to != current_user.id and not current_user.has_permission('manage_tasks'):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Check if there's already an active session for this user and task
        existing_session = TaskSession.query.filter_by(
            task_id=task_id,
            user_id=current_user.id,
            session_status='active'
        ).first()
        
        if existing_session:
            return jsonify({'success': False, 'message': 'Session already active for this task'}), 400
        
        # Create new session
        session = TaskSession(
            task_id=task_id,
            user_id=current_user.id,
            session_status='active',
            start_time=datetime.now(timezone.utc)
        )
        db.session.add(session)
        
        # Update task status to in_progress if it's pending
        if task.status == 'pending':
            task.status = 'in_progress'
            task.start_date = date.today()
        
        # Update task's current session
        task.current_session_id = session.id
        
        # Add user to active users list
        active_users = json.loads(task.active_users) if task.active_users else []
        if current_user.id not in active_users:
            active_users.append(current_user.id)
            task.active_users = json.dumps(active_users)
        
        db.session.commit()
        
        # Log the action
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='session_started',
            user_id=current_user.id,
            description=f'Started task session at {session.start_time.strftime("%Y-%m-%d %H:%M:%S")}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Task session started successfully',
            'session_id': session.id,
            'start_time': session.start_time.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error starting session: {str(e)}'}), 500

@production.route('/api/tasks/<int:task_id>/session/pause', methods=['POST'])
@login_required
@production_role_required
def api_pause_task_session(task_id):
    """Pause the current task session."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Find active session for this user and task
        session = TaskSession.query.filter_by(
            task_id=task_id,
            user_id=current_user.id,
            session_status='active'
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'No active session found'}), 404
        
        # Update session status
        session.session_status = 'paused'
        session.last_activity = datetime.now(timezone.utc)
        
        # Create pause record
        pause = TaskSessionPause(
            session_id=session.id,
            pause_start=datetime.now(timezone.utc),
            reason=request.json.get('reason', 'User paused')
        )
        db.session.add(pause)
        
        db.session.commit()
        
        # Log the action
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='session_paused',
            user_id=current_user.id,
            description=f'Paused task session at {pause.pause_start.strftime("%Y-%m-%d %H:%M:%S")}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Task session paused successfully',
            'pause_id': pause.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error pausing session: {str(e)}'}), 500

@production.route('/api/tasks/<int:task_id>/session/resume', methods=['POST'])
@login_required
@production_role_required
def api_resume_task_session(task_id):
    """Resume a paused task session."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Find paused session for this user and task
        session = TaskSession.query.filter_by(
            task_id=task_id,
            user_id=current_user.id,
            session_status='paused'
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'No paused session found'}), 404
        
        # Update session status
        session.session_status = 'active'
        session.last_activity = datetime.now(timezone.utc)
        
        # End the current pause
        current_pause = TaskSessionPause.query.filter_by(
            session_id=session.id,
            pause_end=None
        ).first()
        
        if current_pause:
            current_pause.pause_end = datetime.now(timezone.utc)
            current_pause.duration = int((current_pause.pause_end - current_pause.pause_start).total_seconds())
            session.pause_duration += current_pause.duration
        
        db.session.commit()
        
        # Log the action
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='session_resumed',
            user_id=current_user.id,
            description=f'Resumed task session at {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Task session resumed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error resuming session: {str(e)}'}), 500

@production.route('/api/tasks/<int:task_id>/session/stop', methods=['POST'])
@login_required
@production_role_required
def api_stop_task_session(task_id):
    """Stop the current task session without completing the task."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Find active session for this user and task
        session = TaskSession.query.filter_by(
            task_id=task_id,
            user_id=current_user.id,
            session_status='active'
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'No active session found'}), 404
        
        # Calculate total duration
        end_time = datetime.now(timezone.utc)
        # Ensure start_time is timezone-aware for comparison
        start_time = session.start_time.replace(tzinfo=timezone.utc) if session.start_time.tzinfo is None else session.start_time
        total_duration = int((end_time - start_time).total_seconds()) - session.pause_duration
        
        # Update session
        session.session_status = 'stopped'
        session.end_time = end_time
        session.total_duration = total_duration
        session.last_activity = end_time
        
        # End any current pause
        current_pause = TaskSessionPause.query.filter_by(
            session_id=session.id,
            pause_end=None
        ).first()
        
        if current_pause:
            current_pause.pause_end = end_time
            current_pause.duration = int((current_pause.pause_end - current_pause.pause_start).total_seconds())
        
        # Update task's current session
        if task.current_session_id == session.id:
            task.current_session_id = None
        
        # Remove user from active users list
        active_users = json.loads(task.active_users) if task.active_users else []
        if current_user.id in active_users:
            active_users.remove(current_user.id)
            task.active_users = json.dumps(active_users) if active_users else None
        
        # Update task's actual duration
        task.actual_duration += total_duration // 60  # Convert seconds to minutes
        
        db.session.commit()
        
        # Log the action
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='session_stopped',
            user_id=current_user.id,
            description=f'Stopped task session. Total duration: {session.get_formatted_duration()}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Task session stopped successfully',
            'total_duration': session.get_formatted_duration()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error stopping session: {str(e)}'}), 500

@production.route('/api/tasks/<int:task_id>/session/complete', methods=['POST'])
@login_required
@production_role_required
def api_complete_task_session(task_id):
    """Complete the task session and mark task as completed."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Find active session for this user and task
        session = TaskSession.query.filter_by(
            task_id=task_id,
            user_id=current_user.id,
            session_status='active'
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'No active session found'}), 404
        
        # Calculate total duration
        end_time = datetime.now(timezone.utc)
        # Ensure start_time is timezone-aware for comparison
        start_time = session.start_time.replace(tzinfo=timezone.utc) if session.start_time.tzinfo is None else session.start_time
        total_duration = int((end_time - start_time).total_seconds()) - session.pause_duration
        
        # Update session
        session.session_status = 'completed'
        session.end_time = end_time
        session.total_duration = total_duration
        session.last_activity = end_time
        
        # End any current pause
        current_pause = TaskSessionPause.query.filter_by(
            session_id=session.id,
            pause_end=None
        ).first()
        
        if current_pause:
            current_pause.pause_end = end_time
            current_pause.duration = int((current_pause.pause_end - current_pause.pause_start).total_seconds())
        
        # Update task
        task.status = 'completed'
        task.completed_at = end_time
        task.current_session_id = None
        task.actual_duration += total_duration // 60  # Convert seconds to minutes
        
        # Remove user from active users list
        active_users = json.loads(task.active_users) if task.active_users else []
        if current_user.id in active_users:
            active_users.remove(current_user.id)
            task.active_users = json.dumps(active_users) if active_users else None
        
        db.session.commit()
        
        # Log the action
        log_task_audit(
            task_id=task_id,
            task_type='production_task',
            operation='session_completed',
            user_id=current_user.id,
            description=f'Completed task session. Total duration: {session.get_formatted_duration()}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Task completed successfully',
            'total_duration': session.get_formatted_duration()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error completing session: {str(e)}'}), 500

@production.route('/api/tasks/<int:task_id>/session/status', methods=['GET'])
@login_required
@production_role_required
def api_get_task_session_status(task_id):
    """Get the current session status for a task."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Find current session for this user and task
        session = TaskSession.query.filter_by(
            task_id=task_id,
            user_id=current_user.id
        ).filter(
            TaskSession.session_status.in_(['active', 'paused'])
        ).first()
        
        if not session:
            return jsonify({
                'success': True,
                'has_session': False,
                'message': 'No active session'
            })
        
        # Get current pause if session is paused
        current_pause = None
        if session.session_status == 'paused':
            current_pause = TaskSessionPause.query.filter_by(
                session_id=session.id,
                pause_end=None
            ).first()
        
        return jsonify({
            'success': True,
            'has_session': True,
            'session_id': session.id,
            'status': session.session_status,
            'start_time': session.start_time.isoformat(),
            'duration': session.get_formatted_duration(),
            'active_duration': session.get_active_duration(),
            'pause_duration': session.pause_duration,
            'current_pause': {
                'start_time': current_pause.pause_start.isoformat(),
                'duration': current_pause.get_duration()
            } if current_pause else None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error getting session status: {str(e)}'}), 500

@production.route('/api/tasks/<int:task_id>/session/history', methods=['GET'])
@login_required
@production_role_required
def api_get_task_session_history(task_id):
    """Get session history for a task."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Get all sessions for this task and user
        sessions = TaskSession.query.filter_by(
            task_id=task_id,
            user_id=current_user.id
        ).order_by(TaskSession.created_at.desc()).all()
        
        session_history = []
        for session in sessions:
            session_data = {
                'id': session.id,
                'status': session.session_status,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat() if session.end_time else None,
                'total_duration': session.get_formatted_duration(),
                'pause_duration': session.pause_duration,
                'notes': session.notes
            }
            
            # Add pauses for this session
            pauses = TaskSessionPause.query.filter_by(session_id=session.id).all()
            session_data['pauses'] = [
                {
                    'start_time': pause.pause_start.isoformat(),
                    'end_time': pause.pause_end.isoformat() if pause.pause_end else None,
                    'duration': pause.get_duration(),
                    'reason': pause.reason
                }
                for pause in pauses
            ]
            
            session_history.append(session_data)
        
        return jsonify({
            'success': True,
            'sessions': session_history
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error getting session history: {str(e)}'}), 500



@production.route('/productivity-analytics')
@login_required
@production_role_required
def productivity_analytics():
    """Productivity analytics dashboard."""
    return render_template('production/productivity_analytics.html')

@production.route('/api/productivity/summary')
@login_required
@production_role_required
def api_productivity_summary():
    """Get productivity summary for current user."""
    try:
        # Get user's session data
        user_sessions = TaskSession.query.filter_by(user_id=current_user.id).all()
        
        # Calculate summary statistics
        total_sessions = len(user_sessions)
        total_duration = sum(session.total_duration for session in user_sessions if session.total_duration)
        completed_tasks = len([s for s in user_sessions if s.session_status == 'completed'])
        active_sessions = len([s for s in user_sessions if s.session_status == 'active'])
        
        # Calculate average session duration
        avg_duration = total_duration / total_sessions if total_sessions > 0 else 0
        
        # Get today's sessions
        today = date.today()
        today_sessions = [s for s in user_sessions if s.start_time.date() == today]
        today_duration = sum(s.total_duration for s in today_sessions if s.total_duration)
        
        # Get this week's sessions
        week_start = today - timedelta(days=today.weekday())
        week_sessions = [s for s in user_sessions if s.start_time.date() >= week_start]
        week_duration = sum(s.total_duration for s in week_sessions if s.total_duration)
        
        return jsonify({
            'success': True,
            'summary': {
                'total_sessions': total_sessions,
                'total_duration_hours': round(total_duration / 3600, 2),
                'completed_tasks': completed_tasks,
                'active_sessions': active_sessions,
                'avg_session_hours': round(avg_duration / 3600, 2),
                'today_duration_hours': round(today_duration / 3600, 2),
                'week_duration_hours': round(week_duration / 3600, 2)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/productivity/chart-data')
@login_required
@production_role_required
def api_productivity_chart_data():
    """Get chart data for productivity analytics."""
    try:
        # Get last 30 days of data
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Daily productivity data
        daily_data = []
        current_date = start_date
        while current_date <= end_date:
            day_sessions = TaskSession.query.filter(
                TaskSession.user_id == current_user.id,
                func.date(TaskSession.start_time) == current_date
            ).all()
            
            day_duration = sum(s.total_duration for s in day_sessions if s.total_duration)
            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'duration_hours': round(day_duration / 3600, 2),
                'sessions_count': len(day_sessions)
            })
            current_date += timedelta(days=1)
        
        # Task type breakdown
        task_types = db.session.query(
            ProductionTask.task_type,
            func.sum(TaskSession.total_duration).label('total_duration')
        ).join(TaskSession, ProductionTask.id == TaskSession.task_id).filter(
            TaskSession.user_id == current_user.id
        ).group_by(ProductionTask.task_type).all()
        
        task_type_data = [
            {
                'task_type': task_type,
                'duration_hours': round(duration / 3600, 2) if duration else 0
            }
            for task_type, duration in task_types
        ]
        
        # Session status breakdown
        status_counts = db.session.query(
            TaskSession.session_status,
            func.count(TaskSession.id)
        ).filter(TaskSession.user_id == current_user.id).group_by(TaskSession.session_status).all()
        
        status_data = [
            {
                'status': status,
                'count': count
            }
            for status, count in status_counts
        ]
        
        return jsonify({
            'success': True,
            'daily_data': daily_data,
            'task_type_data': task_type_data,
            'status_data': status_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/productivity/top-tasks')
@login_required
@production_role_required
def api_productivity_top_tasks():
    """Get top tasks by duration for current user."""
    try:
        # Get tasks with highest duration
        top_tasks = db.session.query(
            ProductionTask.id,
            ProductionTask.title,
            ProductionTask.task_type,
            func.sum(TaskSession.total_duration).label('total_duration')
        ).join(TaskSession, ProductionTask.id == TaskSession.task_id).filter(
            TaskSession.user_id == current_user.id
        ).group_by(ProductionTask.id, ProductionTask.title, ProductionTask.task_type).order_by(
            func.sum(TaskSession.total_duration).desc()
        ).limit(10).all()
        
        task_data = [
            {
                'id': task_id,
                'title': title,
                'task_type': task_type,
                'duration_hours': round(duration / 3600, 2) if duration else 0
            }
            for task_id, title, task_type, duration in top_tasks
        ]
        
        return jsonify({
            'success': True,
            'top_tasks': task_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/productivity/session-history')
@login_required
@production_role_required
def api_productivity_session_history():
    """Get detailed session history for current user."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get paginated session history
        sessions = TaskSession.query.filter_by(user_id=current_user.id).order_by(
            TaskSession.start_time.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        session_data = []
        for session in sessions.items:
            task = ProductionTask.query.get(session.task_id)
            session_data.append({
                'id': session.id,
                'task_title': task.title if task else 'Unknown Task',
                'task_type': task.task_type if task else 'Unknown',
                'status': session.session_status,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat() if session.end_time else None,
                'duration_hours': round(session.total_duration / 3600, 2) if session.total_duration else 0,
                'pause_duration_minutes': round(session.pause_duration / 60, 1) if session.pause_duration else 0
            })
        
        return jsonify({
            'success': True,
            'sessions': session_data,
            'pagination': {
                'page': sessions.page,
                'pages': sessions.pages,
                'per_page': sessions.per_page,
                'total': sessions.total,
                'has_next': sessions.has_next,
                'has_prev': sessions.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/sessions/persist', methods=['POST'])
@login_required
@production_role_required
def api_persist_session():
    """Persist session data for cross-device sync."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        session_data = data.get('session_data', {})
        
        # Store session data in user's session
        session[f'persisted_session_{session_id}'] = {
            'data': session_data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'device_id': data.get('device_id', 'unknown')
        }
        
        return jsonify({
            'success': True,
            'message': 'Session data persisted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/sessions/sync', methods=['GET'])
@login_required
@production_role_required
def api_sync_sessions():
    """Get all persisted sessions for cross-device sync."""
    try:
        # Get all persisted sessions for this user
        persisted_sessions = {}
        for key, value in session.items():
            if key.startswith('persisted_session_'):
                session_id = key.replace('persisted_session_', '')
                persisted_sessions[session_id] = value
        
        return jsonify({
            'success': True,
            'sessions': persisted_sessions
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/sessions/resume/<int:session_id>', methods=['POST'])
@login_required
@production_role_required
def api_resume_session(session_id):
    """Resume a session from persisted data."""
    try:
        # Check if session exists and is valid
        task_session = TaskSession.query.get_or_404(session_id)
        
        # Verify user owns this session
        if task_session.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Check if session is still valid (not too old)
        session_age = datetime.now(timezone.utc) - task_session.start_time
        if session_age.total_seconds() > 24 * 3600:  # 24 hours
            return jsonify({'success': False, 'message': 'Session has expired'}), 400
        
        # Resume the session
        if task_session.session_status == 'paused':
            task_session.session_status = 'active'
            task_session.last_activity = datetime.now(timezone.utc)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Session resumed successfully',
                'session_data': {
                    'id': task_session.id,
                    'task_id': task_session.task_id,
                    'start_time': task_session.start_time.isoformat(),
                    'status': task_session.session_status
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Session cannot be resumed'}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/tasks/<int:task_id>/active-users')
@login_required
@production_role_required
def api_get_active_users(task_id):
    """Get active users for a specific task."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        active_users = []
        if task.active_users:
            user_ids = json.loads(task.active_users)
            for user_id in user_ids:
                user = User.query.get(user_id)
                if user:
                    # Get user's current session for this task
                    current_session = TaskSession.query.filter_by(
                        task_id=task_id,
                        user_id=user_id,
                        session_status='active'
                    ).first()
                    
                    active_users.append({
                        'id': user.id,
                        'name': user.get_full_name(),
                        'avatar': user.avatar_url if hasattr(user, 'avatar_url') else None,
                        'session_start': current_session.start_time.isoformat() if current_session else None,
                        'duration': current_session.get_formatted_duration() if current_session else None
                    })
        
        return jsonify({
            'success': True,
            'active_users': active_users
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/tasks/<int:task_id>/collaboration-status')
@login_required
@production_role_required
def api_get_collaboration_status(task_id):
    """Get collaboration status for a task."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Get all sessions for this task
        sessions = TaskSession.query.filter_by(task_id=task_id).all()
        
        # Calculate collaboration metrics
        total_users = len(set(session.user_id for session in sessions))
        total_duration = sum(session.total_duration for session in sessions if session.total_duration)
        avg_duration_per_user = total_duration / total_users if total_users > 0 else 0
        
        # Get current active users
        active_users = []
        if task.active_users:
            user_ids = json.loads(task.active_users)
            for user_id in user_ids:
                user = User.query.get(user_id)
                if user:
                    active_users.append({
                        'id': user.id,
                        'name': user.get_full_name(),
                        'is_current_user': user_id == current_user.id
                    })
        
        return jsonify({
            'success': True,
            'collaboration': {
                'total_users': total_users,
                'active_users': len(active_users),
                'total_duration_hours': round(total_duration / 3600, 2),
                'avg_duration_per_user_hours': round(avg_duration_per_user / 3600, 2),
                'active_users_list': active_users
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/tasks/<int:task_id>/activity-feed')
@login_required
@production_role_required
def api_get_task_activity_feed(task_id):
    """Get activity feed for a specific task."""
    try:
        # Get recent audit logs for this task
        audit_logs = TaskAuditLog.query.filter_by(
            task_id=task_id,
            task_type='production_task'
        ).order_by(TaskAuditLog.created_at.desc()).limit(20).all()
        
        activity_feed = []
        for log in audit_logs:
            user = User.query.get(log.user_id)
            activity_feed.append({
                'id': log.id,
                'user_name': user.get_full_name() if user else 'Unknown User',
                'action': log.operation.replace('_', ' ').title(),
                'description': log.description,
                'timestamp': log.created_at.isoformat(),
                'field_name': log.field_name,
                'old_value': log.old_value,
                'new_value': log.new_value
            })
        
        return jsonify({
            'success': True,
            'activity_feed': activity_feed
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@production.route('/api/tasks/<int:task_id>/real-time-status')
@login_required
@production_role_required
def api_get_real_time_status(task_id):
    """Get real-time status updates for a task."""
    try:
        task = ProductionTask.query.get_or_404(task_id)
        
        # Get current session status for current user
        current_user_session = TaskSession.query.filter_by(
            task_id=task_id,
            user_id=current_user.id
        ).filter(
            TaskSession.session_status.in_(['active', 'paused'])
        ).first()
        
        # Get task progress
        total_sessions = TaskSession.query.filter_by(task_id=task_id).count()
        completed_sessions = TaskSession.query.filter_by(
            task_id=task_id,
            session_status='completed'
        ).count()
        
        progress_percentage = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        return jsonify({
            'success': True,
            'real_time_status': {
                'task_id': task_id,
                'task_title': task.title,
                'task_status': task.status,
                'progress_percentage': round(progress_percentage, 1),
                'current_user_session': {
                    'has_session': current_user_session is not None,
                    'session_status': current_user_session.session_status if current_user_session else None,
                    'session_duration': current_user_session.get_formatted_duration() if current_user_session else None
                },
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500