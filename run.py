#!/usr/bin/env python3
"""
Energenius - Electricity Consumption Prediction App
Entry point for the Flask application
"""

from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("🔌 Energenius starting...")
    print("📊 Access the application at: http://localhost:5000")
    print("🔑 Demo credentials:")
    print("   Admin: admin@electric-grid.com / admin123")
    print("   Analyst: analyst@electric-grid.com / analyst123")
    app.run(debug=True, host='0.0.0.0', port=5000)
