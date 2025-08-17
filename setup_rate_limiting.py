#!/usr/bin/env python3
# =============================================================================
# RATE LIMITING SETUP SCRIPT - Run this to set up rate limiting
# =============================================================================

import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_file_exists(filepath):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    print(f"{'✅' if exists else '❌'} {filepath} {'exists' if exists else 'not found'}")
    return exists

def main():
    print("="*60)
    print("🔒 SETTING UP RATE LIMITING FOR SENIORCONNECT APP")
    print("="*60)
    
    # Step 1: Check current directory
    print("\n📁 Checking current directory structure...")
    required_files = ['app.py', 'extensions.py', 'user_routes.py']
    for file in required_files:
        check_file_exists(file)
    
    # Step 2: Install required packages
    print("\n📦 Installing required packages...")
    packages = [
        'Flask-Limiter==3.8.0',
        'redis==5.0.1'
    ]
    
    for package in packages:
        success = run_command(f"pip install {package}", f"Installing {package}")
        if not success:
            print(f"⚠️  You may need to install {package} manually")
    
    # Step 3: Check Redis availability
    print("\n🔍 Checking Redis availability...")
    redis_available = run_command("redis-cli ping", "Testing Redis connection")
    
    if not redis_available:
        print("⚠️  Redis not running. Rate limiter will use memory storage.")
        print("💡 To install Redis:")
        print("   - Windows: Download from https://redis.io/download")
        print("   - macOS: brew install redis")
        print("   - Ubuntu: sudo apt-get install redis-server")
        print("   - Docker: docker run -d -p 6379:6379 redis:7-alpine")
    
    # Step 4: Update .env file
    print("\n📝 Checking .env configuration...")
    env_path = '.env'
    if check_file_exists(env_path):
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        if 'REDIS_URL' not in env_content:
            print("➕ Adding REDIS_URL to .env file...")
            with open(env_path, 'a') as f:
                f.write('\n# Redis Configuration for Rate Limiting\n')
                f.write('REDIS_URL=redis://localhost:6379\n')
            print("✅ Added REDIS_URL to .env file")
        else:
            print("✅ REDIS_URL already configured in .env")
    else:
        print("❌ .env file not found. Creating basic .env file...")
        with open(env_path, 'w') as f:
            f.write('# Redis Configuration for Rate Limiting\n')
            f.write('REDIS_URL=redis://localhost:6379\n')
    
    # Step 5: Backup existing files
    print("\n💾 Creating backups of existing files...")
    backup_files = ['extensions.py', 'app.py']
    for file in backup_files:
        if os.path.exists(file):
            backup_name = f"{file}.backup"
            run_command(f"cp {file} {backup_name}", f"Backing up {file}")
    
    # Step 6: Implementation checklist
    print("\n📋 IMPLEMENTATION CHECKLIST:")
    print("="*40)
    
    checklist = [
        "✅ Install Flask-Limiter and redis packages",
        "✅ Update .env file with REDIS_URL",
        "⚠️  Update extensions.py with the fixed version from the artifact",
        "⚠️  Update app.py with rate limiting error handler",
        "⚠️  Add rate limiting decorators to your routes",
        "⚠️  Create rate_limit_exceeded.html template",
        "⚠️  Test the rate limiting functionality"
    ]
    
    for item in checklist:
        print(f"   {item}")
    
    print("\n🚀 NEXT STEPS:")
    print("="*40)
    print("1. Replace your extensions.py with the fixed version from the artifact")
    print("2. Update your app.py with the rate limiting error handler")
    print("3. Add @limiter.limit() decorators to your routes")
    print("4. Test with: python -c 'from app import create_app; app = create_app(); print(\"Rate limiting ready!\")'")
    print("5. Start your application and test rate limiting")
    
    print("\n🔒 SECURITY BENEFITS:")
    print("="*40)
    print("• Prevents brute force attacks on login")
    print("• Stops form submission spam")
    print("• Protects API endpoints from abuse")
    print("• Prevents resource exhaustion attacks")
    print("• OWASP A05:2021 Security Misconfiguration protection")
    
    print("\n" + "="*60)
    print("🎉 RATE LIMITING SETUP COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    main()