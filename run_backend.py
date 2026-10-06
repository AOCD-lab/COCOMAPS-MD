#!/usr/bin/env python3
"""
Run script for the Flask backend (from project root)
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app
from backend.routes.upload import get_analysis_queue

if __name__ == '__main__':
    app = create_app()
    try:
        get_analysis_queue(app)
    except Exception as exc:
        app.logger.error("Analysis queue unavailable at startup: %s", exc)
    print("=" * 60)
    print("PDB Analysis API Server")
    print("=" * 60)
    print("API available at: http://localhost:5001")
    print("Endpoints:")
    print("  GET  /api/systems")
    print("  GET  /api/systems/<id>/interactions")
    print("  GET  /api/systems/<id>/area")
    print("  GET  /api/systems/<id>/trends")
    print("  POST /api/upload")
    print("  GET  /api/status/<id>")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
