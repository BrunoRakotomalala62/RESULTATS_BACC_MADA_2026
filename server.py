#!/usr/bin/env python3
"""
Serveur de développement local.
Pour Vercel, le point d'entrée est api/index.py

Usage:
    python server.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

from index import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    print(f"🚀 API Bacc Madagascar - http://localhost:{port}")
    print(f"📖 Documentation : http://localhost:{port}/")
    print(f"🔍 Recherche : http://localhost:{port}/api/bacc/recherche?nom=RAKOTO&province=mahajanga")
    app.run(host="0.0.0.0", port=port, debug=debug)
