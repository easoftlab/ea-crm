import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIKanbanEnhancer:
    def __init__(self, api_key: str = None):
        """Initialize AI Kanban Enhancer with OpenRouter API key"""
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY', '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')
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ea-crm.com",
            "X-Title": "EA CRM Kanban AI"
        }
    
    def analyze_task_priority(self, task_title: str, task_description: str = "", 
                            due_date: str = None, client_name: str = None) -> Dict:
        """
        Analyze task and return AI-suggested priority and reasoning
        """
        try:
            # Build context for AI analysis
            context = f"""
            Task Title: {task_title}
            Description: {task_description}
            Due Date: {due_date or 'Not specified'}
            Client: {client_name or 'Not specified'}
            
            Please analyze this image post-production task and provide:
            1. Priority level (urgent/high/medium/low)
            2. Reasoning for the priority
            3. Risk level (high/medium/low)
            4. Estimated completion time in hours
            5. Suggested tags (comma-separated)
            
            Consider factors like:
            - Deadline urgency
            - Task complexity
            - Client importance
            - Resource requirements
            - Industry standards for image processing
            
            Respond in JSON format:
            {{
                "priority": "high",
                "reasoning": "Urgent client with tight deadline",
                "risk_level": "medium",
                "estimated_hours": 4.5,
                "suggested_tags": ["ecommerce", "urgent", "color-correction"]
            }}
            """
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert project manager specializing in image post-production workflows. Analyze tasks and provide intelligent prioritization and suggestions."
                        },
                        {
                            "role": "user",
                            "content": context
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Try to parse JSON response
                try:
                    ai_analysis = json.loads(content)
                    return {
                        "success": True,
                        "priority": ai_analysis.get("priority", "medium"),
                        "reasoning": ai_analysis.get("reasoning", "AI analysis completed"),
                        "risk_level": ai_analysis.get("risk_level", "medium"),
                        "estimated_hours": ai_analysis.get("estimated_hours", 2.0),
                        "suggested_tags": ai_analysis.get("suggested_tags", []),
                        "ai_confidence": 0.85
                    }
                except json.JSONDecodeError:
                    # Fallback parsing if JSON is malformed
                    return self._parse_text_response(content)
            else:
                logger.error(f"AI API error: {response.status_code} - {response.text}")
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error in AI priority analysis: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _parse_text_response(self, content: str) -> Dict:
        """Fallback parser for non-JSON AI responses"""
        priority = "medium"
        reasoning = "AI analysis completed"
        risk_level = "medium"
        estimated_hours = 2.0
        suggested_tags = []
        
        # Simple keyword-based parsing
        content_lower = content.lower()
        if any(word in content_lower for word in ["urgent", "emergency", "asap", "immediate"]):
            priority = "urgent"
        elif any(word in content_lower for word in ["high", "important", "critical"]):
            priority = "high"
        elif any(word in content_lower for word in ["low", "minor", "simple"]):
            priority = "low"
        
        return {
            "success": True,
            "priority": priority,
            "reasoning": reasoning,
            "risk_level": risk_level,
            "estimated_hours": estimated_hours,
            "suggested_tags": suggested_tags,
            "ai_confidence": 0.6
        }
    
    def suggest_task_assignee(self, task_data: Dict, available_editors: List[Dict]) -> Dict:
        """
        Suggest the best editor for a task based on skills and workload
        """
        try:
            # Build editor profiles for AI analysis
            editor_profiles = []
            for editor in available_editors:
                profile = f"""
                Editor: {editor.get('name', 'Unknown')}
                Skills: {', '.join(editor.get('skills', []))}
                Current Workload: {editor.get('current_tasks', 0)} tasks
                Average Completion Time: {editor.get('avg_completion_hours', 4)} hours
                Specializations: {', '.join(editor.get('specializations', []))}
                """
                editor_profiles.append(profile)
            
            context = f"""
            Task to assign:
            Title: {task_data.get('title', '')}
            Description: {task_data.get('description', '')}
            Priority: {task_data.get('priority', 'medium')}
            Estimated Hours: {task_data.get('estimated_hours', 2)}
            
            Available Editors:
            {'\n'.join(editor_profiles)}
            
            Please suggest the best editor for this task based on:
            1. Skill match with task requirements
            2. Current workload balance
            3. Specialization alignment
            4. Past performance on similar tasks
            
            Respond in JSON format:
            {{
                "suggested_editor_id": 123,
                "reasoning": "Strong color correction skills, manageable workload",
                "confidence_score": 0.85,
                "alternative_editors": [456, 789]
            }}
            """
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert team manager specializing in image post-production. Match tasks to editors based on skills, workload, and performance."
                        },
                        {
                            "role": "user",
                            "content": context
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 400
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                try:
                    ai_suggestion = json.loads(content)
                    return {
                        "success": True,
                        "suggested_editor_id": ai_suggestion.get("suggested_editor_id"),
                        "reasoning": ai_suggestion.get("reasoning", "AI analysis completed"),
                        "confidence_score": ai_suggestion.get("confidence_score", 0.7),
                        "alternative_editors": ai_suggestion.get("alternative_editors", [])
                    }
                except json.JSONDecodeError:
                    return {"success": False, "error": "Failed to parse AI response"}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error in AI assignee suggestion: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def detect_deadline_risk(self, task_data: Dict, editor_performance: Dict) -> Dict:
        """
        Detect if a task is at risk of missing its deadline
        """
        try:
            context = f"""
            Task Analysis for Deadline Risk:
            
            Task Details:
            - Title: {task_data.get('title', '')}
            - Estimated Hours: {task_data.get('estimated_hours', 2)}
            - Due Date: {task_data.get('due_date', 'Not specified')}
            - Priority: {task_data.get('priority', 'medium')}
            - Current Status: {task_data.get('status', 'pending')}
            
            Editor Performance:
            - Average Completion Time: {editor_performance.get('avg_completion_hours', 4)} hours
            - Current Workload: {editor_performance.get('current_tasks', 0)} tasks
            - On-time Completion Rate: {editor_performance.get('on_time_rate', 0.8)}%
            
            Please analyze the risk of missing the deadline and provide:
            1. Risk level (high/medium/low)
            2. Probability of delay (0-100%)
            3. Recommended actions
            4. Alternative solutions
            
            Respond in JSON format:
            {{
                "risk_level": "medium",
                "delay_probability": 35,
                "recommended_actions": ["Reduce workload", "Add resources"],
                "alternative_solutions": ["Split task", "Extend deadline"]
            }}
            """
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a project risk analyst specializing in deadline management for creative workflows."
                        },
                        {
                            "role": "user",
                            "content": context
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 400
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                try:
                    risk_analysis = json.loads(content)
                    return {
                        "success": True,
                        "risk_level": risk_analysis.get("risk_level", "medium"),
                        "delay_probability": risk_analysis.get("delay_probability", 25),
                        "recommended_actions": risk_analysis.get("recommended_actions", []),
                        "alternative_solutions": risk_analysis.get("alternative_solutions", [])
                    }
                except json.JSONDecodeError:
                    return {"success": False, "error": "Failed to parse AI response"}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error in deadline risk detection: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def generate_activity_summary(self, board_data: Dict) -> Dict:
        """
        Generate AI-powered activity summary for the Kanban board
        """
        try:
            # Prepare board statistics for AI analysis
            stats = {
                "total_tasks": sum(len(tasks) for tasks in board_data.get('tasks', {}).values()),
                "completed_today": len([t for t in board_data.get('tasks', {}).get('completed', []) 
                                     if t.get('completed_at') and str(t.get('completed_at', '')).startswith(datetime.now().strftime('%Y-%m-%d'))]),
                "overdue_tasks": len([t for tasks in board_data.get('tasks', {}).values() 
                                    for t in tasks if t.get('due_date') and datetime.strptime(t['due_date'], '%Y-%m-%d') < datetime.now()]),
                "high_priority_tasks": len([t for tasks in board_data.get('tasks', {}).values() 
                                          for t in tasks if t.get('priority') in ['high', 'urgent']])
            }
            
            context = f"""
            Kanban Board Activity Summary:
            
            Current Statistics:
            - Total Tasks: {stats['total_tasks']}
            - Completed Today: {stats['completed_today']}
            - Overdue Tasks: {stats['overdue_tasks']}
            - High Priority Tasks: {stats['high_priority_tasks']}
            
            Task Distribution by Column:
            {json.dumps(board_data.get('tasks', {}), indent=2)}
            
            Please provide a concise, actionable summary including:
            1. Key insights about team performance
            2. Potential bottlenecks or issues
            3. Recommendations for managers
            4. Priority actions needed
            
            Respond in JSON format:
            {{
                "summary": "Team is performing well with 15 tasks completed today",
                "insights": ["High completion rate", "Some overdue tasks need attention"],
                "bottlenecks": ["Review column has 5 pending tasks"],
                "recommendations": ["Assign more reviewers", "Prioritize overdue tasks"],
                "priority_actions": ["Review overdue tasks", "Balance workload"]
            }}
            """
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert project manager providing concise, actionable insights for creative teams."
                        },
                        {
                            "role": "user",
                            "content": context
                        }
                    ],
                    "temperature": 0.4,
                    "max_tokens": 600
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                try:
                    summary = json.loads(content)
                    return {
                        "success": True,
                        "summary": summary.get("summary", "AI analysis completed"),
                        "insights": summary.get("insights", []),
                        "bottlenecks": summary.get("bottlenecks", []),
                        "recommendations": summary.get("recommendations", []),
                        "priority_actions": summary.get("priority_actions", [])
                    }
                except json.JSONDecodeError:
                    return {"success": False, "error": "Failed to parse AI response"}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error in activity summary generation: {str(e)}")
            return {"success": False, "error": str(e)}

# Global instance
ai_enhancer = AIKanbanEnhancer() 