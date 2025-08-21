"""
Energenius - Electricity Consumption Prediction App
Entry point for the Flask application
"""

from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("Energenius starting...")
    print("Access the application at: http://localhost:5050")
    app.run(debug=True, host='0.0.0.0', port=5050)
