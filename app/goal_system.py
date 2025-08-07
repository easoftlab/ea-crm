#!/usr/bin/env python3
"""
Comprehensive Goal Setting System
Provides goal setting, tracking, and achievement monitoring for users and teams.
"""

from flask import current_app
from datetime import datetime, timedelta, date
from .models import db, User, Team, TeamMemberDailyReport, TeamMemberWeeklyReport, TeamMemberMonthlyReport
from sqlalchemy import func
import logging

# Set up logging
logger = logging.getLogger(__name__)

class GoalSystem:
    """Comprehensive goal setting and tracking system."""
    
    # Goal types
    GOAL_TYPES = {
        'daily_leads': 'Daily Leads Created',
        'daily_calls': 'Daily Calls Made',
        'daily_conversions': 'Daily Conversions',
        'weekly_leads': 'Weekly Leads Created',
        'weekly_calls': 'Weekly Calls Made',
        'weekly_conversions': 'Weekly Conversions',
        'monthly_leads': 'Monthly Leads Created',
        'monthly_calls': 'Monthly Calls Made',
        'monthly_conversions': 'Monthly Conversions',
        'productivity_score': 'Productivity Score',
        'active_time': 'Active Time (hours)'
    }
    
    # Default goals by role
    DEFAULT_GOALS = {
        'marketing_manager': {
            'daily_leads': 20,
            'daily_calls': 30,
            'daily_conversions': 5,
            'productivity_score': 85,
            'active_time': 8
        },
        'marketing_team': {
            'daily_leads': 15,
            'daily_calls': 25,
            'daily_conversions': 3,
            'productivity_score': 80,
            'active_time': 8
        },
        'productions_manager': {
            'daily_leads': 10,
            'daily_calls': 15,
            'daily_conversions': 2,
            'productivity_score': 85,
            'active_time': 8
        },
        'productions_team': {
            'daily_leads': 8,
            'daily_calls': 12,
            'daily_conversions': 1,
            'productivity_score': 80,
            'active_time': 8
        },
        'admin': {
            'daily_leads': 25,
            'daily_calls': 40,
            'daily_conversions': 8,
            'productivity_score': 90,
            'active_time': 8
        }
    }
    
    @staticmethod
    def set_user_goals(user_id, goals_dict):
        """
        Set goals for a specific user.
        
        Args:
            user_id (int): ID of the user
            goals_dict (dict): Dictionary of goals with values
        """
        try:
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found for goal setting")
                return False
            
            # Get user's role to determine default goals
            role_name = user.role.name.lower().replace(' ', '_') if user.role else 'default'
            default_goals = GoalSystem.DEFAULT_GOALS.get(role_name, GoalSystem.DEFAULT_GOALS['marketing_team'])
            
            # Update or create daily report with goals
            today = date.today()
            daily_report = TeamMemberDailyReport.query.filter_by(
                user_id=user_id,
                report_date=today
            ).first()
            
            if daily_report:
                # Update existing report with new goals
                for goal_type, value in goals_dict.items():
                    if hasattr(daily_report, goal_type):
                        setattr(daily_report, goal_type, value)
                
                # Update daily goal (sum of leads and calls)
                daily_report.daily_goal = goals_dict.get('daily_leads', 0) + goals_dict.get('daily_calls', 0)
            else:
                # Create new daily report with goals
                daily_report = TeamMemberDailyReport(
                    user_id=user_id,
                    report_date=today,
                    daily_goal=goals_dict.get('daily_leads', 0) + goals_dict.get('daily_calls', 0),
                    **{k: v for k, v in goals_dict.items() if hasattr(TeamMemberDailyReport, k)}
                )
                db.session.add(daily_report)
            
            db.session.commit()
            logger.info(f"Goals set for user {user_id}: {goals_dict}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting user goals: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_user_goals(user_id):
        """Get current goals for a user."""
        try:
            today = date.today()
            daily_report = TeamMemberDailyReport.query.filter_by(
                user_id=user_id,
                report_date=today
            ).first()
            
            if daily_report:
                return {
                    'daily_leads': daily_report.daily_leads_goal if hasattr(daily_report, 'daily_leads_goal') else 15,
                    'daily_calls': daily_report.daily_calls_goal if hasattr(daily_report, 'daily_calls_goal') else 25,
                    'daily_conversions': daily_report.daily_conversions_goal if hasattr(daily_report, 'daily_conversions_goal') else 3,
                    'productivity_score': daily_report.productivity_goal if hasattr(daily_report, 'productivity_goal') else 80,
                    'active_time': daily_report.active_time_goal if hasattr(daily_report, 'active_time_goal') else 8,
                    'daily_goal': daily_report.daily_goal
                }
            else:
                # Return default goals based on user role
                user = User.query.get(user_id)
                if user and user.role:
                    role_name = user.role.name.lower().replace(' ', '_')
                    return GoalSystem.DEFAULT_GOALS.get(role_name, GoalSystem.DEFAULT_GOALS['marketing_team'])
                else:
                    return GoalSystem.DEFAULT_GOALS['marketing_team']
                    
        except Exception as e:
            logger.error(f"Error getting user goals: {str(e)}")
            return None
    
    @staticmethod
    def calculate_goal_achievement(user_id, period='daily'):
        """
        Calculate goal achievement for a user.
        
        Args:
            user_id (int): ID of the user
            period (str): 'daily', 'weekly', or 'monthly'
        """
        try:
            if period == 'daily':
                today = date.today()
                report = TeamMemberDailyReport.query.filter_by(
                    user_id=user_id,
                    report_date=today
                ).first()
                
                if not report:
                    return None
                
                goals = GoalSystem.get_user_goals(user_id)
                if not goals:
                    return None
                
                # Calculate achievements
                leads_achievement = (report.leads_created / goals['daily_leads'] * 100) if goals['daily_leads'] > 0 else 0
                calls_achievement = (report.calls_made / goals['daily_calls'] * 100) if goals['daily_calls'] > 0 else 0
                conversions_achievement = (report.conversions / goals['daily_conversions'] * 100) if goals['daily_conversions'] > 0 else 0
                productivity_achievement = (report.productivity_score / goals['productivity_score'] * 100) if goals['productivity_score'] > 0 else 0
                
                # Overall achievement (weighted average)
                overall_achievement = (
                    leads_achievement * 0.3 +
                    calls_achievement * 0.3 +
                    conversions_achievement * 0.2 +
                    productivity_achievement * 0.2
                )
                
                return {
                    'leads_achievement': round(leads_achievement, 2),
                    'calls_achievement': round(calls_achievement, 2),
                    'conversions_achievement': round(conversions_achievement, 2),
                    'productivity_achievement': round(productivity_achievement, 2),
                    'overall_achievement': round(overall_achievement, 2),
                    'goals': goals,
                    'actual': {
                        'leads_created': report.leads_created,
                        'calls_made': report.calls_made,
                        'conversions': report.conversions,
                        'productivity_score': report.productivity_score
                    }
                }
            
            elif period == 'weekly':
                # Calculate weekly goals and achievements
                week_start = date.today() - timedelta(days=date.today().weekday())
                report = TeamMemberWeeklyReport.query.filter_by(
                    user_id=user_id,
                    week_start=week_start
                ).first()
                
                if not report:
                    return None
                
                # Weekly goals (7x daily goals)
                daily_goals = GoalSystem.get_user_goals(user_id)
                weekly_goals = {k: v * 7 for k, v in daily_goals.items() if k != 'active_time'}
                weekly_goals['active_time'] = daily_goals['active_time'] * 7
                
                # Calculate weekly achievements
                leads_achievement = (report.total_leads_created / weekly_goals['daily_leads'] * 100) if weekly_goals['daily_leads'] > 0 else 0
                calls_achievement = (report.total_calls_made / weekly_goals['daily_calls'] * 100) if weekly_goals['daily_calls'] > 0 else 0
                conversions_achievement = (report.total_conversions / weekly_goals['daily_conversions'] * 100) if weekly_goals['daily_conversions'] > 0 else 0
                
                overall_achievement = (
                    leads_achievement * 0.4 +
                    calls_achievement * 0.4 +
                    conversions_achievement * 0.2
                )
                
                return {
                    'leads_achievement': round(leads_achievement, 2),
                    'calls_achievement': round(calls_achievement, 2),
                    'conversions_achievement': round(conversions_achievement, 2),
                    'overall_achievement': round(overall_achievement, 2),
                    'goals': weekly_goals,
                    'actual': {
                        'total_leads_created': report.total_leads_created,
                        'total_calls_made': report.total_calls_made,
                        'total_conversions': report.total_conversions
                    }
                }
            
            elif period == 'monthly':
                # Calculate monthly goals and achievements
                month_start = date(date.today().year, date.today().month, 1)
                report = TeamMemberMonthlyReport.query.filter_by(
                    user_id=user_id,
                    month_year=month_start
                ).first()
                
                if not report:
                    return None
                
                # Monthly goals (30x daily goals)
                daily_goals = GoalSystem.get_user_goals(user_id)
                monthly_goals = {k: v * 30 for k, v in daily_goals.items() if k != 'active_time'}
                monthly_goals['active_time'] = daily_goals['active_time'] * 30
                
                # Calculate monthly achievements
                leads_achievement = (report.total_leads_created / monthly_goals['daily_leads'] * 100) if monthly_goals['daily_leads'] > 0 else 0
                calls_achievement = (report.total_calls_made / monthly_goals['daily_calls'] * 100) if monthly_goals['daily_calls'] > 0 else 0
                conversions_achievement = (report.total_conversions / monthly_goals['daily_conversions'] * 100) if monthly_goals['daily_conversions'] > 0 else 0
                
                overall_achievement = (
                    leads_achievement * 0.4 +
                    calls_achievement * 0.4 +
                    conversions_achievement * 0.2
                )
                
                return {
                    'leads_achievement': round(leads_achievement, 2),
                    'calls_achievement': round(calls_achievement, 2),
                    'conversions_achievement': round(conversions_achievement, 2),
                    'overall_achievement': round(overall_achievement, 2),
                    'goals': monthly_goals,
                    'actual': {
                        'total_leads_created': report.total_leads_created,
                        'total_calls_made': report.total_calls_made,
                        'total_conversions': report.total_conversions
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating goal achievement: {str(e)}")
            return None
    
    @staticmethod
    def set_team_goals(team_id, goals_dict):
        """Set goals for an entire team."""
        try:
            from .models import UserTeam
            
            # Get team members
            team_members = UserTeam.query.filter_by(team_id=team_id, is_active=True).all()
            
            success_count = 0
            for member in team_members:
                if GoalSystem.set_user_goals(member.user_id, goals_dict):
                    success_count += 1
            
            logger.info(f"Team goals set for team {team_id}: {success_count}/{len(team_members)} members updated")
            return success_count == len(team_members)
            
        except Exception as e:
            logger.error(f"Error setting team goals: {str(e)}")
            return False
    
    @staticmethod
    def get_team_goals(team_id):
        """Get goals for an entire team."""
        try:
            from .models import UserTeam
            
            # Get team members
            team_members = UserTeam.query.filter_by(team_id=team_id, is_active=True).all()
            
            team_goals = {}
            for member in team_members:
                user_goals = GoalSystem.get_user_goals(member.user_id)
                if user_goals:
                    for goal_type, value in user_goals.items():
                        if goal_type not in team_goals:
                            team_goals[goal_type] = []
                        team_goals[goal_type].append(value)
            
            # Calculate team averages
            team_averages = {}
            for goal_type, values in team_goals.items():
                if values:
                    team_averages[goal_type] = round(sum(values) / len(values), 2)
            
            return team_averages
            
        except Exception as e:
            logger.error(f"Error getting team goals: {str(e)}")
            return None
    
    @staticmethod
    def calculate_team_achievement(team_id, period='daily'):
        """Calculate goal achievement for an entire team."""
        try:
            from .models import UserTeam
            
            # Get team members
            team_members = UserTeam.query.filter_by(team_id=team_id, is_active=True).all()
            
            team_achievements = []
            for member in team_members:
                achievement = GoalSystem.calculate_goal_achievement(member.user_id, period)
                if achievement:
                    team_achievements.append(achievement)
            
            if not team_achievements:
                return None
            
            # Calculate team averages
            team_average = {}
            for key in ['leads_achievement', 'calls_achievement', 'conversions_achievement', 'overall_achievement']:
                values = [a[key] for a in team_achievements if key in a]
                if values:
                    team_average[key] = round(sum(values) / len(values), 2)
            
            return team_average
            
        except Exception as e:
            logger.error(f"Error calculating team achievement: {str(e)}")
            return None
    
    @staticmethod
    def get_goal_recommendations(user_id):
        """Get personalized goal recommendations based on user performance."""
        try:
            # Get user's recent performance
            recent_reports = TeamMemberDailyReport.query.filter_by(user_id=user_id).order_by(
                TeamMemberDailyReport.report_date.desc()
            ).limit(7).all()
            
            if not recent_reports:
                return GoalSystem.get_user_goals(user_id)
            
            # Calculate averages
            avg_leads = sum(r.leads_created for r in recent_reports) / len(recent_reports)
            avg_calls = sum(r.calls_made for r in recent_reports) / len(recent_reports)
            avg_conversions = sum(r.conversions for r in recent_reports) / len(recent_reports)
            avg_productivity = sum(r.productivity_score for r in recent_reports) / len(recent_reports)
            
            # Recommend goals based on performance (10% increase for good performers, 5% for others)
            current_goals = GoalSystem.get_user_goals(user_id)
            
            recommendations = {}
            for goal_type in ['daily_leads', 'daily_calls', 'daily_conversions', 'productivity_score']:
                current_goal = current_goals.get(goal_type, 0)
                current_performance = {
                    'daily_leads': avg_leads,
                    'daily_calls': avg_calls,
                    'daily_conversions': avg_conversions,
                    'productivity_score': avg_productivity
                }.get(goal_type, 0)
                
                # Calculate recommendation
                if current_performance >= current_goal * 0.9:  # Good performer
                    recommendations[goal_type] = round(current_goal * 1.1)  # 10% increase
                else:
                    recommendations[goal_type] = round(current_goal * 1.05)  # 5% increase
            
            recommendations['active_time'] = current_goals.get('active_time', 8)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting goal recommendations: {str(e)}")
            return None

# Convenience functions for easy integration
def set_user_goals(user_id, goals_dict):
    """Convenience function to set user goals."""
    return GoalSystem.set_user_goals(user_id, goals_dict)

def get_user_goals(user_id):
    """Convenience function to get user goals."""
    return GoalSystem.get_user_goals(user_id)

def calculate_goal_achievement(user_id, period='daily'):
    """Convenience function to calculate goal achievement."""
    return GoalSystem.calculate_goal_achievement(user_id, period)

def set_team_goals(team_id, goals_dict):
    """Convenience function to set team goals."""
    return GoalSystem.set_team_goals(team_id, goals_dict)

def get_team_goals(team_id):
    """Convenience function to get team goals."""
    return GoalSystem.get_team_goals(team_id)

def calculate_team_achievement(team_id, period='daily'):
    """Convenience function to calculate team achievement."""
    return GoalSystem.calculate_team_achievement(team_id, period)

def get_goal_recommendations(user_id):
    """Convenience function to get goal recommendations."""
    return GoalSystem.get_goal_recommendations(user_id) 