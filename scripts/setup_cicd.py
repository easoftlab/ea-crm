#!/usr/bin/env python3
"""
CI/CD Setup Helper Script for EA CRM
This script guides you through setting up the CI/CD pipeline
"""

import os
import subprocess
import sys
from pathlib import Path

def print_header():
    """Print a nice header"""
    print("🚀 EA CRM CI/CD Pipeline Setup")
    print("=" * 50)
    print()

def check_git_status():
    """Check if we're in a git repository"""
    try:
        result = subprocess.run(['git', 'status'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def initialize_git():
    """Initialize git repository"""
    print("📁 Setting up Git repository...")
    
    if not check_git_status():
        subprocess.run(['git', 'init'])
        print("✅ Git repository initialized")
    else:
        print("✅ Git repository already exists")
    
    # Add all files
    subprocess.run(['git', 'add', '.'])
    
    # Check if there are changes to commit
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        subprocess.run(['git', 'commit', '-m', 'Initial commit with EA CRM application'])
        print("✅ Initial commit created")
    else:
        print("✅ No changes to commit")

def setup_github_remote():
    """Set up GitHub remote"""
    print("\n🔗 Setting up GitHub remote...")
    
    # Check if remote already exists
    result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
    if 'origin' in result.stdout:
        print("✅ GitHub remote already configured")
        return
    
    print("\n📝 Please provide your GitHub repository URL")
    print("Example: https://github.com/yourusername/ea-crm.git")
    repo_url = input("GitHub repository URL: ").strip()
    
    if not repo_url:
        print("❌ No repository URL provided")
        return
    
    # Add remote
    subprocess.run(['git', 'remote', 'add', 'origin', repo_url])
    subprocess.run(['git', 'branch', '-M', 'main'])
    
    print("✅ GitHub remote configured")
    print("💡 Don't forget to push your code: git push -u origin main")

def create_github_secrets_guide():
    """Create guide for GitHub secrets"""
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

def check_required_files():
    """Check if all required files exist"""
    print("\n📋 Checking required files...")
    
    required_files = [
        "requirements.txt",
        "wsgi.py",
        "config.py",
        "app/__init__.py",
        ".github/workflows/deploy.yml",
        "deploy/post_deploy_setup.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    else:
        print("\n✅ All required files present")
        return True

def create_test_deployment():
    """Create a test deployment"""
    print("\n🧪 Creating test deployment...")
    
    # Create a test file
    test_content = f"# Test deployment - {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}\n"
    with open('test_deployment.md', 'w') as f:
        f.write(test_content)
    
    # Add and commit
    subprocess.run(['git', 'add', 'test_deployment.md'])
    subprocess.run(['git', 'commit', '-m', 'Test CI/CD deployment'])
    
    print("✅ Test deployment file created")
    print("💡 Push to GitHub to test deployment: git push origin main")

def main():
    """Main setup function"""
    print_header()
    
    # Check if we're in the right directory
    if not os.path.exists('app'):
        print("❌ Please run this script from the EA CRM project root directory")
        return
    
    # Check required files
    if not check_required_files():
        print("❌ Some required files are missing. Please ensure all files are present.")
        return
    
    # Initialize git
    initialize_git()
    
    # Setup GitHub remote
    setup_github_remote()
    
    # Create GitHub secrets guide
    create_github_secrets_guide()
    
    # Create test deployment
    create_test_deployment()
    
    print("\n🎉 CI/CD Setup Complete!")
    print("=" * 50)
    print("Next steps:")
    print("1. Push your code to GitHub: git push -u origin main")
    print("2. Configure GitHub secrets (see guide above)")
    print("3. Test deployment by pushing changes")
    print("4. Check your website for the live application")
    print()
    print("📚 For detailed instructions, see: deploy/CI_CD_SETUP_GUIDE.md")

if __name__ == "__main__":
    main() 