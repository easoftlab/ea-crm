#!/usr/bin/env python3
"""
GitHub Deployment Setup Script
Helps you set up your GitHub repository for CI/CD deployment
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"❌ Command failed: {command}")
            print(f"Error: {result.stderr}")
            return False
        return result
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def check_git_status():
    """Check if we're in a git repository"""
    result = run_command("git status", check=False)
    if result and result.returncode == 0:
        return True
    return False

def initialize_git():
    """Initialize git repository if not already done"""
    if not check_git_status():
        print("📁 Initializing git repository...")
        run_command("git init")
        run_command("git add .")
        run_command('git commit -m "Initial commit with CI/CD setup"')
        print("✅ Git repository initialized")
    else:
        print("✅ Git repository already exists")

def setup_github_remote():
    """Set up GitHub remote repository"""
    print("\n🔗 Setting up GitHub remote...")
    
    # Get current remote
    result = run_command("git remote -v", check=False)
    if result and "origin" in result.stdout:
        print("✅ GitHub remote already configured")
        return
    
    # Ask for GitHub repository URL
    print("\n📝 Please provide your GitHub repository URL")
    print("Example: https://github.com/yourusername/ea-crm.git")
    repo_url = input("GitHub repository URL: ").strip()
    
    if not repo_url:
        print("❌ No repository URL provided")
        return
    
    # Add remote and push
    run_command(f"git remote add origin {repo_url}")
    run_command("git branch -M main")
    run_command("git push -u origin main")
    print("✅ GitHub remote configured and code pushed")

def create_github_secrets_guide():
    """Create a guide for setting up GitHub secrets"""
    print("\n🔐 GitHub Secrets Setup Guide")
    print("=" * 50)
    print("Follow these steps to configure your GitHub repository:")
    print()
    print("1. Go to your GitHub repository")
    print("2. Click on 'Settings' tab")
    print("3. Click on 'Secrets and variables' → 'Actions'")
    print("4. Click 'New repository secret'")
    print("5. Add the following secrets:")
    print()
    print("   FTP_SERVER:")
    print("   - Value: Your Hostinger FTP server")
    print("   - Example: ftp.yourdomain.com")
    print()
    print("   FTP_USERNAME:")
    print("   - Value: Your Hostinger FTP username")
    print("   - Example: your_username")
    print()
    print("   FTP_PASSWORD:")
    print("   - Value: Your Hostinger FTP password")
    print("   - Example: your_password")
    print()
    print("6. Click 'Add secret' for each one")
    print()
    print("After setting up secrets, any push to main branch will trigger deployment!")

def check_requirements():
    """Check if all required files exist"""
    required_files = [
        "requirements.txt",
        "wsgi.py",
        "config.py",
        ".github/workflows/deploy.yml",
        "deploy/deploy_script.py",
        "deploy/hostinger_setup.sh"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required files found")
    return True

def main():
    """Main setup function"""
    print("🚀 EA CRM GitHub Deployment Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Please run this script from the EA CRM project root directory")
        sys.exit(1)
    
    # Check requirements
    if not check_requirements():
        print("❌ Setup cannot continue due to missing files")
        sys.exit(1)
    
    # Initialize git
    initialize_git()
    
    # Setup GitHub remote
    setup_github_remote()
    
    # Create secrets guide
    create_github_secrets_guide()
    
    print("\n🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Configure GitHub secrets (see guide above)")
    print("2. Set up your Hostinger server using deploy/hostinger_setup.sh")
    print("3. Push changes to trigger your first deployment!")
    print("\nFor detailed instructions, see: deploy/README_DEPLOYMENT.md")

if __name__ == "__main__":
    main() 