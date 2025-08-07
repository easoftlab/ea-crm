#!/usr/bin/env python3
"""
Automated Deployment Script for EA CRM
Configure your credentials and run this script for automated deployment
"""
import os
import sys
import ftplib
import subprocess
from pathlib import Path

# ============================================================================
# CONFIGURE YOUR HOSTING CREDENTIALS HERE
# ============================================================================

# FTP Configuration
FTP_HOST = "145.223.77.49"
FTP_USERNAME = "u539052962"
FTP_PASSWORD = "Emon_@17711"
REMOTE_PATH = "crm"

# Server Configuration
SERVER_SSH_HOST = "your_server_ip"  # Replace with your server IP
SERVER_SSH_USER = "your_ssh_user"   # Replace with your SSH username
SERVER_SSH_KEY = "~/.ssh/id_rsa"    # Path to your SSH key (optional)

# ============================================================================
# DO NOT MODIFY BELOW THIS LINE
# ============================================================================

class AutoDeployer:
    def __init__(self):
        self.ftp = None
        
    def create_deployment_package(self):
        """Create a fresh deployment package"""
        print("📦 Creating deployment package...")
        
        try:
            # Run the deployment script
            result = subprocess.run([sys.executable, "../deploy.py"], 
                                  capture_output=True, text=True, cwd="..")
            if result.returncode == 0:
                print("✅ Deployment package created successfully!")
                return True
            else:
                print(f"❌ Failed to create deployment package: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Failed to create deployment package: {e}")
            return False
    
    def ftp_upload(self):
        """Upload files via FTP"""
        try:
            print(f"🔌 Connecting to {FTP_HOST}...")
            self.ftp = ftplib.FTP(FTP_HOST)
            self.ftp.login(FTP_USERNAME, FTP_PASSWORD)
            print("✅ FTP connection established!")
            
            # Navigate to remote directory
            try:
                self.ftp.cwd(REMOTE_PATH)
            except:
                print(f"📁 Creating remote directory: {REMOTE_PATH}")
                self.ftp.mkd(REMOTE_PATH)
                self.ftp.cwd(REMOTE_PATH)
            
            # Upload deployment directory - find the latest deployment
            deploy_dirs = [d for d in os.listdir('.') if d.startswith('deploy_')]
            if deploy_dirs:
                deploy_dir = max(deploy_dirs)  # Get the latest deployment
                print(f"📦 Using deployment package: {deploy_dir}")
                self._upload_directory(deploy_dir, ".")
            else:
                print("❌ No deployment package found. Run deploy.py first.")
                return False
            
            print("✅ FTP upload completed!")
            return True
            
        except Exception as e:
            print(f"❌ FTP upload failed: {e}")
            return False
        finally:
            if self.ftp:
                self.ftp.quit()
    
    def _upload_directory(self, local_dir, remote_dir):
        """Upload directory recursively"""
        local_path = Path(local_dir)
        
        for item in local_path.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(local_path)
                remote_file_path = f"{remote_dir}/{rel_path}".replace('\\', '/')
                
                # Create remote directory if needed
                remote_parent = os.path.dirname(remote_file_path)
                try:
                    self.ftp.mkd(remote_parent)
                except:
                    pass
                
                # Upload file
                with open(item, 'rb') as file:
                    self.ftp.storbinary(f'STOR {remote_file_path}', file)
                print(f"✅ Uploaded: {item.name}")
    
    def run_server_setup(self):
        """Run server setup commands via SSH"""
        print("🔧 Running server setup...")
        
        commands = [
            f"cd {REMOTE_PATH}",
            "chmod +x server_setup.sh",
            "./server_setup.sh",
            "find . -type d -exec chmod 755 {} \\;",
            "find . -type f -exec chmod 644 {} \\;",
            "chmod 755 instance/",
            "chmod 755 app/static/uploads/"
        ]
        
        ssh_command = f"ssh {SERVER_SSH_USER}@{SERVER_SSH_HOST} '{'; '.join(commands)}'"
        
        try:
            result = subprocess.run(ssh_command, shell=True, check=True, 
                                  capture_output=True, text=True)
            print("✅ Server setup completed!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Server setup failed: {e}")
            print(f"Error output: {e.stderr}")
            return False
    
    def deploy(self):
        """Complete deployment process"""
        print("🚀 Starting automated deployment...")
        
        # Step 1: Create deployment package
        if not self.create_deployment_package():
            return False
        
        # Step 2: Upload via FTP
        if not self.ftp_upload():
            return False
        
        # Step 3: Run server setup (if SSH is configured)
        if SERVER_SSH_HOST != "your_server_ip":
            if not self.run_server_setup():
                print("⚠️  Server setup failed, but files are uploaded.")
                print("   You can manually run the setup commands.")
        
        print("\n🎉 Deployment completed!")
        print("🌐 Your CRM should now be accessible at: https://crm.eaincorp.com")
        
        return True

def check_configuration():
    """Check if configuration is properly set"""
    issues = []
    
    if FTP_HOST == "ftp.eaincorp.com" and FTP_USERNAME == "your_username":
        issues.append("FTP credentials not configured")
    if FTP_PASSWORD == "your_password":
        issues.append("FTP_PASSWORD not configured")
    
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n📝 Please edit auto_deploy.py and configure your credentials.")
        return False
    
    return True

def main():
    print("🚀 EA CRM Automated Deployment")
    print("=" * 50)
    
    # Check configuration
    if not check_configuration():
        return
    
    # Create deployer and run deployment
    deployer = AutoDeployer()
    
    if deployer.deploy():
        print("\n✅ Deployment successful!")
        print("\n📋 Manual steps (if needed):")
        print("1. SSH into your server")
        print("2. Navigate to: /home/u539052962/domains/eaincorp.com/public_html/crm")
        print("3. Run: ./server_setup.sh")
        print("4. Configure your web server (Apache/Nginx)")
    else:
        print("\n❌ Deployment failed. Please check the error messages above.")

if __name__ == "__main__":
    main() 