"""
Pytest configuration — ensure tests use the CI database or a safe fallback.
"""

import os

# Set DATABASE_URL before any app module is imported.
# In CI, the env var is already set by the workflow; this is a local fallback.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
