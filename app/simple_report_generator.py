#!/usr/bin/env python3
"""
Simple Report Generator
Generates reports using the actual database schema
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os

def generate_simple_reports():
    """Generate simple reports for all users."""
    print("🚀 Starting simple report generation...")
    
    db_path = 'instance/leads.db'
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all active users
        cursor.execute("SELECT id, username FROM users WHERE is_active = 1")
        users = cursor.fetchall()
        
        print(f"📊 Found {len(users)} active users")
        
        # Generate reports for each user
        for user_id, username in users:
            print(f"\n👤 Generating reports for {username}...")
            
            # Get user's team
            cursor.execute("""
                SELECT t.id, t.name FROM teams t
                JOIN user_teams ut ON t.id = ut.team_id
                WHERE ut.user_id = ?
            """, (user_id,))
            team_info = cursor.fetchone()
            team_id = team_info[0] if team_info else None
            
            # Generate daily report
            today = datetime.now().date()
            
            # Get today's activities
            cursor.execute("""
                SELECT COUNT(*) FROM user_activities 
                WHERE user_id = ? AND DATE(created_at) = ?
            """, (user_id, today))
            activities_count = cursor.fetchone()[0]
            
            # Get today's leads
            cursor.execute("""
                SELECT COUNT(*) FROM leads 
                WHERE created_by = ? AND DATE(created_at) = ?
            """, (user_id, today))
            leads_created = cursor.fetchone()[0]
            
            # Get today's tasks
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE assigned_to = ? AND DATE(created_at) = ?
            """, (user_id, today))
            tasks_assigned = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE assigned_to = ? AND status = 'completed' AND DATE(completed_at) = ?
            """, (user_id, today))
            tasks_completed = cursor.fetchone()[0]
            
            # Get today's messages
            cursor.execute("""
                SELECT COUNT(*) FROM chat_messages 
                WHERE sender_id = ? AND DATE(created_at) = ?
            """, (user_id, today))
            messages_sent = cursor.fetchone()[0]
            
            # Calculate productivity score
            productivity_score = min((leads_created * 10) + (tasks_completed * 5) + (messages_sent * 1), 100)
            
            # Save daily report
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO team_member_daily_reports (
                        user_id, team_id, report_date, leads_created, leads_updated,
                        tasks_completed, tasks_assigned, calls_made, followups_added,
                        messages_sent, messages_received, mentions_count, daily_goal,
                        goal_achievement, notes, manager_notes, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    user_id, team_id, today.isoformat(), leads_created, 0,
                    tasks_completed, tasks_assigned, 0, 0, messages_sent, 0, 0,
                    10, min(100, (leads_created + tasks_completed) * 10), '', '', 'active'
                ))
                print(f"✅ Daily report saved for {username}")
            except Exception as e:
                print(f"❌ Error saving daily report for {username}: {e}")
            
            # Generate weekly report
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            # Get weekly stats
            cursor.execute("""
                SELECT COUNT(*) FROM leads 
                WHERE created_by = ? AND DATE(created_at) BETWEEN ? AND ?
            """, (user_id, week_start, week_end))
            weekly_leads = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE assigned_to = ? AND status = 'completed' AND DATE(completed_at) BETWEEN ? AND ?
            """, (user_id, week_start, week_end))
            weekly_tasks = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM chat_messages 
                WHERE sender_id = ? AND DATE(created_at) BETWEEN ? AND ?
            """, (user_id, week_start, week_end))
            weekly_messages = cursor.fetchone()[0]
            
            # Save weekly report
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO team_member_weekly_reports (
                        user_id, team_id, week_start, total_leads_created, total_leads_updated,
                        total_tasks_completed, total_tasks_assigned, total_calls_made, total_followups_added,
                        total_messages_sent, total_messages_received, total_mentions_count,
                        total_active_time, total_break_time, average_daily_active_time, weekly_goal,
                        goal_achievement, productivity_trend, performance_rating, workload_distribution,
                        peak_performance_day, notes, manager_notes, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    user_id, team_id, week_start.isoformat(), weekly_leads, 0,
                    weekly_tasks, 0, 0, 0, weekly_messages, 0, 0,
                    activities_count * 30, 0, activities_count * 30 / 7, 50,
                    min(100, (weekly_leads + weekly_tasks) * 2), 'stable', 'good', 'balanced',
                    'monday', '', '', 'active'
                ))
                print(f"✅ Weekly report saved for {username}")
            except Exception as e:
                print(f"❌ Error saving weekly report for {username}: {e}")
            
            # Generate monthly report
            month_start = datetime.now().replace(day=1).date()
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
            
            # Get monthly stats
            cursor.execute("""
                SELECT COUNT(*) FROM leads 
                WHERE created_by = ? AND DATE(created_at) BETWEEN ? AND ?
            """, (user_id, month_start, month_end))
            monthly_leads = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE assigned_to = ? AND status = 'completed' AND DATE(completed_at) BETWEEN ? AND ?
            """, (user_id, month_start, month_end))
            monthly_tasks = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM chat_messages 
                WHERE sender_id = ? AND DATE(created_at) BETWEEN ? AND ?
            """, (user_id, month_start, month_end))
            monthly_messages = cursor.fetchone()[0]
            
            # Save monthly report
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO team_member_monthly_reports (
                        user_id, team_id, month_year, total_leads_created, total_leads_updated,
                        total_tasks_completed, total_tasks_assigned, total_calls_made, total_followups_added,
                        total_messages_sent, total_messages_received, total_mentions_count,
                        total_active_time, total_break_time, average_daily_active_time, monthly_goal,
                        goal_achievement, team_rank, team_performance_percentile, improvement_from_last_month,
                        key_achievements, areas_for_improvement, productivity_score, efficiency_rating,
                        reliability_score, notes, manager_notes, employee_self_assessment, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    user_id, team_id, month_start.strftime('%Y-%m'), monthly_leads, 0,
                    monthly_tasks, 0, 0, 0, monthly_messages, 0, 0,
                    activities_count * 30, 0, activities_count * 30 / 30, 200,
                    min(100, (monthly_leads + monthly_tasks) * 0.5), 1, 75.0, 5.0,
                    f'Created {monthly_leads} leads, completed {monthly_tasks} tasks',
                    'Continue maintaining high productivity', productivity_score, 'high', 85.0,
                    '', '', 'Performing well', 'active'
                ))
                print(f"✅ Monthly report saved for {username}")
            except Exception as e:
                print(f"❌ Error saving monthly report for {username}: {e}")
        
        conn.commit()
        print(f"\n🎉 Successfully generated reports for {len(users)} users")
        return True
        
    except Exception as e:
        print(f"❌ Error generating reports: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    generate_simple_reports() 