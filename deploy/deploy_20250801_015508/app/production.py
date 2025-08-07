from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from .auth import permission_required
from .models import db, ProductionTask, TaskAttachment, LANServerFile, DropboxUpload, User, ConvertedClient, ProductionActivity, ScreenRecording, ProductivityReport, ApplicationUsage, MouseKeyboardActivity, WebsiteVisit, BrowserActivity, DetailedApplicationUsage
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timezone, date, timedelta
import mimetypes
import io

production = Blueprint('production', __name__)

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@production.route('/dashboard')
@login_required
@permission_required('view_tasks')
def dashboard():
    """Production dashboard with comprehensive tracking."""
    # Get assigned tasks
    assigned_tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).order_by(ProductionTask.created_at.desc()).all()
    
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
    creative_tools = {}
    communication_tools = {}
    browsers = {}
    productivity_tools = {}
    
    for app in today_detailed_apps:
        if app.application_category == 'creative':
            creative_tools[app.application_name] = {
                'time': app.total_time_seconds,
                'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
        elif app.application_category == 'communication':
            communication_tools[app.application_name] = {
                'time': app.total_time_seconds,
                'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
        elif app.application_category == 'browser':
            browsers[app.application_name] = {
                'time': app.total_time_seconds,
                'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
        elif app.application_category == 'productivity':
            productivity_tools[app.application_name] = {
                'time': app.total_time_seconds,
                'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
    
    # Get website visits by category
    reference_sites = {}
    social_media = {}
    client_portals = {}
    other_websites = {}
    
    for visit in today_website_visits:
        if visit.website_category == 'reference':
            reference_sites[visit.website_name] = {
                'visits': visit.visit_count,
                'time': visit.total_time_seconds
            }
        elif visit.website_category == 'social':
            social_media[visit.website_name] = {
                'visits': visit.visit_count,
                'time': visit.total_time_seconds
            }
        elif visit.website_category == 'client':
            client_portals[visit.website_name] = {
                'visits': visit.visit_count,
                'time': visit.total_time_seconds
            }
        elif visit.website_category == 'other':
            other_websites[visit.website_name] = {
                'visits': visit.visit_count,
                'time': visit.total_time_seconds
            }
    
    # Get browser activity
    browser_usage = {}
    for browser in today_browser_activity:
        browser_usage[browser.browser_name] = {
            'time': browser.total_time_seconds,
            'websites': browser.websites_visited,
            'tabs': browser.tabs_opened,
            'percentage': round((browser.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
        }
    
    # Calculate time distribution
    work_apps_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_category in ['creative', 'productivity'])
    web_activity_time = sum(visit.total_time_seconds for visit in today_website_visits)
    communication_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_category == 'communication')
    file_management_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_name in ['File Explorer', 'Finder', 'Dropbox', 'Google Drive'])
    
    # Calculate focus score
    total_work_time = work_apps_time + communication_time + file_management_time
    total_distraction_time = sum(visit.total_time_seconds for visit in today_website_visits if visit.website_category == 'social')
    
    if total_work_time > 0:
        focus_score = min(100, (total_work_time / (total_work_time + total_distraction_time)) * 100)
    else:
        focus_score = 0
    
    # Get task statistics
    task_stats = {
        'total': len(assigned_tasks),
        'pending': len([t for t in assigned_tasks if t.status == 'pending']),
        'in_progress': len([t for t in assigned_tasks if t.status == 'in_progress']),
        'completed': len([t for t in assigned_tasks if t.status == 'completed'])
    }
    
    # Get weekly progress
    week_start = today - timedelta(days=today.weekday())
    week_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to == current_user.id,
        ProductionTask.created_at >= week_start
    ).all()
    
    weekly_completed = len([t for t in week_tasks if t.status == 'completed'])
    weekly_target = 40  # Target tasks per week
    weekly_progress = min(100, (weekly_completed / weekly_target) * 100) if weekly_target > 0 else 0
    
    return render_template('production/dashboard.html',
                         assigned_tasks=assigned_tasks,
                         task_stats=task_stats,
                         today_app_usage=today_app_usage,
                         today_activity=today_activity,
                         today_report=today_report,
                         recent_activities=recent_activities,
                         total_active_time=total_active_time,
                         total_break_time=total_break_time,
                         productivity_score=productivity_score,
                         adobe_usage=adobe_usage,
                         creative_tools=creative_tools,
                         communication_tools=communication_tools,
                         browsers=browsers,
                         productivity_tools=productivity_tools,
                         reference_sites=reference_sites,
                         social_media=social_media,
                         client_portals=client_portals,
                         other_websites=other_websites,
                         browser_usage=browser_usage,
                         work_apps_time=work_apps_time,
                         web_activity_time=web_activity_time,
                         communication_time=communication_time,
                         file_management_time=file_management_time,
                         focus_score=focus_score,
                         weekly_progress=weekly_progress,
                         weekly_completed=weekly_completed,
                         weekly_target=weekly_target)

@production.route('/tasks')
@login_required
@permission_required('view_tasks')
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
    
    return render_template('production/tasks.html', tasks=tasks)

@production.route('/tasks/<int:task_id>')
@login_required
@permission_required('view_tasks')
def view_task(task_id):
    """View specific task details."""
    task = ProductionTask.query.get_or_404(task_id)
    
    # Check if user is assigned to this task
    if task.assigned_to != current_user.id:
        flash('Access denied. You can only view your assigned tasks.', 'error')
        return redirect(url_for('production.tasks'))
    
    # For Production team, mask sensitive client information
    if not current_user.has_permission('admin') and not current_user.has_permission('manage_leads'):
        # Create a copy of task data with masked client info
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'task_type': task.task_type,
            'priority': task.priority,
            'status': task.status,
            'due_date': task.due_date,
            'completed_at': task.completed_at,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            # Mask client information
            'client_id': None,  # Hide Client ID
            'client_name': task.client_name,
            'client_contact': task.client_contact,
            'client_phone': '***-***-' + str(task.client_phone)[-4:] if task.client_phone else None,
            'client_email': task.client_email[:3] + '***@' + task.client_email.split('@')[1] if task.client_email else None,
            'assigned_to': task.assigned_to,
            'assigned_by': task.assigned_by
        }
        return render_template('production/view_task.html', task=task_data)
    
    return render_template('production/view_task.html', task=task)

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
    
    status = request.form.get('status')
    description = request.form.get('description')
    
    if status and status in ['pending', 'in_progress', 'completed', 'cancelled']:
        task.status = status
        if status == 'completed':
            task.completed_at = datetime.now(timezone.utc)
    
    if description:
        task.description = description
    
    task.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    flash('Task updated successfully!', 'success')
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
@permission_required('view_tasks')
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
@permission_required('view_tasks')
def api_dashboard_data():
    today = date.today()
    assigned_tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).order_by(ProductionTask.created_at.desc()).all()
    today_app_usage = ApplicationUsage.query.filter_by(user_id=current_user.id, usage_date=today).all()
    today_detailed_apps = DetailedApplicationUsage.query.filter_by(user_id=current_user.id, usage_date=today).all()
    today_activity = MouseKeyboardActivity.query.filter_by(user_id=current_user.id, activity_date=today).first()
    today_report = ProductivityReport.query.filter_by(user_id=current_user.id, report_date=today).first()
    today_website_visits = WebsiteVisit.query.filter_by(user_id=current_user.id, visit_date=today).all()
    today_browser_activity = BrowserActivity.query.filter_by(user_id=current_user.id, activity_date=today).all()
    recent_activities = ProductionActivity.query.filter_by(user_id=current_user.id).order_by(ProductionActivity.created_at.desc()).limit(10).all()
    total_active_time = sum(app.active_time_seconds for app in today_app_usage) if today_app_usage else 0
    total_break_time = sum(app.idle_time_seconds for app in today_app_usage) if today_app_usage else 0
    productivity_score = min(100, (total_active_time / (total_active_time + total_break_time)) * 100) if total_active_time > 0 else 0
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
    creative_tools = {}
    communication_tools = {}
    browsers = {}
    productivity_tools = {}
    for app in today_detailed_apps:
        if app.application_category == 'creative':
            creative_tools[app.application_name] = {
                'time': app.total_time_seconds,
                'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
        elif app.application_category == 'communication':
            communication_tools[app.application_name] = {
                'time': app.total_time_seconds,
                'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
        elif app.application_category == 'browser':
            browsers[app.application_name] = {
                'time': app.total_time_seconds,
                'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
        elif app.application_category == 'productivity':
            productivity_tools[app.application_name] = {
                'time': app.total_time_seconds,
                'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
    reference_sites = {}
    social_media = {}
    client_portals = {}
    other_websites = {}
    for visit in today_website_visits:
        if visit.website_category == 'reference':
            reference_sites[visit.website_name] = {
                'visits': visit.visit_count,
                'time': visit.total_time_seconds
            }
        elif visit.website_category == 'social':
            social_media[visit.website_name] = {
                'visits': visit.visit_count,
                'time': visit.total_time_seconds
            }
        elif visit.website_category == 'client':
            client_portals[visit.website_name] = {
                'visits': visit.visit_count,
                'time': visit.total_time_seconds
            }
        elif visit.website_category == 'other':
            other_websites[visit.website_name] = {
                'visits': visit.visit_count,
                'time': visit.total_time_seconds
            }
    browser_usage = {}
    for browser in today_browser_activity:
        browser_usage[browser.browser_name] = {
            'time': browser.total_time_seconds,
            'websites': browser.websites_visited,
            'tabs': browser.tabs_opened,
            'percentage': round((browser.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
        }
    work_apps_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_category in ['creative', 'productivity'])
    web_activity_time = sum(visit.total_time_seconds for visit in today_website_visits)
    communication_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_category == 'communication')
    file_management_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_name in ['File Explorer', 'Finder', 'Dropbox', 'Google Drive'])
    total_work_time = work_apps_time + communication_time + file_management_time
    total_distraction_time = sum(visit.total_time_seconds for visit in today_website_visits if visit.website_category == 'social')
    if total_work_time > 0:
        focus_score = min(100, (total_work_time / (total_work_time + total_distraction_time)) * 100)
    else:
        focus_score = 0
    task_stats = {
        'total': len(assigned_tasks),
        'pending': len([t for t in assigned_tasks if t.status == 'pending']),
        'in_progress': len([t for t in assigned_tasks if t.status == 'in_progress']),
        'completed': len([t for t in assigned_tasks if t.status == 'completed'])
    }
    week_start = today - timedelta(days=today.weekday())
    week_tasks = ProductionTask.query.filter(ProductionTask.assigned_to == current_user.id, ProductionTask.created_at >= week_start).all()
    weekly_completed = len([t for t in week_tasks if t.status == 'completed'])
    weekly_target = 40
    weekly_progress = min(100, (weekly_completed / weekly_target) * 100) if weekly_target > 0 else 0
    # Prepare JSON response
    return jsonify({
        'assigned_tasks': [
            {
                'id': t.id,
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'client_id': t.client_id,
                'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else None
            } for t in assigned_tasks
        ],
        'task_stats': task_stats,
        'today_app_usage': [
            {
                'application_name': a.application_name,
                'active_time_seconds': a.active_time_seconds,
                'idle_time_seconds': a.idle_time_seconds,
                'total_time_seconds': a.total_time_seconds
            } for a in today_app_usage
        ],
        'today_activity': {
            'mouse_clicks': today_activity.mouse_clicks if today_activity else 0,
            'keyboard_strokes': today_activity.keyboard_strokes if today_activity else 0
        },
        'productivity_score': productivity_score,
        'adobe_usage': adobe_usage,
        'creative_tools': creative_tools,
        'communication_tools': communication_tools,
        'browsers': browsers,
        'productivity_tools': productivity_tools,
        'reference_sites': reference_sites,
        'social_media': social_media,
        'client_portals': client_portals,
        'other_websites': other_websites,
        'browser_usage': browser_usage,
        'work_apps_time': work_apps_time,
        'web_activity_time': web_activity_time,
        'communication_time': communication_time,
        'file_management_time': file_management_time,
        'focus_score': focus_score,
        'weekly_progress': weekly_progress,
        'weekly_completed': weekly_completed,
        'weekly_target': weekly_target
    }) 