#!/usr/bin/env python3
"""
Secure Configuration Script for EA CRM Deployment
This script helps you configure your FTP password securely
"""
import getpass
import re

def configure_deployment():
    """Configure deployment with your FTP password"""
    
    print("🔐 EA CRM Deployment Configuration")
    print("=" * 50)
    
    # Read current auto_deploy.py
    with open('auto_deploy.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Get password securely
    print("\n📝 Please enter your FTP password:")
    password = getpass.getpass("Password: ")
    
    if not password:
        print("❌ Password cannot be empty!")
        return
    
    # Confirm password
    confirm_password = getpass.getpass("Confirm password: ")
    
    if password != confirm_password:
        print("❌ Passwords don't match!")
        return
    
    # Update the password in auto_deploy.py
    updated_content = re.sub(
        r'FTP_PASSWORD = "your_password"  # Replace with your actual password',
        f'FTP_PASSWORD = "{password}"',
        content
    )
    
    # Write updated content
    with open('auto_deploy.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("\n✅ Configuration updated successfully!")
    print("🔐 Your FTP credentials are now configured:")
    print(f"   Host: ftp.eaincorp.com")
    print(f"   Username: u539052962.crm")
    print(f"   Directory: /home/u539052962/domains/eaincorp.com/public_html/crm")
    
    print("\n🚀 You can now run the deployment:")
    print("   python auto_deploy.py")
    
    print("\n⚠️  Security Note:")
    print("   - Your password is stored in auto_deploy.py")
    print("   - Keep this file secure and don't share it")
    print("   - Consider using environment variables for production")

if __name__ == "__main__":
    configure_deployment() 