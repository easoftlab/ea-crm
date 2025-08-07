# EA CRM Deployment Guide

## 🚀 **Quick Deployment**

This guide provides essential deployment information for the EA CRM system. For comprehensive documentation, see the `/docs` directory.

## 📋 **Prerequisites**

- Hostinger hosting account
- GitHub repository with your code
- SSH access to your server

## 🔧 **Server Setup**

### **SSH Connection Details**
- **IP Address:** 145.223.77.49
- **Port:** 65002
- **Username:** u539052962
- **Password:** Emon_@17711

### **Connection Commands**
```bash
# Command line (Windows/Mac/Linux)
ssh -p 65002 u539052962@145.223.77.49

# VS Code (Recommended)
# Install "Remote - SSH" extension
# Connect to: u539052962@145.223.77.49:65002
```

## 🚀 **CI/CD Pipeline Setup**

### **1. GitHub Repository Setup**
1. Push your code to GitHub
2. Configure GitHub Secrets:
   - `FTP_SERVER`: Your Hostinger FTP server
   - `FTP_USERNAME`: Your Hostinger FTP username
   - `FTP_PASSWORD`: Your Hostinger FTP password

### **2. Automatic Deployment**
- Push to `main` branch triggers automatic deployment
- Deployment package includes: `app/`, `migrations/`, `static/`, `templates/`, `.py` files, `requirements.txt`
- Files are deployed to `/public_html/` on Hostinger

### **3. Database Migrations**
- Automatic migrations run post-deployment
- Backup created before each migration
- Migration files in `/migrations/` directory

## 📚 **Documentation**

For detailed deployment information, see:
- **[Deployment & DevOps Guide](docs/04_DEPLOYMENT_AND_DEVOPS_GUIDE.md)** - Complete deployment documentation
- **[Project Overview](docs/01_PROJECT_OVERVIEW_AND_ARCHITECTURE.md)** - System architecture
- **[API Documentation](docs/03_API_DOCUMENTATION_AND_INTEGRATION.md)** - API reference

## 🆘 **Troubleshooting**

### **Common Issues**
1. **Connection failed**: Check port 65002 and credentials
2. **Deployment failed**: Verify GitHub secrets are correct
3. **Application not loading**: Check file permissions and dependencies

### **Support**
- Check the comprehensive documentation in `/docs`
- Review deployment logs in GitHub Actions
- Verify server configuration and dependencies

---

**For complete deployment documentation, see `/docs/04_DEPLOYMENT_AND_DEVOPS_GUIDE.md`** 