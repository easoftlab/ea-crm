import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app
import os

class AIService:
    def __init__(self):
        self.api_key = "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"
        self.base_url = "https://openrouter.ai/api/v1"
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str, data: Dict) -> Optional[Dict]:
        """Make a request to OpenRouter API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://your-production-dashboard.com",
                "X-Title": "Production Dashboard AI"
            }
            
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error making AI request: {str(e)}")
            return None
    
    def analyze_audit_logs(self, audit_logs: List[Dict], user_stats: Dict) -> Dict:
        """
        Analyze audit logs and user statistics to provide insights
        """
        if not audit_logs:
            return {"summary": "No activity to analyze", "insights": [], "recommendations": []}
        
        # Prepare context for AI analysis
        context = {
            "audit_logs": audit_logs,
            "user_stats": user_stats,
            "analysis_date": datetime.now().isoformat()
        }
        
        prompt = f"""
        Analyze the following production dashboard activity data and provide insights:

        AUDIT LOGS:
        {json.dumps(audit_logs, indent=2)}

        USER STATISTICS:
        {json.dumps(user_stats, indent=2)}

        Please provide:
        1. A concise summary of the day's activity (2-3 sentences)
        2. Key insights about productivity, bottlenecks, or patterns
        3. Specific recommendations for improvement
        4. Any anomalies or concerns that need attention

        Format your response as JSON with these keys:
        - summary: string
        - insights: array of strings
        - recommendations: array of strings
        - anomalies: array of strings
        - productivity_score: number (0-100)
        """
        
        response = self._make_request("chat/completions", {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {"role": "system", "content": "You are an AI assistant analyzing production dashboard data. Provide clear, actionable insights."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        })
        
        if response and 'choices' in response:
            try:
                content = response['choices'][0]['message']['content']
                return json.loads(content)
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"Error parsing AI response: {str(e)}")
                return self._fallback_analysis(audit_logs, user_stats)
        
        return self._fallback_analysis(audit_logs, user_stats)
    
    def _fallback_analysis(self, audit_logs: List[Dict], user_stats: Dict) -> Dict:
        """Fallback analysis when AI is unavailable"""
        total_tasks = len([log for log in audit_logs if log.get('operation') in ['create', 'update']])
        completed_tasks = len([log for log in audit_logs if log.get('new_value') == 'completed'])
        
        insights = []
        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks) * 100
            insights.append(f"Task completion rate: {completion_rate:.1f}%")
        
        if user_stats.get('total_active_time', 0) > 0:
            insights.append(f"Total active time: {user_stats['total_active_time']} minutes")
        
        return {
            "summary": f"Analyzed {len(audit_logs)} activities with {total_tasks} tasks",
            "insights": insights,
            "recommendations": ["Consider implementing the AI analysis for more detailed insights"],
            "anomalies": [],
            "productivity_score": 75.0
        }
    
    def suggest_task_assignee(self, task_data: Dict, available_users: List[Dict]) -> Dict:
        """
        Suggest the best assignee for a task based on skills, workload, and history
        """
        if not available_users:
            return {"suggested_user": None, "reason": "No available users"}
        
        # Prepare context for AI
        context = {
            "task": task_data,
            "available_users": available_users
        }
        
        prompt = f"""
        Analyze the following task and available users to suggest the best assignee:

        TASK:
        {json.dumps(task_data, indent=2)}

        AVAILABLE USERS:
        {json.dumps(available_users, indent=2)}

        Consider:
        - User skills and experience
        - Current workload
        - Past performance on similar tasks
        - Availability and schedule

        Return JSON with:
        - suggested_user_id: number or null
        - reason: string explaining the choice
        - confidence_score: number (0-100)
        """
        
        response = self._make_request("chat/completions", {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {"role": "system", "content": "You are an AI assistant helping with task assignment. Consider skills, workload, and performance."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 500
        })
        
        if response and 'choices' in response:
            try:
                content = response['choices'][0]['message']['content']
                return json.loads(content)
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"Error parsing AI response: {str(e)}")
        
        # Fallback: simple assignment based on workload
        return self._fallback_task_assignment(task_data, available_users)
    
    def _fallback_task_assignment(self, task_data: Dict, available_users: List[Dict]) -> Dict:
        """Fallback task assignment logic"""
        if not available_users:
            return {"suggested_user_id": None, "reason": "No available users", "confidence_score": 0}
        
        # Simple logic: assign to user with lowest current task count
        best_user = min(available_users, key=lambda u: u.get('current_task_count', 0))
        
        return {
            "suggested_user_id": best_user['id'],
            "reason": f"Lowest current workload ({best_user.get('current_task_count', 0)} tasks)",
            "confidence_score": 60.0
        }
    
    def generate_task_summary(self, task_data: Dict, related_activities: List[Dict]) -> str:
        """
        Generate a natural language summary of a task and its activities
        """
        context = {
            "task": task_data,
            "activities": related_activities
        }
        
        prompt = f"""
        Generate a concise, professional summary of this task and its activities:

        TASK:
        {json.dumps(task_data, indent=2)}

        ACTIVITIES:
        {json.dumps(related_activities, indent=2)}

        Provide a 2-3 sentence summary that includes:
        - Task status and progress
        - Key activities or milestones
        - Any notable issues or achievements

        Return only the summary text, no JSON formatting.
        """
        
        response = self._make_request("chat/completions", {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {"role": "system", "content": "You are an AI assistant generating task summaries. Be concise and professional."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 200
        })
        
        if response and 'choices' in response:
            return response['choices'][0]['message']['content'].strip()
        
        # Fallback summary
        status = task_data.get('status', 'unknown')
        return f"Task '{task_data.get('title', 'Untitled')}' is currently {status} with {len(related_activities)} recorded activities."
    
    def analyze_productivity_patterns(self, user_activities: List[Dict]) -> Dict:
        """
        Analyze user productivity patterns and provide recommendations
        """
        if not user_activities:
            return {"patterns": [], "recommendations": [], "productivity_score": 0}
        
        context = {
            "activities": user_activities,
            "analysis_date": datetime.now().isoformat()
        }
        
        prompt = f"""
        Analyze the following user productivity data and identify patterns:

        USER ACTIVITIES:
        {json.dumps(user_activities, indent=2)}

        Please identify:
        1. Productivity patterns (peak hours, breaks, etc.)
        2. Potential bottlenecks or inefficiencies
        3. Recommendations for improvement
        4. Overall productivity score (0-100)

        Return JSON with:
        - patterns: array of identified patterns
        - bottlenecks: array of potential issues
        - recommendations: array of improvement suggestions
        - productivity_score: number (0-100)
        - peak_hours: array of most productive hours
        """
        
        response = self._make_request("chat/completions", {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {"role": "system", "content": "You are an AI assistant analyzing productivity patterns. Provide actionable insights."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 800
        })
        
        if response and 'choices' in response:
            try:
                content = response['choices'][0]['message']['content']
                return json.loads(content)
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"Error parsing AI response: {str(e)}")
        
        return self._fallback_productivity_analysis(user_activities)
    
    def _fallback_productivity_analysis(self, user_activities: List[Dict]) -> Dict:
        """Fallback productivity analysis"""
        total_time = sum(activity.get('duration_seconds', 0) for activity in user_activities)
        total_tasks = len([a for a in user_activities if a.get('activity_type') == 'task_completed'])
        
        return {
            "patterns": [f"Total work time: {total_time//60} minutes"],
            "bottlenecks": [],
            "recommendations": ["Enable AI analysis for detailed insights"],
            "productivity_score": min(75, total_tasks * 10),
            "peak_hours": ["9:00-11:00", "14:00-16:00"]
        }

# Global AI service instance
ai_service = AIService() 