from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_
from . import db
from .models import User, Role, Lead, Team, UserTeam, TeamMemberDailyReport, TeamMemberWeeklyReport, TeamMemberMonthlyReport, ReportSchedule, ChatGroup, Call
from .auth import permission_required

marketing = Blueprint('marketing', __name__, url_prefix='/marketing')

def marketing_manager_required(f):
    """Decorator to require marketing manager permissions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.has_permission('manage_marketing_team'):
            flash('Access denied. Marketing Manager privileges required.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_marketing_team():
    """Get the marketing team, ensuring it exists."""
    marketing_team = Team.query.filter_by(name='Marketing Team').first()
    if not marketing_team:
        flash('Marketing team not found. Please contact administrator.', 'error')
        return None
    return marketing_team

def get_marketing_team_members():
    """Get all active marketing team members."""
    marketing_team = get_marketing_team()
    if not marketing_team:
        return []
    
    return User.query.join(UserTeam).filter(
        UserTeam.team_id == marketing_team.id,
        UserTeam.is_active == True
    ).all()

def filter_marketing_data(query, team_id_field='team_id'):
    """Filter data to only include marketing team data."""
    marketing_team = get_marketing_team()
    if not marketing_team:
        return query.filter(False)  # Return empty result
    
    return query.filter(getattr(query.model, team_id_field) == marketing_team.id)

def ensure_marketing_access(user_id):
    """Ensure a user is a member of the marketing team."""
    marketing_team = get_marketing_team()
    if not marketing_team:
        return False
    
    user_team = UserTeam.query.filter_by(
        user_id=user_id,
        team_id=marketing_team.id,
        is_active=True
    ).first()
    
    return user_team is not None

def validate_marketing_member_access(member_id):
    """Validate that a member belongs to the marketing team or is a Caller role user."""
    # Allow access to Caller role users regardless of team membership
    member = User.query.get(member_id)
    if member and member.role.name == 'Caller':
        return True
    
    # For other roles, check marketing team membership
    if not ensure_marketing_access(member_id):
        flash('Access denied. User is not a member of the marketing team.', 'error')
        return False
    return True

@marketing.route('/dashboard')
@login_required
@marketing_manager_required
def dashboard():
    """Marketing Manager Dashboard - Overview of marketing team performance."""
    
    # Get marketing team members
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    team_members = get_marketing_team_members()
    
    # Get today's date
    today = date.today()
    
    # Get daily reports for today - filtered to marketing team only
    daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == marketing_team.id,
        TeamMemberDailyReport.report_date == today
    ).all()
    
    # Calculate team statistics with null handling
    total_leads_today = sum(report.leads_created or 0 for report in daily_reports)
    total_calls_today = sum(report.calls_made or 0 for report in daily_reports)
    total_tasks_completed = sum(report.tasks_completed or 0 for report in daily_reports)
    total_active_time = sum(report.total_active_time or 0 for report in daily_reports)
    
    # Calculate follow-up call metrics for today
    from datetime import datetime
    from app.models import Call, Lead
    
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get follow-up calls made by marketing team members today
    # Count leads with follow-up dates set by team members (same logic as main dashboard)
    team_member_ids = [member.id for member in team_members]
    today_followup_calls = Lead.query.filter(
        Lead.created_by.in_(team_member_ids),
        Lead.followup_date != None,
        Lead.followup_date != '',
        Lead.followup_date != '-',
        func.date(Lead.updated_at) == today  # Only count leads updated today (when follow-up date was set)
    ).count()
    
    # Get weekly reports for current week - filtered to marketing team only
    week_start = today - timedelta(days=today.weekday())
    weekly_reports = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == marketing_team.id,
        TeamMemberWeeklyReport.week_start == week_start
    ).all()
    
    # Calculate weekly statistics with null handling
    total_leads_week = sum(report.total_leads_created or 0 for report in weekly_reports)
    total_calls_week = sum(report.total_calls_made or 0 for report in weekly_reports)
    total_tasks_week = sum(report.total_tasks_completed or 0 for report in weekly_reports)
    
    # Calculate follow-up call metrics for this week
    week_followup_calls = Lead.query.filter(
        Lead.created_by.in_(team_member_ids),
        Lead.followup_date != None,
        Lead.followup_date != '',
        Lead.followup_date != '-',
        Lead.updated_at >= week_start  # Count leads updated this week (when follow-up date was set)
    ).count()
    
    # Get monthly reports for current month - filtered to marketing team only
    month_start = date(today.year, today.month, 1)
    monthly_reports = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == marketing_team.id,
        TeamMemberMonthlyReport.month_year == month_start
    ).all()
    
    # Calculate monthly statistics with null handling
    total_leads_month = sum(report.total_leads_created or 0 for report in monthly_reports)
    total_calls_month = sum(report.total_calls_made or 0 for report in monthly_reports)
    total_tasks_month = sum(report.total_tasks_completed or 0 for report in monthly_reports)
    
    # Calculate follow-up call metrics for this month
    month_followup_calls = Lead.query.filter(
        Lead.created_by.in_(team_member_ids),
        Lead.followup_date != None,
        Lead.followup_date != '',
        Lead.followup_date != '-',
        Lead.updated_at >= month_start  # Count leads updated this month (when follow-up date was set)
    ).count()
    
    # Get recent leads - filtered to marketing team members only
    recent_leads = Lead.query.filter(
        Lead.created_by.in_(team_member_ids)
    ).order_by(Lead.created_at.desc()).limit(10).all()
    
    # Get team performance rankings
    team_performance = []
    for member in team_members:
        member_daily = next((r for r in daily_reports if r.user_id == member.id), None)
        member_weekly = next((r for r in weekly_reports if r.user_id == member.id), None)
        
        # Calculate individual follow-up call metrics
        member_today_followup_calls = Lead.query.filter(
            Lead.created_by == member.id,
            Lead.followup_date != None,
            Lead.followup_date != '',
            Lead.followup_date != '-',
            func.date(Lead.updated_at) == today  # Only count leads updated today (when follow-up date was set)
        ).count()
        
        member_week_followup_calls = Lead.query.filter(
            Lead.created_by == member.id,
            Lead.followup_date != None,
            Lead.followup_date != '',
            Lead.followup_date != '-',
            Lead.updated_at >= week_start  # Count leads updated this week (when follow-up date was set)
        ).count()
        
        performance = {
            'user': member,
            'daily_leads': member_daily.leads_created or 0 if member_daily else 0,
            'daily_calls': member_daily.calls_made or 0 if member_daily else 0,
            'daily_followup_calls': member_today_followup_calls,
            'weekly_leads': member_weekly.total_leads_created or 0 if member_weekly else 0,
            'weekly_calls': member_weekly.total_calls_made or 0 if member_weekly else 0,
            'weekly_followup_calls': member_week_followup_calls,
            'productivity_score': member_daily.get_productivity_score() if member_daily else 0
        }
        team_performance.append(performance)
    
    # Sort by productivity score
    team_performance.sort(key=lambda x: x['productivity_score'], reverse=True)
    
    return render_template('marketing/dashboard.html',
                         team_members=team_members,
                         team_performance=team_performance,
                         recent_leads=recent_leads,
                         stats={
                             'today': {
                                 'leads': total_leads_today,
                                 'calls': total_calls_today,
                                 'tasks': total_tasks_completed,
                                 'active_time': total_active_time,
                                 'followup_calls': today_followup_calls
                             },
                             'week': {
                                 'leads': total_leads_week,
                                 'calls': total_calls_week,
                                 'tasks': total_tasks_week,
                                 'followup_calls': week_followup_calls
                             },
                             'month': {
                                 'leads': total_leads_month,
                                 'calls': total_calls_month,
                                 'tasks': total_tasks_month,
                                 'followup_calls': month_followup_calls
                             }
                         })

@marketing.route('/team')
@login_required
@marketing_manager_required
def team():
    """Marketing Team Management - View and manage marketing team members."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get all marketing team members with their performance data
    team_members = get_marketing_team_members()
    
    # Get today's performance data
    today = date.today()
    daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == marketing_team.id,
        TeamMemberDailyReport.report_date == today
    ).all()
    
    # Get weekly performance data
    week_start = today - timedelta(days=today.weekday())
    weekly_reports = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == marketing_team.id,
        TeamMemberWeeklyReport.week_start == week_start
    ).all()
    
    # Get monthly performance data
    month_start = date(today.year, today.month, 1)
    monthly_reports = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == marketing_team.id,
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
    
    return render_template('marketing/team.html',
                         team=marketing_team,
                         member_performance=member_performance)

@marketing.route('/reports')
@login_required
@marketing_manager_required
def reports():
    """Marketing Reports - Generate and view marketing team reports."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get report schedules for marketing team
    report_schedules = ReportSchedule.query.filter_by(
        team_id=marketing_team.id,
        is_active=True
    ).all()
    
    # Get recent reports
    today = date.today()
    recent_daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == marketing_team.id,
        TeamMemberDailyReport.report_date >= today - timedelta(days=7)
    ).order_by(TeamMemberDailyReport.report_date.desc()).limit(10).all()
    
    recent_weekly_reports = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == marketing_team.id,
        TeamMemberWeeklyReport.week_start >= today - timedelta(weeks=4)
    ).order_by(TeamMemberWeeklyReport.week_start.desc()).limit(4).all()
    
    recent_monthly_reports = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == marketing_team.id,
        TeamMemberMonthlyReport.month_year >= today.replace(day=1) - timedelta(days=90)
    ).order_by(TeamMemberMonthlyReport.month_year.desc()).limit(3).all()
    
    return render_template('marketing/reports.html',
                         team=marketing_team,
                         report_schedules=report_schedules,
                         recent_daily_reports=recent_daily_reports,
                         recent_weekly_reports=recent_weekly_reports,
                         recent_monthly_reports=recent_monthly_reports)

@marketing.route('/projections')
@login_required
@marketing_manager_required
def projections():
    """Marketing Projections - View and manage marketing projections."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get team member IDs for filtering projections
    team_member_ids = [member.id for member in get_marketing_team_members()]
    
    # Get current month projections for marketing team members
    current_month = date.today().replace(day=1)
    projections = Projection.query.filter(
        Projection.user_id.in_(team_member_ids),
        Projection.month_year == current_month
    ).all()
    
    # Calculate team totals
    total_leads_target = sum(p.target_value for p in projections if p.projection_type == 'leads')
    total_leads_actual = sum(p.actual_value for p in projections if p.projection_type == 'leads')
    total_calls_target = sum(p.target_value for p in projections if p.projection_type == 'calls')
    total_calls_actual = sum(p.actual_value for p in projections if p.projection_type == 'calls')
    total_conversions_target = sum(p.target_value for p in projections if p.projection_type == 'conversions')
    total_conversions_actual = sum(p.actual_value for p in projections if p.projection_type == 'conversions')
    
    return render_template('marketing/projections.html',
                         projections=projections,
                         team_totals={
                             'leads': {'target': total_leads_target, 'actual': total_leads_actual},
                             'calls': {'target': total_calls_target, 'actual': total_calls_actual},
                             'conversions': {'target': total_conversions_target, 'actual': total_conversions_actual}
                         })

@marketing.route('/leads')
@login_required
@marketing_manager_required
def leads():
    """Marketing Leads - View and manage leads created by marketing team."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get filter parameters
    assigned_to_filter = request.args.get('assigned_to', '')
    
    # Build the base query
    base_query = Lead.query
    
    # Apply filters based on user role and permissions
    if current_user.has_permission('manage_marketing_team'):
        # Marketing managers can see all leads assigned to marketing team members
        team_member_ids = [member.id for member in get_marketing_team_members()]
        base_query = base_query.filter(Lead.assigned_to.in_(team_member_ids))
        
        # Apply assigned_to filter if specified
        if assigned_to_filter:
            try:
                assigned_to_id = int(assigned_to_filter)
                base_query = base_query.filter(Lead.assigned_to == assigned_to_id)
            except ValueError:
                pass
    else:
        # Regular team members can only see their assigned leads
        base_query = base_query.filter(Lead.assigned_to == current_user.id)
    
    # Get leads with pagination
    page = request.args.get('page', 1, type=int)
    leads = base_query.order_by(Lead.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get lead statistics based on the same filtering logic
    if current_user.has_permission('manage_marketing_team'):
        team_member_ids = [member.id for member in get_marketing_team_members()]
        stats_base_query = Lead.query.filter(Lead.assigned_to.in_(team_member_ids))
        
        if assigned_to_filter:
            try:
                assigned_to_id = int(assigned_to_filter)
                stats_base_query = stats_base_query.filter(Lead.assigned_to == assigned_to_id)
            except ValueError:
                pass
    else:
        stats_base_query = Lead.query.filter(Lead.assigned_to == current_user.id)
    
    # Get lead statistics
    total_leads = stats_base_query.count()
    new_leads = stats_base_query.filter(Lead.status == 'New').count()
    in_progress_leads = stats_base_query.filter(Lead.status == 'In Progress').count()
    converted_leads = stats_base_query.filter(Lead.status == 'Converted').count()
    
    # Get additional lead statistics for charts
    contacted_leads = stats_base_query.filter(Lead.status == 'Contacted').count()
    qualified_leads = stats_base_query.filter(Lead.status == 'Qualified').count()
    lost_leads = stats_base_query.filter(Lead.status == 'Lost').count()
    
    # Get source statistics
    website_leads = stats_base_query.filter(Lead.source == 'Website').count()
    social_media_leads = stats_base_query.filter(Lead.source == 'Social Media').count()
    referral_leads = stats_base_query.filter(Lead.source == 'Referral').count()
    cold_call_leads = stats_base_query.filter(Lead.source == 'Cold Call').count()
    email_leads = stats_base_query.filter(Lead.source == 'Email').count()
    
    return render_template('marketing/leads.html',
                         leads=leads,
                         stats={
                             'total': total_leads,
                             'status_counts': {
                                 'new': new_leads,
                                 'contacted': contacted_leads,
                                 'qualified': qualified_leads,
                                 'converted': converted_leads,
                                 'lost': lost_leads
                             },
                             'source_counts': {
                                 'website': website_leads,
                                 'social_media': social_media_leads,
                                 'referral': referral_leads,
                                 'cold_call': cold_call_leads,
                                 'email': email_leads
                             }
                         })

@marketing.route('/calls')
@login_required
@marketing_manager_required
def calls():
    """Marketing Calls - View call tracking and analytics."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get team member IDs for filtering calls
    team_member_ids = [member.id for member in get_marketing_team_members()]
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)
    
    # Build query for calls
    calls_query = Call.query.filter(Call.made_by.in_(team_member_ids))
    
    # Apply filters
    if status_filter:
        calls_query = calls_query.filter(Call.status == status_filter)
    if type_filter:
        calls_query = calls_query.filter(Call.call_type == type_filter)
    if date_from:
        calls_query = calls_query.filter(Call.call_date >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        calls_query = calls_query.filter(Call.call_date <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    
    # Order by call date (newest first)
    calls_query = calls_query.order_by(Call.call_date.desc())
    
    # Paginate calls
    calls = calls_query.paginate(
        page=page, 
        per_page=20, 
        error_out=False
    )
    
    # Calculate statistics from actual call data
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get today's calls
    today_calls = Call.query.filter(
        Call.made_by.in_(team_member_ids),
        Call.call_date >= today_start,
        Call.call_date <= today_end
    ).count()
    
    # Get this week's calls
    week_start = today - timedelta(days=today.weekday())
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    week_end_dt = datetime.combine(week_start + timedelta(days=6), datetime.max.time())
    
    week_calls = Call.query.filter(
        Call.made_by.in_(team_member_ids),
        Call.call_date >= week_start_dt,
        Call.call_date <= week_end_dt
    ).count()
    
    # Get total calls
    total_calls = Call.query.filter(Call.made_by.in_(team_member_ids)).count()
    
    # Calculate average duration from completed calls
    completed_calls = Call.query.filter(
        Call.made_by.in_(team_member_ids),
        Call.status == 'completed',
        Call.duration.isnot(None)
    ).all()
    
    if completed_calls:
        avg_duration = sum(call.duration for call in completed_calls) / len(completed_calls)
    else:
        avg_duration = 0.0
    
    # Calculate status counts
    status_counts = {}
    for status in ['completed', 'missed', 'no_answer', 'voicemail', 'busy']:
        count = Call.query.filter(
            Call.made_by.in_(team_member_ids),
            Call.status == status
        ).count()
        status_counts[status] = count
    
    # Calculate type counts
    type_counts = {}
    for call_type in ['outbound', 'inbound', 'follow_up', 'cold_call']:
        count = Call.query.filter(
            Call.made_by.in_(team_member_ids),
            Call.call_type == call_type
        ).count()
        type_counts[call_type] = count
    
    return render_template('marketing/calls.html',
                         calls=calls,
                         stats={
                             'total_calls': total_calls,
                             'today_calls': today_calls,
                             'week_calls': week_calls,
                             'avg_duration': avg_duration,
                             'status_counts': status_counts,
                             'type_counts': type_counts
                         })

@marketing.route('/team-chat')
@login_required
@marketing_manager_required
def team_chat():
    """Marketing Team Chat - Team communication for marketing team."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get marketing team chat groups
    chat_groups = ChatGroup.query.filter_by(
        team_id=marketing_team.id,
        is_archived=False
    ).all()
    
    return render_template('marketing/team-chat.html',
                         team=marketing_team,
                         chat_groups=chat_groups)

@marketing.route('/team-reports')
@login_required
@marketing_manager_required
def team_reports():
    """Marketing Team Reports - Overview of all team reports."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get report schedules
    report_schedules = ReportSchedule.query.filter_by(
        team_id=marketing_team.id,
        is_active=True
    ).all()
    
    # Get recent reports summary
    today = date.today()
    recent_daily_count = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == marketing_team.id,
        TeamMemberDailyReport.report_date >= today - timedelta(days=7)
    ).count()
    
    recent_weekly_count = TeamMemberWeeklyReport.query.filter(
        TeamMemberWeeklyReport.team_id == marketing_team.id,
        TeamMemberWeeklyReport.week_start >= today - timedelta(weeks=4)
    ).count()
    
    recent_monthly_count = TeamMemberMonthlyReport.query.filter(
        TeamMemberMonthlyReport.team_id == marketing_team.id,
        TeamMemberMonthlyReport.month_year >= today.replace(day=1) - timedelta(days=90)
    ).count()
    
    return render_template('marketing/team-reports.html',
                         team=marketing_team,
                         report_schedules=report_schedules,
                         recent_counts={
                             'daily': recent_daily_count,
                             'weekly': recent_weekly_count,
                             'monthly': recent_monthly_count
                         })

@marketing.route('/team-reports/daily')
@login_required
@marketing_manager_required
def team_reports_daily():
    """Marketing Daily Team Reports - View daily reports for marketing team."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get date filter
    report_date = request.args.get('date', date.today().isoformat())
    try:
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    except ValueError:
        report_date = date.today()
    
    # Get daily reports for the specified date
    daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.team_id == marketing_team.id,
        TeamMemberDailyReport.report_date == report_date
    ).all()
    
    # Get team members who should have reports
    team_members = get_marketing_team_members()
    
    # Match reports with team members
    member_reports = []
    for member in team_members:
        report = next((r for r in daily_reports if r.user_id == member.id), None)
        member_reports.append({
            'user': member,
            'report': report,
            'has_report': report is not None
        })
    
    return render_template('marketing/team-reports-daily.html',
                         team=marketing_team,
                         member_reports=member_reports,
                         report_date=report_date)

@marketing.route('/team-reports/weekly')
@login_required
@marketing_manager_required
def team_reports_weekly():
    """Marketing Weekly Team Reports - View weekly reports for marketing team."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
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
        TeamMemberWeeklyReport.team_id == marketing_team.id,
        TeamMemberWeeklyReport.week_start == week_start
    ).all()
    
    # Get team members who should have reports
    team_members = get_marketing_team_members()
    
    # Match reports with team members
    member_reports = []
    for member in team_members:
        report = next((r for r in weekly_reports if r.user_id == member.id), None)
        member_reports.append({
            'user': member,
            'report': report,
            'has_report': report is not None
        })
    
    return render_template('marketing/team-reports-weekly.html',
                         team=marketing_team,
                         member_reports=member_reports,
                         week_start=week_start)

@marketing.route('/team-reports/monthly')
@login_required
@marketing_manager_required
def team_reports_monthly():
    """Marketing Monthly Team Reports - View monthly reports for marketing team."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
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
        TeamMemberMonthlyReport.team_id == marketing_team.id,
        TeamMemberMonthlyReport.month_year == month_year
    ).all()
    
    # Get team members who should have reports
    team_members = get_marketing_team_members()
    
    # Match reports with team members
    member_reports = []
    for member in team_members:
        report = next((r for r in monthly_reports if r.user_id == member.id), None)
        member_reports.append({
            'user': member,
            'report': report,
            'has_report': report is not None
        })
    
    return render_template('marketing/team-reports-monthly.html',
                         team=marketing_team,
                         member_reports=member_reports,
                         month_year=month_year)

@marketing.route('/team-reports/member/<int:member_id>')
@login_required
def team_member_report(member_id):
    """Marketing Individual Team Member Report - View detailed report for a specific team member."""
    
    # Check if user has permission to view team member reports
    if not (current_user.has_permission('manage_marketing_team') or 
            current_user.has_permission('admin') or 
            current_user.has_permission('manage_hr')):
        flash('Access denied. Insufficient permissions to view team member reports.', 'error')
        return redirect(url_for('auth.login'))
    
    # Validate that the member belongs to the marketing team or is a Caller
    if not validate_marketing_member_access(member_id):
        return redirect(url_for('marketing.team_reports'))
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get the team member
    member = User.query.get(member_id)
    if not member:
        flash('Team member not found.', 'error')
        return redirect(url_for('marketing.team_reports'))
    
    # Get date filters
    report_date = request.args.get('date', date.today().isoformat())
    try:
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    except ValueError:
        report_date = date.today()
    
    # Get reports for the member
    # For Caller role users, they might not have team reports, so we'll handle this gracefully
    daily_report = None
    weekly_report = None
    monthly_report = None
    
    if marketing_team:
        daily_report = TeamMemberDailyReport.query.filter_by(
            user_id=member_id,
            team_id=marketing_team.id,
            report_date=report_date
        ).first()
        
        week_start = report_date - timedelta(days=report_date.weekday())
        weekly_report = TeamMemberWeeklyReport.query.filter_by(
            user_id=member_id,
            team_id=marketing_team.id,
            week_start=week_start
        ).first()
        
        month_start = report_date.replace(day=1)
        monthly_report = TeamMemberMonthlyReport.query.filter_by(
            user_id=member_id,
            team_id=marketing_team.id,
            month_year=month_start
        ).first()
    
    # Enhanced data collection for detailed reporting
    from app.models import Lead, Call, FollowUpHistory, Contact, UserActivity
    from sqlalchemy import func
    
    # Date ranges
    today_start = datetime.combine(report_date, datetime.min.time())
    today_end = datetime.combine(report_date, datetime.max.time())
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    week_end_dt = datetime.combine(week_start + timedelta(days=6), datetime.max.time())
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    month_end_dt = datetime.combine(month_start.replace(day=28) + timedelta(days=4), datetime.max.time())
    
    # 1. Follow-up calls (using Lead model with followup_date set)
    today_followups = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.followup_date != None,
        Lead.followup_date != '',
        Lead.followup_date != '-',
        func.date(Lead.updated_at) == report_date  # Only count leads updated today (when follow-up date was set)
    ).count()
    
    week_followups = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.followup_date != None,
        Lead.followup_date != '',
        Lead.followup_date != '-',
        Lead.updated_at >= week_start_dt,
        Lead.updated_at <= week_end_dt
    ).count()
    
    month_followups = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.followup_date != None,
        Lead.followup_date != '',
        Lead.followup_date != '-',
        Lead.updated_at >= month_start_dt,
        Lead.updated_at <= month_end_dt
    ).count()
    
    # 2. Lead collections populations
    today_leads_created = Lead.query.filter(
        Lead.created_by == member_id,
        func.date(Lead.created_at) == report_date
    ).count()
    
    week_leads_created = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.created_at >= week_start_dt,
        Lead.created_at <= week_end_dt
    ).count()
    
    month_leads_created = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.created_at >= month_start_dt,
        Lead.created_at <= month_end_dt
    ).count()
    
    # 3. Converted clients
    today_converted = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.status == 'Converted',
        func.date(Lead.updated_at) == report_date
    ).count()
    
    week_converted = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.status == 'Converted',
        Lead.updated_at >= week_start_dt,
        Lead.updated_at <= week_end_dt
    ).count()
    
    month_converted = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.status == 'Converted',
        Lead.updated_at >= month_start_dt,
        Lead.updated_at <= month_end_dt
    ).count()
    
    # 4. Caller role users projections status
    # Get all leads by this member with their current status
    member_leads = Lead.query.filter_by(created_by=member_id).all()
    lead_status_distribution = {}
    for lead in member_leads:
        status = lead.status or 'New'
        lead_status_distribution[status] = lead_status_distribution.get(status, 0) + 1
    
    # 5. Existing clients (leads with status 'Converted' or 'Interested')
    existing_clients = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.status.in_(['Converted', 'Interested', 'Scheduled for Meeting'])
    ).count()
    
    # 6. Call statistics
    today_calls = Call.query.filter(
        Call.made_by == member_id,
        Call.call_date >= today_start,
        Call.call_date <= today_end
    ).count()
    
    week_calls = Call.query.filter(
        Call.made_by == member_id,
        Call.call_date >= week_start_dt,
        Call.call_date <= week_end_dt
    ).count()
    
    month_calls = Call.query.filter(
        Call.made_by == member_id,
        Call.call_date >= month_start_dt,
        Call.call_date <= month_end_dt
    ).count()
    
    # 7. Recent activity
    recent_activities = UserActivity.query.filter_by(
        user_id=member_id
    ).order_by(UserActivity.created_at.desc()).limit(10).all()
    
    # 8. Recent leads
    recent_leads = Lead.query.filter_by(
        created_by=member_id
    ).order_by(Lead.created_at.desc()).limit(5).all()
    
    # 9. Recent calls
    recent_calls = Call.query.filter_by(
        made_by=member_id
    ).order_by(Call.call_date.desc()).limit(5).all()
    
    # 10. Performance metrics
    total_leads = Lead.query.filter_by(created_by=member_id).count()
    total_calls = Call.query.filter_by(made_by=member_id).count()
    conversion_rate = (existing_clients / total_leads * 100) if total_leads > 0 else 0
    
    return render_template('marketing/team-member-report.html',
                         team=marketing_team,
                         member=member,
                         daily_report=daily_report,
                         weekly_report=weekly_report,
                         monthly_report=monthly_report,
                         report_date=report_date,
                         # Enhanced data
                         today_followups=today_followups,
                         week_followups=week_followups,
                         month_followups=month_followups,
                         today_leads_created=today_leads_created,
                         week_leads_created=week_leads_created,
                         month_leads_created=month_leads_created,
                         today_converted=today_converted,
                         week_converted=week_converted,
                         month_converted=month_converted,
                         lead_status_distribution=lead_status_distribution,
                         existing_clients=existing_clients,
                         today_calls=today_calls,
                         week_calls=week_calls,
                         month_calls=month_calls,
                         recent_activities=recent_activities,
                         recent_leads=recent_leads,
                         recent_calls=recent_calls,
                         total_leads=total_leads,
                         total_calls=total_calls,
                         conversion_rate=conversion_rate) 

@marketing.route('/team/add-member', methods=['GET', 'POST'])
@login_required
@marketing_manager_required
def add_team_member():
    """Add a new member to the marketing team."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int)
        role = request.form.get('role', 'member')
        
        if not user_id:
            flash('Please select a user to add to the team.', 'error')
            return redirect(url_for('marketing.add_team_member'))
        
        # Check if user is already in the team
        existing_membership = UserTeam.query.filter_by(
            user_id=user_id,
            team_id=marketing_team.id
        ).first()
        
        if existing_membership:
            flash('User is already a member of the marketing team.', 'error')
            return redirect(url_for('marketing.add_team_member'))
        
        # Add user to team
        new_membership = UserTeam(
            user_id=user_id,
            team_id=marketing_team.id,
            role=role,
            is_active=True,
            joined_date=date.today()
        )
        
        db.session.add(new_membership)
        db.session.commit()
        
        flash('Team member added successfully!', 'success')
        return redirect(url_for('marketing.team'))
    
    # Get available users (not already in marketing team)
    existing_member_ids = [ut.user_id for ut in UserTeam.query.filter_by(
        team_id=marketing_team.id,
        is_active=True
    ).all()]
    
    available_users = User.query.filter(
        ~User.id.in_(existing_member_ids)
    ).all()
    
    return render_template('marketing/add-team-member.html',
                         team=marketing_team,
                         available_users=available_users)

@marketing.route('/team/remove-member/<int:member_id>', methods=['POST'])
@login_required
@marketing_manager_required
def remove_team_member(member_id):
    """Remove a member from the marketing team."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Validate that the member belongs to the marketing team
    if not validate_marketing_member_access(member_id):
        return redirect(url_for('marketing.team'))
    
    # Deactivate team membership
    membership = UserTeam.query.filter_by(
        user_id=member_id,
        team_id=marketing_team.id
    ).first()
    
    if membership:
        membership.is_active = False
        membership.left_date = date.today()
        db.session.commit()
        flash('Team member removed successfully!', 'success')
    else:
        flash('Team member not found.', 'error')
    
    return redirect(url_for('marketing.team'))

@marketing.route('/team/assign-lead/<int:lead_id>', methods=['POST'])
@login_required
@marketing_manager_required
def assign_lead_to_member(lead_id):
    """Assign a lead to a specific team member."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    member_id = request.form.get('member_id', type=int)
    
    if not member_id:
        flash('Please select a team member to assign the lead to.', 'error')
        return redirect(url_for('marketing.leads'))
    
    # Validate that the member belongs to the marketing team
    if not validate_marketing_member_access(member_id):
        return redirect(url_for('marketing.leads'))
    
    # Get the lead
    lead = Lead.query.get(lead_id)
    if not lead:
        flash('Lead not found.', 'error')
        return redirect(url_for('marketing.leads'))
    
    # Assign lead to member
    lead.assigned_to = member_id
    lead.assigned_date = datetime.now(timezone.utc)
    db.session.commit()
    
    flash('Lead assigned successfully!', 'success')
    return redirect(url_for('marketing.leads'))

@marketing.route('/team/performance/<int:member_id>')
@login_required
@marketing_manager_required
def team_member_performance(member_id):
    """View detailed performance metrics for a specific team member."""
    
    # Validate that the member belongs to the marketing team
    if not validate_marketing_member_access(member_id):
        return redirect(url_for('marketing.team'))
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    # Get the team member
    member = User.query.get(member_id)
    if not member:
        flash('Team member not found.', 'error')
        return redirect(url_for('marketing.team'))
    
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
    leads_created = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.created_at >= start_date,
        Lead.created_at <= end_date
    ).count()
    
    calls_made = 0  # This would come from a calls table
    conversions = Lead.query.filter(
        Lead.created_by == member_id,
        Lead.status == 'converted',
        Lead.created_at >= start_date,
        Lead.created_at <= end_date
    ).count()
    
    # Get daily reports for the period
    daily_reports = TeamMemberDailyReport.query.filter(
        TeamMemberDailyReport.user_id == member_id,
        TeamMemberDailyReport.team_id == marketing_team.id,
        TeamMemberDailyReport.report_date >= start_date,
        TeamMemberDailyReport.report_date <= end_date
    ).order_by(TeamMemberDailyReport.report_date).all()
    
    # Calculate productivity trends
    productivity_data = []
    for report in daily_reports:
        productivity_data.append({
            'date': report.report_date,
            'productivity_score': report.get_productivity_score(),
            'leads_created': report.leads_created,
            'calls_made': report.calls_made
        })
    
    return render_template('marketing/team-member-performance.html',
                         team=marketing_team,
                         member=member,
                         start_date=start_date,
                         end_date=end_date,
                         leads_created=leads_created,
                         calls_made=calls_made,
                         conversions=conversions,
                         productivity_data=productivity_data)

@marketing.route('/team/workload-balance')
@login_required
@marketing_manager_required
def workload_balance():
    """View and manage workload distribution across team members."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    team_members = get_marketing_team_members()
    
    # Get workload data for each member
    workload_data = []
    for member in team_members:
        # Count active leads assigned to member
        active_leads = Lead.query.filter(
            Lead.assigned_to == member.id,
            Lead.status.in_(['new', 'contacted', 'qualified'])
        ).count()
        
        # Count pending calls
        pending_calls = 0  # This would come from a calls table
        
        # Get today's performance
        today_report = TeamMemberDailyReport.query.filter_by(
            user_id=member.id,
            team_id=marketing_team.id,
            report_date=date.today()
        ).first()
        
        workload_data.append({
            'member': member,
            'active_leads': active_leads,
            'pending_calls': pending_calls,
            'today_leads': today_report.leads_created if today_report else 0,
            'today_calls': today_report.calls_made if today_report else 0,
            'productivity_score': today_report.get_productivity_score() if today_report else 0
        })
    
    return render_template('marketing/workload-balance.html',
                         team=marketing_team,
                         workload_data=workload_data)

@marketing.route('/team/notifications')
@login_required
@marketing_manager_required
def team_notifications():
    """Manage team notifications and announcements."""
    
    marketing_team = get_marketing_team()
    if not marketing_team:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        message = request.form.get('message')
        notification_type = request.form.get('type', 'announcement')
        
        if message:
            # Create notification (this would be stored in a notifications table)
            flash('Notification sent to team!', 'success')
        else:
            flash('Please enter a message.', 'error')
    
    return render_template('marketing/team-notifications.html',
                         team=marketing_team) 

@marketing.route('/api/team-reports/daily')
@login_required
@marketing_manager_required
def api_team_reports_daily():
    """API endpoint to get daily team reports for marketing team."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
        # Get date filter
        report_date = request.args.get('date', date.today().isoformat())
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get daily reports for the team
        daily_reports = TeamMemberDailyReport.query.filter_by(
            team_id=marketing_team.id,
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
            'team_id': marketing_team.id,
            'team_name': marketing_team.name,
            'report_date': report_date.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@marketing.route('/api/team-reports/daily/<int:member_id>')
@login_required
@marketing_manager_required
def api_team_member_daily_report(member_id):
    """API endpoint to get daily report for a specific marketing team member."""
    try:
        # Validate member access
        if not validate_marketing_member_access(member_id):
            return jsonify({'error': 'Access denied to this team member'}), 403
        
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
        # Get date filter
        report_date = request.args.get('date', date.today().isoformat())
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get the specific member's daily report
        report = TeamMemberDailyReport.query.filter_by(
            user_id=member_id,
            team_id=marketing_team.id,
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

@marketing.route('/api/team-reports/daily/generate', methods=['POST'])
@login_required
@marketing_manager_required
def api_generate_daily_reports():
    """API endpoint to generate daily reports for marketing team."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
        # Get date from request
        report_date = request.json.get('date', date.today().isoformat())
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
        
        # Get team members
        team_members = get_marketing_team_members()
        
        generated_reports = []
        
        for member in team_members:
            # Check if report already exists
            existing_report = TeamMemberDailyReport.query.filter_by(
                user_id=member.id,
                team_id=marketing_team.id,
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
                team_id=marketing_team.id,
                report_date=report_date,
                daily_goal=10,  # Default goal
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

@marketing.route('/api/team-reports/weekly')
@login_required
@marketing_manager_required
def api_team_reports_weekly():
    """API endpoint to get weekly team reports for marketing team."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
            team_id=marketing_team.id,
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
            'team_id': marketing_team.id,
            'team_name': marketing_team.name,
            'week_start': week_start.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@marketing.route('/api/team-reports/weekly/<int:member_id>')
@login_required
@marketing_manager_required
def api_team_member_weekly_report(member_id):
    """API endpoint to get weekly report for a specific marketing team member."""
    try:
        # Validate member access
        if not validate_marketing_member_access(member_id):
            return jsonify({'error': 'Access denied to this team member'}), 403
        
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
            team_id=marketing_team.id,
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

@marketing.route('/api/team-reports/weekly/generate', methods=['POST'])
@login_required
@marketing_manager_required
def api_generate_weekly_reports():
    """API endpoint to generate weekly reports for marketing team."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
        team_members = get_marketing_team_members()
        
        generated_reports = []
        
        for member in team_members:
            # Check if report already exists
            existing_report = TeamMemberWeeklyReport.query.filter_by(
                user_id=member.id,
                team_id=marketing_team.id,
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
                team_id=marketing_team.id,
                week_start=week_start,
                weekly_goal=50,  # Default goal
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

@marketing.route('/api/team-reports/monthly')
@login_required
@marketing_manager_required
def api_team_reports_monthly():
    """API endpoint to get monthly team reports for marketing team."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
            team_id=marketing_team.id,
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
            'team_id': marketing_team.id,
            'team_name': marketing_team.name,
            'month_year': month_year.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@marketing.route('/api/team-reports/monthly/<int:member_id>')
@login_required
@marketing_manager_required
def api_team_member_monthly_report(member_id):
    """API endpoint to get monthly report for a specific marketing team member."""
    try:
        # Validate member access
        if not validate_marketing_member_access(member_id):
            return jsonify({'error': 'Access denied to this team member'}), 403
        
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
            team_id=marketing_team.id,
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

@marketing.route('/api/team-reports/monthly/generate', methods=['POST'])
@login_required
@marketing_manager_required
def api_generate_monthly_reports():
    """API endpoint to generate monthly reports for marketing team."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
        team_members = get_marketing_team_members()
        
        generated_reports = []
        
        for member in team_members:
            # Check if report already exists
            existing_report = TeamMemberMonthlyReport.query.filter_by(
                user_id=member.id,
                team_id=marketing_team.id,
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
                team_id=marketing_team.id,
                month_year=month_year,
                monthly_goal=200,  # Default goal
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

@marketing.route('/api/team-reports/export/pdf')
@login_required
@marketing_manager_required
def api_export_reports_pdf():
    """API endpoint to export team reports as PDF."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
                    team_id=marketing_team.id,
                    report_date=report_date
                ).all()
            else:
                reports = TeamMemberDailyReport.query.filter_by(
                    team_id=marketing_team.id,
                    report_date=report_date
                ).all()
        elif report_type == 'weekly':
            week_start = report_date - timedelta(days=report_date.weekday())
            if member_id:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    user_id=member_id,
                    team_id=marketing_team.id,
                    week_start=week_start
                ).all()
            else:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    team_id=marketing_team.id,
                    week_start=week_start
                ).all()
        elif report_type == 'monthly':
            month_start = report_date.replace(day=1)
            if member_id:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    user_id=member_id,
                    team_id=marketing_team.id,
                    month_year=month_start
                ).all()
            else:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    team_id=marketing_team.id,
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
            'team_name': marketing_team.name,
            'report_type': report_type,
            'report_date': report_date.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@marketing.route('/api/team-reports/export/excel')
@login_required
@marketing_manager_required
def api_export_reports_excel():
    """API endpoint to export team reports as Excel."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
                    team_id=marketing_team.id,
                    report_date=report_date
                ).all()
            else:
                reports = TeamMemberDailyReport.query.filter_by(
                    team_id=marketing_team.id,
                    report_date=report_date
                ).all()
        elif report_type == 'weekly':
            week_start = report_date - timedelta(days=report_date.weekday())
            if member_id:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    user_id=member_id,
                    team_id=marketing_team.id,
                    week_start=week_start
                ).all()
            else:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    team_id=marketing_team.id,
                    week_start=week_start
                ).all()
        elif report_type == 'monthly':
            month_start = report_date.replace(day=1)
            if member_id:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    user_id=member_id,
                    team_id=marketing_team.id,
                    month_year=month_start
                ).all()
            else:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    team_id=marketing_team.id,
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
            'team_name': marketing_team.name,
            'report_type': report_type,
            'report_date': report_date.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@marketing.route('/api/team-reports/export/csv')
@login_required
@marketing_manager_required
def api_export_reports_csv():
    """API endpoint to export team reports as CSV."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
                    team_id=marketing_team.id,
                    report_date=report_date
                ).all()
            else:
                reports = TeamMemberDailyReport.query.filter_by(
                    team_id=marketing_team.id,
                    report_date=report_date
                ).all()
        elif report_type == 'weekly':
            week_start = report_date - timedelta(days=report_date.weekday())
            if member_id:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    user_id=member_id,
                    team_id=marketing_team.id,
                    week_start=week_start
                ).all()
            else:
                reports = TeamMemberWeeklyReport.query.filter_by(
                    team_id=marketing_team.id,
                    week_start=week_start
                ).all()
        elif report_type == 'monthly':
            month_start = report_date.replace(day=1)
            if member_id:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    user_id=member_id,
                    team_id=marketing_team.id,
                    month_year=month_start
                ).all()
            else:
                reports = TeamMemberMonthlyReport.query.filter_by(
                    team_id=marketing_team.id,
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
            'team_name': marketing_team.name,
            'report_type': report_type,
            'report_date': report_date.isoformat(),
            'reports': reports_data,
            'total_reports': len(reports_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@marketing.route('/api/team-reports/schedule', methods=['POST'])
@login_required
@marketing_manager_required
def api_schedule_reports():
    """API endpoint to schedule automated reports."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
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
            team_id=marketing_team.id,
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

@marketing.route('/api/team-reports/schedule', methods=['GET'])
@login_required
@marketing_manager_required
def api_get_report_schedules():
    """API endpoint to get report schedules."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
        # Get all schedules for the team
        schedules = ReportSchedule.query.filter_by(
            team_id=marketing_team.id,
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

@marketing.route('/api/team-reports/schedule/<int:schedule_id>', methods=['PUT'])
@login_required
@marketing_manager_required
def api_update_report_schedule(schedule_id):
    """API endpoint to update a report schedule."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
        # Get the schedule
        schedule = ReportSchedule.query.filter_by(
            id=schedule_id,
            team_id=marketing_team.id
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

@marketing.route('/api/team-reports/schedule/<int:schedule_id>', methods=['DELETE'])
@login_required
@marketing_manager_required
def api_delete_report_schedule(schedule_id):
    """API endpoint to delete a report schedule."""
    try:
        marketing_team = get_marketing_team()
        if not marketing_team:
            return jsonify({'error': 'Marketing team not found'}), 404
        
        # Get the schedule
        schedule = ReportSchedule.query.filter_by(
            id=schedule_id,
            team_id=marketing_team.id
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