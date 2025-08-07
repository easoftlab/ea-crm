from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_
from . import db
from .models import User, Role, ProductionTask, Team, UserTeam, TeamMemberDailyReport, TeamMemberWeeklyReport, TeamMemberMonthlyReport, ReportSchedule, TaskAttachment, ChatGroup, Projection
from .auth import permission_required
from .forms import ProductionTaskForm
import os
import json

productions = Blueprint('productions', __name__, url_prefix='/productions')

def productions_manager_required(f):
    """Decorator to require productions manager permissions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.has_permission('manage_productions_team'):
            flash('Access denied. Productions Manager privileges required.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_production_team():
    """Get the production team, ensuring it exists."""
    production_team = Team.query.filter_by(name='Production Team').first()
    if not production_team:
        flash('Production team not found. Please contact administrator.', 'error')
        return None
    return production_team

def get_production_team_members():
    """Get all active production team members with production roles only."""
    production_team = get_production_team()
    if not production_team:
        return []
    
    # Get users with Production and Productions Manager roles
    production_roles = ['Production', 'Productions Manager']
    
    return User.query.join(UserTeam).join(Role).filter(
        UserTeam.team_id == production_team.id,
        UserTeam.is_active == True,
        Role.name.in_(production_roles)
    ).all()

def filter_production_data(query, team_id_field='team_id'):
    """Filter data to only include production team data."""
    production_team = get_production_team()
    if not production_team:
        return query.filter(False)  # Return empty result
    
    return query.filter(getattr(query.model, team_id_field) == production_team.id)

def ensure_production_access(user_id):
    """Ensure a user is a member of the production team."""
    production_team = get_production_team()
    if not production_team:
        return False
    
    user_team = UserTeam.query.filter_by(
        user_id=user_id,
        team_id=production_team.id,
        is_active=True
    ).first()
    
    return user_team is not None

def validate_production_member_access(member_id):
    """Validate that a member belongs to the production team."""
    if not ensure_production_access(member_id):
        flash('Access denied. User is not a member of the production team.', 'error')
        return False
    return True

@productions.route('/dashboard')
@login_required
def dashboard():
    """Productions Dashboard - Different views for managers vs regular production users."""
    
    # Check if user is Productions Manager
    if current_user.has_permission('manage_productions_team'):
        return productions_manager_dashboard()
    # Check if user is Production role (has view_tasks permission AND is Production role)
    elif (current_user.has_permission('view_tasks') and 
          current_user.role and current_user.role.name == 'Production'):
        return production_user_dashboard()
    # Check if user has Production role (fallback for users without specific permissions)
    elif current_user.role and current_user.role.name in ['Production', 'Productions Manager']:
        return productions_manager_dashboard()
    else:
        flash('Access denied. Production privileges required.', 'error')
        return redirect(url_for('auth.login'))

@productions.route('/production/dashboard')
@login_required
def production_dashboard():
    """Production Dashboard - Alternative route for production users."""
    return dashboard()

def productions_manager_dashboard():
    """Productions Manager Dashboard - Overview of production team performance."""
    
    # Get production team members
    production_team = get_production_team()
    if not production_team:
        # Create the production team if it doesn't exist
        from app.models import Team
        production_team = Team(name='Production Team', description='Production team for managing production tasks')
        db.session.add(production_team)
        db.session.commit()
        flash('Production team created successfully.', 'success')
    
    team_members = get_production_team_members()
    
    # If no team members found, show message instead of creating sample users
    if not team_members:
        flash('No Production team members found. Please add users with Production role to the Production Team.', 'info')
    
    # Get today's date
    today = date.today()
    
    # Get daily reports for today - filtered to production team only
    daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == production_team.id,
        TeamMemberDailyReport.report_date == today
    ).all()
    
    # Calculate team statistics with null handling
    total_tasks_completed = sum(report.tasks_completed or 0 for report in daily_reports)
    total_tasks_assigned = sum(report.tasks_assigned or 0 for report in daily_reports)
    total_active_time = sum(report.total_active_time or 0 for report in daily_reports)
    
    # Get weekly reports for current week - filtered to production team only
    week_start = today - timedelta(days=today.weekday())
    weekly_reports = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == production_team.id,
        TeamMemberWeeklyReport.week_start == week_start
    ).all()
    
    # Calculate weekly statistics with null handling
    total_tasks_week = sum(report.total_tasks_completed or 0 for report in weekly_reports)
    total_tasks_assigned_week = sum(report.total_tasks_assigned or 0 for report in weekly_reports)
    
    # Get monthly reports for current month - filtered to production team only
    month_start = date(today.year, today.month, 1)
    monthly_reports = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == production_team.id,
        TeamMemberMonthlyReport.month_year == month_start
    ).all()
    
    # Calculate monthly statistics with null handling
    total_tasks_month = sum(report.total_tasks_completed or 0 for report in monthly_reports)
    total_tasks_assigned_month = sum(report.total_tasks_assigned or 0 for report in monthly_reports)
    
    # Get recent tasks - filtered to production team members only
    team_member_ids = [member.id for member in team_members]
    recent_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids + [None])  # Include unassigned tasks
    ).order_by(ProductionTask.created_at.desc()).limit(10).all()
    
    # Get team performance rankings
    team_performance = []
    for member in team_members:
        member_daily = next((r for r in daily_reports if r.user_id == member.id), None)
        member_weekly = next((r for r in weekly_reports if r.user_id == member.id), None)
        
        performance = {
            'user': member,
            'daily_tasks': member_daily.tasks_completed or 0 if member_daily else 0,
            'daily_assigned': member_daily.tasks_assigned or 0 if member_daily else 0,
            'weekly_tasks': member_weekly.total_tasks_completed or 0 if member_weekly else 0,
            'weekly_assigned': member_weekly.total_tasks_assigned or 0 if member_weekly else 0,
            'productivity_score': member_daily.get_productivity_score() if member_daily else 0
        }
        team_performance.append(performance)
    
    # Sort by productivity score
    team_performance.sort(key=lambda x: x['productivity_score'], reverse=True)
    
    # Get task status distribution for charts
    task_status_counts = {}
    task_priority_counts = {}
    
    for task in recent_tasks:
        # Status counts
        status = task.status
        task_status_counts[status] = task_status_counts.get(status, 0) + 1
        
        # Priority counts
        priority = task.priority
        task_priority_counts[priority] = task_priority_counts.get(priority, 0) + 1
    
    return render_template('productions/dashboard.html',
                         team_members=team_members,
                         team_performance=team_performance,
                         recent_tasks=recent_tasks,
                         task_status_counts=task_status_counts,
                         task_priority_counts=task_priority_counts,
                         stats={
                             'today': {
                                 'tasks_completed': total_tasks_completed,
                                 'tasks_assigned': total_tasks_assigned,
                                 'active_time': total_active_time
                             },
                             'week': {
                                 'tasks_completed': total_tasks_week,
                                 'tasks_assigned': total_tasks_assigned_week
                             },
                             'month': {
                                 'tasks_completed': total_tasks_month,
                                 'tasks_assigned': total_tasks_assigned_month
                             }
                         })

def production_user_dashboard():
    """Production User Dashboard - Individual production user view."""
    
    # Get user's assigned tasks (both specifically assigned and unassigned tasks for all production team)
    production_team = get_production_team()
    if not production_team:
        flash('Production team not found.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get tasks specifically assigned to this user
    assigned_tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).all()
    
    # Get unassigned tasks (tasks assigned to None) that should be visible to all production team members
    unassigned_tasks = ProductionTask.query.filter_by(assigned_to=None).all()
    
    # Combine all tasks for this user
    user_tasks = assigned_tasks + unassigned_tasks
    
    # Get today's date
    today = date.today()
    
    # Filter tasks for today
    today_tasks = [task for task in user_tasks if task.due_date == today]
    
    # Get completed tasks
    completed_tasks = [task for task in user_tasks if task.status == 'completed']
    
    # Calculate statistics
    total_tasks = len(user_tasks)
    today_task_count = len(today_tasks)
    completed_count = len(completed_tasks)
    completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0
    
    # Get recent tasks (last 10)
    recent_tasks = sorted(user_tasks, key=lambda x: x.created_at, reverse=True)[:10]
    
    # Get tasks by status
    tasks_by_status = {}
    for task in user_tasks:
        status = task.status
        if status not in tasks_by_status:
            tasks_by_status[status] = 0
        tasks_by_status[status] += 1
    
    # Get monthly task activity
    month_start = date(today.year, today.month, 1)
    monthly_tasks = [task for task in user_tasks if task.created_at.date() >= month_start]
    
    # Get task statistics for charts
    task_stats = {
        'pending': len([t for t in user_tasks if t.status == 'pending']),
        'in_progress': len([t for t in user_tasks if t.status == 'in_progress']),
        'completed': len([t for t in user_tasks if t.status == 'completed']),
        'cancelled': len([t for t in user_tasks if t.status == 'cancelled'])
    }
    
    # Get priority distribution
    priority_counts = {
        'low': len([t for t in user_tasks if t.priority == 'low']),
        'medium': len([t for t in user_tasks if t.priority == 'medium']),
        'high': len([t for t in user_tasks if t.priority == 'high']),
        'urgent': len([t for t in user_tasks if t.priority == 'urgent'])
    }
    
    return render_template('productions/user_dashboard.html',
                         user=current_user,
                         total_tasks=total_tasks,
                         today_tasks=today_task_count,
                         completed_tasks=completed_count,
                         completion_rate=completion_rate,
                         recent_tasks=recent_tasks,
                         tasks_by_status=tasks_by_status,
                         monthly_tasks=monthly_tasks,
                         task_stats=task_stats,
                         priority_counts=priority_counts,
                         today=today)

@productions.route('/team')
@login_required
@productions_manager_required
def team():
    """Production Team Management - View and manage production team members."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get all production team members with their performance data
    team_members = get_production_team_members()
    
    # Get today's performance data
    today = date.today()
    daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == production_team.id,
        TeamMemberDailyReport.report_date == today
    ).all()
    
    # Get weekly performance data
    week_start = today - timedelta(days=today.weekday())
    weekly_reports = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == production_team.id,
        TeamMemberWeeklyReport.week_start == week_start
    ).all()
    
    # Get monthly performance data
    month_start = date(today.year, today.month, 1)
    monthly_reports = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == production_team.id,
        TeamMemberMonthlyReport.month_year == month_start
    ).all()
    
    # Compile member performance data
    member_performance = []
    for member in team_members:
        daily = next((r for r in daily_reports if r.user_id == member.id), None)
        weekly = next((r for r in weekly_reports if r.user_id == member.id), None)
        monthly = next((r for r in monthly_reports if r.user_id == member.id), None)
        
        performance = {
            'user': member,
            'daily': daily,
            'weekly': weekly,
            'monthly': monthly,
            'productivity_score': daily.get_productivity_score() if daily else 0,
            'goal_completion': daily.get_goal_completion() if daily else 0
        }
        member_performance.append(performance)
    
    # Sort by productivity score
    member_performance.sort(key=lambda x: x['productivity_score'], reverse=True)
    
    # Get task statistics for the team
    team_member_ids = [member.id for member in team_members]
    from app.models import ProductionTask
    
    task_stats = {
        'pending': ProductionTask.query.filter(
            ProductionTask.assigned_to.in_(team_member_ids),
            ProductionTask.status == 'pending'
        ).count(),
        'in_progress': ProductionTask.query.filter(
            ProductionTask.assigned_to.in_(team_member_ids),
            ProductionTask.status == 'in_progress'
        ).count(),
        'completed': ProductionTask.query.filter(
            ProductionTask.assigned_to.in_(team_member_ids),
            ProductionTask.status == 'completed'
        ).count(),
        'total': ProductionTask.query.filter(
            ProductionTask.assigned_to.in_(team_member_ids)
        ).count()
    }
    
    return render_template('productions/team.html',
                         team=production_team,
                         member_performance=member_performance,
                         task_stats=task_stats)

@productions.route('/reports')
@login_required
@productions_manager_required
def reports():
    """Production Reports - Generate and view production team reports."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get report schedules for production team
    report_schedules = ReportSchedule.query.filter_by(
        team_id=production_team.id,
        is_active=True
    ).all()
    
    # Get recent reports
    today = date.today()
    recent_daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == production_team.id,
        TeamMemberDailyReport.report_date >= today - timedelta(days=7)
    ).order_by(TeamMemberDailyReport.report_date.desc()).limit(10).all()
    
    recent_weekly_reports = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == production_team.id,
        TeamMemberWeeklyReport.week_start >= today - timedelta(weeks=4)
    ).order_by(TeamMemberWeeklyReport.week_start.desc()).limit(4).all()
    
    recent_monthly_reports = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == production_team.id,
        TeamMemberMonthlyReport.month_year >= today.replace(day=1) - timedelta(days=90)
    ).order_by(TeamMemberMonthlyReport.month_year.desc()).limit(3).all()
    
    # Calculate recent counts for summary
    recent_counts = {
        'daily': len(recent_daily_reports),
        'weekly': len(recent_weekly_reports),
        'monthly': len(recent_monthly_reports)
    }
    
    return render_template('productions/reports.html',
                         team=production_team,
                         report_schedules=report_schedules,
                         recent_daily_reports=recent_daily_reports,
                         recent_weekly_reports=recent_weekly_reports,
                         recent_monthly_reports=recent_monthly_reports,
                         recent_counts=recent_counts)

@productions.route('/tasks')
@login_required
@productions_manager_required
def tasks():
    """Production Tasks - View and manage tasks assigned to production team."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get team member IDs for filtering tasks
    team_member_ids = [member.id for member in get_production_team_members()]
    
    # Get tasks assigned to production team members
    page = request.args.get('page', 1, type=int)
    tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids)
    ).order_by(ProductionTask.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get task statistics
    total_tasks = ProductionTask.query.filter(ProductionTask.assigned_to.in_(team_member_ids)).count()
    pending_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids),
        ProductionTask.status == 'pending'
    ).count()
    in_progress_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids),
        ProductionTask.status == 'in_progress'
    ).count()
    completed_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids),
        ProductionTask.status == 'completed'
    ).count()
    cancelled_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids),
        ProductionTask.status == 'cancelled'
    ).count()
    
    # Get priority counts
    priority_counts = {
        'low': ProductionTask.query.filter(
            ProductionTask.assigned_to.in_(team_member_ids),
            ProductionTask.priority == 'low'
        ).count(),
        'medium': ProductionTask.query.filter(
            ProductionTask.assigned_to.in_(team_member_ids),
            ProductionTask.priority == 'medium'
        ).count(),
        'high': ProductionTask.query.filter(
            ProductionTask.assigned_to.in_(team_member_ids),
            ProductionTask.priority == 'high'
        ).count(),
        'urgent': ProductionTask.query.filter(
            ProductionTask.assigned_to.in_(team_member_ids),
            ProductionTask.priority == 'urgent'
        ).count()
    }
    
    return render_template('productions/tasks.html',
                         tasks=tasks,
                         stats={
                             'total': total_tasks,
                             'pending': pending_tasks,
                             'in_progress': in_progress_tasks,
                             'completed': completed_tasks,
                             'cancelled': cancelled_tasks
                         },
                         priority_counts=priority_counts)

@productions.route('/production/tasks')
@login_required
def production_tasks():
    """Production User Tasks - View tasks assigned to current user."""
    
    # Get tasks assigned to current user
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    
    # Build query for current user's tasks
    query = ProductionTask.query.filter(ProductionTask.assigned_to == current_user.id)
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter(ProductionTask.status == status_filter)
    if priority_filter != 'all':
        query = query.filter(ProductionTask.priority == priority_filter)
    
    # Get paginated tasks
    tasks = query.order_by(ProductionTask.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get task statistics for current user
    total_tasks = ProductionTask.query.filter(ProductionTask.assigned_to == current_user.id).count()
    pending_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to == current_user.id,
        ProductionTask.status == 'pending'
    ).count()
    in_progress_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to == current_user.id,
        ProductionTask.status == 'in_progress'
    ).count()
    completed_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to == current_user.id,
        ProductionTask.status == 'completed'
    ).count()
    
    # Get priority counts for current user
    priority_counts = {
        'low': ProductionTask.query.filter(
            ProductionTask.assigned_to == current_user.id,
            ProductionTask.priority == 'low'
        ).count(),
        'medium': ProductionTask.query.filter(
            ProductionTask.assigned_to == current_user.id,
            ProductionTask.priority == 'medium'
        ).count(),
        'high': ProductionTask.query.filter(
            ProductionTask.assigned_to == current_user.id,
            ProductionTask.priority == 'high'
        ).count(),
        'urgent': ProductionTask.query.filter(
            ProductionTask.assigned_to == current_user.id,
            ProductionTask.priority == 'urgent'
        ).count()
    }
    
    return render_template('productions/user_tasks.html',
                         tasks=tasks,
                         stats={
                             'total': total_tasks,
                             'pending': pending_tasks,
                             'in_progress': in_progress_tasks,
                             'completed': completed_tasks
                         },
                         priority_counts=priority_counts,
                         status_filter=status_filter,
                         priority_filter=priority_filter)

@productions.route('/task-management')
@login_required
@productions_manager_required
def task_management():
    """Task Management - Create and manage production tasks."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get team member IDs for filtering tasks
    team_member_ids = [member.id for member in get_production_team_members()]
    
    # Get all tasks with pagination
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    assigned_filter = request.args.get('assigned_to', 'all')
    
    # Build query with filters
    query = ProductionTask.query.filter(ProductionTask.assigned_to.in_(team_member_ids))
    
    if status_filter != 'all':
        query = query.filter(ProductionTask.status == status_filter)
    if priority_filter != 'all':
        query = query.filter(ProductionTask.priority == priority_filter)
    if assigned_filter != 'all':
        query = query.filter(ProductionTask.assigned_to == int(assigned_filter))
    
    tasks = query.order_by(ProductionTask.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get task statistics
    total_tasks = ProductionTask.query.filter(ProductionTask.assigned_to.in_(team_member_ids)).count()
    pending_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids),
        ProductionTask.status == 'pending'
    ).count()
    in_progress_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids),
        ProductionTask.status == 'in_progress'
    ).count()
    completed_tasks = ProductionTask.query.filter(
        ProductionTask.assigned_to.in_(team_member_ids),
        ProductionTask.status == 'completed'
    ).count()
    
    # Get team members for assignment dropdown
    team_members = get_production_team_members()
    
    return render_template('productions/task-management.html',
                         tasks=tasks,
                         team_members=team_members,
                         stats={
                             'total': total_tasks,
                             'pending': pending_tasks,
                             'in_progress': in_progress_tasks,
                             'completed': completed_tasks
                         },
                         filters={
                             'status': status_filter,
                             'priority': priority_filter,
                             'assigned_to': assigned_filter
                         })

@productions.route('/task-management/create', methods=['GET', 'POST'])
@login_required
@productions_manager_required
def create_task():
    """Create a new production task."""
    
    form = ProductionTaskForm()
    
    # Populate assigned_to choices with production team members
    team_members = get_production_team_members()
    form.assigned_to.choices = [('', 'Select Assignee')] + [(str(member.id), member.get_full_name()) for member in team_members]
    
    if form.validate_on_submit():
        try:
            # Create the task
            task = ProductionTask(
                title=form.title.data,
                description=form.description.data,
                task_type=form.task_type.data,
                priority=form.priority.data,
                assigned_to=int(form.assigned_to.data) if form.assigned_to.data else None,
                assigned_by=current_user.id,
                due_date=form.due_date.data,
                client_name=form.client_name.data,
                client_contact=form.client_contact.data,
                client_phone=form.client_phone.data,
                client_email=form.client_email.data,
                estimated_duration_hours=form.estimated_duration_hours.data,
                project_id=form.project_id.data,
                workflow_stage=form.workflow_stage.data
            )
            
            db.session.add(task)
            db.session.commit()
            
            # Create folders if requested
            if form.auto_create_folders.data:
                create_task_folders(task)
            
            flash(f'Task "{task.title}" created successfully!', 'success')
            return redirect(url_for('productions.task_management'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating task: {str(e)}', 'error')
    
    return render_template('productions/create-task.html', form=form)

@productions.route('/task-management/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@productions_manager_required
def edit_task(task_id):
    """Edit an existing production task."""
    
    task = ProductionTask.query.get_or_404(task_id)
    
    # Ensure task belongs to production team
    if not task.assigned_to or task.assigned_to not in [member.id for member in get_production_team_members()]:
        flash('Access denied. Task not found in production team.', 'error')
        return redirect(url_for('productions.task_management'))
    
    form = ProductionTaskForm(obj=task)
    
    # Populate assigned_to choices
    team_members = get_production_team_members()
    form.assigned_to.choices = [('', 'Select Assignee')] + [(str(member.id), member.get_full_name()) for member in team_members]
    
    if form.validate_on_submit():
        try:
            # Update task
            task.title = form.title.data
            task.description = form.description.data
            task.task_type = form.task_type.data
            task.priority = form.priority.data
            task.assigned_to = int(form.assigned_to.data) if form.assigned_to.data else None
            task.due_date = form.due_date.data
            task.client_name = form.client_name.data
            task.client_contact = form.client_contact.data
            task.client_phone = form.client_phone.data
            task.client_email = form.client_email.data
            task.estimated_duration_hours = form.estimated_duration_hours.data
            task.project_id = form.project_id.data
            task.workflow_stage = form.workflow_stage.data
            task.updated_at = datetime.now()
            
            db.session.commit()
            
            flash(f'Task "{task.title}" updated successfully!', 'success')
            return redirect(url_for('productions.task_management'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating task: {str(e)}', 'error')
    
    return render_template('productions/edit-task.html', form=form, task=task)

@productions.route('/task-management/<int:task_id>/delete', methods=['POST'])
@login_required
@productions_manager_required
def delete_task(task_id):
    """Delete a production task."""
    
    task = ProductionTask.query.get_or_404(task_id)
    
    # Ensure task belongs to production team
    if not task.assigned_to or task.assigned_to not in [member.id for member in get_production_team_members()]:
        flash('Access denied. Task not found in production team.', 'error')
        return redirect(url_for('productions.task_management'))
    
    try:
        task_title = task.title
        db.session.delete(task)
        db.session.commit()
        flash(f'Task "{task_title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting task: {str(e)}', 'error')
    
    return redirect(url_for('productions.task_management'))

def create_task_folders(task):
    """Create folders for a task on LAN server and Dropbox."""
    try:
        # Generate folder name based on task title and date
        safe_title = "".join(c for c in task.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        folder_name = f"{safe_title}_{task.created_at.strftime('%Y%m%d')}"
        
        # LAN Server path
        lan_base_path = current_app.config.get('LAN_SERVER_PATH', '/mnt/lan_server/productions')
        lan_task_path = os.path.join(lan_base_path, folder_name)
        
        # Dropbox path
        dropbox_base_path = current_app.config.get('DROPBOX_PATH', '/mnt/dropbox/productions')
        dropbox_task_path = os.path.join(dropbox_base_path, folder_name)
        
        # Create LAN server folder
        if not os.path.exists(lan_task_path):
            os.makedirs(lan_task_path, exist_ok=True)
            # Create subfolders
            os.makedirs(os.path.join(lan_task_path, 'raw'), exist_ok=True)
            os.makedirs(os.path.join(lan_task_path, 'processed'), exist_ok=True)
            os.makedirs(os.path.join(lan_task_path, 'final'), exist_ok=True)
            os.makedirs(os.path.join(lan_task_path, 'backup'), exist_ok=True)
        
        # Create Dropbox folder
        if not os.path.exists(dropbox_task_path):
            os.makedirs(dropbox_task_path, exist_ok=True)
            # Create subfolders
            os.makedirs(os.path.join(dropbox_task_path, 'raw'), exist_ok=True)
            os.makedirs(os.path.join(dropbox_task_path, 'processed'), exist_ok=True)
            os.makedirs(os.path.join(dropbox_task_path, 'final'), exist_ok=True)
            os.makedirs(os.path.join(dropbox_task_path, 'backup'), exist_ok=True)
        
        # Update task with folder paths
        task.lan_server_path = lan_task_path
        task.dropbox_path = dropbox_task_path
        db.session.commit()
        
        return True
        
    except Exception as e:
        print(f"Error creating task folders: {str(e)}")
        return False

@productions.route('/task/<int:task_id>/start', methods=['POST'])
@login_required
def start_task(task_id):
    """Start working on a task (change status to in_progress)."""
    
    task = ProductionTask.query.get_or_404(task_id)
    
    # Check if user is assigned to this task or if task is unassigned (visible to all production team)
    if task.assigned_to and task.assigned_to != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied. Task not assigned to you.'})
    
    # Ensure user is part of production team
    if not ensure_production_access(current_user.id):
        return jsonify({'success': False, 'message': 'Access denied. Not a production team member.'})
    
    try:
        task.status = 'in_progress'
        task.start_date = date.today()
        task.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Task started successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@productions.route('/task/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Complete a task (change status to completed)."""
    
    task = ProductionTask.query.get_or_404(task_id)
    
    # Check if user is assigned to this task or if task is unassigned (visible to all production team)
    if task.assigned_to and task.assigned_to != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied. Task not assigned to you.'})
    
    # Ensure user is part of production team
    if not ensure_production_access(current_user.id):
        return jsonify({'success': False, 'message': 'Access denied. Not a production team member.'})
    
    try:
        task.status = 'completed'
        task.completed_at = datetime.now()
        task.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Task completed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@productions.route('/task/<int:task_id>/details')
@login_required
def task_details(task_id):
    """Get task details for modal display."""
    
    task = ProductionTask.query.get_or_404(task_id)
    
    # Check if user has permission to view this task
    if task.assigned_to and task.assigned_to != current_user.id and not current_user.has_permission('manage_productions_team'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Get assigned user
        assigned_user = User.query.get(task.assigned_to) if task.assigned_to else None
        
        # Get today's date for template
        from datetime import date
        today = date.today()
        
        # Render task details HTML
        html = render_template('productions/task_details.html', 
                             task=task, 
                             assigned_user=assigned_user,
                             today=today)
        
        return jsonify({'success': True, 'html': html})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@productions.route('/files')
@login_required
@productions_manager_required
def files():
    """Production Files - View and manage files uploaded by production team."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get team member IDs for filtering files
    team_member_ids = [member.id for member in get_production_team_members()]
    
    # Get files uploaded by production team members
    page = request.args.get('page', 1, type=int)
    files = TaskAttachment.query.join(ProductionTask).filter(
        ProductionTask.assigned_to.in_(team_member_ids)
    ).order_by(TaskAttachment.uploaded_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate file statistics
    all_files = TaskAttachment.query.join(ProductionTask).filter(
        ProductionTask.assigned_to.in_(team_member_ids)
    ).all()
    
    total_files = len(all_files)
    total_size = sum(file.file_size for file in all_files if file.file_size)
    
    # Count files by category
    categories = {}
    for file in all_files:
        category = getattr(file, 'category', 'other')
        categories[category] = categories.get(category, 0) + 1
    
    # Count recent uploads (last 7 days)
    from datetime import datetime, timedelta
    recent_uploads = TaskAttachment.query.join(ProductionTask).filter(
        ProductionTask.assigned_to.in_(team_member_ids),
        TaskAttachment.uploaded_at >= datetime.now() - timedelta(days=7)
    ).count()
    
    file_stats = {
        'total_files': total_files,
        'total_size': total_size,
        'categories': categories,
        'recent_uploads': recent_uploads
    }
    
    return render_template('productions/files.html',
                         files=files,
                         file_stats=file_stats)

@productions.route('/team-chat')
@login_required
@productions_manager_required
def team_chat():
    """Production Team Chat - Team communication for production team."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get production team chat groups
    chat_groups = ChatGroup.query.filter_by(
        team_id=production_team.id,
        is_archived=False
    ).all()
    
    return render_template('productions/team-chat.html',
                         team=production_team,
                         chat_groups=chat_groups)

@productions.route('/team-reports')
@login_required
@productions_manager_required
def team_reports():
    """Production Team Reports - Overview of all team reports."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get report schedules
    report_schedules = ReportSchedule.query.filter_by(
        team_id=production_team.id,
        is_active=True
    ).all()
    
    # Get recent reports summary
    today = date.today()
    recent_daily_count = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == production_team.id,
        TeamMemberDailyReport.report_date >= today - timedelta(days=7)
    ).count()
    
    recent_weekly_count = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == production_team.id,
        TeamMemberWeeklyReport.week_start >= today - timedelta(weeks=4)
    ).count()
    
    recent_monthly_count = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == production_team.id,
        TeamMemberMonthlyReport.month_year >= today.replace(day=1) - timedelta(days=90)
    ).count()
    
    return render_template('productions/team-reports.html',
                         team=production_team,
                         report_schedules=report_schedules,
                         recent_counts={
                             'daily': recent_daily_count,
                             'weekly': recent_weekly_count,
                             'monthly': recent_monthly_count
                         })

@productions.route('/team-reports/daily')
@login_required
@productions_manager_required
def team_reports_daily():
    """Production Daily Team Reports - View daily reports for production team."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get date filter
    report_date = request.args.get('date', date.today().isoformat())
    try:
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    except ValueError:
        report_date = date.today()
    
    # Get daily reports for the specified date
    daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == production_team.id,
        TeamMemberDailyReport.report_date == report_date
    ).all()
    
    # Get team members who should have reports
    team_members = get_production_team_members()
    
    # Match reports with team members
    member_reports = []
    for member in team_members:
        report = next((r for r in daily_reports if r.user_id == member.id), None)
        member_reports.append({
            'user': member,
            'report': report,
            'has_report': report is not None
        })
    
    return render_template('productions/team-reports-daily.html',
                         team=production_team,
                         member_reports=member_reports,
                         report_date=report_date)

@productions.route('/team-reports/weekly')
@login_required
@productions_manager_required
def team_reports_weekly():
    """Production Weekly Team Reports - View weekly reports for production team."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get week filter
    week_start_str = request.args.get('week', '')
    if week_start_str:
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except ValueError:
            week_start = date.today() - timedelta(days=date.today().weekday())
    else:
        week_start = date.today() - timedelta(days=date.today().weekday())
    
    # Get weekly reports for the specified week
    weekly_reports = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == production_team.id,
        TeamMemberWeeklyReport.week_start == week_start
    ).all()
    
    # Get team members who should have reports
    team_members = get_production_team_members()
    
    # Match reports with team members
    member_reports = []
    for member in team_members:
        report = next((r for r in weekly_reports if r.user_id == member.id), None)
        member_reports.append({
            'user': member,
            'report': report,
            'has_report': report is not None
        })
    
    # Calculate weekly statistics
    total_members = len(team_members)
    total_tasks = sum(report.tasks_completed for report in weekly_reports if report and report.tasks_completed)
    avg_productivity = sum(report.productivity_score for report in weekly_reports if report and report.productivity_score) / len(weekly_reports) if weekly_reports else 0
    
    weekly_stats = {
        'total_members': total_members,
        'total_tasks': total_tasks,
        'avg_productivity': round(avg_productivity, 1)
    }
    
    # Prepare chart data (placeholder for now)
    chart_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    chart_data = [75, 82, 78, 85, 90, 88, 92]  # Placeholder data
    
    return render_template('productions/team-reports-weekly.html',
                         team=production_team,
                         member_reports=member_reports,
                         report_week_start=week_start,
                         weekly_stats=weekly_stats,
                         chart_labels=chart_labels,
                         chart_data=chart_data)

@productions.route('/team-reports/monthly')
@login_required
@productions_manager_required
def team_reports_monthly():
    """Production Monthly Team Reports - View monthly reports for production team."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get month filter
    month_year_str = request.args.get('month', '')
    if month_year_str:
        try:
            month_year = datetime.strptime(month_year_str, '%Y-%m').date()
        except ValueError:
            month_year = date.today().replace(day=1)
    else:
        month_year = date.today().replace(day=1)
    
    # Get monthly reports for the specified month
    monthly_reports = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == production_team.id,
        TeamMemberMonthlyReport.month_year == month_year
    ).all()
    
    # Get team members who should have reports
    team_members = get_production_team_members()
    
    # Match reports with team members
    member_reports = []
    for member in team_members:
        report = next((r for r in monthly_reports if r.user_id == member.id), None)
        member_reports.append({
            'user': member,
            'report': report,
            'has_report': report is not None
        })
    
    # Calculate monthly statistics
    total_members = len(team_members)
    total_tasks = sum(report.tasks_completed for report in monthly_reports if report and report.tasks_completed)
    total_hours = sum(report.hours_worked for report in monthly_reports if report and report.hours_worked)
    avg_productivity = sum(report.productivity_score for report in monthly_reports if report and report.productivity_score) / len(monthly_reports) if monthly_reports else 0
    
    monthly_stats = {
        'total_members': total_members,
        'total_tasks': total_tasks,
        'total_hours': total_hours,
        'avg_productivity': round(avg_productivity, 1)
    }
    
    # Prepare chart data (placeholder for now)
    productivity_chart_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
    productivity_chart_data = [78, 82, 85, 88]  # Placeholder data
    
    task_chart_data = [total_tasks, 15, 8]  # Completed, In Progress, Pending
    
    # Prepare insights data
    top_performers = []
    recommendations = []
    
    return render_template('productions/team-reports-monthly.html',
                         team=production_team,
                         member_reports=member_reports,
                         report_month_start=month_year,
                         monthly_stats=monthly_stats,
                         productivity_chart_labels=productivity_chart_labels,
                         productivity_chart_data=productivity_chart_data,
                         task_chart_data=task_chart_data,
                         top_performers=top_performers,
                         recommendations=recommendations)

@productions.route('/team-reports/member/<int:member_id>')
@login_required
@productions_manager_required
def team_member_report(member_id):
    """Production Individual Team Member Report - View detailed report for a specific team member."""
    
    # Validate that the member belongs to the production team
    if not validate_production_member_access(member_id):
        return redirect(url_for('productions.team_reports'))
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get the team member
    member = User.query.get(member_id)
    if not member:
        flash('Team member not found.', 'error')
        return redirect(url_for('productions.team_reports'))
    
    # Get date filters
    report_date = request.args.get('date', date.today().isoformat())
    try:
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    except ValueError:
        report_date = date.today()
    
    # Get reports for the member
    daily_report = TeamMemberDailyReport.query.filter_by(
        user_id=member_id,
        team_id=production_team.id,
        report_date=report_date
    ).first()
    
    week_start = report_date - timedelta(days=report_date.weekday())
    weekly_report = TeamMemberWeeklyReport.query.filter_by(
        user_id=member_id,
        team_id=production_team.id,
        week_start=week_start
    ).first()
    
    month_start = report_date.replace(day=1)
    monthly_report = TeamMemberMonthlyReport.query.filter_by(
        user_id=member_id,
        team_id=production_team.id,
        month_year=month_start
    ).first()
    
    return render_template('productions/team-member-report.html',
                         team=production_team,
                         member=member,
                         daily_report=daily_report,
                         weekly_report=weekly_report,
                         monthly_report=monthly_report,
                         report_date=report_date) 

@productions.route('/team/add-member', methods=['GET', 'POST'])
@login_required
@productions_manager_required
def add_team_member():
    """Add a new member to the production team."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int)
        role = request.form.get('role', 'member')
        
        if not user_id:
            flash('Please select a user to add to the team.', 'error')
            return redirect(url_for('productions.add_team_member'))
        
        # Check if user is already in the team
        existing_membership = UserTeam.query.filter_by(
            user_id=user_id,
            team_id=production_team.id
        ).first()
        
        if existing_membership:
            flash('User is already a member of the production team.', 'error')
            return redirect(url_for('productions.add_team_member'))
        
        # Add user to team
        new_membership = UserTeam(
            user_id=user_id,
            team_id=production_team.id,
            role=role,
            is_active=True,
            joined_date=date.today()
        )
        
        db.session.add(new_membership)
        db.session.commit()
        
        flash('Team member added successfully!', 'success')
        return redirect(url_for('productions.team'))
    
    # Get available users (not already in production team)
    existing_member_ids = [ut.user_id for ut in UserTeam.query.filter_by(
        team_id=production_team.id,
        is_active=True
    ).all()]
    
    available_users = User.query.filter(
        ~User.id.in_(existing_member_ids)
    ).all()
    
    return render_template('productions/add-team-member.html',
                         team=production_team,
                         available_users=available_users)

@productions.route('/team/remove-member/<int:member_id>', methods=['POST'])
@login_required
@productions_manager_required
def remove_team_member(member_id):
    """Remove a member from the production team."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Validate that the member belongs to the production team
    if not validate_production_member_access(member_id):
        return redirect(url_for('productions.team'))
    
    # Deactivate team membership
    membership = UserTeam.query.filter_by(
        user_id=member_id,
        team_id=production_team.id
    ).first()
    
    if membership:
        membership.is_active = False
        membership.left_date = date.today()
        db.session.commit()
        flash('Team member removed successfully!', 'success')
    else:
        flash('Team member not found.', 'error')
    
    return redirect(url_for('productions.team'))

@productions.route('/team/assign-task/<int:task_id>', methods=['POST'])
@login_required
@productions_manager_required
def assign_task_to_member(task_id):
    """Assign a task to a specific team member."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    member_id = request.form.get('member_id', type=int)
    
    if not member_id:
        flash('Please select a team member to assign the task to.', 'error')
        return redirect(url_for('productions.tasks'))
    
    # Validate that the member belongs to the production team
    if not validate_production_member_access(member_id):
        return redirect(url_for('productions.tasks'))
    
    # Get the task
    task = ProductionTask.query.get(task_id)
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('productions.tasks'))
    
    # Assign task to member
    task.assigned_to = member_id
    task.assigned_date = datetime.now()
    db.session.commit()
    
    flash('Task assigned successfully!', 'success')
    return redirect(url_for('productions.tasks'))

@productions.route('/team/performance/<int:member_id>')
@login_required
@productions_manager_required
def team_member_performance(member_id):
    """View detailed performance metrics for a specific team member."""
    
    # Validate that the member belongs to the production team
    if not validate_production_member_access(member_id):
        return redirect(url_for('productions.team'))
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get the team member
    member = User.query.get(member_id)
    if not member:
        flash('Team member not found.', 'error')
        return redirect(url_for('productions.team'))
    
    # Get date filters
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
    
    # Get performance data
    tasks_completed = ProductionTask.query.filter(
        ProductionTask.assigned_to == member_id,
        ProductionTask.status == 'completed',
        ProductionTask.completed_at >= start_date,
        ProductionTask.completed_at <= end_date
    ).count()
    
    tasks_assigned = ProductionTask.query.filter(
        ProductionTask.assigned_to == member_id,
        ProductionTask.created_at >= start_date,
        ProductionTask.created_at <= end_date
    ).count()
    
    # Get daily reports for the period
    daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.user_id == member_id,
        TeamMemberDailyReport.team_id == production_team.id,
        TeamMemberDailyReport.report_date >= start_date,
        TeamMemberDailyReport.report_date <= end_date
    ).order_by(TeamMemberDailyReport.report_date).all()
    
    # Calculate productivity trends
    productivity_data = []
    for report in daily_reports:
        productivity_data.append({
            'date': report.report_date,
            'productivity_score': report.get_productivity_score(),
            'tasks_completed': report.tasks_completed,
            'tasks_assigned': report.tasks_assigned
        })
    
    return render_template('productions/team-member-performance.html',
                         team=production_team,
                         member=member,
                         start_date=start_date,
                         end_date=end_date,
                         tasks_completed=tasks_completed,
                         tasks_assigned=tasks_assigned,
                         productivity_data=productivity_data)

@productions.route('/team/workload-balance')
@login_required
@productions_manager_required
def workload_balance():
    """View and manage workload distribution across team members."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    team_members = get_production_team_members()
    
    # Get workload data for each member
    workload_data = []
    for member in team_members:
        # Count active tasks assigned to member
        active_tasks = ProductionTask.query.filter(
            ProductionTask.assigned_to == member.id,
            ProductionTask.status.in_(['pending', 'in_progress'])
        ).count()
        
        # Count completed tasks this week
        week_start = date.today() - timedelta(days=date.today().weekday())
        completed_this_week = ProductionTask.query.filter(
            ProductionTask.assigned_to == member.id,
            ProductionTask.status == 'completed',
            ProductionTask.completed_at >= week_start
        ).count()
        
        # Get today's performance
        today_report = TeamMemberDailyReport.query.filter_by(
            user_id=member.id,
            team_id=production_team.id,
            report_date=date.today()
        ).first()
        
        workload_data.append({
            'member': member,
            'active_tasks': active_tasks,
            'completed_this_week': completed_this_week,
            'today_tasks': today_report.tasks_completed if today_report else 0,
            'productivity_score': today_report.get_productivity_score() if today_report else 0
        })
    
    return render_template('productions/workload-balance.html',
                         team=production_team,
                         workload_data=workload_data)

@productions.route('/team/notifications')
@login_required
@productions_manager_required
def team_notifications():
    """Manage team notifications and announcements."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        message = request.form.get('message')
        notification_type = request.form.get('type', 'announcement')
        
        if message:
            # Create notification (this would be stored in a notifications table)
            flash('Notification sent to team!', 'success')
        else:
            flash('Please enter a message.', 'error')
    
    return render_template('productions/team-notifications.html',
                         team=production_team)

@productions.route('/team/file-sharing')
@login_required
@productions_manager_required
def file_sharing():
    """Manage team file sharing and collaboration."""
    
    production_team = get_production_team()
    if not production_team:
        return redirect(url_for('auth.login'))
    
    # Get team files (this would come from a files table)
    team_files = []  # Placeholder for file data
    
    return render_template('productions/file-sharing.html',
                         team=production_team,
                         team_files=team_files) 

@productions.route('/api/team-reports/daily')
@login_required
@productions_manager_required
def api_team_reports_daily():
    """API endpoint to get daily team reports for production team."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get date filter
        report_date = request.args.get('date', date.today().isoformat())
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get daily reports for the team
        daily_reports = TeamMemberDailyReport.query.filter_by(
            team_id=production_team.id,
            report_date=report_date
        ).all()
        
        # Format response
        reports_data = []
        for report in daily_reports:
            user = User.query.get(report.user_id)
            if user:
                reports_data.append({
                    'id': report.id,
                    'user_id': report.user_id,
                    'user_name': user.name,
                    'user_email': user.email,
                    'report_date': report.report_date.isoformat(),
                    'login_time': report.login_time.isoformat() if report.login_time else None,
                    'logout_time': report.logout_time.isoformat() if report.logout_time else None,
                    'total_active_time': report.total_active_time,
                    'total_break_time': report.total_break_time,
                    'leads_created': report.leads_created,
                    'leads_updated': report.leads_updated,
                    'tasks_completed': report.tasks_completed,
                    'tasks_assigned': report.tasks_assigned,
                    'calls_made': report.calls_made,
                    'followups_added': report.followups_added,
                    'messages_sent': report.messages_sent,
                    'messages_received': report.messages_received,
                    'mentions_count': report.mentions_count,
                    'daily_goal': report.daily_goal,
                    'goal_achievement': report.goal_achievement,
                    'notes': report.notes,
                    'manager_notes': report.manager_notes,
                    'status': report.status,
                    'created_at': report.created_at.isoformat(),
                    'updated_at': report.updated_at.isoformat()
                })
        
        return jsonify({
            'success': True,
            'team_id': production_team.id,
            'team_name': production_team.name,
            'report_date': report_date.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/daily/<int:member_id>')
@login_required
@productions_manager_required
def api_team_member_daily_report(member_id):
    """API endpoint to get daily report for a specific production team member."""
    try:
        # Validate member access
        if not validate_production_member_access(member_id):
            return jsonify({'error': 'Access denied to this team member'}), 403
        
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get date filter
        report_date = request.args.get('date', date.today().isoformat())
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get the specific member's daily report
        report = TeamMemberDailyReport.query.filter_by(
            user_id=member_id,
            team_id=production_team.id,
            report_date=report_date
        ).first()
        
        if not report:
            return jsonify({'error': 'Daily report not found for this member and date'}), 404
        
        user = User.query.get(member_id)
        
        return jsonify({
            'success': True,
            'report': {
                'id': report.id,
                'user_id': report.user_id,
                'user_name': user.name if user else 'Unknown',
                'user_email': user.email if user else '',
                'report_date': report.report_date.isoformat(),
                'login_time': report.login_time.isoformat() if report.login_time else None,
                'logout_time': report.logout_time.isoformat() if report.logout_time else None,
                'total_active_time': report.total_active_time,
                'total_break_time': report.total_break_time,
                'leads_created': report.leads_created,
                'leads_updated': report.leads_updated,
                'tasks_completed': report.tasks_completed,
                'tasks_assigned': report.tasks_assigned,
                'calls_made': report.calls_made,
                'followups_added': report.followups_added,
                'messages_sent': report.messages_sent,
                'messages_received': report.messages_received,
                'mentions_count': report.mentions_count,
                'daily_goal': report.daily_goal,
                'goal_achievement': report.goal_achievement,
                'notes': report.notes,
                'manager_notes': report.manager_notes,
                'status': report.status,
                'created_at': report.created_at.isoformat(),
                'updated_at': report.updated_at.isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/daily/generate', methods=['POST'])
@login_required
@productions_manager_required
def api_generate_daily_reports():
    """API endpoint to generate daily reports for production team."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get date from request
        report_date = request.json.get('date', date.today().isoformat())
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get team members
        team_members = get_production_team_members()
        
        generated_reports = []
        
        for member in team_members:
            # Check if report already exists
            existing_report = TeamMemberDailyReport.query.filter_by(
                user_id=member.id,
                team_id=production_team.id,
                report_date=report_date
            ).first()
            
            if existing_report:
                generated_reports.append({
                    'user_id': member.id,
                    'user_name': member.name,
                    'status': 'already_exists',
                    'report_id': existing_report.id
                })
                continue
            
            # Create new daily report
            new_report = TeamMemberDailyReport(
                user_id=member.id,
                team_id=production_team.id,
                report_date=report_date,
                daily_goal=15,  # Default goal for production
                status='active'
            )
            
            db.session.add(new_report)
            generated_reports.append({
                'user_id': member.id,
                'user_name': member.name,
                'status': 'generated',
                'report_id': new_report.id
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(generated_reports)} daily reports',
            'report_date': report_date.isoformat(),
            'reports': generated_reports
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/weekly')
@login_required
@productions_manager_required
def api_team_reports_weekly():
    """API endpoint to get weekly team reports for production team."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get week filter
        week_start_str = request.args.get('week_start', '')
        if week_start_str:
            try:
                week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            except ValueError:
                week_start = date.today() - timedelta(days=date.today().weekday())
        else:
            week_start = date.today() - timedelta(days=date.today().weekday())
        
        # Get weekly reports for the team
        weekly_reports = TeamMemberWeeklyReport.query.filter_by(
            team_id=production_team.id,
            week_start=week_start
        ).all()
        
        # Format response
        reports_data = []
        for report in weekly_reports:
            user = User.query.get(report.user_id)
            if user:
                reports_data.append({
                    'id': report.id,
                    'user_id': report.user_id,
                    'user_name': user.name,
                    'user_email': user.email,
                    'week_start': report.week_start.isoformat(),
                    'total_leads_created': report.total_leads_created,
                    'total_leads_updated': report.total_leads_updated,
                    'total_tasks_completed': report.total_tasks_completed,
                    'total_tasks_assigned': report.total_tasks_assigned,
                    'total_calls_made': report.total_calls_made,
                    'total_followups_added': report.total_followups_added,
                    'total_messages_sent': report.total_messages_sent,
                    'total_messages_received': report.total_messages_received,
                    'total_mentions_count': report.total_mentions_count,
                    'total_active_time': report.total_active_time,
                    'total_break_time': report.total_break_time,
                    'average_daily_active_time': report.average_daily_active_time,
                    'weekly_goal': report.weekly_goal,
                    'goal_achievement': report.goal_achievement,
                    'productivity_trend': report.productivity_trend,
                    'performance_rating': report.performance_rating,
                    'workload_distribution': report.workload_distribution,
                    'peak_performance_day': report.peak_performance_day,
                    'notes': report.notes,
                    'manager_notes': report.manager_notes,
                    'status': report.status,
                    'created_at': report.created_at.isoformat(),
                    'updated_at': report.updated_at.isoformat()
                })
        
        return jsonify({
            'success': True,
            'team_id': production_team.id,
            'team_name': production_team.name,
            'week_start': week_start.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/weekly/<int:member_id>')
@login_required
@productions_manager_required
def api_team_member_weekly_report(member_id):
    """API endpoint to get weekly report for a specific production team member."""
    try:
        # Validate member access
        if not validate_production_member_access(member_id):
            return jsonify({'error': 'Access denied to this team member'}), 403
        
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get week filter
        week_start_str = request.args.get('week_start', '')
        if week_start_str:
            try:
                week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            except ValueError:
                week_start = date.today() - timedelta(days=date.today().weekday())
        else:
            week_start = date.today() - timedelta(days=date.today().weekday())
        
        # Get the specific member's weekly report
        report = TeamMemberWeeklyReport.query.filter_by(
            user_id=member_id,
            team_id=production_team.id,
            week_start=week_start
        ).first()
        
        if not report:
            return jsonify({'error': 'Weekly report not found for this member and week'}), 404
        
        user = User.query.get(member_id)
        
        return jsonify({
            'success': True,
            'report': {
                'id': report.id,
                'user_id': report.user_id,
                'user_name': user.name if user else 'Unknown',
                'user_email': user.email if user else '',
                'week_start': report.week_start.isoformat(),
                'total_leads_created': report.total_leads_created,
                'total_leads_updated': report.total_leads_updated,
                'total_tasks_completed': report.total_tasks_completed,
                'total_tasks_assigned': report.total_tasks_assigned,
                'total_calls_made': report.total_calls_made,
                'total_followups_added': report.total_followups_added,
                'total_messages_sent': report.total_messages_sent,
                'total_messages_received': report.total_messages_received,
                'total_mentions_count': report.total_mentions_count,
                'total_active_time': report.total_active_time,
                'total_break_time': report.total_break_time,
                'average_daily_active_time': report.average_daily_active_time,
                'weekly_goal': report.weekly_goal,
                'goal_achievement': report.goal_achievement,
                'productivity_trend': report.productivity_trend,
                'performance_rating': report.performance_rating,
                'workload_distribution': report.workload_distribution,
                'peak_performance_day': report.peak_performance_day,
                'notes': report.notes,
                'manager_notes': report.manager_notes,
                'status': report.status,
                'created_at': report.created_at.isoformat(),
                'updated_at': report.updated_at.isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/weekly/generate', methods=['POST'])
@login_required
@productions_manager_required
def api_generate_weekly_reports():
    """API endpoint to generate weekly reports for production team."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get week from request
        week_start_str = request.json.get('week_start', '')
        if week_start_str:
            try:
                week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            except ValueError:
                week_start = date.today() - timedelta(days=date.today().weekday())
        else:
            week_start = date.today() - timedelta(days=date.today().weekday())
        
        # Get team members
        team_members = get_production_team_members()
        
        generated_reports = []
        
        for member in team_members:
            # Check if report already exists
            existing_report = TeamMemberWeeklyReport.query.filter_by(
                user_id=member.id,
                team_id=production_team.id,
                week_start=week_start
            ).first()
            
            if existing_report:
                generated_reports.append({
                    'user_id': member.id,
                    'user_name': member.name,
                    'status': 'already_exists',
                    'report_id': existing_report.id
                })
                continue
            
            # Create new weekly report
            new_report = TeamMemberWeeklyReport(
                user_id=member.id,
                team_id=production_team.id,
                week_start=week_start,
                weekly_goal=75,  # Default goal for production
                status='active'
            )
            
            db.session.add(new_report)
            generated_reports.append({
                'user_id': member.id,
                'user_name': member.name,
                'status': 'generated',
                'report_id': new_report.id
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(generated_reports)} weekly reports',
            'week_start': week_start.isoformat(),
            'reports': generated_reports
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/monthly')
@login_required
@productions_manager_required
def api_team_reports_monthly():
    """API endpoint to get monthly team reports for production team."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get month filter
        month_year_str = request.args.get('month_year', '')
        if month_year_str:
            try:
                month_year = datetime.strptime(month_year_str, '%Y-%m').date()
                month_year = month_year.replace(day=1)
            except ValueError:
                month_year = date.today().replace(day=1)
        else:
            month_year = date.today().replace(day=1)
        
        # Get monthly reports for the team
        monthly_reports = TeamMemberMonthlyReport.query.filter_by(
            team_id=production_team.id,
            month_year=month_year
        ).all()
        
        # Format response
        reports_data = []
        for report in monthly_reports:
            user = User.query.get(report.user_id)
            if user:
                reports_data.append({
                    'id': report.id,
                    'user_id': report.user_id,
                    'user_name': user.name,
                    'user_email': user.email,
                    'month_year': report.month_year.isoformat(),
                    'total_leads_created': report.total_leads_created,
                    'total_leads_updated': report.total_leads_updated,
                    'total_tasks_completed': report.total_tasks_completed,
                    'total_tasks_assigned': report.total_tasks_assigned,
                    'total_calls_made': report.total_calls_made,
                    'total_followups_added': report.total_followups_added,
                    'total_messages_sent': report.total_messages_sent,
                    'total_messages_received': report.total_messages_received,
                    'total_mentions_count': report.total_mentions_count,
                    'total_active_time': report.total_active_time,
                    'total_break_time': report.total_break_time,
                    'average_daily_active_time': report.average_daily_active_time,
                    'monthly_goal': report.monthly_goal,
                    'goal_achievement': report.goal_achievement,
                    'productivity_trend': report.productivity_trend,
                    'performance_rating': report.performance_rating,
                    'team_ranking': report.team_ranking,
                    'improvement_trend': report.improvement_trend,
                    'monthly_summary': report.monthly_summary,
                    'notes': report.notes,
                    'manager_notes': report.manager_notes,
                    'status': report.status,
                    'created_at': report.created_at.isoformat(),
                    'updated_at': report.updated_at.isoformat()
                })
        
        return jsonify({
            'success': True,
            'team_id': production_team.id,
            'team_name': production_team.name,
            'month_year': month_year.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/monthly/<int:member_id>')
@login_required
@productions_manager_required
def api_team_member_monthly_report(member_id):
    """API endpoint to get monthly report for a specific production team member."""
    try:
        # Validate member access
        if not validate_production_member_access(member_id):
            return jsonify({'error': 'Access denied to this team member'}), 403
        
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get month filter
        month_year_str = request.args.get('month_year', '')
        if month_year_str:
            try:
                month_year = datetime.strptime(month_year_str, '%Y-%m').date()
                month_year = month_year.replace(day=1)
            except ValueError:
                month_year = date.today().replace(day=1)
        else:
            month_year = date.today().replace(day=1)
        
        # Get the specific member's monthly report
        report = TeamMemberMonthlyReport.query.filter_by(
            user_id=member_id,
            team_id=production_team.id,
            month_year=month_year
        ).first()
        
        if not report:
            return jsonify({'error': 'Monthly report not found for this member and month'}), 404
        
        user = User.query.get(member_id)
        
        return jsonify({
            'success': True,
            'report': {
                'id': report.id,
                'user_id': report.user_id,
                'user_name': user.name if user else 'Unknown',
                'user_email': user.email if user else '',
                'month_year': report.month_year.isoformat(),
                'total_leads_created': report.total_leads_created,
                'total_leads_updated': report.total_leads_updated,
                'total_tasks_completed': report.total_tasks_completed,
                'total_tasks_assigned': report.total_tasks_assigned,
                'total_calls_made': report.total_calls_made,
                'total_followups_added': report.total_followups_added,
                'total_messages_sent': report.total_messages_sent,
                'total_messages_received': report.total_messages_received,
                'total_mentions_count': report.total_mentions_count,
                'total_active_time': report.total_active_time,
                'total_break_time': report.total_break_time,
                'average_daily_active_time': report.average_daily_active_time,
                'monthly_goal': report.monthly_goal,
                'goal_achievement': report.goal_achievement,
                'productivity_trend': report.productivity_trend,
                'performance_rating': report.performance_rating,
                'team_ranking': report.team_ranking,
                'improvement_trend': report.improvement_trend,
                'monthly_summary': report.monthly_summary,
                'notes': report.notes,
                'manager_notes': report.manager_notes,
                'status': report.status,
                'created_at': report.created_at.isoformat(),
                'updated_at': report.updated_at.isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/monthly/generate', methods=['POST'])
@login_required
@productions_manager_required
def api_generate_monthly_reports():
    """API endpoint to generate monthly reports for production team."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get month from request
        month_year_str = request.json.get('month_year', '')
        if month_year_str:
            try:
                month_year = datetime.strptime(month_year_str, '%Y-%m').date()
                month_year = month_year.replace(day=1)
            except ValueError:
                month_year = date.today().replace(day=1)
        else:
            month_year = date.today().replace(day=1)
        
        # Get team members
        team_members = get_production_team_members()
        
        generated_reports = []
        
        for member in team_members:
            # Check if report already exists
            existing_report = TeamMemberMonthlyReport.query.filter_by(
                user_id=member.id,
                team_id=production_team.id,
                month_year=month_year
            ).first()
            
            if existing_report:
                generated_reports.append({
                    'user_id': member.id,
                    'user_name': member.name,
                    'status': 'already_exists',
                    'report_id': existing_report.id
                })
                continue
            
            # Create new monthly report
            new_report = TeamMemberMonthlyReport(
                user_id=member.id,
                team_id=production_team.id,
                month_year=month_year,
                monthly_goal=300,  # Default goal for production
                status='active'
            )
            
            db.session.add(new_report)
            generated_reports.append({
                'user_id': member.id,
                'user_name': member.name,
                'status': 'generated',
                'report_id': new_report.id
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(generated_reports)} monthly reports',
            'month_year': month_year.isoformat(),
            'reports': generated_reports
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 

@productions.route('/api/team-reports/export/pdf')
@login_required
@productions_manager_required
def api_export_reports_pdf():
    """API endpoint to export team reports as PDF."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get report type and date filters
        report_type = request.args.get('type', 'daily')  # daily, weekly, monthly
        report_date = request.args.get('date', date.today().isoformat())
        member_id = request.args.get('member_id', None)
        
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get reports based on type
        if report_type == 'daily':
            if member_id:
                reports = TeamMemberDailyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    report_date=report_date
                ).all()
            else:
                reports = TeamMemberDailyReport.query.filter_by(
                    team_id=production_team.id,
                    report_date=report_date
                ).all()
        elif report_type == 'weekly':
            week_start = report_date - timedelta(days=report_date.weekday())
            if member_id:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    week_start=week_start
                ).all()
            else:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    team_id=production_team.id,
                    week_start=week_start
                ).all()
        elif report_type == 'monthly':
            month_start = report_date.replace(day=1)
            if member_id:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    month_year=month_start
                ).all()
            else:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    team_id=production_team.id,
                    month_year=month_start
                ).all()
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        # For now, return JSON with report data
        # In a real implementation, you would generate a PDF file
        reports_data = []
        for report in reports:
            user = User.query.get(report.user_id)
            if user:
                report_data = {
                    'user_name': user.name,
                    'user_email': user.email,
                    'report_type': report_type,
                    'report_date': report_date.isoformat()
                }
                
                if report_type == 'daily':
                    report_data.update({
                        'leads_created': report.leads_created,
                        'tasks_completed': report.tasks_completed,
                        'calls_made': report.calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement
                    })
                elif report_type == 'weekly':
                    report_data.update({
                        'total_leads_created': report.total_leads_created,
                        'total_tasks_completed': report.total_tasks_completed,
                        'total_calls_made': report.total_calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement,
                        'productivity_trend': report.productivity_trend
                    })
                elif report_type == 'monthly':
                    report_data.update({
                        'total_leads_created': report.total_leads_created,
                        'total_tasks_completed': report.total_tasks_completed,
                        'total_calls_made': report.total_calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement,
                        'performance_rating': report.performance_rating,
                        'team_ranking': report.team_ranking
                    })
                
                reports_data.append(report_data)
        
        return jsonify({
            'success': True,
            'message': f'PDF export data for {report_type} reports',
            'team_name': production_team.name,
            'report_type': report_type,
            'report_date': report_date.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/export/excel')
@login_required
@productions_manager_required
def api_export_reports_excel():
    """API endpoint to export team reports as Excel."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get report type and date filters
        report_type = request.args.get('type', 'daily')  # daily, weekly, monthly
        report_date = request.args.get('date', date.today().isoformat())
        member_id = request.args.get('member_id', None)
        
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get reports based on type
        if report_type == 'daily':
            if member_id:
                reports = TeamMemberDailyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    report_date=report_date
                ).all()
            else:
                reports = TeamMemberDailyReport.query.filter_by(
                    team_id=production_team.id,
                    report_date=report_date
                ).all()
        elif report_type == 'weekly':
            week_start = report_date - timedelta(days=report_date.weekday())
            if member_id:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    week_start=week_start
                ).all()
            else:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    team_id=production_team.id,
                    week_start=week_start
                ).all()
        elif report_type == 'monthly':
            month_start = report_date.replace(day=1)
            if member_id:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    month_year=month_start
                ).all()
            else:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    team_id=production_team.id,
                    month_year=month_start
                ).all()
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        # For now, return JSON with report data
        # In a real implementation, you would generate an Excel file
        reports_data = []
        for report in reports:
            user = User.query.get(report.user_id)
            if user:
                report_data = {
                    'user_name': user.name,
                    'user_email': user.email,
                    'report_type': report_type,
                    'report_date': report_date.isoformat()
                }
                
                if report_type == 'daily':
                    report_data.update({
                        'leads_created': report.leads_created,
                        'tasks_completed': report.tasks_completed,
                        'calls_made': report.calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement
                    })
                elif report_type == 'weekly':
                    report_data.update({
                        'total_leads_created': report.total_leads_created,
                        'total_tasks_completed': report.total_tasks_completed,
                        'total_calls_made': report.total_calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement,
                        'productivity_trend': report.productivity_trend
                    })
                elif report_type == 'monthly':
                    report_data.update({
                        'total_leads_created': report.total_leads_created,
                        'total_tasks_completed': report.total_tasks_completed,
                        'total_calls_made': report.total_calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement,
                        'performance_rating': report.performance_rating,
                        'team_ranking': report.team_ranking
                    })
                
                reports_data.append(report_data)
        
        return jsonify({
            'success': True,
            'message': f'Excel export data for {report_type} reports',
            'team_name': production_team.name,
            'report_type': report_type,
            'report_date': report_date.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/export/csv')
@login_required
@productions_manager_required
def api_export_reports_csv():
    """API endpoint to export team reports as CSV."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get report type and date filters
        report_type = request.args.get('type', 'daily')  # daily, weekly, monthly
        report_date = request.args.get('date', date.today().isoformat())
        member_id = request.args.get('member_id', None)
        
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get reports based on type
        if report_type == 'daily':
            if member_id:
                reports = TeamMemberDailyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    report_date=report_date
                ).all()
            else:
                reports = TeamMemberDailyReport.query.filter_by(
                    team_id=production_team.id,
                    report_date=report_date
                ).all()
        elif report_type == 'weekly':
            week_start = report_date - timedelta(days=report_date.weekday())
            if member_id:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    week_start=week_start
                ).all()
            else:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    team_id=production_team.id,
                    week_start=week_start
                ).all()
        elif report_type == 'monthly':
            month_start = report_date.replace(day=1)
            if member_id:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    user_id=member_id,
                    team_id=production_team.id,
                    month_year=month_start
                ).all()
            else:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    team_id=production_team.id,
                    month_year=month_start
                ).all()
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        # For now, return JSON with report data
        # In a real implementation, you would generate a CSV file
        reports_data = []
        for report in reports:
            user = User.query.get(report.user_id)
            if user:
                report_data = {
                    'user_name': user.name,
                    'user_email': user.email,
                    'report_type': report_type,
                    'report_date': report_date.isoformat()
                }
                
                if report_type == 'daily':
                    report_data.update({
                        'leads_created': report.leads_created,
                        'tasks_completed': report.tasks_completed,
                        'calls_made': report.calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement
                    })
                elif report_type == 'weekly':
                    report_data.update({
                        'total_leads_created': report.total_leads_created,
                        'total_tasks_completed': report.total_tasks_completed,
                        'total_calls_made': report.total_calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement,
                        'productivity_trend': report.productivity_trend
                    })
                elif report_type == 'monthly':
                    report_data.update({
                        'total_leads_created': report.total_leads_created,
                        'total_tasks_completed': report.total_tasks_completed,
                        'total_calls_made': report.total_calls_made,
                        'total_active_time': report.total_active_time,
                        'goal_achievement': report.goal_achievement,
                        'performance_rating': report.performance_rating,
                        'team_ranking': report.team_ranking
                    })
                
                reports_data.append(report_data)
        
        return jsonify({
            'success': True,
            'message': f'CSV export data for {report_type} reports',
            'team_name': production_team.name,
            'report_type': report_type,
            'report_date': report_date.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/schedule', methods=['POST'])
@login_required
@productions_manager_required
def api_schedule_reports():
    """API endpoint to schedule automated reports."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract schedule data
        report_type = data.get('report_type')  # daily, weekly, monthly
        frequency = data.get('frequency')  # daily, weekly, monthly
        delivery_time = data.get('delivery_time', '09:00')  # HH:MM format
        delivery_method = data.get('delivery_method', 'email')  # email, dashboard
        recipients = data.get('recipients', [])  # list of email addresses
        custom_metrics = data.get('custom_metrics', [])  # list of metrics to include
        format_type = data.get('format', 'pdf')  # pdf, excel, csv
        
        if not report_type or not frequency:
            return jsonify({'error': 'Report type and frequency are required'}), 400
        
        # Create new report schedule
        new_schedule = ReportSchedule(
            team_id=production_team.id,
            report_type=report_type,
            frequency=frequency,
            delivery_time=delivery_time,
            delivery_method=delivery_method,
            recipients=','.join(recipients) if recipients else '',
            custom_metrics=','.join(custom_metrics) if custom_metrics else '',
            format_type=format_type,
            status='active',
            created_by=current_user.id
        )
        
        db.session.add(new_schedule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scheduled {frequency} {report_type} reports',
            'schedule_id': new_schedule.id,
            'schedule': {
                'id': new_schedule.id,
                'report_type': new_schedule.report_type,
                'frequency': new_schedule.frequency,
                'delivery_time': new_schedule.delivery_time,
                'delivery_method': new_schedule.delivery_method,
                'recipients': new_schedule.recipients.split(',') if new_schedule.recipients else [],
                'custom_metrics': new_schedule.custom_metrics.split(',') if new_schedule.custom_metrics else [],
                'format_type': new_schedule.format_type,
                'status': new_schedule.status,
                'created_at': new_schedule.created_at.isoformat()
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/schedule', methods=['GET'])
@login_required
@productions_manager_required
def api_get_report_schedules():
    """API endpoint to get report schedules."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get all schedules for the team
        schedules = ReportSchedule.query.filter_by(
            team_id=production_team.id,
            status='active'
        ).all()
        
        schedules_data = []
        for schedule in schedules:
            schedules_data.append({
                'id': schedule.id,
                'report_type': schedule.report_type,
                'frequency': schedule.frequency,
                'delivery_time': schedule.delivery_time,
                'delivery_method': schedule.delivery_method,
                'recipients': schedule.recipients.split(',') if schedule.recipients else [],
                'custom_metrics': schedule.custom_metrics.split(',') if schedule.custom_metrics else [],
                'format_type': schedule.format_type,
                'status': schedule.status,
                'created_at': schedule.created_at.isoformat(),
                'updated_at': schedule.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'schedules': schedules_data,
            'total_schedules': len(schedules_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/schedule/<int:schedule_id>', methods=['PUT'])
@login_required
@productions_manager_required
def api_update_report_schedule(schedule_id):
    """API endpoint to update a report schedule."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get the schedule
        schedule = ReportSchedule.query.filter_by(
            id=schedule_id,
            team_id=production_team.id
        ).first()
        
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update schedule fields
        if 'report_type' in data:
            schedule.report_type = data['report_type']
        if 'frequency' in data:
            schedule.frequency = data['frequency']
        if 'delivery_time' in data:
            schedule.delivery_time = data['delivery_time']
        if 'delivery_method' in data:
            schedule.delivery_method = data['delivery_method']
        if 'recipients' in data:
            schedule.recipients = ','.join(data['recipients']) if data['recipients'] else ''
        if 'custom_metrics' in data:
            schedule.custom_metrics = ','.join(data['custom_metrics']) if data['custom_metrics'] else ''
        if 'format_type' in data:
            schedule.format_type = data['format_type']
        if 'status' in data:
            schedule.status = data['status']
        
        schedule.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule updated successfully',
            'schedule': {
                'id': schedule.id,
                'report_type': schedule.report_type,
                'frequency': schedule.frequency,
                'delivery_time': schedule.delivery_time,
                'delivery_method': schedule.delivery_method,
                'recipients': schedule.recipients.split(',') if schedule.recipients else [],
                'custom_metrics': schedule.custom_metrics.split(',') if schedule.custom_metrics else [],
                'format_type': schedule.format_type,
                'status': schedule.status,
                'created_at': schedule.created_at.isoformat(),
                'updated_at': schedule.updated_at.isoformat()
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productions.route('/api/team-reports/schedule/<int:schedule_id>', methods=['DELETE'])
@login_required
@productions_manager_required
def api_delete_report_schedule(schedule_id):
    """API endpoint to delete a report schedule."""
    try:
        production_team = get_production_team()
        if not production_team:
            return jsonify({'error': 'Production team not found'}), 404
        
        # Get the schedule
        schedule = ReportSchedule.query.filter_by(
            id=schedule_id,
            team_id=production_team.id
        ).first()
        
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        # Soft delete by setting status to inactive
        schedule.status = 'inactive'
        schedule.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 