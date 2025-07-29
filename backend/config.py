import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'electricity-prediction-secret-key-2024'
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # MongoDB Configuration
    DATABASE_CONNECTION_STRING = os.environ.get('DATABASE_CONNECTION_STRING')
    DATABASE_NAME = os.environ.get('DATABASE_NAME') or 'energenius'
    
    # ML API Configuration
    ML_API_BASE_URL = os.environ.get('ML_API_BASE_URL')
    ML_API_TIMEOUT = int(os.environ.get('ML_API_TIMEOUT', '30'))
    
    # CORS Configuration
    CORS_ORIGINS = [
        'http://localhost:3000',      # React development
        'http://localhost:5173',      # Vite development  
        'http://localhost:8080',      # Vue development
        'http://127.0.0.1:3000',      # Alternative localhost
        'http://127.0.0.1:5173',      # Alternative localhost
    ]
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STRATEGY = "fixed-window"
    
    # Demo users (in production, this would be a database)
    DEMO_USERS = {
        'admin@electric-grid.com': {
            'password': '$2b$12$LQv3c1yqBwlVHpPjrJ0L5.jJ5Q8ZqJ0Z8qJ0Z8qJ0Z8qJ0Z8qJ0Z8q',  # password: admin123
            'name': 'Grid Administrator',
            'role': 'admin'
        },
        'analyst@electric-grid.com': {
            'password': '$2b$12$LQv3c1yqBwlVHpPjrJ0L5.jJ5Q8ZqJ0Z8qJ0Z8qJ0Z8qJ0Z8qJ0Z8q',  # password: analyst123
            'name': 'Energy Analyst',
            'role': 'analyst'
        }
    }
