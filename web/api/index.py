"""
Vercel serverless entrypoint. Vercel's Python runtime detects the ASGI `app`
variable and serves it. Everything else lives in app/.
"""
import os
import sys

# Ensure the project root (web/) is importable so `app` resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402

# Vercel looks for `app`.
