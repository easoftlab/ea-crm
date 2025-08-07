import requests
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import os

class AILeadScoring:
    def __init__(self, api_key: str = None):
        """Initialize AI Lead Scoring with OpenRouter API"""
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY', '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')
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ea-crm.com",
            "X-Title": "EA CRM Lead Scoring AI"
        }
        self.logger = logging.getLogger(__name__)
    
    def score_lead(self, lead_data: Dict) -> Dict:
        """
        Score a lead from 1-10 with detailed reasoning
        
        Args:
            lead_data: Dictionary containing lead information
                - company_name: str
                - company_website: str
                - industry: str
                - country: str
                - revenue: float
                - contacts: List[Dict] with phones, emails, position
                - notes: str
                - source: str
        
        Returns:
            Dict with:
                - score: int (1-10)
                - reasoning: str
                - factors: Dict with individual factor scores
                - confidence: float (0-1)
                - recommendations: List[str]
        """
        try:
            # Prepare context for AI analysis
            context = self._prepare_lead_context(lead_data)
            
            prompt = f"""
            Analyze this lead data and provide a comprehensive score from 1-10 with detailed reasoning:

            LEAD DATA:
            {json.dumps(context, indent=2)}

            Please provide a JSON response with:
            - score: integer (1-10, where 10 is highest quality)
            - reasoning: string explaining the score
            - factors: object with individual scores for:
                * company_quality (0-10)
                * contact_quality (0-10)
                * market_potential (0-10)
                * data_completeness (0-10)
            - confidence: float (0-1, how confident in the assessment)
            - recommendations: array of strings with specific actions to improve lead quality
            - risk_factors: array of strings identifying potential issues
            - priority_level: string ("high", "medium", "low")
            - suggested_followup_timing: string ("immediate", "within_24h", "within_week", "low_priority")

            Consider:
            - Company website validity and professionalism
            - Contact information quality and completeness
            - Industry conversion potential
            - Geographic market viability
            - Revenue indicators
            - Decision maker level
            - Data completeness
            """
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert lead qualification specialist. Analyze leads objectively and provide actionable insights."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 800
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                try:
                    ai_analysis = json.loads(content)
                    return {
                        "success": True,
                        "score": ai_analysis.get("score", 5),
                        "reasoning": ai_analysis.get("reasoning", "AI analysis completed"),
                        "factors": ai_analysis.get("factors", {}),
                        "confidence": ai_analysis.get("confidence", 0.7),
                        "recommendations": ai_analysis.get("recommendations", []),
                        "risk_factors": ai_analysis.get("risk_factors", []),
                        "priority_level": ai_analysis.get("priority_level", "medium"),
                        "suggested_followup_timing": ai_analysis.get("suggested_followup_timing", "within_week")
                    }
                except json.JSONDecodeError:
                    return self._fallback_scoring(lead_data)
            else:
                self.logger.error(f"API error: {response.status_code}")
                return self._fallback_scoring(lead_data)
                
        except Exception as e:
            self.logger.error(f"Error in AI lead scoring: {str(e)}")
            return self._fallback_scoring(lead_data)
    
    def _prepare_lead_context(self, lead_data: Dict) -> Dict:
        """Prepare lead data for AI analysis"""
        context = {
            "company": {
                "name": lead_data.get("company_name", ""),
                "website": lead_data.get("company_website", ""),
                "industry": lead_data.get("industry", ""),
                "country": lead_data.get("country", ""),
                "revenue": lead_data.get("revenue", 0),
                "source": lead_data.get("source", "")
            },
            "contacts": lead_data.get("contacts", []),
            "notes": lead_data.get("notes", ""),
            "website_analysis": self._analyze_website(lead_data.get("company_website", "")),
            "contact_analysis": self._analyze_contacts(lead_data.get("contacts", [])),
            "market_analysis": self._analyze_market_potential(lead_data)
        }
        return context
    
    def _analyze_website(self, website: str) -> Dict:
        """Analyze website quality"""
        if not website:
            return {"valid": False, "quality": "none", "issues": ["No website provided"]}
        
        # Basic website validation
        try:
            parsed = urlparse(website)
            if not parsed.scheme:
                website = "https://" + website
                parsed = urlparse(website)
            
            domain = parsed.netloc.lower()
            
            # Check for common issues
            issues = []
            if "localhost" in domain or "127.0.0.1" in domain:
                issues.append("Invalid domain")
            if len(domain) < 5:
                issues.append("Suspiciously short domain")
            
            quality = "good" if not issues else "poor"
            
            return {
                "valid": len(issues) == 0,
                "quality": quality,
                "domain": domain,
                "issues": issues
            }
        except:
            return {"valid": False, "quality": "invalid", "issues": ["Invalid URL format"]}
    
    def _analyze_contacts(self, contacts: List[Dict]) -> Dict:
        """Analyze contact information quality"""
        if not contacts:
            return {"quality": "none", "issues": ["No contacts provided"], "decision_maker_level": "unknown"}
        
        total_contacts = len(contacts)
        valid_emails = 0
        valid_phones = 0
        decision_makers = 0
        issues = []
        
        for contact in contacts:
            # Email validation
            emails = contact.get("emails", [])
            for email in emails:
                if self._is_valid_email(email):
                    valid_emails += 1
            
            # Phone validation
            phones = contact.get("phones", [])
            for phone in phones:
                if self._is_valid_phone(phone):
                    valid_phones += 1
            
            # Decision maker analysis
            position = contact.get("position", "").lower()
            if any(keyword in position for keyword in ["ceo", "president", "director", "manager", "owner", "founder"]):
                decision_makers += 1
        
        # Quality assessment
        if total_contacts == 0:
            quality = "none"
        elif valid_emails > 0 and valid_phones > 0 and decision_makers > 0:
            quality = "excellent"
        elif valid_emails > 0 or valid_phones > 0:
            quality = "good"
        else:
            quality = "poor"
        
        if valid_emails == 0:
            issues.append("No valid emails")
        if valid_phones == 0:
            issues.append("No valid phone numbers")
        if decision_makers == 0:
            issues.append("No decision makers identified")
        
        return {
            "quality": quality,
            "total_contacts": total_contacts,
            "valid_emails": valid_emails,
            "valid_phones": valid_phones,
            "decision_makers": decision_makers,
            "issues": issues
        }
    
    def _analyze_market_potential(self, lead_data: Dict) -> Dict:
        """Analyze market potential based on industry and geography"""
        industry = lead_data.get("industry", "").lower()
        country = lead_data.get("country", "").lower()
        revenue = lead_data.get("revenue", 0)
        
        # Industry scoring
        high_value_industries = ["technology", "healthcare", "finance", "manufacturing", "consulting"]
        medium_value_industries = ["retail", "education", "real_estate", "legal", "marketing"]
        
        if any(ind in industry for ind in high_value_industries):
            industry_score = "high"
        elif any(ind in industry for ind in medium_value_industries):
            industry_score = "medium"
        else:
            industry_score = "low"
        
        # Geographic scoring
        major_markets = ["united states", "canada", "uk", "australia", "germany", "france"]
        emerging_markets = ["india", "china", "brazil", "mexico", "singapore"]
        
        if any(market in country for market in major_markets):
            geo_score = "high"
        elif any(market in country for market in emerging_markets):
            geo_score = "medium"
        else:
            geo_score = "low"
        
        # Revenue scoring
        if revenue > 1000000:
            revenue_score = "high"
        elif revenue > 100000:
            revenue_score = "medium"
        else:
            revenue_score = "low"
        
        return {
            "industry_potential": industry_score,
            "geographic_potential": geo_score,
            "revenue_potential": revenue_score,
            "overall_potential": "high" if industry_score == "high" and geo_score == "high" else "medium"
        }
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Basic phone validation"""
        if not phone:
            return False
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        return len(digits) >= 10
    
    def _fallback_scoring(self, lead_data: Dict) -> Dict:
        """Fallback scoring when AI is unavailable"""
        score = 5  # Default middle score
        reasoning = "Fallback scoring used due to AI unavailability"
        
        # Basic scoring logic
        contacts = lead_data.get("contacts", [])
        if contacts:
            score += 1
        
        website = lead_data.get("company_website", "")
        if website and "http" in website:
            score += 1
        
        revenue = lead_data.get("revenue", 0)
        if revenue > 100000:
            score += 1
        
        return {
            "success": False,
            "score": min(score, 10),
            "reasoning": reasoning,
            "factors": {
                "company_quality": 5,
                "contact_quality": 5,
                "market_potential": 5,
                "data_completeness": 5
            },
            "confidence": 0.5,
            "recommendations": ["Verify contact information", "Research company details"],
            "risk_factors": ["Limited data available"],
            "priority_level": "medium",
            "suggested_followup_timing": "within_week"
        }
    
    def detect_duplicates(self, new_lead: Dict, existing_leads: List[Dict]) -> List[Dict]:
        """
        Detect potential duplicate leads
        
        Args:
            new_lead: The new lead to check
            existing_leads: List of existing leads to compare against
        
        Returns:
            List of potential duplicates with confidence scores
        """
        duplicates = []
        
        for existing in existing_leads:
            confidence = 0
            reasons = []
            
            # Company name similarity
            if self._similar_company_names(new_lead.get("company_name", ""), existing.get("company_name", "")):
                confidence += 30
                reasons.append("Similar company name")
            
            # Website match
            if new_lead.get("company_website") == existing.get("company_website"):
                confidence += 25
                reasons.append("Same website")
            
            # Contact overlap
            contact_overlap = self._check_contact_overlap(
                new_lead.get("contacts", []),
                existing.get("contacts", [])
            )
            if contact_overlap > 0:
                confidence += contact_overlap * 20
                reasons.append(f"Contact overlap: {contact_overlap}%")
            
            # Phone/email matches
            if self._check_contact_matches(new_lead, existing):
                confidence += 15
                reasons.append("Matching contact information")
            
            if confidence > 20:  # Only report if significant similarity
                duplicates.append({
                    "existing_lead_id": existing.get("id"),
                    "confidence": min(confidence, 100),
                    "reasons": reasons,
                    "existing_lead": existing
                })
        
        # Sort by confidence
        duplicates.sort(key=lambda x: x["confidence"], reverse=True)
        return duplicates
    
    def _similar_company_names(self, name1: str, name2: str) -> bool:
        """Check if company names are similar"""
        if not name1 or not name2:
            return False
        
        # Normalize names
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        # Exact match
        if name1 == name2:
            return True
        
        # Check for common variations
        variations = [
            (name1.replace(" inc", ""), name2.replace(" inc", "")),
            (name1.replace(" llc", ""), name2.replace(" llc", "")),
            (name1.replace(" corp", ""), name2.replace(" corp", "")),
            (name1.replace(" company", ""), name2.replace(" company", ""))
        ]
        
        for var1, var2 in variations:
            if var1 == var2:
                return True
        
        # Simple similarity check (can be enhanced with fuzzy matching)
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if len(words1.intersection(words2)) >= 2:
            return True
        
        return False
    
    def _check_contact_overlap(self, contacts1: List[Dict], contacts2: List[Dict]) -> float:
        """Check overlap between contact lists"""
        if not contacts1 or not contacts2:
            return 0
        
        emails1 = set()
        phones1 = set()
        
        for contact in contacts1:
            emails1.update(contact.get("emails", []))
            phones1.update(contact.get("phones", []))
        
        matches = 0
        total_contacts = len(contacts2)
        
        for contact in contacts2:
            contact_emails = set(contact.get("emails", []))
            contact_phones = set(contact.get("phones", []))
            
            if emails1.intersection(contact_emails) or phones1.intersection(contact_phones):
                matches += 1
        
        return (matches / total_contacts) * 100 if total_contacts > 0 else 0
    
    def _check_contact_matches(self, lead1: Dict, lead2: Dict) -> bool:
        """Check for matching contact information"""
        contacts1 = lead1.get("contacts", [])
        contacts2 = lead2.get("contacts", [])
        
        for contact1 in contacts1:
            for contact2 in contacts2:
                # Check email matches
                emails1 = set(contact1.get("emails", []))
                emails2 = set(contact2.get("emails", []))
                if emails1.intersection(emails2):
                    return True
                
                # Check phone matches
                phones1 = set(contact1.get("phones", []))
                phones2 = set(contact2.get("phones", []))
                if phones1.intersection(phones2):
                    return True
        
        return False 