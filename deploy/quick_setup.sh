#!/bin/bash

# Quick Setup Script for EA CRM
# Run this on your server after FTP upload

echo "🚀 EA CRM Quick Setup"
echo "===================="

# Check if we're in the right directory
if [ ! -f "wsgi.py" ]; then
    echo "❌ Error: wsgi.py not found. Please run this script from the CRM directory."
    echo "   Navigate to the crm directory first: cd crm"
    exit 1
fi

echo "✅ Found CRM files. Starting setup..."

# Step 1: Set file permissions
echo "📁 Setting file permissions..."
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
chmod 755 instance/ 2>/dev/null || mkdir -p instance
chmod 755 app/static/uploads/ 2>/dev/null || mkdir -p app/static/uploads

# Step 2: Create necessary directories
echo "📂 Creating necessary directories..."
mkdir -p instance
mkdir -p app/static/uploads/profiles
mkdir -p logs

# Step 3: Install Python dependencies
echo "📦 Installing Python dependencies..."
if command -v python3 &> /dev/null; then
    python3 -m pip install -r requirements.txt
elif command -v python &> /dev/null; then
    python -m pip install -r requirements.txt
else
    echo "❌ Python not found. Please install Python 3.7+ first."
    exit 1
fi

# Step 4: Create environment file
echo "🔐 Creating environment configuration..."
cat > .env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "your-secret-key-here")
FLASK_ENV=production
FLASK_APP=wsgi.py
EOF

# Step 5: Test the application
echo "🧪 Testing the application..."
if python3 wsgi.py --help &> /dev/null; then
    echo "✅ Application test successful!"
else
    echo "⚠️  Application test failed, but setup completed."
fi

echo ""
echo "🎉 Setup completed!"
echo "=================="
echo "Next steps:"
echo "1. Configure your web server (Apache/Nginx)"
echo "2. Set up your domain: crm.eaincorp.com"
echo "3. Test the application: https://crm.eaincorp.com"
echo ""
echo "📋 Manual web server configuration:"
echo "   - Copy apache_config.conf to your Apache configuration"
echo "   - Enable mod_wsgi, mod_rewrite, and mod_headers"
echo "   - Restart Apache"
echo ""
echo "🔧 If you need help, check POST_DEPLOYMENT_GUIDE.md" 