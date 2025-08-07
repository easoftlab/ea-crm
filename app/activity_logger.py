#!/usr/bin/env python3
"""
Enhanced Activity Logging System
Ensures consistent real-time activity tracking across all user actions.
"""

from flask import current_app, request
from datetime import datetime, timezone
from .models import db, UserActivity, User, Lead
from .active_time_tracker import track_activity_time
import traceback
import logging

# Set up logging
logger = logging.getLogger(__name__)

class ActivityLogger:
    """Enhanced activity logging system with consistent tracking."""
    
    # Activity types for consistent logging
    ACTIVITY_TYPES = {
        # Lead activities
        'lead_created': 'Lead Created',
        'lead_updated': 'Lead Updated', 
        'lead_deleted': 'Lead Deleted',
        'lead_status_changed': 'Lead Status Changed',
        
        # Call activities
        'call_made': 'Call Made',
        'call_attempted': 'Call Attempted',
        'call_successful': 'Call Successful',
        'call_failed': 'Call Failed',
        
        # Task activities
        'task_created': 'Task Created',
        'task_updated': 'Task Updated',
        'task_completed': 'Task Completed',
        'task_assigned': 'Task Assigned',
        
        # User activities
        'user_login': 'User Login',
        'user_logout': 'User Logout',
        'user_profile_updated': 'Profile Updated',
        'user_password_changed': 'Password Changed',
        
        # Follow-up activities
        'followup_added': 'Follow-up Added',
        'followup_completed': 'Follow-up Completed',
        'followup_scheduled': 'Follow-up Scheduled',
        
        # Production activities
        'production_task_started': 'Production Task Started',
        'production_task_completed': 'Production Task Completed',
        'file_uploaded': 'File Uploaded',
        'code_committed': 'Code Committed',
        
        # System activities
        'report_generated': 'Report Generated',
        'data_exported': 'Data Exported',
        'settings_updated': 'Settings Updated'
    }
    
    @staticmethod
    def log_activity(user_id, activity_type, description, related_lead_id=None, 
                    related_task_id=None, additional_data=None):
        """
        Enhanced activity logging with error handling and validation.
        
        Args:
            user_id (int): ID of the user performing the action
            activity_type (str): Type of activity (from ACTIVITY_TYPES)
            description (str): Human-readable description
            related_lead_id (int, optional): Related lead ID
            related_task_id (int, optional): Related task ID
            additional_data (dict, optional): Additional data to store
        """
        try:
            # Validate activity type
            if activity_type not in ActivityLogger.ACTIVITY_TYPES:
                logger.warning(f"Unknown activity type: {activity_type}")
                activity_type = 'unknown_activity'
            
            # Get user IP address
            user_ip = request.remote_addr if request else None
            
            # Create activity record
            activity = UserActivity(
                user_id=user_id,
                activity_type=activity_type,
                description=description,
                related_lead_id=related_lead_id,
                created_at=datetime.now(timezone.utc)
            )
            
            # Add to database
            db.session.add(activity)
            db.session.commit()
            
            # Track active time for this activity
            track_activity_time(user_id, activity_type)
            
            # Log success
            logger.info(f"Activity logged: {activity_type} by user {user_id} - {description}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging activity: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def log_lead_creation(user_id, lead_id, company_name):
        """Log lead creation activity."""
        return ActivityLogger.log_activity(
            user_id=user_id,
            activity_type='lead_created',
            description=f'Created lead: {company_name}',
            related_lead_id=lead_id
        )
    
    @staticmethod
    def log_lead_update(user_id, lead_id, company_name, old_status=None, new_status=None):
        """Log lead update activity."""
        if old_status and new_status and old_status != new_status:
            description = f'Updated lead: {company_name} (Status: {old_status} → {new_status})'
            activity_type = 'lead_status_changed'
        else:
            description = f'Updated lead: {company_name}'
            activity_type = 'lead_updated'
        
        return ActivityLogger.log_activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            related_lead_id=lead_id
        )
    
    @staticmethod
    def log_call_activity(user_id, lead_id, company_name, call_status, call_result):
        """Log call activity with detailed tracking."""
        if call_result in ['Interested', 'Scheduled for Meeting', 'Converted', 'Follow Up']:
            activity_type = 'call_successful'
        elif call_result in ['Call not reach', 'Wrong Number', 'No Answer']:
            activity_type = 'call_failed'
        else:
            activity_type = 'call_made'
        
        description = f'Call to {company_name}: {call_status} → {call_result}'
        
        return ActivityLogger.log_activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            related_lead_id=lead_id
        )
    
    @staticmethod
    def log_task_activity(user_id, task_id, task_title, action_type):
        """Log task-related activities."""
        activity_type_map = {
            'created': 'task_created',
            'updated': 'task_updated',
            'completed': 'task_completed',
            'assigned': 'task_assigned'
        }
        
        activity_type = activity_type_map.get(action_type, 'task_updated')
        description = f'Task {action_type}: {task_title}'
        
        return ActivityLogger.log_activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            related_task_id=task_id
        )
    
    @staticmethod
    def log_user_session(user_id, action_type):
        """Log user login/logout activities."""
        activity_type = 'user_login' if action_type == 'login' else 'user_logout'
        description = f'User {action_type}'
        
        return ActivityLogger.log_activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description
        )
    
    @staticmethod
    def log_followup_activity(user_id, lead_id, company_name, action_type):
        """Log follow-up related activities."""
        activity_type_map = {
            'added': 'followup_added',
            'completed': 'followup_completed',
            'scheduled': 'followup_scheduled'
        }
        
        activity_type = activity_type_map.get(action_type, 'followup_added')
        description = f'Follow-up {action_type} for {company_name}'
        
        return ActivityLogger.log_activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            related_lead_id=lead_id
        )

# Convenience functions for easy integration
def log_lead_created(user_id, lead_id, company_name):
    """Convenience function to log lead creation."""
    return ActivityLogger.log_lead_creation(user_id, lead_id, company_name)

def log_lead_updated(user_id, lead_id, company_name, old_status=None, new_status=None):
    """Convenience function to log lead updates."""
    return ActivityLogger.log_lead_update(user_id, lead_id, company_name, old_status, new_status)

def log_call_made(user_id, lead_id, company_name, call_status, call_result):
    """Convenience function to log call activities."""
    return ActivityLogger.log_call_activity(user_id, lead_id, company_name, call_status, call_result)

def log_task_action(user_id, task_id, task_title, action_type):
    """Convenience function to log task activities."""
    return ActivityLogger.log_task_activity(user_id, task_id, task_title, action_type)

def log_user_login(user_id):
    """Convenience function to log user login."""
    return ActivityLogger.log_user_session(user_id, 'login')

def log_user_logout(user_id):
    """Convenience function to log user logout."""
    return ActivityLogger.log_user_session(user_id, 'logout')

def log_followup_action(user_id, lead_id, company_name, action_type):
    """Convenience function to log follow-up activities."""
    return ActivityLogger.log_followup_activity(user_id, lead_id, company_name, action_type) 