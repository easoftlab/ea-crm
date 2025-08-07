# 🚀 EA CRM CI/CD Pipeline Setup Guide

This guide will help you set up automated deployment of your EA CRM application to your website using GitHub Actions.

## 📋 **Prerequisites**

Before setting up the CI/CD pipeline, ensure you have:

1. **GitHub Repository**: Your EA CRM code pushed to GitHub
2. **Hostinger Account**: Your hosting account with FTP access
3. **Domain**: Your website domain configured
4. **Python 3.9+**: For local development and testing

## 🔧 **Step 1: GitHub Repository Setup**

### **1.1 Initialize Git Repository (if not already done)**
```bash
# Navigate to your project directory
cd "E:\Emon Work\EA CRM - Copy-working"

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit with EA CRM application"

# Set main branch
git branch -M main
```

### **1.2 Connect to GitHub**
```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push -u origin main
```

## 🔐 **Step 2: Configure GitHub Secrets**

### **2.1 Access GitHub Secrets**
1. Go to your GitHub repository
2. Click on **Settings** tab
3. Click on **Secrets and variables** → **Actions**
4. Click **New repository secret**

### **2.2 Add Required Secrets**

Add these secrets to your GitHub repository:

#### **FTP_SERVER**
- **Name**: `FTP_SERVER`
- **Value**: Your Hostinger FTP server
- **Example**: `ftp.yourdomain.com` or `yourdomain.com`

#### **FTP_USERNAME**
- **Name**: `FTP_USERNAME`
- **Value**: Your Hostinger FTP username
- **Example**: `your_username`

#### **FTP_PASSWORD**
- **Name**: `FTP_PASSWORD`
- **Value**: Your Hostinger FTP password
- **Example**: `your_password`

## 🏗️ **Step 3: Server Setup**

### **3.1 SSH into Your Server**
```bash
# Connect to your Hostinger server
ssh -p 65002 u539052962@145.223.77.49
```

### **3.2 Navigate to Website Directory**
```bash
# Navigate to your website directory
cd public_html

# Check current files
ls -la
```

### **3.3 Create Post-Deployment Hook**
```bash
# Create a post-deployment script
cat > post_deploy_hook.sh << 'EOF'
#!/bin/bash
echo "🚀 Running post-deployment setup..."

# Navigate to application directory
cd /home/u539052962/public_html

# Run post-deployment setup
python3 deploy/post_deploy_setup.py

# Set proper permissions
chmod -R 755 .
find . -type f -exec chmod 644 {} \;

echo "✅ Post-deployment setup completed!"
EOF

# Make it executable
chmod +x post_deploy_hook.sh
```

## 🔄 **Step 4: Test the CI/CD Pipeline**

### **4.1 Make a Test Change**
```bash
# Make a small change to test deployment
echo "# Test deployment $(date)" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD deployment"
git push origin main
```

### **4.2 Monitor Deployment**
1. Go to your GitHub repository
2. Click on **Actions** tab
3. You should see the deployment workflow running
4. Monitor the progress and check for any errors

## 📊 **Step 5: Verify Deployment**

### **5.1 Check GitHub Actions**
- Go to **Actions** tab in your GitHub repository
- Look for the latest workflow run
- Check that both **test** and **deploy** jobs completed successfully

### **5.2 Check Your Website**
- Visit your website domain
- Verify the EA CRM application is running
- Test login with default credentials:
  - **Username**: `admin`
  - **Password**: `admin123`

### **5.3 Check Server Logs**
```bash
# SSH into your server
ssh -p 65002 u539052962@145.223.77.49

# Check deployment logs
cd public_html
cat post_deploy.log
cat deployment_success.txt
```

## 🔧 **Step 6: Customize Deployment**

### **6.1 Environment Configuration**
The deployment automatically creates a `.env` file with production settings. You can customize it:

```bash
# SSH into your server
ssh -p 65002 u539052962@145.223.77.49

# Edit environment file
cd public_html
nano .env
```

### **6.2 Database Configuration**
The deployment automatically sets up the database. You can access it:

```bash
# Check database
cd public_html/instance
ls -la *.db
```

### **6.3 Custom Domain Setup**
If you want to use a custom domain:

1. **Configure DNS**: Point your domain to your Hostinger server
2. **SSL Certificate**: Set up SSL in your Hostinger control panel
3. **Update .htaccess**: The deployment includes Apache configuration

## 🚀 **Step 7: Continuous Development Workflow**

### **7.1 Development Process**
```bash
# Make changes to your code
# Test locally
python run.py

# Commit and push
git add .
git commit -m "Add new feature"
git push origin main

# Deployment happens automatically!
```

### **7.2 Database Changes**
If you need to make database changes:

1. **Create Migration**: Add migration files to handle schema changes
2. **Test Locally**: Test migrations on your local environment
3. **Push to GitHub**: The deployment will handle migrations automatically

### **7.3 Monitoring Deployments**
- **GitHub Actions**: Monitor deployment status in Actions tab
- **Server Logs**: Check `post_deploy.log` on server
- **Application Logs**: Check application logs for errors

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Deployment Fails**
1. Check GitHub Actions logs
2. Verify FTP credentials in GitHub secrets
3. Check server disk space
4. Verify file permissions

#### **Application Not Loading**
1. Check `.htaccess` configuration
2. Verify Python dependencies
3. Check application logs
4. Test database connection

#### **Database Issues**
1. Check database file permissions
2. Verify database path in configuration
3. Run database initialization manually
4. Check for migration errors

### **Manual Deployment**
If CI/CD fails, you can deploy manually:

```bash
# SSH into server
ssh -p 65002 u539052962@145.223.77.49

# Navigate to website directory
cd public_html

# Run post-deployment setup
python3 deploy/post_deploy_setup.py
```

## 📈 **Advanced Features**

### **Environment-Specific Deployments**
You can set up different environments:

- **Development**: `dev` branch
- **Staging**: `staging` branch  
- **Production**: `main` branch

### **Database Backups**
The deployment includes automatic database backups:

```bash
# Check backups
cd public_html/backups
ls -la *.db
```

### **Performance Monitoring**
Monitor your application performance:

```bash
# Check application logs
tail -f logs/app.log

# Monitor resource usage
htop
```

## ✅ **Success Checklist**

- [ ] GitHub repository created and connected
- [ ] GitHub secrets configured (FTP_SERVER, FTP_USERNAME, FTP_PASSWORD)
- [ ] Server post-deployment hook created
- [ ] First deployment completed successfully
- [ ] Application accessible on your domain
- [ ] Database initialized and working
- [ ] Admin user created and accessible
- [ ] File permissions set correctly
- [ ] SSL certificate configured (if using custom domain)

## 🎉 **Congratulations!**

Your EA CRM application now has a fully automated CI/CD pipeline! 

**What you can do now:**
- Make changes to your code locally
- Push to GitHub
- Watch automatic deployment to your website
- Access your live EA CRM application

**Next Steps:**
1. Customize the application for your needs
2. Add your own branding and styling
3. Configure user roles and permissions
4. Import your existing data
5. Set up regular backups

---

**Need Help?**
- Check the deployment logs on GitHub Actions
- Review server logs for detailed error messages
- Contact your hosting provider for server-related issues
- Refer to the comprehensive documentation in `/docs` 