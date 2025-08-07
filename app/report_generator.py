#!/usr/bin/env python3
"""
Report Generation System
Generates comprehensive reports for marketing and productions managers
"""

import sqlite3
import json
from datetime import datetime, timedelta
from flask import current_app
import os

class ReportGenerator:
    """Main report generator class."""
    
    def __init__(self, db_path='instance/leads.db'):
        self.db_path = db_path
    
    def connect_db(self):
        """Connect to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            return None
    
    def generate_marketing_reports(self, team_id=None, date_range=None):
        """Generate marketing reports."""
        print("📊 Generating Marketing Reports...")
        
        conn = self.connect_db()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Get date range
            if date_range is None:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
            else:
                start_date, end_date = date_range
            
            # Build team filter
            team_filter = ""
            team_params = []
            if team_id:
                team_filter = "AND t.id = ?"
                team_params.append(team_id)
            
            # Lead Generation Report
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_leads,
                    COUNT(CASE WHEN status = 'converted' THEN 1 END) as converted_leads,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_leads,
                    COUNT(CASE WHEN status = 'lost' THEN 1 END) as lost_leads
                FROM leads l
                JOIN users u ON l.created_by = u.id
                JOIN user_teams ut ON u.id = ut.user_id
                JOIN teams t ON ut.team_id = t.id
                WHERE DATE(l.created_at) BETWEEN ? AND ?
                {team_filter}
            """, [start_date, end_date] + team_params)
            
            lead_stats = cursor.fetchone()
            
            # Call Analytics Report (using user_activities)
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_calls,
                    COUNT(CASE WHEN activity_type = 'call' THEN 1 END) as completed_calls,
                    COUNT(CASE WHEN activity_type = 'missed_call' THEN 1 END) as missed_calls
                FROM user_activities ua
                JOIN users u ON ua.user_id = u.id
                JOIN user_teams ut ON u.id = ut.user_id
                JOIN teams t ON ut.team_id = t.id
                WHERE ua.activity_type IN ('call', 'missed_call')
                AND DATE(ua.created_at) BETWEEN ? AND ?
                {team_filter}
            """, [start_date, end_date] + team_params)
            
            call_stats = cursor.fetchone()
            
            # Revenue Projections
            cursor.execute(f"""
                SELECT 
                    SUM(projected_value) as total_projected,
                    AVG(projected_value) as avg_projected,
                    COUNT(*) as total_projections
                FROM lead_projections lp
                JOIN leads l ON lp.lead_id = l.id
                JOIN users u ON l.created_by = u.id
                JOIN user_teams ut ON u.id = ut.user_id
                JOIN teams t ON ut.team_id = t.id
                WHERE DATE(lp.created_at) BETWEEN ? AND ?
                {team_filter}
            """, [start_date, end_date] + team_params)
            
            revenue_stats = cursor.fetchone()
            
            # Team Performance
            cursor.execute(f"""
                SELECT 
                    u.username,
                    COUNT(l.id) as leads_created,
                    COUNT(CASE WHEN l.status = 'converted' THEN 1 END) as leads_converted,
                    COUNT(ua.id) as activities_count
                FROM users u
                JOIN user_teams ut ON u.id = ut.user_id
                JOIN teams t ON ut.team_id = t.id
                LEFT JOIN leads l ON u.id = l.created_by AND DATE(l.created_at) BETWEEN ? AND ?
                LEFT JOIN user_activities ua ON u.id = ua.user_id AND DATE(ua.created_at) BETWEEN ? AND ?
                WHERE t.id = ? OR ? IS NULL
                GROUP BY u.id, u.username
                ORDER BY leads_created DESC
            """, [start_date, end_date, start_date, end_date, team_id, team_id])
            
            team_performance = cursor.fetchall()
            
            # Create report data
            report_data = {
                'report_type': 'marketing',
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'lead_generation': {
                    'total_leads': lead_stats[0] if lead_stats else 0,
                    'converted_leads': lead_stats[1] if lead_stats else 0,
                    'pending_leads': lead_stats[2] if lead_stats else 0,
                    'lost_leads': lead_stats[3] if lead_stats else 0,
                    'conversion_rate': round((lead_stats[1] / lead_stats[0] * 100) if lead_stats and lead_stats[0] > 0 else 0, 2)
                },
                'call_analytics': {
                    'total_calls': call_stats[0] if call_stats else 0,
                    'completed_calls': call_stats[1] if call_stats else 0,
                    'missed_calls': call_stats[2] if call_stats else 0
                },
                'revenue_projections': {
                    'total_projected': revenue_stats[0] if revenue_stats else 0,
                    'avg_projected': round(revenue_stats[1] if revenue_stats and revenue_stats[1] else 0, 2),
                    'total_projections': revenue_stats[2] if revenue_stats else 0
                },
                'team_performance': [
                    {
                        'username': row[0],
                        'leads_created': row[1],
                        'leads_converted': row[2],
                        'activities_count': row[3],
                        'conversion_rate': round((row[2] / row[1] * 100) if row[1] > 0 else 0, 2)
                    } for row in team_performance
                ]
            }
            
            conn.close()
            return report_data
            
        except Exception as e:
            print(f"❌ Error generating marketing reports: {e}")
            if conn:
                conn.close()
            return None
    
    def generate_productions_reports(self, team_id=None, date_range=None):
        """Generate productions reports."""
        print("📊 Generating Productions Reports...")
        
        conn = self.connect_db()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Get date range
            if date_range is None:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
            else:
                start_date, end_date = date_range
            
            # Build team filter
            team_filter = ""
            team_params = []
            if team_id:
                team_filter = "AND t.id = ?"
                team_params.append(team_id)
            
            # Task Completion Report
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN tk.status = 'completed' THEN 1 END) as completed_tasks,
                    COUNT(CASE WHEN tk.status = 'pending' THEN 1 END) as pending_tasks,
                    COUNT(CASE WHEN tk.status = 'in_progress' THEN 1 END) as in_progress_tasks,
                    AVG(CASE WHEN tk.completed_at IS NOT NULL 
                        THEN JULIANDAY(tk.completed_at) - JULIANDAY(tk.created_at) END) as avg_completion_days
                FROM tasks tk
                JOIN users u ON tk.assigned_to = u.id
                JOIN user_teams ut ON u.id = ut.user_id
                JOIN teams t ON ut.team_id = t.id
                WHERE DATE(tk.created_at) BETWEEN ? AND ?
                {team_filter}
            """, [start_date, end_date] + team_params)
            
            task_stats = cursor.fetchone()
            
            # Productivity Metrics
            cursor.execute(f"""
                SELECT 
                    u.username,
                    COUNT(tk.id) as tasks_assigned,
                    COUNT(CASE WHEN tk.status = 'completed' THEN 1 END) as tasks_completed,
                    AVG(CASE WHEN tk.completed_at IS NOT NULL 
                        THEN JULIANDAY(tk.completed_at) - JULIANDAY(tk.created_at) END) as avg_completion_time
                FROM users u
                JOIN user_teams ut ON u.id = ut.user_id
                JOIN teams t ON ut.team_id = t.id
                LEFT JOIN tasks tk ON u.id = tk.assigned_to AND DATE(tk.created_at) BETWEEN ? AND ?
                WHERE t.id = ? OR ? IS NULL
                GROUP BY u.id, u.username
                ORDER BY tasks_completed DESC
            """, [start_date, end_date, team_id, team_id])
            
            productivity_stats = cursor.fetchall()
            
            # File Management Report
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_files,
                    COUNT(CASE WHEN file_type = 'document' THEN 1 END) as documents,
                    COUNT(CASE WHEN file_type = 'image' THEN 1 END) as images,
                    COUNT(CASE WHEN file_type = 'video' THEN 1 END) as videos,
                    SUM(file_size) as total_size
                FROM task_attachments ta
                JOIN tasks tk ON ta.task_id = tk.id
                JOIN users u ON tk.assigned_to = u.id
                JOIN user_teams ut ON u.id = ut.user_id
                JOIN teams t ON ut.team_id = t.id
                WHERE DATE(ta.created_at) BETWEEN ? AND ?
                {team_filter}
            """, [start_date, end_date] + team_params)
            
            file_stats = cursor.fetchone()
            
            # Project Timeline Tracking
            cursor.execute(f"""
                SELECT 
                    tk.title,
                    tk.status,
                    tk.priority,
                    u.username as assigned_to,
                    tk.due_date,
                    tk.completed_at,
                    CASE WHEN tk.completed_at IS NOT NULL AND tk.due_date IS NOT NULL
                        THEN JULIANDAY(tk.completed_at) - JULIANDAY(tk.due_date)
                        ELSE NULL END as days_overdue
                FROM tasks tk
                JOIN users u ON tk.assigned_to = u.id
                JOIN user_teams ut ON u.id = ut.user_id
                JOIN teams t ON ut.team_id = t.id
                WHERE DATE(tk.created_at) BETWEEN ? AND ?
                {team_filter}
                ORDER BY tk.due_date ASC
            """, [start_date, end_date] + team_params)
            
            project_timeline = cursor.fetchall()
            
            # Create report data
            report_data = {
                'report_type': 'productions',
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'task_completion': {
                    'total_tasks': task_stats[0] if task_stats else 0,
                    'completed_tasks': task_stats[1] if task_stats else 0,
                    'pending_tasks': task_stats[2] if task_stats else 0,
                    'in_progress_tasks': task_stats[3] if task_stats else 0,
                    'completion_rate': round((task_stats[1] / task_stats[0] * 100) if task_stats and task_stats[0] > 0 else 0, 2),
                    'avg_completion_days': round(task_stats[4] if task_stats and task_stats[4] else 0, 2)
                },
                'file_management': {
                    'total_files': file_stats[0] if file_stats else 0,
                    'documents': file_stats[1] if file_stats else 0,
                    'images': file_stats[2] if file_stats else 0,
                    'videos': file_stats[3] if file_stats else 0,
                    'total_size_mb': round((file_stats[4] / (1024 * 1024)) if file_stats and file_stats[4] else 0, 2)
                },
                'productivity_metrics': [
                    {
                        'username': row[0],
                        'tasks_assigned': row[1],
                        'tasks_completed': row[2],
                        'completion_rate': round((row[2] / row[1] * 100) if row[1] > 0 else 0, 2),
                        'avg_completion_time': round(row[3] if row[3] else 0, 2)
                    } for row in productivity_stats
                ],
                'project_timeline': [
                    {
                        'title': row[0],
                        'status': row[1],
                        'priority': row[2],
                        'assigned_to': row[3],
                        'due_date': row[4],
                        'completed_at': row[5],
                        'days_overdue': round(row[6] if row[6] else 0, 2)
                    } for row in project_timeline
                ]
            }
            
            conn.close()
            return report_data
            
        except Exception as e:
            print(f"❌ Error generating productions reports: {e}")
            if conn:
                conn.close()
            return None
    
    def generate_team_member_reports(self, user_id, report_type='daily'):
        """Generate team member reports."""
        print(f"📊 Generating {report_type} report for user {user_id}...")
        
        conn = self.connect_db()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Get user information
            cursor.execute("SELECT username, email FROM users WHERE id = ?", (user_id,))
            user_info = cursor.fetchone()
            if not user_info:
                print(f"❌ User {user_id} not found")
                return None
            
            username, email = user_info
            
            # Get team information
            cursor.execute("""
                SELECT t.name FROM teams t
                JOIN user_teams ut ON t.id = ut.team_id
                WHERE ut.user_id = ?
            """, (user_id,))
            team_info = cursor.fetchone()
            team_name = team_info[0] if team_info else "No Team"
            team_id = team_info[1] if team_info else None
            
            # Set date range based on report type
            if report_type == 'daily':
                start_date = datetime.now().date()
                end_date = start_date
                date_field = 'DATE(created_at)'
                date_condition = f"{date_field} = ?"
                date_params = [start_date]
            elif report_type == 'weekly':
                today = datetime.now().date()
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
                date_field = 'DATE(created_at)'
                date_condition = f"{date_field} BETWEEN ? AND ?"
                date_params = [start_date, end_date]
            elif report_type == 'monthly':
                start_date = datetime.now().replace(day=1).date()
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1) - timedelta(days=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1) - timedelta(days=1)
                date_field = 'DATE(created_at)'
                date_condition = f"{date_field} BETWEEN ? AND ?"
                date_params = [start_date, end_date]
            else:
                print(f"❌ Invalid report type: {report_type}")
                return None
            
            # Get activities
            cursor.execute(f"""
                SELECT activity_type, description, created_at 
                FROM user_activities 
                WHERE user_id = ? AND {date_condition}
                ORDER BY created_at DESC
            """, [user_id] + date_params)
            activities = cursor.fetchall()
            
            # Get leads
            cursor.execute(f"""
                SELECT COUNT(*) FROM leads 
                WHERE created_by = ? AND {date_condition}
            """, [user_id] + date_params)
            leads_created = cursor.fetchone()[0]
            
            # Get tasks
            cursor.execute(f"""
                SELECT COUNT(*) FROM tasks 
                WHERE assigned_to = ? AND {date_condition}
            """, [user_id] + date_params)
            tasks_assigned = cursor.fetchone()[0]
            
            cursor.execute(f"""
                SELECT COUNT(*) FROM tasks 
                WHERE assigned_to = ? AND status = 'completed' AND {date_condition.replace('created_at', 'completed_at')}
            """, [user_id] + date_params)
            tasks_completed = cursor.fetchone()[0]
            
            # Get messages
            cursor.execute(f"""
                SELECT COUNT(*) FROM chat_messages 
                WHERE sender_id = ? AND {date_condition}
            """, [user_id] + date_params)
            messages_sent = cursor.fetchone()[0]
            
            # Calculate productivity score
            productivity_score = self.calculate_productivity_score(leads_created, tasks_completed, messages_sent)
            
            # Create report data based on actual table structure
            if report_type == 'daily':
                report_data = {
                    'user_id': user_id,
                    'team_id': team_id,
                    'report_date': start_date.isoformat(),
                    'leads_created': leads_created,
                    'leads_updated': 0,  # Not tracked in current system
                    'tasks_completed': tasks_completed,
                    'tasks_assigned': tasks_assigned,
                    'calls_made': len([a for a in activities if a[0] == 'call']),
                    'followups_added': len([a for a in activities if a[0] == 'followup']),
                    'messages_sent': messages_sent,
                    'messages_received': 0,  # Not tracked in current system
                    'mentions_count': 0,  # Not tracked in current system
                    'daily_goal': 10,  # Default goal
                    'goal_achievement': min(100, (leads_created + tasks_completed) * 10),
                    'notes': '',
                    'manager_notes': '',
                    'status': 'active'
                }
            elif report_type == 'weekly':
                report_data = {
                    'user_id': user_id,
                    'team_id': team_id,
                    'week_start': start_date.isoformat(),
                    'total_leads_created': leads_created,
                    'total_leads_updated': 0,
                    'total_tasks_completed': tasks_completed,
                    'total_tasks_assigned': tasks_assigned,
                    'total_calls_made': len([a for a in activities if a[0] == 'call']),
                    'total_followups_added': len([a for a in activities if a[0] == 'followup']),
                    'total_messages_sent': messages_sent,
                    'total_messages_received': 0,
                    'total_mentions_count': 0,
                    'total_active_time': len(activities) * 30,  # Estimate 30 min per activity
                    'total_break_time': 0,
                    'average_daily_active_time': len(activities) * 30 / 7,
                    'weekly_goal': 50,
                    'goal_achievement': min(100, (leads_created + tasks_completed) * 2),
                    'productivity_trend': 'stable',
                    'performance_rating': 'good' if productivity_score > 50 else 'needs_improvement',
                    'workload_distribution': 'balanced',
                    'peak_performance_day': 'monday',
                    'notes': '',
                    'manager_notes': '',
                    'status': 'active'
                }
            else:  # monthly
                report_data = {
                    'user_id': user_id,
                    'team_id': team_id,
                    'month_year': start_date.strftime('%Y-%m'),
                    'total_leads_created': leads_created,
                    'total_leads_updated': 0,
                    'total_tasks_completed': tasks_completed,
                    'total_tasks_assigned': tasks_assigned,
                    'total_calls_made': len([a for a in activities if a[0] == 'call']),
                    'total_followups_added': len([a for a in activities if a[0] == 'followup']),
                    'total_messages_sent': messages_sent,
                    'total_messages_received': 0,
                    'total_mentions_count': 0,
                    'total_active_time': len(activities) * 30,
                    'total_break_time': 0,
                    'average_daily_active_time': len(activities) * 30 / 30,
                    'monthly_goal': 200,
                    'goal_achievement': min(100, (leads_created + tasks_completed) * 0.5),
                    'team_rank': 1,
                    'team_performance_percentile': 75.0,
                    'improvement_from_last_month': 5.0,
                    'key_achievements': f'Created {leads_created} leads, completed {tasks_completed} tasks',
                    'areas_for_improvement': 'Continue maintaining high productivity',
                    'productivity_score': productivity_score,
                    'efficiency_rating': 'high' if productivity_score > 70 else 'medium',
                    'reliability_score': 85.0,
                    'notes': '',
                    'manager_notes': '',
                    'employee_self_assessment': 'Performing well',
                    'status': 'active'
                }
            
            conn.close()
            return report_data
            
        except Exception as e:
            print(f"❌ Error generating team member report: {e}")
            if conn:
                conn.close()
            return None
    
    def calculate_productivity_score(self, leads, tasks, messages):
        """Calculate productivity score."""
        score = (leads * 10) + (tasks * 5) + (messages * 1)
        return min(score, 100)
    
    def save_report(self, report_data, report_type):
        """Save report to database."""
        conn = self.connect_db()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Save to appropriate table
            if report_type in ['daily', 'weekly', 'monthly']:
                table_name = f'team_member_{report_type}_reports'
                
                # Check if report exists
                if report_type == 'daily':
                    date_field = 'report_date'
                    date_value = report_data['report_date']
                elif report_type == 'weekly':
                    date_field = 'week_start'
                    date_value = report_data['week_start']
                else:  # monthly
                    date_field = 'month_year'
                    date_value = report_data['month_year']
                
                cursor.execute(f"""
                    SELECT id FROM {table_name} 
                    WHERE user_id = ? AND {date_field} = ?
                """, (report_data['user_id'], date_value))
                
                existing_report = cursor.fetchone()
                
                if existing_report:
                    # Update existing report - use actual column names
                    if report_type == 'daily':
                        cursor.execute(f"""
                            UPDATE {table_name} SET
                            leads_created = ?,
                            leads_updated = ?,
                            tasks_completed = ?,
                            tasks_assigned = ?,
                            calls_made = ?,
                            followups_added = ?,
                            messages_sent = ?,
                            messages_received = ?,
                            mentions_count = ?,
                            daily_goal = ?,
                            goal_achievement = ?,
                            notes = ?,
                            manager_notes = ?,
                            status = ?,
                            updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ? AND {date_field} = ?
                        """, (
                            report_data['leads_created'],
                            report_data['leads_updated'],
                            report_data['tasks_completed'],
                            report_data['tasks_assigned'],
                            report_data['calls_made'],
                            report_data['followups_added'],
                            report_data['messages_sent'],
                            report_data['messages_received'],
                            report_data['mentions_count'],
                            report_data['daily_goal'],
                            report_data['goal_achievement'],
                            report_data['notes'],
                            report_data['manager_notes'],
                            report_data['status'],
                            report_data['user_id'],
                            date_value
                        ))
                    elif report_type == 'weekly':
                        cursor.execute(f"""
                            UPDATE {table_name} SET
                            total_leads_created = ?,
                            total_leads_updated = ?,
                            total_tasks_completed = ?,
                            total_tasks_assigned = ?,
                            total_calls_made = ?,
                            total_followups_added = ?,
                            total_messages_sent = ?,
                            total_messages_received = ?,
                            total_mentions_count = ?,
                            total_active_time = ?,
                            total_break_time = ?,
                            average_daily_active_time = ?,
                            weekly_goal = ?,
                            goal_achievement = ?,
                            productivity_trend = ?,
                            performance_rating = ?,
                            workload_distribution = ?,
                            peak_performance_day = ?,
                            notes = ?,
                            manager_notes = ?,
                            status = ?,
                            updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ? AND {date_field} = ?
                        """, (
                            report_data['total_leads_created'],
                            report_data['total_leads_updated'],
                            report_data['total_tasks_completed'],
                            report_data['total_tasks_assigned'],
                            report_data['total_calls_made'],
                            report_data['total_followups_added'],
                            report_data['total_messages_sent'],
                            report_data['total_messages_received'],
                            report_data['total_mentions_count'],
                            report_data['total_active_time'],
                            report_data['total_break_time'],
                            report_data['average_daily_active_time'],
                            report_data['weekly_goal'],
                            report_data['goal_achievement'],
                            report_data['productivity_trend'],
                            report_data['performance_rating'],
                            report_data['workload_distribution'],
                            report_data['peak_performance_day'],
                            report_data['notes'],
                            report_data['manager_notes'],
                            report_data['status'],
                            report_data['user_id'],
                            date_value
                        ))
                    else:  # monthly
                        cursor.execute(f"""
                            UPDATE {table_name} SET
                            total_leads_created = ?,
                            total_leads_updated = ?,
                            total_tasks_completed = ?,
                            total_tasks_assigned = ?,
                            total_calls_made = ?,
                            total_followups_added = ?,
                            total_messages_sent = ?,
                            total_messages_received = ?,
                            total_mentions_count = ?,
                            total_active_time = ?,
                            total_break_time = ?,
                            average_daily_active_time = ?,
                            monthly_goal = ?,
                            goal_achievement = ?,
                            team_rank = ?,
                            team_performance_percentile = ?,
                            improvement_from_last_month = ?,
                            key_achievements = ?,
                            areas_for_improvement = ?,
                            productivity_score = ?,
                            efficiency_rating = ?,
                            reliability_score = ?,
                            notes = ?,
                            manager_notes = ?,
                            employee_self_assessment = ?,
                            status = ?,
                            updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ? AND {date_field} = ?
                        """, (
                            report_data['total_leads_created'],
                            report_data['total_leads_updated'],
                            report_data['total_tasks_completed'],
                            report_data['total_tasks_assigned'],
                            report_data['total_calls_made'],
                            report_data['total_followups_added'],
                            report_data['total_messages_sent'],
                            report_data['total_messages_received'],
                            report_data['total_mentions_count'],
                            report_data['total_active_time'],
                            report_data['total_break_time'],
                            report_data['average_daily_active_time'],
                            report_data['monthly_goal'],
                            report_data['goal_achievement'],
                            report_data['team_rank'],
                            report_data['team_performance_percentile'],
                            report_data['improvement_from_last_month'],
                            report_data['key_achievements'],
                            report_data['areas_for_improvement'],
                            report_data['productivity_score'],
                            report_data['efficiency_rating'],
                            report_data['reliability_score'],
                            report_data['notes'],
                            report_data['manager_notes'],
                            report_data['employee_self_assessment'],
                            report_data['status'],
                            report_data['user_id'],
                            date_value
                        ))
                else:
                    # Insert new report - use actual column names
                    if report_type == 'daily':
                        cursor.execute(f"""
                            INSERT INTO {table_name} (
                                user_id, team_id, {date_field}, leads_created, leads_updated,
                                tasks_completed, tasks_assigned, calls_made, followups_added,
                                messages_sent, messages_received, mentions_count, daily_goal,
                                goal_achievement, notes, manager_notes, status, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (
                            report_data['user_id'],
                            report_data['team_id'],
                            date_value,
                            report_data['leads_created'],
                            report_data['leads_updated'],
                            report_data['tasks_completed'],
                            report_data['tasks_assigned'],
                            report_data['calls_made'],
                            report_data['followups_added'],
                            report_data['messages_sent'],
                            report_data['messages_received'],
                            report_data['mentions_count'],
                            report_data['daily_goal'],
                            report_data['goal_achievement'],
                            report_data['notes'],
                            report_data['manager_notes'],
                            report_data['status']
                        ))
                    elif report_type == 'weekly':
                        cursor.execute(f"""
                            INSERT INTO {table_name} (
                                user_id, team_id, {date_field}, total_leads_created, total_leads_updated,
                                total_tasks_completed, total_tasks_assigned, total_calls_made, total_followups_added,
                                total_messages_sent, total_messages_received, total_mentions_count,
                                total_active_time, total_break_time, average_daily_active_time, weekly_goal,
                                goal_achievement, productivity_trend, performance_rating, workload_distribution,
                                peak_performance_day, notes, manager_notes, status, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (
                            report_data['user_id'],
                            report_data['team_id'],
                            date_value,
                            report_data['total_leads_created'],
                            report_data['total_leads_updated'],
                            report_data['total_tasks_completed'],
                            report_data['total_tasks_assigned'],
                            report_data['total_calls_made'],
                            report_data['total_followups_added'],
                            report_data['total_messages_sent'],
                            report_data['total_messages_received'],
                            report_data['total_mentions_count'],
                            report_data['total_active_time'],
                            report_data['total_break_time'],
                            report_data['average_daily_active_time'],
                            report_data['weekly_goal'],
                            report_data['goal_achievement'],
                            report_data['productivity_trend'],
                            report_data['performance_rating'],
                            report_data['workload_distribution'],
                            report_data['peak_performance_day'],
                            report_data['notes'],
                            report_data['manager_notes'],
                            report_data['status']
                        ))
                    else:  # monthly
                        cursor.execute(f"""
                            INSERT INTO {table_name} (
                                user_id, team_id, {date_field}, total_leads_created, total_leads_updated,
                                total_tasks_completed, total_tasks_assigned, total_calls_made, total_followups_added,
                                total_messages_sent, total_messages_received, total_mentions_count,
                                total_active_time, total_break_time, average_daily_active_time, monthly_goal,
                                goal_achievement, team_rank, team_performance_percentile, improvement_from_last_month,
                                key_achievements, areas_for_improvement, productivity_score, efficiency_rating,
                                reliability_score, notes, manager_notes, employee_self_assessment, status,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (
                            report_data['user_id'],
                            report_data['team_id'],
                            date_value,
                            report_data['total_leads_created'],
                            report_data['total_leads_updated'],
                            report_data['total_tasks_completed'],
                            report_data['total_tasks_assigned'],
                            report_data['total_calls_made'],
                            report_data['total_followups_added'],
                            report_data['total_messages_sent'],
                            report_data['total_messages_received'],
                            report_data['total_mentions_count'],
                            report_data['total_active_time'],
                            report_data['total_break_time'],
                            report_data['average_daily_active_time'],
                            report_data['monthly_goal'],
                            report_data['goal_achievement'],
                            report_data['team_rank'],
                            report_data['team_performance_percentile'],
                            report_data['improvement_from_last_month'],
                            report_data['key_achievements'],
                            report_data['areas_for_improvement'],
                            report_data['productivity_score'],
                            report_data['efficiency_rating'],
                            report_data['reliability_score'],
                            report_data['notes'],
                            report_data['manager_notes'],
                            report_data['employee_self_assessment'],
                            report_data['status']
                        ))
                
                conn.commit()
                print(f"✅ Saved {report_type} report for user {report_data['user_id']}")
                return True
            
        except Exception as e:
            print(f"❌ Error saving report: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

def generate_all_reports():
    """Generate all reports for all users."""
    print("🚀 Starting comprehensive report generation...")
    
    generator = ReportGenerator()
    
    # Get all active users
    conn = generator.connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE is_active = 1")
        users = cursor.fetchall()
        
        print(f"📊 Found {len(users)} active users")
        
        # Generate team member reports for each user
        for user_id, username in users:
            print(f"\n👤 Generating reports for {username}...")
            
            # Generate daily, weekly, and monthly reports
            for report_type in ['daily', 'weekly', 'monthly']:
                report_data = generator.generate_team_member_reports(user_id, report_type)
                if report_data:
                    generator.save_report(report_data, report_type)
        
        # Generate team reports
        cursor.execute("SELECT id, name FROM teams")
        teams = cursor.fetchall()
        
        for team_id, team_name in teams:
            print(f"\n🏢 Generating team reports for {team_name}...")
            
            # Generate marketing reports
            marketing_report = generator.generate_marketing_reports(team_id)
            if marketing_report:
                print(f"✅ Marketing report generated for {team_name}")
            
            # Generate productions reports
            productions_report = generator.generate_productions_reports(team_id)
            if productions_report:
                print(f"✅ Productions report generated for {team_name}")
        
        conn.close()
        print(f"\n🎉 Successfully generated reports for {len(users)} users and {len(teams)} teams")
        return True
        
    except Exception as e:
        print(f"❌ Error generating reports: {e}")
        return False

if __name__ == "__main__":
    generate_all_reports() 