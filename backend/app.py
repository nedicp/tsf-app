from flask import Flask, session, redirect, send_from_directory, jsonify
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

    app.config.from_object(Config)

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

    limiter.init_app(app)
    limiter._default_limits = app.config.get('RATELIMIT_DEFAULT', "200 per day;50 per hour")
    limiter._storage_uri = app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    limiter._strategy = app.config.get('RATELIMIT_STRATEGY', 'fixed-window')

    Session(app)

    try:
        db.connect()
        print("Database connection initialized")
    except Exception as e:
        print(f"Warning: Database connection failed: {e}")

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'success': False,
            'message': 'Rate limit exceeded. Please try again later.',
            'retry_after': e.retry_after
        }), 429

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

    @app.teardown_appcontext
    def close_db(error):
        """Close database connection on shutdown"""
        pass  # Connection will be closed by the singleton

    return app
