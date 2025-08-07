#!/usr/bin/env python3
"""
Advanced Team Management Features
Provides sophisticated team management capabilities including workload distribution, performance tracking, and team analytics
"""

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

class AdvancedTeamManagement:
    """Advanced team management features."""
    
    def __init__(self, db_path='instance/leads.db'):
        self.db_path = db_path
        self.setup_advanced_tables()
    
    def setup_advanced_tables(self):
        """Setup advanced team management tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Team performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                metric_date DATE,
                total_leads INTEGER DEFAULT 0,
                total_tasks INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                average_productivity REAL DEFAULT 0,
                team_efficiency REAL DEFAULT 0,
                workload_distribution_score REAL DEFAULT 0,
                collaboration_score REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Workload distribution table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workload_distribution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                user_id INTEGER,
                workload_date DATE,
                assigned_leads INTEGER DEFAULT 0,
                completed_tasks INTEGER DEFAULT 0,
                pending_tasks INTEGER DEFAULT 0,
                workload_score REAL DEFAULT 0,
                efficiency_rating REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Team collaboration metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_collaboration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                collaboration_date DATE,
                messages_sent INTEGER DEFAULT 0,
                files_shared INTEGER DEFAULT 0,
                meetings_attended INTEGER DEFAULT 0,
                collaboration_score REAL DEFAULT 0,
                team_cohesion REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                goal_type TEXT,
                target_value REAL,
                current_value REAL DEFAULT 0,
                start_date DATE,
                end_date DATE,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Team analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                analytics_date DATE,
                lead_conversion_rate REAL DEFAULT 0,
                task_completion_rate REAL DEFAULT 0,
                response_time_avg REAL DEFAULT 0,
                customer_satisfaction REAL DEFAULT 0,
                team_growth_rate REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def calculate_workload_distribution(self, team_id, date=None):
        """Calculate optimal workload distribution for team."""
        if date is None:
            date = datetime.now().date()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get team members and their current workload
        cursor.execute("""
            SELECT u.id, u.username, 
                   COALESCE(wd.assigned_leads, 0) as current_leads,
                   COALESCE(wd.completed_tasks, 0) as completed_tasks,
                   COALESCE(wd.pending_tasks, 0) as pending_tasks,
                   COALESCE(wd.efficiency_rating, 0) as efficiency
            FROM users u
            JOIN user_teams ut ON u.id = ut.user_id
            LEFT JOIN workload_distribution wd ON u.id = wd.user_id AND wd.workload_date = ?
            WHERE ut.team_id = ?
        """, (date.isoformat(), team_id))
        
        team_members = cursor.fetchall()
        
        if not team_members:
            return {}
        
        # Calculate total team capacity and current workload
        total_capacity = sum(member[5] for member in team_members)  # efficiency ratings
        current_workload = sum(member[2] + member[4] for member in team_members)  # leads + pending tasks
        
        # Get available work (new leads, tasks)
        cursor.execute("""
            SELECT COUNT(*) FROM leads 
            WHERE team_id = ? AND created_at >= ? AND status = 'new'
        """, (team_id, date.isoformat()))
        
        new_leads = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM tasks 
            WHERE team_id = ? AND created_at >= ? AND status = 'pending'
        """, (team_id, date.isoformat()))
        
        new_tasks = cursor.fetchone()[0]
        
        total_available_work = new_leads + new_tasks
        
        # Calculate optimal distribution
        distribution = {}
        total_assigned = 0
        
        for member in team_members:
            user_id, username, current_leads, completed_tasks, pending_tasks, efficiency = member
            
            # Calculate member's capacity ratio
            capacity_ratio = efficiency / total_capacity if total_capacity > 0 else 1 / len(team_members)
            
            # Calculate optimal workload for this member
            optimal_workload = int(total_available_work * capacity_ratio)
            
            # Ensure minimum workload
            optimal_workload = max(optimal_workload, 1)
            
            distribution[user_id] = {
                'username': username,
                'current_workload': current_leads + pending_tasks,
                'optimal_workload': optimal_workload,
                'efficiency_rating': efficiency,
                'capacity_ratio': capacity_ratio,
                'workload_balance': optimal_workload - (current_leads + pending_tasks),
                'recommended_leads': max(0, optimal_workload - pending_tasks),
                'recommended_tasks': max(0, optimal_workload - current_leads)
            }
            
            total_assigned += optimal_workload
        
        conn.close()
        
        return {
            'team_id': team_id,
            'date': date.isoformat(),
            'total_available_work': total_available_work,
            'total_assigned': total_assigned,
            'distribution': distribution,
            'team_efficiency': total_capacity / len(team_members) if team_members else 0
        }
    
    def track_performance_metrics(self, team_id, date=None):
        """Track comprehensive performance metrics for team."""
        if date is None:
            date = datetime.now().date()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get team performance data
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT l.id) as total_leads,
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT cm.id) as total_messages,
                AVG(dr.productivity_score) as avg_productivity,
                AVG(wd.efficiency_rating) as avg_efficiency
            FROM teams tm
            LEFT JOIN leads l ON tm.id = l.team_id AND DATE(l.created_at) = ?
            LEFT JOIN tasks t ON tm.id = t.team_id AND DATE(t.created_at) = ?
            LEFT JOIN chat_messages cm ON tm.id = cm.team_id AND DATE(cm.created_at) = ?
            LEFT JOIN team_member_daily_reports dr ON tm.id = dr.team_id AND dr.report_date = ?
            LEFT JOIN workload_distribution wd ON tm.id = wd.team_id AND wd.workload_date = ?
            WHERE tm.id = ?
        """, (date.isoformat(), date.isoformat(), date.isoformat(), date.isoformat(), date.isoformat(), team_id))
        
        result = cursor.fetchone()
        
        if result:
            total_leads, total_tasks, total_messages, avg_productivity, avg_efficiency = result
            
            # Calculate team efficiency score
            team_efficiency = self.calculate_team_efficiency(team_id, date)
            
            # Calculate workload distribution score
            workload_score = self.calculate_workload_distribution_score(team_id, date)
            
            # Calculate collaboration score
            collaboration_score = self.calculate_collaboration_score(team_id, date)
            
            # Insert or update performance metrics
            cursor.execute("""
                INSERT OR REPLACE INTO team_performance_metrics 
                (team_id, metric_date, total_leads, total_tasks, total_messages, 
                 average_productivity, team_efficiency, workload_distribution_score, collaboration_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (team_id, date.isoformat(), total_leads or 0, total_tasks or 0, total_messages or 0,
                  avg_productivity or 0, team_efficiency, workload_score, collaboration_score))
            
            conn.commit()
        
        conn.close()
        
        return {
            'team_id': team_id,
            'date': date.isoformat(),
            'total_leads': total_leads or 0,
            'total_tasks': total_tasks or 0,
            'total_messages': total_messages or 0,
            'average_productivity': avg_productivity or 0,
            'team_efficiency': team_efficiency,
            'workload_distribution_score': workload_score,
            'collaboration_score': collaboration_score
        }
    
    def calculate_team_efficiency(self, team_id, date):
        """Calculate team efficiency score."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get team member productivity scores
        cursor.execute("""
            SELECT dr.productivity_score
            FROM team_member_daily_reports dr
            WHERE dr.team_id = ? AND dr.report_date = ?
        """, (team_id, date.isoformat()))
        
        productivity_scores = [row[0] for row in cursor.fetchall() if row[0] is not None]
        
        conn.close()
        
        if not productivity_scores:
            return 0
        
        # Calculate efficiency based on average productivity and consistency
        avg_productivity = statistics.mean(productivity_scores)
        consistency = 1 - statistics.stdev(productivity_scores) / 100 if len(productivity_scores) > 1 else 1
        
        return avg_productivity * consistency
    
    def calculate_workload_distribution_score(self, team_id, date):
        """Calculate workload distribution score."""
        workload_data = self.calculate_workload_distribution(team_id, date)
        
        if not workload_data['distribution']:
            return 0
        
        # Calculate how evenly work is distributed
        workloads = [member['current_workload'] for member in workload_data['distribution'].values()]
        
        if not workloads:
            return 0
        
        avg_workload = statistics.mean(workloads)
        if avg_workload == 0:
            return 100  # Perfect distribution if no work
        
        # Calculate coefficient of variation (lower is better)
        std_dev = statistics.stdev(workloads) if len(workloads) > 1 else 0
        cv = std_dev / avg_workload if avg_workload > 0 else 0
        
        # Convert to score (0-100, higher is better)
        distribution_score = max(0, 100 - (cv * 100))
        
        return distribution_score
    
    def calculate_collaboration_score(self, team_id, date):
        """Calculate team collaboration score."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get collaboration metrics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT cm.id) as messages,
                COUNT(DISTINCT cm.user_id) as active_members,
                AVG(CASE WHEN cm.reply_to_id IS NOT NULL THEN 1 ELSE 0 END) as reply_rate
            FROM chat_messages cm
            WHERE cm.team_id = ? AND DATE(cm.created_at) = ?
        """, (team_id, date.isoformat()))
        
        result = cursor.fetchone()
        
        if not result or result[0] == 0:
            conn.close()
            return 0
        
        messages, active_members, reply_rate = result
        
        # Get team size
        cursor.execute("""
            SELECT COUNT(*) FROM user_teams WHERE team_id = ?
        """, (team_id,))
        
        team_size = cursor.fetchone()[0]
        
        conn.close()
        
        if team_size == 0:
            return 0
        
        # Calculate collaboration score components
        participation_rate = active_members / team_size if team_size > 0 else 0
        engagement_rate = messages / (active_members * 10) if active_members > 0 else 0  # 10 messages per active member is good
        interaction_quality = reply_rate or 0
        
        # Weighted average
        collaboration_score = (
            participation_rate * 0.4 +
            min(engagement_rate, 1) * 0.4 +
            interaction_quality * 0.2
        ) * 100
        
        return min(collaboration_score, 100)
    
    def set_performance_goals(self, team_id, goals):
        """Set performance goals for team."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for goal in goals:
            cursor.execute("""
                INSERT INTO performance_goals 
                (team_id, goal_type, target_value, start_date, end_date)
                VALUES (?, ?, ?, ?, ?)
            """, (team_id, goal['type'], goal['target'], goal['start_date'], goal['end_date']))
        
        conn.commit()
        conn.close()
    
    def track_goal_progress(self, team_id):
        """Track progress towards performance goals."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get active goals
        cursor.execute("""
            SELECT id, goal_type, target_value, start_date, end_date, current_value
            FROM performance_goals
            WHERE team_id = ? AND status = 'active'
        """, (team_id,))
        
        goals = cursor.fetchall()
        
        progress_data = {}
        
        for goal in goals:
            goal_id, goal_type, target_value, start_date, end_date, current_value = goal
            
            # Calculate current progress based on goal type
            if goal_type == 'leads':
                cursor.execute("""
                    SELECT COUNT(*) FROM leads 
                    WHERE team_id = ? AND created_at BETWEEN ? AND ?
                """, (team_id, start_date, end_date))
                current_value = cursor.fetchone()[0]
            
            elif goal_type == 'tasks':
                cursor.execute("""
                    SELECT COUNT(*) FROM tasks 
                    WHERE team_id = ? AND status = 'completed' AND completed_at BETWEEN ? AND ?
                """, (team_id, start_date, end_date))
                current_value = cursor.fetchone()[0]
            
            elif goal_type == 'productivity':
                cursor.execute("""
                    SELECT AVG(productivity_score) FROM team_member_daily_reports
                    WHERE team_id = ? AND report_date BETWEEN ? AND ?
                """, (team_id, start_date, end_date))
                result = cursor.fetchone()
                current_value = result[0] if result[0] else 0
            
            # Update current value
            cursor.execute("""
                UPDATE performance_goals 
                SET current_value = ? WHERE id = ?
            """, (current_value, goal_id))
            
            # Calculate progress percentage
            progress_percentage = (current_value / target_value * 100) if target_value > 0 else 0
            
            progress_data[goal_id] = {
                'goal_type': goal_type,
                'target_value': target_value,
                'current_value': current_value,
                'progress_percentage': progress_percentage,
                'start_date': start_date,
                'end_date': end_date,
                'status': 'on_track' if progress_percentage >= 80 else 'at_risk' if progress_percentage >= 50 else 'behind'
            }
        
        conn.commit()
        conn.close()
        
        return progress_data
    
    def generate_team_analytics(self, team_id, date_range=30):
        """Generate comprehensive team analytics."""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=date_range)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get analytics data
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(DISTINCT l.id) as leads,
                COUNT(DISTINCT t.id) as tasks,
                COUNT(DISTINCT cm.id) as messages,
                AVG(dr.productivity_score) as productivity
            FROM teams tm
            LEFT JOIN leads l ON tm.id = l.team_id AND l.created_at BETWEEN ? AND ?
            LEFT JOIN tasks t ON tm.id = t.team_id AND t.created_at BETWEEN ? AND ?
            LEFT JOIN chat_messages cm ON tm.id = cm.team_id AND cm.created_at BETWEEN ? AND ?
            LEFT JOIN team_member_daily_reports dr ON tm.id = dr.team_id AND dr.report_date BETWEEN ? AND ?
            WHERE tm.id = ?
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (start_date.isoformat(), end_date.isoformat(), 
              start_date.isoformat(), end_date.isoformat(),
              start_date.isoformat(), end_date.isoformat(),
              start_date.isoformat(), end_date.isoformat(), team_id))
        
        analytics_data = cursor.fetchall()
        
        # Calculate trends
        trends = self.calculate_trends(analytics_data)
        
        # Get team composition
        cursor.execute("""
            SELECT u.username, u.role, COUNT(dr.id) as active_days
            FROM users u
            JOIN user_teams ut ON u.id = ut.user_id
            LEFT JOIN team_member_daily_reports dr ON u.id = dr.user_id AND dr.report_date BETWEEN ? AND ?
            WHERE ut.team_id = ?
            GROUP BY u.id, u.username, u.role
        """, (start_date.isoformat(), end_date.isoformat(), team_id))
        
        team_composition = cursor.fetchall()
        
        conn.close()
        
        return {
            'team_id': team_id,
            'date_range': date_range,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'analytics_data': analytics_data,
            'trends': trends,
            'team_composition': team_composition,
            'summary': self.generate_analytics_summary(analytics_data, trends)
        }
    
    def calculate_trends(self, analytics_data):
        """Calculate trends from analytics data."""
        if len(analytics_data) < 2:
            return {}
        
        # Extract metrics
        leads = [row[1] for row in analytics_data]
        tasks = [row[2] for row in analytics_data]
        messages = [row[3] for row in analytics_data]
        productivity = [row[4] for row in analytics_data if row[4] is not None]
        
        # Calculate trends (simple linear regression)
        def calculate_trend(values):
            if len(values) < 2:
                return 0
            n = len(values)
            x = list(range(n))
            y = values
            
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            return slope
        
        return {
            'leads_trend': calculate_trend(leads),
            'tasks_trend': calculate_trend(tasks),
            'messages_trend': calculate_trend(messages),
            'productivity_trend': calculate_trend(productivity) if productivity else 0
        }
    
    def generate_analytics_summary(self, analytics_data, trends):
        """Generate summary of analytics data."""
        if not analytics_data:
            return {}
        
        # Calculate averages
        total_leads = sum(row[1] for row in analytics_data)
        total_tasks = sum(row[2] for row in analytics_data)
        total_messages = sum(row[3] for row in analytics_data)
        productivity_scores = [row[4] for row in analytics_data if row[4] is not None]
        
        avg_productivity = statistics.mean(productivity_scores) if productivity_scores else 0
        
        # Determine trend direction
        def get_trend_direction(trend_value):
            if trend_value > 0.1:
                return 'increasing'
            elif trend_value < -0.1:
                return 'decreasing'
            else:
                return 'stable'
        
        return {
            'total_leads': total_leads,
            'total_tasks': total_tasks,
            'total_messages': total_messages,
            'average_productivity': avg_productivity,
            'leads_trend': get_trend_direction(trends['leads_trend']),
            'tasks_trend': get_trend_direction(trends['tasks_trend']),
            'messages_trend': get_trend_direction(trends['messages_trend']),
            'productivity_trend': get_trend_direction(trends['productivity_trend']),
            'performance_rating': self.calculate_performance_rating(avg_productivity, trends)
        }
    
    def calculate_performance_rating(self, avg_productivity, trends):
        """Calculate overall performance rating."""
        # Base rating on productivity
        base_rating = min(avg_productivity / 10, 1) * 100
        
        # Adjust based on trends
        trend_adjustment = 0
        if trends['productivity_trend'] > 0:
            trend_adjustment += 10
        elif trends['productivity_trend'] < 0:
            trend_adjustment -= 10
        
        if trends['leads_trend'] > 0:
            trend_adjustment += 5
        elif trends['leads_trend'] < 0:
            trend_adjustment -= 5
        
        final_rating = max(0, min(100, base_rating + trend_adjustment))
        
        if final_rating >= 90:
            return 'Excellent'
        elif final_rating >= 80:
            return 'Good'
        elif final_rating >= 70:
            return 'Average'
        elif final_rating >= 60:
            return 'Below Average'
        else:
            return 'Poor'
    
    def get_team_recommendations(self, team_id):
        """Generate recommendations for team improvement."""
        analytics = self.generate_team_analytics(team_id, 30)
        workload = self.calculate_workload_distribution(team_id)
        goals = self.track_goal_progress(team_id)
        
        recommendations = []
        
        # Analyze productivity trends
        if analytics['trends']['productivity_trend'] < 0:
            recommendations.append({
                'type': 'productivity',
                'priority': 'high',
                'title': 'Productivity Declining',
                'description': 'Team productivity has been declining. Consider reviewing workload distribution and providing additional support.',
                'action_items': [
                    'Review individual performance metrics',
                    'Identify bottlenecks in workflow',
                    'Provide additional training if needed',
                    'Consider workload redistribution'
                ]
            })
        
        # Analyze workload distribution
        if workload.get('distribution'):
            unbalanced_members = [
                member for member in workload['distribution'].values()
                if abs(member['workload_balance']) > 5
            ]
            
            if unbalanced_members:
                recommendations.append({
                    'type': 'workload',
                    'priority': 'medium',
                    'title': 'Workload Imbalance Detected',
                    'description': f'{len(unbalanced_members)} team members have significantly unbalanced workloads.',
                    'action_items': [
                        'Redistribute tasks and leads',
                        'Review individual capacity ratings',
                        'Implement workload monitoring',
                        'Consider team restructuring'
                    ]
                })
        
        # Analyze goal progress
        behind_goals = [goal for goal in goals.values() if goal['status'] == 'behind']
        if behind_goals:
            recommendations.append({
                'type': 'goals',
                'priority': 'high',
                'title': 'Goals at Risk',
                'description': f'{len(behind_goals)} performance goals are behind schedule.',
                'action_items': [
                    'Review goal progress weekly',
                    'Identify obstacles to goal achievement',
                    'Provide additional resources if needed',
                    'Consider goal adjustment'
                ]
            })
        
        # Analyze collaboration
        if analytics['summary']['messages_trend'] == 'decreasing':
            recommendations.append({
                'type': 'collaboration',
                'priority': 'medium',
                'title': 'Team Collaboration Declining',
                'description': 'Team communication has decreased. This may impact team cohesion and knowledge sharing.',
                'action_items': [
                    'Schedule regular team meetings',
                    'Encourage team communication',
                    'Implement collaboration tools',
                    'Organize team building activities'
                ]
            })
        
        return recommendations

# Example usage
if __name__ == "__main__":
    team_manager = AdvancedTeamManagement()
    
    # Calculate workload distribution
    workload = team_manager.calculate_workload_distribution(1)
    print("Workload Distribution:", json.dumps(workload, indent=2))
    
    # Track performance metrics
    metrics = team_manager.track_performance_metrics(1)
    print("Performance Metrics:", json.dumps(metrics, indent=2))
    
    # Generate team analytics
    analytics = team_manager.generate_team_analytics(1)
    print("Team Analytics:", json.dumps(analytics['summary'], indent=2))
    
    # Get team recommendations
    recommendations = team_manager.get_team_recommendations(1)
    print("Team Recommendations:", json.dumps(recommendations, indent=2))
    
    print("Advanced team management features initialized successfully!") 