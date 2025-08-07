# API Documentation & Integration Guide

## 🔌 **API Overview**

The EA CRM provides comprehensive RESTful APIs for all system features, enabling seamless integration with external systems, mobile applications, and third-party services.

## 🔐 **Authentication & Security**

### **Authentication Methods**

#### **Bearer Token Authentication**
```http
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

#### **Session-Based Authentication**
```http
Cookie: session=<session_id>
Content-Type: application/json
```

### **API Security Headers**
```http
X-API-Key: <your_api_key>
X-Request-ID: <unique_request_id>
X-Client-Version: <client_version>
```

## 📊 **Core API Endpoints**

### **Authentication APIs**

#### **Login**
```http
POST /api/auth/login
```

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "Manager",
    "permissions": ["view_leads", "edit_leads", "messenger_send"]
  },
  "expires_in": 3600
}
```

#### **Logout**
```http
POST /api/auth/logout
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

#### **Refresh Token**
```http
POST /api/auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "refresh_token_here"
}
```

### **Lead Management APIs**

#### **Get All Leads**
```http
GET /api/leads
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `status`: Filter by status
- `country`: Filter by country
- `industry`: Filter by industry
- `assigned_to`: Filter by assigned user

**Response:**
```json
{
  "leads": [
    {
      "id": 1,
      "company_name": "Tech Corp",
      "website": "https://techcorp.com",
      "industry": "Technology",
      "status": "New",
      "country": "United States",
      "state": "California",
      "created_at": "2024-01-15T10:30:00Z",
      "assigned_to": {
        "id": 2,
        "username": "sarah_manager"
      },
      "contacts": [
        {
          "id": 1,
          "name": "John Smith",
          "position": "CEO",
          "email": "john@techcorp.com",
          "phone": "+1-555-0123"
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "total_pages": 5,
    "total_items": 100,
    "has_next": true,
    "has_prev": false
  }
}
```

#### **Create New Lead**
```http
POST /api/leads
```

**Request Body:**
```json
{
  "company_name": "New Company",
  "website": "https://newcompany.com",
  "industry": "Manufacturing",
  "country": "Canada",
  "state": "Ontario",
  "contacts": [
    {
      "name": "Jane Doe",
      "position": "Marketing Director",
      "email": "jane@newcompany.com",
      "phone": "+1-555-0456"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "lead": {
    "id": 123,
    "company_name": "New Company",
    "created_at": "2024-01-15T11:00:00Z"
  }
}
```

#### **Update Lead**
```http
PUT /api/leads/{lead_id}
```

**Request Body:**
```json
{
  "company_name": "Updated Company Name",
  "status": "Interested",
  "notes": "Customer showed interest in our services"
}
```

#### **Delete Lead**
```http
DELETE /api/leads/{lead_id}
```

### **Contact Management APIs**

#### **Get Lead Contacts**
```http
GET /api/leads/{lead_id}/contacts
```

#### **Add Contact to Lead**
```http
POST /api/leads/{lead_id}/contacts
```

**Request Body:**
```json
{
  "name": "New Contact",
  "position": "CTO",
  "email": "cto@company.com",
  "phone": "+1-555-0789",
  "linkedin": "https://linkedin.com/in/newcontact"
}
```

### **Follow-up Management APIs**

#### **Get Follow-up History**
```http
GET /api/leads/{lead_id}/follow-ups
```

**Response:**
```json
{
  "follow_ups": [
    {
      "id": 1,
      "follow_up_number": 1,
      "status": "Contacted",
      "notes": "Initial contact made",
      "follow_up_date": "2024-01-10",
      "created_at": "2024-01-10T09:00:00Z"
    }
  ]
}
```

#### **Add Follow-up**
```http
POST /api/leads/{lead_id}/follow-ups
```

**Request Body:**
```json
{
  "follow_up_number": 2,
  "status": "Interested",
  "notes": "Customer requested proposal",
  "follow_up_date": "2024-01-20"
}
```

## 🤖 **AI-Powered APIs**

### **Lead Scoring**
```http
POST /api/ai/score-lead
```

**Request Body:**
```json
{
  "company_name": "Tech Startup",
  "industry": "Technology",
  "website": "https://techstartup.com",
  "contact_info": {
    "email": "contact@techstartup.com",
    "phone": "+1-555-0123"
  }
}
```

**Response:**
```json
{
  "score": 85,
  "confidence": 0.92,
  "factors": {
    "industry_match": 90,
    "contact_quality": 80,
    "website_quality": 85
  },
  "recommendations": [
    "High potential lead - prioritize follow-up",
    "Consider offering demo"
  ]
}
```

### **Intent Detection**
```http
POST /api/ai/detect-intent
```

**Request Body:**
```json
{
  "message": "We're looking for a CRM solution for our sales team"
}
```

**Response:**
```json
{
  "intent": "purchase_interest",
  "confidence": 0.89,
  "entities": {
    "product_type": "CRM",
    "use_case": "sales_team"
  }
}
```

### **Message Generation**
```http
POST /api/ai/generate-message
```

**Request Body:**
```json
{
  "lead_context": {
    "company_name": "Tech Corp",
    "industry": "Technology",
    "contact_name": "John Smith"
  },
  "message_type": "follow_up",
  "tone": "professional"
}
```

**Response:**
```json
{
  "message": "Hi John, I hope this message finds you well. I wanted to follow up on our conversation about Tech Corp's CRM needs...",
  "subject": "Follow-up: Tech Corp CRM Solution"
}
```

## 💬 **Messenger APIs**

### **Get Chat Messages**
```http
GET /api/messenger/room/{room_id}/messages
```

**Query Parameters:**
- `limit`: Number of messages to retrieve
- `before_id`: Get messages before this ID
- `after_id`: Get messages after this ID

**Response:**
```json
{
  "messages": [
    {
      "id": 1,
      "sender": {
        "id": 2,
        "username": "sarah_manager",
        "avatar": "https://example.com/avatar.jpg"
      },
      "content": "Hello team!",
      "message_type": "text",
      "created_at": "2024-01-15T10:30:00Z",
      "mentions": [
        {
          "user_id": 3,
          "username": "john_doe"
        }
      ]
    }
  ],
  "has_more": true
}
```

### **Send Message**
```http
POST /api/messenger/room/{room_id}/messages
```

**Request Body:**
```json
{
  "content": "Hello @john_doe, can you review this task?",
  "message_type": "text",
  "mentions": [3]
}
```

### **Upload File**
```http
POST /api/messenger/room/{room_id}/upload
```

**Request Body:**
```multipart/form-data
file: <file_data>
```

## 📋 **Production Management APIs**

### **Task Management**

#### **Get All Tasks**
```http
GET /api/production/tasks
```

**Query Parameters:**
- `status`: Filter by status
- `priority`: Filter by priority
- `assigned_to`: Filter by assigned user
- `due_date`: Filter by due date

**Response:**
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Logo Design for Client A",
      "description": "Create modern logo design",
      "task_type": "design",
      "priority": "high",
      "status": "in_progress",
      "assigned_to": {
        "id": 2,
        "username": "designer_jane"
      },
      "due_date": "2024-01-20",
      "created_at": "2024-01-15T09:00:00Z",
      "progress": 65
    }
  ]
}
```

#### **Create Task**
```http
POST /api/production/tasks
```

**Request Body:**
```json
{
  "title": "Website Redesign",
  "description": "Complete website redesign for client",
  "task_type": "development",
  "priority": "urgent",
  "assigned_to": 3,
  "due_date": "2024-01-25",
  "client_id": 5
}
```

#### **Update Task Status**
```http
PUT /api/production/tasks/{task_id}/status
```

**Request Body:**
```json
{
  "status": "completed",
  "notes": "Task completed successfully"
}
```

### **AI Task Assignment**
```http
POST /api/production/ai/suggest-assignee
```

**Request Body:**
```json
{
  "task": {
    "title": "Logo Design",
    "task_type": "design",
    "priority": "high",
    "required_skills": ["illustrator", "photoshop"]
  }
}
```

**Response:**
```json
{
  "suggested_assignee": {
    "user_id": 2,
    "username": "designer_jane",
    "confidence": 0.95,
    "reasons": [
      "High design skills",
      "Available capacity",
      "Previous similar tasks completed successfully"
    ]
  }
}
```

## 📊 **Analytics & Reporting APIs**

### **Dashboard Analytics**
```http
GET /api/analytics/dashboard
```

**Response:**
```json
{
  "lead_stats": {
    "total_leads": 1250,
    "new_this_month": 89,
    "converted_this_month": 23,
    "conversion_rate": 25.8
  },
  "performance_stats": {
    "daily_goal_achievement": 85.5,
    "weekly_productivity": 92.3,
    "monthly_target": 78.9
  },
  "team_stats": {
    "total_members": 15,
    "online_members": 12,
    "active_today": 14
  }
}
```

### **Lead Analytics**
```http
GET /api/analytics/leads
```

**Query Parameters:**
- `date_from`: Start date (YYYY-MM-DD)
- `date_to`: End date (YYYY-MM-DD)
- `group_by`: Group by field (status, country, industry)

### **User Performance**
```http
GET /api/analytics/users/{user_id}/performance
```

**Response:**
```json
{
  "user": {
    "id": 2,
    "username": "sarah_manager"
  },
  "metrics": {
    "leads_created": 45,
    "leads_converted": 12,
    "conversion_rate": 26.7,
    "avg_follow_up_time": "2.3 days",
    "productivity_score": 88.5
  },
  "trends": {
    "weekly_leads": [10, 12, 8, 15, 11, 9, 13],
    "weekly_conversions": [3, 4, 2, 5, 3, 2, 4]
  }
}
```

## 🔄 **Webhook Integration**

### **Webhook Configuration**
```http
POST /api/webhooks/configure
```

**Request Body:**
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["lead.created", "lead.updated", "task.completed"],
  "secret": "your_webhook_secret"
}
```

### **Webhook Events**

#### **Lead Created Event**
```json
{
  "event": "lead.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "lead_id": 123,
    "company_name": "New Company",
    "created_by": {
      "id": 2,
      "username": "sarah_manager"
    }
  }
}
```

#### **Task Completed Event**
```json
{
  "event": "task.completed",
  "timestamp": "2024-01-15T14:30:00Z",
  "data": {
    "task_id": 45,
    "title": "Logo Design",
    "completed_by": {
      "id": 3,
      "username": "designer_jane"
    },
    "completion_time": "2.5 hours"
  }
}
```

## 🛠️ **Error Handling**

### **Standard Error Response**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

### **HTTP Status Codes**
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

## 📱 **Mobile API Support**

### **Mobile-Specific Endpoints**
```http
GET /api/mobile/dashboard
GET /api/mobile/leads/summary
POST /api/mobile/leads/quick-add
```

### **Push Notifications**
```http
POST /api/mobile/notifications/register
```

**Request Body:**
```json
{
  "device_token": "device_token_here",
  "platform": "ios",
  "user_id": 2
}
```

## 🔧 **SDK Integration**

### **JavaScript SDK**
```javascript
// Initialize SDK
const crmSDK = new EACRM({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.eacrm.com'
});

// Authenticate
await crmSDK.auth.login({
  username: 'user@example.com',
  password: 'password'
});

// Create lead
const lead = await crmSDK.leads.create({
  company_name: 'New Company',
  website: 'https://newcompany.com'
});

// Listen for real-time updates
crmSDK.messenger.on('message', (message) => {
  console.log('New message:', message);
});
```

### **Python SDK**
```python
from ea_crm import EACRM

# Initialize client
client = EACRM(api_key='your_api_key')

# Authenticate
client.auth.login(username='user@example.com', password='password')

# Create lead
lead = client.leads.create({
    'company_name': 'New Company',
    'website': 'https://newcompany.com'
})

# Get analytics
analytics = client.analytics.get_dashboard()
```

## 📈 **Rate Limiting**

### **Rate Limit Headers**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642233600
```

### **Rate Limit Rules**
- **Authentication**: 5 requests per minute
- **Lead Management**: 100 requests per hour
- **Analytics**: 50 requests per hour
- **Messenger**: 200 requests per hour

## 🔍 **API Testing**

### **Postman Collection**
```json
{
  "info": {
    "name": "EA CRM API",
    "description": "Complete API collection for EA CRM"
  },
  "item": [
    {
      "name": "Authentication",
      "item": [
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/auth/login"
          }
        }
      ]
    }
  ]
}
```

### **cURL Examples**
```bash
# Login
curl -X POST https://api.eacrm.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password"}'

# Get leads
curl -X GET https://api.eacrm.com/api/leads \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create lead
curl -X POST https://api.eacrm.com/api/leads \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"New Company","website":"https://newcompany.com"}'
```

This comprehensive API documentation provides all necessary information for integrating with the EA CRM system, including authentication, data management, AI features, and real-time communication capabilities. 