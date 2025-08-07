#!/usr/bin/env python3
"""
Robust Call Tracking System
Provides detailed call analytics and tracking with enhanced features.
"""

from flask import current_app, request
from datetime import datetime, timezone, timedelta
from .models import db, Lead, UserActivity, UserDailyStats, TeamMemberDailyReport, Call
from sqlalchemy import func
import logging

# Set up logging
logger = logging.getLogger(__name__)

class CallTracker:
    """Enhanced call tracking system with detailed analytics."""
    
    # Call status definitions
    CALL_STATUSES = {
        'successful': ['Interested', 'Scheduled for Meeting', 'Converted', 'Follow Up'],
        'failed': ['Call not reach', 'Wrong Number', 'No Answer'],
        'pending': ['New', 'Pending'],
        'converted': ['Converted'],
        'interested': ['Interested', 'Scheduled for Meeting'],
        'followup': ['Follow Up']
    }
    
    @staticmethod
    def track_call(user_id, lead_id, old_status, new_status, call_notes=None):
        """
        Track a call with detailed analytics and create Call record.
        
        Args:
            user_id (int): ID of the user making the call
            lead_id (int): ID of the lead being called
            old_status (str): Previous lead status
            new_status (str): New lead status after call
            call_notes (str, optional): Additional call notes
        """
        try:
            # Get lead details
            lead = Lead.query.get(lead_id)
            if not lead:
                logger.error(f"Lead {lead_id} not found for call tracking")
                return False
            
            # Determine call result and type
            call_result = CallTracker._determine_call_result(old_status, new_status)
            call_type = CallTracker._determine_call_type(old_status, new_status)
            call_status = CallTracker._determine_call_status(new_status)
            call_duration = CallTracker._estimate_call_duration(new_status)
            
            # Get contact information
            contact_name = None
            phone_number = None
            if lead.contacts:
                contact = lead.contacts[0]
                contact_name = contact.name
                if contact.phones:
                    phone_number = contact.phones[0].phone
            
            # Create Call record
            call = Call(
                made_by=user_id,
                lead_id=lead_id,
                contact_name=contact_name,
                phone_number=phone_number or 'Unknown',
                call_type=call_type,
                status=call_status,
                duration=call_duration,
                call_notes=call_notes,
                call_date=datetime.now(timezone.utc)
            )
            db.session.add(call)
            
            # Log call activity
            from .activity_logger import log_call_made
            log_call_made(user_id, lead_id, lead.company_name, old_status, new_status)
            
            # Update call statistics
            CallTracker._update_call_stats(user_id, call_result, call_duration)
            
            # Update lead call history
            CallTracker._update_lead_call_history(lead_id, user_id, old_status, new_status, call_notes)
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Call tracked: User {user_id} called {lead.company_name} - {old_status} → {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking call: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def _determine_call_result(old_status, new_status):
        """Determine the result of a call based on status change."""
        if new_status in CallTracker.CALL_STATUSES['successful']:
            return 'successful'
        elif new_status in CallTracker.CALL_STATUSES['failed']:
            return 'failed'
        elif new_status in CallTracker.CALL_STATUSES['converted']:
            return 'converted'
        elif new_status in CallTracker.CALL_STATUSES['interested']:
            return 'interested'
        elif new_status in CallTracker.CALL_STATUSES['followup']:
            return 'followup'
        else:
            return 'unknown'
    
    @staticmethod
    def _determine_call_type(old_status, new_status):
        """Determine the type of call based on status change."""
        if old_status == 'New':
            return 'cold_call'
        elif new_status in ['Follow Up']:
            return 'follow_up'
        elif new_status in ['Interested', 'Scheduled for Meeting', 'Converted']:
            return 'outbound'
        elif new_status in ['Call not reach', 'Wrong Number', 'No Answer']:
            return 'outbound'
        else:
            return 'outbound'
    
    @staticmethod
    def _determine_call_status(new_status):
        """Determine the call status based on lead status."""
        status_mapping = {
            'Interested': 'completed',
            'Scheduled for Meeting': 'completed',
            'Converted': 'completed',
            'Follow Up': 'completed',
            'Call not reach': 'missed',
            'Wrong Number': 'missed',
            'No Answer': 'no_answer',
            'New': 'missed'
        }
        return status_mapping.get(new_status, 'completed')
    
    @staticmethod
    def _estimate_call_duration(status):
        """Estimate call duration based on status."""
        duration_map = {
            'Interested': 15,  # 15 minutes
            'Scheduled for Meeting': 20,  # 20 minutes
            'Converted': 25,  # 25 minutes
            'Follow Up': 10,  # 10 minutes
            'Call not reach': 2,  # 2 minutes
            'Wrong Number': 1,  # 1 minute
            'No Answer': 3,  # 3 minutes
        }
        return duration_map.get(status, 5)  # Default 5 minutes
    
    @staticmethod
    def _update_call_stats(user_id, call_result, duration):
        """Update call statistics for the user."""
        try:
            today = datetime.now().date()
            
            # Update daily stats
            daily_stats = UserDailyStats.query.filter_by(user_id=user_id, date=today).first()
            if daily_stats:
                if call_result == 'successful':
                    daily_stats.conversions += 1
                # Add call duration to total time
                daily_stats.total_time_spent += duration
            else:
                # Create new daily stats
                daily_stats = UserDailyStats(
                    user_id=user_id,
                    date=today,
                    conversions=1 if call_result == 'successful' else 0,
                    total_time_spent=duration
                )
                db.session.add(daily_stats)
            
            # Update team member daily report
            CallTracker._update_team_member_call_stats(user_id, call_result, duration)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating call stats: {str(e)}")
            db.session.rollback()
    
    @staticmethod
    def _update_team_member_call_stats(user_id, call_result, duration):
        """Update team member daily report with call statistics."""
        try:
            from .models import TeamMemberDailyReport, Team, UserTeam
            
            today = datetime.now().date()
            
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
                daily_report.calls_made += 1
                daily_report.total_active_time += duration
                
                # Update goal achievement
                if daily_report.daily_goal > 0:
                    daily_report.goal_achievement = min(100, (daily_report.leads_created + daily_report.calls_made) / daily_report.daily_goal * 100)
            else:
                # Create new daily report
                daily_report = TeamMemberDailyReport(
                    user_id=user_id,
                    team_id=user_team.team_id,
                    report_date=today,
                    calls_made=1,
                    total_active_time=duration,
                    daily_goal=20,  # Default daily goal
                    goal_achievement=5.0  # 1 call = 5% of 20 goal
                )
                db.session.add(daily_report)
            
        except Exception as e:
            logger.error(f"Error updating team member call stats: {str(e)}")
    
    @staticmethod
    def _update_lead_call_history(lead_id, user_id, old_status, new_status, call_notes):
        """Update lead call history."""
        try:
            # This could be extended to store detailed call history
            # For now, we just update the lead status
            lead = Lead.query.get(lead_id)
            if lead:
                lead.status = new_status
                lead.updated_at = datetime.now(timezone.utc)
                lead.updated_by = user_id
                
                # Add call notes if provided
                if call_notes:
                    if lead.notes:
                        lead.notes += f"\n\nCall Notes ({datetime.now().strftime('%Y-%m-%d %H:%M')}): {call_notes}"
                    else:
                        lead.notes = f"Call Notes ({datetime.now().strftime('%Y-%m-%d %H:%M')}): {call_notes}"
            
        except Exception as e:
            logger.error(f"Error updating lead call history: {str(e)}")
    
    @staticmethod
    def get_call_analytics(user_id, period='today'):
        """Get call analytics for a user."""
        try:
            if period == 'today':
                start_date = datetime.now().date()
            elif period == 'week':
                start_date = datetime.now().date() - timedelta(days=7)
            elif period == 'month':
                start_date = datetime.now().date() - timedelta(days=30)
            else:
                start_date = datetime.now().date()
            
            # Get calls made
            calls_made = Lead.query.filter(
                Lead.created_by == user_id,
                Lead.updated_at >= start_date,
                Lead.status.in_(CallTracker.CALL_STATUSES['successful'] + CallTracker.CALL_STATUSES['failed'])
            ).count()
            
            # Get successful calls
            successful_calls = Lead.query.filter(
                Lead.created_by == user_id,
                Lead.updated_at >= start_date,
                Lead.status.in_(CallTracker.CALL_STATUSES['successful'])
            ).count()
            
            # Get conversions
            conversions = Lead.query.filter(
                Lead.created_by == user_id,
                Lead.updated_at >= start_date,
                Lead.status.in_(CallTracker.CALL_STATUSES['converted'])
            ).count()
            
            # Calculate success rate
            success_rate = (successful_calls / calls_made * 100) if calls_made > 0 else 0
            
            # Calculate conversion rate
            conversion_rate = (conversions / calls_made * 100) if calls_made > 0 else 0
            
            return {
                'calls_made': calls_made,
                'successful_calls': successful_calls,
                'conversions': conversions,
                'success_rate': round(success_rate, 2),
                'conversion_rate': round(conversion_rate, 2),
                'period': period
            }
            
        except Exception as e:
            logger.error(f"Error getting call analytics: {str(e)}")
            return None
    
    @staticmethod
    def get_team_call_analytics(team_id, period='today'):
        """Get call analytics for a team."""
        try:
            from .models import UserTeam
            
            if period == 'today':
                start_date = datetime.now().date()
            elif period == 'week':
                start_date = datetime.now().date() - timedelta(days=7)
            elif period == 'month':
                start_date = datetime.now().date() - timedelta(days=30)
            else:
                start_date = datetime.now().date()
            
            # Get team members
            team_members = UserTeam.query.filter_by(team_id=team_id, is_active=True).all()
            user_ids = [member.user_id for member in team_members]
            
            # Get team calls
            team_calls = Lead.query.filter(
                Lead.created_by.in_(user_ids),
                Lead.updated_at >= start_date,
                Lead.status.in_(CallTracker.CALL_STATUSES['successful'] + CallTracker.CALL_STATUSES['failed'])
            ).count()
            
            # Get team successful calls
            team_successful = Lead.query.filter(
                Lead.created_by.in_(user_ids),
                Lead.updated_at >= start_date,
                Lead.status.in_(CallTracker.CALL_STATUSES['successful'])
            ).count()
            
            # Get team conversions
            team_conversions = Lead.query.filter(
                Lead.created_by.in_(user_ids),
                Lead.updated_at >= start_date,
                Lead.status.in_(CallTracker.CALL_STATUSES['converted'])
            ).count()
            
            # Calculate team success rate
            team_success_rate = (team_successful / team_calls * 100) if team_calls > 0 else 0
            
            # Calculate team conversion rate
            team_conversion_rate = (team_conversions / team_calls * 100) if team_calls > 0 else 0
            
            return {
                'team_calls': team_calls,
                'team_successful': team_successful,
                'team_conversions': team_conversions,
                'team_success_rate': round(team_success_rate, 2),
                'team_conversion_rate': round(team_conversion_rate, 2),
                'team_members': len(user_ids),
                'period': period
            }
            
        except Exception as e:
            logger.error(f"Error getting team call analytics: {str(e)}")
            return None

# Convenience functions for easy integration
def track_call(user_id, lead_id, old_status, new_status, call_notes=None):
    """Convenience function to track a call."""
    return CallTracker.track_call(user_id, lead_id, old_status, new_status, call_notes)

def get_user_call_analytics(user_id, period='today'):
    """Convenience function to get user call analytics."""
    return CallTracker.get_call_analytics(user_id, period)

def get_team_call_analytics(team_id, period='today'):
    """Convenience function to get team call analytics."""
    return CallTracker.get_team_call_analytics(team_id, period) 