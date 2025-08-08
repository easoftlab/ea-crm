# 🚀 EA CRM - Vercel Environment Variables Setup

## 📋 Your Supabase Credentials

**Project URL:** `https://vicvhgaxxwnevhbvxsaw.supabase.co`
**Anon Key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpY3ZoZ2F4eHduZXZoYnZ4c2F3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ2MjIyMzksImV4cCI6MjA3MDE5ODIzOX0.nFQmGAMNSSiFY--r27YLIIYUw2WMpeKa5iq1SGle3FY`

## 🎯 Step-by-Step Process

### Step 1: Add Environment Variables to Vercel

1. **Go to Vercel Dashboard**
   - Visit [vercel.com](https://vercel.com)
   - Login to your account
   - Select your EA CRM project

2. **Navigate to Environment Variables**
   - Click "Settings" tab
   - Click "Environment Variables" in left sidebar

3. **Add First Variable**
   - **Name:** `SUPABASE_URL`
   - **Value:** `https://vicvhgaxxwnevhbvxsaw.supabase.co`
   - **Environment:** Production
   - Click "Add"

4. **Add Second Variable**
   - **Name:** `SUPABASE_ANON_KEY`
   - **Value:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpY3ZoZ2F4eHduZXZoYnZ4c2F3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ2MjIyMzksImV4cCI6MjA3MDE5ODIzOX0.nFQmGAMNSSiFY--r27YLIIYUw2WMpeKa5iq1SGle3FY`
   - **Environment:** Production
   - Click "Add"

### Step 2: Set Up Supabase Database

1. **Go to Supabase Dashboard**
   - Visit [supabase.com](https://supabase.com)
   - Login to your account
   - Select your project

2. **Open SQL Editor**
   - Click "SQL Editor" in left sidebar
   - Click "New Query"

3. **Run Database Schema**
   - Copy the entire content from `supabase_schema.sql`
   - Paste in SQL Editor
   - Click "Run" button

4. **Verify Tables Created**
   - Go to "Table Editor"
   - You should see: `users`, `leads`, `tasks`
   - Check that sample data is inserted

### Step 3: Test the Integration

1. **Wait for Vercel Deployment**
   - Vercel will automatically redeploy
   - Wait 2-3 minutes

2. **Visit Your CRM**
   - Go to your Vercel URL
   - Login with: `admin` / `admin123`

3. **Check Database Status**
   - Dashboard should show "Supabase (Production)"
   - Stats should display real data

## 🔍 Verification Steps

### ✅ Check Environment Variables
- Go to Vercel → Settings → Environment Variables
- Verify both variables are added and deployed

### ✅ Check Supabase Tables
- Go to Supabase → Table Editor
- Verify tables: `users`, `leads`, `tasks`
- Check sample data is present

### ✅ Test CRM Functionality
- Login to your CRM
- Check dashboard shows "Supabase (Production)"
- Try adding a new lead
- Try creating a new task
- Verify data persists

## 🚨 Troubleshooting

### If Dashboard Shows "SQLite (Development)"
- Check environment variables are deployed
- Verify variable names are correct
- Wait for Vercel redeployment

### If "Database error" Appears
- Check Supabase connection
- Verify tables are created
- Check Vercel logs for errors

### If Tables Not Found
- Run the schema script again
- Check for SQL errors
- Verify you're in the correct project

## 🎉 Success Indicators

✅ **Dashboard shows "Supabase (Production)"**
✅ **Real-time stats display**
✅ **Can add/edit leads and tasks**
✅ **Data persists across deployments**
✅ **No "Database error" messages**

---

**Your EA CRM will be production-ready once these steps are completed!** 🚀 