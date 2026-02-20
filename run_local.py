#!/usr/bin/env python3
"""
Local test runner for FRIZZLY API
Run with: python3 run_local.py
"""
from flask_app import app

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🍕 FRIZZLY API - Local Test Server")
    print("="*50)
    print("\n📍 Server running at: http://localhost:8080")
    print("\n📚 Available endpoints:")
    print("   GET  http://localhost:8080/")
    print("   GET  http://localhost:8080/api/health")
    print("   GET  http://localhost:8080/api/products")
    print("\n⚠️  Protected endpoints require Authorization header")
    print("\n🛑 Press CTRL+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
