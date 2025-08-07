#!/bin/bash

# EA CRM Server Setup Script
# Run this on your server after uploading files

echo "🚀 Setting up EA CRM on server..."

# Navigate to the CRM directory
cd /home/u539052962/domains/eaincorp.com/public_html/crm

# Create virtual environment (if Python venv is available)
if command -v python3 -m venv &> /dev/null; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not available, using system Python"
fi

# Install required packages
echo "📦 Installing required packages..."
pip install -r requirements.txt

# Set proper permissions
echo "🔐 Setting file permissions..."
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
chmod +x wsgi.py

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p instance
mkdir -p app/static/uploads/profiles
mkdir -p logs

# Set permissions for writable directories
chmod 755 instance
chmod 755 app/static/uploads
chmod 755 app/static/uploads/profiles
chmod 755 logs

# Create .env file for environment variables
echo "🔐 Creating environment configuration..."
cat > .env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=production
FLASK_APP=wsgi.py
EOF

echo "✅ Server setup complete!"
echo "🌐 Your CRM should now be accessible at: https://crm.eaincorp.com" 