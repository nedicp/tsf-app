import bcrypt
from datetime import datetime
from bson.objectid import ObjectId
from backend.utils.database import db
import re

class User:
    def __init__(self, username, email, name, role, created_at=None, _id=None):
        self.username = username
        self.email = email
        self.name = name
        self.role = role
        self.created_at = created_at or datetime.utcnow()
        self._id = _id

    def save(self):
        """Save user to database"""
        try:
            users_collection = db.get_collection('users')

            user_data = {
                'username': self.username,
                'email': self.email,
                'name': self.name,
                'role': self.role,
                'created_at': self.created_at
            }

            if self._id:
                # Update existing user
                result = users_collection.update_one(
                    {'_id': ObjectId(self._id)},
                    {'$set': user_data}
                )
                return result.modified_count > 0
            else:
                # Create new user
                result = users_collection.insert_one(user_data)
                self._id = str(result.inserted_id)
                return True

        except Exception as e:
            print(f"Error saving user: {e}")
            return False

    @staticmethod
    def create_user(username, email, name, password, role='user'):
        """Create a new user with hashed password"""
        try:
            users_collection = db.get_collection('users')

            # Check if user already exists
            if users_collection.find_one({'$or': [{'username': username}, {'email': email}]}):
                return None, "User with this username or email already exists"

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Create user document
            user_data = {
                'username': username,
                'email': email,
                'name': name,
                'password_hash': hashed_password,
                'role': role,
                'created_at': datetime.utcnow()
            }

            # Insert into database
            result = users_collection.insert_one(user_data)

            # Return user object (without password)
            user = User(username, email, name, role, user_data['created_at'], str(result.inserted_id))
            return user, "User created successfully"

        except Exception as e:
            print(f"Error creating user: {e}")
            return None, f"Error creating user: {str(e)}"

    @staticmethod
    def authenticate(username, password):
        """Authenticate user with username and password"""
        try:
            users_collection = db.get_collection('users')

            # Find user by username
            user_doc = users_collection.find_one({'username': username})

            if not user_doc:
                return None

            # Check password
            if bcrypt.checkpw(password.encode('utf-8'), user_doc['password_hash']):
                return User(
                    user_doc['username'],
                    user_doc['email'],
                    user_doc['name'],
                    user_doc['role'],
                    user_doc['created_at'],
                    str(user_doc['_id'])
                )

            return None

        except Exception as e:
            print(f"Error during authentication: {e}")
            return None

    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        try:
            users_collection = db.get_collection('users')
            user_doc = users_collection.find_one({'username': username})

            if user_doc:
                return User(
                    user_doc['username'],
                    user_doc['email'],
                    user_doc['name'],
                    user_doc['role'],
                    user_doc['created_at'],
                    str(user_doc['_id'])
                )

            return None

        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None

    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        try:
            users_collection = db.get_collection('users')
            user_doc = users_collection.find_one({'email': email})

            if user_doc:
                return User(
                    user_doc['username'],
                    user_doc['email'],
                    user_doc['name'],
                    user_doc['role'],
                    user_doc['created_at'],
                    str(user_doc['_id'])
                )

            return None

        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None

    @staticmethod
    def get_all_users():
        """Get all users (admin function)"""
        try:
            users_collection = db.get_collection('users')
            users = []

            for user_doc in users_collection.find({}, {'password_hash': 0}):  # Exclude password
                users.append(User(
                    user_doc['username'],
                    user_doc['email'],
                    user_doc['name'],
                    user_doc['role'],
                    user_doc['created_at'],
                    str(user_doc['_id'])
                ))

            return users

        except Exception as e:
            print(f"Error getting all users: {e}")
            return []

    @staticmethod
    def delete_user(username):
        """Delete user by username"""
        try:
            users_collection = db.get_collection('users')
            result = users_collection.delete_one({'username': username})
            return result.deleted_count > 0

        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    @staticmethod
    def update_password(username, new_password):
        """Update user password"""
        try:
            users_collection = db.get_collection('users')

            # Hash new password
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

            # Update password
            result = users_collection.update_one(
                {'username': username},
                {'$set': {'password_hash': hashed_password}}
            )

            return result.modified_count > 0

        except Exception as e:
            print(f"Error updating password: {e}")
            return False

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self._id,
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
