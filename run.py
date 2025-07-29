#!/usr/bin/env python3
"""
Energenius - Electricity Consumption Prediction App
Entry point for the Flask application
"""

from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("🔌 Energenius starting...")
    print("📊 Access the application at: http://localhost:5050")
    print("🔑 Demo credentials:")
    print("   Username: admin, analyst, or demo")
    print("   Password: admin123, analyst123, or demo123")
    app.run(debug=True, host='0.0.0.0', port=5050)
