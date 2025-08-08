# 🚀 EA CRM - Supabase PostgreSQL Setup Guide

## 📋 Prerequisites
- Supabase account (free at [supabase.com](https://supabase.com))
- Vercel project with EA CRM deployed

## 🎯 Step-by-Step Setup

### 1. Create Supabase Project

1. **Go to Supabase Dashboard**
   - Visit [supabase.com](https://supabase.com)
   - Sign up/Login to your account

2. **Create New Project**
   - Click "New Project"
   - Choose your organization
   - Enter project name: `ea-crm-database`
   - Set database password (save it!)
   - Choose region (closest to your users)
   - Click "Create new project"

3. **Wait for Setup**
   - Project creation takes 2-3 minutes
   - You'll see "Project is ready" when done

### 2. Get Database Credentials

1. **Go to Project Settings**
   - In your Supabase dashboard
   - Click "Settings" → "API"

2. **Copy Credentials**
   - **Project URL**: `https://your-project-id.supabase.co`
   - **Anon Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - Save these for Vercel environment variables

### 3. Set Up Database Schema

1. **Open SQL Editor**
   - In Supabase dashboard
   - Click "SQL Editor" in left sidebar

2. **Run Schema Script**
   - Copy the entire content from `supabase_schema.sql`
   - Paste in SQL Editor
   - Click "Run" to execute

3. **Verify Tables Created**
   - Go to "Table Editor"
   - You should see: `users`, `leads`, `tasks`
   - Check that sample data is inserted

### 4. Configure Vercel Environment Variables

1. **Go to Vercel Dashboard**
   - Visit [vercel.com](https://vercel.com)
   - Select your EA CRM project

2. **Add Environment Variables**
   - Go to "Settings" → "Environment Variables"
   - Add these variables:

   ```
   SUPABASE_URL = https://your-project-id.supabase.co
   SUPABASE_ANON_KEY = your-anon-key-from-supabase
   ```

3. **Deploy Changes**
   - Vercel will automatically redeploy
   - Wait 2-3 minutes for deployment

### 5. Test the Integration

1. **Visit Your CRM**
   - Go to your Vercel URL
   - Login with: `admin` / `admin123`

2. **Check Database Status**
   - Dashboard should show "Supabase (Production)"
   - Stats should display real data

3. **Test Features**
   - Add new leads
   - Create tasks
   - Verify data persists

## 🔧 Database Schema Details

### Tables Created:

**📊 Users Table**
- `id`: Primary key
- `username`: Unique login name
- `password`: Hashed password
- `role`: User role (admin/user)
- `email`: User email
- `created_at`: Timestamp
- `updated_at`: Auto-updated timestamp

**📋 Leads Table**
- `id`: Primary key
- `name`: Lead name
- `email`: Contact email
- `phone`: Phone number
- `company`: Company name
- `status`: Lead status (new/contacted/qualified)
- `source`: Lead source
- `notes`: Additional notes
- `assigned_to`: Assigned user
- `created_at`: Timestamp
- `updated_at`: Auto-updated timestamp

**📝 Tasks Table**
- `id`: Primary key
- `title`: Task title
- `description`: Task description
- `status`: Task status (pending/in_progress/completed)
- `priority`: Priority level (low/medium/high)
- `due_date`: Due date
- `assigned_to`: Assigned user
- `lead_id`: Related lead (optional)
- `created_at`: Timestamp
- `updated_at`: Auto-updated timestamp

### 🔒 Security Features:

- **Row Level Security (RLS)** enabled
- **Automatic timestamps** for created_at/updated_at
- **Database indexes** for performance
- **Foreign key relationships** between tables
- **Conflict handling** for duplicate inserts

## 🚀 Sample Data Included

**👥 Users:**
- `admin` / `admin123` (Admin role)

**📋 Leads:**
- John Doe (Tech Corp) - New lead
- Jane Smith (Marketing Inc) - Contacted
- Mike Johnson (StartupXYZ) - Qualified

**📝 Tasks:**
- Follow up with John Doe (High priority)
- Update website content (Medium priority)
- Send proposal to Jane Smith (High priority)

## 🔍 Troubleshooting

### Common Issues:

**❌ "Database error" on dashboard**
- Check environment variables in Vercel
- Verify Supabase credentials
- Ensure tables are created

**❌ "Supabase credentials not found"**
- Add SUPABASE_URL and SUPABASE_ANON_KEY to Vercel
- Redeploy the application

**❌ Tables not found**
- Run the schema script in Supabase SQL Editor
- Check for any SQL errors

**❌ Permission denied**
- Verify RLS policies are created
- Check table permissions

### Debug Steps:

1. **Check Vercel Logs**
   - Go to Vercel dashboard
   - Click on latest deployment
   - Check "Functions" logs

2. **Test Supabase Connection**
   - Use Supabase dashboard
   - Try querying tables directly

3. **Verify Environment Variables**
   - Check Vercel project settings
   - Ensure variables are deployed

## 🎉 Success Indicators

✅ **Dashboard shows "Supabase (Production)"**
✅ **Real-time stats display**
✅ **Can add/edit leads and tasks**
✅ **Data persists across deployments**
✅ **No "Database error" messages**

## 📈 Next Steps

Once Supabase is working:
1. **Migrate existing data** from local database
2. **Add more features** (reports, analytics)
3. **Implement user authentication**
4. **Add real-time notifications**
5. **Scale with more users**

## 💡 Tips

- **Free Tier**: Supabase free tier includes 500MB database
- **Backup**: Supabase automatically backs up your data
- **Monitoring**: Use Supabase dashboard for database monitoring
- **Scaling**: Easy to upgrade when you need more resources

---

**Your EA CRM is now production-ready with Supabase PostgreSQL!** 🚀 