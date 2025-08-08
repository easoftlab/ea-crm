# 🚀 Direct Vercel Deployment Guide

## 📋 **Step 1: Deploy to Vercel Default Domain**

### **Option A: Deploy via Vercel Dashboard**

1. **Go to Vercel Dashboard**
   - Visit: https://vercel.com/dashboard
   - Click "New Project"

2. **Import from GitHub**
   - Click "Import Git Repository"
   - Select your `ea-crm` repository
   - Click "Import"

3. **Configure Project**
   - **Framework Preset:** Other
   - **Root Directory:** `./` (leave default)
   - **Build Command:** Leave empty (not needed for Python)
   - **Output Directory:** Leave empty
   - **Install Command:** `pip install -r requirements.txt`

4. **Environment Variables**
   - Add these if needed:
     - `FLASK_ENV=production`
     - `SECRET_KEY=your-secret-key-here`

5. **Deploy**
   - Click "Deploy"
   - Wait for build to complete

### **Option B: Deploy via Vercel CLI**

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy from your project directory**
   ```bash
   vercel
   ```

4. **Follow the prompts**
   - Link to existing project or create new
   - Confirm settings
   - Deploy

## ✅ **Step 2: Test Your Deployment**

After deployment, you'll get a URL like:
- `https://ea-crm-xxxxx.vercel.app`

**Test these endpoints:**
- **Root:** `https://ea-crm-xxxxx.vercel.app/` → Should show "Hello from EA CRM!"
- **Test:** `https://ea-crm-xxxxx.vercel.app/test` → Should show "Test endpoint working!"
- **Debug:** `https://ea-crm-xxxxx.vercel.app/debug` → Should show environment variables

## 🎯 **Step 3: If It Works**

If the test deployment works:
1. ✅ **We know the app can deploy**
2. ✅ **Vercel configuration is correct**
3. ✅ **Ready to set up custom domain**

## 🔧 **Step 4: Set Up Custom Domain (Later)**

Once the default domain works:
1. **Go to your Vercel project settings**
2. **Add custom domain:** `crm.eaincorp.com`
3. **Configure DNS** as instructed by Vercel
4. **Set up GitHub Actions** for automatic deployment

## 🆘 **Troubleshooting**

### **If deployment fails:**
- Check the build logs in Vercel dashboard
- Make sure `requirements.txt` has only `Flask==2.3.3`
- Verify `vercel.json` is correct

### **If app doesn't work:**
- Check the function logs in Vercel dashboard
- Verify environment variables are set
- Test the endpoints mentioned above

---

**Start with Step 1 to get your app working on Vercel's default domain first!** 🚀 