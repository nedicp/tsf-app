from flask import Blueprint, request, jsonify, session, redirect, url_for
from backend.models.user import User
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

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

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password are required'
            }), 400
        
        # Validate username format
        is_valid, message = validate_username(username)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Validate password
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Authenticate user
        user = User.authenticate(username, password)
        
        if user:
            # Store user in session
            session['user'] = user.to_dict()
            session.permanent = True
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict(),
                'redirect': '/dashboard.html'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid username or password'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Logged out successfully',
            'redirect': '/index.html'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred during logout'
        }), 500

@auth_bp.route('/check-session', methods=['GET'])
def check_session():
    """Check if user is logged in"""
    if 'user' in session:
        return jsonify({
            'authenticated': True,
            'user': session['user']
        }), 200
    else:
        return jsonify({
            'authenticated': False
        }), 200
