# 🚀 Vercel Deployment Guide for EA CRM

This guide will help you deploy your EA CRM to Vercel with your subdomain `crm.eaincorp.com`.

## 📋 **Why Vercel?**

- ✅ **Full Python/Flask support** - No hosting limitations
- ✅ **Automatic HTTPS** - SSL certificates included
- ✅ **Global CDN** - Fast loading worldwide
- ✅ **Easy subdomain setup** - Simple DNS configuration
- ✅ **Free tier** - 100GB bandwidth/month
- ✅ **GitHub integration** - Automatic deployments

## 🛠️ **Step 1: Create Vercel Account**

1. **Go to**: [https://vercel.com](https://vercel.com)
2. **Sign up** with your GitHub account
3. **Complete setup** and verify email

## 🛠️ **Step 2: Install Vercel CLI**

```bash
# Install Vercel CLI globally
npm install -g vercel

# Login to Vercel
vercel login
```

## 🛠️ **Step 3: Deploy to Vercel**

### **Option A: Deploy via CLI**
```bash
# Navigate to your project
cd "E:\Emon Work\EA CRM - Copy-working"

# Deploy to Vercel
vercel

# Follow the prompts:
# - Link to existing project? No
# - Project name: ea-crm
# - Directory: ./
# - Override settings? No
```

### **Option B: Deploy via GitHub Integration**
1. **Go to Vercel Dashboard**
2. **Click "New Project"**
3. **Import your GitHub repository**: `easoftlab/ea-crm`
4. **Configure settings**:
   - **Framework Preset**: Other
   - **Root Directory**: `./`
   - **Build Command**: Leave empty
   - **Output Directory**: Leave empty
   - **Install Command**: `pip install -r requirements.txt`

## 🛠️ **Step 4: Get Vercel Credentials**

After deployment, get these values from Vercel:

### **Get Vercel Token:**
1. **Go to**: [https://vercel.com/account/tokens](https://vercel.com/account/tokens)
2. **Create new token**
3. **Copy the token**

### **Get Project ID:**
1. **Go to your project** in Vercel Dashboard
2. **Click "Settings"**
3. **Copy "Project ID"**

### **Get Org ID:**
1. **Go to**: [https://vercel.com/account](https://vercel.com/account)
2. **Copy "Team ID"** (this is your Org ID)

## 🛠️ **Step 5: Add GitHub Secrets**

Go to your GitHub repository: [https://github.com/easoftlab/ea-crm/settings/secrets/actions](https://github.com/easoftlab/ea-crm/settings/secrets/actions)

Add these secrets:

### **VERCEL_TOKEN**
- **Name**: `VERCEL_TOKEN`
- **Value**: Your Vercel token

### **VERCEL_ORG_ID**
- **Name**: `VERCEL_ORG_ID`
- **Value**: Your Team ID

### **VERCEL_PROJECT_ID**
- **Name**: `VERCEL_PROJECT_ID`
- **Value**: Your Project ID

## 🛠️ **Step 6: Configure Subdomain**

### **In Vercel Dashboard:**
1. **Go to your project**
2. **Click "Settings" → "Domains"**
3. **Add domain**: `crm.eaincorp.com`
4. **Copy the DNS records** provided

### **In Cloudflare:**
1. **Go to Cloudflare Dashboard**
2. **Select your domain**: `eaincorp.com`
3. **Go to "DNS"**
4. **Add the CNAME record** provided by Vercel:
   - **Type**: CNAME
   - **Name**: `crm`
   - **Target**: Vercel's domain (e.g., `ea-crm.vercel.app`)
   - **Proxy status**: DNS only (gray cloud)

## 🛠️ **Step 7: Test Deployment**

1. **Wait for DNS propagation** (5-10 minutes)
2. **Visit**: `https://crm.eaincorp.com`
3. **Login with**: `admin` / `admin123`

## 🔧 **Database Configuration**

### **For Vercel (SQLite):**
- ✅ **Works automatically** - No setup needed
- ✅ **Database created** on first visit
- ⚠️ **Data resets** on each deployment (serverless limitation)

### **For Production (External Database):**
Consider using:
- **PlanetScale** (MySQL)
- **Supabase** (PostgreSQL)
- **MongoDB Atlas**

## 📊 **Environment Variables**

Add these in Vercel Dashboard → Settings → Environment Variables:

```env
FLASK_ENV=production
FLASK_APP=wsgi.py
SECRET_KEY=your-secret-key-here
OPENROUTER_API_KEY=your-openrouter-api-key
```

## 🚀 **CI/CD Pipeline**

The GitHub Actions workflow will:
1. **Run tests** on every push
2. **Deploy to Vercel** automatically
3. **Update your subdomain** instantly

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **"Build failed"**
   - Check Python version compatibility
   - Verify requirements.txt

2. **"Domain not found"**
   - Check DNS propagation
   - Verify CNAME record

3. **"Database errors"**
   - SQLite works automatically
   - For persistent data, use external database

## 📈 **Benefits of Vercel:**

- ✅ **No server management**
- ✅ **Automatic scaling**
- ✅ **Global performance**
- ✅ **Easy rollbacks**
- ✅ **Preview deployments**

## 🎯 **Next Steps:**

1. **Follow the setup guide** above
2. **Test your deployment**
3. **Configure your subdomain**
4. **Enjoy your live EA CRM!**

**Your EA CRM will be much more reliable on Vercel!** 🚀 