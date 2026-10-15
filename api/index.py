"""Vercel Serverless Function entrypoint for FreshRoute FastAPI app."""
import sys
from pathlib import Path

# Add backend/src to sys.path so freshroute and validator are importable
_root = Path(__file__).resolve().parent.parent
_src = _root / "backend" / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from freshroute.api.app import app  # noqa: E402, F401
