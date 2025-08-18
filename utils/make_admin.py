#!/usr/bin/env python3
"""
Script to make a user an admin
Usage: python make_admin.py <email>
"""

import sys
from models.user import User
from extensions import db
from app import app  # Import your Flask app

def make_admin(email):
    """Make a user an admin by their email address"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found")
            return False
        
        if user.is_admin:
            print(f"✅ User '{email}' is already an admin")
            return True
        
        user.is_admin = True
        db.session.commit()
        print(f"✅ User '{email}' is now an admin!")
        return True

def list_admins():
    """List all admin users"""
    with app.app_context():
        admins = User.query.filter_by(is_admin=True).all()
        
        if not admins:
            print("No admin users found")
            return
        
        print("Admin Users:")
        print("-" * 50)
        for admin in admins:
            print(f"📧 {admin.email} - {admin.display_name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python make_admin.py <email>          - Make user admin")
        print("  python make_admin.py --list           - List all admins")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_admins()
    else:
        email = sys.argv[1].lower().strip()
        make_admin(email)