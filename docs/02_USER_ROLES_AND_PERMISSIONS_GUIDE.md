# User Roles & Permissions Guide

## 👥 **Role-Based Access Control (RBAC) System**

The EA CRM implements a comprehensive role-based access control system that defines user permissions and access levels across all system features.

## 🎯 **Available Roles**

### **1. Administrator (Admin)**
**Full system access with complete control**

**Permissions:**
- ✅ All system features
- ✅ User management and role assignment
- ✅ System configuration
- ✅ Database administration
- ✅ Analytics and reporting
- ✅ Messenger administration
- ✅ Production management

**Access Areas:**
- Complete CRM functionality
- User administration panel
- System settings and configuration
- All dashboards and reports
- Messenger moderation tools
- Production task management

### **2. Manager**
**Lead management with moderation capabilities**

**Permissions:**
- ✅ Lead management (CRUD operations)
- ✅ Contact management
- ✅ Follow-up tracking
- ✅ Messenger moderation
- ✅ Team management
- ✅ Basic reporting
- ❌ User administration
- ❌ System configuration

**Access Areas:**
- Lead dashboard and management
- Contact management
- Follow-up system
- Messenger with moderation tools
- Team performance reports
- Production task oversight

### **3. User (Standard)**
**Basic lead management capabilities**

**Permissions:**
- ✅ View and edit assigned leads
- ✅ Add new leads
- ✅ Contact management
- ✅ Basic messenger access
- ✅ Personal dashboard
- ❌ Lead deletion
- ❌ System-wide reports
- ❌ User management

**Access Areas:**
- Personal lead dashboard
- Lead creation and editing
- Contact management
- Basic messenger functionality
- Personal performance metrics

### **4. Caller**
**Lead management with calling features**

**Permissions:**
- ✅ Lead management (CRUD)
- ✅ Contact management
- ✅ Call tracking and logging
- ✅ Messenger access
- ✅ Personal dashboard
- ✅ Call analytics
- ❌ System administration

**Access Areas:**
- Lead management with call tracking
- Contact information management
- Call history and analytics
- Messenger for team communication
- Personal performance dashboard

### **5. Lead Generator**
**Focused exclusively on lead generation**

**Permissions:**
- ✅ Add new leads only
- ✅ Personal lead generation dashboard
- ✅ Lead generation projections
- ✅ Personal performance metrics
- ❌ View existing leads
- ❌ Edit or delete leads
- ❌ Follow-up tracking
- ❌ Messenger access

**Access Areas:**
- Lead generation forms
- Personal lead generation dashboard
- Lead generation projections
- Personal performance tracking

### **6. Marketing Manager**
**Marketing-specific dashboards and analytics**

**Permissions:**
- ✅ Marketing dashboard access
- ✅ Team performance analytics
- ✅ Lead generation metrics
- ✅ Campaign tracking
- ✅ Marketing reports
- ✅ Team member management
- ❌ Production management
- ❌ System administration

**Access Areas:**
- Marketing dashboard
- Team performance analytics
- Lead generation tracking
- Campaign management
- Marketing reports

### **7. Production Manager**
**Production task management and oversight**

**Permissions:**
- ✅ Production dashboard access
- ✅ Task creation and assignment
- ✅ Team collaboration tools
- ✅ File management
- ✅ Production analytics
- ✅ Task audit logging
- ❌ Lead management
- ❌ System administration

**Access Areas:**
- Production dashboard
- Task management system
- Team collaboration tools
- File management system
- Production analytics

## 🔐 **Permission System**

### **Core Permissions**

#### **Lead Management Permissions**
```python
# Lead-related permissions
'view_leads'          # View lead information
'add_leads'           # Create new leads
'edit_leads'          # Modify existing leads
'delete_leads'        # Remove leads
'manage_leads'        # Full lead management
'export_leads'        # Export lead data
'import_leads'        # Import lead data
```

#### **Contact Management Permissions**
```python
# Contact-related permissions
'view_contacts'       # View contact information
'add_contacts'        # Add new contacts
'edit_contacts'       # Modify contacts
'delete_contacts'     # Remove contacts
'manage_contacts'     # Full contact management
```

#### **Messenger Permissions**
```python
# Messenger-related permissions
'messenger_admin'     # Full messenger control
'messenger_moderate'  # Content moderation
'messenger_send'      # Send messages
'messenger_read'      # Read-only access
```

#### **Production Permissions**
```python
# Production-related permissions
'view_tasks'          # View production tasks
'create_tasks'        # Create new tasks
'edit_tasks'          # Modify tasks
'delete_tasks'        # Remove tasks
'assign_tasks'        # Assign tasks to users
'manage_tasks'        # Full task management
```

#### **System Permissions**
```python
# System-level permissions
'admin_access'        # Full system access
'user_management'     # Manage users and roles
'system_config'       # System configuration
'reporting'           # Access to reports
'analytics'           # Analytics access
```

### **Permission Implementation**

#### **Route Protection**
```python
from functools import wraps
from flask_login import current_user

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission):
                return render_template('errors/403.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage in routes
@app.route('/leads')
@permission_required('view_leads')
def view_leads():
    # Route implementation
    pass
```

#### **Template-Level Access Control**
```html
<!-- Check permissions in templates -->
{% if current_user.has_permission('add_leads') %}
    <a href="{{ url_for('add_lead') }}" class="btn btn-primary">
        Add New Lead
    </a>
{% endif %}

{% if current_user.has_permission('messenger_admin') %}
    <div class="admin-controls">
        <!-- Admin controls -->
    </div>
{% endif %}
```

## 🎨 **Role-Specific Dashboards**

### **Lead Generator Dashboard**
```html
<!-- Lead Generator specific dashboard -->
<div class="dashboard-lead-generator">
    <div class="welcome-section">
        <h2>Welcome, Lead Generator!</h2>
        <p>Focus on generating quality leads for the organization.</p>
    </div>
    
    <div class="kpi-cards">
        <div class="card bg-primary">
            <h4>Today's Leads</h4>
            <h2>{{ today_leads }}</h2>
        </div>
        <div class="card bg-info">
            <h4>Week's Leads</h4>
            <h2>{{ week_leads }}</h2>
        </div>
        <div class="card bg-success">
            <h4>Month's Leads</h4>
            <h2>{{ month_leads }}</h2>
        </div>
    </div>
    
    <div class="quick-actions">
        <a href="{{ url_for('add_lead') }}" class="btn btn-primary">
            Add New Lead
        </a>
        <a href="{{ url_for('set_projection') }}" class="btn btn-secondary">
            Set Projection
        </a>
    </div>
</div>
```

### **Production Manager Dashboard**
```html
<!-- Production Manager dashboard -->
<div class="dashboard-production">
    <div class="task-overview">
        <h3>Production Tasks</h3>
        <div class="task-stats">
            <div class="stat pending">{{ pending_tasks }}</div>
            <div class="stat in-progress">{{ in_progress_tasks }}</div>
            <div class="stat completed">{{ completed_tasks }}</div>
        </div>
    </div>
    
    <div class="team-chat">
        <h3>Team Communication</h3>
        <div id="chat-container">
            <!-- Real-time chat interface -->
        </div>
    </div>
    
    <div class="quick-actions">
        <a href="{{ url_for('create_task') }}" class="btn btn-primary">
            Create Task
        </a>
        <a href="{{ url_for('team_analytics') }}" class="btn btn-secondary">
            Team Analytics
        </a>
    </div>
</div>
```

## 🔄 **Role Assignment Process**

### **Creating New Users**
```python
# User creation with role assignment
def create_user(username, email, password, role_name):
    user = User(
        username=username,
        email=email,
        role_id=get_role_id(role_name)
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    # Assign role-specific permissions
    assign_role_permissions(user, role_name)
```

### **Role Modification**
```python
# Changing user roles
def change_user_role(user_id, new_role_name):
    user = User.query.get(user_id)
    if user:
        user.role_id = get_role_id(new_role_name)
        db.session.commit()
        
        # Update permissions
        update_user_permissions(user, new_role_name)
```

### **Permission Checking**
```python
# Check user permissions
def has_permission(user, permission_name):
    return permission_name in user.permissions

# Check multiple permissions
def has_any_permission(user, permission_list):
    return any(has_permission(user, perm) for perm in permission_list)

# Check all permissions
def has_all_permissions(user, permission_list):
    return all(has_permission(user, perm) for perm in permission_list)
```

## 📊 **Role Analytics**

### **Permission Usage Tracking**
```python
# Track permission usage
def log_permission_usage(user, permission, action):
    log_entry = PermissionLog(
        user_id=user.id,
        permission=permission,
        action=action,
        timestamp=datetime.utcnow()
    )
    db.session.add(log_entry)
    db.session.commit()
```

### **Role Performance Metrics**
```python
# Generate role-based analytics
def get_role_analytics(role_name):
    users = User.query.filter_by(role=role_name).all()
    
    analytics = {
        'total_users': len(users),
        'active_users': len([u for u in users if u.is_active]),
        'avg_session_duration': calculate_avg_session(users),
        'most_used_features': get_most_used_features(users),
        'performance_metrics': get_performance_metrics(users)
    }
    
    return analytics
```

## 🛡️ **Security Best Practices**

### **Permission Validation**
- Always validate permissions on both client and server side
- Use parameterized queries to prevent SQL injection
- Implement rate limiting for sensitive operations
- Log all permission-related activities

### **Session Management**
- Implement session timeout
- Secure session storage
- Regular session cleanup
- Multi-factor authentication for admin roles

### **Data Access Control**
- Row-level security for sensitive data
- Encrypt sensitive information
- Regular permission audits
- Principle of least privilege

## 🔧 **Configuration Management**

### **Role Configuration File**
```yaml
# roles_config.yaml
roles:
  admin:
    description: "Full system access"
    permissions:
      - admin_access
      - user_management
      - system_config
      - all_features
  
  manager:
    description: "Lead management with moderation"
    permissions:
      - manage_leads
      - messenger_moderate
      - basic_reporting
  
  lead_generator:
    description: "Lead generation focus"
    permissions:
      - add_leads
      - view_own_performance
```

### **Permission Matrix**
```python
# permission_matrix.py
PERMISSION_MATRIX = {
    'admin': [
        'admin_access', 'user_management', 'system_config',
        'all_features', 'messenger_admin', 'manage_tasks'
    ],
    'manager': [
        'manage_leads', 'messenger_moderate', 'basic_reporting',
        'view_tasks', 'edit_tasks'
    ],
    'user': [
        'view_leads', 'add_leads', 'edit_leads',
        'messenger_send', 'view_own_performance'
    ],
    'caller': [
        'manage_leads', 'messenger_send', 'call_tracking',
        'view_own_performance'
    ],
    'lead_generator': [
        'add_leads', 'view_own_performance'
    ]
}
```

This comprehensive role and permission system ensures secure, scalable access control across all system features while maintaining flexibility for future enhancements. 