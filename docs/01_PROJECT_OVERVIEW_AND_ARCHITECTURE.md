# EA CRM - Project Overview & Architecture

## 🏗️ **System Architecture Overview**

The EA CRM is a comprehensive Customer Relationship Management system built with Flask, featuring role-based access control, AI-powered features, real-time messaging, and production management capabilities.

### **Core Technology Stack**
- **Backend**: Flask 2.3.3 with SQLAlchemy ORM
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla + Socket.IO)
- **AI Integration**: OpenRouter API for intelligent features
- **Real-time**: Flask-SocketIO for live communication
- **Deployment**: Gunicorn + Nginx + Supervisor

### **System Components**

#### **1. Core CRM Module**
- Lead management with 3-tier follow-up system
- Contact management with multiple contacts per lead
- Status tracking and filtering capabilities
- Bulk import/export functionality
- Geographic data management (countries, states, timezones)

#### **2. Role-Based Access Control (RBAC)**
- **Admin**: Full system access
- **Manager**: Lead management + moderation
- **User**: Basic lead management
- **Caller**: Lead management + calling features
- **Lead Generator**: Focused on lead generation only
- **Marketing Manager**: Marketing-specific dashboards
- **Production Manager**: Production task management

#### **3. AI-Powered Features**
- Lead scoring and prioritization
- Intent detection and classification
- Smart deduplication
- AI-generated messages
- Relationship mapping
- Productivity pattern analysis

#### **4. Real-Time Communication**
- WhatsApp-style group chat
- @mentions with notifications
- File sharing and media uploads
- Message pinning and reminders
- Online status tracking

#### **5. Production Management**
- Task management with priorities
- Real-time collaboration
- File management system
- Audit logging
- Performance analytics

## 📊 **Database Schema**

### **Core Tables**

#### **Users & Authentication**
```sql
users (id, username, email, password_hash, role_id, created_at, last_login)
roles (id, name, description, permissions)
user_permissions (id, user_id, permission_id)
permissions (id, name, description)
```

#### **Lead Management**
```sql
leads (id, company_name, website, industry, status, country, state, 
       timezone, created_at, updated_at, assigned_to)
contacts (id, lead_id, name, position, phone, email, linkedin, 
          created_at)
follow_up_history (id, lead_id, follow_up_number, status, notes, 
                  follow_up_date, created_at)
```

#### **Production System**
```sql
production_tasks (id, title, description, task_type, priority, status,
                 client_id, assigned_to, due_date, created_at, updated_at)
task_audit_logs (id, task_id, task_type, operation, user_id, field_name,
                old_value, new_value, description, created_at)
```

#### **Messaging System**
```sql
chat_messages (id, sender_id, content, message_type, file_url, room, created_at)
chat_mentions (id, message_id, mentioned_user_id, created_at)
notifications (id, user_id, type, title, message, related_id, is_read, created_at)
user_online_status (id, user_id, is_online, last_seen, session_id)
```

## 🔐 **Security Architecture**

### **Authentication & Authorization**
- Flask-Login for session management
- Role-based permission system
- Route-level access control
- Secure password hashing
- Session timeout management

### **Data Protection**
- SQL injection prevention via SQLAlchemy
- XSS protection with input sanitization
- CSRF protection with Flask-WTF
- File upload security
- Environment variable management

### **API Security**
- Bearer token authentication
- Rate limiting
- Input validation
- Error handling without information leakage

## 🚀 **Deployment Architecture**

### **Development Environment**
```
EA CRM/
├── app/                    # Flask application
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── docs/                   # Documentation
├── instance/               # Database files
├── config.py              # Configuration
├── run.py                 # Development server
└── requirements.txt       # Dependencies
```

### **Production Environment**
```
Server/
├── /home/crmuser/ea_crm/  # Application directory
├── /etc/nginx/sites-available/ea_crm  # Nginx config
├── /etc/supervisor/conf.d/ea_crm.conf # Supervisor config
├── /var/log/ea_crm/       # Application logs
└── /home/crmuser/backups/ # Database backups
```

## 🔄 **Data Flow Architecture**

### **Lead Management Flow**
1. **Lead Creation**: Manual entry or bulk import
2. **AI Processing**: Scoring, deduplication, intent detection
3. **Assignment**: Automatic or manual assignment
4. **Follow-up Tracking**: 3-tier system with status updates
5. **Conversion Tracking**: Status changes and analytics

### **Production Workflow**
1. **Task Creation**: Manager creates production tasks
2. **AI Assignment**: Smart task assignment suggestions
3. **Real-time Collaboration**: Chat and file sharing
4. **Progress Tracking**: Status updates and audit logs
5. **Completion**: Task closure with performance metrics

### **Messaging Flow**
1. **Message Creation**: User composes message
2. **Real-time Delivery**: Socket.IO transmission
3. **Notification System**: Sound, toast, and desktop alerts
4. **Mention Processing**: @user detection and notifications
5. **File Handling**: Secure upload and sharing

## 📈 **Performance Architecture**

### **Caching Strategy**
- Redis for session storage
- Database query optimization
- Static file caching
- CDN integration for assets

### **Scalability Considerations**
- Horizontal scaling with load balancers
- Database connection pooling
- Asynchronous task processing
- Microservices architecture ready

### **Monitoring & Logging**
- Application performance monitoring
- Error tracking and alerting
- User activity analytics
- System health checks

## 🔧 **Configuration Management**

### **Environment Variables**
```env
FLASK_ENV=production
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///instance/leads.db
REDIS_URL=redis://localhost:6379/0
OPENROUTER_API_KEY=your-api-key
```

### **Feature Flags**
- AI features enable/disable
- Real-time features toggle
- Debug mode control
- Maintenance mode

## 🧪 **Testing Architecture**

### **Test Categories**
- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **End-to-End Tests**: User workflow testing
- **Performance Tests**: Load and stress testing

### **Test Coverage**
- Core CRM functionality
- Role-based access control
- AI feature integration
- Real-time communication
- Production management

## 📚 **Documentation Structure**

This comprehensive documentation is organized into 5 main files:
1. **Project Overview & Architecture** (this file)
2. **User Roles & Permissions Guide**
3. **API Documentation & Integration**
4. **Deployment & DevOps Guide**
5. **Features & Functionality Reference**

Each file provides detailed information for different aspects of the system, ensuring complete coverage of all features and capabilities. 