#!/usr/bin/env python3
"""
Upload individual CRM files directly to the crm directory
"""
import os
import ftplib
from ftplib import FTP

# FTP Configuration
FTP_HOST = "145.223.77.49"
FTP_USERNAME = "u539052962"
FTP_PASSWORD = "Emon_@17711"

def upload_file(ftp, local_path, remote_path):
    """Upload a single file"""
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"✅ Uploaded {local_path} -> {remote_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to upload {local_path}: {e}")
        return False

def upload_directory(ftp, local_dir, remote_dir):
    """Upload a directory recursively"""
    for root, dirs, files in os.walk(local_dir):
        # Create remote directory
        remote_root = root.replace(local_dir, remote_dir, 1)
        try:
            ftp.mkd(remote_root)
        except:
            pass  # Directory might already exist
        
        # Upload files
        for file in files:
            local_file = os.path.join(root, file)
            remote_file = os.path.join(remote_root, file).replace('\\', '/')
            upload_file(ftp, local_file, remote_file)

def main():
    """Main upload function"""
    print("🚀 Starting direct file upload...")
    
    try:
        with FTP(FTP_HOST) as ftp:
            ftp.login(FTP_USERNAME, FTP_PASSWORD)
            print("✅ FTP connection established!")
            
            # Change to crm directory
            try:
                ftp.cwd('crm')
            except:
                print("❌ Could not access crm directory")
                return
            
            # Upload essential files
            files_to_upload = [
                'config.py',
                'requirements.txt', 
                'wsgi.py',
                '.htaccess'
            ]
            
            for file in files_to_upload:
                if os.path.exists(file):
                    upload_file(ftp, file, file)
            
            # Upload directories
            dirs_to_upload = ['app', 'static', 'templates', 'instance']
            
            for dir_name in dirs_to_upload:
                if os.path.exists(dir_name):
                    print(f"📁 Uploading directory: {dir_name}")
                    upload_directory(ftp, dir_name, dir_name)
            
            print("🎉 Upload completed!")
            
    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    main() 