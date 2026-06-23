"""
Vercel serverless entrypoint. Vercel's Python runtime detects the ASGI `app`
variable and serves it. Everything else lives in app/.
"""
import os
import sys

# Ensure the project root (web/) is importable so `app` resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel detects this top-level ASGI `app`. Keep the noqa: it is an intentional
# re-export (not unused) and must stay AFTER the sys.path tweak above.
from app.main import app  # noqa: F401,E402
