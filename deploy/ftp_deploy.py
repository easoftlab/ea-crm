#!/usr/bin/env python3
"""
FTP Deployment Script for EA CRM
This script will upload your CRM files to your hosting via FTP
"""
import os
import sys
import ftplib
import zipfile
from datetime import datetime
from pathlib import Path

class FTPDeployer:
    def __init__(self, host, username, password, remote_path="/public_html/crm"):
        self.host = host
        self.username = username
        self.password = password
        self.remote_path = remote_path
        self.ftp = None
        
    def connect(self):
        """Connect to FTP server"""
        try:
            print(f"🔌 Connecting to {self.host}...")
            self.ftp = ftplib.FTP(self.host)
            self.ftp.login(self.username, self.password)
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def upload_file(self, local_path, remote_path):
        """Upload a single file"""
        try:
            with open(local_path, 'rb') as file:
                self.ftp.storbinary(f'STOR {remote_path}', file)
            print(f"✅ Uploaded: {local_path} -> {remote_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to upload {local_path}: {e}")
            return False
    
    def upload_directory(self, local_dir, remote_dir):
        """Upload entire directory recursively"""
        local_path = Path(local_dir)
        
        for item in local_path.rglob('*'):
            if item.is_file():
                # Calculate relative path
                rel_path = item.relative_to(local_path)
                remote_file_path = f"{remote_dir}/{rel_path}".replace('\\', '/')
                
                # Create remote directory if needed
                remote_parent = os.path.dirname(remote_file_path)
                try:
                    self.ftp.mkd(remote_parent)
                except:
                    pass  # Directory might already exist
                
                # Upload file
                self.upload_file(str(item), remote_file_path)
    
    def deploy(self, source_dir="deploy_20250801_013917"):
        """Deploy the CRM application"""
        if not self.connect():
            return False
        
        try:
            print(f"📤 Starting deployment from {source_dir}...")
            
            # Change to remote directory
            try:
                self.ftp.cwd(self.remote_path)
            except:
                print(f"📁 Creating remote directory: {self.remote_path}")
                self.ftp.mkd(self.remote_path)
                self.ftp.cwd(self.remote_path)
            
            # Upload all files
            self.upload_directory(source_dir, ".")
            
            print("✅ Deployment completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False
        finally:
            if self.ftp:
                self.ftp.quit()

def create_deployment_package():
    """Create a fresh deployment package"""
    print("📦 Creating deployment package...")
    
    # Run the deployment script
    import sys
    import os
    sys.path.append('..')
    from deploy import deploy
    zip_file, deploy_dir = deploy.create_deployment_package()
    
    return deploy_dir

def main():
    print("🚀 EA CRM FTP Deployment Tool")
    print("=" * 50)
    
    # Create deployment package
    deploy_dir = create_deployment_package()
    
    # Get FTP credentials
    print("\n🔐 Enter your FTP credentials:")
    host = input("Host (e.g., ftp.eaincorp.com): ").strip()
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    if not all([host, username, password]):
        print("❌ All credentials are required!")
        return
    
    # Create deployer and deploy
    deployer = FTPDeployer(host, username, password)
    
    if deployer.deploy(deploy_dir):
        print("\n🎉 Deployment successful!")
        print("🌐 Your CRM should now be accessible at: https://crm.eaincorp.com")
        print("\n📋 Next steps:")
        print("1. SSH into your server")
        print("2. Navigate to: /home/u539052962/domains/eaincorp.com/public_html/crm")
        print("3. Run: chmod +x server_setup.sh && ./server_setup.sh")
        print("4. Configure your web server (Apache/Nginx)")
    else:
        print("\n❌ Deployment failed. Please check your credentials and try again.")

if __name__ == "__main__":
    main() 