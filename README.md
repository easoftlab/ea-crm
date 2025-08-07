# EA CRM - Enterprise Customer Relationship Management System

## 🚀 **Project Overview**

EA CRM is a comprehensive, AI-powered customer relationship management system designed for modern businesses. Built with Flask and featuring real-time messaging, AI-driven lead scoring, and advanced analytics, it provides everything needed to manage customer relationships effectively.

## ✨ **Key Features**

### 🎯 **Core CRM Capabilities**
- **Lead Management**: Complete lead lifecycle management with advanced filtering
- **Contact Management**: Multi-contact support with interaction history
- **Follow-up System**: 3-tier follow-up tracking with color-coded history
- **Real-time Messaging**: WhatsApp-style messenger with file sharing
- **Production Management**: Task management with AI-powered assignment

### 🤖 **AI-Powered Features**
- **Lead Scoring**: Machine learning-based lead prioritization
- **Intent Detection**: Automatic classification of lead intentions
- **Smart Deduplication**: Intelligent duplicate detection and merging
- **AI Message Generation**: Automated outreach message creation
- **Relationship Mapping**: Advanced lead relationship analysis

### 📊 **Analytics & Reporting**
- **Real-time Dashboards**: Live performance metrics and KPIs
- **Advanced Analytics**: Comprehensive reporting and insights
- **Role-based Views**: Customized dashboards for different user roles
- **Export Capabilities**: Data export to CSV/Excel formats

## 🛠️ **Technology Stack**

- **Backend**: Flask 2.3.3, Python 3.9+
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Real-time**: Socket.IO, Flask-SocketIO
- **AI/ML**: OpenRouter API integration
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Deployment**: Docker, Nginx, Gunicorn

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.9 or higher
- Git
- pip (Python package manager)

### **Installation**

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/ea-crm.git
   cd ea-crm
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   python scripts/db_init.py
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Access the application**
   - Open your browser and go to `http://localhost:5000`
   - Default admin credentials: `admin@example.com` / `password`

## 📚 **Documentation**

Comprehensive documentation is available in the `/docs` directory:

- **[📋 Project Overview & Architecture](docs/01_PROJECT_OVERVIEW_AND_ARCHITECTURE.md)** - System architecture, technology stack, and database schema
- **[👥 User Roles & Permissions](docs/02_USER_ROLES_AND_PERMISSIONS_GUIDE.md)** - Complete RBAC system documentation
- **[🔌 API Documentation & Integration](docs/03_API_DOCUMENTATION_AND_INTEGRATION.md)** - RESTful API reference and integration guides
- **[🚀 Deployment & DevOps](docs/04_DEPLOYMENT_AND_DEVOPS_GUIDE.md)** - Production deployment, CI/CD, and monitoring
- **[⚡ Features & Functionality](docs/05_FEATURES_AND_FUNCTIONALITY_REFERENCE.md)** - Complete feature reference and usage guides

## 🎯 **User Roles**

The system supports multiple user roles with different permissions:

- **Admin**: Full system access and user management
- **Manager**: Team oversight and advanced analytics
- **User**: Standard CRM operations
- **Caller**: Lead calling and follow-up management
- **Lead Generator**: Lead creation and initial qualification
- **Marketing Manager**: Campaign management and analytics
- **Production Manager**: Task and project management

## 🔧 **Development**

### **Running Tests**
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-flask

# Run comprehensive tests
python -m pytest tests/ -v --cov=app --cov-report=html

# Run specific test categories
python -m pytest tests/test_api.py -v
python -m pytest tests/test_frontend.py -v
```

### **Code Structure**
```
ea-crm/
├── app/                    # Main application package
│   ├── ai/                # AI-powered features
│   ├── static/            # Static files (CSS, JS, images)
│   ├── templates/         # HTML templates
│   └── __init__.py        # Flask app initialization
├── docs/                  # Comprehensive documentation
├── migrations/            # Database migration scripts
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── deploy/                # Deployment configurations
├── config.py              # Application configuration
├── requirements.txt       # Python dependencies
└── run.py                 # Development server entry point
```

## 🚀 **Deployment**

### **Quick Deployment to Hostinger**

1. **Set up GitHub repository** with your code
2. **Configure GitHub Secrets**:
   - `FTP_SERVER`: Your Hostinger FTP server
   - `FTP_USERNAME`: Your Hostinger FTP username
   - `FTP_PASSWORD`: Your Hostinger FTP password
3. **Push to main branch** - automatic deployment will trigger

### **Manual Deployment**
See [Deployment & DevOps Guide](docs/04_DEPLOYMENT_AND_DEVOPS_GUIDE.md) for detailed instructions.

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

- **Documentation**: Check the `/docs` directory for comprehensive guides
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Testing**: Run the test suite to verify functionality
- **Deployment**: Follow the deployment guide for production setup

## 🔄 **Version History**

- **v2.0.0**: AI-powered features, real-time messaging, advanced analytics
- **v1.5.0**: Role-based access control, production management
- **v1.0.0**: Core CRM functionality, lead management, follow-up system

---

**Built with ❤️ for modern businesses** 