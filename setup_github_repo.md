# 🚀 **Simple GitHub Repository Setup Guide**

Since there's a Git issue, let me guide you through setting up the GitHub repository manually.

## **Step 1: Create GitHub Repository**

1. **Go to GitHub.com** and sign in to your account
2. **Click the "+" icon** in the top right corner
3. **Select "New repository"**
4. **Fill in the details:**
   - **Repository name**: `ea-crm` (or any name you prefer)
   - **Description**: `EA CRM - Customer Relationship Management System`
   - **Make it Public** (or Private if you prefer)
   - **DO NOT** check "Add a README file"
   - **DO NOT** check "Add .gitignore"
   - **DO NOT** check "Choose a license"
5. **Click "Create repository"**

## **Step 2: Get Your Repository URL**

After creating the repository, GitHub will show you a page with commands. **Copy the repository URL** - it will look like:
```
https://github.com/YOUR_USERNAME/ea-crm.git
```

## **Step 3: Run These Commands in Your Project**

Open Command Prompt or PowerShell in your project folder and run these commands one by one:

```bash
# 1. Initialize Git repository
git init

# 2. Add all files
git add .

# 3. Commit the files
git commit -m "Initial commit with EA CRM application"

# 4. Set the main branch
git branch -M main

# 5. Add your GitHub repository (replace YOUR_USERNAME with your actual username)
git remote add origin https://github.com/YOUR_USERNAME/ea-crm.git

# 6. Push to GitHub
git push -u origin main
```

## **Step 4: Configure GitHub Secrets**

Once your code is on GitHub:

1. **Go to your repository** on GitHub
2. **Click "Settings"** tab
3. **Click "Secrets and variables"** → **"Actions"**
4. **Click "New repository secret"**
5. **Add these 3 secrets:**

### **Secret 1: FTP_SERVER**
- **Name**: `FTP_SERVER`
- **Value**: Your Hostinger FTP server (e.g., `ftp.yourdomain.com`)

### **Secret 2: FTP_USERNAME**
- **Name**: `FTP_USERNAME`
- **Value**: Your Hostinger FTP username

### **Secret 3: FTP_PASSWORD**
- **Name**: `FTP_PASSWORD`
- **Value**: Your Hostinger FTP password

## **Step 5: Test the Deployment**

1. **Make a small change** to any file (like README.md)
2. **Commit and push:**
   ```bash
   git add README.md
   git commit -m "Test deployment"
   git push origin main
   ```
3. **Go to your GitHub repository**
4. **Click "Actions" tab**
5. **Watch the deployment process**

## **Step 6: Check Your Website**

After deployment completes:
1. **Visit your website domain**
2. **You should see your EA CRM application**
3. **Login with:**
   - **Username**: `admin`
   - **Password**: `admin123`

## **Need Help?**

If you get stuck at any step, just let me know and I'll help you troubleshoot!

---

**Your EA CRM will be live on your website with automatic deployments! 🎉** 