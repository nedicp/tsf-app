#!/usr/bin/env python3
"""
Backend run script for Energenius
Alternative entry point from backend directory
"""

import sys
import os

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("🔌 Energenius Backend starting...")
    print("📊 Access at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
