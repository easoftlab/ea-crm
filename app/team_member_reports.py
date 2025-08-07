#!/usr/bin/env python3
"""
Team Member Reports Management
Centralized system for updating team member daily, weekly, and monthly reports
"""

from flask import current_app
from datetime import datetime, timezone, date, timedelta
from .models import db, TeamMemberDailyReport, TeamMemberWeeklyReport, TeamMemberMonthlyReport, UserTeam, User
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

class TeamMemberReportManager:
    """Centralized team member report management system."""
    
    @staticmethod
    def update_team_member_reports(user_id, action_type, **kwargs):
        """
        Centralized method to update team member reports for any user action.
        
        Args:
            user_id (int): ID of the user performing the action
            action_type (str): Type of action ('lead_created', 'call_made', 'task_completed', etc.)
            **kwargs: Additional data for the action
        """
        try:
            today = date.today()
            
            # Ensure user has team assignment
            if not TeamMemberReportManager.ensure_user_team_assignment(user_id):
                logger.warning(f"User {user_id} not assigned to any team")
                return False
            
            # Get user's team
            user_team = UserTeam.query.filter_by(user_id=user_id, is_active=True).first()
            if not user_team:
                logger.error(f"User {user_id} has no active team assignment")
                return False
            
            # Update daily report
            daily_updated = TeamMemberReportManager._update_daily_report(
                user_id, user_team.team_id, action_type, today, **kwargs
            )
            
            # Update weekly report
            week_start = today - timedelta(days=today.weekday())
            weekly_updated = TeamMemberReportManager._update_weekly_report(
                user_id, user_team.team_id, action_type, week_start, **kwargs
            )
            
            # Update monthly report
            month_start = date(today.year, today.month, 1)
            monthly_updated = TeamMemberReportManager._update_monthly_report(
                user_id, user_team.team_id, action_type, month_start, **kwargs
            )
            
            if daily_updated or weekly_updated or monthly_updated:
                db.session.commit()
                logger.info(f"Updated team member reports for user {user_id}, action: {action_type}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating team member reports: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def ensure_user_team_assignment(user_id):
        """Ensure user is assigned to appropriate team based on their role."""
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Check if user already has team assignment
            existing_team = UserTeam.query.filter_by(user_id=user_id, is_active=True).first()
            if existing_team:
                return True
            
            # Auto-assign based on role
            team_name = None
            if user.role.name in ['Caller', 'User', 'Manager']:
                team_name = 'Marketing Team'
            elif user.role.name == 'Production':
                team_name = 'Production Team'
            
            if team_name:
                from .models import Team
                team = Team.query.filter_by(name=team_name).first()
                if team:
                    new_assignment = UserTeam(
                        user_id=user_id,
                        team_id=team.id,
                        role='member',
                        is_active=True
                    )
                    db.session.add(new_assignment)
                    db.session.commit()
                    logger.info(f"Auto-assigned user {user_id} to {team_name}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error ensuring team assignment: {str(e)}")
            return False
    
    @staticmethod
    def _update_daily_report(user_id, team_id, action_type, report_date, **kwargs):
        """Update daily team member report."""
        try:
            daily_report = TeamMemberDailyReport.query.filter_by(
                user_id=user_id,
                team_id=team_id,
                report_date=report_date
            ).first()

            if not daily_report:
                daily_report = TeamMemberDailyReport(
                    user_id=user_id,
                    team_id=team_id,
                    report_date=report_date,
                    daily_goal=20,  # Default daily goal
                    goal_achievement=0.0,
                    leads_created=0,
                    leads_updated=0,
                    calls_made=0,
                    tasks_completed=0,
                    followups_added=0,
                    conversions=0,
                    messages_sent=0,
                    total_active_time=0
                )
                db.session.add(daily_report)

            # Update based on action type
            updated = False

            if action_type == 'lead_created':
                daily_report.leads_created = (daily_report.leads_created or 0) + 1
                updated = True
            elif action_type == 'lead_updated':
                daily_report.leads_updated = (daily_report.leads_updated or 0) + 1
                updated = True
            elif action_type == 'call_made':
                daily_report.calls_made = (daily_report.calls_made or 0) + 1
                duration = kwargs.get('duration', 5)  # Default 5 minutes
                daily_report.total_active_time = (daily_report.total_active_time or 0) + duration
                updated = True
            elif action_type == 'task_completed':
                daily_report.tasks_completed = (daily_report.tasks_completed or 0) + 1
                updated = True
            elif action_type == 'followup_added':
                daily_report.followups_added = (daily_report.followups_added or 0) + 1
                updated = True
            elif action_type == 'conversion':
                daily_report.conversions = (daily_report.conversions or 0) + 1
                updated = True
            elif action_type == 'message_sent':
                daily_report.messages_sent = (daily_report.messages_sent or 0) + 1
                updated = True

            # Update goal achievement
            if updated and daily_report.daily_goal > 0:
                daily_report.goal_achievement = min(100,
                    ((daily_report.leads_created or 0) + (daily_report.tasks_completed or 0)) / daily_report.daily_goal * 100
                )
            return updated

        except Exception as e:
            logger.error(f"Error updating daily report: {str(e)}")
            return False

    @staticmethod
    def _update_weekly_report(user_id, team_id, action_type, week_start, **kwargs):
        """Update weekly team member report."""
        try:
            weekly_report = TeamMemberWeeklyReport.query.filter_by(
                user_id=user_id,
                team_id=team_id,
                week_start=week_start
            ).first()

            if not weekly_report:
                weekly_report = TeamMemberWeeklyReport(
                    user_id=user_id,
                    team_id=team_id,
                    week_start=week_start,
                    weekly_goal=100,  # Default weekly goal
                    goal_achievement=0.0,
                    total_leads_created=0,
                    total_leads_updated=0,
                    total_calls_made=0,
                    total_tasks_completed=0,
                    total_followups_added=0,
                    total_conversions=0,
                    total_messages_sent=0,
                    total_active_time=0
                )
                db.session.add(weekly_report)

            # Update based on action type
            updated = False

            if action_type == 'lead_created':
                weekly_report.total_leads_created = (weekly_report.total_leads_created or 0) + 1
                updated = True
            elif action_type == 'lead_updated':
                weekly_report.total_leads_updated = (weekly_report.total_leads_updated or 0) + 1
                updated = True
            elif action_type == 'call_made':
                weekly_report.total_calls_made = (weekly_report.total_calls_made or 0) + 1
                duration = kwargs.get('duration', 5)
                weekly_report.total_active_time = (weekly_report.total_active_time or 0) + duration
                updated = True
            elif action_type == 'task_completed':
                weekly_report.total_tasks_completed = (weekly_report.total_tasks_completed or 0) + 1
                updated = True
            elif action_type == 'followup_added':
                weekly_report.total_followups_added = (weekly_report.total_followups_added or 0) + 1
                updated = True
            elif action_type == 'conversion':
                weekly_report.total_conversions = (weekly_report.total_conversions or 0) + 1
                updated = True
            elif action_type == 'message_sent':
                weekly_report.total_messages_sent = (weekly_report.total_messages_sent or 0) + 1
                updated = True

            # Update goal achievement
            if updated and weekly_report.weekly_goal > 0:
                weekly_report.goal_achievement = min(100,
                    ((weekly_report.total_leads_created or 0) + (weekly_report.total_tasks_completed or 0)) / weekly_report.weekly_goal * 100
                )
            return updated

        except Exception as e:
            logger.error(f"Error updating weekly report: {str(e)}")
            return False

    @staticmethod
    def _update_monthly_report(user_id, team_id, action_type, month_start, **kwargs):
        """Update monthly team member report."""
        try:
            monthly_report = TeamMemberMonthlyReport.query.filter_by(
                user_id=user_id,
                team_id=team_id,
                month_year=month_start
            ).first()

            if not monthly_report:
                monthly_report = TeamMemberMonthlyReport(
                    user_id=user_id,
                    team_id=team_id,
                    month_year=month_start,
                    monthly_goal=400,  # Default monthly goal
                    goal_achievement=0.0,
                    total_leads_created=0,
                    total_leads_updated=0,
                    total_calls_made=0,
                    total_tasks_completed=0,
                    total_followups_added=0,
                    total_conversions=0,
                    total_messages_sent=0,
                    total_active_time=0
                )
                db.session.add(monthly_report)

            # Update based on action type
            updated = False

            if action_type == 'lead_created':
                monthly_report.total_leads_created = (monthly_report.total_leads_created or 0) + 1
                updated = True
            elif action_type == 'lead_updated':
                monthly_report.total_leads_updated = (monthly_report.total_leads_updated or 0) + 1
                updated = True
            elif action_type == 'call_made':
                monthly_report.total_calls_made = (monthly_report.total_calls_made or 0) + 1
                duration = kwargs.get('duration', 5)
                monthly_report.total_active_time = (monthly_report.total_active_time or 0) + duration
                updated = True
            elif action_type == 'task_completed':
                monthly_report.total_tasks_completed = (monthly_report.total_tasks_completed or 0) + 1
                updated = True
            elif action_type == 'followup_added':
                monthly_report.total_followups_added = (monthly_report.total_followups_added or 0) + 1
                updated = True
            elif action_type == 'conversion':
                monthly_report.total_conversions = (monthly_report.total_conversions or 0) + 1
                updated = True
            elif action_type == 'message_sent':
                monthly_report.total_messages_sent = (monthly_report.total_messages_sent or 0) + 1
                updated = True

            # Update goal achievement
            if updated and monthly_report.monthly_goal > 0:
                monthly_report.goal_achievement = min(100,
                    ((monthly_report.total_leads_created or 0) + (monthly_report.total_tasks_completed or 0)) / monthly_report.monthly_goal * 100
                )
            return updated

        except Exception as e:
            logger.error(f"Error updating monthly report: {str(e)}")
            return False

# Convenience functions for easy integration
def update_team_member_reports(user_id, action_type, **kwargs):
    """Convenience function to update team member reports."""
    return TeamMemberReportManager.update_team_member_reports(user_id, action_type, **kwargs)

def ensure_user_team_assignment(user_id):
    """Convenience function to ensure user team assignment."""
    return TeamMemberReportManager.ensure_user_team_assignment(user_id) 