#!/usr/bin/env python3
"""
Generate Secret Key for EA CRM
This script generates a secure secret key for Flask application
"""

import secrets
import string

def generate_secret_key():
    """Generate a secure secret key"""
    
    print("🔐 Generating Secret Key for EA CRM...")
    print("=" * 50)
    
    # Generate a secure random string
    alphabet = string.ascii_letters + string.digits + string.punctuation
    secret_key = ''.join(secrets.choice(alphabet) for _ in range(50))
    
    print("✅ Your Secret Key:")
    print("-" * 50)
    print(secret_key)
    print("-" * 50)
    
    print("\n📋 How to use this:")
    print("1. Copy the secret key above")
    print("2. Add it to Vercel Environment Variables:")
    print("   - Key: SECRET_KEY")
    print("   - Value: (paste the key above)")
    print("3. Also add it to your local .env file")
    
    print("\n⚠️  Security Notes:")
    print("- Keep this key secret and secure")
    print("- Don't share it publicly")
    print("- Use different keys for development and production")
    
    return secret_key

def generate_simple_key():
    """Generate a simpler key for development"""
    
    print("\n🔑 Simple Secret Key (for development):")
    print("-" * 50)
    simple_key = secrets.token_hex(32)
    print(simple_key)
    print("-" * 50)
    
    return simple_key

if __name__ == "__main__":
    # Generate both types of keys
    secure_key = generate_secret_key()
    simple_key = generate_simple_key()
    
    print("\n🎯 Recommended for Vercel:")
    print("Use the simple key (second one) for easier setup")
    print("Use the secure key (first one) for production") 