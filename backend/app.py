from flask import Flask, session, redirect, url_for, request, send_from_directory, jsonify
from flask_session import Session
from flask_cors import CORS
from backend.config import Config
from backend.auth.routes import auth_bp
from backend.api.routes import api_bp
from backend.utils.database import db
from backend.utils.limiter import limiter
import os

def create_app():
    app = Flask(__name__, 
                static_folder='../frontend',
                static_url_path='')
    
    # Load configuration
    app.config.from_object(Config)
    
    # Configure CORS
    cors_origins = app.config.get('CORS_ORIGINS', [])
    if os.environ.get('FLASK_ENV') == 'production':
        # Add production domain from environment
        production_domain = os.environ.get('PRODUCTION_DOMAIN')
        if production_domain:
            cors_origins.append(f'https://{production_domain}')
    
    CORS(app, 
         origins=cors_origins,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'Accept'],
         supports_credentials=True,        # Allow cookies/sessions
         max_age=600)                      # Cache preflight for 10 minutes
    
    # Initialize Rate Limiter
    limiter.init_app(app)
    limiter._default_limits = app.config.get('RATELIMIT_DEFAULT', "200 per day;50 per hour")
    limiter._storage_uri = app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    limiter._strategy = app.config.get('RATELIMIT_STRATEGY', 'fixed-window')
    
    # Initialize Flask-Session
    Session(app)
    
    # Initialize database connection
    try:
        db.connect()
        print("✅ Database connection initialized")
    except Exception as e:
        print(f"⚠️ Warning: Database connection failed: {e}")
    
    # Error handler for rate limiting
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'success': False,
            'message': 'Rate limit exceeded. Please try again later.',
            'retry_after': e.retry_after
        }), 429
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    
    @app.route('/')
    def index():
        """Serve the login page or redirect to dashboard if authenticated"""
        if 'user' in session:
            return redirect('/dashboard.html')
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/dashboard.html')
    def dashboard():
        """Serve the dashboard page (requires authentication)"""
        if 'user' not in session:
            return redirect('/')
        return send_from_directory(app.static_folder, 'dashboard.html')
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            db.get_database().command('ping')
            db_status = "connected"
        except:
            db_status = "disconnected"
        
        return jsonify({
            'status': 'healthy',
            'database': db_status,
            'session': 'user' in session,
            'cors_enabled': True,
            'rate_limiting_enabled': True
        })
    
    @app.route('/security-info')
    @limiter.limit("30 per minute")
    def security_info():
        """Security information endpoint"""
        return jsonify({
            'cors': {
                'enabled': True,
                'allowed_origins': cors_origins
            },
            'rate_limiting': {
                'enabled': True,
                'default_limits': app.config.get('RATELIMIT_DEFAULT'),
                'storage': app.config.get('RATELIMIT_STORAGE_URL'),
                'strategy': app.config.get('RATELIMIT_STRATEGY')
            },
            'authentication': {
                'session_based': True,
                'password_hashing': 'bcrypt'
            }
        })
    
    # Handle cleanup on app shutdown
    @app.teardown_appcontext
    def close_db(error):
        """Close database connection on shutdown"""
        pass  # Connection will be closed by the singleton
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5050)
