#!/usr/bin/env python3
"""
Deployment script for EA CRM
"""
import os
import shutil
import zipfile
from datetime import datetime

def create_deployment_package():
    """Create a deployment package with all necessary files"""
    
    # Files to include in deployment
    include_files = [
        'app/',
        'config.py',
        'requirements.txt',
        'wsgi.py',
        '.htaccess',
        'docs/README.md'
    ]
    
    # Files to exclude
    exclude_patterns = [
        '__pycache__',
        '.git',
        '.vscode',
        'tests/',
        'scripts/',
        'docs/',
        '*.pyc',
        '*.log',
        'chrome_profile/',
        'instance/',
        '*.db',
        '*.db-journal'
    ]
    
    # Create deployment directory
    deploy_dir = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(deploy_dir, exist_ok=True)
    
    print(f"Creating deployment package: {deploy_dir}")
    
    # Copy files
    for item in include_files:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.copytree(item, os.path.join(deploy_dir, item), 
                               ignore=shutil.ignore_patterns(*exclude_patterns))
            else:
                shutil.copy2(item, deploy_dir)
            print(f"Copied: {item}")
    
    # Create instance directory for database
    instance_dir = os.path.join(deploy_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    
    # Create empty database files
    open(os.path.join(instance_dir, 'leads.db'), 'a').close()
    open(os.path.join(instance_dir, 'scrap.db'), 'a').close()
    
    # Create uploads directory
    uploads_dir = os.path.join(deploy_dir, 'app', 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(os.path.join(uploads_dir, 'profiles'), exist_ok=True)
    
    # Create zip file
    zip_filename = f"{deploy_dir}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, deploy_dir)
                zipf.write(file_path, arcname)
    
    print(f"Deployment package created: {zip_filename}")
    print(f"Unzipped directory: {deploy_dir}")
    
    return zip_filename, deploy_dir

def print_deployment_instructions():
    """Print deployment instructions"""
    
    print("\n" + "="*60)
    print("🚀 DEPLOYMENT INSTRUCTIONS")
    print("="*60)
    
    print("\n1. 📤 UPLOAD FILES:")
    print("   - Upload the entire project folder to: /home/u539052962/domains/eaincorp.com/public_html/crm")
    print("   - Or upload the zip file and extract it on the server")
    
    print("\n2. 🔧 SERVER SETUP:")
    print("   - Ensure Python 3.7+ is installed")
    print("   - Install required packages: pip install -r requirements.txt")
    print("   - Set up virtual environment (recommended)")
    
    print("\n3. 🌐 WEB SERVER CONFIGURATION:")
    print("   - Configure Apache/Nginx to use wsgi.py as the entry point")
    print("   - Ensure .htaccess is enabled")
    print("   - Set proper file permissions (755 for directories, 644 for files)")
    
    print("\n4. 🔐 ENVIRONMENT VARIABLES:")
    print("   - Set SECRET_KEY environment variable")
    print("   - Configure database paths if needed")
    
    print("\n5. 📊 DATABASE SETUP:")
    print("   - The instance/ directory will be created automatically")
    print("   - Database files will be created on first run")
    
    print("\n6. 🔍 TESTING:")
    print("   - Visit: https://crm.eaincorp.com")
    print("   - Check for any error logs")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        zip_file, deploy_dir = create_deployment_package()
        print_deployment_instructions()
    except Exception as e:
        print(f"Error creating deployment package: {e}") 