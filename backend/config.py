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
    
    # AWS Configuration for API calls
    AWS_API_ENDPOINT = os.environ.get('AWS_API_ENDPOINT') or 'https://your-app-runner-endpoint.com'
    
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
