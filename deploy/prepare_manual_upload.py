#!/usr/bin/env python3
"""
Prepare Manual Upload for EA CRM
This script prepares files for manual upload via hosting file manager
"""
import os
import shutil
import zipfile
from datetime import datetime

def prepare_manual_upload():
    """Prepare files for manual upload"""
    
    print("Preparing files for manual upload...")
    print("=" * 50)
    
    # Create deployment package
    deploy_dir = f"crm_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(deploy_dir, exist_ok=True)
    
    # Files to include
    include_files = [
        'app/',
        'config.py',
        'requirements.txt',
        'wsgi.py',
        '.htaccess',
        'docs/README.md',
        'server_setup.sh',
        'apache_config.conf'
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
    
    print(f"Creating upload package: {deploy_dir}")
    
    # Copy files
    for item in include_files:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.copytree(item, os.path.join(deploy_dir, item), 
                               ignore=shutil.ignore_patterns(*exclude_patterns))
            else:
                shutil.copy2(item, deploy_dir)
            print(f"Copied: {item}")
    
    # Create necessary directories
    instance_dir = os.path.join(deploy_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    
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
    
    print(f"Upload package created: {zip_filename}")
    print(f"Unzipped directory: {deploy_dir}")
    
    print("\n" + "=" * 50)
    print("MANUAL UPLOAD INSTRUCTIONS")
    print("=" * 50)
    print("1. Upload the entire folder to your hosting file manager:")
    print(f"   Folder: {deploy_dir}")
    print("   OR")
    print(f"   ZIP file: {zip_filename}")
    print()
    print("2. Extract to: /home/u539052962/domains/eaincorp.com/public_html/crm")
    print()
    print("3. SSH into your server and run:")
    print("   cd /home/u539052962/domains/eaincorp.com/public_html/crm")
    print("   chmod +x server_setup.sh")
    print("   ./server_setup.sh")
    print()
    print("4. Configure your web server (Apache/Nginx)")
    print()
    print("5. Visit: https://crm.eaincorp.com")
    
    return deploy_dir, zip_filename

if __name__ == "__main__":
    prepare_manual_upload() 