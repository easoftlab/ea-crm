# 🚀 Vercel Deployment Setup Guide

## 📋 **Step 1: Get Your Vercel Token**

1. **Go to Vercel Dashboard**
   - Visit: https://vercel.com/dashboard
   - Login to your account

2. **Navigate to Settings**
   - Click on your profile picture (top right)
   - Select "Settings"

3. **Create API Token**
   - Go to "Tokens" tab
   - Click "Create Token"
   - Name it: `EA-CRM-Deployment`
   - Select "Full Account" scope
   - Click "Create"
   - **Copy the token** (you won't see it again!)

## 📋 **Step 2: Get Your Project ID**

1. **Go to Your Project**
   - In Vercel dashboard, click on your `ea-crm` project
   - Go to "Settings" tab

2. **Find Project ID**
   - Scroll down to "General" section
   - Copy the "Project ID" (looks like: `prj_xxxxxxxxxxxxxxxx`)

## 📋 **Step 3: Get Your Org ID**

1. **Check Team Settings**
   - In project settings, look for "General" section
   - Find "Team" or "Organization"
   - Copy the "Team ID" (looks like: `team_xxxxxxxxxxxxxxxx`)

## 📋 **Step 4: Add GitHub Secrets**

1. **Go to GitHub Repository**
   - Visit: https://github.com/easoftlab/ea-crm
   - Click "Settings" tab

2. **Add Secrets**
   - Click "Secrets and variables" → "Actions"
   - Click "New repository secret"
   - Add these 3 secrets:

### **Secret 1: VERCEL_TOKEN**
- **Name:** `VERCEL_TOKEN`
- **Value:** Your Vercel token from Step 1

### **Secret 2: VERCEL_ORG_ID**
- **Name:** `VERCEL_ORG_ID`
- **Value:** Your team/org ID from Step 3

### **Secret 3: VERCEL_PROJECT_ID**
- **Name:** `VERCEL_PROJECT_ID`
- **Value:** Your project ID from Step 2

## ✅ **Step 5: Test Deployment**

1. **Push Changes**
   ```bash
   git add .
   git commit -m "Setup Vercel deployment"
   git push origin main
   ```

2. **Check GitHub Actions**
   - Go to "Actions" tab in your GitHub repo
   - Watch the deployment workflow run

3. **Verify Deployment**
   - Check your Vercel dashboard
   - Visit your deployed URL

## 🎯 **Expected Results**

- ✅ **GitHub Actions** will deploy to Vercel
- ✅ **No more "vercel-token" errors**
- ✅ **Your app will be live** at your Vercel URL
- ✅ **Automatic deployments** on every push to main

## 🆘 **Need Help?**

If you get stuck:
1. **Check the GitHub Actions logs** for specific errors
2. **Verify all 3 secrets** are set correctly
3. **Make sure your Vercel project exists** and is connected

---

**Once you've added these secrets, the deployment will work automatically!** 🚀 