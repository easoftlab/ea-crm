# 🚀 EA CRM - Production Database Setup Guide

## 📊 **Database Options for Production**

### **Option 1: PostgreSQL (Recommended)**
**Best for:** Large datasets, complex queries, high performance

**Setup:**
1. **Use a managed service:**
   - **Railway**: `railway.app` (Free tier available)
   - **Supabase**: `supabase.com` (Free tier available)
   - **Neon**: `neon.tech` (Free tier available)
   - **Heroku Postgres**: `heroku.com` (Paid)

2. **Get your connection string:**
   ```
   postgresql://username:password@host:port/database
   ```

3. **Add to Vercel Environment Variables:**
   - **Name**: `DATABASE_URL`
   - **Value**: `postgresql://username:password@host:port/database`

### **Option 2: MySQL**
**Best for:** Traditional web applications, good performance

**Setup:**
1. **Use a managed service:**
   - **PlanetScale**: `planetscale.com` (Free tier available)
   - **Railway MySQL**: `railway.app` (Free tier available)
   - **Clever Cloud**: `clever-cloud.com` (Free tier available)

2. **Add to Vercel Environment Variables:**
   - **Name**: `DB_HOST` - Your MySQL host
   - **Name**: `DB_USER` - Your MySQL username
   - **Name**: `DB_PASSWORD` - Your MySQL password
   - **Name**: `DB_NAME` - Your MySQL database name
   - **Name**: `DB_PORT` - Your MySQL port (usually 3306)

### **Option 3: SQLite (Development Only)**
**Best for:** Development, testing, small datasets
**Limitations:** Data not persistent on Vercel

## 🎯 **Recommended Setup for Your CRM**

### **Step 1: Choose Your Database Provider**

**For Small to Medium Business:**
- **Railway PostgreSQL** (Free tier: 1GB, 1000 hours/month)
- **Supabase** (Free tier: 500MB, 50MB bandwidth)

**For Large Business:**
- **Neon PostgreSQL** (Free tier: 3GB, 100 hours/month)
- **PlanetScale MySQL** (Free tier: 1GB, 1 billion reads/month)

### **Step 2: Database Setup**

**Example with Railway PostgreSQL:**

1. **Go to** `railway.app`
2. **Sign up** with GitHub
3. **Create new project**
4. **Add PostgreSQL** service
5. **Copy connection string** from Variables tab
6. **Add to Vercel** as `DATABASE_URL`

### **Step 3: Vercel Environment Variables**

**Required Variables:**
```
DATABASE_URL=postgresql://username:password@host:port/database
SECRET_KEY=your-secret-key-here-12345
FLASK_ENV=production
```

**Optional Variables:**
```
OPENROUTER_API_KEY=your-openrouter-api-key
```

### **Step 4: Database Schema**

The app will automatically create these tables:

**Users Table:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Leads Table:**
```sql
CREATE TABLE leads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(255),
    status VARCHAR(50) DEFAULT 'new',
    source VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Tasks Table:**
```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(50) DEFAULT 'medium',
    assigned_to VARCHAR(255),
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 **Performance Considerations**

### **For Large Datasets:**

1. **Indexing:**
   ```sql
   CREATE INDEX idx_leads_status ON leads(status);
   CREATE INDEX idx_leads_company ON leads(company);
   CREATE INDEX idx_tasks_status ON tasks(status);
   ```

2. **Pagination:**
   - The app supports pagination for large lead lists
   - Default: 50 leads per page

3. **Search Optimization:**
   - Full-text search on lead names and companies
   - Status-based filtering

### **Scalability Features:**

- **Connection pooling** for high traffic
- **Read replicas** for heavy read workloads
- **Backup automation** for data safety
- **Monitoring** for performance tracking

## 💰 **Cost Comparison**

### **Free Tiers:**
- **Railway**: 1GB PostgreSQL, 1000 hours/month
- **Supabase**: 500MB PostgreSQL, 50MB bandwidth
- **Neon**: 3GB PostgreSQL, 100 hours/month
- **PlanetScale**: 1GB MySQL, 1 billion reads/month

### **Paid Plans:**
- **Railway**: $5/month for 1GB, unlimited hours
- **Supabase**: $25/month for 8GB, 250GB bandwidth
- **Neon**: $10/month for 10GB, unlimited hours

## 🚀 **Quick Start Guide**

### **1. Set up Railway PostgreSQL (Recommended):**

1. **Visit** `railway.app`
2. **Sign up** with GitHub
3. **Create new project**
4. **Add PostgreSQL** service
5. **Copy connection string**
6. **Add to Vercel** environment variables

### **2. Update Vercel Environment Variables:**

1. **Go to** Vercel Dashboard
2. **Click** your `ea-crm` project
3. **Go to** Settings → Environment Variables
4. **Add:**
   - `DATABASE_URL` = Your PostgreSQL connection string
   - `SECRET_KEY` = `your-secret-key-here-12345`
   - `FLASK_ENV` = `production`

### **3. Deploy and Test:**

1. **Push changes** to GitHub
2. **Wait for deployment**
3. **Test login** with admin/admin123
4. **Add some leads** to test functionality

## 🔒 **Security Best Practices**

1. **Use strong passwords** for database
2. **Enable SSL** for database connections
3. **Regular backups** of your data
4. **Monitor access** logs
5. **Use environment variables** for sensitive data

## 📈 **Monitoring and Maintenance**

### **Database Health Checks:**
- Monitor connection count
- Track query performance
- Set up alerts for errors
- Regular backup verification

### **Performance Optimization:**
- Add indexes for frequently queried columns
- Optimize slow queries
- Monitor disk usage
- Scale up when needed

## 🎉 **Benefits of Production Database**

✅ **Data Persistence** - Your data survives deployments
✅ **Scalability** - Handle thousands of leads
✅ **Backup & Recovery** - Automatic backups
✅ **Performance** - Fast queries and indexing
✅ **Security** - Encrypted connections
✅ **Monitoring** - Track usage and performance

---

**Your EA CRM will be production-ready with a proper database setup!** 🚀 