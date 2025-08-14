#!/usr/bin/env python3
"""
Utility script to create users in the database
Usage: python -m backend.utils.create_user
"""

import sys
import os
import getpass
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.models.user import User

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username format"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        return False, "Username can only contain letters, numbers, dots, underscores and hyphens"
    return True, "Valid"

def validate_password(password):
    """Validate password requirements"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, "Valid"

def create_user_interactive():
    """Interactive user creation"""
    print("🔧 User Creation Tool")
    print("=" * 50)

    try:
        # Get username
        while True:
            username = input("Enter username: ").strip()
            is_valid, message = validate_username(username)
            if is_valid:
                break
            print(f"❌ {message}")

        # Get email
        while True:
            email = input("Enter email: ").strip()
            if validate_email(email):
                break
            print("❌ Please enter a valid email address")

        # Get name
        name = input("Enter full name: ").strip()
        if not name:
            name = username.title()

        # Get role
        while True:
            print("\nAvailable roles:")
            print("1. user (default)")
            print("2. analyst")
            print("3. admin")

            role_choice = input("Select role (1-3) [1]: ").strip()
            if not role_choice:
                role_choice = "1"

            if role_choice == "1":
                role = "user"
                break
            elif role_choice == "2":
                role = "analyst"
                break
            elif role_choice == "3":
                role = "admin"
                break
            else:
                print("❌ Please select 1, 2, or 3")

        # Get password
        while True:
            password = getpass.getpass("Enter password: ")
            is_valid, message = validate_password(password)
            if is_valid:
                break
            print(f"❌ {message}")

        # Confirm password
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Passwords do not match")
            return False

        # Create user
        print(f"\n📝 Creating user '{username}'...")
        user, message = User.create_user(username, email, name, password, role)

        if user:
            print(f"✅ {message}")
            print(f"👤 User Details:")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Name: {user.name}")
            print(f"   Role: {user.role}")
            print(f"   Created: {user.created_at}")
            return True
        else:
            print(f"❌ {message}")
            return False

    except KeyboardInterrupt:
        print("\n\n👋 User creation cancelled")
        return False
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False

def list_users():
    """List all users in the database"""
    print("👥 Current Users")
    print("=" * 50)

    try:
        users = User.get_all_users()

        if not users:
            print("No users found in the database")
            return

        for user in users:
            print(f"👤 {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Name: {user.name}")
            print(f"   Role: {user.role}")
            print(f"   Created: {user.created_at}")
            print()

    except Exception as e:
        print(f"❌ Error listing users: {e}")

def main():
    """Main menu"""
    while True:
        print("\n🔧 User Management Tool")
        print("=" * 30)
        print("1. Create new user")
        print("2. List all users")
        print("3. Exit")

        choice = input("\nSelect option (1-3): ").strip()

        if choice == "1":
            create_user_interactive()
        elif choice == "2":
            list_users()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Please select 1, 2, or 3")

if __name__ == "__main__":
    main()
