#!/usr/bin/env python3
"""
Comprehensive Active Time Tracking System
Provides active time tracking for all user roles with detailed analytics.
"""

from flask import current_app, request
from datetime import datetime, timedelta, date
from .models import db, User, UserActivity, UserDailyStats, TeamMemberDailyReport
from sqlalchemy import func
import logging
import time

# Set up logging
logger = logging.getLogger(__name__)

class ActiveTimeTracker:
    """Enhanced active time tracking system for all user roles."""
    
    # Activity types that count as active time
    ACTIVE_ACTIVITIES = {
        'lead_created': 5,  # 5 minutes
        'lead_updated': 3,  # 3 minutes
        'call_made': 10,    # 10 minutes
        'call_successful': 15,  # 15 minutes
        'call_failed': 2,   # 2 minutes
        'task_created': 5,  # 5 minutes
        'task_completed': 10,  # 10 minutes
        'followup_added': 5,  # 5 minutes
        'production_task_started': 15,  # 15 minutes
        'production_task_completed': 20,  # 20 minutes
        'file_uploaded': 8,  # 8 minutes
        'code_committed': 12,  # 12 minutes
        'report_generated': 10,  # 10 minutes
        'data_exported': 8,  # 8 minutes
        'user_login': 1,  # 1 minute
        'user_logout': 1   # 1 minute
    }
    
    # Minimum active time thresholds by role
    ROLE_ACTIVE_TIME_THRESHOLDS = {
        'admin': 8,  # 8 hours
        'marketing_manager': 8,  # 8 hours
        'marketing_team': 8,  # 8 hours
        'productions_manager': 8,  # 8 hours
        'productions_team': 8,  # 8 hours
        'production': 8,  # 8 hours
        'caller': 8,  # 8 hours
        'lead_generator': 8,  # 8 hours
        'leadgenerator': 8  # 8 hours
    }
    
    @staticmethod
    def track_activity_time(user_id, activity_type, duration_minutes=None):
        """
        Track active time for a user activity.
        
        Args:
            user_id (int): ID of the user
            activity_type (str): Type of activity
            duration_minutes (int, optional): Custom duration in minutes
        """
        try:
            # Get activity duration
            if duration_minutes is not None:
                activity_duration = duration_minutes
            else:
                activity_duration = ActiveTimeTracker.ACTIVE_ACTIVITIES.get(activity_type, 5)  # Default 5 minutes
            
            # Update daily stats
            today = date.today()
            daily_stats = UserDailyStats.query.filter_by(user_id=user_id, date=today).first()
            
            if daily_stats:
                daily_stats.total_time_spent += activity_duration
            else:
                # Create new daily stats
                daily_stats = UserDailyStats(
                    user_id=user_id,
                    date=today,
                    total_time_spent=activity_duration
                )
                db.session.add(daily_stats)
            
            # Update team member daily report
            ActiveTimeTracker._update_team_member_active_time(user_id, activity_duration)
            
            db.session.commit()
            logger.info(f"Active time tracked: User {user_id} - {activity_type} ({activity_duration} minutes)")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking active time: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def _update_team_member_active_time(user_id, duration_minutes):
        """Update team member daily report with active time."""
        try:
            from .models import TeamMemberDailyReport, UserTeam
            
            today = date.today()
            
            # Get user's team
            user_team = UserTeam.query.filter_by(user_id=user_id, is_active=True).first()
            if not user_team:
                return
            
            # Get or create daily report
            daily_report = TeamMemberDailyReport.query.filter_by(
                user_id=user_id,
                team_id=user_team.team_id,
                report_date=today
            ).first()
            
            if daily_report:
                # Update existing report
                daily_report.total_active_time += duration_minutes
                
                # Calculate productivity score based on active time
                daily_report.productivity_score = ActiveTimeTracker._calculate_productivity_score(
                    daily_report.leads_created,
                    daily_report.calls_made,
                    daily_report.total_active_time
                )
            else:
                # Create new daily report
                daily_report = TeamMemberDailyReport(
                    user_id=user_id,
                    team_id=user_team.team_id,
                    report_date=today,
                    total_active_time=duration_minutes,
                    productivity_score=ActiveTimeTracker._calculate_productivity_score(0, 0, duration_minutes)
                )
                db.session.add(daily_report)
            
        except Exception as e:
            logger.error(f"Error updating team member active time: {str(e)}")
    
    @staticmethod
    def _calculate_productivity_score(leads_created, calls_made, active_time_minutes):
        """Calculate productivity score based on activities and active time."""
        try:
            # Base productivity calculation
            base_score = 50  # Base score
            
            # Activity-based scoring
            leads_score = min(leads_created * 5, 30)  # Max 30 points for leads
            calls_score = min(calls_made * 2, 20)     # Max 20 points for calls
            
            # Time-based scoring (efficiency)
            active_hours = active_time_minutes / 60
            time_efficiency = min(active_hours / 8 * 20, 20)  # Max 20 points for time efficiency
            
            # Calculate total score
            total_score = base_score + leads_score + calls_score + time_efficiency
            
            # Cap at 100
            return min(round(total_score, 2), 100)
            
        except Exception as e:
            logger.error(f"Error calculating productivity score: {str(e)}")
            return 50  # Default score
    
    @staticmethod
    def get_user_active_time(user_id, period='today'):
        """Get active time for a user."""
        try:
            if period == 'today':
                start_date = date.today()
            elif period == 'week':
                start_date = date.today() - timedelta(days=7)
            elif period == 'month':
                start_date = date.today() - timedelta(days=30)
            else:
                start_date = date.today()
            
            # Get active time from daily stats
            daily_stats = UserDailyStats.query.filter(
                UserDailyStats.user_id == user_id,
                UserDailyStats.date >= start_date
            ).all()
            
            total_minutes = sum(stat.total_time_spent for stat in daily_stats)
            total_hours = total_minutes / 60
            
            # Get activity breakdown
            activities = UserActivity.query.filter(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= datetime.combine(start_date, datetime.min.time())
            ).all()
            
            activity_breakdown = {}
            for activity in activities:
                activity_type = activity.activity_type
                if activity_type not in activity_breakdown:
                    activity_breakdown[activity_type] = 0
                activity_breakdown[activity_type] += 1
            
            return {
                'total_minutes': total_minutes,
                'total_hours': round(total_hours, 2),
                'period': period,
                'activity_breakdown': activity_breakdown,
                'daily_average': round(total_hours / max(len(daily_stats), 1), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting user active time: {str(e)}")
            return None
    
    @staticmethod
    def get_team_active_time(team_id, period='today'):
        """Get active time for an entire team."""
        try:
            from .models import UserTeam
            
            if period == 'today':
                start_date = date.today()
            elif period == 'week':
                start_date = date.today() - timedelta(days=7)
            elif period == 'month':
                start_date = date.today() - timedelta(days=30)
            else:
                start_date = date.today()
            
            # Get team members
            team_members = UserTeam.query.filter_by(team_id=team_id, is_active=True).all()
            user_ids = [member.user_id for member in team_members]
            
            # Get team active time
            team_stats = UserDailyStats.query.filter(
                UserDailyStats.user_id.in_(user_ids),
                UserDailyStats.date >= start_date
            ).all()
            
            total_minutes = sum(stat.total_time_spent for stat in team_stats)
            total_hours = total_minutes / 60
            
            # Calculate per-member averages
            member_count = len(user_ids)
            avg_hours_per_member = total_hours / member_count if member_count > 0 else 0
            
            return {
                'total_minutes': total_minutes,
                'total_hours': round(total_hours, 2),
                'member_count': member_count,
                'avg_hours_per_member': round(avg_hours_per_member, 2),
                'period': period
            }
            
        except Exception as e:
            logger.error(f"Error getting team active time: {str(e)}")
            return None
    
    @staticmethod
    def check_active_time_threshold(user_id):
        """Check if user meets active time threshold for their role."""
        try:
            user = User.query.get(user_id)
            if not user or not user.role:
                return False
            
            role_name = user.role.name.lower().replace(' ', '_')
            threshold_hours = ActiveTimeTracker.ROLE_ACTIVE_TIME_THRESHOLDS.get(role_name, 8)
            
            # Get today's active time
            today_stats = UserDailyStats.query.filter_by(
                user_id=user_id,
                date=date.today()
            ).first()
            
            if not today_stats:
                return False
            
            active_hours = today_stats.total_time_spent / 60
            return active_hours >= threshold_hours
            
        except Exception as e:
            logger.error(f"Error checking active time threshold: {str(e)}")
            return False
    
    @staticmethod
    def get_active_time_analytics(user_id, period='week'):
        """Get detailed active time analytics for a user."""
        try:
            if period == 'week':
                start_date = date.today() - timedelta(days=7)
            elif period == 'month':
                start_date = date.today() - timedelta(days=30)
            else:
                start_date = date.today() - timedelta(days=7)
            
            # Get daily active time data
            daily_stats = UserDailyStats.query.filter(
                UserDailyStats.user_id == user_id,
                UserDailyStats.date >= start_date
            ).order_by(UserDailyStats.date).all()
            
            # Prepare data for analytics
            dates = [stat.date.strftime('%Y-%m-%d') for stat in daily_stats]
            hours = [round(stat.total_time_spent / 60, 2) for stat in daily_stats]
            
            # Calculate averages
            avg_hours = sum(hours) / len(hours) if hours else 0
            max_hours = max(hours) if hours else 0
            min_hours = min(hours) if hours else 0
            
            # Calculate consistency (standard deviation)
            if len(hours) > 1:
                mean_hours = sum(hours) / len(hours)
                variance = sum((h - mean_hours) ** 2 for h in hours) / len(hours)
                consistency = 100 - (variance ** 0.5 / mean_hours * 100) if mean_hours > 0 else 0
            else:
                consistency = 100
            
            return {
                'dates': dates,
                'hours': hours,
                'avg_hours': round(avg_hours, 2),
                'max_hours': round(max_hours, 2),
                'min_hours': round(min_hours, 2),
                'consistency': round(consistency, 2),
                'period': period,
                'total_days': len(daily_stats)
            }
            
        except Exception as e:
            logger.error(f"Error getting active time analytics: {str(e)}")
            return None

# Convenience functions for easy integration
def track_activity_time(user_id, activity_type, duration_minutes=None):
    """Convenience function to track activity time."""
    return ActiveTimeTracker.track_activity_time(user_id, activity_type, duration_minutes)

def get_user_active_time(user_id, period='today'):
    """Convenience function to get user active time."""
    return ActiveTimeTracker.get_user_active_time(user_id, period)

def get_team_active_time(team_id, period='today'):
    """Convenience function to get team active time."""
    return ActiveTimeTracker.get_team_active_time(team_id, period)

def check_active_time_threshold(user_id):
    """Convenience function to check active time threshold."""
    return ActiveTimeTracker.check_active_time_threshold(user_id)

def get_active_time_analytics(user_id, period='week'):
    """Convenience function to get active time analytics."""
    return ActiveTimeTracker.get_active_time_analytics(user_id, period) 