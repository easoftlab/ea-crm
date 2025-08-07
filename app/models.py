from . import db
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, Text
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import os
import json

# Define your models here 

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, default=1)
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # New: Approval status
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who approved
    approved_at = db.Column(db.DateTime, nullable=True)  # When approved
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Personal Information
    date_of_birth = db.Column(db.Date, nullable=True)
    nid_number = db.Column(db.String(50), nullable=True)  # National ID number
    profile_image = db.Column(db.String(255), nullable=True)  # Path to profile image
    
    # Contact Information
    phone_number = db.Column(db.String(20), nullable=True)
    emergency_phone = db.Column(db.String(20), nullable=True)
    
    # Address Information
    current_address = db.Column(db.Text, nullable=True)
    permanent_address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state_province = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    
    # Family Information
    father_name = db.Column(db.String(100), nullable=True)
    mother_name = db.Column(db.String(100), nullable=True)
    
    # Additional Information
    blood_group = db.Column(db.String(10), nullable=True)
    marital_status = db.Column(db.String(20), nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_relationship = db.Column(db.String(50), nullable=True)
    
    # Relationships
    role = db.relationship('Role', backref='users')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_users', remote_side=[id])
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or self.username
    
    def has_permission(self, permission):
        return self.role and self.role.has_permission(permission)
    
    def get_age(self):
        if self.date_of_birth:
            today = datetime.now().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    def get_profile_image_url(self):
        if self.profile_image:
            return f'/static/uploads/profiles/{self.profile_image}'
        return 'https://via.placeholder.com/150x150/007bff/ffffff?text=User'
    
    def is_profile_complete(self):
        """Check if user's profile is complete with all required fields."""
        required_fields = [
            self.first_name,
            self.last_name,
            self.date_of_birth,
            self.nid_number,
            self.profile_image,
            self.phone_number,
            self.emergency_phone,
            self.current_address,
            self.permanent_address,
            self.city,
            self.state_province,
            self.postal_code,
            self.country,
            self.father_name,
            self.mother_name,
            self.blood_group,
            self.marital_status,
            self.emergency_contact_name,
            self.emergency_contact_relationship
        ]
        
        return all(field is not None and str(field).strip() != '' for field in required_fields)
    
    def get_missing_profile_fields(self):
        """Get list of missing profile fields."""
        missing_fields = []
        
        if not self.first_name or not self.first_name.strip():
            missing_fields.append('First Name')
        if not self.last_name or not self.last_name.strip():
            missing_fields.append('Last Name')
        if not self.date_of_birth:
            missing_fields.append('Date of Birth')
        if not self.nid_number or not self.nid_number.strip():
            missing_fields.append('NID Number')
        if not self.profile_image:
            missing_fields.append('Profile Image')
        if not self.phone_number or not self.phone_number.strip():
            missing_fields.append('Phone Number')
        if not self.emergency_phone or not self.emergency_phone.strip():
            missing_fields.append('Emergency Phone')
        if not self.current_address or not self.current_address.strip():
            missing_fields.append('Current Address')
        if not self.permanent_address or not self.permanent_address.strip():
            missing_fields.append('Permanent Address')
        if not self.city or not self.city.strip():
            missing_fields.append('City')
        if not self.state_province or not self.state_province.strip():
            missing_fields.append('State/Province')
        if not self.postal_code or not self.postal_code.strip():
            missing_fields.append('Postal Code')
        if not self.country or not self.country.strip():
            missing_fields.append('Country')
        if not self.father_name or not self.father_name.strip():
            missing_fields.append('Father\'s Name')
        if not self.mother_name or not self.mother_name.strip():
            missing_fields.append('Mother\'s Name')
        if not self.blood_group or not self.blood_group.strip():
            missing_fields.append('Blood Group')
        if not self.marital_status or not self.marital_status.strip():
            missing_fields.append('Marital Status')
        if not self.emergency_contact_name or not self.emergency_contact_name.strip():
            missing_fields.append('Emergency Contact Name')
        if not self.emergency_contact_relationship or not self.emergency_contact_relationship.strip():
            missing_fields.append('Emergency Contact Relationship')
        
        return missing_fields
    
    def get_teams(self):
        """Get all teams the user belongs to."""
        return [m.team for m in self.team_memberships if m.is_active]
    
    def get_primary_team(self):
        """Get the user's primary team (first active team)."""
        active_teams = [m.team for m in self.team_memberships if m.is_active]
        return active_teams[0] if active_teams else None
    
    def is_team_manager(self, team_id):
        """Check if user is a manager of a specific team."""
        return any(m.team_id == team_id and m.role == 'manager' and m.is_active 
                   for m in self.team_memberships)
    
    def can_access_team_chat(self, team_id):
        """Check if user can access a specific team's chat."""
        return self.is_team_manager(team_id) or any(m.team_id == team_id and m.is_active 
                                                   for m in self.team_memberships)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(256), nullable=True)
    permissions = db.Column(db.String(512), nullable=True)  # Comma-separated permissions
    
    def has_permission(self, permission):
        if not self.permissions:
            return False
        return permission in self.permissions.split(',')
    
    def add_permission(self, permission):
        current_permissions = self.permissions.split(',') if self.permissions else []
        if permission not in current_permissions:
            current_permissions.append(permission)
            self.permissions = ','.join(current_permissions)
    
    def remove_permission(self, permission):
        if self.permissions:
            current_permissions = self.permissions.split(',')
            if permission in current_permissions:
                current_permissions.remove(permission)
                self.permissions = ','.join(current_permissions)

class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(128), nullable=False)
    company_website = db.Column(db.String(256), nullable=False)
    country = db.Column(db.String(64), nullable=False)
    state = db.Column(db.String(64), nullable=True)
    industry = db.Column(db.String(64), nullable=False)
    source = db.Column(db.String(64), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default='New')
    followup_date = db.Column(db.Date, nullable=True)  # Only updated from dashboard
    timezone = db.Column(db.String(16), nullable=True)
    revenue = db.Column(db.Float, nullable=True, default=0.0)  # Revenue amount in dollars
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_date = db.Column(db.DateTime, nullable=True)

    # AI Lead Scoring Fields
    ai_score = db.Column(db.Integer, nullable=True)  # Score from 1-10
    ai_score_reasoning = db.Column(db.Text, nullable=True)  # AI reasoning for the score
    ai_score_factors = db.Column(db.Text, nullable=True)  # JSON string of individual factor scores
    ai_confidence = db.Column(db.Float, nullable=True)  # AI confidence in the assessment (0-1)
    ai_recommendations = db.Column(db.Text, nullable=True)  # JSON string of AI recommendations
    ai_risk_factors = db.Column(db.Text, nullable=True)  # JSON string of identified risk factors
    ai_priority_level = db.Column(db.String(32), nullable=True)  # 'high', 'medium', 'low'
    ai_suggested_followup_timing = db.Column(db.String(32), nullable=True)  # 'immediate', 'within_24h', 'within_week', 'low_priority'
    ai_last_scored = db.Column(db.DateTime, nullable=True)  # When AI last scored this lead
    ai_score_version = db.Column(db.String(32), nullable=True)  # Version of AI scoring algorithm used

    # Duplicate Detection Fields
    is_duplicate = db.Column(db.Boolean, default=False)  # Flag for potential duplicates
    duplicate_confidence = db.Column(db.Float, nullable=True)  # Confidence in duplicate detection
    duplicate_reasons = db.Column(db.Text, nullable=True)  # JSON string of duplicate reasons
    original_lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)  # Reference to original lead if this is a duplicate

    contacts = db.relationship('Contact', backref='lead', cascade='all, delete-orphan', lazy=True)
    followup_history = db.relationship('FollowUpHistory', backref='lead', cascade='all, delete-orphan', lazy=True, order_by='FollowUpHistory.followup_number')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_leads')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='updated_leads')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_leads')
    original_lead = db.relationship('Lead', foreign_keys=[original_lead_id], backref='duplicates', remote_side=[id])

class FollowUpHistory(db.Model):
    __tablename__ = 'followup_history'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    followup_number = db.Column(db.Integer, nullable=False)  # 1st, 2nd, 3rd follow-up
    followup_date = db.Column(db.Date, nullable=False)
    status_at_followup = db.Column(db.String(32), nullable=True)  # Status when this follow-up was created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Ensure unique followup_number per lead
    __table_args__ = (db.UniqueConstraint('lead_id', 'followup_number', name='unique_lead_followup'),)
    
    creator = db.relationship('User', backref='created_followups')

class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    position = db.Column(db.String(128), nullable=True)

    phones = db.relationship('ContactPhone', backref='contact', cascade='all, delete-orphan', lazy=True)
    emails = db.relationship('ContactEmail', backref='contact', cascade='all, delete-orphan', lazy=True)
    socials = db.relationship('SocialProfile', backref='contact', cascade='all, delete-orphan', lazy=True)

class ContactPhone(db.Model):
    __tablename__ = 'contact_phones'
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    phone = db.Column(db.String(32), nullable=False)

class ContactEmail(db.Model):
    __tablename__ = 'contact_emails'
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    email = db.Column(db.String(128), nullable=False)

class SocialProfile(db.Model):
    __tablename__ = 'social_profiles'
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    url = db.Column(db.String(256), nullable=False)
    type = db.Column(db.String(64), nullable=True) 

 

class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(64), nullable=False)  # 'lead_created', 'lead_updated', 'followup_added', 'login', etc.
    description = db.Column(db.String(256), nullable=True)
    related_lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='activities')
    related_lead = db.relationship('Lead', backref='activities')

class UserDailyStats(db.Model):
    __tablename__ = 'user_daily_stats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    leads_created = db.Column(db.Integer, default=0)
    leads_updated = db.Column(db.Integer, default=0)
    followups_added = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    login_count = db.Column(db.Integer, default=0)
    total_time_spent = db.Column(db.Integer, default=0)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique daily stats per user
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='unique_user_daily_stats'),)
    
    user = db.relationship('User', backref='daily_stats')

class UserWeeklyStats(db.Model):
    __tablename__ = 'user_weekly_stats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    week_start = db.Column(db.Date, nullable=False)  # Monday of the week
    leads_created = db.Column(db.Integer, default=0)
    leads_updated = db.Column(db.Integer, default=0)
    followups_added = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    total_time_spent = db.Column(db.Integer, default=0)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique weekly stats per user
    __table_args__ = (db.UniqueConstraint('user_id', 'week_start', name='unique_user_weekly_stats'),)
    
    user = db.relationship('User', backref='weekly_stats')

class UserMonthlyStats(db.Model):
    __tablename__ = 'user_monthly_stats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    month_year = db.Column(db.Date, nullable=False)  # First day of the month
    leads_created = db.Column(db.Integer, default=0)
    leads_updated = db.Column(db.Integer, default=0)
    followups_added = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    total_time_spent = db.Column(db.Integer, default=0)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique monthly stats per user
    __table_args__ = (db.UniqueConstraint('user_id', 'month_year', name='unique_user_monthly_stats'),)
    
    user = db.relationship('User', backref='monthly_stats')

class UserTask(db.Model):
    __tablename__ = 'user_tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    task_type = db.Column(db.String(64), nullable=False)  # 'lead_followup', 'research', 'contact', 'meeting', etc.
    priority = db.Column(db.String(32), default='medium')  # 'low', 'medium', 'high', 'urgent'
    status = db.Column(db.String(32), default='pending')  # 'pending', 'in_progress', 'completed', 'cancelled'
    due_date = db.Column(db.Date, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='assigned_tasks')
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref='created_tasks')

class ProfileChangeRequest(db.Model):
    __tablename__ = 'profile_change_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_type = db.Column(db.String(32), nullable=False)  # 'username', 'email', 'name', 'password'
    old_value = db.Column(db.String(256), nullable=True)
    new_value = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(32), default='pending')  # 'pending', 'approved', 'rejected'
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='profile_change_requests')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_changes')

class ConvertedClient(db.Model):
    __tablename__ = 'converted_clients'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(32), unique=True, nullable=False)  # Short unique ID like "JOHN_001"
    company_name = db.Column(db.String(128), nullable=False)
    client_name = db.Column(db.String(128), nullable=False)
    converted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    converted_at = db.Column(db.DateTime, default=datetime.utcnow)
    industry = db.Column(db.String(64), nullable=True)
    country = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), default='active')  # 'active', 'inactive', 'completed'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    converter = db.relationship('User', backref='converted_clients')
    projections = db.relationship('ConvertedClientProjection', backref='client', cascade='all, delete-orphan')
    
    def generate_client_id(self):
        """Generate a short unique client ID from name"""
        if not self.client_name:
            return None
        
        # Clean the name and take first 4 characters
        clean_name = ''.join(c for c in self.client_name.upper() if c.isalnum())[:4]
        
        # Get count of existing clients with similar name
        count = ConvertedClient.query.filter(
            ConvertedClient.client_id.like(f"{clean_name}_%")
        ).count()
        
        return f"{clean_name}_{count+1:03d}"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.client_id:
            self.client_id = self.generate_client_id()

class LeadProjection(db.Model):
    __tablename__ = 'lead_projections'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    month_year = db.Column(db.Date, nullable=False)  # First day of the month
    projection_type = db.Column(db.String(32), nullable=False)  # 'leads_created', 'leads_updated', 'followups_added'
    target_value = db.Column(db.Integer, nullable=False)
    actual_value = db.Column(db.Integer, default=0)
    completion_percentage = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default='active')  # 'active', 'completed', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique projection per lead per month per type
    __table_args__ = (db.UniqueConstraint('lead_id', 'month_year', 'projection_type', name='unique_lead_month_projection'),)
    
    # Relationships
    lead = db.relationship('Lead', backref='projections')
    
    def calculate_completion(self):
        """Calculate completion percentage"""
        if self.target_value > 0:
            self.completion_percentage = (self.actual_value / self.target_value) * 100
        else:
            self.completion_percentage = 0.0
        return self.completion_percentage
    
    def get_status_color(self):
        """Get status color based on completion"""
        if self.completion_percentage >= 100:
            return 'success'  # Exceeding
        elif self.completion_percentage >= 75:
            return 'warning'  # On Track
        elif self.completion_percentage >= 50:
            return 'info'     # Progressing
        else:
            return 'danger'   # At Risk
    
    def calculate_actual_from_stats(self):
        """Calculate actual value from user monthly stats"""
        from sqlalchemy import func
        
        # Get the user who created this lead
        user_id = self.lead.created_by
        
        if not user_id:
            return 0
        
        # Query monthly stats for this user and month
        monthly_stats = UserMonthlyStats.query.filter_by(
            user_id=user_id,
            month_year=self.month_year
        ).first()
        
        if not monthly_stats:
            return 0
        
        # Map projection type to actual stats
        if self.projection_type == 'leads_created':
            return monthly_stats.leads_created
        elif self.projection_type == 'leads_updated':
            return monthly_stats.leads_updated
        elif self.projection_type == 'followups_added':
            return monthly_stats.followups_added
        else:
            return 0

class ConvertedClientProjection(db.Model):
    __tablename__ = 'converted_client_projections'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('converted_clients.id'), nullable=False)
    month_year = db.Column(db.Date, nullable=False)  # First day of the month
    projection_type = db.Column(db.String(32), nullable=False)  # 'revenue', 'work_volume', 'tasks'
    target_value = db.Column(db.Integer, nullable=False)
    actual_value = db.Column(db.Integer, default=0)
    completion_percentage = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default='active')  # 'active', 'completed', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique projection per client per month per type
    __table_args__ = (db.UniqueConstraint('client_id', 'month_year', 'projection_type', name='unique_client_month_projection'),)
    
    def calculate_completion(self):
        """Calculate completion percentage based on actual vs target"""
        if self.target_value > 0:
            self.completion_percentage = (self.actual_value / self.target_value) * 100
        else:
            self.completion_percentage = 0.0
        return self.completion_percentage
    
    def get_status_color(self):
        """Get Bootstrap color class based on completion percentage"""
        if self.completion_percentage >= 100:
            return 'success'
        elif self.completion_percentage >= 75:
            return 'warning'
        elif self.completion_percentage >= 50:
            return 'info'
        else:
            return 'danger'

class Projection(db.Model):
    __tablename__ = 'projections'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    month_year = db.Column(db.Date, nullable=False)  # First day of the month
    projection_type = db.Column(db.String(32), nullable=False)  # 'leads', 'calls', 'conversions', 'revenue'
    target_value = db.Column(db.Integer, nullable=False)
    actual_value = db.Column(db.Integer, default=0)
    completion_percentage = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default='active')  # 'active', 'completed', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='projections')
    
    # Ensure unique projection per user per month per type
    __table_args__ = (db.UniqueConstraint('user_id', 'month_year', 'projection_type', name='unique_user_month_projection'),)
    
    def calculate_completion(self):
        """Calculate completion percentage based on actual vs target"""
        if self.target_value > 0:
            self.completion_percentage = (self.actual_value / self.target_value) * 100
        else:
            self.completion_percentage = 0.0
        return self.completion_percentage
    
    def get_status_color(self):
        """Get Bootstrap color class based on completion percentage"""
        if self.completion_percentage >= 100:
            return 'success'
        elif self.completion_percentage >= 75:
            return 'warning'
        elif self.completion_percentage >= 50:
            return 'info'
        else:
            return 'danger'
    
    def calculate_actual_from_stats(self):
        """Calculate actual value from user monthly stats"""
        from sqlalchemy import func
        
        # Query monthly stats for this user and month
        monthly_stats = UserMonthlyStats.query.filter_by(
            user_id=self.user_id,
            month_year=self.month_year
        ).first()
        
        if not monthly_stats:
            return 0
        
        # Map projection type to actual stats
        if self.projection_type == 'leads':
            return monthly_stats.leads_created
        elif self.projection_type == 'calls':
            # Count calls made by this user in this month
            from datetime import datetime
            start_date = self.month_year
            end_date = self.month_year.replace(day=28) + timedelta(days=4)
            end_date = end_date.replace(day=1) - timedelta(days=1)
            
            call_count = Call.query.filter(
                Call.made_by == self.user_id,
                Call.call_date >= start_date,
                Call.call_date <= end_date
            ).count()
            return call_count
        elif self.projection_type == 'conversions':
            return monthly_stats.conversions
        elif self.projection_type == 'revenue':
            # For revenue, we might need to calculate from converted clients
            # This is a placeholder - implement based on your revenue tracking
            return 0
        else:
            return 0

# New models for Production role functionality

class ProductionTask(db.Model):
    __tablename__ = 'production_tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    task_type = db.Column(db.String(64), nullable=False)  # 'design', 'development', 'content', 'review', 'other'
    priority = db.Column(db.String(32), default='medium')  # 'low', 'medium', 'high', 'urgent'
    status = db.Column(db.String(32), default='pending')  # 'pending', 'in_progress', 'completed', 'cancelled'
    
    # Client information
    client_id = db.Column(db.String(32), nullable=True)  # Reference to client
    client_name = db.Column(db.String(128), nullable=True)
    client_contact = db.Column(db.String(128), nullable=True)
    client_phone = db.Column(db.String(32), nullable=True)
    client_email = db.Column(db.String(128), nullable=True)
    
    # Assignment and tracking
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Task Dependencies for Gantt/DAG View
    estimated_duration_hours = db.Column(db.Float, default=1.0)  # Estimated time to complete
    actual_duration_hours = db.Column(db.Float, nullable=True)  # Actual time taken
    start_date = db.Column(db.Date, nullable=True)  # When work actually started
    dependencies = db.Column(db.Text, nullable=True)  # JSON array of task IDs this task depends on
    blocking_tasks = db.Column(db.Text, nullable=True)  # JSON array of task IDs that depend on this task
    project_id = db.Column(db.String(64), nullable=True)  # Group tasks by project
    workflow_stage = db.Column(db.String(32), default='planning')  # planning, in_progress, review, completed
    
    # AI Enhancement fields
    ai_priority = db.Column(db.String(32), nullable=True)  # AI-suggested priority
    ai_priority_reasoning = db.Column(db.Text, nullable=True)  # AI reasoning for priority
    ai_risk_level = db.Column(db.String(32), nullable=True)  # AI risk assessment
    ai_estimated_hours = db.Column(db.Float, nullable=True)  # AI time estimation
    ai_suggested_tags = db.Column(db.Text, nullable=True)  # JSON array of AI-suggested tags
    ai_confidence = db.Column(db.Float, default=0.0)  # AI confidence score
    ai_suggested_assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ai_deadline_risk_level = db.Column(db.String(32), nullable=True)  # AI deadline risk
    ai_deadline_risk_probability = db.Column(db.Float, nullable=True)  # Risk probability (0-100)
    ai_last_analyzed = db.Column(db.DateTime, nullable=True)  # When AI last analyzed this task
    
    # Productivity Tracking fields
    estimated_duration = db.Column(db.Integer, default=0)  # in minutes
    actual_duration = db.Column(db.Integer, default=0)  # in minutes
    current_session_id = db.Column(db.Integer, db.ForeignKey('task_sessions.id'), nullable=True)
    active_users = db.Column(db.Text, nullable=True)  # JSON array of active user IDs
    
    # File attachments
    attachments = db.relationship('TaskAttachment', backref='task', cascade='all, delete-orphan')
    
    # Relationships
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_production_tasks')
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref='created_production_tasks')
    
    def get_status_color(self):
        """Get Bootstrap color class based on status"""
        status_colors = {
            'pending': 'secondary',
            'in_progress': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_priority_color(self):
        """Get Bootstrap color class based on priority"""
        priority_colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'urgent': 'danger'
        }
        return priority_colors.get(self.priority, 'warning')
    
    def get_dependencies_list(self):
        """Get list of task IDs this task depends on"""
        if self.dependencies:
            try:
                return json.loads(self.dependencies)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def get_blocking_tasks_list(self):
        """Get list of task IDs that depend on this task"""
        if self.blocking_tasks:
            try:
                return json.loads(self.blocking_tasks)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_dependencies(self, task_ids):
        """Set dependencies as JSON string"""
        self.dependencies = json.dumps(task_ids) if task_ids else None
    
    def set_blocking_tasks(self, task_ids):
        """Set blocking tasks as JSON string"""
        self.blocking_tasks = json.dumps(task_ids) if task_ids else None
    
    def add_dependency(self, task_id):
        """Add a single dependency"""
        deps = self.get_dependencies_list()
        if task_id not in deps:
            deps.append(task_id)
            self.set_dependencies(deps)
    
    def remove_dependency(self, task_id):
        """Remove a single dependency"""
        deps = self.get_dependencies_list()
        if task_id in deps:
            deps.remove(task_id)
            self.set_dependencies(deps)
    
    def is_blocked(self):
        """Check if task is blocked by incomplete dependencies"""
        from . import db
        deps = self.get_dependencies_list()
        if not deps:
            return False
        
        # Check if any dependencies are not completed
        blocked_tasks = db.session.query(ProductionTask).filter(
            ProductionTask.id.in_(deps),
            ProductionTask.status != 'completed'
        ).count()
        
        return blocked_tasks > 0
    
    def get_earliest_start_date(self):
        """Calculate earliest possible start date based on dependencies"""
        from . import db
        deps = self.get_dependencies_list()
        if not deps:
            return self.start_date or self.created_at.date()
        
        # Find the latest completion date among dependencies
        latest_completion = db.session.query(db.func.max(ProductionTask.completed_at)).filter(
            ProductionTask.id.in_(deps)
        ).scalar()
        
        if latest_completion:
            return latest_completion.date()
        return self.start_date or self.created_at.date()
    
    def get_workflow_color(self):
        """Get color for workflow stage"""
        workflow_colors = {
            'planning': 'secondary',
            'in_progress': 'primary',
            'review': 'warning',
            'completed': 'success'
        }
        return workflow_colors.get(self.workflow_stage, 'secondary')

    def get_ai_suggested_tags_list(self):
        """Get AI suggested tags as a list"""
        if self.ai_suggested_tags:
            try:
                return json.loads(self.ai_suggested_tags)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_ai_suggested_tags(self, tags_list):
        """Set AI suggested tags from a list"""
        if tags_list:
            self.ai_suggested_tags = json.dumps(tags_list)
        else:
            self.ai_suggested_tags = None
    
    def get_ai_analysis_summary(self):
        """Get a summary of AI analysis for this task"""
        return {
            'ai_priority': self.ai_priority,
            'ai_priority_reasoning': self.ai_priority_reasoning,
            'ai_risk_level': self.ai_risk_level,
            'ai_estimated_hours': self.ai_estimated_hours,
            'ai_suggested_tags': self.get_ai_suggested_tags_list(),
            'ai_confidence': self.ai_confidence,
            'ai_deadline_risk_level': self.ai_deadline_risk_level,
            'ai_deadline_risk_probability': self.ai_deadline_risk_probability,
            'ai_last_analyzed': self.ai_last_analyzed.isoformat() if self.ai_last_analyzed else None
        }
    
    def needs_ai_analysis(self):
        """Check if task needs AI analysis (never analyzed or old analysis)"""
        if not self.ai_last_analyzed:
            return True
        
        # Re-analyze if analysis is older than 24 hours
        from datetime import datetime, timedelta
        return datetime.now(timezone.utc) - self.ai_last_analyzed > timedelta(hours=24)

class TaskDependency(db.Model):
    __tablename__ = 'task_dependencies'
    id = db.Column(db.Integer, primary_key=True)
    
    # Task that depends on another task
    dependent_task_id = db.Column(db.Integer, db.ForeignKey('production_tasks.id'), nullable=False)
    
    # Task that is being depended upon
    prerequisite_task_id = db.Column(db.Integer, db.ForeignKey('production_tasks.id'), nullable=False)
    
    # Dependency type
    dependency_type = db.Column(db.String(32), default='finish_to_start')  # finish_to_start, start_to_start, finish_to_finish, start_to_finish
    
    # Lag time in hours (optional delay between tasks)
    lag_hours = db.Column(db.Float, default=0.0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    dependent_task = db.relationship('ProductionTask', foreign_keys=[dependent_task_id], backref='dependencies_forward')
    prerequisite_task = db.relationship('ProductionTask', foreign_keys=[prerequisite_task_id], backref='dependencies_backward')
    creator = db.relationship('User', backref='created_dependencies')
    
    # Ensure unique dependency relationship
    __table_args__ = (db.UniqueConstraint('dependent_task_id', 'prerequisite_task_id', name='unique_task_dependency'),)
    
    def __repr__(self):
        return f'<TaskDependency {self.prerequisite_task_id} -> {self.dependent_task_id}>'
    
    def get_dependency_description(self):
        """Get human-readable description of dependency type"""
        descriptions = {
            'finish_to_start': 'Task B starts after Task A finishes',
            'start_to_start': 'Task B starts when Task A starts',
            'finish_to_finish': 'Task B finishes when Task A finishes',
            'start_to_finish': 'Task B finishes when Task A starts'
        }
        return descriptions.get(self.dependency_type, 'Unknown dependency type')

class TaskAttachment(db.Model):
    __tablename__ = 'task_attachments'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('production_tasks.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes
    file_type = db.Column(db.String(64), nullable=True)  # MIME type
    upload_source = db.Column(db.String(32), default='local')  # 'local', 'dropbox', 'lan_server'
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_files')
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

class LANServerFile(db.Model):
    __tablename__ = 'lan_server_files'
    id = db.Column(db.Integer, primary_key=True)
    server_path = db.Column(db.String(512), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(64), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    last_accessed = db.Column(db.DateTime, nullable=True)
    accessed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='accessed_lan_files')
    
    def get_full_path(self):
        """Get the full file path"""
        return os.path.join(self.server_path, self.filename)
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

class DropboxUpload(db.Model):
    __tablename__ = 'dropbox_uploads'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    dropbox_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    file_type = db.Column(db.String(64), nullable=True)
    upload_status = db.Column(db.String(32), default='pending')  # 'pending', 'uploading', 'completed', 'failed'
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    dropbox_url = db.Column(db.String(512), nullable=True)
    
    # Relationships
    uploader = db.relationship('User', backref='dropbox_uploads')
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0 

class ProductionActivity(db.Model):
    __tablename__ = 'production_activities'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(64), nullable=False)  # 'app_usage', 'screen_time', 'mouse_activity', 'keyboard_activity'
    application_name = db.Column(db.String(128), nullable=True)  # Adobe Photoshop, Illustrator, etc.
    duration_seconds = db.Column(db.Integer, default=0)
    mouse_clicks = db.Column(db.Integer, default=0)
    keyboard_strokes = db.Column(db.Integer, default=0)
    productivity_score = db.Column(db.Float, default=0.0)
    session_start = db.Column(db.DateTime, default=datetime.utcnow)
    session_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='production_activities')

class ScreenRecording(db.Model):
    __tablename__ = 'screen_recordings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    duration_seconds = db.Column(db.Integer, default=0)
    file_size_mb = db.Column(db.Float, default=0.0)
    recording_type = db.Column(db.String(32), default='screen')  # 'screen', 'application', 'task'
    task_id = db.Column(db.Integer, db.ForeignKey('production_tasks.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='screen_recordings')
    task = db.relationship('ProductionTask', backref='screen_recordings')

class ProductivityReport(db.Model):
    __tablename__ = 'productivity_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    total_active_time = db.Column(db.Integer, default=0)  # in seconds
    total_break_time = db.Column(db.Integer, default=0)  # in seconds
    tasks_completed = db.Column(db.Integer, default=0)
    tasks_pending = db.Column(db.Integer, default=0)
    productivity_score = db.Column(db.Float, default=0.0)
    efficiency_rating = db.Column(db.String(32), default='good')  # 'excellent', 'good', 'average', 'poor'
    strengths = db.Column(db.Text, nullable=True)
    weaknesses = db.Column(db.Text, nullable=True)
    improvement_suggestions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='productivity_reports')

class ApplicationUsage(db.Model):
    __tablename__ = 'application_usage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    application_name = db.Column(db.String(128), nullable=False)
    usage_date = db.Column(db.Date, nullable=False)
    total_time_seconds = db.Column(db.Integer, default=0)
    active_time_seconds = db.Column(db.Integer, default=0)
    idle_time_seconds = db.Column(db.Integer, default=0)
    sessions_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique usage per user per app per date
    __table_args__ = (db.UniqueConstraint('user_id', 'application_name', 'usage_date', name='unique_user_app_date'),)
    
    # Relationships
    user = db.relationship('User', backref='application_usage')

class MouseKeyboardActivity(db.Model):
    __tablename__ = 'mouse_keyboard_activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_date = db.Column(db.Date, nullable=False)
    mouse_clicks = db.Column(db.Integer, default=0)
    keyboard_strokes = db.Column(db.Integer, default=0)
    mouse_movement_distance = db.Column(db.Float, default=0.0)  # in pixels
    scroll_events = db.Column(db.Integer, default=0)
    double_clicks = db.Column(db.Integer, default=0)
    right_clicks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique activity per user per date
    __table_args__ = (db.UniqueConstraint('user_id', 'activity_date', name='unique_user_activity_date'),)
    
    # Relationships
    user = db.relationship('User', backref='mouse_keyboard_activities') 

class WebsiteVisit(db.Model):
    __tablename__ = 'website_visits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    website_url = db.Column(db.String(512), nullable=False)
    website_name = db.Column(db.String(128), nullable=False)
    website_category = db.Column(db.String(64), nullable=False)  # 'reference', 'social', 'client', 'other'
    visit_date = db.Column(db.Date, nullable=False)
    visit_count = db.Column(db.Integer, default=1)
    total_time_seconds = db.Column(db.Integer, default=0)
    browser_type = db.Column(db.String(32), nullable=True)  # 'chrome', 'firefox', 'edge', 'safari'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique visit per user per website per date
    __table_args__ = (db.UniqueConstraint('user_id', 'website_url', 'visit_date', name='unique_user_website_date'),)
    
    # Relationships
    user = db.relationship('User', backref='website_visits')

class DesktopActivity(db.Model):
    __tablename__ = 'desktop_activities'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    app = db.Column(db.String(256), nullable=False)
    title = db.Column(db.String(512), nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # seconds
    activity_type = db.Column(db.String(64), nullable=True)  # e.g., 'window', 'web'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='desktop_activities')

class BrowserActivity(db.Model):
    __tablename__ = 'browser_activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    browser_name = db.Column(db.String(32), nullable=False)  # 'chrome', 'firefox', 'edge', 'safari'
    activity_date = db.Column(db.Date, nullable=False)
    total_time_seconds = db.Column(db.Integer, default=0)
    websites_visited = db.Column(db.Integer, default=0)
    tabs_opened = db.Column(db.Integer, default=0)
    bookmarks_accessed = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique browser activity per user per browser per date
    __table_args__ = (db.UniqueConstraint('user_id', 'browser_name', 'activity_date', name='unique_user_browser_date'),)
    
    # Relationships
    user = db.relationship('User', backref='browser_activities')

class DetailedApplicationUsage(db.Model):
    __tablename__ = 'detailed_application_usage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    application_name = db.Column(db.String(128), nullable=False)
    application_category = db.Column(db.String(64), nullable=False)  # 'creative', 'communication', 'productivity', 'browser', 'other'
    usage_date = db.Column(db.Date, nullable=False)
    total_time_seconds = db.Column(db.Integer, default=0)
    active_time_seconds = db.Column(db.Integer, default=0)
    idle_time_seconds = db.Column(db.Integer, default=0)
    sessions_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique usage per user per app per date
    __table_args__ = (db.UniqueConstraint('user_id', 'application_name', 'usage_date', name='unique_user_app_detailed_date'),)
    
    # Relationships
    user = db.relationship('User', backref='detailed_application_usage') 

class TaskAuditLog(db.Model):
    __tablename__ = 'task_audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    
    # Task information
    task_id = db.Column(db.Integer, nullable=False)  # ID of the task being modified
    task_type = db.Column(db.String(32), nullable=False)  # 'user_task' or 'production_task'
    
    # Operation details
    operation = db.Column(db.String(32), nullable=False)  # 'create', 'update', 'delete', 'status_change'
    field_name = db.Column(db.String(64), nullable=True)  # Which field was changed (for updates)
    old_value = db.Column(db.Text, nullable=True)  # Previous value
    new_value = db.Column(db.Text, nullable=True)  # New value
    
    # User information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_ip = db.Column(db.String(45), nullable=True)  # IP address of the user
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional context
    description = db.Column(db.Text, nullable=True)  # Human-readable description
    request_data = db.Column(db.Text, nullable=True)  # JSON of request data for debugging
    
    # Relationships
    user = db.relationship('User', backref='task_audit_logs')
    
    def __repr__(self):
        return f'<TaskAuditLog {self.operation} on {self.task_type} {self.task_id} by {self.user_id}>'
    
    def get_operation_icon(self):
        """Get appropriate icon for the operation."""
        icons = {
            'create': 'fas fa-plus',
            'update': 'fas fa-edit',
            'delete': 'fas fa-trash',
            'status_change': 'fas fa-exchange-alt',
            'assign': 'fas fa-user-plus',
            'comment': 'fas fa-comment',
            'attachment': 'fas fa-paperclip'
        }
        return icons.get(self.operation, 'fas fa-info-circle')
    
    def get_operation_color(self):
        """Get appropriate color for the operation."""
        colors = {
            'create': 'success',
            'update': 'info',
            'delete': 'danger',
            'status_change': 'warning',
            'assign': 'primary',
            'comment': 'secondary',
            'attachment': 'info'
        }
        return colors.get(self.operation, 'secondary')

# Chat System Models
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, file, image, system
    file_url = db.Column(db.String(500), nullable=True)
    file_name = db.Column(db.String(200), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    room = db.Column(db.String(50), default='general')  # general, task-specific, project-specific
    group_id = db.Column(db.Integer, db.ForeignKey('chat_groups.id'), nullable=True)  # Reference to chat group
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    
    # Threaded Replies functionality
    parent_message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=True)
    
    # Edit/Delete functionality
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    original_content = db.Column(db.Text, nullable=True)  # Store original content for audit
    edit_history = db.Column(db.Text, nullable=True)  # JSON array of edit history
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='chat_messages')
    deleter = db.relationship('User', foreign_keys=[deleted_by], backref='deleted_messages')
    mentions = db.relationship('ChatMention', backref='message', cascade='all, delete-orphan')
    
    # Threaded Replies relationships
    parent_message = db.relationship('ChatMessage', remote_side=[id], backref='replies')
    
    def __repr__(self):
        return f'<ChatMessage {self.id} by {self.sender_id} in {self.room}>'
    
    def get_file_size_mb(self):
        """Get file size in MB."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    def is_file_message(self):
        """Check if this is a file message."""
        return self.message_type in ['file', 'image']
    
    def get_message_preview(self):
        """Get a preview of the message content."""
        if self.content:
            return self.content[:100] + '...' if len(self.content) > 100 else self.content
        return ''
    
    def can_edit(self, user_id):
        """Check if user can edit this message (within 10 minutes)."""
        if self.sender_id != user_id:
            return False
        
        # Allow editing within 10 minutes
        from datetime import datetime, timedelta
        time_diff = datetime.now(timezone.utc) - self.created_at
        return time_diff <= timedelta(minutes=10)
    
    def can_delete(self, user_id):
        """Check if user can delete this message."""
        return self.sender_id == user_id
    
    def soft_delete(self, user_id):
        """Soft delete the message."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = user_id
        self.updated_at = datetime.now(timezone.utc)
    
    def edit_message(self, new_content, user_id):
        """Edit the message content."""
        import json
        
        # Store original content if this is the first edit
        if not self.is_edited:
            self.original_content = self.content
            self.edit_history = json.dumps([{
                'content': self.content,
                'edited_at': self.created_at.isoformat(),
                'edited_by': self.sender_id
            }])
        
        # Add to edit history
        history = json.loads(self.edit_history) if self.edit_history else []
        history.append({
            'content': self.content,
            'edited_at': self.updated_at.isoformat(),
            'edited_by': user_id
        })
        self.edit_history = json.dumps(history)
        
        # Update content
        self.content = new_content
        self.is_edited = True
        self.updated_at = datetime.now(timezone.utc)
    
    def get_edit_history(self):
        """Get edit history as a list."""
        import json
        if self.edit_history:
            return json.loads(self.edit_history)
        return []
    
    def get_display_content(self):
        """Get content to display (handles deleted messages)."""
        if self.is_deleted:
            return "[Message deleted]"
        return self.content
    
    def is_thread_reply(self):
        """Check if this message is a reply in a thread."""
        return self.parent_message_id is not None
    
    def get_thread_replies_count(self):
        """Get the number of replies in this thread."""
        return len(self.replies) if self.replies else 0
    
    def get_thread_replies(self):
        """Get all replies in this thread, ordered by creation time."""
        if self.replies:
            return sorted(self.replies, key=lambda x: x.created_at)
        return []
    
    def get_thread_preview(self):
        """Get a preview of the thread (first few replies)."""
        replies = self.get_thread_replies()
        if replies:
            preview = replies[0].get_message_preview()
            if len(replies) > 1:
                preview += f" (+{len(replies) - 1} more replies)"
            return preview
        return ""

class ChatMention(db.Model):
    __tablename__ = 'chat_mentions'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=False)
    mentioned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    mentioned_user = db.relationship('User', backref='mentions')
    
    def __repr__(self):
        return f'<ChatMention {self.mentioned_user_id} in message {self.message_id}>'

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # task_assigned, task_completed, mention, deadline, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    related_id = db.Column(db.Integer, nullable=True)  # task_id, message_id, etc.
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.type} for {self.user_id}>'
    
    def get_icon(self):
        """Get appropriate icon for notification type."""
        icons = {
            'task_assigned': 'fas fa-tasks',
            'task_completed': 'fas fa-check-circle',
            'task_overdue': 'fas fa-exclamation-triangle',
            'mention': 'fas fa-at',
            'deadline': 'fas fa-clock',
            'file_upload': 'fas fa-upload',
            'system': 'fas fa-info-circle'
        }
        return icons.get(self.type, 'fas fa-bell')
    
    def get_color(self):
        """Get appropriate color for notification type."""
        colors = {
            'task_assigned': 'primary',
            'task_completed': 'success',
            'task_overdue': 'danger',
            'mention': 'warning',
            'deadline': 'warning',
            'file_upload': 'info',
            'system': 'secondary'
        }
        return colors.get(self.type, 'secondary')
    
    def get_time_ago(self):
        """Get human-readable time ago."""
        from datetime import datetime
        now = datetime.now(timezone.utc)
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"

# Enhanced User Model with online status
class UserOnlineStatus(db.Model):
    __tablename__ = 'user_online_status'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(255), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='online_status')
    
    def __repr__(self):
        return f'<UserOnlineStatus {self.user_id}: {"online" if self.is_online else "offline"}>'

class MessageReadReceipt(db.Model):
    __tablename__ = 'message_read_receipts'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=False)
    read_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    message = db.relationship('ChatMessage', backref='read_receipts')
    read_by = db.relationship('User', backref='message_reads')
    
    def __repr__(self):
        return f'<MessageReadReceipt {self.message_id} by {self.read_by_id}>'

class MessageReaction(db.Model):
    """Model for message reactions (like, heart, laugh, etc.)."""
    __tablename__ = 'message_reactions'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)  # 'like', 'heart', 'laugh', 'wow', 'sad', 'angry'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    message = db.relationship('ChatMessage', backref='reactions')
    user = db.relationship('User', backref='message_reactions')
    
    # Allow multiple reactions from same user (removed unique constraint)
    # Users can now add multiple reactions to the same message
    
    def __repr__(self):
        return f'<MessageReaction {self.reaction_type} on {self.message_id} by {self.user_id}>'
    
    def get_reaction_emoji(self):
        """Get emoji for reaction type."""
        emojis = {
            'like': '👍',
            'heart': '❤️',
            'laugh': '😂',
            'wow': '😮',
            'sad': '😢',
            'angry': '😠'
        }
        return emojis.get(self.reaction_type, '👍')
    
    def get_reaction_color(self):
        """Get color for reaction type."""
        colors = {
            'like': '#1877f2',  # Facebook blue
            'heart': '#e31b23',  # Red
            'laugh': '#ffd700',  # Gold
            'wow': '#ff6b35',    # Orange
            'sad': '#6c757d',    # Gray
            'angry': '#dc3545'   # Red
        }
        return colors.get(self.reaction_type, '#1877f2') 

class ChatMedia(db.Model):
    """Model for storing media files shared in chat."""
    __tablename__ = 'chat_media'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes
    file_type = db.Column(db.String(64), nullable=True)  # MIME type
    media_type = db.Column(db.String(32), nullable=False)  # 'image', 'video', 'audio', 'document', 'link'
    thumbnail_path = db.Column(db.String(512), nullable=True)  # For videos and large images
    duration = db.Column(db.Integer, nullable=True)  # For video/audio in seconds
    width = db.Column(db.Integer, nullable=True)  # For images/videos
    height = db.Column(db.Integer, nullable=True)  # For images/videos
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For link previews
    link_url = db.Column(db.String(512), nullable=True)
    link_title = db.Column(db.String(255), nullable=True)
    link_description = db.Column(db.Text, nullable=True)
    link_image = db.Column(db.String(512), nullable=True)
    
    # Relationships
    message = db.relationship('ChatMessage', backref='media_attachments')
    uploader = db.relationship('User', backref='uploaded_chat_media')
    
    def __repr__(self):
        return f'<ChatMedia {self.original_filename}>'
    
    def get_file_size_mb(self):
        """Get file size in MB."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    def is_image(self):
        """Check if media is an image."""
        return self.media_type == 'image'
    
    def is_video(self):
        """Check if media is a video."""
        return self.media_type == 'video'
    
    def is_audio(self):
        """Check if media is an audio file."""
        return self.media_type == 'audio'
    
    def is_document(self):
        """Check if media is a document."""
        return self.media_type == 'document'
    
    def is_link(self):
        """Check if media is a link preview."""
        return self.media_type == 'link'
    
    def get_media_icon(self):
        """Get appropriate icon for media type."""
        if self.is_image():
            return 'fas fa-image'
        elif self.is_video():
            return 'fas fa-video'
        elif self.is_audio():
            return 'fas fa-music'
        elif self.is_document():
            return 'fas fa-file-alt'
        elif self.is_link():
            return 'fas fa-link'
        return 'fas fa-file'
    
    def get_media_color(self):
        """Get appropriate color for media type."""
        if self.is_image():
            return '#28a745'
        elif self.is_video():
            return '#dc3545'
        elif self.is_audio():
            return '#ffc107'
        elif self.is_document():
            return '#17a2b8'
        elif self.is_link():
            return '#6f42c1'
        return '#6c757d'


class ChatMediaGallery(db.Model):
    """Model for organizing media into galleries."""
    __tablename__ = 'chat_media_galleries'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    room = db.Column(db.String(50), default='general')  # Which chat room this gallery belongs to
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='created_media_galleries')
    media_items = db.relationship('ChatMedia', secondary='gallery_media_association', backref='galleries')
    
    def __repr__(self):
        return f'<ChatMediaGallery {self.name}>'
    
    def get_media_count(self):
        """Get count of media items in gallery."""
        return len(self.media_items)
    
    def get_media_by_type(self, media_type):
        """Get media items filtered by type."""
        return [media for media in self.media_items if media.media_type == media_type]


class GalleryMediaAssociation(db.Model):
    """Association table for many-to-many relationship between galleries and media."""
    __tablename__ = 'gallery_media_association'
    
    id = db.Column(db.Integer, primary_key=True)
    gallery_id = db.Column(db.Integer, db.ForeignKey('chat_media_galleries.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('chat_media.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique association
    __table_args__ = (db.UniqueConstraint('gallery_id', 'media_id', name='unique_gallery_media'),)

class ChatReminder(db.Model):
    __tablename__ = 'chat_reminders'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    reminder_time = db.Column(db.DateTime, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    message = db.relationship('ChatMessage', backref='reminders')
    user = db.relationship('User', backref='chat_reminders')
    
    def is_overdue(self):
        """Check if reminder is overdue"""
        return datetime.now(timezone.utc) > self.reminder_time and not self.is_completed
    
    def get_status(self):
        """Get reminder status"""
        if self.is_completed:
            return 'completed'
        elif self.is_overdue():
            return 'overdue'
        elif datetime.now(timezone.utc) > self.reminder_time - timedelta(hours=1):
            return 'due_soon'
        else:
            return 'pending'
    
    def mark_completed(self):
        """Mark reminder as completed"""
        self.is_completed = True
        self.completed_at = datetime.now(timezone.utc)

class ScheduledMessage(db.Model):
    __tablename__ = 'scheduled_messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room = db.Column(db.String(50), default='general')
    content = db.Column(db.Text, nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', backref='scheduled_messages')
    
    def is_due(self):
        """Check if message is due to be sent"""
        return datetime.now(timezone.utc) >= self.scheduled_time and not self.is_sent
    
    def get_status(self):
        """Get scheduled message status"""
        if self.is_sent:
            return 'sent'
        elif self.is_due():
            return 'due'
        else:
            return 'scheduled'
    
    def mark_sent(self):
        """Mark message as sent"""
        self.is_sent = True
        self.sent_at = datetime.now(timezone.utc) 

class ChatGroup(db.Model):
    """Model for chat groups with roles and permissions."""
    __tablename__ = 'chat_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)
    
    # Group settings
    is_public = db.Column(db.Boolean, default=True)  # Public or private group
    is_archived = db.Column(db.Boolean, default=False)  # Archived status
    allow_guest_messages = db.Column(db.Boolean, default=True)  # Allow non-members to message
    
    # Group metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_chat_groups')
    members = db.relationship('ChatGroupMember', backref='group', cascade='all, delete-orphan')
    messages = db.relationship('ChatMessage', backref='chat_group', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ChatGroup {self.name}>'
    
    def get_member_count(self):
        """Get the number of active members in the group."""
        return len([m for m in self.members if m.is_active])
    
    def get_admin_count(self):
        """Get the number of admin members in the group."""
        return len([m for m in self.members if m.role == 'admin' and m.is_active])
    
    def is_user_member(self, user_id):
        """Check if a user is a member of this group."""
        return any(m.user_id == user_id and m.is_active for m in self.members)
    
    def is_user_admin(self, user_id):
        """Check if a user is an admin of this group."""
        return any(m.user_id == user_id and m.role == 'admin' and m.is_active for m in self.members)
    
    def can_user_send_message(self, user_id):
        """Check if a user can send messages to this group."""
        if self.is_archived:
            return False
        if self.allow_guest_messages:
            return True
        return self.is_user_member(user_id)
    
    def get_members_by_role(self, role):
        """Get all members with a specific role."""
        return [m for m in self.members if m.role == role and m.is_active]


class ChatGroupMember(db.Model):
    """Model for group memberships with roles and permissions."""
    __tablename__ = 'chat_group_members'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('chat_groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Member role and permissions
    role = db.Column(db.String(32), default='member')  # 'admin', 'moderator', 'member'
    permissions = db.Column(db.Text, nullable=True)  # JSON string of specific permissions
    
    # Member status
    is_active = db.Column(db.Boolean, default=True)
    is_muted = db.Column(db.Boolean, default=False)  # Muted notifications
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime, nullable=True)
    
    # Invitation details
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    invitation_accepted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='chat_group_memberships')
    inviter = db.relationship('User', foreign_keys=[invited_by], backref='invited_group_members')
    
    # Ensure unique membership
    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='unique_group_member'),)
    
    def __repr__(self):
        return f'<ChatGroupMember {self.user_id} in {self.group_id}>'
    
    def has_permission(self, permission):
        """Check if member has a specific permission."""
        if self.role == 'admin':
            return True
        
        if not self.permissions:
            return False
        
        import json
        try:
            permissions_list = json.loads(self.permissions)
            return permission in permissions_list
        except (json.JSONDecodeError, TypeError):
            return False
    
    def add_permission(self, permission):
        """Add a permission to the member."""
        import json
        
        if self.role == 'admin':
            return  # Admins have all permissions
        
        current_permissions = []
        if self.permissions:
            try:
                current_permissions = json.loads(self.permissions)
            except (json.JSONDecodeError, TypeError):
                current_permissions = []
        
        if permission not in current_permissions:
            current_permissions.append(permission)
            self.permissions = json.dumps(current_permissions)
    
    def remove_permission(self, permission):
        """Remove a permission from the member."""
        import json
        
        if not self.permissions:
            return
        
        try:
            current_permissions = json.loads(self.permissions)
            if permission in current_permissions:
                current_permissions.remove(permission)
                self.permissions = json.dumps(current_permissions)
        except (json.JSONDecodeError, TypeError):
            pass
    
    def get_role_display_name(self):
        """Get the display name for the role."""
        role_names = {
            'admin': 'Administrator',
            'moderator': 'Moderator',
            'member': 'Member'
        }
        return role_names.get(self.role, self.role.title())
    
    def get_role_color(self):
        """Get the color for the role badge."""
        role_colors = {
            'admin': 'danger',
            'moderator': 'warning',
            'member': 'secondary'
        }
        return role_colors.get(self.role, 'secondary')


class ChatGroupInvitation(db.Model):
    """Model for group invitations."""
    __tablename__ = 'chat_group_invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('chat_groups.id'), nullable=False)
    invited_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Invitation details
    role = db.Column(db.String(32), default='member')  # Role to be assigned
    message = db.Column(db.Text, nullable=True)  # Optional invitation message
    expires_at = db.Column(db.DateTime, nullable=True)  # Invitation expiration
    
    # Status
    status = db.Column(db.String(32), default='pending')  # 'pending', 'accepted', 'declined', 'expired'
    responded_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    group = db.relationship('ChatGroup', backref='invitations')
    invited_user = db.relationship('User', foreign_keys=[invited_user_id], backref='received_invitations')
    invited_by = db.relationship('User', foreign_keys=[invited_by_id], backref='sent_invitations')
    
    def __repr__(self):
        return f'<ChatGroupInvitation {self.invited_user_id} to {self.group_id}>'
    
    def is_expired(self):
        """Check if the invitation has expired."""
        if not self.expires_at:
            return False
        from datetime import datetime
        return datetime.now(timezone.utc) > self.expires_at
    
    def accept(self):
        """Accept the invitation."""
        from datetime import datetime
        
        if self.status != 'pending' or self.is_expired():
            return False
        
        # Create group membership
        member = ChatGroupMember(
            group_id=self.group_id,
            user_id=self.invited_user_id,
            role=self.role,
            invited_by=self.invited_by_id,
            invitation_accepted_at=datetime.now(timezone.utc)
        )
        
        # Update invitation status
        self.status = 'accepted'
        self.responded_at = datetime.now(timezone.utc)
        
        return member
    
    def decline(self):
        """Decline the invitation."""
        from datetime import datetime
        
        if self.status != 'pending':
            return False
        
        self.status = 'declined'
        self.responded_at = datetime.now(timezone.utc)
        return True


class ChatGroupReport(db.Model):
    """Model for group reports and moderation."""
    __tablename__ = 'chat_group_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('chat_groups.id'), nullable=False)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Report details
    report_type = db.Column(db.String(32), nullable=False)  # 'spam', 'inappropriate', 'harassment', 'other'
    description = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text, nullable=True)  # JSON string of evidence (screenshots, etc.)
    
    # Status
    status = db.Column(db.String(32), default='pending')  # 'pending', 'investigating', 'resolved', 'dismissed'
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    group = db.relationship('ChatGroup', backref='reports')
    reported_by = db.relationship('User', foreign_keys=[reported_by_id], backref='filed_reports')
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id], backref='resolved_reports')
    
    def __repr__(self):
        return f'<ChatGroupReport {self.report_type} for {self.group_id}>'
    
    def get_report_type_display(self):
        """Get the display name for the report type."""
        type_names = {
            'spam': 'Spam',
            'inappropriate': 'Inappropriate Content',
            'harassment': 'Harassment',
            'other': 'Other'
        }
        return type_names.get(self.report_type, self.report_type.title())
    
    def get_status_color(self):
        """Get the color for the status badge."""
        status_colors = {
            'pending': 'warning',
            'investigating': 'info',
            'resolved': 'success',
            'dismissed': 'secondary'
        }
        return status_colors.get(self.status, 'secondary')
    
    def resolve(self, resolved_by_id, resolution_notes=None, status='resolved'):
        """Resolve the report."""
        from datetime import datetime
        
        self.status = status
        self.resolved_by_id = resolved_by_id
        self.resolution_notes = resolution_notes
        self.resolved_at = datetime.now(timezone.utc) 


class PinnedMessage(db.Model):
    """Model for pinned messages in messenger."""
    __tablename__ = 'pinned_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=False)
    pinned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pinned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    message = db.relationship('ChatMessage', backref='pinned_status')
    pinned_by_user = db.relationship('User', backref='pinned_messages')
    
    def __repr__(self):
        return f'<PinnedMessage {self.message_id} by {self.pinned_by}>'


class MessageAttachment(db.Model):
    """Model for message attachments in messenger."""
    __tablename__ = 'message_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes
    file_type = db.Column(db.String(64), nullable=True)  # MIME type
    mime_type = db.Column(db.String(64), nullable=True)  # MIME type (duplicate for compatibility)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    message = db.relationship('ChatMessage', backref='attachments')
    
    def __repr__(self):
        return f'<MessageAttachment {self.file_name}>'
    
    def get_file_size_mb(self):
        """Get file size in MB."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

class Team(db.Model):
    """Model for teams in the organization."""
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    manager = db.relationship('User', foreign_keys=[manager_id], backref='managed_teams')
    members = db.relationship('UserTeam', backref='team', cascade='all, delete-orphan')
    chat_groups = db.relationship('ChatGroup', backref='team', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Team {self.name}>'
    
    def get_member_count(self):
        """Get the number of active members in the team."""
        return len([m for m in self.members if m.is_active])
    
    def is_user_member(self, user_id):
        """Check if a user is a member of this team."""
        return any(m.user_id == user_id and m.is_active for m in self.members)
    
    def is_user_manager(self, user_id):
        """Check if a user is the manager of this team."""
        return self.manager_id == user_id

class UserTeam(db.Model):
    """Model for user-team relationships."""
    __tablename__ = 'user_teams'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    role = db.Column(db.String(32), default='member')  # 'member', 'manager'
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='team_memberships')
    
    # Ensure unique user-team relationship
    __table_args__ = (db.UniqueConstraint('user_id', 'team_id', name='unique_user_team'),)
    
    def __repr__(self):
        return f'<UserTeam {self.user_id} in {self.team_id}>'

class TeamMemberDailyReport(db.Model):
    """Model for daily team member performance reports."""
    __tablename__ = 'team_member_daily_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    
    # Daily activity tracking
    login_time = db.Column(db.DateTime, nullable=True)
    logout_time = db.Column(db.DateTime, nullable=True)
    total_active_time = db.Column(db.Integer, default=0)  # in minutes
    total_break_time = db.Column(db.Integer, default=0)  # in minutes
    
    # Daily productivity metrics
    leads_created = db.Column(db.Integer, default=0)
    leads_updated = db.Column(db.Integer, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    tasks_assigned = db.Column(db.Integer, default=0)
    calls_made = db.Column(db.Integer, default=0)
    followups_added = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)  # Daily conversions
    productivity_score = db.Column(db.Float, default=0.0)  # Daily productivity score
    
    # Daily communication activity
    messages_sent = db.Column(db.Integer, default=0)
    messages_received = db.Column(db.Integer, default=0)
    mentions_count = db.Column(db.Integer, default=0)
    
    # Daily goals and achievements
    daily_goal = db.Column(db.Integer, default=0)
    goal_achievement = db.Column(db.Float, default=0.0)  # percentage
    
    # Notes and observations
    notes = db.Column(db.Text, nullable=True)
    manager_notes = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(32), default='active')  # 'active', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique daily report per user per team per date
    __table_args__ = (db.UniqueConstraint('user_id', 'team_id', 'report_date', name='unique_user_team_daily_report'),)
    
    # Relationships
    user = db.relationship('User', backref='daily_reports')
    team = db.relationship('Team', backref='daily_reports')
    
    def __repr__(self):
        return f'<TeamMemberDailyReport {self.user_id} on {self.report_date}>'
    
    def get_productivity_score(self):
        """Calculate daily productivity score."""
        if not self.total_active_time or self.total_active_time == 0:
            return 0
        
        # Weight different activities
        score = 0
        score += self.leads_created * 10
        score += self.leads_updated * 5
        score += self.tasks_completed * 15
        score += self.calls_made * 8
        score += self.followups_added * 3
        
        # Normalize by active time
        return min(100, score / (self.total_active_time / 60))  # Convert minutes to hours
    
    def get_goal_completion(self):
        """Calculate goal completion percentage."""
        if self.daily_goal == 0:
            return 0
        return min(100, (self.leads_created + self.tasks_completed) / self.daily_goal * 100)

class TeamMemberWeeklyReport(db.Model):
    """Model for weekly team member performance reports."""
    __tablename__ = 'team_member_weekly_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    week_start = db.Column(db.Date, nullable=False)  # Monday of the week
    
    # Weekly performance trends
    total_leads_created = db.Column(db.Integer, default=0)
    total_leads_updated = db.Column(db.Integer, default=0)
    total_tasks_completed = db.Column(db.Integer, default=0)
    total_tasks_assigned = db.Column(db.Integer, default=0)
    total_calls_made = db.Column(db.Integer, default=0)
    total_followups_added = db.Column(db.Integer, default=0)
    total_conversions = db.Column(db.Integer, default=0)  # Weekly conversions
    productivity_score = db.Column(db.Float, default=0.0)  # Weekly productivity score
    
    # Weekly communication activity
    total_messages_sent = db.Column(db.Integer, default=0)
    total_messages_received = db.Column(db.Integer, default=0)
    total_mentions_count = db.Column(db.Integer, default=0)
    
    # Weekly time tracking
    total_active_time = db.Column(db.Integer, default=0)  # in minutes
    total_break_time = db.Column(db.Integer, default=0)  # in minutes
    average_daily_active_time = db.Column(db.Float, default=0.0)  # in minutes
    
    # Weekly goal achievement
    weekly_goal = db.Column(db.Integer, default=0)
    goal_achievement = db.Column(db.Float, default=0.0)  # percentage
    
    # Weekly trends
    productivity_trend = db.Column(db.String(32), default='stable')  # 'improving', 'declining', 'stable'
    performance_rating = db.Column(db.String(32), default='average')  # 'excellent', 'good', 'average', 'needs_improvement'
    
    # Workload analysis
    workload_distribution = db.Column(db.Text, nullable=True)  # JSON string of daily workload
    peak_performance_day = db.Column(db.String(10), nullable=True)  # day of week
    
    # Notes and observations
    notes = db.Column(db.Text, nullable=True)
    manager_notes = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(32), default='active')  # 'active', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique weekly report per user per team per week
    __table_args__ = (db.UniqueConstraint('user_id', 'team_id', 'week_start', name='unique_user_team_weekly_report'),)
    
    # Relationships
    user = db.relationship('User', backref='weekly_reports')
    team = db.relationship('Team', backref='weekly_reports')
    
    def __repr__(self):
        return f'<TeamMemberWeeklyReport {self.user_id} week of {self.week_start}>'
    
    def get_productivity_score(self):
        """Calculate weekly productivity score."""
        if not self.total_active_time or self.total_active_time == 0:
            return 0
        
        # Weight different activities
        score = 0
        score += self.total_leads_created * 10
        score += self.total_leads_updated * 5
        score += self.total_tasks_completed * 15
        score += self.total_calls_made * 8
        score += self.total_followups_added * 3
        
        # Normalize by active time
        return min(100, score / (self.total_active_time / 60))
    
    def get_goal_completion(self):
        """Calculate weekly goal completion percentage."""
        if self.weekly_goal == 0:
            return 0
        return min(100, (self.total_leads_created + self.total_tasks_completed) / self.weekly_goal * 100)

class TeamMemberMonthlyReport(db.Model):
    """Model for monthly team member performance reports."""
    __tablename__ = 'team_member_monthly_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    month_year = db.Column(db.Date, nullable=False)  # First day of the month
    
    # Monthly performance summaries
    total_leads_created = db.Column(db.Integer, default=0)
    total_leads_updated = db.Column(db.Integer, default=0)
    total_tasks_completed = db.Column(db.Integer, default=0)
    total_tasks_assigned = db.Column(db.Integer, default=0)
    total_calls_made = db.Column(db.Integer, default=0)
    total_followups_added = db.Column(db.Integer, default=0)
    total_conversions = db.Column(db.Integer, default=0)  # Monthly conversions
    
    # Monthly communication activity
    total_messages_sent = db.Column(db.Integer, default=0)
    total_messages_received = db.Column(db.Integer, default=0)
    total_mentions_count = db.Column(db.Integer, default=0)
    
    # Monthly time tracking
    total_active_time = db.Column(db.Integer, default=0)  # in minutes
    total_break_time = db.Column(db.Integer, default=0)  # in minutes
    average_daily_active_time = db.Column(db.Float, default=0.0)  # in minutes
    
    # Monthly goal vs actual
    monthly_goal = db.Column(db.Integer, default=0)
    goal_achievement = db.Column(db.Float, default=0.0)  # percentage
    
    # Monthly team rankings
    team_rank = db.Column(db.Integer, nullable=True)  # Position in team ranking
    team_performance_percentile = db.Column(db.Float, default=0.0)  # Percentile in team
    
    # Monthly improvement tracking
    improvement_from_last_month = db.Column(db.Float, default=0.0)  # percentage change
    key_achievements = db.Column(db.Text, nullable=True)  # JSON string of achievements
    areas_for_improvement = db.Column(db.Text, nullable=True)  # JSON string of areas
    
    # Performance metrics
    productivity_score = db.Column(db.Float, default=0.0)
    efficiency_rating = db.Column(db.String(32), default='average')  # 'excellent', 'good', 'average', 'needs_improvement'
    reliability_score = db.Column(db.Float, default=0.0)  # based on consistency
    
    # Notes and observations
    notes = db.Column(db.Text, nullable=True)
    manager_notes = db.Column(db.Text, nullable=True)
    employee_self_assessment = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(32), default='active')  # 'active', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique monthly report per user per team per month
    __table_args__ = (db.UniqueConstraint('user_id', 'team_id', 'month_year', name='unique_user_team_monthly_report'),)
    
    # Relationships
    user = db.relationship('User', backref='monthly_reports')
    team = db.relationship('Team', backref='monthly_reports')
    
    def __repr__(self):
        return f'<TeamMemberMonthlyReport {self.user_id} {self.month_year}>'
    
    def get_productivity_score(self):
        """Calculate monthly productivity score."""
        if not self.total_active_time or self.total_active_time == 0:
            return 0
        
        # Weight different activities
        score = 0
        score += self.total_leads_created * 10
        score += self.total_leads_updated * 5
        score += self.total_tasks_completed * 15
        score += self.total_calls_made * 8
        score += self.total_followups_added * 3
        
        # Normalize by active time
        return min(100, score / (self.total_active_time / 60))
    
    def get_goal_completion(self):
        """Calculate monthly goal completion percentage."""
        if self.monthly_goal == 0:
            return 0
        return min(100, (self.total_leads_created + self.total_tasks_completed) / self.monthly_goal * 100)
    
    def get_performance_summary(self):
        """Get a summary of monthly performance."""
        return {
            'productivity_score': self.get_productivity_score(),
            'goal_completion': self.get_goal_completion(),
            'team_rank': self.team_rank,
            'improvement': self.improvement_from_last_month,
            'efficiency': self.efficiency_rating
        }

class ReportSchedule(db.Model):
    """Model for automated report scheduling."""
    __tablename__ = 'report_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Report configuration
    report_type = db.Column(db.String(32), nullable=False)  # 'daily', 'weekly', 'monthly'
    report_frequency = db.Column(db.String(32), nullable=False)  # 'daily', 'weekly', 'monthly'
    delivery_method = db.Column(db.String(32), default='email')  # 'email', 'dashboard', 'both'
    
    # Schedule settings
    schedule_time = db.Column(db.Time, nullable=True)  # Time of day to generate
    schedule_day = db.Column(db.String(10), nullable=True)  # Day of week for weekly reports
    schedule_date = db.Column(db.Integer, nullable=True)  # Date of month for monthly reports
    
    # Report customization
    include_metrics = db.Column(db.Text, nullable=True)  # JSON string of metrics to include
    exclude_users = db.Column(db.Text, nullable=True)  # JSON string of user IDs to exclude
    custom_filters = db.Column(db.Text, nullable=True)  # JSON string of custom filters
    
    # Delivery preferences
    email_recipients = db.Column(db.Text, nullable=True)  # JSON string of email addresses
    cc_recipients = db.Column(db.Text, nullable=True)  # JSON string of CC email addresses
    report_format = db.Column(db.String(32), default='pdf')  # 'pdf', 'excel', 'csv', 'html'
    
    # Status and tracking
    is_active = db.Column(db.Boolean, default=True)
    last_generated = db.Column(db.DateTime, nullable=True)
    next_generation = db.Column(db.DateTime, nullable=True)
    total_generated = db.Column(db.Integer, default=0)
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = db.relationship('Team', backref='report_schedules')
    manager = db.relationship('User', backref='created_report_schedules')
    
    def __repr__(self):
        return f'<ReportSchedule {self.report_type} for team {self.team_id}>'
    
    def get_next_generation_time(self):
        """Calculate the next report generation time."""
        from datetime import datetime, timedelta
        
        if not self.is_active:
            return None
        
        now = datetime.now()
        
        if self.report_frequency == 'daily':
            next_time = now.replace(hour=self.schedule_time.hour, minute=self.schedule_time.minute, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)
        
        elif self.report_frequency == 'weekly':
            # Find next occurrence of schedule_day
            days_ahead = self._get_days_ahead(self.schedule_day)
            next_time = now.replace(hour=self.schedule_time.hour, minute=self.schedule_time.minute, second=0, microsecond=0)
            next_time += timedelta(days=days_ahead)
        
        elif self.report_frequency == 'monthly':
            # Find next occurrence of schedule_date
            next_time = self._get_next_month_date(self.schedule_date)
            if next_time:
                next_time = next_time.replace(hour=self.schedule_time.hour, minute=self.schedule_time.minute, second=0, microsecond=0)
        
        return next_time
    
    def _get_days_ahead(self, day_name):
        """Get days ahead to next occurrence of day_name."""
        days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
                'friday': 4, 'saturday': 5, 'sunday': 6}
        current_day = datetime.now().weekday()
        target_day = days.get(day_name.lower(), 0)
        
        days_ahead = target_day - current_day
        if days_ahead <= 0:
            days_ahead += 7
        return days_ahead
    
    def _get_next_month_date(self, date_number):
        """Get next month's date for the given date number."""
        from datetime import datetime, timedelta
        from calendar import monthrange
        
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        # Try current month first
        days_in_month = monthrange(current_year, current_month)[1]
        if date_number <= days_in_month:
            target_date = datetime(current_year, current_month, date_number)
            if target_date > now:
                return target_date
        
        # Try next month
        if current_month == 12:
            next_month = 1
            next_year = current_year + 1
        else:
            next_month = current_month + 1
            next_year = current_year
        
        days_in_next_month = monthrange(next_year, next_month)[1]
        if date_number <= days_in_next_month:
            return datetime(next_year, next_month, date_number)
        
        return None

class Call(db.Model):
    """Model for tracking individual call records."""
    __tablename__ = 'calls'
    
    id = db.Column(db.Integer, primary_key=True)
    made_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    
    # Call details
    contact_name = db.Column(db.String(128), nullable=True)
    phone_number = db.Column(db.String(32), nullable=False)
    call_type = db.Column(db.String(32), nullable=False)  # 'outbound', 'inbound', 'follow_up', 'cold_call'
    status = db.Column(db.String(32), nullable=False)  # 'completed', 'missed', 'no_answer', 'voicemail', 'busy'
    duration = db.Column(db.Integer, nullable=True)  # Duration in minutes
    call_notes = db.Column(db.Text, nullable=True)
    
    # Call metadata
    call_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    made_by_user = db.relationship('User', foreign_keys=[made_by], backref='calls_made')
    lead = db.relationship('Lead', backref='calls')
    
    def __repr__(self):
        return f'<Call {self.id} by {self.made_by_user.get_full_name() if self.made_by_user else "Unknown"} to {self.contact_name or self.phone_number}>'
    
    def get_duration_display(self):
        """Get formatted duration display."""
        if not self.duration:
            return "N/A"
        return f"{self.duration}m"
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        status_colors = {
            'completed': 'success',
            'missed': 'danger',
            'no_answer': 'warning',
            'voicemail': 'info',
            'busy': 'secondary'
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_type_color(self):
        """Get Bootstrap color class for call type."""
        type_colors = {
            'outbound': 'primary',
            'inbound': 'success',
            'follow_up': 'info',
            'cold_call': 'warning'
        }
        return type_colors.get(self.call_type, 'secondary')

class TaskComment(db.Model):
    __tablename__ = 'task_comments'
    id = db.Column(db.Integer, primary_key=True)
    
    # Task information
    task_id = db.Column(db.Integer, nullable=False)  # ID of the task being commented on
    task_type = db.Column(db.String(32), nullable=False)  # 'production_task' or 'user_task'
    
    # Comment information
    content = db.Column(db.Text, nullable=False)
    comment_type = db.Column(db.String(32), default='comment')  # 'comment', 'reply', 'status_update'
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('task_comments.id'), nullable=True)  # For replies
    
    # User information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Edit/Delete functionality
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete
    deleted_at = db.Column(db.DateTime, nullable=True)
    original_content = db.Column(db.Text, nullable=True)  # Store original content for audit
    
    # Relationships
    user = db.relationship('User', backref='task_comments')
    parent_comment = db.relationship('TaskComment', remote_side=[id], backref='replies')
    
    def __repr__(self):
        return f'<TaskComment {self.id} on {self.task_type} {self.task_id} by {self.user_id}>'
    
    def get_display_content(self):
        """Get display content (handle deleted comments)"""
        if self.is_deleted:
            return "[Comment deleted]"
        return self.content
    
    def can_edit(self, user_id):
        """Check if user can edit this comment (within 30 minutes)"""
        if self.user_id != user_id:
            return False
        
        # Allow editing within 30 minutes
        from datetime import datetime, timedelta
        time_diff = datetime.now(timezone.utc) - self.created_at
        return time_diff <= timedelta(minutes=30)
    
    def can_delete(self, user_id):
        """Check if user can delete this comment"""
        return self.user_id == user_id

class TaskSession(db.Model):
    __tablename__ = 'task_sessions'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('production_tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_status = db.Column(db.String(32), default='active')  # active, paused, completed, stopped
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    total_duration = db.Column(db.Integer, default=0)  # in seconds
    pause_duration = db.Column(db.Integer, default=0)  # in seconds
    last_activity = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    task = db.relationship('ProductionTask', foreign_keys=[task_id], backref='sessions')
    user = db.relationship('User', backref='task_sessions')
    pauses = db.relationship('TaskSessionPause', backref='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<TaskSession {self.id} for task {self.task_id} by user {self.user_id}>'
    
    def get_active_duration(self):
        """Get current active duration in seconds."""
        if self.session_status == 'completed' or self.session_status == 'stopped':
            return self.total_duration
        
        # Calculate current duration
        current_time = datetime.now(timezone.utc)
        elapsed = (current_time - self.start_time).total_seconds()
        return int(elapsed - self.pause_duration)
    
    def get_formatted_duration(self):
        """Get formatted duration string."""
        duration = self.get_active_duration()
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def is_active(self):
        """Check if session is currently active."""
        return self.session_status == 'active'
    
    def is_paused(self):
        """Check if session is paused."""
        return self.session_status == 'paused'

class TaskSessionPause(db.Model):
    __tablename__ = 'task_session_pauses'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('task_sessions.id'), nullable=False)
    pause_start = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    pause_end = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Integer, default=0)  # in seconds
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<TaskSessionPause {self.id} for session {self.session_id}>'
    
    def get_duration(self):
        """Get pause duration in seconds."""
        if self.pause_end:
            return int((self.pause_end - self.pause_start).total_seconds())
        else:
            # Still paused
            current_time = datetime.now(timezone.utc)
            return int((current_time - self.pause_start).total_seconds())