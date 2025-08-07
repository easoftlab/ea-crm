from . import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, Text
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import os

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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

    contacts = db.relationship('Contact', backref='lead', cascade='all, delete-orphan', lazy=True)
    followup_history = db.relationship('FollowUpHistory', backref='lead', cascade='all, delete-orphan', lazy=True, order_by='FollowUpHistory.followup_number')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_leads')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='updated_leads')

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

class ScrapedLead(db.Model):
    __bind_key__ = 'scrap'
    __tablename__ = 'scraped_leads'
    id = Column(Integer, primary_key=True)
    company_name = Column(String(256), nullable=False)
    website = Column(String(256))
    industry = Column(String(128))
    hiring = Column(String(16))  # 'Yes', 'No', or 'Unknown'
    key_person = Column(String(128))
    role = Column(String(128))
    linkedin_url = Column(String(256))
    about = Column(String(1024))  # New: About section
    recent_post = Column(String(1024))  # New: Most recent post
    ai_message = Column(String(1024))  # The AI-generated message sent
    message_variant = Column(String(32))  # A/B test group or template name
    message_reply = Column(String(1024))  # The reply received, if any
    date_scraped = Column(DateTime, default=datetime.utcnow)
    status = Column(String(32), default='new') 

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
    projection_type = db.Column(db.String(32), nullable=False)  # 'revenue', 'work_volume', 'tasks'
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