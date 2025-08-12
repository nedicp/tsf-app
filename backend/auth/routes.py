from flask import Blueprint, request, jsonify, session, redirect, url_for
from backend.models.user import User
from backend.utils.limiter import limiter
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_username(username):
    """Validate username format"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores and hyphens"
    return True, "Valid"

def validate_password(password):
    """Validate password requirements"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, "Valid"

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("3 per minute")  # Prevent brute force attacks
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password are required'
            }), 400

        user = User.authenticate(username, password)

        if user:
            session['user'] = user.to_dict()

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
@limiter.limit("30 per minute")  # More lenient for logout
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
@limiter.limit("60 per minute")  # Frequent session checks are normal
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
