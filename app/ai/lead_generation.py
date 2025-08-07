#!/usr/bin/env python3
"""
AI-Powered Lead Generation Suggestions
Provides intelligent suggestions for finding and researching potential leads.
"""

import requests
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import os

class AILeadGeneration:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY', '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')
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ea-crm.com",
            "X-Title": "EA CRM Lead Generation AI"
        }
        self.logger = logging.getLogger(__name__)
    
    def research_companies(self, industry: str, location: str, company_size: str = "medium") -> List[Dict]:
        """
        Research potential companies in a specific industry and location.
        Returns list of companies with contact information and insights.
        """
        try:
            prompt = f"""
            Research potential companies in the {industry} industry located in {location}.
            Focus on {company_size} sized companies that might need our services.
            
            For each company, provide:
            - Company name
            - Website
            - Industry subcategory
            - Estimated company size (employees)
            - Potential decision makers (titles)
            - Contact information if available
            - Why they might be a good lead
            
            Return as JSON array with company objects.
            """
            
            response = self._make_request("chat/completions", {
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are an expert business researcher specializing in lead generation. Provide accurate, actionable company research."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            })
            
            if response and response.get("choices"):
                content = response["choices"][0]["message"]["content"]
                try:
                    # Extract JSON from response
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        companies = json.loads(json_match.group())
                        return self._validate_companies(companies)
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse company research response")
            
            return self._fallback_company_research(industry, location, company_size)
            
        except Exception as e:
            self.logger.error(f"Company research error: {str(e)}")
            return self._fallback_company_research(industry, location, company_size)
    
    def discover_contacts(self, company_name: str, company_website: str = None) -> List[Dict]:
        """
        Discover potential contacts at a target company.
        Returns list of contacts with their roles and contact information.
        """
        try:
            prompt = f"""
            Find potential decision makers and contacts at {company_name}.
            {f'Company website: {company_website}' if company_website else ''}
            
            Look for:
            - C-level executives (CEO, CTO, CFO, etc.)
            - Department heads (Marketing Director, Sales Director, etc.)
            - Decision makers for technology/services
            - Contact information (email patterns, LinkedIn profiles)
            
            Return as JSON array with contact objects including:
            - name
            - title
            - department
            - contact_info (email, phone, LinkedIn)
            - decision_making_level (high/medium/low)
            """
            
            response = self._make_request("chat/completions", {
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are an expert at finding and validating business contacts. Provide accurate contact discovery."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.6
            })
            
            if response and response.get("choices"):
                content = response["choices"][0]["message"]["content"]
                try:
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        contacts = json.loads(json_match.group())
                        return self._validate_contacts(contacts)
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse contact discovery response")
            
            return self._fallback_contact_discovery(company_name)
            
        except Exception as e:
            self.logger.error(f"Contact discovery error: {str(e)}")
            return self._fallback_contact_discovery(company_name)
    
    def enrich_lead_data(self, lead_data: Dict) -> Dict:
        """
        Enrich existing lead data with additional information.
        Returns enhanced lead data with company insights, social profiles, etc.
        """
        try:
            company_name = lead_data.get("company_name", "")
            website = lead_data.get("company_website", "")
            
            prompt = f"""
            Enrich the following lead data with additional information:
            
            Company: {company_name}
            Website: {website}
            Industry: {lead_data.get('industry', '')}
            Location: {lead_data.get('country', '')}
            
            Provide additional information:
            - Company size and revenue estimates
            - Technology stack and tools they use
            - Recent news or developments
            - Social media profiles
            - Key competitors
            - Growth indicators
            - Potential pain points we can solve
            
            Return as JSON with enriched data.
            """
            
            response = self._make_request("chat/completions", {
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are an expert at business intelligence and lead enrichment. Provide valuable insights."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.5
            })
            
            if response and response.get("choices"):
                content = response["choices"][0]["message"]["content"]
                try:
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        enriched_data = json.loads(json_match.group())
                        return {**lead_data, **enriched_data}
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse lead enrichment response")
            
            return lead_data
            
        except Exception as e:
            self.logger.error(f"Lead enrichment error: {str(e)}")
            return lead_data
    
    def suggest_industries(self, historical_data: Dict) -> List[Dict]:
        """
        Suggest which industries to focus on based on historical conversion data.
        Returns list of industries with conversion probability and reasoning.
        """
        try:
            prompt = f"""
            Based on this historical lead data, suggest which industries to focus on:
            
            {json.dumps(historical_data, indent=2)}
            
            Analyze:
            - Industries with highest conversion rates
            - Industries with good lead volume
            - Emerging industries with potential
            - Industries with high-value clients
            - Seasonal trends
            
            Return as JSON array with industry suggestions including:
            - industry_name
            - conversion_rate
            - lead_volume
            - average_deal_size
            - reasoning
            - priority_level (high/medium/low)
            """
            
            response = self._make_request("chat/completions", {
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are an expert at analyzing business data and making strategic recommendations."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.4
            })
            
            if response and response.get("choices"):
                content = response["choices"][0]["message"]["content"]
                try:
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        suggestions = json.loads(json_match.group())
                        return self._validate_industry_suggestions(suggestions)
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse industry suggestions response")
            
            return self._fallback_industry_suggestions(historical_data)
            
        except Exception as e:
            self.logger.error(f"Industry suggestions error: {str(e)}")
            return self._fallback_industry_suggestions(historical_data)
    
    def generate_lead_ideas(self, user_preferences: Dict) -> List[Dict]:
        """
        Generate creative lead generation ideas based on user preferences and market trends.
        """
        try:
            prompt = f"""
            Generate creative lead generation ideas based on these preferences:
            
            {json.dumps(user_preferences, indent=2)}
            
            Consider:
            - Industry trends and emerging markets
            - Geographic opportunities
            - Company size preferences
            - Technology adoption patterns
            - Seasonal business cycles
            - Networking opportunities
            - Content marketing strategies
            - Partnership possibilities
            
            Return as JSON array with lead ideas including:
            - idea_title
            - target_audience
            - approach_method
            - expected_outcome
            - difficulty_level
            - time_required
            """
            
            response = self._make_request("chat/completions", {
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are a creative lead generation strategist. Generate innovative, actionable ideas."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.8
            })
            
            if response and response.get("choices"):
                content = response["choices"][0]["message"]["content"]
                try:
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        ideas = json.loads(json_match.group())
                        return self._validate_lead_ideas(ideas)
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse lead ideas response")
            
            return self._fallback_lead_ideas(user_preferences)
            
        except Exception as e:
            self.logger.error(f"Lead ideas generation error: {str(e)}")
            return self._fallback_lead_ideas(user_preferences)
    
    def _make_request(self, endpoint: str, data: Dict) -> Optional[Dict]:
        """Make API request to OpenRouter"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API error: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Request error: {str(e)}")
            return None
    
    def _validate_companies(self, companies: List[Dict]) -> List[Dict]:
        """Validate and clean company research results"""
        validated = []
        for company in companies:
            if isinstance(company, dict) and company.get("name"):
                validated.append({
                    "name": company.get("name", ""),
                    "website": company.get("website", ""),
                    "industry": company.get("industry", ""),
                    "size": company.get("size", ""),
                    "location": company.get("location", ""),
                    "decision_makers": company.get("decision_makers", []),
                    "contact_info": company.get("contact_info", {}),
                    "reasoning": company.get("reasoning", ""),
                    "confidence": company.get("confidence", 0.7)
                })
        return validated
    
    def _validate_contacts(self, contacts: List[Dict]) -> List[Dict]:
        """Validate and clean contact discovery results"""
        validated = []
        for contact in contacts:
            if isinstance(contact, dict) and contact.get("name"):
                validated.append({
                    "name": contact.get("name", ""),
                    "title": contact.get("title", ""),
                    "department": contact.get("department", ""),
                    "contact_info": contact.get("contact_info", {}),
                    "decision_level": contact.get("decision_making_level", "medium"),
                    "confidence": contact.get("confidence", 0.7)
                })
        return validated
    
    def _validate_industry_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """Validate and clean industry suggestions"""
        validated = []
        for suggestion in suggestions:
            if isinstance(suggestion, dict) and suggestion.get("industry_name"):
                validated.append({
                    "industry_name": suggestion.get("industry_name", ""),
                    "conversion_rate": suggestion.get("conversion_rate", 0),
                    "lead_volume": suggestion.get("lead_volume", 0),
                    "average_deal_size": suggestion.get("average_deal_size", 0),
                    "reasoning": suggestion.get("reasoning", ""),
                    "priority_level": suggestion.get("priority_level", "medium")
                })
        return validated
    
    def _validate_lead_ideas(self, ideas: List[Dict]) -> List[Dict]:
        """Validate and clean lead generation ideas"""
        validated = []
        for idea in ideas:
            if isinstance(idea, dict) and idea.get("idea_title"):
                validated.append({
                    "idea_title": idea.get("idea_title", ""),
                    "target_audience": idea.get("target_audience", ""),
                    "approach_method": idea.get("approach_method", ""),
                    "expected_outcome": idea.get("expected_outcome", ""),
                    "difficulty_level": idea.get("difficulty_level", "medium"),
                    "time_required": idea.get("time_required", "1-2 weeks")
                })
        return validated
    
    def _fallback_company_research(self, industry: str, location: str, company_size: str) -> List[Dict]:
        """Fallback company research when AI is unavailable"""
        return [
            {
                "name": f"Sample {industry} Company",
                "website": "https://example.com",
                "industry": industry,
                "size": company_size,
                "location": location,
                "decision_makers": ["CEO", "CTO"],
                "contact_info": {"email": "contact@example.com"},
                "reasoning": "Sample company for demonstration",
                "confidence": 0.5
            }
        ]
    
    def _fallback_contact_discovery(self, company_name: str) -> List[Dict]:
        """Fallback contact discovery when AI is unavailable"""
        return [
            {
                "name": "John Doe",
                "title": "CEO",
                "department": "Executive",
                "contact_info": {"email": "john.doe@company.com"},
                "decision_level": "high",
                "confidence": 0.5
            }
        ]
    
    def _fallback_industry_suggestions(self, historical_data: Dict) -> List[Dict]:
        """Fallback industry suggestions when AI is unavailable"""
        return [
            {
                "industry_name": "Technology",
                "conversion_rate": 15.0,
                "lead_volume": 100,
                "average_deal_size": 50000,
                "reasoning": "High technology adoption rate",
                "priority_level": "high"
            }
        ]
    
    def _fallback_lead_ideas(self, user_preferences: Dict) -> List[Dict]:
        """Fallback lead generation ideas when AI is unavailable"""
        return [
            {
                "idea_title": "LinkedIn Networking",
                "target_audience": "Industry professionals",
                "approach_method": "Connect and engage with decision makers",
                "expected_outcome": "Direct connections with potential leads",
                "difficulty_level": "medium",
                "time_required": "2-3 weeks"
            }
        ] 