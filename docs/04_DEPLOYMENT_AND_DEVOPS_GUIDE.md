# Deployment & DevOps Guide

## 🚀 **Deployment Overview**

The EA CRM system supports multiple deployment strategies, from local development to production environments with CI/CD pipelines, containerization, and cloud deployment options.

## 🏗️ **System Requirements**

### **Minimum Requirements**
- **CPU**: 2 cores (4+ recommended)
- **RAM**: 4GB (8GB+ recommended)
- **Storage**: 50GB SSD
- **OS**: Ubuntu 20.04 LTS, CentOS 8+, or Windows Server 2019+

### **Recommended Production Requirements**
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 200GB+ SSD with RAID
- **Network**: 100Mbps+ bandwidth
- **OS**: Ubuntu 22.04 LTS

### **Software Dependencies**
```bash
# Core System
Python 3.9+
PostgreSQL 13+ or MySQL 8+
Redis 6+
Nginx 1.18+
Supervisor or systemd

# Python Dependencies
Flask 2.3.3+
SQLAlchemy 2.0+
Flask-SocketIO 5.3+
Gunicorn 21.2+
```

## 🔧 **Environment Setup**

### **Troubleshooting Common Issues**

#### **Connection Issues:**
1. **Port 65002 blocked:** Try using a VPN or contact your hosting provider
2. **Authentication failed:** Double-check username and password
3. **Connection timeout:** Check your internet connection

#### **Application Issues:**
1. **Permission denied:** Ensure proper file permissions are set
2. **Module not found:** Verify all dependencies are installed
3. **Database connection failed:** Check database configuration and connectivity
4. **Port already in use:** Check if another application is using the same port

#### **API Session Issues:**
1. **APIs redirect to login:** Check CSRF configuration and session settings
2. **Session not persisting:** Verify session configuration in `app/__init__.py`
3. **CSRF token errors:** Ensure API endpoints are properly exempted from CSRF

#### **Performance Issues:**
1. **Slow response times:** Check database queries and indexing
2. **High memory usage:** Monitor application resource usage
3. **Connection timeouts:** Verify network connectivity and firewall settings

### **Testing & Quality Assurance**

#### **Comprehensive Testing Strategy**
The EA CRM system includes a comprehensive testing framework to ensure reliability and functionality:

**Test Categories:**
- **Backend Testing**: API endpoints, database operations, authentication
- **Frontend Testing**: UI components, user interactions, real-time features
- **Integration Testing**: End-to-end workflows, data flow between components
- **Performance Testing**: Load testing, response times, resource usage

**Testing Tools:**
```bash
# Install testing dependencies
pip install pytest pytest-cov pytest-flask

# Run comprehensive tests
python -m pytest tests/ -v --cov=app --cov-report=html

# Run specific test categories
python -m pytest tests/test_api.py -v
python -m pytest tests/test_frontend.py -v
python -m pytest tests/test_integration.py -v
```

**Test Report Example:**
```markdown
# Comprehensive Messenger Testing Report

## 🎯 EXECUTIVE SUMMARY
- **Application Status**: ✅ RUNNING
- **Backend APIs**: ⚠️ PARTIALLY WORKING
- **Frontend Features**: 🔄 NEEDS TESTING
- **Database**: ✅ HEALTHY

## 📊 TEST RESULTS SUMMARY

### ✅ WORKING COMPONENTS
- Database Connection: ✅ Working
- User Authentication: ✅ Users exist and are properly configured
- Role System: ✅ Roles and permissions are correctly set up
- Messenger Tables: ✅ All messenger tables are created
- Flask Application: ✅ Running successfully
- Socket.IO: ✅ Configured and working
- Login System: ✅ Users can log in successfully
- Session Management: ✅ Basic session functionality working

### ⚠️ PARTIALLY WORKING COMPONENTS
- API Endpoints: ⚠️ Session not persisting for API calls
- API Responses: ⚠️ Returning HTML instead of JSON
- CSRF Protection: ⚠️ May be interfering with API calls

### ❌ ISSUES IDENTIFIED
- API Session Persistence: APIs redirect to login page even after successful login
- CSRF Token Handling: CSRF tokens may not be properly handled in API requests
- Frontend Feature Testing: Cannot test frontend features due to API issues
```

#### **Testing Checklist**
```markdown
### Backend Testing
- [x] Database connectivity
- [x] User authentication
- [x] Role and permission system
- [x] Basic API endpoint accessibility
- [ ] API session persistence
- [ ] API JSON responses
- [ ] Socket.IO authentication
- [ ] Error handling

### Frontend Testing (Pending API Fixes)
- [ ] Messenger page load
- [ ] Message sending
- [ ] File upload functionality
- [ ] Emoji picker
- [ ] Message reactions
- [ ] Create group functionality
- [ ] Media gallery access
- [ ] Search functionality
- [ ] Pin messages
- [ ] Online users display
- [ ] Recent conversations

### Integration Testing
- [ ] Real-time messaging
- [ ] File upload and sharing
- [ ] Group creation and management
- [ ] Message persistence
- [ ] User status updates
```

### **Development Environment**

#### **Local Development Setup**
```bash
# Clone repository
git clone https://github.com/your-org/ea-crm.git
cd ea-crm

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python scripts/db_init.py

# Run development server
python run.py
```

#### **Development Configuration**
```env
# .env for development
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev-secret-key
DATABASE_URL=sqlite:///instance/leads.db
REDIS_URL=redis://localhost:6379/0
OPENROUTER_API_KEY=your_api_key
```

### **Production Environment**

#### **SSH Connection Setup**

**Server Details:**
- **IP Address:** 145.223.77.49
- **Port:** 65002 (non-standard port)
- **Username:** u539052962
- **Password:** Emon_@17711

**Connection Methods:**

**Option 1: Command Line (Windows/Mac/Linux)**
```bash
# Windows (PowerShell/Command Prompt)
ssh -p 65002 u539052962@145.223.77.49

# Mac/Linux Terminal
ssh -p 65002 u539052962@145.223.77.49
```

**Option 2: PuTTY (Windows)**
1. Download PuTTY from: https://www.putty.org/
2. Open PuTTY
3. Enter connection details:
   - **Host Name:** 145.223.77.49
   - **Port:** 65002
4. Click "Open"
5. Enter username: `u539052962`
6. Enter password: `Emon_@17711`

**Option 3: VS Code (Recommended)**
1. Install VS Code
2. Install "Remote - SSH" extension
3. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
4. Type "Remote-SSH: Connect to Host"
5. Enter: `u539052962@145.223.77.49:65002`

#### **Server Preparation**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx redis-server supervisor git

# Create application user
sudo useradd -m -s /bin/bash crmuser
sudo usermod -aG sudo crmuser
sudo passwd crmuser
```

#### **Application Deployment**
```bash
# Switch to application user
sudo -u crmuser bash

# Clone repository
git clone https://github.com/your-org/ea-crm.git /home/crmuser/ea_crm
cd /home/crmuser/ea_crm

#### **Step-by-Step Setup Commands**

Once connected to the server, run these commands:

**Step 1: Navigate to CRM Directory**
```bash
cd crm
```

**Step 2: Verify Files Are Present**
```bash
ls -la
```

You should see:
- `app/` (directory)
- `config.py`
- `requirements.txt`
- `wsgi.py`
- `quick_setup.sh`
- `.htaccess`

**Step 3: Run Quick Setup**
```bash
chmod +x quick_setup.sh
./quick_setup.sh
```

**Step 4: If Quick Setup Fails, Run Manual Commands**
```bash
# Set permissions
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
chmod 755 instance/ 2>/dev/null || mkdir -p instance
chmod 755 app/static/uploads/ 2>/dev/null || mkdir -p app/static/uploads

# Create directories
mkdir -p instance
mkdir -p app/static/uploads/profiles
mkdir -p logs

# Install dependencies
python3 -m pip install -r requirements.txt

# Create environment file
cat > .env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=production
FLASK_APP=wsgi.py
EOF

# Test application
python3 wsgi.py
```

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
nano .env  # Configure production settings
```

## 🐳 **Docker Deployment**

### **Dockerfile**
```dockerfile
# Dockerfile for EA CRM
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 crmuser && chown -R crmuser:crmuser /app
USER crmuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:application"]
```

### **Docker Compose**
```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://crmuser:password@db:5432/eacrm
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/app/static/uploads
      - ./logs:/app/logs

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=eacrm
      - POSTGRES_USER=crmuser
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
```

### **Docker Deployment Commands**
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f web

# Scale application
docker-compose up -d --scale web=3

# Update application
docker-compose pull
docker-compose up -d
```

## ☁️ **Cloud Deployment**

### **AWS Deployment**

#### **EC2 Setup**
```bash
# Launch EC2 instance
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --key-name your-key-pair \
    --security-group-ids sg-12345678 \
    --subnet-id subnet-12345678

# Connect to instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Deploy application
git clone https://github.com/your-org/ea-crm.git
cd ea-crm
docker-compose up -d
```

#### **RDS Database Setup**
```bash
# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier eacrm-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username admin \
    --master-user-password your-password \
    --allocated-storage 20

# Update application configuration
DATABASE_URL=postgresql://admin:your-password@eacrm-db.region.rds.amazonaws.com:5432/eacrm
```

#### **Load Balancer Setup**
```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
    --name eacrm-alb \
    --subnets subnet-12345678 subnet-87654321 \
    --security-groups sg-12345678

# Create target group
aws elbv2 create-target-group \
    --name eacrm-tg \
    --protocol HTTP \
    --port 5000 \
    --vpc-id vpc-12345678

# Register targets
aws elbv2 register-targets \
    --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/eacrm-tg \
    --targets Id=i-12345678
```

### **Google Cloud Platform**

#### **GKE Deployment**
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ea-crm
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ea-crm
  template:
    metadata:
      labels:
        app: ea-crm
    spec:
      containers:
      - name: ea-crm
        image: gcr.io/your-project/ea-crm:latest
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: ea-crm-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: ea-crm-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: ea-crm-service
spec:
  selector:
    app: ea-crm
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer
```

#### **GKE Deployment Commands**
```bash
# Create cluster
gcloud container clusters create ea-crm-cluster \
    --zone us-central1-a \
    --num-nodes 3

# Deploy application
kubectl apply -f k8s-deployment.yaml

# Scale deployment
kubectl scale deployment ea-crm --replicas=5

# View logs
kubectl logs -f deployment/ea-crm
```

## 🔄 **CI/CD Pipeline**

### **GitHub Actions Workflow**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run tests
      run: |
        python -m pytest tests/ -v --cov=app

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v4
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /home/crmuser/ea_crm
          git pull origin main
          source venv/bin/activate
          pip install -r requirements.txt
          python deploy/deploy_script.py
          sudo supervisorctl restart ea_crm
          sudo systemctl reload nginx
```

### **Jenkins Pipeline**
```groovy
// Jenkinsfile
pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Test') {
            steps {
                sh 'python -m venv venv'
                sh 'source venv/bin/activate && pip install -r requirements.txt'
                sh 'source venv/bin/activate && python -m pytest tests/'
            }
        }
        
        stage('Build') {
            steps {
                script {
                    docker.build("ea-crm:${env.BUILD_NUMBER}")
                }
            }
        }
        
        stage('Deploy') {
            steps {
                script {
                    docker.withRegistry('https://registry.example.com', 'registry-credentials') {
                        docker.image("ea-crm:${env.BUILD_NUMBER}").push()
                    }
                }
            }
        }
    }
}
```

## 📊 **Monitoring & Logging**

### **Application Monitoring**

#### **Prometheus Configuration**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ea-crm'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

#### **Grafana Dashboard**
```json
{
  "dashboard": {
    "title": "EA CRM Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      }
    ]
  }
}
```

### **Logging Configuration**
```python
# logging_config.py
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # File handler
    file_handler = RotatingFileHandler(
        'logs/ea_crm.log', 
        maxBytes=10240000, 
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    app.logger.addHandler(console_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('EA CRM startup')
```

## 🔒 **Security Configuration**

### **SSL/TLS Setup**
```nginx
# nginx-ssl.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### **Firewall Configuration**
```bash
# UFW firewall setup
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# iptables for advanced rules
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP
```

## 🔄 **Backup & Recovery**

### **Database Backup**
```bash
#!/bin/bash
# backup_script.sh

# PostgreSQL backup
pg_dump -h localhost -U crmuser eacrm > /backups/eacrm_$(date +%Y%m%d_%H%M%S).sql

# SQLite backup
cp /home/crmuser/ea_crm/instance/leads.db /backups/leads_$(date +%Y%m%d_%H%M%S).db

# Upload to cloud storage
aws s3 cp /backups/ s3://your-backup-bucket/ --recursive --exclude "*" --include "*.sql" --include "*.db"

# Clean old backups (keep 30 days)
find /backups -name "*.sql" -mtime +30 -delete
find /backups -name "*.db" -mtime +30 -delete
```

### **Application Backup**
```bash
#!/bin/bash
# app_backup.sh

# Backup application files
tar -czf /backups/app_$(date +%Y%m%d_%H%M%S).tar.gz \
    /home/crmuser/ea_crm/app \
    /home/crmuser/ea_crm/migrations \
    /home/crmuser/ea_crm/static \
    /home/crmuser/ea_crm/templates

# Backup configuration
cp /home/crmuser/ea_crm/.env /backups/env_$(date +%Y%m%d_%H%M%S).backup
```

## 🚨 **Disaster Recovery**

### **Recovery Procedures**
```bash
#!/bin/bash
# recovery_script.sh

# Stop application
sudo supervisorctl stop ea_crm

# Restore database
psql -h localhost -U crmuser eacrm < /backups/eacrm_20240115_120000.sql

# Restore application files
tar -xzf /backups/app_20240115_120000.tar.gz -C /home/crmuser/ea_crm/

# Restore configuration
cp /backups/env_20240115_120000.backup /home/crmuser/ea_crm/.env

# Start application
sudo supervisorctl start ea_crm
```

## 📈 **Performance Optimization**

### **Gunicorn Configuration**
```python
# gunicorn.conf.py
bind = "0.0.0.0:5000"
workers = 4
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
preload_app = True
```

### **Nginx Optimization**
```nginx
# nginx-optimized.conf
worker_processes auto;
worker_connections 1024;

http {
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    
    upstream ea_crm {
        server 127.0.0.1:5000;
        server 127.0.0.1:5001;
        server 127.0.0.1:5002;
        server 127.0.0.1:5003;
    }
    
    server {
        listen 80;
        server_name your-domain.com;
        
        location / {
            proxy_pass http://ea_crm;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /static {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

This comprehensive deployment guide covers all aspects of deploying the EA CRM system, from local development to production environments with advanced monitoring, security, and disaster recovery procedures. 