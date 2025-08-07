# 🗄️ Database Setup Guide for EA CRM

This guide explains how to set up the database for your EA CRM application on Hostinger.

## 📋 **Database Options**

### **Option 1: SQLite (Recommended for Start)**
- ✅ **Easy setup** - No additional configuration needed
- ✅ **Works immediately** - Database file created automatically
- ✅ **No hosting costs** - Uses file-based storage
- ❌ **Limited scalability** - Not ideal for high traffic

### **Option 2: MySQL (Recommended for Production)**
- ✅ **Better performance** - Optimized for multiple users
- ✅ **Scalable** - Handles high traffic well
- ✅ **Professional** - Industry standard for web applications
- ❌ **Requires setup** - Need to create MySQL database

## 🚀 **Quick Start: SQLite Setup**

If you want to get started quickly, SQLite will work automatically:

1. **Deploy your application** (already done)
2. **Visit your website**: `https://crm.eaincorp.com`
3. **Login with**: `admin` / `admin123`
4. **Database will be created automatically**

## 🗄️ **MySQL Setup (Production)**

### **Step 1: Create MySQL Database in Hostinger**

1. **Go to your Hostinger hPanel**
2. **Click "Databases"** in the left sidebar
3. **Click "MySQL Databases"**
4. **Create a new database:**
   - **Database name**: `ea_crm_db`
   - **Username**: `ea_crm_user`
   - **Password**: Create a strong password (save this!)
   - **Host**: `localhost`

### **Step 2: Get Database Connection Details**

After creating the database, note down:
- **Database name**: `ea_crm_db`
- **Username**: `ea_crm_user`
- **Password**: (the one you created)
- **Host**: `localhost`

### **Step 3: Update Environment Variables**

You need to set these environment variables on your server:

```bash
# Database Configuration
DATABASE_URL=mysql://ea_crm_user:your_password@localhost/ea_crm_db
DB_HOST=localhost
DB_NAME=ea_crm_db
DB_USER=ea_crm_user
DB_PASSWORD=your_password

# Application Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

### **Step 4: Run Database Setup Script**

After deployment, run the database setup script:

```bash
# SSH into your server
ssh -p 65002 u539052962@145.223.77.49

# Navigate to your application
cd /home/u539052962/domains/eaincorp.com/public_html/crm

# Run the database setup
python scripts/setup_production_db.py --type mysql
```

## 🔧 **Database Configuration Files**

### **Environment Variables (.env file)**

Create a `.env` file in your application root:

```env
# Database Configuration
DATABASE_URL=mysql://ea_crm_user:your_password@localhost/ea_crm_db
DB_HOST=localhost
DB_NAME=ea_crm_db
DB_USER=ea_crm_user
DB_PASSWORD=your_password

# Application Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
FLASK_APP=wsgi.py

# AI Configuration (optional)
OPENROUTER_API_KEY=your-openrouter-api-key

# Email Configuration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-email-password
```

### **Database Migration**

If you have existing data in SQLite, you can migrate it:

```bash
# Export SQLite data
python scripts/export_sqlite_data.py

# Import to MySQL
python scripts/import_mysql_data.py
```

## 📊 **Database Tables**

Your EA CRM will create these tables automatically:

- **users** - User accounts and authentication
- **roles** - User roles and permissions
- **leads** - Lead management data
- **calls** - Call tracking and history
- **tasks** - Task management
- **projections** - Revenue projections
- **converted_clients** - Client management
- **team_members** - Team management
- **messages** - Real-time messaging
- **notifications** - System notifications

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **"Database connection failed"**
   - Check your database credentials
   - Make sure MySQL is enabled in Hostinger
   - Verify the database exists

2. **"Permission denied"**
   - Check database user permissions
   - Make sure the user has access to the database

3. **"Table doesn't exist"**
   - Run the database setup script
   - Check if all tables were created

### **Testing Database Connection:**

```bash
# Test MySQL connection
python scripts/test_db_connection.py

# Check database tables
python scripts/check_db_tables.py
```

## 📈 **Performance Tips**

### **For SQLite:**
- Keep database file size under 1GB
- Regular backups recommended
- Monitor file permissions

### **For MySQL:**
- Enable query caching
- Regular database optimization
- Monitor connection limits

## 🔒 **Security Considerations**

1. **Strong passwords** for database users
2. **Regular backups** of your database
3. **Limit database access** to necessary users only
4. **Monitor database logs** for suspicious activity

## 📞 **Need Help?**

If you encounter database issues:

1. **Check Hostinger MySQL status**
2. **Verify database credentials**
3. **Run database setup script**
4. **Check application logs**

**Your EA CRM database will be automatically configured during deployment!** 🚀 