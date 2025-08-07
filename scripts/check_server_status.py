#!/usr/bin/env python3
"""
Server Status Check Script for EA CRM
This script helps troubleshoot server connection issues
"""

import os
import sys
import requests
import subprocess
import time

def check_dns_resolution():
    """Check if DNS is resolving correctly"""
    print("🔍 Checking DNS Resolution...")
    
    try:
        import socket
        ip = socket.gethostbyname('crm.eaincorp.com')
        print(f"✅ DNS Resolution: crm.eaincorp.com → {ip}")
        return True
    except Exception as e:
        print(f"❌ DNS Resolution failed: {e}")
        return False

def check_server_connectivity():
    """Check if server is reachable"""
    print("\n🌐 Checking Server Connectivity...")
    
    try:
        response = requests.get('https://crm.eaincorp.com', timeout=10)
        print(f"✅ Server responding: Status {response.status_code}")
        return True
    except requests.exceptions.Timeout:
        print("❌ Server timeout - application not running")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection refused - server not accessible")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def check_hostinger_status():
    """Check Hostinger server status"""
    print("\n🏠 Checking Hostinger Server Status...")
    
    # Common Hostinger IPs
    hostinger_ips = ['145.223.77.49', '185.27.134.10', '185.27.134.11']
    
    for ip in hostinger_ips:
        try:
            response = requests.get(f'http://{ip}', timeout=5)
            print(f"✅ Hostinger server {ip} is reachable")
            return True
        except:
            continue
    
    print("❌ Hostinger servers not responding")
    return False

def check_application_files():
    """Check if application files are deployed"""
    print("\n📁 Checking Application Files...")
    
    # Files that should exist
    required_files = [
        'wsgi.py',
        'app/__init__.py',
        'config.py',
        'requirements.txt',
        '.htaccess'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def check_python_environment():
    """Check Python environment"""
    print("\n🐍 Checking Python Environment...")
    
    try:
        # Check Python version
        python_version = subprocess.check_output(['python', '--version'], text=True)
        print(f"✅ Python: {python_version.strip()}")
        
        # Check if Flask is installed
        try:
            import flask
            print(f"✅ Flask version: {flask.__version__}")
        except ImportError:
            print("❌ Flask not installed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Python environment error: {e}")
        return False

def check_web_server():
    """Check if web server is configured"""
    print("\n🌐 Checking Web Server Configuration...")
    
    # Check if .htaccess exists and has correct content
    if os.path.exists('.htaccess'):
        with open('.htaccess', 'r') as f:
            content = f.read()
            if 'wsgi.py' in content:
                print("✅ .htaccess configured for WSGI")
                return True
            else:
                print("❌ .htaccess not configured for WSGI")
                return False
    else:
        print("❌ .htaccess file missing")
        return False

def main():
    """Main troubleshooting function"""
    print("🔧 EA CRM Server Troubleshooting")
    print("=" * 50)
    
    # Run all checks
    checks = [
        ("DNS Resolution", check_dns_resolution),
        ("Server Connectivity", check_server_connectivity),
        ("Hostinger Status", check_hostinger_status),
        ("Application Files", check_application_files),
        ("Python Environment", check_python_environment),
        ("Web Server Config", check_web_server)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TROUBLESHOOTING SUMMARY")
    print("=" * 50)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(results)} checks passed")
    
    if passed == len(results):
        print("🎉 All checks passed! Server should be working.")
    else:
        print("\n🔧 RECOMMENDED FIXES:")
        print("1. Check if Flask app is running on server")
        print("2. Verify .htaccess configuration")
        print("3. Check Hostinger Python support")
        print("4. Contact Hostinger support if needed")

if __name__ == "__main__":
    main() 