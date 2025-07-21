from flask import Flask, session, redirect, url_for, request, send_from_directory, jsonify
from flask_session import Session
from backend.config import Config
from backend.auth.routes import auth_bp
from backend.api.routes import api_bp
from backend.utils.database import db
import os

def create_app():
    app = Flask(__name__, 
                static_folder='../frontend',
                static_url_path='')
    
    # Load configuration
    app.config.from_object(Config)
    
    # Initialize Flask-Session
    Session(app)
    
    # Initialize database connection
    try:
        db.connect()
        print("✅ Database connection initialized")
    except Exception as e:
        print(f"⚠️ Warning: Database connection failed: {e}")
    
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
            'session': 'user' in session
        })
    
    # Handle cleanup on app shutdown
    @app.teardown_appcontext
    def close_db(error):
        """Close database connection on shutdown"""
        pass  # Connection will be closed by the singleton
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
