#!/usr/bin/env python3
"""
Upload CRM files directly to the crm directory
"""
import os
import ftplib
import zipfile
import tempfile
import shutil

# FTP Configuration
FTP_HOST = "145.223.77.49"
FTP_USERNAME = "u539052962"
FTP_PASSWORD = "Emon_@17711"
REMOTE_PATH = "crm"  # This will upload to /home/u539052962/domains/eaincorp.com/public_html/crm

def upload_files():
    """Upload CRM files to the server"""
    print("🚀 Uploading CRM files to server...")
    
    # Create a temporary directory for the CRM files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy essential files
        essential_files = [
            'app', 'config.py', 'requirements.txt', 'wsgi.py', '.htaccess',
            'instance', 'static', 'templates', 'scripts', 'tests'
        ]
        
        for item in essential_files:
            if os.path.exists(item):
                dest_path = os.path.join(temp_dir, item)
                if os.path.isdir(item):
                    shutil.copytree(item, dest_path)
                else:
                    shutil.copy2(item, dest_path)
                print(f"✅ Copied {item}")
        
        # Create a zip file
        zip_path = os.path.join(temp_dir, "crm_deployment.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != "crm_deployment.zip":
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Upload to server
        try:
            with ftplib.FTP(FTP_HOST) as ftp:
                ftp.login(FTP_USERNAME, FTP_PASSWORD)
                print("✅ FTP connection established!")
                
                # Change to the crm directory
                try:
                    ftp.cwd(REMOTE_PATH)
                except ftplib.error_perm:
                    print(f"❌ Could not access {REMOTE_PATH} directory")
                    return False
                
                # Upload the zip file
                with open(zip_path, 'rb') as f:
                    ftp.storbinary(f'STOR crm_deployment.zip', f)
                print("✅ CRM files uploaded!")
                
                # Extract the files on the server
                print("📦 Extracting files on server...")
                ftp.quit()
                
                return True
                
        except Exception as e:
            print(f"❌ FTP upload failed: {e}")
            return False

if __name__ == "__main__":
    if upload_files():
        print("🎉 Upload completed successfully!")
        print("📋 Next steps:")
        print("1. SSH into your server")
        print("2. Navigate to the crm directory")
        print("3. Run: unzip crm_deployment.zip")
        print("4. Run: pip install -r requirements.txt")
        print("5. Set up your web server configuration")
    else:
        print("❌ Upload failed!") 