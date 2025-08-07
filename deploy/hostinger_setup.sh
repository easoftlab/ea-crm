#!/bin/bash
# Hostinger Server Setup Script for EA CRM
# This script should be run once on your Hostinger server

set -e

echo "🚀 Setting up EA CRM on Hostinger..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ~/ea_crm
mkdir -p ~/ea_crm/instance
mkdir -p ~/ea_crm/logs
mkdir -p ~/ea_crm/backups

# Set up Python virtual environment
echo "🐍 Setting up Python virtual environment..."
cd ~/ea_crm
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install gunicorn
pip install supervisor

# Create supervisor configuration
echo "⚙️ Creating supervisor configuration..."
cat > /etc/supervisor/conf.d/ea_crm.conf << EOF
[program:ea_crm]
command=/home/$(whoami)/ea_crm/venv/bin/gunicorn --workers 3 --bind unix:/tmp/ea_crm.sock wsgi:application
directory=/home/$(whoami)/ea_crm
user=$(whoami)
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/$(whoami)/ea_crm/logs/gunicorn.log
EOF

# Create nginx configuration
echo "🌐 Creating nginx configuration..."
cat > /etc/nginx/sites-available/ea_crm << EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your actual domain

    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/ea_crm.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias /home/$(whoami)/ea_crm/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /home/$(whoami)/ea_crm/app/static/uploads;
        expires 30d;
    }
}
EOF

# Enable the site
echo "🔗 Enabling nginx site..."
ln -sf /etc/nginx/sites-available/ea_crm /etc/nginx/sites-enabled/

# Create deployment hook
echo "🎣 Creating deployment hook..."
cat > ~/ea_crm/deploy_hook.sh << 'EOF'
#!/bin/bash
# Deployment hook for EA CRM

set -e

echo "🔄 Starting deployment..."

# Activate virtual environment
source ~/ea_crm/venv/bin/activate

# Navigate to application directory
cd ~/ea_crm

# Backup current database
if [ -f instance/leads.db ]; then
    cp instance/leads.db instance/leads_backup_$(date +%Y%m%d_%H%M%S).db
    echo "💾 Database backed up"
fi

# Install/update dependencies
pip install -r requirements.txt

# Run deployment script
python deploy/deploy_script.py

# Restart services
sudo supervisorctl restart ea_crm
sudo systemctl reload nginx

echo "✅ Deployment completed!"
EOF

chmod +x ~/ea_crm/deploy_hook.sh

# Set up environment variables
echo "🔧 Setting up environment variables..."
cat > ~/ea_crm/.env << EOF
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=sqlite:///instance/leads.db
EOF

# Create cron job for database backups
echo "⏰ Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * cp ~/ea_crm/instance/leads.db ~/ea_crm/backups/leads_backup_\$(date +\%Y\%m\%d).db") | crontab -

# Set proper permissions
echo "🔐 Setting permissions..."
chmod 755 ~/ea_crm
chmod 644 ~/ea_crm/.env

echo "🎉 Hostinger setup completed!"
echo ""
echo "Next steps:"
echo "1. Update your domain in nginx configuration"
echo "2. Set up SSL certificate with Let's Encrypt"
echo "3. Configure your GitHub repository secrets"
echo "4. Push your code to trigger the first deployment"
echo ""
echo "To manually deploy:"
echo "  cd ~/ea_crm && ./deploy_hook.sh" 